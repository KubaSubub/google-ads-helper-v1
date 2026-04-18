# PHASE 2 — Frontend + Backend + SQL Technical Audit

**Date:** 2026-04-18
**Verdict:** Functional, but with significant technical debt. Monolithic routers (`analytics.py` = 2,799 LOC, 81 endpoints), a 749-line page component, float-typed money-adjacent aggregates, no migrations framework, and missing `response_model` across a wide API surface.

**Scorecard**

| Area | Score | Headline |
|------|-------|----------|
| Frontend | 5/10 | Context layer is clean; pages are bloated; no error boundaries; no AbortController on fetches |
| Backend | 4/10 | Routers well-named; `analytics.py` is a monolith; business logic leaks into routers; streaming endpoints return 200 on failure |
| Database / SQL | 6/10 | Good FKs and WAL; Float for conversion aggregates; NULL-in-UNIQUE workaround papers over a schema bug; no Alembic |
| **Overall** | **4.5/10** | Ships today, scales badly past ~100k rows per table |

---

## Frontend

### Good

- **Context-driven state** — `AppContext` (selectedClientId, clients, auth flag, toast, alert count) and `FilterContext` (campaignType, status, period, dateFrom/To, computed `days`) avoid prop drilling on the primary cross-cutting concerns.
- **Selective memoisation** — `useMemo` + `useCallback` around campaign selection and metric filtering (e.g. `CampaignsPage.jsx:251, 332`).
- **Event-driven 401 handling** — `api.js:10-14` + `AppContext.jsx:65-70` reacts to a custom auth-failure event and falls back through `localStorage`. Graceful.
- **Design tokens via Tailwind constants** (`C`, `T`, `B`, `PILL`, `.v2-card`) — reduces inline-style sprawl and matches the documented v2 design system in `MEMORY.md`.
- **`TrendExplorer` reusable chart component** centralises Recharts usage so individual pages don't each reinvent it.

### Bad

#### 1. `CampaignsPage.jsx` is a 749-line monolith with 21 `useState` calls (`frontend/src/features/campaigns/CampaignsPage.jsx`)

- Three chained `useEffect` blocks (lines ~285–331) with an implicit order dependency — campaigns → KPIs → device/geo. No error boundary, no retry, no fallback; if campaigns fetch silently fails, the downstream fetches never fire.
- `filteredCampaigns` `useMemo` recomputes a sort+filter over potentially 1,000+ campaigns on every prop change.
- Dead state: `roleDraft` (line 226) is set but never rendered; `savingRole` spinner was wired but never connected to an actual API call.
- Should be split into `CampaignList`, `CampaignDetail`, `CampaignMetrics`, `ActionTimeline`. 40%+ render reduction for free.

#### 2. Data fetches have no `AbortController` and no structured error state

- Pages show a spinner, then silently revert to old data if the refresh fails. There is no retry button, no toast, no way for the user to know a load failed.
- React Strict Mode in dev doubles every no-deps `useEffect(fetch, [])` — the initial load fires twice, amplifying API load while the user is still waiting on auth.
- Pages that navigate away mid-fetch still set state on unmounted components → warning spam + memory-leak pattern.

Fix pattern:

```jsx
useEffect(() => {
  const ctrl = new AbortController();
  fetchData(ctrl.signal).catch(err => {
    if (!ctrl.signal.aborted) setError(err);
  });
  return () => ctrl.abort();
}, [deps]);
```

Then wrap the page in an `ErrorBoundary` with retry.

#### 3. Filter contract is ambiguous — backend can't tell what the client wants

- `FilterContext` computes `days` dynamically from `dateFrom`/`dateTo`.
- Some pages call the API with **both** `date_from`/`date_to` **and** numeric `days`. Backend has no documented precedence rule.
- Case-sensitive `'ALL'` sentinel is hardcoded on the frontend; `common_filters()` on the backend normalises enum casing. One side changes casing → silent filter mismatch → wrong data in the UI.
- Fix: introduce `useFilterParams()` hook that always resolves to exactly one of `{ days }` or `{ date_from, date_to }`; enforce the same on every `api.js` call.

