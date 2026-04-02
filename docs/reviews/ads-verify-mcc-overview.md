# Plan implementacji — MCC Overview
> Na podstawie: docs/reviews/ads-expert-mcc-overview.md
> Data weryfikacji: 2026-04-02

## Podsumowanie
- Elementów z raportu: 14
- DONE: 1 | PARTIAL: 3 | MISSING: 10
- Szacowany nakład: mały (Sprint 1 = ~1.5h, Sprint 2 = ~1h)

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| K1 | Konwersje + CPA + ROAS per konto | MISSING | MetricDaily ma `conversions`, `conversion_value_micros`. `_sum_spend()` pattern gotowy do reuse. | Agregacja konwersji w `_build_account_data()`. 3 kolumny w tabeli frontend. | S |
| K2 | Sortowanie tabeli | MISSING | Tabela renderuje accounts bez sort. | State `sortBy`/`sortDir`, klikalne nagłówki TH, `accounts.sort()` w render. | S |
| K3 | Health score tooltip z breakdown | PARTIAL | `get_health_score()` zwraca pełny breakdown (6 filarów). `_get_health_score()` wyrzuca breakdown i zwraca tylko `score`. | Zmienić return na `{score, breakdown}`. Tooltip/popover w UI. | S |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| N1 | Sparkline wydatków | MISSING | Dashboard ma komponent `Sparkline` z Recharts. | Dane daily spend per klient z backendu. Reuse Sparkline w tabeli MCC. | M |
| N2 | Link "Otwórz w Google Ads" | MISSING | `google_customer_id` jest w response overview. | Button per wiersz z URL `ads.google.com/aw/overview?ocid={id}`. | S |
| N3 | Alerty per konto | MISSING | Model `Alert` istnieje z `client_id` + `resolved_at`. | COUNT unresolved alerts w `_build_account_data()`. Ikona/badge w UI. | S |
| N4 | Filtrowanie/wyszukiwanie kont | MISSING | Brak. | Search input + filter state. Przy <10 kont nieistotne. | S |
| N5 | NKL akcje z poziomu MCC | PARTIAL | NKL read-only podgląd cross-account zaimplementowany. CRUD endpointy per-klient istnieją. | UI do tworzenia/edycji list z poziomu MCC. Kopiowanie list cross-account. | L |
| N6 | Kolumna Impression Share | MISSING | MetricDaily ma `search_impression_share`. | Agregacja avg IS w `_build_account_data()`. Kolumna w tabeli. | S |

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Pacing progi 80%/115% → 75%/120% | DONE (do zmiany) | `pct < 0.8` / `pct > 1.15` w `_compute_pacing()` | Zmienić na `0.75` / `1.20` | trivial |
| Z2 | KPI "Rek. Google" bez priorytetu | DONE | Liczba pending Google recs. | Rozważ podział high/low priority — wymaga pola priority na Recommendation. | M |

### NAWIGACJA — brakujące połączenia

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| NAV1 | Deep-link Health → Health Score page | PARTIAL | Kliknięcie wiersza → /dashboard. | onClick na kółko health → `/dashboard` z scrollem do health section lub `/quality-score`. | S |
| NAV2 | Deep-link Rek. Google → Recommendations | MISSING | Kolumna wyświetla liczbę. | onClick na liczbę → `setSelectedClientId()` + `navigate('/recommendations')`. | S |
| NAV3 | Deep-link Zmiany → Action History | MISSING | Kolumna wyświetla liczbę. | onClick na liczbę → `setSelectedClientId()` + `navigate('/action-history')`. | S |
| NAV4 | Deep-link NKL → Keywords page | MISSING | NKL sekcja read-only. | Kliknięcie wiersza NKL → `setSelectedClientId()` + `navigate('/keywords')`. | S |

## Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, ~1.5h):
  [x] K1 — Konwersje + CPA + ROAS w tabeli (backend + frontend) ✅ 2026-04-02
  [x] K2 — Sortowanie tabeli (frontend only) ✅ 2026-04-02
  [x] K3 — Health tooltip z breakdown (backend zmiana return + frontend tooltip) ✅ 2026-04-02
  [x] Z1 — Pacing progi 75%/120% (2 linijki backend) ✅ 2026-04-02

Sprint 2 (deep-links + alerty — nakład S, ~1h):
  [x] NAV2 — Deep-link Rek. Google → Recommendations ✅ 2026-04-02
  [x] NAV3 — Deep-link Zmiany → Action History ✅ 2026-04-02
  [x] NAV4 — Deep-link NKL → Keywords ✅ 2026-04-02
  [x] N3 — Alerty per konto (backend COUNT + frontend badge) ✅ 2026-04-02
  [x] N2 — Link "Otwórz w Google Ads" (frontend only) ✅ 2026-04-02

