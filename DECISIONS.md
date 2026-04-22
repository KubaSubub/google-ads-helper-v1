# DECISIONS.md — Architecture Decision Records
# Documents WHY specific decisions were made. Do NOT reverse these without PM approval.

---

## ADR-001: SQLite over PostgreSQL
**Decision:** Use SQLite for local database
**Why:** Local-first app for 1 user, 2-10 clients, <500MB data. No server needed. PostgreSQL adds install complexity for zero benefit at this scale.
**Trade-off:** No concurrent writes (acceptable — single user app).
**Revisit if:** App becomes multi-user or SaaS.

## ADR-002: BigInteger (micros) over REAL for monetary values
**Decision:** Store ALL money as BigInteger in micros (1 USD = 1,000,000 micros)
**Why:** REAL/float causes rounding errors in financial calculations. Google Ads API returns micros natively.
**Rule:** Convert to float ONLY in Pydantic schemas (API response layer). Never in models or services.
**Note:** PRD Section 4.3 incorrectly suggests `REAL` — IGNORE that. Blueprint Patch v2.1 overrides it.

## ADR-003: PyWebView over Electron
**Decision:** Use PyWebView (Edge WebView2 on Windows) for desktop wrapper
**Why:** Same Python backend, no Node.js dependency, smaller bundle (~35MB vs ~120MB). Native-feeling window. Can migrate to Electron later if needed.
**Trade-off:** Less ecosystem than Electron, Windows-only rendering engine.

## ADR-004: Windows Credential Manager (keyring) over .env files
**Decision:** Store OAuth tokens in Windows Credential Manager via `keyring` library
**Why:** Encrypted at OS level. .env files are plaintext, easily leaked via git or file access.
**Rule:** `credentials_service.py` is the ONLY file that reads/writes tokens. No exceptions.

## ADR-005: Manual sync over auto-sync (MVP) — SUPERSEDED
**Decision:** Sync triggered manually via "Refresh" button only
**Why:** Simpler architecture, no background scheduler needed, user controls when data refreshes.
**Future:** Add APScheduler for daily auto-sync in v1.1 if requested.
**SUPERSEDED:** F1 Scheduled Sync implemented (2026-03-29) — asyncio-based `ScheduledSync` model with per-client schedules (`GET/POST/DELETE /sync/schedule`), no external scheduler dependency (built-in asyncio only). Manual sync still available alongside.

## ADR-006: Segment after sync (batch) over during sync (real-time)
**Decision:** Search term segmentation runs as Phase 4 AFTER sync completes
**Why:** Keeps sync fast (just store data), decouples business logic from data ingestion.
**Trade-off:** User sees unsegmented data briefly after sync. Acceptable for MVP.

## ADR-007: 24-hour revert window
**Decision:** Actions can only be undone within 24 hours
**Why:** After 24h, the account state may have changed due to external factors (Google auto-optimizations, other users editing). Reverting old actions is unsafe.
**Exception:** ADD_NEGATIVE is NEVER revertable (removing negatives immediately re-enables bad traffic).

## ADR-008: Threshold-based anomaly detection over statistical (MVP) — SUPERSEDED
**Decision:** Use simple thresholds (1.5× spend, 0.5% CTR floor) instead of Z-score/IQR
**Why:** MVP simplicity. Statistical methods need sufficient historical daily data which we don't store per-day in MVP schema (only 30-day aggregates).
**Future:** v1.1 will add daily metrics table → enable proper statistical detection.
**SUPERSEDED:** Z-score anomaly detection implemented (2026-03-30) — `GET /analytics/z-score-anomalies` with per-campaign per-day z-score detection. `KeywordDaily` and `MetricDaily` tables provide the daily granularity needed for statistical methods. Threshold-based detection still active alongside z-score as complementary approach.

## ADR-009: React hooks over Redux/Zustand
**Decision:** Use useState + useContext for state management
**Why:** App has simple state (selected client, sync status, recommendations list). No global state complexity warrants a state library.
**Revisit if:** App grows to 15+ pages with shared cross-page state.

## ADR-010: FastAPI serves React build in production
**Decision:** In production, FastAPI serves the built React app (`frontend/dist/`) as static files
**Why:** Single process = simpler PyWebView integration. No CORS issues. One port (8000).
**Dev mode:** React runs on port 5173 (Vite dev server), proxied to FastAPI on 8000.

## ADR-011: No Alembic migrations for MVP — PARTIALLY SUPERSEDED
**Decision:** Use `Base.metadata.create_all()` for schema creation
**Why:** Single user, no production database to migrate. If schema changes, user can re-sync (data comes from Google Ads API anyway).
**Future:** Add Alembic when schema is stable and user has historical data worth preserving.
**PARTIALLY SUPERSEDED:** Schema Auto-Migration in `database.py` now auto-adds missing columns (labels, target_cpa_micros, target_roas, etc.) without requiring DB delete + reseed. Full Alembic still not used.