#### 4. Loading / error / empty states are not uniformly handled

- `EmptyState` is used for "no data" but not for "load failed."
- `Recommendations.jsx` can't distinguish "no recommendations" from "fetch error."
- No global toast on API errors except the 401 redirect.

#### 5. `api.js` lacks tests

- No jest coverage on the filter-parameter builder. The contract between FE and BE is not pinned anywhere.

### Priority fixes (frontend)

1. Split `CampaignsPage.jsx` into 4 components.
2. Add an `AbortController` + `useErrorBoundary` convention; roll it across every page that calls `api.*`.
3. Kill the dual-filter ambiguity: one shape per endpoint, resolved in a central helper, tested.
4. Add API-failure toasts globally (wire into the `api.js` interceptor that already handles 401).
5. Remove dead state in `CampaignsPage.jsx` (`roleDraft`, unwired `savingRole`).

---

## Backend

### Good

- **Router organisation by domain** — `campaigns`, `keywords_ads`, `search_terms`, `recommendations`, `analytics`, `sync`, `auth`, `actions`, `rules`. Clean mental model.
- **Pydantic schemas for inputs** on the main mutation endpoints (`CampaignUpdate`, `PeriodComparisonRequest`, etc.).
- **Session-based auth with 60-min TTL** — `security.py`, checked on startup in `AppContext`.
- **Graceful Google Ads init** — `google_ads.py::_try_init` falls back to mock mode if credentials are missing, keeping the app usable in setup flow.
- **Sync phase isolation** — `sync.py::_run_phase` catches per-phase failures so one broken sync step doesn't nuke the rest.
- **Raw SQL quarantined to schema bootstrapping** — `_ensure_sqlite_columns` is the only place `text()` is used for DDL; query logic stays ORM.
- **Write-safety architecture is real** — `ActionExecutor`, `write_safety.py`, `demo_guard.py`, circuit breaker, audit log. Mutations go through validation and a central executor.

### Bad

#### 1. `analytics.py` — 2,799 LOC, 81 endpoints, zero `response_model` annotations

- Any schema drift on a Pydantic model silently changes what clients receive. A renamed field disappears from the response without anyone noticing.
- No shared pagination helper — `limit = Query(20, ge=1, le=50)` is copy-pasted per endpoint, with different bounds.
- `query.count()` called on every aggregation, often on tables that don't need a total (especially for cursor-style consumption).
- Must be split into focused routers (`analytics_campaigns.py`, `analytics_keywords.py`, `analytics_anomalies.py`, etc.), each ≤ ~200 LOC. Add `response_model=` to every GET.

#### 2. Streaming / SSE endpoints return HTTP 200 on failure

- `backend/app/routers/agent.py:48` yields an SSE `error` event but never sets the response status to 500.
- Client can only detect failure by parsing the event stream. This breaks every generic HTTP observability tool and violates the contract semantics.
- Fix: set status before the first event; include a structured error chunk schema (`{type: "error", code, message, retry_after}`).

#### 3. Business logic leaks into routers

- `campaigns.py:39-42` — `ensure_campaign_roles()` + `db.commit()` inside a GET handler. If the commit fails halfway, the user sees partial roles.
- `keywords_ads.py:29-61` — `_apply_keyword_filters()` is a router-local helper duplicated across 3–4 routers. Belongs in a `KeywordFilterService`.
- `search_terms.py:107-108` — `query.count() + .offset().limit()` on a write-heavy table. No cursor pagination; vulnerable to off-by-one on rapid writes.

#### 4. Aggregate money / conversion columns typed as `Float`

- `keyword.py:27`, `metric_daily.py:19`, `keyword_daily.py:19`, `ad.py:37`, `asset_group_daily.py:18` — `conversions = Column(Float, default=0.0)`.
- Google Ads returns fractional conversions (data-driven attribution). `SUM(conversions)` over 10M+ rows accumulates IEEE-754 rounding error; at 1.5 convs × 1M rows the error exceeds 0.1%.
- Fix: `Numeric(precision=12, scale=4)` or store as `BigInteger` micros (`conversions_micros`).
- **No aggregation precision tests exist** — this will be noticed by a customer, not by CI.

