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
- Category A pages (Dashboard, Campaigns, Keywords, SearchTerms, SearchOptimization, Recommendations) use `allParams` from FilterContext.
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

## SEARCH Optimization Page
- `SearchOptimization.jsx` — 25 collapsible analysis sections (6 base + 7 Phase A + 6 Phase B+C + 6 Phase D)
- Endpoints: dayparting, rsa-analysis, ngram-analysis, match-type-analysis, landing-pages, wasted-spend, search-term-trends, close-variants, conversion-health, keyword-expansion, smart-bidding-health, learning-status, target-vs-actual, portfolio-health, pareto-analysis, scaling-opportunities, ad-group-health, bid-strategy-report, demographics, pmax-channels, asset-group-performance, pmax-search-themes, audience-performance, missing-extensions, extension-performance
- Backend: analytics_service.py methods + analytics.py routes
- Sidebar nav: "Optymalizacja" (Zap icon) in ANALIZA group

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
- 6 new analytics endpoints: pmax-channels, asset-group-performance, pmax-search-themes, audience-performance, missing-extensions, extension-performance.
- 4 new recommendation rules (R28–R31): PMAX_CHANNEL_IMBALANCE, ASSET_GROUP_AD_STRENGTH, AUDIENCE_PERFORMANCE_ANOMALY, MISSING_EXTENSIONS_ALERT.
- 6 new models: AssetGroup, AssetGroupDaily, AssetGroupAsset, AssetGroupSignal, CampaignAudienceMetric, CampaignAsset.
- MetricSegmented model extended with ad_network_type column for channel-level breakdowns.
- 7 new sync methods (22 total phases): sync_pmax_channel_metrics, sync_asset_groups, sync_asset_group_daily, sync_asset_group_assets, sync_asset_group_signals, sync_campaign_audiences, sync_campaign_assets.
- Frontend: 6 new analysis sections in SearchOptimization.jsx (25 total tools).

## SSE Sync Streaming Modal
- `SyncModal.jsx` + `useSyncStream.js` — real-time sync progress with per-phase SSE updates.
- Backend: `POST /sync/trigger-stream` SSE endpoint with preset/phase/date selection.
- Sync presets: `GET /sync/presets` — phase registry with groups, max_days, and preset patterns.
- Per-resource coverage: `GET /sync/coverage` — sync coverage tracking per client.
- `sync_config.py` + `sync_coverage.py` backend modules.
- `DarkSelect` and `GlobalDatePicker` reusable components.

## Schema Auto-Migration
- `database.py` auto-migration adds missing columns (labels, target_cpa_micros, target_roas, primary_status, bidding_strategy_resource_name, portfolio_bid_strategy_id, age_range, gender) without requiring DB delete + reseed.
