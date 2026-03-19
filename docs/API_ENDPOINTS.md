# API Endpoints - Google Ads Helper

Complete list of REST API endpoints.
Base API URL: `/api/v1`

## Auth
- `GET /auth/status` -> auth/config/session status
- `GET /auth/setup-status` -> credentials setup status
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
- `GET /campaigns/{id}/kpis?days=30`
- `GET /campaigns/{id}/metrics?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

## Keywords and Ads
- `GET /keywords/?client_id=X&campaign_id=&ad_group_id=&status=&match_type=&campaign_type=&campaign_status=&include_removed=false&date_from=&date_to=&page=`
- `GET /negative-keywords/?client_id=X&campaign_id=&ad_group_id=&status=&negative_scope=&include_removed=false&page=`
- `GET /ads/?client_id=X&campaign_type=&status=&ad_type=&date_from=&date_to=`

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
- `GET /search-terms/?client_id=X&campaign_id=&ad_group_id=&search=&sort_by=&sort_order=&page=`
- `GET /search-terms/segmented?client_id=X&date_from=&date_to=&campaign_type=&campaign_status=`
- `GET /search-terms/summary?campaign_id=X&days=30` (note: `campaign_id` is required)

## Recommendations
- `GET /recommendations/?client_id=X&priority=&status=&category=&days=30`
- `GET /recommendations/summary?client_id=X&days=30`
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false` (`allow_demo_write=true` required for DEMO)
- `POST /recommendations/{id}/dismiss?client_id=X` (`allow_demo_write=true` required for DEMO)

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
- `GET /analytics/trends?client_id=X&metrics=clicks,cost_micros&days=30`
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






