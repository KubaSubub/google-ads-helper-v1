# CLAUDE.md — Google Ads Helper
# This file is read automatically by Claude Code at the start of every session.
# It is the SINGLE source of context for the AI developer.

## PROJECT OVERVIEW

**Google Ads Helper** — local-first Windows desktop app that automates 80% of a Google Ads specialist's routine work. Syncs data from Google Ads API, analyzes performance, generates optimization recommendations, and enables 1-click actions with safety mechanisms.

**Stack:** FastAPI (Python 3.10+) + React 18 (Vite) + SQLite + PyWebView (desktop wrapper)
**Platform:** Windows 10+ only (MVP)
**Distribution:** PyInstaller → single .exe

---

## CRITICAL RULES (NEVER VIOLATE)

1. **File placement:** Create files EXACTLY in the locations shown in the file tree below. Zero improvisation.
2. **Import direction:** Only import downward in the layer hierarchy. Never circular imports. (utils → config → models → schemas → services → routers → app/main.py → main.py)
3. **Micros conversion:** ALL cost/bid values from Google Ads API are in micros (÷ 1,000,000). Store as `BigInteger` in DB. Convert to float ONLY in Pydantic schemas for API responses.
4. **Circuit breaker:** EVERY write to Google Ads API MUST pass through `validate_action()` in action_executor.py. No exceptions.
5. **Credentials:** NEVER store tokens in SQLite, .env files, or logs. ONLY Windows Credential Manager via `keyring` library.
6. **Error handling:** NEVER let exceptions crash silently. Always log + return meaningful error to frontend.
7. **PRD Section 4.3 uses `REAL` for monetary columns — IGNORE IT.** Always use `BigInteger` (micros). This is final.

---

## FILE TREE (ACTUAL)

