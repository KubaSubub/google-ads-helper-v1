# Plan implementacji — Dashboard (Pulpit)
> Na podstawie: docs/reviews/ads-expert-dashboard.md
> Data weryfikacji: 2026-03-25

## Podsumowanie
- Elementow z raportu: **14** (K1-K4, N1-N4, Z1-Z2, NAV1-NAV4)
- **DONE: 0** | **PARTIAL: 5** | **BACKEND_ONLY: 2** | **MISSING: 4** | **NOT_NEEDED: 3**
- Szacowany naklad: **sredni** (1 sprint quick wins + 1 sprint medium)

---

## Status kazdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| K1 | Impressions + CTR w KPI cards | **PARTIAL** | Backend `dashboard-kpis` zwraca `impressions` i `ctr` (analytics.py:320-325) | Frontend Dashboard.jsx:295-327 renderuje tylko 4 karty (clicks, cost, conversions, roas) — pomija impressions i ctr | **S** |
| K2 | CPA w KPI | **PARTIAL** | Backend ma `cost_usd` i `conversions` w response. Endpoint `/trends` wspiera metrykę `cpa` (analytics.py:532,548). | `dashboard-kpis` nie liczy CPA wprost (analytics.py:320-327). Frontend nie wyświetla CPA. | **S** |
| K3 | Metryki wydajności w tabeli kampanii | **MISSING** | Tabela pokazuje: name, status, type, budget, sparkline, strategy (Dashboard.jsx:362-421). `GET /campaigns/` zwraca snapshot bez metryk performance. | Brak clicks/cost/conversions/ROAS per kampania w tabeli. Osobny endpoint `/campaigns/{id}/kpis` istnieje ale per-kampania, nie batchowo. | **M** |
| K4 | Szybkie akcje w InsightsFeed | **MISSING** | InsightsFeed.jsx jest display-only — wyświetla priority, message, detail. Brak jakichkolwiek przycisków. | Brak "Zastosuj" / "Przejdź do rekomendacji" / link do /recommendations | **M** |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| N1 | Impression Share / Lost IS na dashboardzie | **BACKEND_ONLY** | Pełna implementacja: endpoint `/analytics/impression-share`, model MetricDaily z polami `search_impression_share`, `search_budget_lost_is`, `search_rank_lost_is`. Frontend używa tego na stronie Campaigns.jsx (linie 69-71, 214-216). | Dashboard nie importuje ani nie wyświetla impression share. Dane są, brakuje widgetu na dashboardzie. | **M** |
| N2 | Wasted Spend indicator | **BACKEND_ONLY** | Pełna implementacja: endpoint `/analytics/wasted-spend` (analytics.py:893-909), serwis `get_wasted_spend()` (analytics_service.py:1333+). Frontend używa na stronie SearchOptimization.jsx (linia 1250). | Dashboard nie importuje ani nie wyświetla wasted spend. Dane są, brakuje widgetu. | **S** |
| N3 | WoW comparison chart | **MISSING** | KPI cards mają period-over-period `change_pct` — ale to porównanie equal-length periods, nie stricte WoW. Brak dedykowanego komponentu WoW. | Brak wizualnego porównania tydzień-do-tygodnia (np. overlay chart current vs previous week). | **L** |
| N4 | Quick filters na dashboardzie | **NOT_NEEDED** | Dashboard czyta z FilterContext (Dashboard.jsx:168). Filtry w Sidebar działają globalnie — campaign_type, status, period. Tabela kampanii filtruje in-memory (Dashboard.jsx:236-244). | Filtry na dashboardzie byłyby duplikacją sidebara. Obecne rozwiązanie jest spójne z resztą aplikacji. | — |

### ZMIANY/USUNIECIA

| # | Element | Status | Aktualny stan | Rekomendacja | Naklad |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Sparkline 72x24 w tabeli | **NOT_NEEDED** | Sparkline 72x24px, color-coded (red=up cost, green=down) — Dashboard.jsx:148-163. | Sparkline daje szybki visual cue o kierunku kosztów. Lepiej dodać kolumny metryk OBOK sparkline niż go usuwać. Zachować. | — |
| Z2 | Geo "Top miasta" brak share_cost_pct | **PARTIAL** | Backend geo-breakdown zwraca `share_cost_pct` (analytics_service.py:956). Frontend ignoruje — tabela wyświetla tylko city, clicks, cost_usd, roas (Dashboard.jsx:581-596). | Dodać kolumnę `% kosztu` do geo tabeli — dane już dostępne, 5 min pracy. | **S** |

