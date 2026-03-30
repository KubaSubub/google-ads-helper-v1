# Notatki usera: Pulpit (Dashboard) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Data:** 2026-03-29

---

## Co widze po wejsciu

Ciemny, ladny dashboard. Pierwsze co lapia oczy:

1. **Health Score = 50** w zoltym kole (czyli sredniutko) — obok 3 issue: "3 alerty wysokiej wagi", "1 alert sredniej wagi", kampania "Meble Biurowe" przepala budzet (376% oczekiwanego przy 94% miesiaca). To od razu mowi mi: masz pozar, idz gasic.

2. **8 kart KPI** w siatce 4+4:
   - Gora: Klikniecia 33 657 (+5.9%), Koszt 67 638,81 zl (+2.2%), Konwersje 1487,05 (+0.8%), ROAS 3.75x (+5.3%)
   - Dol: Wyswietlenia 594 236 (+7.0%), CTR 5.66% (+1.2%), CPA 45,49 zl (+1.4%), Wasted Spend 358,14 zl

3. **Quality Score widget** — sredni QS 6.7/10, 4 slowa z niskim QS zjadajace 23.9% budzetu. Klikalne, prowadzi dalej.

4. **Automatyczne insighty** — zwiniety accordion z badge "2". Nie widze tresci bez klikniecia.

5. Ponizej (niewidoczne na screenie, ale wiem z kodu): Trend Explorer, WoW Chart, tabela kampanii z sortowaniem, Budget Pacing, PMax Channel Split, Urzadzenia, Geo top miasta, Impression Share, Ostatnie akcje.

6. W sidebarze po lewej: klient "Demo Meble Sp. z o.o.", ID 123-456-7890, filtry typu kampanii (Wszystkie/Search/PMax/Shopping/Display/Video), nawigacja z kategoriami.

7. Na gorze prawa: selektor okresu "30 dni" i pasek filtrow kampanii (status + szukaj po nazwie).

## Co moge zrobic

- **Zmienic okres** — selektor 30 dni w prawym gornym rogu
- **Filtrowac po typie kampanii** — pill-buttons w sidebarze
- **Filtrowac po statusie kampanii** — dropdown w pasku filtrow
- **Szukac kampanie** — pole "Szukaj..." w pasku filtrow
- **Kliknac Health Score** — prowadzi do monitoringu/alertow
- **Kliknac QS widget** — prowadzi do strony Quality Score
- **Kliknac "Poranny przeglad"** — link w prawym gornym rogu headera
- **Kliknac Wasted Spend** — prowadzi do search terms z segmentem WASTE
- **Kliknac kampanie w tabeli** — prowadzi do strony Kampanie z filtrem
- **Sortowac tabele kampanii** — po koszcie, konwersjach, ROAS, CPA, IS, budzecie
- **Rozwinac insighty** — accordion z automatycznymi insightami
- **Trend Explorer** — wybor metryk, wykres czasowy, korelacja
- **WoW Chart** — porownanie tydzien do tygodnia
- **Zmienic klienta** — dropdown w sidebarze

## Co mam WIECEJ niz w Google Ads UI

1. **Health Score z issues** — Google Ads ma "Optimization Score" ale nie ma jednego "health score" z lista krytycznych problemow na starcie. To jest fajne bo od razu widze "pozar".

2. **Wasted Spend jako osobna metryka** — w Google Ads muszalbym recznie przefiltrowac search terms z 0 konwersji i zsumowac koszt. Tu mam gotowa liczbe na start.

3. **CPA od razu na dashboardzie** — Google Ads domyslnie nie pokazuje CPA w overviewie, muszalbym dodac kolumne.

4. **Quality Score widget** — w Google Ads nie ma QS na dashboardzie, muszalbym wejsc w slowa kluczowe. Tu od razu widze ile budzetu zjada niski QS.

5. **Budget Pacing** — w Google Ads jest "Recommendations" albo trzeba recznie liczyc. Tu mam gotowe progress bary z statusem.

6. **PMax Channel Split** — w Google Ads musisz wejsc w PMax > Insights > kanaly. Tu jest na dashboardzie.

7. **Impression Share na dashboardzie** — w Google Ads trzeba dodac kolumny w widoku kampanii. Tu IS + lost(budget) + lost(rank) sa od razu widoczne.

8. **WoW comparison** — w Google Ads jest porownanie okresow, ale nie w takiej formie (overlay dwoch linii).

9. **Korelacja metryk w Trend Explorer** — tego nie ma nigdzie w Google Ads UI.

## Czego MI BRAKUJE vs Google Ads UI

1. **Conversion Rate (CVR)** — mam CTR, mam CPA, mam ROAS, ale nie mam CVR (% klikniec konczacych sie konwersja). To jest basicowy KPI, powinien byc na gorze.

2. **Conversion Value (revenue)** — widze ROAS 3.75x i koszt 67k, ale nie widze wprost ile przychodu wygenerowaly kampanie. Musze sobie liczyc 67k * 3.75. To powinno byc gotowe.

3. **Avg. CPC** — mam CTR, ale nie mam sredniego kosztu klikniecia. Musze liczyc 67k / 33k. W Google Ads to jest podstawowa metryka.

4. **Trend / zmiana Wasted Spend** — inne KPI maja procent zmiany vs poprzedni okres, Wasted Spend nie ma. Nie wiem czy waste rosnie czy maleje.

5. **Segmentacja po dniu tygodnia** — w Google Ads moge zobaczyc ktore dni tygodnia sa najlepsze/najgorsze. Przydatne do bid adjustments.

