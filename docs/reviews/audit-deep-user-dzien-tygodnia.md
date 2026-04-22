# /audit-deep ETAP 1 — ads-user (Marek, PPC specialist)

Tab: dzien-tygodnia → DayOfWeekWidget (Dashboard) + DaypartingSection (Audit Center)

Pliki ktore sprawdzilem:
- `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx`
- `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx`
- `frontend/src/features/audit-center/AuditCenterPage.jsx`
- `frontend/src/features/audit-center/hooks/useAuditData.js`
- `frontend/src/api.js` (getDayparting)

---

## Findings

### [P0] Przelaczam metryke na CPA / ROAS / CVR / CPC w heatmapie -> "avg" pokazuje "—" zamiast wartosci sredniej
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:153`
- Rzeczywiste: kod renderuje `d['avg_' + metric]` (`avg_cpa`, `avg_roas`, `avg_cvr`, `avg_cpc`). Backend (`backend/app/services/analytics_service.py:1586-1588`) zwraca tylko `avg_clicks`, `avg_cost_usd`, `avg_conversions`. Dla pozostalych metryk kafelek pokazuje stale "avg: —".
- Oczekiwane: dla kazdej metryki widoczna srednia (np. CPA per dzien = cost/conversions per dzien tygodnia podzielone przez liczbe wystapien) albo usuniecie linii avg dla metryk bez tej wartosci.

### [P0] CPA / CPC pokazane z sufiksem " zl" ale backend zwraca wartosci w USD
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:11,14` ("CPA ... zl"), `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:27` ("CPA {d.cpa.toFixed(0)} zł")
- Rzeczywiste: backend (`backend/app/services/analytics_service.py:1576` `cost = a["cost_micros"] / 1_000_000`, `1591` `cpa = cost / conversions`) liczy w USD (sam pole API to `cost_usd`). UI dokleja " zl" / " zł" do wartosci USD.
- Oczekiwane: konsekwentnie PLN — albo zmienic zrodlo (Klient ma walute w `clients.currency`), albo zmienic etykiete na "USD". Aktualnie operator widzi "CPA 12 zl" i podejmuje decyzje budzetowe na zlej walucie.

### [P0] Po zmianie campaign_type w GlobalFilterBar widget zawsze pokazuje SEARCH (PMax/Display nie sa wliczone)
- Selektor: `backend/app/services/analytics_service.py:1548` `self._filter_campaign_ids(client_id, campaign_type or "SEARCH", campaign_status)`
- Rzeczywiste: gdy frontend nie poda `campaign_type` (lub poda "ALL" -> ten parametr w `_filter_campaigns` traktowany jest "ALL" -> bez filtra, ale gdy nie jest podany w ogole to default to SEARCH). Dla klienta typu Sushi Naka Naka (PMax + Search) pokazuje tylko Search. Etykieta zakladki "Dzien tygodnia" niczym tego nie sygnalizuje.
- Oczekiwane: jezeli filtr "ALL" -> wszystkie typy. Default powinien byc "ALL" lub w UI powinno pojawic sie "(tylko Search)" gdy filtra brak.

### [P0] Duplikat endpointu @router.get("/dayparting") — drugi przeslania pierwszy w runtime
- Selektor: `backend/app/routers/analytics.py:1367` (day-of-week, AnalyticsService.get_dayparting) i `backend/app/routers/analytics.py:1498` (hour-of-day breakdown z `dayparting_service`)
- Rzeczywiste: FastAPI rejestruje obie funkcje na tej samej sciezce GET /analytics/dayparting. Drugi handler ma calkowicie inny kontrakt (zwraca `hours` + `suggestions` zamiast `days`). W zaleznosci od kolejnosci ladowania moze sie zwracac zly JSON, a frontend `DayOfWeekWidget` oczekuje `data.days`.
- Oczekiwane: zmienic druga rejestracje na np. `/dayparting-hourly` lub usunac (juz istnieje `/hourly-dayparting` w linii 1708). To jest realna mina ktora moze rozwalic widget przy jakims porzadku importow.

