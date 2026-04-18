# PHASE 4 — UX / Product Audit

**Perspective:** senior product designer + working PPC practitioner.
**Verdict:** feature-rich, well-architected, but UX debt blocks common daily workflows. Journey-friction score across 5 core tasks: **2.4 / 5** (usable but rough). Readiness for paying external users today: ~3.2 / 5; realistic after P0 fixes: 4 / 5.

---

## Journey friction — 5 core tasks a PPC operator does daily

| # | Journey | Steps | Friction | Score |
|---|---------|-------|----------|-------|
| a | Review yesterday's performance | MCC → Dashboard → KPIs | No "yesterday" preset, no side-by-side vs prior week, anomalies on separate page | 3/5 |
| b | Add 30 negative keywords | Search Terms → select rows → bulk action | Bulk bar exists; **no preview, no undo, no "select by segment" shortcut** | 2/5 |
| c | Promote high-performers → keywords | Search Terms → "Add keyword" → toast | **Flow breaks mid-way** — toast says "Go to Recommendations" instead of opening a modal; no match-type suggestion; no ad-group picker | 2/5 |
| d | Audit QS | Keywords → QS tab | Shows data, **no component breakdown, no "fix this" action** per keyword | 3/5 |
| e | React to anomaly alert | Alerts → detail → navigate to entity | **No "jump to affected entity" button**, no acknowledge state → alert fatigue | 2/5 |

Three of five journeys score ≤ 2. The product has the data and the logic; it lacks the connective UI that turns insight into action.

---

## Strengths worth keeping

- **Depth of analysis surfaces** — 34 rule types in recommendations v2.1, cost-weighted health scoring, 20+ audit-centre sections.
- **Segmentation model is the right mental model** — HIGH_PERFORMER / WASTE / IRRELEVANT / OTHER matches how a PPC operator actually thinks.
- **Sidebar grouping is logical** — OVERVIEW / CAMPAIGN DATA / ACTIONS / MONITORING / AI / ANALYSIS. Mental map reads cleanly.
- **Global date picker + filter context** genuinely cross-cutting (unusual for MVPs).
- **Keyboard shortcut hints component exists** — signals a team that thinks about power users.
- **`TrendExplorer` reusable everywhere** — consistent charting experience.
- **EmptyState component consistently used** for "no data" cases.

---

## Weaknesses by category

### Onboarding
- No credential-setup explainer ("Where do I find my developer token?" → empty).
- First-sync completion is silent; no "success! here's what to do next" state.
- No first-run tour / checklist. User lands on MCC Overview and stares.
- Settings for Obsidian vault path not prompted during setup.

### Empty / loading / error states
- Tables have no "data last synced at" timestamp → users act on stale metrics.
- No offline-mode banner; app silently fails when network drops.
- Loading is spinner-only; no skeleton screens (perceived performance suffers).
- Error states don't distinguish "no data" from "fetch failed."
- **`Recommendations.jsx` is marked `hidden: true` in `navConfig.js` line 57** — a full feature is invisible from the sidebar. Either un-hide or delete.

### Bulk actions
- **No undo on bulk negatives** — permanent changes with no 24h rollback. Every competitor in this space (Optmyzr, Adalysis) has this.
- No preview modal before applying ("You're about to exclude 47 terms — review").
- **Search-term → keyword flow is broken** (`SearchTerms.jsx:512`): clicking "Add keyword" shows a toast telling the user to go to a different page. That's not a flow, it's a dead end.
- No bulk bid adjust, no bulk pause, no bulk pause-with-reason (audit trail).
- Multi-page selection loses state on pagination.

### Navigation
- No breadcrumbs — user deep in Audit Center → Wasted Spend can't see the path.
- No back button after drilling into a campaign.
- Deep links lose filter state.
- Settings inaccessible from MCC Overview page.
- 27 sidebar items; ANALYSIS group alone has 7 — needs sub-grouping.

### Visual polish
- Currency units inconsistent (some cells show `zł`, others show bare numbers).
- Number formatting inconsistent (`1000000` vs `1,000,000` vs `1.2M`).
- Date formats mix `DD.MM` and `DD/MM/YYYY`.
- Metric tooltips missing on first encounter — a new user sees "CVR" with no hint what it means.
- Row hover uses inline styles instead of CSS class (design-system drift).
- `SearchTerms.jsx` uses ~500 lines of inline styles instead of tokens — breaks `MEMORY.md` v2 design-system rules.

