# MASTER IMPLEMENTATION BLUEPRINT v2.0
## Google Ads Helper — Source of Truth for AI Developer

**Version:** 2.0  
**Status:** REQUIRED reading before writing ANY code  
**Refers to:** PRD_Core.md v1.0 + Technical_Spec.md v1.0  
**Rule:** If something is not specified here → ask PM. Do NOT improvise.

---

# ⚠️ CRITICAL RULES FOR AI DEVELOPER

1. **File placement:** Create files EXACTLY in the locations shown in Section 1. Zero improvisation.
2. **Import direction:** Only import downward in the layer hierarchy (Section 2). Never circular imports.
3. **Micros conversion:** ALL cost/bid values from Google Ads API are in micros (divide by 1,000,000). Convert ONLY in Pydantic schemas for frontend display. Store micros in DB.
4. **Circuit breaker:** EVERY write to Google Ads API MUST pass through `validate_action()`. No exceptions.
5. **Credentials:** NEVER store tokens in SQLite, .env files, or logs. ONLY Windows Credential Manager via keyring.
6. **Error handling:** NEVER let exceptions crash silently. Always log + return meaningful error to frontend.

---

# SECTION 1: FILE TREE STRUCTURE (STRICT)

```
google-ads-helper/
├── main.py                              # PyWebView entry point and server launcher
├── requirements.txt                     # ALL Python dependencies (pinned versions)
├── .env.example                         # Template, NO secrets, only key names
├── .gitignore                           # Must include: *.db, logs/, .env, __pycache__/
│
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py                      # FastAPI app instance + router registration
│       ├── config.py                    # Settings via pydantic-settings (reads .env)
│       ├── database.py                  # SQLAlchemy engine + SessionLocal + Base
│       │
│       ├── models/                      # Layer 3: SQLAlchemy ORM models
│       │   ├── __init__.py              # Exports all models for Alembic
│       │   ├── client.py
│       │   ├── campaign.py
│       │   ├── keyword.py
│       │   ├── search_term.py
│       │   ├── recommendation.py
│       │   ├── action_log.py
│       │   └── alert.py
│       │
│       ├── schemas/                     # Layer 4: Pydantic request/response schemas
│       │   ├── __init__.py
│       │   ├── common.py                # Shared enums: Priority, Status, ActionType
│       │   ├── client.py
│       │   ├── campaign.py              # Micros to USD conversion happens HERE
│       │   ├── recommendation.py        # RecommendationRead, ApplyActionRequest
│       │   └── search_term.py
│       │
│       ├── routers/                     # Layer 6: FastAPI route handlers (thin layer)
│       │   ├── __init__.py
│       │   ├── auth.py                  # GET /auth/login, GET /auth/callback
│       │   ├── clients.py               # GET /clients, POST /clients/{id}/sync
│       │   ├── campaigns.py
│       │   ├── keywords.py
│       │   ├── search_terms.py
│       │   ├── recommendations.py
│       │   ├── actions.py               # POST /actions/apply, POST /actions/rollback/{id}
│       │   └── analytics.py
│       │
│       ├── services/                    # Layer 5: Business Logic
│       │   ├── __init__.py
│       │   ├── credentials_service.py   # Keyring read/write wrapper
│       │   ├── google_ads_client.py     # GAQL query executor (raw API calls)
│       │   ├── sync_service.py          # Orchestrates: API fetch to DB upsert
│       │   ├── recommendations_engine.py # Implements 7 optimization rules
│       │   ├── action_executor.py       # Writes to Google Ads API (with circuit breaker)
│       │   └── analytics_service.py     # KPI aggregation + anomaly detection
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logger.py                # Rotating file logger setup
│           ├── constants.py             # SAFETY_LIMITS + IRRELEVANT_KEYWORDS
│           └── formatters.py            # micros_to_usd(), usd_to_micros()
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api.js                       # Axios instance (baseURL: localhost:8000)
│       │
│       ├── components/
│       │   ├── KPICard.jsx
│       │   ├── Charts.jsx
│       │   ├── Sidebar.jsx
│       │   ├── ConfirmationModal.jsx    # Before/After action confirmation
│       │   └── Toast.jsx
│       │
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Clients.jsx
│       │   ├── Campaigns.jsx
│       │   ├── Keywords.jsx
│       │   ├── SearchTerms.jsx
│       │   ├── Recommendations.jsx
│       │   ├── ActionHistory.jsx
│       │   ├── Alerts.jsx
│       │   └── Settings.jsx
│       │
│       └── hooks/
│           ├── useClients.js
│           ├── useRecommendations.js
│           └── useSync.js
│
├── database/
│   ├── google_ads.db                    # SQLite file — GITIGNORED
│   └── backups/                         # Auto-backups before Apply actions
│
└── logs/
    └── app.log                          # Rotating logs — GITIGNORED
```

---

# SECTION 2: IMPORT HIERARCHY (No Circular Imports)

```
Layer 1: utils/          — no imports from app
Layer 2: config.py       — imports utils/constants
Layer 3: models/         — imports database only. NEVER schemas, services, routers
Layer 4: schemas/        — imports models, utils/formatters only
Layer 5: services/       — imports models, schemas, utils, config. NEVER routers
Layer 6: routers/        — imports services, schemas only. NEVER other routers
Layer 7: app/main.py     — imports all routers, registers them
Layer 8: main.py (root)  — imports backend/app/main.py, starts PyWebView
```

**Violation example (NEVER DO THIS):**
```python
# services/sync_service.py
from app.routers.clients import some_function  # SERVICE importing ROUTER = WRONG
```

