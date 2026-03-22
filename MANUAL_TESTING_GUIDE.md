# Manual Testing Guide — Google Ads Helper
**Wersja:** 0.1.0 (Phase D GAP Analysis — PMax, Audiences, Extensions)
**Data wygenerowania:** 2026-03-22
**Jak używać:** Przejdź przez każdą sekcję, przetestuj ręcznie, wpisz wynik: ✅ OK | ❌ BUG | ⚠️ Uwaga

---

## SEKCJA 1 — Onboarding & Konfiguracja

### 1.1 Pierwsze uruchomienie
Uruchom aplikację (`python main.py`). PyWebView otwiera okno z osadzonym frontendem serwowanym przez FastAPI na porcie 8000.

Kroki testowania:
1. Uruchom `python main.py` z katalogu głównego repo
2. Poczekaj na otwarcie okna aplikacji

Oczekiwany wynik: Okno PyWebView otwiera się, wyświetla ekran logowania (Login.jsx) z logo "Google Ads Helper" i formularzem konfiguracji API.
Wynik testu: ___________

### 1.2 Konfiguracja Google Ads API credentials
Ekran logowania wyświetla formularz z polami na dane API.

Kroki testowania:
1. Na ekranie logowania znajdź sekcję "Konfiguracja API"
2. Wpisz Developer Token
3. Wpisz OAuth Client ID
4. Wpisz OAuth Client Secret
5. Wpisz Login Customer ID (MCC)
6. Kliknij przycisk pokaż/ukryj hasło (ikona Eye/EyeOff) — sprawdź czy maskowanie działa
7. Kliknij "Zapisz i kontynuuj"

Oczekiwany wynik: Dane zostają zapisane w Windows Credential Manager (keyring). Formularz przechodzi do kroku logowania Google OAuth. Komunikat potwierdzenia wyświetla się na zielono.
Wynik testu: ___________

### 1.3 Logowanie Google OAuth
Po zapisaniu credentiali wyświetla się przycisk logowania Google.

Kroki testowania:
1. Kliknij "Zaloguj się przez Google"
2. Przeglądarka otwiera stronę consent Google
3. Zaakceptuj uprawnienia
4. Callback wraca do aplikacji (`/api/v1/auth/callback`)
5. Sesja zostaje utworzona (cookie)

Oczekiwany wynik: Po pomyślnym logowaniu aplikacja przechodzi do głównego widoku (Dashboard). Status auth: `ready: true`.
Wynik testu: ___________

### 1.4 Zmiana credentiali API
Na ekranie logowania dostępny jest przycisk powrotu do konfiguracji.

Kroki testowania:
1. Na ekranie logowania (gdy OAuth jest gotowy) kliknij "Zmień dane API"
2. Zmień dowolne pole
3. Zapisz ponownie

Oczekiwany wynik: Nowe credentiale nadpisują stare w Windows Credential Manager.
Wynik testu: ___________

### 1.5 Wylogowanie
Przycisk wylogowania w stopce sidebara.

Kroki testowania:
1. Kliknij ikonę LogOut w dolnej części sidebara
2. Potwierdź wylogowanie

Oczekiwany wynik: Sesja zostaje wyczyszczona (`POST /auth/logout`), strona przeładowuje się i wyświetla ekran logowania.
Wynik testu: ___________

### 1.6 Obsługa błędów logowania
Testowanie scenariuszy negatywnych.

Kroki testowania:
1. Wpisz nieprawidłowy Developer Token → zapisz
2. Sprawdź komunikat błędu (czerwony banner z AlertTriangle)
3. Spróbuj OAuth z niepoprawnymi credentialami

Oczekiwany wynik: Komunikaty błędów wyświetlają się czytelnie po polsku. Aplikacja nie crashuje.
Wynik testu: ___________

### 1.7 Sprawdzenie statusu setup (backend only)
Endpoint: `GET /api/v1/auth/setup-status`

Kroki testowania:
1. Wywołaj endpoint w przeglądarce lub curl
2. Sprawdź odpowiedź: `developer_token_set`, `client_id_set`, `client_secret_set`

Oczekiwany wynik: JSON z flagami boolean dla każdego pola.
Wynik testu: ___________

### 1.8 Pobranie zapisanych wartości setup (backend only)
Endpoint: `GET /api/v1/auth/setup-values`

Kroki testowania:
1. Wywołaj endpoint po zapisaniu credentiali
2. Sprawdź czy OAuth tokeny NIE są zwracane (tylko metadata)

Oczekiwany wynik: Zwraca zamaskowane wartości API credentials, bez tokenów OAuth.
Wynik testu: ___________

---

## SEKCJA 2 — Synchronizacja danych

### 2.1 Ręczny sync (przycisk Refresh na stronie Klienci)
Synchronizacja uruchamiana ręcznie.

Kroki testowania:
1. Przejdź do strony Klienci (`/clients`)
2. Wybierz klienta
3. Kliknij przycisk Sync (ikona RefreshCw) przy wybranym kliencie
4. Obserwuj spinner podczas sync

Oczekiwany wynik: Sync uruchamia się (`POST /sync/trigger`), spinner się kręci, po zakończeniu dane zostają odświeżone. Toast z potwierdzeniem.
Wynik testu: ___________

### 2.2 Które dane są synchronizowane (22 fazy sync)
Pełna lista faz synchronizacji:

| # | Faza | Opis |
|---|------|------|
| 1 | campaigns | Kampanie |
| 2 | ad_groups | Grupy reklam |
| 3 | keywords | Słowa kluczowe (pozytywne) |
| 4 | negative_keywords | Negatywne słowa kluczowe |
| 5 | ads | Reklamy |
| 6 | metrics_daily | Metryki dzienne |
| 7 | metrics_segmented | Metryki segmentowane (device, geo, hour) |
| 8 | search_terms | Frazy wyszukiwania |
| 9 | segmentation | Segmentacja search terms |
| 10 | change_events | Historia zmian |
| 11 | conversion_actions | Konfiguracja konwersji |
| 12 | age_metrics | Metryki demograficzne (wiek) |
| 13 | gender_metrics | Metryki demograficzne (płeć) |
| 14 | pmax_channel_metrics | Metryki kanałów PMax |
| 15 | asset_groups | Grupy zasobów PMax |
| 16 | asset_group_daily | Dzienne metryki grup zasobów |
| 17 | asset_group_assets | Zasoby w grupach zasobów |
| 18 | asset_group_signals | Sygnały odbiorców PMax |
| 19 | campaign_audiences | Metryki odbiorców kampanii |
| 20 | campaign_assets | Rozszerzenia kampanii |
| 21 | cleanup | Czyszczenie nieaktualnych danych |
| 22 | recommendations | Generowanie rekomendacji |

Kroki testowania:
1. Uruchom pełny sync dla klienta z prawdziwymi danymi Google Ads
2. Sprawdź logi sync (`GET /sync/logs?client_id=X`)
3. Zweryfikuj czy każda faza wykonała się pomyślnie

Oczekiwany wynik: Wszystkie 22 fazy sync zakończone sukcesem. Logi sync dostępne.
Wynik testu: ___________

### 2.3 Status synchronizacji — gdzie to widać
Endpoint: `GET /api/v1/sync/status`

Kroki testowania:
1. Sprawdź status sync w sidebarze (napis "Sync * aktywny" pod nazwą klienta)
2. Wywołaj endpoint `/sync/status`
3. Sprawdź czy odpowiedź zawiera info o połączeniu z Google Ads API

Oczekiwany wynik: Status sync widoczny w sidebarze. Endpoint zwraca `connected: true/false`.
Wynik testu: ___________

### 2.4 Obsługa błędów sync
Scenariusze negatywne.

Kroki testowania:
1. Uruchom sync z wygaśniętym tokenem OAuth → sprawdź komunikat
2. Uruchom sync z nieistniejącym customer_id → sprawdź komunikat
3. Sprawdź czy błąd jednej fazy nie blokuje pozostałych (per-phase error tracking)

Oczekiwany wynik: Szczegółowe komunikaty błędów. Fazy niezależne kontynuują się mimo błędu innej fazy.
Wynik testu: ___________

### 2.5 Sync pojedynczej fazy (backend only, debug)
Endpoint: `POST /api/v1/sync/phase/{phase_name}`

Kroki testowania:
1. Wywołaj `POST /sync/phase/campaigns?client_id=X`
2. Sprawdź odpowiedź

Oczekiwany wynik: Tylko wskazana faza się wykonuje. Zwraca status fazy.
Wynik testu: ___________

### 2.6 Sync debug — diagnostyka (backend only)
Endpoint: `GET /api/v1/sync/debug`

Kroki testowania:
1. Wywołaj endpoint
2. Sprawdź liczby wierszy per zasób, ścieżki DB, ostatni sync

Oczekiwany wynik: JSON z row counts per resource, active/legacy DB paths, last sync timestamp.
Wynik testu: ___________

### 2.7 Cleanup po sync — usunięte encje
Po pomyślnym sync, kampanie/ad groups/keywords nieobecne w API oznaczane jako REMOVED.

Kroki testowania:
1. Uruchom sync dla klienta
2. Sprawdź czy kampanie usunięte w Google Ads mają status REMOVED lokalnie
3. Sprawdź czy domyślny widok ukrywa REMOVED

Oczekiwany wynik: Brak danych zombie. REMOVED encje ukryte domyślnie, widoczne po włączeniu opcji.
Wynik testu: ___________

---

## SEKCJA 3 — Dashboard (Pulpit nawigacyjny)

### 3.1 Health Score — wskaźnik zdrowia konta
Okrągły gauge SVG w lewym górnym rogu Dashboard.

Kroki testowania:
1. Przejdź na Dashboard (`/`)
2. Sprawdź czy gauge Health Score jest widoczny
3. Sprawdź wartość (0-100) i kolor (zielony >70, żółty 50-70, czerwony <50)

Oczekiwany wynik: Gauge SVG renderuje się poprawnie z animacją strokeDasharray. Wartość odpowiada rzeczywistemu stanowi konta.
Wynik testu: ___________

### 3.2 KPI Grid — metryki dzienne z porównaniem
Siatka KPI z porównaniem dzisiaj vs wczoraj.

Kroki testowania:
1. Sprawdź obecność kart KPI: Wydatki, Kliknięcia, Konwersje, Wyświetlenia, CTR
2. Sprawdź wartości "dzisiaj" vs "wczoraj"
3. Sprawdź strzałki trendu (TrendingUp/Down z kolorem)
4. Sprawdź formatowanie kwot (zł z grosze, nie mikro)

Oczekiwany wynik: 5 kart KPI z aktualnymi wartościami. Strzałki kolorowe (zielona = wzrost, czerwona = spadek). Wartości w formacie czytelnym.
Wynik testu: ___________

### 3.3 GlobalFilterBar — zmiana zakresu dat
Pasek filtrów widoczny na stronach Kategorii A.

Kroki testowania:
1. Na Dashboard sprawdź obecność GlobalFilterBar
2. Zmień Campaign Type dropdown → sprawdź czy KPI się odświeżają
3. Zmień Campaign Status dropdown → sprawdź czy KPI się odświeżają

Oczekiwany wynik: Filtry wpływają na wyświetlane dane. Domyślnie "Wszystkie".
Wynik testu: ___________

### 3.4 Sidebar — zakres dat (DateRangePicker)
Picker dat w sidebarze.

Kroki testowania:
1. Kliknij preset 7d → sprawdź czy Dashboard odświeża dane za 7 dni
2. Kliknij preset 14d, 30d, 90d → analogicznie
3. Kliknij ikonę kalendarza → sprawdź czy pojawiają się pola date-from / date-to
4. Ustaw własny zakres dat → sprawdź odświeżenie

Oczekiwany wynik: Presety i custom range działają, dane na Dashboard reagują na zmianę zakresu.
Wynik testu: ___________

### 3.5 Campaign Budget Pacing Grid
Mini karty z postępem budżetowym per kampania.

Kroki testowania:
1. Sprawdź obecność siatki kart budżetowych
2. Dla każdej kampanii: nazwa, budżet, wydatek, % pacing
3. Sprawdź pasek postępu (progress bar)
4. Sprawdź badge statusu kampanii (ENABLED/PAUSED pill)

Oczekiwany wynik: Karty wyświetlają aktualne dane pacing. Paski postępu kolorowe (zielony <80%, żółty 80-100%, czerwony >100%).
Wynik testu: ___________

### 3.6 Device Share Bar Chart
Wykres podziału urządzeń.

Kroki testowania:
1. Sprawdź obecność wykresu słupkowego z podziałem Desktop/Mobile/Tablet
2. Sprawdź czy dane odpowiadają faktycznym proporcjom

Oczekiwany wynik: Wykres renderuje się poprawnie z etykietami i wartościami procentowymi.
Wynik testu: ___________

### 3.7 Top Audience List Table
Tabela najlepszych odbiorców.

Kroki testowania:
1. Sprawdź obecność tabeli odbiorców
2. Sprawdź kolumny i dane

Oczekiwany wynik: Tabela wyświetla odbiorców z metrykami (kliknięcia, konwersje, CPA).
Wynik testu: ___________

### 3.8 Top Keywords Table ze sparkline'ami
Tabela najważniejszych słów kluczowych.

Kroki testowania:
1. Sprawdź obecność tabeli keywords
2. Sprawdź kolumny: nazwa, QS (badge), Avg CPC, sparkline
3. Sprawdź czy sparkline (72x24px LineChart) renderuje się poprawnie