```
google-ads-helper/
├── main.py                              # PyWebView entry point
├── requirements.txt                     # Pinned Python deps
├── .env                                 # Local env (GITIGNORED)
├── .env.example                         # Template (NO secrets)
├── .gitignore
├── CLAUDE.md                            # THIS FILE
├── DECISIONS.md                         # Architecture decisions
├── PROGRESS.md                          # What's done / in progress
│
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py                      # FastAPI app + router registration
│       ├── config.py                    # pydantic-settings (reads .env)
│       ├── database.py                  # SQLAlchemy engine + SessionLocal + Base
│       ├── seed.py                      # Demo data seeder
│       │
│       ├── models/                      # Layer 3: SQLAlchemy ORM (14 models)
│       │   ├── __init__.py              # Exports all models
│       │   ├── client.py
│       │   ├── campaign.py
│       │   ├── ad_group.py
│       │   ├── keyword.py
│       │   ├── keyword_daily.py         # Keyword daily metrics (date aggregation)
│       │   ├── ad.py
│       │   ├── search_term.py
│       │   ├── recommendation.py
│       │   ├── action_log.py            # Has reverted_at column + REVERTED status
│       │   ├── alert.py
│       │   ├── metric_daily.py          # Campaign daily metrics
│       │   ├── metric_segmented.py      # Device + geo breakdowns
│       │   └── change_event.py          # Google Ads change history
│       │
│       ├── schemas/                     # Layer 4: Pydantic v2 schemas
│       │   ├── __init__.py
│       │   ├── common.py               # Enums, PaginatedResponse
│       │   ├── client.py
│       │   ├── campaign.py             # Micros→USD conversion HERE
│       │   ├── keyword.py
│       │   ├── ad.py
│       │   ├── search_term.py
│       │   ├── recommendation.py
│       │   ├── analytics.py
│       │   └── change_event.py
│       │
│       ├── routers/                     # Layer 6: FastAPI routes (12 routers)
│       │   ├── __init__.py
│       │   ├── auth.py                  # /auth/login, /auth/callback, /auth/status
│       │   ├── clients.py              # /clients CRUD
│       │   ├── campaigns.py            # /campaigns + /campaigns/{id}/kpis
│       │   ├── keywords_ads.py         # /keywords + /ads
│       │   ├── search_terms.py         # /search-terms/segmented, /search-terms/
│       │   ├── recommendations.py      # /recommendations + apply/dismiss
│       │   ├── actions.py              # /actions/ + /actions/revert/{id}
│       │   ├── analytics.py            # /analytics/* (15+ endpoints)
│       │   ├── sync.py                 # /sync/trigger, /sync/status
│       │   ├── export.py               # /export/search-terms, keywords, etc.
│       │   ├── semantic.py             # /semantic/clusters
│       │   └── history.py              # /history/ + /history/unified
│       │
│       ├── services/                    # Layer 5: Business logic
│       │   ├── __init__.py
│       │   ├── credentials_service.py   # Keyring wrapper (ONLY place for tokens)
│       │   ├── google_ads.py            # GAQL executor + sync + write ops
│       │   ├── recommendations.py       # 7 optimization rules
│       │   ├── action_executor.py       # Apply + Revert + circuit breaker
│       │   ├── analytics_service.py     # KPIs + anomaly detection + trends
│       │   ├── search_terms_service.py  # Segmentation logic
│       │   ├── semantic.py              # Semantic clustering
│       │   └── cache.py                 # TTL cache
│       │
│       └── utils/
│           ├── __init__.py
│           ├── constants.py            # SAFETY_LIMITS + IRRELEVANT_KEYWORDS
│           └── formatters.py           # micros_to_currency(), currency_to_micros()
│
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                      # React Router + Layout
│       ├── api.js                       # Axios (baseURL: /api/v1, Vite proxy)
│       │
│       ├── contexts/
│       │   ├── AppContext.jsx           # selectedClientId, alertCount, showToast
│       │   └── FilterContext.jsx        # campaignType, status, period filters
│       │
│       ├── components/
│       │   ├── Sidebar.jsx
│       │   ├── Charts.jsx              # Recharts wrappers
│       │   ├── DataTable.jsx           # TanStack Table wrapper
│       │   ├── ConfirmationModal.jsx    # Before/After preview
│       │   ├── Toast.jsx
│       │   ├── SegmentBadge.jsx        # Color-coded segment labels
│       │   ├── EmptyState.jsx
│       │   ├── FilterBar.jsx           # Pill filters (campaignType/status/period)
│       │   ├── SyncButton.jsx
│       │   ├── TrendExplorer.jsx       # Multi-metric correlation explorer
│       │   ├── InsightsFeed.jsx        # Auto-insights from campaign data
│       │   ├── MetricTooltip.jsx       # Metric definitions popup
│       │   ├── DiffView.jsx            # Before/After JSON diff
│       │   └── UI.jsx                  # Shared UI primitives
│       │
│       ├── pages/
│       │   ├── Dashboard.jsx           # KPI cards + trends + health score
│       │   ├── Clients.jsx
│       │   ├── Campaigns.jsx           # Campaign table + sparklines
│       │   ├── Keywords.jsx
│       │   ├── SearchTerms.jsx         # Segment cards + filterable list
│       │   ├── Recommendations.jsx     # Priority badges + Apply/Dismiss
│       │   ├── ActionHistory.jsx       # Timeline + Tabs (Helper/External/All)
│       │   ├── Alerts.jsx              # Unresolved/Resolved tabs
│       │   ├── Settings.jsx
│       │   ├── QualityScore.jsx        # QS audit dashboard
│       │   ├── Forecast.jsx            # Campaign forecasting
│       │   ├── Semantic.jsx            # Keyword clustering
│       │   ├── Anomalies.jsx
│       │   ├── SearchOptimization.jsx   # SEARCH optimization (6 analyses)
│       │   └── Login.jsx
│       │
│       └── hooks/
│           ├── useClients.js
│           ├── useRecommendations.js
│           └── useSync.js
│
├── data/
│   └── google_ads_app.db               # SQLite — GITIGNORED
│
└── logs/
    └── app.log                          # Rotating — GITIGNORED
```

---

## IMPORT HIERARCHY (Layer System)

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

**VIOLATION = BUG.** If you need something from a higher layer, refactor.

---

## SYNC FLOW (7 Phases)

