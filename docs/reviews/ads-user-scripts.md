# Notatki usera: Skrypty

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont (mix e-comm + lead gen)
**Testowane na:** seed data / aktywny klient z sidebara (Sushi Naka Naka jako domyslny)
**Data:** 2026-04-12

> Uwaga: brak screenshota `frontend/e2e-screenshots/scripts.png`. Raport oparty o czytanie komponentu `ScriptsPage.jsx` i backendowego routera.

---

## Co widze po wejsciu

Wchodze na `/scripts`. Naglowek "Skrypty", pod nim data okresu z globalnego pickera (np. "Ostatnie 30 dni") i — jesli cos jest do zrobienia — niebieski licznik "X do wykonania · ~Y zl potencjalnej oszczednosci". Po prawej button "Odswiez". OK, od razu wiem czy cos mnie czeka.

Pod spodem lista kategorii (akordeony): **Eliminacja marnotrawstwa**, **Rozszerzenie**, **Match Type Optimization**, **N-gram Analysis**, **Temporal/Trending**, **Brand/Competitor**. Domyslnie rozwiniete "Eliminacja marnotrawstwa". Kazda kategoria ma licznik w pigulce jak cos pasuje.

W rozwinietej kategorii widze kafelki skryptow z formatu: `[A1] Zero konwersji przy wysokim koszcie`, krotki opis PL, pigulka "X do wykonania · ~Y zl" albo zielone "czysto", i przycisk **Uruchom**. Jak skrypt nic nie znalazl — przycisk jest wyszarzony.

Po kliknieciu Uruchom otwiera sie modal. Widzi tytul skryptu, zakres dat. Ekran "Parametry skryptu" (min_clicks, min_cost_pln, negative_level, match_type, brand_protection, itd.) — moge edytowac, "Odsiwiez podglad" rerenderuje liste, i przycisk "Zapisz jako domyslne dla klienta" — FAJNE, to zapamieta moje thresholdy dla tego klienta. Pod spodem lista dopasowan: checkbox, search term, kampania, powod, przykladowe terminy, szacowana oszczednosc po prawej. "Zaznacz wszystkie" u gory, licznik zaznaczonych + oszczednosc. Dla B1 pojawia sie dropdown wyboru ad group. Dla C2 (duplicate coverage) — sekcja "Wybierz ktora lokalizacje zostawic" z rekomendacja. Dla skryptow z n-gramami (D1) — taby 1/2/3/4-gram.

Na koncu "Wykonaj (N)". Po wykonaniu zielony bilans "X wykonanych", lista aplikowanych zmian, link "Zobacz w historii".

Na dole strony boxik informacyjny "Sprint 1 — P0 scripts" ktory... klama. Pisze ze "obecnie dostepny: A1" podczas gdy w katalogu juz zarejestrowanych jest 6 skryptow (A1, A2, A6, B1, C2, D1). Ten placeholder jest przeterminowany.

## Co moge zrobic

- Filtr daty — globalny picker z sidebara (rozumiem, jeden kontekst dla calej apki)
- Rozwinac/zwinac kazda kategorie
- Uruchomic dowolny skrypt w trybie preview
- Edytowac parametry skryptu inline (min_clicks, min_cost_pln, negative_level, match_type, brand_protection, itd.)
- Zapisac parametry jako domyslne dla klienta (per-client config!)
- Odznaczac pojedyncze pozycje przed wykonaniem
- Dla B1 — wybrac ad group dla promocji keywordu
- Dla C2 — wybrac ktora kampanie/ad group zostawic, reszta leci jako negative
- Dla D1 — przelaczac miedzy 1/2/3/4-gramami
- Wykonac batch, zobaczyc wynik, przejsc do historii
- Odswiezyc liczniki po zakonczeniu

## Co mam WIECEJ niz w Google Ads UI

To jest mocne. Kilka rzeczy ktore w GAds wymagaja mi 20 min grzebania, tu sa zrobione w 1 kliku:

1. **Wszystkie skrypty w jednym miejscu z licznikiem "ile do zrobienia dzis"**. W GAds to sa fragmenty rozrzucone po Search Terms Report, Keyword Ideas, Recommendations, Insights. Tu mam jeden dashboard ze shopping listem. To jest moja codzienna kawa.
2. **A1 Zero Conv Waste z brand protection wbudowana**. W GAds filtruje search terms po Conv=0 i Cost>X, ale musze pamietac zeby nie dodac negatywu na brand query. Tu to jest default=on, i mam `custom_brand_words`. To jest to czego GAds Recommendations nigdy nie ma — zero false positives na "[klient brand] menu".
3. **B1 High-Conv Promotion z automatycznym wyborem ad group**. W GAds: klikam search term, ide do "Add as keyword", potem musze wybrac ad group z dropdowna (czesto sie myle). Tu mam liste dopasowan z pre-selekcja + dropdown ma tylko SEARCH ad groups. Mniej bledow.
4. **C2 Duplicate Coverage — rzeczy ktorej GAds NIE MA**. Pokazuje mi ten sam search term targetowany z 2+ kampanii/ad groupow, sugeruje ktora zostawic na bazie konwersji, reszta ma dostac EXACT negative. To jest problem ktory w GAds polujesz manualnie przez godzine, a tu mam w kafelku.
5. **D1 N-gram Waste z tabs per size**. Excel z search terms -> kolumna z Power Query ktora liczy unigramy/bigramy/trigramy po kosztach. To byla moja regularna robota co miesiac. Tu jest w 2 klikniecia.
6. **Estimated savings w PLN, per-item i aggregate**. W GAds siedze z kalkulatorem. Tu od razu widze "~340 zl" i wiem czy warto klikac.
7. **Per-client saved params**. W GAds musze pamietac ze dla klienta X prog jest 5 klikow, dla Y 10. Tu zapisze raz i zapomne.
8. **Daily safety cap (circuit breaker)**. Nie rozwale konta dodajac 2000 negatives jednym klikiem — system tnie batch do dziennego limitu. W GAds raz tak zrobilem o 2 w nocy zmeczony, potem 2h debugowalem dlaczego CTR zjazd.

## Czego MI BRAKUJE vs Google Ads UI

1. **Filtr po kampanii wewnatrz preview**. Modal B1 moze miec 80 pozycji z 12 kampanii, a ja chce dzis tylko "kampania X". Musze scrollowac i patrzec na kampanie po prawej. Dodac dropdown "Kampania: [wszystkie]".
2. **Sortowanie listy dopasowan**. Obecnie sa w kolejnosci z backendu (prawdopodobnie po koszcie desc, ale nie moge sortowac po konwersjach / CTR / CPA). W GAds tabele zawsze klikam kolumny.
3. **Kolumny metryk — widoczne na pierwszy rzut oka**. Dla search termu widze tylko koszt/oszczednosc po prawej. A chce widziec: clicks, impr, CTR, konwersje, CPA. To jest minimum do podjecia decyzji "czy naprawde to zablokowac". Dzis musze zaufac reason-string.
4. **Historia uruchomien per skrypt**. W GAds widze "Change History" z ostatnim tygodniem. Tu mam globalny `/action-history` ale nie moge zobaczyc "Kiedy ostatnio odpalilem A1 dla tego klienta i co wyszlo". 
5. **Undo dla pojedynczej pozycji**. Jak sie pomylilem i dodalem negative "pizza napoli" gdzie powinno byc "napoli bez ananasa" — w GAds kliknje w liste negatives i usune. Tu musialbym rowniez isc do ekranu Negatives i szukac. 
6. **Scheduling**. "Uruchamiaj A1 co poniedzialek rano, jesli wiecej niz 10 pozycji — powiadom mnie". Google Ads Scripts to umozliwia, tu nie ma.
7. **Preview "przed/po" na koszcie kampanii**. "Jesli wykonasz ta akcje, spodziewany koszt kampanii nast. 7 dni: -340 zl". Mam estimated savings, ale ogolnie, nie per kampania.
8. **Negative list targeting**. Google pozwala dodac negative do globalnej listy negatywow uzywanej przez wiele kampanii. Tu jestem ograniczony do CAMPAIGN/AD_GROUP.

