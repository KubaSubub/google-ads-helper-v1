# Audit Deep — Dzien tygodnia (DayOfWeekWidget on Dashboard + DaypartingSection in Audit Center)
> Data: 2026-04-19 | Findings: 16 (po deduplikacji) | Critic: APPROVED

Zrodla:
- ads-user: `docs/reviews/audit-deep-user-dzien-tygodnia.md`
- ads-expert: `docs/reviews/audit-deep-expert-dzien-tygodnia.md`

Komponenty:
- `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx`
- `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx`

Backend:
- `backend/app/routers/analytics.py` (linia 1367 + duplikat 1498)
- `backend/app/services/analytics_service.py:get_dayparting:1538`

---

## Findings (posortowane P0 -> P3)

### [P0] Duplikat @router.get("/dayparting") w analytics.py — drugi handler nadpisuje pierwszy
- Gdzie: `backend/app/routers/analytics.py:1367` (day-of-week, kontrakt `{period_days, days[]}`) vs `backend/app/routers/analytics.py:1498` (hour-of-day, kontrakt `{hours[], overall, suggestions}`)
- Problem: Dwa handlery na tej samej sciezce GET /analytics/dayparting w jednym routerze. FastAPI nie rzuca bledem, ale jeden z nich nigdy sie nie uruchomi. `DayOfWeekWidget` oczekuje pierwszego kontraktu — drugi dostarcza dane godzinowe.
- Fix: usunac drugi handler (linia 1498) — `/hourly-dayparting` (linia 1708) juz pokrywa hour-of-day. Dodac assertion w testach: `assert sum(1 for r in app.routes if getattr(r, 'path', None) == '/analytics/dayparting') == 1`.

### [P0] CPA/CPC z sufiksem " zl"/" zł" mimo ze backend liczy w walucie konta nazwanej "USD"
- Gdzie: `backend/app/services/analytics_service.py:1576,1584` (klucz `cost_usd`), `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:11,14`, `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:27`
- Problem: Nazwa `cost_usd` to klamstwo nazewnicze — to jest waluta konta klienta. UI sklada "X zl" do tej wartosci. Dla klientow PLN-account dziala przypadkowo, dla USD-account podpisuje USD jako "zl".
- Fix: 
  1. Zmienic w odpowiedzi `cost_usd` -> `cost_amount` + dodac `currency: clients.currency`.
  2. UI: `{cost.toFixed(2)} {data.currency}`.
  3. Playbook: `AGENTS.md` Core Rules — micros to currency-of-account, nie USD.

### [P0] Heatmap pokazuje "avg: —" dla 4 z 6 metryk (CPA/ROAS/CVR/CPC)
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:153-158` (`d['avg_' + metric]`) vs `backend/app/services/analytics_service.py:1586-1588` (zwraca tylko `avg_clicks`, `avg_cost_usd`, `avg_conversions`)
- Problem: Dla metryk CPA, ROAS, CVR, CPC kafelek pokazuje "avg: —". Operator sadzi ze brak danych, gdy faktycznie pole nie zostalo wyliczone.
- Fix:
  1. Backend: dodac `avg_cpa = cost / count_with_conv`, `avg_roas = cv / cost_per_period`, `avg_cvr = conversions / clicks`, `avg_cpc = cost / clicks`.
  2. Albo frontend: ukryj linie avg gdy pole `null` (`d[avg_${metric}] != null`).

### [P0] Default campaign_type = "SEARCH" odcina PMax/Shopping/Display bez ostrzezenia
- Gdzie: `backend/app/services/analytics_service.py:1548` (`campaign_type or "SEARCH"`)
- Problem: Gdy frontend nie poda parametru, backend automatycznie filtruje do SEARCH. Dla klienta z PMax (Sushi Naka Naka, Klimfix) widget pokazuje czesciowe dane, brak komunikatu "tylko Search".
- Fix:
  1. Default na `"ALL"` (zgodne z `_filter_campaigns:44`).
  2. Zwracac `campaign_type_used: "SEARCH"` w odpowiedzi i UI to wyswietla.

### [P0] Po zmianie metryki na CPA/ROAS heatmap renderuje "avg: —" (powiazane z findingiem #3, ale tu o user impact)
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:104-119` (przelacznik metryk)
- Problem: Marek klikajac CPA dostaje 7 kafelkow z napisem "avg: —" i czuje ze widget nie dziala.
- Fix: jak finding #3.

