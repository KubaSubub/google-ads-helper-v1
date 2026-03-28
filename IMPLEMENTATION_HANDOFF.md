# IMPLEMENTATION_HANDOFF.md
## Zlecenie implementacyjne dla Claude Code
**Data:** 2026-03-22  
**Kontekst:** Wyniki gap analysis workflow specjalistów PPC vs. Google Ads Helper v1  
**Repo:** https://github.com/KubaSubub/google-ads-helper-v1  
**Priorytet:** Realizuj w kolejności Sprint 1 → Sprint 2 → Sprint 3. Nie zaczynaj następnego sprintu bez ukończenia poprzedniego.

---

## Jak czytać ten dokument

Każdy task ma:
- **Lokalizację** — konkretny plik do edycji
- **Logikę** — pseudokod lub warunki
- **Dane** — skąd brać (co już jest w DB vs. co trzeba sync)
- **Test** — jak zweryfikować że działa
- **Effort** — szacunkowy czas

Wszystkie zmiany muszą:
1. Przejść `pytest --tb=short -q` (backend: 355 testów baseline)
2. Przejść `npm run build` (frontend)
3. Przejść `npm run test` (frontend)
4. Nie łamać żadnego istniejącego API contract

---

## SPRINT 1 — Quick Wins (dane już w DB, tylko logika) ~20-25h

### TASK 1.1: Reguła R8 — Quality Score Alert

**Plik:** `backend/app/services/recommendations.py`  
**Typ:** Nowa reguła w engine, kategoria ALERT

**Logika:**
```python
# Dla każdego klienta, dla każdego ENABLED keyword:
IF keyword.quality_score IS NOT NULL
   AND keyword.quality_score < 5
   AND keyword.impressions_last_30d > 100:

    priority = HIGH if keyword.quality_score <= 2 else MEDIUM

    # Określ najsłabszy subkomponent (1=BELOW_AVG, 2=AVG, 3=ABOVE_AVG)
    components = {
        "Expected CTR": keyword.historical_search_predicted_ctr,
        "Ad Relevance": keyword.historical_creative_quality,
        "Landing Page": keyword.historical_landing_page_quality,
    }
    worst = min(components, key=components.get)

    CREATE Recommendation(
        type=RecommendationType.QS_ALERT,
        category="ALERT",  # nie RECOMMENDATION
        priority=priority,
        title=f"Quality Score {keyword.quality_score}/10 — {keyword.text}",
        description=f"Najsłabszy komponent: {worst}. Keyword w ad group '{keyword.ad_group_name}'.",
        entity_type="KEYWORD",
        entity_id=keyword.id,
        evidence={
            "quality_score": keyword.quality_score,
            "worst_component": worst,
            "component_scores": components,
            "impressions": keyword.impressions_last_30d,
        }
    )
```

**Dane:** Kolumny `quality_score`, `historical_search_predicted_ctr`, `historical_creative_quality`, `historical_landing_page_quality` już na modelu `Keyword`. Zero zmian w sync.

**Enum do dodania** w `RecommendationType`:
```python
QS_ALERT = "QS_ALERT"
```

**Kolumna do dodania** na modelu `Recommendation` (jeśli nie istnieje):
```python
category = Column(String(20), default="RECOMMENDATION")  # RECOMMENDATION | ALERT
```

**Test:** Utwórz test w `backend/tests/test_recommendations_contract.py`:
- Keyword z QS=3, impr=500 → generuje QS_ALERT MEDIUM
- Keyword z QS=1, impr=200 → generuje QS_ALERT HIGH  
- Keyword z QS=7 → nie generuje alertu
- Keyword z QS=3, impr=50 → nie generuje alertu (za mało danych)

**Effort:** 1-2h

---

### TASK 1.2: Reguła R9 — Impression Share Lost to Budget

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
# Dla każdej SEARCH kampanii ENABLED:
IF campaign.search_budget_lost_is > 0.20
   AND campaign.conversions_last_30d > 0
   AND campaign.roas_last_30d >= (target_roas * 0.8 if target_roas else 0):

    lost_pct = campaign.search_budget_lost_is * 100
    priority = HIGH if lost_pct > 40 else MEDIUM

    CREATE Recommendation(
        type=RecommendationType.IS_BUDGET_ALERT,
        category="RECOMMENDATION",
        priority=priority,
        title=f"Tracisz {lost_pct:.0f}% wyświetleń przez budżet — {campaign.name}",
        description=f"Kampania ma zdrowy ROAS ale jest ograniczona budżetem. Rozważ zwiększenie budżetu o ~20%.",
        entity_type="CAMPAIGN",
        entity_id=campaign.id,
        evidence={
            "is_lost_budget": campaign.search_budget_lost_is,
            "is_lost_rank": campaign.search_rank_lost_is,
            "roas": campaign.roas_last_30d,
            "conversions": campaign.conversions_last_30d,
        },
        suggested_action="INCREASE_BUDGET",
        suggested_value=campaign.budget_micros * 1.20,  # +20%
    )

