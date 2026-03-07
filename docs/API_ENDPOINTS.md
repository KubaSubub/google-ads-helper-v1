# API Endpoints — Google Ads Helper

Complete list of all REST API endpoints. Base URL: `/api/v1`

---

## Auth
- `GET /auth/status` → {authenticated: bool}
- `GET /auth/login` → {auth_url: str}
- `GET /auth/callback?code=X` → HTML success page
- `POST /auth/logout`
- `GET /auth/setup-status` → {has_credentials: bool}
- `POST /auth/setup` → save credentials to keyring

## Clients
- `GET /clients/` → paginated list
- `GET /clients/{id}` → client detail
- `POST /clients/` → create client
- `POST /clients/discover` → auto-discover from MCC
- `PATCH /clients/{id}` → update client
- `DELETE /clients/{id}` → delete client

## Sync
- `POST /sync/trigger?client_id=X&days=30` → trigger full sync
- `GET /sync/status` → API connection status

## Campaigns
- `GET /campaigns/?client_id=X`
- `GET /campaigns/{id}/kpis?days=30`
- `GET /campaigns/{id}/metrics?date_from&date_to`

## Keywords + Ads
- `GET /keywords/?client_id=X&campaign_type=&status=&match_type=&date_from=&date_to=`

## Search Terms
- `GET /search-terms/?client_id=X&search=&sort_by=&page=`
- `GET /search-terms/segmented?client_id=X` → grouped by segment + summary
- `GET /search-terms/summary?campaign_id=X`

## Recommendations
- `GET /recommendations/?client_id=X&priority=X&status=X&category=X`
- `GET /recommendations/summary?client_id=X` → badge counts
- `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- `POST /recommendations/{id}/dismiss`

## Actions
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X`

## Analytics (Core)
- `GET /analytics/kpis?client_id=X`
- `GET /analytics/dashboard-kpis?client_id=X&days=30`
- `GET /analytics/campaigns?client_id=X`
- `GET /analytics/anomalies?client_id=X&status=unresolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`
- `POST /analytics/detect?client_id=X`

## Analytics (V2 — Trends & Insights)
- `GET /analytics/trends?client_id=X&metrics=&days=`
- `GET /analytics/health-score?client_id=X`
- `GET /analytics/campaign-trends?client_id=X&days=7`
- `GET /analytics/budget-pacing?client_id=X`
- `GET /analytics/quality-score-audit?client_id=X`
- `GET /analytics/forecast?campaign_id=X&metric=&forecast_days=`
- `GET /analytics/impression-share?client_id=X`
- `GET /analytics/device-breakdown?client_id=X`
- `GET /analytics/geo-breakdown?client_id=X`

## Analytics (SEARCH Optimization)
- `GET /analytics/dayparting?client_id=X&days=30`
- `GET /analytics/rsa-analysis?client_id=X`
- `GET /analytics/ngram-analysis?client_id=X&ngram_size=1&min_occurrences=2`
- `GET /analytics/match-type-analysis?client_id=X&days=30`
- `GET /analytics/landing-pages?client_id=X&days=30`
- `GET /analytics/wasted-spend?client_id=X&days=30`

## Export
- `GET /export/search-terms?client_id=X&format=xlsx`
- `GET /export/keywords?client_id=X&format=xlsx`

## Semantic
- `GET /semantic/clusters?client_id=X`

## History (Change Events)
- `GET /history/?client_id=X&date_from=&date_to=&resource_type=`
- `GET /history/unified?client_id=X` → merged action_log + change_events
- `GET /history/filters?client_id=X` → dropdown values

## Health
- `GET /health` → {status: "ok", version, env}
