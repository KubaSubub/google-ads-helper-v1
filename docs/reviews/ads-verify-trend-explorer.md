# Plan implementacji — Trend Explorer
> Na podstawie: `docs/reviews/ads-expert-trend-explorer.md`
> Data weryfikacji: 2026-04-15

## Podsumowanie
- Elementow z raportu: **14** (3 x P0, 4 x P1, 4 x P2, 3 x P3)
- DONE: 0 | PARTIAL: 0 | MISSING: 14 | NOT_NEEDED: 0
- Szacowany naklad laczny: **duzy** (S: 5, M: 6, L: 3)

Kazdy punkt raportu eksperta zweryfikowany bezposrednio w kodzie (Read/Grep). Zero znalezionego "juz zrobione" — wszystkie 14 problemow sa realne.

---

## Status kazdego elementu

### KRYTYCZNE (P0 — must implement, blokuja codzienne uzycie)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 1 | CPA w correlation endpoint (400 Bad Request) | MISSING | `VALID_METRICS` w `analytics.py:28` bez `cpa`; frontend `CORRELATION_METRIC_MAP` TrendExplorer.jsx:26-35 bez `cpa` → silent drop; correlation_matrix L312-321 nie derywuje cpa | Dodac `"cpa"` do `VALID_METRICS`, dopisac mapping `cpa: 'cpa'` w froncie, derywacja `cpa = cost_usd / conversions` w daily_rows | S |
| 2 | ROAS zawsze 0 w mock mode | MISSING | `_mock_daily_data` L431-436 generuje 4 pola, `conv_value_micros` brak; `Keyword.conversion_value_micros` istnieje (kwerenda potwierdza) | Dodac sumowanie `total_conversion_value_micros` i rozdzielenie per-day z szumem | S |
| 3 | Scope kampanii rozjezdza sie (chart vs correlation) | MISSING | `getTrends` TrendExplorer.jsx:141-148 NIE wysyla `campaign_ids`; `getCorrelationMatrix` L307 wysyla `filteredCampaignIds` = tylko ENABLED (DashboardPage.jsx:248-253) | Zunifikowac: `fetchData` ma wysylac `campaign_ids` zbudowane tak samo jak correlation, albo usunac prop `campaignIds` i brac campaigny z sidebara w obu miejscach | M |

### KRYTYCZNE (P1 — must implement, retention po 1 tygodniu)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 4 | Forward-fill brakujacych dni w `get_trends` | MISSING | Petla L348-381 iteruje po `sorted(day_map.keys())` — pomija dni bez `MetricDaily` | Iteracja po `date_from..date_to` z zerami dla brakujacych dni (zeby ReferenceLine action markers renderowaly sie zawsze) | S |
| 5 | Naming metryk zunifikowany (`/trends` vs `/correlation`) | MISSING | `/trends` L843: `{cost, cpc, cvr, ...}`; `/correlation` VALID_METRICS: `{cost_micros, avg_cpc_micros, conversion_rate, ...}`; `CORRELATION_METRIC_MAP` tlumaczy jedno na drugie | Zunifikowac — rekomendacja: `/correlation` przyjmuje user-facing names (`cost`, `cpc`, `cvr`, `cpa`) i mapuje wewnetrznie; `CORRELATION_METRIC_MAP` usuniety | M |
| 6 | Per-campaign split (multi-line per kampania) | MISSING | Brak komponentu `CampaignPicker` (grep = 0 wynikow); `get_trends` zwraca jeden agregat | Nowy `<CampaignPicker />` w headerze widgetu (max 5), backend opcja `split_by=campaign` zwracajaca `{date, series: [{campaign_id, name, values}]}`, frontend rysuje N linii | L |
| 7 | Period-over-period overlay | MISSING | Brak endpointu `/trends-compare`, brak toggle w UI, brak renderu serii `prev_*` w ComposedChart | Parametr `compare_to=previous_period\|previous_year` do `/analytics/trends`, dodatkowe pola w response (`prev_*`), toggle w headerze, dodatkowe `<Line strokeDasharray="4 4">` per metryka | L |
| 8 | Empty state dla < 2 dni danych | MISSING | Backend zwraca `period_days` w response L389, ALE frontend nie czyta tego pola (grep `period_days` w `TrendExplorer.jsx` = 0 wynikow) | Wczytac `period_days` z response, pokazac empty state "Wybierz zakres co najmniej 2 dni" gdy `data.length < 2 \|\| period_days < 2` | S |

