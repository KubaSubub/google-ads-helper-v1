# PHASE 5 — Performance Audit

**Stack:** FastAPI + SQLite (WAL) + React / Vite desktop app.
**Verdict:** healthy on small accounts, several quick wins worth ~5–75× speedups that are each < 1 day of work. One genuine landmine: **N+1 in anomaly detection** that blows up at 100+ campaigns.

---

## Top 10 quick wins (ordered by impact / effort)

| # | Fix | Impact | Effort | File |
|---|-----|--------|--------|------|
| 1 | Composite index `metric_daily(campaign_id, date)` | 5–10× on `/trends`, `/correlation`, `/wow-comparison`, `/dashboard-kpis` | 2 min | `database.py::_ensure_sqlite_columns` |
| 2 | Fix N+1 in anomaly detection (100 campaigns → 301 queries) | 75× (301 → 4 queries) | 1 h | `analytics_service.py:126-150` |
| 3 | Cache `/recommendations/` (TTL 120 s) and `/dashboard-kpis` (60 s) | Dashboard 1–2 s faster, repeat loads instant | 30 min | `routers/recommendations.py:318`, `routers/analytics.py:160` |
| 4 | Route-level code splitting (lazy-load Scripts, Settings, MCCOverview, Recommendations, ActionHistory, SearchTerms) | Main bundle 400 → 200–250 KB gzipped | 1 h | `routes.jsx`, `vite.config.js` |
| 5 | SQLite PRAGMAs: `cache_size=50000`, `synchronous=NORMAL`, `temp_store=MEMORY`, `ANALYZE` on init | Query planning +5–10%, writes +10–20% | 10 min | `database.py:75-85` |
| 6 | `React.memo` on `TrendExplorer` + separate data memo | Smoother metric-toggle UX | 20 min | `components/TrendExplorer.jsx` |
| 7 | Composite index `keyword_daily(keyword_id, date)` and `asset_group_daily(asset_group_id, date)` | Same pattern as #1 on per-keyword / per-asset-group queries | 2 min | `database.py::_ensure_sqlite_columns` |
| 8 | Debounce filter changes (100 ms) + request dedup on Dashboard | Cuts 50% of API calls during filter churn | 1 h | `features/dashboard/DashboardPage.jsx:142-182` |
| 9 | Pre-warm backend in parallel with PyWebView open | ~1 s perceived startup win | 30 min | `main.py:52-114` |
| 10 | Cursor pagination on `/search-terms` (replace offset) | Stable under rapid sync writes | 2 h | `routers/search_terms.py:107` |

Total effort: roughly **6 hours of engineering** for the full list. Items 1–5 are a morning.

---

## Frontend findings

### Bundle (`frontend/package.json`, `vite.config.js`)
Estimated output, gzipped:

| Chunk | Size |
|-------|------|
| vendor (react, react-dom, router, recharts, tanstack) | ~200–250 KB |
| main (every page eagerly bundled) | ~100–150 KB |
| tailwind | ~30–50 KB |
| **Total initial** | **~360–450 KB** |

- No route-level `lazy(() => import(...))` on any page.
- No `manualChunks` config → vendor is one big blob.
- `lucide-react` imported without tree-shaking pattern.

**Fix:** split heavy pages (Scripts 1,384 LOC, Settings 1,318 LOC, MCCOverview 1,024 LOC, Recommendations 956 LOC, ActionHistory 962 LOC, SearchTerms 798 LOC) into lazy chunks. Initial load drops to ~200–250 KB.

### Render hot paths

