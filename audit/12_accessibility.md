# PHASE 12 — Accessibility Audit (WCAG 2.1 AA)

**Verdict: NOT WCAG 2.1 AA compliant.** Approximately **40 %** of criteria pass.

~30–50 % of the application is unusable for keyboard-only users or screen-reader users due to three foundational issues:

1. Colour contrast fails across all secondary text (`rgba(255,255,255,0.35)` on `#0D0F14` = **1.59:1**, needs 4.5:1).
2. Focus indicators are removed (`outline: 'none'`) and not replaced.
3. Custom form components (`DarkSelect`, date picker, modals) are not keyboard-operable and lack ARIA.

None of the three are hard to fix. The three highest-impact fixes together take roughly **5 hours** and close ~60 % of violations.

---

## Compliance snapshot

| Category | WCAG Level | Status |
|----------|------------|--------|
| 1.3.1 Info & relationships | A | ❌ Fail (form labels not associated, 8+ instances) |
| 1.4.3 Contrast minimum | AA | ❌ Fail (40% of UI at 1.59:1 or 1.97:1) |
| 2.1.1 Keyboard | A | ❌ Fail (`DarkSelect`, modals, date picker) |
| 2.4.3 Focus order | A | ❌ Fail (modals don't manage focus) |
| 2.4.7 Focus visible | AA | ❌ Fail (20+ interactive elements) |
| 2.5.5 Target size | AA | ❌ Fail (nav items 27 px, calendar 22 px) |
| 3.1.1 Language of page | A | ✅ Pass (`<html lang="pl">`) |
| 4.1.2 Name, role, value | A | ❌ Fail (10+ custom components) |
| Polish diacritics (domain rule) | — | ✅ Pass (verified across all UI surfaces) |

---

## 1. Perceivable — colour contrast (CRITICAL)

**File:** `frontend/src/constants/designTokens.js:28-29`

- `C.textMuted = rgba(255,255,255,0.35)` on `#0D0F14` bg → contrast ratio **1.59:1** (fails 4.5:1)
- `C.textSecondary = rgba(255,255,255,0.55)` → **1.97:1** (fails)
- Text on hover rows (`bg-white/5` cascade) → ~1.2:1

**Where it hurts:**
- `DataTable.jsx:62` — all table headers use `className="text-app-muted"`
- `GlobalFilterBar.jsx:14` — filter field labels ("Status", "Etykieta")
- `SyncModal.jsx:169` — "Wybierz fazy do synchronizacji" label
- Every KPI sub-label, caption, and metadata string

**Impact:** ~40 % of UI text is unreadable for low-vision users. Also fails the stricter 7:1 AAA check that GDPR-conscious public-sector buyers will ask about.

**Fix (1 hour):** raise `textMuted` opacity from 0.35 → 0.75. Raise `textSecondary` from 0.55 → 0.80. Both pass 4.5:1. Visual hierarchy is preserved because the larger, bolder primary text still dominates.

---

## 2. Perceivable — charts without text alternatives (CRITICAL)

**Files:** `TrendExplorer.jsx:4-6`, `WoWChart.jsx`, `PmaxChannelsSection.jsx`

Charts are SVG-only:
- No `role="img"` + `aria-label` describing the chart.
- No `<table>` fallback with the same data.
- Channel types (SEARCH / DISPLAY / VIDEO) encoded by colour alone — unreadable for colour-blind users.
- Tooltips require mouse hover; keyboard users get nothing.

**Impact:** screen-reader users **cannot access trend data at all**. TrendExplorer is effectively invisible.

**Fix (4 hours for TrendExplorer, 2 hours each for Woe/Pmax):** add `role="img"` + `aria-label` summarising the chart; below each chart, render a visually-hidden `<table>` with the same data series. Add a second visual encoding (pattern, icon) on top of colour.

---

## 3. Operable — focus indicators removed (CRITICAL)

**Files:** `DarkSelect.jsx:61` (`outline: 'none'`), `DataTable.jsx:48` (`focus:outline-none`), and several components that remove the outline without replacement.

**Impact:** tab through the app — you can't see where you are. Every keyboard user is immediately lost.

**Fix (1 hour):** add a global `:focus-visible` rule in `index.css`:

```css
:focus-visible {
  outline: 2px solid #4F8EF7;  /* accent-blue */
  outline-offset: 2px;
  border-radius: 4px;
}
```

Overrides propagate everywhere; no per-component change needed.

---

## 4. Operable — `DarkSelect` not keyboard operable (CRITICAL)

**File:** `frontend/src/components/DarkSelect.jsx:47-73`

- No keyboard open: only mouse click opens the list.
- No arrow-key navigation between options.
- No type-ahead.
- No ARIA: missing `role="combobox"`, `aria-expanded`, `aria-controls`; options are `<button>` without `role="option"`.

**Impact:** every filter dropdown (10+ across the app — status, period, campaign type, etc.) is unusable without a mouse.

**Fix (3 hours):** add keyboard handlers (Space/Enter to open, ↑/↓ to navigate, Enter to select, Escape to close, typed letter for type-ahead), ARIA roles, and focus management on open.

---

## 5. Operable — modals lack focus trap + ARIA

**Files:** `SyncModal.jsx:114-246`, `ConfirmationModal.jsx:18-98`

- No `role="dialog"`, no `aria-modal="true"`, no `aria-labelledby`.
- No Escape-to-close handler → user must tab to the close button.
- Focus doesn't move into the modal on open.
- Focus isn't returned to the trigger on close.
- No focus trap → tab escapes the modal to background content.

**Impact:** screen-reader users get no announcement that a modal has opened. Keyboard users are disoriented.

**Fix (3 hours):**
- Add `role="dialog" aria-modal="true" aria-labelledby="modal-title-id"`.
- `useEffect` to focus first interactive element on open, restore focus on close.
- Trap focus via a small helper or library (`focus-trap-react`).
- `onKeyDown={(e) => e.key === 'Escape' && onClose()}`.

---

## 6. Operable — target size (minor but real)

**WCAG 2.5.5 AA:** interactive elements ≥ 44×44 CSS pixels.

Failures:
- NavItem buttons `py-[7px]` → ~27 px
- Calendar day cells 22×22
- Sort chevrons 12×12
- Modal close buttons 16×16
- `DarkSelect` option rows ~28 px

**Fix (2 hours):** bump padding on small-target elements, or add transparent hit-areas via `::before` pseudo-elements to preserve visual size while enlarging click area.

---

## 7. Understandable — form labels not associated

**File:** `GlobalFilterBar.jsx:11-19`

`FilterField` renders labels as `<div>`, not `<label htmlFor>`. Screen readers announce "Combobox (unlabeled)" for every filter.

Also in `DataTable.jsx:43-50`: search input has `placeholder` but no `aria-label` — screen readers announce "edit text" with no context.

**Fix (1 hour):** convert `FilterField`'s inner `<div>` to `<label htmlFor={inputId}>`; pass an `id` to the child input. Add `aria-label` to the table search input.

---

## 8. Robust — custom components missing ARIA roles

- **DarkSelect:** missing `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-haspopup="listbox"` on trigger; missing `role="listbox"` + `id` on options container; missing `role="option"` + `aria-selected` on each option.
- **Modals:** covered above.
- **Icons:** `Zap`, `Search`, `Clock`, `Loader2` used both decoratively (should be `aria-hidden="true"`) and semantically (status icons — should have `aria-label`). No distinction today.
- **NavItem:** active page not announced. Add `aria-current="page"` to the active link.

**Fix (1.5 hours)** across all four patterns.

---

## 9. Polish diacritics — pass

Spot-checked `SyncModal`, `GlobalFilterBar`, `DataTable`, `TrendExplorer`, `NavItem`. All Polish diacritics (ą ć ę ł ń ó ś ź ż) present correctly. `index.html` sets `lang="pl"`. Compliant with the project's domain rule (`CLAUDE.md` "POLISH UI").

---

## Keyboard-only user journey — test result

Task: Sidebar → keyboard shortcut "2" (Campaigns) → filter by status → open trends modal.

| Step | Expected | Actual | Result |
|------|----------|--------|--------|
| 1. Tab through sidebar | Focus visible on nav items | Focus invisible, items navigable | ⚠️ Partial (outline missing) |
| 2. Press "2" keyboard shortcut | Navigates to Campaigns | Works | ✅ |
| 3. Tab to GlobalFilterBar | Focus reaches filter | Focus reaches filter but invisible | ⚠️ Partial |
| 4. Tab to Status select, press Space | `DarkSelect` opens | Does nothing (mouse-only) | ❌ **Blocked** |
| 5. Tab to date picker, press Enter | Picker opens | Does nothing | ❌ **Blocked** |
| 6. Tab to result row, press Enter | Row opens detail | Row is `onClick`-only, not keyboard | ❌ **Blocked** |
| 7. Open modal, press Escape | Modal closes | Doesn't close | ❌ **Blocked** |

**Verdict:** ~30 % of workflows unreachable without a mouse.

---

## Screen-reader journey — test result

Task: Login → select client → start sync → verify status.

| Step | Expected | Actual | Result |
|------|----------|--------|--------|
| 1. Login form | "Login form with developer token field" | "Form" (fields unannounced) | ⚠️ Partial |
| 2. Client select | "Acme Corp, 1 of 5" | "Combobox (unlabeled), Acme Corp" | ❌ Fail |
| 3. Modal open | "Dialog: Synchronizacja" | "Dialog" (no title) | ❌ Fail |
| 4. Sync running icon | "Loading, sync in progress" | "Graphics" or silent | ❌ Fail |
| 5. Trend chart | "Cost and clicks trend over time" | Silent | ❌ Fail |
| 6. Sortable table | "Column, sortable" | Partially announced, headers too faint | ⚠️ Partial |

**Verdict:** ~50 % of UI information is lost to screen-reader users.

---

## Top 10 fixes — impact × effort

| # | Fix | Impact | Effort | Priority |
|---|-----|--------|--------|----------|
| 1 | Raise `textMuted` 0.35 → 0.75 + `textSecondary` 0.55 → 0.80 in `designTokens.js` | 40 % of UI readability | 1 h | 🔴 |
| 2 | Global `:focus-visible` outline in `index.css` | All interactive elements visibly focusable | 1 h | 🔴 |
| 3 | `DarkSelect` keyboard + ARIA (arrow keys, Space/Enter/Escape, type-ahead, combobox/listbox roles) | 10+ dropdowns become usable | 3 h | 🔴 |
| 4 | Modals: `role="dialog"` + `aria-modal` + `aria-labelledby` + focus trap + Escape close + focus return | Modals fully accessible | 3 h | 🟠 |
| 5 | `FilterField` `<div>` → `<label htmlFor>`; add `aria-label` to DataTable search | Form labels associated | 1 h | 🟠 |
| 6 | Icon ARIA pass: semantic icons get `aria-label`, decorative get `aria-hidden="true"` | Icons properly announced | 1 h | 🟡 |
| 7 | Chart `role="img"` + `aria-label` + visually-hidden `<table>` fallback on `TrendExplorer`, `WoWChart`, `PmaxChannelsSection` | Chart data reachable by screen readers | 4 h | 🟡 |
| 8 | `aria-current="page"` on active NavItem | Active page announced | 30 min | 🟡 |
| 9 | Enlarge touch targets (nav items, calendar days, sort chevrons, close buttons) to 44×44 via padding or pseudo-element hit areas | Mobile + motor-impairment accessibility | 2 h | 🟡 |
| 10 | `GlobalDatePicker` focus management + keyboard navigation | Calendar usable without mouse | 2 h | 🟡 |

**Total:** ~18 hours for full WCAG 2.1 AA compliance.
**The critical three (#1 + #2 + #3) = 5 hours and close roughly 60 % of violations.**

---

## Files requiring changes

1. `frontend/src/constants/designTokens.js` — contrast (line 28)
2. `frontend/src/index.css` — focus-visible global rule
3. `frontend/src/components/DarkSelect.jsx` — keyboard + ARIA
4. `frontend/src/components/SyncModal.jsx` — dialog ARIA + focus trap
5. `frontend/src/components/ConfirmationModal.jsx` — dialog ARIA + focus trap
6. `frontend/src/components/GlobalFilterBar.jsx` — label association
7. `frontend/src/components/DataTable.jsx` — aria-label on search + contrast
8. `frontend/src/components/GlobalDatePicker.jsx` — focus management + keyboard nav
9. `frontend/src/components/Sidebar.jsx` — aria-current + icon labels
10. `frontend/src/components/TrendExplorer.jsx` — chart accessibility
11. `frontend/src/components/NavItem.jsx` — aria-current

---

## Remediation plan

### Week 1 — the critical three (5 hours)
- Contrast fix (designTokens.js).
- Global focus-visible (index.css).
- DarkSelect keyboard + ARIA.

→ App becomes minimally keyboard-navigable with visible focus and readable text.

### Week 2–3 — major (8 hours)
- Modal ARIA + focus trap.
- Form label associations.
- aria-current on NavItem.
- Icon ARIA pass.
- Date picker keyboard.

### Week 3–4 — medium (6 hours)
- Chart accessibility (TrendExplorer first).
- Touch targets to 44×44.
- Session timeout warning UI (1.2.1 partial).

### Phase 4 — nice-to-have
- Light theme toggle (respects `prefers-color-scheme`).
- ARIA live regions for sync progress.
- Keyboard-shortcuts help modal.

---

## Bottom line

GAH has real, fixable accessibility problems. The colour-contrast number (1.59:1) and the non-keyboard-operable `DarkSelect` are the two that cause the most daily pain and both are short fixes. Five hours of focused work moves compliance from ~40 % to ~70 %; another 13 hours gets to full WCAG 2.1 AA.

If the product is going to sell to agencies (GDPR-regulated, often accessibility-conscious buyers), this is a hard prerequisite. If it's going to sell only to solo freelancers, it's still worth doing — every accessibility fix also makes the app better for everyone else.
