# Notatki usera: MCC Overview (re-test po sprintach)

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** live data, 5 kont (Demo Meble, Sushi Naka Naka, Ohtime AN, KlimFix, tanie-materialy.pl)
**Data:** 2026-04-02

---

## Co widzę po wejściu

Otwieram aplikację i od razu ląduję na "Wszystkie konta" — to jest teraz strona startowa. Pierwsze wrażenie: **dużo danych**. Na górze 5 KPI cards (Wydatki $60k, Kliknięcia 0, Wyświetlenia 0, Konwersje 1,795, Avg CTR z kreską). Pod spodem tabela z 5 kontami i MNÓSTWEM kolumn — doliczam się 17: Konto, Wydatki, Kliknięcia, Wyśw., CTR, CPC, Conv., CVR, Wart. konw., CPA, ROAS, Pacing, Health, Płatności, Zmiany, Rek., Sync + ikonki na końcu.

Widzę przycisk z ikoną kolumn obok "Synchronizuj nieaktualne" — to pewnie toggle widoku. Pod tabelą dwie rozwijane sekcje: "Listy wykluczeń MCC" i "Listy wykluczeń per konto".

Sidebar jest czysty — tylko "Wszystkie konta" jako aktywny link. Brak selektora klienta. Podoba mi się.

## Co mogę zrobić

1. **Sortować po każdej kolumnie** — klikam nagłówek, strzałka wskazuje kierunek. Działa.
2. **Kliknąć wiersz** → przechodzi do Dashboard konta z breadcrumbem "← Wszystkie konta"
3. **Odrzucić rekomendacje Google** — przy liczbie rek. jest X, kliknięcie odrzuca wszystkie. 
4. **Przełączyć tryb kompaktowy** — ikona kolumn ukrywa Kliknięcia, Wyświetlenia, CTR, CPC, CVR, Wart. konw. Zostaje 11 kolumn — dużo czytelniej!
5. **Kliknąć w "Zmiany"** → otwiera Historię zmian danego konta
6. **Kliknąć w liczbę rekomendacji** → otwiera Rekomendacje
7. **Kliknąć ikonę alertu (dzwonek)** → otwiera Monitoring
8. **Kliknąć ikonę nowego dostępu (osoba+)** → otwiera Historię (żółta ikona przy koncie z nowym emailem)
9. **Link do Google Ads** — ikona external link per wiersz
10. **Synchronizuj nieaktualne** — syncuje konta z sync > 6h
11. **Rozwinąć sekcje NKL** — listy wykluczeń MCC-level i per konto

## Co mam WIĘCEJ niż w Google Ads UI

1. **Health score z tooltipem** — najeżdżam na kółko "86" i widzę breakdown: Wyniki 92, Jakość 78, Efektywność 85, Zasięg 72, Stabilność 90, Struktura 88. W Google Ads MCC tego po prostu NIE MA.
2. **Zewnętrzne zmiany** — kolumna "Zmiany" z wyróżnieniem "X zewn." oznacza że ktoś spoza mojej agencji grzebał na koncie. W GAds muszę wchodzić w Change History per konto i ręcznie filtrować.
3. **Alert nowych dostępów** — żółta ikona UserPlus gdy pojawił się nowy email na koncie. W GAds nie mam takiego powiadomienia.
4. **Odrzucanie rekomendacji Google jednym klikiem** — w GAds muszę wchodzić per konto, otworzyć Recommendations, i odrzucać po jednej.
5. **Pacing per konto** — zagregowany status budżetowy całego konta. W GAds widzę pacing per kampania.
6. **Tryb kompaktowy** — toggle na mniej kolumn. Google Ads MCC nie ma czegoś takiego.
7. **Dwie sekcje NKL** — listy wykluczeń MCC-level i per konto w jednym widoku.

## Czego MI BRAKUJE vs Google Ads UI