## ADR-012: Dark mode only (MVP)
**Decision:** Dark mode default, no light mode toggle
**Why:** Faster development, consistent design. Target user works long hours — dark mode preferred.
**Future:** Add toggle in v1.1 Settings page.

## ADR-013: Canonical runtime SQLite path
**Decision:** Resolve SQLite runtime data to a single canonical path independent of current working directory.
**Why:** The previous relative `./data/google_ads_app.db` created two different databases depending on whether the app started from repo root or `backend/`.
**Rule:** Source mode uses `<repo>/data/google_ads_app.db`; frozen mode uses `<exe_dir>/data/google_ads_app.db`.
**Migration:** If the canonical DB does not exist and legacy `backend/data/google_ads_app.db` does, move the DB and SQLite sidecar files once before engine startup.

## ADR-014: Missing rows after successful sync become REMOVED, not deleted
**Decision:** Campaigns, ad groups, and keywords missing from a successful full sync are marked `REMOVED` locally.
**Why:** We need historical/debug visibility without polluting default working views with stale cache rows.
**UI rule:** Default keyword list hides `REMOVED`; users can opt in via `include_removed` / local toggle.
**Trade-off:** Local DB keeps tombstones longer, but behavior is explainable and safer than hard-deleting rows.

## ADR-015: Positive and negative keywords use separate canonical caches
**Decision:** Keep positive keywords in `keywords` and negative keyword criteria in `negative_keywords`; do not merge them into one table.
**Why:** Positive keywords carry bids, serving state, and performance metrics that do not apply cleanly to negatives. A unified table would increase null-heavy ambiguity and repeat the exact class of bug that caused the incident.
**Rule:** Both caches expose explicit `criterion_kind` values (`POSITIVE`, `NEGATIVE`), and positive sync must reject `negative=true` rows at query, mapping, and before-save layers.
**Scope:** `negative_keywords` is canonical for campaign-level and ad-group negative keyword criteria. No account-level negative cache in the current milestone.

## ADR-016: AI report generation uses local Claude CLI streaming
**Decision:** Integrate AI report generation through local Claude CLI (`claude -p --output-format stream-json`) invoked as a backend subprocess.
**Why:** The app is local-first and desktop-oriented; local CLI integration avoids adding a second remote LLM credential/token flow into app storage and keeps runtime behavior aligned with user-managed Claude installation.
**Rule:** Backend streams generated content to frontend via SSE and treats CLI availability as runtime capability (`/api/v1/agent/status`), not as a startup hard dependency.
**Trade-off:** Behavior depends on local CLI installation/version and PATH correctness; failure paths must degrade gracefully with explicit user-facing error events.

## ADR-017: AI report generation is single-flight per backend process
**Decision:** Allow only one active AI report generation at a time using an in-memory `asyncio.Lock`.
**Why:** The product is single-user desktop-first; parallel report generation provides limited user value but increases risk of resource contention, overlapping stream handling, and degraded UX stability.
**Rule:** If generation is already in progress, the next request returns a busy SSE error and closes with `done`.
**Trade-off:** No concurrent report generation in the same backend process; users must retry after completion.
**Revisit if:** Multi-user/server mode or queued background report jobs become a product requirement.

