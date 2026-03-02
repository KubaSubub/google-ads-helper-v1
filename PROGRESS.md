# PROGRESS.md — Stan implementacji
# Aktualizacja: 2026-03-01
# Claude Code: czytaj ten plik, aby wiedziec co jest gotowe, a co pozostalo.

---

## STATUS: 🟢 MVP ZBUDOWANY — Backend gotowy, Frontend gotowy, integracja w toku

---

## BACKEND — ✅ KOMPLETNY

### Infrastruktura (Phase 1) — ✅ DONE
| Element | Plik(i) | Status |
|---------|---------|--------|
| Katalogi + __init__.py | cale drzewo backend/app/ | ✅ |
| Python dependencies | requirements.txt | ✅ |
| Logger | loguru (bezposredni import) | ✅ |
| Constants + Safety Limits | utils/constants.py | ✅ |
| Formatters (micros) | utils/formatters.py | ✅ |
| Config (pydantic-settings) | config.py | ✅ |
| Database (SQLAlchemy + SQLite) | database.py | ✅ |
| Seed data (demo) | seed.py | ✅ |

### Modele ORM (Phase 1) — ✅ DONE (14 modeli)
| Model | Plik | Status |
|-------|------|--------|
| Client | models/client.py | ✅ |
| Campaign | models/campaign.py | ✅ |
| AdGroup | models/ad_group.py | ✅ |
| Keyword | models/keyword.py | ✅ |
| KeywordDaily | models/keyword_daily.py | ✅ |
| Ad | models/ad.py | ✅ |
| SearchTerm | models/search_term.py | ✅ |
| Recommendation | models/recommendation.py | ✅ |
| ActionLog | models/action_log.py | ✅ |
| Alert | models/alert.py | ✅ |
| MetricDaily | models/metric_daily.py | ✅ |
| MetricSegmented | models/metric_segmented.py | ✅ |
| ChangeEvent | models/change_event.py | ✅ |

### Schemas Pydantic v2 (Phase 1) — ✅ DONE
| Schema | Plik | Status |
|--------|------|--------|
| Common (enums) | schemas/common.py | ✅ |
| Client | schemas/client.py | ✅ |
| Campaign | schemas/campaign.py | ✅ |
| Keyword | schemas/keyword.py | ✅ |
| Ad | schemas/ad.py | ✅ |
| SearchTerm | schemas/search_term.py | ✅ |
| Recommendation | schemas/recommendation.py | ✅ |
| Analytics | schemas/analytics.py | ✅ |
| ChangeEvent | schemas/change_event.py | ✅ |

### Serwisy (Phase 2-3) — ✅ DONE
| Serwis | Plik | Status |
|--------|------|--------|
| Credentials (keyring) | services/credentials_service.py | ✅ |
| Google Ads (GAQL + sync) | services/google_ads.py | ✅ |
| Recommendations Engine (7 regul) | services/recommendations.py | ✅ |
| Action Executor (circuit breaker) | services/action_executor.py | ✅ |
| Analytics | services/analytics_service.py | ✅ |
| Search Terms Segmentation | services/search_terms_service.py | ✅ |
| Semantic Clustering | services/semantic.py | ✅ |
| Cache (TTL) | services/cache.py | ✅ |

### Routery API (Phase 2-3) — ✅ DONE (12 routerow)
| Router | Prefix | Plik | Status |
|--------|--------|------|--------|
| Auth | /auth | routers/auth.py | ✅ |
| Clients | /clients | routers/clients.py | ✅ |
| Campaigns | /campaigns | routers/campaigns.py | ✅ |
| Keywords + Ads | /keywords | routers/keywords_ads.py | ✅ |
| Search Terms | /search-terms | routers/search_terms.py | ✅ |
| Recommendations | /recommendations | routers/recommendations.py | ✅ |
| Actions | /actions | routers/actions.py | ✅ |
| Analytics | /analytics | routers/analytics.py | ✅ |
| Sync | /sync | routers/sync.py | ✅ |
| Export | /export | routers/export.py | ✅ |
| Semantic | /semantic | routers/semantic.py | ✅ |
| History | /history | routers/history.py | ✅ |

---

## FRONTEND — ✅ KOMPLETNY

### Infrastruktura (Phase 4) — ✅ DONE
| Element | Plik | Status |
|---------|------|--------|
| Vite + React 18 | package.json, vite.config.js | ✅ |
| Tailwind CSS | tailwind.config.js | ✅ |
| App shell + routing | App.jsx | ✅ |
| Axios API client | api.js | ✅ |
| Dark mode v2 design | globalnie | ✅ |

