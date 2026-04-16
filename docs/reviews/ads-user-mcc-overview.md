# Notatki usera: MCC Overview

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data — 4 konta (Sushi Naka Naka, Klimfix, EcoBike, Fakro)
**Data:** 2026-04-14

---

## Co widze po wejsciu

Wchodze i od razu widze tabele z kontami posortowana po wydatkach — to dobry start. Na gorze KPI strip: laczne wydatki 9 496 zl, 14,71 klikniecia (to liczba wyglada niepowaznie, pewnie seed data), 18 485 wyswietlen, 905 konwersji, 3/4 aktywnych kont. Ponizej tabela z kolumnami: Wydatki (ze sparkline!), Konwersje, CPA, ROAS, Health score, Pacing, Platnosci, Zmiany, Sync.

Interfejs ciemny, estetyczny. Pierwsze wrazenie: profesjonalne narzedzie.

---

## Co moge zrobic

- Przelaczac okresy: 7d / 14d / 30d / MTD — przyciski w prawym gornym rogu
- Sortowac tabele po dowolnej kolumnie (Wydatki, Konwersje, CPA, ROAS, Health, Zmiany itp.)
- Kliknac w konto → przejdz od razu do dashboardu tego klienta
- Synchronizowac jedno konto (klik w badge sync)
- Synchronizowac wszystkie nieaktualne naraz (jeden przycisk)
- Synchronizowac wybrane konta przez checkbox + bulk sync
- Odkrywac nowe konta w MCC
- Wlaczyc tryb rozszerzony (przycisk Columns) — pokazuje CTR, CPC, CVR, Wartosc konwersji
- Otworzyc konto bezposrednio w Google Ads UI (ikona external link)
- Przejsc do Historii zmian konkretnego konta
- Zobaczyc historie syncow (klik w badge "Swieze/Stare/Nieaktualne")
- Rozwinac panel "Wykluczenia MCC" — listy negatywnych slow kluczowych i placementow na poziomie managera

---

## Co mam WIECEJ niz w Google Ads UI

1. **Health Score per konto** — w GAds nie ma jednej liczby. Tu jest kolo gauge z wartoscia 0-100 i kolorem (zielony/zolty/czerwony). Moge posortowac po Health i od razu widziec ktore konto wymaga uwagi.
2. **Pacing bar** — w GAds musialbym wchodzic w kazde konto osobno i liczyc recznie. Tu widze dwa paski: budzetowy (ile % budzetu wydane) i miesieczny (ktory dzien miesiaca jestesmy). Kiedy pacing jest pomaranczowy/czerwony wiem ze mam problem bez klikania.
3. **Sparkline trendu wydatkow** — mala linia trendu obok liczby wydatkow. W GAds nie ma tego w MCC view.
4. **Zmiana wydatkow % z trendem** (TrendingUp/Down ze strzalka) — od razu widze czy konto rosnie czy spada vs poprzedni okres.
5. **Status platnosci (billing) per konto** — ikona karty z kolorem. W GAds musisz wchodzic do kazdego konta zeby sprawdzic billing. Tu masz to w jednym rzedzie.
6. **Liczba zmian z podziałem** — kolumna "Zmiany" pokazuje ile zmian bylo w koncie + ile bylo "zewnetrznych" (poza aplikacja). To coś czego w standardowym MCC view Google Ads w ogóle nie ma.
7. **Wykluczenia MCC w jednym miejscu** — lista negatywnych fraz i placement exclusions na poziomie managera z mozliwoscia podgladniecia zawartosci listy. W GAds trzeba klikac do Tools & Settings > Shared Library.
8. **Posortowanie po CPA lub ROAS** — w GAds MCC overview posortowanie po CPA wymaga kilku klikniec i nie zawsze dziala jak chcesz.
9. **Selekcja wielu kont + bulk sync** — w GAds nie mozna "zsynchronizowac" kont do zewnetrznego narzedzia oczywiscie, ale koncept bulk akcji jest tu dobrze zaimplementowany.

---

## Czego MI BRAKUJE vs Google Ads UI

