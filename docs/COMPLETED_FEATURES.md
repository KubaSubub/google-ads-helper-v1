# Completed Features — DO NOT MODIFY UNLESS ASKED

These features are done and tested. Do NOT refactor, "improve", or touch them without explicit user request.

---

## PMax Search Terms
- `sync_pmax_search_terms()` uses `campaign_search_term_view` (NOT `search_term_view`, NOT `campaign_search_term_insight`)
- CRITICAL: Do NOT add `segments.keyword.info.*` to campaign_search_term_view queries — it filters out PMax data
- SearchTerm model: `ad_group_id` is nullable (PMax has no ad_groups), `campaign_id` FK for PMax direct link, `source` column ("SEARCH"/"PMAX")
- Sync Phase 5b calls `sync_pmax_search_terms()` after standard `sync_search_terms()`

## Global Date Range Picker + Unified Filtering
- DateRangePicker component lives in GlobalFilterBar (campaign type, status, date range).
- FilterContext exposes: `filters.period`, `filters.dateFrom`, `filters.dateTo`, computed `days`, `dateParams`, `campaignParams`, `allParams`.
- Period preset (7/14/30/90) auto-sets dateFrom/dateTo. Custom dates clear period to null.
- Backend: `resolve_dates()` in `backend/app/utils/date_utils.py` — central date resolution (`date_from`/`date_to` override `days`).
- Backend: `_filter_campaigns()` / `_filter_campaign_ids()` in AnalyticsService — reusable campaign filtering by type/status.
- ~20 analytics endpoints accept `date_from`, `date_to`, `campaign_type`, `campaign_status` (additive — `days` still works).
- Category A pages (Dashboard, Campaigns, Keywords, SearchTerms, AuditCenter, Recommendations) use `allParams` from FilterContext.
- Category B pages (DailyAudit, ActionHistory, Alerts, QualityScore, Reports, Forecast) have independent or no filtering.
- GlobalFilterBar is conditionally rendered only on Category A routes.
- Campaigns list now uses server-side filtering via API params (was in-memory).
- Keywords: date filtering aggregates from `keywords_daily` table (SUM per keyword); without dates falls back to Keyword snapshot.

## AppContext — Centralized Client State
- `clients`, `clientsLoading`, `refreshClients` live in AppContext (NOT useClients hook)
- Sidebar.jsx reads clients from useApp(), NOT from useClients()
- After discover, clients appear immediately in sidebar dropdown

## Auth Setup Wizard
- `GET /auth/setup-status`, `POST /auth/setup` endpoints in auth.py
- Login.jsx has step-by-step credential setup before Google OAuth
- All tokens stored in Windows Credential Manager via keyring

## KeywordDaily (Date Aggregation)
- Model `KeywordDaily`: keyword_id + date → clicks, impressions, cost_micros, conversions, conversion_value_micros, avg_cpc_micros
- Router `keywords_ads.py`: two paths — daily aggregation (with date_from/date_to) vs snapshot (without dates)
- Seed: 90 days per keyword with trend + dow + noise factors
- Summable metrics in KeywordDaily; snapshot metrics (quality_score, impression_share, bid) stay on Keyword model

## Audit Center (formerly Search Optimization)
- `AuditCenterPage.jsx` (in `features/audit-center/`) — 25 analysis sections with bento card layout, extracted into individual section components
- Endpoints: dayparting, rsa-analysis, ngram-analysis, match-type-analysis, landing-pages, wasted-spend, search-term-trends, close-variants, conversion-health, keyword-expansion, smart-bidding-health, learning-status, target-vs-actual, portfolio-health, pareto-analysis, scaling-opportunities, ad-group-health, bid-strategy-report, demographics, pmax-channels, asset-group-performance, pmax-search-themes, audience-performance, missing-extensions, extension-performance
- Backend: analytics_service.py methods + analytics.py routes
- Sidebar nav: "Centrum audytu" (Zap icon) in ANALIZA group
- Old `/search-optimization` route redirects to `/audit-center`

## Keyword Lifecycle Cleanup + Canonical SQLite
- Successful sync of campaigns, ad groups, and keywords now marks unseen local rows as `REMOVED`.
- Keyword list hides `REMOVED` by default and can include them explicitly via `include_removed` / `Pokaz usuniete`.
- Keyword API returns campaign and ad group context directly (`campaign_id`, `campaign_name`, `ad_group_name`).
- Runtime SQLite path is canonicalized to `<repo>/data/google_ads_app.db`; legacy `backend/data/google_ads_app.db` is migrated once if needed.

## Negative Keyword Hardening
- Positive keywords and negative keyword criteria are cached separately: `keywords` vs `negative_keywords`.
- Both caches use explicit `criterion_kind` values (`POSITIVE`, `NEGATIVE`).
- Positive sync has multi-layer guards against `negative=true` rows.
- Negative keyword sync now covers campaign-level and ad-group negatives and stores them in `negative_keywords`.
- Backend exposes `GET /negative-keywords/` and source-of-truth debug differentiates DB positive vs DB negative rows.

