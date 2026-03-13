# Feature Set - Google Ads Helper v1

Current product scope.

## 1. Core Value Path
`sync -> recommendations/insights -> dry-run/apply -> history/revert`

Official positioning:
- execution-ready only for supported canonical actions
- non-executable alerts are first-class output, not hidden failures
- context correctness is separate from executability

## 2. Human-Centered Recommendation Engine
Active rule families:
- R1-R13, R15-R18
- analytics-generated insights (`source=ANALYTICS`)
- optional native Google Ads recommendation ingest (`source=GOOGLE_ADS_API`)

The engine now adds:
- deterministic campaign role classification
- manual role override
- context-aware budget guardrails
- structured explanation blocks for allowed / blocked / insight-only states

## 3. Campaign Roles and Protection
Supported roles:
- `BRAND`
- `GENERIC`
- `PROSPECTING`
- `REMARKETING`
- `PMAX`
- `LOCAL`
- `UNKNOWN`

Role fields exposed in Campaign API:
- `campaign_role_auto`
- `campaign_role_final`
- `role_confidence`
- `protection_level`
- `role_source`

Protection defaults:
- `BRAND`, `REMARKETING` -> `HIGH`
- `PMAX`, `LOCAL` -> `MEDIUM`
- `GENERIC`, `PROSPECTING` -> `LOW`
- `UNKNOWN` -> `HIGH`

## 4. Business Type vs Executable Action
- Business type: stored in `Recommendation.type`
- Canonical action: stored in `action_payload.action_type`
- Context outcome: stored in `context_outcome`
- This separation is used by generator, persistence, executor, API, and UI

## 5. Executable Matrix
| Business Type | Context Outcome | Category | Canonical Action | Executable |
|---|---|---|---|---|
| `PAUSE_KEYWORD` | `ACTION` | `RECOMMENDATION` | `PAUSE_KEYWORD` | yes |
| `INCREASE_BID` | `ACTION` | `RECOMMENDATION` | `UPDATE_BID` | yes |
| `DECREASE_BID` | `ACTION` | `RECOMMENDATION` | `UPDATE_BID` | yes |
| `ADD_KEYWORD` (SEARCH) | `ACTION` | `RECOMMENDATION` | `ADD_KEYWORD` | yes |
| `ADD_KEYWORD` (PMAX) | `INSIGHT_ONLY` | `ALERT` | none | no |
| `ADD_NEGATIVE` (campaign-level) | `ACTION` | `RECOMMENDATION` | `ADD_NEGATIVE` | yes |
| `ADD_NEGATIVE` (account-level / irrelevant-word) | `INSIGHT_ONLY` | `ALERT` | none | no |
| `PAUSE_AD` | `ACTION` | `RECOMMENDATION` | `PAUSE_AD` | yes |
| `IS_BUDGET_ALERT` healthy branch | `ACTION` | `RECOMMENDATION` | `INCREASE_BUDGET` | yes |
| `IS_BUDGET_ALERT` weak-context branch | `INSIGHT_ONLY` | `ALERT` | none | no |
| `REALLOCATE_BUDGET` same-role healthy branch | `ACTION` | `RECOMMENDATION` | `REALLOCATE_BUDGET` | no |
| `REALLOCATE_BUDGET` role/protection/data conflict | `INSIGHT_ONLY` or `BLOCKED_BY_CONTEXT` | `ALERT` | `REALLOCATE_BUDGET` | no |
| `NGRAM_NEGATIVE` | `INSIGHT_ONLY` | `ALERT` | none | no |
| Google Ads native recommendations | `INSIGHT_ONLY` | `ALERT` | none in phase 1 | no |
| Analytics insights | `INSIGHT_ONLY` | `ALERT` | none | no |

## 6. Fixed Reason Codes
Current stable reason codes:
- `ROLE_MISMATCH`
- `DONOR_PROTECTED_HIGH`
- `DONOR_PROTECTED_MEDIUM`
- `DESTINATION_NO_HEADROOM`
- `ROAS_ONLY_SIGNAL`
- `UNKNOWN_ROLE`
- `INSUFFICIENT_DATA`

