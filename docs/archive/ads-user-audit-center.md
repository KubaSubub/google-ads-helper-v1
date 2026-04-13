# Notatki usera: Centrum Audytu (Audit Center)

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Data:** 2026-03-29

---

## Co widze po wejsciu

Duzy naglowek "Centrum audytu" z podtekstem "Analiza 30 dni -- 28 sekcji". Pod spodem pasek filtrow typu kampanii: Wszystkie, Search, PMax, Shopping, Display, Video. Jest tez osobny blok "Filtry kampanii" z dropdownem STATUS (Wszystkie) i polem szukaj po nazwie kampanii.

Nad kartami jest alert czerwony: "2 problemy wymagaja uwagi: Strategia bidowania, Jakosc konwersji". To od razu przyciaga wzrok i mowi mi, co jest pilne -- super.

Ponizej siatka kart (bento grid), kazda karta ma:
- Ikone + nazwe sekcji audytu
- Wartosc glowna (np. "358 zl", "5 zmian", "100/100")
- Kolorowa kropke statusu (zielona = OK, pomaranczowa = warning, czerwona = danger)
- Podtekst z kontekstem (np. "0.5% spend, 0 kategorii")
- Na niektorych kartach zmiana procentowa vs poprzedni okres (np. strzalka -12%)

Widze karty: Zmarnowany budzet, Strategia bidowania, Zdrowie konwersji, Jakosc konwersji, Target vs Rzeczywistosc, Smart Bidding, Dopasowania, Harmonogram tygodnia, Harmonogram godzinowy -- i dalej widac ze jest jeszcze duzo wiecej pod foldem.

Po kliknieciu w karte otwiera sie drill-down z pelnym widokiem danej sekcji (tabela, metryki, szczegoly).

## Co moge zrobic

1. **Filtrowac po typie kampanii** -- pille Wszystkie/Search/PMax/Shopping/Display/Video zmieniaja widoczne karty. Sensowne -- jak pracuje na koncie z PMax i Search, moge szybko zobaczyc co dotyczy czego.
2. **Filtrowac po statusie kampanii i nazwie** -- dodatkowy blok "Filtry kampanii" z dropdownem i polem tekstowym.
3. **Kliknac w karte** -- drill-down do pelnej analizy sekcji. Np. "Zmarnowany budzet" pokazuje breakdown na keywords, search terms, reklamy z kwotami i przyciskiem "Wyklucz" (dodaje negatyw!).
4. **Przypinac karty** (pin icon) -- przypiete karty ida na gore siatki, zapamietywane w localStorage. Moge odepnac wszystkie jednym przyciskiem.
5. **Zmieniac zakres dat** -- selektor "30 dni" w gornym prawym rogu globalnie wplywa na dane.
6. **Dodawac negatywy** -- w sekcji Wasted Spend przy frazach wyszukiwania jest przycisk "Wyklucz" ktory bezposrednio dodaje negatyw.

## Co mam WIECEJ niz w Google Ads UI

1. **Jeden widok na 28 sekcji audytowych** -- w Google Ads UI musialabym skakac miedzy 8-10 roznych zakladek zeby zebrac te same informacje. Tutaj mam dashboard audytowy w jednym miejscu.
2. **Automatyczny alert o problemach** -- czerwony banner "2 problemy wymagaja uwagi" z listowaniem. Google Ads daje Recommendations, ale nie robi priorytetyzacji w tak jasny sposob.
3. **Porownanie z poprzednim okresem na kartach** -- zmiana procentowa (np. -12% na zmarnowanym budzecie) od razu na karcie, bez koniecznosci recznego porownywania.
4. **Kanibalizacja PMax vs Search** -- dedykowana sekcja porownujaca frazy pokrywajace sie miedzy PMax a Search z CPA per kanal i wskazaniem zwyciezcy. Google Ads tego NIE pokazuje natywnie -- to mega wartosc.
5. **N-gramy** z mozliwoscia przelaczania uni/bi/trigramy i tabela z CVR/CPA per n-gram. W Google Ads musisz to robic recznie w Excelu.
6. **Smart Bidding Health** per kampania z progiem minimum konwersji i statusem Zdrowa/Krytyczna/Niski wolumen. Google Ads nie podsumowuje tego w jednym miejscu.
7. **Target vs Rzeczywistosc** -- porownanie celu CPA/ROAS z aktualnym wynikiem z odchyleniem procentowym. W Google Ads to trzeba klikac w kazda kampanie osobno.
8. **Jakoscz konwersji** -- audyt ustawien konwersji (primary/secondary, attribution, lookback) z issue list. W Google Ads musisz to sprawdzac recznie w Settings > Conversions.
9. **Bezposrednia akcja z audytu** -- przycisk "Wyklucz" przy wasted search terms. Nie trzeba kopiowac frazy i isc osobno dodawac negatyw.
10. **Pinowanie kart** -- personalizacja widoku audytu pod moje priorytety. Google Ads tego nie ma.