## Client Hard Reset
- `POST /clients/{id}/hard-reset` deletes only the selected client's local runtime data and keeps the client record.
- Settings page requires exact-name confirmation before reset.
- Reset clears campaigns and cascaded cache data plus direct client tables like recommendations, action logs, alerts, change events, negatives, and sync logs.

## AI Agent (Raport AI)
- Claude Code headless integration via subprocess (`claude -p --output-format stream-json`).
- Backend: `AgentService` gathers data from existing services (KPIs, campaigns, keywords, search terms, alerts, recommendations, budget pacing), builds prompt, streams response via SSE.
- Router: `agent.py` with `/agent/status` and `/agent/chat` endpoints, single-request lock prevents concurrent generation.
- Frontend: `Agent.jsx` — chat interface with quick report buttons, SSE stream parsing, markdown rendering.
- Quick report types: weekly, campaigns, keywords, search_terms, budget, alerts, freeform.

## Daily Audit Panel
- `DailyAudit.jsx` — centralny widok codziennego workflow z health score, alerts, top movers, budget pacing.
- Agreguje dane z istniejących endpointów (KPIs, alerts, recommendations, budget).
- Sidebar nav: "Codzienny audyt" w grupie WORKFLOW.

## Change History Monitor (ActionHistory)
- Model: `ChangeEvent` — tracking zmian w koncie Google Ads via Change Event API.
- Router: `history.py` — `GET /history/`, `GET /history/unified`, `GET /history/filters` endpoints.
- Frontend: `ActionHistory.jsx` — timeline view z filtrami (typ zmiany, zakres dat, kampania).
- Źródła: lokalne action_log + Google Ads Change Events.

## Bulk Search Term Actions
- SearchTerms page: multi-select + bulk add negative / bulk exclude.
- Backend: batch endpoint for negative keyword operations.
- Frontend: checkbox selection, bulk action toolbar w `SearchTerms.jsx`.

## Quick Optimization Scripts (Bulk-Apply)
- `POST /recommendations/bulk-apply` — apply batch of recommendations by quick-script category.
- Categories: `clean_waste`, `pause_burning`, `boost_winners`, `emergency_brake`, `add_negatives`.
- Dry-run mode supported. Frontend integration in Recommendations page.

## Reports System (Monthly Deep Dive)
- Backend: `reports.py` router with `/reports/generate` SSE endpoint.
- SSE streaming via `backend/app/utils/sse.py` helper.
- Frontend: `Reports.jsx` — report generation with real-time streaming, markdown rendering.
- Report types: monthly performance deep dive.

## Negative Keyword Lists
- Full CRUD for negative keyword lists (create, read, update, delete).
- Backend: endpoints in `keywords_ads.py` for list management.
- Frontend: management UI in `Keywords.jsx` with modal for list operations.

## Weekly & Health Reports
- `POST /reports/generate` now supports `report_type: "weekly"` (last 7 days) and `report_type: "health"` (last 30 days).
- Both types use dedicated `REPORT_DATA_MAP` sections and `REPORT_PROMPTS` in `agent_service.py`.
- Same SSE streaming and DB persistence as monthly reports.

## Search Term Trends (`/analytics/search-term-trends`)
- `GET /analytics/search-term-trends?client_id=X&days=30&min_clicks=5`
- Classifies search terms as rising, declining, or new based on week-over-week click trends.
- Implemented in `AnalyticsService.get_search_term_trends()`.

## Close Variant Analysis (`/analytics/close-variants`)
- `GET /analytics/close-variants?client_id=X&days=30`
- Compares search terms against exact-match keywords to identify close variant leakage.
- Implemented in `AnalyticsService.get_close_variant_analysis()`.

## Conversion Tracking Health (`/analytics/conversion-health`)
- `GET /analytics/conversion-health?client_id=X&days=30`
- Per-campaign audit: spend, conversions, conversion rate, and health status flag.
- Implemented in `AnalyticsService.get_conversion_tracking_health()`.

## Keyword Expansion Suggestions (`/analytics/keyword-expansion`)
- `GET /analytics/keyword-expansion?client_id=X&days=30&min_clicks=3`
- Surfaces high-performing search terms not yet added as keywords, grouped by match type recommendation.
- Implemented in `AnalyticsService.get_keyword_expansion()`.

## Forecast Page
- `Forecast.jsx` — per-campaign metric forecast (clicks, cost, conversions) for the next 14 days.
- Backend: `GET /analytics/forecast?campaign_id=X&metric=clicks&forecast_days=14` with metric aliases (`cost` → `cost_micros`, `cpc` → `avg_cpc_micros`).
- Sidebar nav: "Prognoza" in navigation.
- Category B page (independent filters, no GlobalFilterBar).

