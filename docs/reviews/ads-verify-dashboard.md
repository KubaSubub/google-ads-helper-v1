# Weryfikacja implementacji — Dashboard (Pulpit) — RE-TEST
> Na podstawie: docs/reviews/ads-expert-dashboard.md (re-test 2026-03-26)
> Data weryfikacji: 2026-03-26 | ads-check: 2026-03-26 — **9/9 DONE**

## Podsumowanie
- Elementow z raportu: 13
- **DONE: 10** | **PARTIAL: 0** | **MISSING: 0** | **NOT_NEEDED: 3**
- Szacowany naklad: maly (wiekszosc to frontend-only, kazdy < 30 min)
- **WSZYSTKIE TASKI WDROZONE** — ads-check potwierdził 2026-03-26

Zmiana vs poprzedni verify: WoW dates → DONE (naprawione), WoW legenda → NOT_NEEDED (juz byla po polsku).

---

## Status kazdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| K1 | Sortowanie tabeli kampanii | **DONE** | Tabela bez sort (Dashboard.jsx:430-503). Campaigns.jsx JUZ MA sort. | State sortBy/sortDir, klikalne `<th>`, useMemo sort | **S** |
| K2 | Deep-link do kampanii | **DONE** | `navigate('/campaigns')` (Dashboard.jsx:463) | Zmienic na `navigate('/campaigns?campaign_id=' + c.id)` | **S** |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| N1 | Klikalna karta Wasted Spend → /search-terms | **DONE** | Karta renderowana bez onClick (Dashboard.jsx:374-383) | Dodac onClick + cursor pointer | **S** |
| N2 | Link do /daily-audit z headerze | **DONE** | Brak linku w headerze (Dashboard.jsx:280-292) | Dodac "Poranny przeglad →" link | **S** |
| N3 | InsightsFeed filtr priorytetu | **DONE** | InsightsFeed sortuje ale nie filtruje (InsightsFeed.jsx:40) | State + pill buttons HIGH/MED/LOW | **S** |
| N4 | Sparkline tooltip | **DONE** | Sparkline bez `<Tooltip>` (Dashboard.jsx:165) | Dodac `<Tooltip>` z Recharts | **S** |
| N5 | Tooltip na kolumnie Strategia | **DONE** | `textOverflow: ellipsis` bez title (Dashboard.jsx:497) | Dodac `title={c.bidding_strategy}` | **S** |
| N6 | Sortowanie Geo tabelki | **DONE** | Statyczna tabelka (Dashboard.jsx:665-688) | Klikalne naglowki + state | **S** |
| N7 | IS per kampania w tabeli | **DONE** | Model Campaign ma search_impression_share. IS widget jest account-level. | Kolumna IS w tabeli + dane z campaigns_summary | **M** |

### DONE

| # | Element | Dowod |
|---|---------|-------|
| D1 | WoW chart z datami (zamiast nazw dni) | WoWChart.jsx:57-63 — formatDate() z cur?.date |

### NOT_NEEDED

| # | Element | Powod |
|---|---------|-------|
| X1 | WoW legenda po polsku | Juz jest: WoWChart.jsx:131 "Biezacy okres"/"Poprzedni okres" |
| X2 | Quick actions z dashboardu | L-size, nie blokuje MVP |
| X3 | Nic do usuniecia | Raport potwierdza — dashboard jest kompletny |

---

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, < 30 min kazdy):
  [ ] K1: Sortowanie tabeli kampanii — Dashboard.jsx
  [ ] K2: Deep-link do kampanii — Dashboard.jsx (1 linia)
  [ ] N1: Klikalna karta Wasted Spend → /search-terms — Dashboard.jsx
  [ ] N2: Link do /daily-audit — Dashboard.jsx (header)
  [ ] N4: Sparkline tooltip — Dashboard.jsx
  [ ] N5: Tooltip na Strategia — Dashboard.jsx (1 atrybut)

Sprint 2 (sredni naklad — S/M):
  [ ] N3: Filtr priorytetu w InsightsFeed — InsightsFeed.jsx
  [ ] N6: Sortowanie Geo tabelki — Dashboard.jsx
  [ ] N7: IS per kampania w tabeli — analytics.py + Dashboard.jsx
```

---

## Szczegoly implementacji

### K1: Sortowanie tabeli kampanii
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiany frontend**:
  - Dodac state: `const [sortBy, setSortBy] = useState('cost_usd')` + `const [sortDir, setSortDir] = useState('desc')`
  - Klikalne `<th>` z ikona sort — identyczny pattern jak w Campaigns.jsx (ktory juz ma sort)
  - W useMemo `filteredCampaigns` dodac `.sort()` uzywajac `campaignMetrics[c.id]` do pobrania wartosci
  - Sortowalne kolumny: Budzet/dzien, Koszt, Konwersje, ROAS
- **Backend**: bez zmian
- **Testy**: brak potrzeby (frontend-only)

### K2: Deep-link do kampanii
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: Linia 463 — `onClick={() => navigate('/campaigns')}` → `onClick={() => navigate('/campaigns?campaign_id=' + c.id)}`
- **Zaleznosc**: Sprawdzic czy Campaigns.jsx parsuje `campaign_id` z URL i auto-selectuje

### N1: Klikalna karta Wasted Spend
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: Linia 374-383 — dodac do MiniKPI Wasted Spend: wrapper `<div onClick={() => navigate('/search-terms?segment=WASTE')} style={{ cursor: 'pointer' }}>` lub nowa prop `onClick` na MiniKPI

### N2: Link do /daily-audit
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: W headerze (linia 280-292) dodac: `<span onClick={() => navigate('/daily-audit')} style={{ fontSize: 11, color: '#4F8EF7', cursor: 'pointer' }}>Poranny przegląd →</span>`

### N3: Filtr priorytetu w InsightsFeed
- **Pliki**: `frontend/src/components/InsightsFeed.jsx`
- **Zmiana**: State `filterPriority` (ALL/HIGH/MEDIUM/LOW), pill buttons w headerze, filtr w useMemo insights

### N4: Sparkline tooltip
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: W Sparkline component (linia 165) dodac `<Tooltip>` z minimalnym stylem dark theme

### N5: Tooltip na Strategia
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: Linia 497 — `<span>` → `<span title={c.bidding_strategy ?? ''}>`. Jedna linia.

### N6: Sortowanie Geo tabelki
- **Pliki**: `frontend/src/pages/Dashboard.jsx`
- **Zmiana**: State `geoSortBy`/`geoSortDir`, klikalne `<th>`, sort na `geoData.cities`

### N7: IS per kampania w tabeli
- **Pliki**: `backend/app/routers/analytics.py` (campaigns_summary linia 710+), `frontend/src/pages/Dashboard.jsx`
- **Backend**: Dodac `search_impression_share` z Campaign model do response campaigns_summary
- **Frontend**: Nowa kolumna "IS" miedzy ROAS a Trend. Kolorowanie: zielony >50%, zolty >30%, czerwony <30%
- **Testy**: Rozszerzyc `test_campaigns_summary.py`
