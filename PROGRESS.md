# PROGRESS.md â€” Stan implementacji
# Aktualizacja: 2026-03-03
# Claude Code: czytaj ten plik, aby wiedziec co jest gotowe, a co pozostalo.

---

## STATUS: đźź˘ MVP ZBUDOWANY â€” Backend gotowy, Frontend gotowy, integracja w toku

---

## BACKEND â€” âś… KOMPLETNY

### Infrastruktura (Phase 1) â€” âś… DONE
| Element | Plik(i) | Status |
|---------|---------|--------|
| Katalogi + __init__.py | cale drzewo backend/app/ | âś… |
| Python dependencies | requirements.txt | âś… |
| Logger | loguru (bezposredni import) | âś… |
| Constants + Safety Limits | utils/constants.py | âś… |
| Formatters (micros) | utils/formatters.py | âś… |
| Config (pydantic-settings) | config.py | âś… |
| Database (SQLAlchemy + SQLite) | database.py | âś… |
| Seed data (demo) | seed.py | âś… |

### Modele ORM (Phase 1) â€” âś… DONE (15 modeli)
| Model | Plik | Status |
|-------|------|--------|
| Client | models/client.py | âś… |
| Campaign | models/campaign.py | âś… |
| AdGroup | models/ad_group.py | âś… |
| Keyword | models/keyword.py | âś… |
| KeywordDaily | models/keyword_daily.py | âś… |
| Ad | models/ad.py | âś… |
| SearchTerm | models/search_term.py | âś… |
| Recommendation | models/recommendation.py | âś… |
| ActionLog | models/action_log.py | âś… |
| Alert | models/alert.py | âś… |
| MetricDaily | models/metric_daily.py | âś… |
| MetricSegmented | models/metric_segmented.py | âś… |
| ChangeEvent | models/change_event.py | âś… |
| SyncLog | models/sync_log.py | âś… |

### Schemas Pydantic v2 (Phase 1) â€” âś… DONE
| Schema | Plik | Status |
|--------|------|--------|
| Common (enums) | schemas/common.py | âś… |
| Client | schemas/client.py | âś… |
| Campaign | schemas/campaign.py | âś… |
| Keyword | schemas/keyword.py | âś… |
| Ad | schemas/ad.py | âś… |
| SearchTerm | schemas/search_term.py | âś… |
| Recommendation | schemas/recommendation.py | âś… |
| Analytics | schemas/analytics.py | âś… |
| ChangeEvent | schemas/change_event.py | âś… |

### Serwisy (Phase 2-3) â€” âś… DONE
| Serwis | Plik | Status |
|--------|------|--------|
| Credentials (keyring) | services/credentials_service.py | âś… |
| Google Ads (GAQL + sync) | services/google_ads.py | âś… |
| Recommendations Engine (17 regul aktywnych: R1-R13, R15-R18) | services/recommendations.py | âś… |
| Action Executor (circuit breaker) | services/action_executor.py | âś… |
| Analytics | services/analytics_service.py | âś… |
| Search Terms Segmentation | services/search_terms_service.py | âś… |
| Semantic Clustering | services/semantic.py | âś… |
| Cache (TTL) | services/cache.py | âś… |

### Routery API (Phase 2-3) â€” âś… DONE (12 routerow)
| Router | Prefix | Plik | Status |
|--------|--------|------|--------|
| Auth | /auth | routers/auth.py | âś… |
| Clients | /clients | routers/clients.py | âś… |
| Campaigns | /campaigns | routers/campaigns.py | âś… |
| Keywords + Ads | /keywords | routers/keywords_ads.py | âś… |
| Search Terms | /search-terms | routers/search_terms.py | âś… |
| Recommendations | /recommendations | routers/recommendations.py | âś… |
| Actions | /actions | routers/actions.py | âś… |
| Analytics | /analytics | routers/analytics.py | âś… |
| Sync | /sync | routers/sync.py | âś… |
| Export | /export | routers/export.py | âś… |
| Semantic | /semantic | routers/semantic.py | âś… |
| History | /history | routers/history.py | âś… |

---

## FRONTEND â€” âś… KOMPLETNY

### Infrastruktura (Phase 4) â€” âś… DONE
| Element | Plik | Status |
|---------|------|--------|
| Vite + React 18 | package.json, vite.config.js | âś… |
| Tailwind CSS | tailwind.config.js | âś… |
| App shell + routing | App.jsx | âś… |
| Axios API client | api.js | âś… |
| Dark mode v2 design | globalnie | âś… |

