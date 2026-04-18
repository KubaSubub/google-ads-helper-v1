# PHASE 8 — Code Quality & Maintainability

**Verdict:** **5.2 / 10** — Medium-high maintainability risk. Strong type-hinting, clean imports, solid test-to-source ratio on core domain logic. Dragged down by two 5 000+ LOC god-files, shallow abstraction in the recommendation engine, 15+ copies of the same threshold predicate, and zero frontend type safety.

---

## Top 10 longest files

| Path | LOC | Concern |
|------|-----|---------|
| `backend/app/services/google_ads.py` | 5 598 | **Monolith.** Query building + API calls + transforms + mutations in one class. 68 methods. |
| `backend/app/services/analytics_service.py` | 5 397 | **Monolith.** 50+ analytics methods; no domain boundaries (KPI / anomaly / correlation / forecast all mixed). |
| `backend/app/services/recommendations.py` | 3 250 | 28+ rules inline in one engine class. No plugin boundary. |
| `backend/app/routers/analytics.py` | 2 799 | 81 endpoints doing heavy calculation in the router layer. No `response_model`. |
| `backend/app/seed.py` | 2 005 | Test-data factory; monolithic but acceptable scope. |
| `backend/app/routers/clients.py` | 1 403 | Router + sync orchestration mixed. |
| `frontend/src/features/scripts/ScriptsPage.jsx` | 1 384 | Mega-component (dry-run / execution / results phases in one file). |
| `frontend/src/pages/Settings.jsx` | 1 318 | 18 `useState` calls, multi-section form. |
| `backend/app/routers/sync.py` | 1 170 | Streaming + phase orchestration + error handling coupled. |
| `backend/app/services/agent_service.py` | 1 142 | Agent loop + recommendation filtering + execution flow coupled. |

**Rule of thumb:** anything over ~500 LOC is a smell. Six backend files and two frontend files are over 1 000.

---

## Top 10 longest functions

| Location | ~LOC | Concern |
|----------|------|---------|
| `google_ads.py::sync_campaigns` | 177 | Label fetching + fallback query + JSON serialisation inlined |
| `google_ads.py::sync_keywords` | 173 | Negative-keyword dedup + metrics aggregation + role classification inline |
| `google_ads.py::sync_search_terms` | 120 | Campaign/ad-group dual path resolution |
| `analytics_service.py::compute_trend_kpis` | ~150 | 10+ metric calculations, no composition abstraction |
| `analytics.py::get_metrics_correlation` | ~120 | Manual variance calc + legacy alias mapping + per-segment iteration |
| `action_executor.py::execute_action` | ~100 | Precondition + 6 action branches + safety validation |
| `routers/keywords_ads.py::list_keywords` | ~100 | Join complexity (campaign + ad_group + role) |
| `ScriptsPage.jsx::ScriptExecutor` | ~400 | Phase state machine + checkbox toggles + row rendering |
| `Settings.jsx` body | ~300 | Form, auto-save, sync scheduler, lesson journal |
| `recommendations.py::_rule_1_pause_keyword` | ~80 | CTR + cost + relevance checks inline |

---

## DRY violations

### Confirmed
- **`_apply_keyword_filters`** — defined in `keywords_ads.py:29`, near-identical logic in `search_terms.py:54-97` and partial copy in `recommendations.py`. Already planned for extraction to `app/dependencies/filters.py`.

### New findings
- **Transactional pattern `try / except / logger.error / db.rollback / raise`** — 45+ occurrences across `google_ads.py`, `sync.py`, `action_executor.py`. Extract to `@transactional` decorator or context manager.
- **Metric aggregation loops** — `sum(t.cost_micros or 0 for t in terms)` and friends repeated ~15 times across `analytics_service.py`, `search_terms_service.py`, `recommendations.py`. Extract `aggregate_metrics(records, field, default=0)`.
- **Threshold predicate** — `if kw.clicks >= X and kw_cost >= Y and kw_ctr < Z:` shape appears in R1, R5, R6, R12, R13, and 10+ other places. Predicate builders (`click_threshold_predicate(kw, min_clicks)`) cut this to one line each.
- **Form state on frontend** — `Settings.jsx` (18 `useState`), `ScriptsPage.jsx` (12), `CampaignsPage.jsx` (15). Extract `useFormState(initial)` returning `{values, setField, reset}`.
- **Pydantic response serialisation** — manual `{col.name: getattr(row, col.name) for col in Model.__table__.columns}` pattern replicated in 3+ routers. Use Pydantic `model_validate(row).model_dump()` or add a model base method.

