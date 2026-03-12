# Source of Truth - Google Ads Helper

Last updated: 2026-03-12
Owner: Product + Engineering

## Document Priority
1. `docs/SOURCE_OF_TRUTH.md` - canonical index
2. `docs/API_ENDPOINTS.md` - API contract
3. `docs/FEATURE_SET.md` - product behavior and scope
4. `PROGRESS.md` - delivery status and open work
5. `Technical_Spec.md` - historical snapshot only

## Current Baseline
- Backend routers: 12
- Frontend pages: 15
- Recommendation engine: 17 playbook rules + analytics stream + optional Google Ads native ingest
- Human-centered budget guardrails: enabled
- Sync trigger: `POST /api/v1/sync/trigger`

## Campaign Role Contract
- `campaign_role_auto` is deterministic and may refresh on sync/read.
- `campaign_role_final` is the effective business role.
- `role_confidence` is a `float` in range `0.0-1.0`.
- `protection_level` is derived from `campaign_role_final`.
- `role_source` is `AUTO` or `MANUAL`.
- If `role_source == MANUAL`, sync/classifier must not overwrite `campaign_role_final`.
- Manual override is managed through `PATCH /api/v1/campaigns/{campaign_id}`.

## Recommendation Contract
- `Recommendation.type` is the business rule type.
- `action_payload.action_type` is the canonical executable action.
- `source` identifies the producer: `PLAYBOOK_RULES`, `ANALYTICS`, `GOOGLE_ADS_API`, `HYBRID`.
- `stable_key` is the dedupe/idempotency key.
- `action_payload` contains: `action_type`, `target`, `params`, `preconditions`, `revertability`, `executable`.
- Recommendations expose `campaign_id`, `ad_group_id`, `impact_micros`, `confidence_score`, `risk_score`, `expires_at`, `google_resource_name`.
- Human-centered fields:
  - `context_outcome`: `ACTION`, `INSIGHT_ONLY`, `BLOCKED_BY_CONTEXT`
  - `blocked_reasons[]`
  - `downgrade_reasons[]`
  - `evidence_json.context`
  - `evidence_json.explanation`
- Reason arrays use fixed codes, not free text.

## Budget Guardrails
- Budget transfer comparisons are allowed only for comparable campaign roles.
- `UNKNOWN` role is conservative: high protection, non-comparable, never produces `ACTION` for budget reallocation.
- `REALLOCATE_BUDGET` remains manual-review only even when `context_outcome == ACTION`.
- `IS_BUDGET_ALERT` becomes executable only when deterministic `can_scale` checks pass.

## Execution Readiness Positioning
- The product is execution-ready only for flows that have a real canonical action path and validation.
- Current executable lane:
  - `PAUSE_KEYWORD`
  - `UPDATE_BID`
  - `ADD_KEYWORD` (SEARCH scoped)
  - `ADD_NEGATIVE` (campaign-level only)
  - `PAUSE_AD`
  - `INCREASE_BUDGET`
- Current non-executable alerts:
  - `REALLOCATE_BUDGET`
  - account-level negatives
  - `NGRAM_NEGATIVE`
  - analytics alerts
  - Google Ads native recommendations in phase 1
- Google-native executable allowlist: empty in the current milestone.

## UX Positioning
- Default recommendation view: pending.
- UI groups cards into `Executable` and `Alerts`.
- Recommendations page shows outcome badges, context chips, explanation sections, trade-offs, and risk note.
- Apply is disabled for non-executable cards.
- Insights feed is sourced from backend recommendations with `source=ANALYTICS`.

## Quality Gates
- Apply path always runs precondition checks + safety validation before mutation.
- Dry-run and blocked actions are written to `action_log` for auditability.
- Revert remains limited to explicit reversible strategies.
- Recommendation explanations are deterministic and code-based, not regex-generated free text.
