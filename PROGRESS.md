# PROGRESS.md — Stan implementacji
# Aktualizacja: 2026-02-25
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

### Modele ORM (Phase 1) — ✅ DONE (13 modeli)
| Model | Plik | Status |
|-------|------|--------|
| Client | models/client.py | ✅ |
| Campaign | models/campaign.py | ✅ |
| AdGroup | models/ad_group.py | ✅ |
| Keyword | models/keyword.py | ✅ |
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

### Strony (Phase 4) — ✅ DONE (14 stron)
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

## INTEGRACJA I TESTY (Phase 5) — 🟡 W TOKU

| Zadanie | Status | Uwagi |
|---------|--------|-------|
| Backend <-> Frontend wiring | ✅ | Vite proxy, Axios, CORS |
| Seed data + demo mode | ✅ | seed.py z realistycznymi danymi |
| OAuth end-to-end | ⬜ | Wymaga prawdziwego konta Google Ads |
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
| 4 | FilterContext uzywany tylko w 2/14 stronach | LOW | ⬜ |
| 5 | TH_STYLE zduplikowane w 3 plikach (wyciagnac do theme.js) | LOW | ⬜ |

---

## NASTEPNE KROKI

1. **Testy live** — podlaczenie prawdziwego konta Google Ads
2. **PyWebView** — przetestowac native wrapper
3. **PyInstaller** — zbudowac .exe
4. **Code quality** — wyciagnac wspolne style do theme.js, dodac AbortController
