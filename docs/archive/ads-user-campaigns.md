# Notatki usera: Kampanie (Campaigns)

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Data:** 2026-03-29

---

## Co widze po wejsciu

Layout master-detail: po lewej lista kampanii (260px), po prawej panel szczegolowy wybranej kampanii. Na gorze "Filtry kampanii" z dropdownem statusu (Wszystkie / Aktywna / Wstrzymana / Usunieta) i pole szukaj po nazwie. W sidebarze pill-buttony filtrujace po typie kampanii (Wszystkie, Search, PMax, Shopping, Display, Video).

Lista kampanii pokazuje:
- Nazwe kampanii
- Kolorowa kropka statusu (zielona = aktywna, zolta = wstrzymana, czerwona = usunieta)
- Typ kampanii (Search/Display/PMax/...) + budzet dzienny
- Mini-metryki: koszt, konwersje, ROAS (z kolorowym ROAS: zielony >= 3x, zolty >= 1x, czerwony < 1x)

Nad lista jest toolbar z:
- Sort po metryce (Koszt, Konwersje, ROAS, Klikniecia, CTR, Budzet) + kierunek (malejaco/rosnaco)
- Filtr zaawansowany po metryce (np. "ROAS >= 3")

Po kliknieciu kampanii w panelu szczegolowym widze:
1. **Naglowek** — nazwa, status (kolorowy dot + label), strategia licytacji (np. TARGET_CPA), target CPA/ROAS
2. **Quick-nav buttony** — "Slowa kluczowe" i "Wyszukiwane frazy" (linkuja do odpowiednich zakladek z prefiltrem na te kampanie)
3. **Rola kampanii** — auto-klasyfikacja (Brand/Generic/Remarketing/...) z confidence %, protection level (HIGH/MEDIUM/LOW), mozliwosc recznego override + reset do auto
4. **KPI tiles** — 10 core metryk (klikniecia, wyswietlenia, koszt, konwersje, wartosc konw., CTR, avg CPC, CPA, CVR, ROAS) + 8 dodatkowych IS metryk tylko dla Search (Impr. Share, Top IS, Abs Top IS, Budget Lost IS, Rank Lost IS, Click Share, Abs Top %, Top Impr %)
5. **Trend Explorer** — wielometrykowy wykres dzienny (do 5 metryk naraz) z korelacja Pearsona, dual axis (% vs absolutne), markery akcji (Helper vs zewn.)
6. **Pacing budzetu** — progress bar: wydane vs oczekiwane vs prognozowane, status (na torze/przekroczenie/niedostateczne), dzien X z Y
7. **Urzadzenia** — breakdown mobile/desktop/tablet z % klikniec, CTR, CPC, ROAS
8. **Top miasta** — tabela geo z kliknieciam, kosztem, ROAS per miasto
9. **Historia zmian** — timeline z tagiem HELPER vs ZEWN., typ operacji, entity name, before/after z micros -> PLN

Wszystko ciemny design, karty v2-card, fonty Syne/DM Sans. Data range picker w prawym gornym rogu (30 dni).

---

## Co moge zrobic

1. **Filtrowac kampanie** po typie (sidebar pills), statusie (dropdown), nazwie (search), metryce (zaawansowany filtr >= / <=)
2. **Sortowac liste** po 6 metrykach w obu kierunkach
3. **Szybko przeskakiwac** do slow kluczowych / wyszukiwanych fraz wybranej kampanii (deep-link z campaign_id)
4. **Klasyfikowac role kampanii** recznie (manual override) lub zresetowac do auto-klasyfikacji
5. **Analizowac trendy** — dodawac/usuwac metryki na wykresie (do 5), widziec korelacje miedzy nimi
6. **Identyfikowac wzorce** — markery akcji na wykresie (czy zmiana stawki wplynela na metryki?)
7. **Monitorowac pacing** — czy kampania wydaje za duzo/za malo vs budzet
8. **Analizowac urzadzenia** — ktore urzadzenie daje najlepszy ROAS/CTR
9. **Analizowac lokalizacje** — ktore miasta generuja najlepszy zwrot

---

## Co mam WIECEJ niz w Google Ads UI

1. **Rola kampanii z auto-klasyfikacja** — Google Ads nie ma "campaign role" (Brand/Generic/Remarketing). Musze to sobie robic recznie w konwencjach nazewnictwa lub labelkach. Tu mam auto-detect z confidence score + manual override. Bardzo przydatne.