## Czego MI BRAKUJE vs Google Ads UI

1. **Optimization Score** -- Google Ads ma swoj global score 0-100% z wagami. Tu mam 28 oddzielnych sekcji, ale brakuje jednego globalnego "stanu konta" na gorze (np. "Konto: 72/100").
2. **Historyczny trend sekcji** -- widze zmiane % vs poprzedni okres, ale nie widze wykresu trendu w czasie (np. jak wasted spend zmienial sie z tygodnia na tydzien przez ostatni kwartal).
3. **Priorytetyzacja/sortowanie kart** -- karty sa w ustalonej kolejnosci (z pinami na gorze), ale brakuje sortowania po "severity" -- np. najpierw danger, potem warning, potem OK. Teraz danger moze byc w polowie grida.
4. **Szacunkowy impact finansowy** -- wiem ze mam 5 zmian w strategii bidowania, ale ile to kosztuje? Google Ads Recommendations podaje szacunkowy uplift/savings. Tu brakuje "napraw to a zaoszczedzisz ~X zl/msc".
5. **Export/raport PDF** -- nie widze mozliwosci wygenerowania raportu audytowego dla klienta. Jako specjalista czesto robie audyty dla nowych klientow albo miesieczne raporty -- PDF z wynikami audytu bylby killer feature.
6. **Porownanie z benchmarkami branzy** -- widze ze CVR jest X%, ale nie wiem czy to dobrze dla mojej branzy. Google Ads daje "competitor benchmarks" w niektorych raportach.
7. **Action items z przypisaniem priorytetu** -- sekcja "Rekomendacje Google" jest, ale brakuje ujednoliconej listy "co zrobic teraz" ze wszystkich 28 sekcji. Cos jak lista TODO z audytu.
8. **Change log / historia audytow** -- nie widze historii: "ostatnio audyt robiono 7 dni temu, od tamtego czasu X sie zmienilo". Przydatne zeby sledzic postep napraw.

## Co mnie irytuje / myli

1. **Dwa poziomu filtrow jednoczesnie** -- na gorze jest blok "Filtry kampanii" (STATUS + szukaj po nazwie), a pod tytulem pill-buttons z typem kampanii. Nie od razu wiadomo, ze oba dzialaja razem. Moze polczyc w jeden pasek filtrow?
2. **28 sekcji to duzo** -- przy "Wszystkie" widze ogromna siatke. Pierwsza reakcja to "ooo, ale duzo" -- troche przytlaczajace. Moze grupowanie kategorialne (Budget, Quality, Search-specific, PMax-specific) albo zwijane sekcje?
3. **Karty z wartoscia "---"** -- kilka kart pokazuje myslnik zamiast danych. Nie wiem czy to bug, brak danych, czy sekcja nie dotyczy mojego typu kampanii. Lepiej byloby napisac "Brak danych" albo ukryc karte.
4. **"100/100" na Zdrowie konwersji** a "5/100" na Jakosc konwersji -- dwie podobne nazwy, rozne score'y. Czy to ta sama metoda scoringu? Myli sie. Moze dodac tooltip albo wiecej kontekstu na karcie.
5. **Brakujace animacje/loading per karta** -- caly ekran ma loader, ale jak dane sie dociagaja per sekcja (np. ngram zmienia sie osobno), nie widze feedbacku.
6. **Przypiete karty nie maja wizualnego "separatora"** -- pinned karty ida na gore, ale nie ma linii/naglowka "Przypiete" vs "Pozostale". Moglbym nie zauwazyc ze cos jest przypiete jesli nie widze pinezki.

