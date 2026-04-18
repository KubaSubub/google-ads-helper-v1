# PHASE 1 — Google Ads Logic Audit

**Auditor perspective:** World-class Google Ads specialist (10+ years, 7-figure spend accounts, in-house + agency).
**Date:** 2026-04-18
**Verdict:** Functional MVP. NOT production-ready for a serious PPC operator. A real account manager would hit the gaps within a week.

**Scorecard**

| Area | Score | Comment |
|------|-------|---------|
| Data model | 6/10 | Solid micros + Float conversions + extended IS tracking, but CTR unit bug, PMax/Shopping bolted on, attribution field ignored |
| Sync coverage | 7/10 | Broad GAQL coverage; missing bid simulator, asset-level PMax, offline conversion lag |
| Recommendations engine | 5/10 | 7 shallow rules; no IS root cause, no QS component breakdown, no learning-period safety |
| Agent / LLM | 4/10 | Generic reporting prompts; ignores half the stored data |
| UX workflows | 4/10 | Segmentation good; no bulk add, no match-type suggestion, no heatmaps |
| Playbook | 6/10 | Covers MVP flows; missing PMax, attribution, learning period, seasonality |

---

## A. What's good (and why it matters)

1. **Conversions stored as `Float`** — `keyword.py:27`, `metric_daily.py:19`, `search_term.py:26`. Google Ads returns fractional conversions (1.5 attributed installs from a data-driven model). Integer storage would silently truncate — correct choice.
2. **Micros at storage layer** — `cost_micros`, `conversion_value_micros`, `bid_micros`, `cpa_micros`, `avg_cpc_micros` as `BigInteger`. Matches Google's native format, avoids float money bugs. This is load-bearing and correctly enforced across models.
3. **Extended conversion fields present** — `all_conversions`, `cross_device_conversions`, `conversion_value_per_cost`, `value_per_conversion`. The app at least captured the data; many tools stop at `conversions` alone.
4. **Full Impression Share set** — `search_impression_share`, `search_top_impression_share`, `search_abs_top_impression_share`, `budget_lost_impression_share`, `rank_lost_impression_share` on both campaign and keyword levels. This is the single most actionable set of signals in Search — the app syncs it.
5. **Quality Score components stored** — `historical_quality_score`, `historical_creative_quality_score`, `historical_landing_page_quality_score`, `historical_search_predicted_ctr` (`keyword.py:43-47`). QS root-causing needs all four.
6. **Search-term segmentation** — `search_terms_service.py:25-82` classifies terms into `IRRELEVANT / HIGH_PERFORMER / WASTE / OTHER`. The right mental model for daily SKAG-style hygiene work.
7. **Auction Insights per-competitor daily** — `auction_insight.py` tracks `impression_share`, `overlap_rate`, `position_above_rate`, `outranking_share` per competitor, per day. Lets you see who's eating your lunch.
8. **Separate Search vs PMax search-term sync** — `google_ads.py:3365` vs `google_ads.py:3488`. PMax search terms MUST come via `campaign_search_term_view` without `segments.keyword.*` (which nukes all PMax rows). The code explicitly documents this — a landmine the code avoids.
9. **Write-safety layer** — `demo_guard.py`, `write_safety.py`, `action_executor.py`, `google_ads_mutations.py`. Every mutation routes through a circuit breaker with validation. This is rare and correct.
10. **Conversion Value Rules modeled** — `conversion_value_rule.py`. Recognition that conversion value varies by audience/device/geo is mature.
11. **Campaign role classification** — `campaign_roles.py` distinguishes BRAND / GENERIC / COMPETITOR / DSA / PMAX / SHOPPING / VIDEO / OTHER. This is the correct unit of analysis for thresholds (a 1% CTR is a disaster on brand, normal on generic).

---

## B. What's wrong or misleading

### B1. CTR unit inconsistency — 100× error in comparisons (CRITICAL)

