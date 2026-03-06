# PLAN.md — Roadmap rozwoju Google Ads Helper

Dokument powstal na podstawie analizy zewnetrznej (strukturaodgpt.md) vs aktualny stan projektu.
Aktualizacja: 2026-03-06

---

## STATUS OBECNY: V1 MVP — dziala z prawdziwymi danymi Google Ads

Aplikacja posiada:
- 7-fazowy sync pipeline (campaigns, ad groups, keywords, keyword daily, metrics daily, search terms, PMax terms)
- 14 modeli ORM, 12 routerow, 15+ endpointow analitycznych
- 7 regul rekomendacji + action executor z circuit breakerem
- Revert (undo) zmian w kampaniach
- Anomaly detection + alerty
- Desktop wrapper (PyWebView) + planowany build .exe

---

## ANALIZA: CO ROBIMY DOBRZE

| Obszar | Status | Komentarz |
|--------|--------|-----------|
| Multi-client (agency ready) | DONE | Client model + auto-discover z MCC |
| Daily Sync Pipeline | DONE | 7 faz, upsert logic, bledy nie crashuja calego synca |
| Campaign Daily Metrics | DONE | MetricDaily — naprawione 2026-03-06 |
| Keyword Daily Metrics | DONE | KeywordDaily z historia (90 dni w demo, 30 dni real) |
| Search Terms Segmentation | DONE | 4 segmenty (IRRELEVANT, HIGH_PERFORMER, WASTE, OTHER) |
| Quality Score Monitor | DONE | QS audit dashboard + alerty QS < 5 |
| Wasted Spend Detector | DONE | Analiza keywords, search terms, ads z 0 konwersji |
| Performance Alerts | DONE | Anomaly detection (spend spike, conversion drop, CTR drop) |
| Device Breakdown | DONE | MetricSegmented na poziomie kampanii |
| Action Executor | DONE | Apply/Revert z safety limits (circuit breaker) |
| Semantic Clustering | DONE | Grupowanie slow kluczowych tematycznie |
| SEARCH Optimization | DONE | 6 analiz (dayparting, RSA, n-gram, match type, landing pages, wasted spend) |

---

## CO BRAKUJE — PLAN IMPLEMENTACJI

### V1.1 — Szybkie wygrane (male zmiany, duza wartosc)

#### 1. Sync Log — historia synchronizacji
**Problem:** Nie wiadomo kiedy ostatni sync sie odbyl, ile rekordow pobral, czy mialy bledy.
**Rozwiazanie:** Nowa tabela `sync_logs`:
```
sync_logs
---------
id (pk)
client_id (fk -> clients)
sync_type          -- "full" | "incremental"
status             -- "running" | "success" | "partial" | "failed"
phases             -- JSON: {campaigns: 3, keywords: 128, metrics: 87, ...}
error_message      -- NULL jesli sukces
started_at
finished_at
```
**Wysilek:** Maly (1 model, zmiana w sync.py)
**Wartosc:** Wysoka — debugowanie, audyt, UX (pokazanie "ostatni sync: 2h temu")

#### 2. Currency na Client model
**Problem:** Hardcoded "zl" w UI. Przy klientach z innymi walutami dane sa mylace.
**Rozwiazanie:** Dodac `currency` (String, default "PLN") do Client model. Frontend czyta walute z klienta.
**Wysilek:** Minimalny
**Wartosc:** Srednia — konieczne przy multi-currency accounts

#### 3. Negative Keywords z konta
**Problem:** Rekomendujemy dodanie negatywow, ale nie widzimy jakie juz sa na koncie.
**Rozwiazanie:** Nowa tabela `negative_keywords`:
```
negative_keywords
-----------------
id (pk)
campaign_id (fk)
ad_group_id (fk, nullable)  -- NULL = campaign-level negative
keyword_text
match_type                   -- EXACT | PHRASE | BROAD
source                       -- "SYNCED" | "HELPER_ADDED"
created_at
```
Nowa faza synca: Phase 7 — sync negative keywords z Google Ads API.
**Wysilek:** Maly
**Wartosc:** Srednia — audyt negatywow, unikanie blokowania dobrego ruchu

#### 4. Scheduled Sync (timer)
**Problem:** Sync jest tylko reczny (przycisk w UI). Latwo zapomniec.
**Rozwiazanie:** Background timer w Pythonie (np. APScheduler) — sync co 6h lub raz dziennie.
Konfiguracja w Settings: wlacz/wylacz auto-sync, ustaw interwat.
**Wysilek:** Sredni
**Wartosc:** Srednia — dane zawsze aktualne bez interwencji

---

### V2 — Architektura analityczna (wieksze zmiany)

#### 5. Landing Pages jako osobna encja + daily metrics
**Problem:** Analiza LP oparta na keyword.final_url — brak historii, brak osobnej encji.
**Rozwiazanie:**
```
landing_pages
--------------
id (pk)
client_id (fk)
url
domain
path
first_seen
last_seen

landing_page_metrics_daily
--------------------------
id (pk)
landing_page_id (fk)
date
impressions
clicks
cost_micros
conversions
conversion_value_micros
conversion_rate
```
Sync: Agregacja z keyword_daily + final_url → landing_page_metrics_daily.
**Wysilek:** Sredni
**Wartosc:** Wysoka — "ktory LP zabija kampanie" to kluczowa analiza PPC

