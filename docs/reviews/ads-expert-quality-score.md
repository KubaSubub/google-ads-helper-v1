# Ocena eksperta Google Ads — Wynik jakości (Quality Score)
> Data: 2026-03-26 | Średnia ocena: 7.5/10 | Werdykt: ZMODYFIKOWAĆ

## TL;DR

Zakładka Quality Score to **jeden z najlepszych audytowych widoków w aplikacji** — daje zbiorczy obraz zdrowia konta z perspektywy QS, czego Google Ads UI nie oferuje. Brakuje kluczowych elementów akcyjnych (ad group, regulowany próg, eksport) i trochę głębi w rekomendacjach, ale fundament jest solidny i pokrywa sekcje 4.3 playbooka.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 8/10 | Playbook §4.3 + §checklist (pkt 3) — QS audit to core task, monthly deep dive. Każdy specjalista to robi, tyle że ręcznie w arkuszu |
| Kompletność | 7/10 | 5 KPI, filtry, sortowanie, subkomponenty, breakdown problemów — dużo. Brakuje: ad group, regulowany threshold, eksport, historia QS |
| Wartość dodana vs Google Ads UI | 8/10 | % budżetu na niski QS, agregowany breakdown problemów, IS lost per keyword — tego nie ma w GAds bez skryptów/arkuszy |
| Priorytet MVP | 7/10 | QS audit to monthly task — nie daily driver, ale "must have" dla profesjonalnej aplikacji. Bez tego specjalista nie traktuje narzędzia poważnie |
| **ŚREDNIA** | **7.5/10** | |

## Co robi dobrze

### 1. Karta "Wydatki na niski QS" — killer feature
Playbook §checklist pkt 3: "Ile % keywords ma QS < 5?" — ta karta odpowiada na to pytanie automatycznie i dodaje wymiar finansowy (ile % budżetu idzie na słabe keywords). W Google Ads trzeba to liczyć ręcznie: eksport → filtr QS < 5 → SUMIF kosztów → % total. Tu mam od ręki.

### 2. Breakdown problemów (3 paski: CTR / Ad / LP)
Playbook §4.3 wymienia trzy subkomponenty QS z wagami (50/25/25). Wykres "Główne problemy" od razu pokazuje ile keywords ma problem z każdym subkomponentem. To mówi specjaliście: "masz systemowy problem z landing page" albo "problem jest w ad copy". W Google Ads musisz ręcznie dodać 3 kolumny subkomponentów, przefiltrować każdą i policzyć.

### 3. Subcomponent dots w tabeli (traffic light)
Trzy kolorowe kropki (czerwona/żółta/zielona) per keyword to szybki wizualny scan. W Google Ads subkomponenty to tekst ("Below average" / "Average" / "Above average") — mniej czytelny przy szybkim przeglądzie 50+ keywords.

### 4. IS lost per keyword w kontekście QS
Połączenie QS z Impression Share lost to rank w jednej tabeli to unikat. Specjalista od razu widzi: "ten keyword ma QS=4 i traci 25% IS przez ranking" — jasny sygnał że poprawa QS da więcej impressions. W Google Ads te dane są w osobnych widokach.

### 5. Filtry po kampanii, match type i głównym problemie
Filtr "pokaż mi tylko keywords z problemem landing page" nie istnieje w Google Ads UI. Tu jest jednym kliknięciem. To oszczędza czas przy systematycznym naprawianiu QS per komponent.

## Co brakuje (krytyczne)

### 1. Brak kolumny Ad Group w tabeli
- **Dlaczego:** Playbook §4.3 mówi wprost: "Utwórz SKAG", "Keyword w Headline 1" — to operacje na poziomie ad group, nie kampanii. Specjalista widzi keyword z niskim QS, ale nie wie w której ad group jest. Musi iść do Keywords → szukać.
- **Playbook ref:** §4.3 "Expected CTR Problem → Utwórz SKAG"
- **Implementacja:** Dodać `ad_group_name` do response endpointu (model AdGroup.name jest dostępny, join już jest w query). Dodać kolumnę w tabeli.

### 2. Regulowany próg QS z poziomu UI
- **Dlaczego:** Playbook wymienia QS < 5 (audit) i QS < 3 (pause). Różne konta mają różne "zdrowe" QS — e-commerce meblowy z avg QS 6 ma inne progi niż brand campaign z avg QS 9. Backend już przyjmuje `qs_threshold` jako parametr, ale frontend go nie wysyła.
- **Playbook ref:** §daily checks (QS < 3), §monthly (QS < 5), §checklist (QS < 5)
- **Implementacja:** Dodać slider lub select (3/4/5/6/7) do filter bar. Podłączyć do API param `qs_threshold`.

### 3. Eksport do CSV/PDF
- **Dlaczego:** Specjaliści raportują klientom. "Panie kliencie, 25% budżetu idzie na keywords z niskim Quality Score" to potężny argument do optymalizacji LP albo zwiększenia budżetu na testy ad copy. Bez eksportu specjalista musi robić screenshota lub kopiować ręcznie.
- **Playbook ref:** §reporting framework — raporty dla klientów
- **Implementacja:** Przycisk "Eksport CSV" w headerze. Dane są już w state `data.keywords`.

### 4. Brak filtrowania po dacie
- **Dlaczego:** Koszty w tabeli to snapshot (suma z keyword model, nie z zakresu dat). Specjalista chce wiedzieć: "w ostatnim miesiącu ile wydałem na niski QS?" a nie "od początku świata". Inne zakładki (Dashboard, Keywords) mają date range picker.
- **Implementacja:** Podłączyć do globalnego filtra dat z FilterContext. Backend musiałby agregować koszty z KeywordDaily zamiast snapshot.