### [P1] Brak okresu / liczby dni w naglowku — backend zwraca period_days, UI go nie pokazuje
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:97-120`, `backend/app/services/analytics_service.py:1595` (`period_days` w odpowiedzi)
- Problem: Bez wskazania zakresu Marek nie wie czy 12 klikniec/wtorek to 1 wystapienie czy 12. Nie ocenia istotnosci statystycznej.
- Fix: w naglowku `<span>{data.period_days}d, n={Math.floor(data.period_days/7)} obs/dzien</span>`. Tooltip ostrzegawczy gdy n < 4.

### [P1] Best/Worst highlight tylko dla "wieksze=lepsze" — dla CPA/CPC operator widzi ring na zlym dniu
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:126-131,139`
- Problem: `boxShadow` highlight stosowany tylko dla `isBest || isBestInv` — worst nigdy nie ma czerwonego ringu. Brak symetrii w wizualizacji.
- Fix: dodac drugi ring `border: 2px solid red` dla worst-case dnia. Plus krotka legenda "Najlepszy / Najgorszy".

### [P1] Brak akcji wynikajacej z heatmapy — operator nie ma jak przekuc spostrzezenia w bid schedule
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:96-165`, `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx`
- Problem: Czysto wizualny widget. Brak rekomendacji "obniz stawki we wtorek o -25%" mimo ze identyczna logika juz istnieje dla godzin (`backend/app/services/dayparting_service.py:bid_schedule_suggestions:124`).
- Fix: stworzyc `dow_bid_schedule_suggestions(db, client_id, days)` analogicznie do hourly. Pokazac panel pod heatmapa.

### [P1] Brak conversion_value / AOV jako pierwszoligowych metryk — krytyczne dla e-com dayparting
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:8-15` (METRICS list)
- Problem: Lista metryk kontroluje co operator widzi. Brak `conversion_value` / `aov` (avg order value = conv_value / conversions). Dla restauracji / e-com to **najwazniejsze** dla decyzji per-DOW.
- Fix: backend juz liczy `conv_value_micros` (`analytics_service.py:1568,1577`). Dodac do `days_data`: `conv_value_usd`, `aov_usd`. Dodac do METRICS w UI.

### [P1] Brak per-godzinowego widoku DOW × HOUR — playbook zaleca 7×24 macierz dla bid schedule
- Gdzie: separacja `DayOfWeekWidget` (Dashboard, 7 kafelkow) i `HourlyDaypartingSection` (Audit Center, 24 kafelki) — brak laczonej wizualizacji
- Problem: Real Google Ads bid schedule edytuje sie per (DOW, HOUR) ramka. Operator musi recznie kojarzyc dwie wizualizacje.
- Fix: dodac heatmap 7×24 — `MetricSegmented` ma `day_of_week` + `hour_of_day` (`backend/app/models/metric_segmented.py`).

