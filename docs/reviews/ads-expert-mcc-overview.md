# Ocena eksperta Google Ads — MCC Overview
> Data: 2026-04-14 | Srednia ocena: 7.3/10 | Werdykt: ZMODYFIKOWAC

### TL;DR
Zakladka dostarcza realna przewage nad Google Ads MCC view (Pacing, Health Score, sparklines, billing inline), ale ma trzy blokujace problemy: ROAS wyswietlany jako procent zamiast mnoznik (standard agencyjny), brak filtru kont aktywnych/nieaktywnych, brak eksportu CSV. Health Score jest prawdziwym kompozytem (6 filarow w `analytics_service.py:444`), ale UI nie ujawnia skladowych — klikniecie w kolo nic nie robi.

---

### Oceny
| Kryterium | Ocena | Uzasadnienie |
|-----------|-------|--------------|
| Potrzebnosc | 9/10 | Playbook sekcja 1.1 "Daily Checks" — specjalista sprawdza budzety i anomalie kazdego ranka na wszystkich kontach; MCC Overview to wlasnie ten workflow skondensowany w jednym widoku. Pacing bars + billing status in-line to funkcje niedostepne w standardowym Google Ads MCC. |
| Kompletnosc | 6/10 | Brakuje: filtru statusu konta (P1), eksportu CSV (P1), klikalnego bell-ikonu dla alertow (P1), inline-edit budzetu lub chociazby absolut w tooltipie (P2), zapamiętania sortowania (P2). IS pojawia sie tylko gdy dane sa dostepne (`MCCOverviewPage.jsx:392 hasAnyIS`), co jest prawidlowe, ale bez stale widocznej kolumny specjalista moze nie wiedziec ze dane sa ukryte. |
| Wartosc dodana vs Google Ads UI | 8/10 | Health Score (agregat 6 filarow z wagami) to killer feature — GAds go nie ma. Pacing bar z wizualna logika kolorow (on_track/underspend/overspend `mcc_service.py:582-584`) nie istnieje w GAds MCC. Sparkline trendu wydatkow i zmiana % vs poprzedni okres rowniez brak w GAds. Billing status per konto bez klikania w kazde konto osobno to realna oszczednosc czasu dla agencji 8+ kont. |
| Priorytet MVP | 6/10 | Zakladka jest MVP-ready pod warunkiem naprawy ROAS (mnoznik vs %) i dodania filtru aktywnosci. Bez tych dwoch poprawek specjalista bedzie mylony przez dane lub bedzie musial filtr reczny robic. Eksport CSV jest potrzebny do raportowania klientom — brakuje go, ale nie blokuje codziennego uzycia. |
| **SREDNIA** | **7.3/10** | |

---

### Lista problemow (11 znalezionych — minimum 8)

**[P0] ROAS wyswietlany jako procent zamiast mnoznik — niestandard agencyjny**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:644-646`, `backend/app/services/mcc_service.py:368`
- Problem: Backend oblicza `roas = round(conv_value / spend * 100, 1)` — czyli `421%` zamiast `4.21x`. UI wyswietla `{acc.roas_pct.toFixed(0)}%` bez ostrzezenia. Standard agencyjny (Google Ads UI, SA360, Looker Studio) uzywa mnoznika `x`. PPC specjalista myslacy "ROAS 4x" zobaczy "421%" i bedzie musial przeliczac recznie.
- Fix: Zmienic backend `mcc_service.py:368`: `roas = round(conv_value / spend, 2)` (usunac `* 100`); zmienić pole na `roas` (bez `_pct`); zaktualizowac `MCCOverviewPage.jsx:644`: `{acc.roas.toFixed(2)}x`; zaktualizowac prog kolorow z 400/200 na 4.0/2.0.
- Playbook ref: Sekcja 1.1 "Weekly Reviews — CPA/ROAS"

**[P1] Brak filtru kont aktywnych vs nieaktywnych / porzuconych**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:375-385` (rawAccounts bez zadnego filtru), `backend/app/routers/mcc.py:22-30` (endpoint bez parametru `active_only`)
- Problem: Wszystkie konta laduja sie bez mozliwosci odfiltrowania kont z zerowym spend w dluzszym okresie. Agencja z 15 kontami, z ktorych 4 sa porzucone/zawieszone, bedzie pokazywac je w tabeli. Brak checkboxa "Tylko aktywne" lub dropdown "Status".
- Fix: Dodac parametr `?active_only=true` do `GET /mcc/overview` w routerze; w `MCCService.get_overview()` dodac filtr `where spend > 0`; w UI dodac pill-toggle "Wszystkie / Aktywne" nad tabela.