## Phase B+C GAP Analysis (Smart Bidding, Account Structure, Conversions)
- 12 new analytics endpoints covering playbook gaps: smart-bidding-health, learning-status, target-vs-actual, portfolio-health, conversion-quality, demographics, change-impact, bid-strategy-impact, pareto-analysis, scaling-opportunities, ad-group-health, bid-strategy-report.
- 13 recommendation rules (R19–R27 + sub-rules): AD_GROUP_HEALTH, SINGLE_AD_ALERT, OVERSIZED_AD_GROUP, ZERO_CONV_AD_GROUP, DISAPPROVED_AD_ALERT, SMART_BIDDING_DATA_STARVATION, ECPC_DEPRECATION, SCALING_OPPORTUNITY, TARGET_DEVIATION_ALERT, LEARNING_PERIOD_ALERT, CONVERSION_QUALITY_ALERT, DEMOGRAPHIC_ANOMALY, LOW_CTR_KEYWORD.
- `ConversionAction` model for conversion tracking metadata.
- Campaign model extended with bidding strategy fields (bidding_strategy_type, target_cpa_micros, target_roas, bidding_status, learning_status, performance_label, portfolio_strategy_id).
- MetricSegmented model extended with age_range and gender columns.
- Google Ads sync extended with sync_conversion_actions() and sync_demographic_metrics().

## Phase D GAP Analysis (PMax, Audiences, Extensions)
- 8 new analytics endpoints: pmax-channels, pmax-channel-trends, asset-group-performance, pmax-search-themes, audience-performance, missing-extensions, extension-performance, pmax-search-cannibalization.
- 4 new recommendation rules (R28–R31): PMAX_CHANNEL_IMBALANCE, ASSET_GROUP_AD_STRENGTH, AUDIENCE_PERFORMANCE_ANOMALY, MISSING_EXTENSIONS_ALERT.
- 6 new models: AssetGroup, AssetGroupDaily, AssetGroupAsset, AssetGroupSignal, CampaignAudienceMetric, CampaignAsset.
- MetricSegmented model extended with ad_network_type column for channel-level breakdowns.
- 7 new sync methods (22 total phases): sync_pmax_channel_metrics, sync_asset_groups, sync_asset_group_daily, sync_asset_group_assets, sync_asset_group_signals, sync_campaign_audiences, sync_campaign_assets.
- Frontend: 8 new analysis sections in AuditCenterPage.jsx (25 total tools).

## Campaign Roles + Context-Aware Budget Guardrails + Explanation Layer
- Deterministic campaign role service (`campaign_roles.py`) with `campaign_role_auto`, `campaign_role_final`, `role_confidence`, `protection_level`, `role_source`.
- `PATCH /campaigns/{id}` for manual role override / reset (never overwritten by sync/classifier).
- Recommendation model extended with `context_outcome`, `blocked_reasons`, `downgrade_reasons`.
- Fixed reason-code contract in `recommendation_contract.py`.
- Explanation blocks in recommendation evidence: `why_allowed`, `why_blocked`, `tradeoffs`, `risk_note`, `next_best_action`.
- Frontend: context outcome badges, role/protection/headroom chips, explanation sections, disabled apply for non-executable cards.

## DEMO Write Lock
- Backend DEMO guard (`demo_guard.py`) with protected identity based on `demo_google_customer_id` / `demo_client_id`.
- Enforced on all write paths (sync, recommendations, actions, analytics writes, campaign overrides, client mutations).
- Override is explicit and per-request only: `allow_demo_write=true`.

## Recommendation Rules Refactoring (34 types)
- Split monolithic `AD_GROUP_HEALTH` into 3 granular rules: `SINGLE_AD_ALERT`, `OVERSIZED_AD_GROUP`, `ZERO_CONV_AD_GROUP`.
- Renamed `SMART_BIDDING_CONV_ALERT` → `SMART_BIDDING_DATA_STARVATION`.
- Added `LOW_CTR_KEYWORD` rule.
- Changed `WASTED_SPEND_ALERT` from per-campaign to account-level aggregation with $50 minimum spend threshold.
- Total recommendation types: 34.

## SSE Sync Streaming Modal
- `SyncModal.jsx` + `useSyncStream.js` — real-time sync progress with per-phase SSE updates.
- Backend: `POST /sync/trigger-stream` SSE endpoint with preset/phase/date selection.
- Sync presets: `GET /sync/presets` — phase registry with groups, max_days, and preset patterns.
- Per-resource coverage: `GET /sync/coverage` — sync coverage tracking per client.
- `sync_config.py` + `sync_coverage.py` backend modules.
- `DarkSelect` and `GlobalDatePicker` reusable components.

## Dashboard Overhaul + Cross-App Navigation
- Dashboard: CTR, Impressions, CPA, Wasted Spend KPI cards; geo share_cost_pct; Health→Alerts nav; campaign row click→/campaigns; "Wszystkie →" links.
- New `GET /analytics/campaigns-summary` endpoint — per-campaign aggregated metrics (clicks, impressions, cost_usd, conversions, ctr, roas) for a given period.
- New `GET /analytics/wow-comparison` endpoint — current vs previous period with day-of-week alignment for overlay chart.
- `WoWChart.jsx` — WoW period comparison chart with metric selector.
- `useNavigateTo` hook for centralized cross-tab navigation (Alerts→Campaigns, QualityScore→Keywords, Forecast→Campaigns, etc.).
- Forecast: horizon selector (7/14/30d), FilterContext integration.
- Semantic: FilterContext integration, search input for clusters, bulk negative per waste cluster.
- Settings: form validation (min/max on safety_limits + business_rules), dirty state tracking with beforeunload.
- Agent: chat history persistence via localStorage (max 50 messages, "Wyczyść historię" button).
- Reports: PDF/Print button (window.print, zero new dependencies).

