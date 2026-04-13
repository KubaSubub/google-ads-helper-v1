# Notatki usera: Pełna aplikacja Google Ads Helper

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** seed data / client Demo Meble Sp. z o.o.
**Data:** 2026-03-28

---

## Co widzę po wejściu

Ciemny interfejs, ładnie zrobiony. Sidebar po lewej z menu, na górze wybór klienta (Demo Meble), pod nim **pills filtrów po typie kampanii** (Wszystkie/Search/PMax/Shopping/Display/Video). To nowość — nie widziałem tego wcześniej w żadnym narzędziu do Google Ads.

**Pulpit**: Health Score 50 (żółty gauge), KPI karty: 20 553 kliknięć, 41 431 zł koszt, 899 konwersji, ROAS 3.68x. Pod spodem CTR 5.71%, CPA 46 zł, Wasted Spend 287 zł. Jest Quality Score summary (6.7/10) i Trend Explorer z wykresem. Solidne podsumowanie.

**Optymalizacja kampanii (Command Center)**: WOW. Zamiast 26 sekcji do scrollowania mam **bento grid z kartami**. Każda karta = jeden obszar: "Zmarnowany budżet 287 zł", "Strategia bidowania 4 zmian", "Zdrowie konwersji 97/100". Kolorowe kropki i obramowania: czerwone = problem, żółte = uwaga, zielone = OK. Na górze alert bar: "3 problemy wymagają uwagi". Klikam kartę — drill-down do szczegółów.

**Filtr Display**: Sidebar ukrywa zakładki Słowa kluczowe, Wyszukiwane frazy, Prognoza, Inteligencja, Wynik jakości. Grid optymalizacji: 8 sekcji zamiast 35. Widać Placements, Tematy, Odbiorców, Rekomendacje Google. Inteligentne.

---

## Co mogę zrobić

- **Sidebar**: Wybrać klienta (dropdown), zmienić typ kampanii (pills), nawigować po zakładkach
- **Pulpit**: Przegląd KPI, Health Score, Quality Score, Trend Explorer (wielometryczny)
- **Poranny przegląd**: Alerty (6 wymaga uwagi), rekomendacje z priorytetem (HIGH), szybkie frazy do przejrzenia
- **Kampanie**: Lista 9 kampanii, klik → detail z rolą kampanii (Brand/Generic), KPI per kampania
- **Słowa kluczowe**: Tabela 28 keywords z match type, badgami "Rzadko"/"Mało zapytań", QS audit, eksport CSV/XLSX
- **Optymalizacja**: 35 kart bento grid, filtr po typie, drill-down do każdej sekcji, alert bar
- **Filtr globalny**: Pills w sidebar filtrują zarówno menu JAK I karty optymalizacji

---

## Co mam WIĘCEJ niż w Google Ads UI

1. **Command Center z bento grid** — widzę w 1 ekranie status 35 obszarów audytu. W GAds muszę klikać po 8 różnych zakładkach i jeszcze potem robić kalkulacje w arkuszu
2. **Globalny filtr po typie kampanii** — w GAds nie ma czegoś takiego. Klikam "Display" i cały interfejs się dostosowuje. W GAds muszę ręcznie filtrować w każdym widoku osobno
3. **Alert bar z priorytetami** — "3 problemy wymagają uwagi" od razu na górze. W GAds rekomendacje są w osobnym tabie i nie mają takiej priorytetyzacji
4. **Health Score** na pulpicie — jeden numerek 50/100 + najważniejsze problemy. W GAds muszę sam oceniać zdrowie konta
5. **Wasted Spend** jako karta — od razu widzę ile zł wyrzucam na śmieciowe keywords
6. **Trend Explorer** wielometryczny — Koszt + Kliknięcia na jednym wykresie z korelacją. W GAds muszę ściągać dane do Sheets
7. **Poranny przegląd** z checklistą — gotowy workflow dzienny, w GAds nie ma takiego widoku

---

## Czego MI BRAKUJE vs Google Ads UI

