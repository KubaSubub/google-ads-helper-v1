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
    ChangeEvent, ActionLog, KeywordDaily, NegativeKeyword, ConversionAction,
    AssetGroup, AssetGroupDaily, AssetGroupAsset, CampaignAsset,
    NegativeKeywordList, NegativeKeywordListItem,
    PlacementExclusionList, PlacementExclusionListItem,
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


from app.services.google_ads_mutations import GoogleAdsMutationsMixin


class GoogleAdsService(GoogleAdsMutationsMixin):
    """Wrapper around Google Ads API for data fetching and mutations.

    Write/mutation methods (apply_action, _mutate_*, batch_*, upload_*, add_placement)
    are defined in GoogleAdsMutationsMixin (google_ads_mutations.py) for maintainability.
    """

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

            self.client = GoogleAdsClient.load_from_dict(config, version="v23")
            logger.info("Google Ads API client initialized successfully (API v23, SDK 29.1.0)")
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

    def _execute_query(self, customer_id: str, query: str):
        """Execute a GAQL query and return the response rows as a list."""
        ga_service = self.client.get_service("GoogleAdsService")
        normalized = self.normalize_customer_id(customer_id)
        return list(ga_service.search(customer_id=normalized, query=query))

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
    def _mark_missing_ads_removed(
        db: Session,
        client_id: int,
        seen_ad_keys: set[tuple[int, str]],
    ) -> int:
        removed = 0
        existing_ads = (
            db.query(Ad)
            .join(AdGroup)
            .join(Campaign)
            .filter(Campaign.client_id == client_id)
            .all()
        )
        for ad in existing_ads:
            key = (ad.ad_group_id, ad.google_ad_id)
            if key not in seen_ad_keys and ad.status != "REMOVED":
                ad.status = "REMOVED"
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
                campaign.bidding_strategy_type,
                campaign.target_cpa.target_cpa_micros,
                campaign.target_roas.target_roas,
                campaign.primary_status,
                campaign.primary_status_reasons,
                campaign.bidding_strategy,
                campaign.labels
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

            # Pre-fetch label names if extended query succeeded
            label_name_map: dict[str, str] = {}
            if selected_query == "extended":
                try:
                    label_query = "SELECT label.id, label.name FROM label"
                    label_response = ga_service.search(customer_id=normalized_customer_id, query=label_query)
                    for lr in label_response:
                        label_name_map[lr.label.resource_name] = lr.label.name
                except Exception as label_exc:
                    logger.warning(f"Label fetch failed for {normalized_customer_id}: {self._format_google_ads_error(label_exc)}")

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

                # Extended fields (GAP 1A, 1D, 1E)
                if selected_query == "extended":
                    import json as _json
                    # GAP 1D: Smart Bidding targets
                    target_cpa = getattr(campaign, 'target_cpa', None)
                    if target_cpa:
                        data["target_cpa_micros"] = getattr(target_cpa, 'target_cpa_micros', None) or None
                    target_roas_obj = getattr(campaign, 'target_roas', None)
                    if target_roas_obj:
                        data["target_roas"] = getattr(target_roas_obj, 'target_roas', None) or None
                    # GAP 1A: Learning period
                    ps = getattr(campaign, 'primary_status', None)
                    data["primary_status"] = ps.name if hasattr(ps, 'name') else (str(ps) if ps else None)
                    psr = getattr(campaign, 'primary_status_reasons', None)
                    if psr:
                        data["primary_status_reasons"] = _json.dumps([r.name if hasattr(r, 'name') else str(r) for r in psr])
                    # Labels
                    raw_labels = getattr(campaign, 'labels', None)
                    if raw_labels:
                        label_names = [label_name_map.get(r, r.split('/')[-1]) for r in raw_labels]
                        data["labels"] = _json.dumps(label_names)
                    else:
                        data["labels"] = None
                    # GAP 1E: Portfolio bid strategy
                    bs_resource = getattr(campaign, 'bidding_strategy', None)
                    if bs_resource and isinstance(bs_resource, str) and 'biddingStrategies' in bs_resource:
                        data["bidding_strategy_resource_name"] = bs_resource
                        # Extract portfolio ID from resource name
                        parts = bs_resource.split('/')
                        data["portfolio_bid_strategy_id"] = parts[-1] if parts else None

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
    # Ads Sync (RSA inventory from ad_group_ad resource)
    # -----------------------------------------------------------------------

    def sync_ads(self, db: Session, customer_id: str) -> int:
        """Fetch all ads from Google Ads API and upsert into local DB."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                ad_group_ad.ad.id,
                ad_group_ad.ad.type,
                ad_group_ad.ad.final_urls,
                ad_group_ad.ad.responsive_search_ad.headlines,
                ad_group_ad.ad.responsive_search_ad.descriptions,
                ad_group_ad.status,
                ad_group_ad.ad_strength,
                ad_group_ad.policy_summary.approval_status,
                ad_group.id,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM ad_group_ad
            WHERE ad_group_ad.status != 'REMOVED'
              AND campaign.status != 'REMOVED'
              AND ad_group.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            seen_ad_keys: set[tuple[int, str]] = set()

            for row in response:
                ad_data = row.ad_group_ad.ad
                google_ad_group_id = str(row.ad_group.id)

                ad_group = (
                    db.query(AdGroup)
                    .join(Campaign)
                    .filter(
                        Campaign.client_id == client_record.id,
                        AdGroup.google_ad_group_id == google_ad_group_id,
                    )
                    .first()
                )
                if not ad_group:
                    continue

                google_ad_id = str(ad_data.id)
                seen_ad_keys.add((ad_group.id, google_ad_id))

                # Parse RSA headlines/descriptions
                headlines = []
                for h in ad_data.responsive_search_ad.headlines:
                    headlines.append({
                        "text": h.text,
                        "pinned_position": h.pinned_field.name if h.pinned_field else None,
                    })

                descriptions = []
                for d in ad_data.responsive_search_ad.descriptions:
                    descriptions.append({
                        "text": d.text,
                        "pinned_position": d.pinned_field.name if d.pinned_field else None,
                    })

                # Final URL
                final_url = ad_data.final_urls[0] if ad_data.final_urls else None

                # Ad strength
                ad_strength = row.ad_group_ad.ad_strength.name if row.ad_group_ad.ad_strength else None
                if ad_strength == "UNSPECIFIED":
                    ad_strength = None

                # Approval status
                approval = row.ad_group_ad.policy_summary.approval_status.name if row.ad_group_ad.policy_summary.approval_status else None

                data = {
                    "ad_group_id": ad_group.id,
                    "google_ad_id": google_ad_id,
                    "ad_type": ad_data.type_.name if ad_data.type_ else "UNKNOWN",
                    "status": row.ad_group_ad.status.name,
                    "approval_status": approval,
                    "ad_strength": ad_strength,
                    "final_url": final_url,
                    "headlines": headlines,
                    "descriptions": descriptions,
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "cost_micros": row.metrics.cost_micros,
                    "conversions": row.metrics.conversions,
                    "ctr": round(row.metrics.ctr * 100, 2) if row.metrics.ctr else 0.0,
                }

                existing = db.query(Ad).filter(
                    Ad.ad_group_id == ad_group.id,
                    Ad.google_ad_id == google_ad_id,
                ).first()

                if existing:
                    for key, value in data.items():
                        setattr(existing, key, value)
                else:
                    db.add(Ad(**data))
                count += 1

            removed_count = self._mark_missing_ads_removed(
                db, client_record.id, seen_ad_keys
            )
            db.commit()
            logger.info(
                f"Synced {count} ads for customer {normalized_customer_id} "
                f"(marked {removed_count} as REMOVED)"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing ads: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # MCC Account Hierarchy Sync (E8)
    # -----------------------------------------------------------------------

    def sync_mcc_links(self, db: Session, manager_customer_id: str) -> int:
        """Fetch child accounts from MCC manager account."""
        from app.models.mcc_link import MccLink

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(manager_customer_id)

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                customer_client.client_customer,
                customer_client.descriptive_name,
                customer_client.status,
                customer_client.hidden,
                customer_client.manager
            FROM customer_client
            WHERE customer_client.status = 'ENABLED'
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                cc = row.customer_client
                client_rn = cc.client_customer
                client_cid = client_rn.split("/")[-1] if client_rn else None
                if not client_cid:
                    continue

                # Check if we have a local client for this CID
                from app.models import Client
                local = db.query(Client).filter(
                    func.replace(Client.google_customer_id, "-", "") == client_cid
                ).first()

                data = {
                    "manager_customer_id": normalized,
                    "client_customer_id": client_cid,
                    "client_descriptive_name": cc.descriptive_name or None,
                    "status": cc.status.name if cc.status else "ENABLED",
                    "is_hidden": bool(cc.hidden),
                    "is_manager": bool(cc.manager),
                    "local_client_id": local.id if local else None,
                }

                existing = db.query(MccLink).filter(
                    MccLink.manager_customer_id == normalized,
                    MccLink.client_customer_id == client_cid,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MccLink(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} MCC child accounts for manager {normalized}")
            return count

        except Exception as e:
            logger.warning(f"MCC sync: {self._format_google_ads_error(e)}")
            db.rollback()
            return 0

    # upload_offline_conversions → inherited from GoogleAdsMutationsMixin

    # -----------------------------------------------------------------------
    # Conversion Value Rules Sync (E6)
    # -----------------------------------------------------------------------

    def sync_conversion_value_rules(self, db: Session, customer_id: str) -> int:
        """Fetch conversion value rules."""
        from app.models.conversion_value_rule import ConversionValueRule

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                conversion_value_rule.resource_name,
                conversion_value_rule.id,
                conversion_value_rule.action.type,
                conversion_value_rule.action.value,
                conversion_value_rule.audience_condition.user_lists,
                conversion_value_rule.device_condition.device_types,
                conversion_value_rule.geo_location_condition.geo_target_constants,
                conversion_value_rule.status
            FROM conversion_value_rule
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                rule = row.conversion_value_rule
                google_id = str(rule.id)

                # Determine condition type
                cond_type = None
                cond_value = None
                try:
                    if rule.audience_condition.user_lists:
                        cond_type = "AUDIENCE"
                        cond_value = ", ".join(str(ul) for ul in rule.audience_condition.user_lists)
                except (AttributeError, TypeError):
                    pass
                try:
                    if not cond_type and rule.device_condition.device_types:
                        cond_type = "DEVICE"
                        cond_value = ", ".join(dt.name for dt in rule.device_condition.device_types)
                except (AttributeError, TypeError):
                    pass
                try:
                    if not cond_type and rule.geo_location_condition.geo_target_constants:
                        cond_type = "GEO_LOCATION"
                        cond_value = ", ".join(str(g) for g in rule.geo_location_condition.geo_target_constants)
                except (AttributeError, TypeError):
                    pass

                data = {
                    "client_id": client_record.id,
                    "google_rule_id": google_id,
                    "resource_name": rule.resource_name,
                    "condition_type": cond_type,
                    "condition_value": cond_value,
                    "action_type": rule.action.type.name if rule.action.type else None,
                    "action_value_micros": int(rule.action.value * 1_000_000) if rule.action.type and rule.action.type.name == "ADD" and rule.action.value else None,
                    "action_multiplier": rule.action.value if rule.action.type and rule.action.type.name == "MULTIPLY" and rule.action.value else None,
                    "status": rule.status.name if rule.status else "ENABLED",
                }

                existing = db.query(ConversionValueRule).filter(
                    ConversionValueRule.client_id == client_record.id,
                    ConversionValueRule.google_rule_id == google_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(ConversionValueRule(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} conversion value rules")
            return count

        except Exception as e:
            logger.warning(f"Conversion value rules sync: {self._format_google_ads_error(e)}")
            db.rollback()
            return 0

    # add_placement_exclusion → inherited from GoogleAdsMutationsMixin

    # -----------------------------------------------------------------------
    # Google Native Recommendations Sync (E7)
    # -----------------------------------------------------------------------

    def sync_google_recommendations(self, db: Session, customer_id: str) -> int:
        """Fetch Google's native recommendations."""
        from app.models.google_recommendation import GoogleRecommendation

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                recommendation.resource_name,
                recommendation.type,
                recommendation.campaign,
                recommendation.impact.base_metrics.impressions,
                recommendation.impact.base_metrics.clicks,
                recommendation.impact.base_metrics.cost_micros,
                recommendation.impact.base_metrics.conversions,
                recommendation.impact.potential_metrics.impressions,
                recommendation.impact.potential_metrics.clicks,
                recommendation.impact.potential_metrics.cost_micros,
                recommendation.impact.potential_metrics.conversions,
                campaign.name
            FROM recommendation
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                rec = row.recommendation
                rn = rec.resource_name
                rec_id = rn.split("/")[-1] if rn else str(count)
                rec_type = rec.type.name if rec.type else "UNKNOWN"

                # Resolve campaign
                campaign_rn = rec.campaign
                local_campaign_id = None
                campaign_name = row.campaign.name if row.campaign else None
                if campaign_rn:
                    camp_gid = campaign_rn.split("/")[-1]
                    camp = db.query(Campaign).filter(
                        Campaign.client_id == client_record.id,
                        Campaign.google_campaign_id == camp_gid,
                    ).first()
                    if camp:
                        local_campaign_id = camp.id

                impact = {}
                try:
                    base = rec.impact.base_metrics
                    pot = rec.impact.potential_metrics
                    impact = {
                        "base": {"impressions": base.impressions, "clicks": base.clicks,
                                 "cost_micros": base.cost_micros, "conversions": float(base.conversions)},
                        "potential": {"impressions": pot.impressions, "clicks": pot.clicks,
                                      "cost_micros": pot.cost_micros, "conversions": float(pot.conversions)},
                    }
                except (AttributeError, TypeError):
                    pass

                data = {
                    "client_id": client_record.id,
                    "campaign_id": local_campaign_id,
                    "google_recommendation_id": rec_id,
                    "recommendation_type": rec_type,
                    "impact_estimate": impact if impact else None,
                    "campaign_name": campaign_name,
                    "status": "ACTIVE",
                    "dismissed": False,
                }

                existing = db.query(GoogleRecommendation).filter(
                    GoogleRecommendation.client_id == client_record.id,
                    GoogleRecommendation.google_recommendation_id == rec_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(GoogleRecommendation(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} Google recommendations")
            return count

        except Exception as e:
            logger.warning(f"Google recommendations sync: {self._format_google_ads_error(e)}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Audiences Sync (C6 — remarketing, in-market, affinity, custom)
    # -----------------------------------------------------------------------

    def sync_audiences(self, db: Session, customer_id: str) -> int:
        """Fetch audience lists (user lists + custom audiences)."""
        from app.models.audience import Audience

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                audience.id,
                audience.name,
                audience.description,
                audience.status,
                audience.resource_name
            FROM audience
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                a = row.audience
                google_id = str(a.id)

                data = {
                    "client_id": client_record.id,
                    "google_audience_id": google_id,
                    "resource_name": a.resource_name,
                    "name": a.name or f"Audience {google_id}",
                    "description": a.description or None,
                    "status": a.status.name if a.status else "ENABLED",
                }

                existing = db.query(Audience).filter(
                    Audience.client_id == client_record.id,
                    Audience.google_audience_id == google_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(Audience(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} audiences")
            return count

        except Exception as e:
            logger.warning(f"Audiences sync: {self._format_google_ads_error(e)}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Topic Performance Sync (C3 — Display/Video topic targeting)
    # -----------------------------------------------------------------------

    def sync_topic_metrics(self, db: Session, customer_id: str,
                            date_from: date = None, date_to: date = None) -> int:
        """Fetch topic targeting performance for Display/Video campaigns."""
        from app.models.topic import TopicPerformance

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
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
                topic_view.resource_name,
                ad_group_criterion.topic.path,
                ad_group_criterion.topic.topic_constant,
                ad_group_criterion.bid_modifier,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr
            FROM topic_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                topic_constant = row.ad_group_criterion.topic.topic_constant
                topic_id = topic_constant.split("/")[-1] if topic_constant else None
                topic_path = ""
                try:
                    paths = row.ad_group_criterion.topic.path
                    topic_path = " > ".join(paths) if paths else ""
                except (AttributeError, TypeError):
                    pass

                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                existing = db.query(TopicPerformance).filter(
                    TopicPerformance.campaign_id == campaign.id,
                    TopicPerformance.date == metric_date,
                    TopicPerformance.topic_id == topic_id,
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "topic_id": topic_id,
                    "topic_path": topic_path,
                    "bid_modifier": row.ad_group_criterion.bid_modifier,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(m.ctr * 100, 2) if m.ctr else 0.0,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(TopicPerformance(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} topic performance rows")
            return count

        except Exception as e:
            logger.warning(f"Topic metrics sync: {self._format_google_ads_error(e)}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Bid Modifiers Sync (device + location + ad_schedule)
    # -----------------------------------------------------------------------

    def sync_bid_modifiers(self, db: Session, customer_id: str) -> int:
        """Fetch device, location, and ad schedule bid modifiers."""
        from app.models.bid_modifier import BidModifier

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        campaign_map = {
            c.google_campaign_id: c.id
            for c in db.query(Campaign).filter(Campaign.client_id == client_record.id).all()
        }
        if not campaign_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        total = 0

        # 1. Device bid modifiers
        device_query = """
            SELECT
                campaign.id,
                campaign_criterion.criterion_id,
                campaign_criterion.device.type,
                campaign_criterion.bid_modifier
            FROM campaign_criterion
            WHERE campaign_criterion.type = 'DEVICE'
              AND campaign.status != 'REMOVED'
        """
        try:
            for row in ga_service.search(customer_id=normalized, query=device_query):
                gcid = str(row.campaign.id)
                local_id = campaign_map.get(gcid)
                if not local_id:
                    continue
                device = row.campaign_criterion.device.type.name
                mod = row.campaign_criterion.bid_modifier or 1.0

                existing = db.query(BidModifier).filter(
                    BidModifier.campaign_id == local_id,
                    BidModifier.modifier_type == "DEVICE",
                    BidModifier.device_type == device,
                ).first()

                data = {
                    "campaign_id": local_id,
                    "google_criterion_id": str(row.campaign_criterion.criterion_id),
                    "modifier_type": "DEVICE",
                    "device_type": device,
                    "bid_modifier": mod,
                }
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(BidModifier(**data))
                total += 1
        except Exception as e:
            logger.warning(f"Device bid modifiers sync error: {e}")

        # 2. Location bid modifiers
        location_query = """
            SELECT
                campaign.id,
                campaign_criterion.criterion_id,
                campaign_criterion.location.geo_target_constant,
                campaign_criterion.bid_modifier
            FROM campaign_criterion
            WHERE campaign_criterion.type = 'LOCATION'
              AND campaign.status != 'REMOVED'
        """
        try:
            for row in ga_service.search(customer_id=normalized, query=location_query):
                gcid = str(row.campaign.id)
                local_id = campaign_map.get(gcid)
                if not local_id:
                    continue
                loc_rn = row.campaign_criterion.location.geo_target_constant
                loc_id = loc_rn.split("/")[-1] if loc_rn else None
                mod = row.campaign_criterion.bid_modifier or 1.0

                existing = db.query(BidModifier).filter(
                    BidModifier.campaign_id == local_id,
                    BidModifier.modifier_type == "LOCATION",
                    BidModifier.location_id == loc_id,
                ).first()

                data = {
                    "campaign_id": local_id,
                    "google_criterion_id": str(row.campaign_criterion.criterion_id),
                    "modifier_type": "LOCATION",
                    "location_id": loc_id,
                    "location_name": loc_rn,
                    "bid_modifier": mod,
                }
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(BidModifier(**data))
                total += 1
        except Exception as e:
            logger.warning(f"Location bid modifiers sync error: {e}")

        # 3. Ad schedule bid modifiers (A4)
        schedule_query = """
            SELECT
                campaign.id,
                campaign_criterion.criterion_id,
                campaign_criterion.ad_schedule.day_of_week,
                campaign_criterion.ad_schedule.start_hour,
                campaign_criterion.ad_schedule.end_hour,
                campaign_criterion.ad_schedule.start_minute,
                campaign_criterion.ad_schedule.end_minute,
                campaign_criterion.bid_modifier
            FROM campaign_criterion
            WHERE campaign_criterion.type = 'AD_SCHEDULE'
              AND campaign.status != 'REMOVED'
        """
        try:
            for row in ga_service.search(customer_id=normalized, query=schedule_query):
                gcid = str(row.campaign.id)
                local_id = campaign_map.get(gcid)
                if not local_id:
                    continue
                sched = row.campaign_criterion.ad_schedule
                dow = sched.day_of_week.name if sched.day_of_week else None
                mod = row.campaign_criterion.bid_modifier or 1.0

                existing = db.query(BidModifier).filter(
                    BidModifier.campaign_id == local_id,
                    BidModifier.modifier_type == "AD_SCHEDULE",
                    BidModifier.day_of_week == dow,
                    BidModifier.start_hour == sched.start_hour,
                ).first()

                data = {
                    "campaign_id": local_id,
                    "google_criterion_id": str(row.campaign_criterion.criterion_id),
                    "modifier_type": "AD_SCHEDULE",
                    "day_of_week": dow,
                    "start_hour": sched.start_hour,
                    "end_hour": sched.end_hour,
                    "start_minute": sched.start_minute.name if sched.start_minute else "ZERO",
                    "end_minute": sched.end_minute.name if sched.end_minute else "ZERO",
                    "bid_modifier": mod,
                }
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(BidModifier(**data))
                total += 1
        except Exception as e:
            logger.warning(f"Ad schedule bid modifiers sync error: {e}")

        db.commit()
        logger.info(f"Synced {total} bid modifiers for customer {normalized}")
        return total

    # -----------------------------------------------------------------------
    # Portfolio Bidding Strategies Sync
    # -----------------------------------------------------------------------

    def sync_bidding_strategies(self, db: Session, customer_id: str) -> int:
        """Fetch portfolio bidding strategies."""
        from app.models.bidding_strategy import BiddingStrategy

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                bidding_strategy.id,
                bidding_strategy.name,
                bidding_strategy.type,
                bidding_strategy.status,
                bidding_strategy.resource_name,
                bidding_strategy.target_cpa.target_cpa_micros,
                bidding_strategy.target_roas.target_roas,
                bidding_strategy.maximize_conversions.target_cpa_micros,
                bidding_strategy.campaign_count
            FROM bidding_strategy
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                bs = row.bidding_strategy
                google_id = str(bs.id)

                target_cpa = None
                target_roas_val = None
                try:
                    if bs.target_cpa.target_cpa_micros:
                        target_cpa = bs.target_cpa.target_cpa_micros
                except (AttributeError, TypeError):
                    pass
                try:
                    if bs.target_roas.target_roas:
                        target_roas_val = bs.target_roas.target_roas
                except (AttributeError, TypeError):
                    pass
                try:
                    if not target_cpa and bs.maximize_conversions.target_cpa_micros:
                        target_cpa = bs.maximize_conversions.target_cpa_micros
                except (AttributeError, TypeError):
                    pass

                data = {
                    "client_id": client_record.id,
                    "google_strategy_id": google_id,
                    "resource_name": bs.resource_name,
                    "name": bs.name,
                    "strategy_type": bs.type.name if bs.type else None,
                    "status": bs.status.name if bs.status else "ENABLED",
                    "target_cpa_micros": target_cpa,
                    "target_roas": target_roas_val,
                    "campaign_count": bs.campaign_count or 0,
                }

                existing = db.query(BiddingStrategy).filter(
                    BiddingStrategy.client_id == client_record.id,
                    BiddingStrategy.google_strategy_id == google_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(BiddingStrategy(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} bidding strategies")
            return count

        except Exception as e:
            logger.error(f"Error syncing bidding strategies: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Shared Budgets Sync
    # -----------------------------------------------------------------------

    def sync_shared_budgets(self, db: Session, customer_id: str) -> int:
        """Fetch shared budgets."""
        from app.models.bidding_strategy import SharedBudget

        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign_budget.id,
                campaign_budget.name,
                campaign_budget.amount_micros,
                campaign_budget.delivery_method,
                campaign_budget.status,
                campaign_budget.resource_name,
                campaign_budget.reference_count
            FROM campaign_budget
            WHERE campaign_budget.explicitly_shared = TRUE
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                cb = row.campaign_budget
                google_id = str(cb.id)

                data = {
                    "client_id": client_record.id,
                    "google_budget_id": google_id,
                    "resource_name": cb.resource_name,
                    "name": cb.name or f"Budget {google_id}",
                    "amount_micros": cb.amount_micros,
                    "delivery_method": cb.delivery_method.name if cb.delivery_method else None,
                    "status": cb.status.name if cb.status else "ENABLED",
                    "campaign_count": cb.reference_count or 0,
                }

                existing = db.query(SharedBudget).filter(
                    SharedBudget.client_id == client_record.id,
                    SharedBudget.google_budget_id == google_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(SharedBudget(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} shared budgets")
            return count

        except Exception as e:
            logger.error(f"Error syncing shared budgets: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Placement Metrics Sync (Display + Video campaigns)
    # -----------------------------------------------------------------------

    def sync_placement_metrics(self, db: Session, customer_id: str,
                                date_from: date = None, date_to: date = None) -> int:
        """Fetch placement performance for Display/Video campaigns."""
        from app.models.placement import Placement

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
                detail_placement_view.display_name,
                detail_placement_view.target_url,
                detail_placement_view.placement_type,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.average_cpc,
                metrics.video_views,
                metrics.video_view_rate,
                metrics.average_cpv
            FROM detail_placement_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0

            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                dpv = row.detail_placement_view
                placement_url = dpv.target_url or dpv.display_name or "unknown"
                placement_type = dpv.placement_type.name if dpv.placement_type else None
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                existing = db.query(Placement).filter(
                    Placement.campaign_id == campaign.id,
                    Placement.date == metric_date,
                    Placement.placement_url == placement_url,
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "placement_url": placement_url,
                    "placement_type": placement_type,
                    "display_name": dpv.display_name or placement_url,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(m.ctr * 100, 2) if m.ctr else 0.0,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                    "video_views": m.video_views if m.video_views else None,
                    "video_view_rate": round(m.video_view_rate * 100, 2) if m.video_view_rate else None,
                    "avg_cpv_micros": int(m.average_cpv * 1_000_000) if m.average_cpv else None,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(Placement(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} placement rows for customer {normalized_customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing placement metrics: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Product Groups Sync (Shopping campaigns — listing_group_filter)
    # -----------------------------------------------------------------------

    def sync_product_groups(self, db: Session, customer_id: str) -> int:
        """Fetch product group listing criteria for Shopping campaigns."""
        from app.models.product_group import ProductGroup

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
                ad_group_criterion.listing_group.parent_ad_group_criterion,
                ad_group_criterion.listing_group.type,
                ad_group_criterion.listing_group.case_value.product_brand.value,
                ad_group_criterion.listing_group.case_value.product_type.value,
                ad_group_criterion.listing_group.case_value.product_category.category_id,
                ad_group_criterion.listing_group.case_value.product_channel.channel,
                ad_group_criterion.listing_group.case_value.product_custom_attribute.value,
                ad_group_criterion.cpc_bid_micros,
                ad_group_criterion.status,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = 'LISTING_GROUP'
              AND campaign.status != 'REMOVED'
              AND campaign.advertising_channel_type IN ('SHOPPING', 'PERFORMANCE_MAX')
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                ad_group_google_id = str(row.ad_group.id)

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                ad_group = db.query(AdGroup).filter(
                    AdGroup.campaign_id == campaign.id,
                    AdGroup.google_ad_group_id == ad_group_google_id,
                ).first()

                criterion = row.ad_group_criterion
                criterion_id = str(criterion.criterion_id)
                lg = criterion.listing_group

                # Determine case value type and value
                case_type = None
                case_val = None
                try:
                    if lg.case_value.product_brand.value:
                        case_type = "PRODUCT_BRAND"
                        case_val = lg.case_value.product_brand.value
                except (AttributeError, TypeError):
                    pass
                try:
                    if not case_type and lg.case_value.product_type.value:
                        case_type = "PRODUCT_TYPE"
                        case_val = lg.case_value.product_type.value
                except (AttributeError, TypeError):
                    pass
                try:
                    if not case_type and lg.case_value.product_category.category_id:
                        case_type = "PRODUCT_CATEGORY"
                        case_val = str(lg.case_value.product_category.category_id)
                except (AttributeError, TypeError):
                    pass
                try:
                    if not case_type and lg.case_value.product_custom_attribute.value:
                        case_type = "CUSTOM_ATTRIBUTE"
                        case_val = lg.case_value.product_custom_attribute.value
                except (AttributeError, TypeError):
                    pass
                try:
                    if not case_type and lg.case_value.product_channel.channel:
                        case_type = "PRODUCT_CHANNEL"
                        case_val = lg.case_value.product_channel.channel.name
                except (AttributeError, TypeError):
                    pass

                # Parent criterion
                parent_id = None
                try:
                    parent_rn = lg.parent_ad_group_criterion
                    if parent_rn:
                        parent_id = parent_rn.split("~")[-1] if "~" in parent_rn else None
                except (AttributeError, TypeError):
                    pass

                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                data = {
                    "campaign_id": campaign.id,
                    "ad_group_id": ad_group.id if ad_group else None,
                    "google_criterion_id": criterion_id,
                    "parent_criterion_id": parent_id,
                    "case_value_type": case_type,
                    "case_value": case_val,
                    "partition_type": lg.type.name if lg.type else None,
                    "bid_micros": criterion.cpc_bid_micros if criterion.cpc_bid_micros else 0,
                    "status": criterion.status.name if criterion.status else "ENABLED",
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "ctr": round(m.ctr * 100, 2) if m.ctr else 0.0,
                }

                existing = db.query(ProductGroup).filter(
                    ProductGroup.campaign_id == campaign.id,
                    ProductGroup.ad_group_id == (ad_group.id if ad_group else None),
                    ProductGroup.google_criterion_id == criterion_id,
                ).first()

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(ProductGroup(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} product groups for customer {normalized_customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing product groups: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Auction Insights Sync (per Search/Shopping campaign)
    # -----------------------------------------------------------------------

    def sync_auction_insights(self, db: Session, customer_id: str,
                               date_from: date = None, date_to: date = None) -> int:
        """Fetch auction insights per Search/Shopping campaign and upsert."""
        from app.models.auction_insight import AuctionInsight

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

        # Only Search and Shopping campaigns support auction insights
        campaigns = (
            db.query(Campaign)
            .filter(
                Campaign.client_id == client_record.id,
                Campaign.status != "REMOVED",
                Campaign.campaign_type.in_(["SEARCH", "SHOPPING"]),
            )
            .all()
        )

        ga_service = self.client.get_service("GoogleAdsService")
        total_count = 0

        for campaign in campaigns:
            query = f"""
                SELECT
                    auction_insight.display_domain,
                    metrics.auction_insight_search_impression_share,
                    metrics.auction_insight_search_overlap_rate,
                    metrics.auction_insight_search_position_above_rate,
                    metrics.auction_insight_search_outranking_share,
                    metrics.auction_insight_search_top_impression_percentage,
                    metrics.auction_insight_search_absolute_top_impression_percentage,
                    segments.date
                FROM auction_insight
                WHERE campaign.id = {campaign.google_campaign_id}
                  AND segments.date BETWEEN '{date_from}' AND '{date_to}'
            """

            try:
                response = ga_service.search(
                    customer_id=normalized_customer_id, query=query
                )

                for row in response:
                    domain = row.auction_insight.display_domain
                    row_date = date(
                        row.segments.date.year,
                        row.segments.date.month,
                        row.segments.date.day,
                    )

                    existing = (
                        db.query(AuctionInsight)
                        .filter(
                            AuctionInsight.campaign_id == campaign.id,
                            AuctionInsight.date == row_date,
                            AuctionInsight.display_domain == domain,
                        )
                        .first()
                    )

                    data = {
                        "campaign_id": campaign.id,
                        "date": row_date,
                        "display_domain": domain,
                        "impression_share": row.metrics.auction_insight_search_impression_share,
                        "overlap_rate": row.metrics.auction_insight_search_overlap_rate,
                        "position_above_rate": row.metrics.auction_insight_search_position_above_rate,
                        "outranking_share": row.metrics.auction_insight_search_outranking_share,
                        "top_of_page_rate": row.metrics.auction_insight_search_top_impression_percentage,
                        "abs_top_of_page_rate": row.metrics.auction_insight_search_absolute_top_impression_percentage,
                    }

                    if existing:
                        for key, value in data.items():
                            setattr(existing, key, value)
                    else:
                        db.add(AuctionInsight(**data))
                    total_count += 1

            except Exception as e:
                error_str = self._format_google_ads_error(e)
                # Empty results are normal for low-volume campaigns
                if "INSUFFICIENT" in str(error_str).upper() or "NO_DATA" in str(error_str).upper():
                    logger.debug(f"No auction insight data for campaign {campaign.name}: {error_str}")
                    continue
                logger.warning(f"Auction insights error for campaign {campaign.name}: {error_str}")
                continue

        db.commit()
        logger.info(f"Synced {total_count} auction insight rows for customer {normalized_customer_id}")
        return total_count

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

    def sync_negative_keyword_lists(self, db: Session, customer_id: str) -> int:
        """Fetch shared negative keyword lists and their members from Google Ads API."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")

        # Step 1: Fetch all NEGATIVE shared sets
        shared_set_query = """
            SELECT
                shared_set.id,
                shared_set.resource_name,
                shared_set.name,
                shared_set.type,
                shared_set.status,
                shared_set.member_count
            FROM shared_set
            WHERE shared_set.type = NEGATIVE_KEYWORDS
              AND shared_set.status != 'REMOVED'
        """

        # Step 2: Fetch all criteria (members) of negative shared sets
        shared_criterion_query = """
            SELECT
                shared_criterion.shared_set,
                shared_criterion.criterion_id,
                shared_criterion.type,
                shared_criterion.keyword.text,
                shared_criterion.keyword.match_type
            FROM shared_criterion
            WHERE shared_criterion.type = KEYWORD
        """

        try:
            # Fetch shared sets
            set_rows = ga_service.search(customer_id=normalized_customer_id, query=shared_set_query)
            seen_set_ids: set[int] = set()
            set_map: dict[str, int] = {}  # google resource_name -> local list id
            count = 0

            for row in set_rows:
                ss = row.shared_set
                google_id = ss.id
                seen_set_ids.add(google_id)

                existing = (
                    db.query(NegativeKeywordList)
                    .filter(
                        NegativeKeywordList.client_id == client_record.id,
                        NegativeKeywordList.google_shared_set_id == google_id,
                    )
                    .first()
                )

                if existing:
                    existing.name = ss.name
                    existing.status = ss.status.name
                    existing.member_count = ss.member_count
                    existing.google_resource_name = ss.resource_name
                    existing.source = "GOOGLE_ADS_SYNC"
                    set_map[ss.resource_name] = existing.id
                else:
                    nkl = NegativeKeywordList(
                        client_id=client_record.id,
                        google_shared_set_id=google_id,
                        google_resource_name=ss.resource_name,
                        name=ss.name,
                        source="GOOGLE_ADS_SYNC",
                        member_count=ss.member_count,
                        status=ss.status.name,
                    )
                    db.add(nkl)
                    db.flush()
                    set_map[ss.resource_name] = nkl.id
                count += 1

            # Mark removed: synced lists no longer in API
            stale_lists = (
                db.query(NegativeKeywordList)
                .filter(
                    NegativeKeywordList.client_id == client_record.id,
                    NegativeKeywordList.source == "GOOGLE_ADS_SYNC",
                    NegativeKeywordList.google_shared_set_id.isnot(None),
                    ~NegativeKeywordList.google_shared_set_id.in_(seen_set_ids) if seen_set_ids else True,
                )
                .all()
            )
            for stale in stale_lists:
                stale.status = "REMOVED"

            # Fetch shared criteria (list members)
            criterion_rows = ga_service.search(customer_id=normalized_customer_id, query=shared_criterion_query)
            seen_items: dict[int, set[tuple[str, str]]] = {}  # list_id -> set of (text, match_type)

            for row in criterion_rows:
                sc = row.shared_criterion
                shared_set_rn = sc.shared_set
                local_list_id = set_map.get(shared_set_rn)
                if not local_list_id:
                    continue

                text = sc.keyword.text
                match_type = getattr(sc.keyword.match_type, "name", str(sc.keyword.match_type))
                criterion_id = sc.criterion_id

                seen_items.setdefault(local_list_id, set()).add((text, match_type))

                existing_item = (
                    db.query(NegativeKeywordListItem)
                    .filter(
                        NegativeKeywordListItem.list_id == local_list_id,
                        NegativeKeywordListItem.text == text,
                        NegativeKeywordListItem.match_type == match_type,
                    )
                    .first()
                )

                if existing_item:
                    existing_item.google_criterion_id = criterion_id
                else:
                    db.add(NegativeKeywordListItem(
                        list_id=local_list_id,
                        google_criterion_id=criterion_id,
                        text=text,
                        match_type=match_type,
                    ))

            # Remove stale items from synced lists
            for local_list_id, seen_pairs in seen_items.items():
                all_items = (
                    db.query(NegativeKeywordListItem)
                    .filter(NegativeKeywordListItem.list_id == local_list_id)
                    .all()
                )
                for item in all_items:
                    if (item.text, item.match_type) not in seen_pairs:
                        db.delete(item)

            # Also clean items from synced lists that had zero criteria returned
            for rn, local_list_id in set_map.items():
                if local_list_id not in seen_items:
                    db.query(NegativeKeywordListItem).filter(
                        NegativeKeywordListItem.list_id == local_list_id
                    ).delete()

            db.commit()
            logger.info(
                f"Synced {count} negative keyword lists for customer {normalized_customer_id}"
            )
            return count

        except Exception as e:
            logger.error(f"Error syncing negative keyword lists: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    def sync_mcc_exclusion_lists(self, db: Session, manager_customer_id: str) -> dict:
        """Sync MCC-level exclusion lists (negative keywords + placements) from manager account.

        These are lists owned by the MCC manager, applied across client accounts.
        Stored with ownership_level='mcc' and source='MCC_SYNC'.
        """
        if not self.is_connected:
            return {"keyword_lists": 0, "placement_lists": 0}

        normalized = self.normalize_customer_id(manager_customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return {"keyword_lists": 0, "placement_lists": 0}

        ga_service = self.client.get_service("GoogleAdsService")

        kw_count = self._sync_mcc_negative_keyword_lists(db, ga_service, normalized, client_record)
        pl_count = self._sync_mcc_placement_exclusion_lists(db, ga_service, normalized, client_record)

        db.commit()
        logger.info(
            f"MCC sync for {normalized}: {kw_count} keyword lists, {pl_count} placement lists"
        )
        return {"keyword_lists": kw_count, "placement_lists": pl_count}

    def _sync_mcc_negative_keyword_lists(
        self, db: Session, ga_service, customer_id: str, client_record
    ) -> int:
        """Sync NEGATIVE_KEYWORDS SharedSets from manager account as MCC-level lists."""
        query = """
            SELECT
                shared_set.id, shared_set.resource_name, shared_set.name,
                shared_set.type, shared_set.status, shared_set.member_count
            FROM shared_set
            WHERE shared_set.type = NEGATIVE_KEYWORDS
              AND shared_set.status != 'REMOVED'
        """
        criterion_query = """
            SELECT
                shared_criterion.shared_set, shared_criterion.criterion_id,
                shared_criterion.type, shared_criterion.keyword.text,
                shared_criterion.keyword.match_type
            FROM shared_criterion
            WHERE shared_criterion.type = KEYWORD
        """

        try:
            rows = ga_service.search(customer_id=customer_id, query=query)
            seen_ids: set[int] = set()
            set_map: dict[str, int] = {}
            count = 0

            for row in rows:
                ss = row.shared_set
                seen_ids.add(ss.id)

                existing = (
                    db.query(NegativeKeywordList)
                    .filter(
                        NegativeKeywordList.client_id == client_record.id,
                        NegativeKeywordList.google_shared_set_id == ss.id,
                    )
                    .first()
                )

                if existing:
                    existing.name = ss.name
                    existing.status = ss.status.name
                    existing.member_count = ss.member_count
                    existing.google_resource_name = ss.resource_name
                    existing.source = "MCC_SYNC"
                    existing.ownership_level = "mcc"
                    set_map[ss.resource_name] = existing.id
                else:
                    nkl = NegativeKeywordList(
                        client_id=client_record.id,
                        google_shared_set_id=ss.id,
                        google_resource_name=ss.resource_name,
                        name=ss.name,
                        source="MCC_SYNC",
                        ownership_level="mcc",
                        member_count=ss.member_count,
                        status=ss.status.name,
                    )
                    db.add(nkl)
                    db.flush()
                    set_map[ss.resource_name] = nkl.id
                count += 1

            # Mark stale MCC lists as REMOVED
            if seen_ids:
                stale = (
                    db.query(NegativeKeywordList)
                    .filter(
                        NegativeKeywordList.client_id == client_record.id,
                        NegativeKeywordList.ownership_level == "mcc",
                        NegativeKeywordList.google_shared_set_id.isnot(None),
                        ~NegativeKeywordList.google_shared_set_id.in_(seen_ids),
                    )
                    .all()
                )
                for s in stale:
                    s.status = "REMOVED"

            # Sync criteria (list members)
            crit_rows = ga_service.search(customer_id=customer_id, query=criterion_query)
            seen_items: dict[int, set[tuple[str, str]]] = {}

            for row in crit_rows:
                sc = row.shared_criterion
                local_id = set_map.get(sc.shared_set)
                if not local_id:
                    continue

                text = sc.keyword.text
                match_type = getattr(sc.keyword.match_type, "name", str(sc.keyword.match_type))
                seen_items.setdefault(local_id, set()).add((text, match_type))

                existing_item = (
                    db.query(NegativeKeywordListItem)
                    .filter(
                        NegativeKeywordListItem.list_id == local_id,
                        NegativeKeywordListItem.text == text,
                        NegativeKeywordListItem.match_type == match_type,
                    )
                    .first()
                )
                if existing_item:
                    existing_item.google_criterion_id = sc.criterion_id
                else:
                    db.add(NegativeKeywordListItem(
                        list_id=local_id,
                        google_criterion_id=sc.criterion_id,
                        text=text,
                        match_type=match_type,
                    ))

            # Remove stale items
            for local_id, pairs in seen_items.items():
                for item in db.query(NegativeKeywordListItem).filter(
                    NegativeKeywordListItem.list_id == local_id
                ).all():
                    if (item.text, item.match_type) not in pairs:
                        db.delete(item)

            for rn, local_id in set_map.items():
                if local_id not in seen_items:
                    db.query(NegativeKeywordListItem).filter(
                        NegativeKeywordListItem.list_id == local_id
                    ).delete()

            return count

        except Exception as e:
            logger.error(f"Error syncing MCC keyword lists: {self._format_google_ads_error(e)}")
            return 0

    def _sync_mcc_placement_exclusion_lists(
        self, db: Session, ga_service, customer_id: str, client_record
    ) -> int:
        """Sync NEGATIVE_PLACEMENTS SharedSets from manager account."""
        query = """
            SELECT
                shared_set.id, shared_set.resource_name, shared_set.name,
                shared_set.type, shared_set.status, shared_set.member_count
            FROM shared_set
            WHERE shared_set.type = NEGATIVE_PLACEMENTS
              AND shared_set.status != 'REMOVED'
        """
        criterion_query = """
            SELECT
                shared_criterion.shared_set, shared_criterion.criterion_id,
                shared_criterion.type, shared_criterion.placement.url
            FROM shared_criterion
            WHERE shared_criterion.type = PLACEMENT
        """

        try:
            rows = ga_service.search(customer_id=customer_id, query=query)
            seen_ids: set[int] = set()
            set_map: dict[str, int] = {}
            count = 0

            for row in rows:
                ss = row.shared_set
                seen_ids.add(ss.id)

                existing = (
                    db.query(PlacementExclusionList)
                    .filter(
                        PlacementExclusionList.client_id == client_record.id,
                        PlacementExclusionList.google_shared_set_id == ss.id,
                    )
                    .first()
                )

                if existing:
                    existing.name = ss.name
                    existing.status = ss.status.name
                    existing.member_count = ss.member_count
                    existing.google_resource_name = ss.resource_name
                    existing.source = "MCC_SYNC"
                    existing.ownership_level = "mcc"
                    set_map[ss.resource_name] = existing.id
                else:
                    pel = PlacementExclusionList(
                        client_id=client_record.id,
                        google_shared_set_id=ss.id,
                        google_resource_name=ss.resource_name,
                        name=ss.name,
                        source="MCC_SYNC",
                        ownership_level="mcc",
                        member_count=ss.member_count,
                        status=ss.status.name,
                    )
                    db.add(pel)
                    db.flush()
                    set_map[ss.resource_name] = pel.id
                count += 1

            # Mark stale
            if seen_ids:
                stale = (
                    db.query(PlacementExclusionList)
                    .filter(
                        PlacementExclusionList.client_id == client_record.id,
                        PlacementExclusionList.ownership_level == "mcc",
                        PlacementExclusionList.google_shared_set_id.isnot(None),
                        ~PlacementExclusionList.google_shared_set_id.in_(seen_ids),
                    )
                    .all()
                )
                for s in stale:
                    s.status = "REMOVED"

            # Sync placement criteria
            crit_rows = ga_service.search(customer_id=customer_id, query=criterion_query)
            seen_items: dict[int, set[str]] = {}

            for row in crit_rows:
                sc = row.shared_criterion
                local_id = set_map.get(sc.shared_set)
                if not local_id:
                    continue

                url = sc.placement.url
                seen_items.setdefault(local_id, set()).add(url)

                existing_item = (
                    db.query(PlacementExclusionListItem)
                    .filter(
                        PlacementExclusionListItem.list_id == local_id,
                        PlacementExclusionListItem.url == url,
                    )
                    .first()
                )
                if existing_item:
                    existing_item.google_criterion_id = sc.criterion_id
                else:
                    # Determine placement type from URL pattern
                    ptype = "WEBSITE"
                    if "youtube.com/channel" in url or "youtube.com/c/" in url:
                        ptype = "YOUTUBE_CHANNEL"
                    elif "youtube.com/watch" in url or "youtube.com/video" in url:
                        ptype = "YOUTUBE_VIDEO"
                    elif "play.google.com" in url or "apps.apple.com" in url:
                        ptype = "MOBILE_APP"

                    db.add(PlacementExclusionListItem(
                        list_id=local_id,
                        google_criterion_id=sc.criterion_id,
                        url=url,
                        placement_type=ptype,
                    ))

            # Remove stale items
            for local_id, urls in seen_items.items():
                for item in db.query(PlacementExclusionListItem).filter(
                    PlacementExclusionListItem.list_id == local_id
                ).all():
                    if item.url not in urls:
                        db.delete(item)

            for rn, local_id in set_map.items():
                if local_id not in seen_items:
                    db.query(PlacementExclusionListItem).filter(
                        PlacementExclusionListItem.list_id == local_id
                    ).delete()

            return count

        except Exception as e:
            logger.error(f"Error syncing MCC placement lists: {self._format_google_ads_error(e)}")
            return 0

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

        ids_str = ",".join(str(int(cid)) for cid in criterion_ids)
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

            # Aggregate raw rows by (campaign, date, resolved_city) — multiple
            # criterion IDs can map to the same resolved city name, creating
            # duplicate storage keys that trigger UNIQUE constraint failures
            # when autoflush=False defers inserts until commit.
            batch: dict[tuple, dict] = {}
            raw_by_city: dict[str, set] = {}  # resolved_city -> set of raw names (for existing lookup)
            for row in raw_rows:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                geo_city_raw = row.segments.geo_target_city
                geo_city = geo_name_map.get(geo_city_raw, geo_city_raw) if geo_city_raw else "Unknown"
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                key = (campaign_google_id, metric_date, geo_city)
                if geo_city_raw:
                    raw_by_city.setdefault(geo_city, set()).add(geo_city_raw)

                if key in batch:
                    agg = batch[key]
                    agg["clicks"] += m.clicks
                    agg["impressions"] += m.impressions
                    agg["conversions"] += float(m.conversions)
                    agg["conversion_value_micros"] += int(conv_value * 1_000_000)
                    agg["cost_micros"] += m.cost_micros
                else:
                    batch[key] = {
                        "clicks": m.clicks,
                        "impressions": m.impressions,
                        "conversions": float(m.conversions),
                        "conversion_value_micros": int(conv_value * 1_000_000),
                        "cost_micros": m.cost_micros,
                    }

            count = 0
            for (campaign_google_id, metric_date, geo_city), agg in batch.items():
                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                # Match by resolved name OR any raw resource name (handles migration from old encoding)
                match_cities = [geo_city] + list(raw_by_city.get(geo_city, set()))
                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.in_(match_cities),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.age_range.is_(None),
                    MetricSegmented.gender.is_(None),
                    MetricSegmented.ad_network_type.is_(None),
                ).first()

                ctr = (agg["clicks"] / agg["impressions"] * 100) if agg["impressions"] else 0.0
                avg_cpc = int(agg["cost_micros"] / agg["clicks"]) if agg["clicks"] else 0

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "device": None,
                    "geo_city": geo_city,
                    "clicks": agg["clicks"],
                    "impressions": agg["impressions"],
                    "ctr": ctr,
                    "conversions": agg["conversions"],
                    "conversion_value_micros": agg["conversion_value_micros"],
                    "cost_micros": agg["cost_micros"],
                    "avg_cpc_micros": avg_cpc,
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
    # Apply Action + all _mutate_* methods → moved to GoogleAdsMutationsMixin
    # (see google_ads_mutations.py)
    # -----------------------------------------------------------------------
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

    # _mutate_* and batch_* methods → inherited from GoogleAdsMutationsMixin

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
                    customer_client.level,
                    customer_client.currency_code
                FROM customer_client
                WHERE customer_client.level <= 1
            """
            response = ga_service.search(customer_id=mcc_id, query=query)

            accounts = []
            for row in response:
                cc = row.customer_client
                if cc.manager:
                    continue
                currency_code = (getattr(cc, "currency_code", "") or "").strip().upper() or None
                accounts.append({
                    "customer_id": str(cc.id),
                    "name": cc.descriptive_name or f"Account {cc.id}",
                    "currency_code": currency_code,
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

    # -----------------------------------------------------------------------
    # Conversion Actions Sync (GAP 2A-2D)
    # -----------------------------------------------------------------------

    def sync_conversion_actions(self, db: Session, customer_id: str) -> int:
        """Fetch conversion actions for data quality audit."""
        if not self.is_connected:
            return 0

        normalized_customer_id = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized_customer_id)
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                conversion_action.id,
                conversion_action.name,
                conversion_action.category,
                conversion_action.status,
                conversion_action.type,
                conversion_action.primary_for_goal,
                conversion_action.counting_type,
                conversion_action.value_settings.default_value,
                conversion_action.value_settings.always_use_default_value,
                conversion_action.attribution_model_settings.attribution_model,
                conversion_action.click_through_lookback_window_days,
                conversion_action.view_through_lookback_window_days,
                conversion_action.include_in_conversions_metric
            FROM conversion_action
            WHERE conversion_action.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            for row in response:
                ca = row.conversion_action
                google_id = str(ca.id)

                existing = db.query(ConversionAction).filter(
                    ConversionAction.client_id == client_record.id,
                    ConversionAction.google_conversion_action_id == google_id,
                ).first()

                data = {
                    "client_id": client_record.id,
                    "google_conversion_action_id": google_id,
                    "name": ca.name,
                    "category": ca.category.name if hasattr(ca.category, 'name') else str(ca.category),
                    "status": ca.status.name if hasattr(ca.status, 'name') else str(ca.status),
                    "type": ca.type.name if hasattr(ca.type, 'name') else str(ca.type) if ca.type else None,
                    "primary_for_goal": bool(ca.primary_for_goal),
                    "counting_type": ca.counting_type.name if hasattr(ca.counting_type, 'name') else str(ca.counting_type) if ca.counting_type else None,
                    "value_settings_default_value": float(ca.value_settings.default_value) if ca.value_settings and ca.value_settings.default_value else None,
                    "value_settings_always_use_default": bool(ca.value_settings.always_use_default_value) if ca.value_settings else None,
                    "attribution_model": ca.attribution_model_settings.attribution_model.name if ca.attribution_model_settings and hasattr(ca.attribution_model_settings.attribution_model, 'name') else None,
                    "click_through_lookback_window_days": int(ca.click_through_lookback_window_days) if ca.click_through_lookback_window_days else None,
                    "view_through_lookback_window_days": int(ca.view_through_lookback_window_days) if ca.view_through_lookback_window_days else None,
                    "include_in_conversions_metric": bool(ca.include_in_conversions_metric),
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(ConversionAction(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} conversion actions for customer {normalized_customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing conversion actions: {self._format_google_ads_error(e)}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Demographic Metrics Sync (GAP 4A)
    # -----------------------------------------------------------------------

    def sync_age_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch age-segmented daily campaign metrics via age_range_view."""
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
                ad_group_criterion.age_range.type,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM age_range_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            # age_range_view returns one row per ad_group_criterion. Aggregate in memory
            # so (campaign_google_id, date, age_range) is unique before touching DB —
            # prevents UNIQUE constraint violations on uq_metric_segmented_coalesced
            # when autoflush=False defers inserts until commit.
            batch: dict[tuple, dict] = {}
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                age_range = row.ad_group_criterion.age_range.type.name
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                key = (campaign_google_id, metric_date, age_range)
                if key in batch:
                    agg = batch[key]
                    agg["clicks"] += m.clicks
                    agg["impressions"] += m.impressions
                    agg["conversions"] += float(m.conversions)
                    agg["conversion_value_micros"] += int(conv_value * 1_000_000)
                    agg["cost_micros"] += m.cost_micros
                else:
                    batch[key] = {
                        "clicks": m.clicks,
                        "impressions": m.impressions,
                        "conversions": float(m.conversions),
                        "conversion_value_micros": int(conv_value * 1_000_000),
                        "cost_micros": m.cost_micros,
                    }

            count = 0
            for (campaign_google_id, metric_date, age_range), agg in batch.items():
                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.age_range == age_range,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.is_(None),
                    MetricSegmented.gender.is_(None),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.ad_network_type.is_(None),
                ).first()

                # Recompute derivative metrics after aggregation
                ctr = (agg["clicks"] / agg["impressions"] * 100) if agg["impressions"] else 0.0
                avg_cpc = int(agg["cost_micros"] / agg["clicks"]) if agg["clicks"] else 0

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "age_range": age_range,
                    "clicks": agg["clicks"],
                    "impressions": agg["impressions"],
                    "ctr": ctr,
                    "conversions": agg["conversions"],
                    "conversion_value_micros": agg["conversion_value_micros"],
                    "cost_micros": agg["cost_micros"],
                    "avg_cpc_micros": avg_cpc,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} age-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing age metrics: {e}")
            db.rollback()
            raise

    def sync_gender_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch gender-segmented daily campaign metrics via gender_view."""
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
                ad_group_criterion.gender.type,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM gender_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            # Aggregate per-ad_group rows into (campaign, date, gender) before insert
            # to avoid UNIQUE constraint violations (see sync_age_metrics for rationale).
            batch: dict[tuple, dict] = {}
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                gender = row.ad_group_criterion.gender.type.name
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                key = (campaign_google_id, metric_date, gender)
                if key in batch:
                    agg = batch[key]
                    agg["clicks"] += m.clicks
                    agg["impressions"] += m.impressions
                    agg["conversions"] += float(m.conversions)
                    agg["conversion_value_micros"] += int(conv_value * 1_000_000)
                    agg["cost_micros"] += m.cost_micros
                else:
                    batch[key] = {
                        "clicks": m.clicks,
                        "impressions": m.impressions,
                        "conversions": float(m.conversions),
                        "conversion_value_micros": int(conv_value * 1_000_000),
                        "cost_micros": m.cost_micros,
                    }

            count = 0
            for (campaign_google_id, metric_date, gender), agg in batch.items():
                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.gender == gender,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.is_(None),
                    MetricSegmented.age_range.is_(None),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.ad_network_type.is_(None),
                ).first()

                ctr = (agg["clicks"] / agg["impressions"] * 100) if agg["impressions"] else 0.0
                avg_cpc = int(agg["cost_micros"] / agg["clicks"]) if agg["clicks"] else 0

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "gender": gender,
                    "clicks": agg["clicks"],
                    "impressions": agg["impressions"],
                    "ctr": ctr,
                    "conversions": agg["conversions"],
                    "conversion_value_micros": agg["conversion_value_micros"],
                    "cost_micros": agg["cost_micros"],
                    "avg_cpc_micros": avg_cpc,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} gender-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing gender metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Parental Status Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def sync_parental_status_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch parental-status-segmented daily campaign metrics via parental_status_view."""
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
                ad_group_criterion.parental_status.type,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM parental_status_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            # Aggregate per-ad_group rows into (campaign, date, parental_status) before insert
            # to avoid UNIQUE constraint violations (see sync_age_metrics for rationale).
            batch: dict[tuple, dict] = {}
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                parental = row.ad_group_criterion.parental_status.type.name
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                key = (campaign_google_id, metric_date, parental)
                if key in batch:
                    agg = batch[key]
                    agg["clicks"] += m.clicks
                    agg["impressions"] += m.impressions
                    agg["conversions"] += float(m.conversions)
                    agg["conversion_value_micros"] += int(conv_value * 1_000_000)
                    agg["cost_micros"] += m.cost_micros
                else:
                    batch[key] = {
                        "clicks": m.clicks,
                        "impressions": m.impressions,
                        "conversions": float(m.conversions),
                        "conversion_value_micros": int(conv_value * 1_000_000),
                        "cost_micros": m.cost_micros,
                    }

            count = 0
            for (campaign_google_id, metric_date, parental), agg in batch.items():
                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == campaign.id,
                    MetricSegmented.date == metric_date,
                    MetricSegmented.parental_status == parental,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.is_(None),
                    MetricSegmented.age_range.is_(None),
                    MetricSegmented.gender.is_(None),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.ad_network_type.is_(None),
                    MetricSegmented.income_range.is_(None),
                ).first()

                ctr = (agg["clicks"] / agg["impressions"] * 100) if agg["impressions"] else 0.0
                avg_cpc = int(agg["cost_micros"] / agg["clicks"]) if agg["clicks"] else 0

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "parental_status": parental,
                    "clicks": agg["clicks"],
                    "impressions": agg["impressions"],
                    "ctr": ctr,
                    "conversions": agg["conversions"],
                    "conversion_value_micros": agg["conversion_value_micros"],
                    "cost_micros": agg["cost_micros"],
                    "avg_cpc_micros": avg_cpc,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} parental-status-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing parental status metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Income Range Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def sync_income_range_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch income-range-segmented daily campaign metrics via income_range_view."""
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
                ad_group_criterion.income_range.type,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM income_range_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized_customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                income = row.ad_group_criterion.income_range.type.name
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
                    MetricSegmented.income_range == income,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.is_(None),
                    MetricSegmented.age_range.is_(None),
                    MetricSegmented.gender.is_(None),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.ad_network_type.is_(None),
                    MetricSegmented.parental_status.is_(None),
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "income_range": income,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "cost_micros": m.cost_micros,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} income-range-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing income range metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # PMax Channel (ad_network_type) Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def sync_pmax_channel_metrics(self, db: Session, customer_id: str,
                                   date_from: date = None, date_to: date = None) -> int:
        """Sync PMax channel breakdown (ad_network_type) into MetricSegmented."""
        if not self.is_connected:
            return 0
        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        campaign_map = {
            c.google_campaign_id: c.id
            for c in db.query(Campaign).filter(
                Campaign.client_id == client_record.id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        }
        if not campaign_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.id,
                segments.date,
                segments.ad_network_type,
                metrics.clicks,
                metrics.impressions,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.advertising_channel_type = 'PERFORMANCE_MAX'
              AND campaign.status != 'REMOVED'
        """

        count = 0
        try:
            response = ga_service.search(customer_id=normalized, query=query)
            for row in response:
                gcid = str(row.campaign.id)
                local_campaign_id = campaign_map.get(gcid)
                if not local_campaign_id:
                    continue

                row_date = date.fromisoformat(row.segments.date) if isinstance(row.segments.date, str) else row.segments.date
                network = row.segments.ad_network_type.name if hasattr(row.segments.ad_network_type, 'name') else str(row.segments.ad_network_type)

                existing = db.query(MetricSegmented).filter(
                    MetricSegmented.campaign_id == local_campaign_id,
                    MetricSegmented.date == row_date,
                    MetricSegmented.ad_network_type == network,
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city.is_(None),
                    MetricSegmented.hour_of_day.is_(None),
                    MetricSegmented.age_range.is_(None),
                    MetricSegmented.gender.is_(None),
                ).first()

                metrics_data = {
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "conversions": float(row.metrics.conversions),
                    "conversion_value_micros": int(row.metrics.conversions_value * 1_000_000) if row.metrics.conversions_value else 0,
                    "cost_micros": row.metrics.cost_micros,
                }

                if existing:
                    for k, v in metrics_data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(
                        campaign_id=local_campaign_id,
                        date=row_date,
                        ad_network_type=network,
                        **metrics_data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} PMax channel-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing PMax channel metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Asset Group Structure Sync
    # -----------------------------------------------------------------------

    def sync_asset_groups(self, db: Session, customer_id: str) -> int:
        """Sync PMax asset group structure into AssetGroup model."""
        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        campaign_map = {
            c.google_campaign_id: c.id
            for c in db.query(Campaign).filter(
                Campaign.client_id == client_record.id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        }
        if not campaign_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                asset_group.id,
                asset_group.name,
                asset_group.status,
                asset_group.ad_strength,
                asset_group.final_urls,
                asset_group.final_mobile_urls,
                asset_group.path1,
                asset_group.path2,
                campaign.id
            FROM asset_group
            WHERE campaign.status != 'REMOVED'
              AND asset_group.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                gcid = str(row.campaign.id)
                local_campaign_id = campaign_map.get(gcid)
                if not local_campaign_id:
                    continue

                google_ag_id = str(row.asset_group.id)
                ag_name = row.asset_group.name
                ag_status = row.asset_group.status.name if hasattr(row.asset_group.status, 'name') else str(row.asset_group.status)
                ad_strength = row.asset_group.ad_strength.name if hasattr(row.asset_group.ad_strength, 'name') else str(row.asset_group.ad_strength)

                final_url = row.asset_group.final_urls[0] if row.asset_group.final_urls else None
                final_mobile_url = row.asset_group.final_mobile_urls[0] if row.asset_group.final_mobile_urls else None
                path1 = row.asset_group.path1 or None
                path2 = row.asset_group.path2 or None

                existing = db.query(AssetGroup).filter(
                    AssetGroup.campaign_id == local_campaign_id,
                    AssetGroup.google_asset_group_id == google_ag_id,
                ).first()

                data = {
                    "name": ag_name,
                    "status": ag_status,
                    "ad_strength": ad_strength,
                    "final_url": final_url,
                    "final_mobile_url": final_mobile_url,
                    "path1": path1,
                    "path2": path2,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(AssetGroup(
                        campaign_id=local_campaign_id,
                        google_asset_group_id=google_ag_id,
                        **data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} asset groups")
            return count

        except Exception as e:
            logger.error(f"Error syncing asset groups: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Asset Group Daily Metrics Sync
    # -----------------------------------------------------------------------

    def sync_asset_group_daily(self, db: Session, customer_id: str,
                                date_from: date = None, date_to: date = None) -> int:
        """Sync daily metrics for PMax asset groups into AssetGroupDaily."""
        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        # Build asset_group_map: google_asset_group_id -> local id
        pmax_campaign_ids = [
            c.id for c in db.query(Campaign).filter(
                Campaign.client_id == client_record.id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        ]
        if not pmax_campaign_ids:
            return 0

        asset_group_map = {
            ag.google_asset_group_id: ag.id
            for ag in db.query(AssetGroup).filter(
                AssetGroup.campaign_id.in_(pmax_campaign_ids),
            ).all()
        }
        if not asset_group_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                asset_group.id,
                campaign.id,
                segments.date,
                metrics.clicks,
                metrics.impressions,
                metrics.ctr,
                metrics.conversions,
                metrics.conversions_value,
                metrics.cost_micros,
                metrics.average_cpc
            FROM asset_group
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
              AND asset_group.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                google_ag_id = str(row.asset_group.id)
                local_ag_id = asset_group_map.get(google_ag_id)
                if not local_ag_id:
                    continue

                metric_date = date.fromisoformat(row.segments.date)
                m = row.metrics
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0

                existing = db.query(AssetGroupDaily).filter(
                    AssetGroupDaily.asset_group_id == local_ag_id,
                    AssetGroupDaily.date == metric_date,
                ).first()

                data = {
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(conv_value * 1_000_000),
                    "cost_micros": m.cost_micros,
                    "avg_cpc_micros": int(m.average_cpc) if m.average_cpc else 0,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(AssetGroupDaily(
                        asset_group_id=local_ag_id,
                        date=metric_date,
                        **data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} asset group daily metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing asset group daily metrics: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Asset Group Assets Sync
    # -----------------------------------------------------------------------

    def sync_asset_group_assets(self, db: Session, customer_id: str) -> int:
        """Sync assets linked to PMax asset groups into AssetGroupAsset."""
        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        # Build asset_group_map: google_asset_group_id -> local id
        pmax_campaign_ids = [
            c.id for c in db.query(Campaign).filter(
                Campaign.client_id == client_record.id,
                Campaign.campaign_type == "PERFORMANCE_MAX",
            ).all()
        ]
        if not pmax_campaign_ids:
            return 0

        asset_group_map = {
            ag.google_asset_group_id: ag.id
            for ag in db.query(AssetGroup).filter(
                AssetGroup.campaign_id.in_(pmax_campaign_ids),
            ).all()
        }
        if not asset_group_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        # Google Ads API v23 removed asset_group_asset.performance_label.
        # Use asset_group_asset.status instead (ENABLED / PAUSED / REMOVED).
        query = """
            SELECT
                asset_group.id,
                campaign.id,
                asset_group_asset.asset,
                asset_group_asset.field_type,
                asset_group_asset.status,
                asset.id,
                asset.type,
                asset.text_asset.text
            FROM asset_group_asset
            WHERE campaign.status != 'REMOVED'
              AND asset_group.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                google_ag_id = str(row.asset_group.id)
                local_ag_id = asset_group_map.get(google_ag_id)
                if not local_ag_id:
                    continue

                google_asset_id = str(row.asset.id)
                asset_type = row.asset.type.name if hasattr(row.asset.type, 'name') else str(row.asset.type)
                field_type = row.asset_group_asset.field_type.name if hasattr(row.asset_group_asset.field_type, 'name') else str(row.asset_group_asset.field_type)
                # performance_label was removed in v23 — store status as proxy so downstream UI can still show state
                perf_label = row.asset_group_asset.status.name if hasattr(row.asset_group_asset.status, 'name') else str(row.asset_group_asset.status)

                # text_asset.text may not exist for non-text assets
                text_content = None
                try:
                    text_content = row.asset.text_asset.text or None
                except (AttributeError, TypeError):
                    pass

                existing = db.query(AssetGroupAsset).filter(
                    AssetGroupAsset.asset_group_id == local_ag_id,
                    AssetGroupAsset.google_asset_id == google_asset_id,
                    AssetGroupAsset.field_type == field_type,
                ).first()

                data = {
                    "asset_type": asset_type,
                    "text_content": text_content,
                    "performance_label": perf_label,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(AssetGroupAsset(
                        asset_group_id=local_ag_id,
                        google_asset_id=google_asset_id,
                        field_type=field_type,
                        **data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} asset group assets")
            return count

        except Exception as e:
            logger.error(f"Error syncing asset group assets: {e}")
            db.rollback()
            raise

    # -----------------------------------------------------------------------
    # Campaign Assets (Extensions) Sync
    # -----------------------------------------------------------------------

    def sync_campaign_assets(self, db: Session, customer_id: str) -> int:
        """Sync campaign-level assets (sitelinks, callouts, etc.) into CampaignAsset."""
        if not self.is_connected:
            return 0

        normalized = self.normalize_customer_id(customer_id)
        client_record = self._find_client_record(db, normalized)
        if not client_record:
            return 0

        campaign_map = {
            c.google_campaign_id: c.id
            for c in db.query(Campaign).filter(
                Campaign.client_id == client_record.id,
            ).all()
        }
        if not campaign_map:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        # Google Ads API v23: campaign.status must be in SELECT when used in WHERE.
        # asset.sitelink_asset.final_urls is not a queryable field; drop it (sitelink
        # URLs are not needed in UI — link_text is the displayed label).
        query = """
            SELECT
                campaign.id,
                campaign.status,
                asset.id,
                asset.type,
                asset.name,
                campaign_asset.status,
                campaign_asset.source,
                asset.sitelink_asset.link_text,
                asset.sitelink_asset.description1,
                asset.sitelink_asset.description2,
                asset.callout_asset.callout_text,
                asset.structured_snippet_asset.header,
                asset.structured_snippet_asset.values,
                asset.call_asset.phone_number,
                asset.call_asset.country_code,
                asset.promotion_asset.promotion_target,
                asset.promotion_asset.discount_modifier,
                asset.price_asset.type,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions
            FROM campaign_asset
            WHERE campaign.status != 'REMOVED'
        """

        try:
            import json as _json
            response = ga_service.search(customer_id=normalized, query=query)
            count = 0
            for row in response:
                gcid = str(row.campaign.id)
                local_campaign_id = campaign_map.get(gcid)
                if not local_campaign_id:
                    continue

                google_asset_id = str(row.asset.id)
                asset_type = row.asset.type.name if hasattr(row.asset.type, 'name') else str(row.asset.type)
                asset_status = row.campaign_asset.status.name if hasattr(row.campaign_asset.status, 'name') else str(row.campaign_asset.status)
                perf_label = None
                source_val = row.campaign_asset.source.name if hasattr(row.campaign_asset.source, 'name') else str(row.campaign_asset.source)

                # Extract asset_name and structured detail from type-specific fields
                asset_name = row.asset.name or None
                detail_dict = {}
                try:
                    sl = row.asset.sitelink_asset
                    if sl.link_text:
                        asset_name = sl.link_text
                        detail_dict = {
                            "link_text": sl.link_text,
                            "description1": sl.description1 or "",
                            "description2": sl.description2 or "",
                        }
                except (AttributeError, TypeError):
                    pass
                try:
                    co = row.asset.callout_asset
                    if co.callout_text:
                        asset_name = co.callout_text
                        detail_dict = {"callout_text": co.callout_text}
                except (AttributeError, TypeError):
                    pass
                try:
                    ss = row.asset.structured_snippet_asset
                    if ss.header:
                        asset_name = ss.header
                        detail_dict = {
                            "header": ss.header,
                            "values": list(ss.values) if ss.values else [],
                        }
                except (AttributeError, TypeError):
                    pass
                try:
                    ca = row.asset.call_asset
                    if ca.phone_number:
                        asset_name = ca.phone_number
                        detail_dict = {
                            "phone_number": ca.phone_number,
                            "country_code": ca.country_code or "",
                        }
                except (AttributeError, TypeError):
                    pass
                try:
                    pr = row.asset.promotion_asset
                    if pr.promotion_target:
                        asset_name = pr.promotion_target
                        detail_dict = {
                            "promotion_target": pr.promotion_target,
                            "discount_modifier": pr.discount_modifier.name if hasattr(pr.discount_modifier, 'name') else str(pr.discount_modifier),
                        }
                except (AttributeError, TypeError):
                    pass

                asset_detail = _json.dumps(detail_dict, ensure_ascii=False) if detail_dict else None

                m = row.metrics

                existing = db.query(CampaignAsset).filter(
                    CampaignAsset.campaign_id == local_campaign_id,
                    CampaignAsset.google_asset_id == google_asset_id,
                    CampaignAsset.asset_type == asset_type,
                ).first()

                data = {
                    "asset_name": asset_name,
                    "asset_detail": asset_detail,
                    "status": asset_status,
                    "performance_label": perf_label,
                    "source": source_val,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "cost_micros": m.cost_micros,
                    "conversions": float(m.conversions),
                    "ctr": m.ctr * 100,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(CampaignAsset(
                        campaign_id=local_campaign_id,
                        google_asset_id=google_asset_id,
                        asset_type=asset_type,
                        **data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} campaign assets")
            return count

        except Exception as e:
            logger.error(f"Error syncing campaign assets: {e}")
            db.rollback()
            raise

    # ------------------------------------------------------------------
    # GAP 3C: Asset Group Signals (search themes + audience signals)
    # ------------------------------------------------------------------
    def sync_asset_group_signals(self, db: Session, customer_id: str) -> int:
        """Sync asset group signals (search themes and audience segments) for PMax campaigns."""
        from app.models.asset_group_signal import AssetGroupSignal
        from app.models.asset_group import AssetGroup

        if not self.is_connected:
            return 0

        try:
            query = """
                SELECT
                    asset_group.id,
                    asset_group_signal.resource_name,
                    asset_group_signal.audience.audience,
                    asset_group_signal.search_theme.text
                FROM asset_group_signal
                WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
            """

            response = self._execute_query(customer_id, query)

            ag_ids = {
                r.asset_group.id for r in response
            }
            local_ags = {
                ag.google_asset_group_id: ag.id
                for ag in db.query(AssetGroup).filter(
                    AssetGroup.google_asset_group_id.in_([str(a) for a in ag_ids])
                ).all()
            } if ag_ids else {}

            count = 0
            for row in response:
                ag_gid = str(row.asset_group.id)
                local_ag_id = local_ags.get(ag_gid)
                if not local_ag_id:
                    continue

                resource_name = row.asset_group_signal.resource_name

                # Parse signal type from audience / search_theme fields
                audience_rn = ""
                audience_name = ""
                signal_type = "SEARCH_THEME"
                search_theme_text = ""

                try:
                    theme_text = row.asset_group_signal.search_theme.text or ""
                    if theme_text:
                        signal_type = "SEARCH_THEME"
                        search_theme_text = theme_text
                    else:
                        audience_rn = row.asset_group_signal.audience.audience or ""
                        if audience_rn:
                            signal_type = "AUDIENCE"
                            audience_name = audience_rn.split("/")[-1] if audience_rn else ""
                except Exception:
                    pass

                existing = db.query(AssetGroupSignal).filter(
                    AssetGroupSignal.asset_group_id == local_ag_id,
                    AssetGroupSignal.signal_type == signal_type,
                    AssetGroupSignal.search_theme_text == search_theme_text,
                    AssetGroupSignal.audience_resource_name == audience_rn,
                ).first()

                if not existing:
                    db.add(AssetGroupSignal(
                        asset_group_id=local_ag_id,
                        signal_type=signal_type,
                        search_theme_text=search_theme_text,
                        audience_resource_name=audience_rn,
                        audience_name=audience_name,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} asset group signals")
            return count

        except Exception as e:
            logger.error(f"Error syncing asset group signals: {e}")
            db.rollback()
            raise

    # ------------------------------------------------------------------
    # GAP 4B: Campaign Audience Metrics
    # ------------------------------------------------------------------
    def sync_campaign_audiences(self, db: Session, customer_id: str,
                                date_from: date = None, date_to: date = None) -> int:
        """Sync campaign audience metrics from campaign_audience_view."""
        from app.models.campaign_audience import CampaignAudienceMetric

        if not self.is_connected:
            raise RuntimeError("Google Ads API not connected")

        if not date_from:
            date_from = date.today() - timedelta(days=90)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        try:
            query = f"""
                SELECT
                    campaign.id,
                    campaign_criterion.resource_name,
                    campaign_criterion.type,
                    campaign_criterion.user_list.user_list,
                    segments.date,
                    metrics.clicks,
                    metrics.impressions,
                    metrics.ctr,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.cost_micros,
                    metrics.average_cpc
                FROM campaign_audience_view
                WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
            """

            response = self._execute_query(customer_id, query)

            campaign_ids = {r.campaign.id for r in response}
            local_campaigns = {
                c.google_campaign_id: c.id
                for c in db.query(Campaign).filter(
                    Campaign.google_campaign_id.in_([str(cid) for cid in campaign_ids])
                ).all()
            } if campaign_ids else {}

            count = 0
            for row in response:
                camp_gid = str(row.campaign.id)
                local_campaign_id = local_campaigns.get(camp_gid)
                if not local_campaign_id:
                    continue

                m = row.metrics
                seg_date = row.segments.date
                resource_name = row.campaign_criterion.resource_name
                audience_type_raw = str(row.campaign_criterion.type).split(".")[-1]

                # Map criterion type to audience type
                audience_type_map = {
                    "USER_LIST": "REMARKETING",
                    "USER_INTEREST": "AFFINITY",
                    "CUSTOM_AFFINITY": "CUSTOM",
                    "CUSTOM_INTENT": "IN_MARKET",
                    "CUSTOM_AUDIENCE": "CUSTOM",
                }
                audience_type = audience_type_map.get(audience_type_raw, "OTHER")

                # Try to get audience name from user_list
                audience_name = ""
                try:
                    ul = row.campaign_criterion.user_list.user_list
                    audience_name = ul.split("/")[-1] if ul else resource_name.split("/")[-1]
                except Exception:
                    audience_name = resource_name.split("/")[-1] if resource_name else "Unknown"

                existing = db.query(CampaignAudienceMetric).filter(
                    CampaignAudienceMetric.campaign_id == local_campaign_id,
                    CampaignAudienceMetric.audience_resource_name == resource_name,
                    CampaignAudienceMetric.date == seg_date,
                ).first()

                data = {
                    "audience_name": audience_name,
                    "audience_type": audience_type,
                    "clicks": m.clicks,
                    "impressions": m.impressions,
                    "ctr": m.ctr * 100,
                    "conversions": float(m.conversions),
                    "conversion_value_micros": int(m.conversions_value * 1_000_000),
                    "cost_micros": m.cost_micros,
                    "avg_cpc_micros": m.average_cpc,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(CampaignAudienceMetric(
                        campaign_id=local_campaign_id,
                        audience_resource_name=resource_name,
                        date=seg_date,
                        **data,
                    ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} campaign audience metrics")
            return count

        except Exception as e:
            logger.error(f"Error syncing campaign audiences: {e}")
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

























