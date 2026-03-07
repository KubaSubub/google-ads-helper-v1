# Plan rozszerzenia Recommendations Engine
## Mapowanie checklisty optymalizacyjnej na Google Ads Helper v1.1+

**Wersja:** 2.0
**Data:** 2026-03-07
**Status:** Zaktualizowany — zweryfikowany vs kod (marzec 2026)
**Kontekst:** Dokument definiuje, które elementy eksperckiej checklisty optymalizacyjnej Google Ads mogą zostać zaimplementowane jako nowe reguły w recommendations engine — po ukończeniu MVP (7 reguł, Phase 1–4).

---

## 1. Stan obecny (MVP — 7 reguł)

Obecny recommendations engine implementuje 7 reguł zdefiniowanych w Playbooku i PRD:

| ID | Reguła | Priorytet | Typ akcji |
|----|--------|-----------|-----------|
| R1 | Pause Keyword: (A) cost ≥ $50, conv=0, clicks ≥ 30 [HIGH] + (B) impr ≥ 1000, CTR < 0.5% [MEDIUM] | HIGH/MEDIUM | PAUSE_KEYWORD |
| R2 | Increase Bid (CVR > 1.5×campaign avg, CPA < 0.8×campaign avg, conv ≥ 2) | MEDIUM | INCREASE_BID |
| R3 | Decrease Bid (CPA > 1.5×campaign avg, spend ≥ $100, conv > 0) | MEDIUM | DECREASE_BID |
| R4 | Add Keyword: (A) conv ≥ 3 [HIGH, EXACT/PHRASE] + (B) clicks ≥ 10, CTR ≥ 5%, conv=0 [LOW, PHRASE] | HIGH/LOW | ADD_KEYWORD |
| R5 | Add Negative: (A) irrelevant words [HIGH] + (B) clicks ≥ 5, conv=0, CTR < 1% [MEDIUM] + (C) cost ≥ $30, conv=0 [HIGH] | HIGH/MEDIUM | ADD_NEGATIVE |
| R6 | Pause Ad: (A) CTR < 50% best ad, impr ≥ 500 [MEDIUM] + (B) cost ≥ $50, conv=0 [HIGH] | HIGH/MEDIUM | PAUSE_AD |
| R7 | Reallocate Budget (best ROAS > 2×worst ROAS, worst budget > best budget) | HIGH | REALLOCATE_BUDGET |

**Dane już synchronizowane z API:** campaigns, ad groups, keywords, ads, search terms (z metrykami: impressions, clicks, cost, conversions, CTR, CPC, CPA, ROAS, Quality Score, impression share).

**Dane NIEDOSTĘPNE w obecnym sync:** asset performance, placement reports, audience segments, auction insights, conversion tracking config.

> **[AKTUALIZACJA v2.0]** Usunięto z powyższej listy: device/geo breakdowns (tabela `metric_segmented` + `sync_device_metrics()` / `sync_geo_metrics()` już istnieją), change history (`sync_change_events()` istnieje — Phase 6 sync).

---

## 2. Analiza checklisty — co jest automatyzowalne?

Checklista optymalizacyjna zawiera ~60 pozycji w 15 obszarach. Poniżej kategoryzacja każdego elementu pod kątem automatyzacji w aplikacji.

### Kategoria A: Nowe reguły w recommendations engine (automatable)

Elementy, które można zaimplementować jako nowe reguły decyzyjne działające na danych z Google Ads API. Wymagają rozszerzenia sync (nowe dane) i/lub nowej logiki w engine.

### Kategoria B: Alerty i diagnostyka (semi-automatable)

Elementy, które nie generują konkretnej akcji (pause/bid/add), ale mogą generować alerty diagnostyczne lub audytowe wyświetlane użytkownikowi w dashboardzie. Rozszerzenie istniejącego systemu anomalii.

### Kategoria C: Manualne / zewnętrzne (nie automatyzowalne)

Elementy wymagające decyzji strategicznej, zewnętrznych narzędzi lub ręcznej konfiguracji (np. Consent Mode setup, landing page redesign, naming conventions). Te NIE trafiają do engine — mogą być checklistą w UI (static checklist / onboarding wizard).

---

## 3. Nowe reguły — szczegółowe specyfikacje

### v1.1 — Quick Wins (po MVP, Sprint 5–6)

Reguły wykorzystujące dane już dostępne w DB. Nie wymagają rozszerzenia sync — wystarczy dodać logikę reguł.

---

#### R8: Quality Score Alert — Keywords z QS < 5
**Źródło w checkliście:** §5 Quality Score diagnostyka
**Kategoria:** B (alert diagnostyczny)

**Logika:**
```
IF (Keyword.quality_score IS NOT NULL
    AND Keyword.quality_score < 5
    AND Keyword.status == 'ENABLED'
    AND Keyword.impressions > 100)
→ ALERT: "Quality Score {QS} — sprawdź: {subkomponent z najniższą oceną}"
PRIORITY: MEDIUM (QS 3-4), HIGH (QS 1-2)
```