# Wariant 2: kampania wyczerpuje budżet przy złym CPA
IF campaign.search_budget_lost_is > 0.50
   AND campaign.cpa_last_30d > (target_cpa * 1.2 if target_cpa else campaign.avg_cpa * 1.2):

    CREATE Recommendation(
        type=RecommendationType.IS_BUDGET_ALERT,
        priority=HIGH,
        title=f"Kampania wyczerpuje budżet za wcześnie przy wysokim CPA — {campaign.name}",
        description=f"Tracisz {campaign.search_budget_lost_is*100:.0f}% wyświetleń ale CPA jest za wysoki. Obniż stawki.",
        suggested_action="DECREASE_BID",
    )
```

**Dane:** Kolumna `search_budget_lost_is` = `search_budget_lost_is` na modelu Campaign (zsynchronizowane przez `sync_campaign_impression_share()`). Zero zmian.

**Enum do dodania:**
```python
IS_BUDGET_ALERT = "IS_BUDGET_ALERT"
IS_RANK_ALERT = "IS_RANK_ALERT"
```

**Uwaga:** `INCREASE_BUDGET` jako suggested_action — sprawdź czy `validate_action()` w `action_executor.py` obsługuje ten typ. Jeśli nie — dodaj walidację lub oznacz jako non-executable (jak REALLOCATE_BUDGET).

**Test:** Kampania z search_budget_lost_is=0.35, conv>0 → IS_BUDGET_ALERT MEDIUM

**Effort:** 2h

---

### TASK 1.3: Reguła R10 — IS Lost to Rank Alert

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
IF campaign.search_rank_lost_is > 0.30
   AND campaign.search_budget_lost_is < 0.10:  # nie jest problem budżetu

    CREATE Recommendation(
        type=RecommendationType.IS_RANK_ALERT,
        category="ALERT",
        priority=MEDIUM,
        title=f"Tracisz {campaign.search_rank_lost_is*100:.0f}% wyświetleń przez niski Ad Rank — {campaign.name}",
        description="Nie jest to problem budżetu — sprawdź Quality Score keywords i trafność reklam. Niski Ad Rank = niskie QS lub za niskie stawki.",
        entity_type="CAMPAIGN",
        entity_id=campaign.id,
        evidence={
            "is_lost_rank": campaign.search_rank_lost_is,
            "is_lost_budget": campaign.search_budget_lost_is,
        }
    )
```

**Effort:** 1h

---

### TASK 1.4: Reguła R11 — Low CTR High Impressions (match type)

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
IF keyword.ctr < 0.005  # < 0.5%
   AND keyword.impressions_last_30d > 1000
   AND keyword.conversions_last_30d == 0
   AND keyword.match_type IN ('BROAD', 'PHRASE')
   AND keyword.status == 'ENABLED':

    CREATE Recommendation(
        type=RecommendationType.LOW_CTR_KEYWORD,
        category="RECOMMENDATION",
        priority=MEDIUM,
        title=f"Niski CTR przy wysokich wyświetleniach — '{keyword.text}'",
        description=f"CTR {keyword.ctr*100:.2f}% przy {keyword.impressions_last_30d} wyświetleniach. Match type {keyword.match_type} może generować nietrafny ruch.",
        entity_type="KEYWORD",
        entity_id=keyword.id,
        evidence={
            "ctr": keyword.ctr,
            "impressions": keyword.impressions_last_30d,
            "match_type": keyword.match_type,
        },
        suggested_action="PAUSE_KEYWORD",  # lub zmiana match type — na razie pauza
    )
```

**Enum:** `LOW_CTR_KEYWORD = "LOW_CTR_KEYWORD"`

**Uwaga:** R1 sprawdza `cost/clicks/conv`, R11 sprawdza `CTR/impressions/match_type` — komplementarne, nie duplikujące. Keyword może trafić do obu.

**Effort:** 1h

---

### TASK 1.5: Reguła R12 — Wasted Spend Alert

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
# Per klient, nie per kampania (alert na poziomie konta)
total_spend = SUM(keyword.cost_micros WHERE date IN last_30_days)
wasted_spend = SUM(keyword.cost_micros WHERE date IN last_30_days AND keyword.conversions == 0)
wasted_pct = wasted_spend / total_spend if total_spend > 0 else 0

IF wasted_pct > 0.25 AND total_spend > 50_000_000:  # >$50 spend, >25% wasted

    priority = HIGH if wasted_pct > 0.35 else MEDIUM

    CREATE Recommendation(
        type=RecommendationType.WASTED_SPEND_ALERT,
        category="ALERT",
        priority=priority,
        title=f"{wasted_pct*100:.0f}% budżetu bez konwersji",
        description=f"${wasted_spend/1_000_000:.0f} wydane na keywords bez żadnej konwersji w ostatnich 30 dniach.",
        entity_type="CLIENT",
        entity_id=client_id,
        evidence={
            "wasted_pct": wasted_pct,
            "wasted_spend_micros": wasted_spend,
            "total_spend_micros": total_spend,
        }
    )
```