---

# SECTION 3: COMPLETE MODULE IMPLEMENTATIONS

## Module 1: Credentials Service

```python
# backend/app/services/credentials_service.py
"""
Wraps Windows Credential Manager (keyring) for secure token storage.
RULE: This is the ONLY place in the codebase that reads/writes tokens.
"""

import json
import keyring
from app.utils.logger import logger

KEYRING_SERVICE = "GoogleAdsHelper"
KEYRING_KEY = "oauth_credentials"


class CredentialsNotFoundError(Exception):
    """Raised when no credentials exist (user not authenticated)"""
    pass


class CredentialsService:

    @staticmethod
    def save(refresh_token: str, token_uri: str, client_id: str,
             client_secret: str, developer_token: str) -> None:
        """Save all credentials to Windows Credential Manager. Called once after OAuth."""
        token_data = {
            "refresh_token": refresh_token,
            "token_uri": token_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "developer_token": developer_token
        }
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, json.dumps(token_data))
        logger.info("Credentials saved to Windows Credential Manager")

    @staticmethod
    def get() -> dict:
        """
        Retrieve credentials from Windows Credential Manager.
        Returns dict with: refresh_token, token_uri, client_id, client_secret, developer_token
        Raises CredentialsNotFoundError if not authenticated yet.
        """
        raw = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
        if not raw:
            raise CredentialsNotFoundError("No credentials found. User must complete OAuth flow first.")
        return json.loads(raw)

    @staticmethod
    def delete() -> None:
        """Remove credentials (logout)"""
        keyring.delete_password(KEYRING_SERVICE, KEYRING_KEY)
        logger.info("Credentials removed from Windows Credential Manager")

    @staticmethod
    def exists() -> bool:
        """Check if user is authenticated without raising exception"""
        try:
            raw = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
            return raw is not None
        except Exception:
            return False
```

---

## Module 2: Authentication Router (Complete OAuth2 Flow)

```python
# backend/app/routers/auth.py
"""
OAuth2 flow for Google Ads API.
IMPORTANT: Uses prompt='consent' to force refresh_token on every login.
"""

import json
import keyring
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from app.config import settings
from app.services.credentials_service import CredentialsService
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

SCOPES = ['https://www.googleapis.com/auth/adwords']
REDIRECT_URI = "http://localhost:8000/auth/callback"


def _get_flow() -> Flow:
    """Helper: create Flow with current settings"""
    config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


@router.get("/status")
async def auth_status():
    """Check if user is authenticated"""
    return {"authenticated": CredentialsService.exists()}


@router.get("/login")
async def login():
    """
    Step 1: Generate OAuth URL.
    Frontend opens this URL in browser window.
    """
    flow = _get_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',        # CRITICAL: needed to get refresh_token
        prompt='consent',             # CRITICAL: forces consent screen, always gets refresh_token
        include_granted_scopes='true'
    )
    logger.info("OAuth login URL generated")
    return {"auth_url": auth_url}


@router.get("/callback")
async def callback(code: str, state: str = None, error: str = None):
    """
    Step 2: Google redirects here with authorization code.
    Exchange code for tokens, save to Windows Credential Manager.
    """
    if error:
        logger.warning(f"OAuth denied by user: {error}")
        return HTMLResponse(content="<html><body><h2>Authentication cancelled. Close this window.</h2></body></html>")

    try:
        flow = _get_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.refresh_token:
            raise HTTPException(
                status_code=400,
                detail="No refresh token returned. Revoke app access at "
                       "https://myaccount.google.com/permissions and try again."
            )

        CredentialsService.save(
            refresh_token=credentials.refresh_token,
            token_uri=credentials.token_uri,
            client_id=credentials.client_id,
            client_secret=credentials.client_secret,
            developer_token=settings.GOOGLE_DEVELOPER_TOKEN
        )

        logger.info("OAuth authentication successful")
        return HTMLResponse(content="<html><body><h2>Authentication successful! Return to Google Ads Helper.</h2></body></html>")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")


@router.post("/logout")
async def logout():
    """Remove credentials from Windows Credential Manager"""
    CredentialsService.delete()
    return {"status": "logged_out"}
```

---

## Module 3: Google Ads Client (GAQL Executor)

