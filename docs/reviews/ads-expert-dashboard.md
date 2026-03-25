# Ocena eksperta Google Ads — Pulpit (Dashboard)
> Data: 2026-03-25 | Srednia ocena: 8.5/10 | Werdykt: ZMODYFIKOWAC

## TL;DR
Pulpit to solidna, dobrze zaprojektowana strona startowa ktora pokrywa kluczowe potrzeby codziennego przegladu konta. Daje realną wartość ponad natywny Google Ads UI dzięki Health Score, automatycznym insightom i pacing budżetu w jednym widoku. Brakuje kilku krytycznych elementów wymienionych w playbooku.

## Oceny
| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebnosc | 9/10 | Dashboard to absolutny must-have — specjalista zaczyna od niego każdy dzień. Playbook sekcja 1.1 "Daily Checks" mapuje się bezpośrednio na tę zakładkę |
| Kompletnosc | 7/10 | 8 endpointów, bogate dane — ale brakuje Impressions i CTR w KPI cards, brakuje CPA. Tabela kampanii nie pokazuje metryk performance (clicks, cost, conv) |
| Wartosc dodana vs Google Ads UI | 8/10 | Health Score, InsightsFeed, Budget Pacing, Device+Geo w jednym widoku — Google Ads nie ma takiego "single pane of glass" |
| Priorytet MVP | 10/10 | Absolutnie pierwsza strona którą specjalista otwiera. Bez dashboardu aplikacja nie ma sensu |
| **SREDNIA** | **8.5/10** | |

## Co robi dobrze
- **Health Score** (Dashboard.jsx:36-111) — unikalny element, Google Ads tego nie ma. Circular gauge z listą issues daje natychmiastowy "pulse check" konta. Playbook sekcja 5.1 Anomaly Detection jest tu pokryta
- **4 KPI cards z % change** (Dashboard.jsx:295-327) — Kliknięcia, Koszt, Konwersje, ROAS z porównaniem do poprzedniego okresu. Odpowiada na playbook 2.1 "Kluczowe Metryki" i 3.1 "Pull Yesterday's Data"
- **InsightsFeed** (InsightsFeed.jsx) — automatyczne rekomendacje z priorytetyzacją HIGH/MEDIUM/LOW, filtrowane po źródle ANALYTICS. Realizuje playbook 5.3 "Automated Recommendations"
- **TrendExplorer** (TrendExplorer.jsx) — multi-metric charting z korelacją, 9 dostępnych metryk, dual Y-axis. Pokrywa playbook 1.1 "Performance Analysis" i 4.2 "Correlation Matrix"
- **Budget Pacing** (Dashboard.jsx:431-465) — status on_track/underspend/overspend per kampania z progress bar. Realizuje playbook daily check #1 "Sprawdzenie wydatku"
- **Device + Geo breakdown** (Dashboard.jsx:467-604) — z rozwijalnymi trendami per device. Pokrywa playbook weekly "Audience Analysis" / segmentacja po devices i locations
- **Polskie UI labels** — "Kliknięcia", "Koszt", "Konwersje", "Ładowanie…", "Brak kampanii dla wybranych filtrów"
- **Filtrowanie z FilterContext** — campaign_type, status, period/date range działają globalnie

## Co brakuje (krytyczne)

### K1: Brak Impressions i CTR w KPI cards
Specjalista Google Ads sprawdza te metryki codziennie. 4 karty to za mało, playbook wymienia 7 podstawowych KPI (CTR, CPC, CVR, CPA, ROAS, Impr. Share, QS). Endpoint `dashboard-kpis` zwraca `impressions` i `ctr` ale frontend ich nie wyświetla.
- Playbook ref: Sekcja 2.1 "Kluczowe Metryki"
- Implementacja: Dodać CTR i CPA do KPI cards (dane już dostępne z backendu), albo zrobić 2 rzędy po 4 karty

### K2: Brak CPA (Cost Per Acquisition) w KPI
To metryka #1 dla lead gen klientów. Backend nie liczy CPA wprost ale ma cost i conversions.
- Playbook ref: Sekcja 2.1 — "CPA: Cost Per Acquisition < target CPA"
- Implementacja: Obliczyć `cost / conversions` w froncie lub dodać do endpointu

### K3: Tabela kampanii nie pokazuje metryk wydajności
Wyświetla tylko Nazwę, Status, Typ, Budżet/dzień, Trend (sparkline), Strategię. Brakuje: Clicks, Cost, Conversions, CTR, ROAS per kampania. Specjalista musi widzieć *które kampanie generują wyniki* bez przechodzenia do /campaigns.
- Playbook ref: Sekcja 3.1 "Daily Check" → "Identyfikacja anomalii" per campaign
- Implementacja: Dodać kolumny Cost, Conversions, ROAS do tabeli (dane trzeba dociągnąć z metrics lub osobnego endpointu)