2. **Korelacja Pearsona na wykresie trendow** — Google Ads UI nie pokazuje korelacji miedzy metrykami. Jak porownuje koszt vs konwersje, musze to oceniac na oko. Tu widze liczbowa korelacje (+0.85 silna, -0.42 umiarkowana) — to oszczedza czas analizy.

3. **Unified action timeline z before/after** — Google Ads ma "Change History" ale jest to osobny widok, nie zintegrowany z kampania. Tu widze zmiany bezposrednio w kontekscie kampanii, z tagiem "Helper" vs "zewnetrzna", plus before/after w czytelnym formacie (Stawka: 1.50 -> 2.00 zl).

4. **Markery akcji na wykresie trendow** — w Google Ads nie ma markerow "tu zmieniles stawke" na wykresie metryk. Tu widze pionowe linie w dniach zmian. Mega przydatne do oceny cause-effect.

5. **Protection level** — auto-informacja jak bardzo kampania jest chroniona przed automatycznymi zmianami. Google Ads nie ma nic takiego.

6. **Budget pacing z prognoza** — Google Ads pokazuje "ile wydales" ale nie prognozuje "ile wydasz do konca miesiaca" w tak czytelnej formie (progress bar + projected spend).

---

## Czego MI BRAKUJE vs Google Ads UI

1. **Edycja budzetu inline** — w Google Ads klikam w budzet i go zmieniam. Tu widze budzet, pacing, ale nie moge go edytowac. To krytyczne — jesli widzac pacing "przekroczenie" nie moge od razu zmniejszyc budzetu, to musze przeskakiwac do Google Ads UI.

2. **Zmiana statusu kampanii** (pause/enable) — widze status, ale nie moge go zmienic. Jesli mam kampanie ktora spala kase i chce ja wstrzymac, musze isc do Google Ads.

3. **Strategia licytacji — edycja** — widze TARGET_CPA/TARGET_ROAS, ale nie moge zmienic targetow. Jesli CPA jest za wysoki, chcialbym go podniesc/obnizyc bez wychodzenia z toolki.

4. **Reklamy (Ads)** — kompletny brak. W Google Ads widze liste reklam per kampania/ad group z headline'ami, opisami, approval statusem, ad strength. Tu nie ma nic o reklamach. Nie wiem nawet ile reklam mam w kampanii.

5. **Ad Groups** — nie ma widoku grup reklam. W Google Ads kampania -> ad groups -> keywords/ads to podstawowa hierarchia. Tu przeskakuje z kampanii prosto do keywords, pomijajac warstwe ad group.

6. **Harmonogram reklam (Ad Schedule)** — nie widze kiedy kampania jest aktywna (godziny/dni tygodnia). W Google Ads to podstawowa informacja do optymalizacji.

7. **Odbiorcy (Audiences)** — brak informacji o listach odbiorcow podpietych do kampanii (remarketing, in-market, custom audiences).

8. **Rozszerzenia reklam (Assets/Extensions)** — brak informacji o sitelinkach, calloutach, structured snippets etc. podpietych do kampanii.

9. **Quality Score na poziomie kampanii** — brak zagregowanego "zdrowia" kampanii z perspektywy quality score (sredni QS slow kluczowych w kampanii).

10. **Negatywne slowa kluczowe** — nie widze listy negatywow dla kampanii. Linkuie do keywords, ale negatywy to osobna kwestia.

11. **Historyczne porownanie okresow** — w Google Ads moge "Compare: Previous period" i widziec kolumny obok siebie. Tu widze change %, ale nie mam side-by-side.

12. **Eksport danych** — nie moge wyeksportowac danych kampanii do CSV/Excel.

---

## Co mnie irytuje / myli

1. **Pola "budget_usd" i "cost_usd" w kodzie** — wyswietlam w zlotowkach (zl), ale zmienne w kodzie maja suffix `_usd`. To mylace — nie wiem czy to dolary przeliczone na zlote, czy zlote nazwane jako usd. W UI widze "zl" wiec pewnie ok, ale dev powinien to posprzatac.

2. **"Save override" i "Reset to auto" po angielsku** — caly UI jest po polsku, ale te dwa buttony sa po angielsku. Niespojne. Albo "Use auto classification" w dropdownie.

3. **Sekcja "Rola kampanii" zabiera za duzo miejsca** — to techniczny feature (klasyfikacja AI), ale zajmuje cala szerokosc panelu i jest nad KPI tiles. Dla mnie jako uzytkownika, KPI tiles sa wazniejsze niz rola kampanii. Przenioslbym role nizej lub zwinalby ja do collapsible.

