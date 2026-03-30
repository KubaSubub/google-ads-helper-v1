# ads-user: Alerts (Monitoring)

**Tester:** Marek — specjalista Google Ads, 6 lat doswiadczenia, 8 kont
**Data:** 2026-03-29
**Klient testowy:** Demo Meble Sp. z o.o. (client_id=1)

---

## Co widze

Zakladka "Monitoring" z dwoma pod-tabami: **Alerty** i **Anomalie (z-score)**.

### Tab: Alerty
- Lista 4 nierozwiazanych alertow, kazdy z severity pill (WYSOKI/SREDNI), typem (SPEND_SPIKE, CONVERSION_DROP, CTR_DROP), tytulem, opisem i przyciskiem "Rozwiaz".
- Przelacznik Nierozwiazane/Rozwiazane z licznikiem "(4)".
- Karty alertow sa czytelne — severity kolorystycznie odroznialne (czerwony = wysoki, zolty = sredni).
- Opisy alertow w jezyku naturalnym — np. "Kampania wydala 3.2x wiecej niz proporcjonalny udzial w budzecie konta w ciagu ostatnich 24h".
- Nazwy kampanii przy alertach sa klikalne (link do Kampanie).

### Tab: Anomalie (z-score)
- Panel kontrolny: metryka (Koszt/Klikniecia/Wyswietlenia/Konwersje/CTR), prog z-score (1.5-3.0 sigma), okres (30/60/90d).
- Trzy KPI-boxy: Anomalie (count), Srednia, Odch. std.
- Tabela anomalii: Data, Kampania, Wartosc, Z-score, Typ (Skok/Spadek).
- Ikony strzalek w gore/dol dla typu anomalii.

---

## Co moge zrobic

1. **Przegladac alerty** — lista nierozwiazanych/rozwiazanych.
2. **Rozwiazywac alerty** — przycisk "Rozwiaz" oznacza alert jako resolved.
3. **Przechodzic do kampanii** — klik na nazwe kampanii przenosi do zakladki Kampanie.
4. **Konfigurowac detekcje z-score** — wybieram metryke, prog, okres.
5. **Analizowac anomalie statystyczne** — tabela z z-score i kierunkiem.

---

## Wiecej niz Google Ads

1. **Z-score anomaly detection** — Google Ads nie ma wbudowanego narzedzia statystycznego do wykrywania anomalii z-score. Fajne dla analitykow. Mozliwosc zmiany progu czulosci to dobry pomysl.
2. **Unified alert view** — Google Ads rozrzuca powiadomienia po roznych miejscach (Recommendations, overview alerts, email alerts). Tu jest jedno centrum.
3. **Resolve workflow** — mozliwosc jawnego oznaczenia alertu jako "rozwiazany" — Google Ads nie ma tego (alerty po prostu znikaja albo sie powtarzaja).
4. **CPA_SUSTAINED rule** — 3+ dni z CPA > 150% sredniej to inteligentna regula, Google Ads nie monitoruje tego automatycznie.
5. **DISAPPROVED_ADS detection** — auto-alert na odrzucone reklamy to dobra wartosc dodana.

---

## Brakuje vs Google Ads

### Krytyczne (blokuje moja prace)

1. **Brak alertu na budget cap** — "Kampania wyczerpala budzet o 14:00" to najczestszy alert ktory potrzebuje. Google Ads ma "Limited by budget" status — tutaj zero informacji o tym.
2. **Brak alertu na impression share drop** — spadek IS to kluczowy sygnal ze cos sie psuje (konkurencja, budzet, jakoscowka). Nie monitorowane.
3. **Brak email/push powiadomien** — alerty sa tylko w aplikacji. Jak nie otworze apki rano, nie dowiem sie o spike'u z wczoraj. Google Ads przynajmniej wysyla maile.
4. **Z-score tab nie dziala poprawnie** — frontend wysyla parametry `metric`, `threshold`, `days` do `GET /analytics/anomalies`, ale backend ignoruje je i zwraca zwykle alerty. Caly z-score panel jest prawdopodobnie "pozorny" — renderuje dane alertowe w formacie z-score, ale nie robi prawdziwej analizy statystycznej.

### Wazne (znaczaco ogranicza)

5. **Brak `campaign_name` w odpowiedzi API** — backend zwraca `campaign_id` ale nie `campaign_name`. Frontend renderuje `alert.campaign_name` ktore jest undefined. Link do kampanii moze nie dzialac prawidlowo (ale tytul alertu zawiera nazwe kampanii, wiec user widzi ja w tytule).
6. **Brak historical alertow z timestamp** — nie widze kiedy alert zostal wygenerowany (pole `created_at` jest w API, ale nie wyswietlane w UI). Nie wiem czy alert jest sprzed godziny czy sprzed tygodnia.
7. **Brak prioretyzacji po wplywi finansowym** — alerty nie pokazuja "ile to kosztuje" w zlotowkach. Spend spike mowi "3.2x wiecej" ale nie mowi "przepalono 2000 zl ponad norma".
8. **Brak auto-detekcji** — `POST /detect` endpoint istnieje, ale nie ma widocznego triggera w UI (przycisk "Skanuj teraz" ani scheduler). Alerty sa z seed data, nie z rzeczywistego monitoringu.
9. **Brak filtrowania alertow** — nie moge filtrowac po typie (SPEND_SPIKE vs CTR_DROP), severity, kampanii. Przy 50+ alertach to bedzie nieuzywalne.