```python
# backend/app/services/google_ads_client.py
"""
Wrapper around Google Ads Python SDK.
RULE: This file only fetches/writes data. No business logic here.
"""

from google.ads.googleads.client import GoogleAdsClient as _GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from app.services.credentials_service import CredentialsService
from app.utils.logger import logger
from typing import Optional


class GoogleAdsAPIError(Exception):
    pass


class GoogleAdsClient:

    def __init__(self, customer_id: str, login_customer_id: Optional[str] = None):
        self.customer_id = customer_id.replace("-", "")
        self.login_customer_id = login_customer_id.replace("-", "") if login_customer_id else None

        creds = CredentialsService.get()
        config = {
            "developer_token": creds["developer_token"],
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "use_proto_plus": True,
        }
        if self.login_customer_id:
            config["login_customer_id"] = self.login_customer_id

        self._client = _GoogleAdsClient.load_from_dict(config)

    def _execute_query(self, query: str) -> list:
        """Execute GAQL query, return list of rows"""
        service = self._client.get_service("GoogleAdsService")
        try:
            response = service.search(customer_id=self.customer_id, query=query)
            return list(response)
        except GoogleAdsException as ex:
            error_message = "; ".join([e.message for e in ex.failure.errors])
            logger.error(f"Google Ads API error for {self.customer_id}: {error_message}")
            raise GoogleAdsAPIError(f"API Error: {error_message}")

    # ── GAQL QUERIES (Source of Truth) ─────────────────────────────────────

    def get_campaigns(self) -> list:
        query = """
            SELECT
                campaign.id,
                campaign.name,
                campaign.status,
                campaign_budget.amount_micros,
                metrics.cost_micros,
                metrics.impressions,
                metrics.clicks,
                metrics.conversions,
                metrics.conversions_value,
                metrics.ctr,
                metrics.search_budget_lost_impression_share,
                metrics.search_rank_lost_impression_share
            FROM campaign
            WHERE segments.date DURING LAST_30_DAYS
                AND campaign.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
        """
        return self._execute_query(query)

    def get_keywords(self) -> list:
        query = """
            SELECT
                ad_group_criterion.criterion_id,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.status,
                ad_group_criterion.effective_cpc_bid_micros,
                ad_group_criterion.quality_info.quality_score,
                campaign.id,
                campaign.name,
                ad_group.id,
                ad_group.name,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM keyword_view
            WHERE segments.date DURING LAST_30_DAYS
                AND campaign.status = 'ENABLED'
                AND ad_group.status = 'ENABLED'
                AND ad_group_criterion.status != 'REMOVED'
            ORDER BY metrics.cost_micros DESC
            LIMIT 10000
        """
        return self._execute_query(query)

    def get_search_terms(self) -> list:
        query = """
            SELECT
                search_term_view.search_term,
                search_term_view.status,
                campaign.id,
                campaign.name,
                ad_group.id,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros,
                metrics.conversions,
                metrics.ctr
            FROM search_term_view
            WHERE segments.date DURING LAST_30_DAYS
                AND campaign.status = 'ENABLED'
            ORDER BY metrics.cost_micros DESC
            LIMIT 10000
        """
        return self._execute_query(query)

    def list_accessible_customers(self) -> list[str]:
        """List all accounts accessible via current credentials (for initial setup)"""
        service = self._client.get_service("CustomerService")
        accessible = service.list_accessible_customers()
        return list(accessible.resource_names)

    # ── WRITE OPERATIONS ────────────────────────────────────────────────────

    def pause_keyword(self, ad_group_id: str, criterion_id: str) -> bool:
        try:
            service = self._client.get_service("AdGroupCriterionService")
            op = self._client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = f"customers/{self.customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"
            criterion.status = self._client.enums.AdGroupCriterionStatusEnum.PAUSED
            field_mask = self._client.get_type("FieldMask")
            field_mask.paths.append("status")
            op.update_mask.CopyFrom(field_mask)
            service.mutate_ad_group_criteria(customer_id=self.customer_id, operations=[op])
            logger.info(f"Paused keyword {criterion_id} in ad_group {ad_group_id}")
            return True
        except GoogleAdsException as ex:
            raise GoogleAdsAPIError(str(ex))

    def add_negative_keyword(self, campaign_id: str, keyword_text: str, match_type: str = "BROAD") -> bool:
        try:
            service = self._client.get_service("CampaignCriterionService")
            op = self._client.get_type("CampaignCriterionOperation")
            criterion = op.create
            criterion.campaign = f"customers/{self.customer_id}/campaigns/{campaign_id}"
            criterion.negative = True
            criterion.keyword.text = keyword_text
            criterion.keyword.match_type = getattr(self._client.enums.KeywordMatchTypeEnum, match_type)
            service.mutate_campaign_criteria(customer_id=self.customer_id, operations=[op])
            logger.info(f"Added negative '{keyword_text}' to campaign {campaign_id}")
            return True
        except GoogleAdsException as ex:
            raise GoogleAdsAPIError(str(ex))

    def update_keyword_bid(self, ad_group_id: str, criterion_id: str, new_bid_micros: int) -> bool:
        try:
            service = self._client.get_service("AdGroupCriterionService")
            op = self._client.get_type("AdGroupCriterionOperation")
            criterion = op.update
            criterion.resource_name = f"customers/{self.customer_id}/adGroupCriteria/{ad_group_id}~{criterion_id}"
            criterion.cpc_bid_micros = new_bid_micros
            field_mask = self._client.get_type("FieldMask")
            field_mask.paths.append("cpc_bid_micros")
            op.update_mask.CopyFrom(field_mask)
            service.mutate_ad_group_criteria(customer_id=self.customer_id, operations=[op])
            logger.info(f"Updated bid for keyword {criterion_id}: {new_bid_micros} micros")
            return True
        except GoogleAdsException as ex:
            raise GoogleAdsAPIError(str(ex))
```

---

## Module 4: Sync Service

