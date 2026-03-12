# API Endpoints - Google Ads Helper

Complete REST contract for current backend. Base API prefix: `/api/v1`.

Legend:
- `[PROD]` production-facing endpoint.
- `[AUX]` helper/diagnostic endpoint.

---

## Auth
- `[PROD]` `GET /auth/status`
- `[PROD]` `GET /auth/login`
- `[PROD]` `GET /auth/callback?code=X`
- `[PROD]` `POST /auth/logout`
- `[PROD]` `GET /auth/setup-status`
- `[PROD]` `POST /auth/setup`

## Clients
- `[PROD]` `GET /clients/`
- `[PROD]` `GET /clients/{id}`
- `[PROD]` `POST /clients/`
- `[PROD]` `POST /clients/discover`
- `[PROD]` `PATCH /clients/{id}`
- `[PROD]` `DELETE /clients/{id}`

## Sync
- `[PROD]` `POST /sync/trigger?client_id=X&days=30`
- `[PROD]` `GET /sync/status`
- `[AUX]` `GET /sync/logs?client_id=X&limit=10`
- `[AUX]` `GET /sync/debug?client_id=X`

## Campaigns
- `[PROD]` `GET /campaigns/?client_id=X`
- `[PROD]` `GET /campaigns/{id}/kpis?days=30`
- `[PROD]` `GET /campaigns/{id}/metrics?date_from=&date_to=`

## Keywords + Ads
- `[PROD]` `GET /keywords/?client_id=X&campaign_type=&status=&match_type=&date_from=&date_to=`

## Search Terms
- `[PROD]` `GET /search-terms/?client_id=X&search=&sort_by=&page=`
- `[PROD]` `GET /search-terms/segmented?client_id=X&date_from=&date_to=`
- `[PROD]` `GET /search-terms/summary?campaign_id=X`

## Recommendations
- `[PROD]` `GET /recommendations/?client_id=X&priority=X&status=X&category=X&days=30`
- `[PROD]` `GET /recommendations/summary?client_id=X&days=30`
- `[PROD]` `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- `[PROD]` `POST /recommendations/{id}/dismiss?client_id=X`

## Actions
- `[PROD]` `GET /actions/?client_id=X&limit=50&offset=0`
- `[PROD]` `POST /actions/revert/{action_log_id}?client_id=X`

## Analytics (Core)
- `[PROD]` `GET /analytics/kpis?client_id=X`
- `[PROD]` `GET /analytics/anomalies?client_id=X&status=unresolved`
- `[PROD]` `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`
- `[PROD]` `POST /analytics/detect?client_id=X`
- `[PROD]` `POST /analytics/correlation`
- `[PROD]` `POST /analytics/compare-periods`

## Analytics (V2 - Trends & Insights)
- `[PROD]` `GET /analytics/dashboard-kpis?client_id=X&days=30`
- `[PROD]` `GET /analytics/quality-score-audit?client_id=X`
- `[PROD]` `GET /analytics/forecast?campaign_id=X&metric=&forecast_days=`
- `[PROD]` `GET /analytics/trends?client_id=X&metrics=&days=`
- `[PROD]` `GET /analytics/health-score?client_id=X`
- `[PROD]` `GET /analytics/campaign-trends?client_id=X&days=7`
- `[PROD]` `GET /analytics/budget-pacing?client_id=X`
- `[PROD]` `GET /analytics/impression-share?client_id=X`
- `[PROD]` `GET /analytics/device-breakdown?client_id=X`
- `[PROD]` `GET /analytics/geo-breakdown?client_id=X`

## Analytics (Search Optimization)
- `[PROD]` `GET /analytics/dayparting?client_id=X&days=30`
- `[PROD]` `GET /analytics/rsa-analysis?client_id=X`
- `[PROD]` `GET /analytics/ngram-analysis?client_id=X&ngram_size=1&min_occurrences=2`
- `[PROD]` `GET /analytics/match-type-analysis?client_id=X&days=30`
- `[PROD]` `GET /analytics/landing-pages?client_id=X&days=30`
- `[PROD]` `GET /analytics/wasted-spend?client_id=X&days=30`
- `[PROD]` `GET /analytics/account-structure?client_id=X`
- `[PROD]` `GET /analytics/bidding-advisor?client_id=X&days=30`
- `[PROD]` `GET /analytics/hourly-dayparting?client_id=X&days=7`

## Export
- `[PROD]` `GET /export/search-terms?client_id=X&format=xlsx`
- `[PROD]` `GET /export/keywords?client_id=X&format=xlsx`

## Semantic
- `[PROD]` `GET /semantic/clusters?client_id=X`

## History
- `[PROD]` `GET /history/?client_id=X&date_from=&date_to=&resource_type=`
- `[PROD]` `GET /history/unified?client_id=X`
- `[PROD]` `GET /history/filters?client_id=X`

## System
- `[PROD]` `GET /health` (outside `/api/v1`)