4. **KPI tiles 5 kolumn — jest ich 10 + 8 IS** — przy 18 kafelkach to 4 rzedy po 5. Na mniejszym ekranie moze byc przytlaczajace. Moze warto grupowac: core (5 najwazniejszych) + rozwiniety widok z reszta?

5. **Brak legendy statusow na liscie** — kolorowe kropki przy kampaniach, ale nie ma legendy. Nowy uzytkownik nie wie co zielona/zolta/czerwona oznacza (dopoki nie najedzie na panel szczegolowy i zobaczy label).

6. **Trend Explorer bez mozliwosci eksportu** — moge ogladac trend, ale nie moge pobrac danych do dalszej analizy (np. do raportu dla klienta).

7. **Geo "Top miasta" obciete do 8** — a jesli prowadze kampanie na cala Polske i chce widziec wiecej miast? Nie moge rozwinac ani przefilctrowac.

8. **Brak direct-linku do kampanii w Google Ads** — jesli widze problem i chce szybko przejsc do kampanii w natywnym UI, nie mam linka.

---

## Co bym chcial

1. **Inline edycja budzetu** (klik -> edit -> save) z walidacja (np. min 10 zl, max budzet klienta)
2. **Pause/Enable kampanii** jednym kliknieciem (z potwierdzeniem)
3. **Edycja target CPA/ROAS** dla smart bidding
4. **Zakladka "Reklamy"** z lista ads per kampania (headline, opis, typ, ad strength, approval status)
5. **Warstwa Ad Groups** — chociaz jako tree-view w liscie kampanii
6. **Deep-link do Google Ads UI** — "Otworz w Google Ads" button per kampania
7. **Eksport danych** kampanii do CSV
8. **Comparison mode** — porownanie 2 okresow obok siebie
9. **Collapsible sekcja "Rola kampanii"** — domyslnie zwiniety, rozwijam jak potrzebuje
10. **Legenda statusow** na liscie kampanii (lub tooltip na kropce)
11. **Geo view z mapa** lub przynajmniej pelna lista miast z paginacja
12. **Negatywne slowa kluczowe** lista per kampania
13. **Ad Schedule heatmapa** — kiedy kampania performuje najlepiej (dzien tygodnia x godzina)
14. **Polskie tlumaczenia** dla "Save override", "Reset to auto", "Use auto classification"

---

## Verdykt

**Zakladka Campaigns to SOLIDNY przeglad kampanii z kilkoma unikalnymi featurami** (rola kampanii, korelacja, action timeline z markerami). Master-detail layout jest czytelny i pozwala szybko przeskakiwac miedzy kampaniami bez przeladowania strony.

**Najwiekszy problem: read-only.** Widze metryki, pacing, ale nie moge nic zmienic (budzet, status, target CPA/ROAS). To sprawia, ze zakladka jest diagnostyczna, ale nie operacyjna — ciagle musze wracac do Google Ads UI zeby wykonac akcje.

**Drugi problem: brak warstwy reklam i ad groups.** Kampanie bez reklam to polowa obrazka. Nie wiem czy moje reklamy maja dobry ad strength, czy sa approved, ile mam aktywnych RSA vs ETA.

**Jako PPCowiec uzylbym tej zakladki do:** szybkiego przegladu performance, identyfikacji kampanii z problemami (pacing, spadek ROAS), analizy trendow z korelacja, i sprawdzenia czy auto-klasyfikacja ról jest poprawna. Ale na krotko — bo kazde dzialanie wymaga przeskoku do Google Ads.

**Ocena: 6.5/10** — dobra diagnostyka, ale bez mozliwosci dzialania.

---

## Pytania do @ads-expert

1. Czy auto-klasyfikacja ról kampanii (Brand/Generic/Remarketing) ma realna wartosc dodana w toolce, czy to "nice to have" ktore nikt nie uzywa w praktyce?
2. Korelacja Pearsona na wykresie — czy to faktycznie uzyteczne operacyjnie, czy bardziej "wygladajacy madrze" feature?
3. Brak warstwy Ad Groups — czy to swiadome uproszczenie, czy luka ktora trzeba wypelnic?
4. Protection level (HIGH/MEDIUM/LOW) — skad sie bierze i jak wplywa na zachowanie toolki? Czy to blokuje jakies automatyczne akcje?
5. Budget pacing jest per kampania — czy powinien byc tez zagregowany na poziomie konta (calkowity budzet klienta vs suma kampanii)?
6. Impression Share metryki widoczne tylko dla Search — a co z Shopping IS? Google API to zwraca.
7. Czy brak Ad Schedule view to duza luka, czy mniej istotna w erze smart bidding (gdzie Google sam optymalizuje czas wyswietlania)?
