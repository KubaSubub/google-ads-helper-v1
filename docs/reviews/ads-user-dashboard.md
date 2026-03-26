# Notatki usera: Pulpit (Dashboard) — RE-TEST

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-26 (re-test po poprawkach)

---

## Co widze po wejsciu

Ciemny, elegancki kokpit. Pierwszy rzut oka: po lewej duzy Health Score z okraglym gaugemem i lista problemow. Po prawej dwa rzedy KPI kart — 8 sztuk: Klikniecia, Koszt, Konwersje, ROAS (gorny rzad), Wyswietlenia, CTR, CPA, Wasted Spend (dolny). Kazda karta ma wartosc + procent zmiany z kolorowa strzalka. Pod spodem rozwijany panel "Automatyczne insighty", Trend Explorer (multi-metric chart), "Porownanie okresow" (WoW), tabela kampanii, Budget Pacing, Device + Geo breakdown, Impression Share.

Duzo tego — ale wszystko jest czytelne i logicznie ulozne. Nic nie jest zbedne.

## Co moge zrobic

- **Zmienic okres i filtry** — globalny bar u gory: zakres dat, typ kampanii, status
- **Kliknac Health Score** — przenosi do Monitoringu (/alerts)
- **Rozwinac Insighty** — lista rekomendacji z priorytetami, przycisk "Przejdz" do /recommendations
- **Trend Explorer** — dodawac/usuwac metryki (do 5), porownywac na jednym wykresie, widac korelacje miedzy nimi. Dual Y-axis jak metryki maja rozne jednostki
- **Porownanie okresow** — wybieram metryke z dropdown, widze biezacy vs poprzedni okres nakladane na wykresie. Os X teraz pokazuje DATY (np. "25.03") zamiast nazw dni — nareszcie widac kiedy dokladnie co sie dzialo
- **Tabela kampanii** — klikam wiersz, ide na /campaigns. Link "Wszystkie →". Kolumny: Nazwa, Status, Typ, Budzet/dzien, Koszt, Konwersje, ROAS (kolorowany), Trend sparkline, Strategia
- **Budget Pacing** — karteczki per kampania z progress barem i "Na torze"/"Przekroczenie"/"Niedostateczne"
- **Device breakdown** — klikam urzadzenie → rozwija sie mini-chart z trendem clicks/cost/conversions + avg/dzien
- **Geo breakdown** — top 8 miast z klikniecami, kosztem, % kosztu, ROAS
- **Impression Share** — 3 wskazniki z progress barami: IS, Lost Budget, Lost Rank

## Co mam WIECEJ niz w Google Ads UI

1. **Health Score** — nie ma nic takiego w GAds. Mam liczbe 0-100 + liste problemow. Klikam i ide glebiej. Rano otwieram, widze 72 — OK, nic sie nie pali. Widze 38 — o kurde, co sie stalo.
2. **Wasted Spend jako KPI na dashboardzie** — w GAds musze reczenie filtrowac search terms bez konwersji i sumowac. Tu mam to jako karte z automatycznym kolorowaniem (zielony/zolty/czerwony).
3. **Trend Explorer z korelacjami** — to jest absolutny killer. W GAds moge dac max 2 metryki na jednym charcie. Tu daje 5 naraz i widze "korelacja cost vs conversions: +0.85 silna dodatnia". To jest cos czego nie daje ZADNE narzedzie na rynku.
4. **Porownanie okresow z datami** — teraz na osi X widze "20.03", "21.03" zamiast "Pon", "Wt". W koncu widze dokladnie ktory dzien mial peak. W GAds "Compare" daje tabelke procentowa, nie nakladany chart.
5. **Budget Pacing zbiorczy** — widze wszystkie kampanie naraz. W GAds musze klikac w kazda kampanie osobno.
6. **Device breakdown z rozwijalnym trendem** — klikam "MOBILE" i widze chart z 3 liniami. W GAds to wymaga przejscia do Reports > Devices.
7. **Insighty z wlasnych regul** — nie z algorytmow Google ktore chca zeby wydawal wiecej, ale z playbooka ktory mowi co faktycznie optymalizowac.