### Nice-to-have

10. **Brak trendline/sparkline przy alertach** — alert mowi "spadek konwersji z 4.2 do 0.8" ale nie widze wykresu tego spadku. Jeden mini-wykres bylby wart wiecej niz opis tekstowy.
11. **Brak custom rules** — nie moge dodac wlasnej reguly np. "alert kiedy CPC slowa X przekroczy 5 zl". Tylko 5 wbudowanych regulow.
12. **Brak snooze/mute** — nie moge wyciszyc alertu na 7 dni. Tylko "rozwiaz" (= zamknij na zawsze).
13. **Brak grupowania** — 3 alerty CONVERSION_DROP na roznych kampaniach moglyby byc zgrupowane w jeden: "Spadek konwersji na 3 kampaniach".
14. **Brak severity LOW** — frontend ma SEVERITY_COLORS.LOW zdefiniowany (#4F8EF7), ale backend generuje tylko HIGH i MEDIUM. Brak alertow informacyjnych.

---

## Irytuje

1. **Z-score tab to fasada** — wyglada swietnie na screenshocie, ale po analizie kodu widac ze nie robi prawdziwej analizy z-score. To ten sam endpoint co Alerty, tylko frontend renderuje dane inaczej. Pola `z_score`, `direction`, `mean`, `std` nie istnieja w odpowiedzi backendu. To jest mylace — albo zrobic to porzdanie, albo nie udawac.
2. **Brak daty na alertach** — nie wiem kiedy alert powstal. Alert sprzed 3 tygodni i alert sprzed godziny wygladaja identycznie.
3. **Przycisk "Rozwiaz" bez kontekstu** — co to znaczy "rozwiazalem"? Gdzie moga wpisac co zrobilem? Idealnie: popup z notatka "Zmienilem budzet z X na Y" i data rozwiazania.
4. **Kampania w tabeli z-score pokazuje "ID: 5" zamiast nazwy** — user nie pamietapamieta ID kampanii, powinien widziec nazwe.

---

## Chcialbym

1. **Prawdziwy z-score engine** — backend agreguje MetricDaily per kampania, liczy mean/std per metryka, wyznacza z-score per dzien, zwraca anomalie z prawdziwym z_score i direction. Endpoint `GET /analytics/anomalies/zscore?metric=cost&threshold=2.0&days=90`.
2. **Alerty z timestampem i kwota** — "Wczoraj o 14:00 kampania X wydala 1500 zl wiecej niz normalnie".
3. **Budget alerts** — "Kampania Y wyczerpala dzienny budzet o 11:30" i "Kampania Z wydaje tylko 40% budzetu dziennego — underspend".
4. **Impression share alerts** — "Search IS kampanii A spadl z 65% do 38% w ciagu 7 dni".
5. **Przycisk "Skanuj teraz"** — wywoluje `POST /detect` i odswieza liste alertow.
6. **Mini-wykres w alercie** — sparkline 7-dniowy pokazujacy trend metryki.
7. **Filtry** — po typie alertu, severity, kampanii.
8. **Notatka przy rozwiazywaniu** — "Co zrobilem zeby to naprawic".
9. **Snooze** — "Przypomnij za 3 dni".
10. **Dashboard widget** — top 3 alerty na glownym dashboardzie (widzialem ze jest badge w sidebar z liczba alertow — to dobrze).

---

## Verdykt

**5/10** — Pomysl jest dobry, ale wykonanie jest polowiczne.

**Plusy:**
- Koncept dwoch warstw (alerty biznesowe + anomalie statystyczne) to trafiony pomysl
- UI jest czyste i czytelne
- Resolve workflow to wartosc dodana vs Google Ads
- 5 regul detekcji (SPEND_SPIKE, CONVERSION_DROP, CTR_DROP, CPA_SUSTAINED, DISAPPROVED_ADS) to solidna baza

**Minusy:**
- Z-score tab nie dziala — frontend i backend sa rozlaczone, dane sie nie mapuja
- Brak budget alerts i impression share alerts — to fundamenty monitoringu GAds
- Brak timestampow, filtrowania, notyfikacji poza apka
- Brak `campaign_name` w API response (drobny bug ale irytujacy)
- Brak przycisku "Skanuj teraz" — alerty sa statyczne z seed data

Jako PPCowiec uzywalabym tab Alerty na co dzien, ale tylko po naprawieniu fundamentalnych brakow. Z-score tab jest na ten moment bezuzyteczny — moze wygladac ladnie na demo, ale specjalista to zobaczy w 30 sekund.

---

## Pytania @ads-expert

1. Czy z-score anomaly detection powinien byc osobnym endpointem z prawdziwym obliczaniem z-score, czy wystarczy rozbudowac istniejace reguly alert?
2. Jakie progi sa sensowne dla roznych metryk? Czy 2 sigma na koszcie to to samo co 2 sigma na CTR?
3. Czy budget utilization alerts (underspend/overspend) powinny byc osobna kategoria czy wchodzic w SPEND_SPIKE?
4. Jakie alerty sa "must-have" z perspektywy Google Ads best practice — poza tymi 5 ktore juz sa?
5. Czy warto implementowac alert fatigue management (auto-grouping, smart severity escalation)?
