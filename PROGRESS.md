# PROGRESS.md - Implementation Status
# Updated: 2026-03-15

## Status
- Backend: human-centered recommendations milestone completed
- Frontend: recommendations and campaigns UI updated for context-aware decisions
- Frontend: first iteration of unified global filtering shipped
- Google Ads native recommendation phase 1: ingest + cache + display + local dismiss

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
- Address one npm audit high-severity dependency warning in frontend toolchain
- Consider code-splitting frontend bundle (current build warning > 500 kB)

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

