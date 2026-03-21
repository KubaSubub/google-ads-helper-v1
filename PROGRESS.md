# PROGRESS.md - Implementation Status
# Updated: 2026-03-21 (189934d)

## Status
- Backend: 355 tests passing (`pytest --tb=short -q`)
- Frontend: unified global filtering (Category A/B) + Playwright E2E (19 smoke tests)
- Roadmap features delivered: Weekly/Health reports, search-term-trends, close-variants, conversion-health, keyword-expansion
- Filtering: `date_from`/`date_to` + `campaign_type`/`campaign_status` unified across ~20 analytics endpoints

## Frontend Filtering Iteration 1
- Added a shared top-level global filter bar in `frontend/src/components/GlobalFilterBar.jsx`
- Global filters now consistently cover:
  - active client
  - date range
  - campaign type
  - campaign status
- Campaign type and campaign status now use single-select dropdowns with default `Wszystkie`
- Removed duplicated global filter UI from sidebar, dashboard, campaigns, keywords, and search terms
- Preserved existing local view filters such as keyword match type/include removed and search-term view mode/search/segment
- No backend or API contract changes were required

## Completed In This Milestone

### Phase 1 - Campaign Roles
- Added deterministic campaign role service in `backend/app/services/campaign_roles.py`
- Expanded `Campaign` model and API with:
  - `campaign_role_auto`
  - `campaign_role_final`
  - `role_confidence`
  - `protection_level`
  - `role_source`
- Added `PATCH /api/v1/campaigns/{campaign_id}` for manual role override / reset
- Enforced contract that manual override is never overwritten by sync/classifier
- Added Campaigns UI controls for role override, confidence, and protection display

### Phase 2 - Context-Aware Budget Guardrails
- Expanded `Recommendation` model with:
  - `context_outcome`
  - `blocked_reasons`
  - `downgrade_reasons`
- Added fixed reason-code contract in `backend/app/services/recommendation_contract.py`
- Reworked budget rules:
  - `REALLOCATE_BUDGET` now respects role comparability, protection, unknown-role blocking, and deterministic `can_scale`
  - `IS_BUDGET_ALERT` becomes executable only for healthy lost-IS scenarios
- Persisted and serialized structured context through recommendation API

### Phase 3 - Explanation Layer and UI
- Added explanation blocks to recommendation evidence:
  - `why_allowed`
  - `why_blocked`
  - `tradeoffs`
  - `risk_note`
  - `next_best_action`
- Recommendations UI now renders:
  - context outcome badge
  - role/protection/headroom chips
  - explanation sections built from reason codes
  - disabled apply for non-executable cards
- Summary widgets now expose `ACTION` and `BLOCKED_BY_CONTEXT` counts

### Execution / Safety Follow-Through
- Confirmed canonical execution flow for:
  - `PAUSE_KEYWORD`
  - `UPDATE_BID`
  - `ADD_KEYWORD`
  - `ADD_NEGATIVE` (campaign-level)
  - `PAUSE_AD`
  - `INCREASE_BUDGET`
- Kept `REALLOCATE_BUDGET` non-executable by design
- Added expiry and precondition regression coverage
- Replaced backend `datetime.utcnow()` usages that were generating warnings in covered paths

### Frontend Testing
- Added Vitest + Testing Library setup
- Added recommendations UI tests for:
  - context outcome rendering
  - explanation copy from reason codes
  - disabled apply for `INSIGHT_ONLY` / `BLOCKED_BY_CONTEXT`

## Validation
- Backend tests passed:
  - `tests/test_campaign_roles.py`
  - `tests/test_human_centered_recommendations.py`
  - `tests/test_write_actions_flow.py`
  - `tests/test_api_contract_smoke.py`
  - `tests/test_recommendations_contract.py`
- Frontend tests passed:
  - `npm run test`
- Frontend production build passed with Vite