## Dashboard Polish Sprint
- Sortable campaign table — click Budżet/Koszt/Konwersje/ROAS headers to sort.
- Deep-link campaign rows → `/campaigns?campaign_id=X`.
- Clickable Wasted Spend card → `/search-terms?segment=WASTE`.
- "Poranny przegląd →" link in dashboard header → `/daily-audit`.
- InsightsFeed priority filter pills (Pilne/Średnie/Info).
- Sparkline tooltip on hover.
- Tooltip on truncated bidding strategy column.
- Sortable geo table (click any column header).
- IS (Impression Share) per campaign column in dashboard table.
- WoW chart X-axis shows dates (25.03) instead of day names.

## Campaigns Sort/Filter Enhancements
- Sort dropdown + metric filter in sidebar campaign tiles.
- Mini-metrics (cost, conversions, ROAS) visible in campaign sidebar tiles.

## Google Ads Coverage Expansion (Wave A-E)
- 12 new models: AuctionInsight, ProductGroup, Placement, BidModifier, Audience, TopicPerformance, BiddingStrategy, SharedBudget, GoogleRecommendation, ConversionValueRule, MccLink, OfflineConversion.
- 14 new sync phases (37 total): product_groups, placement_metrics, bid_modifiers, bidding_strategies, shared_budgets, audiences, topic_metrics, google_recommendations, conversion_value_rules, pmax_channel_metrics, campaign_audiences, campaign_assets, asset_group_signals + existing asset_groups/asset_group_daily/asset_group_assets.
- Wave A: Auction Insights, Bid Modifiers, Target CPA/ROAS write, Extension details, Demographics (parental + income).
- Wave B: Shopping Product Group model + sync + analytics endpoint.
- Wave C: Placement model + sync + exclusion write, Topic Targeting, Audience Management.
- Wave D: Video metrics merged into Placement model.
- Wave E: Portfolio Bid Strategies, Shared Budgets, Google Recommendations, Conversion Value Rules, MCC Multi-Account, Offline Conversions.
- Frontend: new analysis sections in AuditCenterPage.jsx for each wave.

## Schema Auto-Migration
- `database.py` auto-migration adds missing columns (labels, target_cpa_micros, target_roas, primary_status, bidding_strategy_resource_name, portfolio_bid_strategy_id, age_range, gender) without requiring DB delete + reseed.

## Visual Verification Pipeline
- `/visual-check` command: Playwright screenshots of all 15 pages against live backend.
- `visual-audit.spec.js`: automated screenshot test suite.
- `VISUAL_AUDIT_REPORT.md`: per-page analysis + design system compliance check.
- Integrated into `/ceo`, `/done`, `/ads-user` pipelines as required verification step.

## Frontend Modular Architecture (features/)
- 16 feature modules under `frontend/src/features/`: audit-center, benchmarks, campaigns, competitive, cross-campaign, dashboard, display, dsa, keywords, mcc-overview, pmax, rules, scripts, shopping, task-queue, video.
- Sidebar extracted to `frontend/src/components/layout/Sidebar/` (SidebarContent, ClientSelector, ClientDrawer, NavItem, CampaignTypePills, navConfig).
- Shared components: `MatchBadge`, `MetricPill`, `SectionHeader` in `components/shared/`.
- Constants: `designTokens.js`, `campaignTypes.js`.
- Routes centralized in `frontend/src/app/routes.jsx` with lazy loading.
- Sidebar nav groups: PRZEGLĄD, DANE KAMPANII, DZIAŁANIA, MONITORING, AI, ANALIZA.

## Automated Rules Engine (F3)
- New router `rules.py` — 7 endpoints (GET/POST/PUT/DELETE/dry-run/execute per rule).
- Model `AutomatedRule` — per-client rule definition with conditions, actions, schedule.
- Service `rules_engine.py` — rule evaluation and execution engine.
- Frontend: `RulesPage.jsx` at `/rules`.

## Cross-Campaign Analysis (G4) + Benchmarks (H2) + Scheduled Sync (F1)
- Cross-Campaign (G4): 3 endpoints (`keyword-overlap`, `budget-allocation`, `campaign-comparison`), `CrossCampaignPage.jsx` at `/cross-campaign`.
- Benchmarks (H2): 2 endpoints (`benchmarks`, `client-comparison`), `BenchmarksPage.jsx` at `/benchmarks`.
- Scheduled Sync (F1): `ScheduledSyncConfig` model, `scheduler.py` asyncio-based background runner, 3 endpoints (`GET/POST/DELETE /sync/schedule`).