```
POST /sync/trigger?client_id=X → google_ads_service methods
  │
  ├─ PHASE 1: Campaigns (GAQL) → sync_campaigns()
  ├─ PHASE 2: Ad Groups (GAQL) → sync_ad_groups()
  ├─ PHASE 3: Keywords (GAQL) → sync_keywords()
  ├─ PHASE 4: Daily Metrics (GAQL) → sync_daily_metrics()
  ├─ PHASE 5: Search Terms (GAQL) → sync_search_terms()
  ├─ PHASE 6: Change Events (non-critical) → sync_change_events()
  └─ return stats dict
```

Phase 6 is non-critical: if it fails, log error but DON'T rollback sync data.

---

## 7 RECOMMENDATION RULES

| Rule | Trigger | Action | Priority |
|------|---------|--------|----------|
| 1 | spend > 2× avg AND conv=0 AND clicks > 10 | PAUSE_KEYWORD | HIGH |
| 2 | conv > 5 AND CVR > 1.5× campaign avg | UPDATE_BID +20% | MEDIUM |
| 3 | CPA > 2× campaign avg AND spend > $50 | UPDATE_BID -20% | MEDIUM |
| 4 | search term conv ≥ 3 AND not already keyword | ADD_KEYWORD (EXACT) | HIGH |
| 5 | clicks ≥ 5 AND conv=0 AND CTR < 1% OR irrelevant intent | ADD_NEGATIVE | HIGH |
| 6 | ad CTR < 50% of best ad AND impressions > 500 | PAUSE_AD | MEDIUM |
| 7 | campaign ROAS > 2× account avg | INCREASE_BUDGET +30% | HIGH |

---

## SEARCH TERM SEGMENTS (Priority Order)

1. **IRRELEVANT** — query contains words from IRRELEVANT_KEYWORDS list → immediate
2. **HIGH_PERFORMER** — conv ≥ 3 AND CVR > campaign avg CVR → "Add as Keyword"
3. **WASTE** — clicks ≥ 5 AND conv = 0 AND CTR < 1% → "Add as Negative"
4. **OTHER** — default (insufficient data)

---

## SAFETY LIMITS (from constants.py)

```python
SAFETY_LIMITS = {
    "MAX_BID_CHANGE_PCT": 0.50,        # Max 50% bid change per action
    "MIN_BID_USD": 0.10,
    "MAX_BID_USD": 100.00,
    "MAX_BUDGET_CHANGE_PCT": 0.30,     # Max 30% budget change
    "MAX_KEYWORD_PAUSE_PCT": 0.20,     # Max 20% keywords paused/day/campaign
    "MAX_NEGATIVES_PER_DAY": 100,
    "MAX_ACTIONS_PER_BATCH": 50,
    "PAUSE_KEYWORD_MIN_CLICKS": 10,
    "ADD_KEYWORD_MIN_CONV": 3,
    "ADD_NEGATIVE_MIN_CLICKS": 5,
    "HIGH_PERFORMER_CVR_MULTIPLIER": 1.5,
    "LOW_PERFORMER_CPA_MULTIPLIER": 2.0,
}
```

---

## ANOMALY DETECTION THRESHOLDS

- **SPEND_SPIKE**: campaign spend > 3× proportional share of account → alert HIGH
- **CONVERSION_DROP**: daily avg ≥ 3 but total < daily_avg × 15 → alert HIGH
- **CTR_DROP**: campaign CTR < 0.5% with impressions > 1000 → alert MEDIUM

---

## REVERT (UNDO) RULES

- Action must be < 24 hours old
- Action status must be SUCCESS
- Action must not already be REVERTED
- **IRREVERSIBLE:** ADD_NEGATIVE (removing negatives re-enables bad traffic)
- PAUSE_KEYWORD → ENABLE_KEYWORD
- UPDATE_BID → restore old_bid_micros
- ADD_KEYWORD → PAUSE the added keyword

---

## UI DESIGN (v2)

