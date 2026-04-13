# ads-check: Dashboard (Pulpit)
> Data: 2026-03-26 | Plan z: 2026-03-26 | Wynik: 9/9 taskow wdrozonych

## Podsumowanie
- Taskow w planie: 9
- DONE: 9 | PARTIAL: 0 | STILL_MISSING: 0 | SKIPPED: 0 | DIFFERENT: 0
- Verdykt: **GOTOWE**

## Status taskow

### Wdrozone (DONE)

| # | Task | Dowod |
|---|------|-------|
| K1 | Sortowanie tabeli kampanii | Dashboard.jsx:196-197 — useState sortBy/sortDir. Linia 270-276 — sort w useMemo. Linia 467-490 — klikalne `<th>` z ChevronDown/Up |
| K2 | Deep-link do kampanii | Dashboard.jsx:514 — `navigate('/campaigns?campaign_id=${c.id}')` |
| N1 | Klikalna Wasted Spend → /search-terms | Dashboard.jsx:398 — `onClick={() => navigate('/search-terms?segment=WASTE')}` wrapper div |
| N2 | Link do /daily-audit | Dashboard.jsx:312 — "Poranny przeglad →" link w headerze |
| N3 | Filtr priorytetu InsightsFeed | InsightsFeed.jsx:54 — PRIORITY_PILLS, linia 59 — filterPriority state, linia 63-66 — filteredInsights useMemo, linia 117-138 — pill buttons UI |
| N4 | Sparkline tooltip | Dashboard.jsx:167 — `<Tooltip>` dodany w Sparkline component |
| N5 | Tooltip na Strategia | Dashboard.jsx:551 — `title={c.bidding_strategy ?? ''}` na `<span>` |
| N6 | Sortowanie Geo tabelki | Dashboard.jsx:198-199 — geoSortBy/geoSortDir state. Linia 729-759 — klikalne naglowki + sort logic |
| N7 | IS per kampania w tabeli | Backend: analytics.py:747-750 — is_map z Campaign model, linia 766 — `impression_share` w response. Frontend: Dashboard.jsx:463 — kolumna IS w `<th>`, linia 542-543 — komórka z kolorowaniem |

### Brakujace (STILL_MISSING)

Brak.

## Nastepne kroki

Zakladka gotowa — wszystkie 9 taskow wdrozone. Odpalam /ads-user dashboard jako re-test.