## DSA Support (C1/C2/C3)
- 4 analytics endpoints: `dsa-targets`, `dsa-coverage`, `dsa-headlines`, `dsa-search-overlap`.
- 2 models: `DsaTarget`, `DsaHeadline`.
- Frontend: `DsaPage.jsx` at `/dsa`.

## Task Queue / Plan dnia (H1)
- `TaskQueuePage.jsx` at `/tasks` — aggregates actionable items from recommendations, alerts, wasted spend.
- Priority badges, progress bar with localStorage persistence, quick action buttons per task type.

## Write Safety Layer + Remote-First Bidding
- `write_safety.py` — unified write-path safety: `record_write_action()`, daily limit helpers.
- `PATCH /campaigns/{id}/bidding-target` — remote-first (API push → local commit; fallback to local-only with `pending_sync: true`).
- `POST /analytics/offline-conversions/upload` — now functional (calls Google Ads API).
- Pipeline: demo guard → safety check → audit log.

## MCC Overview — Cross-Account Landing Page
- `MccOverviewPage.jsx` at `/mcc-overview` — default entry point (/ redirects here).
- Backend: `mcc.py` router with 7 endpoints: overview, new-access, dismiss-google-recommendations, negative-keyword-lists, shared-lists, shared-lists/{id}/items, billing-status.
- Per-account metrics: spend, conversions, CPA, ROAS, budget pacing, health score, change activity, Google recs, alerts, last sync.
- Sortable table columns, currency-aware formatting, spend sparkline per account row.
- MCC shared exclusion lists (negative keyword + placement) with drill-down.

## Settings — Marketing Mastermind Brief
- `strategy_context` JSON column on `clients` (auto-migrated via `_ensure_sqlite_columns`).
- `PATCH /clients/{id}` deep-merges `strategy_context` (partial updates, null is no-op).
- Schemas: `StrategyContext`, `LessonEntry`, `DecisionLogEntry` with length validators.
- Frontend: 5 brief sections in `Settings.jsx` (strategia, roadmap, log decyzji, lessons learned, brand voice).
- `ConversionGoalsSection.jsx` with full-width ConversionAction table and `primary_for_goal` column.

## Dashboard Consolidation + Scripts Engine Integration
- Dashboard reworked as single daily-operations surface; `/daily-audit` hidden from nav (still accessible).
- Removed redundant widgets (Insights Feed, Campaign Table, PMax Split, Recent Actions).
- Header filter bar: `HeaderClientSelector.jsx` + `HeaderCampaignTypeSelector.jsx` (hidden on /mcc-overview).
- Scripts Engine badge linking to `/scripts` showing total actionable items.
- Component extraction: `BudgetPacingCard`, `AnomalyAlertsCard`, `ScriptRunModal` (~500 LOC reduction).
- TrendExplorer annotations: action history markers on chart with rich tooltips.
- KPI tooltips: full definitions for all 25 dashboard KPIs.

## Optimization Scripts Engine
- `backend/app/services/scripts/` — modular script architecture with `BaseScript`, `_helpers.py`.
- 9 scripts: `a1_zero_conv_waste`, `a2_irrelevant_dictionary`, `a3_low_ctr_waste`, `a6_non_latin_script`, `b1_high_conv_promotion`, `c2_duplicate_coverage`, `d1_ngram_waste`, `d3_ngram_audit`, `f1_competitor_term`.
- Router `scripts.py` — 8 endpoints: catalog, counts, dry-run, execute, history, config CRUD.
- Frontend: `ScriptsPage.jsx` at `/scripts` — catalog view, per-script dry-run/execute UI, execution history.
- Per-client config in `Client.script_configs` JSON column (auto-migrated).
- Sidebar: "Skrypty" (Zap icon) in DZIAŁANIA group; `/recommendations` hidden but reachable.
- 11 test files + shared `scripts_fixtures.py`.

## Frontend Modular Architecture
- Monolithic page components (Dashboard 977→768 LOC, Campaigns 1180→779, Keywords 1035→55) refactored into feature modules under `frontend/src/features/`.
- 16 feature modules: audit-center, benchmarks, campaigns, competitive, cross-campaign, dashboard, display, dsa, keywords, mcc-overview, pmax, rules, scripts, shopping, task-queue, video.
- Sidebar extracted into `components/layout/Sidebar/` with data-driven `navConfig.js`.
- Routes centralized in `app/routes.jsx` with lazy loading for all pages.
- Shared UI: `MatchBadge`, `MetricPill`, `SectionHeader` in `components/shared/`.
- Design tokens and campaign type constants extracted into `constants/`.

## Campaign-Type Specific Pages
- 5 new campaign-type pages with dedicated UIs:
  - `/shopping` — ShoppingPage: product group performance tree, ROAS color-coding.
  - `/pmax` — PMaxPage: channel breakdown, asset groups, search themes, PMax vs Search cannibalization.
  - `/display` — DisplayPage: placement performance, topic targeting, placement exclusions.
  - `/video` — VideoPage: video placement metrics (views, view_rate, avg_cpv).
  - `/competitive` — CompetitivePage: auction insights, competitor visibility (IS, overlap, position above, outranking).