### NAWIGACJA (brakujące połączenia)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| NAV1 | Kliknięcie kampanii → /campaigns | **MISSING** | Wiersz tabeli ma tylko hover styling (onMouseEnter/Leave). Brak onClick, Link, navigate. Dashboard.jsx nie importuje useNavigate ani Link. | Dodać onClick na wierszu → navigate(`/campaigns?highlight=${c.id}`) | **S** |
| NAV2 | InsightsFeed link → /recommendations | **MISSING** | InsightsFeed.jsx — brak jakiejkolwiek nawigacji. | Dodać link/przycisk "Zobacz w rekomendacjach" per insight | **S** |
| NAV3 | Health Score → /alerts | **PARTIAL** | HealthScoreCard (Dashboard.jsx:36-111) wyświetla issues ale nie linkuje do /alerts. | Dodać kliknięcie na HealthScoreCard → navigate('/alerts') | **S** |
| NAV4 | "Zobacz wszystkie" na sekcjach | **MISSING** | Budget Pacing, Device, Geo — brak linków "więcej". | Dodać "Zobacz wszystkie →" linkujące do odpowiednich zakładek | **S** |

---

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, ~2h łącznie):
  [ ] K1 — Dodać CTR + Impressions do KPI cards (Dashboard.jsx)
  [ ] K2 — Dodać CPA do dashboard-kpis endpoint + KPI card
  [ ] Z2 — Dodać kolumnę % kosztu do geo tabeli (Dashboard.jsx)
  [ ] N2 — Dodać Wasted Spend widget na dashboard (endpoint gotowy)
  [ ] NAV1 — Kliknięcie kampanii → /campaigns
  [ ] NAV3 — Health Score kliknięcie → /alerts
  [ ] NAV4 — Linki "Zobacz wszystkie" na sekcjach

Sprint 2 (sredni naklad — M, ~4h łącznie):
  [ ] K3 — Metryki wydajności w tabeli kampanii (wymaga batch endpoint lub rozszerzenia /campaigns)
  [ ] K4 — Przyciski akcji w InsightsFeed
  [ ] NAV2 — Link z InsightsFeed do /recommendations
  [ ] N1 — Widget Impression Share na dashboardzie

Sprint 3 (duzy naklad — L, opcjonalny):
  [ ] N3 — WoW comparison chart (nowy komponent + potencjalnie nowy endpoint)
```

---

## Szczegoly implementacji

### Sprint 1

#### K1: CTR + Impressions w KPI cards
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany backend**: BRAK — endpoint `dashboard-kpis` już zwraca `impressions` i `ctr`
- **Zmiany frontend**: Zmienić grid z `repeat(4, 1fr)` na `repeat(3, 1fr)` w 2 rzędach LUB `repeat(6, 1fr)`. Dodać 2 nowe MiniKPI:
  ```jsx
  <MiniKPI title="Wyświetlenia" value={current?.impressions} change={change_pct?.impressions} icon={Eye} iconColor="#7B5CE0" />
  <MiniKPI title="CTR" value={current?.ctr} change={change_pct?.ctr} suffix="%" icon={MousePointerClick} iconColor="#4F8EF7" />
  ```
- **Import**: dodać `Eye` z lucide-react
- **Testy**: test_dashboard_kpis.py już pokrywa endpoint

#### K2: CPA w KPI
- **Pliki do modyfikacji**: `backend/app/routers/analytics.py` (linia 320-327), `frontend/src/pages/Dashboard.jsx`
- **Zmiany backend**: W funkcji `_agg()` dodać po linii 326:
  ```python
  "cpa": round((total_cost_usd / total_conversions) if total_conversions else 0, 2),
  ```
- **Zmiany frontend**: Dodać MiniKPI card:
  ```jsx
  <MiniKPI title="CPA" tooltip="Cost Per Acquisition" value={current?.cpa} change={change_pct?.cpa} suffix=" zł" icon={DollarSign} iconColor="#F87171" />
  ```
  Uwaga: dla CPA trend odwrócony — spadek = dobrze
- **Testy**: rozszerzyć test_dashboard_kpis.py o asercję na pole `cpa`

#### Z2: Kolumna % kosztu w geo tabeli
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx` (linie 581-596)
- **Zmiany backend**: BRAK — `share_cost_pct` już w response
- **Zmiany frontend**: Dodać 'Udział' do headerów tabeli geo i dodać `<td>`:
  ```jsx
  <td ...>{c.share_cost_pct}%</td>
  ```

