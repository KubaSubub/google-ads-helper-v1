## Plan implementacji — Full App
> Na podstawie: docs/reviews/ads-expert-full-app.md
> Data weryfikacji: 2026-03-28

### Podsumowanie
- Elementów z raportu: 14
- DONE: 3 | PARTIAL: 3 | MISSING: 5 | NOT_NEEDED: 3
- Szacowany nakład: średni

### Status każdego elementu

#### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| 1 | Podwójna filtracja — usunąć dropdown "Typ kampanii" z GlobalFilterBar | MISSING | Sidebar pills + GlobalFilterBar dropdown oba ustawiają `filters.campaignType` | Usunąć dropdown z GlobalFilterBar, zmienić grid z 4 na 3 kolumny | S |
| 2 | Write actions — pause keyword z Command Center | PARTIAL | Backend: `PATCH /campaigns/{id}` istnieje, DailyAudit ma `pause_burning` script. Brak: pause keyword endpoint + UI button w drill-down | Dodać button "Pauzuj" w drill-down low-perf keywords | M |
| 3 | Write actions — Apply recommendation z Command Center | DONE | Backend: `POST /recommendations/{id}/apply`, `POST /bulk-apply`. Frontend: DailyAudit renderuje rekomendacje | UI w Command Center drill-down "Google Recommendations" brakuje Apply button | S |
| 4 | Write actions — Exclude placement z Command Center | PARTIAL | Backend: `POST /analytics/placement-exclusion` istnieje. Stary render SearchOptimization miał "Wyklucz" button, ale nowy drill-down go nie ma | Dodać "Wyklucz" button w drill-down placementPerf | S |
| 5 | Poranny przegląd — KPI z zerami | PARTIAL | DailyAudit używa `period_days: 3`. Seed data nie pokrywa ostatnich 3 dni. Brak empty state z info o zakresie danych | Dodać komunikat "Brak danych za ostatnie 3 dni" lub zmienić fallback na 7 dni | S |
| 6 | Impression Share w tabeli kampanii | DONE | Campaigns.jsx linie 65-77: `search_impression_share`, `search_top_impression_share`, `search_abs_top_impression_share`, `search_budget_lost_is`, `search_rank_lost_is`, `search_click_share` — pełne IS z 6 metrykami! | — | — |

#### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| 7 | Period comparison w Command Center | MISSING | Pulpit ma `% vs poprz.` w KPI chipach. Command Center karty nie mają trendów | Dodać strzałki up/down + `% change` per karta bento | M |
| 8 | Bulk actions (zaznacz wiele → akcja) | PARTIAL | Backend: `POST /search-terms/bulk-add-negative`, `POST /bulk-apply`. Frontend: brak checkboxów w tabelach | Dodać checkboxy + toolbar z bulk actions | L |
| 9 | Klawiszowe skróty | MISSING | Brak | Dodać keyboard nav: 1-9 karty, Enter drill-down, Esc powrót | M |
| 10 | Eksport PDF raportu Command Center | MISSING | CSV/XLSX eksport w ActionHistory i Keywords. Brak PDF | Dodać html2canvas/jsPDF eksport bento grid | M |
| 11 | Pinning kart | MISSING | Brak | Dodać localStorage + drag-to-pin UI | M |

#### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| 12 | Usunąć dropdown "Typ kampanii" z GlobalFilterBar | MISSING | GlobalFilterBar.jsx linia 56-63 ma dropdown | Usunąć, zmienić grid 4→3 kolumny | S |
| 13 | Zmiana nazwy "Optymalizacja kampanii" → "Centrum audytu" | MISSING | SearchOptimization.jsx: "Optymalizacja kampanii" | Zmienić tytuł + sidebar label | S |
| 14 | Link z Pulpitu do Command Center | MISSING | Pulpit "Wasted Spend 287 zł" nie jest klikalny | Dodać onClick → navigate('/search-optimization') + setActiveSection('waste') | S |