**Dane wymagane:** Wszystkie już zsynchronizowane. Kolumny na modelu `Keyword`:
- `quality_score` (Integer, 1-10)
- `historical_quality_score` (Integer: 1=BELOW_AVERAGE, 2=AVERAGE, 3=ABOVE_AVERAGE)
- `historical_creative_quality` (Integer, ten sam mapping)
- `historical_landing_page_quality` (Integer, ten sam mapping)
- `historical_search_predicted_ctr` (Integer, ten sam mapping)

> **[AKTUALIZACJA v2.0]** ~~Wymaga rozszerzenia GAQL~~ — GAQL już pobiera `metrics.historical_quality_score`, `metrics.historical_creative_quality_score`, `metrics.historical_landing_page_quality_score`, `metrics.historical_search_predicted_ctr`. Zero zmian w sync/DB.

**Zmiana w DB:** Brak — kolumny już istnieją.

**Akcja użytkownika:** Brak automatycznej akcji. Alert z diagnozą, który subkomponent wymaga pracy. Link do Google Ads UI.

**Szacowany effort:** ~~4h~~ **1-2h** (tylko logika reguły + UI alert card)

---

#### R9: Impression Share Lost to Budget — Budget Bottleneck
**Źródło w checkliście:** §8 Impression Share diagnostyka
**Kategoria:** A (rekomendacja z akcją)

**Logika:**
```
IF (Campaign.search_impression_share_lost_budget > 20%
    AND Campaign.conversions > 0
    AND Campaign.roas >= target_roas * 0.8)
→ RECOMMEND: "Zwiększ budżet o 20% — tracisz {X}% wyświetleń z powodu budżetu przy zdrowym ROAS"
PRIORITY: HIGH (lost IS > 40%), MEDIUM (20-40%)

IF (Campaign.search_impression_share_lost_budget > 50%
    AND Campaign.cpa > target_cpa * 1.2)
→ RECOMMEND: "Obniż stawki — kampania wyczerpuje budżet za wcześnie przy za wysokim CPA"
PRIORITY: HIGH
```

**Dane wymagane:** Wszystkie już zsynchronizowane. Model `Campaign` ma 13 kolumn impression share:
- `search_impression_share`, `search_top_impression_share`, `search_abs_top_impression_share`
- `search_budget_lost_is`, `search_budget_lost_top_is`, `search_budget_lost_abs_top_is`
- `search_rank_lost_is`, `search_rank_lost_top_is`, `search_rank_lost_abs_top_is`
- `search_click_share`, `search_exact_match_is`, `abs_top_impression_pct`, `top_impression_pct`

Metoda `sync_campaign_impression_share()` już istnieje w `google_ads.py`.

> **[AKTUALIZACJA v2.0]** ~~Wymaga rozszerzenia GAQL~~ — dane już w DB. Zero zmian w sync/DB.

**Zmiana w DB:** Brak — kolumny już istnieją.

**Akcja:** ADJUST_BUDGET (nowy typ akcji w action_executor — **uwaga: wymaga implementacji w `validate_action()`**) lub DECREASE_BID (istniejący).

**Szacowany effort:** ~~6h~~ **2h** (logika reguły + ewentualnie nowy typ akcji w executor)

---

#### R10: Impression Share Lost to Rank — Quality/Bid Problem
**Źródło w checkliście:** §8 Impression Share diagnostyka
**Kategoria:** B (alert z sugestią)

**Logika:**
```
IF (Campaign.search_impression_share_lost_rank > 30%
    AND Campaign.search_impression_share_lost_budget < 10%)
→ ALERT: "Tracisz {X}% wyświetleń z powodu niskiego Ad Rank. 
  Sprawdź Quality Score keywords i trafność reklam."
PRIORITY: MEDIUM
```

**Dane wymagane:** Te same co R9 (współdzielone) — już dostępne w DB.

**Zmiana w DB:** Brak.

**Akcja:** Brak automatycznej. Alert diagnostyczny z linkiem do QS audit (R8).

**Szacowany effort:** ~~2h~~ **1h** (rule only, dane już w DB)

---

#### R11: Keyword z niskim CTR i wysokimi impressions — Irrelevant
**Źródło w checkliście:** §2 match type strategy, §5 Expected CTR
**Kategoria:** A (rekomendacja z akcją)

**Logika:**
```
IF (Keyword.ctr < 0.5%
    AND Keyword.impressions > 1000
    AND Keyword.conversions == 0
    AND Keyword.match_type IN ('BROAD', 'PHRASE'))
→ RECOMMEND: "Pause lub zmień match type — CTR {X}% przy {Y} impressions sugeruje słabe dopasowanie"
PRIORITY: MEDIUM
```

**Uwaga:** Częściowo pokrywa się z R1 (pause bleeding keywords), ale R1 sprawdza spend/clicks/conv — ten sprawdza CTR/impressions/match type. Komplementarne, nie duplikujące.

**Dane wymagane:** `match_type` — już zsynchronizowane. Kolumna `match_type = Column(String(20))` istnieje na modelu `Keyword`. GAQL pobiera `ad_group_criterion.keyword.match_type`.

