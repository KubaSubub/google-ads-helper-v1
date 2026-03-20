# API Endpoints - Google Ads Helper

Complete list of REST API endpoints.
Base API URL: `/api/v1`

## Auth
- `GET /auth/status` -> auth/config/session status
- `GET /auth/setup-status` -> credentials setup status
- `GET /auth/setup-values` -> current credential values (masked)
- `POST /auth/setup` -> save credentials to keyring
- `GET /auth/login` -> generate OAuth URL
- `GET /auth/callback?code=...&state=...` -> OAuth callback (HTML)
- `POST /auth/logout` -> clear credentials/session

## Clients
- `GET /clients/?page=1&page_size=20` -> paginated list
- `GET /clients/{id}` -> client detail
- `POST /clients/` -> create client
- `PATCH /clients/{id}` -> update client (`allow_demo_write=true` required for DEMO)
- `DELETE /clients/{id}` -> delete client (`allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/hard-reset` -> delete only this client's local runtime data, keep client profile (`allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/seed-demo-showcase?days=30` -> wygeneruj lokalne dane pokazowe DEMO (keywords_daily, ads, helper actions, dodatkowe search_terms i kontrolowane wzorce waste) (`allow_demo_write=true` required, endpoint tylko dla DEMO)
- `POST /clients/{id}/clone-runtime?source_client_id=Y` -> skopiuj lokalne dane runtime z klienta Y do klienta id (bez wywolan write do Google Ads API, `allow_demo_write=true` required for DEMO)
- `POST /clients/{id}/restore-runtime-from-legacy` -> odtworz lokalne dane runtime klienta z legacy bazy `backend/data/google_ads_app.db` (domyslnie po `google_customer_id`, opcjonalnie `source_client_id`, `allow_demo_write=true` required for DEMO)
- `POST /clients/discover` -> auto-discover from MCC

## Sync
- `POST /sync/trigger?client_id=X&days=30` -> full sync (`allow_demo_write=true` required for DEMO)
- `GET /sync/status` -> Google Ads connection status
- `GET /sync/logs?client_id=X&limit=10` -> recent sync logs
- `GET /sync/debug?client_id=X` -> row counts + last sync diagnostics + active/legacy SQLite paths
- `GET /sync/debug/keywords?client_id=X&search=term&search=term2&include_removed=true&limit=50` -> helper debug comparing keyword_view API rows with local positive/negative SQLite rows
- `GET /sync/debug/keyword-source-of-truth?client_id=X&criterion_id=Y` -> authoritative debug for one criterion across Google Ads `keyword_view`, `ad_group_criterion`, local SQLite, and request context
- `POST /sync/phase/{phase_name}?client_id=X&days=30` -> run single sync phase (`allow_demo_write=true` required for DEMO)

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
- `GET /campaigns/{id}/kpis?days=30`
- `GET /campaigns/{id}/metrics?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

## Keywords and Ads
- `GET /keywords/?client_id=X&campaign_id=&ad_group_id=&status=&match_type=&campaign_type=&campaign_status=&include_removed=false&date_from=&date_to=&search=&sort_by=cost&sort_order=desc&page=&page_size=50`
- `GET /negative-keywords/?client_id=X&campaign_id=&ad_group_id=&status=&negative_scope=&include_removed=false&search=&page=&page_size=50`
- `POST /negative-keywords/` — create one or more negative keywords (body: `NegativeKeywordCreate`; `allow_demo_write` enforced)
- `DELETE /negative-keywords/{negative_keyword_id}` — soft-delete (sets status to REMOVED; `allow_demo_write` enforced)
- `GET /ad-groups/?client_id=X&campaign_id=` — lightweight ad group list for dropdowns
- `GET /ads/?client_id=X&campaign_id=&ad_group_id=&status=&sort_by=cost&sort_order=desc&page=&page_size=50`

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
- `GET /recommendations/?client_id=X&priority=&status=&category=&days=30`
- `GET /recommendations/summary?client_id=X&days=30`
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false` (`allow_demo_write=true` required for DEMO)
- `POST /recommendations/{id}/dismiss?client_id=X` (`allow_demo_write=true` required for DEMO)
- `POST /recommendations/bulk-apply` — apply batch of recommendations by quick-script category (`allow_demo_write=true` required for DEMO)
  - Body: `{client_id: int, category: "clean_waste"|"pause_burning"|"boost_winners"|"emergency_brake"|"add_negatives", dry_run: true}`
  - `dry_run=true` (default): preview matching recommendations; `dry_run=false`: apply via ActionExecutor

## Actions
- `[PROD]` `GET /actions/?client_id=X&limit=50&offset=0`
- `[PROD]` `POST /actions/revert/{action_log_id}?client_id=X` (`allow_demo_write=true` required for DEMO)

## Analytics - Core
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/dashboard-kpis?client_id=X&days=30&campaign_type=ALL&status=ALL`
- `GET /analytics/anomalies?client_id=X&status=unresolved|resolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X` (`allow_demo_write=true` required for DEMO)
- `POST /analytics/detect?client_id=X` (`allow_demo_write=true` required for DEMO)

## Analytics - Advanced
- `POST /analytics/correlation`
- `POST /analytics/compare-periods`
- `GET /analytics/trends?client_id=X&metrics=cost,clicks&days=30&campaign_type=ALL&status=ALL`
  - allowed metrics: `cost`, `clicks`, `impressions`, `conversions`, `ctr`, `cpc`, `roas`, `cpa`, `cvr`
- `GET /analytics/health-score?client_id=X`
- `GET /analytics/campaign-trends?client_id=X&days=7`
- `GET /analytics/budget-pacing?client_id=X`
- `GET /analytics/quality-score-audit?client_id=X&qs_threshold=5`
- `GET /analytics/forecast?campaign_id=X&metric=clicks&forecast_days=14`
  - aliases supported: `metric=cost` -> `cost_micros`, `metric=cpc` -> `avg_cpc_micros`
- `GET /analytics/impression-share?client_id=X`
- `GET /analytics/device-breakdown?client_id=X&days=30`
- `GET /analytics/geo-breakdown?client_id=X&days=30`
- `GET /analytics/account-structure?client_id=X`
- `GET /analytics/bidding-advisor?client_id=X&days=30`
- `GET /analytics/hourly-dayparting?client_id=X&days=30`

## Analytics - Search Optimization
- `GET /analytics/dayparting?client_id=X&days=30`
- `GET /analytics/rsa-analysis?client_id=X`
- `GET /analytics/ngram-analysis?client_id=X&ngram_size=1&min_occurrences=2`
- `GET /analytics/match-type-analysis?client_id=X&days=30`
- `GET /analytics/landing-pages?client_id=X&days=30`
- `GET /analytics/wasted-spend?client_id=X&days=30`
- `GET /analytics/search-term-trends?client_id=X&days=30&min_clicks=5` — search term trend analysis: rising, declining, and new terms (B2)
- `GET /analytics/close-variants?client_id=X&days=30` — close variant analysis: search terms vs exact keywords (B3)
- `GET /analytics/conversion-health?client_id=X&days=30` — conversion tracking health audit per campaign (A3)
- `GET /analytics/keyword-expansion?client_id=X&days=30&min_clicks=3` — keyword expansion suggestions from high-performing search terms (G2)

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
- `GET /export/metrics?client_id=X&format=xlsx&days=30`
- `GET /export/recommendations?client_id=X&format=xlsx&days=30`

## Semantic
- `GET /semantic/clusters?client_id=X&min_cluster_size=3&max_features=500`

## History (Change Events)
- `GET /history/?client_id=X&date_from=&date_to=&resource_type=&user_email=&page=1&page_size=50`
- `GET /history/unified?client_id=X&days=30&source=all|helper|external&page=1&page_size=50`
- `GET /history/filters?client_id=X`

## AI Agent
- `GET /agent/status` -> Claude CLI availability check (`{available: bool, version?: str, reason?: str}`)
- `POST /agent/chat?client_id=X` -> SSE stream: report generation via Claude Code headless
  - Body: `{message: str, report_type: "weekly"|"campaigns"|"keywords"|"search_terms"|"budget"|"alerts"|"freeform"}`
  - SSE events: `status` (progress), `delta` (content chunk), `error`, `done`

## Health
- `GET /health` -> `{status: "ok", version, env}` (outside `/api/v1`)