6. **Top/Bottom campaigns** — na dashboardzie powinien byc szybki widok "3 najlepsze kampanie po ROAS" i "3 najgorsze". Nie chce scrollowac calej tabeli.

7. **Budget utilization summary** — ile z calkowitego budzetu dziennego wydaje (np. 85% budzetu zuzywanego) jako jedna liczba, nie rozbite per kampania.

8. **Auction Insights (pozycja vs konkurencja)** — w Google Ads widze kto jest nade mna, tu nie.

## Co mnie irytuje / myli

1. **Wasted Spend nie ma zmiany procentowej** — wszystkie inne KPI maja strzalke i % vs poprzedni okres, a Wasted Spend stoi golem. Wyglada to niespojnie i nie wiem czy sytuacja sie poprawia.

2. **Kolory zmian przy malym foncie** — strzalki zmiany % przy koszcie i CPA maja `invertChange` w kodzie (wzrost = czerwony), ale na ekranie przy foncie 11px kolory sa ciezko rozrozniane. Nie wiadomo na pierwszy rzut oka czy zmiana jest dobra czy zla.

3. **CPA +1.4% — w ktora strone to jest?** — CPA rosnie = ZLE, ale muszalem patrzec na kolor zeby to ocenic. Moze dodac slownie "gorzej" / "lepiej" albo strzalke w gore/dol z kolorem?

4. **"Automatyczne insighty" zwiniety domyslnie** — jesli sa 2 wazne insighty, dlaczego mam klikac zeby je zobaczyc? Powinny byc rozwiniete domyslnie.

5. **Filtry w dwoch miejscach** — typ kampanii w sidebarze (pills), status + szukajka w pasku filtrow na gorze. Dezorientujace — ktore filtry wplywaja na co?

6. **Brak wyraznego CTA** — dashboard pokazuje dane ale nie mowi "co powinienem zrobic TERAZ". Health Score daje hinta, ale brakuje "Top 3 akcje na dzis".

7. **Zbyt duzo sekcji pod scrollem** — na jednym ekranie widze KPI + QS widget + insighty. Reszta (tabela kampanii, budget pacing, urzadzenia, geo, IS, ostatnie akcje) wymaga scrollowania. To jest dashboard, nie raport — powinien byc bardziej skondensowany.

## Co bym chcial

1. **Conversion Value i CVR w KPI** — dodac przychod i wspolczynnik konwersji, ewentualnie zamieniac z Wyswietleniami (ktore sa mniej actionable).

2. **Avg. CPC w KPI** — zamiast lub obok Wyswietlenia.

3. **"Top 3 akcje na dzis"** — sekcja zaraz pod Health Score, wyciagajaca z rekomendacji i insightow 3 najpilniejsze rzeczy do zrobienia. Z guzikami "Wykonaj" / "Odroc" / "Odrzuc".

4. **Wasted Spend ze zmiana %** — tak jak inne KPI.

5. **Mini-ranking kampanii** — top 3 best / worst po ROAS lub CPA, bez koniecznosci scrollowania do pelnej tabeli.

6. **Bardziej agresywne kolory alarmowe** — jesli Health Score = 50, caly kafelek powinien miec lekkie czerwone tlo, nie tylko zolty ring. Teraz wyglada zbyt spokojnie jak na "3 alerty wysokiej wagi".

7. **Customizable KPI grid** — pozwolcie mi wybrac ktore 8 KPI chce widziec. Ja bym zamienil Wyswietlenia na CVR, a Wasted Spend na Revenue.

8. **Szybki link do Google Ads UI** — przycisk "Otworz w Google Ads" przy konkretnej kampanii. Czasem chce szybko przejsc do natywnego UI.

## Verdykt

Dashboard jest **solidny i wizualnie przyjemny** — duzo lepszy niz wiele narzedzi trzecich ktore testowalem. Health Score + Wasted Spend + QS na starcie to realna wartosc dodana vs Google Ads UI. Ale brakuje CVR, Revenue i Avg CPC w KPI, a ilosc sekcji pod scrollem jest przytlaczajaca. Jako glowny widok codziennej pracy — uzywalny, ale potrzebuje dopracowania zeby stac sie moim "jednym ekranem porankowym".

---

## Pytania do @ads-expert

1. Czy Health Score 50 przy 3 alertach wysokiej wagi to wlasciwa kalibracja? W mojej praktyce 3 alerty high = powazna sprawa, a 50 brzmi jak "srednio dobrze".
2. Czy Wasted Spend 358 zl przy budzecie 67k (0.5%) to w ogole warte wyswietlania jako osobna karta? Moze powinien byc prog % ponizej ktorego to chowamy?
3. Czy brak Conversion Rate (CVR) w KPI to swiadoma decyzja? Dla mnie CTR bez CVR to polowa obrazka.
4. Sekcja Budget Pacing, Device, Geo, IS, Actions — czy to nie za duzo na jednym dashboardzie? Moze czesc powinna byc na oddzielnych zakladkach / raporcie?
5. Trend Explorer i WoW Chart — oba robia podobne rzeczy (linia czasu metryki). Czy nie powinno byc jednego narzedzia z opcja porownania okresow?
6. Impression Share — pokazany jest tylko dla Search. Co z IS dla Shopping? To jest kluczowa metryka e-commerce.
7. PMax Channel Split — fajne, ale czy nie powinien tez pokazywac ROAS per kanal, nie tylko cost share i conv share?
