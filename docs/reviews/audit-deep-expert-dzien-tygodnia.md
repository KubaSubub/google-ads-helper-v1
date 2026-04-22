# /audit-deep ETAP 2 — ads-expert (Google Ads expert, 10+ lat)

Tab: dzien-tygodnia → DayOfWeekWidget (Dashboard) + DaypartingSection (Audit Center)

Sprawdzone obszary: walutowe konwersje, micros, kontrakt API, edge cases, kompletnosc metryk Google Ads, zgodnosc z playbookiem (`google_ads_optimization_playbook.md` -> sekcja "Ad Schedule / Dayparting").

Findings powstaly z syntezy raportu ads-user (`docs/reviews/audit-deep-user-dzien-tygodnia.md`) + wlasna analiza kodu.

---

## Findings

### [P0] CPA/CPC w UI etykietowane jako "zl" / "zł" mimo ze backend liczy w USD (cost_micros / 1_000_000)
- Gdzie: `backend/app/services/analytics_service.py:1576` (`cost = a["cost_micros"] / 1_000_000`), `backend/app/services/analytics_service.py:1584` (klucz `cost_usd`), `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:11,14`, `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:27`
- Problem: micros sa juz w walucie konta (Google Ads zwraca cost w currency klienta — domyslnie PLN dla polskich kont). Etykieta backendu `cost_usd` to **klamstwo nazewnicze** — to jest waluta konta. UI doleja " zl"/" zł" do tej wartosci, co dla wielu klientow daje wlasciwy wynik **przypadkowo**, ale dla klienta z USD-account daje bledne dolarowe wartosci podpisane "zl".
- Fix: 
  1. Zmienic w backendzie wszystkie nazwy `cost_usd` -> `cost` (lub `cost_amount`) — to nie jest USD.
  2. W odpowiedzi dolaczyc `currency` z `clients.currency` (np. "PLN").
  3. UI: `{cost.toFixed(2)} {data.currency}`.
- Playbook ref: zasada projektu (`AGENTS.md` sekcja Core Rules) — "Keep Google Ads money values in micros at storage level"; konsekwencja: po dzieleniu nazewnictwo musi odzwierciedlac waluty konta.

### [P0] Heatmap renderuje "avg: —" dla 4 z 6 metryk (CPA/ROAS/CVR/CPC) bo backend nie zwraca avg_cpa/avg_roas/avg_cvr/avg_cpc
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:153-158` (`d['avg_' + metric]`), `backend/app/services/analytics_service.py:1586-1588` (zwracane: `avg_clicks`, `avg_cost_usd`, `avg_conversions`)
- Problem: dla 4/6 metryk operator widzi pusty napis "avg: —". Sugeruje brak danych, gdy w rzeczywistosci to po prostu nie zaimplementowane.
- Fix:
  1. Backend dodaje `avg_cpa`, `avg_roas`, `avg_cvr`, `avg_cpc` (kazdy = metric / count, gdzie count = liczba wystapien tego dnia w oknie).
  2. Albo frontend ukrywa linie "avg" dla metryk bez tej wartosci (warunek `d[avg_${metric}] != null`).
- Playbook ref: nie dotyczy bezposrednio, kwestia kompletnosci kontraktu.

### [P0] Duplikat @router.get("/dayparting") w analytics.py — drugi handler nadpisuje pierwszy w czasie rejestracji
- Gdzie: `backend/app/routers/analytics.py:1367` (day-of-week, kontrakt `{period_days, days[]}`), `backend/app/routers/analytics.py:1498` (hour-of-day, kontrakt `{hours[], overall, suggestions}`)
- Problem: Te same metoda i sciezka w jednym `APIRouter`. FastAPI nie rzuca bledem, ale routing zaleznie od kolejnosci moze przekierowac na drugi handler. `DayOfWeekWidget` i `useAuditData` oczekuja kontraktu pierwszego — drugi jest dla godzin.
- Fix:
  1. Drugiego handlera (linia 1498) usunac — `/hourly-dayparting` (linia 1708) juz istnieje i pokrywa hour-of-day.
  2. Albo zmienic prefix na `/dayparting/hourly`.
  3. Dodac assertion w testach: `assert len([r for r in app.routes if r.path == '/analytics/dayparting']) == 1`.
- Playbook ref: nie dotyczy, kwestia higieny route'ow.

### [P0] Default campaign_type = "SEARCH" odcina PMax/Shopping/Display — dla restauracyjnego (Sushi) i e-com klientow widget pokazuje niepelne dane bez ostrzezenia
- Gdzie: `backend/app/services/analytics_service.py:1548` (`campaign_type or "SEARCH"`), filtr `_filter_campaigns:44` (`if campaign_type and campaign_type != "ALL"`)
- Problem: Gdy frontend nie przekaze parametru, backend wklada "SEARCH" — czyli day-of-week nigdy nie pokazuje calkowitej skali, jezeli klient ma PMax/Shopping. Dashboard nie ma globalnego selektora typu kampanii w domyslnym widoku, wiec uzytkownik nie wie ze patrzy tylko na Search.
- Fix:
  1. Default zmienic na `"ALL"` (zgodnie z `_filter_campaigns` ktory traktuje `None`/`ALL` jak "wszystkie").
  2. Albo w odpowiedzi zwrocic `campaign_type_used: "SEARCH"` i UI to wyswietla.
- Playbook ref: `google_ads_optimization_playbook.md` — sekcja "Ad schedule" wymaga decyzji na podstawie **calego konta**, nie tylko Search.

### [P1] DayOfWeekWidget nie pokazuje dlugosci okresu, mimo ze backend zwraca period_days
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:96-120` (header bez period_days), `backend/app/services/analytics_service.py:1595` (`return {"period_days": period_days, "days": ...}`)
- Problem: Bez zakresu dat operator nie wie czy wartosci sa istotne statystycznie (1 wystapienie wtorku vs 12 wystapien wtorku to inna pewnosc).
- Fix: w naglowku obok tytulu dorzucic `<span>{data.period_days}d, n={Math.floor(data.period_days/7)} wystapien/dzien</span>`. Plus tooltip ostrzegajacy gdy n < 4.
- Playbook ref: wymog "minimum 4 obserwacje per bucket dla decyzji bid".