### K4: Brak szybkich akcji z dashboardu
Specjalista widzi problem w InsightsFeed ale nie może nic zrobić bez nawigacji do innej zakładki. "One-click apply recommendation" jest w playbooku (5.3).
- Playbook ref: Sekcja 5.3 "One-click apply recommendation"
- Implementacja: InsightsFeed mógłby mieć przycisk "Zastosuj" lub "Przejdź do rekomendacji"

## Co brakuje (nice to have)

### N1: Impression Share / Lost IS (Budget)
Playbook sekcja 2.1 wymienia Search Lost IS (Budget) i Lost IS (Rank) jako "zaawansowane metryki". Pozwalają odpowiedzieć na pytanie "czy tracimy udział w aukcjach?" Obecnie brak w API i UI.

### N2: Wasted Spend indicator
Playbook 2.1: "Wasted Spend: Spend bez conversions < 20% total spend". Prosta metryka, dużo wartości.

### N3: Porównanie WoW (Week over Week)
KPI cards pokazują % vs poprzedni okres, ale brak wizualnego WoW comparison chart. Playbook weekly "Porównanie Last 7 days vs Previous 7 days".

### N4: Quick filters na dashboardzie
Np. "pokaż tylko kampanie z problemami" albo "pokaż tylko SEARCH".

## Co usunac/zmienic

### Z1: Sparkline w tabeli kampanii ma ograniczoną wartość
Dashboard.jsx:411-414 — malutki wykres 72x24px bez osi Y i wartości. Specjalista nie wyciągnie z niego insightów. Lepiej zamienić na kolumnę z cost/conversions za dany okres.

### Z2: Geo "Top miasta" — ograniczona przydatność
Wartościowe dla lokalnych biznesów, ale dla krajowych kampanii 8 miast bez kontekstu (% total) jest mało przydatne. Rozważyć dodanie share_cost_pct (dane są w API) albo zmienić na mapę/heatmapę.

## Porownanie z Google Ads UI
| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Przegląd KPIs | Overview tab — 6+ metryk, customizable | 4 KPI cards + Health Score | GORSZE (mniej metryk) ale Health Score daje wartość dodaną |
| Trend chart | Customizable chart, 1 metryka na raz | TrendExplorer — multi-metric z korelacją | LEPSZE |
| Lista kampanii | Pełna tabela ze wszystkimi metrykami, sortowalna | Uproszczona tabela — brak clicks/cost/conv | GORSZE |
| Budget pacing | Brak natywnego pacing view | Dedykowana sekcja z progress bars | LEPSZE |
| Device breakdown | Reports > Devices — osobna zakładka | Inline na dashboardzie z trendami | LEPSZE |
| Geo breakdown | Reports > Locations — osobna zakładka | Inline na dashboardzie | LEPSZE ale uproszczone |
| Automated insights | Recommendations tab — algorytmy Google | InsightsFeed — własne reguły z playbooka | IDENTYCZNE koncepcyjnie |
| Health Score | Optimization Score (0-100%) | Health Score (0-100) z issues | LEPSZE — bardziej przejrzysty |

## Nawigacja i kontekst
- Skąd user trafia: Domyślna strona po zalogowaniu (`/` route). Sidebar: "Pulpit" w sekcji PRZEGLĄD
- Dokąd powinien móc przejść: Kliknięcie kampanii → /campaigns, Kliknięcie insightu → /recommendations, Kliknięcie "więcej alertów" → /alerts
- Brakujące połączenia:
  - Brak kliknięcia na kampanię w tabeli (nawigacja do /campaigns z filtrem)
  - Brak linku z InsightsFeed do /recommendations z podświetlonym insightem
  - Brak linku z Health Score do /alerts
  - Brak "Zobacz wszystkie" na Budget Pacing, Device, Geo sekcjach

## Rekomendacja koncowa
ZMODYFIKOWAC

Dashboard jest najważniejszą zakładką aplikacji i jest solidnie zbudowany. Główne modyfikacje: (1) dodać CTR i CPA do KPI cards — 10 min pracy, dane już w API, (2) dodać kolumny performance do tabeli kampanii — wymaga dociągnięcia danych z metrics, (3) dodać nawigację kliknięciami (kampania → /campaigns, insight → /recommendations, health → /alerts). Te 3 zmiany podniosłyby ocenę kompletności z 7 do 9/10.
