# Plan implementacji — WSZYSTKIE ZAKŁADKI
> Na podstawie: docs/reviews/ads-expert-all.md
> Data weryfikacji: 2026-03-25

## Podsumowanie
- Elementow z raportu: **19**
- **DONE: 3** | **PARTIAL: 1** | **MISSING: 12** | **NOT_NEEDED: 3**
- Szacowany naklad: **sredni** (2 sprinty quick wins + 1 sprint medium)

---

## Status kazdego elementu

### KRYTYCZNE (must implement)

| # | Element | Zakładka | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|----------|--------|-------------|------------|--------|
| 1 | Forecast retry bug (`loadForecast()` undefined) | Forecast | **MISSING** | Linia 148: `onClick={loadForecast}` — funkcja nie istnieje | Zamienić na prawidłową funkcję retry | **S** |
| 2 | Forecast hardcoded 7 dni | Forecast | **MISSING** | Linia 73: `getForecast(selectedCampaign, metric, 7)` — hardcoded | Dodać selector horyzontu (7/14/30) | **S** |
| 3 | Forecast brak FilterContext | Forecast | **MISSING** | Nie importuje `useFilter()`. Brak `days`/`allParams` | Podpiąć do FilterContext | **S** |
| 4 | Semantic hardcoded `days: 30` | Semantic | **MISSING** | Linia 24: `days: 30` hardcoded w API call | Podpiąć do FilterContext | **S** |
| 5 | Semantic brak bulk actions na waste clusters | Semantic | **MISSING** | Brak `bulkAddNegative` ani żadnych akcji | Dodać "Dodaj jako negatywy" per waste cluster | **M** |
| 6 | Settings brak form validation | Settings | **MISSING** | Inputy `type="number"` bez `min`/`max` atrybutów | Dodać min/max, required, validation | **S** |
| 7 | Settings brak dirty state | Settings | **MISSING** | Brak porównania form vs loaded data, brak beforeunload | Dodać dirty tracking + warning | **S** |

### NICE TO HAVE

| # | Element | Zakładka | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|----------|--------|-------------|------------|--------|
| 8 | Cross-navigation utility (systemowy) | Cała apka | **MISSING** | Każda strona używa `navigate()` inline. Campaigns.jsx: query params. Dashboard: proste routes | Hook `useNavigateTo(tab, filters)` | **M** |
| 9 | Semantic search input per cluster | Semantic | **MISSING** | Brak jakiegokolwiek search inputa | Dodać filtr tekstowy | **S** |
| 10 | Alerts → Campaigns navigation | Alerts | **MISSING** | Alert card wyświetla `campaign_id` ale brak onClick navigate | Dodać kliknięcie → /campaigns | **S** |
| 11 | QualityScore → Keywords navigation | QualityScore | **MISSING** | Tabela low-QS keywords — brak click handlera | Dodać kliknięcie → /keywords z filtrem | **S** |
| 12 | Forecast → Campaigns navigation | Forecast | **MISSING** | Campaign selector bez nawigacji | Dodać "Zobacz kampanię →" link | **S** |
| 13 | SearchOptimization inline actions | SearchOptimization | **MISSING** | 25 sekcji — wszystkie read-only | Dodać "Pause" w Wasted Spend, "Add negative" w N-gram | **L** |
| 14 | Agent chat history persistence | Agent | **MISSING** | `useState([])` — ginie po odświeżeniu | localStorage lub sessionStorage | **S** |
| 15 | Reports PDF export | Reports | **MISSING** | Markdown-only view, brak jspdf/html2pdf | Dodać export PDF | **M** |
| 16 | Recommendations scheduling | Recommendations | **MISSING** | Apply jest natychmiastowe, brak cron/timer | Auto-apply scheduler | **L** |

### ELEMENTY KTÓRE JUŻ ISTNIEJĄ (DONE / NOT_NEEDED)

