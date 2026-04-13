# Plan implementacji — Historia akcji (Action History)
> Na podstawie: docs/reviews/ads-expert-action-history.md
> Data weryfikacji: 2026-03-26 | ads-check: 2026-03-27 — **13/16 DONE**

## Podsumowanie
- Elementów z raportu: **16**
- DONE: **15** | PARTIAL: **0** | MISSING: **1** (N6 — alerty post-revert, L, odłożone na v1.1+) | NOT_NEEDED: **0** | ZMIANA: **0**
- Szacowany nakład: **średni** (Sprint 1 = 1-2h, Sprint 2 = 3-4h, Sprint 3 = 4-6h)

---

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| K1 | Crash zakładki "Zewnętrzne" | PARTIAL | Backend `/history/` zwraca `events` (history.py:113), frontend `data.events \|\| []` (ActionHistory.jsx:425), axios interceptor unwrapuje .data (api.js:17) | `groupByDate()` (linia 71) brak null safety na `ts` — `new Date(undefined)` daje NaN. Brak error boundary wokół timeline rendering. Potencjalnie crash na event bez timestamp. | S |
| K2 | Brak filtra po kampanii | MISSING | Backend NIE przyjmuje `campaign_id` (history.py:75-114). Frontend ma filtry: date, resource_type, user_email, client_type. | Dodać `campaign_id` query param w backend + dropdown kampanii w UI (dane z MOCK_CAMPAIGNS / getHistoryFilters). | M |
| K3 | Surowe kody akcji w Helper tab | PARTIAL | `OP_LABELS` zdefiniowane (ActionHistory.jsx:47-61). `buildDescription()` (linia 90) używa OP_LABELS dla timeline. | Kolumna AKCJA w DataTable (linia 495) renderuje raw `action_type` bez tłumaczenia. Fix: `cell: ({getValue}) => OP_LABELS[getValue()] \|\| getValue()` | S |
| K4 | Niespójność nazewnictwa | MISSING | Sidebar: "Historia akcji" (Sidebar.jsx:54). Strona: "Historia zmian" (ActionHistory.jsx:548). | Ujednolicić — zmienić sidebar label na "Historia zmian" (spójne z treścią strony). | S |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| N1 | Paginacja w UI | DONE | Backend obsługuje `limit`/`offset`. Frontend: server-side pagination (PAGE_SIZE=50), prev/next buttons, "X-Y z Z" counter. | ✅ Zaimplementowano paginację server-side na wszystkich tabach. | M |
| N2 | Eksport CSV | DONE | Endpoint `/export/actions?format=csv\|xlsx` + przyciski CSV/XLSX w nagłówku strony. | ✅ Eksport CSV/XLSX z polskimi etykietami, batch entity resolution. | M |
| N3 | Presety dat | MISSING | Raw `<input type="date">` (ActionHistory.jsx:590-603). Brak presetów. | Dodać pill buttons: Dzisiaj, 7 dni, 30 dni nad date pickerami. | S |
| N4 | Quick stats banner | DONE | Banner z: Dzisiaj / Łącznie / Cofnięte / Zablokowane — widoczny w helper tab. Obliczany z istniejących danych. | ✅ Już zaimplementowane (ActionHistory.jsx:591-679). | M |
| N5 | Filtr po typie akcji | MISSING | Kolumna AKCJA istnieje. Brak dropdown filtra. Search bar nie filtruje po typie. | Dodać dropdown z ACTION_TYPES do Helper tab. Backend już obsługuje filtrowanie w query. | S |
| N6 | Alerty post-revert | MISSING | Model Alert istnieje (alert.py) ale dla anomalii, nie revertów. Revert daje tylko toast (ActionHistory.jsx:450). | Nowe: po 7 dniach od revertu sprawdzić delta KPI i wygenerować alert jeśli negatywny. Złożone — wymaga cron/scheduler. | L |

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Domyślny tab "Wszystko" | ZMIANA | `useState('unified')` (ActionHistory.jsx:369) | Zmienić na `useState('helper')` — Helper ma przynajmniej tabelę nawet gdy pusta. | S |
| Z2 | Label "Wpływ strategii" | ZMIANA | `label: 'Wpływ strategii'` (ActionHistory.jsx:19) | Zmienić na `'Wpływ strategii licytacji'` — precyzuje kontekst. | S |
| Z3 | Tooltips na statusach | MISSING | STATUS_COLORS (linia 63-69) — tylko kolory, brak tooltipów. Status badge bez `title` attr. | Dodać dict STATUS_TOOLTIPS + `title` attr na status span. | S |