#### 6. Search Term Daily Metrics (dimension/fact split)
**Problem:** SearchTerm laczy encje i metryki w jednej tabeli z date_from/date_to.
Nie mozna sledzic jak performance search termu zmienia sie dzien po dniu.
**Rozwiazanie:**
```
search_terms (dimension — encja)
-------------
id (pk)
client_id (fk)
text
first_seen
last_seen
segment                  -- IRRELEVANT, HIGH_PERFORMER, WASTE, OTHER

search_term_metrics_daily (fact — metryki)
-------------------------
id (pk)
search_term_id (fk)
keyword_id (fk, nullable)
campaign_id (fk)
date
impressions
clicks
cost_micros
conversions
conversion_value_micros
```
**Wysilek:** Duzy (przebudowa modelu, synca, routerow, frontendu)
**Wartosc:** Wysoka — prawdziwa analiza trendow search termow w czasie

#### 7. Geo Metrics (naprawa)
**Problem:** sync_geo_metrics() wylaczony — GAQL query uzywa `segments.geo_target_city`
ktory nie jest kompatybilny z zasobem CAMPAIGN.
**Rozwiazanie:** Uzyc `geographic_view` zamiast `campaign` w FROM clause.
```sql
SELECT
    campaign.id,
    geographic_view.country_criterion_id,
    geographic_view.location_type,
    segments.date,
    metrics.clicks, metrics.impressions, metrics.cost_micros, metrics.conversions
FROM geographic_view
WHERE segments.date BETWEEN '...' AND '...'
```
**Wysilek:** Sredni (zmiana GAQL + parsowanie geo resource names)
**Wartosc:** Srednia — geo performance analysis

---

### V3 — Zaawansowane funkcje (przyszlosc)

#### 8. Ad Daily Metrics
Dzienne metryki per reklama — sledzenie CTR/konwersji reklam w czasie.
```
ad_metrics_daily
----------------
date, ad_id, impressions, clicks, cost_micros, conversions
```

#### 9. Ad Group Daily Metrics
Dzienne metryki per ad group.
```
ad_group_metrics_daily
----------------------
date, ad_group_id, impressions, clicks, cost_micros, conversions
```

#### 10. API Rate Tracking
Monitorowanie zuzycia Google Ads API.
```
api_usage
---------
date, client_id, endpoint, requests_count
```

#### 11. Device Breakdown na poziomie keyword
Obecnie device breakdown jest na poziomie kampanii.
Rozszerzenie do keyword-level da precyzyjniejsza optymalizacje.

#### 12. Audience Performance (PMax)
Metryki per audience segment dla kampanii PMax.

#### 13. Agent System (AI)
Podzial pracy AI na specjalizowanych agentow:
- Agent 1: Data Sync + Quality Check
- Agent 2: Analiza danych + anomaly detection
- Agent 3: Strategia + rekomendacje
To jest kierunek "Google Ads Intelligence Platform".

---

## ZASADY ARCHITEKTONICZNE (z analizy GPT — przyjmujemy)

### Dimension vs Fact tables
Kazda nowa encja powinna miec:
- **Dimension table** — encja (keyword, search_term, landing_page)
- **Fact table** — metryki dzienne (keyword_metrics_daily, search_term_metrics_daily)

Nie laczyc encji z metrykami w jednej tabeli (blad SearchTerm model — do naprawy w V2).

### Data Flow
```
Google Ads API
    |
    v
Sync Worker (Python)
    |
    v
Database (SQLite -> PostgreSQL w przyszlosci)
    |
    v
Analysis Engine (Python services)
    |
    v
REST API (FastAPI)
    |
    v
Frontend (React)
```

Frontend NIGDY nie odpytuje Google Ads API bezposrednio.

### Indeksy
Najwieksze tabele (keyword_metrics_daily, search_term_metrics_daily, landing_page_metrics_daily):
- `INDEX (date)`
- `INDEX (entity_id)` — keyword_id, search_term_id, etc.
- `INDEX (campaign_id)` — dla filtrow

---

## CZEGO GPT NIE UWZGLEDNIL (nasza przewaga)

| Funkcja | Opis |
|---------|------|
| Action Executor + Circuit Breaker | Bezpieczne zapisy do Google Ads z limitami |
| Revert (Undo) | Cofanie zmian (24h window) |
| 7 regul rekomendacji | Automatyczne wykrywanie optymalizacji |
| Semantic Clustering | Grupowanie slow kluczowych tematycznie |
| N-gram / RSA / Match Type Analysis | Zaawansowane analizy SEARCH |
| Budget Pacing | Monitorowanie wydatkow vs budzet |
| Forecast | Prognozowanie metryk |
| Change Event History | Historia zmian (Google + Helper) |
| PyWebView Desktop | Natywna aplikacja Windows (.exe) |

GPT zaproponowal dashboard do czytania danych.
My mamy narzedzie ktore DZIALA na kontach (apply/revert) — to jest fundamentalna roznica.

---

## PRIORYTET IMPLEMENTACJI

```
TERAZ (V1 — stabilizacja):
  [x] Naprawic sync_daily_metrics (conversions_value_per_cost incompatible)
  [x] Naprawic 10 frontend bugow z real data
  [x] Naprawic campaign KPIs 500 error
  [ ] Przetestowac wszystkie widoki z prawdziwymi danymi
  [ ] PyWebView test
  [ ] PyInstaller build (.exe)

NASTEPNE (V1.1 — szybkie wygrane):
  [ ] Sync Log
  [ ] Currency na Client
  [ ] Negative Keywords sync
  [ ] Scheduled sync (auto)

POZNIEJ (V2 — architektura analityczna):
  [ ] Landing Pages entity + daily metrics
  [ ] Search Term dimension/fact split
  [ ] Geo Metrics fix (geographic_view)
  [ ] PostgreSQL migration (jesli SaaS)

PRZYSZLOSC (V3):
  [ ] Ad Daily Metrics
  [ ] Ad Group Daily Metrics
  [ ] Device breakdown per keyword
  [ ] Agent System (AI)
  [ ] Prediction engine
```