- Sidebar nav items filtered by campaign type (e.g., Keywords visible only for SEARCH).
- SearchOptimization renamed to "Centrum audytu" (`/audit-center`), old route redirects preserved.

## Audit Center Refactor + Bento Enhancements
- `SearchOptimization.jsx` removed from `pages/`; all audit logic lives in `features/audit-center/AuditCenterPage.jsx`.
- 25 type-specific section cards extracted into dedicated components under `features/audit-center/components/sections/`.
- `BentoCard.jsx` — reusable bento card wrapper with pin toggle and period comparison display.
- Period comparison on bento cards: `comparisonDefs` extracts numeric values and shows `% change vs previous period` badge per card.
- Card pinning: `pinnedKeys` state backed by `localStorage` (`audit-center-pinned` key), pinned cards sorted first in grid.
- Clear all pins button when any cards are pinned.

## Keyboard Shortcuts
- `useKeyboardShortcuts` hook (`frontend/src/hooks/useKeyboardShortcuts.js`) — global hotkeys for page navigation.
- `ShortcutsHint` component (`frontend/src/components/ShortcutsHint.jsx`) — floating hint overlay.
- Integrated in `App.jsx`.

## Cross-Navigation Hook (useNavigateTo)
- `useNavigateTo` hook (`frontend/src/hooks/useNavigateTo.js`) — centralized cross-tab navigation helper.
- Used in `Alerts.jsx`, `QualityScore.jsx`, `Forecast.jsx` for contextual deep-links (e.g., alert row -> campaign, keyword row -> keywords page).

## Forecast FilterContext Integration + Horizon Selector + Smart Retry
- `Forecast.jsx` uses `useFilter()` from FilterContext to sync initial horizon with global date range.
- Horizon selector pill buttons (7/14/30 days) with `forecastDays` state synced from FilterContext `days`.
- Smart retry: `retryCount` state triggers re-fetch on user action without full page reload.

## Semantic FilterContext + Search Input + Bulk Waste Exclude
- `Semantic.jsx` uses `useFilter()` for `days` parameter.
- `searchTerm` state with text input for filtering clusters by name or item text.
- Bulk waste exclude: `selectedWaste` set + `bulkExcluding` state; multi-select clusters and batch-add as negative keywords via `addNegativeKeyword` API.
- Floating bulk action toolbar appears when clusters are selected, showing count and total phrase count.

## Settings Form Validation + Dirty State Tracking
- `Settings.jsx` — `validate()` function checks safety_limits and business_rules fields against min/max constraints.
- `validationErrors` state with `hasErrors` gate on save button.
- `isDirty` computed from `JSON.stringify(formData) !== JSON.stringify(originalData)`.
- `beforeunload` event listener warns on unsaved changes; `popstate` listener covers in-app navigation.

## Shopping Page Enriched
- `ShoppingPage.jsx` (`features/shopping/`) — 3 tabs: Product Groups, Performance, Feed Health.
- KPI cards row: Clicks, Cost, Conversions, ROAS with aggregated data from all product groups.
- `roasColor()` helper for ROAS color-coding (red < 1, yellow 1-3, green > 3).
- Performance tab: top 5 and bottom 5 product groups ranked by ROAS.

## Video Page Enriched
- `VideoPage.jsx` (`features/video/`) — 3 tabs: Placements, Topics, Audiences.
- KPI cards: Views, View Rate, Avg CPV (PLN), Cost.
- CPV metrics with median-based high-CPV highlighting (>1.5x median flagged).
- Placement exclusion: `handleExclude()` per-row action to block underperforming placements.

## Competitive Page Enriched
- `CompetitivePage.jsx` (`features/competitive/`) — KPI cards for IS, overlap, position above, outranking share.
- `MetricBar` component for inline visual bars in table cells (overlap rate, outranking share).
- Competitive position summary section with self-metrics extracted from auction insights.
- Sortable table with per-competitor metrics.

## GlobalFilterBar Campaign Type Filter Removal
- `GlobalFilterBar.jsx` no longer renders a campaign type dropdown (was duplicate of Sidebar campaign type pills).
- Remaining filters: Status, Label (conditional), Campaign Name search.
- Campaign type filtering is handled exclusively by Sidebar `CampaignTypePills`.

## PMax Asset Groups Enrichment (D2)
- `PMaxPage.jsx` enriched with asset group KPI summary row (total groups, avg ad_strength, top/bottom performer).
- Asset strength distribution with colored pills (EXCELLENT/GOOD/AVERAGE/LOW/UNSPECIFIED).
- Sortable columns: clicks, cost, conversions, ROAS.
- ROAS color-coding: green (>4), yellow (2-4), red (<2).
- Expandable detail rows per asset group.