> **[AKTUALIZACJA v2.0]** ~~Wymaga dodania match_type do sync~~ — już w DB. Zero zmian w sync/DB.

**Zmiana w DB:** Brak — kolumna już istnieje.

**Szacowany effort:** ~~3h~~ **1h** (tylko logika reguły)

---

#### R12: Wasted Spend Alert — % budżetu bez konwersji
**Źródło w checkliście:** §8 Budget reallocation
**Kategoria:** B (alert diagnostyczny)

**Logika:**
```
wasted_spend = SUM(keyword.cost WHERE keyword.conversions == 0) / SUM(keyword.cost) * 100

IF (wasted_spend_pct > 25%)
→ ALERT: "{X}% budżetu ({$Y}) idzie na słowa kluczowe bez konwersji"
PRIORITY: HIGH (>35%), MEDIUM (25-35%)
```

**Dane wymagane:** Już dostępne (keywords: cost_micros, conversions).

> **[AKTUALIZACJA v2.0]** Metoda `get_wasted_spend()` już istnieje w `analytics_service.py` — agreguje zero-conversion waste z keywords, search terms i ads. Można reużywać jako źródło danych dla reguły.

**Zmiana w DB:** Brak.

**Akcja:** Brak bezpośredniej. Link do listy keywords z conv=0, posortowanych by spend desc. Użytkownik decyduje, co pausować.

**Szacowany effort:** 1-2h (pure rule + dashboard widget, reużywając istniejący `get_wasted_spend()`)

---

#### R13: Search Term Cannibalization — PMax vs. Search overlap
**Źródło w checkliście:** §2 cross-campaign keyword conflicts, §11 PMax cannibalization
**Kategoria:** B (alert diagnostyczny)

**Logika:**
```
FOR EACH search_term appearing in BOTH Search campaign AND PMax campaign:
  IF (pmax_cost > search_cost * 0.5
      AND search_keyword_match_type != 'EXACT')
→ ALERT: "Search term '{X}' pojawia się w Search i PMax. 
  PMax wydaje ${Y} na ten term. Rozważ exact match w Search lub negative w PMax."
PRIORITY: HIGH (jeśli pmax_cost > $50), MEDIUM (otherwise)
```

**Dane wymagane:** Już dostępne:
- `Campaign.campaign_type` (kolumna `String(50)`) przechowuje `advertising_channel_type.name` (SEARCH, PERFORMANCE_MAX, DISPLAY, VIDEO, etc.)
- `SearchTerm.source` (kolumna: "SEARCH" / "PMAX") identyfikuje źródło search termu

> **[AKTUALIZACJA v2.0]** ~~Wymaga dodania channel_type~~ — `campaign_type` już w DB. Zero zmian w sync/DB.

**Zmiana w DB:** Brak — kolumna już istnieje.

**Szacowany effort:** ~~5h~~ **3h** (cross-campaign overlap analysis + UI)

---

### v1.2 — Rozszerzenia (Sprint 7–8)

> **[AKTUALIZACJA v2.0]** Większość reguł v1.2 (R15-R18) **nie wymaga nowych danych** — sync i analytics już istnieją. Jedynie R14 (Asset Performance) wymaga nowej tabeli + sync.

---

#### R14: Asset Performance — Low-performing assets w RSA
**Źródło w checkliście:** §3 Asset performance ratings
**Kategoria:** A (rekomendacja)

**Logika:**
```
IF (Asset.performance_label == 'LOW'
    AND Asset.type IN ('HEADLINE', 'DESCRIPTION')
    AND Ad.impressions > 1000)
→ RECOMMEND: "Asset '{X}' w grupie '{Y}' ma rating LOW. Zastąp nowym wariantem."
PRIORITY: MEDIUM
```

**Nowe dane do sync:**
```sql
SELECT
  ad_group_ad.ad.responsive_search_ad.headlines,
  ad_group_ad.ad.responsive_search_ad.descriptions,
  ad_group_ad_asset_view.performance_label,
  ad_group_ad_asset_view.field_type
FROM ad_group_ad_asset_view
WHERE ad_group_ad.status = 'ENABLED'
```

**Nowa tabela DB:** `ad_assets`
```
id, ad_id, asset_type (HEADLINE/DESCRIPTION), text, 
performance_label (BEST/GOOD/LOW/LEARNING/PENDING/UNSPECIFIED),
pinned_field (HEADLINE_1/HEADLINE_2/HEADLINE_3/DESCRIPTION_1/DESCRIPTION_2/UNSPECIFIED),
google_asset_id
```

**Sync service:** Nowa metoda `_sync_ad_assets()` w Phase 3 sync.

> **[AKTUALIZACJA v2.0]** UWAGA: `sync_ads()` nie istnieje w obecnym kodzie — model `Ad` jest zdefiniowany, ale nigdy nie populowany z API. Implementacja R14 wymaga najpierw zbudowania sync ads, co zwiększa effort.

