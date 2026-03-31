# Google Ads Coverage — Gap Analysis

> Wygenerowane 2026-03-27, zaktualizowane 2026-03-28.
> Analiza pokrycia aplikacji vs pełne możliwości Google Ads.

## Legenda

- **TAK** — w pełni zaimplementowane (sync + model + UI + akcje)
- **CZĘŚCIOWO** — częściowo zaimplementowane (brakuje elementów)
- **NIE** — brak implementacji

---

## 1. POKRYCIE TYPÓW KAMPANII

| Typ kampanii | Status | Co obsługuje | Czego brakuje |
|---|---|---|---|
| **Search** | **TAK** | Kampanie, słowa kluczowe (QS, IS, match type, bid), search terms (segmentacja), reklamy RSA, negatywne KW, metryki dzienne, device/geo/demo segmentacja, rekomendacje (30 reguł), akcje (pause/bid/negative), historia zmian | Auction insights, ad scheduling (config, nie metryki), bid modifiers per device/location |
| **PMax** | **CZĘŚCIOWO** | Kampanie, asset groups (struktura + daily metrics), assets (headline/desc/image/video + performance label), sygnały (search themes + audiences), channel breakdown, search terms (via campaign_search_term_view), cannibalization detection | Listing groups, feed/product integration, audience signal details, per-asset daily metrics, URL expansion settings |
| **Shopping** | **NIE** | Kampanie widoczne w liście (basic metrics) | Product groups, product feed, custom labels, Merchant Center integration, product-level bidding, Shopping-specific reporting |
| **Display** | **NIE** | Kampanie widoczne w liście (basic metrics) | Placements (managed + automatic), placement exclusions, topic targeting, responsive display ads, image ads, audience targeting config, remarketing lists |
| **Video** | **NIE** | Kampanie widoczne w liście (basic metrics) | Video ads (TrueView, bumper, non-skippable), placement targeting, YouTube metrics (views, view rate, earned actions), video-specific bidding (CPV) |
| **Demand Gen** | **NIE** | Brak | Cały typ kampanii (discover + Gmail + YouTube Shorts), product feeds, audience signals, creative assets |
| **App** | **NIE** | Brak | App install/engagement campaigns, app-specific assets, deep linking |
| **Local** | **NIE** | Brak | Local Services Ads, service area, lead types, booking |
| **Smart** | **NIE** | Widoczne w liście | Smart campaign specifics (auto-generated ads, auto-targeting) |

---

## 2. POKRYCIE OBSZARÓW ZARZĄDZANIA

### 2A. Targeting

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **Keywords** | **TAK** | EXACT/PHRASE/BROAD, QS (1-10 + subcomponents), IS, serving status, bid management, daily metrics, extended conversions | — |
| **Negative Keywords** | **TAK** | Campaign/ad group level, shared lists, bulk operations, bidirectional sync | — |
| **Audiences** | **CZĘŚCIOWO** | CampaignAudienceMetric (read-only metryki), AssetGroupSignal (PMax audience references) | Brak master Audience model, brak audience creation/edit, brak remarketing list management, brak custom/in-market/affinity audience details |
| **Demographics** | **CZĘŚCIOWO** | Age range + gender w MetricSegmented (read-only metryki) | Parental status, household income, education level; brak bid adjustments per demo |
| **Locations** | **CZĘŚCIOWO** | Geo city breakdown w MetricSegmented (read-only metryki) | Brak location targeting config, brak location exclusions, brak radius targeting, brak location bid adjustments |
| **Devices** | **CZĘŚCIOWO** | Device breakdown w MetricSegmented (read-only metryki) | Brak device bid adjustments, brak device-specific campaign settings |
| **Scheduling** | **CZĘŚCIOWO** | Hour-of-day metryki w MetricSegmented | Brak ad schedule config (dzień/godzina bid adjustments), brak schedule creation/edit |
| **Placements** | **NIE** | Brak | Managed placements, automatic placements, placement exclusions, topic targeting (dla Display/Video) |

### 2B. Reklamy

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **RSA (Responsive Search Ads)** | **CZĘŚCIOWO** | Model Ad z headlines/descriptions JSON, ad strength, approval status, metryki, RSA analysis | Brak sync reklam z API (tylko write: pause), brak ad preview, brak A/B test tracking |
| **DSA (Dynamic Search Ads)** | **NIE** | Brak | Dynamic ad targets (auto/webpage), feed-based headlines, DSA-specific reporting |
| **Shopping Ads** | **NIE** | Brak | Product listing ads, showcase ads, product group structure |
| **Video Ads** | **NIE** | Brak | In-stream, bumper, discovery, outstream ads |
| **Image/Display Ads** | **NIE** | Brak | Responsive display ads, uploaded image ads, HTML5 ads |
| **App Ads** | **NIE** | Brak | Universal app campaigns ad formats |