1. **Brak filtru po typie kont** — nie moge oddzielic kont e-commerce od lead gen, kont aktywnych od porzuconych. Chcialbym checkbox "pokaz tylko aktywne" albo dropdown Status konta.
2. **Brak kolumny Impression Share w trybie kompaktowym** — IS jest ukryte i pojawia sie tylko gdy API zwroci dane. To jedna z kluczowych metryk przy monitoringu kont Search.
3. **Brak kolumny budzetow** — ile wynosi laczny budzet dzienny/miesieczny na koncie. Mam Pacing (%) ale nie mam wartosci absolutnych widocznych bez hover.
4. **Brak szybkiego podgladu alertow** — widze ikone dzwonka gdy sa alarmy, ale zeby zobaczyc szczegoly musze najechac mysza. Nie moge kliknac w dzwonek i pojsc do listy alertow dla tego konta.
5. **ROAS w procentach zamiast mnoznika** — widze "421%" zamiast "4,21x". PPC-owiec mysi w mnoznikach, nie procentach. 400% to 4x ROAS — ta konwencja jest niestandardowa i myli.
6. **Brak kolumny "Kampanie aktywne"** — ile kampanii jest aktywnych per konto. W GAds MCC to widac od razu.
7. **Brak sortowania po stalym kryterium z pamiecią** — za kazdym razem wracam do sortowania po "Wydatki DESC". Nie pamięta mojego wyboru.
8. **Wykluczenia MCC sa tylko do odczytu** — widze listy ale nie moge dodac/usunac frazy bezposrednio z tej zakladki. Musialbym wchodzic gdzie indziej.

---

## Co mnie irytuje / myli

1. **KPI "Klikniecia: 14,71"** — liczba klikniec jako ulamek dziesiowy nie ma sensu. W seed data cos jest nie tak, ale nawet jesli to blad danych — UI powinien zaokraglac klikniecia do liczb calkowitych.
2. **Tryb kompaktowy domyslnie wlaczony** — dobrze ze jest, ale przy pierwszym wejsciu nie widze CTR ani CPC. Chcialbym moze 2 tryby: "Wydajnosc" (CPA/ROAS) vs "Traffic" (CTR/CPC).
3. **Przycisk "Odkryj konta" wyglada tak samo jak Sync** — oba sa przyciskami w tym samym stylu. "Odkryj konta" to rzadka operacja i nie powinna byc tak prominentna jak Synchronizuj.
4. **Status sync "Stare (Xh)" — co to znaczy dla mnie?** Stare 6h to jeszcze OK albo juz problem? Brakuje kontekstu co to oznacza w praktyce.
5. **Klik w wiersz = przejdz do klienta** — ok, ale nie widze cursora: pointer... a wlasciwie jest, ale nie ma zadnej animacji hover oprocz subtelnego tla. Mogloby byc wyrazniejsze ze to klikalne.
6. **Health Score — brak rozwinięcia** — widzę cyfrę na kółku, mogę posortować, ale nie mogę kliknąć i zobaczyć "co składa się na ten wynik dla tego konta".

---

## Co bym chcial

1. **Szybki tryb Daily briefing** — po wejsciu jedno kliknięcie "Pokaz co sie zepsulo od wczoraj": konta z duzym spadkiem wydatkow, konta z zerowym ruchem, konta z alertami. Nie musialbym skanowac tabeli wzrokiem.
2. **Eksport tabeli do CSV/XLSX** — chce wyslac klientowi zestawienie wszystkich kont z KPI jednym kliknieciem.
3. **Alert count przy ikonie dzwonka jako clickable badge** → otwarcie panelu alertow dla tego konta bez przechodzenia do oddzielnej zakladki.
4. **ROAS jako mnoznik (4,2x)** zamiast procent (421%).
5. **Kolumna "Aktywne kampanie"** — szybki przegld czy konto w ogole prowadzi kampanie.
6. **Zapamiętanie sortowania** — localStorage, zeby moje ustawienie przezylo odswiezenie strony.
7. **Inline edit budzetu** lub chociazby tooltip z wartoscia budzetu w Pacing bar (teraz jest budzetPCT ale wartosc absolutna tylko po hover).

---

## Verdykt

**Wchodzilbym tu codziennie jako punkt startowy zamiast Google Ads MCC.** Pacing bars, Health Score, billing status i sparklines to realna przewaga nad tym co GAds daje w MCC view. Blokuje mnie brak filtrow statusu kont oraz ROAS w procentach — te dwa elementy trzeba poprawic przed uznaniem zakladki za gotowa produkcyjnie.

---

## Pytania do @ads-expert

1. Czy Health Score (0-100) jest oparty o realne czynniki jakosci konta (QS, structure, negative coverage) czy to metryka syntetyczna z seed data?
2. Czy "Zmiany zewnetrzne" to zmiany wprowadzone bezposrednio w Google Ads UI z pominieciem tej aplikacji? Jesli tak — czy jest mozliwosc zobaczenia co dokladnie zmieniono?
3. ROAS w % vs mnoznik — jaka jest standardowa konwencja w narzędziach agencyjnych?
4. Wykluczenia MCC: czy lista fraz jest pobierana z Google Ads API w czasie synchronizacji czy przechowywana lokalnie? Jak czesto jest aktualizowana?
5. Czy Impression Share w MCC overview to average z kont czy weighted average po wydatkach?
