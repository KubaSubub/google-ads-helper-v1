# Ocena eksperta Google Ads — Trend Explorer
> Data: 2026-04-15 | Srednia ocena: 7.0/10 | Werdykt: ZACHOWAC Z MODYFIKACJAMI (P0/P1 blokery do naprawy przed codziennym uzyciem)

### TL;DR
Killer feature (action annotations + Pearson popup) dziala, ale pod spodem siedza dwa P0: (1) `VALID_METRICS` w `correlation_matrix` nie zawiera `cpa`, wiec dodanie CPA do metryk wysyla backendowi 400, (2) mock path w `_mock_daily_data` nie generuje `conv_value_micros`, wiec ROAS w mock mode to zawsze 0 (mylace dane na fresh instance). Dodatkowo scope korelacji i wykresu rozjezdzaja sie, bo `getTrends` nie dostaje `campaign_ids`, a `getCorrelationMatrix` dostaje — na tych samych filtrach dwa widoki licza sie na innych zbiorach kampanii.

### Oceny
| Kryterium | Ocena | Uzasadnienie (plik:linia lub playbook ref) |
|-----------|-------|---------------------------------------------|
| Potrzebnosc | 8/10 | Playbook 1.1 Daily (linie 16-43) i 1.1 Weekly (49-52) wymagaja przegladu trendu spend/CTR/CPC/conv + porownania okresow — Trend Explorer to robi w 1 widoku. Specjalista siada tu codziennie rano. Minus 2 pkt bo brak per-campaign split blokuje konta z 20+ kampaniami. |
| Kompletnosc | 6/10 | Ma 9 metryk, dual-axis, korelacje, action annotations, mock fallback, error/loading states, banner. Brakuje: per-campaign split (brak w zakladce), period-over-period overlay, zoom/brush, anomaly detection overlay (playbook 5.1 L421-437), save preset, export CSV/PNG. Do tego 3 bugi (P0). |
| Wartosc dodana vs Google Ads UI | 9/10 | Action annotations z before/after nalozone na wykres to cos czego Google Ads Explorer nie ma w ogole — change history siedzi w osobnej zakladce. Pearson matrix popup jednym klikiem + dual-axis auto-detect to kolejne wartosci dodane. Gdyby to dzialalo na cpa i scope byl spojny, ocena bylaby 10. |
| Priorytet MVP | 8/10 | Playbook 6 "Basic Analytics" (L518-521) wymienia "Wykresy trendow (ostatnie 30 dni)" jako MUST dla MVP. To jest spelnione. Minus 2 pkt bo dziala tylko jako widget na dashboardzie, nie jako pelny standalone "Trends" tab. |
| **SREDNIA** | **7.75/10 → 7.0** | Zaokraglam w dol przez 3 otwarte bugi (P0). |

### Lista problemow (12 znalezionych)

**[P0] CPA rozwala correlation endpoint — 400 Bad Request**
- Gdzie: `backend/app/routers/analytics.py:28` (`VALID_METRICS`) + `frontend/src/components/TrendExplorer.jsx:26-35` (`CORRELATION_METRIC_MAP`)
- Problem: User dodaje CPA do wykresu, frontend buduje `mapped = activeMetrics.map(k => CORRELATION_METRIC_MAP[k])` — ale `cpa` nie ma klucza w tym mapie, wiec `backend === undefined` i jest wyfiltrowany (L300 `filter(m => m.backend)`). Mozliwosc 1: jesli mamy tylko `[cpa, clicks]`, `mapped.length < 2` → `correlationData=null`, badge znika bez komunikatu. Mozliwosc 2: jesli user doda obchodzenie, nawet dodanie `cpa` do backend correlation zwroci 400 bo `VALID_METRICS` w `analytics.py:28` nie zawiera `cpa`.
- Fix: (a) W `CORRELATION_METRIC_MAP` dodaj `cpa: 'cpa'`. (b) W `analytics.py:28` dodaj `"cpa"` do `VALID_METRICS`. (c) W `correlation_matrix` (analytics.py:301-321) dodaj derywacje `cpa = cost_usd / conversions if conversions else 0` do `daily_rows`. (d) Frontend powinien tez pokazac graceful toast "Korelacja niedostepna dla tej kombinacji" zamiast silent fail.
- Playbook ref: 1.1 Weekly L51 wymienia CPA/ROAS jako kluczowe metryki do porownan — brak korelacji dla CPA lamie playbook.

