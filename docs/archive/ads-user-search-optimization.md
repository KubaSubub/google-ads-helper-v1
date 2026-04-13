# Notatki usera: Optymalizacja SEARCH — RE-TEST #3 (po Wave A-E)

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** seed data / Demo Meble Sp. z o.o.
**Data:** 2026-03-28

---

## Co widzę po wejściu

Wchodzę na zakładkę "Optymalizacja" i widzę stronę z tytułem "Optymalizacja SEARCH". Od razu otwarte są 3 sekcje: **Zmarnowany budżet**, **Harmonogram (dni tygodnia)** i **Analiza dopasowań**. Reszta to zamknięte akordeony z ikonkami — mogę kliknąć i rozwinąć.

Pierwsze wrażenie: to jest **kombajn**. Widzę 33 sekcji w jednym scrollowalnym widoku. Z jednej strony mam wszystko w jednym miejscu, z drugiej — to przytłaczające. W Google Ads te dane są rozsiane po kilkunastu raportach i zakładkach.

Zmarnowany budżet od razu przyciąga wzrok — widzę kwotę waste w złotówkach i procent. To jest coś czego w GAds nie mam od ręki.

## Co mogę zrobić

1. **Rozwijać/zwijać sekcje** — klik na nagłówek każdej karty
2. **Wykluczyć search term** — przycisk "Wyklucz" w sekcji Zmarnowany budżet (jedyna akcja write na tej stronie!)
3. **Przełączać n-gram size** — tabsy Słowa/Bigramy/Trigramy
4. **Przełączać widok PMax** — Tabela/Trend
5. **Klikać linki do miejsc docelowych** (sekcja Placements — otwiera URL w nowej karcie)
6. **Filtrować globalnie po datach** — z paska filtrów w sidebarze

I to tyle z interakcji. Reszta to wyłącznie read-only tabele i wykresy.

## Co mam WIĘCEJ niż w Google Ads UI

1. **Zmarnowany budżet w jednym widoku** — w GAds muszę ręcznie filtrować keywords bez konwersji i liczyć waste w arkuszu. Tu mam to w jednej karcie z kwotą i %.

2. **N-gram analysis** — tego w GAds nie ma w ogóle. Muszę eksportować search terms do arkusza i robić pivot. Tu mam gotowe uni/bi/trigramy z kosztami i konwersjami.

3. **Kanibalizacja PMax ↔ Search** — absolutny killer feature. W GAds nie widzę które search terms nakładają się między PMax a Search. Tu mam tabelę z wyraźnym "Zwycięzcą" per fraza.

4. **Auction Insights z trendem** — w GAds mam auction insights ale muszę ręcznie porównywać okresy. Tu mam trend IS konkurentów na wykresie liniowym. Wiersz "Ty" jest wyróżniony niebieskim.

5. **Brakujące rozszerzenia audit** — szybki audit per kampania ile sitelinków/calloutów/snippets brakuje. W GAds muszę wchodzić w każdą kampanię osobno.

6. **Grupy produktów Shopping** — wydajność product groups w tabeli: ROAS per grupa, kolorowanie (zielony ≥3, żółty 1-3, czerwony <1). W GAds jest to rozsiane po raportach Shopping.

7. **Placements (Display/Video)** — top 50 miejsc docelowych z kosztami, konwersjami i ROAS. Klikalne linki. Video views i view rate widoczne jeśli dane istnieją.

8. **Tematy Display/Video** — topic performance z ROAS. W GAds jest to w zakładce Topics, tu zbiorczo.

9. **Modyfikatory stawek** — device, location, ad schedule bid modifiers w jednej tabeli. Widzę +20%, -30%, "Wykluczono". W GAds to rozsiane po ustawieniach kampanii.

10. **Rekomendacje Google** — lista natywnych rekomendacji Google pogrupowanych per typ. W GAds mam to samo, ale tu jest obok moich playbook-owych rekomendacji (z zakładki Rekomendacje).

11. **Pareto 80/20**, **Target vs Rzeczywistość**, **Struktura konta audit**, **Demografia z anomaliami** — to wszystko analizy których w GAds nie mam "out of the box".

## Czego MI BRAKUJE vs Google Ads UI

1. **Zero write actions poza "Wyklucz"** — nie mogę pauzować keywordów, zmieniać stawek, edytować budżetów. W GAds mogę działać od razu.

2. **Brak filtrów per kampania** — w GAds mogę filtrować każdy raport po kampanii/grupie/etykiecie. Tu globalne filtry dat i tyle. Mam 33 sekcje ale nie mogę powiedzieć "pokaż mi to tylko dla kampanii Branded".

3. **Brak placement exclusions** — widzę placements ale nie mogę wykluczyć złego placement'u z tego widoku.

4. **Brak bid modifier editing** — widzę modyfikatory ale nie mogę ich zmienić. Read-only.

5. **Google Recommendations bez Apply/Dismiss** — to lista bez akcji.

## Co mnie irytuje / myli

1. **33 sekcje w jednym widoku to za dużo** — scroll jest nieskończony. Potrzebuję nawigacji bocznej lub kategoryzacji.

2. **"Optymalizacja SEARCH"** ale widzę też sekcje Display, Video, Shopping, PMax — nazwa nie pasuje do treści.

3. **Auction Insights "Pozycja wyżej %"** — nie wiem czyja pozycja jest wyżej bez tooltipa.

4. **Sekcje "Brak danych" po sync** — nowe sekcje wymagają dodatkowego sync ale user nie wie że musi odpalić sync z konkretną fazą.

5. **34 API calle na wejście** — lag odczuwalny.

## Co bym chciał

1. **Quick actions** — "Pauzuj", "Zmień stawkę", "Wyklucz" przy wierszach w tabelach
2. **Filtr per kampania** na każdej sekcji
3. **Grupowanie sekcji** — kategorie: "Audyt Search", "PMax", "Display/Video", "Konkurencja"
4. **Priorytety** — "3 rzeczy do zrobienia dziś" na górze strony
5. **Export PDF** — cały raport do prezentacji dla klienta

## Verdykt

To jest **najlepsza zakładka w aplikacji** pod względem wartości analitycznej. Mam tu więcej insightów w jednym miejscu niż w całym Google Ads UI. Ale to jest **read-only dashboard, nie narzędzie optymalizacyjne**. Wchodzę tu żeby wiedzieć CO robić, ale potem idę do GAds żeby TO ZROBIĆ.

Nowe sekcje (Auction Insights, Shopping, Placements, Topics, Bid Modifiers, Google Recommendations) — solidna baza, ale wymagają sync i write actions żeby być naprawdę użyteczne.

Ocena: **8/10** jako analityka (było 7.5, +0.5 za 6 nowych sekcji), **4/10** jako narzędzie do działania.

---

## Pytania do @ads-expert

1. Jedyna akcja write to "Wyklucz" w Wasted Spend — czy jest plan dodania pause/bid actions w tabelach?
2. Auction Insights — "Pozycja wyżej %" nie ma tooltipa wyjaśniającego kierunek. Bug czy design?
3. Google Recommendations — lista typów bez Apply/Dismiss. Stub do dorobienia?
4. 34 API calle na wejście — plan na lazy loading per sekcja?
5. Nazwa "Optymalizacja SEARCH" nie pasuje do treści (obejmuje Display/Video/Shopping/PMax) — zmienić?
6. Bid Modifiers read-only — kiedy planujecie write operations?
7. Brak globalnego filtra kampanii — #1 request. W roadmapie?