**Akcja:** Brak automatycznej (Google Ads API nie pozwala modyfikować pojedynczych assetów RSA — trzeba zastąpić całą reklamę). Rekomendacja manualna.

**Szacowany effort:** ~~10h~~ **12h+** (nowa tabela + sync ads + sync assets + rule + UI)

---

#### R15: Device Performance Breakdown — Alert anomalii per device
**Źródło w checkliście:** §4 Bid adjustments (device)
**Kategoria:** B (alert)

**Logika:**
```
FOR EACH campaign, compare CPA per device:
  IF (mobile_cpa > desktop_cpa * 2.0 AND mobile_spend > $100)
→ ALERT: "Mobile CPA (${X}) jest 2× wyższy niż desktop (${Y}) w kampanii '{Z}'. 
  Rozważ bid adjustment -100% na mobile lub dedykowane LP."
PRIORITY: MEDIUM
```

> **[AKTUALIZACJA v2.0]** ~~Nowe dane do sync / nowa tabela~~ — dane już dostępne:
> - Tabela `metric_segmented` z kolumną `device` (MOBILE/DESKTOP/TABLET/OTHER) już istnieje
> - Metoda `sync_device_metrics()` w `google_ads.py` już synchronizuje dane
> - Metoda `get_device_breakdown()` w `analytics_service.py` już agreguje dane per device
> - Endpoint `GET /analytics/device-breakdown` już istnieje
>
> Zero nowych tabel, zero nowego sync — wymaga tylko logiki reguły alertu.

**Szacowany effort:** ~~8h~~ **2h** (tylko logika reguły alertu, reużywając istniejący `get_device_breakdown()`)

---

#### R16: Geo Performance Breakdown — Alert anomalii per lokalizacja
**Źródło w checkliście:** §4 Location adjustments
**Kategoria:** B (alert)

**Logika:**
```
FOR EACH campaign, compare CPA per geo:
  IF (geo_cpa > campaign_avg_cpa * 2.0 AND geo_spend > $50)
→ ALERT: "Lokalizacja '{geo}' ma CPA ${X} (2× średnia kampanii). 
  Rozważ geo bid adjustment."
PRIORITY: LOW
```

> **[AKTUALIZACJA v2.0]** ~~Nowe dane do sync / nowa tabela~~ — dane już dostępne:
> - Tabela `metric_segmented` z kolumną `geo_city` (rozwiązane nazwy miast) już istnieje
> - Metoda `sync_geo_metrics()` w `google_ads.py` już synchronizuje dane
> - Metoda `get_geo_breakdown()` w `analytics_service.py` już agreguje dane per lokalizacja
> - Endpoint `GET /analytics/geo-breakdown` już istnieje
>
> Zero nowych tabel, zero nowego sync — wymaga tylko logiki reguły alertu.

**Szacowany effort:** ~~8h~~ **2h** (tylko logika reguły alertu, reużywając istniejący `get_geo_breakdown()`)

---

#### R17: Budget Pacing Alert — Overspend / Underspend
**Źródło w checkliście:** §8 Budget pacing
**Kategoria:** B (alert)

**Logika:**
```
day_of_month = current_day / total_days_in_month
expected_spend = monthly_budget * day_of_month
actual_spend = SUM(campaign.cost_micros) for current month

IF (actual_spend > expected_spend * 1.3)
→ ALERT: "Kampania '{X}' wydaje za szybko — {Y}% budżetu przy {Z}% miesiąca"
PRIORITY: HIGH

IF (actual_spend < expected_spend * 0.5 AND day_of_month > 0.3)
→ ALERT: "Kampania '{X}' niedowydaje — {Y}% budżetu przy {Z}% miesiąca"
PRIORITY: MEDIUM
```

**Dane wymagane:** Już dostępne:
- `Campaign.budget_micros` (kolumna `BigInteger`) — budżet dzienny kampanii, synchronizowany w `sync_campaigns()`
- Tabela `metric_daily` — dzienne koszty per kampania, synchronizowana w `sync_daily_metrics()`

> **[AKTUALIZACJA v2.0]** ~~Dodaj daily_budget_micros / wymaga metric_daily~~ — obie dane już w DB.
> Endpoint `GET /analytics/budget-pacing` już istnieje. Zero zmian w sync/DB.

**Zmiana w DB:** Brak.

**Szacowany effort:** ~~6h~~ **2h** (logika reguły alertu, reużywając istniejące dane)

---

#### R18: N-gram Negative Detection — Wzorce w search terms
**Źródło w checkliście:** §2 N-gram analysis
**Kategoria:** A (rekomendacja z akcją)

**Logika:**
```python
# Grupuj search terms w n-gramy (1-3 wyrazy)
ngrams = extract_ngrams(all_search_terms, n=[1,2,3])

FOR EACH ngram:
  total_cost = SUM(cost WHERE search_term CONTAINS ngram)
  total_conv = SUM(conversions WHERE search_term CONTAINS ngram)
  
  IF (total_cost > $100 AND total_conv == 0 AND count_terms > 3)
→ RECOMMEND: "N-gram '{ngram}' pojawia się w {count} search terms, 
  łączny koszt ${total_cost}, 0 konwersji. Dodaj jako broad match negative."
PRIORITY: HIGH
```