- **Dark mode** only (MVP)
- Fonts: **Syne** (headings/KPI, fontWeight 700), **DM Sans** (body/UI)
- Colors: bg-primary=#0D0F14, sidebar=#111318, cards=rgba(255,255,255,0.03) with 0.07 border
- accent-blue=#4F8EF7, accent-purple=#7B5CE0
- Success=#4ADE80, Warning=#FBBF24, Danger=#F87171
- PageHeader: fontSize 22, fontWeight 700, fontFamily 'Syne'
- Table headers: fontSize 10, fontWeight 500, color rgba(255,255,255,0.35), uppercase
- Pill buttons: borderRadius 999, active state with border + bg
- Design reference: Linear, Vercel Dashboard
- Charts: Recharts
- Tables: @tanstack/react-table

---

## API ENDPOINTS (Complete)

### Auth
- `GET /auth/status` → {authenticated: bool}
- `GET /auth/login` → {auth_url: str}
- `GET /auth/callback?code=X` → HTML success page
- `POST /auth/logout`

### Clients
- `GET /clients/` → paginated list
- `GET /clients/{id}` → client detail
- `POST /clients/` → create client
- `POST /clients/discover` → auto-discover from MCC
- `PATCH /clients/{id}` → update client
- `DELETE /clients/{id}` → delete client

### Sync
- `POST /sync/trigger?client_id=X&days=30` → trigger full sync
- `GET /sync/status` → API connection status

### Campaigns
- `GET /campaigns/?client_id=X`
- `GET /campaigns/{id}/kpis?days=30`
- `GET /campaigns/{id}/metrics?date_from&date_to`

### Keywords + Ads
- `GET /keywords/?client_id=X&campaign_type=&status=&match_type=&date_from=&date_to=`

### Search Terms
- `GET /search-terms/?client_id=X&search=&sort_by=&page=`
- `GET /search-terms/segmented?client_id=X` → grouped by segment + summary
- `GET /search-terms/summary?campaign_id=X`

### Recommendations
- `GET /recommendations/?client_id=X&priority=X&status=X`
- `GET /recommendations/summary?client_id=X` → badge counts
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- `POST /recommendations/{id}/dismiss`

### Actions
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X`

### Analytics (Core)
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/dashboard-kpis?client_id=X&days=30`
- `GET /analytics/campaigns?client_id=X`
- `GET /analytics/anomalies?client_id=X&status=unresolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`
- `POST /analytics/detect?client_id=X`

### Analytics (V2 — Trends & Insights)
- `GET /analytics/trends?client_id=X&metrics=&days=`
- `GET /analytics/health-score?client_id=X`
- `GET /analytics/campaign-trends?client_id=X&days=7`
- `GET /analytics/budget-pacing?client_id=X`
- `GET /analytics/quality-score-audit?client_id=X`
- `GET /analytics/forecast?campaign_id=X&metric=&forecast_days=`
- `GET /analytics/impression-share?client_id=X`
- `GET /analytics/device-breakdown?client_id=X`
- `GET /analytics/geo-breakdown?client_id=X`

### Analytics (SEARCH Optimization)
- `GET /analytics/dayparting?client_id=X&days=30`
- `GET /analytics/rsa-analysis?client_id=X`
- `GET /analytics/ngram-analysis?client_id=X&ngram_size=1&min_occurrences=2`
- `GET /analytics/match-type-analysis?client_id=X&days=30`
- `GET /analytics/landing-pages?client_id=X&days=30`
- `GET /analytics/wasted-spend?client_id=X&days=30`

### Export
- `GET /export/search-terms?client_id=X&format=xlsx`
- `GET /export/keywords?client_id=X&format=xlsx`

### Semantic
- `GET /semantic/clusters?client_id=X`

### History (Change Events)
- `GET /history/?client_id=X&date_from=&date_to=&resource_type=`
- `GET /history/unified?client_id=X` → merged action_log + change_events
- `GET /history/filters?client_id=X` → dropdown values

### Health
- `GET /health` → {status: "ok", version, env}

---

## DOCUMENTATION HIERARCHY