```python
# backend/app/services/sync_service.py
"""
Orchestrates data sync: Google Ads API to Local SQLite DB.
Sequential sync per client. Transactional (rollback on failure).
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.google_ads_client import GoogleAdsClient
from app.models.client import Client
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.search_term import SearchTerm
from app.utils.logger import logger


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    def sync_client(self, client_id: int) -> dict:
        """
        Sync single client: campaigns then keywords then search terms.
        Returns: { status, campaigns_synced, keywords_synced, search_terms_synced, errors }
        """
        client = self.db.query(Client).filter(Client.id == client_id).first()
        if not client:
            return {"status": "error", "message": f"Client {client_id} not found"}

        logger.info(f"Starting sync for client {client_id} ({client.name})")
        stats = {"campaigns": 0, "keywords": 0, "search_terms": 0, "errors": []}

        try:
            gads = GoogleAdsClient(
                customer_id=client.google_ads_customer_id,
                login_customer_id=client.manager_id
            )

            # PHASE 1: CAMPAIGNS
            logger.info(f"[Client {client_id}] Fetching campaigns...")
            campaigns_data = gads.get_campaigns()
            synced_campaign_ids = {}

            for row in campaigns_data:
                campaign = self._upsert_campaign(client_id, row)
                synced_campaign_ids[str(row.campaign.id)] = campaign.id
                stats["campaigns"] += 1

            self.db.commit()
            logger.info(f"[Client {client_id}] Synced {stats['campaigns']} campaigns")

            # PHASE 2: KEYWORDS
            logger.info(f"[Client {client_id}] Fetching keywords...")
            keywords_data = gads.get_keywords()

            for row in keywords_data:
                campaign_google_id = str(row.campaign.id)
                if campaign_google_id not in synced_campaign_ids:
                    continue
                self._upsert_keyword(synced_campaign_ids[campaign_google_id], row)
                stats["keywords"] += 1

            self.db.commit()
            logger.info(f"[Client {client_id}] Synced {stats['keywords']} keywords")

            # PHASE 3: SEARCH TERMS (always fresh 30-day window)
            logger.info(f"[Client {client_id}] Fetching search terms...")
            self.db.query(SearchTerm).filter(SearchTerm.client_id == client_id).delete()

            search_terms_data = gads.get_search_terms()
            for row in search_terms_data:
                self._insert_search_term(client_id, row)
                stats["search_terms"] += 1

            self.db.commit()

            # PHASE 4: FINALIZE
            client.last_synced_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Sync complete for client {client_id}: {stats}")
            return {"status": "success", "stats": stats}

        except Exception as e:
            self.db.rollback()
            logger.error(f"Sync FAILED for client {client_id}: {str(e)}")
            return {"status": "error", "message": str(e), "stats": stats}

    def _upsert_campaign(self, client_id: int, row) -> Campaign:
        google_id = str(row.campaign.id)
        campaign = self.db.query(Campaign).filter(
            Campaign.google_id == google_id,
            Campaign.client_id == client_id
        ).first()

        if not campaign:
            campaign = Campaign(google_id=google_id, client_id=client_id)
            self.db.add(campaign)

        campaign.name = row.campaign.name
        campaign.status = row.campaign.status.name
        campaign.budget_micros = row.campaign_budget.amount_micros
        campaign.spend_micros = row.metrics.cost_micros
        campaign.conversions = row.metrics.conversions
        campaign.ctr = row.metrics.ctr
        campaign.updated_at = datetime.utcnow()

        if row.metrics.cost_micros > 0 and row.metrics.conversions_value:
            spend = row.metrics.cost_micros / 1_000_000
            campaign.roas = (row.metrics.conversions_value / spend * 100) if spend > 0 else 0
        else:
            campaign.roas = 0

        return campaign

    def _upsert_keyword(self, campaign_id: int, row) -> Keyword:
        google_id = str(row.ad_group_criterion.criterion_id)
        keyword = self.db.query(Keyword).filter(
            Keyword.google_id == google_id,
            Keyword.campaign_id == campaign_id
        ).first()

        if not keyword:
            keyword = Keyword(google_id=google_id, campaign_id=campaign_id)
            self.db.add(keyword)

        keyword.text = row.ad_group_criterion.keyword.text
        keyword.match_type = row.ad_group_criterion.keyword.match_type.name
        keyword.status = row.ad_group_criterion.status.name
        keyword.bid_micros = row.ad_group_criterion.effective_cpc_bid_micros
        keyword.quality_score = row.ad_group_criterion.quality_info.quality_score
        keyword.clicks = row.metrics.clicks
        keyword.cost_micros = row.metrics.cost_micros
        keyword.conversions = row.metrics.conversions
        keyword.ad_group_id = str(row.ad_group.id)
        keyword.updated_at = datetime.utcnow()
        keyword.cpa_micros = int(keyword.cost_micros / keyword.conversions) if keyword.conversions > 0 else 0

        return keyword

    def _insert_search_term(self, client_id: int, row) -> SearchTerm:
        term = SearchTerm(
            client_id=client_id,
            query_text=row.search_term_view.search_term,
            clicks=row.metrics.clicks,
            impressions=row.metrics.impressions,
            cost_micros=row.metrics.cost_micros,
            conversions=row.metrics.conversions,
            segment="OTHER"
        )
        self.db.add(term)
        return term
```

---

## Module 5: Recommendations Engine (All 7 Rules)