### NOT_NEEDED (już pokryte)

- **IS w tabeli kampanii** — DONE, Campaigns.jsx ma 6 metryk IS
- **Apply recommendation** — DONE w backend (POST /recommendations/{id}/apply), potrzebny tylko UI w Command Center
- **Filtr po labelu kampanii** — FilterContext ma `campaignLabel` field (linia 55), GlobalFilterBar ma go zaimplementowanego

### Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, ~2h):
  [ ] #12 — Usunąć dropdown "Typ kampanii" z GlobalFilterBar (GlobalFilterBar.jsx)
  [ ] #13 — Zmiana nazwy "Optymalizacja kampanii" → "Centrum audytu" (SearchOptimization.jsx + Sidebar.jsx)
  [ ] #5  — Poranny przegląd — dodać empty state dla zerowych KPI (DailyAudit.jsx)
  [ ] #4  — Dodać "Wyklucz" button w drill-down placements (SearchOptimization.jsx renderSection)
  [ ] #14 — Link z Pulpitu Wasted Spend → Command Center (Dashboard.jsx)

Sprint 2 (średni nakład — M, ~4h):
  [ ] #3  — Dodać Apply/Dismiss buttons w drill-down Google Recommendations (SearchOptimization.jsx)
  [ ] #7  — Period comparison w kartach bento (% change vs prev period)
  [ ] #9  — Klawiszowe skróty (useEffect + keydown handler)

Sprint 3 (duży nakład — L, ~8h):
  [ ] #2  — Pause keyword z Command Center drill-down (nowy endpoint + UI)
  [ ] #8  — Bulk actions z checkboxami w tabelach
  [ ] #10 — Eksport PDF raportu Command Center
  [ ] #11 — Pinning kart bento grid
```

### Szczegóły implementacji

#### Sprint 1, Task #12: Usunąć dropdown "Typ kampanii" z GlobalFilterBar
- **Pliki**: `frontend/src/components/GlobalFilterBar.jsx`
- **Zmiany**: Usunąć sekcję z `campaignType` select (linie ~56-63). Zmienić grid `gridTemplateColumns` z 4 na 3 kolumny (Status, Nazwa, [pusty] lub rozszerzyć Status/Nazwa).
- **Testy**: build check

#### Sprint 1, Task #13: Zmiana nazwy
- **Pliki**: `frontend/src/pages/SearchOptimization.jsx`, `frontend/src/components/Sidebar.jsx`
- **Zmiany**: Sidebar NAV_GROUPS linia ~79: zmienić label `'Optymalizacja'` → `'Centrum audytu'`. SearchOptimization.jsx: zmienić h1 "Optymalizacja kampanii" → "Centrum audytu".
- **Testy**: build check

#### Sprint 1, Task #5: Poranny przegląd KPI empty state
- **Pliki**: `frontend/src/pages/DailyAudit.jsx`
- **Zmiany**: W sekcji KPI (linia ~310), dodać warunek: jeśli `kpi.current_spend === 0 && kpi.current_clicks === 0` → pokazać komunikat "Brak danych za ostatnie {periodDays} dni. Dane dostępne od {seed date range}."
- **Testy**: visual check

#### Sprint 1, Task #4: Button "Wyklucz" w placements drill-down
- **Pliki**: `frontend/src/pages/SearchOptimization.jsx`
- **Zmiany**: W `renderSection('placementPerf')` dodać kolumnę "Akcja" z buttonem "Wyklucz" (wywołuje `addPlacementExclusion`). Wzorować się na starym kodzie który miał ten button.
- **Testy**: build check

#### Sprint 1, Task #14: Link Wasted Spend → Command Center
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany**: Na karcie "Wasted Spend" dodać `onClick` → `navigate('/search-optimization')`. Opcjonalnie: przekazać state `{ activeSection: 'waste' }` przez React Router.
- **Testy**: visual check