## Open Follow-ups
- Add more frontend coverage for Campaigns role override interactions and dry-run modal rendering
- Add backend coverage for Google-native cache invalidation edge cases
- Decide future executable allowlist for Google-native recommendation types after safety review
- Address one npm audit high-severity dependency warning in frontend toolchain
- Consider code-splitting frontend bundle (current build warning > 500 kB)

## Keyword Lifecycle Cleanup and Canonical SQLite (2026-03-12)
- Added successful-sync cleanup for campaigns, ad groups, and keywords so stale local rows are marked `REMOVED` instead of lingering forever.
- Keyword API now returns campaign context (`campaign_id`, `campaign_name`, `ad_group_name`) and hides `REMOVED` keywords by default unless `include_removed=true`.
- Keywords export now supports `campaign_id` and `include_removed`, and includes campaign/ad group columns.
- Keywords UI now shows campaign context, real keyword status badges, delivery issue badges next to the keyword, a local `Pokaz usuniete` toggle, and readable action labels/tooltips.
- Runtime data path is now canonicalized to `<repo>/data/google_ads_app.db` with one-time migration from legacy `backend/data/google_ads_app.db`.

## Validation (2026-03-12)
- Backend tests passed:
  - `backend/tests/test_keyword_sync_cleanup.py`
  - `backend/tests/test_api_contract_smoke.py`
- Frontend tests passed:
  - `frontend/src/pages/Keywords.test.jsx`
- Frontend production build passed:
  - `cd frontend && npm run build`

## Client Hard Reset (2026-03-12)
- Added `POST /api/v1/clients/{client_id}/hard-reset` to wipe only one client's local runtime data while keeping the client profile.
- Added a guarded `Twardy reset danych klienta` section in Settings with typed-name confirmation.

## Validation (client hard reset)
- Backend tests passed:
  - `backend/tests/test_client_hard_reset.py`
- Frontend tests passed:
  - `frontend/src/pages/Settings.test.jsx`
- Frontend production build passed:
  - `cd frontend && npm run build`


## Keyword Source Diagnostics (2026-03-12)
- Added GET /api/v1/sync/debug/keywords to compare raw Google Ads keyword_view rows with local SQLite keyword rows for a single client.
- Diagnostic payload includes normalized customer ID, repeated search filters, exact GAQL query, raw API matches, and local DB matches.

## Keyword Source Of Truth and Negative Criterion Fix (2026-03-13)
- Added `GET /api/v1/sync/debug/keyword-source-of-truth` for one-criterion diagnostics across `keyword_view`, `ad_group_criterion`, local SQLite, Google Ads `request_id`, `ListAccessibleCustomers`, and MCC `customer_client` lookup.
- Confirmed the disputed Sushi Naka Naka criterion `33694032` is a negative ad group criterion (`negative=true`), not a positive keyword.
- Fixed keyword sync to exclude `ad_group_criterion.negative = true`, so negative criteria are no longer persisted into the local `keywords` table.
- Re-synced the affected client and the disputed `bydgoszcz` rows are now `REMOVED` locally and hidden from the default keyword view.
- Verified on a temporary database copy that hard reset clears the client's local rows and, after the sync fix, the disputed criterion is not recreated.

## Validation (2026-03-13)
- Backend tests passed:
  - `backend/tests/test_sync_debug_keywords.py`
  - `backend/tests/test_keyword_sync_cleanup.py`
  - `backend/tests/test_client_hard_reset.py`
  - `backend/tests/test_api_contract_smoke.py`

## Negative Keyword Cleanup and Sync Hardening (2026-03-13)
- Expanded `negative_keywords` from a campaign-level shadow table into the canonical negative keyword cache with explicit `criterion_kind`, `negative_scope`, `source`, Google criterion identifiers, and `updated_at`.
- Positive keyword cache (`keywords`) now carries explicit `criterion_kind='POSITIVE'`.
- Added dedicated `sync_negative_keywords()` for ad-group and campaign negatives.
- Hardened positive keyword sync at query, mapping, and before-save layers; negative rows now emit warnings and are never persisted into `keywords`.
- Added backend-only `GET /api/v1/negative-keywords/`.
- Reworked keyword debug payloads so source-of-truth differentiates API rows, DB positive rows, DB negative rows, and active/legacy SQLite paths.
- Strengthened runtime diagnostics so `/sync/debug` also shows active and legacy DB paths.

