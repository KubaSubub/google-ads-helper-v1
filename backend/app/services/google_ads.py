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
from app.services.credentials_service import CredentialsService

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
    # Keywords Sync
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
                metrics.cost_micros,
                metrics.average_cpc
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

                clicks = row.metrics.clicks
                impressions = row.metrics.impressions
                conversions = int(row.metrics.conversions)
                cost_micros = row.metrics.cost_micros
                avg_cpc_micros = int(row.metrics.average_cpc) if row.metrics.average_cpc else 0
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
                    "ctr": int(row.metrics.ctr * 1_000_000),
                    "avg_cpc_micros": avg_cpc_micros,
                    "cpa_micros": cpa_micros,
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

                cost_micros = row.metrics.cost_micros
                conversions = int(row.metrics.conversions)
                cost_usd = cost_micros / 1_000_000 if cost_micros else 0
                roas = conversions / cost_usd if cost_usd > 0 else 0

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
                    "cost_micros": cost_micros,
                    "roas": roas,
                    "avg_cpc_micros": int(row.metrics.average_cpc) if row.metrics.average_cpc else 0,
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

                db.add(SearchTerm(
                    ad_group_id=ad_group.id,
                    text=row.search_term_view.search_term,
                    keyword_text=row.segments.keyword.info.text if row.segments.keyword.info.text else None,
                    match_type=row.segments.keyword.info.match_type.name if row.segments.keyword.info.match_type else None,
                    clicks=row.metrics.clicks,
                    impressions=row.metrics.impressions,
                    cost_micros=row.metrics.cost_micros,
                    conversions=row.metrics.conversions,
                    ctr=int(row.metrics.ctr * 1_000_000),
                    conversion_rate=int(row.metrics.conversions_from_interactions_rate * 1_000_000),
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
                    kw.bid_micros = int(float(params["amount"]) * 1_000_000)
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
                            clicks=0, impressions=0, cost_micros=0, conversions=0
                        )
                        db.add(new_kw)

            db.commit()
            return {"status": "success", "message": f"Successfully executed {action_type}"}

        except Exception as e:
            db.rollback()
            logger.error(f"❌ ACTION FAILED: {str(e)}")
            return {"status": "error", "message": str(e)}


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