**Dane:** Reużyj `analytics_service.get_wasted_spend()` który już istnieje — wywołaj go z poziomu reguły.

**Enum:** `WASTED_SPEND_ALERT = "WASTED_SPEND_ALERT"`

**Effort:** 1-2h

---

### TASK 1.6: Reguła R13 — PMax vs Search Cannibalization

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
# Znajdź search terms które pojawiają się JEDNOCZEŚNIE w Search i PMax:
search_terms_by_source = GROUP search_terms BY (client_id, query_text, campaign.campaign_type)

for query_text, sources in search_terms_by_source.items():
    has_search = any(s.campaign_type == 'SEARCH' for s in sources)
    has_pmax = any(s.campaign_type == 'PERFORMANCE_MAX' for s in sources)

    if has_search and has_pmax:
        pmax_cost = SUM(s.cost_micros for s in sources if s.campaign_type == 'PERFORMANCE_MAX')
        search_keyword = find_keyword_matching(query_text, client_id)

        if pmax_cost > 50_000_000:  # PMax wydał > $50 na ten term
            priority = HIGH
        elif pmax_cost > 0:
            priority = MEDIUM
        else:
            continue

        if search_keyword and search_keyword.match_type != 'EXACT':
            tip = f"Dodaj '{query_text}' jako exact match w Search lub jako negative w PMax."
        else:
            tip = f"PMax wydaje ${pmax_cost/1_000_000:.0f} na ten term. Sprawdź priorytet kampanii."

        CREATE Recommendation(
            type=RecommendationType.PMAX_CANNIBALIZATION,
            category="ALERT",
            priority=priority,
            title=f"Overlap Search/PMax: '{query_text}'",
            description=tip,
            entity_type="SEARCH_TERM",
            evidence={
                "query": query_text,
                "pmax_cost_micros": pmax_cost,
                "has_exact_match": (search_keyword.match_type == 'EXACT' if search_keyword else False),
            }
        )
```

**Dane:** `SearchTerm.source` (SEARCH/PMAX), `Campaign.campaign_type` — wszystko w DB.

**Enum:** `PMAX_CANNIBALIZATION = "PMAX_CANNIBALIZATION"`

**Effort:** 3h

---

### TASK 1.7: Reguły R15/R16 — Device/Geo Anomaly Alerts

**Plik:** `backend/app/services/recommendations.py`

**Logika R15 (Device):**
```python
# Reużyj analytics_service.get_device_breakdown(client_id, days=30)
breakdown = get_device_breakdown(client_id, days=30)

for campaign_id, devices in breakdown.items():
    desktop = devices.get('DESKTOP', {})
    mobile = devices.get('MOBILE', {})

    if (mobile.get('spend', 0) > 100
        and desktop.get('cpa') and mobile.get('cpa')
        and mobile['cpa'] > desktop['cpa'] * 2.0):

        CREATE Recommendation(
            type=RecommendationType.DEVICE_ANOMALY,
            category="ALERT",
            priority=MEDIUM,
            title=f"CPA mobile 2x wyższe niż desktop — {campaign_name}",
            description=f"Mobile CPA: ${mobile['cpa']:.2f} vs Desktop CPA: ${desktop['cpa']:.2f}. Rozważ bid adjustment -20% do -50% na mobile lub dedykowany landing page.",
            entity_type="CAMPAIGN",
            entity_id=campaign_id,
            evidence={"mobile_cpa": mobile['cpa'], "desktop_cpa": desktop['cpa'], "mobile_spend": mobile['spend']}
        )
