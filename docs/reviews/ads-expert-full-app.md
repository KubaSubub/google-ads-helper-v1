# Ocena eksperta Google Ads — Pełna aplikacja
> Data: 2026-03-28 | Srednia ocena: 7.8/10 | Werdykt: ZMODYFIKOWAC

## TL;DR
Aplikacja dostarcza solidny read-only audit workbench z unikalnym Command Center (bento grid) i globalnym filtrem kampanijnym. Pokrywa ~70% playbooka (daily checks + weekly reviews). Brakuje write operations i spójności filtracji — podwójny filtr (sidebar pills + GlobalFilterBar) to krytyczny UX problem do naprawy.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 9/10 | Pokrywa wszystkie daily checks z playbooka. Command Center to unikalna wartość — żadne narzędzie GAds tego nie ma. Codzienne użycie. |
| Kompletność | 7/10 | 35 sekcji analitycznych, 134 endpointy, 38 tabel DB. Brak write operations (pause/enable/bid change). Poranny przegląd z zerami w KPI. |
| Wartość dodana vs GAds UI | 8/10 | Bento grid, Health Score, Wasted Spend karta, globalny filtr kampanijny, cross-campaign Trend Explorer — to wszystko nie istnieje w GAds UI. |
| Priorytet MVP | 8/10 | Jako audit-only tool jest gotowy do użycia. Specjalista użyłby go w pierwszym dniu — Command Center + Poranny przegląd to killer combo. |
| **ŚREDNIA** | **7.8/10** | |

## Co robi dobrze

1. **Command Center (bento grid)** — 35 sekcji audytu w jednym ekranie z kolorowymi statusami. Priorytetyzacja wizualna (czerwony > żółty > zielony > niebieski). Alert bar na górze. To jest wartość #1 aplikacji — żaden konkurent tego nie ma.

2. **Globalny filtr kampanijny w sidebarze** — pills Search/PMax/Shopping/Display/Video filtrują zarówno nawigację sidebar JAK I karty w Command Center. Kliknięcie "Display" ukrywa irrelevantne zakładki (Słowa kluczowe, Prognoza, QS). W GAds nie ma takiego globalnego filtra.

3. **Pulpit z Health Score** — jeden numerek 50/100 agregujący zdrowie konta + top 3 problemy. W GAds musisz sam to oceniać subiektywnie. Quality Score summary (6.7/10) od razu widoczne.

4. **Poranny przegląd** — gotowy workflow: alerty z priorytetem HIGH, rekomendacje z konkretnymi keywords, frazy do przejrzenia. Playbook: "Daily Checks 15-30 min" — ta zakładka to realizuje.

5. **Keywords z QS audit i badgami** — tabela z match type badges (EXACT/PHRASE/BROAD), etykiety "Mało zapytań"/"Rzadko", 5 tabów (Słowa/Wykluczenia/Listy/Ekspansja/Audyt QS), eksport CSV/XLSX. Lepsze niż GAds bo ma QS subkomponenty w jednym widoku.

6. **Kampanie z rolami** — automatyczna klasyfikacja Brand/Generic z confidence score. Campaign detail z szybkimi linkami do Słów kluczowych i Wyszukiwanych fraz. W GAds nie ma auto-klasyfikacji.

7. **Trend Explorer** — wielometryczny wykres z korelacją (np. Koszt + Kliknięcia, Kor. +0.82). W GAds muszę ściągać dane do Sheets i budować wykres ręcznie.

## Co brakuje (krytyczne)

1. **Podwójna filtracja — CONFLICT** — sidebar pills (Typ kampanii) + GlobalFilterBar dropdown (Typ kampanii) robią TO SAMO. Oba ustawiają `filters.campaignType` w FilterContext. Ale user nie wie który jest "prawdziwy". Ktoś może kliknąć "Search" w sidebar a potem wybrać "Display" w dropdown — co się stanie? Musi być JEDEN source of truth.
   - Playbook ref: nie dotyczy, to UX problem
   - Rekomendacja: **Usunąć dropdown "Typ kampanii" z GlobalFilterBar** — pills w sidebarze wystarczą i są czytelniejsze. Dropdown zostawić tylko dla Status i Nazwa kampanii.

2. **Brak write operations** — specjalista widzi problem ale nie może go naprawić z poziomu apki. Nie może: spausować keyword, zmienić bid, zmienić budżet, dodać negative (poza jednym addNegativeKeyword w SearchTerms), wyklucz placement (jest, ale tylko w starej wersji drilldown).
   - Playbook ref: "Decision Rules" — pause keyword when CPA > 3x target
   - Rekomendacja: Dodać przyciski akcji na kartach Command Center: "Pauzuj" na low-perf keywords, "Zmień bid" na bid modifier, "Apply" na Google Recommendations

3. **Poranny przegląd — KPI z zerami** — "WYDATKI 0 zł, KLIKNIĘCIA 0, KONWERSJE 0" z "100% spadek". Seed data nie pokrywa ostatnich 3 dni — ale user tego nie wie. Powinien być komunikat "Dane dostępne od-do" lub "Brak danych za ostatnie 3 dni".
   - Rekomendacja: Dodać empty state z informacją o zakresie danych, lub zmienić domyślny okres na 7 dni zamiast 3

