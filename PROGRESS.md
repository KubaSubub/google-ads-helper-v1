# PROGRESS.md - Implementation Status
# Updated: 2026-04-12 (docs-sync auto)

## Status
- Backend: 663 tests collected (pytest --collect-only)
- Frontend: build OK, modular feature architecture + unified global filtering + Playwright E2E
- DB: 45 models (26 original + 12 coverage expansion + ScheduledSync + AutomatedRule + AutomatedRuleLog + DsaTarget + DsaHeadline + PlacementExclusionList + PlacementExclusionListItem)
- Sync: 37 total phases (22 prior + 14 new from Wave A-E + mcc_exclusion_lists) + scheduled sync service (asyncio-based, no external packages)
- API endpoints: 174 total across 19 routers (73 analytics, 13 keywords/ads, 11 sync, 11 clients, 7 auth, 7 rules, 7 mcc, 7 scripts, 6 campaigns, 6 search-terms, 6 export, 5 recommendations, 3 history, 3 reports, 3 scheduled-sync, 2 agent, 2 actions, 1 daily-audit, 1 semantic) + /health
- Models: 45 (26 original + AuctionInsight, ProductGroup, Placement, BidModifier, Audience, TopicPerformance, BiddingStrategy, SharedBudget, GoogleRecommendation, ConversionValueRule, MccLink, OfflineConversion, ScheduledSync, AutomatedRule, AutomatedRuleLog, DsaTarget, DsaHeadline, PlacementExclusionList, PlacementExclusionListItem)
- Frontend pages: 27 routes (15 original + Shopping, PMax, Display, Video, Competitive, TaskQueue, CrossCampaign, Benchmarks, Rules, DSA, MCCOverview, Scripts) — all with enriched UX
- Dashboard: overhaul with WoW chart, campaign summary, mini ranking (top/bottom ROAS), day-of-week heatmap, top actions widget, enriched health score with breakdown
- Campaigns: sort/filter sidebar, bidding target write (target CPA/ROAS)
- AuditCenter: 25 bento cards, period comparison, card pinning, keyboard shortcuts (1-9/Esc/?)
- Ads review pipeline: /ads-user → /ads-expert → /ads-verify → /ads-check — see open items below
- Roadmap: 25/26 DONE (96%) — only G3 Landing Page Audit is PARTIAL (endpoint exists; PageSpeed Insights, mobile-friendliness, message match not integrated)

## Raport Konkurenta — Full App (2026-03-30)
> Ocena: **4.5/10** | Autor: persona "Marek K., CTO konkurencji" | Pelny raport: `docs/reviews/competitor-all.md`

### Krytyczne slabosci (blokujace adopcje):
1. **Desktop-only (nie SaaS)** — brak wspolpracy, brak sharingu, brak mobile. W 2026 to dyskwalifikacja
2. **Tabele read-only (brak bulk edit)** — specjalista widzi problem ale nie moze go naprawic inline. To lookbook, nie narzedzie pracy
3. **SQLite bez migracji** — zmiana schematu = kasowanie danych. Bomba zegarowa
4. ~~**Brak MCC dashboard**~~ — DONE: MCC Overview landing page at /mcc-overview (commit 854f481)
5. **Monolity 5800+ linii** — google_ads.py i recommendations.py nierefaktorowalne

### Powazne braki:
- Brak zarzadzania tresciami reklamowymi (RSA editor, A/B testing)
- Rekomendacje z hardcodowanymi progami (one-size-fits-all zamiast adaptive)
- Forecast na regresji liniowej (Google Performance Planner jest lepszy za darmo)
- Brak CI/CD, Docker, monitoring (Sentry), health checks
- Brak onboardingu, brak scheduled reports (email), brak multi-user

### Co zostalo docenione:
- **Audit Center (35 bento kart)** — unikalne na rynku, nikt tego nie ma
- **Campaign Role Classification** z protection levels — inteligentne
- **Safety guardrails** na mutacjach — enterprise-grade (circuit breaker, dry-run, revert, audit trail)
- **Search Terms Intelligence** — kompletny workflow (segmentacja + semantic clustering + trends)
- **Polskie UI** — pelna lokalizacja, przewaga na polskim rynku
- **Keyboard shortcuts** — power user friendly

### Scorecard:
| Kategoria | Ocena |
|-----------|-------|
| Wartosc dla specjalisty | 5/10 |
| Kompletnosc vs konkurencja | 4/10 |
| UX/Design | 6/10 |
| Tech quality | 5/10 |
| Unikatowa wartosc (moat) | 4/10 |
| Gotowosc rynkowa | 3/10 |
| **SREDNIA** | **4.5/10** |

### Werdykt:
> "Silnik Porsche w karoserii Malucha. Solidny backend z 187 endpointami i enterprise-grade safety — ale zapakowany w desktop-only format dystrybucji z 2010 roku."

### 30-dniowy plan zagrozenia (co musielibysmy zrobic zeby konkurencja sie bala):
1. **Tydz 1-2:** Cloud deploy (Railway/Fly.io) + PostgreSQL zamiast SQLite
2. **Tydz 2-3:** Multi-user auth + team workspace
3. **Tydz 3-4:** "Top 5 actions today" z PLN impact + one-click apply + email digest

## Optimization Scripts Engine — Sprint 1-4 (2026-04-13)
- Spec: `docs/specs/scripts-p0-p1-fixes.md`, CEO entry in `docs/ceo-log.md`
- New **scripts engine** — date-aware optimization scripts with configurable parameters, dry-run/execute flow, per-client config persistence
- Backend: `backend/app/services/scripts/` — modular script architecture with `BaseScript` class, shared helpers (`_helpers.py`)
  - 9 scripts implemented:
    - `a1_zero_conv_waste` — zero-conversion keyword waste detection
    - `a2_irrelevant_dictionary` — irrelevant search term dictionary matching
    - `a3_low_ctr_waste` — low CTR keyword waste detection (Sprint 1-4)
    - `a6_non_latin_script` — non-Latin script search term detection
    - `b1_high_conv_promotion` — high-converting search term promotion
    - `c2_duplicate_coverage` — duplicate keyword coverage analysis
    - `d1_ngram_waste` — n-gram waste pattern detection
    - `d3_ngram_audit` — n-gram audit report (Sprint 1-4)
    - `f1_competitor_term` — competitor term detection (Sprint 1-4)