**[P0] ROAS zawsze = 0 w mock mode (swiezy klient bez `MetricDaily`)**
- Gdzie: `backend/app/services/analytics_service.py:431-436` (`_mock_daily_data`)
- Problem: Mock generator tworzy `clicks/impressions/cost_micros/conversions`, ale NIE `conv_value_micros`. W `get_trends` L355 liczy `conv_value_usd = agg.get("conv_value_micros", 0) / 1_000_000` → zawsze 0 → `roas = conv_value_usd / cost_usd = 0`. User widzi plaska linie ROAS=0 i mysli ze konto nic nie zarabia, lub ze bug w trackingu. To psuje pierwsze wrazenie na freshly-seeded/nowo-podlaczonym koncie.
- Fix: W `_mock_daily_data` dodaj `total_conversion_value_micros = sum(k.conversion_value_micros or 0 for k in keywords)` i `day_map[current]["conv_value_micros"] = int((total_conversion_value_micros / days) * noise())`. Alternatywa: uzyj `conversions * avg_order_value_micros * noise()` jesli Keyword nie ma conv_value.
- Playbook ref: 6.1 Basic Analytics L519 wymaga ROAS jako KPI — mock mode musi zwracac sensowne wartosci zeby user nie mial wrazenia "nic nie dziala".

**[P0] Scope kampanii rozjezdza sie miedzy wykresem a korelacja**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:136-159` (fetchData) vs `307` (correlation body) + `frontend/src/features/dashboard/DashboardPage.jsx:248-257` (filteredCampaigns)
- Problem: `getTrends` NIE wysyla `campaign_ids` — agregat liczy sie serwerowo na wszystkich kampaniach klienta ograniczonych przez `campaign_type` + `status`. Ale `getCorrelationMatrix` dostaje `campaignIds={filteredCampaignIds}`, czyli tylko kampanie z `status === 'ENABLED'` (DashboardPage.jsx:250). Jesli sidebar ma `status=ALL` lub `status=PAUSED`, wykres pokazuje inne dane niz korelacja — user widzi "Kor. +0.87" dla kompletnie innego zbioru niz to co ma na wykresie. W przypadku `status=PAUSED` → `filteredCampaignIds=[]` → correlation backend L275 `if data.campaign_ids:` dla pustej listy = False → liczy na ALL → skrajna rozbieznosc.
- Fix: (a) Zunifikuj — `TrendExplorer` powinien albo ignorowac prop `campaignIds` i brac filtry z Sidebara (jak wykres), albo oba wywolania powinny wysylac identyczny `campaign_ids`. Rekomendacja: niech DashboardPage nie przekazuje `campaignIds`, a frontend dodatkowo niech wysyla `campaign_ids` explicitnie do obu endpointow budowane z tych samych kryteriow. (b) Backend: `getCorrelationMatrix` powinien przyjmowac `campaign_type`/`status` i filtrowac identycznie jak `/trends`.
- Playbook ref: 1.1 Weekly L49-52 — jesli specjalista porownuje okresy, zbior musi byc spojny, inaczej wnioski sa falszywe.

**[P1] ReferenceLine action markery znikaja gdy dzien akcji nie ma danych w wykresie**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:607-617`
- Problem: Recharts `ReferenceLine x={d}` na kategorycznej osi `dataKey="date"` wyswietla marker TYLKO jesli `d` istnieje jako wartosc w `data`. Jesli dzien akcji nie ma rzedu w `MetricDaily` (np. weekend, nowa kampania, przerwa), ReferenceLine nie renderuje sie — milczaco znika. User z raportu `ads-user` (L62-64) juz to zauwazyl w inny sposob ("Action markers to 1 kropka na dzien"), ale tu jest worse case: marker znika zupelnie.
- Fix: Wymus, by kazdy dzien w okresie mial wiersz w `data` (nawet zerowy) — backend powinien forward-fill zerami. W `get_trends` L348-381 iteruj po `date_from..date_to`, dla brakujacych dni daj `{date: str(d), cost: 0, ...}`.
- Playbook ref: 5.1 L429 anomaly detection wymaga ciaglej serii — zera lepsze niz dziury.