## Validation (negative keyword cleanup)
- Backend tests passed:
  - `backend/tests/test_sync_debug_keywords.py`
  - `backend/tests/test_keyword_sync_cleanup.py`
  - `backend/tests/test_client_hard_reset.py`
  - `backend/tests/test_api_contract_smoke.py`

## Demo Runtime Clone (2026-03-13)
- Added `POST /api/v1/clients/{id}/clone-runtime?source_client_id=Y` to copy local runtime data from source client to target client.
- Endpoint clears target client runtime data first (same policy as hard reset), then clones:
  - campaigns, ad groups, keywords, keyword daily metrics
  - daily + segmented metrics
  - search terms
  - recommendations, negative keywords, alerts
  - action log, change events, sync logs
- Intended for fast demo setup without mutating real Google Ads accounts.

## Validation (demo runtime clone)
- Verified API endpoint is exposed and clone operation executed for DEMO target in local run.
- Frontend/Backend runtime smoke checks performed through live API:
  - `/health`
  - `/api/v1/auth/status?bootstrap=1`
  - `/api/v1/clients/`
  - `/api/v1/campaigns/?client_id=<demo>`

## Legacy Demo Restore (2026-03-13)
- Reverted frontend-only DEMO data remapping (no cross-client data substitution in UI reads).
- Added `POST /api/v1/clients/{id}/restore-runtime-from-legacy`:
  - source: `backend/data/google_ads_app.db` (legacy DB)
  - target: canonical runtime DB from `settings.database_url` (currently `data/google_ads_app.db`)
  - matching: by target client `google_customer_id` (fallback: first legacy client with `name LIKE '%demo%'`)
  - optional override: `source_client_id`
- Restore pipeline:
  - hard reset target client runtime data
  - restore campaigns, ad groups, keywords, keyword daily
  - restore daily + segmented metrics
  - restore search terms
  - restore recommendations, negative keywords, alerts
  - restore sync logs and change events (with unique `resource_name` suffix to avoid global conflicts)

## Validation (legacy demo restore)
- Confirmed both DB files exist and differ:
  - canonical: `data/google_ads_app.db`
  - legacy: `backend/data/google_ads_app.db`
- Confirmed runtime currently uses canonical DB (`/api/v1/sync/debug`).
- Automated endpoint execution is pending backend process reload/restart in desktop shortcut runtime.

## DEMO Write Lock (2026-03-13)
- Added backend DEMO guard (`backend/app/demo_guard.py`) with protected identity based on:
  - `settings.demo_google_customer_id`
  - optional `settings.demo_client_id` hard pin
- Added config switches:
  - `demo_protection_enabled` (default `True`)
  - `demo_client_id` (default `None`)
  - `demo_google_customer_id` (default `123-456-7890`)
- Enforced lock on write paths:
  - client mutations (`PATCH`, `DELETE`, `hard-reset`, `clone-runtime`, `restore-runtime-from-legacy`)
  - sync mutations (`/sync/trigger`, `/sync/phase/*`)
  - recommendation actions (`apply`, `dismiss`)
  - action revert
  - analytics writes (`anomalies resolve`, `detect`)
  - campaign role override (`PATCH /campaigns/{id}`)
- Override is explicit and per-request only: `allow_demo_write=true`.

## Validation (demo lock + demo restore)
- Restored DEMO from legacy data source:
  - `POST /api/v1/clients/4/restore-runtime-from-legacy`
  - restored counts included campaigns/ad groups/keywords/metrics/search terms/recommendations/history.