## ADR-018: Google Ads API version tracking and upgrade policy
**Decision:** Track the Google Ads API version (via `google-ads` Python SDK) as a first-class dependency. Before implementing any new Google Ads feature, verify the minimum API version required and check if our SDK version supports it.
**Current state:** `google-ads==29.1.0` (API v23, explicitly pinned). Client initialized with `version="v23"`.
**Why:** Google frequently unlocks new capabilities in newer API versions (e.g., PMax campaign-level negatives require API v20, June 2025). Building features against an unsupported API version wastes effort and creates silent failures. The SDK version is the single source of truth for what the API can do.
**Rule:** When planning features that touch Google Ads mutations or new resource types, check the [Google Ads API release notes](https://developers.google.com/google-ads/api/docs/release-notes) for minimum version. Document the required version in the feature task. Update `requirements.txt` and test before shipping.
**Known version gates:**
- API v23 (SDK 29.1.0): current pinned version — all existing features + PMax negatives unlocked
- API v20+ (SDK >=27.x): PMax campaign-level negative keywords (limit 10k/campaign), PMax granular reporting — AVAILABLE since SDK 29.1.0
- API v18 (SDK >=25.x): historical baseline (superseded)
**Revisit:** On every major feature that touches Google Ads API write operations.

## ADR-019: Pin Google Ads SDK version and declare API version explicitly
**Decision:** Pin `google-ads==29.1.0` in requirements.txt (was `>=25.1.0`) and pass `version="v23"` explicitly to `GoogleAdsClient.load_from_dict()`.
**Why:** The loose pin `>=25.1.0` caused a silent upgrade from SDK 25.x (API v18) to SDK 29.1.0 (API v23). Documentation and ADR-018 still referenced API v18, while production code was already running on v23. This created a documentation-reality mismatch: PMax negatives were technically available but not recognized as such.
**Rule:** Always pin the SDK to an exact version (`==`). Always pass the API version explicitly to the client constructor. Update both when upgrading.
**Trade-off:** Requires manual `requirements.txt` update for SDK upgrades — this is intentional to force conscious version management.

## ADR-020: Sync lives only in MCC Overview — `incremental` is the only default
**Decision:** All sync UI and logic are consolidated into the MCC Overview page. No sync buttons in Sidebar, Settings, or anywhere else. The `incremental` preset is the only default sync mode across the app (app startup, bulk "Synchronizuj nieaktualne").
**Rules:**
- **App startup (auto):** `clients/discover` runs silently, then for each client:
  - existing client with `coverage.data_to` → `incremental` (from `data_to + 1` to yesterday)
  - new client (no coverage) → fixed **30 days**
  - no other scenarios at startup
- **Manual sync in MCC Overview:** checkbox rows → "Synchronizuj" button → modal with **two** options only:
  - **Pełny** — full history per phase (max `max_days` from `PHASE_REGISTRY`)
  - **Ostatnie N dni** — user enters N, applied to all phases
- `quick` and `metrics_only` presets removed from UI. `incremental` and `full` remain in backend; `fixed` is used by the "N dni" option.
- `date_to` is always yesterday (today is incomplete per Google Ads API).
**Why:** Previous state had 3 sync entry points (MCC, Sidebar, Settings), 3 different default periods (30d / 30d / 90d), 4 presets, plus a background scheduler with its own hardcoded 30d path — none of them agreed. Single entry point + single default removes confusion and API quota waste.
**Supersedes:** ADR-005 (manual-only), the F1 scheduled sync asyncio loop (`services/scheduler.py` disabled), and the multi-preset modal.
**Removed code:** `components/SyncButton.jsx`, `hooks/useSync.js`, `handleSync` dead path in MCC, Settings "Synchronizuj teraz", Sidebar per-client sync button, `POST /sync/trigger` (replaced by `/sync/trigger-stream` everywhere).


## ADR-021: Analytics god-object split — mixin pattern for service, sub-router package for API
**Decision (2026-04-22):** Split two analytics trunks — `backend/app/services/analytics_service.py` (5418 lines, 51 methods) and `backend/app/routers/analytics.py` (3038 lines, 83 endpoints) — into domain modules with zero URL change and zero caller change.

**Structure — service (`app/services/analytics/`):**
- `_shared.py` owns `AnalyticsBase(__init__(db), _filter_campaigns, _filter_campaign_ids, _aggregate_metric_daily, _create_alert)` — helpers used by 5–30 domain methods
- 11 domain mixins (`kpi`, `health`, `breakdown`, `quality`, `pacing`, `bidding`, `waste`, `insights`, `pmax`, `comparison`, `dsa`) — each a stateless mixin class requiring `self.db` from `AnalyticsBase`
- `analytics_service.py` reduced to 37 lines: `class AnalyticsService(KPIMixin, ..., AnalyticsBase)` — pure composition, backward-compatible

**Structure — router (`app/routers/analytics/`):**
- Package with `__init__.py` aggregating 16 sub-routers (15 domain + `_legacy` stub) under `prefix="/analytics"`
- One sub-router per domain (`_kpis`, `_health`, `_breakdown`, ...) — each `APIRouter()` without prefix, included via `router.include_router(sub)`
- URLs unchanged; `main.py` `include_router(analytics.router, prefix=API_PREFIX)` unchanged (package exposes `router` attribute)

**Why:** Both files acted as trunks, not leaves — every new analytic method or endpoint compounded tech slop because Claude reading them would mirror their style. Per-domain files cap cognitive load per edit and make it possible to co-locate tests.

**Rules going forward (added to AGENTS.md):**
- No single service file in `backend/app/services/` exceeds 1000 lines
- No single router file in `backend/app/routers/` exceeds 600 lines
- When adding an analytics method, extend the appropriate mixin (`app/services/analytics/<domain>.py`); don't add to `analytics_service.py`
- When adding an analytics endpoint, add to the appropriate sub-router (`app/routers/analytics/_<domain>.py`); don't reopen `_legacy.py`

**Migration:**
- Backward compat preserved: `from app.services.analytics_service import AnalyticsService` + `from app.routers.analytics import router` both still work
- Only one test needed updating: `test_date_boundaries.py` patched `app.routers.analytics.date` (now lives in `_pacing.date`)
- 806 backend tests green after full split; 83 unique URLs, 0 duplicates (fixed pre-existing `/shopping-product-groups` shadow by renaming the tree variant to `/shopping-product-groups-tree`)

**Trade-off accepted:** Slight increase in total line count (5418 → 5881) from repeated imports per mixin; paid for by domain-local edits and cleaner git diffs.