```

**Logika R16 (Geo):** Analogiczna, reużyj `get_geo_breakdown()`.

**Enum:**
```python
DEVICE_ANOMALY = "DEVICE_ANOMALY"
GEO_ANOMALY = "GEO_ANOMALY"
```

**Effort:** 2h łącznie

---

### TASK 1.8: Reguła R17 — Budget Pacing Alert

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
from datetime import date
import calendar

today = date.today()
days_in_month = calendar.monthrange(today.year, today.month)[1]
day_of_month = today.day
month_progress = day_of_month / days_in_month  # np. 0.5 = połowa miesiąca

for campaign in enabled_campaigns:
    # Zsumuj spend od początku miesiąca
    month_start = today.replace(day=1)
    actual_spend = SUM(metric_daily.cost_micros WHERE campaign_id=campaign.id AND date >= month_start)

    # Budżet dzienny * dni w miesiącu = miesięczny budżet
    monthly_budget = campaign.budget_micros * days_in_month
    expected_spend = monthly_budget * month_progress

    if expected_spend > 0:
        spend_ratio = actual_spend / expected_spend

        if spend_ratio > 1.30 and month_progress > 0.1:  # wydaje za szybko
            CREATE Recommendation(
                type=RecommendationType.BUDGET_PACING,
                priority=HIGH,
                title=f"Kampania wydaje za szybko — {campaign.name}",
                description=f"Wydano {actual_spend/monthly_budget*100:.0f}% budżetu przy {month_progress*100:.0f}% miesiąca.",
                evidence={"spend_ratio": spend_ratio, "month_progress": month_progress}
            )

        elif spend_ratio < 0.50 and month_progress > 0.30:  # niedowydaje
            CREATE Recommendation(
                type=RecommendationType.BUDGET_PACING,
                priority=MEDIUM,
                title=f"Kampania niedowydaje — {campaign.name}",
                description=f"Wydano tylko {actual_spend/monthly_budget*100:.0f}% budżetu przy {month_progress*100:.0f}% miesiąca.",
                evidence={"spend_ratio": spend_ratio, "month_progress": month_progress}
            )
```

**Dane:** `campaign.budget_micros` + tabela `metric_daily` — wszystko w DB.

**Enum:** `BUDGET_PACING = "BUDGET_PACING"`

**Effort:** 2h

---

### TASK 1.9: Reguła R18 — N-gram Negative Detection

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
# Reużyj analytics_service.get_ngram_analysis(client_id, days=30)
ngrams = get_ngram_analysis(client_id, days=30)

for ngram in ngrams:
    if (ngram['total_cost'] > 100  # $100 spend
        and ngram['total_conversions'] == 0
        and ngram['term_count'] >= 3):  # pojawia się w min. 3 search terms

        CREATE Recommendation(
            type=RecommendationType.NGRAM_NEGATIVE,
            category="RECOMMENDATION",
            priority=HIGH,
            title=f"N-gram '{ngram['text']}' — {ngram['term_count']} terminów, ${ngram['total_cost']:.0f}, 0 konwersji",
            description=f"Wzorzec '{ngram['text']}' pojawia się w {ngram['term_count']} search terms bez konwersji. Dodaj jako broad match negative.",
            entity_type="SEARCH_TERM_PATTERN",
            evidence={
                "ngram": ngram['text'],
                "term_count": ngram['term_count'],
                "total_cost_micros": ngram['total_cost_micros'],
                "example_terms": ngram['example_terms'][:3],
            },
            suggested_action="ADD_NEGATIVE",
            suggested_value=ngram['text'],  # tekst do dodania jako negative
        )
```

**Dane:** Reużyj `get_ngram_analysis()` w `analytics_service.py` — już istnieje.

**Enum:** `NGRAM_NEGATIVE = "NGRAM_NEGATIVE"`

**Effort:** 3h

---

### TASK 1.10: Frontend — zaktualizuj Recommendations UI o nowe typy

**Plik:** `frontend/src/pages/Recommendations.jsx`

Dodaj do `TYPE_CONFIG` wpisy dla wszystkich nowych typów z TASK 1.1–1.9:
```javascript
QS_ALERT: { label: 'Quality Score', icon: '⚠️', color: '#f5a623', category: 'alert' },
IS_BUDGET_ALERT: { label: 'Impression Share — Budżet', icon: '📊', color: '#3d7fff', category: 'recommendation' },
IS_RANK_ALERT: { label: 'Impression Share — Ad Rank', icon: '📉', color: '#7a8499', category: 'alert' },
LOW_CTR_KEYWORD: { label: 'Niski CTR', icon: '🔍', color: '#f5a623', category: 'recommendation' },
WASTED_SPEND_ALERT: { label: 'Przepalony Budżet', icon: '💸', color: '#ff4d6a', category: 'alert' },
PMAX_CANNIBALIZATION: { label: 'PMax Kanibalizacja', icon: '⚔️', color: '#ff4d6a', category: 'alert' },
DEVICE_ANOMALY: { label: 'Anomalia Urządzeń', icon: '📱', color: '#f5a623', category: 'alert' },
GEO_ANOMALY: { label: 'Anomalia Lokalizacji', icon: '📍', color: '#f5a623', category: 'alert' },
BUDGET_PACING: { label: 'Tempo Budżetu', icon: '⏱️', color: '#f5a623', category: 'alert' },
NGRAM_NEGATIVE: { label: 'N-gram do Wykluczenia', icon: '🚫', color: '#ff4d6a', category: 'recommendation' },
```

Dodaj filtrowanie: tab "Rekomendacje" (category=recommendation) i tab "Alerty" (category=alert).

**Effort:** 2h

---

### TASK 1.11: GAP 1B — Conversion Data Starvation Alert

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
# Dla każdej kampanii z Smart Bidding (nie Manual CPC):
SMART_BIDDING_TYPES = ['TARGET_CPA', 'TARGET_ROAS', 'MAXIMIZE_CONVERSIONS', 'MAXIMIZE_CONVERSION_VALUE']

for campaign in client_campaigns:
    if campaign.bidding_strategy_type not in SMART_BIDDING_TYPES:
        continue

    # Policz konwersje last 30 days z metric_daily
    conv_30d = SUM(metric_daily.conversions WHERE campaign_id=campaign.id AND date >= today-30)

    if conv_30d < 50:
        CREATE Recommendation(
            type=RecommendationType.SMART_BIDDING_DATA_STARVATION,
            category="ALERT",
            priority=HIGH if conv_30d < 20 else MEDIUM,
            title=f"Zbyt mało danych dla Smart Bidding — {campaign.name}",
            description=f"Kampania ma {conv_30d} konwersji w ostatnich 30 dniach. Smart Bidding potrzebuje min. 50/miesiąc żeby działać optymalnie. Algorytm zgaduje.",
            entity_type="CAMPAIGN",
            entity_id=campaign.id,
            evidence={
                "conversions_30d": conv_30d,
                "threshold_min": 50,
                "threshold_optimal": 200,
                "bidding_strategy": campaign.bidding_strategy_type,
            }
        )
```

