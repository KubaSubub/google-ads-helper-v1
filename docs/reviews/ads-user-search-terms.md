# Notatki usera: Wyszukiwane frazy (Search Terms) — RE-TEST #2

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-27 (re-test)

---

## Co widze po wejsciu

Nagłówek "Wyszukiwane frazy" z liczbą wyszukiwań. Po prawej 4 przyciski widoku: Segmenty / Lista / Trendy / Warianty. Obok search input (w trybie Lista) i eksport CSV/XLSX. Domyślnie widok Segmenty — 4 kolorowe karty (Top Performerzy, Strata, Nieistotne, Inne) z liczbą fraz w każdym segmencie. Klikam kartę → filtruje tabelę. Pod kartami: czerwony banner "Zmarnowany budżet: X zł" ze statusem wykluczeń. Poniżej tabela z kolumnami: checkbox, Segment, Fraza, Kampania, Kliknięcia, Koszt, Konwersje, CVR, Powód, Akcje.

Bardzo czytelne i dobrze zorganizowane. Segmentacja fraz to coś czego w GAds nie dostanę bez ręcznej pracy.

## Co moge zrobic

- **Przełączać widoki** — Segmenty (domyślny), Lista (flat z paginacją), Trendy (rosnące/spadające/nowe), Warianty (close variant analysis)
- **Filtrować po segmencie** — klikam kartę Top Performerzy/Strata/Nieistotne/Inne
- **Zaznaczać frazy bulk** — checkbox per wiersz + "zaznacz wszystkie", sticky bulk action bar
- **Bulk dodać negatywy** — "Dodaj jako negatywy (EXACT)" dla zaznaczonych
- **Eksport CSV/XLSX** — przyciski w headerze
- **Szukać frazy** — input w trybie Lista
- **Sortować** — w trybie Lista po Fraza/Kliknięcia/Wyświetlenia/Koszt/Konwersje/CTR
- **Paginacja** — w trybie Lista, 50 per strona
- **Inline akcje** — "Dodaj słowo" na Top Performerach, "Wyklucz" na Strata/Nieistotne
- **Trendy** — widzę rosnące frazy, spadające frazy, nowe frazy w osobnych tabelach
- **Warianty** — analiza close variants z kosztami

## Co mam WIECEJ niz w Google Ads UI

1. **Automatyczna segmentacja** — GAds pokazuje flat listę. Tu mam Top Performerzy / Strata / Nieistotne / Inne z 1 kliknięciem. To jest game-changer. Rano otwieram, patrzę na Stratę — 15 fraz za 200 zł. Klik-klik wyklucz.
2. **Bulk negatywy jednym klikiem** — zaznaczam 10 fraz strata, klikam "Dodaj jako negatywy" — zrobione. W GAds muszę iść do Negative keywords, dodawać ręcznie jedną po drugiej.
3. **Waste callout** — duży czerwony banner "Zmarnowany budżet: X zł" + info ile fraz jest już wykluczone, ile nie. W GAds nie ma czegoś takiego.
4. **Close variant analysis** — widzę ile kosztują bliskie warianty vs exact matches. W GAds to wymaga ręcznej analizy w arkuszu.
5. **Trend frazy** — rosnące/spadające/nowe frazy z porównaniem okresów. W GAds mogę najwyżej dodać kolumnę "change" ale nie tak przejrzyście.
6. **Eksport CSV/XLSX** — jednym klikiem. W GAds też jest ale tu jest wygodniejszy bo mam już segmentację.

## Czego MI BRAKUJE vs Google Ads UI

1. **Filtr po kampanii w widoku Segmenty** — mogę filtrować globalnie (FilterContext) ale w widoku Segmenty nie mam szybkiego filtra po konkretnej kampanii. Kolumna "Kampania" jest, ale nie klikalna do filtrowania. W GAds to jest podstawa.
2. **Match type kolumna** — w GAds widzę czy fraza była dopasowana jako EXACT, PHRASE czy BROAD. W widoku Lista nie ma tej kolumny (jest w Wariantach, ale nie w głównej tabeli).
3. **Brak sortowania w widoku Segmenty** — w trybie Lista mogę sortować, ale w Segmenty (domyślny widok) nagłówki nie są sortowalne. Chcę posortować WASTE po koszcie.
4. **Inline "Wyklucz" mówi "przejdź do Rekomendacje"** — klikam "Wyklucz" na frazie i dostaję toast "przejdź do Rekomendacje, aby wykluczyć". A myślałem że wykluczy od razu. Bulk action DZIAŁA, ale inline nie.

## Co mnie irytuje / myli

1. **Niespójność inline vs bulk** — Bulk "Dodaj jako negatywy" działa natychmiast (API call). Inline "Wyklucz" wyświetla toast "przejdź do Rekomendacje". Dlaczego jedna ścieżka działa a druga nie?
2. **"Dodaj jako słowa kluczowe" button** — bulk akcja "Dodaj jako słowa kluczowe" wyświetla toast o wyborze grupy reklam ale nic nie robi. Przycisk jest, funkcjonalność nie.
3. **Widok Segmenty nie ma paginacji** — jak mam 500 fraz w segmencie WASTE, widzę je WSZYSTKIE? To może być wolne.

## Co bym chcial

1. **Inline wyklucz od razu** — klikam "Wyklucz" na frazie → wyklucza jako EXACT w tej kampanii, bez przechodzenia nigdzie.
2. **Sortowanie w widoku Segmenty** — klikalne nagłówki jak w widoku Lista.
3. **Filtr po kampanii w segmentach** — dropdown z listą kampanii albo klikalna kolumna kampania.
4. **Match type w tabeli Lista** — kolumna "Dopasowanie" obok frazy.

## Verdykt

Zakładka search terms to jeden z najsilniejszych elementów tej aplikacji. Segmentacja + bulk negatywy + waste callout + trend analysis + close variants — to jest komplet. W GAds spędzam 30 minut na ręcznej analizie, tu mam to w 5 minut. Niespójność inline vs bulk akcji to irytujące ale nie blokujące. Brak sortowania w domyślnym widoku Segmenty to drobny feler. Ogólnie: wchodzę tu codziennie.

**Ocena: 8.5/10**

---

## Pytania do @ads-expert

1. Inline "Wyklucz" vs bulk "Dodaj jako negatywy" — dlaczego różne zachowanie? Inline powinno działać jak bulk (API call).
2. "Dodaj jako słowa kluczowe" — to jest placeholder czy planowana funkcjonalność? Przycisk jest, toast jest, efektu brak.
3. Sortowanie w widoku Segmenty — łatwe do dodania? Ten widok jest domyślny, ludzie tu lądują.
4. Match type w tabeli Lista — dane są w bazie (z search term report), dlaczego nie wyświetlamy?
