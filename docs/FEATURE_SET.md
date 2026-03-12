# Feature Set - Google Ads Helper v1

Kompletna lista aktualnych funkcjonalnosci aplikacji.
Ten dokument opisuje stan biezacy produktu (nie snapshot historyczny).

---

## 1. Core MVP Lane

Core value path:
`sync -> insight -> apply/revert -> history`

Oficjalne pozycjonowanie (stan biezacy):
- execution-ready (po green testach write-flow i API contract)

Moduly advanced (semantic, forecast, optimization, monitoring) sa expansion layer, a nie rdzen MVP.

---

## 2. Sync (Google Ads API)

| Faza | Co syncuje | Zrodlo GAQL | Uwagi |
|------|-----------|-------------|-------|
| Campaigns | Kampanie (nazwa, typ, status, budzet) | `campaign` | Wszystkie typy |
| Impression Share | Udzial w wyswietleniach per kampania | `campaign` | Faza 1b |
| Ad Groups | Grupy reklam | `ad_group` | Pomijane jesli campaigns fail |
| Keywords | Slowa kluczowe + QS + bid | `keyword_view` | Pomijane jesli ad_groups fail |
| Keyword Daily | Metryki dzienne per keyword | `keyword_view` | Agregacja po dacie |
| Daily Metrics | Metryki dzienne per kampania | `campaign` | cost, clicks, impressions, conversions, ROAS |
| Device Metrics | Segmentacja po urzadzeniu | `campaign` | MOBILE/DESKTOP/TABLET |
| Geo Metrics | Segmentacja po miastach | `geographic_view` | Auto-resolve geo names |
| Search Terms (SEARCH) | Frazy z kampanii SEARCH | `search_term_view` | Upsert po (text, ad_group_id, date range) |
| Search Terms (PMAX) | Frazy z PMax | `campaign_search_term_view` | `ad_group_id` nullable, `source="PMAX"` |
| Change Events | Historia zmian konta | `change_event` | Max 28 dni (limit API) |

---

## 3. Recommendation Engine (17 aktywnych regul)

Aktywne reguly: **R1-R13, R15-R18**.
R14: celowo nieaktywna (poza zakresem implementacji).

### Mapa regul

| Rule ID | Type | Category | Executable |
|---------|------|----------|------------|
| R1 | `PAUSE_KEYWORD` | `RECOMMENDATION` | yes |
| R2 | `INCREASE_BID` | `RECOMMENDATION` | yes |
| R3 | `DECREASE_BID` | `RECOMMENDATION` | yes |
| R4 | `ADD_KEYWORD` | `RECOMMENDATION` | yes |
| R5 | `ADD_NEGATIVE` | `RECOMMENDATION` | yes |
| R6 | `PAUSE_AD` | `RECOMMENDATION` | yes |
| R7 | `REALLOCATE_BUDGET` | `RECOMMENDATION` | yes |
| R8 | `QS_ALERT` | `ALERT` | no |
| R9 | `IS_BUDGET_ALERT` | `RECOMMENDATION` | yes |
| R10 | `IS_RANK_ALERT` | `ALERT` | no |
| R11 | `PAUSE_KEYWORD` | `RECOMMENDATION` | yes |
| R12 | `WASTED_SPEND_ALERT` | `ALERT` | no |
| R13 | `PMAX_CANNIBALIZATION` | `ALERT` | no |
| R15 | `DEVICE_ANOMALY` | `ALERT` | no |
| R16 | `GEO_ANOMALY` | `ALERT` | no |
| R17 | `BUDGET_PACING` | `ALERT` | no |
| R18 | `NGRAM_NEGATIVE` | `RECOMMENDATION` | yes |

---

## 4. Write Actions i Safety

- Apply: `POST /recommendations/{id}/apply?client_id=X&dry_run=false`
- Revert: `POST /actions/revert/{action_log_id}?client_id=X`
- Circuit breaker: `validate_action()` przed kazdym write
- Safety limits: max bid/budget change, pause limits, negatives/day
- Action history: statusy `SUCCESS`, `FAILED`, `REVERTED`

---

## 5. Strony Frontendu (15)

1. Dashboard
2. Clients
3. Campaigns
4. Keywords
5. Search Terms
6. Recommendations
7. Action History
8. Alerts
9. Settings
10. Quality Score
11. Forecast
12. Semantic
13. Anomalies
14. Search Optimization
15. Login

---

## 6. Metryki Projektu

- 15 modeli ORM (+ SyncLog)
- 12 routerow API
- 15 stron frontend
- 14+ komponentow UI
- 17 aktywnych regul recommendation engine
- 11 faz sync