### Strony (Phase 4) â€” âś… DONE (15 stron)
| Strona | Plik | Status |
|--------|------|--------|
| Dashboard | pages/Dashboard.jsx | âś… |
| Clients | pages/Clients.jsx | âś… |
| Campaigns | pages/Campaigns.jsx | âś… |
| Keywords | pages/Keywords.jsx | âś… |
| Search Terms | pages/SearchTerms.jsx | âś… |
| Recommendations | pages/Recommendations.jsx | âś… |
| Action History | pages/ActionHistory.jsx | âś… |
| Alerts | pages/Alerts.jsx | âś… |
| Settings | pages/Settings.jsx | âś… |
| Quality Score | pages/QualityScore.jsx | âś… |
| Forecast | pages/Forecast.jsx | âś… |
| Semantic | pages/Semantic.jsx | âś… |
| Anomalies | pages/Anomalies.jsx | âś… |
| Search Optimization | pages/SearchOptimization.jsx | âś… |
| Login | pages/Login.jsx | âś… |

### Komponenty (Phase 4) â€” âś… DONE
| Komponent | Plik | Status |
|-----------|------|--------|
| Sidebar | components/Sidebar.jsx | âś… |
| Charts (Recharts) | components/Charts.jsx | âś… |
| DataTable (TanStack) | components/DataTable.jsx | âś… |
| ConfirmationModal | components/ConfirmationModal.jsx | âś… |
| Toast | components/Toast.jsx | âś… |
| SegmentBadge | components/SegmentBadge.jsx | âś… |
| EmptyState | components/EmptyState.jsx | âś… |
| FilterBar | components/FilterBar.jsx | âś… |
| SyncButton | components/SyncButton.jsx | âś… |
| TrendExplorer | components/TrendExplorer.jsx | âś… |
| InsightsFeed | components/InsightsFeed.jsx | âś… |
| MetricTooltip | components/MetricTooltip.jsx | âś… |
| DiffView | components/DiffView.jsx | âś… |
| UI (shared) | components/UI.jsx | âś… |

### Contexts + Hooks â€” âś… DONE
| Element | Plik | Status |
|---------|------|--------|
| AppContext | contexts/AppContext.jsx | âś… |
| FilterContext | contexts/FilterContext.jsx | âś… |
| useClients | hooks/useClients.js | âś… |
| useRecommendations | hooks/useRecommendations.js | âś… |
| useSync | hooks/useSync.js | âś… |

---

## ZMIANY Z SESJI 2026-02-27/28

### OAuth + Credentials Setup Wizard â€” âś… DONE
- `GET /auth/setup-status` â€” sprawdza czy credentials sa skonfigurowane
- `POST /auth/setup` â€” zapisuje client_id, client_secret, developer_token, login_customer_id do keyring
- Login.jsx â€” kreator konfiguracji (krok po kroku) + przycisk "Zaloguj przez Google"
- Credentials zapisywane TYLKO w Windows Credential Manager (keyring)

### PMax Search Terms (campaign_search_term_view) â€” âś… DONE
- `sync_pmax_search_terms()` w google_ads.py â€” uzywa `campaign_search_term_view` (NIE `search_term_view`)
- WAZNE: NIE uzywac `segments.keyword.info.*` z campaign_search_term_view â€” wyfiltruje PMax
- SearchTerm model: `ad_group_id` nullable, dodane `campaign_id` (FK), `source` ("SEARCH"/"PMAX")
- Campaign model: dodana relacja `search_terms`
- search_terms router: outerjoin z or_() obsluguje oba typy (Search + PMax)
- search_terms_service: `_fetch_terms()` helper, queries obsluguja PMax
- Sync Phase 5b: sync_pmax_search_terms() po standardowym sync_search_terms()

### Sidebar â€” Client State Centralization â€” âś… DONE
- Klienci przeniesieni do AppContext (clients, clientsLoading, refreshClients)
- Sidebar.jsx uzywa useApp() zamiast osobnego useClients()
- Clients.jsx uzywa refreshClients z AppContext
- Po discover klienci od razu widoczni w dropdown

### Global Date Range Picker â€” âś… DONE
- DateRangePicker w Sidebar.jsx â€” presety (7d/14d/30d/90d) + custom date inputs
- FilterContext: dateFrom, dateTo, period (auto-sync), computed `days`
- Dashboard, Campaigns, TrendExplorer â€” uzywaja `days` z useFilter()
- SearchTerms (list + segmented) â€” wysylaja `date_from`/`date_to` do backendu
- FilterBar: period pills ukryte (hidePeriod) â€” daty sa globalne w sidebarze
- Segmented endpoint: przyjmuje `date_from`/`date_to`, przekazuje do service

### Drobne fixy
- Recommendations.jsx: key prop fallback `key={rec.id ?? \`rec-${idx}\`}`
- Clients.jsx: syncingClientId per-client zamiast globalnego boolean
- Auto-select pierwszego klienta po discover

---

## ZMIANY Z SESJI 2026-03-01