- Runtime smoke after restore:
  - `campaigns total=7`
  - `recommendations total=26`
  - `history total=35`
- Note: lock validation requires backend process restart to load latest code in the currently running desktop process.

## DEMO Showcase Seeder + Forecast Alias Fix (2026-03-13)
- Added `POST /api/v1/clients/{id}/seed-demo-showcase` (DEMO-only, write-override required):
  - seeds recent `keywords_daily` rows (14-90 days),
  - seeds RSA-style `ads` rows for SEARCH ad groups,
  - seeds helper `action_log` entries (`execution_mode=DEMO_SEED`),
  - seeds curated DEMO `search_terms`,
  - injects a controlled subset of zero-conversion spend patterns for showcase quality (`wasted-spend` visibility).
- Added forecast metric aliases in backend:
  - `cost` -> `cost_micros`
  - `cpc` -> `avg_cpc_micros`
  - micros metrics are normalized to currency units in forecast response values.
- Added frontend compatibility mapping in `getForecast()` for the same aliases.
- Cleaned duplicate demo tenant in runtime by deleting `client_id=5` (`DEMO - Prezentacja`) after hard reset, leaving one canonical DEMO client.

## Validation (showcase + cleanup)
- Runtime API checks before/after cleanup:
  - `/api/v1/clients` confirmed duplicate demo client existed and was removed.
  - `POST /api/v1/clients/5/hard-reset` -> `200`
  - `DELETE /api/v1/clients/5` -> `200`
- Runtime smoke after seeding:
  - `POST /api/v1/clients/4/seed-demo-showcase?days=30&allow_demo_write=true` -> `200`
  - key read endpoints for DEMO return `200` with populated payloads (dashboard, campaigns, keywords, search terms, recommendations, action history, monitoring, forecast).
- Note on desktop runtime process:
  - latest seeder extension (curated waste patterns/search terms) is committed in code and requires backend process restart/reload to be reflected in live response fields.
- Environment limitation in this session:
  - Playwright MCP/CLI browser automation failed with process spawn permissions (`EPERM`), so full click-through UI regression could not be executed here.

## Daily Audit + Bulk Search Term Actions (2026-03-16 — commit bb2111c)
- Added `GET /api/v1/daily-audit/` — single aggregated morning PPC audit view:
  - budget pacing per enabled campaign (today vs daily budget)
  - unresolved anomaly alerts from last 24 h
  - disapproved / approved-limited ads
  - budget-capped campaigns with below-average CPA
  - top 50 wasted search terms from last 7 days (≥3 clicks or >$5 spend, 0 conversions)
  - pending recommendations summary (total + top 5 by priority)
  - health score + active campaign/keyword counts
  - today vs yesterday KPI snapshot (spend/clicks/conversions)
- Added bulk search term actions in `backend/app/routers/search_terms.py`:
  - `POST /search-terms/bulk-add-negative` — add selected terms as negative keywords (campaign or ad-group level)
  - `POST /search-terms/bulk-add-keyword` — promote selected terms as positive keywords to a target ad group
  - `POST /search-terms/bulk-preview` — return enriched preview data for selected terms before a bulk action
- Bulk actions log to `action_log` (`BULK_ADD_NEGATIVE`, `BULK_ADD_KEYWORD`) and enforce demo write guard.
- Added frontend `Daily Audit` page wired to `/daily-audit`.

## Negative Keyword Lists + Reports System (2026-03-16 — commit 5482626)
- Added negative keyword list management in `backend/app/routers/keywords_ads.py`:
  - `GET/POST /negative-keyword-lists/` — list and create lists
  - `GET/DELETE /negative-keyword-lists/{list_id}` — detail view and delete
  - `POST /negative-keyword-lists/{list_id}/items` — add keywords (duplicates skipped)
  - `DELETE /negative-keyword-lists/{list_id}/items/{item_id}` — remove single item
  - `POST /negative-keyword-lists/{list_id}/apply` — bulk-apply list items to campaigns/ad groups as `NegativeKeyword` records