### 2C. Assets / Extensions

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **Sitelinks** | **CZĘŚCIOWO** | CampaignAsset type=SITELINK (read-only, basic metrics) | Brak detail model (URL, description lines), brak create/edit/delete |
| **Callouts** | **CZĘŚCIOWO** | CampaignAsset type=CALLOUT (read-only) | Brak detail model, brak CRUD |
| **Structured Snippets** | **CZĘŚCIOWO** | CampaignAsset type=STRUCTURED_SNIPPET (read-only) | Brak detail model (header type, values), brak CRUD |
| **Call** | **CZĘŚCIOWO** | CampaignAsset type=CALL (read-only) | Brak phone number tracking, call forwarding, call metrics |
| **Location** | **CZĘŚCIOWO** | CampaignAsset type=LOCATION (read-only) | Brak geo coordinates, business address details |
| **Price** | **CZĘŚCIOWO** | CampaignAsset type=PRICE (read-only) | Brak price list structure (qualifier, currency, price pairs) |
| **Promotion** | **CZĘŚCIOWO** | CampaignAsset type=PROMOTION (read-only) | Brak promotion details (discount type, dates, occasion) |
| **Image** | **CZĘŚCIOWO** | CampaignAsset type=IMAGE (read-only) | Brak image dimensions, source URL |
| **Lead Form** | **CZĘŚCIOWO** | CampaignAsset type=LEAD_FORM (read-only) | Brak form field definitions, submission data |
| **PMax Assets** | **TAK** | AssetGroupAsset (headline, desc, image, video) z performance labels | — |

### 2D. Bidding

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **Manual CPC** | **TAK** | Keyword-level bid management (read + write), ad group max CPC | — |
| **Enhanced CPC (eCPC)** | **CZĘŚCIOWO** | Campaign.bidding_strategy=ENHANCED_CPC widoczne | Brak modyfikacji, deprecation detection (rule R24 istnieje) |
| **Target CPA** | **CZĘŚCIOWO** | Campaign.target_cpa_micros (read), learning status tracking | Brak modyfikacji target CPA, brak CPA simulation |
| **Target ROAS** | **CZĘŚCIOWO** | Campaign.target_roas (read), learning status tracking | Brak modyfikacji target ROAS, brak ROAS simulation |
| **Maximize Conversions** | **CZĘŚCIOWO** | Widoczne w Campaign.bidding_strategy enum | Brak szczegółowych ustawień, brak modyfikacji |
| **Maximize Clicks** | **CZĘŚCIOWO** | Widoczne w enum | Brak max CPC limit setting, brak modyfikacji |
| **Target Impression Share** | **NIE** | Brak | Brak w enum, brak ustawień (location, target %, max CPC) |
| **Portfolio Strategies** | **CZĘŚCIOWO** | Campaign.portfolio_bid_strategy_id (reference) | Brak BiddingStrategy master model, brak strategy details/config |
| **Shared Budgets** | **NIE** | Brak | Brak SharedBudget model, brak budget sharing relationships |
| **Bid Modifiers** | **CZĘŚCIOWO** | CampaignAudienceMetric.bid_modifier (audience only) | Brak device/location/schedule bid modifiers |

### 2E. Konwersje

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **Conversion Actions** | **TAK** | Pełny model: name, category, type, status, primary_for_goal, counting_type, attribution_model, lookback windows, value settings | — |
| **Attribution Models** | **CZĘŚCIOWO** | attribution_model field (LAST_CLICK, DATA_DRIVEN etc.) | Brak attribution path analysis, brak model comparison |
| **Conversion Windows** | **TAK** | click_through_lookback_window_days, view_through_lookback_window_days | — |
| **Enhanced Conversions** | **NIE** | Brak | Enhanced conversions for web/leads setup |
| **Offline Import** | **NIE** | Brak | Offline conversion upload, GCLID tracking |
| **Value Rules** | **NIE** | Brak | Conversion value rules (adjustments by audience, device, location) |
| **Cross-device** | **CZĘŚCIOWO** | cross_device_conversions field na kilku modelach | Brak dedykowanego cross-device reporting |

### 2F. Raportowanie