#### 5. Timezone handling mixes naive and aware datetimes

- `negative_keyword.py:26-30` uses `datetime.now(timezone.utc).replace(tzinfo=None)` — strips the UTC marker, then gets compared elsewhere to `datetime.now()` (naive local).
- `database.py:72` sends ISO strings to the wire (`isoformat() + "Z"`), but reads naive strings back from SQLite.
- DST boundary → mismatched times → subtle 1-hour shifts in trend data.
- Fix: **never** strip `tzinfo`. Always store UTC-aware; convert at the output boundary only.

#### 6. Missing `response_model` across the read-heavy API surface

- Not only `analytics.py` — `sync.py::trigger_sync` returns a dict; `agent.py` streams chunks without a schema contract.
- When a backend field is added/renamed, frontends silently break.

#### 7. Google Ads API errors collapse into generic strings

- `_try_init` catches `Exception`, logs the string, returns `None`.
- `recommendations.py::apply` catches `GoogleAdsException`, returns 400 with message — no distinct 429 for quota, no retry-after, no action-type hint.
- The user sees "bad request" for what is actually a rate limit or a transient API error.

#### 8. Sync partial-failure semantics are unclear

- `sync.py::trigger_sync` runs ~20 phases. If phase 10 fails, phases 11–20 still commit their partial results.
- Caller has no way to tell "data is corrupted for phase 10" from "phase 10 genuinely had no data."
- Fix: group phases into "core" (all-or-nothing transaction) and "optional" (independent), surface per-phase status.

#### 9. Unbounded queries on user-facing endpoints

- `recommendations` without pagination for clients with 10k+ recs.
- `search_terms.py:107` fetches all terms for a client with no default date filter.
- `semantic.py` accepts `top_n: int = 1000` with no upper bound (also a security finding — see `audit/03_security_audit.md`).

### Priority fixes (backend)

1. Split `analytics.py` into 6–8 focused routers; add `response_model=` on every GET.
2. Add a shared `common_filters` / `common_pagination` dependency (the project already has a CommonFilters contract — use it everywhere; enforce cursor pagination on large tables).
3. Replace `Float` with `Numeric(12,4)` (or micros `BigInteger`) for conversion/value aggregates; write an aggregation precision test.
4. Fix timezone handling — UTC-aware end to end.
5. SSE / streaming endpoints must set status before the first event and follow a structured error chunk schema.
6. Move business logic out of routers (role assignment, filter builders, multi-step commits) into services.
7. Classify Google Ads API errors (401 → re-auth, 429 → rate limit with retry-after, 400 → validation, 500 → transient server error) and surface specific status codes.

---

## Database / SQL

### Good

- **Foreign keys with CASCADE delete** on child tables (`campaign`, `metric_daily`, `keyword_daily`, etc.). Referential integrity is preserved.
- **Indexes on date columns** in `metric_daily`, `keywords_daily`, `asset_group_daily`. Time-range queries work.
- **WAL mode + busy timeout** (`database.py:79-84`) — prevents the classic "database is locked" pain on concurrent reads/writes.
- **Unique constraints on natural keys** — `uq_campaign_google_id`, `uq_metric_daily`, etc.
- **Good use of `BigInteger` for micros** across `cost_micros`, `bid_micros`, `cpa_micros`, etc.

### Bad

#### 1. `Float` for conversion aggregates

Covered above in backend. This is the single highest-severity SQL finding.

#### 2. NULL-in-UNIQUE bug in `metric_segmented`

- `metric_segmented.py:12-24` — `UNIQUE(campaign_id, date, device, geo_city, hour_of_day, age_range, gender, parental_status, income_range, ad_network_type)` with all dimension columns nullable.
- SQLite (and ANSI SQL) treat `NULL != NULL` in unique keys → the same logical row can be inserted multiple times if any dimension is null.
- `database.py:215-227` adds a functional `COALESCE(col, '__NONE__')` unique index as a workaround. That's duct tape on a schema problem, and it's **only applied to `metric_segmented`** — any other table with a similar pattern (e.g. `placement_exclusion`, `asset_group_signal`) has the same bug and no workaround.
- Fix: `NOT NULL DEFAULT '__NONE__'` on each dimension column, or split into per-dimension tables, then drop the functional index.