Oczekiwany wynik: Tabela z miniaturowymi wykresami trendów (sparklines). QS badge kolorowy.
Wynik testu: ___________

### 3.9 Przycisk Refresh na Dashboard
Odświeżanie danych.

Kroki testowania:
1. Kliknij przycisk Refresh (ikona RefreshCw) na Dashboard
2. Sprawdź czy dane się odświeżają

Oczekiwany wynik: Dane odświeżone, spinner podczas ładowania.
Wynik testu: ___________

---

## SEKCJA 4 — Kampanie

### 4.1 Lista kampanii
Tabela kampanii z danymi.

Kroki testowania:
1. Przejdź na stronę Kampanie (`/campaigns`)
2. Sprawdź obecność tabeli z kampaniami
3. Sprawdź kolumny: Nazwa, Status, Typ, Budżet, Wydatek, Kliknięcia, Wyświetlenia, Konwersje/Koszt, Pacing, Health Score

Oczekiwany wynik: Tabela wyświetla wszystkie kampanie klienta z aktualnymi danymi.
Wynik testu: ___________

### 4.2 Status badge (ENABLED/PAUSED)
Badge statusu kampanii w tabeli.

Kroki testowania:
1. Sprawdź badge'e statusu w kolumnie Status
2. ENABLED = zielony pill
3. PAUSED = szary pill

Oczekiwany wynik: Badge'e kolorowe, czytelne.
Wynik testu: ___________

### 4.3 Typ kampanii badge (SEARCH/DISPLAY/SHOPPING/PMAX)
Badge typu kampanii.

Kroki testowania:
1. Sprawdź badge'e typu w kolumnie Typ
2. Różne kolory dla różnych typów

Oczekiwany wynik: Badge z krótkim typem kampanii, kolorowy.
Wynik testu: ___________

### 4.4 Campaign Roles — auto-classification
Automatyczna klasyfikacja ról kampanii.

Kroki testowania:
1. Sprawdź kolumnę/sekcję roli kampanii (np. BRAND, NON_BRAND, TOP_CATEGORY)
2. Sprawdź `campaign_role_auto` i `role_confidence` w odpowiedzi API
3. Sprawdź badge z poziomem pewności

Oczekiwany wynik: Każda kampania ma automatycznie przypisaną rolę z poziomem pewności. Badge widoczny.
Wynik testu: ___________

### 4.5 Campaign Roles — manual override
Ręczna zmiana roli kampanii.

Kroki testowania:
1. Kliknij przycisk edycji roli przy kampanii
2. Zmień rolę na inną (np. BRAND → COMPETITOR)
3. Zapisz (`PATCH /campaigns/{id}`)
4. Sprawdź czy `role_source` zmienił się na `MANUAL`
5. Uruchom sync → sprawdź czy ręczna rola NIE jest nadpisywana

Oczekiwany wynik: Ręczna rola zapisana. `role_source: MANUAL`. Sync nie nadpisuje manual override.
Wynik testu: ___________

### 4.6 Campaign Roles — reset do auto
Reset ręcznej roli do automatycznej.

Kroki testowania:
1. Przy kampanii z manual override kliknij reset
2. Sprawdź czy rola wróciła do `campaign_role_auto`
3. Sprawdź `role_source: AUTO`

Oczekiwany wynik: Rola zresetowana do auto-klasyfikacji.
Wynik testu: ___________

### 4.7 Ochrona kampanii (protection level)
Poziom ochrony kampanii.

Kroki testowania:
1. Sprawdź `protection_level` dla kampanii BRAND → powinien być HIGH
2. Sprawdź dla kampanii NON_BRAND → powinien być MEDIUM/LOW
3. Sprawdź czy protection level wpływa na rekomendacje (blokuje agresywne akcje)

Oczekiwany wynik: Protection level widoczny. Kampanie BRAND chronione przed agresywnymi zmianami.
Wynik testu: ___________

### 4.8 KPI Row kampanii
Wiersz KPI nad tabelą kampanii.

Kroki testowania:
1. Sprawdź podsumowanie KPI: Cost, Clicks, Conversions, CTR, ROAS
2. Sprawdź czy wartości reagują na filtr GlobalFilterBar

Oczekiwany wynik: KPI agregatowe dla wyfiltrowanych kampanii.
Wynik testu: ___________

### 4.9 Filtrowanie kampanii przez GlobalFilterBar
Filtrowanie po typie i statusie.

Kroki testowania:
1. Wybierz Campaign Type = SEARCH → tylko kampanie SEARCH widoczne
2. Wybierz Campaign Status = PAUSED → tylko wstrzymane kampanie
3. Zmień zakres dat → KPI i pacing się aktualizują
4. Zresetuj na "Wszystkie" → wszystkie kampanie widoczne

Oczekiwany wynik: Filtrowanie działa server-side (API params). Dane odświeżają się po zmianie filtra.
Wynik testu: ___________

### 4.10 KPI per kampania
Szczegółowe KPI dla pojedynczej kampanii.

Kroki testowania:
1. Wywołaj `GET /campaigns/{id}/kpis?days=30`
2. Sprawdź odpowiedź: current period vs previous period, delty

Oczekiwany wynik: JSON z danymi porównawczymi dwóch okresów.
Wynik testu: ___________

### 4.11 Metryki dzienne kampanii
Endpoint: `GET /campaigns/{id}/metrics`

Kroki testowania:
1. Wywołaj endpoint z `date_from` i `date_to`
2. Sprawdź odpowiedź: dzienne metryki

Oczekiwany wynik: Array z dziennymi danymi (data, clicks, impressions, cost, conversions).
Wynik testu: ___________

### 4.12 Trend Explorer
Zakładka Trend Explorer na stronie Kampanie.

Kroki testowania:
1. Przejdź na zakładkę Trend Explorer
2. Wybierz metrykę (Cost, Clicks, Conversions, CTR, ROAS)
3. Wybierz kampanię
4. Sprawdź wykres ComposedChart
5. Sprawdź oś czasu akcji (action timeline)
6. Włącz tryb porównania Before/After

Oczekiwany wynik: Wykres z dwoma osiami, linia trendu z zaznaczonymi akcjami. Tabela porównawcza.
Wynik testu: ___________

---

## SEKCJA 5 — Słowa kluczowe

### 5.1 Lista keywords z filtrami
Strona Słowa kluczowe (`/keywords`).

Kroki testowania:
1. Przejdź na stronę Keywords
2. Sprawdź tabelę ze słowami kluczowymi
3. Sprawdź kolumny: Keyword, Campaign, Ad Group, QS, Status, Avg CPC, Impressions, Clicks, Conversions, Cost

Oczekiwany wynik: Tabela z pełnymi danymi keywords.
Wynik testu: ___________

### 5.2 Status badges (Enabled/Paused/Removed)
Badge statusu słowa kluczowego.

Kroki testowania:
1. Sprawdź badge ENABLED (zielony)
2. Sprawdź badge PAUSED (szary)
3. Włącz "Pokaż usunięte" → sprawdź badge REMOVED (czerwony)

Oczekiwany wynik: Badge'e kolorowe odpowiednio do statusu.
Wynik testu: ___________

### 5.3 Match type display
Badge typu dopasowania.

Kroki testowania:
1. Sprawdź badge'e: Broad (B), Phrase (P), Exact (E) — każdy w innym kolorze
2. Sprawdź filtr match type pills: Broad, Phrase, Exact, Wszystkie
3. Kliknij filtr → sprawdź czy tabela filtruje

Oczekiwany wynik: Badge'e match type kolorowe. Filtrowanie po match type działa.
Wynik testu: ___________

### 5.4 Quality Score badge
Badge wyniku jakości.

Kroki testowania:
1. Sprawdź kolumnę QS z kolorowym badge (kwadrat 30x30px z liczbą)
2. QS 8-10 = zielony
3. QS 5-7 = żółty
4. QS 1-4 = czerwony

Oczekiwany wynik: Badge QS kolorowy, wartość czytelna.
Wynik testu: ___________

### 5.5 Ukrywanie/pokazywanie usuniętych
Toggle "Pokaż usunięte".

Kroki testowania:
1. Domyślnie usunięte keywords są ukryte
2. Kliknij toggle "Pokaż usunięte"
3. Sprawdź czy REMOVED keywords się pojawiły
4. Kliknij ponownie → ukryte z powrotem

Oczekiwany wynik: Toggle działa, REMOVED keywords widoczne/ukryte.
Wynik testu: ___________

### 5.6 Export keywords (CSV/Excel)
Eksport danych.

Kroki testowania:
1. Kliknij przycisk Export CSV
2. Sprawdź pobrany plik — kolumny: keyword, campaign, ad_group, match_type, QS, metryki
3. Kliknij przycisk Export Excel
4. Sprawdź pobrany plik .xlsx

Oczekiwany wynik: Pliki pobierają się poprawnie z pełnymi danymi. Kolumny campaign/ad group zawarte.
Wynik testu: ___________

### 5.7 Wyszukiwanie keywords
Pole Search.

Kroki testowania:
1. Wpisz tekst w pole wyszukiwania
2. Sprawdź czy tabela filtruje po nazwie keyword

Oczekiwany wynik: Filtrowanie po tekście działa w czasie rzeczywistym.
Wynik testu: ___________

### 5.8 Paginacja
Nawigacja między stronami wyników.

Kroki testowania:
1. Sprawdź przyciski Previous/Next
2. Kliknij Next → sprawdź czy ładują się następne wyniki
3. Sprawdź wskaźnik strony

Oczekiwany wynik: Paginacja działa poprawnie.
Wynik testu: ___________

### 5.9 Kontekst kampanii per keyword
Wyświetlanie nazwy kampanii i ad group przy keywordzie.

Kroki testowania:
1. Sprawdź kolumny Campaign i Ad Group w tabeli keywords
2. Sprawdź czy nazwy odpowiadają rzeczywistej strukturze konta

Oczekiwany wynik: Nazwa kampanii i ad group wyświetlają się poprawnie.
Wynik testu: ___________

### 5.10 Delivery issue badges
Badge'e problemów z dostarczaniem.

Kroki testowania:
1. Sprawdź czy keywords z problemami mają dodatkowe badge (np. Low Search Volume, Below First Page Bid)

Oczekiwany wynik: Badge'e widoczne obok nazwy keyword.
Wynik testu: ___________

### 5.11 Zakładka Negative Keywords
Zarządzanie negatywnymi słowami kluczowymi.

Kroki testowania:
1. Przejdź na zakładkę Negative Keywords
2. Sprawdź listę negative keywords z kolumnami: keyword, scope (Campaign/Ad Group), match type
3. Sprawdź filtr scope (Account, Campaign, Ad Group pills)

Oczekiwany wynik: Lista negative keywords wyświetla się poprawnie.
Wynik testu: ___________

### 5.12 Dodawanie negative keyword
Modal dodawania.

Kroki testowania:
1. Kliknij przycisk "+" (Add)
2. Sprawdź modal z polami: keyword text, match type, scope
3. Wpisz keyword → dodaj (`POST /negative-keywords/`)
4. Sprawdź czy pojawił się na liście

Oczekiwany wynik: Modal otwiera się, keyword zostaje dodany, lista odświeżona.
Wynik testu: ___________

### 5.13 Usuwanie negative keyword
Soft-delete.

Kroki testowania:
1. Kliknij przycisk Delete przy negative keyword
2. Potwierdź usunięcie
3. Sprawdź czy keyword zniknął z listy

Oczekiwany wynik: Keyword usunięty (soft-delete), lista odświeżona.
Wynik testu: ___________

### 5.14 Zakładka Negative Keyword Lists
Zarządzanie listami negatywnych.

Kroki testowania:
1. Przejdź na zakładkę Negative Keyword Lists
2. Sprawdź listę list (nazwa, liczba elementów)

Oczekiwany wynik: Lista list negatywnych wyświetla się.
Wynik testu: ___________

### 5.15 Tworzenie nowej listy negatywnych
Tworzenie listy.

Kroki testowania:
1. Kliknij "Utwórz listę"
2. Wpisz nazwę listy
3. Zapisz (`POST /negative-keyword-lists/`)
4. Sprawdź czy lista pojawiła się

Oczekiwany wynik: Lista utworzona, widoczna na liście.
Wynik testu: ___________

### 5.16 Dodawanie keywords do listy
Dodawanie elementów.

Kroki testowania:
1. Rozwiń listę
2. Kliknij "Dodaj elementy"
3. Wpisz keywords (oddzielone enterem)
4. Zapisz (`POST /negative-keyword-lists/{id}/items`)
5. Sprawdź czy keywords zostały dodane (duplikaty pominięte)

Oczekiwany wynik: Keywords dodane. Duplikaty pominięte z info.
Wynik testu: ___________

### 5.17 Usuwanie z listy negatywnych
Usuwanie elementu.

Kroki testowania:
1. Kliknij X przy keyword w rozwiniętej liście
2. Sprawdź usunięcie (`DELETE /negative-keyword-lists/{id}/items/{item_id}`)

Oczekiwany wynik: Element usunięty z listy.
Wynik testu: ___________

### 5.18 Bulk-apply listy na kampanie/ad groups
Masowe zastosowanie.

Kroki testowania:
1. Kliknij "Zastosuj listę" przy wybranej liście
2. Wybierz kampanie lub ad groups w modaludoku
3. Zatwierdź (`POST /negative-keyword-lists/{id}/apply`)
4. Sprawdź czy negative keywords zostały utworzone

