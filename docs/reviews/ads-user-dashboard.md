# Notatki usera: Pulpit (Dashboard) — RE-TEST #2

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-27 (re-test po sprincie poprawek)

---

## Co widze po wejsciu

Dashboard wygląda profesjonalnie. Ciemny motyw, czytelny layout. Na górze nagłówek "Pulpit" z okresem + link "Poranny przegląd →". Poniżej dwuczęściowy rząd: po lewej Health Score z gaugemem i listą problemów, po prawej 2 rzędy po 4 karty KPI (Kliknięcia, Koszt, Konwersje, ROAS / Wyświetlenia, CTR, CPA, Wasted Spend). Każdy KPI ma ikonę, wartość i % zmianę z kolorową strzałką. Pod KPI: widget Quality Score (kliknięcie → /quality-score), InsightsFeed (rozwijany), Trend Explorer, WoW comparison, tabela kampanii z sortowaniem, Budget Pacing, PMax channels (pie chart), Device + Geo breakdown, Impression Share, Ostatnie akcje.

Ogromna ilość danych ale nic nie jest zbędne. Wszystko służy mojemu porannemu workflow.

## Co moge zrobic

- **Filtry globalne** — okres, typ kampanii, status (z GlobalFilterBar)
- **Health Score** — klikam → /alerts
- **QS widget** — klikam → /quality-score, widzę średni QS i ile słów z niskim QS
- **Wasted Spend** — klikam → /search-terms?segment=WASTE
- **InsightsFeed** — rozwijam, filtruję po priorytecie (ALL/HIGH/MEDIUM/LOW), klikam "Przejdź"
- **Trend Explorer** — dodaję/usuwam do 5 metryk, widzę korelacje, dual Y-axis
- **WoW chart** — wybieram metrykę, widzę bieżący vs poprzedni okres z datami na osi X
- **Tabela kampanii** — sortuję po Budżet/Koszt/Konwersje/ROAS/IS, klikam wiersz → /campaigns?campaign_id=X
- **Budget Pacing** — progress bary per kampania
- **Device breakdown** — klikam urządzenie → rozwija trend chart
- **Geo breakdown** — top 8 miast z sortowalnymi nagłówkami
- **Impression Share** — 3 metryki Search z progress barami
- **Ostatnie akcje** — 5 ostatnich z linkiem "Wszystkie"
- **Link "Poranny przegląd →"** — jeden klik do /daily-audit

## Co mam WIECEJ niz w Google Ads UI

1. **Health Score 0-100** — w GAds nie ma nic takiego. Rano otwieram, widzę 72 — spoko. Widzę 38 — idę kopać.
2. **Wasted Spend jako KPI z deep-linkiem** — klikam kartę i od razu widzę waste terms. W GAds muszę ręcznie filtrować search terms → brak konwersji → sumować.
3. **Trend Explorer z korelacjami** — 5 metryk na jednym charcie z liczoną korelacją. W GAds max 2 metryki. To killer feature.
4. **WoW chart z datami** — nakładany chart bieżący vs poprzedni z konkretnymi datami. GAds "Compare" daje suchą tabelkę.
5. **Budget Pacing zbiorczy** — wszystkie kampanie naraz. GAds wymaga klikania w każdą osobno.
6. **QS widget na dashboardzie** — średni QS + liczba słów z niskim QS + % budżetu na nie. W GAds muszę iść do Keywords → dodać kolumnę Quality Score → filtrować.
7. **PMax channel split** — pie chart z rozkładem kosztów po kanałach PMax + alert gdy kanał je koszty bez konwersji. W GAds Insights nie daje tego tak przejrzyście.
8. **InsightsFeed z filtrem priorytetu** — HIGH/MEDIUM/LOW pille, widzę tylko pilne. Rekomendacje Google to spam — tu są z playbooka.
9. **Device breakdown z trendem** — klikam MOBILE → widzę chart. W GAds Reports > Devices wymaga 3 kliknięć.

