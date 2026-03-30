# Notatki Marka — zakładka KEYWORDS (Słowa kluczowe)

**Data:** 2026-03-29
**Persona:** Marek, specjalista Google Ads, 6 lat doświadczenia, 8 kont
**Źródło:** screenshot `keywords.png` + kod `features/keywords/`

---

## Co widzę

Zakładka podzielona na **4 taby** (pill buttons u góry):
1. **Słowa kluczowe** — główna tabela positive keywords
2. **Wykluczenia** — lista negative keywords z filtrowaniem po scope (kampania/grupa reklam) i match type
3. **Listy** — zarządzanie shared negative keyword lists (tworzenie, dodawanie słów, stosowanie do kampanii)
4. **Ekspansja** — sugestie nowych keywordów z search terms (niezmapowane frazy z priorytetem)

Plus przycisk **Audyt QS** (fioletowy) — link do osobnej strony Quality Score.

### Tab "Słowa kluczowe" (domyślny widok na screenshocie)
- Filtry kampanii u góry: STATUS dropdown + pole szukaj po nazwie kampanii
- Filtrowanie po match type: ALL / EXACT / PHRASE / BROAD (pill buttons)
- Checkbox "Pokaż usunięte"
- Eksport: CSV / XLSX
- Sortowanie po: kliknięcia, wyświetlenia, koszt, konwersje, CTR, Avg CPC (klikalne nagłówki)
- Kolumny w tabeli: Słowo kluczowe, Kampania (+ grupa reklam pod spodem), Dopasowanie, Kliknięcia, Wyświetlenia, Koszt, Konwersje, CTR, Avg CPC, QS, Status, ROAS, IS %, Akcje
- Serving status badges (złote/czerwone): "Mało zapytań", "Bid za niski", "Rzadko"
- Akcje kontekstowe per keyword: "Pauzuj" (koszt>50zł, 0 konwersji), "Podnieś" (CVR>5%), "Obniż" (CPA>50zł)
- Paginacja: 50 per strona
- Tooltips na metrykach (CTR, CPC, QS, ROAS, IS)

### Tab "Wykluczenia"
- Filtrowanie: zakres (Kampania/Grupa reklam), match type, szukaj tekst, checkbox "Usunięte"
- Kolumny: Fraza, Dopasowanie, Zakres, Kampania, Grupa reklam, Status, Źródło (Ręczne/Google Ads), Dodano, Akcje
- Przycisk "Dodaj wykluczenie" — modal z bulk input (wiele fraz na raz), wybór match type, scope, kampania, grupa reklam
- Usuwanie single negative

### Tab "Listy"
- Lista shared negative keyword lists z item count
- Badge "Google Ads" przy zsyncowanych listach (read-only)
- Expandable — kliknięcie rozwija listę słów
- Akcje: dodaj słowa (modal z textarea + match type), usuń listę, **zastosuj do kampanii** (modal z checkboxami kampanii)
- Tworzenie nowej listy: nazwa + opis

### Tab "Ekspansja"
- Summary KPI: niezmapowane frazy, sugestie, wysoki priorytet, obecne słowa
- Tabela sugestii: Fraza, Kliknięcia, Wyświetlenia, CTR, Koszt, Konwersje, CPA, Priorytet (score), Sugerowany typ dopasowania

---

## Co mogę zrobić

1. Przeglądać wszystkie keywords z metrykami performance (kliknięcia, koszt, konwersje, CTR, CPC, ROAS, IS%)
2. Filtrować po: match type, status kampanii, typ kampanii (sidebar), zakres dat (sidebar 30 dni)
3. Sortować po kluczowych metrykach
4. Zobaczyć Quality Score per keyword
5. Zobaczyć serving status (problemy emisji) — czytelne badge'e
6. Dostać rekomendacje akcji per keyword (pauzuj / podnieś / obniż bid) — na podstawie prostych reguł
7. Eksportować do CSV/XLSX
8. Zarządzać negative keywords — dodawać bulk, usuwać, filtrować po scope
9. Zarządzać shared negative keyword lists — tworzyć, dodawać słowa, stosować do kampanii
10. Widzieć sugestie ekspansji keywordów z search terms — z priorytetem i sugerowanym match type
11. Przejść do Audyt QS jednym klikiem