### KeywordDaily â€” metryki dzienne per keyword â€” âś… DONE
- Nowy model `KeywordDaily` (keyword_id + date â†’ clicks, impressions, cost_micros, conversions, conversion_value_micros, avg_cpc_micros)
- Router `keywords_ads.py`: dwie sciezki â€” agregacja z KeywordDaily (z date_from/date_to) vs snapshot (bez dat)
- Seed: 90 dni per keyword z trend_factor + dow_factor + noise
- Frontend Keywords.jsx: przekazuje date_from/date_to z FilterContext
- Zmiana dat w sidebarze (7d/14d/30d/90d) teraz wplywa na dane w tabeli Keywords

### SEARCH Optimization â€” 6 nowych analiz â€” âś… DONE
- Nowa strona `SearchOptimization.jsx` z 6 rozwijalnymi sekcjami
- 6 nowych metod w analytics_service.py:
  1. `get_dayparting()` â€” analiza dnia tygodnia (MetricDaily)
  2. `get_rsa_analysis()` â€” analiza RSA reklam (CTR spread, headlines)
  3. `get_ngram_analysis()` â€” n-gramy z search terms (1/2/3-gramy)
  4. `get_match_type_analysis()` â€” porownanie EXACT/PHRASE/BROAD (KeywordDaily)
  5. `get_landing_page_analysis()` â€” analiza landing pages (KeywordDaily + final_url)
  6. `get_wasted_spend()` â€” zmarnowany budzet (keywords 0 conv, search terms 0 conv, ads 0 conv)
- 6 nowych endpointow w analytics.py router
- 6 nowych funkcji API w api.js
- Sidebar: "Optymalizacja" (Zap icon) w grupie ANALIZA
- Seed: final_url per keyword, waste_kw_ids (3 keywords z 0 conversions)

---

## STRONY 100% KOMPLETNE (przetestowane, nie modyfikowac)

| Strona | Plik | Data zamkniecia |
|--------|------|-----------------|
| Dashboard (Pulpit) | pages/Dashboard.jsx | 2026-03-03 |
| Clients (Klienci) | pages/Clients.jsx | 2026-03-03 |

---

## ZMIANY Z SESJI 2026-03-03

### Auth retry przy starcie â€” âś… DONE
- AppContext `checkAuth()` â€” retry do 5Ă— z 1s przerwÄ… (backend moze startowac wolniej niz frontend)
- Login.jsx `checkSetup()` â€” retry do 3Ă— z 1s przerwÄ…
- Naprawia problem: formularz setup pokazywal sie po restarcie mimo ze credentials sa w keyring

---

## INTEGRACJA I TESTY (Phase 5) â€” đźźˇ W TOKU

| Zadanie | Status | Uwagi |
|---------|--------|-------|
| Backend <-> Frontend wiring | âś… | Vite proxy, Axios, CORS |
| Seed data + demo mode | âś… | seed.py z realistycznymi danymi |
| OAuth end-to-end | âś… | Setup wizard + Google OAuth flow |
| Sync test (live API) | âś… | 11/11 phases pass, 3 real clients tested |
| Recommendations test | â¬ś | 17 regul (R1-R13, R15-R18) - DONE (pokrycie testowe + kontrakt) |
| Apply/Revert test | â¬ś | dry_run + live - DONE (apply/revert + safety/circuit breaker) |
| PyWebView wrapper | â¬ś | main.py do przetestowania |
| PyInstaller build | â¬ś | .exe |

---

## ZNANE PROBLEMY DO NAPRAWY

| # | Problem | Priorytet | Status |
|---|---------|-----------|--------|
| 1 | CTR storage niespojne (Float vs Integer micros) miedzy modelami | MEDIUM | â¬ś |
| 2 | Dashboard secondary data â€” silent error suppression | LOW | â¬ś |
| 3 | Brak AbortController w useEffect (memory leaks) | LOW | â¬ś |
| 4 | TH_STYLE zduplikowane w 3 plikach (wyciagnac do theme.js) | LOW | â¬ś |
| 5 | Keywords maja KeywordDaily (date filtering dziala). Campaigns â€” nadal snapshot z synca | INFO | Czesciowo naprawione |
| 6 | SQLite: brak Alembic, zmiana schematu = usun DB + reseed | INFO | N/A |

---

---

## ZMIANY Z SESJI 2026-03-06

### CRITICAL FIX: Real Client Data Now Syncing â€” âś… DONE
**Problem:** After syncing real Google Ads client (Sushi Naka Naka), Dashboard showed "Brak danych" (No data) while SearchTerms had 989 rows of real data.

**Root Cause:** GAQL query in `sync_daily_metrics()` included incompatible metric `conversions_value_per_cost` for CAMPAIGN resource, causing silent query failure and returning 0 metrics.

**Fix Applied:**
- Removed `metrics.conversions_value_per_cost` from Query 1 (core_query) SELECT clause
- Removed corresponding field from data dictionary
- Disabled geo_metrics sync (requires different GAQL resource structure)