**Dane:** `campaign.bidding_strategy_type` już synchronizowane. `metric_daily.conversions` w DB. Zero nowych danych.

**Enum:** `SMART_BIDDING_DATA_STARVATION = "SMART_BIDDING_DATA_STARVATION"`

**Effort:** 2h

---

### TASK 1.12: GAP 8 — Ad Group Health Alerts

**Plik:** `backend/app/services/recommendations.py`

**Logika:**
```python
for ad_group in client_ad_groups:
    if ad_group.status != 'ENABLED':
        continue

    # Alert: tylko 1 aktywna reklama (brak A/B testing)
    active_ads = COUNT(ads WHERE ad_group_id=ad_group.id AND status='ENABLED')
    if active_ads < 2:
        CREATE Recommendation(
            type=RecommendationType.SINGLE_AD_ALERT,
            category="ALERT",
            priority=LOW,
            title=f"Tylko {active_ads} reklama w grupie '{ad_group.name}'",
            description="Minimum 2 reklamy RSA per ad group dla A/B testing. Google potrzebuje rotacji żeby uczyć się.",
        )

    # Alert: za dużo keywords w ad group
    keyword_count = COUNT(keywords WHERE ad_group_id=ad_group.id AND status='ENABLED')
    if keyword_count > 20:
        CREATE Recommendation(
            type=RecommendationType.OVERSIZED_AD_GROUP,
            category="ALERT",
            priority=LOW,
            title=f"Za dużo keywords w grupie '{ad_group.name}' ({keyword_count})",
            description="Więcej niż 20 keywords = słabe message match. Rozważ podział na mniejsze grupy.",
        )

    # Alert: ad group bez konwersji last 30 days przy spend > threshold
    ag_spend = SUM(keyword.cost WHERE ad_group_id=ad_group.id AND date in last_30)
    ag_conv = SUM(keyword.conversions WHERE ad_group_id=ad_group.id AND date in last_30)
    if ag_spend > 100_000_000 and ag_conv == 0:  # $100 spend, 0 conv
        CREATE Recommendation(
            type=RecommendationType.ZERO_CONV_AD_GROUP,
            category="ALERT",
            priority=MEDIUM,
            title=f"Ad group '{ad_group.name}' — ${ag_spend/1e6:.0f} bez konwersji (30 dni)",
        )
```

**Dane:** `ad_groups`, `keywords`, `ads` — wszystkie tabele w DB. Zero nowych danych.

**Enum:**
```python
SINGLE_AD_ALERT = "SINGLE_AD_ALERT"
OVERSIZED_AD_GROUP = "OVERSIZED_AD_GROUP"
ZERO_CONV_AD_GROUP = "ZERO_CONV_AD_GROUP"
```

**Effort:** 3h

---

## SPRINT 2 — Post-Change Delta & Pareto ~12h

### TASK 2.1: GAP 6A — Post-Change Performance Delta (PRIORYTET — unikalna funkcja)

Ten feature jest możliwy BEZ ŻADNYCH NOWYCH DANYCH Z API. Wszystko jest w `action_log` + `metric_daily`.

**Nowy endpoint:**

**Plik:** `backend/app/routers/analytics.py`

```python
@router.get("/analytics/change-impact")
async def get_change_impact(
    client_id: int,
    action_log_id: Optional[int] = None,  # konkretna akcja lub None = wszystkie last 30 dni
    days_window: int = 7,  # porównaj 7 dni przed vs 7 dni po
    db: Session = Depends(get_db)
):
    """
    Dla każdej akcji z action_log (ostatnie 30 dni):
    - pobierz datę wykonania akcji
    - policz KPI (cost, conversions, CPA, CTR) window dni PRZED
    - policz KPI window dni PO
    - zwróć delta jako % i wartość bezwzględną
    """
```