- Backend: `backend/app/routers/scripts.py` — 7 endpoints (catalog, dry-run, execute, history, config CRUD)
- Frontend: `frontend/src/features/scripts/ScriptsPage.jsx` — dedicated Scripts page at `/scripts` with catalog view, per-script dry-run/execute UI, execution history
- Tests: 11 test files (`test_scripts_a1.py`, `test_scripts_a2.py`, `test_scripts_a3.py`, `test_scripts_a6.py`, `test_scripts_b1.py`, `test_scripts_c2.py`, `test_scripts_d1.py`, `test_scripts_d3.py`, `test_scripts_f1.py`, `test_scripts_helpers.py`, `test_scripts_router_history.py`) + shared `scripts_fixtures.py`
- Commits: 1addab6 (P0+P1), 25dbbc9 (Sprint 1-4: UX polish + 3 new scripts + history)

## Dashboard (Pulpit) Consolidation + Quick Scripts Preview Flow (2026-04-11)
- Dashboard reworked as the single landing surface for daily operations; `/daily-audit` hidden from sidebar nav (still reachable by URL via `{hidden: true}` in `navConfig.js`)
- Removed redundant widgets that duplicated dedicated tabs: Insights Feed, Campaign Table, PMax Split, Recent Actions (users are pointed at `/recommendations`, `/campaigns`, `/pmax`, `/action-history`)
- Compact Budget Pacing card with expandable campaign list; QS Widget + Top Actions rendered as side-by-side compact squares
- New **Quick Scripts** section on Dashboard (Clean Waste / Pause Burning / Boost Winners / Emergency Brake) powered by `POST /recommendations/bulk-apply`:
  - Always-clickable tiles (no disabled state) — empty categories show an "all good" modal
  - 3-phase execution flow: **Preview** (per-item cards with entity/campaign name, reason, priority badge, metrics snapshot, per-row checkbox to opt out) → **Executing** (locked modal with "do not close" spinner) → **Result** (ZMIANY ZAPISANE W GOOGLE ADS banner + deep link to `/action-history`)
  - `POST /recommendations/bulk-apply` extended: preview items now carry `entity_name`, `campaign_name`, `reason`, `suggested_action`, `priority`, and `metrics_snapshot`; accepts optional `item_ids[]` on execution to honor user opt-outs
- **Header filter bar** replaces sidebar-mounted client/campaign-type controls:
  - `HeaderClientSelector.jsx` — dropdown with client list, Google Customer ID, manage link
  - `HeaderCampaignTypeSelector.jsx` — segmented pills (ALL / Search / PMax / Shopping / …)
  - Both hidden on `/mcc-overview` route
- Dashboard data reactivity fixes: endpoints resolve state independently (previously `Promise.all` blocked Health Score on slow recommendations); date filters propagated to `getRecommendations` + `getQualityScoreAudit`; dashboard forces ENABLED-only campaigns; `CampaignMiniRanking` receives filtered campaigns so it respects the active campaign-type pill; Quick Scripts counts reload with recommendations refresh
- TrendExplorer annotations: fetches action history for the selected date range, groups by date, renders `ReferenceLine` markers on the chart with rich tooltips (operation label, entity name, before→after values, timestamp)
- KPI tooltips: full definitions for all 25 dashboard KPIs (benchmarks, formulas, practical advice) via viewport-aware floating info tooltip
- `DayOfWeekWidget`: 5-level color scale with per-cell border colors; `CampaignMiniRanking`: column headers + "sortowane po ROAS" hint
- Fixed compact Budget Pacing bar — previously read non-existent fields, now uses backend `status` / `actual_spend_usd` / `expected_spend_usd`
- Commit: 646a265

## Settings — Marketing Mastermind Brief (2026-04-10)
- Spec: `docs/specs/settings-mastermind-brief.md`, CEO entry in `docs/ceo-log.md`
- Pivot: Settings transformed from operational hub (which duplicated Dashboard/Daily Audit/Campaigns/Monitoring) into marketing mastermind brief — single place where a specialist documents WHO the client is, WHAT the strategy is, what worked / didn't work, and what the AI agent needs as prompt context
- Backend: new `strategy_context` JSON column on `clients` with auto-migration via `_ensure_sqlite_columns` (no manual migration)
  - New Pydantic schemas: `StrategyContext`, `LessonEntry`, `DecisionLogEntry` with length validators (narrative ≤10k, brand_voice ≤5k, lesson description 10-2000 chars, lessons_learned ≤200, decisions_log ≤500)
  - `PATCH /clients/{id}` now deep-merges `strategy_context` (partial updates preserve other fields — critical for future AI writing `decisions_log`)
  - `PATCH` with `{"strategy_context": null}` is a no-op (does not wipe column)
  - 11 new backend tests in `test_client_strategy.py` (total: 596 → 607)
- Frontend: new `ConversionGoalsSection.jsx` replaces operational 4-card `ClientHealthSection` view
  - Full-width table of `ConversionAction` rows with checkbox toggling `business_rules.priority_conversions`
  - New column "Cel Google Ads" shows `primary_for_goal` from API — surfaces the semantic gap between local priority and Google Ads primary
  - Helper text clarifies: local priority does NOT mutate Google Ads settings
- Frontend: 5 new brief sections in `Settings.jsx` under "Brief kliencki" header
  1. Strategia marketingowa — narrative textarea (Obsidian-ready)
  2. Plan działań / Roadmap — narrative textarea
  3. Log decyzji — read-only, "AI coming soon" banner; structure ready for AI agent
  4. Wnioski i lessons learned — structured wins/losses/tests journal with append + delete
  5. Brand voice & zakazy — 2-column tone/restrictions
- Settings.jsx grouped with "Brief kliencki" / "Execution" headers to distinguish strategic vs operational sections
- Tests: `frontend/e2e/settings-mastermind-brief.spec.js` 10 E2E (DOM-based, remove lesson flow, primary_for_goal column visibility)
- Dead code: `ClientHealthSection.jsx` unreferenced after pivot (sandbox denied delete; not imported)
- Commit: 9f8d7f1

## Settings — Client Info Hub + AI Context (2026-04-10, superseded by Mastermind Brief)
- Spec: `docs/specs/settings-client-info-hub.md`
- Backend: `GET /clients/{id}/health` endpoint + `client_health_service.py` + `ClientHealthResponse` schema
- Aggregates: account metadata (DB + optional Google Ads API enrichment), sync freshness badge (green<6h/yellow<12h/red≥12h), conversion tracking from `ConversionAction` table (no live API call), linked accounts shell (GA4, GMC, YT, Search Console)
- Graceful degradation — always HTTP 200, partial failures surfaced via `errors[]`
- AI context: `business_rules` JSON extended with 6 fields — `target_cpa`, `target_roas`, `ltv_per_customer`, `profit_margin_pct`, `priority_conversions`, `brand_terms` (all validated, `brand_terms` max 50 items × 200 chars)
- Currency fix in `Settings.jsx`: hardcoded USD → `client.currency`
- Security: GAQL injection guard (regex validation of `customer_id` before interpolation)
- Domain: MANAGER/CLIENT terminology (MCC deprecated 2022), DATA_DRIVEN enum (API v23)
- Frontend: new `ClientHealthSection.jsx` (v2-card pattern), `brand_terms` tag input in Reguły biznesowe matching competitors pill pattern
- Tests: `backend/tests/test_client_health.py` (AC1/AC2/AC3/AC4/AC7/AC8) + `frontend/e2e/settings-client-info-hub.spec.js` (4 E2E)
- Review: code 8/10, security 8/10, domain 8/10
- Commits: c11db08 (main feature), e384cd1 (follow-up fix — `ClientHealthSection` now uses unwrapped axios response data)