**[P1] Correlation popup uzywa backendowych nazw zmiennych w czesciach UI**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:317-326` + `backend/app/routers/analytics.py:331-333`
- Problem: Backend zwraca matrix z kluczami `"cost_micros"`, `"avg_cpc_micros"`, `"conversion_rate"` (L333 `to_dict()`). Frontend L317-319 wyciaga `response?.matrix?.[mapped[i].backend]?.[mapped[j].backend]` — poprawnie uzywa backend names. Ale jesli user doda metryke `cvr`, backend dostaje `"conversion_rate"` (mapa L34), a `correlation_matrix` L301-321 liczy derived metrics i DataFrame ma kolumny `["clicks","impressions","cost_micros","conversions","ctr","roas","avg_cpc_micros","conversion_rate"]`. Ale L325 `valid_cols = [m for m in data.metrics if m in df.columns]` — jesli request ma `"conversion_rate"`, jest w `df.columns`, OK. Tu wlasciwie wszystko gra, ALE: frontend wysyla `"cost_micros"` dla `cost` (L27), a w `/trends` uzywa plain `"cost"` — niespojne naming. Debuggowanie tego to koszmar.
- Fix: Zunifikuj naming metryk miedzy `/trends` i `/correlation`. Albo oba uzywaja user-facing `"cost"/"cpc"/"cvr"`, albo oba uzywaja `"cost_micros"/"avg_cpc_micros"/"conversion_rate"`. Usun `CORRELATION_METRIC_MAP` w ogole.

**[P1] Brak per-campaign split (blokuje konta z 20+ kampanii)**
- Gdzie: `frontend/src/components/TrendExplorer.jsx` (cala zakladka)
- Problem: Wykres rysuje zawsze AGREGAT wszystkich kampanii przefiltrowanych przez sidebar. Dla klienta agencyjnego z 20-40 kampaniami nie da sie porownac "kampania A vs kampania B" w jednym widoku — specjalista z raportu ads-user (L48) to juz zglosil jako top blocker. Google Ads Explorer robi to natywnie.
- Fix: Dodaj multi-select `<CampaignPicker />` w headerze widgetu (max 5 kampanii). Backend `get_trends` juz przyjmuje `campaign_ids` przez `_filter_campaign_ids` — trzeba przekazac listing + zwrocic `data: {date, campaign_id, cost, clicks, ...}` zamiast agregatu per-day. Front: jedna `<Line>` per kampania.
- Playbook ref: 1.1 Weekly L54-56 bid adjustments wymagaja porownania high/low performers side-by-side.

**[P1] Brak period-over-period overlay**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:618-634` (Line mapping) + brak dodatkowego endpointu
- Problem: Specjalista w raporcie ads-user L49 wskazal brak "porownaj z poprzednim okresem". Playbook 1.1 Weekly L50 mowi DOSLOWNIE "Porownanie Last 7 days vs Previous 7 days". Obecnie w Trend Explorer nie ma takiej opcji — jest osobny `WoWChart`, ale on pokazuje SUMY, nie nalozone linie.
- Fix: Dodaj toggle "Porownaj z poprzednim okresem" w headerze. Backend: nowy endpoint `/analytics/trends-compare` lub rozszerzenie istniejacego o `compare_to=previous_period|previous_year`. Frontend renderuje dodatkowe `<Line>` z `strokeDasharray="4 4"` dla serii "prev_*".
- Playbook ref: 1.1 Weekly L50 (explicit).

