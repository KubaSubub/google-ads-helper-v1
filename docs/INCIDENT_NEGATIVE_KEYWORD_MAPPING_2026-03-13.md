# Incident Summary - Negative Keywords Mapped as Positive Keywords

Date: 2026-03-13
Status: Closed

## Symptom
- The app showed disputed keyword rows for `Sushi Naka Naka` that were not visible in the Google Ads positive keyword UI.
- Source-of-truth debug and local SQLite showed criterion `33694032` for `bydgoszcz`.

## Root Cause
- Positive keyword sync used `keyword_view` but did not treat `ad_group_criterion.negative = true` as a hard stop.
- Negative ad-group criteria were therefore persisted into the positive `keywords` cache.
- Legacy `backend/data/google_ads_app.db` also amplified confusion during manual inspection because it still contained stale copies.

## Detection
- Live source-of-truth debug compared:
  - `keyword_view`
  - `ad_group_criterion`
  - local SQLite
  - MCC/account context (`ListAccessibleCustomers`, `customer_client`)
- The disputed criterion was confirmed as `negative=true`.

## Fix
- Positive keyword sync now blocks negatives at:
  - GAQL query layer
  - mapping/classification layer
  - before-save guard layer with warning logs
- Added dedicated sync for negative keyword criteria into `negative_keywords`.
- Added explicit `criterion_kind` to both positive and negative caches.
- Reworked debug payloads to distinguish:
  - API vs DB
  - DB positive vs DB negative
  - active vs legacy SQLite path

## Guardrails Added
- Positive keyword API stays positive-only.
- New backend endpoint `/api/v1/negative-keywords/` exposes canonical negative cache.
- `/sync/debug` now shows active and legacy DB paths.
- Source-of-truth debug now reports `presence_state`, `criterion_kind`, and DB positive/negative counts.
- Regression tests cover positive sync, negative sync, reset+resync, debug payloads, and API contracts.