- **Where:** `keyword.py:29`, `metric_daily.py:18`, `ad.py:38`, `search_term.py:28`, `placement.py:26` — all store CTR as percentage (`5.0` means `5%`).
- **Problem:** Google Ads API returns CTR as a fraction (`0.05` means `5%`). The sync pipeline multiplies by 100 inconsistently — `google_ads.py:1071`, `:3457`, `:3579` apply `* 100`, others don't. Some downstream rules compare to thresholds expecting decimals.
- **Symptom:** A rule like `"r11_max_ctr": 0.5` (meaning "alert if CTR under 0.5%") compares against `keyword.ctr = 5.0` (5%). Condition is always false — rule silently never fires.
- **Fix effort:** Medium. Canonicalize as decimal in DB, drop the `*100` sprinkling, update any threshold config and UI `toFixed(2)` display calls.

### B2. CPA calculation — undefined behaviour on fractional conversions

- **Where:** `google_ads.py:2335` — `cpa_micros = int(cost_micros / conversions) if conversions > 0 else 0`.
- **Problem:** The `> 0` guard allows `conversions = 0.1` through. A keyword with $10 spend and 0.1 conversions reports CPA = $100 — mathematically correct, operationally meaningless (no conversion occurred). Then any recommendation that pauses "keywords with CPA > 2× target" fires on noise.
- **Fix:** Require `conversions >= 1` for CPA display, or surface both `raw_cpa` and `confidence = conversions / 10`.

### B3. ROAS — conversion_value = 0 means two different things

- **Where:** `analytics_service.py:98` — `roas = (total_conv_value_usd / total_spend_usd) if total_spend_usd else 0`.
- **Problem:** An account without conversion values configured returns zero value for every conversion. The app reports `ROAS = 0`, triggers "low ROAS" alerts, and pushes the user to reallocate budget away from campaigns that are actually converting. This is the #1 way automated tools damage accounts.
- **Fix:** Distinguish "no value tracked" from "value tracked = 0". Gate ROAS recommendations on `conversion_value_present = True` at the conversion action level.

### B4. Quality Score double model — 1–10 and 1–3 are mixed

- **Where:** `google_ads.py:52-59` maps API enum to `int 1-10`, but `historical_*_quality_score` uses `BELOW_AVERAGE=1 / AVERAGE=2 / ABOVE_AVERAGE=3`.
- **Problem:** Downstream rules like `r8_max_qs: 5` only work on the 1–10 field. If the 1–10 field is null (API omits QS for low-impression keywords), the rule falls back to the 1–3 component and every `< 5` check passes.
- **Fix:** Two fields, two rule sets. Never compare across scales.

### B5. Impression Share null handling — `None` vs `0` conflated

- **Where:** `google_ads.py::_safe_is()` returns `None` when value is zero.
- **Problem:** `IS = 0%` is a legitimate, highly actionable signal ("you got zero impressions in that segment"). Storing it as `NULL` erases the distinction from "no data available yet."
- **Fix:** Keep 0 as 0; use `NULL` only when the field is genuinely absent in the API response.

### B6. Attribution model stored but never used

- **Where:** `conversion_action.py:22` stores `attribution_model` (LAST_CLICK / DATA_DRIVEN / POSITION_BASED / TIME_DECAY / LINEAR). Grep shows zero usage in recommendations or analytics.
- **Problem:** For a last-click account, brand campaigns look like low-ROAS spend because they don't get credit for assists. Smart-bidding performance comparisons are invalid across attribution models. Without attribution context, every keyword recommendation is approximate at best.

### B7. Budget type field ignored

- **Where:** `campaign.py:23` — `budget_type` stored (`DAILY` vs `TOTAL`). Not used in pacing.
- **Problem:** Total-budget campaigns (common in retail for seasonal pushes) burn through differently than daily — pacing math that assumes daily gives wrong "you'll overspend today" alerts.

### B8. CTR threshold in recommendations fails on all accounts