### [P1] DayOfWeekWidget i DaypartingSection nie pokazuja conversion_value / ROAS jako koloru — Marek widzi "klikow duzo w piatek" ale nie wie czy to przyniosloby zysk
- Gdzie: `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:21-24` (rysuje tylko 2 slupki: clicks i conversions), `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:8-15` (lista 6 metryk, brak conversion_value)
- Problem: Brakuje wartosci konwersji jako 1st-class metryki w bento. Dla e-com to **najwazniejsza** wartosc do dayparting.
- Fix: dodac metryki `conversion_value` i `aov` (avg order value = conv_value / conversions) do listy METRICS.
- Playbook ref: hierarchia metryk — value > conversions > clicks > impressions.

### [P1] Brak per-godzinowego widoku w DayOfWeekWidget, mimo ze tab nazywa sie "dzien-tygodnia" — playbook zaleca DOW × HOUR macierz 7×24
- Gdzie: separacja `DayOfWeekWidget` (Dashboard, 7 kafelkow) vs `HourlyDaypartingSection` (Audit Center, 24 kafelki) — brak laczonej wizualizacji.
- Problem: real Google Ads bid schedule ustawia sie per (DOW, HOUR) ramka. Operator musi recznie kojarzyc dwie wizualizacje.
- Fix: dodac 7×24 heatmap (z `MetricSegmented` ktory ma `day_of_week` + `hour_of_day`). Backend juz ma surowe dane (`backend/app/models/metric_segmented.py`).
- Playbook ref: "Ad Schedule" — granularnosc DOW×HOUR.

### [P1] Brak istotnosci statystycznej — widget oznacza dzien jako "best" nawet gdy roznica jest w ramach szumu (5 klikow vs 4)
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:92-93` (`bestIdx = values.indexOf(Math.max(...values))`)
- Problem: Best/Worst sa marker'owane bez progu istotnosci. Dla niskotrafficznego konta (np. <100 kliknieciow/dzien) Marek dostaje sugestie na podstawie szumu.
- Fix: dodac prog np. "best wymaga >= 1.2x median i >= 30 obserwacji". Gdy nie spelnia — nie pokazuj highlight + tooltip "zbyt malo danych".
- Playbook ref: progi minimum cost / kliknieciow przed bid changes.

### [P2] DaypartingSection nie ma filtra metryki (jest hardcoded clicks + conversions + CPA), DayOfWeekWidget ma 6 metryk — niespojnosc
- Gdzie: `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:8-30` vs `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:8-15,104-119`
- Problem: Audit Center to "powerusera widok" — powinien miec **wiecej** metryk niz Dashboard, nie mniej.
- Fix: zunifikowac komponenty — uzyc `DayOfWeekWidget` jako bazowego, dodac w Audit Center extra rzad z bid suggestion.
- Playbook ref: nie dotyczy, kwestia DRY.

### [P2] DayOfWeekWidget nie reaguje na error 4xx/5xx z toastem — chowanie pod `null` ukrywa awarie
- Gdzie: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:64-70` (catch ustawia error i toast), `:74-81` (renderuje error tylko gdy `error && !data`), `:83` (`return null` gdy brak `data?.days?.length`)
- Problem: Gdy odpowiedz przyjdzie z `days: []` (np. dla nowego klienta bez metryk) — widget znika bez sladu. Brak komunikatu "Brak danych dnia tygodnia w wybranym okresie".
- Fix: zwracac pusty stan z message zamiast `return null`.
- Playbook ref: UX.

### [P2] Brak dat w nazwach kolumn — "Pn"/"Wt" nie wskazuja konkretnych dni; przy 7-dniowym oknie operator chcialby zobaczyc daty
- Gdzie: `backend/app/services/analytics_service.py:1571` (statyczne `["Pn", "Wt", ...]`)
- Problem: Dla okien <= 14 dni warto pokazac "Pn (15.04, 22.04)".
- Fix: gdy period_days <= 21, dolaczac `dates: ["15.04", "22.04"]` per dzien.
- Playbook ref: nie dotyczy.

### [P3] DOW_NAMES hardcoded po polsku — brak i18n, ale projekt jest LOCAL-ONLY polski wiec OK
- Gdzie: `backend/app/services/analytics_service.py:1571`
- Problem: brak — zgodne z polityka projektu.
- Fix: brak.
- Playbook ref: brak.

---

Findings: 12 (P0 x4, P1 x4, P2 x3, P3 x1)