**[P1] Health Score — brak mozliwosci drill-down do skladowych**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:659-678` (kolo SVG z `title` tooltipem, brak `onClick`)
- Problem: Specjalista widzi liczbe 67/100 na kole, ale nie moze kliknac i zobaczyc ktory filar zawiodl (Performance 25%, Quality 20%, Efficiency 20%, Coverage 15%, Stability 10%, Structure 10% — `analytics_service.py:449-457`). Odpowiedz API juz zawiera `health.pillars` (`mcc_service.py:596-601`) ale UI go nie renderuje.
- Fix: Dodac `onClick` do kola health score, ktory otwiera small popover/tooltip z 6 filarami i ich odzielonymi wartosciami z `acc.health_pillars` (potrzebne przekazanie z `_build_account_data` przez `health.get("pillars")`).

**[P1] Brak eksportu CSV / XLSX tabeli kont**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx` — brak jakiejkolwiek funkcji eksportu; `backend/app/routers/mcc.py` — brak endpointu `/mcc/export`
- Problem: Specjalista ktory potrzebuje wyslac klientowi zestawienie wszystkich kont z KPI musi recznie kopiowac dane. Tablica zawiera pelne dane strukturalne (`accounts[]`) gotowe do eksportu.
- Fix: Dodac przycisk "Eksportuj CSV" przy headerze strony; implementacja po stronie frontendu wystarczy — `JSON → CSV` z `accounts` array; alternatywnie endpoint `GET /mcc/export.csv`.

**[P1] Bell-ikona alertow nie jest klikalna — brak przejscia do listy alertow**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:605-614` — `onClick={e => e.stopPropagation()}` zatrzymuje klikniecie zamiast nawigowac do alertow
- Problem: Klikniecie w dzwonek zatrzymuje propagacje (`stopPropagation`) i nic wiecej nie robi. `handleDeepLink` jest juz zaimplementowany dla kolumny "Zmiany" (`MCCOverviewPage.jsx:716`). Brakuje tego samego dla alertow.
- Fix: Zmienic `onClick={e => e.stopPropagation()}` na `onClick={(e) => handleDeepLink(acc, '/alerts', e)}` (zakladajac ze taka sciezka istnieje w routerze aplikacji).

**[P1] Impression Share (IS) ukryta w trybie kompaktowym i warunkowo**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:392` — `const hasAnyIS = accounts.some(a => a.search_impression_share_pct != null)` — kolumna IS pojawia sie tylko gdy przynajmniej jedno konto ma dane
- Problem: IS to metryka kluczowa dla kampanii Search (playbook sekcja 1.1 tygodniowe). Specjalista ktory nie wie ze dane sa ukryte nie bedzie ich szukal. Seed data moze nie miec IS, wiec w dev zawsze jest ukryta.
- Fix: Zawsze pokazywac kolumne IS z `—` gdy brak danych zamiast ukrywac kolumne; alternatywnie: dodac IS do expanded mode (kompaktowy wylaczony).

**[P2] Brak zapamiętania sortowania i trybu kolumn w localStorage**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:211-212` — `useState('spend')` i `useState(true)` dla `compactMode` — stan resetuje sie przy odswiezeniu strony
- Problem: Specjalista ktory preferuje sortowanie po Health Score lub CPA musi ustawienic to ponownie przy kazdym wejsciu.
- Fix: Zamienic `useState('spend')` na `useLocalStorage('mcc-sort-by', 'spend')` i analogicznie dla `sortDir` i `compactMode`. Prosta implementacja hooka `useLocalStorage` lub uzycie `localStorage` bezposrednio w `setSortBy`.

**[P2] KPI strip: "Klikniecia" moze wyswietlic ulamek dziesiowy**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:495` — `fmtNum(totalClicks)` gdzie `fmtNum` uzywane z `decimals=0`; `backend/app/services/mcc_service.py:506` — `clicks = int(row[0] or 0)` jest int na poziomie konta, ale `totalClicks` w froncie jest suma kont `accounts.reduce((s, a) => s + (a.clicks || 0), 0)` — OK dla sum; jednak seed moze dac float przez agregacje
- Problem: Marek w raporcie ads-user zobaczyл "Kliknięcia: 14,71" — to sugeruje ze gdzies klikniecia sa float. `_aggregate_metrics` zwraca `clicks = int(row[0] or 0)` wiec backend jest poprawny. Problem moze byc w seed data lub edge case gdy brak danych.
- Fix: Sprawdzic seed data pod katem `clicks` jako float; dodac `Math.round()` w frontendzie przy `totalClicks` jako dodatkowe zabezpieczenie: `fmtNum(Math.round(totalClicks))`.

