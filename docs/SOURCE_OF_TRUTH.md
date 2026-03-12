# Source of Truth - Google Ads Helper

Last updated: 2026-03-12
Owner: Product + Engineering

## Document Priority
1. This file (`docs/SOURCE_OF_TRUTH.md`) is the canonical index.
2. API contract: `docs/API_ENDPOINTS.md`
3. Feature scope and product behavior: `docs/FEATURE_SET.md`
4. Delivery status and open work: `PROGRESS.md`
5. Historical snapshot (non-authoritative): `Technical_Spec.md`

## Current Product Baseline
- Backend: 12 API routers
- Frontend: 15 pages
- Recommendation engine: 17 active rules (R1-R13, R15-R18)
- Sync trigger: `POST /api/v1/sync/trigger` (legacy `/clients/{id}/sync` is deprecated)

## Recommendation Engine Scope
- Active rules: R1-R13 and R15-R18
- Inactive rule: R14 (intentionally not implemented)
- Rule categories:
  - `RECOMMENDATION`: executable actions
  - `ALERT`: diagnostic recommendations (non-executable)

## Execution Readiness Positioning
- Current official message: execution-ready (validated write-flow + API contract smoke tests).
- Core value path: `sync -> insight -> apply/revert -> history`.
- Advanced modules (semantic, forecast, optimization, monitoring) are expansion layer, not core MVP lane.

## Consistency Checklist
- [x] No documentation should advertise `/clients/{id}/sync` as current endpoint.
- [x] No current-state document should state "7 recommendation rules".
- [x] API endpoint docs and backend routers use consistent prefixes and query params.
- [x] Technical spec is marked as legacy snapshot (2025-02-17).

