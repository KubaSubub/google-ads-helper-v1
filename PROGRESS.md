# PROGRESS.md - Implementation Status
# Updated: 2026-03-13

## Status
- Backend: human-centered recommendations milestone completed
- Frontend: recommendations and campaigns UI updated for context-aware decisions
- Google Ads native recommendation phase 1: ingest + cache + display + local dismiss

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