### NICE TO HAVE (P2)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 9 | Zoom/brush na osi czasu | MISSING | ComposedChart bez `<Brush>` (grep = 0 w TrendExplorer.jsx) | Dodac `<Brush dataKey="date" height={20} stroke={C.accentBlue} />` pod osia X | S |
| 10 | Rolling 14-day correlation | MISSING | `/correlation` robi global Pearson L329; brak `window` param, brak `rolling()` | Parametr `window=14` do endpointu, zwrot serii `{date, r}[]`, mini-sparkline pod wykresem | M |
| 11 | Tooltip pozycjonowanie / overflow przy 5 metrykach + 4 akcjach | MISSING | CustomTooltip L195-261 z `maxWidth: 340`, brak `position`/`offset`, brak accordion | Dodac `wrapperStyle` z `pointerEvents: 'auto'` + smart offset; accordion "Pokaz X akcji" domyslnie zwiniete lub limit 2 eventow | M |
| 12 | `cpa` w derived metrics correlation | MISSING | correlation_matrix L312-321 nie liczy cpa (powiazane z P0#1) | Dopisac do `daily_rows`: `"cpa": cost_usd / conversions if conversions else 0` (razem z P0#1) | S (w ramach P0#1) |

### DROBIAZGI (P3)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 13 | Dropdown close-on-outside-click zamyka oba popupy naraz | MISSING | `useEffect` L264-274 zamyka jednoczesnie `showCorrelationPopup` i `showDropdown` | Osobne warunki per popup (sprawdzac closest per data-attribute osobno) | S |
| 14 | Klikalne action markers (deeplink do Action History) | MISSING | `ReferenceLine` L607-617 nie ma `onClick` (Recharts nie wspiera) | Zamienic na `<Scatter>` z custom shape + onClick → `navigate('/actions?date={d}')` | M |
| 15 | Mock banner precyzyjny komunikat | MISSING | Banner L544-561: "Brak rzeczywistych danych — synchronizuj konto" | Zmienic tekst na "Caly wykres to dane symulowane (brak pobranych MetricDaily). Synchronizuj konto w sidebarze aby zobaczyc realne metryki." | S |

---

## Kolejnosc implementacji (rekomendowana)

### Sprint 1 — P0 quick wins (naklad S/M, ~2h)
```
[ ] Task 1 — CPA w correlation endpoint (P0#1 + P2#12 w jednym PR)
    Plik: backend/app/routers/analytics.py:28, 312-321
    Plik: frontend/src/components/TrendExplorer.jsx:26-35
    Naklad: S (15 min)

[ ] Task 2 — ROAS w mock mode
    Plik: backend/app/services/analytics_service.py:399-438 (_mock_daily_data)
    Naklad: S (15 min)

[ ] Task 3 — Scope kampanii chart vs correlation
    Plik: frontend/src/components/TrendExplorer.jsx:141-148 (fetchData)
    Plik: frontend/src/features/dashboard/DashboardPage.jsx:254-257 (filteredCampaignIds)
    Naklad: M (45 min)

[ ] Task 4 — Forward-fill brakujacych dni
    Plik: backend/app/services/analytics_service.py:289-397 (get_trends)
    Naklad: S (20 min)

[ ] Task 5 — Empty state dla period_days < 2
    Plik: frontend/src/components/TrendExplorer.jsx:146-158 (fetchData), 564-576 (render)
    Naklad: S (15 min)
```

### Sprint 2 — P1 feature parity (naklad M/L, ~6-8h)
```
[ ] Task 6 — Naming metryk zunifikowany
    Plik: backend/app/routers/analytics.py:262-335 (correlation_matrix)
    Plik: frontend/src/components/TrendExplorer.jsx:26-35, 296-328
    Naklad: M (1h — wymaga tez aktualizacji testow)

[ ] Task 7 — Period-over-period overlay
    Plik: backend/app/routers/analytics.py:817-856 (/trends)
    Plik: backend/app/services/analytics_service.py:289-397 (get_trends)
    Plik: frontend/src/components/TrendExplorer.jsx:351-541 (header), 618-634 (lines)
    Naklad: L (3h)

[ ] Task 8 — Per-campaign split (multi-line)
    Plik: frontend/src/components/CampaignPicker.jsx (NEW)
    Plik: backend/app/routers/analytics.py:817-856 (/trends + split_by)
    Plik: backend/app/services/analytics_service.py:289-397 (get_trends)
    Plik: frontend/src/components/TrendExplorer.jsx (state dla wybranych kampanii, render N linii)
    Naklad: L (3h)
```

### Sprint 3 — P2 advanced (naklad M, ~3-4h)
```
[ ] Task 9 — Zoom/brush
    Plik: frontend/src/components/TrendExplorer.jsx:579-636 (ComposedChart)
    Naklad: S (20 min)

[ ] Task 10 — Rolling 14-day correlation
    Plik: backend/app/routers/analytics.py:262-335 (correlation_matrix)
    Plik: frontend/src/components/TrendExplorer.jsx (mini-sparkline pod glownym wykresem)
    Naklad: M (1.5h)

[ ] Task 11 — Tooltip overflow/accordion
    Plik: frontend/src/components/TrendExplorer.jsx:195-261 (CustomTooltip)
    Naklad: M (45 min)
```

### Sprint 4 — P3 cosmetics (naklad S/M, ~1.5h)
```
[ ] Task 12 — Dropdown close-on-outside-click per popup
    Plik: frontend/src/components/TrendExplorer.jsx:264-274
    Naklad: S (10 min)

[ ] Task 13 — Klikalne action markers → deeplink do /actions?date=
    Plik: frontend/src/components/TrendExplorer.jsx:607-617 (ReferenceLine → Scatter)
    Plik: frontend/src/pages/ActionHistory.jsx (sprawdzic czy czyta ?date= z URL)
    Naklad: M (1h)

[ ] Task 14 — Mock banner text
    Plik: frontend/src/components/TrendExplorer.jsx:557-560
    Naklad: S (2 min)
```

---

## Szczegoly implementacji — Sprint 1 (kluczowy)

### Task 1 — CPA w correlation endpoint

**Pliki:**
- `backend/app/routers/analytics.py:28` — dopisz `"cpa"` do `VALID_METRICS`
- `backend/app/routers/analytics.py:312-321` — dopisz `"cpa": cost_usd / conversions if conversions else 0` do `daily_rows.append({...})`
- `frontend/src/components/TrendExplorer.jsx:26-35` — dodaj `cpa: 'cpa'` do `CORRELATION_METRIC_MAP`

**Backend:** minimalna zmiana, bez nowego endpointu

**Frontend:** tylko mapping

**Testy:** `backend/tests/test_analytics_endpoints.py::test_correlation_returns_200` rozszerz o `metrics=["cost_micros", "cpa"]`, expected: `r` dla pary w response

### Task 2 — ROAS w mock mode

**Pliki:**
- `backend/app/services/analytics_service.py:399-438` (`_mock_daily_data`)

**Zmiany:**
```python
# L417 — dodaj:
total_conv_value_micros = sum(k.conversion_value_micros or 0 for k in keywords)
# L423 — dodaj:
day_conv_value = total_conv_value_micros / days
# L431-436 — rozszerz day_map[current]:
day_map[current] = {
    "clicks": ...,
    "impressions": ...,
    "cost_micros": ...,
    "conversions": ...,
    "conv_value_micros": max(0, int(day_conv_value * noise())),
}
```

**Testy:** `backend/tests/test_new_analytics.py` (lub podobny) — test `get_trends` z pustym `MetricDaily`, sprawdz ze `row["roas"] > 0` dla dni z konwersjami

### Task 3 — Scope kampanii chart vs correlation

**Rekomendacja:** usun `campaignIds` prop z `TrendExplorer` i zostaw logike oparta o sidebar dla OBU wywolan.

**Pliki:**
- `frontend/src/features/dashboard/DashboardPage.jsx:254-257` — usun `filteredCampaignIds` i prop
- `frontend/src/features/dashboard/DashboardPage.jsx:382` — `<TrendExplorer />` bez propa
- `frontend/src/components/TrendExplorer.jsx:123` — usun `{ campaignIds = [] }` z props
- `frontend/src/components/TrendExplorer.jsx:307` — zamiast `campaign_ids: campaignIds`, wysylaj ten sam set co `fetchData` (czyli nie wysylaj `campaign_ids` wcale; backend filtruje przez `campaign_type`/`status`)
- `backend/app/routers/analytics.py:262-284` — rozszerz `CorrelationRequest` / endpoint o `campaign_type`, `campaign_status` zeby backend mogl filtrowac identycznie jak `/trends`

**Alternatywa (jesli chcemy zachowac pipeline campaignIds):** `fetchData` TEZ wysyla `campaign_ids: campaignIds` i oba identyczne — wymaga backend `get_trends` zeby obslugiwal `campaign_ids` bezposrednio (teraz nie obsluguje).

### Task 4 — Forward-fill brakujacych dni

**Pliki:**
- `backend/app/services/analytics_service.py:348-381`

**Zmiany:**
```python
# Po aggregacji, przed budowaniem output:
from datetime import timedelta
all_dates = []
current = date_from
while current <= date_to:
    all_dates.append(current)
    current += timedelta(days=1)

# W petli wymuszamy zerowy wiersz dla brakujacych:
for d in all_dates:
    agg = day_map.get(d, {"clicks": 0, "impressions": 0, "cost_micros": 0, "conversions": 0.0, "conv_value_micros": 0})
    ...
```

**Testy:** `test_trends_returns_200` — dodaj case `date_from=2025-01-01, date_to=2025-01-10` z `MetricDaily` tylko dla 3 dni, assert `len(data) == 10`

### Task 5 — Empty state dla `period_days < 2`

**Pliki:**
- `frontend/src/components/TrendExplorer.jsx:146-158` — zapisz `result.period_days` w stan
- `frontend/src/components/TrendExplorer.jsx:573-576` — warunek `data.length < 2` pokazuj "Wybierz zakres co najmniej 2 dni zeby zobaczyc trend"

**Dane:** bez zmian — backend juz zwraca `period_days` w response L389

**Testy:** frontend e2e — wybierz ten sam dzien w date pickerze, assert empty state text

---

## Pliki chronione

Zadne z zadan NIE dotyka:
- `backend/app/services/recommendations.py` (protected)
- `backend/app/services/analytics_service.py` — CLAUDE.md mowi "add new methods at end of file", ale tu MUSIMY modyfikowac istniejaca metode `get_trends` i `_mock_daily_data`. Jest to zgodne z duchem regul (fix bugu w istniejacej metodzie, nie refaktor), ale warto zaznaczyc w commit message.
- `backend/app/routers/analytics.py` — CLAUDE.md mowi "add new endpoints at end of file"; Task 7 (period-over-period) moze byc rozszerzeniem istniejacego endpointu `/trends` — nie nowym; alternatywnie mozna dodac nowy `/trends-compare` na koncu pliku zeby byc w zgodzie z regula.

---

## Podsumowanie statusu

- **DONE: 0**
- **MISSING: 14** (P0: 3, P1: 4, P2: 4, P3: 3; #12 scalone z #1)
- **PARTIAL: 0**
- **NOT_NEEDED: 0**

**Rekomendacja:** zacznij od **Sprint 1** — 5 zadan, ~2h laczenie, zamyka wszystkie 3 P0 + 2 z 4 P1. Po Sprincie 1 uruchom `/ads-check trend-explorer` zeby zweryfikowac fixy, potem Sprint 2 (feature parity) i dalej.