## Co mnie irytuje / myli

1. **Placeholder z dolu klamie**. Pisze "obecnie dostepny: A1" gdy tak naprawde jest 6 skryptow. Przy pierwszym wejsciu myslalem ze aplikacja jest undev.
2. **Dry-run w tle przy wejsciu dla WSZYSTKICH 6 skryptow rownoczesnie**. To trwa. Za kazdym razem gdy zmienie date albo klienta leci 6 requestow. Jesli backend dla C2 trwa 3 sek to caly ekran laduje 3 sek. Lepiej: ladowac lazy, tylko dla rozwinietej kategorii, reszta na zadanie.
3. **Parametr `custom_brand_words` jest ukryty (`type: 'hidden'`)**. Czyli nie moge dodac brandu klienta z poziomu UI — tylko przez backend / DB. To jest glowny problem: defaultowy auto-detect moze przegapic "nakanaka" vs "naka-naka". Jako Marek bede krzyczec ze system mi tnie brand.
4. **Brak wyboru `custom_brand_words` -> musze zaufac `brand_protection: True` i liczyc ze algorytm je zlapie**. To ryzyko.
5. **Zapis konfiguracji nie jest oddzielony od "Odsiwiez podglad"**. Jesli zmienie parametr, zapomne kliknac Odswiez, i kliknie "Wykonaj" — leci na nowych parametrach ale dry-run na starych. Trzeba force-rerun przed execute albo disable Execute dopoki nie klikne Odswiez.
6. **Parametry `number` nie maja walidacji min/max**. Mozna wpisac `min_clicks: -5` albo `min_cost_pln: 99999999`. UI powinno blokowac.
7. **Dla C2 "wybierz keepera"** wymaga klikniecia w konkretna lokalizacje ZEBY w ogole zaznaczyc item. To dodaje krok ktorego nie ma w innych skryptach — mozna by zaznaczyc item z keeperem=rekomendacja domyslnie.
8. **Modal max 760px szerokosci**. Przy 12 kolumnach metryk w wierszu to sie nie zmiesci. Powinien byc fullscreen lub resizable.
9. **Tab n-gram pokazuje `(0)`** dla wszystkich sizeow jesli nic nie pasuje — klikalnosc wylaczona ale tab widoczny. Moglby zostac schowany.
10. **Info bar "N do wykonania · szacowana oszczednosc"** jest niebieski niezaleznie czy oszczednosc to 30 zl czy 3000 zl. Jako Marek chce heatmape — oszczednosc > 500 zl = zielony, < 50 zl = szary.

## Co bym chcial

- **Grupowanie per kampania w preview**. Zwinalna sekcja "Kampania [Sushi Warszawa] — 34 pozycje · ~230 zl" -> rozwin -> pozycje.
- **Bulk param edit**. "Ustaw min_clicks=10 dla wszystkich skryptow eliminacji marnotrawstwa" zamiast per-skrypt.
- **Dry-run z cache**. Jezeli odpalilem A1 2 min temu dla tego samego zakresu dat i klienta — pokaz dane z cache i przycisk "Odswiez". Teraz lece 6 requestow za kazdym powrotem na strone.
- **Komentarze do akcji**. "Dodaje ten negatyw bo klient prosil o wylacznie pizza napoli tylko w kampanii promocyjnej". Idzie do history, moge pokazac klientowi.
- **Export listy przed wykonaniem**. CSV z pozycjami do zatwierdzenia przez klienta. Czesty workflow w agencjach.
- **Auto-run po syncu**. "Po sync danych, jesli A1 znalazl >X pozycji, wyslij mi toast/mail". Teraz musze pamietac zeby wejsc tu codziennie.
- **Counter rewidowania**. "Dla klienta X ostatni run A1 byl 3 dni temu — zalecam sprawdzenie". Zapobiega staleness.
- **"Why not" explanation**. Kliknie search term ktory mysle ze powinien byc w liscie ale go nie ma, dostaje "Nie zakwalifikowal sie bo: min_cost_pln (20 zl) niedosiegniete — ma 18 zl".
- **Preview keyword conflict**. Dla A1 widziec "Ten negatyw zablokuje Twoj keyword 'pizza napoli' w kampanii X" ZANIM wykonam — nie po.
- **Szablon raport po wykonaniu**. Dla klienta: "Wykonano A1: dodano 34 negatywow, oszczednosc 340 zl/mies. szacowana. Historia: [link]".