**Dane wymagane:** Już dostępne (search_terms z cost i conversions).

**Zmiana w DB:** Brak (obliczenia in-memory).

> **[AKTUALIZACJA v2.0]** ~~Nowy service: services/ngram_analyzer.py~~ — metoda `get_ngram_analysis()` już istnieje w `analytics_service.py`. Endpoint `GET /analytics/ngram-analysis` już działa. Wystarczy dodać logikę reguły decyzyjnej wykorzystującą istniejącą analizę.

**Akcja:** ADD_NEGATIVE (broad match) — istniejący typ akcji.

**Szacowany effort:** ~~8h~~ **3h** (logika reguły + integracja z istniejącym `get_ngram_analysis()`)

---

### v2.0 — Zaawansowane rozszerzenia (kwartalny roadmap)

Funkcje wymagające znaczących zmian w architekturze lub nowych integracji.

---

#### R19: Auction Insights Monitoring — Competitor Tracking
**Źródło w checkliście:** §14 Auction Insights
**Kategoria:** B (alert)

**Logika:**
```
IF (competitor.impression_share increased > 15% vs previous period
    AND my.impression_share decreased > 10%)
→ ALERT: "Konkurent '{X}' zwiększył IS o {Y}pp. Twój IS spadł o {Z}pp."
PRIORITY: MEDIUM
```

**Nowe dane:**
```sql
SELECT
  auction_insights.display_domain,
  auction_insights.impression_share,
  auction_insights.outranking_share,
  auction_insights.position_above_rate
FROM auction_insight
WHERE segments.date DURING LAST_30_DAYS
```

**Nowa tabela DB:** `auction_insights` (domain, impression_share, overlap_rate, outranking_share, position_above_rate, campaign_id, date_range).

**Uwaga:** Auction Insights API ma wyższe rate limits. Sync raz na tydzień, nie codziennie.

**Szacowany effort:** 12h

---

#### R20: Conversion Tracking Health Check
**Źródło w checkliście:** §7 Śledzenie konwersji
**Kategoria:** B (alert diagnostyczny)

**Logika:**
```
IF (campaign.conversions == 0 
    AND campaign.clicks > 50
    AND campaign.status == 'ENABLED'
    AND campaign.active_days > 7)
→ ALERT: "Kampania '{X}' ma 0 konwersji przy {Y} kliknięciach. 
  Sprawdź konfigurację conversion tracking."
PRIORITY: HIGH

IF (conversion_action.status == 'NOT_RECENTLY_ACTIVE')
→ ALERT: "Conversion action '{X}' nie rejestruje danych od {Y} dni."
PRIORITY: HIGH
```

**Nowe dane:**
```sql
SELECT
  conversion_action.id,
  conversion_action.name,
  conversion_action.status,
  conversion_action.type,
  conversion_action.tag_snippets
FROM conversion_action
```

**Nowa tabela DB:** `conversion_actions` (google_id, name, status, type, category, counting_type, client_id).

**Szacowany effort:** 8h

---

#### R21: Landing Page Performance Audit
**Źródło w checkliście:** §6 Landing pages
**Kategoria:** B (alert)

**Logika:**
```
FOR EACH unique landing_page_url in campaign:
  IF (bounce_rate > 70% AND clicks > 50)
→ ALERT: "Landing page '{URL}' ma bounce rate {X}%. Sprawdź message match i szybkość."
PRIORITY: MEDIUM
```

**Uwaga:** Bounce rate nie jest dostępny w Google Ads API. Wymaga integracji z GA4 Data API (odrębne OAuth scope + credentials). Alternatywa: użyj `landing_page_view` z Google Ads API, który daje metryki per URL ale BEZ bounce rate.

**Dane z Google Ads API (bez GA4):**
```sql
SELECT
  landing_page_view.unexpanded_final_url,
  metrics.clicks,
  metrics.conversions,
  metrics.cost_micros
FROM landing_page_view
```

**Uproszczona logika (bez bounce rate):**
```
IF (landing_page.clicks > 50 AND landing_page.conversions == 0)
→ ALERT: "Landing page '{URL}' — {X} kliknięć, 0 konwersji. 
  Sprawdź trafność strony."
PRIORITY: MEDIUM
```

> **[AKTUALIZACJA v2.0]** Metoda `get_landing_page_analysis()` już istnieje w `analytics_service.py` — agreguje metryki per `final_url` z modelu Keyword. Jeśli wystarczą te dane (bez `landing_page_view` z API), effort jest mniejszy.

**Szacowany effort:** ~~10h~~ **6h** (z istniejącą `get_landing_page_analysis()`) / z GA4: 20h+

---

## 4. Elementy NIE-automatyzowalne — Static Checklist w UI