**Implementacja w `analytics_service.py`:**

```python
def get_change_impact(self, client_id: int, days_window: int = 7, action_log_id: int = None):
    # Pobierz akcje z action_log last 30 dni
    actions = db.query(ActionLog).filter(
        ActionLog.client_id == client_id,
        ActionLog.status == 'COMPLETED',
        ActionLog.executed_at >= today - 30 days,
    ).all()

    if action_log_id:
        actions = [a for a in actions if a.id == action_log_id]

    results = []
    for action in actions:
        action_date = action.executed_at.date()
        before_start = action_date - timedelta(days=days_window)
        after_end = action_date + timedelta(days=days_window)

        # Pobierz metryki dla kampanii/ad group/keyword której dotyczyła akcja
        entity_filter = build_entity_filter(action)  # na podstawie action.entity_type + entity_id

        before_metrics = aggregate_metrics(
            db, client_id, entity_filter,
            date_from=before_start, date_to=action_date - 1
        )
        after_metrics = aggregate_metrics(
            db, client_id, entity_filter,
            date_from=action_date, date_to=after_end
        )

        delta = {
            "cost_delta_pct": pct_change(before_metrics['cost'], after_metrics['cost']),
            "conversions_delta_pct": pct_change(before_metrics['conv'], after_metrics['conv']),
            "cpa_delta_pct": pct_change(before_metrics['cpa'], after_metrics['cpa']),
            "ctr_delta_pct": pct_change(before_metrics['ctr'], after_metrics['ctr']),
        }

        results.append({
            "action": action_to_dict(action),
            "before": before_metrics,
            "after": after_metrics,
            "delta": delta,
            "verdict": "POSITIVE" if delta['cpa_delta_pct'] < -10 else "NEGATIVE" if delta['cpa_delta_pct'] > 10 else "NEUTRAL",
            "days_since_action": (today - action_date).days,
            "data_available": after_end <= today,  # czy mamy pełne 7 dni "po"?
        })

    return sorted(results, key=lambda x: abs(x['delta']['cpa_delta_pct']), reverse=True)
```

**Nowa strona w frontend:**

**Plik:** `frontend/src/pages/ChangeImpact.jsx`

Widok: lista wykonanych akcji z kolorowym wskaźnikiem efektu:
- 🟢 CPA spadło >10% po akcji
- 🔴 CPA wzrosło >10% po akcji  
- ⚪ Brak wyraźnej zmiany
- 🕐 Za wcześnie na ocenę (< 7 dni po akcji)

Każda akcja expandowalna: show before/after tabela z KPI.

Dodaj do `Sidebar.jsx` i `App.jsx` pod nazwą "Wpływ Zmian".

**Testy:**
- `backend/tests/test_change_impact.py`: akcja sprzed 14 dni ma before/after metrics
- Akcja sprzed 3 dni → `data_available: false`
- Akcja dla nieistniejącej kampanii → empty metrics, nie crash

**Effort:** 6-8h

---

### TASK 2.2: GAP 7 — Pareto / 80-20 View

**Nowy endpoint:**

**Plik:** `backend/app/routers/analytics.py`

```python
@router.get("/analytics/pareto")
async def get_pareto_analysis(
    client_id: int,
    days: int = 30,
    entity_type: str = "CAMPAIGN",  # CAMPAIGN | KEYWORD | AD_GROUP
    metric: str = "conversions",    # conversions | cost | roas
    db: Session = Depends(get_db)
):
    """
    Zwraca posortowaną listę entities z kumulatywnym % konwersji/kosztu.
    Flaguje: HERO (top 20%), MAIN (środek), TAIL (bottom 20% generujące <5% wartości).
    """
```

**Implementacja:**
```python
def get_pareto_analysis(client_id, days, entity_type, metric):
    entities = get_entities_with_metrics(client_id, days, entity_type)
    total = sum(e[metric] for e in entities)

    sorted_entities = sorted(entities, key=lambda x: x[metric], reverse=True)

    cumulative = 0
    results = []
    for i, entity in enumerate(sorted_entities):
        cumulative += entity[metric]
        cumulative_pct = cumulative / total if total > 0 else 0

        # Flaga Pareto
        entity_pct_of_total = entity[metric] / total if total > 0 else 0
        if i < len(sorted_entities) * 0.20:
            flag = "HERO"
        elif cumulative_pct >= 0.95:
            flag = "TAIL"
        else:
            flag = "MAIN"

        results.append({
            **entity,
            "cumulative_pct": cumulative_pct,
            "entity_pct": entity_pct_of_total,
            "pareto_flag": flag,
            "rank": i + 1,
        })

    summary = {
        "hero_count": len([r for r in results if r['pareto_flag'] == 'HERO']),
        "hero_pct_of_total": sum(r['entity_pct'] for r in results if r['pareto_flag'] == 'HERO'),
        "tail_count": len([r for r in results if r['pareto_flag'] == 'TAIL']),
    }

    return {"entities": results, "summary": summary, "total": total}
```

