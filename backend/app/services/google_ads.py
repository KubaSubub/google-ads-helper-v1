"""
Google Ads API Service — handles authentication and data fetching.

This service wraps the official google-ads Python client and provides
methods to fetch campaigns, ad groups, keywords, search terms, and ads
from the Google Ads API.

IMPORTANT: You need a Google Ads API developer token and OAuth credentials.
See: https://developers.google.com/google-ads/api/docs/first-call/overview
"""

from datetime import date, timedelta
from loguru import logger
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily, MetricSegmented,
    ChangeEvent, ActionLog, KeywordDaily,
)
from app.services.cache import get_cached, set_cached
from app.services.credentials_service import CredentialsService

# Optional: Import google-ads client (only if credentials are configured)
try:
    from google.ads.googleads.client import GoogleAdsClient
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    logger.warning("google-ads package not installed. API sync will be unavailable.")


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
        """Attempt to initialize GoogleAdsClient.

        Credential priority:
          1. Windows Credential Manager (keyring) — set after OAuth callback
          2. .env / environment variables — dev fallback
        This allows the .exe to work without .env once the user completes OAuth.
        """
        if not GOOGLE_ADS_AVAILABLE:
            return

        refresh_token = CredentialsService.get(CredentialsService.REFRESH_TOKEN)
        if not refresh_token:
            logger.info("No refresh_token in keyring — user must complete OAuth first")
            return

        # Resolve each credential: keyring first, .env fallback
        developer_token = (
            CredentialsService.get(CredentialsService.DEVELOPER_TOKEN)
            or settings.google_ads_developer_token
        )
        client_id = (
            CredentialsService.get(CredentialsService.CLIENT_ID)
            or settings.google_ads_client_id
        )
        client_secret = (
            CredentialsService.get(CredentialsService.CLIENT_SECRET)
            or settings.google_ads_client_secret
        )

        if not developer_token:
            logger.warning("No developer_token found in keyring or .env")
            return

        login_customer_id = (
            CredentialsService.get("login_customer_id")
            or settings.google_ads_login_customer_id
        )

        try:
            config = {
                "developer_token": developer_token,
                "client_id": client_id,
                "client_secret": client_secret,
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
        """Re-init client (call after OAuth completion)."""
        self.client = None
        self._try_init()

    @property
    def is_connected(self) -> bool:
        if self.client is None:
            self._try_init()
        return self.client is not None

    # -----------------------------------------------------------------------
    # Campaign Sync (structural data only — no metrics)
    # -----------------------------------------------------------------------

    def sync_campaigns(self, db: Session, customer_id: str) -> int:
        """
        Fetch all campaigns from Google Ads API and upsert into local DB.
        Returns the number of campaigns synced.
        """
        if not self.is_connected:
            logger.warning("Google Ads API not connected — skipping campaign sync")
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
        if not client_record:
            logger.error(f"Client with customer_id={customer_id} not found in DB")
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign.advertising_channel_type,
                campaign_budget.amount_micros,
                campaign.start_date,
                campaign.end_date,
                campaign.bidding_strategy_type
            FROM campaign
            WHERE campaign.status != 'REMOVED'
            ORDER BY campaign.name
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                campaign = row.campaign
                budget = row.campaign_budget

                existing = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == str(campaign.id),
                ).first()

                data = {
                    "client_id": client_record.id,
                    "google_campaign_id": str(campaign.id),
                    "name": campaign.name,
                    "status": campaign.status.name,
                    "campaign_type": campaign.advertising_channel_type.name,
                    "budget_micros": budget.amount_micros if budget.amount_micros else 0,
                    "bidding_strategy": campaign.bidding_strategy_type.name if campaign.bidding_strategy_type else None,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(Campaign(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} campaigns for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing campaigns: {e}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Campaign Impression Share Sync (aggregated last 30 days)
    # -----------------------------------------------------------------------

    def sync_campaign_impression_share(self, db: Session, customer_id: str) -> int:
        """Fetch campaign-level impression share metrics (last 30d aggregate)."""
        if not self.is_connected:
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
            return 0

    # -----------------------------------------------------------------------
    # Ad Groups Sync
    # -----------------------------------------------------------------------

    def sync_ad_groups(self, db: Session, customer_id: str) -> int:
        """Fetch all ad groups from Google Ads API and upsert into local DB."""
        if not self.is_connected:
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                ag = row.ad_group
                campaign_google_id = str(row.campaign.id)

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_google_id,
                ).first()
                if not campaign:
                    continue

                existing = db.query(AdGroup).filter(
                    AdGroup.campaign_id == campaign.id,
                    AdGroup.google_ad_group_id == str(ag.id),
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "google_ad_group_id": str(ag.id),
                    "name": ag.name,
                    "status": ag.status.name,
                    "bid_micros": ag.cpc_bid_micros if ag.cpc_bid_micros else 0,
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(AdGroup(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} ad groups for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing ad groups: {e}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Keywords Sync (expanded with IS, QS historical, extended conv, top %)
    # -----------------------------------------------------------------------

    def sync_keywords(self, db: Session, customer_id: str) -> int:
        """Fetch all keywords from Google Ads API and upsert into local DB."""
        if not self.is_connected:
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
        if not client_record:
            return 0

        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
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
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                ad_group_google_id = str(row.ad_group.id)
                criterion = row.ad_group_criterion
                m = row.metrics

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

                existing = db.query(Keyword).filter(
                    Keyword.ad_group_id == ad_group.id,
                    Keyword.google_keyword_id == google_keyword_id,
                ).first()

                clicks = m.clicks
                impressions = m.impressions
                conversions = float(m.conversions)
                conv_value = float(m.conversions_value) if m.conversions_value else 0.0
                cost_micros = m.cost_micros
                avg_cpc_micros = int(m.average_cpc) if m.average_cpc else 0
                cpa_micros = int(cost_micros / conversions) if conversions > 0 else 0

                data = {
                    "ad_group_id": ad_group.id,
                    "google_keyword_id": google_keyword_id,
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
                    "ctr": int(m.ctr * 1_000_000),
                    "avg_cpc_micros": avg_cpc_micros,
                    "cpa_micros": cpa_micros,
                    # Impression Share (keyword-level, rank-based only)
                    "search_impression_share": _safe_is(m.search_impression_share),
                    "search_top_impression_share": _safe_is(m.search_top_impression_share),
                    "search_abs_top_impression_share": _safe_is(m.search_absolute_top_impression_share),
                    "search_rank_lost_is": _safe_is(m.search_rank_lost_impression_share),
                    "search_rank_lost_top_is": _safe_is(m.search_rank_lost_top_impression_share),
                    "search_rank_lost_abs_top_is": _safe_is(m.search_rank_lost_absolute_top_impression_share),
                    "search_exact_match_is": _safe_is(m.search_exact_match_impression_share),
                    # Historical Quality Score
                    "historical_quality_score": _qs_enum(m.historical_quality_score),
                    "historical_creative_quality": _qs_enum(m.historical_creative_quality_score),
                    "historical_landing_page_quality": _qs_enum(m.historical_landing_page_quality_score),
                    "historical_search_predicted_ctr": _qs_enum(m.historical_search_predicted_ctr),
                    # Extended Conversions
                    "all_conversions": _safe_float(m.all_conversions),
                    "all_conversions_value_micros": int(float(m.all_conversions_value) * 1_000_000) if m.all_conversions_value else None,
                    "cross_device_conversions": _safe_float(m.cross_device_conversions),
                    "value_per_conversion_micros": int(float(m.value_per_conversion) * 1_000_000) if m.value_per_conversion else None,
                    "conversions_value_per_cost": _safe_float(m.conversions_value_per_cost),
                    # Top Impression %
                    "abs_top_impression_pct": _safe_is(m.absolute_top_impression_percentage),
                    "top_impression_pct": _safe_is(m.top_impression_percentage),
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(Keyword(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} keywords for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing keywords: {e}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Keyword Daily Metrics Sync
    # -----------------------------------------------------------------------

    def sync_keyword_daily(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch daily keyword metrics and upsert into keywords_daily table."""
        if not self.is_connected:
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                ad_group.id,
                ad_group_criterion.criterion_id,
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
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                ad_group_google_id = str(row.ad_group.id)
                google_keyword_id = str(row.ad_group_criterion.criterion_id)
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
            return 0

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

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
            return 0

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

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
                    "ctr": int(m.ctr * 1_000_000),
                    "conversion_rate": int(m.conversions_from_interactions_rate * 1_000_000),
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
            return 0

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

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
                    "ctr": int(m.ctr * 1_000_000),
                    "conversion_rate": int(
                        (conv / m.clicks * 1_000_000) if m.clicks > 0 else 0
                    ),
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
            return 0

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

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
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
            return 0

    # -----------------------------------------------------------------------
    # Geo Segmented Metrics Sync
    # -----------------------------------------------------------------------

    def sync_geo_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch geo-segmented (city) daily campaign metrics."""
        if not self.is_connected:
            return 0

        client_record = db.query(Client).filter(
            Client.google_customer_id == customer_id
        ).first()
        if not client_record:
            return 0

        if not date_from:
            date_from = date.today() - timedelta(days=7)  # Shorter range to limit data volume
        if not date_to:
            date_to = date.today() - timedelta(days=1)

        ga_service = self.client.get_service("GoogleAdsService")
        query = f"""
            SELECT
                campaign.id,
                segments.date,
                segments.geo_target_city,
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
              AND metrics.impressions > 0
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                campaign_google_id = str(row.campaign.id)
                metric_date = date.fromisoformat(row.segments.date)
                # geo_target_city returns resource name like "geoTargetConstants/1023191"
                geo_city_raw = row.segments.geo_target_city
                # Extract a readable name — for now store resource name, resolve later
                geo_city = geo_city_raw if geo_city_raw else "Unknown"
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
                    MetricSegmented.device.is_(None),
                    MetricSegmented.geo_city == geo_city,
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
                    "search_impression_share": _safe_is(m.search_impression_share),
                }

                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    db.add(MetricSegmented(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} geo-segmented metric rows")
            return count

        except Exception as e:
            logger.error(f"Error syncing geo metrics: {e}")
            db.rollback()
            return 0

    # -----------------------------------------------------------------------
    # Apply Action (mutations)
    # -----------------------------------------------------------------------

    def apply_action(self, db: Session, action_type: str, entity_id: int, params: dict = None):
        """
        Execute an action on a Google Ads entity.

        Updates local DB immediately. If Google Ads API is connected,
        also sends the mutation to the API. Otherwise operates in local-only mode.
        """
        from app.models import Keyword, Ad, Campaign

        log_details = f"Action: {action_type}, Entity: {entity_id}, Params: {params}"
        logger.info(f"EXECUTING: {log_details}")

        try:
            if action_type == "PAUSE_KEYWORD":
                kw = db.query(Keyword).get(entity_id)
                if not kw:
                    return {"status": "error", "message": f"Keyword {entity_id} not found"}
                kw.status = "PAUSED"
                if self.is_connected:
                    self._mutate_keyword_status(kw.google_keyword_id, "PAUSED", db, kw)

            elif action_type == "ENABLE_KEYWORD":
                kw = db.query(Keyword).get(entity_id)
                if not kw:
                    return {"status": "error", "message": f"Keyword {entity_id} not found"}
                kw.status = "ENABLED"
                if self.is_connected:
                    self._mutate_keyword_status(kw.google_keyword_id, "ENABLED", db, kw)

            elif action_type == "PAUSE_AD":
                ad = db.query(Ad).get(entity_id)
                if not ad:
                    return {"status": "error", "message": f"Ad {entity_id} not found"}
                ad.status = "PAUSED"

            elif action_type in ("UPDATE_BID", "SET_KEYWORD_BID"):
                kw = db.query(Keyword).get(entity_id)
                if not kw:
                    return {"status": "error", "message": f"Keyword {entity_id} not found"}
                if params and "amount" in params:
                    kw.bid_micros = int(float(params["amount"]) * 1_000_000)
                    if self.is_connected:
                        self._mutate_keyword_bid(kw, db)

            elif action_type == "ADD_NEGATIVE":
                # Negative keywords need a dedicated model in the future.
                # For now, log intent and mark as executed.
                logger.info(f"ADD_NEGATIVE logged: text={params.get('text')}, campaign={params.get('campaign_id')}")

            elif action_type == "ADD_KEYWORD":
                ad_group_id = params.get("ad_group_id") if params else None
                text = params.get("text") if params else None
                match_type = params.get("match_type", "EXACT") if params else "EXACT"

                if not ad_group_id or not text:
                    return {"status": "error", "message": "Missing ad_group_id or text"}

                existing = db.query(Keyword).filter(
                    Keyword.ad_group_id == ad_group_id,
                    Keyword.text == text,
                ).first()

                if not existing:
                    from datetime import datetime
                    new_kw = Keyword(
                        ad_group_id=ad_group_id,
                        text=text,
                        match_type=match_type,
                        status="ENABLED",
                        google_keyword_id=f"local-{int(datetime.utcnow().timestamp())}",
                        clicks=0, impressions=0, cost_micros=0, conversions=0.0,
                    )
                    db.add(new_kw)

            elif action_type == "INCREASE_BUDGET":
                campaign = db.query(Campaign).get(entity_id)
                if not campaign:
                    return {"status": "error", "message": f"Campaign {entity_id} not found"}
                if params and "amount" in params:
                    campaign.budget_micros = int(float(params["amount"]) * 1_000_000)

            else:
                return {"status": "error", "message": f"Unknown action_type: {action_type}"}

            db.commit()
            return {"status": "success", "message": f"Executed {action_type}"}

        except Exception as e:
            db.rollback()
            logger.error(f"ACTION FAILED: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _mutate_keyword_status(self, google_keyword_id: str, new_status: str, db: Session, kw):
        """Send keyword status mutation to Google Ads API."""
        if not self.client or not google_keyword_id:
            return
        try:
            from app.models.ad_group import AdGroup
            from app.models.campaign import Campaign

            ag = db.query(AdGroup).get(kw.ad_group_id)
            if not ag:
                return
            campaign = db.query(Campaign).get(ag.campaign_id)
            if not campaign:
                return
            client_record = db.query(Client).get(campaign.client_id)
            if not client_record:
                return

            customer_id = client_record.google_customer_id.replace("-", "")
            service = self.client.get_service("AdGroupCriterionService")
            operation = self.client.get_type("AdGroupCriterionOperation")
            criterion = operation.update
            criterion.resource_name = service.ad_group_criterion_path(
                customer_id, str(ag.google_ad_group_id), google_keyword_id
            )
            status_enum = self.client.enums.AdGroupCriterionStatusEnum
            criterion.status = getattr(status_enum, new_status)

            field_mask = self.client.get_type("FieldMask")
            field_mask.paths.append("status")
            operation.update_mask.CopyFrom(field_mask)

            service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=[operation]
            )
            logger.info(f"Google Ads API: keyword {google_keyword_id} -> {new_status}")
        except Exception as e:
            logger.warning(f"Google Ads API mutation failed (local DB updated): {e}")

    def _mutate_keyword_bid(self, kw, db: Session):
        """Send keyword bid mutation to Google Ads API."""
        if not self.client or not kw.google_keyword_id:
            return
        try:
            from app.models.ad_group import AdGroup
            from app.models.campaign import Campaign

            ag = db.query(AdGroup).get(kw.ad_group_id)
            if not ag:
                return
            campaign = db.query(Campaign).get(ag.campaign_id)
            if not campaign:
                return
            client_record = db.query(Client).get(campaign.client_id)
            if not client_record:
                return

            customer_id = client_record.google_customer_id.replace("-", "")
            service = self.client.get_service("AdGroupCriterionService")
            operation = self.client.get_type("AdGroupCriterionOperation")
            criterion = operation.update
            criterion.resource_name = service.ad_group_criterion_path(
                customer_id, str(ag.google_ad_group_id), kw.google_keyword_id
            )
            criterion.cpc_bid_micros = kw.bid_micros

            field_mask = self.client.get_type("FieldMask")
            field_mask.paths.append("cpc_bid_micros")
            operation.update_mask.CopyFrom(field_mask)

            service.mutate_ad_group_criteria(
                customer_id=customer_id, operations=[operation]
            )
            logger.info(f"Google Ads API: keyword {kw.google_keyword_id} bid -> {kw.bid_micros}")
        except Exception as e:
            logger.warning(f"Google Ads API bid mutation failed (local DB updated): {e}")


    # -----------------------------------------------------------------------
    # Discover Accounts (MCC → list of client accounts)
    # -----------------------------------------------------------------------

    def discover_accounts(self) -> list[dict]:
        """
        Fetch client accounts accessible from the MCC (login_customer_id).
        Uses customer_client resource queried through the MCC.
        Returns list of dicts: [{customer_id, name}, ...]
        """
        if not self.is_connected:
            logger.warning("Google Ads API not connected — cannot discover accounts")
            return []

        mcc_id = settings.google_ads_login_customer_id
        if not mcc_id:
            logger.warning("No login_customer_id (MCC) configured")
            return []

        ga_service = self.client.get_service("GoogleAdsService")

        try:
            # Query customer_client through the MCC to find all sub-accounts
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
                # Skip the MCC itself (manager accounts)
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
            return []

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

        days = min(days, 30)  # API hard limit
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

                    event = ChangeEvent(
                        client_id=client_id,
                        resource_name=res_name,
                        change_date_time=ce.change_date_time,
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
                    db.add(event)
                    page_count += 1
                    last_timestamp = ce.change_date_time

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
            return 0


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
