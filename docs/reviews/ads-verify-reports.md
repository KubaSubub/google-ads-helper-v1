## Plan implementacji — Raporty
> Na podstawie: docs/reviews/ads-expert-reports.md
> Data weryfikacji: 2026-03-27 | ads-check: 2026-03-27 — **7/13 DONE** (100% KRYTYCZNE)

### Podsumowanie
- Elementow z raportu: 14
- DONE: 0 | PARTIAL: 2 | MISSING: 8 | NOT_NEEDED: 4
- Szacowany naklad: sredni (Sprint 1 = quick wins, Sprint 2 = features)

### Status kazdego elementu

#### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 1 | BUG: `getReport()` nie przekazuje `client_id` | PARTIAL | Backend `GET /reports/{id}` wymaga `client_id` (`reports.py:273`). Frontend `getReport()` nie wysyla go (`api.js:270`). Testy backendowe poprawnie testuja z `client_id` (`test_reports_router.py:144`) | Frontend musi przekazac `client_id` w query params. Komponent `loadReport()` (`Reports.jsx:412`) musi przekazac `selectedClientId` | S |
| 2 | BUG: Przycisk PDF uzywa `selectedReport` zamiast `activeReport` | PARTIAL | Przycisk istnieje w kodzie (`Reports.jsx:627-639`) z `window.print()`. Logika renderowania jest poprawna | Zmienna `selectedReport` nie istnieje — powinna byc `activeReport` (zdefiniowana w `Reports.jsx:387`) | S |
| 3 | Selektor okresu (miesiaca/tygodnia) | PARTIAL | Backend WSPIERA `req.year` i `req.month` (`reports.py:78-79` — `ReportGenerateRequest` schema). Frontend wysyla TYLKO `report_type` (`Reports.jsx:472`) | Frontend potrzebuje date picker i przekazanie `year`/`month` do body POST | M |
| 4 | Seed data raportow | MISSING | Tabela `reports` istnieje w modelu (`report.py`). `seed.py` NIE zawiera zadnej logiki seedowania raportow. Testy maja wlasna `_seed_reports()` ale to nie jest produkcyjny seed | Dodac seed z 2-3 przykladowymi raportami (monthly + weekly) z realistycznymi danymi strukturalnymi i probka narracji AI | M |

#### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 5 | Scheduler raportow | MISSING | Brak jakiejkolwiek logiki cron/scheduler | Caly feature: model schedule, backend cron/celery, UI konfiguracji | L |
| 6 | White-label PDF | MISSING | Jest `window.print()` (linia 629) ale brak CSS `@media print` w stylach apki | CSS print styles, opcjonalnie logo/header/footer | M |
| 7 | Porownanie dwoch raportow | MISSING | Brak | Nowy layout side-by-side, logika ladowania 2 raportow | L |
| 8 | Filtr per kampania / typ kampanii | MISSING | `generate_report` operuje na calym kliencie. `_gather_section` nie przyjmuje filtra kampanii | Dodac `campaign_ids` param do `ReportGenerateRequest` i propagowac | M |
| 9 | Trend health score | MISSING | Raporty sa w DB, mozna query po `report_type=health` | Endpoint + mini chart na stronie Reports | M |
| 10 | Email delivery | MISSING | Brak | Nowy serwis email, UI z polem email | L |
| 11 | Custom sekcje raportu | MISSING | `REPORT_DATA_MAP` jest static dict per report_type | Frontend checkboxy + dynamiczny `sections` list w request | M |

#### ZMIANY/USUNIECIA

| # | Element | Status | Aktualny stan | Rekomendacja | Naklad |
|---|---------|--------|---------------|--------------|--------|
| 12 | Nazwa "Raport AI" vs "Raporty" — mylace | NOT_NEEDED (low prio) | Sidebar: "Raport AI" (agent) + "Raporty" (reports) w sekcji AI | Zmiana nazwy "Raport AI" na "Asystent AI" w Sidebar — 1 linia, ale wymaga decyzji produktowej | S |
| 13 | Badge "Claude dostepny" — techniczny jargon | NOT_NEEDED (kosmetyka) | Badge renderuje sie na gorze strony (`Reports.jsx:573-582`) | Ukryc jesli `available=true`, pokazac tylko warning z ludzkim opisem | S |
| 14 | Lock per app zamiast per client | MISSING | Jeden `asyncio.Lock()` globalny (`reports.py:22`) — blokuje generowanie dla WSZYSTKICH klientow | Dict of locks per `client_id`: `_client_locks: dict[int, asyncio.Lock] = {}` | S |
| 15 | Label "PLN" przy zmiennej `cost_usd` | NOT_NEEDED (naming only) | Frontend: `{c.cost_usd} PLN` (`Reports.jsx:96`), backend: `cost_usd` field | Backend naming jest wewnetrzny — nie wplywaja na usera. PLN jest poprawny dla polskiego usera. Zmiana nazwy byłaby kozmetycznym refaktorem bez wartosci | — |

### Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, ~1h lacznie):
  [x] #1 — Fix getReport() brak client_id (api.js + Reports.jsx) ✅ DONE (already in code)
  [x] #2 — Fix przycisk PDF selectedReport → activeReport (Reports.jsx:627) ✅ DONE (already in code)
  [x] #14 — Lock per client_id zamiast globalny (reports.py) ✅ DONE (already in code)
  [x] #12 — Rename "Raport AI" → "Asystent AI" w Sidebar ✅ DONE