## Verdykt

**Tak, wchodzilbym tu codziennie rano z kawa** — to jest dokladnie ta rzecz ktora zastepuje moje 30 minut grzebania w Search Terms Report co dzien. Ale dzis jest za bardzo **demo** — brakuje filtrow, sortowania, widocznych metryk, historii uruchomien, schedulingu, exportu. To zarodek killer feature'a. Dajcie mi te 5 rzeczy i przestaje uzywac Google Ads UI do search terms w ogole.

Stosunek "wiecej niz GAds" vs "mniej niz GAds": **8 plusow vs 8 brakow, ale plusy sa core-workflow (C2, D1, brand protection, savings), a braki sa UX-polish (filtr, sort, historia)**. Czyli: dobry core, slaby shell.

---

## Pytania do @ads-expert

1. Czy A1 `brand_protection: True` + auto-detect `_build_brand_patterns` wystarczy zeby nie zablokowac brand search term na kontach z nietypowymi nazwami (np. "naka-naka", akronimy, polskie znaki)? Czy `custom_brand_words` nie powinno byc wystawione jako UI input od razu, nie jako `type: hidden`?
2. Jaki jest prog "ile oszczednosci miesiecznie robi ze skrypt jest usable a nie demo"? Czy <50 zl/mies to sygnal ze skrypt ma zla heurystyke, czy ze klient jest zdrowy?
3. Czy `min_clicks: 5` + `min_cost_pln: 20` to zdrowy default dla malych kont (Sushi Naka Naka ~500 zl/mies budzetu) czy lepiej skalowac do `min_cost_pln = budget * 0.02`?
4. Czy C2 Duplicate Coverage powinno blokowac wykonanie jesli "recommended_keeper" ma < 3 konwersji? Czyli jak dane sa cienkie — pokazac alert zamiast akcji.
5. Dla D1 N-gram — ktory size (1/2/3/4-gram) ma najlepszy ROI do blokowania? Czy 4-gramy maja sens na malych kontach (za malo wolumen zeby statystyki mialy moc)?
6. Czy powinnismy mieć osobny skrypt "A1-weekly" i "A1-monthly" z innymi progami, czy uzytkownik sam ma zmieniac params w zaleznosci od zakresu?
7. Scheduling — czy skrypty powinny sie odpalac automatycznie (cron) czy zawsze wymagac approval Marka? Gdzie jest granica "auto vs half-auto"?
8. Czy widok powinien dzielic skrypty "OK do odpalenia bez myslenia" vs "Wymaga mysli — zweryfikuj kazda pozycje"? Np. A1 auto, C2 manual.
9. Jak wyswietlic "preview after-effect" — zmiana prognozowanego kosztu kampanii po wykonaniu akcji? Na bazie czego? Na bazie dzisiejszych danych?
10. Czy przycisk "Zapisz jako domyslne dla klienta" powinien miec button "Zapisz jako domyslne dla WSZYSTKICH klientow" (moje wlasne progi)? Marek jako agencja chcialby jednego defaulta dla 8 kont.
