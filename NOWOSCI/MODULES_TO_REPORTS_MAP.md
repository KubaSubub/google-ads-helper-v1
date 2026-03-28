# Mapa integracji → Raport AI i Raporty

## Koncepcja

Raport AI (`/agent`) i Raporty (`/reports`) to moduły **konsumujące** dane z całej aplikacji.
Każdy inny moduł jest potencjalnym **dostawcą danych** do tych raportów.

```
Pulpit / KPI          ──┐
Kampanie              ──┤
Słowa kluczowe        ──┤
Wyszukiwane frazy     ──┤
Rekomendacje          ──┤──→ AgentService.gather_data() ──→ Raport AI
Monitoring (Anomalie) ──┤                                ──→ Raporty
Historia akcji        ──┤
Prognoza              ──┤  ← brakuje
Optymalizacja SEARCH  ──┤  ← brakuje
Trend Explorer        ──┤  ← brakuje
Quality Score         ──┘  ← brakuje
```

---

## Stan aktualny — co już trafia do raportów

Źródło: `REPORT_DATA_MAP` w `agent_service.py`

| Sekcja danych | Typ raportu | Endpoint/źródło |
|---------------|-------------|-----------------|
| `kpis` | weekly, freeform, monthly, health | `/analytics/kpis` |
| `campaigns` | weekly, freeform | `/campaigns/` (top 30 by cost) |
| `campaigns_detail` | monthly, campaigns | rozszerzone metryki kampanii |
| `alerts` | weekly, freeform, monthly, alerts, health | `/alerts/` |
| `recommendations` | weekly | `/recommendations/` |
| `health` | weekly, monthly, alerts, health | `/clients/{id}/health` |
| `keywords` | keywords | `/keywords/` |
| `search_terms` | search_terms | `/search-terms/` |
| `budget_pacing` | monthly, campaigns, budget | `/analytics/budget-pacing` |
| `wasted_spend` | monthly, budget, health | `/analytics/wasted-spend` |
| `month_comparison` | monthly | `/analytics/compare-periods` |
| `change_history` | monthly | `/history/` |
| `change_impact` | monthly | `/history/impact` |
| `conversion_health` | health | `/analytics/conversion-health` |
| `quality_scores` | health | `/quality-score/` |
| `account_structure` | health | `/analytics/account-structure` |

---

## Luki — czego brakuje

### 1. Trend Explorer — korelacje
**Co wnosi:** top korelacje między metrykami za okres (np. CTR vs Konwersje r=0.63)  
**Wartość w raporcie:** AI może wyjaśnić "dlaczego CTR spada mimo rosnącego kosztu" mając r(CTR, koszt) = -0.49  
**Endpoint:** `GET /analytics/correlation?client_id=X&days=30` — **już istnieje**  
**Brakuje:** dodania sekcji `correlation` do `REPORT_DATA_MAP` dla typów `weekly`, `monthly`

```python
# agent_service.py — dodać do REPORT_DATA_MAP:
"weekly": [..., "correlation"],
"monthly": [..., "correlation"],

# _gather_section() — dodać case:
"correlation": self._get_correlation(client_id, days)
```

---

### 2. Prognoza
**Co wnosi:** 7-14 dniowa prognoza per kampania (slope, R², trend %, confidence)  
**Wartość w raporcie:** "Przy obecnym trendzie Koszt wzrośnie o 12% w przyszłym tygodniu"  
**Endpoint:** `GET /analytics/forecast?campaign_id=X&metric=cost` — **już istnieje**  
**Problem:** endpoint jest per-kampania — do raportu potrzebny agregat top 3-5 kampanii  
**Brakuje:** nowy endpoint `GET /analytics/forecast-summary?client_id=X` agregujący prognozy

```python
# Nowy endpoint lub nowa sekcja w AnalyticsService:
def get_forecast_summary(client_id, top_n=5, metric="cost"):
    # Pobiera top N kampanii by cost
    # Liczy forecast dla każdej
    # Zwraca: lista {campaign_name, slope, trend_pct, confidence, predicted_7d}
```

---

### 3. Optymalizacja SEARCH (wasted spend detail, n-gramy, dayparting)
**Co wnosi:** szczegółowe dane które nie są w ogólnym `wasted_spend` — n-gramy, godziny szczytu, problemy RSA  
**Wartość w raporcie:** "Frazy zawierające 'darmowy' generują 23% kosztu bez konwersji"  
**Endpointy:** `/analytics/wasted-spend`, `/analytics/ngrams`, `/analytics/dayparting` — **już istnieją**  
**Brakuje:** sekcji `search_optimization_summary` w `REPORT_DATA_MAP` dla `monthly`, `health`

---

### 4. Quality Score — szczegóły
**Aktualny stan:** `quality_scores` w raporcie `health` już jest  
**Brakuje:** w raportach `weekly` i `monthly` — skrót: "X keywords z QS < 5, średni QS = 6.2"  
**Nakład:** minimalny — ta sama sekcja, tylko dodać do innych typów raportów

---

### 5. Semantic / Inteligencja
**Co wnosi:** klastry tematyczne keywords z flagą waste  
**Wartość w raporcie:** "Klaster 'restauracja warszawa' marnuje 340 zł — brak konwersji"  
**Brakuje:** endpointu zwracającego top problematyczne klastry (już jest `/semantic/clusters` ale nie jest w `REPORT_DATA_MAP`)

---

## Priorytetyzacja

| # | Integracja | Nakład | Wartość | Priorytet |
|---|-----------|--------|---------|-----------|
| 1 | Trend Explorer → korelacje | ~1h | wysoka | v1.1 |
| 2 | Quality Score → weekly/monthly | ~1h | średnia | v1.1 |
| 3 | Prognoza summary endpoint | ~3h | wysoka | v1.1 |
| 4 | Optymalizacja SEARCH summary | ~4h | średnia | v1.2 |
| 5 | Semantic clusters | ~2h | niska | v1.2 |

---

## Docelowa mapa `REPORT_DATA_MAP` (po integracji)

```python
REPORT_DATA_MAP = {
    "weekly": [
        "kpis", "campaigns", "alerts", "recommendations", "health",
        "correlation",          # NOWE
        "quality_scores",       # NOWE
    ],
    "monthly": [
        "month_comparison", "campaigns_detail", "change_history",
        "change_impact", "budget_pacing", "wasted_spend", "alerts", "health",
        "correlation",          # NOWE
        "forecast_summary",     # NOWE
        "search_optimization_summary",  # NOWE (v1.2)
    ],
    "health": [
        "health", "kpis", "conversion_health", "quality_scores",
        "account_structure", "wasted_spend",
        "correlation",          # NOWE
        "semantic_clusters",    # NOWE (v1.2)
    ],
    # pozostałe typy bez zmian
}
```
