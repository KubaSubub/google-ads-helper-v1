# Notatki usera: MCC Overview (re-test #2 po sprint 2026-04-08)

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** 4 konta (Sushi Naka Naka, Ohtime AN, Klimfix, tanie-materialy.pl)
**Data:** 2026-04-08
**Poprzedni test:** 2026-04-02, ocena 9/10

---

## Co widze po wejsciu

Otwieram aplikacje i laduje na "Wszystkie konta" — to domyslna strona startowa. Naglowek "Wszystkie konta", pod spodem "Przeglad MCC — 4 kont (2026-03-10 — 2026-04-08)". Od razu wiem zakres dat.

Na gorze 5 KPI kart: Wydatki (1 739,56), Klikniecia (948), Wyswietlenia (15 926), Konwersje (211,2), Aktywne konta (2/4). Widze od razu ze 2 konta nic nie wydaja. KPI klikniecia/wyswietlenia pojawiaja sie teraz z danymi — wczesniej byly zera. Dobrze.

**NOWE** od ostatniego testu:
- **Pilulki 7d/14d/30d/MTD** w prawym gornym rogu. 30d aktywne (niebieskie). Klikam 7d — tabela sie odswi
eza z nowymi liczbami. Super, tego brakowalo!
- **Checkboxy** przy kazdym koncie — zaznaczam 2 i pojawia sie toolbar "Zaznaczono: 2 | Synchronizuj | Odrzuc rekomendacje". Bulk actions dzialaja!
- **Kolumna IS** po ROAS — same myslniki ale naglowek jest, sortowanie tez.

Tryb kompaktowy domyslnie wlaczony. Tabela ma ~11 kolumn, czytelna bez scrolla. Dobrze — ostatnio prosilem o to.

## Co moge zrobic (pelna lista)

1. **Zmieniac okres** — pilulki 7d/14d/30d/MTD (nowe!)
2. **Zaznaczac konta** — checkboxy + select all + bulk toolbar (nowe!)
3. **Sortowac** — klikalne naglowki z kierunkiem
4. **Kliknac wiersz** — dashboard konta
5. **Kliknac "Zmiany"** — historia zmian konta
6. **Kliknac rekomendacje** — strona rekomendacji
7. **Odrzucic rek. per konto** — ikonka EyeOff
8. **Bulk odrzucenie rek.** — checkbox + toolbar (nowe!)
9. **Bulk sync** — checkbox + toolbar (nowe!)
10. **Sync nieaktualne** — przycisk globalny
11. **Otworzyc w Google Ads** — external link
12. **Compact/full mode** — toggle kolumn
13. **Listy wykluczen MCC** — zwijana sekcja

## Co mam WIECEJ niz w Google Ads UI

1. **Pacing w jednym rzucie oka** — podwojny progress bar per konto. W GAds MCC musze wchodzic w kazde konto. Tu na screenie widze "Budzet 6%, Miesiac 8/30d" — od razu wiem kto underspenduje.
2. **Zewnetrzne zmiany** — "5 zewn." na zolto. W GAds nie mam crossowego widoku kto grzebal.
3. **Rekomendacje Google crossowo** — "Brak" lub "X rek." per konto + bulk dismiss.
4. **KPI aggregowane** — sumaryczne metryki na gorze. W GAds MCC mam "Account Performance" ale trzeba konfigurowacc.
5. **Period pills** — 7/14/30/MTD jednym kliknieciem (nowe!). W GAds MCC date picker wymaga kilku klikniec.
6. **New access detection** — zolta ikonka UserPlus. GAds tego nie ma.
7. **Billing status** — ikona karty + tooltip na hover. Nie musze wchodzic w Billing per konto.
8. **Listy wykluczen MCC** — shared NKL w jednym widoku.
9. **Bulk actions** — zaznacz 3 konta, syncuj albo odrzuc rek. jednym guzikiem (nowe!).

## Czego MI BRAKUJE vs Google Ads UI

1. **Optimization Score** — w GAds MCC widze OptScore per konto. Tu brak. IS to nie to samo.
2. **Filtr "tylko aktywne"** — 2 z 4 kont maja 0 wydatkow. Chcialbym je ukryc jednym kliknieciem.
3. **Budget jako liczba** — widze pacing bar ale nie widze "budzet: 5000 PLN/mies". Musze przeliczac z %. Dodajcie tooltip na pacing z budzetem.
4. **Waluta** — 1729.19 czego? Brak oznaczenia PLN/USD/EUR. Jak mam konta w roznych walutach, to jest problem.
5. **Sparkline trendu** — strzalka +23.6% to ok, ale ksztalt krzywej dałby wiecej informacji.
6. **Porownanie okresow** — chce widziec "30d vs prev 30d" obok siebie, nie tylko % zmiany spend.

## Co mnie irytuje / myli

1. **IS kolumna — same myslniki** — pusta kolumna zajmuje miejsce. Albo seed nie ma IS, albo sync nie ciagnie IS. Tak czy siak, wyglada to na buga dla usera. Sugestia: ukryc kolumne gdy 0% kont ma dane.
2. **ROAS 0% przy Ohtime** — konto ma 10.37 spend, 0 konwersji. CPA poprawnie pokazuje "—", ale ROAS pokazuje "0%" (na zolto). To niespojne — powinno byc "—" tak jak CPA, bo nie ma z czego liczyc ROAS.
3. **Compact toggle bez tooltipa** — ikona kolumn nie mowi jakie kolumny ukrywa. Tooltip "Pokaż: Kliknięcia, Wyśw., CTR, CPC, CVR, Wart. konw." bylby przydatny.
4. **"Rekomendacje Google: Brak"** — tekst zamiast liczby. Drobnostka, ale "0" byloby czytelniejsze.

## Co bym chcial (wishlist)

1. **Export CSV** — tabele do arkusza raz w tygodniu dla klienta
2. **Alert summary** — "3 konta z alertami, 2 HIGH" na gorze
3. **Quick sync per wiersz** — bez zaznaczania checkboxa
4. **Notatki per konto** — "czeka na landing page"
5. **Campaign type breakdown** — "3x Search, 2x PMax, 1x Shopping"

## Verdykt

Wszystko co prosilem w poprzednim tescie (okres, compact domyslny, bulk actions) zostalo zrobione. Strona jest teraz pelna narzedzi — pills, checkboxy, bulk sync, bulk dismiss. Jako codzienny widok poranny: otwieram, szybki scan, klikam 7d zeby zobaczyc co sie dzialo w tym tygodniu, sortuje po ROAS, widze kto ma zmiany zewnetrzne, zaznaczam 2 konta i syncuje.

Minusy: IS pusta kolumna, brak OptScore, ROAS 0% zamiast "—", brak waluty. Ale to drobnostki vs wartosc jaka daje.

**Ocena: 8.5/10** (w dol z 9 bo IS kolumna pusta + ROAS 0% niespojne)

---

## Pytania do @ads-expert

1. IS kolumna pusta — czy MetricDaily ma dane search_impression_share w seeded DB? Jesli nie, moze ukryc kolumne automatycznie gdy brak danych?
2. ROAS 0% przy 0 konwersji — nie powinno byc "—"? CPA poprawnie zwraca None, ROAS tez powinien.
3. Czy jest plan na Optimization Score per konto? W GAds MCC to kluczowa metryka i brak jej tu jest odczuwalny.
4. Waluta — czy konta moga byc w roznych walutach? Jesli tak, trzeba dodac walute do tabeli.
5. Pacing — czy mozna dodac tooltip z kwota budzetu i wydanej kwoty? Teraz widze tylko %.