## MCC Overview — Remove Broken Rekomendacje Google UI (2026-04-10)
- Non-functional "Rekomendacje Google" column + dismiss flow removed from `MCCOverviewPage.jsx`
- Removed: `dismissMccGoogleRecommendations` import, `EyeOff` icon, `dismissingAll` state, `handleDismissRecs`/`handleBulkDismissRecs`, column header, table cell, bulk bar button
- Preserved for future reuse: backend endpoint `POST /mcc/dismiss-google-recommendations`, `MCCService.dismiss_google_recommendations()`, contract tests, `api.js` export, `google_recs_pending` response field
- E2E regression guard: `mcc-overview.spec.js` now asserts column header + bulk button stay removed (prevents accidental re-introduction)
- Commit: 2cc34d3

## MCC Overview Regression Shield (2026-04-10)
- Added comprehensive test coverage protecting the MCC Overview view from accidental damage by changes elsewhere
- Backend contract lock: `tests/test_mcc_router_contract.py` — 24 tests locking response shape for all 7 MCC endpoints
  - `REQUIRED_ACCOUNT_KEYS` set guards every field `MCCOverviewPage.jsx` reads from `accounts[]` (missing/renamed field breaks tests)
  - Type invariants: `conversions` must be float, `spend_trend` must be `list[{date, spend}]`, `alert_details` have fixed keys
  - Behavioural invariants: demo client excluded, date params honored, empty accounts returns `[]` not `null`, `last_synced_at` reflects sync_logs
  - Drill-down tests for keyword + placement shared lists
  - Dismiss recs test: only GOOGLE_ADS_API source affected, PLAYBOOK_RULES untouched
- Frontend regression shield: `e2e/mcc-overview.spec.js` +8 tests
  - Sort works on every core metric column (Wydatki, Konwersje, CPA, ROAS)
  - Pacing bar renders for overspend status (not just on_track)
  - Period buttons (7d/14d/30d/MTD) update API dateParams
  - Single-account render doesn't break KPI strip
  - Overview 500 error doesn't crash page — error toast shown, no JS errors
  - Billing-status fetched once per unique `customer_id` (no redundant calls)
  - Bulk dismiss recs flow triggers dismiss endpoint
  - Smoke test: full render + multi-interaction flow with 0 JS errors
- Fixed pre-existing `settings-clients.spec.js` gaps (5 failing tests) — root cause: root route "/" now redirects to "/mcc-overview" and ClientSelector/ClientDrawer are not rendered on MCC pages; tests now navigate to `/dashboard` where drawer exists
- Commit: 869cea3

## MCC "Synchronizuj nieaktualne" Fix + Sync Contract Lock (2026-04-10)
- Fixed "500 + 3x timeout 30000ms" error on MCC Overview "Synchronizuj nieaktualne" button
- Root causes:
  1. Frontend `handleSyncAll` fired up to 3 parallel fire-and-forget POST `/sync/trigger` calls; full sync takes 20-45s per client so Axios 30s timeout fired deterministically for 2/3 requests
  2. SQLite `PRAGMA busy_timeout=0` (default) caused "database is locked" HTTP 500 under concurrent writers
- Fix: sequential sync in `MCCOverviewPage.jsx` handleSyncAll + `busy_timeout` PRAGMA set on SQLite connection
- New contract tests in `test_sync_router.py` guarding `/sync/trigger` response shape (success/status/message) that the MCC frontend relies on:
  - `test_trigger_unknown_client_matches_contract`
  - `test_trigger_google_ads_not_ready_matches_contract`
- Commits: f46f07a (fix), 79f5f8d (contract tests)

## MCC Overview Sprint 2 — Currency + Sparkline (2026-04-10)
- Currency-aware money formatting: per-account `currency` field drives symbol placement ($1,234 vs 1 234 zł vs 1 234 €)
- Spend sparkline per account row (56×20 LineChart from `spend_trend` daily data)
- Applies to: spend, avg CPC, conversion value, CPA, budget pacing tooltip
- Commits: ace8ffc (feat), c8b7eeb (review fixes)

## MCC Exclusion Lists + Drill-Down (2026-04-09)
- Added `GET /mcc/shared-lists/{list_id}/items` — drill-down endpoint returning items of a specific MCC shared exclusion list
- MCC shared lists now include both negative keyword lists and placement exclusion lists
- E2E lock: 20 backend tests covering MCC endpoints
- Commit: 95c79e9

## Google Ads API Version Fix (2026-04-03)
- Discovered silent SDK upgrade: `google-ads>=25.1.0` (loose pin) installed SDK 29.1.0 (API v23), while documentation said API v18
- Pinned SDK to `google-ads==29.1.0` in `requirements.txt`
- Added explicit `version="v23"` to `GoogleAdsClient.load_from_dict()` in `google_ads.py`
- Added ADR-019 (pin SDK + declare API version explicitly)
- Updated ADR-018, SOURCE_OF_TRUTH.md — all API version references now correct
- PMax campaign-level negative keywords: now officially AVAILABLE (API v20+ requirement met by v23)

## MCC Overview — Cross-Account Landing Page (2026-04-02)
- New landing page `MccOverviewPage.jsx` (`features/mcc-overview/`) at `/mcc-overview` — default entry point (/ redirects to /mcc-overview)
- Backend: `mcc.py` router with 7 endpoints:
  - `GET /mcc/overview` — aggregated KPIs, health scores, pacing, change activity for all clients
  - `GET /mcc/new-access` — detect new user emails in change history
  - `POST /mcc/dismiss-google-recommendations` — bulk dismiss Google recommendations
  - `GET /mcc/negative-keyword-lists` — negative keyword lists across all clients
  - `GET /mcc/shared-lists` — MCC-level shared negative keyword lists
  - `GET /mcc/shared-lists/{list_id}/items` — items in a specific MCC shared list
  - `GET /mcc/billing-status` — billing/payment status per customer