```python
# backend/app/services/recommendations_engine.py
"""
Implements 7 optimization rules from the Google Ads Playbook.
RULE: Only reads from DB. Never writes to Google Ads API.
"""

import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.search_term import SearchTerm
from app.models.recommendation import Recommendation
from app.utils.constants import SAFETY_LIMITS, IRRELEVANT_KEYWORDS
from app.utils.logger import logger


class RecommendationEngine:

    def __init__(self, db: Session, client_id: int):
        self.db = db
        self.client_id = client_id

    def run_all_rules(self) -> int:
        """Run all 7 rules. Returns count of new recommendations saved."""
        logger.info(f"Running recommendation engine for client {self.client_id}")
        all_recs = []
        all_recs.extend(self._rule_01_pause_bleeding_keywords())
        all_recs.extend(self._rule_02_increase_bid_high_performers())
        all_recs.extend(self._rule_03_decrease_bid_high_cpa())
        all_recs.extend(self._rule_04_add_search_term_as_keyword())
        all_recs.extend(self._rule_05_add_negative_keywords())
        all_recs.extend(self._rule_06_pause_underperforming_ads())
        all_recs.extend(self._rule_07_reallocate_budget())
        saved = self._save_recommendations(all_recs)
        logger.info(f"Client {self.client_id}: {len(all_recs)} recs generated, {saved} new saved")
        return saved

    def _rule_01_pause_bleeding_keywords(self) -> list:
        """RULE 1: spend > 2x avg AND conversions = 0 AND clicks > threshold. Priority: HIGH"""
        recs = []
        campaigns = self.db.query(Campaign).filter(Campaign.client_id == self.client_id).all()

        for campaign in campaigns:
            stats = self.db.query(func.avg(Keyword.cost_micros).label('avg_cost')).filter(
                Keyword.campaign_id == campaign.id,
                Keyword.cost_micros > 0
            ).first()

            if not stats or not stats.avg_cost:
                continue

            threshold = stats.avg_cost * 2
            bleeding = self.db.query(Keyword).filter(
                Keyword.campaign_id == campaign.id,
                Keyword.status == 'ENABLED',
                Keyword.conversions == 0,
                Keyword.clicks >= SAFETY_LIMITS['PAUSE_KEYWORD_MIN_CLICKS'],
                Keyword.cost_micros > threshold
            ).all()

            for kw in bleeding:
                recs.append(self._make_rec(
                    rule_id="RULE_01_PAUSE_KEYWORD",
                    entity_type="keyword",
                    entity_id=kw.google_id,
                    priority="HIGH",
                    reason=f"Spend ${kw.cost_micros/1e6:.2f} with 0 conversions ({kw.clicks} clicks). Avg: ${stats.avg_cost/1e6:.2f}.",
                    action={"type": "PAUSE_KEYWORD", "ad_group_id": kw.ad_group_id,
                            "criterion_id": kw.google_id, "old_status": "ENABLED", "new_status": "PAUSED"}
                ))
        return recs

    def _rule_02_increase_bid_high_performers(self) -> list:
        """RULE 2: conversions > 5 AND CVR > 1.5x campaign average. Priority: MEDIUM"""
        recs = []
        campaigns = self.db.query(Campaign).filter(Campaign.client_id == self.client_id).all()

        for campaign in campaigns:
            keywords = self.db.query(Keyword).filter(
                Keyword.campaign_id == campaign.id, Keyword.clicks > 0
            ).all()
            if not keywords:
                continue

            total_conv = sum(k.conversions for k in keywords)
            total_clicks = sum(k.clicks for k in keywords)
            if total_clicks == 0:
                continue

            avg_cvr = total_conv / total_clicks
            threshold = avg_cvr * SAFETY_LIMITS['HIGH_PERFORMER_CVR_MULTIPLIER']

            for kw in keywords:
                if kw.clicks == 0:
                    continue
                kw_cvr = kw.conversions / kw.clicks
                if kw.conversions >= 5 and kw_cvr > threshold:
                    new_bid = int(kw.bid_micros * 1.20)
                    recs.append(self._make_rec(
                        rule_id="RULE_02_INCREASE_BID",
                        entity_type="keyword",
                        entity_id=kw.google_id,
                        priority="MEDIUM",
                        reason=f"High performer: {kw.conversions} conv, CVR {kw_cvr:.1%} vs avg {avg_cvr:.1%}.",
                        action={"type": "UPDATE_BID", "ad_group_id": kw.ad_group_id,
                                "criterion_id": kw.google_id,
                                "old_bid_micros": kw.bid_micros, "new_bid_micros": new_bid}
                    ))
        return recs

    def _rule_03_decrease_bid_high_cpa(self) -> list:
        """RULE 3: CPA > 2x campaign avg AND spend > $50. Priority: MEDIUM"""
        recs = []
        campaigns = self.db.query(Campaign).filter(Campaign.client_id == self.client_id).all()

        for campaign in campaigns:
            keywords = self.db.query(Keyword).filter(
                Keyword.campaign_id == campaign.id, Keyword.conversions > 0
            ).all()
            if not keywords:
                continue

            total_cost = sum(k.cost_micros for k in keywords)
            total_conv = sum(k.conversions for k in keywords)
            if total_conv == 0:
                continue

            avg_cpa_micros = total_cost / total_conv
            cpa_threshold = avg_cpa_micros * SAFETY_LIMITS['LOW_PERFORMER_CPA_MULTIPLIER']

            for kw in keywords:
                if kw.cost_micros < 50 * 1_000_000:
                    continue
                if kw.cpa_micros > cpa_threshold:
                    new_bid = int(kw.bid_micros * 0.80)
                    recs.append(self._make_rec(
                        rule_id="RULE_03_DECREASE_BID",
                        entity_type="keyword",
                        entity_id=kw.google_id,
                        priority="MEDIUM",
                        reason=f"High CPA ${kw.cpa_micros/1e6:.2f} vs avg ${avg_cpa_micros/1e6:.2f}.",
                        action={"type": "UPDATE_BID", "ad_group_id": kw.ad_group_id,
                                "criterion_id": kw.google_id,
                                "old_bid_micros": kw.bid_micros, "new_bid_micros": new_bid}
                    ))
        return recs

    def _rule_04_add_search_term_as_keyword(self) -> list:
        """RULE 4: conversions >= 3 AND not already a keyword. Priority: HIGH"""
        recs = []
        search_terms = self.db.query(SearchTerm).filter(
            SearchTerm.client_id == self.client_id,
            SearchTerm.conversions >= SAFETY_LIMITS['ADD_KEYWORD_MIN_CONV']
        ).all()

        existing_keywords = set(
            kw.text.lower() for kw in
            self.db.query(Keyword).join(Campaign).filter(Campaign.client_id == self.client_id).all()
        )

        for term in search_terms:
            if term.query_text.lower() in existing_keywords or term.clicks == 0:
                continue
            cvr = term.conversions / term.clicks
            recs.append(self._make_rec(
                rule_id="RULE_04_ADD_KEYWORD",
                entity_type="search_term",
                entity_id=term.query_text,
                priority="HIGH",
                reason=f"High-performing search: {term.conversions} conv, CVR {cvr:.1%}, cost ${term.cost_micros/1e6:.2f}.",
                action={"type": "ADD_KEYWORD", "query_text": term.query_text,
                        "match_type": "EXACT", "conversions": term.conversions}
            ))
        return recs

    def _rule_05_add_negative_keywords(self) -> list:
        """RULE 5: waste spend OR irrelevant intent. Priority: HIGH"""
        recs = []
        search_terms = self.db.query(SearchTerm).filter(
            SearchTerm.client_id == self.client_id
        ).all()

        for term in search_terms:
            # Trigger A: Waste spend
            if (term.clicks >= SAFETY_LIMITS['ADD_NEGATIVE_MIN_CLICKS']
                    and term.conversions == 0
                    and term.ctr < 0.01):
                recs.append(self._make_rec(
                    rule_id="RULE_05_ADD_NEGATIVE",
                    entity_type="search_term",
                    entity_id=term.query_text,
                    priority="HIGH",
                    reason=f"Wasted spend: ${term.cost_micros/1e6:.2f} on {term.clicks} clicks, 0 conv.",
                    action={"type": "ADD_NEGATIVE", "keyword_text": term.query_text,
                            "match_type": "BROAD", "level": "campaign"}
                ))
                continue

            # Trigger B: Irrelevant intent
            query_lower = term.query_text.lower()
            for word in IRRELEVANT_KEYWORDS:
                if word in query_lower:
                    recs.append(self._make_rec(
                        rule_id="RULE_05_ADD_NEGATIVE",
                        entity_type="search_term",
                        entity_id=term.query_text,
                        priority="HIGH",
                        reason=f"Irrelevant intent: contains '{word}'.",
                        action={"type": "ADD_NEGATIVE", "keyword_text": term.query_text,
                                "match_type": "BROAD", "level": "account"}
                    ))
                    break
        return recs

    def _rule_06_pause_underperforming_ads(self) -> list:
        """RULE 6: Placeholder. Requires Ad model (not in MVP schema yet)."""
        return []

    def _rule_07_reallocate_budget(self) -> list:
        """RULE 7: ROAS > 2x account avg. Priority: HIGH"""
        recs = []
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == self.client_id,
            Campaign.status == 'ENABLED'
        ).all()

        campaigns_with_roas = [c for c in campaigns if c.roas and c.roas > 0]
        if not campaigns_with_roas:
            return recs

        avg_roas = sum(c.roas for c in campaigns_with_roas) / len(campaigns_with_roas)

        for campaign in campaigns_with_roas:
            if campaign.roas > avg_roas * 2:
                recs.append(self._make_rec(
                    rule_id="RULE_07_BUDGET_REALLOCATION",
                    entity_type="campaign",
                    entity_id=str(campaign.id),
                    priority="HIGH",
                    reason=f"High ROAS {campaign.roas:.0f}% (2x account avg {avg_roas:.0f}%). Consider increasing budget.",
                    action={"type": "INCREASE_BUDGET", "campaign_id": campaign.id,
                            "old_budget_micros": campaign.budget_micros,
                            "new_budget_micros": int(campaign.budget_micros * 1.30)}
                ))
        return recs

    def _make_rec(self, rule_id, entity_type, entity_id, priority, reason, action) -> Recommendation:
        return Recommendation(
            client_id=self.client_id,
            rule_id=rule_id,
            entity_type=entity_type,
            entity_id=str(entity_id),
            priority=priority,
            reason=reason,
            suggested_action=json.dumps(action),
            status="pending"
        )

    def _save_recommendations(self, new_recs: list) -> int:
        """Save recommendations, skipping pending duplicates. Returns count saved."""
        saved = 0
        for rec in new_recs:
            exists = self.db.query(Recommendation).filter(
                Recommendation.entity_id == rec.entity_id,
                Recommendation.rule_id == rec.rule_id,
                Recommendation.client_id == rec.client_id,
                Recommendation.status == 'pending'
            ).first()
            if not exists:
                self.db.add(rec)
                saved += 1
        self.db.commit()
        return saved
```