### Strony (Phase 4) — ✅ DONE (15 stron)
| Strona | Plik | Status |
|--------|------|--------|
| Dashboard | pages/Dashboard.jsx | ✅ |
| Clients | pages/Clients.jsx | ✅ |
| Campaigns | pages/Campaigns.jsx | ✅ |
| Keywords | pages/Keywords.jsx | ✅ |
| Search Terms | pages/SearchTerms.jsx | ✅ |
| Recommendations | pages/Recommendations.jsx | ✅ |
| Action History | pages/ActionHistory.jsx | ✅ |
| Alerts | pages/Alerts.jsx | ✅ |
| Settings | pages/Settings.jsx | ✅ |
| Quality Score | pages/QualityScore.jsx | ✅ |
| Forecast | pages/Forecast.jsx | ✅ |
| Semantic | pages/Semantic.jsx | ✅ |
| Anomalies | pages/Anomalies.jsx | ✅ |
| Search Optimization | pages/SearchOptimization.jsx | ✅ |
| Login | pages/Login.jsx | ✅ |

### Komponenty (Phase 4) — ✅ DONE
| Komponent | Plik | Status |
|-----------|------|--------|
| Sidebar | components/Sidebar.jsx | ✅ |
| Charts (Recharts) | components/Charts.jsx | ✅ |
| DataTable (TanStack) | components/DataTable.jsx | ✅ |
| ConfirmationModal | components/ConfirmationModal.jsx | ✅ |
| Toast | components/Toast.jsx | ✅ |
| SegmentBadge | components/SegmentBadge.jsx | ✅ |
| EmptyState | components/EmptyState.jsx | ✅ |
| FilterBar | components/FilterBar.jsx | ✅ |
| SyncButton | components/SyncButton.jsx | ✅ |
| TrendExplorer | components/TrendExplorer.jsx | ✅ |
| InsightsFeed | components/InsightsFeed.jsx | ✅ |
| MetricTooltip | components/MetricTooltip.jsx | ✅ |
| DiffView | components/DiffView.jsx | ✅ |
| UI (shared) | components/UI.jsx | ✅ |

### Contexts + Hooks — ✅ DONE
| Element | Plik | Status |
|---------|------|--------|
| AppContext | contexts/AppContext.jsx | ✅ |
| FilterContext | contexts/FilterContext.jsx | ✅ |
| useClients | hooks/useClients.js | ✅ |
| useRecommendations | hooks/useRecommendations.js | ✅ |
| useSync | hooks/useSync.js | ✅ |

---

## ZMIANY Z SESJI 2026-02-27/28

### OAuth + Credentials Setup Wizard — ✅ DONE
- `GET /auth/setup-status` — sprawdza czy credentials sa skonfigurowane
- `POST /auth/setup` — zapisuje client_id, client_secret, developer_token, login_customer_id do keyring
- Login.jsx — kreator konfiguracji (krok po kroku) + przycisk "Zaloguj przez Google"
- Credentials zapisywane TYLKO w Windows Credential Manager (keyring)

### PMax Search Terms (campaign_search_term_view) — ✅ DONE
- `sync_pmax_search_terms()` w google_ads.py — uzywa `campaign_search_term_view` (NIE `search_term_view`)
- WAZNE: NIE uzywac `segments.keyword.info.*` z campaign_search_term_view — wyfiltruje PMax
- SearchTerm model: `ad_group_id` nullable, dodane `campaign_id` (FK), `source` ("SEARCH"/"PMAX")
- Campaign model: dodana relacja `search_terms`
- search_terms router: outerjoin z or_() obsluguje oba typy (Search + PMax)
- search_terms_service: `_fetch_terms()` helper, queries obsluguja PMax
- Sync Phase 5b: sync_pmax_search_terms() po standardowym sync_search_terms()

### Sidebar — Client State Centralization — ✅ DONE
- Klienci przeniesieni do AppContext (clients, clientsLoading, refreshClients)
- Sidebar.jsx uzywa useApp() zamiast osobnego useClients()
- Clients.jsx uzywa refreshClients z AppContext
- Po discover klienci od razu widoczni w dropdown