---

## Więcej niż Google Ads UI

- **Akcje kontekstowe per keyword** — Google Ads UI nie podpowiada "pauzuj bo koszt>50zł i 0 konwersji" wprost w tabeli keywords. Tu mam to od razu przy każdym wierszu.
- **Ekspansja keywordów z priorytetem** — w Google Ads muszę sam wyciągać search terms, porównywać z keywordami, liczyć CPA. Tu jest gotowy priorytet i sugerowany match type.
- **Shared negative lists z apply do kampanii** — w Google Ads mogę to zrobić, ale tu workflow jest prostszy (checkbox + apply).
- **Serving status jako badge** — w Google Ads muszę dodać kolumnę ręcznie i szukać filtra. Tu widać od razu.
- **ROAS i IS% w jednej tabeli** — w Google Ads muszę sam dodawać kolumny do widoku. Tu są domyślnie.

---

## Brakuje vs Google Ads

1. **Bid management** — nie widzę aktualnej stawki (CPC max bid) per keyword, ani możliwości jej edycji inline. W Google Ads mogę kliknąć i zmienić bid. Tu przycisk "Podnieś"/"Obniż" odsyła do Rekomendacji zamiast pozwalać na inline edit.
2. **Filtr po ad group** — mogę filtrować po kampanii (przez URL param), ale nie widzę filtra po grupie reklam. W Google Ads to standard.
3. **Bulk operations** — nie ma checkboxów do zaznaczania wielu keywordów i masowej akcji (pauzuj, włącz, zmień bid). Google Ads to umożliwia.
4. **Search terms per keyword** — w Google Ads mogę kliknąć keyword i zobaczyć, jakie search terms go triggerowały. Tu takiego drill-down nie ma.
5. **Kolumna Conversion Value / Conv. Value / Cost** — widzę ROAS, ale nie widzę raw conversion value. Przydatne do oceny wartości keywordów.
6. **Trend/zmiana vs poprzedni okres** — nie widzę sparklines czy delta% (np. CTR wzrósł o 12% vs poprzednie 30 dni). Dashboard ma TrendExplorer, keywords nie.
7. **Labels / Etykiety** — w Google Ads mogę tagować keywords etykietami. Tu tego nie ma.
8. **Auction Insights per keyword** — w Google Ads mogę zobaczyć kto jeszcze licytuje na mój keyword. Tu IS% jest, ale brak pełnych auction insights.
9. **Keyword status zmiana** — nie mogę pauzować/włączać keywordu bezpośrednio z tabeli. Przycisk "Pauzuj" to tylko hint, nie akcja.
10. **Final URL per keyword** — w Google Ads widzę, na jaką stronę kieruje keyword. Tu nie ma.
11. **Impression share breakdown** — widzę IS%, ale nie widzę "Lost IS (rank)" vs "Lost IS (budget)". To krytyczne do optymalizacji.
12. **Ad group level QS** — QS jest per keyword, OK, ale nie widzę Expected CTR / Ad Relevance / Landing Page Experience jako sub-komponentów QS. (Sprawdzę czy to na stronie Audyt QS.)

---

## Irytuje