## Co bym chcial

1. **Globalny Audit Score** -- jeden numer na gorze (np. 72/100) z rozbiciem na kategorie (Budget, Quality, Structure). Jak traffic light dla calego konta.
2. **Widok "Action Plan"** -- ze wszystkich 28 sekcji wygeneruj liste top-10 akcji do zrobienia, posortowanych po szacowanym impakcie. "Napraw A -- szacowane oszczednosci 500 zl/msc", "Napraw B -- poprawa CVR o ~15%".
3. **Export do PDF** -- wygeneruj raport audytowy z datowaniem, logo klienta, wynikami sekcji. Idealny dla klientow i zebrania wewnetrznych.
4. **Kategorie kart z zwijaniem** -- np. "Budzet i bidding (7 sekcji)", "Jakosc reklam (5 sekcji)", "Struktura konta (4 sekcji)". Pozwala ogarnac 28 sekcji.
5. **Scheduled audit** -- cykliczny audyt (co tydzien/miesiac) z powiadomieniem jesli score spadnie ponizej progu. "Uwaga: Optimization Score spadl z 78 na 62 w tym tygodniu".
6. **Porownanie konto vs konto** -- mam 8 kont, chcialabym porownac wyniki audytu miedzy nimi (benchmark wewnetrzny).
7. **Integracja z Google Recommendations** -- sekcja "Rekomendacje Google" jest, ale chcialbym moc je accept/dismiss bezposrednio z tego widoku (tak jak moge dodawac negatywy z Wasted Spend).

## Verdykt

Centrum Audytu to najlepsza zakladka w calym narzedziu i cos czego najbardziej brakowalo mi w codziennej pracy. W Google Ads zrobienie pelnego audytu konta to 2-3 godziny skakania po zakladkach -- tutaj mam widok na 28 obszarow w jednym miejscu z drill-downem, statusami i nawet akcjami (negatywy!). Kanibalizacja PMax/Search i Smart Bidding Health to pure gold. Jedyne co brakuje to synteza -- globalny score i action plan, zeby z 28 sekcji zrobic 5 konkretnych krokow do zrobienia TERAZ.

---

## Pytania do @ads-expert

1. Czy 28 sekcji to nie za duzo? Moze podzielic na "Core audit" (10-12 najwazniejszych) i "Extended" (reszta)? Jaka jest optymalna granulacja dla codziennego uzycia vs kwartalnego audytu?
2. Jak powinien wygladac globalny Audit Score? Proste srednia z 28 sekcji, czy wazona (np. wasted spend i konwersje wazniejsze niz demografia)?
3. Sekcja "Rekomendacje Google" -- czy powinna byc read-only (jak jest), czy powinno sie moc accept/dismiss bezposrednio? Jakie ryzyka?
4. Czy sekcja "Konwersje offline" i "Reguly wartosci" nie powinny byc raczej w Settings/Ustawienia niz w audycie? Bo to bardziej config niz performance review.
5. Brakuje mi sekcji o feedzie produktowym (Merchant Center) dla Shopping/PMax. Czy to swiadomie poza scopem (bo wymaga innego API), czy przeoczenie?
6. Target vs Rzeczywistosc pokazuje $ zamiast zl -- bug czy celowe (konto w USD)?
7. Jak czesto powinienem odpalac ten audyt? Codziennie, tyg, miesiescznie? Czy kazda czestotliwosc ma inne "must-see" sekcje?