Poniższe elementy checklisty wymagają decyzji strategicznej lub manualnej konfiguracji. Proponowane wdrożenie: **statyczna checklista w UI** (ekran „Audit Checklist") z możliwością oznaczania pozycji jako „Done" per klient, per kwartał.

### Struktura konta
- Weryfikacja naming conventions
- Separacja brand vs non-brand (setup-level)
- Konsolidacja kampanii pod Smart Bidding (strategia)
- Label management

### Śledzenie konwersji (konfiguracja)
- Enhanced Conversions setup
- Consent Mode v2 implementacja
- Server-side tracking wdrożenie
- Micro vs macro konwersje konfiguracja
- Offline Conversion Import pipeline

### Strony docelowe
- Message match audit
- Core Web Vitals optymalizacja
- Mobile UX audit
- CRO testy A/B

### Reklamy
- RSA pin strategy
- A/B testing cykl
- Asset portfolio completeness (sitelinks, callouts, snippets, images)

### PMax
- Audience signals konfiguracja
- Search themes strategy (użyć vs nie używać)
- Brand exclusions setup
- URL expansion settings
- Video asset quality

### Brand Safety
- Content suitability settings
- Placement exclusion lists
- IP exclusions

### Odbiorcy
- Remarketing segmentacja setup
- Customer Match upload
- Combined segments konfiguracja

### Nowe funkcje
- AI Max for Search evaluation
- Demand Gen activation
- Asset Studio wykorzystanie

**Szacowany effort na static checklist UI:** 8h (nowa strona w React, storage w SQLite: `audit_checklist_items` z client_id, item_key, completed_at, next_due_at).

---

## 5. Podsumowanie — Roadmap wdrożenia

### Priorytet 1: MVP (obecny scope — nie zmieniamy)
**Reguły R1–R7 + 7 core features (sync, apply, recommendations, search terms, dashboard, anomalies, action history)**
Status: Phase 1–4 per PROGRESS.md.

### Priorytet 2: v1.1 — Quick Wins (Sprint 5–6, ~~31h~~ **~17-19h**)
| Reguła | Effort | Wymaga nowych danych? | Impact |
|--------|--------|-----------------------|--------|
| R8: QS Alert | ~~4h~~ **1-2h** | ~~Tak~~ **Nie** (historical_* już w DB) | HIGH |
| R9: IS Lost to Budget | ~~6h~~ **2h** | ~~Tak~~ **Nie** (13 kolumn IS już w DB) | HIGH |
| R10: IS Lost to Rank | ~~2h~~ **1h** | Nie (dane już w DB) | MEDIUM |
| R11: Low CTR + high impr | ~~3h~~ **1h** | ~~Tak~~ **Nie** (match_type już w DB) | MEDIUM |
| R12: Wasted Spend % | 1-2h | Nie (+ `get_wasted_spend()` istnieje) | HIGH |
| R13: PMax vs Search overlap | ~~5h~~ **3h** | ~~Tak~~ **Nie** (campaign_type już w DB) | HIGH |
| Static Checklist UI | 8h | Nie | MEDIUM |
| **TOTAL** | **~17-19h** | | |

> **[AKTUALIZACJA v2.0]** ~~Wymagane zmiany w sync_service.py dla v1.1~~ — **Brak zmian w sync wymaganych.** Wszystkie dane potrzebne dla reguł R8–R13 są już zsynchronizowane (QS subkomponenty, impression share, match_type, campaign_type). Wystarczy dodać logikę reguł w `recommendations.py`.

### Priorytet 3: v1.2 — Extended Analytics (Sprint 7–8, ~~40h~~ **~21h**)
| Reguła | Effort | Wymaga nowych danych? | Impact |
|--------|--------|-----------------------|--------|
| R14: Asset Performance | ~~10h~~ **12h+** | Tak (nowa tabela + brak sync_ads) | MEDIUM |
| R15: Device Breakdown | ~~8h~~ **2h** | ~~Tak~~ **Nie** (metric_segmented + sync istnieją) | LOW |
| R16: Geo Breakdown | ~~8h~~ **2h** | ~~Tak~~ **Nie** (metric_segmented + sync istnieją) | LOW |
| R17: Budget Pacing | ~~6h~~ **2h** | ~~Tak~~ **Nie** (budget_micros + metric_daily istnieją) | MEDIUM |
| R18: N-gram Analysis | ~~8h~~ **3h** | Nie (+ `get_ngram_analysis()` istnieje) | HIGH |
| **TOTAL** | **~21h** | | |

### Priorytet 4: v2.0 — Advanced (kwartał po v1.2, ~~30h~~ **~26h**)
| Reguła | Effort | Wymaga nowych danych? | Impact |
|--------|--------|-----------------------|--------|
| R19: Auction Insights | 12h | Tak (nowa tabela) | MEDIUM |
| R20: Conv Tracking Health | 8h | Tak (nowa tabela) | HIGH |
| R21: Landing Page Audit | ~~10h~~ **6h** | Częściowo (+ `get_landing_page_analysis()` istnieje) | MEDIUM |
| **TOTAL** | **~26h** | | |

---

## 6. Zmiana w architekturze — rekomendacje

### 6.1 Thresholds jako konfiguracja per klient
Obecny engine używa `DEFAULT_THRESHOLDS` (hardcoded dict). Dla v1.1+ dodaj:
- Tabela `client_thresholds` (client_id, threshold_key, value) w DB
- Fallback: jeśli brak per-client → default
- UI: Settings per klient z suwakami/inputami

### 6.2 Recommendation types enum
Rozszerz `RecommendationType` enum o nowe typy:
```python
# v1.1
QS_ALERT = "QS_ALERT"
IS_BUDGET_ALERT = "IS_BUDGET_ALERT"
IS_RANK_ALERT = "IS_RANK_ALERT"
WASTED_SPEND_ALERT = "WASTED_SPEND_ALERT"
PMAX_CANNIBALIZATION = "PMAX_CANNIBALIZATION"

# v1.2
ASSET_PERFORMANCE = "ASSET_PERFORMANCE"
DEVICE_ANOMALY = "DEVICE_ANOMALY"
GEO_ANOMALY = "GEO_ANOMALY"
BUDGET_PACING = "BUDGET_PACING"
NGRAM_NEGATIVE = "NGRAM_NEGATIVE"

# v2.0
AUCTION_INSIGHT_SHIFT = "AUCTION_INSIGHT_SHIFT"
CONV_TRACKING_ISSUE = "CONV_TRACKING_ISSUE"
LANDING_PAGE_ISSUE = "LANDING_PAGE_ISSUE"
```

### 6.3 Rozróżnienie: Recommendation vs Alert
Obecny model traktuje wszystko jako „recommendation". Dla v1.1+ warto rozróżnić:
- **Recommendation** — ma konkretną akcję do wykonania (Apply button)
- **Alert** — informacja diagnostyczna bez bezpośredniej akcji (Review button → link do Google Ads UI lub wewnętrzny drill-down)

Dodaj kolumnę `category` (VARCHAR: 'RECOMMENDATION' | 'ALERT') do tabeli `recommendations`. Frontend filtruje po kategorii (osobne taby).

### 6.4 Sync scheduling dla v1.2+

> **[AKTUALIZACJA v2.0]** Device/geo sync już istnieją (`sync_device_metrics()`, `sync_geo_metrics()`) i działają jako część standardowego sync. Poniższe dotyczy przyszłych rozszerzeń (auction insights, assets).

Duże zapytania API — nie syncuj przy każdym refresh:
- Core data (campaigns, keywords, search terms): co kliknięcie Refresh
- Extended data (device, geo, assets): raz dziennie (background)
- Auction insights: raz na tydzień

Wymaga implementacji `sync_level` parametru: `QUICK` (core only) vs `FULL` (core + extended).

### 6.5 Znane braki w action_executor (dodane w v2.0)

Następujące typy akcji są zdefiniowane w `RecommendationType` enum, ale **NIE mają walidacji w `action_executor.py`**:
- `INCREASE_BID` — zdefiniowany w recommendations, brak w `validate_action()`
- `DECREASE_BID` — zdefiniowany w recommendations, brak w `validate_action()`
- `REALLOCATE_BUDGET` — zdefiniowany w recommendations, brak w `validate_action()`

**Działające w executor:** `UPDATE_BID`, `SET_BID`, `INCREASE_BUDGET`, `SET_BUDGET`, `PAUSE_KEYWORD`, `ADD_NEGATIVE`, `ENABLE_KEYWORD`, `SET_KEYWORD_BID`, `ADD_KEYWORD`.

**Implikacje:** Nowe reguły R9 (ADJUST_BUDGET) wymagają implementacji walidacji w executor. Przed wdrożeniem v1.1 należy uzupełnić brakujące typy akcji.

Dodatkowo: `sync_ads()` nie istnieje — model `Ad` jest zdefiniowany, ale nigdy nie populowany z API. Blokuje R14 (Asset Performance) i sprawia, że R6 (Pause Ad) działa tylko na danych demo.

---

## 7. Otwarte pytania (do decyzji PM)

1. **Priorytety v1.1:** Czy kolejność reguł R8–R13 jest OK, czy priorytetyzujemy inaczej?
2. **Static Checklist:** Czy wystarczy prosty checkbox UI, czy chcemy reminder system (email/notification gdy checklist item overdue)?
3. **Thresholds per klient:** Czy wdrażamy w v1.1 (dodatkowe 4h na UI), czy odkładamy na v1.2?
4. **N-gram analysis (R18):** Czy warto przesunąć do v1.1 ze względu na wysoki impact? Nie wymaga nowych danych z API.
5. **GA4 integracja (R21):** Czy planujemy kiedykolwiek? Wymaga dodatkowego OAuth scope i osobnej konfiguracji. Alternatywa: `landing_page_view` z Google Ads API (mniej danych, ale zero dodatkowej konfiguracji).

---

## Appendix A: Pełne mapowanie checklista → engine

| # | Element checklisty | Reguła | Wersja | Kategoria |
|---|-------------------|--------|--------|-----------|
| 1 | Konsolidacja kampanii pod Smart Bidding | — | — | C (manualna) |
| 2 | Separacja brand vs non-brand | — | — | C (manualna) |
| 3 | Naming conventions | — | — | C (manualna) |
| 4 | STAGs zamiast SKAGs | — | — | C (manualna) |
| 5 | Power Pack audit | — | — | C (manualna) |
| 6 | Search terms review | R4, R5 | MVP | A |
| 7 | Match type strategy | R11 | v1.1 | A |
| 8 | Negative keyword lists | R5, R18 | MVP/v1.2 | A |
| 9 | N-gram analysis | R18 | v1.2 | A |
| 10 | PMax vs Search overlap | R13 | v1.1 | B |
| 11 | RSA optimization (1 RSA/ag) | R14 | v1.2 | A |
| 12 | Asset performance ratings | R14 | v1.2 | A |
| 13 | Ad Strength monitoring | — | — | C (nie wdrażamy — nie koreluje z performance) |
| 14 | A/B testing kreacji | — | — | C (manualna) |
| 15 | Sitelinks/callouts/snippets | — | — | C (manualna) |
| 16 | Smart Bidding wybór/walidacja | — | — | C (manualna) |
| 17 | Learning period monitoring | — | v2.0+ | B (potential alert) |
| 18 | Value-Based Bidding setup | — | — | C (manualna) |
| 19 | Conversion Value Rules | — | — | C (manualna) |
| 20 | Seasonality Adjustments | — | — | C (manualna) |
| 21 | Bid adjustments audit | — | — | C (manualna) |
| 22 | Smart Bidding Exploration | — | — | C (manualna) |
| 23 | QS diagnostyka per komponent | R8 | v1.1 | B |
| 24 | QS w erze Smart Bidding | R8 | v1.1 | B |
| 25 | Message match audit | — | — | C (manualna) |
| 26 | Core Web Vitals | — | — | C (zewnętrzne) |
| 27 | Mobile UX / CRO | — | — | C (zewnętrzne) |
| 28 | Google Ads tag vs GA4 | — | — | C (manualna) |
| 29 | Enhanced Conversions | — | — | C (manualna) |
| 30 | Consent Mode v2 | — | — | C (manualna) |
| 31 | Server-side tracking | — | — | C (zewnętrzne) |
| 32 | Micro vs macro konwersje | — | — | C (manualna) |
| 33 | Offline Conversion Import | — | — | C (manualna) |
| 34 | Impression Share analysis | R9, R10 | v1.1 | A/B |
| 35 | Budget reallocation | R7 | MVP | A |
| 36 | Budget pacing | R17 | v1.2 | B |
| 37 | Wasted spend % | R12 | v1.1 | B |
| 38 | Placement exclusions | — | — | C (manualna) |
| 39 | Brand safety settings | — | — | C (manualna) |
| 40 | IP exclusions | — | — | C (manualna) |
| 41 | Remarketing segmentacja | — | — | C (manualna) |
| 42 | Customer Match | — | — | C (manualna) |
| 43 | Similar audiences zamienniki | — | — | C (manualna) |
| 44 | PMax asset groups | — | — | C (manualna) |
| 45 | PMax search themes | — | — | C (manualna) |
| 46 | PMax Insights tab | R13 | v1.1 | B |
| 47 | PMax brand exclusions | — | — | C (manualna) |
| 48 | YouTube/Video formaty | — | — | C (manualna) |
| 49 | Frequency capping | — | — | C (manualna) |
| 50 | Display placements | — | — | C (manualna) |
| 51 | Display targeting | — | — | C (manualna) |
| 52 | Daily/weekly/monthly cykl | Dashboard | MVP | N/A |
| 53 | Auction Insights | R19 | v2.0 | B |
| 54 | Google Ads Scripts | — | — | C (zewnętrzne) |
| 55 | Looker Studio dashboards | — | — | C (zewnętrzne) |
| 56 | AI Max for Search | — | — | C (manualna) |
| 57 | Demand Gen | — | — | C (manualna) |
| 58 | Privacy Sandbox | — | — | C (brak akcji) |
| 59 | Asset Studio / Gemini | — | — | C (zewnętrzne) |
| 60 | Conv Tracking health | R20 | v2.0 | B |
| 61 | Landing Page audit | R21 | v2.0 | B |
| 62 | Device performance | R15 | v1.2 | B |
| 63 | Geo performance | R16 | v1.2 | B |

**Podsumowanie:** 14 nowych reguł (R8–R21) + static checklist UI. Razem z MVP (R1–R7) = 21 reguł pokrywających ~35% checklisty automatycznie + ~15% jako alerty diagnostyczne. Pozostałe ~50% to decyzje strategiczne wymagające ludzkiego osądu — pokryte przez static checklist w UI.

> **[AKTUALIZACJA v2.0]** Większość reguł v1.1 i v1.2 (R8–R13, R15–R18) **nie wymaga nowych danych z API** — sync i modele DB zostały rozbudowane od czasu powstania wersji 1.0 tego dokumentu. Łączny skorygowany effort: v1.1 ~17-19h (było ~31h), v1.2 ~21h (było ~40h), v2.0 ~26h (było ~30h).