### Missing workflows (ranked)
1. Bulk keyword import with match-type auto-suggest (CSV upload) — **every competitor has it**.
2. Search-term → keyword modal with ad-group + match-type suggestion (the broken flow above, completed).
3. N-gram bulk-add as negatives (data is in Audit Center; action is not).
4. Device / geo bid-modifier recommendations with one-click apply.
5. Quality Score component breakdown + targeted fix recommendation per keyword.
6. Budget pacing alerts on the Alerts page (not just a gauge on Dashboard).
7. Two-way Obsidian sync (core VISION.md feature, not yet built — correctly scoped as v2).
8. Alert acknowledge + snooze (prevents alert fatigue).
9. Bulk pause with reason field (audit compliance for agencies).
10. Negative-keyword list cloning across clients.

---

## Competitor comparison (what we're measured against)

### Optmyzr (≈ $500 / mo)
| Feature | Optmyzr | GAH | Gap |
|---------|---------|-----|-----|
| Undo / 24h rollback | ✅ | ❌ | Critical trust gap |
| Bulk CSV keyword import + match-type detection | ✅ | ❌ | Core daily workflow |
| Alert snooze + severity grouping | ✅ | ❌ | Alert fatigue today |
| Recommendation confidence + reasoning | ✅ | Stored in DB, not shown in UI | Data exists, UI doesn't surface it |

### Adalysis (≈ $150 / mo)
| Feature | Adalysis | GAH | Gap |
|---------|----------|-----|-----|
| Custom dashboard drag-and-drop | ✅ | ❌ | Fixed layouts only |
| Visual rule builder UI | ✅ | Backend only | Power users can't self-serve |
| Change scheduling ("apply Monday 9am") | ✅ | ❌ | Changes are always immediate |
| Before/after change audit view | ✅ | Logs exist; UI doesn't show diffs | Compliance gap for teams |

### Opteo (≈ $250 / mo)
| Feature | Opteo | GAH | Gap |
|---------|-------|-----|-----|
| One-click apply from Google Ads UI | ✅ (native extension) | ❌ | GAH is a separate app — extra context-switch |
| Real-time sync | ✅ | 5–30 min behind | Expected for local-desktop, but worth acknowledging |
| Account-level % impact framing | ✅ | Raw counts only | "47 low-QS keywords" vs "12% of your spend at risk" |

---

## Priority recommendations

### P0 — blocks daily workflows (1 week)
1. **Fix search-term → keyword flow.** Replace the "go to Recommendations" toast with a modal that: picks ad group, suggests match type based on volume/CTR, lets user add-and-return in one step. **(S)**
2. **Show "last synced at" on every data table.** Kill the "am I looking at stale data?" anxiety. **(S)**
3. **Add undo button / 24h revert UX on bulk actions.** Backend has `revert_within_hours`; frontend doesn't expose it. **(S–M)**
4. **Un-hide `Recommendations` page** (or rename and promote). Currently `hidden: true` in `navConfig.js:57`. **(S)**
5. **Add breadcrumbs on 3+ level deep pages** (Audit Center, Analysis). **(M)**

### P1 — meaningful friction fixes (2–3 weeks)
6. Bulk keyword import (CSV upload + match-type heuristic). **(M)**
7. Alert acknowledge + 7-day snooze. **(M)**
8. QS component breakdown + targeted fix recommendation per keyword. **(M)**
9. N-gram bulk-add-as-negative action (data already exists in Audit Center). **(S)**
10. Device / geo bid-modifier recommendation section + one-click apply. **(L)**
11. Bulk pause with reason field. **(S)**
12. Expose `confidence_score` / `risk_score` on recommendation cards (they're in the DB at `recommendations.py:142-143`, just not rendered). **(S)**

### P2 — polish (ongoing)
13. Standardise currency display + number grouping (1,234.56 zł).
14. Metric tooltips on first hover (CVR, CPA, ROAS formulas).
15. Skeleton screens in place of bare spinners.
16. Back-button behaviour after drill-in.
17. Settings accessible from everywhere (header icon).
18. Retire inline styles in `SearchTerms.jsx`; port to tokens.
19. Two-way Obsidian sync (VISION.md v2.0 milestone).

---

## Bottom line

The app has the data, the domain logic, and a coherent design system. What it lacks is the **UX connective tissue** that turns data into action — undo, preview, bulk flows that complete, consistent formatting, visible confidence signals. The P0 list is five small-to-medium fixes that would move the daily-workflow friction score from 2.4 to ~3.8 in about a week.

Current readiness for external paying users: **3.2 / 5**. After P0: **4 / 5**. After P1: **4.5 / 5** and competitive with Optmyzr for a self-managed freelancer.