## Task Queue / Plan dnia (H1)
- `TaskQueuePage.jsx` (`features/task-queue/`) — aggregates actionable items from recommendations, alerts, and wasted spend.
- Priority badges (HIGH/MEDIUM/LOW) with sorting by priority.
- Progress tracking bar with localStorage persistence.
- Quick action buttons per task type (apply recommendation, resolve alert, exclude search term).
- Route: `/tasks`, sidebar: "Plan dnia" (ListChecks icon) in DZIAŁANIA group.

## Cross-Campaign Analysis (G4)
- 3 new analytics endpoints: keyword-overlap, budget-allocation, campaign-comparison.
- `CrossCampaignPage.jsx` (`features/cross-campaign/`) — keyword overlap matrix, budget allocation chart, side-by-side campaign comparison.
- Route: `/cross-campaign`, sidebar nav in ANALIZA group.

## Benchmarks (H2)
- 2 new analytics endpoints: benchmarks, client-comparison.
- `BenchmarksPage.jsx` (`features/benchmarks/`) — account KPI benchmarks and cross-client comparison.
- Route: `/benchmarks`, sidebar nav in ANALIZA group.

## Scheduled Sync (F1)
- `ScheduledSync` model (`scheduled_sync.py`) — per-client sync schedule (enabled, interval_hours).
- `Scheduler` service (`scheduler.py`) — asyncio-based background sync runner (no external packages).
- 3 endpoints in `scheduled_sync.py`: GET/POST/DELETE `/sync/schedule`.
- Registered in `main.py` as protected router.

## Automated Rules Engine (F3)
- New router: `rules.py` — 7 CRUD + execution endpoints.
- `GET /rules/` — list rules, `POST /rules/` — create, `GET/PUT/DELETE /rules/{rule_id}` — CRUD.
- `POST /rules/{rule_id}/dry-run` — simulate execution, `POST /rules/{rule_id}/execute` — run rule.
- Per-client rule definitions with conditions, actions, and scheduling.
- Registered in `main.py` as protected router (18 routers total).

## DSA Support (C1/C2/C3)
- 4 new analytics endpoints: `dsa-targets`, `dsa-coverage`, `dsa-headlines`, `dsa-search-overlap`.
- 2 new models: `DsaTarget` (auto-targets per campaign), `DsaHeadline` (headline performance metrics).
- C1: DSA target performance — auto-targets per campaign with clicks, cost, conversions.
- C2: DSA headline performance analysis — top/worst headlines by CTR/conversions.
- C3: DSA vs manual keyword overlap detection — search terms appearing in both DSA and manual campaigns.
- Seed data: DSA targets and headlines generated per client.
- Frontend: `features/dsa/` — dedicated DSA page at `/dsa` route.

## Automated Rules Frontend (F3)
- Frontend: `features/rules/` — dedicated Rules management page at `/rules` route.
- Full CRUD UI for automated rules (list, create, edit, delete, dry-run, execute).

## Z-Score Anomaly Detection
- `GET /analytics/z-score-anomalies?client_id=X&metric=cost&days=90&threshold=2.0` — z-score anomaly detection per campaign per day.
- Supported metrics: cost, clicks, impressions, conversions, ctr.
- Returns anomalies with z-score, date, metric value, plus mean/std for context.
- Anomalies list endpoint enriched with `campaign_name` and `metric_value` fields.

## Dashboard Widgets Expansion
- `DayOfWeekWidget.jsx` — day-of-week performance analysis (clicks/cost/conversions per weekday).
- `CampaignMiniRanking.jsx` — top/bottom campaign mini ranking by key metrics.
- `TopActions.jsx` — top recommended actions summary widget.
- `MiniKpiGrid.jsx` — expanded KPI grid with visual enhancements.
- `HealthScoreCard.jsx` — enhanced health score display with additional metrics.

## Write Safety Pipeline
- `write_safety.py` — unified write-path safety layer (demo guard → safety check → audit log) for all direct user-initiated mutations.
- Campaigns bidding-target endpoint refactored to remote-first (API push first, local commit on success, fallback with pending_sync warning).
- Complements ActionExecutor for recommendation-driven actions.

## Reusable UI Modules (BudgetPacingModule + KpiCard)
- Extracted shared `BudgetPacingModule` and `KpiCard` from duplicated inline code into `frontend/src/components/modules/`.
- `BudgetPacingModule.jsx` — budget pacing display with progress bar, spend vs budget, pacing percentage.
- `KpiCard.jsx` — standardized KPI card with label, value, trend indicator, optional comparison.
- `PacingProgressBar.jsx` — reusable progress bar for budget pacing visualization.
- `pacing-utils.js` — shared pacing calculation logic (pacing %, status, color).
- Used by: DashboardPage, CampaignsPage, DailyAudit, Reports, VideoPage, CrossCampaignPage, CompetitivePage.