#### 3. Missing composite indexes on `(campaign_id, date)`

- `metric_daily` has `idx_metrics_daily_date` but no composite `(campaign_id, date)`.
- Every `WHERE campaign_id = ? AND date BETWEEN ? AND ?` query scans by campaign_id, then filter by date — or vice versa. For large accounts this is the hot path.
- `keyword_daily` does it right. Fix parity.

#### 4. No migrations framework

- Schema evolves via `_ensure_sqlite_columns` running `ALTER TABLE` on startup. Not transactional, not rollback-able, not versioned.
- Two concurrent backends starting simultaneously race on `EXISTS(column)` / `CREATE INDEX`.
- Project-level decision (documented in MEMORY.md) is "no Alembic — reseed the DB." That's defensible while the app is single-user pre-1.0, but it means **every schema change requires users to lose historical data** unless they manually rebuild.
- Adopt Alembic before any customer relies on historical analysis beyond the current sync window.

#### 5. String interpolation for table names in bulk updates

- `database.py:194-205` interpolates table names (not user input, but fragile). A typo yields "UPDATE 0 rows" silently.
- Fix: centralise table-name references; fail loud if a referenced table doesn't exist.

### Priority fixes (SQL)

1. Replace `Float` with `Numeric(12,4)` or micros `BigInteger` for `conversions`, `conversion_value`, any other non-count aggregate. Add precision tests.
2. Add `Index("idx_metrics_daily_campaign_date", "campaign_id", "date")` and audit every time-series table for the same pattern.
3. Fix `metric_segmented` (and any similar) NULL-in-UNIQUE at the schema level; remove the functional-index workaround.
4. Adopt Alembic. Backfill migration `0001_initial` from current schema.
5. Standardise `created_at` / `updated_at` columns as timezone-aware across all tables.

---

## Top 5 technical issues by severity

| # | Severity | Issue | File / locus |
|---|----------|-------|-------------|
| 1 | **CRITICAL** | `conversions = Column(Float)` across 8+ models → silent precision loss on SUM at scale | `models/keyword.py:27`, `metric_daily.py:19`, `keyword_daily.py:19`, `ad.py:37`, `asset_group_daily.py:18` |
| 2 | **CRITICAL** | `analytics.py` is 2,799 LOC / 81 endpoints / zero `response_model` → silent schema drift | `backend/app/routers/analytics.py` |
| 3 | **HIGH** | `CampaignsPage.jsx` 749 LOC, 21 `useState`, 3 chained `useEffect`, no AbortController, dead state | `frontend/src/features/campaigns/CampaignsPage.jsx:207-331` |
| 4 | **HIGH** | Streaming / SSE endpoints return HTTP 200 on internal error | `backend/app/routers/agent.py:48`, any other streaming handler |
| 5 | **MEDIUM** | NULL-in-UNIQUE on `metric_segmented` papered over with a functional index, not applied to peer tables | `backend/app/models/metric_segmented.py:12-24`, `backend/app/database.py:215-227` |

Secondary, worth fixing in the same pass:

- Timezone mixing (`models/negative_keyword.py:26-30`, `database.py:72`).
- No composite `(campaign_id, date)` index on `metric_daily`.
- Filter-shape ambiguity (FE sending both `days` and `date_from/date_to`).
- `semantic.py` `top_n` unbounded (also a security finding).
- No Alembic.

---

## Suggested refactor sequence

1. **Fix Float → Numeric on conversion/value fields** (with migration + precision test).
2. **Add `response_model` + split `analytics.py`.**
3. **Introduce Alembic** so the above don't require reseed.
4. **Frontend: AbortController + ErrorBoundary convention + split CampaignsPage.**
5. **Timezone clean-up and streaming-endpoint status semantics.**
6. **Composite indexes + NULL-in-UNIQUE cleanup across segmented tables.**

Each step is one PR, each one independently ships value, and the ordering lets the heavier data-layer changes land first so the frontend changes build on a stable contract.
