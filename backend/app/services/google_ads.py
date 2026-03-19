"""
Google Ads API Service — handles authentication and data fetching.

This service wraps the official google-ads Python client and provides
methods to fetch campaigns, ad groups, keywords, search terms, and ads
from the Google Ads API.

IMPORTANT: You need a Google Ads API developer token and OAuth credentials.
See: https://developers.google.com/google-ads/api/docs/first-call/overview
"""

from datetime import date, datetime, timedelta, timezone
from loguru import logger
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import (
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily, MetricSegmented,
    ChangeEvent, ActionLog, KeywordDaily, NegativeKeyword,
)
from app.services.cache import get_cached, set_cached
from app.services.campaign_roles import apply_role_classification
from app.services.credentials_service import CredentialsService
from app.services.recommendation_contract import (
    GOOGLE_ADS_API,
    build_action_payload,
    build_stable_key,
    compute_confidence_score,
    compute_priority,
    compute_risk_score,
    default_expires_at,
    estimate_impact_micros,
)

# Optional: Import google-ads client (only if credentials are configured)
try:
    from google.ads.googleads.client import GoogleAdsClient
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    logger.warning("google-ads package not installed. API sync will be unavailable.")

try:
    from google.ads.googleads.errors import GoogleAdsException
except ImportError:
    GoogleAdsException = None


# Map Google Ads quality score enum values to integers
QS_ENUM_MAP = {
    "BELOW_AVERAGE": 1,
    "AVERAGE": 2,
    "ABOVE_AVERAGE": 3,
    "UNSPECIFIED": None,
    "UNKNOWN": None,
}


def _safe_float(val):
    """Safely convert API value to float, returning None for missing/zero."""
    if val is None:
        return None
    f = float(val)
    return f if f != 0 else None


def _safe_is(val):
    """Convert impression share from API (0.0-1.0 or None)."""
    if val is None:
        return None
    f = float(val)
    return f if f > 0 else None


def _qs_enum(val):
    """Map QS enum to integer (1/2/3) or None."""
    if val is None:
        return None
    name = val.name if hasattr(val, 'name') else str(val)
    return QS_ENUM_MAP.get(name)