### [P1] Brak istotnosci statystycznej — best/worst marker'owany nawet przy szumie (5 vs 4 kliki)
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:92-93`
- Problem: `bestIdx = values.indexOf(Math.max(...values))` bez progu. Niskotrafficzne konta dostaja zlowrogi sygnal na podstawie szumu.
- Fix: prog "best wymaga >= 1.2x median i >= 30 obserwacji". Inaczej brak highlight + tooltip "zbyt malo danych".

### [P2] DaypartingSection oznacza weekend zawsze na czerwono niezaleznie od metryki
- Gdzie: `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:11,15-18`
- Problem: `isWeekend = d.day_of_week >= 5` -> czerwona ramka i czerwony naglowek, niezaleznie od tego czy w soboty CPA jest swietny czy zly. Dla restauracji sobota = top day.
- Fix: kolor wg metryki (jak w `DayOfWeekWidget`). "Weekend" co najwyzej drobna ikona kalendarza.

### [P2] Brak comparison do prev period — pozostale karty AuditCenter to maja, dayparting nie
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:62`, `frontend/src/features/audit-center/hooks/useAuditData.js:69-89`
- Problem: Operator nie wie "wtorek pogorszyl sie o +18% CPA vs poprzedni miesiac".
- Fix: dorzucic prev-period call. Na kazdym kafelku mala delta vs poprzedni okres.

### [P2] DaypartingSection ma hardcoded 3 metryki, DayOfWeekWidget ma 6 — niespojnosc Audit Center vs Dashboard
- Gdzie: `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:8-30` vs `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:8-15`
- Problem: Audit Center to power-user view, powinien miec **wiecej** metryk, nie mniej.
- Fix: zunifikowac — uzyc `DayOfWeekWidget` jako bazowego, w Audit Center dodac extra rzad z bid suggestions.

### [P2] Brak loading state w DayOfWeekWidget — widget nagle "wyskakuje" gdy dane przyjda
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:83`
- Problem: `if (!data?.days?.length) return null` — przed zaladowaniem widget znika. Inne karty Dashboard maja skeleton.
- Fix: skeleton card podczas ladowania (loading state).

### [P2] Brak dat w nazwach kolumn dla okien <= 14 dni
- Gdzie: `backend/app/services/analytics_service.py:1571`
- Problem: "Pn"/"Wt" nie sygnalizuje ktora konkretna data. Dla okna 7d to akurat 1 wystapienie kazdego dnia.
- Fix: gdy period_days <= 21, dolaczac `dates: ["15.04", "22.04"]` per dzien.

---

## Nastepne kroki

- [ ] **P0** Usunac duplikat `@router.get("/dayparting")` (linia 1498) i dodac assertion w `tests/test_analytics_endpoints.py`
- [ ] **P0** Backend: zmienic `cost_usd` -> `cost_amount` w odpowiedzi `get_dayparting`, dodac `currency`. UI: pokazac walute klienta.
- [ ] **P0** Backend: dodac `avg_cpa`, `avg_roas`, `avg_cvr`, `avg_cpc` do per-day response.
- [ ] **P0** Backend: zmienic default `campaign_type` z `"SEARCH"` na `"ALL"` w `analytics_service.get_dayparting:1548`.
- [ ] **P1** UI: dodac period_days + n=obs/dzien w naglowku `DayOfWeekWidget`.
- [ ] **P1** UI: dodac czerwony ring dla worst-day + legenda Best/Worst.
- [ ] **P1** Backend: stworzyc `dow_bid_schedule_suggestions` (analog hourly). UI: panel rekomendacji pod heatmapa.
- [ ] **P1** Backend+UI: dodac `conversion_value` i `aov` do dostepnych metryk.
- [ ] **P1** Backend+UI: heatmap DOW x HOUR (7x24) — uzyc `MetricSegmented`.
- [ ] **P1** UI: prog istotnosci statystycznej dla best/worst marker.
- [ ] **P2** UI: `DaypartingSection` przestaje hardcodowac weekend na czerwono — kolor wg metryki.
- [ ] **P2** UI: dodac prev-period delta do `DayOfWeekWidget`.
- [ ] **P2** Refactor: zunifikowac `DaypartingSection` z `DayOfWeekWidget`.
- [ ] **P2** UI: skeleton loading state w `DayOfWeekWidget`.
- [ ] **P2** Backend: dodac konkretne daty w odpowiedzi dla krotkich okien.