---

## Module 6: Action Executor (Circuit Breaker)

```python
# backend/app/services/action_executor.py
"""
Executes actions on Google Ads API.
RULE: validate_action() MUST be called before every write operation.
RULE: Every action MUST be logged in action_log table.
"""

import json
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.recommendation import Recommendation
from app.models.action_log import ActionLog
from app.models.keyword import Keyword
from app.models.client import Client
from app.services.google_ads_client import GoogleAdsClient
from app.utils.constants import SAFETY_LIMITS
from app.utils.logger import logger


class SafetyViolationError(Exception):
    pass


def validate_action(action_type: str, current_val: float,
                    new_val: float, context: dict) -> None:
    """
    Circuit breaker. Raises SafetyViolationError if action is unsafe.
    All monetary values in USD (NOT micros).
    """
    if action_type in ("UPDATE_BID", "SET_BID"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change bid: current bid is 0 or None")
        pct_change = abs(new_val - current_val) / current_val
        if pct_change > SAFETY_LIMITS["MAX_BID_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Bid change {pct_change:.0%} exceeds {SAFETY_LIMITS['MAX_BID_CHANGE_PCT']:.0%} limit. "
                f"${current_val:.2f} to ${new_val:.2f}"
            )
        if new_val < SAFETY_LIMITS["MIN_BID_USD"]:
            raise SafetyViolationError(f"New bid ${new_val:.2f} below minimum ${SAFETY_LIMITS['MIN_BID_USD']:.2f}")

    if action_type in ("INCREASE_BUDGET", "SET_BUDGET"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change budget: current budget is 0 or None")
        pct_change = abs(new_val - current_val) / current_val
        if pct_change > SAFETY_LIMITS["MAX_BUDGET_CHANGE_PCT"]:
            raise SafetyViolationError(f"Budget change {pct_change:.0%} exceeds {SAFETY_LIMITS['MAX_BUDGET_CHANGE_PCT']:.0%} limit")

    if action_type == "PAUSE_KEYWORD":
        total = context.get("total_keywords_in_campaign", 0)
        paused_today = context.get("keywords_paused_today_in_campaign", 0)
        if total > 0 and (paused_today + 1) / total > SAFETY_LIMITS["MAX_KEYWORD_PAUSE_PCT"]:
            raise SafetyViolationError(
                f"Already paused {paused_today}/{total} keywords today. "
                f"Limit: {SAFETY_LIMITS['MAX_KEYWORD_PAUSE_PCT']:.0%}"
            )

    if action_type == "ADD_NEGATIVE":
        negatives_today = context.get("negatives_added_today", 0)
        if negatives_today >= SAFETY_LIMITS["MAX_NEGATIVES_PER_DAY"]:
            raise SafetyViolationError(f"Daily negative limit reached: {negatives_today}/{SAFETY_LIMITS['MAX_NEGATIVES_PER_DAY']}")


class ActionExecutor:

    def __init__(self, db: Session):
        self.db = db

    def apply_recommendation(self, recommendation_id: int, client_id: int, dry_run: bool = False) -> dict:
        """
        Apply recommendation via Google Ads API.
        Returns: { status, action_type, message }
        """
        rec = self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.client_id == client_id,
            Recommendation.status == 'pending'
        ).first()

        if not rec:
            return {"status": "error", "message": "Recommendation not found or already applied"}

        action = json.loads(rec.suggested_action)
        action_type = action["type"]
        client = self.db.query(Client).filter(Client.id == client_id).first()

        context = self._build_context(action, client_id)
        current_val, new_val = self._extract_values(action)

        # Circuit breaker check
        try:
            validate_action(action_type, current_val, new_val, context)
        except SafetyViolationError as e:
            logger.warning(f"Safety violation for rec {recommendation_id}: {e}")
            return {"status": "blocked", "reason": str(e)}

        # Dry run: return preview without executing
        if dry_run:
            return {"status": "dry_run", "action": action,
                    "current_val": current_val, "new_val": new_val,
                    "message": "Dry run. Action NOT applied."}

        # Execute
        try:
            gads = GoogleAdsClient(
                customer_id=client.google_ads_customer_id,
                login_customer_id=client.manager_id
            )

            if action_type == "PAUSE_KEYWORD":
                gads.pause_keyword(action["ad_group_id"], action["criterion_id"])
            elif action_type == "ADD_NEGATIVE":
                gads.add_negative_keyword(
                    campaign_id=context.get("campaign_id", ""),
                    keyword_text=action["keyword_text"],
                    match_type=action.get("match_type", "BROAD")
                )
            elif action_type == "UPDATE_BID":
                gads.update_keyword_bid(action["ad_group_id"], action["criterion_id"], action["new_bid_micros"])
            else:
                return {"status": "error", "message": f"Unknown action type: {action_type}"}

            self._log_action(client_id, action_type, rec.entity_id,
                             {"val": current_val}, {"val": new_val}, recommendation_id, "SUCCESS")
            rec.status = "applied"
            self.db.commit()

            logger.info(f"Applied recommendation {recommendation_id}: {action_type}")
            return {"status": "success", "action_type": action_type}

        except Exception as e:
            self._log_action(client_id, action_type, rec.entity_id,
                             {"val": current_val}, {"val": new_val}, recommendation_id, "FAILED", str(e))
            logger.error(f"Action {action_type} failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _build_context(self, action: dict, client_id: int) -> dict:
        today = date.today()
        context = {}

        if action["type"] == "PAUSE_KEYWORD":
            kw = self.db.query(Keyword).filter(Keyword.google_id == action.get("criterion_id")).first()
            if kw:
                total = self.db.query(func.count(Keyword.id)).filter(Keyword.campaign_id == kw.campaign_id).scalar()
                paused_today = self.db.query(func.count(ActionLog.id)).filter(
                    ActionLog.client_id == client_id,
                    ActionLog.action_type == "PAUSE_KEYWORD",
                    ActionLog.status == "SUCCESS",
                    func.date(ActionLog.timestamp) == today
                ).scalar()
                context["total_keywords_in_campaign"] = total or 0
                context["keywords_paused_today_in_campaign"] = paused_today or 0

        if action["type"] == "ADD_NEGATIVE":
            negatives_today = self.db.query(func.count(ActionLog.id)).filter(
                ActionLog.client_id == client_id,
                ActionLog.action_type == "ADD_NEGATIVE",
                ActionLog.status == "SUCCESS",
                func.date(ActionLog.timestamp) == today
            ).scalar()
            context["negatives_added_today"] = negatives_today or 0

        return context

    def _extract_values(self, action: dict) -> tuple:
        action_type = action["type"]
        if action_type == "UPDATE_BID":
            return (action.get("old_bid_micros", 0) / 1_000_000, action.get("new_bid_micros", 0) / 1_000_000)
        if action_type in ("INCREASE_BUDGET", "SET_BUDGET"):
            return (action.get("old_budget_micros", 0) / 1_000_000, action.get("new_budget_micros", 0) / 1_000_000)
        return (0, 0)

    def _log_action(self, client_id, action_type, entity_id, old_value, new_value,
                    recommendation_id, status, error_message=None):
        log = ActionLog(
            client_id=client_id,
            action_type=action_type,
            entity_id=str(entity_id),
            old_value_json=json.dumps(old_value),
            new_value_json=json.dumps(new_value),
            status=status,
            error_message=error_message
        )
        self.db.add(log)
        self.db.commit()
```