Sprint 3 (nice to have — nakład M/L):
  [ ] N1 — Sparkline wydatków (wymaga daily breakdown z backendu)
  [ ] N6 — Kolumna Impression Share
  [ ] N4 — Filtrowanie/wyszukiwanie kont
  [ ] N5 — NKL edycja cross-account (L)
```

## Szczegóły implementacji

### Sprint 1

#### K1: Konwersje + CPA + ROAS

**Pliki do modyfikacji:**
- `backend/app/services/mcc_service.py` — `_build_account_data()`
- `frontend/src/features/mcc-overview/MCCOverviewPage.jsx` — tabela

**Backend — dodać do `_build_account_data()`:**
```python
# Po _sum_spend calls, dodać analogiczną metodę _sum_conversions:
conversions_30d = self._sum_metric(cid, today - timedelta(days=30), today, MetricDaily.conversions)
conv_value_30d = self._sum_metric(cid, today - timedelta(days=30), today, MetricDaily.conversion_value_micros)
conv_value_usd = micros_to_currency(conv_value_30d)
cpa = round(spend_30d / conversions_30d, 2) if conversions_30d > 0 else None
roas = round(conv_value_usd / spend_30d * 100, 1) if spend_30d > 0 else None

# Dodać do return dict:
"conversions_30d": round(conversions_30d, 1),
"cpa_usd": cpa,
"roas_pct": roas,
```

**Frontend — dodać 3 kolumny po "Wydatki 30d":**
- Konwersje 30d (number, 1 decimal)
- CPA ($ format, lub "—" jeśli null)
- ROAS (% format, lub "—" jeśli null)

**Testy:** Dodać `test_mcc_overview_conversions_cpa_roas` w `backend/tests/test_mcc.py`

#### K2: Sortowanie tabeli

**Pliki do modyfikacji:**
- `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`

**Zmiany:**
1. State: `const [sortBy, setSortBy] = useState('spend_30d_usd'); const [sortDir, setSortDir] = useState('desc');`
2. Handler: `handleSort(column)` — toggle asc/desc
3. Sorted accounts: `useMemo(() => [...accounts].sort(...), [accounts, sortBy, sortDir])`
4. TH: dodać `onClick` + ikona sortowania (ChevronUp/ChevronDown)

#### K3: Health tooltip

**Pliki do modyfikacji:**
- `backend/app/services/mcc_service.py` — `_get_health_score()`
- `frontend/src/features/mcc-overview/MCCOverviewPage.jsx` — kółko health

**Backend — zmienić `_get_health_score()`:**
```python
def _get_health_score(self, client_id: int) -> dict | None:
    try:
        svc = AnalyticsService(self.db)
        result = svc.get_health_score(client_id, days=30)
        return {
            "score": result.get("score"),
            "breakdown": {
                k: v.get("score") for k, v in result.get("breakdown", {}).items()
            },
        }
    except Exception:
        return None
```

**Frontend — tooltip na hover kółka health:**
Custom tooltip z 6 filarami: Performance, Quality, Efficiency, Coverage, Stability, Structure.

#### Z1: Pacing progi

**Plik:** `backend/app/services/mcc_service.py` — `_compute_pacing()`
**Zmiana:** `0.8` → `0.75`, `1.15` → `1.20`

### Sprint 2

#### NAV2/NAV3: Deep-links z kolumn

**Plik:** `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`
**Zmiana:** Dodać `onClick` na komórkach "Rek. Google" i "Zmiany":
```jsx
onClick={(e) => {
    e.stopPropagation()
    setSelectedClientId(acc.client_id)
    navigate('/recommendations')
}}
```

#### N3: Alerty per konto

**Pliki:**
- `backend/app/services/mcc_service.py` — import Alert, COUNT w `_build_account_data()`
- `frontend/src/features/mcc-overview/MCCOverviewPage.jsx` — badge/ikona

**Backend:**
```python
from app.models import Alert

unresolved_alerts = (
    self.db.query(func.count(Alert.id))
    .filter(Alert.client_id == cid, Alert.resolved_at.is_(None))
    .scalar()
) or 0
```

#### N2: Link "Otwórz w Google Ads"

**Plik:** `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`
**Zmiana:** Dodać ikonę ExternalLink w kolumnie akcji, onClick → `window.open(url)`
