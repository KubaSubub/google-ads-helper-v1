# Notatki usera: Wyszukiwane frazy (Search Terms) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** Demo Meble Sp. z o.o. (seed data) — screenshot + kod
**Data:** 2026-03-29 (re-test po sprincie)

---

## Co widze po wejsciu

Naglowek "Wyszukiwane frazy" z liczba wyszukiwan (77 wyszukiwan). Widok domyslny: **Segmenty**. Po prawej 4 przyciski widoku: Segmenty / Lista / Trendy / Warianty + eksport CSV/XLSX.

Pod naglowkiem 4 kolorowe karty segmentow:
- **Top Performerzy** (zielona) — 0 fraz
- **Strata** (czerwona) — 0 fraz
- **Nieistotne** (szara) — 0 fraz
- **Inne** (niebieska) — **5 fraz**

Wszystkie frazy laduja w "Inne" bo seed data nie ma wystarczajacych danych do automatycznej klasyfikacji (brak fraz z zerowa konwersja i wysokim kosztem = brak WASTE, brak fraz z wysokim CVR = brak TOP_PERFORMER).

Tabela z kolumnami: checkbox | Segment | Fraza | Kampania | Klikniecia | Koszt | Konwersje | CVR | Powod | Akcje.

Widoczne frazy: "biurko do domu" (51 klikniec, 190.80 zl, 3.2 konw, 6.24%), "lozko drewniane 160x200" (116 klik, 165.04 zl, 7.8 konw, 6.69%), "kanapa narozna" (33 klik, 151.33 zl, 6.2 konw, 18.91%), "sofa rozkladana" (60 klik, 148.67 zl, 3.7 konw, 6.12%), "lozko drewniane" (48 klik, 40.94 zl, 2.5 konw, 5.12%).

Powod dla wszystkich: "Niewystarczajace dane do klasyfikacji..." — uciety tekst.

## Co moge zrobic

- **Przelaczac widoki** — Segmenty (domyslny), Lista (flat z paginacja, search input), Trendy (rosnace/spadajace/nowe), Warianty (close variant analysis)
- **Filtrowac po segmencie** — klikam karte Top Performerzy/Strata/Nieistotne/Inne — toggles aktywny segment
- **Zaznaczac frazy bulk** — checkbox per wiersz + "zaznacz wszystkie" w headerze
- **Bulk dodac negatywy** — "Dodaj jako negatywy (EXACT)" — sticky bar z liczba zaznaczonych
- **Bulk dodac slowa kluczowe** — przycisk jest ale pokazuje tylko toast informacyjny
- **Inline akcje** — "Dodaj slowo" na Top Performerach, "Wyklucz" na Strata/Nieistotne (teraz z prawdziwym API callem!)
- **Sortowac w Segmentach** — naglowki Fraza/Klikniecia/Koszt/Konwersje/CVR sa klikalne (sortowanie client-side)
- **Sortowac w Liscie** — naglowki Fraza/Klikniecia/Wyswietlenia/Koszt/Konwersje/CTR (server-side)
- **Szukac** — input w trybie Lista
- **Paginacja** — 50 per strona w trybie Lista
- **Eksport CSV/XLSX** — przyciski zawsze widoczne
- **Filtry globalne** — typ kampanii (sidebar pills), status, zakres dat (30 dni domyslnie)

## Co mam WIECEJ niz w Google Ads UI

1. **Automatyczna segmentacja fraz** — GAds pokazuje plaska liste. Tu mam 4 segmenty z 1 kliknieciem. To jest core value tej zakladki. Rano otwieram → Strata → bulk wyklucz. W GAds to 30 min recznej pracy.
2. **Waste callout banner** — czerwony alert "Zmarnowany budzet: X zl" + info ile fraz juz wykluczone a ile nie. GAds nic takiego nie ma.
3. **Bulk negatywy jednym klikiem** — zaznaczam frazy, "Dodaj jako negatywy (EXACT)" — gotowe. W GAds: Negative keywords → Add → recznie jedna po drugiej.
4. **Inline wykluczenie** — klikam "Wyklucz" na frazie WASTE → API call → od razu wykluczona. Nie muszac opuszczac strony. **Naprawione vs ostatni test!**
5. **Close variant analysis** — widze ile kosztuja bliskie warianty vs exact matches, z podsumowaniem kosztu wariantow.
6. **Trend frazy** — rosnace/spadajace/nowe frazy z porownaniem okresow. W GAds mogę co najwyzej dodac kolumne "zmiana" ale nie tak przejrzyscie.
7. **Eksport z segmentacja** — CSV/XLSX jednym klikiem, dane juz posegmentowane.
8. **Status "Juz wykluczone"** — przy frazach ktore sa already_negative, zamiast przycisku "Wyklucz" widac badge "Juz wykluczone". W GAds nie widac tego inline.

## Czego MI BRAKUJE vs Google Ads UI