---

# SECTION 4: CONSTANTS (Complete)

```python
# backend/app/utils/constants.py

SAFETY_LIMITS = {
    "MAX_BID_CHANGE_PCT": 0.50,
    "MIN_BID_USD": 0.10,
    "MAX_BID_USD": 100.00,
    "MAX_BUDGET_CHANGE_PCT": 0.30,
    "MAX_KEYWORD_PAUSE_PCT": 0.20,
    "MAX_NEGATIVES_PER_DAY": 100,
    "MAX_ACTIONS_PER_BATCH": 50,
    "HIGH_SPEND_THRESHOLD_USD": 1000.0,
    "PAUSE_KEYWORD_MIN_CLICKS": 10,
    "ADD_KEYWORD_MIN_CONV": 3,
    "ADD_NEGATIVE_MIN_CLICKS": 5,
    "HIGH_PERFORMER_CVR_MULTIPLIER": 1.5,
    "LOW_PERFORMER_CPA_MULTIPLIER": 2.0,
    "SPEND_SPIKE_THRESHOLD": 1.5,
    "CTR_DROP_THRESHOLD": 0.7,
}

IRRELEVANT_KEYWORDS = [
    "free", "gratis", "za darmo",
    "cheap", "tani", "najtaniej",
    "how to", "what is", "jak zrobić", "co to jest", "tutorial", "poradnik",
    "job", "jobs", "praca", "salary", "wynagrodzenie", "hiring",
    "download", "torrent", "crack", "pobierz za darmo",
    "review", "opinie", "complaint", "scam", "oszustwo"
]

GOOGLE_ADS_API_VERSION = "v17"
MICROS_PER_UNIT = 1_000_000
```