Oczekiwany wynik: Elementy listy zastosowane jako NegativeKeyword records dla wybranych kampanii/ad groups.
Wynik testu: ___________

### 5.19 Usuwanie listy negatywnych
Usuwanie całej listy.

Kroki testowania:
1. Kliknij Delete list
2. Potwierdź usunięcie (`DELETE /negative-keyword-lists/{id}`)
3. Sprawdź czy lista i wszystkie elementy zniknęły

Oczekiwany wynik: Lista usunięta z wszystkimi elementami.
Wynik testu: ___________

### 5.20 Zakładka Keyword Expansion
Sugestie rozszerzenia keywords.

Kroki testowania:
1. Przejdź na zakładkę Keyword Expansion
2. Sprawdź tabelę sugestii (search terms → keyword)
3. Sprawdź kolumny: term, clicks, conversions, suggested match type

Oczekiwany wynik: Tabela z sugestiami opartymi na high-performing search terms.
Wynik testu: ___________

---

## SEKCJA 6 — Frazy wyszukiwania (Search Terms)

### 6.1 Lista search terms
Strona Frazy wyszukiwania (`/search-terms`).

Kroki testowania:
1. Przejdź na stronę Search Terms
2. Sprawdź tabelę: search term, match type, segment, clicks, impressions, cost, conversions, CPC

Oczekiwany wynik: Tabela z pełnymi danymi search terms.
Wynik testu: ___________

### 6.2 Widok Aggregated vs Segmented
Przełączanie trybu widoku.

Kroki testowania:
1. Sprawdź pills "Zagregowane" / "Segmentowane"
2. Kliknij Segmentowane → sprawdź grupowanie po: Match Type, Device, Day of Week, Hour

Oczekiwany wynik: Widok zmienia się między agregatowym a segmentowanym.
Wynik testu: ___________

### 6.3 Segment badge
Badge segmentu search term.

Kroki testowania:
1. Sprawdź badge'e segmentów: HIGH_PERFORMER (zielony), WASTE (czerwony), IRRELEVANT (szary), OTHER (niebieski)
2. Sprawdź czy kolory odpowiadają segmentowi

Oczekiwany wynik: Badge'e kolorowe z etykietą segmentu.
Wynik testu: ___________

### 6.4 Wyszukiwanie i filtrowanie
Pole search.

Kroki testowania:
1. Wpisz tekst w pole wyszukiwania
2. Sprawdź filtrowanie po nazwie search term
3. Sprawdź reakcję na GlobalFilterBar (date range, campaign type, campaign status)

Oczekiwany wynik: Filtrowanie po tekście i globalnych filtrach działa.
Wynik testu: ___________

### 6.5 Export search terms (CSV/Excel)
Eksport danych.

Kroki testowania:
1. Kliknij Export CSV → sprawdź pobrany plik
2. Kliknij Export Excel → sprawdź pobrany plik .xlsx
3. Sprawdź czy PMax search terms (bez ad_group_id) są zawarte

Oczekiwany wynik: Pliki pobierają się z pełnymi danymi, włącznie z PMax terms.
Wynik testu: ___________

### 6.6 Bulk select — zaznaczanie search terms
Zaznaczanie checkboxami.

Kroki testowania:
1. Zaznacz kilka search terms checkboxami
2. Sprawdź czy pojawia się Bulk Action Bar
3. Sprawdź licznik zaznaczonych

Oczekiwany wynik: Bulk Action Bar pojawia się z liczbą zaznaczonych.
Wynik testu: ___________

### 6.7 Bulk add negative — wybór terminów
Masowe dodanie negatywnych.

Kroki testowania:
1. Zaznacz kilka waste search terms
2. Kliknij "Dodaj jako negatywne"
3. Wybierz poziom: Campaign lub Ad Group
4. Sprawdź podgląd (preview) przed akcją
5. Potwierdź akcję (`POST /search-terms/bulk-add-negative`)

Oczekiwany wynik: Search terms dodane jako negative keywords na wybranym poziomie. Akcja zalogowana w action_log.
Wynik testu: ___________

### 6.8 Bulk add keyword — promocja search terms
Masowe dodanie jako positive keywords.

Kroki testowania:
1. Zaznacz high-performing search terms
2. Kliknij "Dodaj jako keyword"
3. Wybierz target ad group
4. Potwierdź (`POST /search-terms/bulk-add-keyword`)

Oczekiwany wynik: Search terms dodane jako keywords w wybranym ad group. Akcja zalogowana.
Wynik testu: ___________

### 6.9 Bulk preview przed akcją
Podgląd przed bulk action.

Kroki testowania:
1. Zaznacz search terms
2. Kliknij podgląd (`POST /search-terms/bulk-preview`)
3. Sprawdź wzbogacone dane preview (campaign, ad group, match type)

Oczekiwany wynik: Preview wyświetla szczegóły zaznaczonych terms z kontekstem.
Wynik testu: ___________

### 6.10 Paginacja search terms
Nawigacja stronami.

Kroki testowania:
1. Sprawdź przyciski Previous/Next
2. Nawiguj między stronami

Oczekiwany wynik: Paginacja działa poprawnie.
Wynik testu: ___________

### 6.11 Summary search terms (backend only)
Endpoint: `GET /api/v1/search-terms/summary`

Kroki testowania:
1. Wywołaj endpoint z `campaign_id`
2. Sprawdź aggregated summary

Oczekiwany wynik: JSON z podsumowaniem search terms dla kampanii.
Wynik testu: ___________

---

## SEKCJA 7 — Rekomendacje Engine

### 7.1 R1 — Pause Keyword: wysoki koszt bez konwersji
**Typ:** `PAUSE_KEYWORD`
**Warunek wyzwolenia:** `cost >= $50 AND clicks >= 30 AND conversions == 0`
**Priorytet:** HIGH
**Executable:** TAK (ACTION)

Kroki testowania:
1. Znajdź keyword z cost ≥ $50, clicks ≥ 30, conversions = 0
2. Uruchom rekomendacje → sprawdź czy R1 się pojawia
3. **Apply button:** kliknij Apply → keyword powinien przejść na PAUSED
4. **Confirmation modal:** sprawdź czy modal potwierdzenia się wyświetla
5. **Dry-run:** wywołaj z `dry_run=true` → sprawdź symulację bez zmiany
6. **Rollback:** sprawdź czy akcja jest revertable w ciągu 24h

Wynik testu: ___________

### 7.2 R1b — Pause Keyword: niski CTR
**Typ:** `PAUSE_KEYWORD`
**Warunek wyzwolenia:** `impressions >= 1000 AND CTR < 0.5%`
**Priorytet:** MEDIUM
**Executable:** TAK (ACTION)

Kroki testowania:
1. Znajdź keyword z impressions ≥ 1000 i CTR < 0.5%
2. Sprawdź rekomendację → porada: "Pause or improve ad relevance"

Wynik testu: ___________

### 7.3 R2 — Increase Bid
**Typ:** `INCREASE_BID`
**Warunek wyzwolenia:** `CVR > avg_CVR × 1.5 AND CPA < avg_CPA × 0.8 AND conversions >= 2`
**Priorytet:** dynamiczny
**Executable:** TAK (ACTION) — zwiększa bid o 20%

Kroki testowania:
1. Znajdź keyword z high CVR i low CPA relative to campaign average
2. Sprawdź rekomendację → nowy bid = current × 1.2
3. Apply → sprawdź czy bid został zmieniony w payload
4. Sprawdź `change_pct: +20%` w action_payload

Wynik testu: ___________

### 7.4 R3 — Decrease Bid
**Typ:** `DECREASE_BID`
**Warunek wyzwolenia:** `CPA > avg_CPA × 1.5 AND cost >= $100 AND conversions > 0`
**Priorytet:** dynamiczny
**Executable:** TAK (ACTION) — zmniejsza bid o 20%

Kroki testowania:
1. Znajdź keyword z high CPA i cost ≥ $100
2. Sprawdź rekomendację → nowy bid = current × 0.8
3. Apply → sprawdź zmianę bidu

Wynik testu: ___________

### 7.5 R4 — Add Keyword (z search terms)
**Typ:** `ADD_KEYWORD`
**Warunek wyzwolenia:**
- High-converting: `conversions >= 3` → SEARCH: ACTION, PMax: INSIGHT_ONLY
- High-engagement: `clicks >= 10, CVR == 0, CTR >= 5%` → LOW priority
**Executable:** TAK dla SEARCH / NIE dla PMax

Kroki testowania:
1. Znajdź search term z ≥ 3 konwersjami, nie istniejący jako keyword
2. Sprawdź rekomendację → suggested match type: EXACT (≤2 words) / PHRASE (>2 words)
3. Apply → sprawdź czy keyword został dodany
4. Sprawdź scenariusz PMax → powinien być INSIGHT_ONLY

Wynik testu: ___________

### 7.6 R5 — Add Negative
**Typ:** `ADD_NEGATIVE`
**Warunek wyzwolenia:**
- Irrelevant patterns (account-level): matched against `_IRRELEVANT_PATTERNS` → HIGH
- Low CTR, no conversions: `clicks >= 5, conversions == 0, CTR < 1%` → MEDIUM
- Immediate waste: `cost >= $30, conversions == 0` → HIGH
**Executable:** TAK (ACTION)

Kroki testowania:
1. Sprawdź rekomendacje ADD_NEGATIVE
2. Sprawdź match `negative_level: CAMPAIGN` lub `ACCOUNT`
3. Sprawdź `negative_match_type: PHRASE`
4. Apply → sprawdź czy negative keyword został dodany
5. **Uwaga: ADD_NEGATIVE jest NIEREVERTABLE** (ADR-007)

Wynik testu: ___________

### 7.7 R6 — Pause Ad
**Typ:** `PAUSE_AD`
**Warunek wyzwolenia:**
- Low CTR: `CTR < best_ad_CTR × 0.5, min 2 ads, impressions >= 500` → MEDIUM
- High spend, zero conv: `cost >= $50, conversions == 0` → HIGH
**Executable:** TAK (ACTION)

Kroki testowania:
1. Znajdź ad group z ≥ 2 reklamami, jedna z niskim CTR
2. Sprawdź rekomendację → "Pause and create new variant"
3. Apply → reklama przechodzi na PAUSED
4. Rollback → sprawdź revert w ciągu 24h

Wynik testu: ___________

### 7.8 R7 — Reallocate Budget
**Typ:** `REALLOCATE_BUDGET`
**Warunek wyzwolenia:** `best_ROAS > worst_ROAS × 2.0, min 2 campaigns`
**Priorytet:** dynamiczny
**Executable:** NIE (INSIGHT_ONLY by design — ADR)

Kroki testowania:
1. Sprawdź rekomendację z sugestią przesuniecia 20% budżetu
2. Sprawdź `from_campaign_id` i `to_campaign_id` w payload
3. Sprawdź czy przycisk Apply jest **wyłączony** (disabled)
4. Sprawdź kontekst: role comparability, protection checks

Wynik testu: ___________

### 7.9 R8 — Quality Score Alert
**Typ:** `QS_ALERT`
**Warunek wyzwolenia:** `quality_score < 5 AND impressions >= 100`
**Priorytet:** dynamiczny
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację dla keywords z QS < 5
2. Sprawdź metadata: Expected CTR, Ad Relevance, Landing Page subcomponents
3. Sprawdź disabled Apply button

Wynik testu: ___________

### 7.10 R9 — IS Lost to Budget
**Typ:** `IS_BUDGET_ALERT`
**Warunek wyzwolenia:** `search_budget_lost_is >= 20%`
**Priorytet:** HIGH jeśli > 40%, MEDIUM w.p.p.
**Executable:** WARUNKOWO (ACTION jeśli `can_scale`, INSIGHT_ONLY w.p.p.)

Kroki testowania:
1. Sprawdź rekomendację dla kampanii z dużym lost IS do budżetu
2. Sprawdź context outcome: ACTION vs INSIGHT_ONLY
3. Jeśli ACTION → sprawdź `budget_action: increase 20%`
4. Sprawdź `downgrade_reasons` jeśli zablokowany

Wynik testu: ___________

### 7.11 R10 — IS Lost to Rank
**Typ:** `IS_RANK_ALERT`
**Warunek wyzwolenia:** `search_rank_lost_is > 30% AND search_budget_lost_is <= 10%`
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Improve Quality Score or increase bids"
2. Sprawdź wykluczenie kampanii z dużym lost IS do budżetu

Wynik testu: ___________

### 7.12 R11 — Low CTR Keyword
**Typ:** `LOW_CTR_KEYWORD`
**Warunek wyzwolenia:** `CTR < 0.5% AND impressions > 1000 AND match_type ∈ {BROAD, PHRASE} AND conversions == 0`
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Pause or narrow to EXACT match"
2. Sprawdź filtr na match type (Broad/Phrase only)

Wynik testu: ___________

### 7.13 R12 — Wasted Spend Alert
**Typ:** `WASTED_SPEND_ALERT`
**Warunek wyzwolenia:** Account-level: `total_spend >= $50 AND wasted_pct >= 25%`
**Priorytet:** HIGH (≥35%) / MEDIUM (≥25%)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację z podsumowaniem wasted spend na poziomie konta
2. Sprawdź `wasted_pct` w evidence
3. Sprawdź progi: 25% MEDIUM, 35% HIGH

Wynik testu: ___________

