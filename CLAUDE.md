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

## FILE TREE (STRICT)

```
google-ads-helper/
├── main.py                              # PyWebView entry point
├── requirements.txt                     # Pinned Python deps
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
│       │
│       ├── models/                      # Layer 3: SQLAlchemy ORM
│       │   ├── __init__.py              # Exports all models
│       │   ├── client.py
│       │   ├── campaign.py
│       │   ├── keyword.py
│       │   ├── search_term.py
│       │   ├── recommendation.py
│       │   ├── action_log.py            # Has reverted_at column + REVERTED status
│       │   └── alert.py
│       │
│       ├── schemas/                     # Layer 4: Pydantic v2 schemas
│       │   ├── __init__.py
│       │   ├── common.py               # Enums: Priority, Status, ActionType
│       │   ├── client.py
│       │   ├── campaign.py             # Micros→USD conversion HERE
│       │   ├── recommendation.py
│       │   └── search_term.py
│       │
│       ├── routers/                     # Layer 6: FastAPI routes (thin)
│       │   ├── __init__.py
│       │   ├── auth.py                  # /auth/login, /auth/callback, /auth/status
│       │   ├── clients.py              # /clients, /clients/{id}/sync
│       │   ├── campaigns.py
│       │   ├── keywords.py
│       │   ├── search_terms.py         # /search-terms/segmented, /search-terms/
│       │   ├── recommendations.py
│       │   ├── actions.py              # /actions/, /actions/revert/{id}
│       │   └── analytics.py            # /analytics/kpis, /analytics/anomalies
│       │
│       ├── services/                    # Layer 5: Business logic
│       │   ├── __init__.py
│       │   ├── credentials_service.py   # Keyring wrapper (ONLY place for tokens)
│       │   ├── google_ads_client.py     # GAQL executor + write ops
│       │   ├── sync_service.py          # 6-phase sync orchestrator
│       │   ├── recommendations_engine.py # 7 optimization rules
│       │   ├── action_executor.py       # Apply + Revert + circuit breaker
│       │   ├── analytics_service.py     # KPIs + anomaly detection
│       │   └── search_terms_service.py  # Segmentation logic
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logger.py               # Rotating file logger
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
│       ├── api.js                       # Axios (baseURL: http://localhost:8000)
│       │
│       ├── components/
│       │   ├── KPICard.jsx
│       │   ├── Charts.jsx              # Recharts wrappers
│       │   ├── Sidebar.jsx
│       │   ├── ConfirmationModal.jsx    # Before/After preview
│       │   ├── Toast.jsx
│       │   ├── DataTable.jsx           # TanStack Table wrapper
│       │   └── SegmentBadge.jsx        # Color-coded segment labels
│       │
│       ├── pages/
│       │   ├── Dashboard.jsx
│       │   ├── Clients.jsx
│       │   ├── Campaigns.jsx
│       │   ├── Keywords.jsx
│       │   ├── SearchTerms.jsx         # Segment cards + filterable list
│       │   ├── Recommendations.jsx     # Priority badges + Apply/Dismiss
│       │   ├── ActionHistory.jsx       # Chronological + Undo button
│       │   ├── Alerts.jsx              # Unresolved/Resolved tabs
│       │   └── Settings.jsx
│       │
│       └── hooks/
│           ├── useClients.js
│           ├── useRecommendations.js
│           └── useSync.js
│
├── database/
│   ├── google_ads.db                    # SQLite — GITIGNORED
│   └── backups/                         # Auto-backups before Apply
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

## SYNC FLOW (6 Phases)

```
POST /clients/{id}/sync → SyncService.sync_client(client_id)
  │
  ├─ PHASE 1: Campaigns (GAQL) → _upsert_campaign() × N → commit
  ├─ PHASE 2: Keywords (GAQL) → _upsert_keyword() × N → commit
  ├─ PHASE 3: Search Terms (GAQL) → delete old → _insert_search_term() × N → commit
  ├─ PHASE 4: Segmentation → SearchTermsService.segment_all_search_terms() → commit
  ├─ PHASE 5: Anomaly Detection → AnalyticsService.detect_and_save_anomalies() → commit
  └─ PHASE 6: Update last_synced_at → commit → return stats
```

Phases 4-5 are non-critical: if they fail, log error but DON'T rollback sync data.

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

## UI DESIGN

- **Dark mode** default
- Colors: bg=#0F172A, sidebar=#1E293B, cards=#334155, text=#F1F5F9, accent=#3B82F6
- Success=#10B981, Warning=#F59E0B, Danger=#EF4444
- Design reference: Linear, Vercel Dashboard
- Use Tailwind CSS + shadcn/ui components
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
- `GET /clients` → list of clients
- `GET /clients/{id}` → client detail
- `POST /clients/{id}/sync` → trigger sync

### Campaigns
- `GET /campaigns?client_id=X`

### Keywords
- `GET /keywords?campaign_id=X`

### Search Terms
- `GET /search-terms/?client_id=X&segment=X`
- `GET /search-terms/segmented?client_id=X` → grouped by segment + stats

### Recommendations
- `GET /recommendations?client_id=X&priority=X&status=X`
- `GET /recommendations/summary?client_id=X` → badge counts
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- `POST /recommendations/{id}/dismiss`

### Actions
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X`

### Analytics
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/campaigns?client_id=X`
- `GET /analytics/anomalies?client_id=X&status=unresolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`
- `POST /analytics/detect?client_id=X`

### Health
- `GET /health` → {status: "ok"}

---

## DOCUMENTATION HIERARCHY

Read in this order when you need context:
1. **CLAUDE.md** (this file) — quick reference, rules, architecture
2. **PROGRESS.md** — what's done, what to build next
3. **Implementation_Blueprint.md** — full backend code (copy-paste ready)
4. **Blueprint_Patch_v2_1.md** — 3 critical additions (revert, analytics, segmentation)
5. **PRD_Core.md** — product requirements, features, acceptance criteria
6. **google_ads_optimization_playbook.md** — domain knowledge reference

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

## WHEN IN DOUBT

- If a requirement is ambiguous → check Blueprint v2.0 + Patch v2.1 first
- If Blueprint and PRD conflict → Blueprint wins (it's newer and corrected)
- If Patch v2.1 and Blueprint v2.0 conflict → Patch wins
- If nothing covers it → ASK. Do NOT improvise.