### [P1] Brak okresu / liczby dni w naglowku — Marek nie wie czy patrzy na 7 dni, 30 dni czy 90
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:97-120` (header)
- Rzeczywiste: header pokazuje tylko "Dzien tygodnia" + przyciski metryk. `data.period_days` z backendu (`analytics_service.py:1595`) jest dostepne ale nie wyswietlone.
- Oczekiwane: obok tytulu: "Dzien tygodnia (ostatnie 30 dni, 4 wystapienia / dzien)" — pomaga ocenic istotnosc statystyczna.

### [P1] Heatmap pokazuje "best/worst" highlight tylko gdy metryka jest "wieksza = lepsza" — dla CPA/CPC najlepszy dzien jest oznaczony zlym borderem
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:126-131,139` 
- Rzeczywiste: zmienne `isBest`/`isWorst` z `metricDef.invert` sa policzone, ale `boxShadow: highlight ? '0 0 0 1px rgba(74,222,128,0.4)' : 'none'` uzywa tylko `highlight = isBest || isBestInv`. Samo `border` nie roznicuje — wszystkie 7 kafelkow ma kolor heatmapy ale tylko jeden ma "ring". Brak rownoczesnego oznaczenia worst (np. czerwony ring) — Marek widzi tylko "ten dzien jest najlepszy", nie wie ktory jest najgorszy bez wpatrywania sie w kolor.
- Oczekiwane: obie wartosci graniczne maja widoczny ring (zielony best, czerwony worst), albo legenda "Najlepszy / Najgorszy" przy heatmapie.

### [P1] Brak akcji wynikajacej z heatmapy — widzac "wtorek = najgorszy CPA" Marek nie ma jak ustawic ad schedule
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:96-165` + `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:1-43`
- Rzeczywiste: widget jest czysto wizualny. Nie ma rekomendacji "obniz stawki we wtorek o -25%", nie ma linku do edytora harmonogramu Google Ads, nie ma export do CSV.
- Oczekiwane: dolaczyc panel "Sugerowane korekty harmonogramu" (analogicznie do `dayparting_service.bid_schedule_suggestions`, ktory juz istnieje dla godzin) z deltami CPA per dzien tygodnia + button "Skopiuj harmonogram".

### [P2] Brak comparison do poprzedniego okresu (delta vs prev)
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:62` (single `getDayparting` call)
- Rzeczywiste: TrendExplorer i AuditCenter maja prev-period (`useAuditData.js:69-89`), ale DayOfWeekWidget go nie uzywa. Brak informacji "wtorek pogorszyl sie o +18% CPA vs zeszly miesiac".
- Oczekiwane: dorzucic prev-period call, na kazdym kafelku male delta vs poprzedni okres (rgba zielone/czerwone +X%).

### [P2] DaypartingSection pokazuje weekend zawsze na czerwono niezaleznie od metryki
- Selektor: `frontend/src/features/audit-center/components/sections/DaypartingSection.jsx:11,15-18` (`isWeekend = d.day_of_week >= 5`, czerwona ramka i czerwony naglowek)
- Rzeczywiste: weekend jest oznaczany czerwono niezaleznie od tego czy w soboty CPA jest swietny czy zly. Dla restauracji (Sushi Naka Naka) sobota czesto = najlepszy dzien.
- Oczekiwane: kolor wynikajacy z metryki (jak heatmap w DayOfWeekWidget), a "weekend" co najwyzej drobnym znacznikiem (np. ikona kalendarza).

### [P2] Brak loading state — widget chowa sie do `null` gdy `data` nie jest jeszcze pobrane
- Selektor: `frontend/src/features/dashboard/components/DayOfWeekWidget.jsx:83` (`if (!data?.days?.length) return null`)
- Rzeczywiste: na wolnym laczu Dashboard ma "skok" — widget pojawia sie nagle. Inne karty (KPI, TrendExplorer) maja skeleton/loading.
- Oczekiwane: skeleton card podczas ladowania.

### [P3] Polskie nazwy dni po polsku ale skroty bez diacritics ("Sr" zamiast "Śr") — w innych miejscach uzywamy "Śr"
- Selektor: `backend/app/services/analytics_service.py:1571` `["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"]`
- Rzeczywiste: Backend zwraca "Śr" — OK. Ale UI etykiety w `DayOfWeekWidget.jsx:142` `textTransform: 'uppercase'` -> "ŚR" (uppercase z diacritic dziala w Chrome). Sprawdzilem — tu jest OK.
- Wniosek: brak bledu, ale warto trzymac. SKIP.

---

Findings: 10 (P0 x4, P1 x3, P2 x3, P3 x0)