| Obszar | Status | Co jest | Czego brakuje |
|---|---|---|---|
| **KPI Dashboard** | **TAK** | Cost, clicks, impressions, conversions, CTR, CPC, CPA, ROAS, health score, WoW comparison | — |
| **Campaign Trends** | **TAK** | Daily time series, multi-metric charts, forecast | — |
| **Impression Share** | **TAK** | Campaign + keyword level, budget-lost, rank-lost, top/abs-top IS | — |
| **Quality Score** | **TAK** | QS 1-10, subcomponents (CTR, ad relevance, landing page), audit page | — |
| **Budget Pacing** | **TAK** | Daily spend vs budget limit, utilization % | — |
| **Device Breakdown** | **TAK** | MOBILE/DESKTOP/TABLET metrics per campaign | — |
| **Geo Breakdown** | **TAK** | City-level performance metrics | Brak region/country level |
| **Demographics** | **TAK** | Age + gender breakdown | Brak parental status, income |
| **Time-of-Day** | **TAK** | Hourly + day-of-week analysis (dayparting) | — |
| **Match Type Analysis** | **TAK** | EXACT/PHRASE/BROAD performance comparison | — |
| **N-gram Analysis** | **TAK** | Search term word sequence clustering | — |
| **Landing Pages** | **TAK** | Page-level CTR, cost, conversions | — |
| **Wasted Spend** | **TAK** | Keywords + search terms waste identification | — |
| **RSA Analysis** | **TAK** | Headline/description performance | — |
| **Auction Insights** | **NIE** | Brak | Competitor IS, overlap rate, position above rate, outranking share |
| **Ad Strength Report** | **CZĘŚCIOWO** | Ad strength enum na Ad model + AssetGroup | Brak dedicated ad strength improvement recommendations |
| **Placement Report** | **NIE** | Brak | Display/Video placement performance |
| **Search Query Report** | **TAK** | Search terms z segmentacją (high performer, waste, irrelevant) | — |
| **Change History** | **TAK** | ChangeEvent sync + ActionLog (internal), unified timeline, impact analysis | — |

---

## 3. PODSUMOWANIE POKRYCIA

| Kategoria | Pokrycie | Komentarz |
|---|---|---|
| **Search Campaigns** | **90%** | Brak auction insights, ad scheduling config, bid modifiers |
| **PMax Campaigns** | **70%** | Brak listing groups, feed integration, URL expansion |
| **Shopping Campaigns** | **5%** | Tylko basic campaign metrics |
| **Display Campaigns** | **5%** | Tylko basic campaign metrics |
| **Video Campaigns** | **5%** | Tylko basic campaign metrics |
| **Keyword Management** | **95%** | Pełne — QS, IS, match type, bid, daily metrics |
| **Search Terms** | **95%** | Pełne — segmentacja, trends, bulk actions |
| **Audience Targeting** | **20%** | Read-only metryki, brak management |
| **Ad Management** | **15%** | Pause only, brak inventory sync, brak editor |
| **Extensions/Assets** | **30%** | Read-only type detection, brak details/CRUD |
| **Bidding Strategy** | **40%** | Read campaign settings, brak strategy management |
| **Conversion Tracking** | **60%** | Actions model pełny, brak enhanced/offline/value rules |
| **Reporting** | **85%** | Bogaty zestaw, brak auction insights i placements |
| **Actions/Execution** | **70%** | 8 action types, undo/revert, brak campaign/strategy mutations |

---

## 4. EXPANSION WAVES

### Wave A: Dokończ Search + PMax (PRIORYTET #1)

Codzienne operacje specjalisty PPC na Search i PMax — luki które blokują pełny daily audit.

