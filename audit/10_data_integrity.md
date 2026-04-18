# PHASE 10 — Data Integrity & Sync Quality

**Verdict:** **75 / 100. Core sync is sound** (micros correct, transactions safe, upserts idempotent, ADR-019 SDK/API pinning is exemplary). **Lacks three things that will bite at scale:** reconciliation / drift detection, provisional-data tagging for the last 3 days, retry+backoff on transient API errors. Plus: account timezone is missing from the schema entirely.

**Safe for:** 1–3 single-user clients on desktop.
**Not safe for:** 5+ clients or any cloud deployment, until the five CRITICAL fixes below.

---

## Sync coverage matrix

| Resource | Present | Frequency | Window | Delta | Notes |
|----------|---------|-----------|--------|-------|-------|
| Campaigns | ✅ | Full | n/a | Full + REMOVED tombstone | — |
| Ad groups | ✅ | Full | n/a | Full + REMOVED tombstone | — |
| Keywords (positive) | ✅ | Full | n/a | Full + REMOVED tombstone | — |
| Keywords (negative) | ✅ | Full | n/a | Full + REMOVED tombstone | — |
| Ads (RSA) | ✅ | Full | n/a | Full + REMOVED tombstone | — |
| Search terms (Search) | ✅ | Incremental | 180d | Delta by date | Max window ✅ |
| Search terms (PMax) | ✅ separate path | Incremental | 180d | Delta by date | `source=PMAX` — correct isolation |
| Asset groups | ✅ | Full | n/a | Full | — |
| Asset group daily | ✅ | Incremental | 1095d | Delta by date | Max window ✅ |
| Keyword daily | ✅ | Incremental | 1095d | Delta by date | Max window ✅ |
| Daily campaign metrics | ✅ | Incremental | 1095d | Delta by date | Max window ✅ |
| Device / geo / demographic metrics | ✅ | Incremental | 1095d | Delta by date | Max window ✅ |
| Auction insights | ✅ | Incremental | 90d | Delta by date | Max window ✅ |
| Change events | ✅ | Incremental | 28d | Delta (always last 28d) | Max window ✅ |
| Conversion actions | ✅ | Full | n/a | Full | — |
| **Impression share (campaign)** | ✅ | Full aggregate | **30d FIXED** | Aggregated last-30d only | ⚠️ arbitrary; loses history for old campaigns |
| Bidding strategies | ✅ | Full | n/a | Full | — |
| Audiences | ✅ | Full | n/a | Full | — |
| Bid modifiers | ✅ | Full | n/a | Full | — |
| Google recommendations | ✅ | Full | n/a | Full | — |
| Conversion value rules | ✅ | Full | n/a | Full | — |
| **Placement metrics** | ✅ | Incremental | **90d** | Delta by date | ⚠️ arbitrary; older placements invisible |
| **Topic metrics** | ✅ | Incremental | **90d** | Delta by date | ⚠️ arbitrary |
| MCC exclusion lists | ✅ | Full | n/a | Full (manager account) | — |
| Negative-keyword lists | ✅ | Full | n/a | Full | — |
| Campaign audiences (metrics) | ✅ | Incremental | 1095d | Delta by date | Max window ✅ |
| Offline conversions | ❌ | — | — | — | Model stub exists; sync not built |

**Max-window adherence:** strong — 12 of 15 incremental syncs hit the API hard limit. Three exceptions (Impression Share 30d fixed, placement 90d, topic 90d) are either arbitrary or documented API limits; needs labelling in `sync_config.py`.

---

## Integrity findings

### Micros — excellent

All monetary values stored as `BigInteger` micros across `MetricDaily`, `KeywordDaily`, `SearchTerm`, `Campaign.budget_micros`, `Campaign.target_cpa_micros`, `avg_cpc_micros`, `conversion_value_micros`, `all_conversions_value_micros`, `value_per_conversion_micros`. **No `REAL` or `Float` money columns anywhere.** ADR-002 compliance is complete.

### Conversions as `Float` — consistent

Conversions and their extended variants (`all_conversions`, `cross_device_conversions`) are `Float` across `MetricDaily`, `KeywordDaily`, `SearchTerm`. Correct choice (fractional attribution). But `Float` precision on `SUM` at 1M+ rows is a separate concern covered in `02_technical_audit.md` — consider `Numeric(12,4)` or `BigInteger` units for aggregate-heavy paths.

### Impression Share NULL vs 0

`google_ads.py::_safe_is()` converts `0.0` to `None`. Semantically defensible ("no data") but **not documented**, and `None` vs `0` means two different things to the user. See also `01_google_ads_logic.md` B5 — fix there is to keep `0` as `0` and reserve `NULL` for genuine absence.

---

## Partial-failure handling — robust

`sync.py::_run_phase` pattern:

```python
try:
    count = fn()
    phases[name] = {"count": count, "status": "ok"}
except Exception as e:
    phases[name] = {"count": 0, "status": "error", "error": str(e)[:500]}
    # continues to next phase
```

Phase-level isolation works. Dependency tracking in `sync.py:1016-1028` prevents phase N+1 from running if phase N failed critically. Every `sync_*` method wraps in `try/except` + `db.rollback()`.

**What's missing:** no test actually exercises this. See `06_tests_qa.md` Zone 7.

## Idempotency — upsert by natural key

| Resource | Natural key |
|----------|-------------|
| Campaign | `(client_id, google_campaign_id)` — UQ constraint |
| AdGroup | `(campaign_id, google_ad_group_id)` |
| Keyword | `(ad_group_id, google_keyword_id)` |
| SearchTerm | `(campaign_id, text, date_from, date_to)` |
| MetricDaily | `(campaign_id, date)` — UQ constraint |
| KeywordDaily | `(keyword_id, date)` — UQ constraint |
| **NegativeKeyword** | **No DB-level UNIQUE constraint** ⚠️ |

Mid-sync crash + restart → upserts are safe (matching natural key updates in-place, new rows inserted). Except for negative keywords — the dedup is application-level only. Add a DB-level unique constraint; dedupe existing duplicates first.

---

## Reconciliation — missing entirely

**No drift detection. No post-sync verification. No row-count reconciliation.**

Sync reports "200 keywords synced" but doesn't check "does Google Ads UI show 200, 198, or 210?" If transient API errors drop 2% of results mid-page, the user never knows. Three mechanisms that belong in v1.1:

1. **Post-sync count check** — query API for `COUNT(1)` per resource, compare to synced count. If variance > 5%, flag `drift_detected=True` in `SyncCoverage`.
2. **Checksum fingerprints** — hash `(count, sum(cost_micros))` per resource per sync. Compare across runs to catch silent partial writes.
3. **Variance report UI** — surface drift to the user in the sync modal.

Today's `/sync/debug/keywords` endpoint (`sync.py:566`) is diagnostic-only, not continuous.

---

## Date / timezone findings

### UTC storage — OK
`datetime.now(timezone.utc)` consistently used across models (`sync_log.py:27` et al.). `UTCJsonResponse` in `main.py:19-32` ISO-stringifies with `Z` suffix.

### Account timezone — **missing**
Google Ads metrics are anchored to the **account timezone**, not UTC. A Polish account (`Europe/Warsaw`, UTC+1/+2) reporting "2026-04-18 spend = $100" actually covers 2026-04-17 22:00 UTC → 2026-04-18 22:00 UTC.

- `Client` schema has a `timezone` field (`schemas/client.py:189`).
- **It is never persisted to the DB.** `clients` table has no `account_timezone` column.
- Agencies managing multi-timezone portfolios will see misaligned daily breakdowns; trend charts off by a day depending on account.

**Fix:** `ALTER TABLE clients ADD COLUMN account_timezone VARCHAR(50)`; sync it from `customer.time_zone`; consume it in analytics aggregations via `zoneinfo.ZoneInfo`.

### Today's data is not flagged provisional
Google keeps finalising the last ~3 days of metrics. User sees "Yesterday: 50 conversions," refreshes 2 hours later, sees "Yesterday: 52 conversions." Looks like a bug.

`sync.py:93-94` correctly excludes today (`date_to = today - 1`), but does **not** tag yesterday / last 3 days as `is_provisional = True`. Add the flag; render a subtle indicator in the UI.

---

## Retry / backoff — missing

Zero client-side retry logic. Reliance on the Google Ads SDK defaults (3 attempts, 1s base delay).

Risks:
- Rate-limit during peak → 3 attempts fail → sync phase drops.
- Quota exceeded → SDK fails immediately, no exponential backoff.
- Transient 503 → may not retry.

**Fix:** wrap high-volume queries in `tenacity` with exponential backoff (1s → 60s, 5 attempts, jitter) on quota / 429 / 503 / timeout. ~8 hours.

---

## Rate limiting — missing

No client-side throttle. All phases fire API calls as fast as they can. Daily Google Ads quota is 6M requests/day for standard developers; GAH with 5–10 clients syncing concurrently could burn through it unannounced.

**Fix:** simple token bucket in `google_ads.py` — track requests/minute per sync session; soft-warn at 80% quota. ~4 hours.

---

## Sync log completeness — good

`SyncLog` captures: `client_id`, `status` (running / success / partial / failed), `days`, per-phase breakdown JSON `{phase: {count, status, error}}`, `total_synced`, `total_errors`, `error_message`, `started_at`, `finished_at`.

Per-phase granularity is present and correct. What's missing: pre-vs-post comparison (reconciliation) — see above.