1. **Match type w widoku Lista** — w GAds widze czy fraza byla dopasowana jako EXACT, PHRASE, BROAD. W widoku Lista nie ma tej kolumny. Jest w Wariantach (close variants), ale nie w glownej tabeli. Jako PPCowiec potrzebuje widziec match type OBOK frazy.
2. **Kolumna "Grupa reklam"** — w GAds widze search term → ad group → keyword. Tu widze tylko kampanie. Brak powiazania fraza → grupa reklam → slowo kluczowe.
3. **Filtr po kampanii w Segmentach** — moge filtrowac globalnie po typie kampanii (sidebar), ale nie mam szybkiego dropdowna "pokaz frazy tylko z kampanii X". Kolumna Kampania jest, ale nie klikalna.
4. **Wartosc konwersji** — widzę konwersje (ilosc) ale nie wartosc konwersji. Przy e-commerce (meble!) ROAS/wartość jest wazniejsza niz liczba konwersji.
5. **Wyswietlenia w widoku Segmenty** — w Lista sa, w Segmentach nie. Chcę wiedziec ile razy fraza sie wyswietlila (impression share thinking).
6. **Search terms → keyword link** — w GAds widze "dopasowane do slowa kluczowego: [meble]". Tu nie widze jakiemu slowu kluczowemu fraza odpowiada (poza zakladka Warianty).

## Co mnie irytuje / myli

1. **Wszystko w "Inne"** — na seed data 5 fraz i wszystkie w "Inne" bo "niewystarczajace dane do klasyfikacji". Rozumiem logike (seed), ale na prawdziwych danych tez sie moze zdarzac. Frustrujace gdy otwieram zakladke i widze 0/0/0/5. Segmentacja nie daje wartosci jesli engine nie klasyfikuje.
2. **"Dodaj jako slowa kluczowe" (bulk)** — przycisk jest, klikalny, ale pokazuje tylko toast "Wybierz grupe reklam w oknie dialogowym". Zadnego okna nie ma. To jest martwy przycisk. Albo usun albo zaimplementuj.
3. **"Dodaj slowo" inline na Top Performer** — toast "przejdz do Rekomendacje, aby zastosowac". Czemu? Inline wyklucz dziala natychmiast, ale inline dodaj slowo — nie. Niespojnosc.
4. **Powod uciety** — kolumna "Powod" ma text-overflow ellipsis. Widze "Niewystarczajace dane do klasyfik..." — nie moge przeczytac calego powodu bez hover tooltip (ktorego nie ma).
5. **Brak widocznego linku miedzy widokami** — jestem w Segmentach, klikam fraze i... nic. Nie moge przejsc do Listy z filtrowana ta fraza, ani do szczegolowego widoku frazy.

## Co bym chcial

1. **Match type kolumna** — zarowno w Lista jak i Segmenty. Minimum w Lista.
2. **Wartosc konwersji** — kolumna conversion_value obok conversions + ROAS.
3. **Tooltip na "Powod"** — hover na uciętym tekscie pokazuje pelen powod segmentacji.
4. **"Dodaj jako slowa kluczowe"** — albo zaimplementowac (dialog z wyborem ad group + match type) albo usunac przycisk.
5. **Klikalna kampania** — klik na nazwe kampanii w tabeli → filtruje search terms do tej kampanii.
6. **Progi segmentacji** — info/config ile klikniec/konwersji potrzeba aby fraza wpadla do segmentu, zeby nie miec 100% "Inne".

## Verdykt

Zakladka search terms to **jeden z najsilniejszych elementow tej aplikacji**. Segmentacja + bulk negatywy + waste callout + inline wyklucz + trend analysis + close variants — to jest pelny workflow PPCowca do zarzadzania search terms. W Google Ads UI spedzam 30 minut na recznej analizie i 15 min na wykluczaniu. Tu robie to w 5 minut.

Od ostatniego testu naprawiono kluczowe rzeczy: sortowanie w Segmentach dziala, inline "Wyklucz" robi prawdziwy API call. To duzy krok.

Ciagle brakuje: match type, wartosc konwersji, link fraza→keyword. Martwy przycisk "Dodaj jako slowa kluczowe" psuje zaufanie. Seed data klasyfikujaca wszystko jako "Inne" nie pokazuje potencjalu segmentacji.

**Ocena: 8.5/10** (wzrosla by do 9+ z match type + conversion value + fix "Dodaj slowo")

---

## Pytania do @ads-expert

1. **Match type** — dane sa w bazie z search term report (match_type). Dlaczego nie wyswietlamy w tabeli Lista? To jest podstawowa informacja dla PPCowca.
2. **Conversion value / ROAS** — czy backend zwraca conversion_value_micros? Jesli tak — powinno byc w tabeli. Meble to e-commerce, wartosc konwersji > ilosc konwersji.
3. **"Dodaj jako slowa kluczowe"** — dead button. Plan implementacji (dialog z ad group picker + match type) czy wywalamy?
4. **Progi segmentacji** — ile klikniec/kosztu/konwersji potrzeba aby fraza wpadla do HIGH_PERFORMER vs WASTE? Moze konfiguracja per klient?
5. **Fraza → matched keyword** — w widoku Warianty widac matched_keyword. Czy mozna to samo w glownej tabeli Segmenty/Lista?