1. **Kliknięcia i wyświetlenia na KPI cards pokazują "0"** — to pewnie seed data bez clicks/impressions, ale wygląda jakby coś nie działało. KPI card "Kliknięcia: 0" przy wydatkach $60k to alarm — user pomyśli że jest bug.
2. **Kolumna "Płatności" — same szare ikony** — widzę ikonę karty kredytowej przy każdym koncie ale wszystkie szare. Nie wiem czy to znaczy "OK" czy "brak informacji". Brak tooltipa widocznego na screenshocie.
3. **Brak filtra po okresie** — tabela pokazuje "30d" (bo tak jest w KPI), ale nie mogę zmienić na 7d, 14d, 90d. W Google Ads MCC mogę ustawić dowolny zakres dat.
4. **Brak porównania okresów** — w GAds MCC mogę porównać "ten tydzień vs zeszły tydzień". Tu mam tylko `spend_change_pct` ale nie dla wszystkich metryk.
5. **Brak kolumny "Impression Share"** — w Google Ads MCC mogę dodać IS jako kolumnę. Tu go nie ma.

## Co mnie irytuje / myli

1. **KPI "Kliknięcia: 0" i "Wyświetlenia: 0"** — wygląda na buga. Jeśli seed nie ma tych danych, to lepiej nie pokazywać tych KPI niż pokazywać zera przy $60k wydatków.
2. **"Avg. CTR: —"** na KPI — spójne z zerami ale wzmacnia wrażenie że coś nie działa.
3. **17 kolumn w trybie full** — trzeba skrolować horyzontalnie. Tryb kompaktowy ratuje sytuację, ale może powinien być domyślny?
4. **Kolumna "Płatności" — nie wiem co szare ikony znaczą** — potrzebuję tooltip albo legendy. Czy szare = "OK"? Czy "brak danych"? Czy "błąd"?
5. **Sekcja "Listy wykluczeń MCC" jest pusta** — bo nie mam MCC managera w danych. Specjalista może pomyśleć że feature nie działa.

## Co bym chciał

1. **Filtr okresu** — dropdown "30d / 14d / 7d / Ten miesiąc" nad tabelą
2. **Domyślny compact mode** — włączony od razu, full mode na życzenie
3. **Tooltip na billing ikonie** — "Płatności OK" / "Brak billing setup" / "Brak dostępu"
4. **Row selection z bulk actions** — checkbox per wiersz, button "Synchronizuj zaznaczone" / "Odrzuć rek. zaznaczonych"
5. **Mini sparkline w kolumnie wydatków** — trend 30d zamiast samej liczby

## Verdykt

**Ogromny postęp od pierwszego review.** Tabela ma teraz WSZYSTKIE metryki jak w Google Ads MCC plus rzeczy których GAds nie ma (health score, external changes, new access). Tryb kompaktowy rozwiązuje problem z 17 kolumnami. Przycisk "Odrzuć" na rekomendacjach oszczędza realne minuty dziennie. To jest widok na który WCHODZĘ rano jako pierwszy — szybki scan, sortowanie po ROAS żeby zobaczyć które konto performuje, po health żeby zobaczyć co wymaga uwagi. Kliknięcie → Dashboard. Jedyny minus to zera w KPI kliknięć/wyświetleń (pewnie seed data) i nieprzejrzysta kolumna Płatności.

**Ocena: 8/10 → teraz 9/10** (punkt w dół za KPI zera + billing UX)

---

## Pytania do @ads-expert

1. KPI "Kliknięcia: 0" przy $60k wydatków — czy seed data nie ma clicks/impressions w MetricDaily? Jeśli tak, to powinniśmy albo doseedować te dane albo ukryć puste KPI.
2. Kolumna "Płatności" — same szare ikony bez tooltipa. Czy billing API działa na tych kontach? Potrzebuję wiedzieć co szary kolor oznacza.
3. Czy tryb kompaktowy powinien być domyślny? Przy 17 kolumnach full mode wymaga scrolla.
4. Brak filtra okresu (30d hardcoded) — czy to planowane? W GAds MCC to podstawa.
5. Sekcja "Listy wykluczeń MCC" jest pusta — czy to expected behavior przy braku manager account w danych?