| # | Element | Zakładka | Status | Weryfikacja |
|---|---------|----------|--------|-------------|
| 17 | DailyAudit link do SearchTerms | DailyAudit | **DONE** | Linia 458: `navigate('/search-terms')` — ISTNIEJE! |
| 18 | DailyAudit anomaly summary | DailyAudit | **DONE** | Linie 304-400: alerty inline (anomalies_24h, disapproved, budget-capped), do 4 na banerze + link "/alerts" |
| 19 | DailyAudit date filtering | DailyAudit | **NOT_NEEDED** | Backend-driven `period_days` (linia 309). DailyAudit z natury to snapshot "dziś vs wczoraj" — date picker tu nie pasuje |

---

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, ~3h łącznie):
  [ ] #1 — Forecast retry bug fix (Forecast.jsx:148)
  [ ] #2 — Forecast horizon selector (7/14/30 dni)
  [ ] #3 — Forecast podpiąć do FilterContext
  [ ] #4 — Semantic podpiąć do FilterContext (Semantic.jsx:24)
  [ ] #6 — Settings form validation (min/max na inputach)
  [ ] #7 — Settings dirty state tracking
  [ ] #9 — Semantic search input
  [ ] #14 — Agent chat history (localStorage)

Sprint 2 (cross-navigation — naklad S-M, ~3h łącznie):
  [ ] #8 — useNavigateTo hook (shared utility)
  [ ] #10 — Alerts → Campaigns navigation
  [ ] #11 — QualityScore → Keywords navigation
  [ ] #12 — Forecast → Campaigns navigation

Sprint 3 (medium naklad — M-L, ~6h łącznie):
  [ ] #5 — Semantic bulk negative action per cluster
  [ ] #13 — SearchOptimization inline actions (Wasted Spend pause, N-gram negatives)
  [ ] #15 — Reports PDF export
  [ ] #16 — Recommendations scheduling (v1.2 roadmap)