- Per-account metrics: spend 30d (with delta %), conversions, CPA, ROAS, budget pacing (75%/120% thresholds), health score (6-pillar tooltip), change activity (total + external), Google recs pending, unresolved alerts, last sync
- Full account metrics (clicks, impressions, CTR, CPC, CVR, conv value), new access badges, dismiss Google recs button, MCC shared lists, billing status endpoint
- Sortable table columns, deep-links from cells to per-account pages (Recommendations, Action History, Alerts, Keywords)
- Collapsible NKL cross-account section (lazy-loaded)
- Link "Open in Google Ads" per row, alert badge (Bell) per account
- Sidebar: "Wszystkie konta" always visible, ClientSelector/CampaignTypePills hidden on MCC page
- Dashboard breadcrumb "← Wszystkie konta" when navigating from MCC
- Config: `SPECIALIST_EMAILS` env var for external change detection
- Reuses `BudgetPacingModule` and `KpiCard` shared components
- 13 backend tests, frontend build OK, ads review pipeline complete (ads-user → ads-expert 7.5/10 → ads-verify Sprint 1+2 done)

## Reusable UI Modules — BudgetPacingModule + KpiCard (2026-04-01)
- Extracted `BudgetPacingModule` and `KpiCard` from duplicated inline code across 5+ pages into `frontend/src/components/modules/`.
- New shared modules: `BudgetPacingModule.jsx`, `KpiCard.jsx`, `PacingProgressBar.jsx`, `pacing-utils.js`, `index.js`.
- Consumers updated: DashboardPage, CampaignsPage, DailyAudit, Reports, VideoPage, CrossCampaignPage, CompetitivePage.
- Eliminates copy-paste budget pacing logic and KPI card styling across pages.

## Project Cleanup (2026-04-01)
- Removed archived docs, screenshots, and duplicate files (commit 69b84e7).
- Cleaned `docs/archive/` directory (obsolete MD files previously archived from 2026-03-31).
- Removed `frontend/e2e-screenshots/` baseline snapshots no longer needed.

## Write Safety Layer + Remote-First Bidding (2026-03-30)
- New service `backend/app/services/write_safety.py` — unified write-path safety layer for direct user-initiated writes:
  - `record_write_action()` — audit trail for non-recommendation writes (complements ActionExecutor)
  - `count_negatives_added_today()` / `count_pauses_today()` — daily limit helpers
  - Pipeline: demo guard → safety check → audit log
- `PATCH /campaigns/{id}/bidding-target` refactored to remote-first:
  - Tries Google Ads API push first, commits to local DB only on success
  - Falls back to local-only if API disconnected (returns `pending_sync: true`)
  - API failure now returns HTTP 502 with error detail (previously wrote local + logged warning)
  - Full audit trail via `record_write_action()`
- `POST /analytics/offline-conversions/upload` now functional:
  - Actually calls `google_ads_service.upload_offline_conversions()` (was previously placeholder returning info message)
  - Audit trail via `record_write_action()`
- Auth config: `OAUTHLIB_INSECURE_TRANSPORT` now controlled by `settings.oauth_allow_insecure_transport` / `settings.is_development` instead of unconditional env override

## Dashboard Enhancements — Z-Score Anomalies + New Widgets (2026-03-30)
- New `GET /analytics/z-score-anomalies` endpoint — z-score anomaly detection per campaign per day for a given metric (cost, clicks, impressions, conversions, ctr)
- Anomalies response enriched with `campaign_name` and `metric_value` fields
- New dashboard components:
  - `DayOfWeekWidget.jsx` — day-of-week performance analysis widget
  - `CampaignMiniRanking.jsx` — mini campaign ranking widget
  - `TopActions.jsx` — top recommended actions widget
  - `MiniKpiGrid.jsx` — enhanced with expanded KPI cards and visual improvements
  - `HealthScoreCard.jsx` — enhanced with additional health metrics display

## DSA Support — C1/C2/C3 (2026-03-29)
- 4 new analytics endpoints: `dsa-targets`, `dsa-coverage`, `dsa-headlines`, `dsa-search-overlap`
- 2 new models: `DsaTarget`, `DsaHeadline`
- Seed data: DSA targets + headlines per client
- C1: DSA target performance (auto-targets per campaign)
- C2: DSA headline performance analysis (top/worst headlines by CTR/conversions)
- C3: DSA vs manual keyword overlap detection

## Automated Rules Engine (F3) (2026-03-29)
- New router: `rules.py` — 7 endpoints (CRUD + dry-run + execute)
- New model: `AutomatedRule` — per-client rule definition with conditions, actions, schedule
- New service: `rules_engine.py` — rule evaluation and execution engine
- Route: `/rules/`, registered in `main.py` (17 routers total)

## Cross-Campaign Analysis (G4) + Benchmarks (H2) + Scheduled Sync (F1) (2026-03-29)

### Cross-Campaign Analysis (G4)
- 3 new analytics endpoints: `keyword-overlap`, `budget-allocation`, `campaign-comparison`
- New page: `features/cross-campaign/CrossCampaignPage.jsx` — keyword overlap matrix, budget allocation chart, side-by-side campaign comparison
- Route: `/cross-campaign`, sidebar nav in ANALIZA group

### Benchmarks (H2)
- 2 new analytics endpoints: `benchmarks`, `client-comparison`
- New page: `features/benchmarks/BenchmarksPage.jsx` — account KPI benchmarks and cross-client comparison
- Route: `/benchmarks`, sidebar nav in ANALIZA group

### Scheduled Sync (F1)
- New model: `ScheduledSync` — per-client sync schedule (enabled, interval_hours)
- New service: `scheduler.py` — asyncio-based background sync runner (no external packages)
- New router: `scheduled_sync.py` — 3 endpoints (GET/POST/DELETE `/sync/schedule`)
- Registered in `main.py` as protected router (17 routers total)

## PMax Asset Groups Enrichment (D2) + Task Queue Page (H1) (2026-03-29)

### PMax Asset Groups (D2)
- Enriched `PMaxPage.jsx` with asset group KPI summary (total groups, avg strength, top/bottom performer)
- Asset strength distribution with colored pills
- Sortable columns (clicks, cost, conversions, ROAS)
- ROAS color-coding (green >4, yellow 2-4, red <2)
- Expandable rows with detail view

### Task Queue / Plan dnia (H1)
- New page: `features/task-queue/TaskQueuePage.jsx` — aggregates actionable items from recommendations, alerts, wasted spend
- Priority badges (HIGH/MEDIUM/LOW) with sorting
- Progress bar with localStorage persistence
- Quick action buttons per task type
- Route: `/tasks`, sidebar: "Plan dnia" in DZIAŁANIA group

## Ads-Verify Sprint 2 — Full-App Polish (2026-03-29)

### Codebase Cleanup
- Deleted `SearchOptimization.jsx` (2014 lines dead code) — replaced by `features/audit-center/AuditCenterPage.jsx`
- AuditCenter refactored: removed 7 type-specific bento cards, 8 redundant API calls removed from `useAuditData.js`
- Fixed PERFORMANCE_MAX vs PMAX naming inconsistency across frontend (unified in `constants/campaignTypes.js`)
- Removed duplicate campaign type filter from `GlobalFilterBar.jsx` (now: Status, Label, Name only; campaign type handled by sidebar pills)