- Added positive/negative keyword CRUD:
  - `POST /negative-keywords/` — create one or more negative keywords
  - `DELETE /negative-keywords/{negative_keyword_id}` — soft-delete
- Added lightweight ad group lookup endpoint: `GET /ad-groups/?client_id=X&campaign_id=`
- Added reports system in `backend/app/routers/reports.py` backed by `Report` model:
  - `POST /reports/generate?client_id=X` — SSE stream; phases: data gather per section → AI narrative via Claude CLI → persist to DB
  - `GET /reports/?client_id=X` — list saved reports (newest first)
  - `GET /reports/{report_id}?client_id=X` — full report detail (data + AI narrative + token/cost metadata)
- `AgentService` extended with `MONTHLY_PROMPT`, `REPORT_DATA_MAP`, `_gather_section()`, and `pre_gathered_data` support in `generate_report()`.
- Frontend `Keywords` page rebuilt with negative keyword list UI.

## AI Agent (Raport AI) (2026-03-16)
- Added protected backend router `backend/app/routers/agent.py` with:
  - `GET /api/v1/agent/status` for Claude CLI availability/version check
  - `POST /api/v1/agent/chat?client_id=X` for SSE report generation
- Added `AgentService` (`backend/app/services/agent_service.py`) to:
  - gather scoped analytics context by `report_type`
  - build bounded prompt payload
  - invoke local Claude CLI in headless mode (`claude -p --output-format stream-json`)
  - stream report chunks as SSE-safe events
- Registered agent router in `backend/app/main.py` under protected API routes.
- Added frontend AI page `frontend/src/pages/Agent.jsx` with:
  - quick report actions (`weekly`, `campaigns`, `keywords`, `search_terms`, `budget`, `alerts`, `freeform`)
  - SSE streaming parser and incremental assistant rendering
  - markdown output rendering via `react-markdown` + `remark-gfm`
- Added navigation + route wiring:
  - `/agent` route in `frontend/src/App.jsx`
  - `Raport AI` entry in `frontend/src/components/Sidebar.jsx`
  - `getAgentStatus()` helper in `frontend/src/api.js`

## AI Agent Stabilization (2026-03-16, current workspace)
- Router lock flow hardened to atomic single-flight behavior:
  - busy request now returns SSE `error` + `done` from the stream path
  - lock check + acquire happen in one async context
- KPI window parity fixed in agent analytics:
  - current window: `today-6 .. today` (7 days)
  - previous window: `today-13 .. today-7` (7 days)
- Campaign metrics gathering optimized:
  - replaced per-campaign aggregate queries (N+1) with grouped batch queries
  - kept result limits (`30` summary, `40` detail) and empty-list fast paths
- Claude subprocess noise/error handling simplified:
  - removed `--verbose`
  - redirected stderr to `DEVNULL`
  - returncode error now emits short standardized message
- Frontend cleanup in `Agent.jsx`:
  - removed dead/partial legacy sender implementation
  - added explicit 401 handling (`auth:unauthorized`) for SSE fetch failures

## Validation (2026-03-16)
- Implemented tests for AI Agent feature in `backend/tests/test_agent.py`:
  - endpoint contract checks
  - report type fallback behavior
  - gather-data section coverage
  - KPI date-range parity
  - prompt truncation behavior
- Additional coverage milestone already committed (2026-03-16):
  - commit `1c555ea`: +81 tests across backend/frontend critical gaps
- Pre-existing regression fixes already committed (2026-03-16):
  - commit `60b24cb`: segmentation + keyword cleanup test fixes
  - commit message states full backend suite passed in that run (`145` tests)
- Environment limitation for this documentation update:
  - local re-run was not possible in this session because `python`/`pytest` executables are unavailable in PATH.