## Co brakuje (nice to have)

### 1. Trend QS w czasie
- Wykres liniowy: średni QS per tydzień/miesiąc. Odpowiada na pytanie: "czy moje optymalizacje działają? QS rośnie czy spada?"
- **Ograniczenie:** KeywordDaily nie trackuje QS per dzień, tylko metryki performance. Wymagałoby dodania `quality_score` do modelu KeywordDaily lub osobnej tabeli snapshotów QS.

### 2. Grupowanie po ad group
- Zamiast płaskiej listy: "Ad Group X — avg QS 4.2 (5 keywords)", "Ad Group Y — avg QS 8.1 (3 keywords)". Od razu widać które ad groups wymagają pracy.

### 3. Rekomendacje kontekstowe (nie generyczne)
- Obecne: "Popraw nagłówki reklam — dodaj słowo kluczowe + CTA" (identyczne dla każdego keyword z problemem CTR).
- Lepiej: "CTR=14% ale Expected CTR poniżej średniej → benchmark dla tego tematu jest wyższy. Rozważ DKI lub SKAG." — uzależnione od danych keyword.
- **Playbook ref:** §4.3 — konkretne kroki per subkomponent (SKAG, DKI, LP speed < 3s)

### 4. Link do Google Ads UI per keyword
- Deep link do keyword w Google Ads: `https://ads.google.com/aw/keywords?...&keywordId=XXX`. Specjalista klika i od razu jest w edycji.

### 5. Akcje z poziomu tabeli
- "Pauza keyword" dla QS < 3 (playbook §daily: "QS < 3 AND Cost > $100 → PAUSE"). Przycisk obok wiersza.

## Co usunąć/zmienić

### 1. Kolumna "CTR / Ad / LP" — potrzebuje legendy
Trzy kropki bez opisu wymagają hovera. Dodać mini-podpisy pod kropkami albo legendę nad tabelą: "● CTR  ● Ad  ● LP". Alternatywnie: rozbić na 3 osobne kolumny z ikonkami i labelami.

### 2. Label "IS utracony (rank)" — dwuznaczny
Zmienić na "IS utracony (ranking)" z tooltipem: "Impression Share utracony z powodu niskiego rankingu reklamy (Quality Score + bid)". Odróżnia od IS lost to budget.

### 3. Koszt w tabeli bez waluty
Dodać "zł" po kwocie lub zmienić nagłówek na "Koszt (zł)". KPI karta ma "zł", tabela nie — niespójność.

### 4. Rekomendacja "OK" dla keywords z QS 7+
Kolumna rekomendacji pokazuje kursywne "OK" dla zdrowych keywords. To marnuje miejsce w wierszu. Lepiej: pusta komórka lub delikatna zielona ikona ✓.

## Porównanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| QS per keyword | Kolumna w tabeli Keywords | Badge kolorowy + tabela | IDENTYCZNE |
| Subkomponenty QS | Tooltip na QS kolumnie lub 3 osobne kolumny | 3 kolorowe kropki (traffic light) | LEPSZE (wizualnie) |
| Średni QS konta | Brak natywnie — trzeba skrypt/arkusz | KPI karta na górze | LEPSZE |
| % budżetu na niski QS | Brak — wymaga ręcznego obliczenia | KPI karta "Wydatki na niski QS" | LEPSZE (unikat) |
| Breakdown problemów (ile CTR vs Ad vs LP) | Brak — ręczne liczenie | Wykres + filtr | LEPSZE (unikat) |
| IS lost per keyword + QS | Osobne widoki/kolumny | Razem w jednej tabeli | LEPSZE |
| Filtr po subkomponencie | Brak | Dropdown "Główny problem" | LEPSZE |
| Trend QS w czasie | Brak natywnie | Brak | IDENTYCZNE (oba nie mają) |
| Regulowany próg QS | Brak (stałe filtry) | Brak w UI (jest w API) | IDENTYCZNE |
| Ad Group context | Zawsze widoczny | Brak w tabeli | GORSZE |
| Eksport raportu QS | Eksport do CSV/Sheets | Brak | GORSZE |
| Akcje (pauza, bid change) | Bulk actions w tabeli | Brak | GORSZE |
| Deep link do keyword | Natywna nawigacja | Generyczny link do /keywords | GORSZE |

**Wynik: 6× LEPSZE, 3× IDENTYCZNE, 4× GORSZE**

## Nawigacja i kontekst

- **Skąd user trafia:** Tylko z Sidebar (sekcja ANALIZA). Brak linków z Dashboard ani Keywords.
- **Dokąd powinien móc przejść:**
  - Do konkretnego keyword w zakładce Keywords (teraz idzie do generycznej strony /keywords)
  - Do ad group w Google Ads UI (deep link)
  - Do zakładki Recommendations (powiązane rekomendacje QS z Rule 8)
- **Brakujące połączenia:**
  - Dashboard powinien mieć widget "QS Health" z linkiem do /quality-score
  - Keywords powinna mieć przycisk "Audyt QS" obok tabeli
  - Recommendations Rule 8 (QS alerts) powinna linkować do /quality-score

## Rekomendacja końcowa

**ZMODYFIKOWAĆ** — Fundament jest świetny (5 KPI, filtry, subkomponenty, breakdown problemów). Trzy krytyczne braki to: (1) ad group w tabeli, (2) regulowany próg QS, (3) eksport. Po ich dodaniu zakładka będzie jednym z najsilniejszych argumentów za używaniem aplikacji zamiast ręcznej pracy w arkuszach. Priorytet: ad group + próg QS → sprint 1, eksport + date range → sprint 2.
