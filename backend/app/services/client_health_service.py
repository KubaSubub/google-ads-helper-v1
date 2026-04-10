"""Client Health Service — aggregates account health from DB + Google Ads API.

Data sources (by priority / availability):
  account_metadata  → Client model (DB, always) + Google Ads customer resource (API, optional)
  sync_health       → SyncLog (DB, always)
  conversion_tracking → ConversionAction table (DB, synced via sync_conversion_actions)
  linked_accounts   → Google Ads product_link resource (API, optional; fallback = not_linked)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy.orm import Session

from app.models import Client, SyncLog
from app.models.conversion_action import ConversionAction
from app.schemas.client import (
    AccountMetadata,
    ClientHealthResponse,
    ConversionActionSummary,
    ConversionTracking,
    LinkedAccount,
    SyncHealth,
)

_LINKED_ACCOUNT_TYPES = ("GA4", "MERCHANT_CENTER", "YOUTUBE", "SEARCH_CONSOLE")

# Strict digit-only pattern for Google Ads customer IDs (10 digits after normalization).
# Validated before interpolation into GAQL to prevent injection.
_CUSTOMER_ID_RE = re.compile(r"^\d{10}$")


def _hours_since(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def _freshness(hours: float | None) -> str:
    """green < 6h, yellow 6-12h (daily optimizer needs fresh data), red ≥ 12h."""
    if hours is None:
        return "red"
    if hours < 6:
        return "green"
    if hours < 12:
        return "yellow"
    return "red"


def _build_sync_health(db: Session, client_id: int) -> SyncHealth:
    log = (
        db.query(SyncLog)
        .filter(SyncLog.client_id == client_id)
        .order_by(SyncLog.finished_at.desc().nullslast())
        .first()
    )
    if log is None:
        return SyncHealth(freshness="red")

    finished = log.finished_at
    hours = _hours_since(finished)
    duration: float | None = None
    if log.started_at and finished:
        started = log.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        duration = (finished - started).total_seconds()

    return SyncHealth(
        last_synced_at=log.finished_at,
        hours_since_sync=round(hours, 2) if hours is not None else None,
        freshness=_freshness(hours),
        last_status=log.status,
        last_duration_seconds=round(duration, 1) if duration is not None else None,
    )


def _build_conversion_tracking(db: Session, client_id: int) -> ConversionTracking:
    actions = (
        db.query(ConversionAction)
        .filter(ConversionAction.client_id == client_id)
        .all()
    )
    active = [a for a in actions if a.status == "ENABLED"]

    primary_attribution: str | None = None
    if active:
        first_with_attribution = next(
            (a for a in active if a.attribution_model), None
        )
        if first_with_attribution:
            primary_attribution = first_with_attribution.attribution_model

    summaries = [
        ConversionActionSummary(
            name=a.name,
            category=a.category,
            status=a.status,
            include_in_conversions=bool(a.include_in_conversions_metric),
            primary_for_goal=bool(a.primary_for_goal),
        )
        for a in active
    ]

    return ConversionTracking(
        active_count=len(active),
        attribution_model=primary_attribution,
        enhanced_conversions_enabled=None,  # not available from DB in SDK 29.1
        actions=summaries,
    )


def _build_linked_accounts_shell() -> list[LinkedAccount]:
    """Return placeholder entries for all known integration types (MVP B2 shell).

    detected_via is "shell_placeholder" because no API call is made yet;
    a future task can query Google Ads product_link resource for real data.
    """
    return [
        LinkedAccount(type=t, status="not_linked", resource_name=None, detected_via="shell_placeholder")
        for t in _LINKED_ACCOUNT_TYPES
    ]


def _try_google_ads_metadata(client: Client) -> tuple[dict, list[str]]:
    """Attempt to enrich account_metadata from Google Ads API.

    Returns (extra_fields dict, errors list). On any failure returns ({}, [error]).
    """
    from app.services.google_ads import google_ads_service

    errors: list[str] = []
    extra: dict = {}
    try:
        diagnostics = google_ads_service.get_connection_diagnostics()
        if not diagnostics.get("ready"):
            errors.append("google_ads_api_unavailable")
            return extra, errors

        cid = google_ads_service.normalize_customer_id(client.google_customer_id)

        # Validate customer ID is purely numeric before interpolating into GAQL
        # to prevent injection attacks if the DB field contains unexpected content.
        if not _CUSTOMER_ID_RE.fullmatch(cid):
            logger.error("client_health: invalid customer_id format '{}' — skipping API call", cid)
            errors.append("invalid_customer_id_format")
            return extra, errors

        ads_service = google_ads_service.client.get_service("GoogleAdsService")
        query = (
            "SELECT customer.time_zone, customer.auto_tagging_enabled, "
            "customer.tracking_url_template, customer.manager "
            f"FROM customer WHERE customer.id = {cid}"
        )
        response = ads_service.search(customer_id=cid, query=query)
        for row in response:
            c = row.customer
            extra["timezone"] = c.time_zone or None
            extra["auto_tagging_enabled"] = c.auto_tagging_enabled
            extra["tracking_url_template"] = c.tracking_url_template or None
            # "MANAGER" / "CLIENT" — preferred terms (Google deprecated "MCC" in 2022)
            extra["account_type"] = "MANAGER" if c.manager else "CLIENT"
            break
    except Exception as exc:
        logger.warning("client_health: Google Ads metadata fetch failed: {}", str(exc)[:200])
        errors.append("google_ads_metadata_error")
    return extra, errors


def get_client_health(db: Session, client: Client) -> ClientHealthResponse:
    """Aggregate health data for a client. Never raises — always returns 200-safe response."""
    errors: list[str] = []

    # account_metadata — from DB (always), enriched from API (optional)
    api_extra, api_errors = _try_google_ads_metadata(client)
    errors.extend(api_errors)

    account_metadata = AccountMetadata(
        customer_id=client.google_customer_id,
        name=client.name,
        account_type=api_extra.get("account_type", "STANDARD"),
        currency=client.currency or "PLN",
        timezone=api_extra.get("timezone"),
        auto_tagging_enabled=api_extra.get("auto_tagging_enabled"),
        tracking_url_template=api_extra.get("tracking_url_template"),
    )

    # sync_health — from SyncLog (DB, always)
    sync_health = _build_sync_health(db, client.id)

    # conversion_tracking — from ConversionAction table (DB, always)
    conversion_tracking = _build_conversion_tracking(db, client.id)

    # linked_accounts — MVP shell (no live API call for linked accounts yet)
    linked_accounts = _build_linked_accounts_shell()

    return ClientHealthResponse(
        account_metadata=account_metadata,
        sync_health=sync_health,
        conversion_tracking=conversion_tracking,
        linked_accounts=linked_accounts,
        errors=errors,
    )