| # | Feature | Pliki do modyfikacji | Nakład | Opis |
|---|---|---|---|---|
| A1 | **Ad Sync (RSA inventory)** | `google_ads.py`, `models/ad.py`, `seed.py` | **M** | Sync `ad_group_ad` z API → pełny inventory reklam (nie tylko pause). Headlines, descriptions, final URLs, metryki per ad. |
| A2 | **Auction Insights** | `google_ads.py` (nowy sync), nowy model `auction_insight.py`, `analytics_service.py`, `analytics.py`, frontend: `SearchOptimization.jsx` | **L** | Sync `auction_insights` per campaign/ad group. Model: competitor domain, impression share, overlap rate, position above rate, outranking share. UI: tabela konkurentów + trend. |
| A3 | **Bid Modifiers (Device/Location)** | `google_ads.py`, nowy model `bid_modifier.py`, `seed.py` | **M** | Sync campaign/ad group level bid adjustments per device i location. Read + write (adjust modifier). |
| A4 | **Ad Schedule Config** | `google_ads.py`, nowy model `ad_schedule.py`, `seed.py` | **M** | Sync `campaign_criterion` type=AD_SCHEDULE. Read aktualne schedules + bid adjustments. |
| A5 | **Target CPA/ROAS Write** | `google_ads.py` (nowa mutacja), `routers/keywords_ads.py` lub nowy router | **S** | Mutacja `campaign.target_cpa_micros` i `campaign.target_roas`. UI: editable field w campaign detail. |
| A6 | **PMax Listing Groups** | `google_ads.py`, nowy model `listing_group.py` | **M** | Sync `asset_group_listing_group_filter` — struktura product groups w PMax. |
| A7 | **Extension Details** | `models/campaign_asset.py` (rozszerzenie), `google_ads.py` | **M** | Rozszerzenie CampaignAsset o szczegółowe pola: sitelink URLs/descriptions, callout text, structured snippet header+values, call phone number. |
| A8 | **Missing Demographics** | `google_ads.py` (nowy sync), `models/metric_segmented.py` | **S** | Dodaj parental_status_view i household_income_view do segmented metrics. |

**Łączny nakład Wave A:** ~3-4 tygodnie

---

### Wave B: Shopping Campaigns (PRIORYTET #2)

Shopping to drugi najważniejszy typ kampanii dla e-commerce (główna grupa docelowa aplikacji).

| # | Feature | Pliki do modyfikacji | Nakład | Opis |
|---|---|---|---|---|
| B1 | **Product Group Model** | Nowy `models/product_group.py`, `schemas/product_group.py` | **M** | Model: product_group_id, campaign_id, ad_group_id, case_value (brand, category, product_type, custom_label), parent_id (tree), bid_micros, metrics. |
| B2 | **Product Group Sync** | `google_ads.py` (nowy sync `ad_group_criterion` type=LISTING_GROUP) | **M** | GAQL query na `ad_group_criterion` z `listing_scope` i `listing_group` info. Hierarchia tree. |
| B3 | **Shopping Reports** | `analytics_service.py`, `analytics.py`, nowy endpoint | **M** | Product group performance, bid recommendations per product group, ROAS by product category. |
| B4 | **Shopping UI** | Nowa strona lub sekcja w Campaigns | **M** | Product group tree view, performance per group, bid adjustment interface. |
| B5 | **Merchant Center Status** | `google_ads.py` (query `shopping_product` resource) | **S** | Feed status, disapproved products count, pricing issues. Read-only diagnostic. |

**Łączny nakład Wave B:** ~2-3 tygodnie

---

### Wave C: Display Campaigns (PRIORYTET #3)

Display campaigns wymagają osobnego zestawu targetowania (placements, topics, audiences).

| # | Feature | Pliki do modyfikacji | Nakład | Opis |
|---|---|---|---|---|
| C1 | **Placement Model + Sync** | Nowy `models/placement.py`, `google_ads.py` | **M** | Sync `detail_placement_view` + `group_placement_view`. Model: URL/app/YouTube channel, type (WEBSITE, YOUTUBE_CHANNEL, MOBILE_APP), metrics. |
| C2 | **Placement Exclusions** | `google_ads.py` (write), `models/placement.py` | **S** | Read + write placement exclusions (campaign + account level). |
| C3 | **Topic Targeting** | Nowy `models/topic.py`, `google_ads.py` | **M** | Sync `topic_view`. Model: topic_id, topic_path, bid_modifier, metrics. |
| C4 | **Responsive Display Ads** | Rozszerzenie `models/ad.py` | **S** | Dodaj pola: marketing_images, square_images, logos, headlines, descriptions (JSON arrays jak RSA). |
| C5 | **Display Reporting** | `analytics_service.py`, frontend | **M** | Placement performance, topic performance, audience overlap, viewability metrics. |
| C6 | **Audience Management** | Nowy `models/audience.py`, `google_ads.py` | **L** | Master Audience model: audience_id, type (REMARKETING, IN_MARKET, AFFINITY, CUSTOM), name, size, membership_status. Sync + basic management. |

**Łączny nakład Wave C:** ~3-4 tygodnie

---

### Wave D: Video Campaigns (PRIORYTET #4)

Video campaigns (YouTube) wymagają video-specific metrics i ad formats.