### 7.14 R13 — PMax Cannibalization
**Typ:** `PMAX_CANNIBALIZATION`
**Warunek wyzwolenia:** Search term w obu SEARCH i PMAX kampaniach, `pmax_cost > search_cost × 0.5`
**Priorytet:** HIGH (jeśli pmax_cost > $50) / MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Add exact match in Search or negative in PMax"
2. Sprawdź evidence z search term, campaign IDs, kosztami

Wynik testu: ___________

### 7.15 R15 — Device Anomaly
**Typ:** `DEVICE_ANOMALY`
**Warunek wyzwolenia:** `device_CPA > desktop_CPA × 2.0 AND device_spend >= $50`
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Apply bid adjustment or test device-specific landing pages"
2. Sprawdź device breakdown w evidence

Wynik testu: ___________

### 7.16 R16 — Geo Anomaly
**Typ:** `GEO_ANOMALY`
**Warunek wyzwolenia:** `geo_CPA > avg_CPA × 2.0 AND geo_spend >= $50`
**Priorytet:** LOW
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Apply geo bid adjustment"
2. Sprawdź lokalizację w evidence

Wynik testu: ___________

### 7.17 R17 — Budget Pacing
**Typ:** `BUDGET_PACING`
**Warunek wyzwolenia:**
- Overspend: `pacing_ratio > 1.2` → HIGH
- Underspend: `pacing_ratio < 0.8 AND month_pct > 20%` → MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendacje pacing — overspend lub underspend
2. Sprawdź progi i priorytety

Wynik testu: ___________

### 7.18 R18 — N-gram Negative
**Typ:** `NGRAM_NEGATIVE`
**Warunek wyzwolenia:** `ngram_cost >= $50 AND conversions == 0 AND ngram in >= 2 distinct search terms`
**Priorytet:** HIGH
**Executable:** NIE (INSIGHT_ONLY — manual review required)

Kroki testowania:
1. Sprawdź rekomendację → "Review manually before adding account-level negative"
2. Sprawdź n-gram details w evidence

Wynik testu: ___________

### 7.19 R19 — Single Ad Alert / Ad Group Health
**Typ:** `SINGLE_AD_ALERT`
**Warunek wyzwolenia:** Ad group ma < 2 reklamy
**Priorytet:** HIGH (0 ads) / LOW (1 ad)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Add minimum 2 RSA per ad group"

Wynik testu: ___________

### 7.20 R20 — Oversized Ad Group
**Typ:** `OVERSIZED_AD_GROUP`
**Warunek wyzwolenia:** Keywords > 20 w ad group
**Priorytet:** LOW
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Split into smaller, more focused ad groups"

Wynik testu: ___________

### 7.21 R21 — Zero Conv Ad Group
**Typ:** `ZERO_CONV_AD_GROUP`
**Warunek wyzwolenia:** `ad_group_spend >= $50 AND conversions == 0` (30-day lookback)
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Review keywords and ads; consider pause or restructure"

Wynik testu: ___________

### 7.22 R22 — Disapproved Ad Alert
**Typ:** `DISAPPROVED_AD_ALERT`
**Warunek wyzwolenia:** `ad.approval_status ∈ {DISAPPROVED, APPROVED_LIMITED}`
**Priorytet:** HIGH (DISAPPROVED) / MEDIUM (APPROVED_LIMITED)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Fix ad content or appeal Google's decision"

Wynik testu: ___________

### 7.23 R23 — Smart Bidding Data Starvation
**Typ:** `SMART_BIDDING_DATA_STARVATION`
**Warunek wyzwolenia:**
- tROAS: < 20 konwersji w 30 dniach
- tCPA: < 15 konwersji w 30 dniach
**Priorytet:** HIGH (< 50% progu) / MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Lower target, merge campaigns, or switch to Maximize Clicks"

Wynik testu: ___________

### 7.24 R24 — eCPC Deprecation
**Typ:** `ECPC_DEPRECATION`
**Warunek wyzwolenia:** `bidding_strategy == "ENHANCED_CPC"` (deprecated March 2025)
**Priorytet:** HIGH (always)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Migrate to Target CPA or Maximize Conversions"

Wynik testu: ___________

### 7.25 R25 — Scaling Opportunity
**Typ:** `SCALING_OPPORTUNITY`
**Warunek wyzwolenia:** Hero campaign (top 20% by value) AND `lost_IS >= 10%`
**Priorytet:** HIGH (incremental > $500) / MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Increase budget or improve Ad Rank"
2. Sprawdź `incremental_value` estimate w evidence

Wynik testu: ___________

### 7.26 R26 — Target Deviation Alert
**Typ:** `TARGET_DEVIATION_ALERT`
**Warunek wyzwolenia:** Smart Bidding campaign: `|actual - target| / target >= 20%`
**Priorytet:** HIGH (>50%) / MEDIUM (≥20%)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Check conversions/tracking or adjust target"
2. Sprawdź deviation % w evidence

Wynik testu: ___________

### 7.27 R27 — Learning Period Alert
**Typ:** `LEARNING_PERIOD_ALERT`
**Warunek wyzwolenia:** `"LEARNING" in primary_status_reasons`
- STUCK: > 14 dni → HIGH
- EXTENDED: > 7 dni → MEDIUM
- LEARNING: normalnie → LOW
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację z odpowiednim severity
2. Sprawdź czas w learning period

Wynik testu: ___________

### 7.28 R28 — Conversion Quality Alert
**Typ:** `CONVERSION_QUALITY_ALERT`
**Warunek wyzwolenia:**
- 2A: Sekundarne konwersje w metryce "Conversions" (nie powinny być)
- 2B: Primarne konwersje z value=0 przy tROAS
**Priorytet:** HIGH (always)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Exclude secondaries or set conversion values"

Wynik testu: ___________

### 7.29 R29 — Demographic Anomaly
**Typ:** `DEMOGRAPHIC_ANOMALY`
**Warunek wyzwolenia:** `segment_CPA > avg_CPA × 2.0 AND segment_spend >= $50`
**Priorytet:** HIGH (multiplier ≥ 3.0) / MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Exclude or reduce bids for underperforming segment"
2. Sprawdź age_range/gender w evidence

Wynik testu: ___________

### 7.30 R30 — PMax Channel Imbalance
**Typ:** `PMAX_CHANNEL_IMBALANCE`
**Warunek wyzwolenia:** PMax campaign: `cost_share > 40% AND conv_share < 20%` per ad network
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Check channel effectiveness; adjust asset group signals"
2. Sprawdź channel breakdown w evidence

Wynik testu: ___________

### 7.31 R31 — Asset Group Ad Strength
**Typ:** `ASSET_GROUP_AD_STRENGTH`
**Warunek wyzwolenia:** `ad_strength ∈ {POOR, AVERAGE} AND spend >= $50`
**Priorytet:** HIGH (POOR) / MEDIUM (AVERAGE)
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Add more headlines, descriptions, images"

Wynik testu: ___________

### 7.32 R32 — Audience Performance Anomaly
**Typ:** `AUDIENCE_PERFORMANCE_ANOMALY`
**Warunek wyzwolenia:** `audience_CPA > avg_CPA × 2.0 AND audience_spend >= $50`
**Priorytet:** MEDIUM
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Exclude or reduce bids for underperforming audience"

Wynik testu: ___________

### 7.33 R33 — Missing Extensions Alert
**Typ:** `MISSING_EXTENSIONS_ALERT`
**Warunek wyzwolenia:** Search campaigns: `sitelinks < 4 OR callouts < 3`
**Priorytet:** HIGH
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź rekomendację → "Add missing extensions to increase CTR by 10-15%"

Wynik testu: ___________

### 7.34 Analytics Alerts (ANALYTICS_ALERT)
**Typ:** `ANALYTICS_ALERT`
**Źródło:** ANALYTICS (nie PLAYBOOK_RULES)
**Warianty:**
- Above Average No Conversions: campaign spend > avg AND conv = 0
- CTR/Conversion Divergence: CTR up >10% but conv down >5%
- High Priority Queue: dużo HIGH-priority recommendations
- ROAS Outliers: campaign ROAS > 2× account average
**Executable:** NIE (INSIGHT_ONLY)

Kroki testowania:
1. Sprawdź obecność analytics alerts w widoku rekomendacji
2. Sprawdź treść alertów po polsku

Wynik testu: ___________

---

### Widok listy rekomendacji — elementy UI

### 7.35 Filtr: priorytet (ALL/HIGH/MEDIUM/LOW)
Kroki testowania:
1. Sprawdź pills filtrów: ALL, HIGH, MEDIUM, LOW
2. Kliknij HIGH → tylko HIGH priority widoczne
3. Kliknij ALL → wszystkie widoczne

Oczekiwany wynik: Filtrowanie po priorytecie działa.
Wynik testu: ___________

### 7.36 Sortowanie rekomendacji
Kroki testowania:
1. Sprawdź selector sortowania
2. Zmień sortowanie → sprawdź zmianę kolejności

Oczekiwany wynik: Sortowanie po priorytecie/typie/impact działa.
Wynik testu: ___________

### 7.37 Context outcome badge
Kroki testowania:
1. Sprawdź badge outcome: ACTION (zielony), INSIGHT_ONLY (niebieski), BLOCKED_BY_CONTEXT (czerwony)
2. Sprawdź kolorowanie i tekst

Oczekiwany wynik: Badge widoczny, odpowiednio kolorowy.
Wynik testu: ___________

### 7.38 Explanation (why_allowed / why_blocked)
Kroki testowania:
1. Rozwiń kartę rekomendacji
2. Sprawdź sekcje: `why_allowed`, `why_blocked`, `tradeoffs`, `risk_note`, `next_best_action`
3. Sprawdź czy teksty bazują na reason codes

Oczekiwany wynik: Wyjaśnienia widoczne, powiązane z reason codes.
Wynik testu: ___________

### 7.39 Disabled Apply dla INSIGHT_ONLY / BLOCKED_BY_CONTEXT
Kroki testowania:
1. Znajdź rekomendację INSIGHT_ONLY → przycisk Apply powinien być wyłączony
2. Znajdź rekomendację BLOCKED_BY_CONTEXT → przycisk Apply wyłączony
3. Kliknij disabled button → nic się nie dzieje

Oczekiwany wynik: Apply disabled, cursor not-allowed, brak akcji.
Wynik testu: ___________

### 7.40 Dismiss rekomendacji
Kroki testowania:
1. Kliknij Dismiss na dowolnej rekomendacji
2. Sprawdź czy status zmienił się na DISMISSED
3. Sprawdź czy rekomendacja zniknęła z listy aktywnych

Oczekiwany wynik: Rekomendacja odrzucona, niewidoczna.
Wynik testu: ___________

### 7.41 Role/protection/headroom chips
Kroki testowania:
1. Rozwiń kartę rekomendacji budżetowej
2. Sprawdź chips: campaign role, protection level, headroom info

Oczekiwany wynik: Chips renderują się poprawnie z informacjami kontekstowymi.
Wynik testu: ___________

### 7.42 Summary widget (ACTION vs BLOCKED_BY_CONTEXT counts)
Endpoint: `GET /recommendations/summary`

Kroki testowania:
1. Sprawdź widget podsumowania na górze strony
2. Sprawdź liczniki: łączne, ACTION, BLOCKED_BY_CONTEXT, INSIGHT_ONLY

Oczekiwany wynik: Liczniki poprawne, odpowiadają zawartości listy.
Wynik testu: ___________

### 7.43 Bulk Apply
Endpoint: `POST /recommendations/bulk-apply`

Kroki testowania:
1. Zaznacz kilka rekomendacji ACTION
2. Kliknij "Apply All"
3. Sprawdź czy wszystkie zostały zastosowane
4. Sprawdź kategorie quick-script: clean_waste, pause_burning, boost_winners, emergency_brake, add_negatives

Oczekiwany wynik: Bulk apply przetwarza batch. Wynik dla każdej rekomendacji w odpowiedzi.
Wynik testu: ___________

### 7.44 TYPE_CONFIG — polskie etykiety
Kroki testowania:
1. Sprawdź czy etykiety typów rekomendacji są po polsku
2. Sprawdź wszystkie 30+ typów

Oczekiwany wynik: Etykiety po polsku, czytelne.
Wynik testu: ___________

---

## SEKCJA 8 — Daily Audit (Codzienny Audyt)

### 8.1 Otwarcie Daily Audit — co widać
Strona `/daily-audit`.

Kroki testowania:
1. Przejdź na stronę Codzienny Audyt
2. Sprawdź ogólny status badge: Critical (czerwony) / Warning (żółty) / OK (zielony)
3. Sprawdź obecność wszystkich sekcji

Oczekiwany wynik: Strona ładuje się z pełnymi danymi. Status badge odzwierciedla stan konta.
Wynik testu: ___________

### 8.2 KPI Chips (Today vs Yesterday)
Chipy porównawcze.

Kroki testowania:
1. Sprawdź chipy: Wydatki, Kliknięcia, Konwersje
2. Sprawdź wartości dzisiaj i % zmiana vs wczoraj
3. Sprawdź kolorowanie (zielony = poprawa, czerwony = pogorszenie)

Oczekiwany wynik: 3 chipy z aktualnymi wartościami i deltą procentową.
Wynik testu: ___________

### 8.3 Health Score w Daily Audit
Gauge Health Score.

Kroki testowania:
1. Sprawdź gauge SVG ze score
2. Sprawdź czy wartość jest spójna z Dashboard health score

Oczekiwany wynik: Gauge renderuje się poprawnie.
Wynik testu: ___________

### 8.4 Unresolved anomaly alerts (last 24h)
Lista anomalii.