#### N2: Wasted Spend widget
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`, `frontend/src/api.js`
- **Zmiany backend**: BRAK — endpoint `/analytics/wasted-spend` istnieje
- **Zmiany frontend**:
  1. Import `getWastedSpend` z api.js (już eksportowane — używane w SearchOptimization.jsx)
  2. Dodać fetch w `loadData()` secondary data
  3. Dodać mini card/widget: `Wasted Spend: {waste_pct}% ({total_waste_usd} zł)` z kolorem wg thresholdu (<15% green, 15-25% yellow, >25% red)
- **Dane**: seed generuje dane — SearchOptimization już to używa

#### NAV1: Kliknięcie kampanii → /campaigns
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany frontend**:
  1. `import { useNavigate } from 'react-router-dom'`
  2. W komponencie: `const navigate = useNavigate()`
  3. Na `<tr>` kampanii dodać: `onClick={() => navigate('/campaigns')}` + `style={{ cursor: 'pointer' }}`

#### NAV3: Health Score → /alerts
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany frontend**: Opakować HealthScoreCard w `<div onClick={() => navigate('/alerts')} style={{ cursor: 'pointer' }}>` lub dodać prop `onClick` do komponentu

#### NAV4: Linki "Zobacz wszystkie"
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany frontend**: Przy headerach sekcji Budget Pacing, Device, Geo dodać:
  ```jsx
  <span onClick={() => navigate('/campaigns')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>
    Zobacz wszystkie →
  </span>
  ```

---

### Sprint 2

#### K3: Metryki wydajności w tabeli kampanii
- **Pliki do modyfikacji**: `backend/app/routers/analytics.py` lub `campaigns.py`, `frontend/src/pages/Dashboard.jsx`
- **Zmiany backend**: Nowy endpoint `GET /analytics/campaigns-summary?client_id=X&days=Y` zwracający per-campaign aggregated metrics (clicks, cost, conversions, roas) — lub rozszerzenie `dashboard-kpis` o breakdown per campaign
- **Zmiany frontend**: Dodać kolumny: Koszt, Konwersje, ROAS do tabeli kampanii. Joinować dane z campaigns response + nowy endpoint po campaign_id
- **Dane**: MetricDaily ma campaign_id — wystarczy GROUP BY campaign_id
- **Testy**: nowy test na endpoint campaigns-summary

#### K4 + NAV2: Akcje w InsightsFeed + link do /recommendations
- **Pliki do modyfikacji**: `frontend/src/components/InsightsFeed.jsx`
- **Zmiany frontend**:
  1. Dodać prop `onNavigate` lub użyć `useNavigate` bezpośrednio
  2. Per insight dodać przycisk: `<button onClick={() => navigate('/recommendations')}>Przejdź →</button>`
  3. Dla executable recommendations: dodać "Zastosuj" button z `POST /recommendations/{id}/apply`

#### N1: Impression Share widget
- **Pliki do modyfikacji**: `frontend/src/pages/Dashboard.jsx`, `frontend/src/api.js`
- **Zmiany backend**: BRAK — endpoint `/analytics/impression-share` istnieje
- **Zmiany frontend**: Nowa sekcja/card obok Device breakdown:
  - Import `getImpressionShare` z api.js
  - Mini gauge lub bar chart: `Search IS: 72%`, `Lost (Budget): 15%`, `Lost (Rank): 13%`
  - Color coding: IS > 80% green, 50-80% yellow, <50% red

---

### Sprint 3

#### N3: WoW comparison chart
- **Pliki do modyfikacji**: nowy komponent `frontend/src/components/WoWChart.jsx`, `backend/app/routers/analytics.py`
- **Zmiany backend**: Potencjalnie nowy endpoint `/analytics/wow-comparison` — lub reuse `/trends` z parametrem `compare_previous=true`
- **Zmiany frontend**: Overlay chart — bieżący tydzień (solid line) vs poprzedni tydzień (dashed line) dla wybranej metryki
- **Testy**: test na endpoint + komponent
- **Uwaga**: Ten element jest opcjonalny — TrendExplorer częściowo pokrywa tę potrzebę