Sprint 2 (sredni naklad — M, ~3-4h):
  [x] #3 — Selektor okresu (date picker frontend + year/month w body) ✅ DONE
  [x] #4 — Seed data raportow (seed.py + realistyczne dane) ✅ DONE
  [x] #6 — Print CSS (@media print styles) ✅ DONE

Sprint 3 (nice to have — L, backlog):
  [ ] #8 — Filtr per kampania w raporcie
  [ ] #11 — Custom sekcje raportu
  [ ] #9 — Trend health score chart
  [ ] #5 — Scheduler raportow
  [ ] #7 — Porownanie dwoch raportow
  [ ] #10 — Email delivery
```

### Szczegoly implementacji

---

#### #1 — Fix `getReport()` brak `client_id` (P0)

**Pliki do modyfikacji:**
- `frontend/src/api.js` — linia 270-271
- `frontend/src/pages/Reports.jsx` — linia 412-415

**Zmiana api.js:**
```javascript
// PRZED:
export const getReport = (reportId) =>
    api.get(`/reports/${reportId}`);

// PO:
export const getReport = (reportId, clientId) =>
    api.get(`/reports/${reportId}`, { params: { client_id: clientId } });
```

**Zmiana Reports.jsx — `loadReport` callback:**
```javascript
// PRZED:
const loadReport = useCallback(async (reportId) => {
    setLoadingReport(true);
    try {
        const data = await getReport(reportId);

// PO:
const loadReport = useCallback(async (reportId) => {
    setLoadingReport(true);
    try {
        const data = await getReport(reportId, selectedClientId);
```
Dodac `selectedClientId` do dependency array useCallback (linia 421).

**Testy:** Istniejace testy w `test_reports_router.py` juz pokrywaja backend z `client_id`. Frontend nie ma unit testow — weryfikacja manualna.

---

#### #2 — Fix przycisk PDF `selectedReport` → `activeReport` (P0)

**Pliki do modyfikacji:**
- `frontend/src/pages/Reports.jsx` — linia 627

**Zmiana:**
```javascript
// PRZED:
{selectedReport && !generating && (

// PO:
{activeReport && !generating && (
```

**Testy:** Weryfikacja manualna — po zaladowaniu raportu przycisk PDF powinien byc widoczny.

---

#### #14 — Lock per client_id (P1)

**Pliki do modyfikacji:**
- `backend/app/routers/reports.py` — linie 22, 87-92, 226

**Zmiana:**
```python
# PRZED:
_reports_lock = asyncio.Lock()

# PO:
_client_locks: dict[int, asyncio.Lock] = {}

def _get_client_lock(client_id: int) -> asyncio.Lock:
    if client_id not in _client_locks:
        _client_locks[client_id] = asyncio.Lock()
    return _client_locks[client_id]
```
Uzycie w `event_stream()`: `lock = _get_client_lock(client_id)`, potem `lock.locked()`, `await lock.acquire()`, `lock.release()`.

**Testy:** Dodac test w `test_reports_router.py` — dwa rozne `client_id` nie blokuja sie nawzajem.

---

#### #3 — Selektor okresu (P1)

**Pliki do modyfikacji:**
- `frontend/src/pages/Reports.jsx` — stan + UI + handleGenerate
- Backend — brak zmian (juz wspiera `year`/`month` w `ReportGenerateRequest`)

**Zmiana frontend:**
1. Dodac stan `selectedYear`/`selectedMonth` (domyslnie biezacy)
2. Dla report_type `monthly` — renderowac dropdown z lista 12 ostatnich miesiecy
3. Dla report_type `weekly` — renderowac date picker z wyborem tygodnia (Monday-Sunday)
4. W `handleGenerate()` dodac `year` i `month` do body JSON:
```javascript
body: JSON.stringify({
    report_type: reportType,
    year: selectedYear,
    month: selectedMonth,
}),
```

**Testy:** Weryfikacja manualna — generowanie raportu za wybrany miesiac.

---

#### #4 — Seed data raportow (P1)

**Pliki do modyfikacji:**
- `backend/app/seed.py` — dodac sekcje seedowania raportow

**Zmiana:**
Dodac na koncu `seed.py` funkcje `seed_reports(db)`:
- 2-3 raporty miesieczne (completed) z realistycznym `report_data` (month_comparison, campaigns_detail, budget_pacing)
- 1 raport tygodniowy (completed)
- 1 raport health (completed)
- Probka `ai_narrative` (200-300 slow markdownu z naglowkami i bullet points)
- Powiazane z istniejacymi klientami seed (client_id=3 Sushi Naka Naka)

**Testy:** Istniejace testy maja wlasna `_seed_reports()` i nie zaleza od seed.py.

---

#### #6 — Print CSS (P2)

**Pliki do modyfikacji:**
- `frontend/src/index.css` lub nowy `frontend/src/print.css`

**Zmiana:**
Dodac `@media print` block:
- Ukryc sidebar, header, nawigacje
- Ukryc przycisk "Generuj" i pill-buttony
- Biale tlo zamiast ciemnego
- Powiekszyc fonty dla czytelnosci druku
- Zachowac tabele i KPI karty

**Testy:** Weryfikacja manualna — Ctrl+P w przegladarce.