Kroki testowania:
1. Sprawdź sekcję anomalii (ikona kolorowa, severity badge)
2. Sprawdź czy wyświetla anomalie z ostatnich 24h

Oczekiwany wynik: Lista anomalii z opisami i severity.
Wynik testu: ___________

### 8.5 Disapproved / approved-limited ads
Reklamy z problemami.

Kroki testowania:
1. Sprawdź sekcję z reklamami odrzuconymi (ikona Ban, czerwona)
2. Sprawdź listę DISAPPROVED i APPROVED_LIMITED ads

Oczekiwany wynik: Lista reklam z problemami, jeśli istnieją.
Wynik testu: ___________

### 8.6 Budget-capped kampanie z poniżej-średnim CPA
Kampanie ograniczone budżetem.

Kroki testowania:
1. Sprawdź sekcję budget-capped (ikona DollarSign, żółta)
2. Sprawdź listę kampanii ograniczonych budżetem z dobrym CPA

Oczekiwany wynik: Kampanie warte skalowania wylistowane.
Wynik testu: ___________

### 8.7 Top wasted search terms (last 7 days)
Frazy marnujące budżet.

Kroki testowania:
1. Sprawdź sekcję wasted search terms
2. Sprawdź filtr: ≥3 clicks lub >$5 spend, 0 conversions
3. Sprawdź przycisk "View All Search Terms"

Oczekiwany wynik: Top 50 najgorzej wydajnych search terms z ostatnich 7 dni.
Wynik testu: ___________

### 8.8 Pending recommendations summary
Podsumowanie rekomendacji.

Kroki testowania:
1. Sprawdź sekcję pending recommendations
2. Sprawdź total + top 5 by priority
3. Sprawdź przycisk "View All Recommendations"

Oczekiwany wynik: Podsumowanie oczekujących rekomendacji.
Wynik testu: ___________

### 8.9 Quick Optimization Scripts
Szybkie skrypty optymalizacyjne.

Kroki testowania:
1. Sprawdź 4 przyciski: Clean Waste, Pause Burning, Boost Winners, Emergency Brake
2. Kliknij każdy → sprawdź czy bulk-apply się uruchamia
3. Sprawdź kolory ikon (czerwony, żółty, zielony, niebezpieczeństwo)

Oczekiwany wynik: Przyciski uruchamiają odpowiednie kategorie bulk-apply.
Wynik testu: ___________

### 8.10 Budget Pacing Table
Tabela pacing budżetowego.

Kroki testowania:
1. Sprawdź tabelę z kampaniami i progress bar pacing
2. Sprawdź kolumny: kampania, budżet, wydatek, % pacing
3. Sprawdź kolorowanie progress bar

Oczekiwany wynik: Tabela z aktualnymi danymi pacing i progress bar.
Wynik testu: ___________

---

## SEKCJA 9 — Negative Keywords (backend + UI w Keywords)

### 9.1 Lista negative keywords per klient (backend)
Endpoint: `GET /api/v1/negative-keywords/`

Kroki testowania:
1. Wywołaj endpoint z `client_id`
2. Sprawdź odpowiedź: lista negative keywords z `criterion_kind`, `negative_scope`, `source`

Oczekiwany wynik: JSON z listą negative keywords.
Wynik testu: ___________

### 9.2 Tworzenie negative keywords (backend)
Endpoint: `POST /api/v1/negative-keywords/`

Kroki testowania:
1. Wyślij POST z keyword text, match type, scope
2. Sprawdź czy keyword został utworzony

Oczekiwany wynik: Negative keyword utworzony, zwraca ID.
Wynik testu: ___________

### 9.3 Usuwanie negative keyword (backend)
Endpoint: `DELETE /api/v1/negative-keywords/{id}`

Kroki testowania:
1. Wyślij DELETE
2. Sprawdź soft-delete (keyword nadal w DB, ale niewidoczny)

Oczekiwany wynik: Negative keyword soft-deleted.
Wynik testu: ___________

### 9.4 UI negative keywords — patrz Sekcja 5.11-5.19
(Testy UI dla negative keywords opisane w sekcji Keywords)
Wynik testu: ___________

---

## SEKCJA 10 — Optymalizacja (SearchOptimization — 25 narzędzi analitycznych)

### 10.1 Device Breakdown (CPA per urządzenie)
Endpoint: `GET /analytics/device-breakdown`

Kroki testowania:
1. Przejdź na stronę Optymalizacja (`/search-optimization`)
2. Znajdź sekcję Device Breakdown
3. Sprawdź dane per urządzenie: Desktop, Mobile, Tablet
4. Sprawdź metryki: clicks, impressions, cost, conversions, CPA

Oczekiwany wynik: Tabela/wykres z podziałem per device.
Wynik testu: ___________

### 10.2 Geo Breakdown (CPA per lokalizacja)
Endpoint: `GET /analytics/geo-breakdown`

Kroki testowania:
1. Sprawdź sekcję Geo Breakdown
2. Sprawdź top 20 miast z metrykami
3. Sprawdź CPA per lokalizacja

Oczekiwany wynik: Tabela z top lokalizacjami i CPA.
Wynik testu: ___________

### 10.3 Budget Pacing view
Endpoint: `GET /analytics/budget-pacing`

Kroki testowania:
1. Sprawdź sekcję Budget Pacing
2. Sprawdź per-campaign: budżet, wydatek, pacing ratio

Oczekiwany wynik: Dane pacing z progress bar per kampania.
Wynik testu: ___________

### 10.4 N-gram Analysis
Endpoint: `GET /analytics/ngram-analysis`

Kroki testowania:
1. Sprawdź sekcję N-gram Analysis
2. Sprawdź n-gramy z metrykami (cost, clicks, conversions)
3. Sprawdź filtr n-gram size (1, 2, 3)

Oczekiwany wynik: Tabela n-gramów z agregatami.
Wynik testu: ___________

### 10.5 Keyword Expansion suggestions
Endpoint: `GET /analytics/keyword-expansion`

Kroki testowania:
1. Sprawdź sekcję Keyword Expansion
2. Sprawdź sugestie: search term, clicks, conversions, suggested match type

Oczekiwany wynik: Lista sugestii nowych keywords.
Wynik testu: ___________

### 10.6 Landing Page Analysis
Endpoint: `GET /analytics/landing-pages`

Kroki testowania:
1. Sprawdź sekcję Landing Pages
2. Sprawdź metryki per landing page URL

Oczekiwany wynik: Tabela z URL i metrykami.
Wynik testu: ___________

### 10.7 Conversion Health
Endpoint: `GET /analytics/conversion-health`

Kroki testowania:
1. Sprawdź sekcję Conversion Health
2. Sprawdź audyt konwersji per kampania

Oczekiwany wynik: Audyt z flagami problemów.
Wynik testu: ___________

### 10.8 Search Term Trends
Endpoint: `GET /analytics/search-term-trends`

Kroki testowania:
1. Sprawdź sekcję Search Term Trends
2. Sprawdź rising, declining, new terms
3. Sprawdź reakcję na zmianę zakresu dat (GlobalFilterBar)

Oczekiwany wynik: Lista trendów search terms z kierunkami zmian.
Wynik testu: ___________

### 10.9 Close Variant Analysis
Endpoint: `GET /analytics/close-variants`

Kroki testowania:
1. Sprawdź sekcję Close Variants
2. Sprawdź search terms vs exact keywords distance scoring

Oczekiwany wynik: Analiza bliskich wariantów z scoring.
Wynik testu: ___________

### 10.10 Impression Share Trends
Endpoint: `GET /analytics/impression-share`

Kroki testowania:
1. Sprawdź sekcję Impression Share
2. Sprawdź dzienne metryki IS dla SEARCH campaigns

Oczekiwany wynik: Wykres/tabela IS z danymi dziennymi.
Wynik testu: ___________

### 10.11 Dayparting (Day of Week)
Endpoint: `GET /analytics/dayparting`

Kroki testowania:
1. Sprawdź sekcję Dayparting
2. Sprawdź metryki per dzień tygodnia

Oczekiwany wynik: Tabela/heatmap z danymi per dzień.
Wynik testu: ___________

### 10.12 Hourly Dayparting
Endpoint: `GET /analytics/hourly-dayparting`

Kroki testowania:
1. Sprawdź sekcję Hourly Dayparting
2. Sprawdź metryki per godzina dnia

Oczekiwany wynik: Wykres/tabela z danymi per godzina.
Wynik testu: ___________

### 10.13 RSA Analysis
Endpoint: `GET /analytics/rsa-analysis`

Kroki testowania:
1. Sprawdź sekcję RSA Analysis
2. Sprawdź performance per ad group

Oczekiwany wynik: Analiza RSA per ad group.
Wynik testu: ___________

### 10.14 Match Type Analysis
Endpoint: `GET /analytics/match-type-analysis`

Kroki testowania:
1. Sprawdź sekcję Match Type Analysis
2. Sprawdź porównanie Broad vs Phrase vs Exact

Oczekiwany wynik: Porównanie metryk per match type.
Wynik testu: ___________

### 10.15 Wasted Spend
Endpoint: `GET /analytics/wasted-spend`

Kroki testowania:
1. Sprawdź sekcję Wasted Spend
2. Sprawdź breakdown: keywords, search terms, ads z 0 konwersjami
3. Sprawdź łączną wartość waste

Oczekiwany wynik: Podsumowanie wasted spend z detalami.
Wynik testu: ___________

### 10.16 Account Structure Audit
Endpoint: `GET /analytics/account-structure`

Kroki testowania:
1. Sprawdź sekcję Account Structure
2. Sprawdź issues: cannibalization, oversized groups, match mixing

Oczekiwany wynik: Lista problemów strukturalnych.
Wynik testu: ___________

### 10.17 Bidding Advisor
Endpoint: `GET /analytics/bidding-advisor`

Kroki testowania:
1. Sprawdź sekcję Bidding Advisor
2. Sprawdź rekomendację strategii per kampania

Oczekiwany wynik: Sugerowana strategia biddingu per kampania.
Wynik testu: ___________

### 10.18 Smart Bidding Health
Endpoint: `GET /analytics/smart-bidding-health`

Kroki testowania:
1. Sprawdź sekcję Smart Bidding Health
2. Sprawdź czy kampanie Smart Bidding mają wystarczającą liczbę konwersji

Oczekiwany wynik: Health check per kampania Smart Bidding.
Wynik testu: ___________

### 10.19 Target vs Actual (CPA/ROAS)
Endpoint: `GET /analytics/target-vs-actual`

Kroki testowania:
1. Sprawdź sekcję Target vs Actual
2. Sprawdź porównanie target CPA vs actual CPA per kampania
3. Sprawdź verdict: ON_TARGET / TOO_AGGRESSIVE / TOO_LOOSE

Oczekiwany wynik: Tabela z porównaniem target/actual i verdict.
Wynik testu: ___________

### 10.20 Pareto Analysis (80/20)
Endpoint: `GET /analytics/pareto-analysis`

Kroki testowania:
1. Sprawdź sekcję Pareto Analysis
2. Sprawdź campaigns i keywords generujące 80% wartości
3. Sprawdź flagi: HERO / MAIN / TAIL

Oczekiwany wynik: Analiza Pareto z flagami.
Wynik testu: ___________

### 10.21 Scaling Opportunities
Endpoint: `GET /analytics/scaling-opportunities`

Kroki testowania:
1. Sprawdź sekcję Scaling Opportunities
2. Sprawdź hero campaigns z IS headroom

Oczekiwany wynik: Lista kampanii wart skalowania.
Wynik testu: ___________

### 10.22 Demographics (Age/Gender)
Endpoint: `GET /analytics/demographics`

Kroki testowania:
1. Sprawdź sekcję Demographics
2. Sprawdź breakdown: age range, gender
3. Sprawdź CPA anomaly flags

Oczekiwany wynik: Tabela z danymi demograficznymi i anomaliami.
Wynik testu: ___________

### 10.23 PMax Channels
Endpoint: `GET /analytics/pmax-channels`

Kroki testowania:
1. Sprawdź sekcję PMax Channels
2. Sprawdź breakdown: Search, Display, YouTube, Gmail

Oczekiwany wynik: Podział metryk per kanał PMax.
Wynik testu: ___________

### 10.24 Asset Group Performance
Endpoint: `GET /analytics/asset-group-performance`

Kroki testowania:
1. Sprawdź sekcję Asset Groups
2. Sprawdź metryki per asset group + ad_strength + asset counts

Oczekiwany wynik: Tabela asset group z danymi performance i ad strength.
Wynik testu: ___________

### 10.25 PMax Search Themes
Endpoint: `GET /analytics/pmax-search-themes`

Kroki testowania:
1. Sprawdź sekcję PMax Search Themes
2. Sprawdź search themes per asset group

Oczekiwany wynik: Lista tematów wyszukiwania PMax.
Wynik testu: ___________

### 10.26 Audience Performance
Endpoint: `GET /analytics/audience-performance`

Kroki testowania:
1. Sprawdź sekcję Audience Performance
2. Sprawdź metryki per audience segment + CPA anomaly flags

Oczekiwany wynik: Tabela audience z metrykami i flagami.
Wynik testu: ___________

### 10.27 Missing Extensions
Endpoint: `GET /analytics/missing-extensions`

Kroki testowania:
1. Sprawdź sekcję Missing Extensions
2. Sprawdź audit per kampania: sitelinks, callouts, snippets

Oczekiwany wynik: Lista kampanii z brakującymi rozszerzeniami.
Wynik testu: ___________

