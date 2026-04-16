# API Endpoints - Google Ads Helper

Complete list of REST API endpoints.
Base API URL: `/api/v1`

## Auth
- `GET /auth/status?bootstrap=0` -> auth/config/session status (bootstrap=1 on first load)
- `GET /auth/setup-status` -> credentials setup status
- `GET /auth/setup-values` -> current credential values (masked)
- `POST /auth/setup` -> save credentials to keyring
- `GET /auth/login` -> generate OAuth URL
- `GET /auth/callback?code=...&state=...` -> OAuth callback (HTML)
- `POST /auth/logout` -> clear credentials/session

## Clients
- `GET /clients/?page=1&page_size=20&search=` -> paginated list (optional `search` filters by name)
- `GET /clients/{id}` -> client detail
- `POST /clients/` -> create client
- `PATCH /clients/{id}` -> update client (`allow_demo_write=true` required for DEMO)
  - `strategy_context` field is **deep-merged** (partial updates preserve other fields; `null` payload is a no-op, does NOT wipe column)
  - Accepts: `narrative`, `roadmap`, `brand_voice`, `restrictions`, `lessons_learned[]` (LessonEntry), `decisions_log[]` (DecisionLogEntry)
- `DELETE /clients/{id}` -> delete client (`allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/hard-reset` -> delete only this client's local runtime data, keep client profile (`allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/seed-demo-showcase?days=30` -> wygeneruj lokalne dane pokazowe DEMO (keywords_daily, ads, helper actions, dodatkowe search_terms i kontrolowane wzorce waste) (`allow_demo_write=true` required, endpoint tylko dla DEMO)
- `POST /clients/{id}/clone-runtime?source_client_id=Y` -> skopiuj lokalne dane runtime z klienta Y do klienta id (bez wywolan write do Google Ads API, `allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/restore-runtime-from-legacy` -> odtworz lokalne dane runtime klienta z legacy bazy `backend/data/google_ads_app.db` (domyslnie po `google_customer_id`, opcjonalnie `source_client_id`, `allow_demo_write=true` required for DEMO)
- `POST /clients/discover?customer_ids=` -> auto-discover from MCC (optional `customer_ids` comma-separated override)
- `GET /clients/{id}/health` -> aggregated client health hub (always HTTP 200, partial failures reported via `errors[]`):
  - `account_metadata` — name, currency, customer_id, timezone, auto_tagging (DB + optional Google Ads API enrichment)
  - `sync_health` — last_synced_at, last_status, freshness (`green` < 6h / `yellow` < 24h / `red` >= 24h or never)
  - `conversion_tracking` — active ConversionAction list from DB (name, category, status, include_in_conversions_metric, attribution_model)
  - `linked_accounts` — linked GA4/GMC/etc via Google Ads API `product_link` / `customer_client` (graceful fallback to `[]` with `google_ads_api_unavailable` error)

## Sync
- `POST /sync/trigger?client_id=X&days=30` -> full sync (`allow_demo_write=true` required for DEMO)
- `GET /sync/status` -> Google Ads connection status
- `GET /sync/logs?client_id=X&limit=10` -> recent sync logs
- `GET /sync/debug?client_id=X` -> row counts + last sync diagnostics + active/legacy SQLite paths
- `GET /sync/debug/keywords?client_id=X&search=term&search=term2&include_removed=true&limit=50` -> helper debug comparing keyword_view API rows with local positive/negative SQLite rows
- `GET /sync/debug/keyword-source-of-truth?client_id=X&criterion_id=Y` -> authoritative debug for one criterion across Google Ads `keyword_view`, `ad_group_criterion`, local SQLite, and request context
- `POST /sync/phase/{phase_name}?client_id=X&days=30` -> run single sync phase (`allow_demo_write=true` required for DEMO)
  - Available phases (37 total): `campaigns`, `impression_share`, `ad_groups`, `ads`, `product_groups`, `keywords`, `negative_keywords`, `negative_keyword_lists`, `mcc_exclusion_lists`, `keyword_daily`, `daily_metrics`, `search_terms`, `pmax_terms`, `device_metrics`, `geo_metrics`, `auction_insights`, `change_events`, `conversion_actions`, `age_metrics`, `gender_metrics`, `parental_metrics`, `income_metrics`, `placement_metrics`, `bid_modifiers`, `bidding_strategies`, `shared_budgets`, `audiences`, `topic_metrics`, `google_recommendations`, `conversion_value_rules`, `pmax_channel_metrics`, `asset_groups`, `asset_group_daily`, `asset_group_assets`, `asset_group_signals`, `campaign_audiences`, `campaign_assets`
- `GET /sync/data-coverage?client_id=X` -> date range of synced data and last sync info for a client
- `GET /sync/presets` -> sync presets and phase registry for the configuration modal (phases, groups, max_days, patterns)
- `GET /sync/coverage?client_id=X` -> per-resource sync coverage for a client
- `POST /sync/trigger-stream?client_id=X&preset=&phases=&date_from=&date_to=` -> SSE streaming sync with per-phase progress updates (`allow_demo_write=true` required for DEMO)

### Keyword source-of-truth debug
- Returns Google Ads request context: `customer_id_used`, `login_customer_id`, masked OAuth/developer token metadata, and `request_id` values from Google Ads API responses.
- Returns both account-access perspectives:
  - `accessible_customers` from `ListAccessibleCustomers`
  - `mcc_customer_lookup` from `customer_client` queried under the configured `login_customer_id`
- Returns normalized rows from both Google Ads API and local SQLite.
- Each row contains:
  - `customer_id`
  - `campaign_id`, `campaign_name`, `campaign_status`, `campaign_advertising_channel_type`
  - `ad_group_id`, `ad_group_name`, `ad_group_status`
  - `criterion_id`
  - `criterion_kind`
  - `criterion_status`
  - `negative`
  - `keyword_text`
  - `match_type`
  - `request_id`
  - `source_query_type`
  - `storage_kind`
- Returns local SQLite evidence:
  - `synced_to_db`
  - `presence_state`
  - `db_rows_found`
  - `db_positive_rows_found`
  - `db_negative_rows_found`
  - `db_rows`
  - `db_source_path`
  - `db_legacy_path`
  - `db_legacy_exists`

## Campaigns
- `GET /campaigns/?client_id=X&page=1&page_size=50&campaign_type=&status=`
- `GET /campaigns/{id}`
- `PATCH /campaigns/{id}` -> patch campaign role override / reset (`allow_demo_write=true` required for DEMO)
- `PATCH /campaigns/{id}/bidding-target?field=target_cpa_micros|target_roas&value=X` -> update bidding target (remote-first: API push → local commit; falls back to local-only if API disconnected; returns `pending_sync: true` when local-only; `allow_demo_write` enforced)
- `GET /campaigns/{id}/kpis?days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (date_from/date_to override days)
- `GET /campaigns/{id}/metrics?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

## Keywords and Ads
- `GET /keywords/?client_id=X&campaign_id=&ad_group_id=&status=&match_type=&campaign_type=&campaign_status=&include_removed=false&date_from=&date_to=&search=&sort_by=cost&sort_order=desc&page=&page_size=50`
- `GET /negative-keywords/?client_id=X&campaign_id=&ad_group_id=&status=&negative_scope=&include_removed=false&search=&page=&page_size=50`
- `POST /negative-keywords/` — create one or more negative keywords (body: `NegativeKeywordCreate`; `allow_demo_write` enforced)
- `DELETE /negative-keywords/{negative_keyword_id}` — soft-delete (sets status to REMOVED; `allow_demo_write` enforced)
- `GET /ad-groups/?client_id=X&campaign_id=` — lightweight ad group list for dropdowns
- `GET /ads/?client_id=X&campaign_id=&ad_group_id=&status=&sort_by=cost&sort_order=desc&page=1&page_size=50`

### Negative Keyword Lists
- `GET /negative-keyword-lists/?client_id=X` — list all negative keyword lists with item counts
- `POST /negative-keyword-lists/` — create a new list (body: `NegativeKeywordListCreate`)
- `GET /negative-keyword-lists/{list_id}` — get list detail with all items
- `DELETE /negative-keyword-lists/{list_id}` — delete list and all its items
- `POST /negative-keyword-lists/{list_id}/items` — add keywords to a list (body: `NegativeKeywordListAddItems`; duplicates skipped)
- `DELETE /negative-keyword-lists/{list_id}/items/{item_id}` — remove a single item from a list
- `POST /negative-keyword-lists/{list_id}/apply` — apply list to campaigns/ad groups (body: `ApplyListRequest`; creates `NegativeKeyword` records; `allow_demo_write` enforced)

### Keyword response fields
- `criterion_kind` is always `POSITIVE` on `/keywords/`.
- `status` is the real Google Ads lifecycle status for the keyword: `ENABLED`, `PAUSED`, `REMOVED`.
- `serving_status` stays separate and only describes delivery issues such as `LOW_SEARCH_VOLUME`.
- Keyword payload now includes `campaign_id`, `campaign_name`, and `ad_group_name`.
- Default keyword list excludes local `REMOVED` rows unless `include_removed=true` is sent.
- Keyword sync only persists positive search keywords. Rows where `ad_group_criterion.negative = true` are excluded from sync and should be inspected through source-of-truth debug instead of the normal keyword list.

### Negative keyword response fields
- `criterion_kind` is always `NEGATIVE` on `/negative-keywords/`.
- `negative_scope` is `CAMPAIGN` or `AD_GROUP`.
- `status` uses the Google Ads lifecycle vocabulary (`ENABLED`, `REMOVED`).
- `source` indicates whether the row came from Google Ads sync (`GOOGLE_ADS_SYNC`) or a local write path (`LOCAL_ACTION`).
- `google_criterion_id` is the canonical criterion identifier for synced/debugged negative keyword criteria.

## Search Terms
- `GET /search-terms/?client_id=X&campaign_id=&ad_group_id=&min_clicks=&min_cost=&min_impressions=&campaign_type=&campaign_status=&date_from=&date_to=&search=&sort_by=cost&sort_order=desc&page=&page_size=50`
- `GET /search-terms/segmented?client_id=X&date_from=&date_to=&campaign_type=&campaign_status=`
- `GET /search-terms/summary?campaign_id=X&days=30` (note: `campaign_id` is required)
- `POST /search-terms/bulk-add-negative` — add selected terms as negative keywords (body: `{search_term_ids, level: campaign|ad_group, match_type, client_id}`; `allow_demo_write` enforced)
- `POST /search-terms/bulk-add-keyword` — promote selected terms as positive keywords to a target ad group (body: `{search_term_ids, ad_group_id, match_type, client_id}`; `allow_demo_write` enforced)
- `POST /search-terms/bulk-preview` — preview details for selected search terms before bulk action (body: `{search_term_ids, client_id}`)

## Recommendations
- `GET /recommendations/?client_id=X&priority=&status=&category=&source=&executable=&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (date_from/date_to override days)
- `GET /recommendations/summary?client_id=X&source=&category=&executable=&status=&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` (date_from/date_to override days)
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false` (`allow_demo_write=true` required for DEMO)
- `POST /recommendations/{id}/dismiss?client_id=X` (`allow_demo_write=true` required for DEMO; dismiss is local-only, no Google Ads API call)
- `POST /recommendations/bulk-apply` — apply batch of recommendations by quick-script category (`allow_demo_write=true` required for DEMO)
  - Body: `{client_id: int, category: "clean_waste"|"pause_burning"|"boost_winners"|"emergency_brake"|"add_negatives", dry_run: true, item_ids?: list[int]}`
  - `dry_run=true` (default): preview matching recommendations. Preview items include `id`, `entity_name`, `campaign_name`, `reason`, `suggested_action`, `priority`, and `metrics_snapshot` (clicks/impressions/cost_usd/conversions/ctr/cpa/roas/quality_score) so the UI can build a per-item opt-out selection list.
  - `dry_run=false`: apply via ActionExecutor. Optional `item_ids` narrows execution to user-selected rows from the preview (omit to execute the full matching set).

## Actions
- `[PROD]` `GET /actions/?client_id=X&limit=50&offset=0`
- `[PROD]` `POST /actions/revert/{action_log_id}?client_id=X` (`allow_demo_write=true` required for DEMO)

## Analytics - Core
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/dashboard-kpis?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=ALL&campaign_status=&status=ALL` (date_from/date_to override days; campaign_status preferred, status=alias)
- `GET /analytics/anomalies?client_id=X&status=unresolved|resolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X` (`allow_demo_write=true` required for DEMO)
- `POST /analytics/detect?client_id=X` (`allow_demo_write=true` required for DEMO)
- `GET /analytics/z-score-anomalies?client_id=X&metric=cost&days=90&threshold=2.0` — z-score anomaly detection per campaign per day for a given metric (metrics: cost, clicks, impressions, conversions, ctr)

## Analytics - Advanced
- `POST /analytics/correlation` — body: `{client_id, metrics: [..], days?, date_from?, date_to?, campaign_ids?: [..]}`.
  - Accepts unified metric names (see `/analytics/trends` below). Legacy names (`cost_micros`, `avg_cpc_micros`, `conversion_rate`) are auto-aliased for backward compatibility.
- `POST /analytics/compare-periods`
- `GET /analytics/trends?client_id=X&metrics=cost,clicks&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=ALL&campaign_status=&status=ALL&campaign_ids=1,2` (date_from/date_to override days; campaign_status preferred, status=alias; max span clamped to 365 days; `campaign_ids` optional, scopes aggregation to specific campaigns)
  - allowed metrics (unified `TREND_METRICS` — shared with `/correlation` and `/wow-comparison`):
    - core: `cost`, `clicks`, `impressions`, `conversions`, `conversion_value`
    - derived: `ctr`, `cpc`, `cpa`, `cvr`, `roas`
    - share: `search_impression_share`, `search_top_impression_share`, `search_abs_top_impression_share`, `search_budget_lost_is`, `search_rank_lost_is`, `search_click_share`, `abs_top_impression_pct`, `top_impression_pct`
  - share metrics are impression-weighted when aggregating across multiple campaigns
- `GET /analytics/trends-by-device?client_id=X&metric=clicks&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=ALL&campaign_status=&campaign_ids=1,2` — daily time-series for a single metric split across device segments (MOBILE, DESKTOP, TABLET, OTHER); powers TrendExplorer device segmentation
- `GET /analytics/health-score?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` (date_from/date_to override days)
- `GET /analytics/campaign-trends?client_id=X&days=7&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` (date_from/date_to override days)
- `GET /analytics/wow-comparison?client_id=X&days=7&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&metric=cost&campaign_type=ALL&campaign_status=&status=ALL` — current vs previous period with day-of-week alignment for overlay chart. Allowed metrics: cost, clicks, impressions, conversions, ctr, cpc, roas, cpa
- `GET /analytics/campaigns-summary?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=ALL&campaign_status=&status=ALL` — per-campaign aggregated metrics (clicks, impressions, cost_usd, conversions, ctr, roas, impression_share) for a given period
- `GET /analytics/budget-pacing?client_id=X&campaign_type=&campaign_status=`
- `GET /analytics/quality-score-audit?client_id=X&qs_threshold=5&campaign_id=&match_type=&sort_by=quality_score&sort_dir=asc&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`
- `GET /analytics/forecast?campaign_id=X&metric=clicks&forecast_days=14`
  - aliases supported: `metric=cost` -> `cost_micros`, `metric=cpc` -> `avg_cpc_micros`
- `GET /analytics/impression-share?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_id=&campaign_type=&campaign_status=`
- `GET /analytics/device-breakdown?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_id=&campaign_type=&campaign_status=&status=`
- `GET /analytics/geo-breakdown?client_id=X&days=7&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_id=&limit=20&campaign_type=&campaign_status=&status=`
- `GET /analytics/account-structure?client_id=X`
- `GET /analytics/bidding-advisor?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`
- `GET /analytics/hourly-dayparting?client_id=X&days=7&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`

## Analytics - Search Optimization
- `GET /analytics/dayparting?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`
- `GET /analytics/rsa-analysis?client_id=X&campaign_type=&campaign_status=`
- `GET /analytics/ngram-analysis?client_id=X&ngram_size=1&min_occurrences=2&campaign_type=&campaign_status=`
- `GET /analytics/match-type-analysis?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`
- `GET /analytics/landing-pages?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`
- `GET /analytics/wasted-spend?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=`
- `GET /analytics/search-term-trends?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&min_clicks=5&campaign_type=&campaign_status=` — search term trend analysis (B2)
- `GET /analytics/close-variants?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — close variant analysis (B3)
- `GET /analytics/conversion-health?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — conversion tracking health audit (A3)
- `GET /analytics/keyword-expansion?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&min_clicks=3&campaign_type=&campaign_status=` — keyword expansion suggestions (G2)

## Analytics - Smart Bidding & Strategy
- `GET /analytics/smart-bidding-health?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — Smart Bidding conversion volume health check (GAP 1C)
- `GET /analytics/learning-status?client_id=X` — detect campaigns in Smart Bidding learning period (GAP 1A)
- `GET /analytics/target-vs-actual?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — compare Smart Bidding targets with actual CPA/ROAS (GAP 1D)
- `GET /analytics/portfolio-health?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — portfolio bid strategy health analysis (GAP 1E)
- `GET /analytics/bid-strategy-report?client_id=X&days=30&campaign_id=` — daily time series of target vs actual CPA/ROAS per campaign (GAP 10)
- `GET /analytics/bid-strategy-impact?client_id=X&days=90` — bid strategy change impact, 14-day before/after comparison (GAP 6B)

## Analytics - Account & Campaign Analysis
- `GET /analytics/pareto-analysis?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — Pareto 80/20 campaign value contribution (GAP 7A)
- `GET /analytics/scaling-opportunities?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — hero campaigns with IS headroom to scale (GAP 7B)
- `GET /analytics/change-impact?client_id=X&days=60` — post-change performance delta, 7-day before/after comparison (GAP 6A)
- `GET /analytics/ad-group-health?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — ad group structural health: ad count, keyword count, zero-conv groups (GAP 8)
- `GET /analytics/conversion-quality?client_id=X` — conversion action configuration audit for data quality issues (GAP 2A-2D)
- `GET /analytics/demographics?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — aggregate metrics by age/gender/parental/income, flag CPA anomalies (GAP 4A)

## Analytics - Google Ads Coverage Expansion (Wave A-E)
- `GET /analytics/auction-insights?client_id=X&campaign_id=&days=30&date_from=&date_to=` — competitor visibility metrics (IS, overlap, position above, outranking, top of page)
- `GET /analytics/shopping-product-groups?client_id=X&campaign_id=` — Shopping product group performance tree
- `GET /analytics/placement-performance?client_id=X&campaign_id=&days=30&date_from=&date_to=` — Display/Video placement performance (top 100)
- `POST /analytics/placement-exclusion?client_id=X&campaign_id=X&placement_url=X` — add placement exclusion to campaign (`allow_demo_write` enforced)
- `GET /analytics/bid-modifiers?client_id=X&campaign_id=&modifier_type=DEVICE|LOCATION|AD_SCHEDULE` — bid modifier list
- `GET /analytics/topic-performance?client_id=X&days=30&date_from=&date_to=` — Display/Video topic targeting performance
- `GET /analytics/audiences-list?client_id=X` — synced audience segments
- `GET /analytics/google-recommendations?client_id=X` — Google's native recommendations
- `GET /analytics/mcc-accounts?manager_customer_id=X` — MCC child accounts
- `GET /analytics/offline-conversions?client_id=X&status=PENDING|UPLOADED|FAILED` — offline conversion upload history
- `POST /analytics/offline-conversions/upload?client_id=X` — upload offline conversions via Google Ads API (body: JSON array of `{gclid, conversion_action_id, conversion_time, conversion_value, currency_code}`; goes through write safety pipeline: demo guard → audit log; `allow_demo_write` enforced)
- `GET /analytics/conversion-value-rules?client_id=X` — conversion value adjustment rules

## Analytics - PMax, Audiences & Extensions (Phase D)
- `GET /analytics/pmax-channels?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — PMax channel breakdown (Search, Display, YouTube, etc.) via ad_network_type segmented metrics
- `GET /analytics/asset-group-performance?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — asset group metrics with ad_strength, asset counts, and daily aggregates
- `GET /analytics/pmax-search-themes?client_id=X` — PMax search themes extracted from asset group audience signals
- `GET /analytics/audience-performance?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — audience segment performance across campaigns (segment_type, audience_name, metrics)
- `GET /analytics/missing-extensions?client_id=X&campaign_type=&campaign_status=` — detect campaigns missing recommended extensions (sitelinks, callouts, structured snippets, etc.)
- `GET /analytics/extension-performance?client_id=X&campaign_type=&campaign_status=` — extension type performance metrics (clicks, impressions, cost aggregated by extension type)
- `GET /analytics/pmax-search-cannibalization?client_id=X&days=30&date_from=&date_to=&min_clicks=2` — PMax vs Search overlap detection
- `GET /analytics/pmax-channel-trends?client_id=X&days=30&date_from=&date_to=` — daily PMax channel cost/conversion trends

## Analytics - Cross-Campaign & Benchmarks (G4, H2)
- `GET /analytics/keyword-overlap?client_id=X` — keyword overlap analysis across campaigns (shared keywords, unique keywords, overlap %)
- `GET /analytics/budget-allocation?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — budget allocation analysis (spend distribution, efficiency per campaign)
- `GET /analytics/campaign-comparison?client_id=X&campaign_ids=1,2,3&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — side-by-side campaign comparison (metrics, trends)
- `GET /analytics/benchmarks?client_id=X&days=30` — account benchmarks (KPI percentiles, industry comparison baselines)
- `GET /analytics/client-comparison?days=30` — cross-client comparison (all clients KPIs side-by-side)

## Analytics - DSA (Dynamic Search Ads) (C1/C2/C3)
- `GET /analytics/dsa-targets?client_id=X&campaign_type=&campaign_status=` — DSA auto-targets per campaign with performance metrics
- `GET /analytics/dsa-coverage?client_id=X` — DSA coverage: which campaigns are DSA, target counts
- `GET /analytics/dsa-headlines?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&campaign_type=&campaign_status=` — DSA headline performance analysis
- `GET /analytics/dsa-search-overlap?client_id=X&days=30&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — DSA search term overlap with manual keywords

## MCC (Cross-Account Overview)
- `GET /mcc/overview?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&active_only=false` — aggregated data for all client accounts: full metrics (clicks, impressions, CTR, avg CPC, spend, conversions, CVR, conversion value, CPA, ROAS as multiplier), pacing, health score with 6-pillar breakdown, change activity (total + external), new access emails, Google recs pending, unresolved alerts, last sync. Defaults: `date_from=1st of current month`, `date_to=today`. `active_only=true` excludes accounts with spend<=0 in the period.
- `GET /mcc/new-access?client_id=X&days=30` — detect new user emails in change history (last N days vs 31-90 days ago, excluding specialist_emails)
- `POST /mcc/dismiss-google-recommendations` — bulk dismiss Google Ads API recommendations (body: `{client_id, recommendation_ids?, dismiss_all?}`)
- `GET /mcc/negative-keyword-lists` — all negative keyword lists across all clients with item counts
- `GET /mcc/shared-lists` — MCC-level exclusion lists from manager account via MccLink hierarchy: both negative keyword lists and placement exclusion lists
- `GET /mcc/shared-lists/{list_id}/items?list_type=keyword|placement` — drill-down: items of a specific MCC shared exclusion list (defaults to `keyword`)
- `GET /mcc/sync-history?client_id=X&limit=5` — sync history for a specific client, newest first (limit 1-20, default 5); returns id, status, total_synced, total_errors, started_at, finished_at, duration_s
- `GET /mcc/billing-status?customer_id=X` — check billing/payment status via Google Ads billing_setup API (returns status or error if access insufficient)

## Scheduled Sync (F1)
- `GET /sync/schedule?client_id=X` — get sync schedule for a client
- `POST /sync/schedule` — create/update sync schedule (body: `{client_id, enabled, interval_hours}`)
- `DELETE /sync/schedule?client_id=X` — disable and remove schedule

## Daily Audit
- `GET /daily-audit/?client_id=X` — single aggregated morning audit view:
  - `budget_pacing`: enabled campaigns with daily budget, today's spend, pacing %, budget-limited flag
  - `anomalies_24h`: unresolved alerts from last 24 hours
  - `disapproved_ads`: ads with `DISAPPROVED` or `APPROVED_LIMITED` approval status
  - `budget_capped_performers`: campaigns with budget constraints but below-average CPA
  - `search_terms_needing_action`: top 50 wasted search terms from last 7 days
  - `pending_recommendations`: total count + top 5 by priority
  - `health_summary`: health score + active campaign/keyword counts
  - `kpi_snapshot`: today vs yesterday spend / clicks / conversions

## Reports
- `POST /reports/generate?client_id=X` — generate a report (SSE stream); saves to DB
  - Body: `{report_type: "monthly"|"weekly"|"health", year?: int, month?: int}`
  - SSE events: `progress` (`{pct, label}`), `data_ready` (`{report_id, report_data}`), `delta` (AI narrative chunk), `model`, `usage`, `report_id`, `error`, `done`
- `GET /reports/?client_id=X&limit=20&offset=0` — list saved reports (newest first)
- `GET /reports/{report_id}?client_id=X` — get full report (data + AI narrative + token usage)

## Export
- `GET /export/search-terms?client_id=X&format=xlsx`
- `GET /export/keywords?client_id=X&campaign_id=&include_removed=false&format=xlsx`
- `GET /export/metrics?campaign_id=X&days=30&format=xlsx` (note: `campaign_id` is required, not `client_id`)
- `GET /export/recommendations?client_id=X&format=xlsx&days=30`
- `GET /export/quality-score?client_id=X&qs_threshold=5&format=csv|xlsx`
- `GET /export/actions?client_id=X&format=csv|xlsx` — export action history (CSV/XLSX)

## Semantic
- `GET /semantic/clusters?client_id=X&days=30&top_n=1000&threshold=1.0`

## History (Change Events)
- `GET /history/?client_id=X&date_from=&date_to=&resource_type=&user_email=&client_type=&operation=&campaign_name=&limit=50&offset=0`
- `GET /history/unified?client_id=X&date_from=&date_to=&resource_type=&campaign_name=&limit=50&offset=0`
- `GET /history/filters?client_id=X` — available filter values (resource types, user emails, client types, operations, campaign names)

## AI Agent
- `GET /agent/status` -> Claude CLI availability check (`{available: bool, version?: str, reason?: str}`)
- `POST /agent/chat?client_id=X` -> SSE stream: report generation via Claude Code headless
  - Body: `{message: str, report_type: "weekly"|"campaigns"|"keywords"|"search_terms"|"budget"|"alerts"|"freeform"}`
  - SSE events: `status` (progress), `delta` (content chunk), `error`, `done`

## Automated Rules Engine (F3)
- `GET /rules/?client_id=X` — list all automated rules for a client
- `POST /rules/` — create a new automated rule (body: rule config)
- `GET /rules/{rule_id}?client_id=X` — get a single rule
- `PUT /rules/{rule_id}` — update a rule
- `DELETE /rules/{rule_id}` — delete a rule
- `POST /rules/{rule_id}/dry-run?client_id=X` — dry-run a rule (simulate execution without applying)
- `POST /rules/{rule_id}/execute?client_id=X` — execute a rule

## Scripts (Optimization Actions)
- `GET /scripts/catalog` — all registered scripts grouped by category (for UI rendering)
- `POST /scripts/{script_id}/dry-run` — preview mode: returns matching items without applying (body: `{client_id, date_from?, date_to?, params: {}}`)
- `GET /scripts/counts` — bulk counts: total_matching + savings for every registered script, cached 60s (query: `client_id`)
- `POST /scripts/{script_id}/execute` — apply script actions, honors `item_ids` filter (body: `{client_id, date_from?, date_to?, params: {}, item_ids?: [], item_overrides?: {}}`)
- `GET /scripts/{script_id}/history` — execution history for a specific script (filtered by client_id)
- `GET /scripts/config/{client_id}` — saved script configs for a client, merged with defaults
- `PUT /scripts/{script_id}/config` — save per-client param overrides (body: `{client_id, params: {}}`)
- `DELETE /scripts/{script_id}/config/{client_id}` — reset script config to defaults for a client

## Health
- `GET /health` -> `{status: "ok", version, env}` (outside `/api/v1`)