**[P2] IS obliczana jako AVG zamiast weighted average po wydatkach**
- Gdzie: `backend/app/services/mcc_service.py:502-503` — `func.avg(MetricDaily.search_impression_share)` — prosta srednia
- Problem: Konto z 100 zl dziennie i IS=80% ma taki sam wplyw jak konto z 10000 zl i IS=20%. Weighted average po `cost_micros` dawalby bardziej reprezentatywny wynik MCC IS.
- Fix: Obliczyc `weighted_IS = sum(cost * IS) / sum(cost)` przez query z dwoma agregatami: `sum(cost_micros * search_impression_share)` i `sum(cost_micros)`.

**[P2] Brak testu pokrywajacego "no data" edge case dla IS w API**
- Gdzie: `backend/tests/test_mcc.py` — test `test_mcc_overview_impression_share` (linia 460) pokrywa case z danymi, brak testu dla case gdy zadne konto nie ma IS
- Problem: Jezeli `row[5]` zwroci `None`, backend ustawia `avg_is = None` poprawnie. Ale brak explicitnego testu regresji ze `search_impression_share_pct` jest `None` (nie 0) gdy brak danych.
- Fix: Dodac `test_mcc_overview_IS_none_when_no_data` w `test_mcc.py` sprawdzajacy ze bez IS danych zwracane jest `null` a nie 0.

**[P3] "Odkryj konta" przycisk ma taki sam wizualny priorytet jak "Synchronizuj nieaktualne"**
- Gdzie: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:481-487` — oba przyciski w tej samej linii, sync ma `C.infoBg` / `B.info` a discover ma `C.w04` / `B.subtle` — ta roznica jest subtelna
- Problem: "Odkryj konta" to rzadka operacja (raz na miesiac?), "Synchronizuj nieaktualne" to codzienna. W aktualnym layoucie sa obok siebie rownej wielkosci.
- Fix: Przeniesc "Odkryj konta" do menu lub wyraznie zmniejszyc (tylko ikona bez tekstu z tooltipem).

---

### Porownanie z Google Ads UI
| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Przeglad wszystkich kont | Podstawowe metryki, brak pacing | Pacing bars z kolorami, spend trend | LEPSZE |
| Health Score | Brak | Kompozyt 6 filarow (0-100) | LEPSZE |
| Billing status inline | Wymaga klikniecia w kazde konto | CreditCard ikona z tooltipem | LEPSZE |
| Sparkline trendu wydatkow | Brak w MCC view | Sparkline 56x20px obok wydatkow | LEPSZE |
| Zmiana wydatkow % vs poprzedni okres | Wymaga custom raportu | TrendingUp/Down z % inline | LEPSZE |
| Wykluczenia MCC w jednym miejscu | Tools > Shared Library (2-3 kliki) | Panel rozwijany z drilldown | LEPSZE |
| Zewnetrzne zmiany (nie przez app) | Brak | Kolumna "Zmiany" z podziałem | LEPSZE |
| Filtr kont po statusie | Podstawowy | Brak | GORSZE |
| Eksport CSV | Wbudowany | Brak | GORSZE |
| ROAS wyswietlanie | Mnoznik (x) | Procent (%) — niestandardowe | GORSZE |
| Aktywne kampanie per konto | Widoczne w tabeli | Brak kolumny | GORSZE |
| Impression Share | Zawsze widoczna | Ukryta gdy brak danych | GORSZE |

---

### Rekomendacja koncowa
**ZMODYFIKOWAC — zakladka jest high-value i powinna byc default startowym widokiem dla agencji.**

Trzy zmiany musza byc wprowadzone przed uznaniem za production-ready: (1) naprawic ROAS z `roas_pct` na mnoznik `roas_x` w backendzie i frontendzie [P0], (2) dodac filtr aktywnych kont [P1], (3) klikniety dzwonek alertow powinien nawigowac do `/alerts` dla danego klienta [P1]. Eksport CSV [P1] i drill-down Health Score [P1] sa nastepne w kolejce — obie funkcje sa techniczne proste (dane juz sa dostepne w API) i znaczaco podnosza wartosc zakladki.