### 10.28 Extension Performance
Endpoint: `GET /analytics/extension-performance`

Kroki testowania:
1. Sprawdź sekcję Extension Performance
2. Sprawdź metryki per typ rozszerzenia

Oczekiwany wynik: Performance per extension type.
Wynik testu: ___________

---

## SEKCJA 11 — Wpływ Zmian (Change Impact)

### 11.1 Lista wykonanych akcji z datami
Endpoint: `GET /analytics/change-impact`

Kroki testowania:
1. Sprawdź sekcję Change Impact (w SearchOptimization lub ActionHistory)
2. Sprawdź listę akcji z datami

Oczekiwany wynik: Lista akcji z timestampami.
Wynik testu: ___________

### 11.2 Delta KPI: before vs after (7 dni)
Porównanie 7 dni przed i 7 dni po akcji.

Kroki testowania:
1. Sprawdź per-action delty: cost, clicks, conversions, CPA
2. Sprawdź poprawność obliczeń

Oczekiwany wynik: Tabela z before/after/delta per metryka.
Wynik testu: ___________

### 11.3 Verdict: POSITIVE / NEGATIVE / NEUTRAL
Ocena wpływu.

Kroki testowania:
1. Sprawdź verdict per akcja
2. POSITIVE = poprawa (zielony), NEGATIVE = pogorszenie (czerwony), NEUTRAL (szary)

Oczekiwany wynik: Verdict kolorowy, odpowiada faktycznej zmianie.
Wynik testu: ___________

### 11.4 Akcje zbyt świeże (< 7 dni) — oznaczenie
Akcje bez wystarczających danych post-change.

Kroki testowania:
1. Sprawdź czy akcje nowsze niż 7 dni mają oznaczenie "zbyt świeże"
2. Sprawdź brak verdict dla takich akcji

Oczekiwany wynik: Oznaczenie widoczne, brak misleading verdict.
Wynik testu: ___________

### 11.5 Bid Strategy Impact
Endpoint: `GET /analytics/bid-strategy-impact`

Kroki testowania:
1. Sprawdź wpływ zmian strategii biddingu (14d before/after)
2. Sprawdź metryki z ChangeEvent records

Oczekiwany wynik: Analiza impact zmian strategii.
Wynik testu: ___________

---

## SEKCJA 12 — Pareto / 80-20 Analysis

### 12.1 Pareto per kampania (konwersje)
Endpoint: `GET /analytics/pareto-analysis`

Kroki testowania:
1. Sprawdź ranking kampanii wg % udziału w konwersjach
2. Sprawdź cumulative %

Oczekiwany wynik: Kampanie posortowane od najważniejszych, z cumulative %.
Wynik testu: ___________

### 12.2 Pareto per keyword
Podobna analiza na poziomie keywords.

Kroki testowania:
1. Sprawdź ranking keywords wg % udziału w wartości
2. Sprawdź cumulative %

Oczekiwany wynik: Keywords posortowane, cumulative %.
Wynik testu: ___________

### 12.3 Flagi: HERO / MAIN / TAIL
Segmentacja kampanii/keywords.

Kroki testowania:
1. Sprawdź flagi: HERO (top 20% value), MAIN (next 30%), TAIL (bottom 50%)
2. Sprawdź kolorowanie flag

Oczekiwany wynik: Flagi widoczne, odpowiadają rzeczywistej dystrybucji.
Wynik testu: ___________

### 12.4 Alert: hero kampania ograniczona budżetem
Kombinacja Pareto + IS.

Kroki testowania:
1. Sprawdź czy hero kampanie z dużym lost_IS mają alert
2. Sprawdź link do Scaling Opportunities

Oczekiwany wynik: Alert widoczny dla hero campaigns z headroom.
Wynik testu: ___________

---

## SEKCJA 13 — Bid Strategy Health

### 13.1 Lista kampanii z Smart Bidding
Endpoint: `GET /analytics/smart-bidding-health`

Kroki testowania:
1. Sprawdź listę kampanii używających Smart Bidding
2. Sprawdź typy strategii: TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, MAXIMIZE_CONVERSION_VALUE

Oczekiwany wynik: Lista kampanii z typem strategii.
Wynik testu: ___________

### 13.2 Target CPA vs Actual CPA per kampania
Endpoint: `GET /analytics/target-vs-actual`

Kroki testowania:
1. Sprawdź porównanie target vs actual CPA
2. Sprawdź % deviation

Oczekiwany wynik: Tabela z target, actual, deviation %.
Wynik testu: ___________

### 13.3 Target ROAS vs Actual ROAS
Sprawdź analogicznie dla ROAS.

Kroki testowania:
1. Sprawdź porównanie target vs actual ROAS
2. Sprawdź % deviation

Oczekiwany wynik: Tabela z target, actual, deviation %.
Wynik testu: ___________

### 13.4 Verdict: ON_TARGET / TOO_AGGRESSIVE / TOO_LOOSE
Ocena strategii.

Kroki testowania:
1. Sprawdź verdict per kampania
2. ON_TARGET (zielony), TOO_AGGRESSIVE (czerwony), TOO_LOOSE (żółty)

Oczekiwany wynik: Verdict odpowiada deviation level.
Wynik testu: ___________

### 13.5 Alert: kampania nie dowozi targetu (>14 dni)
Long-term underperformance.

Kroki testowania:
1. Sprawdź alerty dla kampanii z deviation > 14 dni

Oczekiwany wynik: Alert z sugestią korekty targetu.
Wynik testu: ___________

### 13.6 Alert: eCPC deprecated
Endpoint: patrz R24 (ECPC_DEPRECATION)

Kroki testowania:
1. Sprawdź alerty eCPC w recommendations
2. Sprawdź priorytet HIGH

Oczekiwany wynik: Alert o przestarzałej strategii.
Wynik testu: ___________

### 13.7 Learning Status
Endpoint: `GET /analytics/learning-status`

Kroki testowania:
1. Sprawdź kampanie w fazie learning
2. Sprawdź czas w learning period
3. Sprawdź status: LEARNING / EXTENDED / STUCK

Oczekiwany wynik: Lista kampanii z learning status.
Wynik testu: ___________

### 13.8 Portfolio Health
Endpoint: `GET /analytics/portfolio-health`

Kroki testowania:
1. Sprawdź health portfolio bid strategies
2. Sprawdź kampanie zgrupowane w portfolio

Oczekiwany wynik: Analiza health per portfolio strategy.
Wynik testu: ___________

### 13.9 Bid Strategy Report — daily time series
Endpoint: `GET /analytics/bid-strategy-report`

Kroki testowania:
1. Sprawdź dzienną serię target vs actual CPA/ROAS
2. Sprawdź wykres timeline

Oczekiwany wynik: Dane dzienne z target vs actual.
Wynik testu: ___________

---

## SEKCJA 14 — Monitoring & Anomalie

### 14.1 Lista anomalii (Alerty tab)
Strona `/alerts`.

Kroki testowania:
1. Przejdź na stronę Monitoring
2. Sprawdź zakładkę "Alerty"
3. Sprawdź sub-taby: Nierozwiązane | Rozwiązane
4. Sprawdź listę alertów z severity badge'ami

Oczekiwany wynik: Lista alertów z badges HIGH/MEDIUM/LOW.
Wynik testu: ___________

### 14.2 Resolve anomalii
Rozwiązywanie alertu.

Kroki testowania:
1. Kliknij "Rozwiąż" (CheckCircle icon) przy alercie
2. Sprawdź czy alert przeniósł się do "Rozwiązane"
3. Sprawdź `POST /analytics/anomalies/{id}/resolve`

Oczekiwany wynik: Alert przeniesiony na listę rozwiązanych.
Wynik testu: ___________

### 14.3 Anomalie z-score tab
Zakładka z statystycznym wykrywaniem anomalii.

Kroki testowania:
1. Przejdź na zakładkę "Anomalie (z-score)"
2. Sprawdź metric pills: Cost, Clicks, Impressions, Conversions, CTR
3. Sprawdź threshold selector: 1.5σ, 2.0σ, 2.5σ, 3.0σ
4. Sprawdź period selector: 30d, 60d, 90d

Oczekiwany wynik: Wykrywanie anomalii z wybranym progiem i okresem.
Wynik testu: ___________

### 14.4 Stats Cards anomalii
Karty statystyk.

Kroki testowania:
1. Sprawdź karty: Number of anomalies, Mean value, Std deviation
2. Sprawdź czy wartości reagują na zmianę metryk/progu

Oczekiwany wynik: Stats cards aktualizują się przy zmianie parametrów.
Wynik testu: ___________

### 14.5 Tabela anomalii
Szczegółowa tabela.

Kroki testowania:
1. Sprawdź kolumny: Date, Campaign, Value, Z-score, Type (Spike/Dip)
2. Sprawdź kolorowanie z-score wg severity
3. Sprawdź ikony Spike (TrendingUp) / Dip (TrendingDown)

Oczekiwany wynik: Tabela z pełnymi danymi anomalii.
Wynik testu: ___________

### 14.6 Wykrywanie anomalii (trigger)
Endpoint: `POST /analytics/detect`

Kroki testowania:
1. Kliknij przycisk wykrywania (jeśli dostępny w UI)
2. Sprawdź czy nowe anomalie są tworzone
3. Sprawdź deduplikacja (nie tworzy duplikatów)

Oczekiwany wynik: Nowe anomalie wykryte, bez duplikatów.
Wynik testu: ___________

### 14.7 Alert badge w sidebarze
Licznik alertów na ikonie Monitoring.

Kroki testowania:
1. Sprawdź badge (czerwona pill) przy ikonie Monitoring w sidebarze
2. Sprawdź czy liczba odpowiada unresolvedoom
3. Po resolve → sprawdź czy badge się aktualizuje

Oczekiwany wynik: Badge z liczbą nierozwiązanych alertów.
Wynik testu: ___________

---

## SEKCJA 15 — Forecast (Prognozowanie)

### 15.1 Otwarcie Forecast
Strona `/forecast`.

Kroki testowania:
1. Przejdź na stronę Prognozowanie
2. Sprawdź obecność selektorów i wykresu

Oczekiwany wynik: Strona ładuje się z domyślną kampanią i metryką.
Wynik testu: ___________

### 15.2 Wybór kampanii
Dropdown kampanii.

Kroki testowania:
1. Sprawdź dropdown z listą kampanii
2. Zmień kampanię → dane i wykres się odświeżają

Oczekiwany wynik: Wykres i KPI aktualizują się dla wybranej kampanii.
Wynik testu: ___________

### 15.3 Wybór metryki
Pills: Cost, Clicks, Conversions, CTR.

Kroki testowania:
1. Kliknij każdy pill metryki
2. Sprawdź czy wykres i KPI cards się zmieniają

Oczekiwany wynik: Wykres odzwierciedla wybraną metrykę.
Wynik testu: ___________

### 15.4 KPI Cards
4 karty KPI nad wykresem.

Kroki testowania:
1. Sprawdź kartę Trend (7 days) z ikoną TrendingUp/Down
2. Sprawdź kartę Forecast (average daily value)
3. Sprawdź kartę Model Confidence (R²) z badge HIGH/MEDIUM/LOW
4. Sprawdź kartę Slope (growth per day)

Oczekiwany wynik: 4 karty z aktualnymi wartościami i badge'ami.
Wynik testu: ___________

### 15.5 Wykres prognozy
ComposedChart z Recharts.

Kroki testowania:
1. Sprawdź linię historyczną (niebieska)
2. Sprawdź linię prognozy (zielona, przerywana)
3. Sprawdź obszar confidence interval (zielony, shaded)
4. Sprawdź tooltip po najechaniu
5. Sprawdź oś X (daty MM-DD) i oś Y (wartości metryki)

Oczekiwany wynik: Wykres renderuje się poprawnie z 3 warstwami.
Wynik testu: ___________

### 15.6 Aliasy metryk forecast
Backend aliasy: `cost` → `cost_micros`, `cpc` → `avg_cpc_micros`.

Kroki testowania:
1. Wybierz metrykę "Cost" → sprawdź czy wartości są w normalnych jednostkach (nie mikro)
2. Sprawdź poprawne przeliczenie z micros

Oczekiwany wynik: Wartości w czytelnych jednostkach walutowych.
Wynik testu: ___________

---

## SEKCJA 16 — Raporty AI (Agent)

### 16.1 Status Claude CLI
Sprawdzenie dostępności.

Kroki testowania:
1. Przejdź na stronę Raport AI (`/agent`)
2. Sprawdź status badge: "Claude dostępny" (zielony) lub "Claude niedostępny" (czerwony)
3. Sprawdź `GET /agent/status` → wersja CLI

Oczekiwany wynik: Badge odzwierciedla faktyczną dostępność Claude CLI.
Wynik testu: ___________

### 16.2 Generowanie raportu tygodniowego
Quick action: Weekly Report.

Kroki testowania:
1. Kliknij przycisk "Raport tygodniowy" (FileText icon)
2. Obserwuj streaming SSE odpowiedzi
3. Sprawdź rendering Markdown

Oczekiwany wynik: Raport generuje się w SSE, treść pojawia się na bieżąco.
Wynik testu: ___________

### 16.3 Generowanie raportu kampanii
Quick action: Campaign Analysis.

Kroki testowania:
1. Kliknij "Analiza kampanii"
2. Sprawdź kontekst: metryki kampanii w prompcie

Oczekiwany wynik: Raport z analizą kampanii.
Wynik testu: ___________

### 16.4 Generowanie raportu budżetu
Quick action: Budget Analysis.