### AuditCenter Enhancements
- Added period comparison (% change) to bento cards via `prevData` in `useAuditData` + `changePct` prop in `BentoCard.jsx`
- Added card pinning with localStorage persistence (`audit-center-pinned` key, pin/unpin UI on hover)

### Cross-App Navigation & UX
- Added keyboard shortcuts: 1-9 for page navigation, Esc for back, `/` for search focus, `?` tooltip (`useKeyboardShortcuts.js`, `ShortcutsHint.jsx`)
- Added `useNavigateTo` hook (`frontend/src/hooks/useNavigateTo.js`) + cross-nav links in Alerts, QualityScore, Forecast

### Page-Level Improvements
- **Forecast**: smart retry on error, horizon selector (7/14/30d), FilterContext integration for global date range
- **Semantic**: FilterContext integration, search input for clusters, bulk waste exclude (select waste clusters + floating action bar)
- **Settings**: form validation (min/max on safety_limits + business_rules), dirty state tracking with `beforeunload` navigation warning
- **Shopping** (`features/shopping/ShoppingPage.jsx`): KPIs row, performance tabs, ROAS color-coding, search input
- **Video** (`features/video/VideoPage.jsx`): 3 tabs (placements, topics, exclusions), CPV metrics, high-CPV highlighting
- **Competitive** (`features/competitive/CompetitivePage.jsx`): KPIs row, competitor ranking, visual bars for IS/outranking