## MCC Overview Landing Page
- `MccOverviewPage.jsx` (`features/mcc-overview/`) — cross-account aggregation dashboard as the app landing page.
- Route: `/mcc-overview`, set as default landing page (redirects from `/`).
- KPI cards: total spend, conversions, CPA, ROAS across all client accounts.
- Per-account table with health score (6-pillar breakdown), pacing status, change activity, unresolved alerts, last sync.
- External changes detection (`/mcc/new-access`), Google recommendations pending count.
- Negative keyword lists overview across all accounts (`/mcc/negative-keyword-lists`).
- Bulk dismiss Google recommendations (`/mcc/dismiss-google-recommendations`).
- MCC shared lists overview (`/mcc/shared-lists`), billing status check (`/mcc/billing-status`).
- Backend: `mcc.py` router with 7 endpoints (overview, new-access, dismiss-google-recommendations, negative-keyword-lists, shared-lists, shared-lists/{list_id}/items, billing-status).
- Reuses `BudgetPacingModule` and `KpiCard` shared components.
- Sprint 2: currency-aware formatting (per-account currency symbol), spend sparkline per row (56×20 LineChart from `spend_trend`).

## Optimization Scripts Engine (P0+P1 + Sprint 1-4)
- Modular script architecture in `backend/app/services/scripts/` with `BaseScript` class and shared helpers.
- 9 date-aware optimization scripts: zero-conv waste (A1), irrelevant dictionary (A2), low CTR waste (A3), non-Latin script (A6), high-conv promotion (B1), duplicate coverage (C2), n-gram waste (D1), n-gram audit (D3), competitor term detection (F1).
- Router: `scripts.py` — 8 endpoints: `GET /scripts/catalog`, `POST /scripts/{id}/dry-run`, `GET /scripts/counts`, `POST /scripts/{id}/execute`, `GET /scripts/{id}/history`, `GET /scripts/config/{client_id}`, `PUT /scripts/{id}/config`, `DELETE /scripts/{id}/config/{client_id}`.
- Per-client config persistence with defaults merging.
- Frontend: `ScriptsPage.jsx` (`features/scripts/`) — catalog view, dry-run preview, execute flow, execution history.
- Route: `/scripts`, sidebar: "Skrypty" (Zap icon) in DZIAŁANIA group.
- 11 backend test files with shared fixtures (`scripts_fixtures.py`).

## Settings — Marketing Mastermind Brief
- Settings pivoted from operational hub (duplicating Dashboard/DailyAudit) into marketing mastermind brief — single place for strategy, roadmap, decisions, lessons learned, brand voice.
- Backend: `strategy_context` JSON column on `Client` model with auto-migration via `_ensure_sqlite_columns`.
- Pydantic schemas: `StrategyContext`, `LessonEntry`, `DecisionLogEntry` with length validators.
- `PATCH /clients/{id}` deep-merges `strategy_context` (partial updates preserve other fields; `null` payload is a no-op).
- Frontend: `ConversionGoalsSection.jsx` — conversion action table with local priority toggling + "Cel Google Ads" column showing `primary_for_goal`.
- 5 brief sections: Strategia marketingowa, Plan działań/Roadmap, Log decyzji (read-only, AI coming soon), Wnioski i lessons learned (structured journal), Brand voice & zakazy.
- Tests: 11 backend (`test_client_strategy.py`), 10 E2E (`settings-mastermind-brief.spec.js`).

## Dashboard Consolidation + Header Filter Bar
- Dashboard reworked as single landing surface for daily operations; `/daily-audit` hidden from sidebar nav.
- Removed redundant widgets duplicating dedicated tabs: Insights Feed, Campaign Table, PMax Split, Recent Actions.
- Extracted components: `BudgetPacingCard.jsx`, `AnomalyAlertsCard.jsx`, `ScriptRunModal.jsx` (~500 LOC reduction).
- **Quick Scripts badge** links to `/scripts` page — shows total actionable items from scripts engine.
- **Header filter bar** replaces sidebar-mounted controls:
  - `HeaderClientSelector.jsx` — dropdown with client list, Google Customer ID, manage link.
  - `HeaderCampaignTypeSelector.jsx` — segmented pills (ALL / Search / PMax / Shopping / …).
  - Both hidden on `/mcc-overview` route.
- **TrendExplorer action annotations**: fetches action history, groups by date, renders `ReferenceLine` markers with rich tooltips (operation, entity, before→after values).
- **KPI tooltips**: full definitions for all 25 dashboard KPIs (benchmarks, formulas, practical advice) via viewport-aware floating info tooltip.
- Dashboard data reactivity fixes: endpoints resolve independently (no `Promise.all` blocking), date filters propagated to recommendations + QS audit, ENABLED-only campaigns forced.

## PERFORMANCE_MAX / PMAX Naming Consistency
- `constants/campaignTypes.js` uses `PERFORMANCE_MAX` as the canonical key (matching Google Ads API).
- Display label: `PMax` (short, user-facing).
- `CAMP_TYPES` array and `CAMP_TYPE_LABELS` map both use `PERFORMANCE_MAX` consistently.
- `globalFilters.js` campaign type options also use `PERFORMANCE_MAX` value.