Kroki testowania:
1. Kliknij "Analiza budżetu"
2. Sprawdź treść raportu

Oczekiwany wynik: Raport budżetowy z pacing i optymalizacjami.
Wynik testu: ___________

### 16.5 Generowanie raportu keywords
Quick action: Keywords.

Kroki testowania:
1. Kliknij "Słowa kluczowe"
2. Sprawdź treść raportu

Oczekiwany wynik: Raport z analizą keywords.
Wynik testu: ___________

### 16.6 Generowanie raportu search terms
Quick action: Search Terms.

Kroki testowania:
1. Kliknij "Wyszukiwane frazy"
2. Sprawdź treść raportu

Oczekiwany wynik: Raport z analizą search terms.
Wynik testu: ___________

### 16.7 Generowanie raportu alertów
Quick action: Alerts & Anomalies.

Kroki testowania:
1. Kliknij "Alerty i anomalie"
2. Sprawdź treść raportu

Oczekiwany wynik: Raport z alertami i anomaliami.
Wynik testu: ___________

### 16.8 Freeform zapytanie
Textarea z dowolnym pytaniem.

Kroki testowania:
1. Wpisz własne pytanie w textarea
2. Kliknij Send
3. Sprawdź odpowiedź AI

Oczekiwany wynik: AI odpowiada na dowolne pytanie z kontekstem danych klienta.
Wynik testu: ___________

### 16.9 SSE streaming — czy tekst pojawia się na bieżąco
Sprawdzenie streaming.

Kroki testowania:
1. Generuj dowolny raport
2. Obserwuj czy tekst pojawia się słowo po słowie (streaming)
3. Sprawdź spinner/indicator podczas generowania

Oczekiwany wynik: Tekst streamuje się na żywo, nie pojawia się cały naraz.
Wynik testu: ___________

### 16.10 Markdown rendering w odpowiedzi
Formatowanie odpowiedzi.

Kroki testowania:
1. Sprawdź czy odpowiedź renderuje Markdown (nagłówki, listy, bold, tabele)
2. Sprawdź obsługę tabel GFM (GitHub Flavored Markdown)

Oczekiwany wynik: Markdown renderowany poprawnie (react-markdown + remark-gfm).
Wynik testu: ___________

### 16.11 Token usage badge
Informacje o zużyciu tokenów.

Kroki testowania:
1. Po wygenerowaniu raportu sprawdź badge z: input tokens, output tokens, cache, cost, duration
2. Sprawdź model name badge

Oczekiwany wynik: Badge z informacjami o zużyciu.
Wynik testu: ___________

### 16.12 Single-flight lock (busy state)
Tylko jeden raport na raz.

Kroki testowania:
1. Uruchom generowanie raportu
2. Podczas generowania spróbuj uruchomić drugi → powinien dostać SSE error "busy"
3. Sprawdź graceful handling w UI

Oczekiwany wynik: Drugi request zwraca busy error z SSE event, UI informuje o zajętości.
Wynik testu: ___________

### 16.13 401 handling
Obsługa braku autoryzacji.

Kroki testowania:
1. Spróbuj generować raport bez sesji
2. Sprawdź czy `auth:unauthorized` event jest emitowany

Oczekiwany wynik: Przekierowanie do logowania lub komunikat o braku autoryzacji.
Wynik testu: ___________

---

## SEKCJA 17 — Raporty (Reports)

### 17.1 Lista zapisanych raportów
Strona `/reports`.

Kroki testowania:
1. Przejdź na stronę Raporty
2. Sprawdź listę zapisanych raportów (newest first)
3. Sprawdź kolumny: typ, data, status

Oczekiwany wynik: Lista raportów posortowana chronologicznie.
Wynik testu: ___________

### 17.2 Generowanie raportu miesięcznego
Endpoint: `POST /reports/generate?report_type=monthly`

Kroki testowania:
1. Uruchom generowanie raportu miesięcznego
2. Sprawdź SSE streaming odpowiedzi
3. Sprawdź zapisanie do DB

Oczekiwany wynik: Raport wygenerowany i zapisany, widoczny na liście.
Wynik testu: ___________

### 17.3 Generowanie raportu tygodniowego
Endpoint: `POST /reports/generate?report_type=weekly`

Kroki testowania:
1. Uruchom raport weekly (7-day window)
2. Sprawdź treść i dane

Oczekiwany wynik: Raport tygodniowy z danymi 7-dniowymi.
Wynik testu: ___________

### 17.4 Generowanie raportu health
Endpoint: `POST /reports/generate?report_type=health`

Kroki testowania:
1. Uruchom raport health (30-day audit)
2. Sprawdź sekcje: conversion health, quality scores, account structure

Oczekiwany wynik: Raport zdrowia konta z audytem.
Wynik testu: ___________

### 17.5 Szczegóły raportu
Endpoint: `GET /reports/{id}`

Kroki testowania:
1. Kliknij na raport → sprawdź widok szczegółowy
2. Sprawdź: KPI summary, campaign detail, change history, budget pacing
3. Sprawdź token usage badge (cost display)

Oczekiwany wynik: Pełne dane raportu z narracją AI i danymi.
Wynik testu: ___________

### 17.6 Status pills raportu
Badge statusu.

Kroki testowania:
1. Sprawdź badge GENERATED (zielony)
2. Sprawdź badge GENERATING (żółty/spinner)
3. Sprawdź badge FAILED (czerwony)

Oczekiwany wynik: Badge'e kolorowe, odpowiadające statusowi.
Wynik testu: ___________

---

## SEKCJA 18 — Action History (Historia akcji)

### 18.1 Lista wszystkich wykonanych akcji
Strona `/action-history`.

Kroki testowania:
1. Przejdź na stronę Historia akcji
2. Sprawdź timeline view (grouped by date)
3. Sprawdź pola: action icon, description, campaign, timestamp, impact delta

Oczekiwany wynik: Timeline z akcjami, posortowany chronologicznie.
Wynik testu: ___________

### 18.2 Filtrowanie po typie akcji
Dropdown action type.

Kroki testowania:
1. Wybierz typ akcji (np. PAUSE_KEYWORD) → sprawdź filtrowanie
2. Wybierz "Wszystkie" → pełna lista

Oczekiwany wynik: Lista filtruje się po wybranym typie.
Wynik testu: ___________

### 18.3 Filtrowanie po kampanii
Dropdown kampanii.

Kroki testowania:
1. Wybierz kampanię → sprawdź filtrowanie
2. Sprawdź czy endpointy `GET /actions/` respektują parametr

Oczekiwany wynik: Lista filtruje się po kampanii.
Wynik testu: ___________

### 18.4 Status akcji (completed / failed / reverted)
Badge statusu.

Kroki testowania:
1. Sprawdź badge'e: completed (zielony), failed (czerwony), reverted (szary)
2. Sprawdź kolorowanie

Oczekiwany wynik: Badge'e statusu widoczne.
Wynik testu: ___________

### 18.5 Revert akcji (rollback)
Cofanie akcji.

Kroki testowania:
1. Znajdź akcję z przyciskiem Revert (dostępny w ciągu 24h)
2. Kliknij Revert → potwierdź
3. Sprawdź czy status zmienił się na "reverted"
4. Sprawdź `POST /actions/revert/{id}`
5. **Uwaga:** ADD_NEGATIVE jest NIEREVERTABLE

Oczekiwany wynik: Akcja cofnięta, oryginalna wartość przywrócona.
Wynik testu: ___________

### 18.6 Expandowanie szczegółów akcji
Rozwijanie detali.

Kroki testowania:
1. Kliknij Expand na wpisie timeline
2. Sprawdź Change Impact View (before/after metrics table)
3. Sprawdź Strategy Impact View (metrics with colored changes)

Oczekiwany wynik: Rozwinięty widok z detalami akcji.
Wynik testu: ___________

### 18.7 Delta Pill
Pill z procentową zmianą.

Kroki testowania:
1. Sprawdź kolorowe pill z % zmianą (np. +15% zielony, -10% czerwony)
2. Sprawdź strzałki up/down

Oczekiwany wynik: Pill czytelny, kolorowy, z procentem.
Wynik testu: ___________

---

## SEKCJA 19 — Change History (Historia zmian Google Ads)

### 19.1 Lista zmian z Google Ads
Endpoint: `GET /api/v1/history/`

Kroki testowania:
1. Sprawdź listę change events z Google Ads
2. Sprawdź filtry (po typie, kampanii)

Oczekiwany wynik: Lista zmian z filtrami.
Wynik testu: ___________

### 19.2 Unified Timeline
Endpoint: `GET /api/v1/history/unified`

Kroki testowania:
1. Sprawdź unified timeline (merging action_log + change_event by timestamp)
2. Sprawdź chronologiczną kolejność

Oczekiwany wynik: Timeline z obu źródeł, posortowany chronologicznie.
Wynik testu: ___________

### 19.3 Filter values
Endpoint: `GET /api/v1/history/filters`

Kroki testowania:
1. Sprawdź zwrócone distinct filter values
2. Sprawdź czy dropdown values odpowiadają faktycznym danym

Oczekiwany wynik: Unikalne wartości do filtrów.
Wynik testu: ___________

---

## SEKCJA 20 — Ustawienia (Settings)

### 20.1 Informacje ogólne klienta
Strona `/settings`.

Kroki testowania:
1. Przejdź na Ustawienia
2. Sprawdź pola: nazwa klienta, branża, strona www, Google Customer ID (read-only), notatki
3. Edytuj nazwę → zapisz
4. Sprawdź `PATCH /clients/{id}`

Oczekiwany wynik: Formularz wyświetla aktualne dane. Zapis działa.
Wynik testu: ___________

### 20.2 Strategia i konkurencja
Sekcja strategii.

Kroki testowania:
1. Sprawdź pola: target audience, USP, competitors (tag pills)
2. Dodaj konkurenta (przycisk Plus) → sprawdź tag pill
3. Usuń konkurenta (ikona X na tag) → sprawdź usunięcie
4. Zapisz zmiany

Oczekiwany wynik: Tag pills dodają się i usuwają. Zapis działa.
Wynik testu: ___________

### 20.3 Reguły biznesowe
Limity biznesowe.

Kroki testowania:
1. Sprawdź pola: Min ROAS, Max daily budget USD
2. Zmień wartości → zapisz
3. Sprawdź czy rekomendacje respektują nowe limity

Oczekiwany wynik: Wartości zapisane, wpływają na engine rekomendacji.
Wynik testu: ___________

### 20.4 Limity bezpieczeństwa
Safety limits.

Kroki testowania:
1. Sprawdź pola: Max bid change %, Max budget change %, Min bid USD, Max bid USD, Max keyword pause %, Max negatives per day
2. Sprawdź unit indicators (%, $)
3. Zmień wartości → zapisz

Oczekiwany wynik: Limity zapisane z odpowiednimi jednostkami.
Wynik testu: ___________

### 20.5 Hard reset danych klienta
Usunięcie wszystkich danych runtime klienta.

Kroki testowania:
1. Przewiń do sekcji "Twardy reset danych klienta" (czerwona)
2. Wpisz nazwę klienta w pole potwierdzenia
3. Kliknij "Twardy reset" (czerwony przycisk z ShieldAlert)
4. Sprawdź `POST /clients/{id}/hard-reset`
5. Sprawdź czy dane (kampanie, keywords, metrics, recommendations) zostały usunięte
6. Sprawdź czy profil klienta (nazwa, credentials) zachowany

Oczekiwany wynik: Dane runtime usunięte. Profil klienta zachowany. Wymaga wpisania dokładnej nazwy klienta.
Wynik testu: ___________

### 20.6 Hard reset — zabezpieczenie (wpisanie nazwy)
Potwierdzenie wymagane.

Kroki testowania:
1. Wpisz błędną nazwę → przycisk powinien być disabled
2. Wpisz poprawną nazwę → przycisk aktywny
3. Kliknij bez wpisania → nic się nie dzieje

Oczekiwany wynik: Przycisk aktywny tylko po wpisaniu dokładnej nazwy klienta.
Wynik testu: ___________

---

## SEKCJA 21 — Klienci (Clients)

### 21.1 Lista klientów
Strona `/clients`.

Kroki testowania:
1. Przejdź na stronę Klienci
2. Sprawdź karty klientów: nazwa, Google Customer ID, last synced
3. Sprawdź aktywny klient (zielona kropka)

Oczekiwany wynik: Lista klientów z kartami.
Wynik testu: ___________

### 21.2 Discovery — pobranie klientów z MCC
Automatyczne odkrywanie kont.

Kroki testowania:
1. Kliknij "Pobierz wszystkich klientów" (Download icon)
2. Sprawdź czy klienci z MCC zostali dodani
3. Alternatywnie: wpisz Customer ID i kliknij Search

Oczekiwany wynik: Nowi klienci dodani z Google Ads API.
Wynik testu: ___________

### 21.3 Przełączanie między klientami
Zmiana aktywnego klienta.

Kroki testowania:
1. Kliknij na innego klienta → sprawdź czy sidebar update'uje aktywnego
2. Sprawdź czy dane na Dashboard/Campaigns/etc. odświeżają się
3. Użyj dropdown w sidebarze → sprawdź zmianę klienta

Oczekiwany wynik: Zmiana klienta odświeża wszystkie dane. Sidebar update'uje.
Wynik testu: ___________

### 21.4 Sync per klient
Przycisk Sync na karcie klienta.

