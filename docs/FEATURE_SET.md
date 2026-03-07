# Feature Set — Google Ads Helper v1

Kompletna lista funkcjonalnosci aplikacji.
Moze sluzyc jako template do innych modulow/projektow.

---

## 1. SYNC (Pobieranie danych z Google Ads API)

| Faza | Co syncuje | Zrodlo GAQL | Uwagi |
|------|-----------|-------------|-------|
| Campaigns | Kampanie (nazwa, typ, status, budzet) | `campaign` | Wszystkie typy: SEARCH, PMAX, DISPLAY... |
| Impression Share | Udzial w wyswietleniach per kampania | `campaign` | Faza 1b, osobny query |
| Ad Groups | Grupy reklam | `ad_group` | Pomijane jesli campaigns fail |
| Keywords | Slowa kluczowe + QS + bid | `keyword_view` | Pomijane jesli ad_groups fail |
| Keyword Daily | Metryki dzienne per keyword | `keyword_view` | Agregacja po dacie |
| Daily Metrics | Metryki dzienne per kampania | `campaign` | cost, clicks, impressions, conversions, ROAS |
| Device Metrics | Segmentacja po urzadzeniu | `campaign` | MOBILE/DESKTOP/TABLET |
| Geo Metrics | Segmentacja po miastach | `geographic_view` | Auto-resolve nazw miast z geoTargetConstants |
| Search Terms (SEARCH) | Wyszukiwane frazy z kampanii SEARCH | `search_term_view` | Upsert po (text, ad_group_id, date range) |
| Search Terms (PMAX) | Wyszukiwane frazy z PMax | `campaign_search_term_view` | ad_group_id nullable, source="PMAX" |
| Change Events | Historia zmian z konta | `change_event` | Max 28 dni wstecz (limit API) |

**SyncLog** — kazdy sync tworzy wpis z wynikiem per faza (status, ilosc, bledy).
Dependency checking: jesli campaigns fail → abort; jesli ad_groups fail → skip keywords/search_terms.

---

## 2. DASHBOARD (Pulpit)

| Element | Opis |
|---------|------|
| KPI Cards | Clicks, Impressions, Cost, Conversions, CTR, ROAS — z porownaniem do poprzedniego okresu (% zmiana) |
| Health Score | Gauge 0-100 (alerty, kampanie bez konwersji, niski ROAS, spadek CTR) |
| Trend Chart | Wykres dzienny cost + clicks (Recharts) |
| Campaign Trends | Top kampanie z mini-sparkline |
| Budget Pacing | Wykorzystanie budzetu per kampania (% + pasek) |
| Device Breakdown | Pie/bar chart: MOBILE vs DESKTOP vs TABLET |
| Geo Breakdown | Top 8 miast: klikniecia, koszt, ROAS |
| Campaign Table | Tabela wszystkich kampanii z sortowaniem |
| Recommendations Preview | 3 najwazniejsze rekomendacje |

---

## 3. STRONY ANALITYCZNE

### Campaigns (Kampanie)
- Lista kampanii z KPI (clicks, cost, conv, ROAS)
- KPI detail per kampania z wykresem metryk

### Keywords (Slowa kluczowe)
- Tabela z filtrami (campaign_type, status, match_type)
- Date filtering agreguje z KeywordDaily (SUM per keyword)
- Quality Score, impression share, bid z snapshot

### Search Terms (Wyszukiwane frazy)
- Segmentacja: IRRELEVANT / HIGH_PERFORMER / WASTE / OTHER
- Segmented view z kartami podsumowania per segment
- Filtrowanie po tekst, kampania, segment
- Eksport do XLSX

### Recommendations (Rekomendacje)
- 7 regul optymalizacyjnych (auto-generowane)
- Priority badges (HIGH/MEDIUM)
- Apply z ConfirmationModal (before/after preview)
- Dismiss z notatka
- Dry-run mode

### Action History (Historia akcji)
- Timeline wykonanych akcji (Apply/Revert)
- Tabs: Helper / External / All
- Revert z walidacja (< 24h, SUCCESS, nie REVERTED)

### Alerts (Alerty)
- Anomaly detection: SPEND_SPIKE, CONVERSION_DROP, CTR_DROP
- Tabs: Unresolved / Resolved
- Resolve z notatka

---

## 4. STRONY ZAAWANSOWANE

### Quality Score Audit
- Rozklad QS per kampania
- Identyfikacja keywords z niskim QS

### Forecast
- Prognoza metryk per kampania (ekstrapolacja trendu)

### Semantic Clustering
- Grupowanie keywords po tematyce (TF-IDF + cosine similarity)

### Anomalies
- Wykryte anomalie z progami (3x spend spike, conversion drop, CTR drop)

### Search Optimization (6 analiz)
1. **Dayparting** — performance per dzien tygodnia
2. **RSA Analysis** — CTR spread reklam, ranking headlines
3. **N-gram Analysis** — najczestsze n-gramy w search terms
4. **Match Type Analysis** — porownanie EXACT/PHRASE/BROAD
5. **Landing Pages** — performance per landing page URL
6. **Wasted Spend** — keywords, search terms i ads z 0 konwersji

### Trend Explorer
- Multi-metric correlation (wybierz metryki, porownaj na jednym wykresie)
- is_mock indicator (baner jesli brak real data)

---

## 5. INFRASTRUKTURA

| Feature | Opis |
|---------|------|
| Auth | OAuth 2.0 Google + Setup Wizard (krok po kroku) |
| Credentials | Windows Credential Manager via keyring (NIGDY w DB/.env) |
| Global Date Picker | 7d/14d/30d/90d presety + custom range (w sidebar) |
| Client Selector | Dropdown w sidebar, auto-select pierwszego klienta |
| Export | XLSX eksport search terms i keywords |
| Circuit Breaker | Kazdy write do Google Ads API przez validate_action() |
| Safety Limits | Max 50% bid change, 30% budget change, 20% keywords paused/day |
| SyncLog | Per-phase tracking z error details |
| Dark Mode | Jedyny tryb (MVP) — design Linear/Vercel |

---

## 6. STACK TECHNICZNY

| Warstwa | Technologia |
|---------|------------|
| Backend | FastAPI (Python 3.10+) |
| Frontend | React 18 + Vite |
| Baza danych | SQLite (SQLAlchemy ORM) |
| Desktop wrapper | PyWebView |
| Charts | Recharts |
| Tables | @tanstack/react-table |
| CSS | Tailwind CSS + custom dark theme |
| Build | PyInstaller → single .exe |
| Google Ads | google-ads Python client + GAQL |

---

## 7. METRYKI PROJEKTU

- **15 modeli ORM** (+ SyncLog)
- **12 routerow API** (40+ endpointow)
- **15 stron frontend**
- **14 komponentow**
- **7 regul rekomendacyjnych**
- **6 analiz SEARCH optimization**
- **11 faz sync**
- **3 contexty React** (App, Filter)