```

---

## Szczegoly implementacji

### Sprint 1

#### #1: Forecast retry bug fix
- **Plik**: `frontend/src/pages/Forecast.jsx` linia 148
- **Zmiana**: Zamienić `onClick={loadForecast}` na `onClick={() => { setError(null) }}` (useEffect na linii 66 automatycznie re-fetchuje po zmianie stanu)
- **Alternatywa**: Wyciągnąć logikę fetch z useEffect do named function i użyć jej w retry

#### #2: Forecast horizon selector
- **Plik**: `frontend/src/pages/Forecast.jsx`
- **Zmiana**: Dodać state `forecastDays` z opcjami [7, 14, 30]. Pill buttons obok metric selector. Zamienić hardcoded `7` na zmienną. Zaktualizować label "Predykcja na {forecastDays} dni"
- **Backend**: Endpoint `getForecast` już akceptuje `forecastDays` param — bez zmian

#### #3: Forecast podpiąć do FilterContext
- **Plik**: `frontend/src/pages/Forecast.jsx`
- **Zmiana**: `import { useFilter } from '../contexts/FilterContext'`. Użyć `days` jako default dla forecastDays. Opcjonalnie: filtrowanie po campaign_type z FilterContext

#### #4: Semantic podpiąć do FilterContext
- **Plik**: `frontend/src/pages/Semantic.jsx` linia 24
- **Zmiana**: `import { useFilter } from '../contexts/FilterContext'`. Zamienić hardcoded `days: 30` na `days: days || 30`. Dodać `allParams` do deps useEffect

#### #6: Settings form validation
- **Plik**: `frontend/src/pages/Settings.jsx`
- **Zmiana**: Na inputach safety_limits dodać `min={0}` i `max` wg logiki:
  - `MAX_BID_CHANGE_PCT`: min=1, max=100
  - `MAX_BUDGET_CHANGE_PCT`: min=1, max=100
  - `MIN_BID_USD`: min=0.01, max=100
  - `MAX_BID_USD`: min=0.01, max=1000
  - `MAX_KEYWORD_PAUSE_PCT`: min=1, max=50
  - `MAX_NEGATIVES_PER_DAY`: min=1, max=500
- Na business_rules: `min_roas` min=0, `max_daily_budget` min=0

#### #7: Settings dirty state tracking
- **Plik**: `frontend/src/pages/Settings.jsx`
- **Zmiana**:
  1. `const [originalData, setOriginalData] = useState(null)` — zapisać po load
  2. `const isDirty = JSON.stringify(formData) !== JSON.stringify(originalData)`
  3. `useEffect` z `beforeunload` event listener gdy `isDirty`
  4. Visual indicator: Save button zmienia kolor gdy dirty

#### #9: Semantic search input
- **Plik**: `frontend/src/pages/Semantic.jsx`
- **Zmiana**: Dodać `searchTerm` state + input field obok cost filter pills. Filtrować klastry: `clusters.filter(c => c.terms.some(t => t.text.includes(searchTerm)))`

#### #14: Agent chat history (localStorage)
- **Plik**: `frontend/src/pages/Agent.jsx`
- **Zmiana**:
  1. Na mount: `useState(() => JSON.parse(localStorage.getItem('agent_chat') || '[]'))`
  2. Po każdej wiadomości: `localStorage.setItem('agent_chat', JSON.stringify(messages))`
  3. Przycisk "Wyczyść historię" → `localStorage.removeItem('agent_chat')`
  4. Limit: max 50 wiadomości w localStorage (FIFO)

### Sprint 2

#### #8: useNavigateTo hook
- **Nowy plik**: `frontend/src/hooks/useNavigateTo.js`
- **Implementacja**:
  ```js
  export function useNavigateTo() {
    const navigate = useNavigate()
    return (tab, filters = {}) => {
      const params = new URLSearchParams(filters).toString()
      navigate(params ? `/${tab}?${params}` : `/${tab}`)
    }
  }
  ```
- **Użycie**: `const navigateTo = useNavigateTo()` → `navigateTo('keywords', { campaign_id: 5 })`

#### #10: Alerts → Campaigns
- **Plik**: `frontend/src/pages/Alerts.jsx`
- **Zmiana**: Import `useNavigateTo`. Na alert card z campaign_id dodać `onClick={() => navigateTo('campaigns')}`

#### #11: QualityScore → Keywords
- **Plik**: `frontend/src/pages/QualityScore.jsx`
- **Zmiana**: Import `useNavigateTo`. Na wierszu low-QS keyword dodać `onClick` → navigate do `/keywords` z filtrem

#### #12: Forecast → Campaigns
- **Plik**: `frontend/src/pages/Forecast.jsx`
- **Zmiana**: Dodać link "Zobacz kampanię →" obok campaign selectora

### Sprint 3

#### #5: Semantic bulk negative action
- **Plik**: `frontend/src/pages/Semantic.jsx`
- **Zmiana**: Per waste cluster dodać przycisk "Dodaj jako negatywy". Import `bulkAddNegative` z api. Dialog potwierdzenia z listą termów. Toast po akcji.
- **Backend**: Endpoint `POST /search-terms/bulk-add-negative` już istnieje

#### #13: SearchOptimization inline actions
- **Plik**: `frontend/src/pages/SearchOptimization.jsx`
- **Zmiana**: W sekcji Wasted Spend dodać "Pause" button per keyword. W N-gram dodać "Add as negative" per n-gram. Wymaga importu odpowiednich API funkcji i confirmation dialogs.
- **Uwaga**: Duży plik (~1600 linii), ostrożnie z edycjami

#### #15: Reports PDF export
- **Plik**: `frontend/src/pages/Reports.jsx`
- **Zmiana**: `npm install html2pdf.js`. Przycisk "Export PDF" w headerze raportu. `html2pdf().from(reportElement).save()`
- **Testy**: Manual — sprawdzić rendering na różnych raportach

#### #16: Recommendations scheduling
- **Werdykt**: Odłożyć na **v1.2 roadmap** — wymaga backend cron job, UI scheduler, safety checks
- Nie implementować teraz