## Czego MI BRAKUJE vs Google Ads UI

1. **Urządzenia po angielsku** — widzę "MOBILE", "DESKTOP", "TABLET" zamiast polskich nazw. Reszta UI jest po polsku, to razi.
2. **PMax kanały po angielsku** — "SEARCH", "DISPLAY", "VIDEO" — powinno być po polsku jak reszta dashboardu.
3. **Brak morning briefing** — nagłówek mówi "Pulpit" i "Ostatnie 30 dni". Chciałbym jedno zdanie: "Wczoraj 3 kampanie przekroczyły budżet, Health Score -5 vs tydzień temu". Coś co mówi mi CZY jest pożar.
4. **Brak eksportu** — klient chce cotygodniowy raport. Przycisk "Eksport PDF" zaoszczędziłby mi 30 min na screenshotach.
5. **Tabela kampanii — brak kolumny CPA** — mam Koszt, Konwersje, ROAS, IS ale nie mam CPA. Przy lead gen CPA to moja najważniejsza metryka.

## Co mnie irytuje / myli

1. **Angielskie labele w Device i PMax** — niespójność. Sidebar, KPI, tabele — wszystko po polsku. A tu nagle MOBILE, DESKTOP, SEARCH, DISPLAY. Jak robię screenshota dla klienta to wygląda dziwnie.
2. **"Ostatnie akcje" widget jest minimalistyczny** — widzę status + nazwę + datę. Nie wiem CO zmieniono (jaka wartość?). W Historia zmian mam pełne info, ale tu na dashboardzie za mało.
3. **InsightsFeed "Automatyczne insighty" — nazwa** — brzmi jak coś technicznego. Wolałbym "Co wymaga uwagi" albo "Problemy do sprawdzenia".

## Co bym chcial

1. **Morning briefing** — jedno zdanie pod nagłówkiem: "3 kampanie over-budget, 12 nowych waste terms, QS spadł o 2 pkt". Oszczędziłoby mi 30 sekund scrollowania.
2. **Eksport PDF** — przycisk generujący raport z aktualnym dashboardem. Moi klienci tego chcą co tydzień.
3. **Kolumna CPA w tabeli kampanii** — dla lead gen to krytyczna metryka.
4. **Polskie nazwy urządzeń i kanałów** — Mobile → Telefony, Desktop → Komputery, Tablet → Tablety. SEARCH → Wyszukiwarka, DISPLAY → Sieć reklamowa, VIDEO → YouTube.

## Verdykt

Ten dashboard ZASTĘPUJE mi Google Ads Overview na co dzień. Serio. Health Score + 8 KPI + Trend Explorer + WoW + Budget Pacing + PMax channels + QS widget — tego nigdzie nie dostanę w jednym widoku. Wszystkie problemy z poprzedniego testu (sortowanie, deep-link, sparkline tooltip, geo sort, InsightsFeed filter, Wasted Spend click, IS kolumna) zostały naprawione. Teraz to jest dojrzały produkt. Pozostałe uwagi to polish — angielskie labele urządzeń/kanałów i brak morning briefing. Nic nie blokuje codziennego użycia.

**Ocena: 9/10** — z 7/10 w pierwszym teście. Ogromny postęp.

---

## Pytania do @ads-expert

1. Angielskie nazwy urządzeń (MOBILE/DESKTOP) i kanałów PMax (SEARCH/DISPLAY) — to świadoma decyzja czy niedopatrzenie? Reszta UI jest po polsku.
2. Morning briefing — czy jest to w planach? Jedno zdanie "co się zmieniło od wczoraj" pod nagłówkiem Pulpit oszczędziłoby czas.
3. Eksport PDF — na ile to realistyczne w obecnej architekturze?
4. Kolumna CPA w tabeli kampanii — łatwa do dodania? Mam koszt i konwersje, CPA to po prostu koszt/konwersje.
