# Jak działa aplikacja — Przewodnik po funkcjach

Dokument dla specjalistów Google Ads i kierowników projektu.
Bez kodu — tylko logika biznesowa i co widzisz na ekranie.

---

## Spis treści

1. [Dashboard (Pulpit)](#1-dashboard-pulpit)
   - 1.1 [Health Score](#11-health-score)
   - 1.2 [KPI](#12-kpi)
2. [Poranny przegląd (Daily Audit)](#2-poranny-przegląd)
3. [Kampanie](#3-kampanie)
4. [Słowa kluczowe](#4-słowa-kluczowe)
5. [Wyszukiwane frazy (Search Terms)](#5-wyszukiwane-frazy)
6. [Produkty / Shopping](#6-produkty--shopping)
7. [Performance Max](#7-performance-max)
8. [Display](#8-display)
9. [DSA (Dynamic Search Ads)](#9-dsa)
10. [Monitoring (Alerty i Anomalie)](#10-monitoring)
    - 10.1 [Alerty biznesowe](#101-alerty-biznesowe)
    - 10.2 [Anomalie z-score](#102-anomalie-z-score)
11. [Plan dnia (Task Queue)](#11-plan-dnia)
12. [Rekomendacje](#12-rekomendacje)
13. [Reguły automatyczne](#13-reguły-automatyczne)
14. [Historia zmian](#14-historia-zmian)
15. [Asystent AI](#15-asystent-ai)
16. [Raporty](#16-raporty)
17. [Centrum audytu](#17-centrum-audytu)
18. [Konkurencja (Auction Insights)](#18-konkurencja)
19. [Analiza cross-kampaniowa](#19-analiza-cross-kampaniowa)
20. [Benchmarki](#20-benchmarki)
21. [Prognoza](#21-prognoza)
22. [Inteligencja semantyczna](#22-inteligencja-semantyczna)
23. [Wynik jakości (Quality Score)](#23-wynik-jakości)
24. [Ustawienia](#24-ustawienia)

---

## 1. Dashboard (Pulpit)

Główny ekran aplikacji. Po zalogowaniu i wybraniu klienta widzisz przegląd najważniejszych wskaźników konta.

**Co jest na ekranie:**
- Health Score (okrąg z oceną konta)
- KPI w kafelkach (kliknięcia, koszt, konwersje, ROAS, CPA)
- Quality Score widget (średni QS + ile słów z niskim)
- Trend wydatków (wykres)
- Device breakdown (desktop vs mobile vs tablet)
- Geo breakdown (mapa/lista miast)
- Wasted spend (ile pieniędzy marnujesz)
- Impression share (ile aukcji wygrywasz)

**Odświeżanie:** Dane przeładowują się po zmianie klienta, zakresu dat lub filtra kampanii.

---

### 1.1 Health Score

**Co to jest?**

Jedna liczba 0-100 odpowiadająca na pytanie: *"Czy z tym kontem jest OK?"*

- **80-100** (zielony) — Konto w dobrej kondycji
- **40-79** (żółty) — Są rzeczy do poprawy
- **0-39** (czerwony) — Poważne problemy

**Skąd bierze się ta liczba?**

Średnia ważona z 6 obszarów, każdy oceniany osobno 0-100:

#### Wyniki (25% wagi) — *Czy kampanie przynoszą efekty?*

- Ile kampanii ma kliknięcia, ale **zero konwersji**
- Ile kampanii ma **ROAS poniżej 1.0** (za złotówkę reklamy dostajemy mniej niż złotówkę przychodu)
- Łączny ROAS na koncie
- Kampanie brandowe pomijane w ocenie ROAS (brand ma inny model)

#### Jakość (20% wagi) — *Jak Google ocenia nasze reklamy?*

- **Średni Quality Score** słów kluczowych (ideał 7+, poniżej 5 to problem)
- **% słów z QS poniżej 5** — powyżej 30% = potrzebna praca
- **Siła reklam (Ad Strength)** — ile reklam jest POOR/AVERAGE zamiast GOOD/EXCELLENT

Quality Score wpływa bezpośrednio na CPC. Konto z QS 8 płaci mniej za tę samą pozycję niż konto z QS 4.

#### Efektywność (20% wagi) — *Czy mądrze wydajemy budżet?*

- **Zmarnowany budżet na słowach kluczowych** — % wydatków na słowa bez konwersji
- **Zmarnowany budżet na wyszukiwaniach** — % wydatków na nieistotne zapytania użytkowników
- **Pacing budżetu** — czy kampanie wydają tyle ile powinny w danym momencie miesiąca

#### Zasięg (15% wagi) — *Czy pokazujemy się klientom?*

- **Impression Share** — na jaki % aukcji się wyświetlamy (80%+ to dobrze)
- **Stracony IS przez budżet** — ile wyświetleń tracimy bo budżet się kończy
- **Stracony IS przez ranking** — ile tracimy bo QS lub stawki za niskie

Dotyczy tylko kampanii Search.

#### Stabilność (10% wagi) — *Czy konto jest stabilne?*

- **Nierozwiązane alerty** — ile alertów czeka na reakcję
- **Trend CTR** — czy klikalność spada (porównanie dwóch połów okresu)

Kampanie PMax, Display i Video pomijane w CTR.

#### Struktura (10% wagi) — *Czy konto jest poukładane?*

- **Grupy reklam z < 2 reklamami** — Google zaleca 2-3 reklamy per grupę
- **Kampanie bez sitelinków** — brakujące rozszerzenia = stracona widoczność

**Co widzisz na ekranie:**

```
┌──────────────────────────────────────────────┐
│  HEALTH SCORE                                 │
│                                               │
│   ╭────╮   ● 2 kampanie z ROAS < 1           │
│   │ 74 │   ● 35% budżetu na słowa bez konw.  │
│   ╰────╯   ● Impression Share tylko 55%       │
│                                               │
│  Wyniki  Jakość  Efekt.  Zasięg  Stab. Strukt│
│  ██████  ████░░  ██████  ████░░  █████ █████  │
└──────────────────────────────────────────────┘
```

- Okrąg z liczbą — kolor zmienia się zielony → żółty → czerwony
- Lista max 3 najważniejszych problemów
- 6 pasków — który obszar ciągnie wynik w dół

**Kliknięcie w Health Score** otwiera zakładkę **Monitoring** z pełną listą alertów.

Każdy problem na liście kieruje do odpowiedniej zakładki (Kampanie, Słowa kluczowe, Alerty, Wyszukiwania).

---

### 1.2 KPI

Kafelki z najważniejszymi liczbami za wybrany okres:

| Kafelek | Co pokazuje |
|---------|------------|
| Kliknięcia | Suma kliknięć + zmiana % vs poprzedni okres |
| Koszt | Suma wydatków + zmiana % |
| Konwersje | Suma konwersji + zmiana % |
| ROAS | Zwrot z wydatków reklamowych |
| CPA | Koszt per konwersja |

Zmiana procentowa porównuje wybrany okres z analogicznym wcześniejszym (np. ostatnie 7 dni vs 7 dni przed nimi).

---

## 2. Poranny przegląd

Zakładka "Poranny przegląd" to codzienny briefing — jeden ekran z odpowiedzią na pytanie *"Co się działo i co wymaga uwagi?"*

Zawiera: KPI snapshot, alerty, rekomendacje, pacing budżetu, anomalie — wszystko w jednym miejscu żeby nie klikać po 5 zakładkach.

---

## 3. Kampanie

Lista wszystkich kampanii klienta z kluczowymi metrykami.

**Widoczne kolumny:** nazwa, status, typ, budżet, kliknięcia, wyświetlenia, CTR, koszt, konwersje, ROAS, CPA.

**Funkcje:**
- Filtrowanie po typie (Search, PMax, Shopping, Display, Video) i statusie (ENABLED, PAUSED)
- Sparkline — mini wykres trendu kosztu per kampania
- Device breakdown per kampania
- Geo breakdown per kampania
- Pacing budżetu — ile % budżetu wykorzystane vs ile powinno być
- Historia zmian per kampania (timeline)

---

## 4. Słowa kluczowe

Zarządzanie słowami kluczowymi z 4 zakładkami:

| Zakładka | Co zawiera |
|----------|-----------|
| Pozytywne | Lista słów z metrykami (QS, IS, kliknięcia, konwersje, CPA) |
| Wykluczenia | Negatywne słowa na poziomie kampanii/grupy |
| Listy wykluczeń | Shared negative keyword lists |
| Ekspansja | Propozycje nowych słów na podstawie search terms |

**Quality Score** widoczny per słowo z kolorowym wskaźnikiem (zielony 7+, żółty 5-6, czerwony <5).

Tylko dla kampanii Search.

---

## 5. Wyszukiwane frazy

Co wpisują użytkownicy zanim klikną Twoją reklamę.

**Segmentacja automatyczna:**
- **Top performers** — frazy z konwersjami
- **Waste** — frazy z kosztem ale bez konwersji
- **Irrelevant** — frazy niezwiązane z ofertą

**Akcje:** Dodaj jako słowo kluczowe, dodaj jako wykluczenie (jedno kliknięcie).

Działa dla Search i Performance Max.

---

## 6. Produkty / Shopping

Analiza kampanii Shopping: grupy produktów, ROAS per produkt, feed health.

Widoczne tylko gdy klient ma kampanie Shopping.

---

## 7. Performance Max

Dedykowana analiza kampanii PMax:
- Asset groups (grupy zasobów) z metrykami
- Kanały (Search, Display, YouTube, Discover, Gmail, Maps)
- Search themes (tematy wyszukiwań)
- Kanibalizacja — czy PMax kradnie ruch kampaniom Search

---

## 8. Display

Analiza kampanii Display:
- Placements (strony na których wyświetlają się reklamy)
- Topics (tematy)
- Audiences (grupy odbiorców)
- Bid modifiers (modyfikatory stawek per urządzenie/lokalizacja)

---

## 9. DSA

Dynamic Search Ads — reklamy dynamiczne:
- Targety DSA (strony, kategorie)
- Nagłówki generowane przez Google
- Overlap z kampaniami Search (czy DSA kanibalizuje ręczne słowa kluczowe)

---

## 10. Monitoring

Zakładka do której trafiasz po kliknięciu Health Score. Służy do śledzenia problemów na koncie.

**Dwie zakładki:**

### 10.1 Alerty biznesowe

System generuje alerty gdy wykryje problem:

| Typ alertu | Kiedy się pojawia | Severity |
|------------|------------------|----------|
| SPEND_SPIKE | Kampania wydaje 3x więcej niż średnia | HIGH |
| CONVERSION_DROP | Konwersje spadły znacząco vs średnia | HIGH |
| CTR_DROP | CTR poniżej 0.5% przy >1000 wyświetleń | MEDIUM |
| CPA_SUSTAINED | CPA ponad 150% normy przez 3+ dni | HIGH |
| DISAPPROVED_ADS | Reklamy odrzucone przez Google | MEDIUM |

**Co widzisz na ekranie:**

```
┌──────────────────────────────────────────────────┐
│  MONITORING                                       │
│  [Alerty]  [Anomalie (z-score)]                   │
│                                                   │
│  [Nierozwiązane (4)]  [Rozwiązane]                │
│                                                   │
│  ┌────────────────────────────────────────────┐   │
│  │ ⊘ WYSOKI  SPEND_SPIKE                     │   │
│  │ Nagły wzrost kosztów: Łóżka - Generic     │   │
│  │ Kampania wydała 3.2x więcej niż zwykle    │   │
│  │ → Łóżka - Generic                [Rozwiąż]│   │
│  └────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────┐   │
│  │ ⊘ WYSOKI  CONVERSION_DROP                 │   │
│  │ Spadek konwersji: Kanapy - Generic         │   │
│  │ Średnia spadła z 4.2 do 0.8 dziennie       │   │
│  │ → Kanapy - Generic                [Rozwiąż]│   │
│  └────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

**Każdy alert zawiera:**
- Badge severity (Wysoki = czerwony, Średni = żółty, Niski = niebieski)
- Typ alertu (SPEND_SPIKE, CONVERSION_DROP, ...)
- Tytuł i opis — co się stało, konkretne liczby
- Nazwa kampanii (klikalna — przenosi do Kampanii)
- Przycisk "Rozwiąż" — oznacza alert jako rozwiązany

**Sub-zakładki:** Nierozwiązane (domyślnie) i Rozwiązane.

Alerty powstają automatycznie podczas synchronizacji danych z Google Ads lub ręcznego uruchomienia detekcji.

---

### 10.2 Anomalie z-score

Statystyczne wykrywanie anomalii — niezależne od reguł biznesowych.

**Jak działa:**
1. Bierzemy wybraną metrykę (np. Koszt) z ostatnich X dni
2. Liczymy średnią i odchylenie standardowe per dzień
3. Każdy dzień z wartością dalej niż próg σ od średniej = anomalia

**Ustawienia:**
- **Metryka:** Koszt, Kliknięcia, Wyświetlenia, Konwersje, CTR
- **Próg (z-score):** 1.5σ, 2.0σ, 2.5σ, 3.0σ — im wyższy próg, tym mniej fałszywych alarmów
- **Okres:** 30, 60, 90 dni

**Co widzisz:**
- 3 kafelki: Ilość anomalii, Średnia metryki, Odchylenie standardowe
- Tabela anomalii: Data, Kampania (z nazwą), Wartość, Z-score, Typ (Skok/Spadek)
- Kolory: z-score > 3σ = czerwony (poważna anomalia), poniżej = żółty

**Przykład użycia:** Ustawiasz metrykę "Koszt", próg 2σ, okres 90 dni. System pokaże dni w których koszt był ponad 2 odchylenia od średniej — np. 5 marca koszt wystrzelił do $500 (średnia $180, z-score 3.1σ). Klikasz w kampanię i sprawdzasz co się stało.

---

## 11. Plan dnia

Priorytetyzowana lista zadań do wykonania dziś:
- Rekomendacje posortowane po ważności
- Alerty wymagające akcji
- Wasted spend do wyeliminowania

Jedno miejsce zamiast klikania po 3 zakładkach.

---

## 12. Rekomendacje

AI generuje konkretne rekomendacje:
- Wstrzymaj słowo kluczowe (za drogie, brak konwersji)
- Zmień stawkę (za niska/wysoka vs CPA target)
- Zwiększ budżet (kampania traci IS przez budżet)
- Dodaj wykluczenie (search term marnuje pieniądze)

Każda rekomendacja ma przycisk "Zastosuj" — wykonuje akcję jednym kliknięciem (z potwierdzeniem).

---

## 13. Reguły automatyczne

Tworzenie własnych reguł typu:
- "Jeśli słowo kluczowe ma > 50 kliknięć i 0 konwersji → wstrzymaj"
- "Jeśli kampania wydaje > 130% budżetu → wyślij alert"

Reguły działają w trybie dry-run (podgląd co by się stało) lub live.

---

## 14. Historia zmian

Pełna historia wszystkich zmian na koncie:
- Akcje wykonane przez aplikację (wstrzymania, zmiany stawek)
- Zmiany zewnętrzne (ktoś zmienił coś w Google Ads UI)
- Timeline z filtrowaniem
- Analiza wpływu zmian na metryki (przed vs po)

---

## 15. Asystent AI

Chatbot z szybkimi akcjami:
- Tygodniowy raport
- Analiza kampanii
- Przegląd budżetu
- Identyfikacja problemów

---

## 16. Raporty

Generowanie raportów AI:
- Miesięczny raport (trendy, top kampanie, rekomendacje)
- Tygodniowy raport
- Raport zdrowia konta (health audit)

Raporty w formacie markdown z wykresami i danymi.

---

## 17. Centrum audytu

Najbardziej rozbudowana zakładka — 25+ sekcji analizy:

| Sekcja | Co analizuje |
|--------|-------------|
| Wasted Spend | Pieniądze wydane na 0-konwersyjne słowa/frazy |
| Dayparting | O której godzinie/dniu konwertujemy najlepiej |
| Match Types | Rozkład typów dopasowania i ich efektywność |
| N-gram Analysis | Najczęstsze fragmenty słów w search terms |
| RSA Analysis | Jakość reklam responsywnych |
| Landing Pages | Które strony docelowe konwertują najlepiej |
| Account Structure | Struktura konta (kampanie → grupy → słowa) |
| Bidding Advisor | Rekomendacje strategii biddingu |
| Ad Group Health | Ile reklam/słów per grupa, problemy strukturalne |
| Smart Bidding Health | Czy kampanie smart bidding mają wystarczający wolumen |
| Portfolio Health | Strategie portfolio — dominacja jednej kampanii |
| Conversion Quality | Czy śledzenie konwersji jest poprawnie skonfigurowane |
| Demographics | Wyniki per wiek/płeć |
| Audiences | Efektywność grup odbiorców |
| Extensions | Brakujące/działające rozszerzenia |
| PMax Cannibalization | Czy PMax kradnie ruch Search |
| Scaling Insights | Które kampanie mają potencjał do skalowania |
| Learning Status | Czy smart bidding jest w fazie uczenia |

---

## 18. Konkurencja

Auction Insights — porównanie z konkurentami:
- Impression Share per konkurent
- Overlap Rate (jak często się spotykamy w aukcji)
- Position Above Rate (jak często konkurent jest wyżej)
- Outranking Share

---

## 19. Analiza cross-kampaniowa

Porównanie kampanii między sobą:
- Alokacja budżetu — czy pieniądze idą tam gdzie powinny
- Porównanie efektywności kampanii A vs B

---

## 20. Benchmarki

Porównanie metryk konta z benchmarkami branżowymi:
- CTR, CPC, CPA, CVR, ROAS
- Czy jesteśmy powyżej/poniżej normy branżowej

---

## 21. Prognoza

Prognoza wyników kampanii na 7/14/30 dni do przodu.

Tylko dla kampanii Search — oparta na trendach historycznych.

---

## 22. Inteligencja semantyczna

Grupowanie słów kluczowych w klastry tematyczne:
- Które tematy generują koszt/konwersje
- Propozycje wykluczeń per klaster

Tylko dla kampanii Search.

---

## 23. Wynik jakości

Dedykowany audyt Quality Score:
- Rozkład QS na koncie (histogram)
- Wpływ niskiego QS na koszty (ile przepłacamy)
- Konkretne słowa z niskim QS + powody (trafność reklamy, landing page, oczekiwany CTR)
- Rekomendacje poprawy

---

## 24. Ustawienia

Konfiguracja konta:
- Limity bezpieczeństwa (max zmiana stawki, max zmiana budżetu, min/max bid)
- Zarządzanie kontami MCC
- Konfiguracja synchronizacji
