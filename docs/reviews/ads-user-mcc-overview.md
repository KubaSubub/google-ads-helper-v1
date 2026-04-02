# Notatki usera: MCC Overview

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** seed data + dodatkowi klienci (4 konta widoczne)
**Data:** 2026-04-02

---

## Co widzę po wejściu

Ciemna strona z nagłówkiem "Wszystkie konta". Na górze 3 karty KPI: wydatki 30d ($60,114.97), zmiany 30d (101), rekomendacje Google (9). Pod spodem tabela z 4 kontami w wierszach. W prawym górnym rogu niebieski przycisk "Synchronizuj nieaktualne".

Sidebar jest wyczyszczony — widzę tylko "Wszystkie konta" jako aktywny link. Nie ma żadnych innych zakładek, nie ma selektora klienta. Dopiero jak kliknę w wiersz, pewnie przeniesie mnie na dashboard konkretnego konta. To jest dobre — na start nie przytłacza.

Na dole strony jest zwinięta sekcja "Listy wykluczających słów kluczowych" z ikoną chevron — widać że można rozwinąć.

## Co mogę zrobić

1. **Kliknąć wiersz konta** → przejście do Dashboard tego konta (nawigacja z breadcrumbem)
2. **Synchronizuj nieaktualne** → przycisk na górze, triggeruje sync stale kont
3. **Rozwinąć sekcję NKL** → widok list wykluczeń cross-account
4. **Odczytać metryki per konto** — wydatki 30d, zmiana %, pacing, health, zmiany, rek. Google, sync status

Nie mogę: sortować tabeli, filtrować kont, eksportować, wyszukiwać konta po nazwie.

## Co mam WIĘCEJ niż w Google Ads UI

1. **Jednna strona na wszystkie konta** — w Google Ads MCC muszę wchodzić w każde konto osobno żeby zobaczyć health i pacing. Tutaj mam wszystko w jednej tabeli.
2. **Health score** — Google Ads nie ma jednego "wyniku zdrowia" konta. Muszę sam oceniać na podstawie dziesiątek metryk. Tu mam kółko z liczbą 0-100.
3. **Pacing zagregowany per konto** — w Google Ads widzę pacing per kampania. Tu widzę pacing CAŁEGO konta jednym rzutem oka.
4. **Zmiana wydatków 30d vs prev 30d** — ze strzałką i % — w GAds muszę ustawiać zakresy dat i porównywać ręcznie.
5. **Zewnętrzne zmiany** — widzę ile zmian zrobił ktoś spoza mojej agencji. W Google Ads Change History muszę to ręcznie filtrować per konto.
6. **Listy NKL cross-account** — w Google Ads shared negative lists widzę osobno per konto. Tu mam podgląd ze wszystkich kont w jednym miejscu.

## Czego MI BRAKUJE vs Google Ads UI

1. **Sortowanie tabeli** — nie mogę posortować kont po wydatkach, health, czy ilości rekomendacji. W Google Ads MCC mogę sortować tabelę kont.
2. **Kliknięcie w kolumnę "Rek. Google"** — chciałbym jednym kliknięciem zobaczyć JAKIE rekomendacje są pending, nie tylko liczbę. W Google Ads klikam w Recommendations i widzę listę.
3. **Konwersje** — nie widzę ile konwersji generuje każde konto. Wydatki bez konwersji to połowa obrazu. W Google Ads MCC widzę conversions i CPA na liście kont.
4. **ROAS / CPA per konto** — brak. To jest KLUCZOWE dla specjalisty. Wydatki to koszt, ale bez wyniku nie wiem czy konto działa dobrze.
5. **Filtrowanie** — nie mogę filtrować kont po typie (e-commerce vs lead gen), statusie, branży. Przy 8 kontach to nieistotne, ale przy 20+ będzie problem.
6. **Status płatności** — w Google Ads MCC widzę czy konto ma problem z płatnością. Tu tego nie ma.

## Co mnie irytuje / myli

1. **Kolumna "Health" bez tooltipa** — widzę kółko z liczbą (np. 68) ale nie wiem co to dokładnie oznacza. Jak jest liczone? Z czego wynika? Potrzebuję tooltipa z breakdownem.
2. **Pacing pille są żółte na prawie wszystkich kontach** — "Niedowydanie" na 3/4 kont. Czy to prawdziwy problem czy artefakt danych seed? Przy seed data specjalista nie wie czy to sygnał czy szum.
3. **"Synchronizuj nieaktualne" bez feedbacku** — po kliknięciu nie wiem co się dzieje. Ile kont synchronizuje? Ile to potrwa? Spinner na wierszu jest ok, ale brak ogólnego progress bara.
4. **Kolumna "Zmiany" — co to jest?** — "101" zmian to dużo czy mało? Brakuje kontekstu — jaki okres, jakie typy zmian. W Google Ads Change History mam filtry po typie zmiany.
5. **Brak odświeżenia po syncu** — po synchronizacji dane w tabeli nie odświeżają się automatycznie. Muszę ręcznie odświeżyć stronę?
6. **Sekcja NKL** — jest zwinięta, ale po rozwinięciu jest statyczna tabela. Nie mogę z tego poziomu dodać nowej listy ani edytować istniejącej. To jest read-only podgląd.

## Co bym chciał

1. **Mini-sparkline wydatków** w kolumnie "Wydatki 30d" — żebym widział trend, nie tylko punkt.
2. **Quick actions per wiersz** — "Synchronizuj" button na każdym wierszu (nie tylko globalny), "Pokaż rekomendacje", "Pokaż zmiany".
3. **Kolumna "Konwersje 30d"** i **"CPA"** — absolutny must-have.
4. **Porównanie kont** — możliwość zaznaczenia 2-3 kont i porównania ich metryk obok siebie.
5. **Alerty per konto** — ikona alerty przy koncie które ma aktywne alerty (anomalie, budżet, etc.).
6. **Link do Google Ads** — button "Otwórz w Google Ads" per wiersz — szybki skok do natywnego UI.

## Verdykt

**Solidny start, ale jeszcze nie zastąpi mi Google Ads MCC.** Widzę tu rzeczy których w Google Ads nie mam (health score, pacing per konto, zewnętrzne zmiany), ale brakuje mi konwersji i CPA — bez tego nie podejmę żadnych decyzji. Otwierałbym to rano jako "szybki przegląd co się dzieje", ale potem i tak muszę wejść w Google Ads żeby zobaczyć wyniki. Jak dorzucą konwersje, ROAS i sortowanie — będzie obowiązkowy poranki dashboard.

---

## Pytania do @ads-expert

1. Brak kolumny konwersji i CPA/ROAS na liście kont — czy to świadome pominięcie czy w planie? Dla mnie to showstopper.
2. Health score bez tooltipa z breakdownem — specjalista nie wie co poprawić. Czy kliknięcie w health powinno rozwijać szczegóły?
3. Pacing "Niedowydanie" na prawie wszystkich kontach — czy progi 80%/115% są odpowiednie? W praktyce 85% pacing to norma, nie problem.
4. Sekcja NKL jest read-only — czy plan zakłada możliwość tworzenia/edytowania list z poziomu MCC? To byłby game-changer.
5. Brak sortowania tabeli — to wydaje się trywialne do dodania. Planowane?
6. Zmiany "101" bez kontekstu — czy warto dodać mini breakdown (ile CREATE, ile UPDATE, ile z zewnątrz)?