1. **Sortowanie niewidoczne** — nagłówki kolumn się podświetlają ikoną ArrowUpDown, ale nie wiem czy sortuję asc czy desc. Brak wizualnej strzałki kierunkowej.
2. **Match type filter "Wszystkie" nie podświetla się na biało** — gdy aktywne, wygląda tak samo jak inne pille, ale bez koloru match type. Drobnostka, ale niekonsekwentne.
3. **Akcje "Pauzuj"/"Podnieś"/"Obniż" nic nie robią** — wyświetlają toast "przejdź do Rekomendacje". To trochę frustrujące — spodziewam się akcji, dostaję redirect. Albo zróbcie prawdziwą akcję, albo zmieńcie na link/badge informacyjny.
4. **Brak search w tabeli positive keywords** — mogę szukać kampanię w filtrze kampanii (u góry), ale nie mam search/filter po tekście samego keywordu. Na 28 keywordach OK, na 500 — problem.
5. **Pagination info skąpa** — "Strona 1 z 1". Nie widzę ile wyników na stronie (50) ani total wyników w paginacji. Total jest nad tabelą, ale w paginacji przydałby się "28 z 28".
6. **Kolumna kampanii za szeroka** — na screenshocie kampania + ad group zajmują dużo miejsca. Przy wielu kolumnach (14!) tabela się może nie mieścić na mniejszym ekranie.

---

## Chciałbym

1. **Inline bid editing** — kliknij na bid, zmień, zapisz. Prosta edycja CPC max.
2. **Checkbox bulk actions** — zaznacz 10 keywordów, pauzuj / zmień match type / zmień bid masowo.
3. **Search po tekście keywordu** — input "Szukaj keyword..." nad tabelą lub w filtrach.
4. **Delta vs poprzedni okres** — kolumna lub ikona ze zmianą % clicks/cost/conversions vs poprzedni okres.
5. **Drill-down: keyword -> search terms** — kliknij keyword, pokaż jakie search terms go triggerowały.
6. **QS sub-komponenty** — Expected CTR / Ad Relevance / Landing Page w tooltipie lub expandable row.
7. **IS breakdown** — Lost IS (rank) + Lost IS (budget) obok IS%.
8. **Quick pause/enable** — toggle/switch per keyword bez przechodzenia do Rekomendacji.
9. **Kolumna Max CPC bid** — widoczna aktualna stawka.
10. **Conversion Value kolumna** — obok konwersji i ROAS.
11. **"Dodaj do wykluczeń" z search terms** — na tab Ekspansja brakuje akcji "Dodaj" / "Wyklucz" per sugestia.

---

## Verdykt

**7.5/10** — Bardzo solidna zakładka. Wyraźnie powyżej typowego "keyword readera". Cztery taby pokrywające positive, negative, lists i ekspansję to dobry scope. Metryki kompletne (QS, ROAS, IS%, serving status). Serving status badges i akcje kontekstowe to fajny value-add. Ekspansja z priorytetem to coś, czego nie mam out-of-the-box w Google Ads UI.

Główny minus: **brak operatywności**. Mogę patrzeć, ale nie mogę działać. Nie zmienię bidu, nie spauzuję keywordu, nie zrobię bulk action. Przyciski akcji (Pauzuj/Podnieś/Obniż) to hinty, nie akcje. To degraduje wartość — jeśli i tak muszę iść do Google Ads żeby cokolwiek zmienić, to po co tu siedzieć?

Drugie: brak filtra po tekście keywordu — podstawowa rzecz, która brakuje.

Trzecie: Ekspansja super, ale brak przycisku "Dodaj keyword" / "Wyklucz" — sugestie bez akcji to połowa wartości.

---

## Pytania @ads-expert

1. Czy reguły akcji kontekstowych (koszt>50zł, CVR>5%, CPA>50zł) są sensowne? Progi wydają mi się sztywne i zależne od branży. Może powinny być konfigurowalne?
2. Czy tab Ekspansja faktycznie analizuje search terms vs existing keywords poprawnie? Jaki algorytm priorytetyzacji?
3. Czy brak inline bid editing to świadoma decyzja (safety) czy brak feature?
4. Jak Audyt QS (osobna strona) uzupełnia tab Keywords? Czy są redundancje?
5. Czy negative keyword lists z "Zastosuj do kampanii" faktycznie tworzą wykluczenia na poziomie kampanii, czy to shared list (account level)?
6. Czy IS% to search impression share? Czy bierze pod uwagę exact match impression share?
7. Jakie dane zasilają tab Ekspansja — sync z ostatnich 30 dni? Czy min_clicks=3 to hardcoded?