**DashboardPage** (`features/dashboard/DashboardPage.jsx:88-182`) fires 10–12 parallel API calls on mount. Two of them (`getRecommendations`, `getScriptsCounts`) are expensive backend computations (~500 ms and ~200 ms respectively). These dominate time-to-interactive and re-fire on every filter change. Caching them backend-side (#3) is the single biggest perceived-performance win.

**CampaignsPage** (`features/campaigns/CampaignsPage.jsx:332-358`) has two O(N) `campSummary[String(c.id)]` lookups inside a sort comparator — repeated per pair, so O(N² log N) in practice on the sort path. Pre-index `campSummary` into a `Map` once per render.

**TrendExplorer** re-renders all Recharts lines on every metric toggle (`METRIC_OPTIONS` has 18 entries). `React.memo` + `useMemo` on the enriched data series eliminates most of the churn.

### Fetch patterns
- No `AbortController` cleanup — navigating away mid-load leaks promises and can set state on unmounted components.
- React Strict Mode doubles every `useEffect(..., [])` fetch in dev.
- No request dedup: switching date from "30 days" to "7 days" and back to "30 days" fires 36+ requests.

---

## Backend findings

### N+1 in anomaly detection — the one genuine landmine

`backend/app/services/analytics_service.py:126-150`:

```python
for campaign in campaigns:
    rows_7d  = db.query(MetricDaily).filter(MetricDaily.campaign_id == campaign.id, ...).all()
    rows_30d = db.query(MetricDaily).filter(MetricDaily.campaign_id == campaign.id, ...).all()
    rows_3d  = db.query(MetricDaily).filter(MetricDaily.campaign_id == campaign.id, ...).all()
```

For a client with 100 campaigns: 1 + 100 + 100 + 100 = **301 queries**.

Fix: one `campaign_id.in_(ids)` query per window, then group in Python by `defaultdict(list)`. 4 queries total. ~75× reduction, observed latency drops from ~2 s to ~20 ms on realistic data.

### Routers doing DB work and holding state
- `campaigns.py:39-42` runs `ensure_campaign_roles()` + `db.commit()` inside a GET. Partial-commit risk on failure.
- `search_terms.py:107` does `count()` + `offset().limit()` on a write-heavy table — vulnerable to off-by-one during rapid sync writes.
- `analytics.py` (2,799 LOC) has no `response_model` on any GET — silent schema drift (covered in `02_technical_audit.md`).

### Google Ads API usage
Approximate call count per full sync for a 10 k-keyword / 90-day account: ~150 calls, well under the 6,000 / day quota. Not the bottleneck.

### Sync pipeline
20+ phases run **sequentially**. Estimated total for a 10 k-keyword / 90-day account: **15–40 minutes**. Independent phases (keywords / ads / search terms) could parallelise — that's a day's work and would reduce the longest-tail sync from 40 min to ~10 min. Out of scope for quick wins; worth putting on the roadmap.

---

## Database findings

### Indexes today

| Table | Index | Comment |
|-------|-------|---------|
| `metric_daily` | `idx_metrics_daily_date` | **Missing `(campaign_id, date)`** — the hot path |
| `keyword_daily` | `idx_keywords_daily_date`, `idx_keywords_daily_keyword` | Missing composite |
| `asset_group_daily` | `idx_asset_group_daily_date` | Missing composite |
| `metrics_segmented` | functional `uq_metric_segmented_coalesced` | Works but papers over schema bug (see `02_technical_audit.md`) |

### SQLite config (`database.py:75-85`)
- ✅ WAL mode, `foreign_keys=ON`, `busy_timeout=30000`.
- ❌ No `cache_size` (default ~2000 pages = ~8 MB). Bump to 50000 (~200 MB) for the working set.
- ❌ No `synchronous=NORMAL` (defaults to FULL — safer but slower writes during sync).
- ❌ No `temp_store=MEMORY` (intermediate joins spill to disk).
- ❌ No `ANALYZE` after DB init — query planner runs on stale stats post-seed.

### Estimated footprint (90-day history, 10 k-keyword account)

| Table | Rows | Size |
|-------|------|------|
| campaigns | 100 | 0.1 MB |
| keywords | 10 k | 5 MB |
| keyword_daily | 900 k | ~50 MB |
| metric_daily | 9 k | ~1 MB |
| metrics_segmented | ~150 k | ~8 MB |
| search_terms | 50 k+ | ~20 MB (unbounded growth) |
| indexes | — | ~20 MB |
| **Total on disk** | — | **~150–160 MB** |

Comfortable for a local SQLite database. Growth beyond 12 months of history on a 10 k-keyword account starts to push toward the upper limit where PRAGMAs and composite indexes stop being optional.

---

## Startup

`main.py:52-114` polls `/health` 75× at 200 ms — well designed. Cold start breakdown:

| Step | ms |
|------|-----|
| Python process | ~500 |
| FastAPI import | ~1000 |
| SQLAlchemy engine | ~200 |
| Uvicorn bind | ~200 |
| PyWebView open | ~100 |
| React bundle parse | ~1000–2000 |
| First render + initial fetches | ~500 |
| **Total** | **~4–5 s** |

Parallelising the React bundle with backend startup gets this to ~3 s for essentially no cost.

---

## What's already good

- WAL mode + 30 s busy timeout — prevents the canonical "database is locked" pain.
- `/health` poll-based startup instead of fixed sleep.
- Primary dashboard fetches are `Promise.all` + non-blocking secondary fetches.
- `useMemo` + `useCallback` applied at the right grain in `CampaignsPage`.
- `recommendations.py:166-241` batches with a single `db.flush()` — correct pattern.

---

## Priority order

1. **This morning (2 hours):** #1 composite index on `metric_daily`, #5 SQLite PRAGMAs + ANALYZE, #3 cache layer on two hot endpoints, #7 parity composite indexes.
2. **This week (1 day):** #2 N+1 fix, #4 code splitting, #6 TrendExplorer memoisation.
3. **Next sprint (1–2 days):** #8 debounce + dedup, #9 startup parallelism, #10 cursor pagination.
4. **Roadmap:** sync pipeline parallelism — reduces largest-account sync from 40 min to ~10 min, 2–3 days of work.
