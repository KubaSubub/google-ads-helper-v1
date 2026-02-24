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
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily, MetricSegmented
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
        """Attempt to initialize GoogleAdsClient using keyring refresh_token."""
        if not GOOGLE_ADS_AVAILABLE:
            return

        refresh_token = CredentialsService.get(CredentialsService.REFRESH_TOKEN)
        if not refresh_token:
            logger.info("No refresh_token in keyring — user must complete OAuth first")
            return

        if not settings.google_ads_developer_token:
            logger.warning("No developer_token in .env")
            return

        try:
            self.client = GoogleAdsClient.load_from_dict({
                "developer_token": settings.google_ads_developer_token,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "refresh_token": refresh_token,
                "login_customer_id": settings.google_ads_login_customer_id,
                "use_proto_plus": True,
            })
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
    # Daily Metrics Sync (expanded with IS, extended conv, top %)
    # -----------------------------------------------------------------------

    def sync_daily_metrics(
        self, db: Session, customer_id: str,
        date_from: date = None, date_to: date = None
    ) -> int:
        """Fetch daily campaign metrics and upsert into local DB."""
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
        query = f"""
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
                metrics.cost_per_conversion,
                metrics.average_cpc,
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
                metrics.all_conversions,
                metrics.all_conversions_value,
                metrics.cross_device_conversions,
                metrics.value_per_conversion,
                metrics.conversions_value_per_cost,
                metrics.absolute_top_impression_percentage,
                metrics.top_impression_percentage
            FROM campaign
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
              AND campaign.status != 'REMOVED'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
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
                roas = conv_value / cost_usd if cost_usd > 0 else 0  # Real ROAS = revenue / cost

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
                    # Impression Share (daily)
                    "search_impression_share": _safe_is(m.search_impression_share),
                    "search_top_impression_share": _safe_is(m.search_top_impression_share),
                    "search_abs_top_impression_share": _safe_is(m.search_absolute_top_impression_share),
                    "search_budget_lost_is": _safe_is(m.search_budget_lost_impression_share),
                    "search_budget_lost_top_is": _safe_is(m.search_budget_lost_top_impression_share),
                    "search_budget_lost_abs_top_is": _safe_is(m.search_budget_lost_absolute_top_impression_share),
                    "search_rank_lost_is": _safe_is(m.search_rank_lost_impression_share),
                    "search_rank_lost_top_is": _safe_is(m.search_rank_lost_top_impression_share),
                    "search_rank_lost_abs_top_is": _safe_is(m.search_rank_lost_absolute_top_impression_share),
                    "search_click_share": _safe_is(m.search_click_share),
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
                    db.add(MetricDaily(**data))
                count += 1

            db.commit()
            logger.info(f"Synced {count} daily metric rows for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing daily metrics: {e}")
            db.rollback()
            return 0

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

                conv_value = float(m.conversions_value) if m.conversions_value else 0.0
                db.add(SearchTerm(
                    ad_group_id=ad_group.id,
                    text=row.search_term_view.search_term,
                    keyword_text=row.segments.keyword.info.text if row.segments.keyword.info.text else None,
                    match_type=row.segments.keyword.info.match_type.name if row.segments.keyword.info.match_type else None,
                    clicks=m.clicks,
                    impressions=m.impressions,
                    cost_micros=m.cost_micros,
                    conversions=float(m.conversions),
                    conversion_value_micros=int(conv_value * 1_000_000),
                    ctr=int(m.ctr * 1_000_000),
                    conversion_rate=int(m.conversions_from_interactions_rate * 1_000_000),
                    # Extended Conversions
                    all_conversions=_safe_float(m.all_conversions),
                    all_conversions_value_micros=int(float(m.all_conversions_value) * 1_000_000) if m.all_conversions_value else None,
                    cross_device_conversions=_safe_float(m.cross_device_conversions),
                    value_per_conversion_micros=int(float(m.value_per_conversion) * 1_000_000) if m.value_per_conversion else None,
                    conversions_value_per_cost=_safe_float(m.conversions_value_per_cost),
                    date_from=date_from,
                    date_to=date_to,
                ))
                count += 1

            db.commit()
            logger.info(f"Synced {count} search terms for customer {customer_id}")
            return count

        except Exception as e:
            logger.error(f"Error syncing search terms: {e}")
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


# Singleton instance
google_ads_service = GoogleAdsService()