Kroki testowania:
1. Kliknij Sync przy kliencie
2. Sprawdź spinner podczas sync
3. Sprawdź timestamp "last synced" po sync

Oczekiwany wynik: Sync uruchomiony, timestamp zaktualizowany.
Wynik testu: ___________

### 21.5 Tworzenie nowego klienta (backend only)
Endpoint: `POST /api/v1/clients`

Kroki testowania:
1. Wyślij POST z danymi nowego klienta
2. Sprawdź odpowiedź

Oczekiwany wynik: Klient utworzony, zwraca ID.
Wynik testu: ___________

### 21.6 Usuwanie klienta (backend only)
Endpoint: `DELETE /api/v1/clients/{id}`

Kroki testowania:
1. Wyślij DELETE
2. Sprawdź soft-delete

Oczekiwany wynik: Klient soft-deleted.
Wynik testu: ___________

---

## SEKCJA 22 — Multi-Account

### 22.1 Przełączanie między klientami
Kroki testowania:
1. Wybierz klienta A → sprawdź dane
2. Przełącz na klienta B → sprawdź czy dane się zmieniły
3. Przełącz z powrotem na A → dane A widoczne

Oczekiwany wynik: Dane odświeżają się przy każdej zmianie klienta.
Wynik testu: ___________

### 22.2 Czy GlobalFilterBar resetuje się przy zmianie klienta
Kroki testowania:
1. Ustaw filtr Campaign Type = SEARCH dla klienta A
2. Przełącz na klienta B
3. Sprawdź czy filtry się zresetowały

Oczekiwany wynik: Filtry powinny być niezależne od klienta lub się resetować.
Wynik testu: ___________

### 22.3 Sidebar — aktywny klient
Kroki testowania:
1. Sprawdź dropdown w sidebarze "Aktywny klient"
2. Sprawdź zieloną kropkę przy aktywnym kliencie
3. Zmień klienta → sprawdź update

Oczekiwany wynik: Sidebar zawsze wyświetla aktualnie wybranego klienta.
Wynik testu: ___________

---

## SEKCJA 23 — Bezpieczeństwo akcji

### 23.1 Confirmation modal przy nieodwracalnej akcji
Kroki testowania:
1. Apply rekomendacji PAUSE_KEYWORD → sprawdź modal potwierdzenia
2. Apply UPDATE_BID → sprawdź modal z nową wartością bidu
3. Sprawdź przyciski: Potwierdź / Anuluj

Oczekiwany wynik: Modal wyświetla szczegóły akcji i wymaga potwierdzenia.
Wynik testu: ___________

### 23.2 Rollback window (24h)
Kroki testowania:
1. Apply akcji → sprawdź przycisk Revert w Action History
2. Po 24h → przycisk Revert powinien być niedostępny
3. Wyjątek: ADD_NEGATIVE nigdy nie ma Revert

Oczekiwany wynik: Revert dostępny w ciągu 24h, potem zablokowany. ADD_NEGATIVE zawsze nierevertable.
Wynik testu: ___________

### 23.3 DEMO write lock
Kroki testowania:
1. Wybierz klienta DEMO (google_customer_id: 123-456-7890)
2. Spróbuj sync → sprawdź blokadę
3. Spróbuj apply recommendation → sprawdź blokadę
4. Spróbuj hard-reset → sprawdź blokadę
5. Spróbuj campaign role override → sprawdź blokadę
6. Sprawdź czy `allow_demo_write=true` odblokuje (per-request override)

Oczekiwany wynik: Wszystkie mutacje zablokowane dla DEMO. Override działa per-request.
Wynik testu: ___________

### 23.4 Dry-run mode
Kroki testowania:
1. Apply rekomendacji z `dry_run=true`
2. Sprawdź odpowiedź: symulacja bez wykonania
3. Sprawdź czy nic się nie zmieniło w danych

Oczekiwany wynik: Dry-run zwraca symulację wyniku bez faktycznej zmiany.
Wynik testu: ___________

---

## SEKCJA 24 — Dodatkowe funkcjonalności

### 24.1 Quality Score Audit
Strona `/quality-score`.

Kroki testowania:
1. Przejdź na stronę Wynik jakości
2. Sprawdź summary: Average QS, Low QS Count, High QS Count
3. Sprawdź wykres słupkowy (dystrybucja QS 1-10)
4. Sprawdź tabelę issues: keyword, QS badge, diagnostyka, rekomendacja
5. Sprawdź cel: średni QS > 7.0

Oczekiwany wynik: Pełny audyt Quality Score z wizualizacjami.
Wynik testu: ___________

### 24.2 Semantic Clusters
Strona `/semantic`.

Kroki testowania:
1. Przejdź na stronę Inteligencja (Klastry Semantyczne)
2. Sprawdź filtr kosztowy (pills: 0, >10, >50, >100 zł)
3. Sprawdź karty klastrów (rozwijalne)
4. Rozwiń klaster → sprawdź term pills z kosztem
5. Sprawdź ikona waste (AlertCircle czerwony) vs normal (Layers)

Oczekiwany wynik: Klastry semantyczne z danymi i filtrami.
Wynik testu: ___________

### 24.3 Conversion Quality Audit
Endpoint: `GET /analytics/conversion-quality`

Kroki testowania:
1. Sprawdź audyt konfiguracji konwersji
2. Sprawdź issues: secondary included, zero-value primaries

Oczekiwany wynik: Audyt z listą problemów konfiguracji konwersji.
Wynik testu: ___________

### 24.4 Ad Group Health
Endpoint: `GET /analytics/ad-group-health`

Kroki testowania:
1. Sprawdź health check: ad count, keyword count, zero-conversion groups
2. Sprawdź rekomendacje per ad group

Oczekiwany wynik: Lista ad groups z problemami strukturalnymi.
Wynik testu: ___________

### 24.5 Ads — lista reklam (backend only, częściowo w UI)
Endpoint: `GET /api/v1/ads/`

Kroki testowania:
1. Wywołaj endpoint z `client_id`
2. Sprawdź odpowiedź: lista reklam z danymi

Oczekiwany wynik: JSON z listą reklam.
Wynik testu: ___________

### 24.6 Ad Groups — lookup (backend only, dropdown support)
Endpoint: `GET /api/v1/ad-groups/`

Kroki testowania:
1. Wywołaj endpoint z `client_id` i opcjonalnie `campaign_id`
2. Sprawdź odpowiedź: lista ad groups

Oczekiwany wynik: Lista ad groups dla dropdownów.
Wynik testu: ___________

---

## SEKCJA 25 — Export danych

### 25.1 Export search terms
Endpoint: `GET /export/search-terms?format=xlsx`

Kroki testowania:
1. Kliknij Export Excel na stronie Search Terms
2. Sprawdź pobrany plik
3. Sprawdź format CSV (`format=csv`)

Oczekiwany wynik: Plik pobiera się z pełnymi danymi.
Wynik testu: ___________

### 25.2 Export keywords
Endpoint: `GET /export/keywords?format=xlsx`

Kroki testowania:
1. Kliknij Export na stronie Keywords
2. Sprawdź pobrany plik z kolumnami: keyword, campaign, ad_group, match_type, QS, metryki

Oczekiwany wynik: Plik z pełnymi danymi keywords + kontekst kampanii.
Wynik testu: ___________

### 25.3 Export metrics (backend only)
Endpoint: `GET /export/metrics`

Kroki testowania:
1. Wywołaj endpoint z campaign_id
2. Sprawdź pobrany plik z dziennymi metrykami

Oczekiwany wynik: Plik z daily metrics.
Wynik testu: ___________

### 25.4 Export recommendations (backend only)
Endpoint: `GET /export/recommendations`

Kroki testowania:
1. Wywołaj endpoint z client_id
2. Sprawdź pobrany plik z rekomendacjami

Oczekiwany wynik: Plik z rekomendacjami.
Wynik testu: ___________

---

## SEKCJA 26 — Correlation & Compare (backend only)

### 26.1 Correlation Matrix
Endpoint: `POST /analytics/correlation`

Kroki testowania:
1. Wyślij POST z danymi metryk
2. Sprawdź Pearson correlation matrix

Oczekiwany wynik: Matrix korelacji między metrykami.
Wynik testu: ___________

### 26.2 Compare Periods
Endpoint: `POST /analytics/compare-periods`

Kroki testowania:
1. Wyślij POST z dwoma okresami do porównania
2. Sprawdź delty metryk

Oczekiwany wynik: Porównanie dwóch okresów z deltami.
Wynik testu: ___________

---

## SEKCJA 27 — Edge Cases & Error Handling

### 27.1 Brak danych (nowy klient bez sync) — co widać
Kroki testowania:
1. Utwórz nowego klienta bez synca
2. Przejdź na Dashboard → sprawdź empty state
3. Przejdź na Campaigns → sprawdź pustą tabelę
4. Sprawdź czy brak crashy

Oczekiwany wynik: Empty state bez błędów. Czytelne komunikaty "brak danych".
Wynik testu: ___________

### 27.2 Błąd API Google Ads — komunikat błędu
Kroki testowania:
1. Symuluj błąd API (nieprawidłowy token)
2. Sprawdź komunikat błędu w UI
3. Sprawdź czy nie ma raw stack trace

Oczekiwany wynik: Czytelny komunikat błędu po polsku, bez technical details.
Wynik testu: ___________

### 27.3 Timeout sync — co się dzieje
Kroki testowania:
1. Symuluj timeout (np. wolna sieć)
2. Sprawdź zachowanie UI podczas długiego sync
3. Sprawdź per-phase error tracking

Oczekiwany wynik: UI nie zamraża się. Timeout fazy nie blokuje innych faz.
Wynik testu: ___________

### 27.4 Pusta lista rekomendacji — empty state
Kroki testowania:
1. Znajdź klienta bez rekomendacji
2. Sprawdź empty state na stronie Rekomendacje

Oczekiwany wynik: Czytelny empty state "Brak rekomendacji".
Wynik testu: ___________

### 27.5 Filtr dający 0 wyników — empty state
Kroki testowania:
1. Ustaw filtry zwracające 0 wyników (np. Campaign Type = SHOPPING gdy brak takich)
2. Sprawdź empty state

Oczekiwany wynik: Pusty widok z informacją "Brak wyników" (nie broken UI).
Wynik testu: ___________

### 27.6 Bardzo długie nazwy kampanii — czy UI się nie psuje
Kroki testowania:
1. Utwórz kampanię z bardzo długą nazwą (100+ znaków)
2. Sprawdź tabele kampanii, rekomendacji, search terms
3. Sprawdź czy tekst jest truncated / overflow jest obsługiwany

Oczekiwany wynik: Długie nazwy nie łamią layoutu. Truncation z "..." gdzie potrzebne.
Wynik testu: ___________

### 27.7 Polskie znaki diakrytyczne — poprawność wyświetlania
Kroki testowania:
1. Sprawdź czy ą, ę, ó, ś, ź, ż, ć, ń, ł wyświetlają się poprawnie
2. Sprawdź etykiety UI (sidebar, headers, buttons, tooltips)
3. Sprawdź dane klienta z polskimi znakami
4. Sprawdź rekomendacje — polskie opisy

Oczekiwany wynik: Wszystkie polskie znaki wyświetlają się poprawnie, brak mojibake (???, â€™).
Wynik testu: ___________

### 27.8 Responsywność mobilna
Kroki testowania:
1. Zmniejsz okno przeglądarki
2. Sprawdź hamburger menu (ikona Menu) na mobile
3. Sprawdź sidebar jako overlay
4. Sprawdź nawigację mobilną

Oczekiwany wynik: Sidebar chowa się w hamburger menu. Nawigacja działa na mobile.
Wynik testu: ___________

### 27.9 Health endpoint
Endpoint: `GET /health`

Kroki testowania:
1. Wywołaj endpoint
2. Sprawdź: `status: "ok"`, `version: "0.1.0"`, `env`

Oczekiwany wynik: JSON z informacjami o stanie aplikacji.
Wynik testu: ___________

---

## PODSUMOWANIE TESTOWANIA

| Sekcja | Przetestowano | OK | Bugi | Uwagi |
|--------|--------------|-----|------|-------|
| 1. Onboarding & Konfiguracja | | | | |
| 2. Synchronizacja danych | | | | |
| 3. Dashboard | | | | |
| 4. Kampanie | | | | |
| 5. Słowa kluczowe | | | | |
| 6. Frazy wyszukiwania | | | | |
| 7. Rekomendacje Engine | | | | |
| 8. Daily Audit | | | | |
| 9. Negative Keywords | | | | |
| 10. Optymalizacja (25 narzędzi) | | | | |
| 11. Wpływ Zmian | | | | |
| 12. Pareto Analysis | | | | |
| 13. Bid Strategy Health | | | | |
| 14. Monitoring & Anomalie | | | | |
| 15. Forecast | | | | |
| 16. Raporty AI (Agent) | | | | |
| 17. Raporty | | | | |
| 18. Action History | | | | |
| 19. Change History | | | | |
| 20. Ustawienia | | | | |
| 21. Klienci | | | | |
| 22. Multi-Account | | | | |
| 23. Bezpieczeństwo akcji | | | | |
| 24. Dodatkowe funkcjonalności | | | | |
| 25. Export danych | | | | |
| 26. Correlation & Compare | | | | |
| 27. Edge Cases & Error Handling | | | | |

**Łączna liczba punktów testowych:** ~200
**Łączna liczba znalezionych bugów:** ___
**Krytyczne:** ___
**Do poprawy:** ___
**Uwagi ogólne:** ___