4. **Brak Impression Share w tabeli kampanii** — IS to jedna z top 3 metryk w GAds. Jest w Auction Insights ale nie w głównej tabeli kampanii.
   - Playbook ref: "Advanced Metrics: Search Lost IS (Budget), Search Lost IS (Rank)"
   - Rekomendacja: Dodać kolumny IS, Lost IS (budget), Lost IS (rank) do tabeli kampanii

## Co brakuje (nice to have)

1. **Period comparison** — "vs poprzedni okres" jest na Pulpicie (jako % change) ale nie w Command Center. Karty bento mogłyby pokazywać trendy (strzałka up/down).

2. **Bulk actions** — zaznacz 5 keywords → Pauzuj wszystkie. W GAds to standard.

3. **Klawiszowe skróty** — power userzy chcą 1-9 do nawigacji po kartach, Enter do drill-down, Esc do powrotu.

4. **Eksport PDF** raportu Command Center — "raport z audytu z dnia X" jednym kliknięciem.

5. **Pinning kart** — użytkownik przypina 5 najważniejszych na górę grida.

## Co usunąć/zmienić

1. **Dropdown "Typ kampanii" z GlobalFilterBar** — zdublowany z pills w sidebarze. Powoduje confusion. USUNĄĆ.

2. **Nazwa "Optymalizacja kampanii"** — zbyt ogólna. Lepsze: "Centrum audytu" lub "Command Center" (jak w prototypach Pencil). Specjalista GAds szuka "audyt", nie "optymalizacja".

3. **Sekcja "Filtry kampanii" card na górze stron** — po dodaniu pills do sidebara, ten card jest redundantny na stronach gdzie filtr kampanijny jest w sidebarze. Zostaw go tylko tam gdzie jest potrzebny (Kampanie, Keywords — bo tam jest też filtr po Status i Nazwa).

## Porównanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Overview konta | Karty KPI, wykres | Pulpit z Health Score + bento grid | **LEPSZE** |
| Filtr po typie kampanii | Ręczny filtr per widok | Global pills w sidebar | **LEPSZE** |
| Campaign management | Pełne CRUD + bid editing | Read-only tabela + rola | **GORSZE** |
| Keyword management | Pełne CRUD + match type edit | Read-only + QS audit | **GORSZE** (dane), **LEPSZE** (analiza) |
| Search terms review | Tabela + add negative | Tabela + negative + N-gramy | **LEPSZE** |
| Recommendations | Lista + Apply button | Poranny przegląd + priorytet | **LEPSZE** (priorytetyzacja), **GORSZE** (brak Apply) |
| Quality Score | Kolumna w tabeli keywords | Dedykowana strona + subkomponenty | **LEPSZE** |
| Auction Insights | Osobny raport | Karta w Command Center | **LEPSZE** (zintegrowane) |
| Budget management | Edycja inline | Brak | **GORSZE** |
| Wasted Spend | Brak (ręczne kalkulacje) | Dedykowana karta z kwotą | **LEPSZE** |
| Daily audit workflow | Brak | Poranny przegląd + Command Center | **LEPSZE** |
| Multi-campaign type view | Brak | Global pills + adaptive sidebar | **LEPSZE** |

Score: 7 LEPSZE, 3 GORSZE, 2 mieszane = **netto +4 na korzyść aplikacji** jako audit tool.

## Nawigacja i kontekst

- **Skąd user trafia**: Login → Pulpit (default). Sidebar → dowolna strona.
- **Dokąd powinien móc przejść**: Z karty Command Center → drill-down szczegółowy → akcja (brak!)
- **Brakujące połączenia**:
  1. Z Pulpitu "Wasted Spend 287 zł" → klik → powinien otwierać kartę "Zmarnowany budżet" w Command Center (teraz nie ma linku)
  2. Z Poranniego przeglądu "Obniż stawkę" → klik na keyword → powinien otwierać Keywords z filtrem na to keyword
  3. Z Command Center drill-down → nie ma przycisku "Wykonaj akcję" → specjalista musi iść do GAds

## Rekomendacja końcowa

**ZMODYFIKOWAC** — aplikacja jako audit tool jest 8/10. Trzy krytyczne zmiany podniosą ją do 9/10:

1. **Usunąć podwójną filtrację** (pills w sidebar = jedyny filtr typu kampanii, dropdown usunąć)
2. **Naprawić Poranny przegląd** (zera w KPI — seed data lub fallback na 7 dni)
3. **Dodać minimum 3 write actions**: pause keyword, apply recommendation, exclude placement — z poziomu Command Center drill-down

Command Center z bento grid jest unikalny na rynku i sam w sobie uzasadnia istnienie aplikacji. Globalny filtr kampanijny to second killer feature. Teraz trzeba domknąć pętlę: audit → insight → **action**.