**[P1] `days` query constraint pozwala <7, rozwala wykres przy pelnym `all_time` presecie**
- Gdzie: `backend/app/routers/analytics.py:821` + `833-841`
- Problem: `days` ma `ge=7, le=365`. Ale `date_from/date_to` to bypassuja — L839-841 wymusza max 365. OK. ALE odwrotny kierunek: jesli `date_to - date_from = 1 dzien`, zwracamy 1 wiersz — linia z 1 punktu nie rysuje sie w Recharts (potrzebuje >=2 punktow). Brak komunikatu dla uzytkownika.
- Fix: Jesli `period_days < 2`, frontend powinien pokazac empty state "Wybierz zakres minimum 2 dni". Lub backend powinien zwrocic `period_days` w response (juz jest L389) i frontend to czyta — ale nie czyta.

**[P2] Brak zoom/brush na osi czasu**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:579` (ComposedChart)
- Problem: Dla 90-dniowego okna nie ma sposobu "zoom na 7 dni w okolicach spike". Recharts ma `<Brush>` component ktory to robi. User z ads-user L53 zglosil.
- Fix: Dodaj `<Brush dataKey="date" height={20} stroke={C.accentBlue} />` pod wykresem.

**[P2] Korelacja globalna na calym okresie — maskuje rolling zmiany**
- Gdzie: `backend/app/routers/analytics.py:329` (`df[valid_cols].corr(method="pearson")`)
- Problem: Jesli user ma 90 dni i w ostatnim tygodniu CPA rosnie razem z konwersjami (zly bidding), globalne r=0.8 z poprzednich 83 dni to maskuje. Specjalista z raportu (L61) wprost prosi o rolling 14-day correlation.
- Fix: Dodaj parametr `window=14` do `/correlation` i policz `df[valid_cols].rolling(14).corr()` — zwroc ostatni wynik + pelna serie. Frontend: mini-sparkline pod wykresem glownym.

**[P2] Tooltip moze zaslonic pol wykresu przy 5 metrykach + 4 akcjach**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:197-258`
- Problem: Tooltip `maxWidth: 340` + padding + borderTop z listaakcji rozrasta sie do ~320-380px wysokosci przy 5 metrykach + 4 eventach. Wykres ma 220px wysokosci, wiec tooltip wystaje ponad niego albo zaslania wykres w 70%.
- Fix: (a) Tooltip powinien pozycjonowac sie inteligentnie (Recharts `wrapperStyle` + offset). (b) Zrob accordion "Pokaz X akcji" domyslnie zwiniete. (c) Albo zmniejsz sekcje akcji do 2 eventow max w tooltipie + "otworz szczegoly".

**[P2] Brak `cpa` w derived metrics correlation — zlamana spojnosc z `/trends`**
- Gdzie: `backend/app/routers/analytics.py:312-321`
- Problem: `/trends` derywuje cpa (service L361 `cpa = cost_usd / conversions`), ale `correlation_matrix` tego nie robi (L312-321 nie ma `cpa`). Nawet gdyby dodac `"cpa"` do `VALID_METRICS` (P0 fix), to correlation i tak nie policzy bo go nie deryvuje. Musi byc naprawione RAZEM z P0.
- Fix: Dopisz do `daily_rows.append({...})` L312-321: `"cpa": cost_usd / conversions if conversions else 0`. Upewnij sie tez ze mapping w froncie oddaje tego samo pod ta sama nazwa.

