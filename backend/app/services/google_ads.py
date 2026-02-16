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
    Client, Campaign, AdGroup, Keyword, SearchTerm, Ad, MetricDaily
)
from app.services.cache import get_cached, set_cached

# Optional: Import google-ads client (only if credentials are configured)
try:
    from google.ads.googleads.client import GoogleAdsClient
    GOOGLE_ADS_AVAILABLE = True
except ImportError:
    GOOGLE_ADS_AVAILABLE = False
    logger.warning("google-ads package not installed. API sync will be unavailable.")


class GoogleAdsService:
    """Wrapper around Google Ads API for data fetching and mutations."""

    def __init__(self):
        self.client = None
        if GOOGLE_ADS_AVAILABLE and settings.google_ads_developer_token:
            try:
                self.client = GoogleAdsClient.load_from_dict({
                    "developer_token": settings.google_ads_developer_token,
                    "client_id": settings.google_ads_client_id,
                    "client_secret": settings.google_ads_client_secret,
                    "login_customer_id": settings.google_ads_login_customer_id,
                    "use_proto_plus": True,
                })
                logger.info("Google Ads API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Ads client: {e}")
                self.client = None

    @property
    def is_connected(self) -> bool:
        return self.client is not None

    # -----------------------------------------------------------------------
    # Campaign Sync
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
                    "budget_amount": budget.amount_micros / 1_000_000 if budget.amount_micros else None,
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
    # Daily Metrics Sync
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
                metrics.conversions_from_interactions_rate,
                metrics.cost_micros,
                metrics.cost_per_conversion,
                metrics.average_cpc
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

                campaign = db.query(Campaign).filter(
                    Campaign.client_id == client_record.id,
                    Campaign.google_campaign_id == campaign_id_google,
                ).first()
                if not campaign:
                    continue

                cost = row.metrics.cost_micros / 1_000_000
                conversions = row.metrics.conversions
                roas = conversions / cost if cost > 0 else 0

                existing = db.query(MetricDaily).filter(
                    MetricDaily.campaign_id == campaign.id,
                    MetricDaily.date == metric_date,
                ).first()

                data = {
                    "campaign_id": campaign.id,
                    "date": metric_date,
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "ctr": row.metrics.ctr * 100,  # API returns as fraction
                    "conversions": conversions,
                    "conversion_rate": row.metrics.conversions_from_interactions_rate * 100,
                    "cost": cost,
                    "cost_per_conversion": row.metrics.cost_per_conversion / 1_000_000,
                    "roas": roas,
                    "avg_cpc": row.metrics.average_cpc / 1_000_000,
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
    # Search Terms Sync
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
                metrics.cost_micros,
                metrics.conversions_from_interactions_rate,
                metrics.cost_per_conversion
            FROM search_term_view
            WHERE segments.date BETWEEN '{date_from}' AND '{date_to}'
        """

        try:
            response = ga_service.search(customer_id=customer_id, query=query)
            count = 0
            for row in response:
                ad_group_google_id = str(row.ad_group.id)

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

                cost = row.metrics.cost_micros / 1_000_000

                db.add(SearchTerm(
                    ad_group_id=ad_group.id,
                    text=row.search_term_view.search_term,
                    keyword_text=row.segments.keyword.info.text if row.segments.keyword.info.text else None,
                    match_type=row.segments.keyword.info.match_type.name if row.segments.keyword.info.match_type else None,
                    clicks=row.metrics.clicks,
                    impressions=row.metrics.impressions,
                    cost=cost,
                    conversions=row.metrics.conversions,
                    ctr=row.metrics.ctr * 100,
                    conversion_rate=row.metrics.conversions_from_interactions_rate * 100,
                    cost_per_conversion=row.metrics.cost_per_conversion / 1_000_000 if row.metrics.cost_per_conversion else 0,
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


    def apply_action(self, db: Session, action_type: str, entity_id: int, params: dict = None):
        """
        Execute an action on a Google Ads entity.
        MVP: Updates local DB and mocks the API call.
        """
        from app.models import Keyword, Ad, SearchTerm, AdGroup, Campaign

        log_details = f"Action: {action_type}, Entity: {entity_id}, Params: {params}"
        logger.info(f"🚀 EXECUTING: {log_details}")

        try:
            if action_type == "PAUSE_KEYWORD":
                kw = db.query(Keyword).get(entity_id)
                if kw:
                    kw.status = "PAUSED"
                    # self.google_ads_client.pause_keyword(kw.google_keyword_id) # MOCKED
            
            elif action_type == "PAUSE_AD":
                ad = db.query(Ad).get(entity_id)
                if ad:
                    ad.status = "PAUSED"
                    # self.google_ads_client.pause_ad(ad.google_ad_id) # MOCKED

            elif action_type == "ADD_NEGATIVE_KEYWORD":
                # params: {"text": "...", "match_type": "...", "campaign_id": ...}
                # For MVP, just log it, as we don't have a NegativeKeyword model yet
                pass

            elif action_type == "SET_KEYWORD_BID":
                # params: {"amount": 1.50}
                kw = db.query(Keyword).get(entity_id)
                if kw and params and "amount" in params:
                    kw.cpc_bid = float(params["amount"])
                    # self.google_ads_client.set_keyword_bid(kw.google_keyword_id, amount) # MOCKED

            elif action_type == "ADD_KEYWORD":
                # params: {"text": "...", "match_type": "...", "ad_group_id": ...}
                ad_group_id = params.get("ad_group_id")
                text = params.get("text")
                match_type = params.get("match_type", "BROAD")
                
                if ad_group_id and text:
                    # Check if already exists
                    existing = db.query(Keyword).filter(
                        Keyword.ad_group_id == ad_group_id,
                        Keyword.text == text
                    ).first()
                    
                    if not existing:
                        from datetime import datetime
                        new_kw = Keyword(
                            ad_group_id=ad_group_id,
                            text=text,
                            match_type=match_type,
                            status="ENABLED",
                            google_keyword_id=f"new-{int(datetime.utcnow().timestamp())}", # Mock ID
                            clicks=0, impressions=0, cost=0, conversions=0
                        )
                        db.add(new_kw)

            db.commit()
            return {"status": "success", "message": f"Successfully executed {action_type}"}

        except Exception as e:
            db.rollback()
            logger.error(f"❌ ACTION FAILED: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
google_ads_service = GoogleAdsService()