class GoogleAdsService:
    """Wrapper around Google Ads API for data fetching and mutations."""

    def __init__(self):
        self.client = None
        self._try_init()

    def _try_init(self):
        """Attempt to initialize GoogleAdsClient from the secure credential store."""
        if not GOOGLE_ADS_AVAILABLE:
            self.client = None
            return

        credentials = CredentialsService.get_google_ads_credentials()
        refresh_token = credentials["refresh_token"]
        if not refresh_token:
            logger.info("No refresh_token in keyring - user must complete OAuth first")
            self.client = None
            return

        missing_setup = [
            key for key in CredentialsService.SETUP_KEYS if not credentials.get(key)
        ]
        if missing_setup:
            logger.warning(
                "Missing setup credentials in keyring: {}".format(
                    ", ".join(missing_setup)
                )
            )
            self.client = None
            return

        login_customer_id = credentials["login_customer_id"]

        try:
            config = {
                "developer_token": credentials["developer_token"],
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "refresh_token": refresh_token,
                "use_proto_plus": True,
            }
            if login_customer_id:
                config["login_customer_id"] = login_customer_id

            self.client = GoogleAdsClient.load_from_dict(config)
            logger.info("Google Ads API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Ads client: {e}")
            self.client = None

    def reinitialize(self):
        """Re-init client after credential changes."""
        self.client = None
        self._try_init()

    @property
    def is_connected(self) -> bool:
        if self.client is None:
            self._try_init()
        return self.client is not None

    @staticmethod
    def _missing_setup_credentials(credentials: dict[str, str | None]) -> list[str]:
        return [key for key in CredentialsService.SETUP_KEYS if not credentials.get(key)]

    @staticmethod
    def _format_missing_credentials(keys: list[str]) -> str:
        return "Brakuje zapisanych credentials Google Ads: {}.".format(
            ", ".join(keys)
        )

    @staticmethod
    def get_login_customer_id() -> str | None:
        return CredentialsService.get(CredentialsService.LOGIN_CUSTOMER_ID)

    @staticmethod
    def normalize_customer_id(customer_id: str | None) -> str:
        return (customer_id or "").replace("-", "").strip()

    @staticmethod
    def _format_google_ads_error(exc: Exception) -> str:
        if GoogleAdsException and isinstance(exc, GoogleAdsException):
            details = []
            for error in getattr(exc.failure, "errors", []):
                code = None
                if getattr(error, "error_code", None) and hasattr(error.error_code, "_pb"):
                    fields = error.error_code._pb.ListFields()
                    if fields:
                        code = fields[0][0].name
                location = None
                if getattr(error, "location", None) and getattr(error.location, "field_path_elements", None):
                    location = ".".join(
                        element.field_name for element in error.location.field_path_elements
                    )
                part = error.message or "Google Ads API error"
                if code:
                    part = f"{code}: {part}"
                if location:
                    part = f"{part} (field: {location})"
                details.append(part)
            if details:
                prefix = f"request_id={exc.request_id}: " if getattr(exc, "request_id", None) else ""
                return prefix + "; ".join(details)

        if hasattr(exc, "details") and callable(exc.details):
            try:
                details = exc.details()
                if details:
                    return str(details)
            except Exception:
                pass

        return str(exc)

    def _find_client_record(self, db: Session, customer_id: str) -> Client | None:
        normalized_customer_id = self.normalize_customer_id(customer_id)
        return db.query(Client).filter(
            func.replace(Client.google_customer_id, "-", "") == normalized_customer_id
        ).first()

    @staticmethod
    def _mark_missing_campaigns_removed(
        db: Session,
        client_id: int,
        seen_google_campaign_ids: set[str],
    ) -> int:
        removed = 0
        existing_campaigns = db.query(Campaign).filter(Campaign.client_id == client_id).all()
        for campaign in existing_campaigns:
            if campaign.google_campaign_id not in seen_google_campaign_ids and campaign.status != "REMOVED":
                campaign.status = "REMOVED"
                removed += 1
        return removed

    @staticmethod
    def _mark_missing_ad_groups_removed(
        db: Session,
        client_id: int,
        seen_ad_group_keys: set[tuple[int, str]],
    ) -> int:
        removed = 0
        existing_ad_groups = (
            db.query(AdGroup)
            .join(Campaign)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        for ad_group in existing_ad_groups:
            key = (ad_group.campaign_id, ad_group.google_ad_group_id)
            if key not in seen_ad_group_keys and ad_group.status != "REMOVED":
                ad_group.status = "REMOVED"
                removed += 1
        return removed

    @staticmethod
    def _mark_missing_keywords_removed(
        db: Session,
        client_id: int,
        seen_keyword_keys: set[tuple[int, str]],
    ) -> int:
        removed = 0
        existing_keywords = (
            db.query(Keyword)
            .join(AdGroup)
            .join(Campaign)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        for keyword in existing_keywords:
            key = (keyword.ad_group_id, keyword.google_keyword_id)
            if key not in seen_keyword_keys and keyword.status != "REMOVED":
                keyword.status = "REMOVED"
                removed += 1
        return removed

    @staticmethod
    def _keyword_kind_from_negative(is_negative: bool) -> str:
        return "NEGATIVE" if is_negative else "POSITIVE"

    @staticmethod
    def _negative_seen_key(
        negative_scope: str,
        campaign_id: int | None,
        ad_group_id: int | None,
        google_criterion_id: str | None,
        text: str,
        match_type: str | None,
    ) -> tuple[str, int | None, int | None, str, str, str | None]:
        return (
            negative_scope,
            campaign_id,
            ad_group_id,
            google_criterion_id or "",
            (text or "").strip().lower(),
            match_type,
        )

    @staticmethod
    def _mark_missing_negative_keywords_removed(
        db: Session,
        client_id: int,
        seen_negative_keys: set[tuple[str, int | None, int | None, str, str, str | None]],
    ) -> int:
        removed = 0
        existing_negatives = db.query(NegativeKeyword).filter(NegativeKeyword.client_id == client_id).all()
        for negative in existing_negatives:
            key = GoogleAdsService._negative_seen_key(
                negative.negative_scope,
                negative.campaign_id,
                negative.ad_group_id,
                negative.google_criterion_id,
                negative.text,
                negative.match_type,
            )
            if key not in seen_negative_keys and negative.status != "REMOVED":
                negative.status = "REMOVED"
                removed += 1
        return removed

    @staticmethod
    def _log_negative_positive_guard(
        customer_id: str,
        campaign_id: str | None,
        ad_group_id: str | None,
        criterion_id: str | None,
        keyword_text: str | None,
        path_label: str,
    ) -> None:
        logger.warning(
            "Skipped negative criterion in positive keyword path '{}' customer_id={} campaign_id={} ad_group_id={} criterion_id={} keyword_text={}",
            path_label,
            customer_id,
            campaign_id,
            ad_group_id,
            criterion_id,
            keyword_text,
        )

    @staticmethod
    def _find_matching_negative_keyword(
        db: Session,
        client_id: int,
        campaign_id: int | None,
        ad_group_id: int | None,
        negative_scope: str,
        google_criterion_id: str | None,
        text: str,
        match_type: str | None,
    ) -> NegativeKeyword | None:
        if google_criterion_id:
            existing = (
                db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.client_id == client_id,
                    NegativeKeyword.google_criterion_id == google_criterion_id,
                )
                .first()
            )
            if existing:
                return existing

        return (
            db.query(NegativeKeyword)
            .filter(
                NegativeKeyword.client_id == client_id,
                NegativeKeyword.campaign_id == campaign_id,
                NegativeKeyword.ad_group_id == ad_group_id,
                NegativeKeyword.negative_scope == negative_scope,
                func.lower(NegativeKeyword.text) == (text or "").strip().lower(),
                NegativeKeyword.match_type == match_type,
            )
            .first()
        )

    @staticmethod
    def _escape_gaql_string(value: str) -> str:
        return value.replace("'", "''")

    def _build_keyword_debug_query(
        self,
        search_terms: list[str] | None = None,
        include_removed: bool = True,
        limit: int = 50,
    ) -> str:
        has_search_terms = bool(search_terms)
        filters = []

        if not include_removed:
            filters.extend(
                [
                    "ad_group_criterion.status != 'REMOVED'",
                    "campaign.status != 'REMOVED'",
                ]
            )

        where_clause = ""
        if filters:
            where_clause = "WHERE " + "\n              AND ".join(filters)

        limit_clause = f"\n            LIMIT {int(limit)}" if not has_search_terms else ""

        return """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status
            FROM keyword_view
            {where_clause}
            ORDER BY campaign.name, ad_group.name, ad_group_criterion.keyword.text{limit_clause}
        """.format(where_clause=where_clause, limit_clause=limit_clause)
    def debug_keyword_sources(
        self,
        db: Session,
        customer_id: str,
        search_terms: list[str] | None = None,
        include_removed: bool = True,
        limit: int = 50,
    ) -> dict:
        """Fetch raw keyword_view rows and matching local DB rows for source diagnostics."""
        if not self.is_connected:
            raise RuntimeError("Google Ads API not connected")

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            raise RuntimeError(f"Client with customer_id={customer_id} not found in DB")

        normalized_terms = [term.strip() for term in (search_terms or []) if term and term.strip()]
        query = self._build_keyword_debug_query(
            search_terms=normalized_terms,
            include_removed=include_removed,
            limit=limit,
        )

        ga_service = self.client.get_service("GoogleAdsService")
        fetched_at = datetime.now(timezone.utc)
        response = ga_service.search(customer_id=normalized_customer_id, query=query)

        api_rows = []
        for row in response:
            api_row = {
                "campaign_id": str(row.campaign.id),
                "campaign_name": row.campaign.name,
                "campaign_status": getattr(row.campaign.status, "name", str(row.campaign.status)),
                "ad_group_id": str(row.ad_group.id),
                "ad_group_name": row.ad_group.name,
                "ad_group_status": getattr(row.ad_group.status, "name", str(row.ad_group.status)),
                "criterion_id": str(row.ad_group_criterion.criterion_id),
                "keyword_text": row.ad_group_criterion.keyword.text,
                "match_type": getattr(
                    row.ad_group_criterion.keyword.match_type,
                    "name",
                    str(row.ad_group_criterion.keyword.match_type),
                ),
                "status": getattr(
                    row.ad_group_criterion.status,
                    "name",
                    str(row.ad_group_criterion.status),
                ),
            }
            if normalized_terms:
                keyword_text = api_row["keyword_text"].lower()
                if not any(term.lower() in keyword_text for term in normalized_terms):
                    continue
            api_rows.append(api_row)
            if len(api_rows) >= limit:
                break

        local_query = (
            db.query(Keyword, AdGroup, Campaign)
            .join(AdGroup, Keyword.ad_group_id == AdGroup.id)
            .join(Campaign, AdGroup.campaign_id == Campaign.id)
            .filter(Campaign.client_id == client_record.id)
        )

        if not include_removed:
            local_query = local_query.filter(Keyword.status != "REMOVED")

        if normalized_terms:
            local_filters = [
                func.lower(Keyword.text).like(f"%{term.lower()}%")
                for term in normalized_terms
            ]
            local_query = local_query.filter(or_(*local_filters))

        local_rows = []
        for keyword, ad_group, campaign in (
            local_query
            .order_by(Campaign.name.asc(), AdGroup.name.asc(), Keyword.text.asc())
            .limit(limit)
            .all()
        ):
            local_rows.append(
                {
                    "keyword_id": keyword.id,
                    "campaign_id": campaign.id,
                    "campaign_google_id": campaign.google_campaign_id,
                    "campaign_name": campaign.name,
                    "campaign_status": campaign.status,
                    "ad_group_id": ad_group.id,
                    "ad_group_google_id": ad_group.google_ad_group_id,
                    "ad_group_name": ad_group.name,
                    "ad_group_status": ad_group.status,
                    "google_keyword_id": keyword.google_keyword_id,
                    "keyword_text": keyword.text,
                    "match_type": keyword.match_type,
                    "status": keyword.status,
                    "updated_at": keyword.updated_at.isoformat() if keyword.updated_at else None,
                }
            )

        return {
            "client_id": client_record.id,
            "client_name": client_record.name,
            "customer_id": normalized_customer_id,
            "search_terms": normalized_terms,
            "include_removed": include_removed,
            "limit": limit,
            "fetched_at": fetched_at.isoformat(),
            "query": query,
            "api_count": len(api_rows),
            "local_count": len(local_rows),
            "api_rows": api_rows,
            "local_rows": local_rows,
        }
    def get_connection_diagnostics(self) -> dict:
        credentials = CredentialsService.get_google_ads_credentials()
        missing_setup = self._missing_setup_credentials(credentials)
        authenticated = bool(credentials["refresh_token"])
        configured = not missing_setup
        missing_credentials = list(missing_setup)

        if not authenticated:
            missing_credentials.append(CredentialsService.REFRESH_TOKEN)

        if not configured:
            return {
                "authenticated": authenticated,
                "configured": False,
                "ready": False,
                "connected": False,
                "reason": self._format_missing_credentials(missing_setup),
                "missing_credentials": missing_credentials,
                "has_login_customer_id": bool(credentials["login_customer_id"]),
            }

        if not authenticated:
            return {
                "authenticated": False,
                "configured": True,
                "ready": False,
                "connected": False,
                "reason": "Brak refresh_token. Zaloguj sie przez Google, aby polaczyc aplikacje z Google Ads API.",
                "missing_credentials": missing_credentials,
                "has_login_customer_id": bool(credentials["login_customer_id"]),
            }

        if not GOOGLE_ADS_AVAILABLE:
            return {
                "authenticated": True,
                "configured": True,
                "ready": False,
                "connected": False,
                "reason": "Pakiet google-ads nie jest dostepny w srodowisku aplikacji.",
                "missing_credentials": [],
                "has_login_customer_id": bool(credentials["login_customer_id"]),
            }

        connected = self.is_connected
        if connected:
            return {
                "authenticated": True,
                "configured": True,
                "ready": True,
                "connected": True,
                "reason": "Google Ads API jest gotowe do uzycia.",
                "missing_credentials": [],
                "has_login_customer_id": bool(credentials["login_customer_id"]),
            }

        return {
            "authenticated": True,
            "configured": True,
            "ready": False,
            "connected": False,
            "reason": "Credentials sa zapisane, ale klient Google Ads API nie moze zostac zainicjalizowany. Sprawdz poprawnosc danych i dostep do konta Google Ads.",
            "missing_credentials": [],
            "has_login_customer_id": bool(credentials["login_customer_id"]),
        }

    # -----------------------------------------------------------------------
    # Campaign Sync (structural data only — no metrics)
    # -----------------------------------------------------------------------

    def sync_campaigns(self, db: Session, customer_id: str) -> int:
        """
        Fetch all campaigns from Google Ads API and upsert into local DB.
        Returns the number of campaigns synced.
        """
        if not self.is_connected:
            logger.warning("Google Ads API not connected - skipping campaign sync")
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            logger.error(f"Client with customer_id={customer_id} not found in DB")
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        campaign_queries = [
            (
                "extended",
                """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.bidding_strategy_type
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """,
            ),
            (
                "fallback",
                """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """,
            ),
        ]

        try:
            response = None
            selected_query = None
            last_error = None
            for query_name, query in campaign_queries:
                try:
                    response = ga_service.search(customer_id=normalized_customer_id, query=query)
                    selected_query = query_name
                    break
                except Exception as query_exc:
                    last_error = query_exc
                    logger.warning(
                        f"Campaign sync query '{query_name}' failed for customer {normalized_customer_id}: "
                        f"{self._format_google_ads_error(query_exc)}"
                    )

            if response is None:
                raise RuntimeError(self._format_google_ads_error(last_error)) from last_error

            count = 0
            seen_google_campaign_ids: set[str] = set()
            for row in response:
                campaign = row.campaign
                budget = row.campaign_budget
                google_campaign_id = str(campaign.id)
                seen_google_campaign_ids.add(google_campaign_id)

                existing = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == google_campaign_id,
                ).first()

                bidding_strategy = existing.bidding_strategy if existing else None
                if selected_query == "extended" and getattr(campaign, "bidding_strategy_type", None):
                    bidding_strategy = campaign.bidding_strategy_type.name

                data = {
                    "client_id": client_record.id,
                    "google_campaign_id": google_campaign_id,
                    "name": campaign.name,
                    "status": campaign.status.name,
                    "campaign_type": campaign.advertising_channel_type.name,
                    "budget_micros": budget.amount_micros if budget.amount_micros else 0,
                    "bidding_strategy": bidding_strategy,
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(Campaign(**data))
                count += 1

            removed_count = self._mark_missing_campaigns_removed(
                db,
                client_record.id,
                seen_google_campaign_ids,
            )
            db.commit()
            if selected_query == "fallback":
                logger.warning(
                    f"Campaign sync for customer {normalized_customer_id} succeeded with fallback GAQL query"
                )
            logger.info(
                f"Synced {count} campaigns for customer {normalized_customer_id} "
                f"(marked {removed_count} as REMOVED)"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing campaigns: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Campaign Impression Share Sync (aggregated last 30 days)
    # -----------------------------------------------------------------------

    def sync_campaign_impression_share(self, db: Session, customer_id: str) -> int:
        """Fetch campaign-level impression share metrics (last 30d aggregate)."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id,
                metrics.search_impression_share,
                metrics.search_top_impression_share,
                metrics.search_absolute_top_impression_share,
                metrics.search_budget_lost_impression_share,
                metrics.search_budget_lost_top_impression_share,
                metrics.search_budget_lost_absolute_top_impression_share,
                metrics.search_rank_lost_impression_share,
                metrics.search_rank_lost_top_impression_share,
                metrics.search_rank_lost_absolute_top_impression_share,
                metrics.search_click_share,
                metrics.search_exact_match_impression_share,
                metrics.absolute_top_impression_percentage,
                metrics.top_impression_percentage
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
              AND campaign.status != 'REMOVED'
              AND campaign.advertising_channel_type = 'SEARCH'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                m = row.metrics

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                campaign.search_impression_share = _safe_is(m.search_impression_share)
                campaign.search_top_impression_share = _safe_is(m.search_top_impression_share)
                campaign.search_abs_top_impression_share = _safe_is(m.search_absolute_top_impression_share)
                campaign.search_budget_lost_is = _safe_is(m.search_budget_lost_impression_share)
                campaign.search_budget_lost_top_is = _safe_is(m.search_budget_lost_top_impression_share)
                campaign.search_budget_lost_abs_top_is = _safe_is(m.search_budget_lost_absolute_top_impression_share)
                campaign.search_rank_lost_is = _safe_is(m.search_rank_lost_impression_share)
                campaign.search_rank_lost_top_is = _safe_is(m.search_rank_lost_top_impression_share)
                campaign.search_rank_lost_abs_top_is = _safe_is(m.search_rank_lost_absolute_top_impression_share)
                campaign.search_click_share = _safe_is(m.search_click_share)
                campaign.search_exact_match_is = _safe_is(m.search_exact_match_impression_share)
                campaign.abs_top_impression_pct = _safe_is(m.absolute_top_impression_percentage)
                campaign.top_impression_pct = _safe_is(m.top_impression_percentage)
                count += 1

            db.commit()
            logger.info(f"Synced impression share for {count} campaigns")
            return count

        except Exception as e:
            logger.error(f"Error syncing campaign impression share: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Ad Groups Sync
    # -----------------------------------------------------------------------

    def sync_ad_groups(self, db: Session, customer_id: str) -> int:
        """Fetch all ad groups from Google Ads API and upsert into local DB."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                ad_group.id,
                ad_group.name,
                ad_group.status,
                ad_group.cpc_bid_micros,
                campaign.id
            FROM ad_group
            WHERE ad_group.status != 'REMOVED'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            seen_ad_group_keys: set[tuple[int, str]] = set()
            for row in response:
                ad_group = row.ad_group
                campaign_google_id = str(row.campaign.id)

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                google_ad_group_id = str(ad_group.id)
                seen_ad_group_keys.add((campaign.id, google_ad_group_id))

                existing = db.query(AdGroup).filter(
                    AdGroup.campaign_id == campaign.id,
                    AdGroup.google_ad_group_id == google_ad_group_id,
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "google_ad_group_id": google_ad_group_id,
                    "name": ad_group.name,
                    "status": ad_group.status.name,
                    "bid_micros": ad_group.cpc_bid_micros if ad_group.cpc_bid_micros else 0,
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(AdGroup(**data))
                count += 1

            removed_count = self._mark_missing_ad_groups_removed(
                db,
                client_record.id,
                seen_ad_group_keys,
            )
            db.commit()
            logger.info(
                f"Synced {count} ad groups for customer {normalized_customer_id} "
                f"(marked {removed_count} as REMOVED)"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing ad groups: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Keywords Sync (expanded with IS, QS historical, extended conv, top %)
    # -----------------------------------------------------------------------

    def sync_keywords(self, db: Session, customer_id: str) -> int:
        """Fetch all keywords from Google Ads API and upsert into local DB."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id,
                ad_group.id,
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.final_urls,
                ad_group_criterion.effective_cpc_bid_micros,
                ad_group_criterion.quality_info.quality_score,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc,
                metrics.search_impression_share,
                metrics.search_top_impression_share,
                metrics.search_absolute_top_impression_share,
                metrics.search_rank_lost_impression_share,
                metrics.search_rank_lost_top_impression_share,
                metrics.search_rank_lost_absolute_top_impression_share,
                metrics.search_exact_match_impression_share,
                metrics.historical_quality_score,
                metrics.historical_creative_quality_score,
                metrics.historical_landing_page_quality_score,
                metrics.historical_search_predicted_ctr,
                metrics.all_conversions,
                metrics.all_conversions_value,
                metrics.cross_device_conversions,
                metrics.value_per_conversion,
                metrics.conversions_value_per_cost,
                metrics.absolute_top_impression_percentage,
                metrics.top_impression_percentage
            FROM keyword_view
            WHERE ad_group_criterion.status != 'REMOVED'
              AND ad_group_criterion.negative = false
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            seen_keyword_keys: set[tuple[int, str]] = set()
            for row in response:
                campaign_google_id = str(row.campaign.id)
                ad_group_google_id = str(row.ad_group.id)
                criterion = row.ad_group_criterion
                metrics = row.metrics
                criterion_kind = self._keyword_kind_from_negative(bool(getattr(criterion, "negative", False)))

                if criterion_kind != "POSITIVE":
                    self._log_negative_positive_guard(
                        customer_id=normalized_customer_id,
                        campaign_id=campaign_google_id,
                        ad_group_id=ad_group_google_id,
                        criterion_id=str(criterion.criterion_id),
                        keyword_text=criterion.keyword.text,
                        path_label="sync_keywords",
                    )
                    continue

                ad_group = (
                    db.query(AdGroup)
                    .join(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        AdGroup.google_ad_group_id == ad_group_google_id,
                    )
                    .first()
                )
                if not ad_group:
                    continue

                google_keyword_id = str(criterion.criterion_id)
                seen_keyword_keys.add((ad_group.id, google_keyword_id))

                existing = db.query(Keyword).filter(
                    Keyword.ad_group_id == ad_group.id,
                    Keyword.google_keyword_id == google_keyword_id,
                ).first()

                clicks = metrics.clicks
                impressions = metrics.impressions
                conversions = float(metrics.conversions)
                conv_value = float(metrics.conversions_value) if metrics.conversions_value else 0.0
                cost_micros = metrics.cost_micros
                avg_cpc_micros = int(metrics.average_cpc) if metrics.average_cpc else 0
                cpa_micros = int(cost_micros / conversions) if conversions > 0 else 0

                data = {
                    "ad_group_id": ad_group.id,
                    "google_keyword_id": google_keyword_id,
                    "criterion_kind": criterion_kind,
                    "text": criterion.keyword.text,
                    "match_type": criterion.keyword.match_type.name,
                    "status": criterion.status.name,
                    "final_url": criterion.final_urls[0] if criterion.final_urls else None,
                    "bid_micros": criterion.effective_cpc_bid_micros or 0,
                    "quality_score": criterion.quality_info.quality_score if criterion.quality_info.quality_score else 0,
                    "clicks": clicks,
                    "impressions": impressions,
                    "cost_micros": cost_micros,
                    "conversions": conversions,
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(metrics.ctr * 100, 2),  # fraction → percentage
                    "avg_cpc_micros": avg_cpc_micros,
                    "cpa_micros": cpa_micros,
                    "search_impression_share": _safe_is(metrics.search_impression_share),
                    "search_top_impression_share": _safe_is(metrics.search_top_impression_share),
                    "search_abs_top_impression_share": _safe_is(metrics.search_absolute_top_impression_share),
                    "search_rank_lost_is": _safe_is(metrics.search_rank_lost_impression_share),
                    "search_rank_lost_top_is": _safe_is(metrics.search_rank_lost_top_impression_share),
                    "search_rank_lost_abs_top_is": _safe_is(metrics.search_rank_lost_absolute_top_impression_share),
                    "search_exact_match_is": _safe_is(metrics.search_exact_match_impression_share),
                    "historical_quality_score": _qs_enum(metrics.historical_quality_score),
                    "historical_creative_quality": _qs_enum(metrics.historical_creative_quality_score),
                    "historical_landing_page_quality": _qs_enum(metrics.historical_landing_page_quality_score),
                    "historical_search_predicted_ctr": _qs_enum(metrics.historical_search_predicted_ctr),
                    "all_conversions": _safe_float(metrics.all_conversions),
                    "all_conversions_value_micros": int(float(metrics.all_conversions_value) * 1_000_000) if metrics.all_conversions_value else None,
                    "cross_device_conversions": _safe_float(metrics.cross_device_conversions),
                    "value_per_conversion_micros": int(float(metrics.value_per_conversion) * 1_000_000) if metrics.value_per_conversion else None,
                    "conversions_value_per_cost": _safe_float(metrics.conversions_value_per_cost),
                    "abs_top_impression_pct": _safe_is(metrics.absolute_top_impression_percentage),
                    "top_impression_pct": _safe_is(metrics.top_impression_percentage),
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(Keyword(**data))
                count += 1

            removed_count = self._mark_missing_keywords_removed(
                db,
                client_record.id,
                seen_keyword_keys,
            )
            db.commit()
            logger.info(
                f"Synced {count} keywords for customer {normalized_customer_id} "
                f"(marked {removed_count} as REMOVED)"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing keywords: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Keyword Daily Metrics Sync
    # -----------------------------------------------------------------------

    def sync_negative_keywords(self, db: Session, customer_id: str) -> int:
        """Fetch campaign/ad-group negative keyword criteria and upsert into local DB."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        ad_group_query = """
            SELECT
                campaign.id,
                ad_group.id,
                ad_group_criterion.criterion_id,
                ad_group_criterion.resource_name,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.negative
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = KEYWORD
              AND ad_group_criterion.negative = true
              AND ad_group_criterion.status != 'REMOVED'
              AND campaign.status != 'REMOVED'
        """
        campaign_query = """
            SELECT
                campaign.id,
                campaign_criterion.criterion_id,
                campaign_criterion.resource_name,
                campaign_criterion.keyword.text,
                campaign_criterion.keyword.match_type,
                campaign_criterion.status,
                campaign_criterion.negative
            FROM campaign_criterion
            WHERE campaign_criterion.type = KEYWORD
              AND campaign_criterion.negative = true
              AND campaign_criterion.status != 'REMOVED'
              AND campaign.status != 'REMOVED'
        """

        try:
            ad_group_rows = ga_service.search(customer_id=normalized_customer_id, query=ad_group_query)
            campaign_rows = ga_service.search(customer_id=normalized_customer_id, query=campaign_query)
            count = 0
            seen_negative_keys: set[tuple[str, int | None, int | None, str, str, str | None]] = set()

            for row in ad_group_rows:
                campaign_google_id = str(row.campaign.id)
                ad_group_google_id = str(row.ad_group.id)
                criterion = row.ad_group_criterion

                campaign = (
                    db.query(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        Campaign.google_campaign_id == campaign_google_id,
                    )
                    .first()
                )
                if not campaign:
                    logger.warning(
                        "Skipping ad-group negative criterion because campaign {} is missing locally for customer {}",
                        campaign_google_id,
                        normalized_customer_id,
                    )
                    continue

                ad_group = (
                    db.query(AdGroup)
                    .filter(
                        AdGroup.campaign_id == campaign.id,
                        AdGroup.google_ad_group_id == ad_group_google_id,
                    )
                    .first()
                )
                if not ad_group:
                    logger.warning(
                        "Skipping ad-group negative criterion because ad_group {} is missing locally for customer {}",
                        ad_group_google_id,
                        normalized_customer_id,
                    )
                    continue

                google_criterion_id = str(criterion.criterion_id)
                match_type = getattr(criterion.keyword.match_type, "name", str(criterion.keyword.match_type))
                seen_key = self._negative_seen_key(
                    "AD_GROUP",
                    campaign.id,
                    ad_group.id,
                    google_criterion_id,
                    criterion.keyword.text,
                    match_type,
                )
                seen_negative_keys.add(seen_key)

                existing = self._find_matching_negative_keyword(
                    db,
                    client_record.id,
                    campaign.id,
                    ad_group.id,
                    "AD_GROUP",
                    google_criterion_id,
                    criterion.keyword.text,
                    match_type,
                )

                data = {
                    "client_id": client_record.id,
                    "campaign_id": campaign.id,
                    "ad_group_id": ad_group.id,
                    "google_criterion_id": google_criterion_id,
                    "google_resource_name": getattr(criterion, "resource_name", None),
                    "criterion_kind": "NEGATIVE",
                    "text": criterion.keyword.text,
                    "match_type": match_type,
                    "negative_scope": "AD_GROUP",
                    "status": criterion.status.name,
                    "source": existing.source if existing and existing.source == "LOCAL_ACTION" else "GOOGLE_ADS_SYNC",
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(NegativeKeyword(**data))
                count += 1

            for row in campaign_rows:
                campaign_google_id = str(row.campaign.id)
                criterion = row.campaign_criterion

                campaign = (
                    db.query(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        Campaign.google_campaign_id == campaign_google_id,
                    )
                    .first()
                )
                if not campaign:
                    logger.warning(
                        "Skipping campaign negative criterion because campaign {} is missing locally for customer {}",
                        campaign_google_id,
                        normalized_customer_id,
                    )
                    continue

                google_criterion_id = str(criterion.criterion_id)
                match_type = getattr(criterion.keyword.match_type, "name", str(criterion.keyword.match_type))
                seen_key = self._negative_seen_key(
                    "CAMPAIGN",
                    campaign.id,
                    None,
                    google_criterion_id,
                    criterion.keyword.text,
                    match_type,
                )
                seen_negative_keys.add(seen_key)

                existing = self._find_matching_negative_keyword(
                    db,
                    client_record.id,
                    campaign.id,
                    None,
                    "CAMPAIGN",
                    google_criterion_id,
                    criterion.keyword.text,
                    match_type,
                )

                data = {
                    "client_id": client_record.id,
                    "campaign_id": campaign.id,
                    "ad_group_id": None,
                    "google_criterion_id": google_criterion_id,
                    "google_resource_name": getattr(criterion, "resource_name", None),
                    "criterion_kind": "NEGATIVE",
                    "text": criterion.keyword.text,
                    "match_type": match_type,
                    "negative_scope": "CAMPAIGN",
                    "status": criterion.status.name,
                    "source": existing.source if existing and existing.source == "LOCAL_ACTION" else "GOOGLE_ADS_SYNC",
                }

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(NegativeKeyword(**data))
                count += 1

            removed_count = self._mark_missing_negative_keywords_removed(
                db,
                client_record.id,
                seen_negative_keys,
            )
            db.commit()
            logger.info(
                f"Synced {count} negative keywords for customer {normalized_customer_id} "
                f"(marked {removed_count} as REMOVED)"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing negative keywords: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    def sync_keyword_daily(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch daily keyword metrics and upsert into keywords_daily table."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.id,
                ad_group.id,
                ad_group_criterion.criterion_id,
                ad_group_criterion.negative,
                segments.date,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.average_cpc
            FROM keyword_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND ad_group_criterion.status != 'REMOVED'
              AND ad_group_criterion.negative = false
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                ad_group_google_id = str(row.ad_group.id)
                google_keyword_id = str(row.ad_group_criterion.criterion_id)
                if bool(getattr(row.ad_group_criterion, "negative", False)):
                    self._log_negative_positive_guard(
                        customer_id=normalized_customer_id,
                        campaign_id=campaign_google_id,
                        ad_group_id=ad_group_google_id,
                        criterion_id=google_keyword_id,
                        keyword_text=getattr(row.ad_group_criterion.keyword, "text", None),
                        path_label="sync_keyword_daily",
                    )
                    continue
                metric_date = date.fromisoformat(row.segments.date)
                m = row.metrics

                # Find local keyword
                keyword = (
                    db.query(Keyword)
                    .join(AdGroup)
                    .join(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        AdGroup.google_ad_group_id == ad_group_google_id,
                        Keyword.google_keyword_id == google_keyword_id,
                    )
                    .first()
                )
                if not keyword:
                    continue

                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                existing = db.query(KeywordDaily).filter(
                    KeywordDaily.keyword_id == keyword.id,
                    KeywordDaily.date == metric_date,
                ).first()

                data = {
                    "keyword_id": keyword.id,
                    "date": metric_date,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(KeywordDaily(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} keyword daily rows for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing keyword daily metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Daily Metrics Sync (expanded with IS, extended conv, top %)
    # -----------------------------------------------------------------------

    def sync_daily_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch daily campaign metrics and upsert into local DB.

        Uses two separate queries:
        1. Core metrics for ALL campaign types (clicks, cost, conversions, etc.)
        2. Search IS metrics for SEARCH campaigns only (search_impression_share, etc.)

        This avoids Google Ads API errors when requesting search-only metrics
        on accounts with non-SEARCH campaigns (PMax, Display, Shopping, Video).
        """
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)  # Yesterday (today may be incomplete)

        ga_service = self.client.get_service("GoogleAdsService")

        # ── Query 1: Core metrics for ALL campaign types ──
        core_query = f"""
            SELECT
                campaign.id,
                segments.date,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.conversions_from_interactions_rate,
                metrics.cost_micros,
                metrics.average_cpc,
                metrics.all_conversions,
                metrics.all_conversions_value,
                metrics.cross_device_conversions,
                metrics.value_per_conversion
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        count = 0
        try:
            response = ga_service.search(customer_id=customer_id, query=core_query)
            for row in response:
                campaign_id_google = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                m = row.metrics

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_id_google,
                ).first()
                if not campaign:
                    continue

                cost_micros = m.cost_micros
                conversions = float(m.conversions)
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0
                conv_value_micros = int(conv_value * 1_000_000)
                cost_usd = cost_micros / 1_000_000 if cost_micros else 0
                roas = conv_value / cost_usd if cost_usd > 0 else 0

                existing = db.query(MetricDaily).filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date == metric_date,
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,  # API returns as fraction, store as %
                    "conversions": conversions,
                    "conversion_value_micros": conv_value_micros,
                    "conversion_rate": m.conversions_from_interactions_rate * 100,
                    "cost_micros": cost_micros,
                    "roas": roas,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                    # Extended Conversions
                    "all_conversions": _safe_float(m.all_conversions),
                    "all_conversions_value_micros": int(float(m.all_conversions_value) * 1_000_000) if m.all_conversions_value else None,
                    "cross_device_conversions": _safe_float(m.cross_device_conversions),
                    "value_per_conversion_micros": int(float(m.value_per_conversion) * 1_000_000) if m.value_per_conversion else None,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricDaily(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} core daily metric rows for customer {customer_id}")

        except Exception as e:
            logger.error(f"Error syncing core daily metrics: {e}")
            db.rollback()
            raise

        # ── Query 2: Search IS metrics (SEARCH campaigns only) ──
        is_query = f"""
            SELECT
                campaign.id,
                segments.date,
                metrics.search_impression_share,
                metrics.search_top_impression_share,
                metrics.search_absolute_top_impression_share,
                metrics.search_budget_lost_impression_share,
                metrics.search_budget_lost_top_impression_share,
                metrics.search_budget_lost_absolute_top_impression_share,
                metrics.search_rank_lost_impression_share,
                metrics.search_rank_lost_top_impression_share,
                metrics.search_rank_lost_absolute_top_impression_share,
                metrics.search_click_share,
                metrics.absolute_top_impression_percentage,
                metrics.top_impression_percentage
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
              AND campaign.advertising_channel_type = 'SEARCH'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=is_query)
            is_count = 0
            for row in response:
                campaign_id_google = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                m = row.metrics

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_id_google,
                ).first()
                if not campaign:
                    continue

                existing = db.query(MetricDaily).filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date == metric_date,
                ).first()
                if not existing:
                    continue  # Core row should already exist

                existing.search_impression_share = _safe_is(m.search_impression_share)
                existing.search_top_impression_share = _safe_is(m.search_top_impression_share)
                existing.search_abs_top_impression_share = _safe_is(m.search_absolute_top_impression_share)
                existing.search_budget_lost_is = _safe_is(m.search_budget_lost_impression_share)
                existing.search_budget_lost_top_is = _safe_is(m.search_budget_lost_top_impression_share)
                existing.search_budget_lost_abs_top_is = _safe_is(m.search_budget_lost_absolute_top_impression_share)
                existing.search_rank_lost_is = _safe_is(m.search_rank_lost_impression_share)
                existing.search_rank_lost_top_is = _safe_is(m.search_rank_lost_top_impression_share)
                existing.search_rank_lost_abs_top_is = _safe_is(m.search_rank_lost_absolute_top_impression_share)
                existing.search_click_share = _safe_is(m.search_click_share)
                existing.abs_top_impression_pct = _safe_is(m.absolute_top_impression_percentage)
                existing.top_impression_pct = _safe_is(m.top_impression_percentage)
                is_count += 1

            db.commit()
            logger.info(f"Enriched {is_count} rows with Search IS for customer {customer_id}")

        except Exception as e:
            # Non-critical — core metrics are already saved
            logger.warning(f"Search IS enrichment failed (non-critical): {e}")

        return count

    # -----------------------------------------------------------------------
    # Search Terms Sync (expanded with extended conv)
    # -----------------------------------------------------------------------

    def sync_search_terms(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch search term report and store in local DB."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.id,
                ad_group.id,
                search_term_view.search_term,
                segments.keyword.info.text,
                segments.keyword.info.match_type,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.conversions_from_interactions_rate,
                metrics.cost_per_conversion,
                metrics.all_conversions,
                metrics.all_conversions_value,
                metrics.cross_device_conversions,
                metrics.value_per_conversion,
                metrics.conversions_value_per_cost
            FROM search_term_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                ad_group_google_id = str(row.ad_group.id)
                campaign_google_id = str(row.campaign.id)
                m = row.metrics

                # Find local ad_group
                ad_group = (
                    db.query(AdGroup)
                    .join(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        AdGroup.google_ad_group_id == ad_group_google_id,
                    )
                    .first()
                )
                if not ad_group:
                    continue

                # Find local campaign for campaign_id FK
                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()

                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                # Upsert: check if search term exists for this ad_group/text/date range
                existing = db.query(SearchTerm).filter(
                    SearchTerm.ad_group_id == ad_group.id,
                    SearchTerm.text == row.search_term_view.search_term,
                    SearchTerm.date_from == date_from,
                    SearchTerm.date_to == date_to,
                ).first()

                term_data = {
                    "ad_group_id": ad_group.id,
                    "campaign_id": campaign.id if campaign else None,
                    "source": "SEARCH",
                    "text": row.search_term_view.search_term,
                    "keyword_text": row.segments.keyword.info.text if row.segments.keyword.info.text else None,
                    "match_type": row.segments.keyword.info.match_type.name if row.segments.keyword.info.match_type else None,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(m.ctr * 100, 2),  # fraction → percentage
                    "conversion_rate": round(m.conversions_from_interactions_rate * 100, 2),
                    "all_conversions": _safe_float(m.all_conversions),
                    "all_conversions_value_micros": int(float(m.all_conversions_value) * 1_000_000) if m.all_conversions_value else None,
                    "cross_device_conversions": _safe_float(m.cross_device_conversions),
                    "value_per_conversion_micros": int(float(m.value_per_conversion) * 1_000_000) if m.value_per_conversion else None,
                    "conversions_value_per_cost": _safe_float(m.conversions_value_per_cost),
                    "date_from": date_from,
                    "date_to": date_to,
                }

                if existing:
                    for key, val in term_data.items():
                        setattr(existing, key, val)
                else:
                    db.add(SearchTerm(**term_data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} search terms for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing search terms: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # PMax Search Terms Sync (via campaign_search_term_view)
    # -----------------------------------------------------------------------

    def sync_pmax_search_terms(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch PMax search terms via campaign_search_term_view.

        campaign_search_term_view aggregates at campaign level and INCLUDES
        Performance Max data (unlike search_term_view which is ad_group level).

        IMPORTANT: Do NOT use segments.keyword.info.* fields — they filter
        out all PMax data from results.
        """
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")

        # Single query for all PMax campaigns — no keyword segments!
        query = f"""
            SELECT
                campaign.id,
                campaign_search_term_view.search_term,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros
            FROM campaign_search_term_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.advertising_channel_type = 'PERFORMANCE_MAX'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0

            for row in response:
                campaign_google_id = str(row.campaign.id)
                m = row.metrics
                search_term_text = row.campaign_search_term_view.search_term

                if not search_term_text:
                    continue

                # Find local campaign
                campaign = (
                    db.query(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        Campaign.google_campaign_id == campaign_google_id,
                    )
                    .first()
                )
                if not campaign:
                    continue

                conv = float(m.conversions) if m.conversions else 0.0
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                # Upsert: check if search term exists for this campaign/text/date range (PMax has no ad_group)
                existing = db.query(SearchTerm).filter(
                    SearchTerm.campaign_id == campaign.id,
                    SearchTerm.text == search_term_text,
                    SearchTerm.date_from == date_from,
                    SearchTerm.date_to == date_to,
                    SearchTerm.source == "PMAX",
                ).first()

                term_data = {
                    "campaign_id": campaign.id,
                    "ad_group_id": None,
                    "text": search_term_text,
                    "keyword_text": None,
                    "match_type": None,
                    "source": "PMAX",
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": conv,
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(m.ctr * 100, 2),  # fraction → percentage
                    "conversion_rate": round(
                        (conv / m.clicks * 100), 2
                    ) if m.clicks > 0 else 0.0,
                    "date_from": date_from,
                    "date_to": date_to,
                }

                if existing:
                    for key, val in term_data.items():
                        setattr(existing, key, val)
                else:
                    db.add(SearchTerm(**term_data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} PMax search terms for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing PMax search terms: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Device Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def sync_device_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch device-segmented daily campaign metrics."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.id,
                segments.date,
                segments.device,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc,
                metrics.search_impression_share
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                device = row.segments.device.name
                m = row.metrics

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.device == device,
                    MetricSegmented.geo_city.is_(None),
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "device": device,
                    "geo_city": None,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "cost_micros": m.cost_micros,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                    "search_impression_share": _safe_is(m.search_impression_share),
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} device-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing device metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Geo Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def _resolve_geo_names(self, customer_id: str, criterion_ids: set[str]) -> dict[str, str]:
        """Resolve geoTargetConstants criterion IDs to human-readable city names.

        Returns dict: {"geoTargetConstants/1011243": "Wroclaw", ...}
        """
        if not criterion_ids or not self.is_connected:
            return {}

        ga_service = self.client.get_service("GoogleAdsService")
        mcc_id = self.get_login_customer_id() or customer_id

        ids_str = ",".join(criterion_ids)
        query = f"""
            SELECT
                geo_target_constant.id,
                geo_target_constant.name
            FROM geo_target_constant
            WHERE geo_target_constant.id IN ({ids_str})
        """
        name_map = {}
        try:
            response = ga_service.search(customer_id=mcc_id, query=query)
            for row in response:
                gtc = row.geo_target_constant
                name_map[f"geoTargetConstants/{gtc.id}"] = gtc.name
        except Exception as e:
            logger.warning(f"Could not resolve geo names: {e}")
        return name_map

    def sync_geo_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch geo-segmented (city) daily campaign metrics via geographic_view."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=7)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        # geographic_view requires campaign.status in SELECT
        query = f"""
            SELECT
                campaign.id,
                campaign.status,
                geographic_view.country_criterion_id,
                geographic_view.location_type,
                segments.date,
                segments.geo_target_city,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM geographic_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
              AND metrics.impressions > 0
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)

            # First pass: collect all rows and unique criterion IDs
            raw_rows = []
            criterion_ids = set()
            for row in response:
                geo_city_raw = row.segments.geo_target_city
                if geo_city_raw:
                    # Extract criterion ID from "geoTargetConstants/1011243"
                    parts = geo_city_raw.split("/")
                    if len(parts) == 2:
                        criterion_ids.add(parts[1])
                raw_rows.append(row)

            # Batch-resolve all criterion IDs to city names
            geo_name_map = self._resolve_geo_names(customer_id, criterion_ids)

            # Second pass: upsert rows with resolved city names
            count = 0
            for row in raw_rows:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                geo_city_raw = row.segments.geo_target_city
                geo_city = geo_name_map.get(geo_city_raw, geo_city_raw) if geo_city_raw else "Unknown"
                m = row.metrics

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                # Match by resolved name OR raw resource name (handles migration)
                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.in_([geo_city, geo_city_raw]),
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "device": None,
                    "geo_city": geo_city,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "cost_micros": m.cost_micros,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                    "search_impression_share": None,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} geo-segmented metric rows (resolved {len(geo_name_map)} city names)")
            return count

        except Exception as e:
            logger.error(f"Error syncing geo metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Apply Action (mutations)
    # -----------------------------------------------------------------------

    def apply_action(
        self,
        db: Session,
        action_type: str,
        entity_id: int | None,
        params: dict | None = None,
        target: dict | None = None,
        client_id: int | None = None,
    ):
        """Execute a canonical action on a Google Ads entity.

        Mutations are applied to the local DB first and flushed. The caller owns the
        surrounding transaction. When Google Ads credentials are configured, the same
        mutation is sent to the API; otherwise the method returns `mode=LOCAL_ONLY`.
        """
        from app.models import Ad, Campaign, Keyword
        from app.services.action_executor import SafetyViolationError, validate_action
        from app.utils.formatters import micros_to_currency

        params = params or {}
        target = target or {}
        mode = "LIVE" if self.is_connected else "LOCAL_ONLY"

        logger.info(f"EXECUTING: {action_type} entity={entity_id} params={params} target={target}")

        client_limits = None
        if client_id is not None:
            client_record = db.get(Client, client_id)
            if client_record and client_record.business_rules:
                client_limits = (client_record.business_rules or {}).get("safety_limits")

        if action_type == "PAUSE_KEYWORD":
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            kw.status = "PAUSED"
            if self.is_connected:
                self._mutate_keyword_status(kw.google_keyword_id, "PAUSED", db, kw)
            db.flush()
            return {
                "status": "success",
                "message": "Executed PAUSE_KEYWORD",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "ENABLE_KEYWORD":
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            kw.status = "ENABLED"
            if self.is_connected:
                self._mutate_keyword_status(kw.google_keyword_id, "ENABLED", db, kw)
            db.flush()
            return {
                "status": "success",
                "message": "Executed ENABLE_KEYWORD",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "PAUSE_AD":
            ad = db.get(Ad, entity_id)
            if not ad:
                return {"status": "error", "message": f"Ad {entity_id} not found"}
            ad.status = "PAUSED"
            if self.is_connected:
                self._mutate_ad_status(ad, db, "PAUSED")
            db.flush()
            return {
                "status": "success",
                "message": "Executed PAUSE_AD",
                "entity_type": "ad",
                "entity_id": ad.id,
                "mode": mode,
            }

        if action_type in {"UPDATE_BID", "SET_KEYWORD_BID", "SET_BID"}:
            kw = db.get(Keyword, entity_id)
            if not kw:
                return {"status": "error", "message": f"Keyword {entity_id} not found"}
            amount_micros = params.get("amount_micros")
            if amount_micros is None and params.get("amount") is not None:
                amount_micros = int(round(float(params["amount"]) * 1_000_000))
            if amount_micros is None:
                return {"status": "error", "message": "Missing amount for bid update"}

            current_bid = micros_to_currency(kw.bid_micros or 0)
            new_bid = amount_micros / 1_000_000
            try:
                validate_action(action_type, current_bid, new_bid, {}, client_limits)
            except SafetyViolationError as exc:
                return {"status": "error", "message": f"Safety violation: {exc}"}

            kw.bid_micros = int(amount_micros)
            if self.is_connected:
                self._mutate_keyword_bid(kw, db)
            db.flush()
            return {
                "status": "success",
                "message": "Executed UPDATE_BID",
                "entity_type": "keyword",
                "entity_id": kw.id,
                "mode": mode,
            }

        if action_type == "ADD_KEYWORD":
            ad_group_id = target.get("ad_group_id") or params.get("ad_group_id")
            text = (params.get("text") or "").strip()
            match_type = params.get("match_type", "EXACT")
            if not ad_group_id or not text:
                return {"status": "error", "message": "Missing ad_group_id or text"}

            existing = (
                db.query(Keyword)
                .filter(
                    Keyword.ad_group_id == ad_group_id,
                    func.lower(Keyword.text) == text.lower(),
                    Keyword.status != "REMOVED",
                )
                .first()
            )
            if existing:
                return {"status": "error", "message": "Keyword already exists in target ad group"}

            new_kw = Keyword(
                ad_group_id=ad_group_id,
                text=text,
                match_type=match_type,
                status="ENABLED",
                google_keyword_id=f"local-{int(datetime.now(timezone.utc).timestamp())}",
                clicks=0,
                impressions=0,
                cost_micros=0,
                conversions=0.0,
                bid_micros=0,
            )
            db.add(new_kw)
            db.flush()
            if self.is_connected:
                self._mutate_add_keyword(new_kw, db)
            return {
                "status": "success",
                "message": "Executed ADD_KEYWORD",
                "entity_type": "keyword",
                "entity_id": new_kw.id,
                "mode": mode,
            }

        if action_type == "ADD_NEGATIVE":
            campaign_id = target.get("campaign_id") or params.get("campaign_id") or entity_id
            ad_group_id = params.get("ad_group_id")
            text = (params.get("text") or "").strip()
            match_type = params.get("match_type", "PHRASE")
            negative_level = params.get("negative_level", "CAMPAIGN")
            if negative_level not in ("CAMPAIGN", "AD_GROUP"):
                return {"status": "error", "message": "negative_level must be CAMPAIGN or AD_GROUP"}

            if negative_level == "AD_GROUP":
                if not ad_group_id:
                    return {"status": "error", "message": "Missing ad_group_id for AD_GROUP level"}
                ad_group = db.get(AdGroup, ad_group_id)
                if not ad_group:
                    return {"status": "error", "message": f"Ad group {ad_group_id} not found"}
                campaign_id = ad_group.campaign_id
                if not text:
                    return {"status": "error", "message": "Missing text"}
                existing = (
                    db.query(NegativeKeyword)
                    .filter(
                        NegativeKeyword.ad_group_id == ad_group_id,
                        NegativeKeyword.negative_scope == "AD_GROUP",
                        func.lower(NegativeKeyword.text) == text.lower(),
                        NegativeKeyword.status != "REMOVED",
                    )
                    .first()
                )
                if existing:
                    return {"status": "error", "message": "Negative keyword already exists"}
                campaign = db.get(Campaign, campaign_id)
                if not campaign:
                    return {"status": "error", "message": f"Campaign {campaign_id} not found"}
                negative = NegativeKeyword(
                    client_id=campaign.client_id,
                    campaign_id=campaign.id,
                    ad_group_id=ad_group_id,
                    criterion_kind="NEGATIVE",
                    text=text,
                    match_type=match_type,
                    negative_scope="AD_GROUP",
                    status="ENABLED",
                    source="LOCAL_ACTION",
                )
                db.add(negative)
                db.flush()
                if self.is_connected:
                    self._mutate_ad_group_negative(ad_group, db, negative)
                return {
                    "status": "success",
                    "message": "Executed ADD_NEGATIVE",
                    "entity_type": "ad_group",
                    "entity_id": ad_group.id,
                    "mode": mode,
                }

            # CAMPAIGN level (default)
            if not campaign_id or not text:
                return {"status": "error", "message": "Missing campaign_id or text"}

            existing = (
                db.query(NegativeKeyword)
                .filter(
                    NegativeKeyword.campaign_id == campaign_id,
                    NegativeKeyword.negative_scope == "CAMPAIGN",
                    func.lower(NegativeKeyword.text) == text.lower(),
                    NegativeKeyword.status != "REMOVED",
                )
                .first()
            )
            if existing:
                return {"status": "error", "message": "Negative keyword already exists"}

            campaign = db.get(Campaign, campaign_id)
            if not campaign:
                return {"status": "error", "message": f"Campaign {campaign_id} not found"}

            negative = NegativeKeyword(
                client_id=campaign.client_id,
                campaign_id=campaign.id,
                ad_group_id=None,
                criterion_kind="NEGATIVE",
                text=text,
                match_type=match_type,
                negative_scope="CAMPAIGN",
                status="ENABLED",
                source="LOCAL_ACTION",
            )
            db.add(negative)
            db.flush()
            if self.is_connected:
                self._mutate_campaign_negative(campaign, db, negative)
            return {
                "status": "success",
                "message": "Executed ADD_NEGATIVE",
                "entity_type": "campaign",
                "entity_id": campaign.id,
                "mode": mode,
            }

        if action_type in {"INCREASE_BUDGET", "SET_BUDGET"}:
            campaign = db.get(Campaign, entity_id)
            if not campaign:
                return {"status": "error", "message": f"Campaign {entity_id} not found"}
            amount_micros = params.get("amount_micros")
            if amount_micros is None and params.get("amount") is not None:
                amount_micros = int(round(float(params["amount"]) * 1_000_000))
            if amount_micros is None:
                return {"status": "error", "message": "Missing amount for budget update"}

            current_budget = micros_to_currency(campaign.budget_micros or 0)
            new_budget = amount_micros / 1_000_000
            try:
                validate_action(action_type, current_budget, new_budget, {}, client_limits)
            except SafetyViolationError as exc:
                return {"status": "error", "message": f"Safety violation: {exc}"}

            campaign.budget_micros = int(amount_micros)
            if self.is_connected:
                self._mutate_campaign_budget(campaign, db)
            db.flush()
            return {
                "status": "success",
                "message": f"Executed {action_type}",
                "entity_type": "campaign",
                "entity_id": campaign.id,
                "mode": mode,
            }

        return {"status": "error", "message": f"Unknown action_type: {action_type}"}
    def fetch_native_recommendations(self, db: Session, client_id: int) -> list[dict]:
        """Fetch native Google Ads recommendations and map them to the local contract."""
        if not self.is_connected:
            return []

        client_record = db.query(Client).filter(Client.id == client_id).first()
        if not client_record or not client_record.google_customer_id:
            return []

        customer_id = client_record.google_customer_id.replace("-", "")
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                recommendation.resource_name,
                recommendation.type,
                recommendation.dismissed
            FROM recommendation
            WHERE recommendation.dismissed = FALSE
        """

        native_recommendations: list[dict] = []
        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            for row in response:
                recommendation = row.recommendation
                google_type = recommendation.type.name if recommendation.type else "UNKNOWN"
                rec = {
                    "type": f"GOOGLE_{google_type}",
                    "priority": "MEDIUM",
                    "entity_type": "campaign",
                    "entity_id": 0,
                    "entity_name": self._humanize_google_recommendation(google_type),
                    "campaign_name": None,
                    "reason": f"Google Ads native recommendation: {self._humanize_google_recommendation(google_type)}.",
                    "category": "ALERT",
                    "current_value": None,
                    "recommended_action": "Review in Google Ads before applying.",
                    "estimated_impact": None,
                    "metadata": {"google_type": google_type},
                    "source": GOOGLE_ADS_API,
                    "google_resource_name": recommendation.resource_name,
                }
                rec["action_payload"] = build_action_payload(rec)
                rec["executable"] = False
                rec["expires_at"] = default_expires_at(rec)
                rec["impact_micros"] = estimate_impact_micros(rec)
                rec["confidence_score"] = compute_confidence_score(rec, 30)
                rec["risk_score"] = compute_risk_score(rec)
                rec["priority"], rec["score"] = compute_priority(
                    {
                        **rec,
                        "impact_micros": rec["impact_micros"],
                        "confidence_score": rec["confidence_score"],
                        "risk_score": rec["risk_score"],
                    }
                )
                rec["stable_key"] = build_stable_key(rec, client_id)
                native_recommendations.append(rec)
        except Exception as exc:
            logger.warning(f"Failed to fetch native recommendations: {exc}")
            return []

        return native_recommendations

    def _mutate_keyword_status(self, google_keyword_id: str, new_status: str, db: Session, kw):
        """Send keyword status mutation to Google Ads API."""
        if not self.client or not google_keyword_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ag = db.get(AdGroup, kw.ad_group_id)
        if not ag:
            raise RuntimeError("Ad group not found for keyword mutation")
        campaign = db.get(Campaign, ag.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for keyword mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = service.ad_group_criterion_path(
            customer_id,
            str(ag.google_ad_group_id),
            google_keyword_id,
        )
        criterion.status = getattr(self.client.enums.AdGroupCriterionStatusEnum, new_status)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])

    def _mutate_keyword_bid(self, kw, db: Session):
        """Send keyword bid mutation to Google Ads API."""
        if not self.client or not kw.google_keyword_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ag = db.get(AdGroup, kw.ad_group_id)
        if not ag:
            raise RuntimeError("Ad group not found for bid mutation")
        campaign = db.get(Campaign, ag.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for bid mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for bid mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.update
        criterion.resource_name = service.ad_group_criterion_path(
            customer_id,
            str(ag.google_ad_group_id),
            kw.google_keyword_id,
        )
        criterion.cpc_bid_micros = kw.bid_micros

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("cpc_bid_micros")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])

    def _mutate_ad_status(self, ad, db: Session, new_status: str):
        """Pause or enable an ad via AdGroupAdService."""
        if not self.client or not ad.google_ad_id:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ad_group = db.get(AdGroup, ad.ad_group_id)
        if not ad_group:
            raise RuntimeError("Ad group not found for ad mutation")
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for ad mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for ad mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupAdService")
        operation = self.client.get_type("AdGroupAdOperation")
        ad_group_ad = operation.update
        ad_group_ad.resource_name = service.ad_group_ad_path(
            customer_id,
            str(ad_group.google_ad_group_id),
            str(ad.google_ad_id),
        )
        ad_group_ad.status = getattr(self.client.enums.AdGroupAdStatusEnum, new_status)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("status")
        operation.update_mask.CopyFrom(field_mask)
        service.mutate_ad_group_ads(customer_id=customer_id, operations=[operation])

    def _mutate_add_keyword(self, kw, db: Session):
        """Create a keyword in Google Ads for a locally staged ADD_KEYWORD action."""
        if not self.client:
            return
        from app.models.ad_group import AdGroup
        from app.models.campaign import Campaign

        ad_group = db.get(AdGroup, kw.ad_group_id)
        if not ad_group:
            raise RuntimeError("Ad group not found for keyword creation")
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for keyword creation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for keyword creation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = self.client.get_service("AdGroupService").ad_group_path(
            customer_id,
            str(ad_group.google_ad_group_id),
        )
        criterion.status = self.client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.keyword.text = kw.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, kw.match_type)
        if kw.bid_micros:
            criterion.cpc_bid_micros = kw.bid_micros
        response = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            kw.google_keyword_id = resource_name.split("~")[-1]

    def _mutate_campaign_negative(self, campaign, db: Session, negative):
        """Create a campaign-level negative keyword in Google Ads."""
        if not self.client:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for negative keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("CampaignCriterionService")
        operation = self.client.get_type("CampaignCriterionOperation")
        criterion = operation.create
        criterion.campaign = self.client.get_service("CampaignService").campaign_path(
            customer_id,
            str(campaign.google_campaign_id),
        )
        criterion.negative = True
        criterion.keyword.text = negative.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, negative.match_type)
        response = service.mutate_campaign_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            negative.google_resource_name = resource_name
            negative.google_criterion_id = resource_name.split("~")[-1]

    def _mutate_ad_group_negative(self, ad_group, db: Session, negative):
        """Create an ad-group-level negative keyword in Google Ads."""
        if not self.client:
            return
        campaign = db.get(Campaign, ad_group.campaign_id)
        if not campaign:
            raise RuntimeError("Campaign not found for ad-group negative keyword mutation")
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for ad-group negative keyword mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        service = self.client.get_service("AdGroupCriterionService")
        operation = self.client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = self.client.get_service("AdGroupService").ad_group_path(
            customer_id,
            str(ad_group.google_ad_group_id),
        )
        criterion.negative = True
        criterion.keyword.text = negative.text
        criterion.keyword.match_type = getattr(self.client.enums.KeywordMatchTypeEnum, negative.match_type)
        response = service.mutate_ad_group_criteria(customer_id=customer_id, operations=[operation])
        if response.results:
            resource_name = response.results[0].resource_name
            negative.google_resource_name = resource_name
            negative.google_criterion_id = resource_name.split("~")[-1]

    def _mutate_campaign_budget(self, campaign, db: Session):
        """Update campaign budget amount in Google Ads."""
        if not self.client:
            return
        client_record = db.get(Client, campaign.client_id)
        if not client_record:
            raise RuntimeError("Client not found for budget mutation")

        customer_id = client_record.google_customer_id.replace("-", "")
        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.campaign_budget
            FROM campaign
            WHERE campaign.id = {campaign.google_campaign_id}
        """
        response = list(ga_service.search(customer_id=customer_id, query=query))
        if not response:
            raise RuntimeError("Campaign budget resource not found")
        budget_resource = response[0].campaign.campaign_budget

        budget_service = self.client.get_service("CampaignBudgetService")
        operation = self.client.get_type("CampaignBudgetOperation")
        budget = operation.update
        budget.resource_name = budget_resource
        budget.amount_micros = int(campaign.budget_micros or 0)

        field_mask = self.client.get_type("FieldMask")
        field_mask.paths.append("amount_micros")
        operation.update_mask.CopyFrom(field_mask)
        budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[operation])

    @staticmethod
    def _humanize_google_recommendation(google_type: str) -> str:
        return google_type.replace("_", " ").title()

    # -----------------------------------------------------------------------
    # Discover Accounts (MCC -> list of client accounts)
    # -----------------------------------------------------------------------

    def discover_accounts(self) -> list[dict]:
        """
        Fetch client accounts accessible from the MCC (login_customer_id).
        Uses customer_client resource queried through the MCC.
        Returns list of dicts: [{customer_id, name}, ...]
        """
        if not self.is_connected:
            logger.warning("Google Ads API not connected - cannot discover accounts")
            raise RuntimeError("Google Ads API nie jest gotowe do pobierania kont.")

        mcc_id = self.get_login_customer_id()
        if not mcc_id:
            logger.warning("No login_customer_id (MCC) configured")
            raise RuntimeError(
                "Brak login_customer_id (MCC). Uzupelnij Login Customer ID w konfiguracji API."
            )

        ga_service = self.client.get_service("GoogleAdsService")

        try:
            query = """
                SELECT
                    customer_client.client_customer,
                    customer_client.id,
                    customer_client.descriptive_name,
                    customer_client.manager,
                    customer_client.level
                FROM customer_client
                WHERE customer_client.level <= 1
            """
            response = ga_service.search(customer_id=mcc_id, query=query)

            accounts = []
            for row in response:
                cc = row.customer_client
                if cc.manager:
                    continue
                accounts.append({
                    "customer_id": str(cc.id),
                    "name": cc.descriptive_name or f"Account {cc.id}",
                })

            logger.info(f"Discovered {len(accounts)} client accounts under MCC {mcc_id}")
            return accounts

        except Exception as e:
            logger.error(f"Error discovering accounts via MCC {mcc_id}: {e}")
            raise RuntimeError("Nie udalo sie pobrac listy kont z Google Ads API.") from e

    # ------------------------------------------------------------------
    # Change Events — fetch full account change history
    # ------------------------------------------------------------------

    def sync_change_events(self, db: Session, customer_id: str, client_id: int, days: int = 30) -> int:
        """
        Fetch change_event records from Google Ads API and upsert into local DB.

        Uses timestamp-based cursor pagination to handle the 10,000 row LIMIT.
        Max lookback: 30 days (API constraint).

        Returns number of change events synced.
        """
        if not self.is_connected:
            logger.warning("Google Ads API not connected — skipping change events sync")
            return 0

        import json
        from datetime import datetime, timezone

        days = min(days, 28)  # API hard limit is 30 days; use 28 to stay safely within
        date_from = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        date_to = date.today().strftime("%Y-%m-%d")

        ga_service = self.client.get_service("GoogleAdsService")
        total_count = 0
        current_end = date_to

        try:
            while True:
                query = f"""
                    SELECT
                        change_event.resource_name,
                        change_event.change_date_time,
                        change_event.change_resource_name,
                        change_event.user_email,
                        change_event.client_type,
                        change_event.change_resource_type,
                        change_event.old_resource,
                        change_event.new_resource,
                        change_event.resource_change_operation,
                        change_event.changed_fields
                    FROM change_event
                    WHERE change_event.change_date_time >= '{date_from}'
                      AND change_event.change_date_time <= '{current_end}'
                    ORDER BY change_event.change_date_time DESC
                    LIMIT 10000
                """

                response = ga_service.search(customer_id=customer_id, query=query)
                page_count = 0
                last_timestamp = None

                for row in response:
                    ce = row.change_event
                    res_name = ce.resource_name

                    # Dedup — skip if already in DB
                    existing = db.query(ChangeEvent.id).filter(
                        ChangeEvent.resource_name == res_name
                    ).first()
                    if existing:
                        page_count += 1
                        last_timestamp = ce.change_date_time
                        continue

                    # Serialize protobuf old/new resources to JSON
                    old_json = _protobuf_to_json(ce.old_resource)
                    new_json = _protobuf_to_json(ce.new_resource)

                    # Extract changed_fields mask
                    fields_list = list(ce.changed_fields.paths) if ce.changed_fields else []

                    # Extract entity info
                    entity_id = _extract_entity_id(ce.change_resource_name)
                    entity_name = _extract_entity_name(new_json)
                    campaign_name = _extract_campaign_name(ce.change_resource_name, db, client_id)

                    # Map enum values to strings
                    client_type_str = (
                        ce.client_type.name
                        if hasattr(ce.client_type, "name")
                        else str(ce.client_type)
                    )
                    resource_type_str = (
                        ce.change_resource_type.name
                        if hasattr(ce.change_resource_type, "name")
                        else str(ce.change_resource_type)
                    )
                    operation_str = (
                        ce.resource_change_operation.name
                        if hasattr(ce.resource_change_operation, "name")
                        else str(ce.resource_change_operation)
                    )

                    # Parse change_date_time string to datetime object for SQLite
                    change_dt = ce.change_date_time
                    if isinstance(change_dt, str):
                        try:
                            change_dt = datetime.strptime(change_dt, "%Y-%m-%d %H:%M:%S.%f")
                        except ValueError:
                            change_dt = datetime.strptime(change_dt, "%Y-%m-%d %H:%M:%S")

                    event = ChangeEvent(
                        client_id=client_id,
                        resource_name=res_name,
                        change_date_time=change_dt,
                        user_email=ce.user_email or None,
                        client_type=client_type_str,
                        change_resource_type=resource_type_str,
                        change_resource_name=ce.change_resource_name,
                        resource_change_operation=operation_str,
                        changed_fields=json.dumps(fields_list) if fields_list else None,
                        old_resource_json=old_json,
                        new_resource_json=new_json,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        campaign_name=campaign_name,
                    )
                    try:
                        db.add(event)
                        db.flush()
                    except Exception:
                        db.rollback()  # skip duplicate — resource_name UNIQUE violation
                        continue
                    page_count += 1
                    last_timestamp = change_dt

                db.commit()
                total_count += page_count

                # If fewer than 10000, we got everything
                if page_count < 10000:
                    break

                # Cursor: adjust end date to last seen timestamp
                if last_timestamp:
                    current_end = (last_timestamp - timedelta(seconds=1)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    break

            # Best-effort: match change events to our action_log entries
            _match_change_events_to_actions(db, client_id)

            # Update client's last_change_sync_at
            client_record = db.query(Client).filter(Client.id == client_id).first()
            if client_record:
                client_record.last_change_sync_at = datetime.now(timezone.utc)
                db.commit()

            logger.info(f"Synced {total_count} change events for client {client_id}")
            return total_count

        except Exception as e:
            logger.error(f"Error syncing change events for client {client_id}: {e}")
            db.rollback()
            raise


# ------------------------------------------------------------------
# Change Event helpers (module-level)
# ------------------------------------------------------------------

def _protobuf_to_json(resource) -> str | None:
    """Convert a protobuf resource to JSON string."""
    if not resource:
        return None
    import json
    try:
        from google.protobuf.json_format import MessageToDict
        pb = resource._pb if hasattr(resource, "_pb") else resource
        d = MessageToDict(pb, preserving_proto_field_name=True)
        return json.dumps(d, default=str) if d else None
    except Exception:
        return None


def _extract_entity_id(change_resource_name: str) -> str | None:
    """Extract numeric entity ID from resource path like 'customers/123/campaigns/456'."""
    if not change_resource_name:
        return None
    parts = change_resource_name.strip("/").split("/")
    return parts[-1] if parts else None


def _extract_entity_name(new_resource_json: str | None) -> str | None:
    """Try to extract entity name from new_resource JSON."""
    if not new_resource_json:
        return None
    import json
    try:
        data = json.loads(new_resource_json)
        return data.get("name") or data.get("ad", {}).get("name")
    except Exception:
        return None


def _extract_campaign_name(change_resource_name: str, db: Session, client_id: int) -> str | None:
    """Try to find campaign name by looking up campaign ID from resource path."""
    if not change_resource_name:
        return None
    parts = change_resource_name.strip("/").split("/")
    for i, part in enumerate(parts):
        if part == "campaigns" and i + 1 < len(parts):
            campaign_gid = parts[i + 1]
            camp = db.query(Campaign).filter(
                Campaign.client_id == client_id,
                Campaign.google_campaign_id == campaign_gid,
            ).first()
            return camp.name if camp else None
    return None


def _match_change_events_to_actions(db: Session, client_id: int):
    """Best-effort match: link change_events to action_log entries by entity + timestamp window."""
    from datetime import datetime, timedelta

    unmatched = db.query(ChangeEvent).filter(
        ChangeEvent.client_id == client_id,
        ChangeEvent.action_log_id.is_(None),
    ).all()

    for event in unmatched:
        if not event.entity_id:
            continue
        window_start = event.change_date_time - timedelta(minutes=5)
        window_end = event.change_date_time + timedelta(minutes=5)

        action = db.query(ActionLog).filter(
            ActionLog.client_id == client_id,
            ActionLog.entity_id == event.entity_id,
            ActionLog.executed_at >= window_start,
            ActionLog.executed_at <= window_end,
        ).first()

        if action:
            event.action_log_id = action.id

    db.commit()


# Singleton instance
google_ads_service = GoogleAdsService()

























