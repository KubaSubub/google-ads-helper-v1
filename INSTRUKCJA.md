# Google Ads Helper — Instrukcja użytkownika

**Wersja:** 1.1
**Data:** marzec 2026

---

## Spis treści

1. [Co to jest Google Ads Helper?](#1-co-to-jest-google-ads-helper)
2. [Wymagania systemowe](#2-wymagania-systemowe)
3. [Pierwsze uruchomienie — konfiguracja](#3-pierwsze-uruchomienie--konfiguracja)
4. [Interfejs — przegląd ekranów](#4-interfejs--przegląd-ekranów)
5. [Przepływ pracy](#5-przepływ-pracy)
6. [Synchronizacja danych](#6-synchronizacja-danych)
7. [Rekomendacje — 17 reguł optymalizacyjnych](#7-rekomendacje--17-reguł-optymalizacyjnych)
8. [Limity bezpieczeństwa](#8-limity-bezpieczeństwa)
9. [Cofanie akcji (Revert)](#9-cofanie-akcji-revert)
10. [Ustawienia klienta](#10-ustawienia-klienta)
11. [Eksport danych](#11-eksport-danych)
12. [Rozwiązywanie problemów](#12-rozwiązywanie-problemów)
13. [Architektura techniczna](#13-architektura-techniczna)
14. [Baza danych i logi](#14-baza-danych-i-logi)
15. [Słowniczek pojęć Google Ads](#15-słowniczek-pojęć-google-ads)

---

## 1. Co to jest Google Ads Helper?

Google Ads Helper to desktopowa aplikacja dla Windows, która automatyzuje rutynową pracę specjalisty Google Ads:

- **Synchronizuje dane** z konta Google Ads (kampanie, słowa kluczowe, wyszukiwane frazy, metryki)
- **Analizuje wyniki** i wykrywa problemy (marnowany budżet, niska jakość, anomalie)
- **Generuje rekomendacje** optymalizacyjne (17 reguł decyzyjnych)
- **Umożliwia 1-click akcje** z mechanizmami bezpieczeństwa (limity zmian, podgląd przed/po, cofanie)

Dane przechowywane są **lokalnie** na komputerze (SQLite). Żadne dane nie są wysyłane do chmury poza komunikację z Google Ads API.

---

## 2. Wymagania systemowe

| Wymaganie | Wartość |
|-----------|---------|
| System operacyjny | Windows 10+ |
| Python | 3.10+ |
| Node.js | 18+ |
| Przeglądarka | dowolna (do autoryzacji OAuth) |
| Konto Google Ads | z dostępem API (developer token) |

---

## 3. Pierwsze uruchomienie — konfiguracja

### 3.1 Pozyskanie danych dostępowych Google Ads API

Potrzebujesz 4 wartości z Google Cloud Console:

| Wartość | Skąd ją wziąć |
|---------|---------------|
| **GOOGLE_CLIENT_ID** | Google Cloud Console → Credentials → OAuth 2.0 Client ID (Desktop) |
| **GOOGLE_CLIENT_SECRET** | Tamże, przy Client ID |
| **GOOGLE_DEVELOPER_TOKEN** | Google Ads → Narzędzia → API Center |
| **GOOGLE_LOGIN_CUSTOMER_ID** | Twój ID konta Google Ads (MCC lub konto, **bez myślników**, np. `1234567890`) |

Szczegółowy poradnik krok po kroku: plik `JAK_ZDOBYC_CREDENTIALS.md` w katalogu projektu.

**Czas:** 10–30 minut (zatwierdzenie developer token może trwać do 48h jeśli jest nowe konto).

### 3.2 Uruchomienie aplikacji

```bash
# Backend (terminal 1)
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Albo jednym plikiem:
```bash
URUCHOM_APLIKACJE.bat
```

### 3.3 Kreator logowania

Przy pierwszym uruchomieniu pojawi się ekran logowania z formularzem:

1. Wpisz 4 dane dostępowe (skopiuj z Google Cloud Console)
2. Kliknij **„Zaloguj przez Google"**
3. Autoryzuj aplikację w przeglądarce
4. Przekierowanie z powrotem do aplikacji → Dashboard

Dane dostępowe są przechowywane w **Windows Credential Manager** — nigdy nie trafiają do plików `.env` ani logów.

### 3.4 Dodanie klientów

Po zalogowaniu:
1. Przejdź do **Klienci** w sidebarze
2. Kliknij **„Odkryj konta z MCC"** — automatycznie znajdzie konta podłączone do Twojego MCC
3. Lub dodaj klienta ręcznie (nazwa + Google Customer ID)
4. Wybierz aktywnego klienta w dropdown w sidebarze

---

## 4. Interfejs — przegląd ekranów

### Sidebar (pasek boczny)

Sidebar zawiera:
- **Selektor klienta** — dropdown „Aktywny klient" przełącza wszystkie widoki na wybranego klienta
- **Zakres dat** — 4 presety (7/14/30/90 dni) + custom zakres dat (kalendarz z polami „od" / „do")
- **Nawigacja** — 5 grup menu (opisane poniżej)
- **Przycisk Sync** — ręczna synchronizacja danych z Google Ads (ze wskaźnikiem postępu)
- **Badge rekomendacji** — czerwony znacznik z liczbą oczekujących rekomendacji HIGH
- **Badge alertów** — czerwony znacznik z liczbą nierozwiązanych anomalii

### Filtry globalne

Na wielu ekranach dostępny jest **FilterBar** z filtrami:

- **Typ kampanii:** ALL, SEARCH, PERFORMANCE_MAX, DISPLAY, SHOPPING, VIDEO, SMART
- **Status:** ALL, ENABLED, PAUSED, REMOVED
- **Zakres dat:** ustawiany globalnie w sidebarze (presety 7/14/30/90 dni lub custom)

Filtry działają in-memory — dane są pobrane z API raz, a filtrowanie odbywa się po stronie przeglądarki.

### Grupy nawigacyjne — mapa ekranów

#### PRZEGLĄD

| Ekran | Opis |
|-------|------|
| **Pulpit** | Dashboard — główny ekran z KPI, health score, trendami, insightami |
| **Klienci** | Lista kont Google Ads. Dodawanie, edycja, odkrywanie z MCC |

#### DANE KAMPANII

| Ekran | Opis |
|-------|------|
| **Kampanie** | Tabela kampanii z metrykami, sparkline charts, filtrowanie po typie i statusie |
| **Słowa kluczowe** | Keywords z bidami, match type, QS, CTR, konwersjami. Z datami → agregacja dzienna |
| **Wyszukiwane frazy** | Search terms w 4 segmentach + widok listy z inline akcjami |

#### DZIAŁANIA

| Ekran | Opis |
|-------|------|
| **Rekomendacje** | 17 reguł z priorytetem. Rekomendacje (Apply) + Alerty (diagnostyczne) |
| **Historia akcji** | Timeline akcji w 3 zakładkach z możliwością cofnięcia |

#### MONITORING

| Ekran | Opis |
|-------|------|
| **Monitoring** | Wykrywanie anomalii z konfigurowalnym z-score |
| **Prognozowanie** | 7-dniowa prognoza per kampania z regresją liniową |

#### ANALIZA

| Ekran | Opis |
|-------|------|
| **Optymalizacja** | 9 analiz dla kampanii SEARCH |
| **Inteligencja** | Semantyczne klastrowanie słów kluczowych |
| **Quality Score** | Audyt QS z identyfikacją problemów per keyword |

#### Dolna część sidebaru

| Ekran | Opis |
|-------|------|
| **Ustawienia** | Informacje o kliencie, strategia, reguły biznesowe, limity bezpieczeństwa |

---

### Szczegóły ekranów

### 4.1 Pulpit (Dashboard)

Główny ekran aplikacji z 6 sekcjami:

**Karty KPI (góra ekranu)**
- 5 kart: Kliknięcia, Wyświetlenia, Koszt, Konwersje, ROAS
- Każda karta pokazuje wartość za wybrany okres + zmianę procentową vs poprzedni okres (np. +12% ↑)
- Kolor zmiany: zielony = poprawa, czerwony = pogorszenie

**Health Score**
- Wskaźnik zdrowia konta od 0 do 100 (gauge/koło)
- Rozbicie na zidentyfikowane problemy (np. „3 kampanie z QS < 5", „wasted spend > 25%")
- Aktualizuje się po każdym sync

**TrendExplorer (wykres wielometryczny)**
- Interaktywny wykres z możliwością dodania do **5 metryk** jednocześnie
- Dostępne metryki: cost, clicks, impressions, conversions, CTR, CPC, ROAS, CPA, CVR
- **Korelacja Pearsona** — automatycznie liczona między pierwszymi 2 wybranymi metrykami (np. „silna dodatnia r=0.87")
- **Podwójna oś Y** — aktywuje się automatycznie przy mieszaniu jednostek (np. % i PLN)
- Respektuje globalny zakres dat z sidebaru

**InsightsFeed (automatyczne insighty)**
- Zwijana sekcja z automatycznie generowanymi obserwacjami:
  - **HIGH** (czerwony): kampanie z wysokim kosztem i 0 konwersji
  - **MEDIUM** (żółty): rozbieżność CTR i konwersji (CTR rośnie, konwersje spadają)
  - **INFO** (niebieski): niezastosowane rekomendacje HIGH priority
  - **POSITIVE** (zielony): kampanie z ROAS > 2× średnia konta

**Budget Pacing (tempo budżetu)**
- Tabela per kampania z postępem wydawania budżetu w bieżącym miesiącu
- Trzy statusy:
  - **Na torze** (zielony) — wydatki zgodne z planem
  - **Niedostateczne** (żółty) — wydaje < 50% oczekiwanego (po 30% miesiąca)
  - **Przekroczenie** (czerwony) — wydaje > 130% oczekiwanego
- Pasek postępu: actual spend vs expected spend + pacing %

**Device & Geo Breakdown**
- **Urządzenia**: podział wyników na MOBILE / DESKTOP / TABLET — kliknięcia %, CTR, CPC, ROAS per device
- **Lokalizacje**: top 8 miast/regionów — kliknięcia, koszt, ROAS z kolorowaniem warunkowym

### 4.2 Klienci

- Lista wszystkich dodanych kont Google Ads
- **Odkryj konta z MCC** — automatycznie znajduje konta podłączone do konta menedżerskiego
- Dodaj ręcznie — formularz: nazwa + Google Customer ID
- Edycja / usuwanie klienta
- Po odkryciu konta pojawiają się natychmiast w dropdownie w sidebarze

### 4.3 Kampanie

- Tabela ze wszystkimi kampaniami wybranego klienta
- Kolumny: nazwa, typ (SEARCH/PMAX/DISPLAY/...), status, budżet, kliknięcia, impressions, CTR, CPC, konwersje, ROAS
- **Sparkline charts** — miniaturowe wykresy trendów w kolumnie
- Filtrowanie po typie kampanii i statusie (FilterBar)
- Kliknięcie w kampanię → szczegółowe KPI z wykresem metrycznym

### 4.4 Słowa kluczowe

- Tabela keywords z kolumnami: keyword, match type, bid, QS, clicks, impressions, CTR, conversions, cost
- **Dwa tryby danych:**
  - Bez dat → snapshot (aktualne wartości z ostatniego sync)
  - Z datami (globalny zakres dat) → agregacja z tabeli `keywords_daily` (SUM kliknięć, kosztów itd.)
- Sortowanie po dowolnej kolumnie
- Eksport do XLSX

### 4.5 Wyszukiwane frazy (Search Terms)

**Dwa widoki** przełączane przyciskami:

**Widok segmentów (domyślny):**
- 4 zwijane karty z podsumowaniem:
  - **HIGH_PERFORMER** (zielony) — conv ≥ 3 i CVR > średnia kampanii → sugestia: dodaj jako keyword
  - **WASTE** (czerwony) — clicks ≥ 5, 0 konwersji, CTR < 1% → sugestia: dodaj jako negative
  - **IRRELEVANT** (szary) — zawiera słowa z czarnej listy → natychmiast do wykluczenia
  - **OTHER** (niebieski) — za mało danych do klasyfikacji
- Każda karta: ilość fraz, łączny koszt, łączne konwersje

**Widok listy:**
- Tabela z paginacją (50 wierszy na stronę)
- Wyszukiwanie pełnotekstowe w zapytaniach
- Sortowanie: koszt, konwersje, kliknięcia, CTR, ROAS (rosnąco / malejąco)
- **Inline akcje** per wiersz:
  - „+ Dodaj jako Keyword" (EXACT lub PHRASE)
  - „+ Dodaj jako Negative"
- Filtrowanie po dacie (globalny zakres dat z sidebaru)
- Eksport do XLSX

### 4.6 Rekomendacje

Szczegółowy opis reguł → sekcja 7.

- **Filtr priorytet:** HIGH / MEDIUM / LOW (pill buttons)
- **Filtr kategoria:** Rekomendacja (z przyciskiem „Zastosuj") / Alert (diagnostyczny, bez akcji)
- **Filtr status:** oczekujące / zastosowane / odrzucone
- **Podsumowanie:** ilość per priorytet + per typ rekomendacji
- **Podgląd przed/po** — przed zastosowaniem akcji można zobaczyć co się zmieni (dry run)
- **Odrzuć** — oznacza rekomendację jako odrzuconą (nie pojawi się ponownie)

### 4.7 Historia akcji

**3 zakładki:**

| Zakładka | Co pokazuje |
|----------|------------|
| **Helper** | Akcje wykonane z Google Ads Helper (Apply recommendation) |
| **Zewnętrzne** | Zmiany z Google Ads UI lub API (wykryte przez Change Events) |
| **Wszystko** | Połączony timeline z obu źródeł |

**Funkcje:**
- Grupowanie chronologiczne: Dziś, Wczoraj, Ten tydzień, Starsze
- **Podgląd diff** — przed/po w formacie JSON (komponent DiffView)
- Kolor źródła: zielony = Helper, niebieski = API/UI Google
- Status: zielony = success, czerwony = failed, szary = reverted
- **Przycisk „Cofnij"** — dostępny dla akcji < 24h ze statusem SUCCESS (szczegóły → sekcja 9)

### 4.8 Monitoring (Anomalie)

Wykrywanie statystycznych odchyleń od normy:

- **Konfigurowalny próg z-score:** 1.5σ, 2.0σ, 2.5σ, 3.0σ (im wyższy próg, tym mniej alertów)
- **Wybór metryki:** cost, clicks, impressions, conversions, CTR
- **Okno czasowe:** 30, 60 lub 90 dni wstecz
- **Statystyki:** średnia i odchylenie standardowe wybranej metryki
- **Kierunek anomalii:** „Skok" (wzrost ponad normę) lub „Spadek" (poniżej normy)
- **Z-score wizualizacja:** >3σ = czerwony, <3σ = żółty
- **Zakładki:** Nierozwiązane / Rozwiązane — kliknij „Rozwiąż" aby przenieść alert

### 4.9 Prognozowanie (Forecast)

7-dniowa prognoza przyszłych wartości metryki:

- **Wybór kampanii** — dropdown z listą kampanii
- **Wybór metryki** — pill buttons: Cost, Clicks, Conversions, CTR
- **Wykres:** linia historyczna (ciągła) + prognoza (przerywana) z **przedziałami ufności** (zacieniowany obszar 95% CI)
- **Karty KPI:**
  - Trend (7 dni): zmiana procentowa + kierunek (↑↓)
  - Średnia prognozy: przewidywana dzienna wartość
  - Pewność modelu: HIGH / MEDIUM / LOW (oparta na R²)
  - Nachylenie: tempo zmiany per dzień
- Metoda: regresja liniowa na danych historycznych

### 4.10 Optymalizacja SEARCH

9 zwijanych sekcji analitycznych dla kampanii SEARCH:

| # | Analiza | Co pokazuje |
|---|---------|-------------|
| 1 | **Wasted Spend** | Ile % budżetu idzie na keywords/search terms/reklamy bez konwersji |
| 2 | **Dayparting (dni tygodnia)** | 7 kart (Pon–Nd), kliknięcia vs konwersje per dzień, CPA |
| 3 | **Dayparting (godziny)** | Rozbicie na 24 godziny — kiedy kampanie działają najlepiej |
| 4 | **RSA Analysis** | Wydajność reklam per grupa reklam — które nagłówki/opisy są najlepsze |
| 5 | **N-gram Analysis** | Częstotliwość słów (1/2/3-gramy) w search terms z metrykami kosztowymi |
| 6 | **Match Type Analysis** | Porównanie EXACT vs PHRASE vs BROAD — CTR, CPA, ROAS per typ |
| 7 | **Landing Pages** | Wydajność per URL docelowy — najlepsze/najgorsze strony |
| 8 | **Audyt struktury konta** | Wykrywanie: za duże grupy reklam, mieszane match types, kanibalizacja keywords |
| 9 | **Doradca strategii stawek** | Rekomendacja bidding strategy per kampania (na podstawie wolumenu konwersji) |

### 4.11 Klasteryzacja semantyczna (Inteligencja)

Automatyczne grupowanie keywords w tematyczne klastry:

- **Karty klastrów** — zwijane, z nazwą tematu (auto-generowana) i metrykami
- **Metryki per klaster:** ilość keywords, łączny koszt, % waste
- **Filtr kosztowy:** przyciski > 0 zł, > 10 zł, > 50 zł, > 100 zł
- **Flaga waste:** czerwona ikona = klaster marnujący budżet, niebieska = zdrowy
- **Rozwinięcie karty:** lista keywords w klastrze z ich indywidualnymi metrykami

### 4.12 Quality Score Audit

Audyt jakości słów kluczowych:

- **Histogram rozkładu QS** — wykres słupkowy pokazujący ile keywords ma QS 1, 2, ... 10
- **Konfigurowalny próg** — domyślnie flaguje keywords z QS < 5
- **Identyfikacja problemów** per keyword:
  - „Niski Expected CTR" — reklama nie przyciąga kliknięć
  - „Niska Ad Relevance" — reklama nie pasuje do keywordu
  - „Słaby Landing Page" — strona docelowa wymaga poprawy
- **Sortowanie:** od najniższego QS
- **Cel benchmarkowy:** „Średni QS powyżej 7.0"
- Kolumny: keyword, QS, CTR%, kliknięcia, koszt, match type

---

## 5. Przepływ pracy

Typowy cykl pracy z aplikacją:

```
1. SYNC        → Pobierz aktualne dane z Google Ads (przycisk Refresh)
2. PRZEGLĄD    → Sprawdź Dashboard: KPI, health score, trendy
3. MONITORING  → Sprawdź alerty anomalii, rozwiąż lub zbadaj
4. ANALIZA     → Przejrzyj wyszukiwane frazy, Quality Score, optymalizację
5. REKOMENDACJE → Przejrzyj sugestie engine'u, zastosuj lub odrzuć
6. WERYFIKACJA → Sprawdź historię akcji, cofnij jeśli potrzeba
```

### Częstotliwość

| Czynność | Jak często |
|----------|-----------|
| Sync danych | Codziennie lub po większych zmianach w koncie |
| Przegląd rekomendacji | 2–3× w tygodniu |
| Analiza search terms | Co tydzień |
| Audyt Quality Score | Co 2 tygodnie |
| Pełna analiza optymalizacyjna | Co miesiąc |

---

## 6. Synchronizacja danych

Sync jest **ręczny** — kliknij przycisk **Refresh / Sync** w sidebarze.

### Fazy synchronizacji

| Faza | Co pobiera | Krytyczność |
|------|-----------|------------|
| 1 | Kampanie | Wymagana |
| 2 | Grupy reklam | Wymagana |
| 3 | Słowa kluczowe | Wymagana |
| 4 | Metryki dzienne (impressions, clicks, cost, conversions) | Wymagana |
| 5a | Search terms (SEARCH) | Wymagana |
| 5b | Search terms (PMax) | Wymagana |
| 6 | Impression share per kampania | Wymagana |
| 7 | Breakdown per urządzenie (device) | Wymagana |
| 8 | Breakdown per lokalizacja (geo) | Wymagana |
| 9 | Historia zmian (change events) | Niekrytyczna — jeśli faza zawiedzie, nie blokuje reszty |

### Parametry

- **Domyślny zakres:** ostatnie 30 dni
- **Maksymalny zakres:** 90 dni
- **Czas trwania:** 15–60 sekund (zależy od rozmiaru konta)

### Po synchronizacji

Automatycznie uruchamiają się:
- Segmentacja search terms (IRRELEVANT → HIGH_PERFORMER → WASTE → OTHER)
- Generowanie rekomendacji (17 reguł)
- Wykrywanie anomalii

---

## 7. Rekomendacje — 17 reguł optymalizacyjnych

Engine generuje dwa typy wyników:

- **RECOMMENDATION** (rekomendacja) — ma konkretną akcję do wykonania (przycisk „Zastosuj")
- **ALERT** (alert diagnostyczny) — informacja bez bezpośredniej akcji (przycisk „Sprawdź")

### MVP — Reguły R1–R7

| # | Reguła | Priorytet | Typ | Kategoria |
|---|--------|-----------|-----|-----------|
| R1 | **Pause Keyword** — wysoki koszt ($50+), 0 konwersji, 30+ kliknięć. Lub: 1000+ impressions, CTR < 0.5% | HIGH / MEDIUM | PAUSE_KEYWORD | RECOMMENDATION |
| R2 | **Increase Bid** — CVR > 1.5× średnia kampanii, CPA < 0.8× średnia, ≥2 konwersje | MEDIUM | INCREASE_BID | RECOMMENDATION |
| R3 | **Decrease Bid** — CPA > 1.5× średnia kampanii, koszt ≥ $100, konwersje > 0 | MEDIUM | DECREASE_BID | RECOMMENDATION |
| R4 | **Add Keyword** — search term z ≥3 konwersjami (EXACT/PHRASE). Lub: 10+ kliknięć, CTR ≥ 5% (PHRASE) | HIGH / LOW | ADD_KEYWORD | RECOMMENDATION |
| R5 | **Add Negative** — irrelevant words (lista), lub: 5+ kliknięć + 0 konwersji + CTR < 1%, lub: koszt ≥ $30 + 0 konwersji | HIGH / MEDIUM | ADD_NEGATIVE | RECOMMENDATION |
| R6 | **Pause Ad** — CTR < 50% najlepszej reklamy w grupie (500+ impr). Lub: koszt $50+ i 0 konwersji | HIGH / MEDIUM | PAUSE_AD | RECOMMENDATION |
| R7 | **Reallocate Budget** — najlepsza kampania ROAS > 2× najgorsza, gorsza ma wyższy budżet | HIGH | REALLOCATE_BUDGET | RECOMMENDATION |

### v1.1 — Reguły R8–R13

| # | Reguła | Priorytet | Typ | Kategoria |
|---|--------|-----------|-----|-----------|
| R8 | **Quality Score Alert** — keyword z QS < 5, impr > 100. Identyfikuje najsłabszy subkomponent (Expected CTR / Ad Relevance / Landing Page) | HIGH (QS 1-2) / MEDIUM (QS 3-4) | QS_ALERT | ALERT |
| R9 | **Impression Share Lost to Budget** — kampania traci >20% IS z powodu budżetu. Jeśli ROAS zdrowy → zwiększ budżet. Jeśli CPA za wysoki → obniż stawki | HIGH (>40%) / MEDIUM | IS_BUDGET_ALERT | RECOMMENDATION |
| R10 | **Impression Share Lost to Rank** — kampania traci >30% IS z powodu Ad Rank (nie budżetu) | MEDIUM | IS_RANK_ALERT | ALERT |
| R11 | **Low CTR + High Impressions** — keyword BROAD/PHRASE z CTR < 0.5%, 1000+ impr, 0 konwersji — słabe dopasowanie | MEDIUM | PAUSE_KEYWORD | RECOMMENDATION |
| R12 | **Wasted Spend Alert** — per kampania: >25% budżetu idzie na keywords bez konwersji | HIGH (>35%) / MEDIUM | WASTED_SPEND_ALERT | ALERT |
| R13 | **PMax vs Search Overlap** — search term pojawia się w kampanii SEARCH i PMax. PMax wydaje ≥50% kosztu Searcha na ten sam term | HIGH (PMax koszt > $50) / MEDIUM | PMAX_CANNIBALIZATION | ALERT |

### v1.2 — Reguły R15–R18

| # | Reguła | Priorytet | Typ | Kategoria |
|---|--------|-----------|-----|-----------|
| R15 | **Device Anomaly** — CPA na mobile >2× CPA na desktop, mobile spend > $100 | MEDIUM | DEVICE_ANOMALY | ALERT |
| R16 | **Geo Anomaly** — lokalizacja z CPA >2× średnia kampanii, spend > $50 | LOW | GEO_ANOMALY | ALERT |
| R17 | **Budget Pacing** — kampania wydaje >130% oczekiwanego budżetu (overspend) lub <50% (underspend, po 30% miesiąca) | HIGH / MEDIUM | BUDGET_PACING | ALERT |
| R18 | **N-gram Negative** — n-gram (1–3 słowa) w ≥3 search terms, łączny koszt > $100, 0 konwersji → dodaj jako broad match negative | HIGH | NGRAM_NEGATIVE | RECOMMENDATION |

### Filtrowanie rekomendacji

W interfejsie możesz filtrować po:
- **Priorytet:** HIGH, MEDIUM, LOW
- **Status:** pending (oczekująca), applied (zastosowana), dismissed (odrzucona)
- **Kategoria:** RECOMMENDATION (z akcją), ALERT (diagnostyczny)

---

## 8. Limity bezpieczeństwa

Każda akcja przechodzi przez **circuit breaker** (`validate_action()`) zanim zostanie wysłana do Google Ads API.

### Globalne limity (domyślne)

| Limit | Wartość |
|-------|---------|
| Max zmiana stawki per akcja | 50% |
| Min stawka | $0.10 |
| Max stawka | $100.00 |
| Max zmiana budżetu per akcja | 30% |
| Max % keywords paused/dzień/kampania | 20% |
| Max negatywów dodanych/dzień | 100 |
| Max akcji w jednym batchu | 50 |

### Limity per klient

W Ustawieniach (ekran Settings) możesz nadpisać limity globalne dla konkretnego klienta — np. ustawić max zmianę stawki na 30% zamiast 50%.

---

## 9. Cofanie akcji (Revert)

Cofanie jest dostępne w ekranie **Historia akcji** (przycisk „Cofnij").

### Warunki cofnięcia

- Akcja musi mieć **mniej niż 24 godziny**
- Status akcji musi być **SUCCESS**
- Akcja **nie była już cofnięta**

### Co cofnięcie robi

| Typ akcji | Cofnięcie |
|-----------|-----------|
| PAUSE_KEYWORD | Ponowne włączenie keywordu (ENABLE) |
| UPDATE_BID | Przywrócenie poprzedniej stawki |
| ADD_KEYWORD | Pauzowanie dodanego keywordu |
| ADD_NEGATIVE | **Niemożliwe do cofnięcia** — usunięcie negative'a ponownie włączyłoby niechciany ruch |

---

## 10. Ustawienia klienta

Ekran **Ustawienia** (ikona koła zębatego) zawiera 4 sekcje:

### Informacje ogólne
- Nazwa klienta, branża, strona WWW, Google Customer ID (tylko do odczytu), notatki

### Strategia i konkurencja
- Target audience (opis grupy docelowej)
- USP (unikalna propozycja wartości)
- Konkurencja (lista konkurentów jako tagi)

### Reguły biznesowe
- **Minimalny ROAS** — kampanie poniżej tego progu będą flagowane
- **Max budżet dzienny** — limit wydatków dziennych

### Limity bezpieczeństwa
- 6 pól z nadpisywalnymi limitami (puste = wartość globalna):
  - Max zmiana stawki (%)
  - Max zmiana budżetu (%)
  - Min stawka (USD)
  - Max stawka (USD)
  - Max pause keywords/dzień (%)
  - Max negatywów/dzień

---

## 11. Eksport danych

Dostępne eksporty (format XLSX):

| Eksport | Co zawiera |
|---------|-----------|
| **Wyszukiwane frazy** | Search terms z metrykami (clicks, cost, conversions, CTR, ROAS) i segmentacją (HIGH_PERFORMER/WASTE/IRRELEVANT/OTHER) |
| **Słowa kluczowe** | Keywords z metrykami, Quality Score, match type, bidami, impression share |
| **Metryki dzienne** | Dzienne metryki kampanii: data, kampania, impressions, clicks, cost, conversions, ROAS, CPC, CTR |
| **Rekomendacje** | Lista rekomendacji z priorytetem, typem, statusem, datą utworzenia i zastosowania |

Pliki pobierają się bezpośrednio do folderu Downloads.

---

## 12. Rozwiązywanie problemów

### „Invalid developer token"
- Sprawdź status na https://ads.google.com/aw/apicenter
- Jeśli „In Review" — czekaj na zatwierdzenie (do 48h)
- Jeśli „Approved" — sprawdź literówki, spacje na początku/końcu

### „Invalid client_id" lub „client_secret"
- Wróć do Google Cloud Console → Credentials
- Skopiuj ponownie OAuth Desktop client credentials
- Wprowadź przez kreator logowania

### „Customer not found"
- Login Customer ID musi być **bez myślników** (np. `1234567890`, nie `123-456-7890`)
- Sprawdź czy Twoje konto Google ma dostęp do tego Customer ID
- Jeśli używasz MCC → podaj ID MCC (nie sub-klienta)

### Sync pokazuje „0 rows synced"
- Sprawdź czy w koncie Google Ads istnieją kampanie
- Poczekaj 30 sekund i spróbuj ponownie
- Sprawdź logi: `logs/app.log`

### Rekomendacje się nie generują
- Upewnij się, że sync przebiegł poprawnie (status „completed")
- Sprawdź czy wybrany klient ma dane w bazie (kampanie, keywords)
- Niektóre reguły wymagają minimalnych progów danych (np. R1 wymaga ≥30 kliknięć)

### Nie można zastosować rekomendacji
- Sprawdź czy aplikacja jest zalogowana (`/auth/status`)
- Sprawdź limity bezpieczeństwa — akcja może być zablokowana przez circuit breaker
- Alert (kategoria ALERT) nie ma przycisku „Zastosuj" — to informacja diagnostyczna

---

## 13. Architektura techniczna

Sekcja dla deweloperów przejmujących projekt.

### Stack technologiczny

| Warstwa | Technologia |
|---------|------------|
| Backend | Python 3.10+, FastAPI, SQLAlchemy, Pydantic v2 |
| Frontend | React 18, Vite, TailwindCSS, Recharts, TanStack Table |
| Baza danych | SQLite (lokalna, plik `.db`) |
| Desktop wrapper | PyWebView (okno natywne Windows) |
| Dystrybucja | PyInstaller → `.exe` |
| Tokeny | Windows Credential Manager (`keyring`) |

### Struktura katalogów

```
google-ads-helper/
├── main.py                   # PyWebView entry point
├── backend/app/
│   ├── main.py               # FastAPI app + router registration
│   ├── config.py             # Ustawienia (.env)
│   ├── database.py           # SQLAlchemy engine + sesja
│   ├── seed.py               # Seeder demo danych
│   ├── models/               # 14 modeli ORM (SQLAlchemy)
│   ├── schemas/              # Walidacja Pydantic v2
│   ├── routers/              # 12 routerów FastAPI
│   ├── services/             # Logika biznesowa
│   └── utils/                # Stałe, formattery
├── frontend/src/
│   ├── App.jsx               # Router + Layout
│   ├── api.js                # Axios (baseURL: /api/v1)
│   ├── contexts/             # AppContext, FilterContext
│   ├── components/           # Komponenty UI
│   ├── pages/                # 14 stron
│   └── hooks/                # Custom hooks
├── data/                     # SQLite DB (gitignored)
└── logs/                     # Logi aplikacji (gitignored)
```

### Hierarchia importów (warstwy)

Importy mogą iść TYLKO w dół — nigdy w górę ani cyklicznie:

```
utils → config → models → schemas → services → routers → app/main.py
```

Np. `services/` może importować `models/` i `schemas/`, ale **nigdy** `routers/`.

### Jak dodać nowy endpoint

1. Dodaj metodę w odpowiednim serwisie (`services/`)
2. Dodaj route w odpowiednim routerze (`routers/`)
3. Jeśli potrzeba nowego modelu — dodaj w `models/`, zaktualizuj `models/__init__.py`
4. Zmiana schematu DB → wymaga usunięcia `.db` + reseed (brak migracji)

### Jak dodać nową regułę rekomendacji

1. Dodaj typ do `RecommendationType` enum w `services/recommendations.py`
2. Dodaj progi do `DEFAULT_THRESHOLDS`
3. Zaimplementuj metodę `_rule_N_nazwa()` w klasie `RecommendationsEngine`
4. Dodaj wywołanie w `generate_all()`
5. Jeśli typ jest wykonywalny → obsłuż w `_build_suggested_action()` w `routers/recommendations.py`

### Komendy deweloperskie

```bash
# Backend (dev mode z auto-reload)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (dev mode z HMR)
cd frontend && npm run dev

# Pełna aplikacja (PyWebView)
python main.py

# Reseed bazy danych
cd backend && rm data/google_ads_app.db
PYTHONIOENCODING=utf-8 python -m app.seed

# Build .exe
pyinstaller --onefile --windowed main.py
```

---

## 14. Baza danych i logi

### Baza danych (SQLite)

| Parametr | Wartość |
|----------|---------|
| Lokalizacja (z `backend/`) | `backend/data/google_ads_app.db` |
| Lokalizacja (z roota) | `data/google_ads_app.db` |
| Migracje | **Brak** (no Alembic) |
| Reset bazy | Usuń plik `.db` → uruchom seeder |

**Tabele:** `clients`, `campaigns`, `ad_groups`, `keywords`, `keywords_daily`, `ads`, `search_terms`, `recommendations`, `action_logs`, `alerts`, `metrics_daily`, `metrics_segmented`, `change_events`

#### Wartości monetarne

Wszystkie kwoty (cost, bid, budget, conversion_value) przechowywane w **micros** — wartość × 1 000 000.
Np. $5.23 = `5_230_000` w bazie. Konwersja na USD następuje dopiero w warstwie API (schemas).

#### Reseed (odtworzenie demo danych)

```bash
cd backend
rm data/google_ads_app.db       # Usuń starą bazę
PYTHONIOENCODING=utf-8 python -m app.seed
```

Seeder tworzy 3 demo klientów z kampaniami, keywords, search terms, metrykami dziennymi (90 dni) i segmented metrics.

### Logi

| Parametr | Wartość |
|----------|---------|
| Lokalizacja | `logs/app.log` |
| Format | Loguru (timestamp + level + message) |
| Rotacja | Automatyczna (rozmiar pliku) |
| Co loguje | Błędy API, sync, akcje, wyjątki |

Logi są pierwszym miejscem do sprawdzenia, jeśli coś nie działa — zwłaszcza błędy synchronizacji z Google Ads API.

---

## 15. Słowniczek pojęć Google Ads

| Skrót / Pojęcie | Pełna nazwa | Opis |
|-----------------|-------------|------|
| **CPC** | Cost Per Click | Koszt za kliknięcie |
| **CTR** | Click-Through Rate | Współczynnik klikalności = clicks ÷ impressions × 100% |
| **CPA** | Cost Per Acquisition | Koszt za konwersję = cost ÷ conversions |
| **CVR** | Conversion Rate | Współczynnik konwersji = conversions ÷ clicks × 100% |
| **ROAS** | Return On Ad Spend | Zwrot z wydatków reklamowych = conversion_value ÷ cost |
| **QS** | Quality Score | Wynik Jakości (1–10) — ocena Google jakości keywordu |
| **IS** | Impression Share | Udział w wyświetleniach — % aukcji w których pojawiliśmy się |
| **MCC** | My Client Center | Konto menedżerskie Google Ads (agreguje wiele kont) |
| **GAQL** | Google Ads Query Language | Język zapytań do Google Ads API |
| **Micros** | — | Jednostka walutowa Google Ads: $1.00 = 1 000 000 micros |
| **Keyword** | Słowo kluczowe | Fraza, na którą licytujesz w kampanii |
| **Search Term** | Wyszukiwana fraza | To co użytkownik faktycznie wpisał w Google |
| **Negative** | Wykluczenie | Keyword, na który NIE chcesz się wyświetlać |
| **Match Type** | Typ dopasowania | EXACT (dokładne), PHRASE (do frazy), BROAD (przybliżone) |
| **SEARCH** | Kampania w wyszukiwarce | Klasyczna kampania tekstowa Google |
| **PMax** | Performance Max | Kampania automatyczna Google (wszystkie kanały) |
| **Ad Group** | Grupa reklam | Zbiór keywords + reklam wewnątrz kampanii |
| **RSA** | Responsive Search Ad | Elastyczna reklama w wyszukiwarce (wiele nagłówków/opisów) |
| **IS Lost (Budget)** | — | Procent aukcji utraconych z powodu zbyt niskiego budżetu |
| **IS Lost (Rank)** | — | Procent aukcji utraconych z powodu niskiej pozycji (Ad Rank) |
| **N-gram** | — | Fragment frazy: 1-gram = jedno słowo, 2-gram = dwa słowa itd. |
| **Circuit Breaker** | — | Mechanizm bezpieczeństwa blokujący zbyt agresywne zmiany |
| **Dayparting** | — | Analiza wyników w rozbiciu na godziny dnia / dni tygodnia |

---

## Dokumentacja techniczna — dodatkowe pliki

Dla deweloperów i zaawansowanych użytkowników dostępne są:

| Plik | Zawartość |
|------|-----------|
| `CLAUDE.md` | Pełna architektura, reguły, schemat DB, endpointy API |
| `PROGRESS.md` | Stan implementacji, co zrobione, co dalej |
| `DECISIONS.md` | Decyzje architektoniczne (12 ADRów) |
| `CHECKLIST_TO_ENGINE_PLAN.md` | Plan rozszerzenia engine'u z 7 do 21 reguł |
| `JAK_ZDOBYC_CREDENTIALS.md` | Poradnik konfiguracji Google Ads API |