**Frontend — dodaj sekcję do Dashboard lub osobna strona "Analiza Pareto":**

Widok: wykres słupkowy + tabela z kolorowymi flagami HERO/MAIN/TAIL.

Alert dla hero kampanii: jeśli `pareto_flag == 'HERO'` i `search_budget_lost_is > 0.20` → "Hero kampania ograniczona budżetem — to pierwsza do skalowania."

**Testy:**
- Klient z 5 kampaniami → top 1 to HERO, bottom 2 to TAIL
- Klient bez konwersji → graceful empty state

**Effort:** 4-6h

---

## SPRINT 3 — Smart Bidding Health Layer ~12h

> ⚠️ Sprint 3 wymaga rozszerzenia sync. Zanim zaczniesz — przejrzyj `backend/app/services/google_ads.py` i potwierdź aktualne pole `campaign.bidding_strategy_type`.

### TASK 3.1: Sync — dodaj brakujące pola do kampanii

**Plik:** `backend/app/services/google_ads.py` — metoda `sync_campaigns()`

Dodaj do GAQL zapytania kampanii:
```sql
-- Dodaj do istniejącego SELECT:
campaign.target_cpa.target_cpa_micros,
campaign.target_roas.target_roas,
campaign.maximize_conversions.target_cpa_micros AS max_conv_target_cpa,
campaign.maximize_conversion_value.target_roas AS max_value_target_roas,
```

**Plik:** `backend/app/models.py` — model `Campaign`

Dodaj kolumny:
```python
target_cpa_micros = Column(BigInteger, nullable=True)
target_roas = Column(Float, nullable=True)
```

**Migracja:** Utwórz nową migrację Alembic lub dodaj kolumny przez `ALTER TABLE` jeśli projekt używa bezpośrednich migracji. Sprawdź pattern w istniejących migracjach.

**Effort:** 2h

---

### TASK 3.2: GAP 10 — Bid Strategy Target vs. Actual

**Nowy endpoint:**

**Plik:** `backend/app/routers/analytics.py`

```python
@router.get("/analytics/bid-strategy-health")
async def get_bid_strategy_health(client_id: int, days: int = 30, db=Depends(get_db)):
    """
    Per kampania z Smart Bidding:
    - target CPA/ROAS (z campaign model po TASK 3.1)
    - actual CPA/ROAS (wyliczone z metric_daily)
    - trend last 30 dni (7-dniowe rolling average)
    - verdict: ON_TARGET | TOO_AGGRESSIVE | TOO_LOOSE | NO_DATA
    """
```

**Implementacja:**
```python
for campaign in smart_bidding_campaigns:
    actual_cpa = total_cost / total_conv if total_conv > 0 else None
    actual_roas = total_conv_value / total_cost if total_cost > 0 else None

    if campaign.target_cpa_micros and actual_cpa:
        target = campaign.target_cpa_micros / 1_000_000
        ratio = actual_cpa / target
        verdict = (
            "TOO_AGGRESSIVE" if ratio > 1.5 else  # algorytm nie dowozi
            "TOO_LOOSE" if ratio < 0.5 else        # target za łagodny
            "ON_TARGET"
        )
    # analogicznie dla tROAS
```

**Reguła w engine (TASK 3.2B):**
```python
# Po sync nowych pól (TASK 3.1):
IF actual_cpa > target_cpa * 1.5 AND days_above_target >= 14:
    CREATE Recommendation(BID_STRATEGY_UNDERPERFORMING, HIGH)

IF actual_cpa < target_cpa * 0.5 AND days_below_target >= 14:
    CREATE Recommendation(BID_STRATEGY_TARGET_TOO_LOOSE, MEDIUM,
        description="Actual CPA znacznie poniżej targetu — możesz obniżyć tCPA i zdobyć więcej konwersji.")
```

**Enum:**
```python
BID_STRATEGY_UNDERPERFORMING = "BID_STRATEGY_UNDERPERFORMING"
BID_STRATEGY_TARGET_TOO_LOOSE = "BID_STRATEGY_TARGET_TOO_LOOSE"
```

**Effort:** 4h

---

### TASK 3.3: GAP 1A+1C — Learning Period + ECPC Deprecation

**Logika (po weryfikacji że `bidding_strategy_type` jest w DB):**