## Code Review Fixes (2026-03-20 — commit 2111501)
- Removed dead `import calendar as cal2` in `reports.py`
- Fixed PMax search terms export: INNER JOIN → `outerjoin` so terms with no `ad_group_id` (PMax) are included
- Fixed `Report.created_at` timezone: naive UTC (`datetime.utcnow`) for SQLite compatibility
- Added per-read timeout guard in agent streaming loop to prevent hangs when Claude CLI stalls

## Full Project Audit + Cleanup (2026-03-20 — commit 9760f4d)
- Full PM/Tech Lead audit: 6 CRITICAL + 6 WARNING issues identified and fixed
- Fixed UTF-8 mojibake in Dashboard.jsx (~30 occurrences) and ActionHistory.jsx (~17 occurrences)
- Fixed silent error catches in AppContext.jsx, TrendExplorer.jsx, Alerts.jsx
- Fixed OAUTHLIB conditional in auth.py (unconditional override → conditional)
- Centralized shared styles (TH_STYLE, MODAL_OVERLAY, MODAL_BOX) in UI.jsx
- Replaced 9 off-palette colors in Campaigns.jsx with v2 design system
- Deleted dead code: Charts.jsx (17KB unused), SegmentBadge.jsx (duplicate)
- Added Playwright E2E smoke tests: 19 tests covering all pages with mocked API
- Archived 5 obsolete MD files to `docs/archive/`
- Updated DEVELOPMENT_ROADMAP_OPTIMIZATION.md with implementation status (6 DONE, 4 PARTIAL, 16 NOT DONE)
- Synced COMPLETED_FEATURES.md with 6 newly delivered features
- Updated SOURCE_OF_TRUTH.md and AGENTS.md references
- TaskCompleted hook upgraded to auto-commit instead of remind-only