## Scheduled sync — asyncio-based, session-bound

`ScheduledSyncConfig` model stores per-client `enabled`, `interval_hours`, `last_run_at`, `next_run_at`. Endpoint trio `GET/POST/DELETE /sync/schedule`. Scheduler runs as an asyncio task inside the uvicorn process.

**Caveat:** if the desktop app closes, scheduling stops. On restart the scheduler reinitialises. Acceptable for desktop MVP where the user controls the lifecycle; **not** suitable for a cloud deployment (would need Celery, APScheduler with persistent job store, or a separate worker process).

---

## Mock data — realistic

`backend/app/seed.py`:

| Metric | Distribution | Real-world | Match |
|--------|--------------|------------|-------|
| CTR | 0.5–10% | 0.5–5% typical | ✅ close |
| CVR | 0–15% | 1–10% | ✅ |
| CPA | $100–800 | $50–500 | ✅ |
| QS | peak at 7–8 (weighted) | median 7–8 | ✅ excellent |
| Serving status | ELIGIBLE 60 / LOW_VOLUME 15 / BELOW_FIRST_PAGE_BID 15 / RARELY_SERVED 10 | close to real | ✅ |
| IS | 10–95% | 30–85% typical | ✅ |
| Seasonality | Black Friday ×2.5, Q1 ×0.7, Summer ×0.8 | ✅ excellent |

**Gaps:**
- One `LEARNING` campaign only — no variety of bidding-strategy states.
- No `TOTAL` budget campaigns (end-date-bounded).
- Minimal portfolio-strategy variation.

---

## MCC / multi-account — supported

- `MccLink` model maps manager account ↔ client accounts.
- `sync_mcc_exclusion_lists` queries manager account for shared lists (`ownership_level='mcc'`).
- `MCCService.get_overview()` / `get_billing_status()` / `get_mcc_shared_lists()` all present.

Viable for 2–10 clients per user without architectural changes.

---

## API version + SDK hygiene — exemplary

- `requirements.txt:8` → `google-ads==29.1.0` (pinned).
- `GoogleAdsClient.load_from_dict(config, version="v23")` — explicit.
- API v23 is the current production version as of April 2026.

ADR-018 / ADR-019 compliance is textbook.

---

## Top 10 data-integrity fixes

| # | Fix | Severity | Effort | Hours |
|---|-----|----------|--------|-------|
| 1 | Post-sync reconciliation check (API count vs DB count, flag drift) | **CRITICAL** | M | 12 |
| 2 | Mark last-3-days metrics as `is_provisional = True` | **CRITICAL** | S | 5 |
| 3 | Exponential backoff + retry on 429 / 503 / timeout via `tenacity` | **CRITICAL** | M | 8 |
| 4 | Persist `account_timezone` on `clients` + use in analytics aggregations | High | M | 7 |
| 5 | Client-side rate-limiter (token bucket, warn at 80% quota) | High | S | 4 |
| 6 | Document / fix Impression Share 30d window (either store historical snapshots keyed by `(campaign_id, date)`, or label the 30d-aggregate behaviour in `sync_config.py`) | Medium | S–M | 5 |
| 7 | DB-level UNIQUE constraint on `negative_keywords` — dedupe first | Medium | S | 3 |
| 8 | `SyncCoverage.variance_pct` / `drift_detected` fields + variance tracking per sync | Medium | M | 8 |
| 9 | Offline conversions sync (model stub exists; wire it up) | Low–Medium | L | 16 |
| 10 | "Data freshness & integrity" dashboard — last sync, data range, variance, provisional flag | Low | M | 13 |
| **Total** | | | | **~81 h** |

---

## Architecture strengths worth keeping

- Per-phase transaction safety (`try` / `except` / `db.rollback`).
- Upsert idempotency via natural keys.
- Phase dependency tracking — fails gracefully on upstream errors.
- SDK + API version discipline.
- Realistic mock data that models seasonality and status distributions.
- MCC-aware sync paths (separate for manager vs client).

---

## Pre-release checklist (recommended)

- [ ] #2 provisional tagging — user education is essential; no tag means "why did yesterday's number just change?"
- [ ] #3 retry / backoff — single most impactful reliability fix.
- [ ] #1 reconciliation — drift detection is table stakes for any tool users trust with budget decisions.
- [ ] #6 label IS window — manage expectations; prevents wrong-conclusions from 30d-only data.
- [ ] Load-test #4 and #5 with 10+ clients and multiple timezones before shipping.

---

## Bottom line

Sync is well-engineered at the per-call level. It's not yet trustworthy at the **per-account level** because there's no reconciliation feedback loop. Close #1, #2, #3 and the product moves from "seems to work" to "you can show a client this dashboard and answer their questions without hedging."