**Result:** Real client now syncs **87 daily metric rows** successfully
- Dashboard KPIs: 1618 clicks, 26919 impressions, 2419.35 USD cost, 733.71 conversions, ROAS 57.36
- TrendExplorer: `is_mock: false` (displays real data, no warning banner)
- Device metrics: 194 rows (already working)

**Files Changed:**
- `backend/app/services/google_ads.py`: Removed incompatible metric from sync_daily_metrics()
- `backend/app/routers/sync.py`: Disabled geo_metrics call pending query structure fix

### SYNC PIPELINE OVERHAUL â€” âś… DONE (2026-03-06 session 2)
**Problem:** Sync pipeline had 5 independent bugs: geo metrics disabled, impression share never called, change_events date format, silent error swallowing, no sync history tracking.

**Fixes Applied:**
1. **sync_geo_metrics** â€” rewrote GAQL to use `geographic_view` instead of `campaign` resource (+ `campaign.status` in SELECT required by API). Now returns 227 rows.
2. **sync_campaign_impression_share** â€” added to pipeline as Phase 1b. Returns 2-5 rows per client.
3. **change_events** â€” fixed 2 bugs: date range capped at 28 days (API's "30-day" limit is strict), parse `change_date_time` string to Python datetime for SQLite.
4. **Silent failures** â€” all 10 sync methods now `raise` after `db.rollback()` instead of `return 0`. Errors properly propagate to the sync router.
5. **SyncLog** â€” new model + per-phase error tracking. Every sync creates a SyncLog entry with phase-by-phase results, timestamps, counts.
6. **sync.py router rewrite** â€” 11 phases with dependency checking (if campaigns fail â†’ abort; if ad_groups fail â†’ skip keywords/search_terms). New `/sync/logs` endpoint.

**Result:** All 11 phases succeed across 3 real clients:
- Sushi Naka Naka: 1,734 rows (3 campaigns, 128 keywords, 87 daily metrics, 227 geo, 194 device, 51+938 search terms, 1 change event)
- Klimfix: 910 rows (17 campaigns, 379 keywords, 103 keyword daily, 24 geo, 46 device, 281 search terms, 1 change event)
- tanie-materialy.pl: 0 rows (all phases OK, empty account)

**Files Changed:**
- `backend/app/services/google_ads.py`: geo_metrics rewrite, change_events datetime fix, all sync methods raise on error
- `backend/app/routers/sync.py`: complete rewrite with SyncLog, dependency checking, `/sync/logs` endpoint
- `backend/app/models/sync_log.py`: new SyncLog model
- `backend/app/models/__init__.py`: added SyncLog export

---

## NASTEPNE KROKI

1. **PyWebView** â€” przetestowac native wrapper
2. **PyInstaller** â€” zbudowac .exe
3. **Code quality** â€” wyciagnac wspolne style do theme.js, dodac AbortController
4. **Negative Keywords sync** â€” nowa faza synca (V1.1)
5. **Scheduled sync** â€” auto-sync co 6h/24h (V1.1)




---

## ZMIANY Z SESJI 2026-03-12

### SoT + Execution Readiness Hardening - DONE
- Dodano `docs/SOURCE_OF_TRUTH.md` jako glowny indeks dokumentacji i jednoznaczne SoT.
- `Technical_Spec.md` oznaczony jako LEGACY snapshot (2025-02-17) z linkiem do aktywnego SoT.
- `docs/API_ENDPOINTS.md` ujednolicony do aktualnego kontraktu routerow i oznaczony `[PROD]/[AUX]`.
- `docs/FEATURE_SET.md` zaktualizowany do 17 aktywnych regul (R1-R13, R15-R18), z adnotacja o nieaktywnej R14 i mapa rule->category->executable.
- Product messaging zaktualizowany na `execution-ready` po green testach write-flow + API contract.

### Testy krytyczne write-flow + API contract - DONE
- Dodano `backend/tests/test_write_actions_flow.py`:
  - apply dry-run (bez mutacji),
  - apply live success,
  - blokada safety limits,
  - fail path i status `FAILED`,
  - revert success,
  - double-revert blocked,
  - revert window >24h blocked.
- Dodano `backend/tests/test_api_contract_smoke.py`:
  - smoke dla grup: auth, clients, sync, recommendations, actions, analytics,
  - walidacja obecnosci krytycznych tras API w app routes.
- Dodano `backend/tests/test_recommendations_contract.py`:
  - walidacja aktywnego ruleset types,
  - deterministyczne filtry `priority/category` dla `/recommendations`.

### Wynik testow
- `pytest tests/test_write_actions_flow.py tests/test_api_contract_smoke.py tests/test_recommendations_contract.py`
- Result: **10 passed**