### Global Date Range Picker — ✅ DONE
- DateRangePicker w Sidebar.jsx — presety (7d/14d/30d/90d) + custom date inputs
- FilterContext: dateFrom, dateTo, period (auto-sync), computed `days`
- Dashboard, Campaigns, TrendExplorer — uzywaja `days` z useFilter()
- SearchTerms (list + segmented) — wysylaja `date_from`/`date_to` do backendu
- FilterBar: period pills ukryte (hidePeriod) — daty sa globalne w sidebarze
- Segmented endpoint: przyjmuje `date_from`/`date_to`, przekazuje do service

### Drobne fixy
- Recommendations.jsx: key prop fallback `key={rec.id ?? \`rec-${idx}\`}`
- Clients.jsx: syncingClientId per-client zamiast globalnego boolean
- Auto-select pierwszego klienta po discover

---

## ZMIANY Z SESJI 2026-03-01

### KeywordDaily — metryki dzienne per keyword — ✅ DONE
- Nowy model `KeywordDaily` (keyword_id + date → clicks, impressions, cost_micros, conversions, conversion_value_micros, avg_cpc_micros)
- Router `keywords_ads.py`: dwie sciezki — agregacja z KeywordDaily (z date_from/date_to) vs snapshot (bez dat)
- Seed: 90 dni per keyword z trend_factor + dow_factor + noise
- Frontend Keywords.jsx: przekazuje date_from/date_to z FilterContext
- Zmiana dat w sidebarze (7d/14d/30d/90d) teraz wplywa na dane w tabeli Keywords

### SEARCH Optimization — 6 nowych analiz — ✅ DONE
- Nowa strona `SearchOptimization.jsx` z 6 rozwijalnymi sekcjami
- 6 nowych metod w analytics_service.py:
  1. `get_dayparting()` — analiza dnia tygodnia (MetricDaily)
  2. `get_rsa_analysis()` — analiza RSA reklam (CTR spread, headlines)
  3. `get_ngram_analysis()` — n-gramy z search terms (1/2/3-gramy)
  4. `get_match_type_analysis()` — porownanie EXACT/PHRASE/BROAD (KeywordDaily)
  5. `get_landing_page_analysis()` — analiza landing pages (KeywordDaily + final_url)
  6. `get_wasted_spend()` — zmarnowany budzet (keywords 0 conv, search terms 0 conv, ads 0 conv)
- 6 nowych endpointow w analytics.py router
- 6 nowych funkcji API w api.js
- Sidebar: "Optymalizacja" (Zap icon) w grupie ANALIZA
- Seed: final_url per keyword, waste_kw_ids (3 keywords z 0 conversions)

---

## INTEGRACJA I TESTY (Phase 5) — 🟡 W TOKU

| Zadanie | Status | Uwagi |
|---------|--------|-------|
| Backend <-> Frontend wiring | ✅ | Vite proxy, Axios, CORS |
| Seed data + demo mode | ✅ | seed.py z realistycznymi danymi |
| OAuth end-to-end | ✅ | Setup wizard + Google OAuth flow |
| Sync test (live API) | ⬜ | Wymaga credentials |
| Recommendations test | ⬜ | 7 regul do przetestowania |
| Apply/Revert test | ⬜ | dry_run + live |
| PyWebView wrapper | ⬜ | main.py do przetestowania |
| PyInstaller build | ⬜ | .exe |

---

## ZNANE PROBLEMY DO NAPRAWY

| # | Problem | Priorytet | Status |
|---|---------|-----------|--------|
| 1 | CTR storage niespojne (Float vs Integer micros) miedzy modelami | MEDIUM | ⬜ |
| 2 | Dashboard secondary data — silent error suppression | LOW | ⬜ |
| 3 | Brak AbortController w useEffect (memory leaks) | LOW | ⬜ |
| 4 | TH_STYLE zduplikowane w 3 plikach (wyciagnac do theme.js) | LOW | ⬜ |
| 5 | Keywords maja KeywordDaily (date filtering dziala). Campaigns — nadal snapshot z synca | INFO | Czesciowo naprawione |
| 6 | SQLite: brak Alembic, zmiana schematu = usun DB + reseed | INFO | N/A |

---

## NASTEPNE KROKI

1. **Sync test** — zsynchronizowac prawdziwe konto Google Ads, zweryfikowac PMax search terms
2. **PyWebView** — przetestowac native wrapper
3. **PyInstaller** — zbudowac .exe
4. **Code quality** — wyciagnac wspolne style do theme.js, dodac AbortController
