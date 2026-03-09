# Feature Set - Google Ads Helper v1

Aktualna lista funkcjonalnosci aplikacji (stan implementacji).

---

## 1. Sync (Google Ads -> lokalna baza)

### Fazy sync
1. `campaigns` - kampanie (nazwa, typ, status, budzet)
2. `impression_share` - impression share per kampania (SEARCH)
3. `ad_groups` - grupy reklam
4. `keywords` - slowa kluczowe + QS + stawki + metryki snapshot
5. `keyword_daily` - dzienne metryki keywordow
6. `daily_metrics` - dzienne metryki kampanii
7. `device_metrics` - segmentacja urzadzen (MOBILE/DESKTOP/TABLET)
8. `geo_metrics` - segmentacja geograficzna
9. `search_terms` - frazy wyszukiwane z SEARCH
10. `pmax_terms` - frazy z Performance Max
11. `change_events` - historia zmian (change_event)

### Zasady wykonania
- Sync logowany jest per-faza (status, count, error).
- Krytyczna zaleznosc: blad `campaigns` zatrzymuje caly sync.
- `keywords`, `keyword_daily`, `search_terms` sa pomijane, jesli wymagane fazy zalezne nie przejda.
- Dostepny jest pelny sync oraz uruchamianie pojedynczej fazy diagnostycznej.

---

## 2. Dashboard (Pulpit)

- KPI cards: clicks, impressions, cost, conversions, CTR, ROAS.
- Porownanie okres do okresu (`dashboard-kpis`).
- Health score konta.
- Trendy metryk.
- Campaign trends.
- Budget pacing.
- Device breakdown.
- Geo breakdown.
- Preview rekomendacji.

---

## 3. Strony i moduly UI

### Nawigacja glowna
- Pulpit
- Klienci
- Kampanie
- Slowa kluczowe
- Wyszukiwane frazy
- Rekomendacje
- Historia akcji
- Monitoring (alerty)
- Optymalizacja (search optimization)
- Inteligencja (semantic)
- Quality Score
- Forecast
- Ustawienia

### Dodatkowe zachowanie
- Trasa `/anomalies` przekierowuje do `/alerts`.
- Globalny date picker (7/14/30/90 dni + custom).
- Globalny wybor klienta.

---

## 4. Analytics i insighty

### Core
- KPIs
- Alerty anomalii (lista unresolved/resolved)
- Resolve alertu
- Trigger detekcji anomalii

### Advanced
- Correlation matrix (`/analytics/correlation`)
- Compare periods (`/analytics/compare-periods`)
- Forecast
- Quality score audit
- Impression share
- Device breakdown
- Geo breakdown
- Account structure
- Bidding advisor
- Hourly dayparting

### Search optimization
- Dayparting
- RSA analysis
- N-gram analysis
- Match type analysis
- Landing pages
- Wasted spend

---

## 5. Recommendations i Actions

### Recommendations
- Silnik rekomendacji oparty o zestaw regul decyzyjnych.
- Obecnie aktywne: reguly R1-R13 oraz R15-R18 (lacznie 17 regul).
- Kategorie: rekomendacje wykonawcze + alerty analityczne.
- Priorytety: HIGH / MEDIUM / LOW.

### Actions
- Apply rekomendacji (z `dry_run=true` lub execute).
- Dismiss rekomendacji.
- Historia akcji (helper/external/unified).
- Revert akcji z walidacja warunkow bezpieczenstwa.

---

## 6. Search Terms i Keywords

### Search Terms
- Lista z filtrowaniem i sortowaniem.
- Widok segmentowany.
- Summary per kampania (`campaign_id` wymagany).
- Eksport XLSX.

### Keywords
- Lista keywordow z filtrami.
- Metryki dzienne i agregacje po okresie.
- Eksport XLSX.

---

## 7. Export

- Search terms -> XLSX
- Keywords -> XLSX
- Metrics -> XLSX
- Recommendations -> XLSX

---

## 8. Auth i bezpieczenstwo

- OAuth 2.0 Google Ads.
- Setup endpointy do zapisania credentiali.
- Sesja API (Bearer token).
- Sekrety przechowywane przez Windows Credential Manager (keyring).
- Circuit breaker i walidacja akcji write (`validate_action`).
- Safety limits (m.in. limity zmian bid/budget i limit pause/day).

---

## 9. Stack

- Backend: FastAPI + SQLAlchemy
- Frontend: React + Vite
- DB: SQLite
- Desktop: PyWebView
- Integracja: Google Ads API (google-ads client)

---

## 10. Metryki projektu

- Modele ORM: 14
- Routery API: 12
- Endpointy API (get/post/patch/delete): 65
- Strony frontend: 15