```python
# Learning Period Detection
# Uwaga: Google Ads API udostępnia learning_stage przez campaign.bidding_strategy.
# Jeśli nie jest synchronizowany — użyj proxy: kampania zmieniła bid strategy
# w ostatnich 7 dniach (z change_events) i ma <10 conv od zmiany.

def detect_learning_campaigns(client_id, db):
    recent_changes = db.query(ChangeEvent).filter(
        ChangeEvent.client_id == client_id,
        ChangeEvent.change_type.contains('BID_STRATEGY'),
        ChangeEvent.changed_at >= today - 14 days,
    ).all()

    for change in recent_changes:
        campaign = get_campaign(change.campaign_id)
        days_since_change = (today - change.changed_at.date()).days
        conv_since_change = SUM(metric_daily.conversions WHERE
            campaign_id=change.campaign_id AND date >= change.changed_at.date())

        if days_since_change > 7 and conv_since_change < 10:
            CREATE Recommendation(
                type=RecommendationType.LEARNING_PERIOD_EXTENDED,
                priority=MEDIUM,
                title=f"Kampania może być w trybie uczenia — {campaign.name}",
                description=f"Zmiana strategii {days_since_change} dni temu, {conv_since_change} konwersji od zmiany. Unikaj kolejnych zmian przez min. 7-14 dni.",
            )

# ECPC Deprecation Alert
for campaign in client_campaigns:
    if campaign.bidding_strategy_type == 'MANUAL_CPC':
        # Sprawdź change_events: czy wcześniej miała ENHANCED_CPC?
        ecpc_to_manual = db.query(ChangeEvent).filter(
            ChangeEvent.campaign_id == campaign.id,
            ChangeEvent.old_value.contains('ENHANCED_CPC'),
            ChangeEvent.changed_at >= '2025-03-01',
        ).first()

        if ecpc_to_manual:
            CREATE Recommendation(
                type=RecommendationType.ECPC_DEPRECATED,
                priority=HIGH,
                title=f"Kampania przeszła na Manual CPC po wycofaniu ECPC — {campaign.name}",
                description="ECPC zostało wycofane w marcu 2025. Ta kampania automatycznie przeszła na Manual CPC. Zalecane: migracja na tCPA lub Maximize Conversions.",
            )
```

**Enum:**
```python
LEARNING_PERIOD_EXTENDED = "LEARNING_PERIOD_EXTENDED"
ECPC_DEPRECATED = "ECPC_DEPRECATED"
```

**Effort:** 3-4h

---

## Wymagania dla każdego tasku

### Przy każdym nowym typie Recommendation:
1. Dodaj do `RecommendationType` enum w `backend/app/models.py`
2. Dodaj do `TYPE_CONFIG` w `frontend/src/pages/Recommendations.jsx`
3. Napisz minimum 2 testy backend w odpowiednim pliku test
4. Uruchom pełny `pytest --tb=short -q` — musi przejść bez regresji

### Przy każdym nowym endpoincie analytics:
1. Dodaj do `backend/app/routers/analytics.py`
2. Zarejestruj w `backend/app/main.py` jeśli router jest osobny
3. Dodaj funkcję w `frontend/src/api.js`
4. Napisz minimum 3 testy w `backend/tests/test_analytics_endpoints.py`

### Przy każdej nowej stronie frontend:
1. Utwórz `frontend/src/pages/NazwaStrony.jsx`
2. Dodaj route w `frontend/src/App.jsx`
3. Dodaj do `frontend/src/components/Sidebar.jsx`
4. Dodaj smoke test w `frontend/e2e/smoke.spec.js` (wzoruj na istniejących 19 testach)

---

## Kolejność realizacji (optymalna)

```
Sprint 1: TASK 1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 → 1.8 → 1.9 → 1.10 → 1.11 → 1.12
Sprint 2: TASK 2.1 (change impact — unikalna, priorytet) → 2.2 (pareto)
Sprint 3: TASK 3.1 (sync) → 3.2 (bid strategy health) → 3.3 (learning + ecpc)
```

Każdy sprint kończy się:
- `pytest --tb=short -q` → wszystkie testy zielone
- `cd frontend && npm run build` → build bez błędów
- Aktualizacja `PROGRESS.md` z nowym stanem

---

## Pliki referencyjne do przeczytania przed implementacją

- `backend/app/services/recommendations.py` — wzorzec istniejących reguł R1-R7
- `backend/app/services/analytics_service.py` — istniejące metody do reużycia
- `backend/app/models.py` — definicje tabel i enums
- `backend/app/routers/analytics.py` — wzorzec istniejących endpointów
- `backend/tests/test_analytics_endpoints.py` — wzorzec testów
- `frontend/src/pages/Recommendations.jsx` — wzorzec TYPE_CONFIG i UI
- `DECISIONS.md` — architectural decisions (nie łam istniejących decyzji)
- `CLAUDE.md` — reguły projektu (pre-commit hooks, naming conventions)