---

## Dead code

- `CampaignsPage.jsx:4` — `Monitor` icon imported, never rendered.
- `CampaignsPage.jsx:226` — `roleDraft` state: flagged in earlier audit as unused; second review shows it *is* used by the edit-role form. **Not dead.** Keep.
- `Settings.jsx` — `SectionGroupHeader` component defined, not referenced after refactor.
- `analytics.py` — `from scipy.stats import ttest_ind` imported but only mentioned in a comment; actual t-test logic missing.
- `search_terms_service.py` — `Topic`, `Placement` imported, never used.

Low total volume, but worth sweeping.

---

## Naming inconsistencies

| Issue | Example |
|-------|---------|
| Route casing | `/recommendations` ✅ vs `/search-terms` ✅ vs `/daily-audit` ✅, query params in `snake_case`. Consistent. Minor — double-check the full list for any `camelCase` escapees. |
| Service import alias | `ga_service` vs `GoogleAdsService` vs `google_ads_service` used in different routers. Pick one (`google_ads_service` singleton). |
| Model vs schema | `Keyword` + `KeywordResponse` + `KeywordSchema` all appear. Adopt convention: model + `ModelResponse`; retire `...Schema`. |
| Status fields | `is_enabled` vs `status='ENABLED'` vs `paused` vs `active` used in different places. Standardise on the `status: Literal['ENABLED', 'PAUSED', 'REMOVED']` pattern already present on `Campaign`. |
| Ambiguous identifiers | `entity_id` / `entity_name` on `ActionLog`, `Recommendation` — without `entity_type` context, ambiguous. |

---

## Error handling patterns

| Pattern | Count | Risk |
|---------|-------|------|
| `except Exception as e: logger.error(...); db.rollback(); raise` | 45+ | Medium — loses error type info |
| `except (AttributeError, TypeError):` | 12 | Low — good specificity |
| `except GoogleAdsException:` | 8 | Good — domain-specific |
| `try ... except` with no logging | 15+ | Medium — silent failures |
| Bare `except:` | 3 | **Red** — silent blanket catch; verify each in `demo_guard.py`, `auth.py` |
| `HTTPException(status_code=400, detail=str(e))` | ~20 | Medium — raw error messages can leak internals (see `03_security_audit.md`) |

**Consistency score: 4 / 10.** No standardised error response schema. Build `ErrorResponse(code, message, detail, retry_after)`, a custom exception hierarchy (`GoogleAdsQuotaError`, `ValidationError`, etc.), and a `@transactional` decorator. Rolls up cleanly with the response-model audit in `02_technical_audit.md`.

---

## Logging

- 40+ `logger.info(f"string {var}")` — raw interpolation, no structured context.
- 30+ `logger.error()` + manual formatting; not using `exc_info=True` for tracebacks.
- 25+ `logger.warning()` sometimes used for non-error conditions (fallback queries) → severity drift.
- **Zero** structured logging (`extra={}`).
- **Zero** print statements. Good.

**Score: 5 / 10.** Add request-ID middleware and structured context (`client_id`, `request_id`, `user`). One hour of work, big debugging dividend.

---

## Type hints

| Layer | Coverage | Gap |
|-------|----------|-----|
| Backend services | ~80% | Missing on small utilities (`_safe_float`, `_ctr_micros_to_pct`) |
| Backend routers | ~70% on Query params, ~60% on returns | Nested response dicts often untyped |
| Backend models (SQLAlchemy) | 100% | — |
| Pydantic schemas | ~95% | — |
| **Frontend** | **0%** | No TypeScript, no JSDoc, no PropTypes |