## 7. UI Behavior
- Recommendations page supports filters by priority, source, executable state.
- Cards display source, confidence, risk, expiry, and `context_outcome` badge.
- Cards render structured explanation sections from backend reason codes.
- Apply button is disabled for `INSIGHT_ONLY` and `BLOCKED_BY_CONTEXT` cards.
- Campaign details page exposes manual role override and reset-to-auto controls.
- Dashboard insights come from backend analytics recommendations instead of frontend-only heuristics.

## 8. Safety and Audit
- Every write path goes through preconditions and `validate_action()`.
- `action_log` stores:
  - `execution_mode`
  - `precondition_status`
  - `context_json`
  - `action_payload`
- `DRY_RUN` and `BLOCKED` events are logged.
- Revert is allowed only where `revertability.strategy` exists.

## 9. Google Ads Native Recommendation Phase
Phase 1 scope:
- fetch and cache native recommendations
- map them into unified recommendation model
- expose in list and summary
- local dismiss only

Out of scope in phase 1:
- native auto-apply
- RecommendationSubscriptionService
- live executable allowlist for Google-native types
## 10. Keyword Lifecycle and Cache Behavior
- Full sync now marks campaigns, ad groups, and keywords as `REMOVED` when they disappear from a successful Google Ads fetch.
- `REMOVED` rows stay in SQLite for history/debugging, but keyword lists hide them by default.
- Keywords page consumes the positive-only `/keywords/` cache and every row is explicitly tagged as `criterion_kind=POSITIVE`.
- Keyword status badge uses the real lifecycle status (`ENABLED`, `PAUSED`, `REMOVED`).
- Delivery issues such as low search volume are shown separately from lifecycle status.
- Keyword action hints use readable labels (`Pauzuj`, `Podnies`, `Obniz`) with tooltip copy that explains the trigger.

## 11. Negative Keyword Cache
- Negative keyword criteria are cached separately from positive keywords in `negative_keywords`.
- The cache supports `CAMPAIGN` and `AD_GROUP` scopes.
- Rows are explicitly tagged as `criterion_kind=NEGATIVE` and carry `source=GOOGLE_ADS_SYNC` or `LOCAL_ACTION`.
- Backend exposes `GET /api/v1/negative-keywords/` for diagnostics and backend consumers.
- There is no dedicated negatives UI page in the current scope.

## 12. Runtime Data Path
- Runtime SQLite path is canonicalized to `<repo>/data/google_ads_app.db` in source mode.
- Frozen desktop builds use `<exe_dir>/data/google_ads_app.db`.
- If only the legacy `backend/data/google_ads_app.db` exists, the app migrates it once to the canonical path before engine startup.
- If both files exist, runtime uses the canonical DB and logs that `backend/data/google_ads_app.db` is ignored legacy data.
## 13. Client Hard Reset
- Settings page exposes a per-client Twardy reset danych klienta action.
- Hard reset deletes only local runtime data for the selected client: campaigns, ad groups, keywords, search terms, recommendations, alerts, history, negatives, and sync logs.
- Client profile, business context, safety limits, and Google Customer ID stay intact.
- Reset requires typing the exact client name before the button becomes active.

## 14. Keyword Source Diagnostics
- Sync debug now exposes a read-only keyword source comparison endpoint for one client.
- The helper endpoint compares `keyword_view` API rows with both local positive and local negative SQLite rows.
- It supports repeated search filters, optional inclusion of `REMOVED`, and returns the exact GAQL used for inspection.

## 15. Keyword Source Of Truth
- The canonical per-keyword diagnostic path is `GET /api/v1/sync/debug/keyword-source-of-truth`.
- It compares the same criterion across `keyword_view`, `ad_group_criterion`, local positive cache, and local negative cache in one response.
- The payload explicitly includes `criterion_kind`, `negative`, `presence_state`, lifecycle statuses, campaign/ad group context, Google Ads `request_id`, `ListAccessibleCustomers`, MCC `customer_client` lookup, and the active SQLite file path used by runtime.
- Positive keyword sync excludes `ad_group_criterion.negative = true` at query, mapping, and before-save layers.