- **Where:** `recommendations.py:166-168` — rule config expects `max_ctr: 0.5` (percent) but applies it to `keyword.ctr` which is already in percent.
- **Symptom:** User sees no CTR-based recommendations. Or (worse) gets the wrong ones silently ignored and other rules fire instead.

### B9. Search-term segmentation thresholds don't scale

- **Where:** `search_terms_service.py:36-41` — HIGH_PERFORMER = `conversions >= 3 AND CVR > campaign avg`.
- **Problem:** 3 is a hardcoded absolute. A $20/day account might accumulate 3 conversions on a single keyword over a month; a $5k/day account sees 3 conversions on noise. Good segmentation uses a **relative** threshold: `conversions >= max(3, 0.1 × campaign median per-keyword convs)` or percentile-based.

### B10. PMax treated as "search with a twist"

- **Where:** PMax search terms are synced correctly (B1), but recommendations R1–R7 (built for Search keyword operations) run against PMax rows because nothing branches on `campaign.type == PERFORMANCE_MAX`.
- **Problem:** "Pause this PMax search term" is nonsensical — PMax has no keyword-level bid/pause. The right PMax levers are: asset group signals, audience signals, campaign-level tCPA/tROAS, asset rotation, product group structure. None of those are surfaced.

### B11. IS loss without bid/QS/competitor context

- **Where:** Recommendations in `recommendations.py` see `budget_lost_is` and `rank_lost_is` separately but never cross-reference with first-page bid estimate, QS, or Auction Insights competitor movement.
- **Problem:** "You lost 30% IS" is noise; "you lost 30% IS, 22% was rank-lost, your QS is 4, first-page bid is $3.20, you're bidding $2.40, competitor `acme.com` gained 12% share in 7 days" is actionable. The data is all there, the synthesis isn't.

### B12. Negative-keyword conflict detection absent

- **Where:** `negative_keyword.py` model exists. No service checks if a negative (phrase `"cheap shoes"`) overlaps with a positive (exact `"cheap running shoes"`) in the same campaign.
- **Problem:** Every mature account accumulates conflicts over years. They silently block revenue and they're invisible without this check. Google Ads UI has a report for this — the app should too.

### B13. `MetricSegmented` schema-level flaw

- **Where:** `metric_segmented.py` — all seven dimension columns nullable, single composite UNIQUE constraint.
- **Problem:** NULL ≠ NULL in SQL UNIQUE logic. Multiple rows with `(campaign_id=1, date=2026-04-18, device=NULL, …)` can exist. The code in `database.py:215-227` adds a functional `COALESCE(...)` index as a workaround — that's duct tape. Correct modelling: one table per dimension, or `COALESCE` baked into ingestion with a sentinel value, enforced NOT NULL.

### B14. No learning-period awareness for smart bidding

- **Where:** `campaign.primary_status` is stored. Nothing acts on `LEARNING`, `LIMITED_BY_BUDGET`, `PAUSE_ON_LOW_QUALITY`.
- **Problem:** A tCPA campaign in LEARNING that gets its target CPA manually tweaked resets learning and burns 7–14 days of budget. The app will happily recommend target adjustments against learning campaigns.

---

## C. What's missing (critical gaps for real PPC work)

Ordered within each tier by daily value to an account manager.

### Tier 1 — core workflows you'll miss within days