| # | Feature | Pliki do modyfikacji | Nakład | Opis |
|---|---|---|---|---|
| D1 | **Video Ad Model** | Rozszerzenie `models/ad.py` | **M** | Video ad fields: video_id, channel_id, ad_format (IN_STREAM, BUMPER, DISCOVERY, SHORTS), duration. |
| D2 | **Video Metrics Sync** | `google_ads.py` | **M** | Video-specific metrics: views, view_rate, avg_cpv, earned_views, earned_subscribers, quartile completion (25/50/75/100%). |
| D3 | **Video Placement Targeting** | Rozszerzenie placement model z Wave C | **S** | YouTube channel/video targeting, topic targeting for video. |
| D4 | **Video Reporting** | `analytics_service.py`, frontend | **M** | Video performance dashboard: view rate by format, audience retention, earned actions, CPV trends. |

**Łączny nakład Wave D:** ~2 tygodnie

---

### Wave E: Demand Gen + Advanced Features (PRIORYTET #5)

| # | Feature | Pliki do modyfikacji | Nakład | Opis |
|---|---|---|---|---|
| E1 | **Demand Gen Campaigns** | Model extensions, `google_ads.py` | **L** | Discover + Gmail + YouTube Shorts campaigns. Creative assets (single image, carousel, video). Product feeds. |
| E2 | **Portfolio Bid Strategy Model** | Nowy `models/bidding_strategy.py`, `google_ads.py` | **M** | BiddingStrategy master table: strategy_id, type, targets, campaign count, shared budget reference. Full sync + config view. |
| E3 | **Shared Budgets** | Nowy `models/shared_budget.py`, `google_ads.py` | **S** | SharedBudget model: budget_id, amount_micros, campaigns (relation), delivery_method. Read + write. |
| E4 | **Enhanced Conversions** | Rozszerzenie `models/conversion_action.py` | **M** | Enhanced conversions setup status, first-party data signals, consent mode settings. |
| E5 | **Offline Conversion Import** | Nowy endpoint, model | **L** | GCLID-based offline conversion upload. Upload UI, validation, status tracking. |
| E6 | **Conversion Value Rules** | Nowy model, `google_ads.py` | **M** | Value rules: adjust conversion value by audience, device, location. Read + write. |
| E7 | **Google Recommendations Integration** | `google_ads.py`, nowy model | **M** | Sync Google's native `recommendation` resource. Show alongside playbook rules. Apply/dismiss via API. |
| E8 | **MCC / Multi-Account** | Nowy `models/mcc.py`, `google_ads.py` | **L** | Manager account support. Account hierarchy, cross-account reporting, bulk operations. |

**Łączny nakład Wave E:** ~5-6 tygodni

---

## 5. PRIORYTETYZACJA — WIDOK OGÓLNY

```
Wave A: Search + PMax gaps      [3-4 tyg]  ← TERAZ (dokończ core)
Wave B: Shopping Campaigns      [2-3 tyg]  ← e-commerce focus
Wave C: Display Campaigns       [3-4 tyg]  ← audience + placements
Wave D: Video Campaigns         [2 tyg]    ← YouTube
Wave E: Demand Gen + Advanced   [5-6 tyg]  ← full coverage
                                ─────────
                        Łącznie: ~15-19 tyg
```

## 6. MAPA ZALEŻNOŚCI

```
Wave A (Search+PMax) ──► Wave B (Shopping) ──► Wave C (Display)
     │                                              │
     │                                              ▼
     │                                         Wave D (Video)
     │
     └──► Wave E (Advanced)
           ├── Portfolio Strategies (zależy od A5: target write)
           ├── MCC (niezależne, ale L)
           └── Google Recommendations (niezależne)

Niezależne od siebie: Wave C i Wave D mogą iść równolegle po Wave B.
Wave E items mogą być robione selektywnie w dowolnym momencie.
```

## 7. CO JEST UNIKALNE (NIE DO POKRYCIA)

Niektóre elementy Google Ads **nie mają sensu** w desktop app:
- **Google Analytics 4 integration** — wymaga osobnego API + OAuth scope
- **Data Studio / Looker Studio** — osobny produkt Google
- **Google Merchant Center feed management** — osobne API, osobny flow
- **Smart campaigns auto-creation** — Google automatycznie zarządza
- **Local Services Ads** — zupełnie inny model biznesowy (leads, nie clicks)
- **Hotel Ads** — niszowy typ, osobny API

Te elementy można pominąć bez utraty wartości dla typowego specjalisty PPC.