**Backend score: 7 / 10. Frontend: 2 / 10.**

---

## Magic numbers

### Recommendation thresholds

| Value | Used in | Proposal |
|-------|---------|----------|
| `30` (min days / clicks / keywords / learning days) | `recommendations.py:165, 211, 215, 221` | `MIN_ANALYSIS_PERIOD_DAYS = 30` |
| `0.5` (CTR / underspend / pmax-cost ratio) | `recommendations.py:166, 180, 197, 205` | `PERFORMANCE_BASELINE_RATIO = 0.5` |
| `50.0` USD (min spend for rules R13/R27/R30) | `recommendations.py:198, 224, 230` | `MIN_SPEND_FOR_RECOMMENDATION_USD = 50.0` |
| `3` (min conversions R4) | `recommendations.py:174` | `MIN_CONVERSIONS_FOR_ADD_KEYWORD = 3` |
| `500` (min impressions R6/R11) | `recommendations.py:181, 194` | `MIN_IMPRESSIONS_FOR_AD_EVALUATION = 500` |
| `2.0` (ROAS ratio / CPA multiplier) | `recommendations.py:183, 200, 229` | `UNDERPERFORMANCE_MULTIPLIER = 2.0` |
| `24` (revert window hours) | `action_executor.py:36` | `REVERT_WINDOW_HOURS = 24` |

### Query limits

| Value | Proposal |
|-------|----------|
| `50` default page size | `DEFAULT_PAGE_SIZE = 50` |
| `500` max page size | `MAX_PAGE_SIZE = 500` |
| `365` max days range | `MAX_DATE_RANGE_DAYS = 365` |

### Frontend
- `500` / `50` savings colour thresholds in `ScriptsPage.jsx:98-99`.
- `4` spacing unit repeated 50+ times across `Settings.jsx`, `CampaignsPage.jsx` — CSS variable `--spacing-sm` would centralise.

**Fix:** single `app/config/thresholds.py` (or per-client overrides in DB) + a frontend `spacing.js` constants file.

---

## SOLID violations

### Single responsibility
- `GoogleAdsService` — query + API + transform + mutation orchestration (5.6 k LOC).
- `AnalyticsService` — KPI + anomaly + correlation + forecast.
- `ActionExecutor` — validate + execute + revert + log.
- `RecommendationsEngine` — generate + filter + dedupe + prioritise 28 rules.

### Open/closed
- Adding a rule requires editing `RecommendationsEngine.__init__` + a new method. No plugin boundary.
- Adding an analytics metric requires editing `AnalyticsService` directly.

### Dependency inversion
- `ActionExecutor` imports concrete models directly, no abstraction → hard to mock.
- Routers depend on the concrete `GoogleAdsService` singleton; no interface to inject test doubles.

---

## Frontend patterns

| Pattern | Score | Comment |
|---------|-------|---------|
| Functional components | 9/10 | 100% functional, no legacy classes |
| Hooks rules | 8/10 | Mostly clean; some missing deps cause redundant callbacks |
| Context vs props | 7/10 | `AppContext` + `FilterContext` well scoped |
| Component splitting | 4/10 | 4 mega-components over 900 LOC |
| API fetch pattern | 5/10 | `useEffect + useState + try/catch` repeated; no `useApi` hook; no error boundary |
| Styling (inline vs tokens) | 7/10 | Tokens mostly applied; `SearchTerms.jsx` drifts into inline |

---

## Comment quality

| File | Comment ratio | Quality |
|------|---------------|---------|
| `google_ads.py` | 1.6% | Mostly "what" ("Fetch all campaigns from API"); missing "why" |
| `recommendations.py` | 2.7% | Good rule docstrings; threshold justification absent |
| `analytics_service.py` | 0.8% | Low. Long functions with opaque logic |
| `CampaignsPage.jsx` | 2% | Minimal; timeline/history logic undocumented |

**Score: 4 / 10.** Comments describe syntax, not intent. Add one-line "why this threshold" comments on each rule; revisit `CLAUDE.md` guidance that comments should carry non-obvious WHY.