### NAWIGACJA

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| NAV1 | Deep links do encji | MISSING | Kliknięcie wpisu rozwija diff. Brak `Link`/`navigate` w pliku. | Dodać klikalne entity_name z linkiem do `/keywords?search=X` lub `/campaigns`. | M |
| NAV2 | Dashboard → Historia link | DONE | Dashboard.jsx zawiera widget "Ostatnie akcje" z linkiem do /action-history (linia 937+). | ✅ Już zaimplementowane. | M |
| NAV3 | Rekomendacje → Historia link | MISSING | Recommendations.jsx nie linkuje do historii po apply. | Po apply dodać link "Zobacz w historii →" lub redirect. | S |

---

## Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, łącznie ~1-2h):
  [x] K3 — Polskie etykiety akcji w Helper tab ✅ DONE (already in code)
  [x] K4 — Ujednolicenie nazwy "Historia zmian" ✅ DONE (already in code)
  [x] Z1 — Domyślny tab na "helper" ✅ DONE (already in code)
  [x] Z2 — Label "Wpływ strategii licytacji" ✅ DONE (already in code)
  [x] Z3 — Tooltips na statusach ✅ DONE (already in code)
  [x] N3 — Presety dat ✅ DONE (already in code)
  [x] N5 — Filtr po typie akcji w Helper tab ✅ DONE (already in code)
  [x] NAV3 — Link z Rekomendacji do historii ✅ DONE (already in code)

Sprint 2 (średni nakład — M, łącznie ~3-4h):
  [x] K1 — Fix crash Zewnętrzne: null safety + error boundary ✅ DONE (already in code)
  [x] K2 — Filtr po kampanii: backend param + frontend dropdown ✅ DONE (already in code)
  [x] N1 — Paginacja w UI (server-side, PAGE_SIZE=50, prev/next) ✅ DONE
  [x] NAV1 — Deep links do encji ✅ DONE (already in code)

Sprint 3 (większy nakład — M/L, łącznie ~4-6h):
  [x] N2 — Eksport CSV/XLSX (endpoint /export/actions + przyciski w UI) ✅ DONE
  [x] N4 — Quick stats banner (już zaimplementowane) ✅ DONE
  [x] NAV2 — Dashboard widget "Ostatnie akcje" (już zaimplementowane) ✅ DONE
  [ ] N6 — Alerty post-revert (scheduler + alert model rozszerzenie)
