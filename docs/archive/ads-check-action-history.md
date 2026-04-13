# ads-check: Action History (Historia zmian)
> Data: 2026-03-27 | Plan z: 2026-03-26 | Wynik: 13/16 tasków wdrożonych

## Podsumowanie
- Tasków w planie: 16
- DONE: 13 | PARTIAL: 0 | STILL_MISSING: 3 | SKIPPED: 0 | DIFFERENT: 0
- Verdykt: **PRAWIE** (81% complete)

## Status tasków

### Wdrożone (DONE)

| # | Task | Dowód |
|---|------|-------|
| K1 | Fix crash Zewnętrzne — null safety | ActionHistory.jsx:90-94 — if (!ts) + isNaN check |
| K2 | Filtr po kampanii | history.py:84 campaign_name param + ActionHistory.jsx:725-733 DarkSelect |
| K3 | Polskie etykiety akcji | ActionHistory.jsx:533 — OP_LABELS[getValue()] cell renderer |
| K4 | Ujednolicenie nazwy | Sidebar.jsx:54 — "Historia zmian" |
| Z1 | Domyślny tab helper | ActionHistory.jsx:397 — useState('helper') |
| Z2 | Label strategii licytacji | ActionHistory.jsx:20 — "Wpływ strategii licytacji" |
| Z3 | Tooltips na statusach | ActionHistory.jsx:72-78 STATUS_TOOLTIPS + :183,:564 title attr |
| N3 | Presety dat | ActionHistory.jsx:613-617 DATE_PRESETS (Dzisiaj/7dni/30dni) |
| N4 | Quick stats banner | ActionHistory.jsx:659-679 — Dzisiaj/Łącznie/Cofnięte/Zablokowane |
| N5 | Filtr po typie akcji | ActionHistory.jsx:746-759 DarkSelect z OP_LABELS |
| NAV1 | Deep links do encji | ActionHistory.jsx:103-111 getEntityLink() + :542-547 Link |
| NAV2 | Dashboard widget | Dashboard.jsx:195,240,938-950 — "Ostatnie akcje" widget |
| NAV3 | Link z Rekomendacji | Recommendations.jsx:609 — toast "Historia zmian" |

### Brakujące (STILL_MISSING)

| # | Task | Priorytet | Nakład |
|---|------|-----------|--------|
| N1 | Paginacja w UI | NICE TO HAVE | M |
| N2 | Eksport CSV | NICE TO HAVE | M |
| N6 | Alerty post-revert (scheduler) | NICE TO HAVE | L |

## Następne kroki
Wdrożono 13 z 16 tasków (81%). Brakujące to wyłącznie NICE TO HAVE:
- N1 (paginacja) i N2 (eksport CSV) — średni nakład, warte zrobienia
- N6 (alerty post-revert) — wymaga schedulera, odłożone na v1.1+