### Ads Review Pipeline — Honest Status (audit 2026-03-30)
- ads-verify-full-app.md: DONE: 11, PARTIAL: 3 (#2 pause keyword, #4 placement exclude UI, #8 bulk checkboxes), NOT_NEEDED: 3
- ads-check-reports.md: DONE: 7/13 — 6 STILL_MISSING are all NICE TO HAVE (scheduler, compare, filter, trend, email, custom sections)
- ads-check-quality-score.md: DONE: 12/15 — PARTIAL: 1 (#7 deeper recommendation logic), STILL_MISSING: 2 (#5 QS trend history, #9 per-row pause)
- ads-check-action-history.md: DONE: 13/16 — STILL_MISSING: 3 (#N1 pagination, #N2 CSV export, #N6 post-revert alerts) — all NICE TO HAVE
- ads-check-dashboard.md: DONE: 9/9 — fully complete
- All KRYTYCZNE items across all reviews are DONE. Open items are exclusively NICE TO HAVE / backlog for v1.1+

## Frontend Modular Architecture (2026-03-29 — commit 5b36e3a)
- Extracted monolithic page components into feature modules under `frontend/src/features/` (14 modules):
  - `audit-center/` — AuditCenterPage (replaces SearchOptimization, 25 analysis sections with bento card layout)
  - `benchmarks/` — BenchmarksPage (account KPI benchmarks, cross-client comparison)
  - `campaigns/` — CampaignsPage + CampaignKpiRow + CampaignTrendExplorer
  - `competitive/` — CompetitivePage (auction insights, competitor visibility)
  - `cross-campaign/` — CrossCampaignPage (keyword overlap, budget allocation, campaign comparison)
  - `dashboard/` — DashboardPage + HealthScoreCard + MiniKpiGrid + QsHealthWidget
  - `display/` — DisplayPage (placements, topics, exclusions)
  - `dsa/` — DsaPage (DSA targets, headlines, search overlap)
  - `keywords/` — KeywordsPage + PositiveKeywordsTab + NegativeKeywordsTab + NegativeKeywordListsTab + KeywordExpansionTab + AddNegativeModal
  - `pmax/` — PMaxPage (channel breakdown, asset groups, search themes, cannibalization)
  - `rules/` — RulesPage (automated rules CRUD, dry-run, execute)
  - `shopping/` — ShoppingPage (product group performance, ROAS color-coding)
  - `task-queue/` — TaskQueuePage (plan dnia, priority sorting, progress tracking)
  - `video/` — VideoPage (video placements, view metrics)
- Extracted sidebar into `frontend/src/components/layout/Sidebar/` (SidebarContent, ClientSelector, ClientDrawer, NavItem, CampaignTypePills, navConfig)
- Added shared components: `MatchBadge`, `MetricPill`, `SectionHeader` in `frontend/src/components/shared/`
- Added constants: `designTokens.js`, `campaignTypes.js` in `frontend/src/constants/`
- Extracted route config into `frontend/src/app/routes.jsx` with lazy loading
- SearchOptimization route redirects to `/audit-center` (backward compat)
- GLOBAL_FILTER_ROUTES expanded to include new campaign-type pages
- Sidebar nav reorganized: PRZEGLĄD, DANE KAMPANII (with campaign-type filtering), DZIAŁANIA, MONITORING, AI, ANALIZA
- Campaign-type nav items show/hide based on `types` filter (e.g. Keywords shows only for SEARCH)

### New Files (98 files changed, +10141/-4635 lines)
- `frontend/src/app/routes.jsx` — centralized route configuration
- `frontend/src/features/` — 9 feature modules with 40+ component files
- `frontend/src/components/layout/Sidebar/` — 6 sidebar sub-components
- `frontend/src/components/shared/` — 3 shared components
- `frontend/src/constants/` — 2 constants files
- `docs/reviews/ads-{user,expert,verify}-full-app.md` — full-app ads review pipeline
- `docs/GOOGLE_ADS_EXPERT_AUDIT.md` — comprehensive expert audit document
- `frontend/e2e-screenshots/` — 16 page screenshots for visual audit baseline

## Google Ads Coverage Expansion (2026-03-28)

### Wave A — Search + PMax Gaps
- Ad Sync: `sync_ads()` method, RSA inventory from `ad_group_ad` resource
- Auction Insights: model + sync per campaign + analytics endpoint + UI section with competitor table + IS trend chart
- Bid Modifiers: model + sync (device/location/ad_schedule campaign criteria)
- Target CPA/ROAS Write: `PATCH /campaigns/{id}/bidding-target` + Google Ads API mutation
- Extension Details: expanded GAQL for sitelink URLs/descriptions, snippet values, call phone, promotion details
- Demographics: parental_status + income_range added to MetricSegmented + analytics

### Wave B — Shopping Campaigns
- Product Group model: tree structure (parent/child), case_value_type, bid_micros, metrics
- Product Group Sync: `sync_product_groups()` via ad_group_criterion LISTING_GROUP
- Shopping Reports: `GET /analytics/shopping-product-groups` with ROAS color-coding
- Shopping UI: "Grupy produktów" section in SearchOptimization

### Wave C — Display Campaigns
- Placement model: URL, type, metrics + video-specific fields (views, view_rate, avg_cpv)
- Placement Sync: `sync_placement_metrics()` via detail_placement_view
- Placement Exclusion Write: `POST /analytics/placement-exclusion`
- Topic Targeting: model TopicPerformance + sync + endpoint + UI section
- Audience Management: model Audience + `sync_audiences()` + endpoint
- Display/Video UI: "Miejsca docelowe" + "Tematy" sections in SearchOptimization

### Wave D — Video Campaigns
- Video metrics merged into Placement model (video_views, video_view_rate, avg_cpv_micros)

### Wave E — Advanced Features
- Portfolio Bid Strategies: model BiddingStrategy + sync
- Shared Budgets: model SharedBudget + sync
- Google Recommendations: model GoogleRecommendation + sync + endpoint + UI section
- Conversion Value Rules: model ConversionValueRule + sync + endpoint
- MCC Multi-Account: model MccLink + `sync_mcc_links()`
- Offline Conversions: model OfflineConversion + upload method + endpoints

### Review Fixes
- Micros compliance: offline_conversion.conversion_value → conversion_value_micros
- Import hierarchy: moved QS helpers from analytics router to utils/quality_score.py
- Silent catch: campaigns.py bidding target → logger.warning + api_error in response
- Frontend: Settings2 import, hardcoded domain → is_self flag, LineChart data flatten, helper tab filter params

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

## Dashboard Overhaul + Cross-App Improvements (2026-03-25)

### ads-expert / ads-verify Skills
- Created `/ads-expert` skill — Google Ads specialist review per tab (saves to docs/reviews/)
- Created `/ads-verify` skill — code verification vs expert report + sprint plan generation
- Full 15-tab audit completed (ads-expert-all.md), avg score 7.6/10

### Dashboard Sprints (from ads-verify-dashboard.md)
- Sprint 1: Added CTR, Impressions, CPA, Wasted Spend KPI cards; geo share_cost_pct; Health→Alerts nav; campaign row click→/campaigns; "Wszystkie →" links
- Sprint 2: New `GET /analytics/campaigns-summary` endpoint; per-campaign metrics in table (cost, conversions, ROAS); InsightsFeed action buttons + "Wszystkie rekomendacje →"; Impression Share widget
- Sprint 3: New `GET /analytics/wow-comparison` endpoint; WoW comparison chart with metric selector (WoWChart.jsx)

### Bug Fixes
- Fixed wasted-spend date filtering — search terms now filtered by date_from/date_to range (was returning all-time data: 2968 zł regardless of period)
- Fixed Forecast retry bug — `loadForecast()` was undefined, replaced with retry counter

### Cross-App Improvements (from ads-verify-all.md)
- Forecast: horizon selector (7/14/30d), FilterContext integration
- Semantic: FilterContext integration, search input for clusters, bulk negative per waste cluster
- Settings: form validation (min/max on safety_limits + business_rules), dirty state tracking with beforeunload
- Agent: chat history persistence via localStorage (max 50 messages, "Wyczyść historię" button)
- New `useNavigateTo` hook (frontend/src/hooks/useNavigateTo.js) for centralized cross-tab navigation
- Alerts anomalies → Campaigns navigation (click campaign_id)
- QualityScore → Keywords navigation (click low-QS keyword row)
- Forecast → Campaigns navigation ("Kampania →" link)
- SearchOptimization inline "Wyklucz" button on wasted search terms
- Reports PDF/Print button (window.print, zero new dependencies)

### New Files
- `frontend/src/components/WoWChart.jsx` — WoW period comparison chart
- `frontend/src/hooks/useNavigateTo.js` — centralized navigation hook
- `backend/tests/test_campaigns_summary.py` — 2 tests for campaigns-summary endpoint
- `backend/tests/test_wasted_spend_dates.py` — 3 tests for wasted-spend date filtering
- `backend/tests/test_wow_comparison.py` — 3 tests for wow-comparison endpoint
- `docs/reviews/` — 4 review documents (ads-expert + ads-verify for dashboard and all)

## Dashboard Polish Sprint (2026-03-26)

### From ads-verify plan (9/9 tasks DONE — confirmed by /ads-check)
- K1: Sortable campaign table — click Budżet/Koszt/Konwersje/ROAS headers
- K2: Deep-link campaign rows → /campaigns?campaign_id=X
- N1: Clickable Wasted Spend card → /search-terms?segment=WASTE
- N2: "Poranny przegląd →" link in dashboard header → /daily-audit
- N3: InsightsFeed priority filter pills (Pilne/Średnie/Info)
- N4: Sparkline tooltip on hover
- N5: Tooltip on truncated bidding strategy column
- N6: Sortable geo table (click any column header)
- N7: IS per campaign column in dashboard table (backend: campaigns-summary endpoint + frontend)

### Other improvements
- WoW chart fix: X-axis now shows dates (25.03) instead of day names (Pon)
- Campaigns page: sort dropdown + metric filter + mini-metrics (cost/conv/ROAS) in sidebar tiles
- New skills: `/ads-user` (PPC user simulation), `/ads-check` (QA gate)
- Updated `/ads-verify` with post-implementation instructions
- Ads review pipeline documented in CLAUDE.md section 7b

### Validation
- 474 backend tests passing
- Frontend build passing (vite build)
- Ads review reports: docs/reviews/ads-{user,expert,verify,check}-dashboard.md

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
- Address 3 npm audit high-severity dependency warnings in frontend toolchain (undici — fixable via `npm audit fix`)

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
- Archived 5 obsolete MD files to `docs/archive/` (removed 2026-03-31, content absorbed into roadmap)
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

## GAP Analysis — Phase A + B + C (2026-03-21 — commit e627d82)
- Implemented 12 new analytics endpoints covering Smart Bidding, account structure, conversion quality, and demographics:
  - **GAP 1A** `GET /analytics/learning-status` — detect campaigns in Smart Bidding learning period
  - **GAP 1C** `GET /analytics/smart-bidding-health` — Smart Bidding conversion volume health check
  - **GAP 1D** `GET /analytics/target-vs-actual` — compare targets with actual CPA/ROAS
  - **GAP 1E** `GET /analytics/portfolio-health` — portfolio bid strategy health analysis
  - **GAP 2A-2D** `GET /analytics/conversion-quality` — conversion action configuration audit
  - **GAP 4A** `GET /analytics/demographics` — age/gender breakdown with CPA anomaly flags
  - **GAP 6A** `GET /analytics/change-impact` — post-change performance delta (7d before/after)
  - **GAP 6B** `GET /analytics/bid-strategy-impact` — bid strategy change impact (14d before/after)
  - **GAP 7A** `GET /analytics/pareto-analysis` — Pareto 80/20 campaign value contribution
  - **GAP 7B** `GET /analytics/scaling-opportunities` — hero campaigns with IS headroom
  - **GAP 8** `GET /analytics/ad-group-health` — ad group structural health checks
  - **GAP 10** `GET /analytics/bid-strategy-report` — daily target vs actual time series
- Added `ConversionAction` model (`backend/app/models/conversion_action.py`) for conversion tracking metadata
- Added 9 new recommendation rules (R19–R27):
  - R19: `AD_GROUP_HEALTH` — ad count, keyword count, zero-conv groups (split into `SINGLE_AD_ALERT`, `OVERSIZED_AD_GROUP`, `ZERO_CONV_AD_GROUP`)
  - R20: `DISAPPROVED_AD_ALERT` — disapproved/approved-limited ads
  - R21: `SMART_BIDDING_DATA_STARVATION` — insufficient conversion volume for Smart Bidding (renamed from `SMART_BIDDING_CONV_ALERT`)
  - R22: `ECPC_DEPRECATION` — eCPC deprecation warning
  - R23: `SCALING_OPPORTUNITY` — hero campaigns with IS headroom to scale
  - R24: `TARGET_DEVIATION_ALERT` — CPA/ROAS significantly off target
  - R25: `LEARNING_PERIOD_ALERT` — stuck in learning period
  - R26: `CONVERSION_QUALITY_ALERT` — conversion configuration issues
  - R27: `DEMOGRAPHIC_ANOMALY` — age/gender CPA anomalies
- Extended Campaign model with `target_cpa_micros`, `target_roas`, `primary_status`, `primary_status_reasons`, `bidding_strategy_resource_name`, `portfolio_bid_strategy_id`
- Extended MetricSegmented model with `age_range`, `gender` columns
- Extended Google Ads sync with `sync_conversion_actions()`, `sync_age_metrics()`, `sync_gender_metrics()`
- Extended seed data for new models (conversion actions, demographic metrics)
- Frontend: expanded SearchOptimization.jsx with 5 new analysis sections (19 tools total), updated ActionHistory.jsx and Recommendations.jsx
- Seed: 8 campaigns (was 7), 6 ConversionAction records with intentional quality issues, 90 days age/gender demographic data
- DB schema: deleted + reseeded (no Alembic — new columns + new table require fresh DB)

## Validation (GAP Analysis Phase A+B+C 2026-03-21)
- Backend: 355 tests passed (`pytest --tb=short -q`)
- Recommendations contract test: 26 enum values verified
- Seed: all new data visible after reseed (ConversionAction, demographics, campaign extensions)

## GAP Analysis — Phase D: PMax, Audiences, Extensions (2026-03-22)
- Added 6 new models:
  - `AssetGroup` — PMax asset group metadata (ad_strength, status, final_urls)
  - `AssetGroupDaily` — daily metrics per asset group (clicks, impressions, cost, conversions)
  - `AssetGroupAsset` — assets linked to asset groups (type, performance_label, policy_summary)
  - `AssetGroupSignal` — audience signals attached to asset groups (signal_type, signal_value)
  - `CampaignAudienceMetric` — audience segment performance per campaign (audience_name, segment_type)
  - `CampaignAsset` — campaign-level assets/extensions (sitelinks, callouts, structured snippets, etc.)
- Extended `MetricSegmented` model with `ad_network_type` column for channel-level breakdowns
- Added 7 new analytics endpoints:
  - `GET /analytics/pmax-channels` — PMax channel breakdown (Search, Display, YouTube, etc.) via ad_network_type
  - `GET /analytics/asset-group-performance` — asset group metrics with ad_strength and asset counts
  - `GET /analytics/pmax-search-themes` — PMax search themes from asset group signals
  - `GET /analytics/audience-performance` — audience segment performance across campaigns
  - `GET /analytics/missing-extensions` — detect campaigns missing recommended extensions
  - `GET /analytics/extension-performance` — extension type performance metrics
  - (plus 1 internal helper endpoint)
- Added 7 new sync methods (total 22 sync phases):
  - `sync_pmax_channel_metrics` — PMax ad_network_type segmented metrics
  - `sync_asset_groups` — asset group metadata from Google Ads
  - `sync_asset_group_daily` — daily asset group performance
  - `sync_asset_group_assets` — asset-to-asset-group mappings
  - `sync_asset_group_signals` — audience signals per asset group
  - `sync_campaign_audiences` — audience segment metrics per campaign
  - `sync_campaign_assets` — campaign-level extensions/assets
- Wired 3 previously orphaned sync phases into the sync pipeline
- Added 4 new recommendation rules (R28–R31, total 30 enum values):
  - R28: `PMAX_CHANNEL_IMBALANCE` — PMax channel distribution anomalies
  - R29: `ASSET_GROUP_AD_STRENGTH` — weak ad strength in asset groups
  - R30: `AUDIENCE_PERFORMANCE_ANOMALY` — underperforming audience segments
  - R31: `MISSING_EXTENSIONS_ALERT` — campaigns missing recommended extensions
- Frontend: added 6 new analysis sections in `SearchOptimization.jsx` (25 total tools)
- Frontend: added 4 new TYPE_CONFIG entries in `Recommendations.jsx` for Phase D rules
- Seed data extended with Phase D data (asset groups, signals, audience metrics, campaign assets, PMax channel metrics)
- DB schema: deleted + reseeded (no Alembic — new models + new columns require fresh DB)

## Validation (GAP Analysis Phase D 2026-03-22)
- Backend: 385 tests passed (`pytest --tb=short -q` — 30 new Phase D tests)
- Recommendations contract test: 34 enum values verified (was 26 → 30 → 34)
- Seed: all Phase D data visible after reseed (AssetGroup, AssetGroupDaily, AssetGroupAsset, AssetGroupSignal, CampaignAudienceMetric, CampaignAsset, PMax channel metrics)

## Comprehensive Playwright E2E Tests (2026-03-22 — commit 262792d)
- Added 104 new mocked-API E2E tests across 12 spec files based on MANUAL_TESTING_GUIDE.md:
  - `dashboard.spec.js` (8 tests) — Sekcja 3: health score gauge, KPI cards, budget pacing, device share, date range
  - `campaigns.spec.js` (7 tests) — Sekcja 4: table rendering, status/type badges, KPI row, Polish chars
  - `keywords.spec.js` (8 tests) — Sekcja 5: table, match type pills, search, tabs, QS badges, Polish chars
  - `search-terms.spec.js` (8 tests) — Sekcja 6: segments, bulk actions, checkboxes, export, view toggle
  - `recommendations.spec.js` (9 tests) — Sekcja 7: cards, priority filters, outcome badges, dismiss, summary
  - `daily-audit.spec.js` (9 tests) — Sekcja 8: health gauge, KPI chips, anomalies, disapproved ads, quick scripts
  - `alerts.spec.js` (9 tests) — Sekcja 14: tabs, severity badges, z-score anomalies, threshold/period pills
  - `agent-reports.spec.js` (7 tests) — Sekcje 16-17: quick actions, textarea, report list
  - `settings-clients.spec.js` (7 tests) — Sekcje 20-21: form sections, hard reset, client list
  - `analytics-tools.spec.js` (6 tests) — Sekcja 10: search optimization, quality score, forecast, semantic
  - `action-history.spec.js` (6 tests) — Sekcja 18: timeline, status badges, tabs
  - `edge-cases.spec.js` (20 tests) — Sekcja 27: empty states (13 pages), Polish chars, no undefined/NaN, responsive, long names
- Added shared `fixtures.js` with realistic mock data (micros values, float conversions, Polish chars)
- Total Playwright E2E: 185 tests (19 smoke + 20 full-app + 104 comprehensive + 42 edge-case retries)

## Validation (E2E tests 2026-03-22)
- Playwright: 185 tests passed (100% pass rate, `npx playwright test`)

## Recommendation Rules Refactoring (2026-03-22)
- Split monolithic `AD_GROUP_HEALTH` rule into 3 granular rules:
  - `SINGLE_AD_ALERT` — ad group with <2 active ads (no A/B testing)
  - `OVERSIZED_AD_GROUP` — ad group with too many keywords (>20)
  - `ZERO_CONV_AD_GROUP` — ad group with spend but 0 conversions
- Renamed `SMART_BIDDING_CONV_ALERT` → `SMART_BIDDING_DATA_STARVATION` for clarity
- Added `LOW_CTR_KEYWORD` rule (was incorrectly using `PAUSE_KEYWORD` for low-CTR alerts)
- Changed `WASTED_SPEND_ALERT` from per-campaign to account-level aggregation with $50 minimum spend threshold
- Total recommendation types: 30 → 34
- Frontend: added TYPE_CONFIG entries for all previously missing v1.1/v1.2 rule types + added category filter (Rekomendacje/Alerty)

## Full Audit Fixes + SSE Sync Modal (2026-03-25 — commit b139228)
- Backend fixes:
  - Fixed batch apply contradictory failed/applied logic in action_executor.py
  - Added int() guards on GAQL query interpolation (google_ads.py)
  - Added ImportError guard for numpy/pandas/scipy (analytics.py)
  - Moved deferred imports to top-level (daily_audit.py, recommendations.py)
  - Return HTTPException(400) instead of 200+error dict for forecast (analytics.py)
  - Fixed schema default conversions: float = 0 → 0.0 (campaign.py)
  - Added auto-migration for new columns (labels, target_cpa_micros, target_roas, primary_status, bidding_strategy_resource_name, portfolio_bid_strategy_id, age_range, gender)
- Frontend fixes:
  - Fixed SyncModal drawer-close bug (mousedown handler was closing drawer when clicking inside overlay)
  - Replaced 8 silent `.catch(() => {})` with console.error logging
  - Added `_catch(label)` helper for 25 SearchOptimization silent catches
  - Fixed off-palette colors: #EF4444 → #F87171, #14171D → #111318
  - Fixed Forecast.jsx infinite spinner on error (added error state + cancelled guard)
  - Added AbortController to Reports SSE fetch + cleanup on unmount
  - Fixed Polish diacritics in Reports.jsx
  - Removed unused FilterBar.jsx, Clients.jsx, exportSearchTerms/exportKeywords
- New features:
  - SSE sync streaming modal (`SyncModal.jsx`, `useSyncStream.js`)
  - Sync configuration with presets (`sync_config.py`, 4 new sync endpoints)
  - Per-resource sync coverage tracking (`sync_coverage.py`)
  - `DarkSelect`, `GlobalDatePicker` components

## Validation (2026-03-25)
- Backend: 466 tests passed (385 prior + 15 new sync router + 66 from other new test files)
- Frontend production build passed

## Sync Phase Runtime Fixes (2026-03-25 — commit 69e87da)
- Added missing `_execute_query()` method in `google_ads.py` used by `sync_asset_group_signals` and `sync_campaign_audiences`
- Fixed UNIQUE constraint failures on `metrics_segmented`: added missing `hour_of_day`, `ad_network_type`, `age_range`, `gender` IS NULL filters to existing-row lookups
- Fixed SQLite Date type error in `sync_pmax_channel_metrics`: convert string date to Python `date` object via `date.fromisoformat()`
- Fixed INVALID_ARGUMENT in `sync_campaign_assets`: removed unsupported `campaign_asset.source` and `metrics.ctr` fields
- Fixed SyncModal drawer-close bug: added `data-sync-modal` attribute to overlay to prevent ClientDrawer mousedown handler from closing it

## Sprint Test Expansion (2026-03-25 — commit 4151e26)
- Fixed `test_keyword_sync_cleanup` mock: `build_campaign_row` now includes extended query fields (labels, bidding_strategy_type, target_cpa, target_roas, primary_status) so sync_campaigns succeeds on first extended query attempt
- Added 62 new sprint tests across 4 files:
  - `test_sprint1_rules.py`: 37 tests for recommendation rules engine (all 34 rule types + edge cases)
  - `test_sprint2_analytics.py`: 7 tests for analytics endpoints (Phase B+C+D)
  - `test_sprint3_bidding.py`: 11 tests for bidding advisor and smart bidding endpoints
  - `test_data_coverage.py`: 7 tests for sync data coverage and presets endpoints
- Backend test count: 466 → 528 tests

## Visual Verification Pipeline (2026-03-28 — commit 5a77a17)
- New `/visual-check` command: Playwright screenshots of all pages against live backend
- `visual-audit.spec.js`: automated screenshot test for all 15 pages
- `VISUAL_AUDIT_REPORT.md`: full audit with per-page analysis + design system check
- 15/15 pages render correctly, 0 JS errors, 0 crashes, 9/10 visual score
- Updated `/ceo`, `/done`, `/ads-user` pipelines to require visual verification step

## Frontend Endpoint Gap Fix (2026-03-28 — commit 9341d9f)
- Connected 6 backend-only endpoints to frontend UI:
  - `audiences-list`: wired existing api function into SearchOptimization loadAll
  - `mcc-accounts`, `offline-conversions`, `conversion-value-rules`: added api functions + UI sections
  - `bidding-target PATCH`: added api function + target CPA/ROAS display in Campaigns header
  - `placement-exclusion POST`: added api function + "Wyklucz" button in placements table
- New UI section: Conversion Value Rules in SearchOptimization
- Visual regression: 15/15 page baseline snapshots pass