---

## Test-to-source ratio

| Module | Source LOC | Test LOC | Ratio | Assessment |
|--------|-----------|----------|-------|------------|
| `recommendations.py` | 3 250 | ~2 000 (8 files) | 0.62 | Good — R1–R7 + PMax cannib + rule contract |
| `search_terms_service.py` | 437 | ~300 | 0.69 | Good |
| `action_executor.py` | 876 | ~400 | 0.46 | Medium |
| `analytics_service.py` | 5 397 | ~1 200 | 0.22 | **Low** — KPIs tested; correlation / forecast not |
| `google_ads.py` | 5 598 | ~800 | 0.14 | **Low** — integration-heavy; no unit tests for helpers |

---

## Refactor candidates by pain × frequency

### Tier 1 — critical (next sprint)
1. **Split `GoogleAdsService`** into `CampaignSyncService`, `KeywordSyncService`, `MetricsSyncService`, `MutationService`. Effort: ~40 h. Payoff: every sync fix becomes localisable instead of wading through 5 600 LOC.
2. **Decompose `AnalyticsService`** into `KPICalculator`, `AnomalyDetector`, `CorrelationAnalyzer`, `ForecastModel`. Effort: ~30 h.
3. **Plugin architecture for recommendations** — `RuleInterface` + `RuleRegistry`. Effort: ~35 h. Payoff: new rules stop requiring edits to a 3 k-LOC class.
4. **Extract `_apply_keyword_filters` + `CommonFilters` as FastAPI dependency.** Effort: ~8 h.

### Tier 2 — high (next 2 sprints)
5. Router → service boundary cleanup on `sync.py`, `clients.py`, `actions.py`.
6. `@transactional` decorator + custom exception hierarchy.
7. Frontend `useFormState(schema)` hook + error boundary + `useApi` wrapper.
8. Split `ActionExecutor` into `ActionValidator`, `ActionRunner`, `ActionReverter`.

### Tier 3 — medium (backlog)
9. Move magic numbers to `config/thresholds.py`.
10. Split mega-pages (`ScriptsPage`, `Settings`, `CampaignsPage`) into focused sub-components.
11. Adopt TypeScript or JSDoc for the frontend API layer.
12. Structured logging with request-ID middleware.

---

## Priority fixes

### Small (<4 h, immediate)
- Remove unused imports (`ttest_ind`, `Topic`, `Placement`, `Monitor` icon).
- Investigate the 3 bare `except:` clauses (`demo_guard.py`, `auth.py`).
- Extract `SAVINGS_THRESHOLDS` constant in `ScriptsPage.jsx`.
- Document the `30`-day threshold choice at the top of `recommendations.py`.

### Medium (4–16 h, this sprint)
- Central `filter_helpers.py` + `CommonFilters` DI.
- `ActionExecutor` split into three classes.
- `useFormState` hook + rollout to 3 pages.
- `@transactional` decorator + one exception hierarchy.

### Large (16+ h, next sprint)
- `GoogleAdsService` decomposition.
- `AnalyticsService` decomposition.
- Recommendation plugin architecture.
- Sync orchestration extracted from routers.

---

## Scorecard

| Category | Score |
|----------|-------|
| File / function length | 3/10 |
| DRY | 5/10 |
| Naming consistency | 6/10 |
| Dead code | 8/10 |
| SOLID | 3/10 |
| Magic numbers | 4/10 |
| Error handling | 4/10 |
| Logging | 5/10 |
| Type hints (backend) | 7/10 |
| Type hints (frontend) | 2/10 |
| Frontend patterns | 7/10 |
| Comments | 4/10 |
| Test coverage | 6/10 |
| Import hygiene | 9/10 |
| **Overall** | **5.2 / 10 — Medium-high risk** |

The codebase ships and works. It won't continue to feel shippable past ~12 months of accumulated new features without the Tier-1 decompositions. Enforce a 400-LOC function limit and a 800-LOC file limit in code review starting today, and the top-of-file monoliths stop growing.
