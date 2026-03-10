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
- `PATCH /clients/{id}` -> update client
- `DELETE /clients/{id}` -> delete client
- `POST /clients/discover` -> auto-discover from MCC

## Sync
- `POST /sync/trigger?client_id=X&days=30` -> full sync
- `GET /sync/status` -> Google Ads connection status
- `GET /sync/logs?client_id=X&limit=10` -> recent sync logs
- `GET /sync/debug?client_id=X` -> row counts + last sync diagnostics
- `POST /sync/phase/{phase_name}?client_id=X&days=30` -> run single sync phase

## Campaigns
- `GET /campaigns/?client_id=X&page=1&page_size=50&campaign_type=&status=`
- `GET /campaigns/{id}`
- `GET /campaigns/{id}/kpis?days=30`
- `GET /campaigns/{id}/metrics?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD`

## Keywords and Ads
- `GET /keywords/?client_id=X&campaign_type=&status=&match_type=&date_from=&date_to=`
- `GET /ads/?client_id=X&campaign_type=&status=&ad_type=&date_from=&date_to=`

## Search Terms
- `GET /search-terms/?client_id=X&campaign_id=&ad_group_id=&search=&sort_by=&sort_order=&page=`
- `GET /search-terms/segmented?client_id=X&date_from=&date_to=&campaign_type=&campaign_status=`
- `GET /search-terms/summary?campaign_id=X&days=30` (note: `campaign_id` is required)

## Recommendations
- `GET /recommendations/?client_id=X&priority=&status=&category=&days=30`
- `GET /recommendations/summary?client_id=X&days=30`
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- `POST /recommendations/{id}/dismiss?client_id=X`

## Actions
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X`

## Analytics - Core
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/dashboard-kpis?client_id=X&days=30&campaign_type=ALL&status=ALL`
- `GET /analytics/anomalies?client_id=X&status=unresolved|resolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`
- `POST /analytics/detect?client_id=X`

## Analytics - Advanced
- `POST /analytics/correlation`
- `POST /analytics/compare-periods`
- `GET /analytics/trends?client_id=X&metrics=clicks,cost_micros&days=30`
- `GET /analytics/health-score?client_id=X`
- `GET /analytics/campaign-trends?client_id=X&days=7`
- `GET /analytics/budget-pacing?client_id=X`
- `GET /analytics/quality-score-audit?client_id=X&qs_threshold=5`
- `GET /analytics/forecast?campaign_id=X&metric=clicks&forecast_days=14`
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
- `GET /export/keywords?client_id=X&format=xlsx`
- `GET /export/metrics?client_id=X&format=xlsx&days=30`
- `GET /export/recommendations?client_id=X&format=xlsx&days=30`

## Semantic
- `GET /semantic/clusters?client_id=X&min_cluster_size=3&max_features=500`

## History (Change Events)
- `GET /history/?client_id=X&date_from=&date_to=&resource_type=&user_email=&page=1&page_size=50`
- `GET /history/unified?client_id=X&days=30&source=all|helper|external&page=1&page_size=50`
- `GET /history/filters?client_id=X`

## Health
- `GET /health` -> `{status: "ok", version, env}` (outside `/api/v1`)