## Czego MI BRAKUJE vs Google Ads UI

1. **Sortowanie tabeli kampanii** — NADAL nie moge kliknac naglowek "Koszt" zeby posortowac. To jest moj #1 workflow: "pokaz najdrozsze". W GAds to jest standard.
2. **Klikniecie kampanii nie prowadzi do DETALU** — klikam wiersz i ide na /campaigns (liste ogolna), nie na detail tej konkretnej kampanii. W GAds klikam kampanie i od razu widze jej metryki.
3. **Brak filtra search terms z dashboardu** — karta Wasted Spend mowi mi ze 2000 zl poszlo w bloto, ale nie moge kliknac zeby zobaczyc KTORE frazy to generuja. W GAds tez tego nie ma na overview, ale tutaj mogloby byc bo mamy dane.
4. **Sparkline bez tooltipa** — widze maly wykresik trendu w tabeli, ale na hover nic sie nie pokazuje. Nie wiem jaka wartosc jest na gorce.
5. **Kolumna Strategia ucina tekst** — dlugie nazwy jak "Target ROAS: Maximize conversion value" sa uciete bez tooltipa. Nie widze co to za strategia.

## Co mnie irytuje / myli

1. **InsightsFeed nie ma filtra po priorytecie** — widze mieszanke HIGH/MEDIUM/LOW. Rano chce TYLKO HIGH. Mam 15 insightow, z czego 3 sa pilne — ale musze je sam odszukac wsrod reszty.
2. **Brak linku do Porannego przegladu** — w sidebarze jest "Poranny przeglad" (/daily-audit) ale z dashboardu nie moge tam przejsc jednym kliknieciem. Naturalnie: otwieram Pulpit, widze ze cos nie gra, chce przejsc do szybkich akcji.
3. **Geo tabelka — brak sortowania** — 8 miast wyswietlonych losowo (?). Chcialbym posortowac po ROAS zeby zobaczyc ktore miasto daje najlepszy zwrot.

## Co bym chcial

1. **Klikalna karta Wasted Spend** — klikam → przenosi do /search-terms z filtrem na waste terms. One-click "pokaz mi co marnuje pieniadze".
2. **Morning briefing jednym zdaniem** — np. "Wczoraj 3 kampanie przekroczyly budzet, 12 nowych waste terms, Health Score -5 vs tydzien temu". Jedno zdanie pod tytulem "Pulpit" zamiast suchego "Ostatnie 30 dni".
3. **Eksport dashboardu** — przycisk "Generuj raport" ktory daje PDF z aktualnym stanem. Moj klient chce to co tydzien.

## Verdykt

Wchodzilbym tu CODZIENNIE rano zamiast do Google Ads Overview. Serio. Health Score + 8 KPIs + Trend Explorer z korelacjami + Budget Pacing + WoW z datami — to jest cos czego Google Ads nie daje w jednym widoku. Poprawka dat w WoW chart to byl dobry ruch, teraz ten widget jest uzyteczny. Dwa blokery do pelnego zastapienia Google Ads Overview: sortowanie tabeli kampanii i deep-link do kampanii. Reszta to nice-to-have.

---

## Pytania do @ads-expert

1. Sortowanie tabeli kampanii — to byl zgłoszony w pierwszym review i nadal nie ma. Jak to priorytetyzujecie? Dla mnie to deal-breaker przy 20+ kampaniach.
2. Czy jest plan na klikalna karte Wasted Spend → /search-terms z filtrem waste? To by zamknelo petla "widze problem → robie cos z nim" bez nawigowania po 3 zakladkach.
3. InsightsFeed — filtr HIGH/MEDIUM/LOW byl w planie ads-verify. Kiedy?
4. Sparkline tooltip — drobnostka ale irytujaca. Na hover chce widziec wartosc + date.
5. Geo tabelka — czy jest plan na sortowanie? 8 miast bez mozliwosci posortowania po ROAS to stracona szansa.