## Test Coverage Expansion (2026-03-20 — commit e4456ee)
- Added 53 new backend tests covering previously untested endpoints:
  - `test_analytics_endpoints.py`: 30 tests for all /analytics/* routes
  - `test_daily_audit.py`: 8 tests for /daily-audit/ endpoint
  - `test_bulk_search_terms.py`: 5 tests for bulk-add-negative, bulk-add-keyword, bulk-preview
  - `test_bulk_apply.py`: 5 tests for /recommendations/bulk-apply
  - `test_semantic_clusters.py`: 4 tests for /semantic/clusters
- Polish labels in Recommendations.jsx TYPE_CONFIG (was English)

## Validation (2026-03-20)
- Backend: 275 tests passed (`pytest --tb=short -q`)
- Playwright E2E: 19 smoke tests (all pages render, no JS errors, Polish encoding verified)

## Roadmap Features — 6 New Endpoints + Reports Expansion (2026-03-20)
- Implemented 6 roadmap features as new analytics endpoints and report types:
  - **E1 Weekly Report** — `POST /reports/generate` now supports `report_type: "weekly"` (7-day window)
  - **E3 Account Health Report** — `POST /reports/generate` now supports `report_type: "health"` (30-day audit with conversion health, quality scores, account structure)
  - **B2 Search Terms Trend Analysis** — `GET /analytics/search-term-trends?client_id=X&days=30&min_clicks=5` (rising, declining, new terms)
  - **B3 Close Variant Analysis** — `GET /analytics/close-variants?client_id=X&days=30` (search terms vs exact keywords distance scoring)
  - **A3 Conversion Tracking Health** — `GET /analytics/conversion-health?client_id=X&days=30` (per-campaign conversion audit)
  - **G2 Keyword Expansion** — `GET /analytics/keyword-expansion?client_id=X&days=30&min_clicks=3` (high-performing search terms as keyword suggestions)
- Added 18 new tests: 15 analytics endpoint tests + 3 report type tests
- Backend test count: 293 tests total

## Validation (roadmap features 2026-03-20)
- Backend: 293 tests passed
- Roadmap status updated: 10 DONE, 2 PARTIAL, 14 NOT DONE (was 6/4/16)

## Unified Filtering Refactor (2026-03-20 — commit 1bda791)
- Unified the entire filtering system across backend and frontend — one consistent pattern for dates, campaign type, and campaign status.

### Backend
- Added `backend/app/utils/date_utils.py` with `resolve_dates()` helper — central date resolution from `date_from`/`date_to` or `days` lookback.
- Added `_filter_campaigns()` and `_filter_campaign_ids()` helpers in `AnalyticsService` for reusable campaign filtering.
- Extended ~20 analytics endpoints with `date_from`, `date_to`, `campaign_type`, `campaign_status` params (additive — `days` still works).
- Extended `campaigns/{id}/kpis` with `date_from`/`date_to` (overrides `days`).
- Extended `recommendations/` and `recommendations/summary` with `date_from`/`date_to` (converted to `effective_days` for protected service).
- Added `campaign_status` alias alongside existing `status` param on endpoints that had it (backward compat preserved).

### Frontend
- Added computed `dateParams`, `campaignParams`, `allParams` to `FilterContext` — pages spread `allParams` into API calls.
- Migrated Dashboard, Campaigns, SearchTerms, SearchOptimization, Recommendations pages to use `allParams` from `FilterContext`.
- Campaigns page now uses server-side campaign filtering via API params (was in-memory `useMemo` filter).
- SearchTerms Trends/Variants now react to global date range (was hardcoded `days: 30`).
- Recommendations hook now accepts `days` from FilterContext.
- Removed dead `useFilter` import from DailyAudit.
- GlobalFilterBar now conditionally rendered only on Category A routes (Dashboard, Campaigns, Keywords, SearchTerms, SearchOptimization, Recommendations).
- API functions in `api.js` updated to accept `params` objects for consistent parameter passing.

### Page Categories
- **Category A** (use global filters): Dashboard, Campaigns, Keywords, SearchTerms, SearchOptimization, Recommendations
- **Category B** (independent/own filters): DailyAudit, ActionHistory, Alerts, QualityScore, Reports, Forecast

## Validation (unified filtering 2026-03-20)
- Backend: 293 tests passed
- All changes additive — no breaking changes to existing API contracts

## Polish Diacritics Fix + Analytics Alerts i18n (2026-03-21 — commit 189934d)
- Fixed missing/incorrect Polish diacritics (ą, ę, ó, ś, ź, ż, ć, ń, ł) across ~20 frontend files
- Translated 4 analytics alerts (InsightsFeed) from English to Polish in `recommendations.py`
- Synced frontend tests and E2E smoke tests with corrected labels

## Test Coverage Expansion — resolve_dates + Unified Filtering + CRUD (2026-03-20 — commit a814b01)
- Added 62 new backend tests covering previously untested utilities and endpoints:
  - `test_resolve_dates.py`: 15 unit tests for `resolve_dates()` helper and `_filter_campaigns()` in AnalyticsService
  - `test_unified_filtering.py`: 27 integration tests for `date_from`/`date_to` + `campaign_type`/`campaign_status` params across analytics endpoints
  - `test_campaigns_clients_crud.py`: 20 tests for campaigns list/detail/patch/kpis, clients list/detail/create/patch/delete, ad-groups, ads, recommendations summary, and bulk-preview
- Total test count: 293 → 355

## Forecast Sidebar + Anomalies Cleanup (2026-03-20 — commit ec1d22c)
- Added `Forecast` entry to Sidebar navigation (`frontend/src/components/Sidebar.jsx`) — the `Forecast.jsx` page existed but was not linked.
- Removed orphaned `Anomalies` frontend page (was disconnected from navigation; anomaly management remains via `Alerts.jsx` and `/analytics/anomalies` backend endpoints).
- Added `/frontend/e2e/` to `.gitignore` to exclude Playwright test artifacts from repo.