1. **Search-term → keyword bulk add with match-type recommendation.** Segmentation exists; the action doesn't. A real operator adds 20–80 terms at once, and the tool should suggest match type based on volume + CTR (high-volume low-intent → phrase, low-volume high-intent → exact).
2. **Budget pacing view.** "Today's daily budget $100, spent $45 at 9am, projected $360, will overspend by $100 — recommend: cap bids 10%." Needs hourly accumulation against remaining budget. All data is already synced via `metric_daily`; no new API calls needed.
3. **QS component breakdown + fix.** "QS=4 because LP experience = Below Average on 3 keywords — test faster LP / fix CLS" vs "QS=4 because expected CTR = Below Average — test new RSA headline variants." Different fixes for different root causes.
4. **Device performance comparison.** Mobile CPA vs desktop CPA vs tablet CPA is a 5-minute analysis that should be a single screen. `metric_segmented` has the data.
5. **Location (city/region) performance heatmap.** Any national account has 80/20 city distribution; without this, the user doesn't know which cities to scale or exclude.
6. **Audience segments + overlap.** Which audiences convert? Which overlap so heavily they're redundant? No Google product gives this — custom tools are the whole point.
7. **N-gram waste analysis, fully integrated.** `scripts/d3_ngram_audit.py` exists but isn't wired to the UI. The single biggest daily time saver across search-term review.
8. **Learning-period status indicator + "don't touch" guardrail.** Block target-CPA recommendations while a campaign is in LEARNING.
9. **First-page / top-of-page / first-position bid estimates.** The Google Ads API exposes these and the app ignores them. They're the only objective way to recommend a bid change.
10. **Bid simulator data.** `keyword_plan_ad_group_keyword_forecast` / `bid_landscape` — "bid $2 → 150 clicks, bid $2.50 → 210 clicks." The entire bid-change recommendation UI is weak without this.

### Tier 2 — expected by week 2