---

# SECTION 5: PYWEBVIEW ENTRY POINT

```python
# main.py (project root)

import sys
import threading
import time
import webview
import uvicorn
from backend.app.main import app as fastapi_app
from backend.app.utils.logger import logger


def start_backend():
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")


def wait_for_backend(timeout=10) -> bool:
    import requests
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get("http://127.0.0.1:8000/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


if __name__ == "__main__":
    logger.info("Starting Google Ads Helper...")

    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()

    if not wait_for_backend(timeout=10):
        logger.error("Backend failed to start. Exiting.")
        sys.exit(1)

    logger.info("Backend ready. Opening window...")

    window = webview.create_window(
        title="Google Ads Helper",
        url="http://127.0.0.1:8000",
        width=1440,
        height=900,
        resizable=True,
        min_size=(1024, 600),
    )

    webview.start(debug=False, http_server=False)
    logger.info("Window closed. Shutting down.")
```

---

# SECTION 6: TESTING CHECKLIST

Before marking any module DONE, verify all boxes checked:

### Authentication
- [ ] OAuth URL generated (GET /auth/login returns auth_url)
- [ ] Callback receives code parameter from Google
- [ ] refresh_token present in credentials (not None)
- [ ] Token stored in Windows Credential Manager (verify via keyring.get_password())
- [ ] CredentialsService.exists() returns True after auth
- [ ] GET /auth/status returns {"authenticated": true}

### Sync Service
- [ ] Returns {"status": "success"} for valid client
- [ ] campaigns table populated
- [ ] keywords table populated
- [ ] search_terms table refreshed (old deleted, new inserted)
- [ ] client.last_synced_at updated
- [ ] Invalid client_id returns error dict (no crash)
- [ ] Exception triggers db.rollback() (no partial data)

### Recommendations Engine
- [ ] Rule 1 fires for keywords: spend > 2x avg AND conversions = 0
- [ ] Rule 1 does NOT fire for keywords with any conversions
- [ ] No duplicate pending recommendations for same entity + rule
- [ ] run_all_rules() idempotent (running twice = same count saved)

### Circuit Breaker
- [ ] Bid change 51% raises SafetyViolationError
- [ ] Bid change 49% passes validation
- [ ] current_val = 0 raises SafetyViolationError (no division by zero)
- [ ] Pausing 21st keyword of 100 raises SafetyViolationError
- [ ] 101st negative today raises SafetyViolationError

### Action Executor
- [ ] dry_run=True returns preview, does NOT call Google Ads API
- [ ] dry_run=False calls API and logs to action_log
- [ ] Failed API call logged with status=FAILED + error_message
- [ ] Recommendation status updated to 'applied' on success

---

# END OF BLUEPRINT v2.0

**This document + Technical_Spec.md + PRD_Core.md = Complete Source of Truth**

**For any ambiguity: ask PM before coding. Do NOT guess.**