1. **Brak segmentacji po sieci** (Search vs Search Partners) — w GAds to jest podstawa
2. **Brak view-through conversions** — karty pokazują konwersje ale nie rozróżniają typu
3. **Brak kolumny Impression Share w tabeli kampanii** — IS to krytyczna metryka, a widzę ją tylko w Auction Insights
4. **Brak edycji budżetu/stawek** z poziomu tabeli kampanii — mogę tylko patrzeć, nie mogę zmieniać
5. **Brak filtra po labelu kampanii** — w GAds labelki to moje główne narzędzie organizacyjne
6. **Brak kolumny "Zmiana % vs poprzedni okres"** w tabeli keywords — same wartości absolutne
7. **Poranny przegląd** — dane KPI pokazują "0 zł" i "100% spadek" — wygląda jakby seed data nie pokrywał tego widoku prawidłowo

---

## Co mnie irytuje / myli

1. **Podwójna filtracja kampanijne**: W sidebarze mam pills (Search/PMax...) ALE na górze strony jest też panel "Filtry kampanii" z dropdownami. To zdublowana filtracja — pills w sidebar filtrują globalnie, dropdown na górze filtruję stare pole. Czy one się nawzajem nadpisują? Matka boska, muszę to sprawdzić żeby nie dostać złych danych
2. **"Jakość konwersji 5/100"** — czerwona karta. Ale po kliknięciu nie wiem CO jest nie tak. Score 5/100 brzmi jak katastrofa ale może to seed data?
3. **Poranny przegląd** — "WYDATKI 0 zł, KLIKNIĘCIA 0, KONWERSJE 0" z "100% spadek" — to jest straszne na pierwszy rzut oka ale prawdopodobnie seed data nie ma danych z ostatnich 3 dni
4. **"Optymalizacja kampanii"** jako nazwa — specjalista GAds myśli tu "optymalizacja CZEGO?". Poprzednia nazwa "Optymalizacja SEARCH" była jaśniejsza. Może "Centrum audytu" albo "Audit Center"?
5. **Brak tooltipów** na kartach bento — "2 kryt." przy Smart Bidding — krytycznych co? Brak kontekstu

---

## Co bym chciał

1. **Tryb porównawczy** — klikam 2 karty i widzę porównanie metryki side-by-side (ten okres vs poprzedni)
2. **Pinning kart** — żebym mógł przypiąć 5 najważniejszych kart na górę grida
3. **Custom dashboard builder** — przeciągam karty, buduję swój widok pod konkretne konto
4. **Eksport PDF** raportu bento grid — "tu jest screen konta z 28 marca, oto problemy"
5. **Powiadomienie push** gdy karta zmieni kolor z zielonego na czerwony
6. **Klawiszowe skróty** — wcisnąłbym 1-9 żeby szybko przejść do karty

---

## Verdykt

**8/10 — to jest serio użyteczne.** Command Center z bento grid rozwiązuje mój #1 problem: "co sprawdzić jako pierwsze?". Globalny filtr po typie kampanii to game changer — w GAds nie ma nic takiego. Brakuje write operations (edycja budżetów/stawek z UI) i poranny przegląd ma dziwne zera, ale jako narzędzie do szybkiego audytu — wchodzę tu codziennie rano zamiast otwierać GAds na start.

---

## Pytania do @ads-expert

1. Podwójna filtracja (pills w sidebar + dropdown "Filtry kampanii" na górze) — czy one się nadpisują? Który jest source of truth?
2. "Jakość konwersji 5/100" — czemu tak nisko? Czy to seed data problem czy prawdziwy scoring?
3. Poranny przegląd z zerami (0 zł, 0 kliknięć, "100% spadek") — seed data nie pokrywa ostatnich 3 dni?
4. Czy da się dodać Impression Share jako kolumnę w tabeli kampanii?
5. Bento grid — jakie są plany na write actions? Np. "Pauza keyword" z karty "Low-perf keywords"?
6. Czy planujecie klawiszowe skróty do nawigacji po kartach?