**[P3] Dropdown close-on-outside-click nasluchuje nawet przy zamknietych popupach**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:264-274`
- Problem: `useEffect` dodaje listener gdy `showCorrelationPopup || showDropdown`, ale early return L265 prawidlowo omija — OK. Drobiazg: handler zamyka OBA popupy naraz, nawet jesli click byl obok otwartego dropdown → dropdown sie zamyka. Kosmetyka.
- Fix: Osobne refs/listenery per popup, lub sprawdz w handlerze `if (showDropdown && !closest('[data-metric-dropdown]')) setShowDropdown(false)` — osobno dla kazdego.

**[P3] Brak klikalnych action markers (deeplink do Action History)**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:607-617`
- Problem: ReferenceLine nie jest klikalny w Recharts. User z ads-user L64-65 zglosil ze chcialby klik → Action History z prefiltrem.
- Fix: Zamiast `ReferenceLine`, rysuj `<Scatter>` z customowym dot componentem ktory ma onClick. On click → `navigate('/actions?date={d}')`. Alternatywa: transparentna linia + obszar `onMouseEnter` pod kropka (hack, ale dziala).

**[P3] Mock banner nie precyzuje co jest mockowe**
- Gdzie: `frontend/src/components/TrendExplorer.jsx:544-561`
- Problem: Banner mowi "Brak rzeczywistych danych — synchronizuj konto", ale user z ads-user L66 pyta "ktore dane sa mockowe?". Odpowiedz: caly wykres (mock mode = 100% fake). Komunikat moze to wyjasnic.
- Fix: Zmien na "Caly wykres to dane symulowane (brak pobranych MetricDaily). Synchronizuj konto w sidebarze aby zobaczyc realne metryki."

### Porownanie z Google Ads UI
| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Daily trend chart (cost, clicks, conv) | Performance tab | TrendExplorer | IDENTYCZNE |
| Action history na wykresie (change annotations) | BRAK (osobna zakladka) | Tak, z before/after | LEPSZE |
| Pearson correlation matrix | BRAK (export → Sheets) | Klik → popup | LEPSZE |
| Dual-axis auto-detect | Reczne przelaczenie | Automatycznie | LEPSZE |
| Per-campaign split w 1 wykresie | Tak (multi-line) | BRAK | GORSZE |
| Period-over-period overlay | Tak (dotted line) | BRAK | GORSZE |
| Segmentacja po device/network/daypart | Tak | BRAK | GORSZE |
| Anomaly detection overlay | Tak (warning icons) | BRAK | GORSZE |
| Benchmarks / industry avg | Tak (Optimization Score) | BRAK | GORSZE |
| Zoom/brush na osi czasu | Tak (drag-select) | BRAK | GORSZE |
| Export PNG/CSV | Tak | BRAK | GORSZE |
| Save preset combos | BRAK | BRAK | IDENTYCZNE |
| Forecast (extrapolation) | Tak (w Recommendations) | BRAK | GORSZE |
| Rolling correlation (14d) | BRAK | BRAK | BRAK |
| Click-through to action detail | N/A | BRAK (ma byc) | BRAK |
| Mock data fallback | N/A | Tak (banner) | LEPSZE |

### Rekomendacja koncowa
**ZACHOWAC Z MODYFIKACJAMI.** Trend Explorer to jedna z dwoch-trzech zakladek ktore maja **realna wartosc dodana** nad Google Ads UI (action annotations + Pearson + dual-axis) i playbook wprost wymaga ich jako MVP (sekcja 6 L518-521). Ale trzy P0 (CPA w correlation, ROAS=0 w mocku, rozjechany scope kampanii) trzeba naprawic zanim Marek zacznie tego uzywac codziennie — na tym etapie jedna z tych wpadek i traci zaufanie do narzedzia. P1 (per-campaign split, period-over-period, zunifikowane naming) to musi dla retention po 1 tygodniu. Reszta (P2/P3) mozna zrobic w v1.1.

**Kolejnosc naprawy:** P0 Correlation CPA + mock ROAS + scope → P1 Per-campaign split + period overlay → P1 Naming unification → P2 Zoom brush + rolling correlation → P3 cosmetics.