11. **Negative-keyword conflict detection.**
12. **Keyword cannibalisation detection** (two exact matches in same ad group that should be one).
13. **Auction Insights trend** (is competitor X's outranking share rising over 7/14/30d?).
14. **Change-history correlation** ("CTR dropped 20% yesterday — here are the 4 changes made to this campaign in the prior 48h").
15. **Attribution model comparison** (LAST_CLICK vs DATA_DRIVEN side-by-side).
16. **Campaign-role-aware thresholds** (brand: CTR 3–8% normal; generic: CTR 0.5–2% normal — one threshold set per role).
17. **RSA asset-level performance** (which headlines/descriptions have `LEARNING` / `GOOD` / `LOW` rating).
18. **PMax asset-group signal analysis** (which audience signals are active, which assets are rotating in which channels).
19. **Landing page diagnostics** (load time, bounce rate, final_url vs final_mobile_url, tracking template status).
20. **Shopping product-group performance + feed quality** (missing images, category errors, disapprovals).

### Tier 3 — operator polish

21. Hourly dayparting heatmap + ad-schedule modifier recommendations.
22. Seasonality / YoY comparison.
23. Offline-conversion import lag tracking.
24. Experiments / drafts support.
25. Google-recommendation auto-apply risk analysis (which auto-applied recs backfired).
26. Customer Match / Similar Audiences performance.
27. Conversion-lag visualization (how many conversions are still going to arrive for last 7 days' traffic).
28. Tracking template / UTM parameter health check.

---

## D. Agent / LLM prompts — do they ask the right questions?

**Location:** `backend/app/services/agent_service.py` — `SYSTEM_PROMPT` (line 67), `WEEKLY_PROMPT` (100), `HEALTH_PROMPT` (119), `MONTHLY_PROMPT` (141).

**What they ask:** KPI trends, top/bottom campaigns, anomalies, wasted spend, QS distribution, sync freshness, budget pacing.

**What they don't ask — a real PPC pro would never skip these:**

1. **IS root cause.** "Where did we lose impression share — budget or rank? What's the first-page bid estimate vs current bid?" The prompt reports `rank_lost_is` and stops.
2. **QS components.** "Which keywords have Below-Average expected CTR vs Below-Average LP experience?" The prompt just says "low QS."
3. **Attribution model context.** "Are we on last-click? If yes, brand CPA is probably overstated." Prompt ignores `attribution_model`.
4. **Learning-period status.** "Which smart-bidding campaigns are in LEARNING? Don't recommend bid changes on those." Prompt ignores `primary_status`.
5. **Device / geo / audience anomalies.** "Mobile CPA is 3× desktop — recommend device bid adjustment." Prompt only looks at aggregates.
6. **Negative conflicts.** "Are any phrase negatives blocking exact positives?" Prompt doesn't even know negatives exist.
7. **Auction Insights trend.** "Any competitor gaining >5% IS in last 7 days?" Prompt only reads current snapshot.
8. **N-gram waste patterns.** "What 2-gram / 3-gram patterns dominate waste this week?" Prompt does per-term review, not pattern review.
9. **Search-term match-type recommendation.** "For each HIGH_PERFORMER, recommend exact vs phrase based on volume/CTR." Prompt surfaces segments, not actions.
10. **Campaign role branching.** "This is a brand campaign — CTR of 4% is normal, don't flag." Prompt uses one threshold set.

**Verdict:** The prompts are **reporters, not diagnosticians**. They restate data to the LLM. A useful PPC agent prompts the LLM with **hypotheses and diagnostic questions**, not summaries. The app has ~70% of the data needed for world-class agent behaviour and uses ~30%.

---

## E. Knowledge base / playbook

**File:** `google_ads_optimization_playbook.md`.

**Covered well:** daily hygiene (spend, anomalies, search terms, pause poor performers), bid adjustments, match-type logic (SKAG is dead → STAG), budget reallocation with ROAS rules, audience/device/location segmentation mentions, negative-keyword list approach.

**Missing or naive:**

- **Learning-period protocol.** No "don't manually adjust tCPA in first 14 days / after 30% budget change" rule.
- **Attribution strategy.** No last-click vs data-driven discussion; no "audit attribution before trusting ROAS" step.
- **Negative-keyword conflict audit.** Not mentioned.
- **IS root-cause decision tree.** Budget-lost → budget action; rank-lost → bid/QS action. Absent.
- **PMax workflow.** The playbook is Search-only. PMax asset groups, signals, channel attribution, brand exclusions — nothing.
- **Shopping feed optimisation.** Feed diagnostics, Merchant Center integration, title/image/price rules — absent.
- **Seasonality adjustments.** Google's Seasonality Adjustment tool, bid seasonality, budget planning across YoY patterns — missing.
- **Landing-page strategy.** One-LP-per-ad-group rule, message match, page speed targets — absent.
- **Bid simulator usage.** "Before changing bid, check simulator forecast" — missing.
- **Thresholds don't vary by campaign role.** One CTR/CPA/ROAS rule set for brand, generic, competitor, DSA, shopping. Wrong.
- **Ad-copy workflow post-ETA sunset.** RSA asset-level ratings, pinning strategy, "LOW" asset swap-out — not in playbook.

---

## F. Priority recommendations

Ordered by impact on a real account manager's daily work. Effort: S ≤ 1 day, M ≤ 1 week, L > 1 week.

### P0 — fix before anyone trusts the numbers

1. **Fix CTR unit storage.** One canonical representation (decimal `0.05`). Migrate data, strip the `*100` sprinkling, update UI. **Effort: M.** **Impact:** every CTR threshold and comparison is currently wrong or fragile.
2. **Fix CPA / ROAS degenerate cases.** `conversions < 1` → no CPA; `conversion_value_present == False` → suppress ROAS-based recommendations. **Effort: S.** **Impact:** eliminates false alerts that push users toward account-damaging changes.
3. **Guard learning-period campaigns from bid/target recommendations.** Respect `primary_status == LEARNING`. **Effort: S.** **Impact:** prevents smart-bidding resets and the 7–14 days of wasted budget that follow.
4. **Differentiate NULL vs 0 in Impression Share.** `_safe_is` fix. **Effort: S.** **Impact:** IS analysis becomes trustworthy.

### P1 — give the user workflows they can't do without

5. **Search-term → keyword bulk-add with match-type recommendation.** New service method (`search_terms_service.recommend_match_type`), new endpoint, bulk-action UI on Search Terms tab. **Effort: M.** **Impact:** single biggest daily workflow.
6. **IS root cause + first-page-bid context.** Sync `keyword_view.bid_simulator`, surface "Lost IS = X% (budget Y / rank Z), first-page bid Y1, your bid Y2, QS Q." **Effort: M.** **Impact:** turns IS from metric into decision.
7. **QS component breakdown + targeted recommendation.** Branch rules on weakest component (`historical_search_predicted_ctr` vs `historical_creative_quality_score` vs `historical_landing_page_quality_score`). **Effort: M.**
8. **Device / geo / audience anomaly surfaces.** Three pages using `metric_segmented`. **Effort: M.** **Impact:** device bid modifiers are the fastest-to-implement ROAS lift on most accounts.
9. **N-gram waste analysis in UI.** Wire existing `scripts/d3_ngram_audit.py` into a tab; bulk-negative action. **Effort: M.** **Impact:** hours per week saved on search-term hygiene.
10. **Negative-keyword conflict detection.** Static analysis across positives/negatives by match type. **Effort: M.**

### P2 — advanced diagnostics the market expects

11. **Auction Insights trend module.** 7/14/30d per-competitor IS deltas, outranking-share rate of change. **Effort: M.**
12. **Campaign-role-aware thresholds.** Rule config keyed on `campaign_role_final`. **Effort: S once data model hardened.**
13. **Change-history correlation.** Join `change_event` to `metric_daily` anomalies. **Effort: M.**
14. **Attribution model comparison.** Surface last-click vs data-driven on every keyword/campaign (requires pulling alternate-attribution data from API). **Effort: L.**
15. **Keyword cannibalisation detection.** Pairwise fuzzy match on exact keywords within the same ad group / cross-campaign. **Effort: M.**
16. **RSA asset-level performance + pinning review.** Needs asset-level sync (`ad_group_ad_asset_view`). **Effort: M.**
17. **PMax asset-group signal + channel attribution panel.** **Effort: L.**

### P3 — LLM agent upgrade (highest ROI relative to effort)

18. **Rewrite `agent_service.py` prompts as diagnostic, not reporter.** Feed the LLM structured hypothesis context: `{brand_vs_nonbrand, attribution_model, learning_period_campaigns, negative_conflicts, ngram_waste_patterns, device_anomalies, is_root_cause_summary}`. **Effort: M.** **Impact:** quality of every agent response jumps; uses data already in DB.
19. **Gate agent recommendations on confidence + volume.** Expose `confidence_score` / `risk_score` in UI (they exist at `recommendations.py:142-143`, unused in frontend). **Effort: S.**
20. **Separate prompts per campaign role.** Brand campaigns have different reasonable thresholds, so the agent needs different context. **Effort: S.**

### P4 — playbook rewrite

21. **Split playbook by campaign role** (brand / generic / competitor / DSA / PMax / shopping / video). Different thresholds and workflows for each.
22. **Add learning-period protocol, attribution strategy, IS decision tree, PMax workflow, feed optimisation, seasonality, landing-page strategy.**
23. **Replace absolute thresholds with relative ones** where possible (percentile / campaign-median based).

---

## Root cause — why this app got where it is

- **Search-first MVP.** PMax and Shopping were bolted on; the recommendation engine and agent prompts still assume a keyword world.
- **Data collection outran analysis.** `attribution_model`, `primary_status`, `budget_type`, `confidence_score` are all synced but unused.
- **Thresholds are absolute, not role-aware.** Every rule treats brand and generic identically — the first thing a PPC specialist would fix.
- **Agent prompts restate; they don't diagnose.** The LLM is the most expensive part of the stack; the prompts use ~30% of its potential.
- **No campaign-type branching anywhere.** Search, PMax, Shopping, Video all flow through the same rules and the same UI.

A real account manager would outgrow this app in under a week of daily use. The foundation is good enough that closing the P0 + P1 list would make it genuinely useful; without that, it's a prettier Google Ads UI.