Read in this order when you need context:
1. **CLAUDE.md** (this file) — quick reference, rules, architecture
2. **PROGRESS.md** — what's done, what to build next
3. **DECISIONS.md** — 12 ADRs (architecture decisions)
4. **Implementation_Blueprint.md** — original backend code reference
5. **Blueprint_Patch_v2_1.md** — 3 critical additions (revert, analytics, segmentation)
6. **PRD_Core.md** — product requirements, features, acceptance criteria
7. **Technical_Spec.md** — frontend API contract
8. **google_ads_optimization_playbook.md** — domain knowledge reference
9. **JAK_ZDOBYC_CREDENTIALS.md** — Google Ads API credentials setup guide

---

## COMMANDS

```bash
# Backend
cd backend && pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Full app (PyWebView)
python main.py

# Build exe
pyinstaller --onefile --windowed main.py
```

---

## COMPLETED FEATURES — DO NOT MODIFY UNLESS ASKED

These features are done and tested. Do NOT refactor, "improve", or touch them without explicit user request.

### PMax Search Terms
- `sync_pmax_search_terms()` uses `campaign_search_term_view` (NOT `search_term_view`, NOT `campaign_search_term_insight`)
- CRITICAL: Do NOT add `segments.keyword.info.*` to campaign_search_term_view queries — it filters out PMax data
- SearchTerm model: `ad_group_id` is nullable (PMax has no ad_groups), `campaign_id` FK for PMax direct link, `source` column ("SEARCH"/"PMAX")
- Sync Phase 5b calls `sync_pmax_search_terms()` after standard `sync_search_terms()`

### Global Date Range Picker
- DateRangePicker component lives in Sidebar.jsx (after client selector, before nav)
- FilterContext exposes: `filters.period`, `filters.dateFrom`, `filters.dateTo`, computed `days`
- Period preset (7/14/30/90) auto-sets dateFrom/dateTo. Custom dates clear period to null.
- Pages using dates: Dashboard (`days`), Campaigns (`days`), TrendExplorer (`days`), SearchTerms (`date_from`/`date_to`), Keywords (`date_from`/`date_to` via KeywordDaily)
- Campaigns list: snapshot data — NO date filtering
- Keywords: date filtering aggregates from `keywords_daily` table (SUM per keyword); without dates falls back to Keyword snapshot
- FilterBar period pills hidden (`hidePeriod`) since dates are global in sidebar

### AppContext — Centralized Client State
- `clients`, `clientsLoading`, `refreshClients` live in AppContext (NOT useClients hook)
- Sidebar.jsx reads clients from useApp(), NOT from useClients()
- After discover, clients appear immediately in sidebar dropdown

### Auth Setup Wizard
- `GET /auth/setup-status`, `POST /auth/setup` endpoints in auth.py
- Login.jsx has step-by-step credential setup before Google OAuth
- All tokens stored in Windows Credential Manager via keyring

### KeywordDaily (Date Aggregation)
- Model `KeywordDaily`: keyword_id + date → clicks, impressions, cost_micros, conversions, conversion_value_micros, avg_cpc_micros
- Router `keywords_ads.py`: two paths — daily aggregation (with date_from/date_to) vs snapshot (without dates)
- Seed: 90 days per keyword with trend + dow + noise factors
- Summable metrics in KeywordDaily; snapshot metrics (quality_score, impression_share, bid) stay on Keyword model

### SEARCH Optimization Page
- `SearchOptimization.jsx` — 6 collapsible analysis sections
- Endpoints: dayparting, rsa-analysis, ngram-analysis, match-type-analysis, landing-pages, wasted-spend
- Backend: 6 methods in analytics_service.py + 6 routes in analytics.py
- Sidebar nav: "Optymalizacja" (Zap icon) in ANALIZA group

---

## SQLITE SCHEMA NOTES

- No Alembic migrations. Adding/removing columns = delete DB file + reseed
- DB location when running from `backend/`: `backend/data/google_ads_app.db`
- DB location when running from root: `data/google_ads_app.db`
- Run seed: `cd backend && PYTHONIOENCODING=utf-8 python -m app.seed`

---

## WHEN IN DOUBT

- If a requirement is ambiguous → check Blueprint v2.0 + Patch v2.1 first
- If Blueprint and PRD conflict → Blueprint wins (it's newer and corrected)
- If Patch v2.1 and Blueprint v2.0 conflict → Patch wins
- If nothing covers it → ASK. Do NOT improvise.