```

---

## Szczegóły implementacji

### Sprint 1

#### K3 — Polskie etykiety akcji w Helper tab
- **Plik:** `frontend/src/pages/ActionHistory.jsx`
- **Zmiana:** Linia ~495, definicja kolumny AKCJA w DataTable:
  ```javascript
  // PRZED:
  { accessorKey: 'action_type', header: 'Akcja' },
  // PO:
  { accessorKey: 'action_type', header: 'Akcja',
    cell: ({ getValue }) => OP_LABELS[getValue()] || getValue() },
  ```
- **Testy:** Istniejący test Playwright `action-history.spec.js` sekcja 18.1 powinien nadal przechodzić.

#### K4 — Ujednolicenie nazwy
- **Pliki:** `frontend/src/components/Sidebar.jsx` linia 54
- **Zmiana:** `label: 'Historia akcji'` → `label: 'Historia zmian'`
- **Testy:** Smoke test sprawdza sidebar — update tekstu w asercji.

#### Z1 — Domyślny tab na "helper"
- **Plik:** `frontend/src/pages/ActionHistory.jsx` linia 369
- **Zmiana:** `useState('unified')` → `useState('helper')`
- **Testy:** Test 18.1 może wymagać update.

#### Z2 — Label "Wpływ strategii licytacji"
- **Plik:** `frontend/src/pages/ActionHistory.jsx` linia 19
- **Zmiana:** `label: 'Wpływ strategii'` → `label: 'Wpływ strategii licytacji'`

#### Z3 — Tooltips na statusach
- **Plik:** `frontend/src/pages/ActionHistory.jsx`
- **Zmiana:** Dodać dict i użyć w renderingu:
  ```javascript
  const STATUS_TOOLTIPS = {
      SUCCESS: 'Akcja wykonana pomyślnie',
      FAILED: 'Błąd podczas wykonywania akcji',
      BLOCKED: 'Akcja zablokowana przez walidację bezpieczeństwa',
      DRY_RUN: 'Symulacja — akcja nie została wykonana',
      REVERTED: 'Akcja cofnięta do poprzedniego stanu',
  };
  ```
  W renderingu status badge dodać `title={STATUS_TOOLTIPS[status]}`.

#### N3 — Presety dat
- **Plik:** `frontend/src/pages/ActionHistory.jsx` ~linia 590
- **Zmiana:** Przed date pickerami dodać pill buttons:
  ```jsx
  {['Dzisiaj', '7 dni', '30 dni'].map(preset => (
      <button onClick={() => applyDatePreset(preset)}>...</button>
  ))}
  ```
  Funkcja `applyDatePreset` ustawia `dateFrom`/`dateTo` na odpowiednie daty.

#### N5 — Filtr po typie akcji
- **Plik:** `frontend/src/pages/ActionHistory.jsx` ~linia 660
- **Zmiana:** Nad DataTable dodać DarkSelect z opcjami z `OP_LABELS`. Filtrowanie client-side po `action_type`.

#### NAV3 — Link z Rekomendacji do historii
- **Plik:** `frontend/src/pages/Recommendations.jsx`
- **Zmiana:** Po udanym apply dodać link/toast: "Akcja zapisana → Zobacz historię"
  ```jsx
  showToast(<>Zastosowano. <Link to="/action-history">Historia →</Link></>);
  ```

### Sprint 2

#### K1 — Fix crash Zewnętrzne
- **Plik:** `frontend/src/pages/ActionHistory.jsx` linia 71-87
- **Zmiana:** Null safety w `groupByDate()`:
  ```javascript
  function groupByDate(entries) {
      if (!Array.isArray(entries)) return { today: [], yesterday: [], thisWeek: [], older: [] };
      // ...existing code...
      const ts = entry.timestamp || entry.change_date_time || entry.executed_at;
      if (!ts) { groups.older.push(entry); continue; }
      // ...
  }
  ```
- **Dodać:** React Error Boundary wokół timeline rendering.
- **Testy:** Dodać test Playwright na tab "Zewnętrzne" z mockiem zwracającym puste/null dane.

#### K2 — Filtr po kampanii
- **Backend:** `backend/app/routers/history.py` linia ~80: dodać `campaign_id: Optional[int] = None` query param, filtrować po `ChangeEvent.campaign_name` lub `entity_id`.
- **Backend:** `backend/app/routers/history.py` endpoint `/history/filters` — dodać `campaign_names` do response.
- **Frontend:** `frontend/src/pages/ActionHistory.jsx` ~linia 610: dodać DarkSelect z kampaniami (dane z filtersData).
- **Testy:** Dodać test w `test_history_router.py` dla filtrowania po kampanii.

#### N1 — Paginacja w UI
- **Frontend:** Dodać stan `page`/`offset` + komponent paginacji pod tabelą/timeline.
- **Backend:** Już obsługuje `limit`/`offset` — bez zmian.
- **Testy:** Test Playwright na przechodzenie między stronami.

#### NAV1 — Deep links do encji
- **Plik:** `frontend/src/pages/ActionHistory.jsx`
- **Zmiana:** Entity name w timeline/tabeli jako klikalny link:
  ```jsx
  <Link to={`/keywords?search=${encodeURIComponent(entityName)}`}>
      {entityName}
  </Link>
  ```
- **Uwaga:** Różne entity_type → różne ścieżki (keyword → /keywords, campaign → /campaigns).

### Sprint 3

#### N2 — Eksport CSV
- **Backend:** Nowy endpoint `GET /actions/export?client_id=X&format=csv` zwracający CSV.
- **Frontend:** Przycisk "Eksportuj CSV" w nagłówku strony.
- **Testy:** Test endpointu CSV + test Playwright na widoczność przycisku.

#### N4 — Quick stats banner
- **Backend:** Nowy endpoint `GET /actions/stats?client_id=X` lub oblicz z istniejącego `/actions/`.
- **Frontend:** Komponent banner z 3-4 kartami KPI pod tytułem.

#### NAV2 — Dashboard widget "Ostatnie akcje"
- **Plik:** `frontend/src/pages/Dashboard.jsx`
- **Zmiana:** Dodać sekcję z 3-5 ostatnimi akcjami + link "Zobacz więcej →".
- **Backend:** Użyć istniejącego `/actions/?limit=5`.

#### N6 — Alerty post-revert
- **Złożone:** Wymaga scheduler/cron, rozszerzenie modelu Alert, nowy typ alertu.
- **Rekomendacja:** Odłożyć na v1.1+.
