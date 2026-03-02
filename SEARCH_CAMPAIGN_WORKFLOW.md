# SEARCH Campaign Workflow & Optimization Checklist
# Kompletny przewodnik pracy z kampaniami SEARCH w Google Ads

> **Legenda:** 🟢 = zaimplementowane w aplikacji | 🟡 = częściowo zaimplementowane | brak znacznika = do zrobienia poza aplikacją

---

## FAZA 1: AUDYT & DISCOVERY (przed jakąkolwiek optymalizacją)

### 1.1 Struktura konta
- [ ] Sprawdź hierarchię: Konto → Kampanie → Grupy reklam → Słowa kluczowe → Reklamy
- [ ] Czy kampanie są logicznie podzielone (brand vs generic vs competitor vs long-tail)?
- [ ] 🟢 Czy grupy reklam mają tematyczną spójność (max 15-20 keywords per ad group)? — *account-structure audit: oversized ad groups (>20 kw)*
- [ ] 🟢 Czy nie ma duplikacji słów kluczowych między grupami/kampaniami (kanibalizacja)? — *account-structure audit: cannibalization detection*
- [ ] Sprawdź ustawienia kampanii: lokalizacja, język, sieci (wyłącz Search Partners jeśli nie performuje)
- [ ] 🟢 Sprawdź strategię bidowania vs cel biznesowy (czy to właściwy match?) — *bidding-advisor: rekomendacja strategii na podstawie wolumenu konwersji*
- [ ] 🟢 Sprawdź budżety — czy nie ma kampanii ograniczonych budżetem, które performują dobrze? — *budget pacing endpoint*

### 1.2 Baseline metryk
- [ ] 🟢 Zbierz KPI z ostatnich 30/60/90 dni: CTR, CPC, CPA, ROAS, Conv Rate, Impression Share — *dashboard-kpis + trends*
- [ ] Porównaj z benchmarkami branżowymi
- [ ] 🟢 Zidentyfikuj top 20% kampanii/grup/keywords (Pareto — skąd idzie 80% konwersji?) — *analytics/campaigns + wasted-spend*
- [ ] 🟢 Zidentyfikuj bottom 20% (gdzie pali się budżet bez efektu?) — *wasted-spend analysis*
- [ ] 🟢 Zanotuj sezonowość — porównaj YoY jeśli dane dostępne — *trends + compare-periods*

### 1.3 Tracking & atrybucja
- [ ] Czy konwersje są poprawnie skonfigurowane (Google Tag / GTM)?
- [ ] Czy wartości konwersji są przekazywane (e-commerce / lead value)?
- [ ] Jaki model atrybucji? (data-driven preferowany, last-click = czerwona flaga)
- [ ] Czy enhanced conversions są włączone?
- [ ] Czy offline conversion import jest skonfigurowany (jeśli applicable)?
- [ ] Czy consent mode v2 jest wdrożony?

---

## FAZA 2: STRUKTURA SŁÓW KLUCZOWYCH

### 2.1 Keyword research
- [ ] Keyword Planner — wolumeny, konkurencja, suggested bids
- [ ] 🟢 Analiza search terms z istniejących kampanii (złoto w danych!) — *search-terms/segmented + n-gram*
- [ ] Competitor keyword analysis (Auction Insights + narzędzia 3rd party)
- [ ] Long-tail expansion — pytania, "jak", "najlepszy", "porównanie"
- [ ] Mapowanie intencji: informacyjna vs nawigacyjna vs transakcyjna vs komercyjna
- [ ] 🟢 Grupowanie tematyczne (SKAG jest martwy → STAG: Single Theme Ad Groups) — *semantic clustering*

### 2.2 Match types — strategia
- [ ] 🟢 Exact match → high-intent, proven converters (rdzeń) — *match-type-analysis*
- [ ] 🟢 Phrase match → kontrolowane rozszerzenie (środek) — *match-type-analysis*
- [ ] 🟢 Broad match → TYLKO z Target CPA/ROAS bidding (eksploracja) — *match-type-analysis*
- [ ] 🟢 Nie mieszaj broad + exact w tej samej grupie reklam (broad kradnie ruch) — *account-structure audit: mixed match types detection*
- [ ] 🟢 Każdy match type ma swoją rolę — exact = precyzja, broad = zasięg/discovery — *match-type-analysis z CTR/CPC/CPA/ROAS per type*

### 2.3 Negative keywords
- [ ] Lista negatywów na poziomie konta (shared negative lists)
- [ ] Lista negatywów per kampania (specyficzne wykluczenia)
- [ ] 🟢 Standardowe wykluczenia: "darmowy", "praca", "jak zrobić", "DIY", "wikipedia" — *IRRELEVANT_KEYWORDS w constants.py + auto-segmentation*
- [ ] Cross-campaign negatives (brand campaign wyklucza generic terms i odwrotnie)
- [ ] 🟢 Regularne przeglądanie search terms (min. 1x/tydzień) → nowe negatywy — *search-terms/segmented WASTE + IRRELEVANT segments + rekomendacja ADD_NEGATIVE*

---

## FAZA 3: REKLAMY (Ad Copy)

### 3.1 RSA (Responsive Search Ads) — best practices
- [ ] Min. 1 RSA per ad group (Google wymaga, ale najlepiej 2-3 do testów)
- [ ] 15 nagłówków: wykorzystaj WSZYSTKIE sloty
  - [ ] 3-4 z głównym keyword (relevance)
  - [ ] 2-3 z USP / wyróżnikami
  - [ ] 2-3 z CTA (Zamów, Sprawdź, Otrzymaj)
  - [ ] 2-3 z liczbami/statystykami/social proof
  - [ ] 2-3 z ofertą/promocją (jeśli applicable)
- [ ] 4 opisy: complementary, nie powtarzające nagłówków
- [ ] 🟢 Pin TYLKO gdy absolutnie konieczne (ogranicza ML optymalizację) — *RSA analysis pokazuje pinned asset count*
- [ ] 🟢 Ad Strength: celuj w "Good" lub "Excellent" (nie obsesyjnie — performance > strength) — *RSA analysis z ad_strength badge per reklama*

### 3.2 Ad extensions (Assets)
- [ ] Sitelinks (min. 4, najlepiej 8) — z własnymi opisami
- [ ] Callouts (min. 4) — USP, darmowa dostawa, gwarancja, etc.
- [ ] Structured snippets — kategorie produktów/usług
- [ ] Call extension (jeśli telefon = konwersja)
- [ ] Location extension (jeśli lokalny biznes)
- [ ] Price extension (jeśli applicable)
- [ ] Image extensions (zwiększa CTR 5-15%)
- [ ] Promotion extension (przy aktywnych promocjach)
- [ ] Lead form extension (jeśli lead gen)

### 3.3 Landing pages
- [ ] Czy LP jest spójny z reklamą (message match)?
- [ ] Mobile-first (>60% ruchu to mobile)
- [ ] Page speed: < 3s load time (Core Web Vitals green)
- [ ] Jasny CTA above the fold
- [ ] Trust signals: opinie, certyfikaty, loga klientów
- [ ] 🟢 Czy jest dedykowany LP per ad group/temat (nie generic homepage)? — *landing-pages analysis grupuje metryki per URL*

---

## FAZA 4: BIDDING & BUDŻETY

### 4.1 Wybór strategii bidowania
- [ ] 🟢 **Nowe kampanie / mało danych (<30 conv/30d):** Manual CPC lub Maximize Clicks (z cap) — *bidding-advisor: automatyczna rekomendacja na podstawie wolumenu*
- [ ] 🟢 **Wystarczające dane (30-50 conv/30d):** Target CPA lub Maximize Conversions — *bidding-advisor*
- [ ] 🟢 **Dużo danych (>50 conv/30d) + wartości:** Target ROAS lub Maximize Conversion Value — *bidding-advisor*
- [ ] Portfolio bid strategies dla kampanii z tym samym celem
- [ ] Nie zmieniaj strategii zbyt często (min. 2-3 tygodnie nauki)

### 4.2 Budget management
- [ ] Budżet dzienny = miesięczny / 30.4
- [ ] 🟢 Nigdy nie ograniczaj budżetu kampanii, która spełnia target CPA/ROAS — *budget pacing + health score uwzględnia budget-capped campaigns*
- [ ] 🟢 Kampanie z Limited by Budget + dobry CPA → zwiększ budżet — *rekomendacja REALLOCATE_BUDGET (Rule 7)*
- [ ] Shared budgets dla kampanii z tym samym priorytetem
- [ ] 🟢 Budget pacing: czy wydaje się równomiernie czy front-loads? — *budget-pacing endpoint z projected spend*

### 4.3 Bid adjustments (Manual/eCPC)
- [ ] 🟢 Device bid adjustments (mobile vs desktop — na podstawie danych konwersji) — *device-breakdown z CTR/CPC/ROAS per device*
- [ ] 🟢 Location bid adjustments (regiony z lepszym/gorszym performance) — *geo-breakdown per miasto*
- [ ] 🟢 Ad schedule bid adjustments (godziny/dni z wyższym CVR) — *dayparting (dzień tygodnia)*
- [ ] Audience bid adjustments (RLSA, in-market, custom segments)
- [ ] UWAGA: przy Smart Bidding większość adjustments jest ignorowana (poza device -100%)

---

## FAZA 5: CODZIENNA OPTYMALIZACJA (Daily/Weekly Rituals)

### 5.1 Codziennie (5-10 min per konto)
- [ ] 🟢 Sprawdź spend vs budget pacing — czy jesteśmy on track? — *budget-pacing*
- [ ] 🟢 Sprawdź alerty: odrzucone reklamy, problemy z płatnością, anomalie — *alerts system + anomaly detection*
- [ ] 🟢 Szybki przegląd top campaigns: CPA/ROAS w normie? — *dashboard-kpis*
- [ ] 🟢 Czy są spiki/dropy w wydatkach lub konwersjach? — *anomaly detection (spend spike, conversion drop, CTR drop)*

### 5.2 Co tydzień (30-60 min)
- [ ] 🟢 **Search Terms Report** — NAJWAŻNIEJSZY raport:
  - [ ] 🟢 Nowe negatywy (irrelevant, off-topic, competitor names jeśli nie chcesz) — *segmented WASTE + IRRELEVANT + rekomendacja ADD_NEGATIVE*
  - [ ] 🟢 Nowe positive keywords (search terms z konwersjami, ale nie jako keyword) — *segmented HIGH_PERFORMER + rekomendacja ADD_KEYWORD*
  - [ ] Sprawdź close variants — czy exact match nie łapie śmieci?
- [ ] Auction Insights — kto zyskuje/traci impression share?
- [ ] 🟢 Ad performance — który RSA variant wygrywa? — *RSA analysis z BEST/WORST per ad group*
- [ ] 🟢 Keyword status — czy nie ma "Low search volume", "Below first page bid"? — *serving_status badge na liście keywords*
- [ ] 🟢 Quality Score changes — co spadło, co wzrosło? — *quality-score-audit*

### 5.3 Co miesiąc (2-4h deep dive)
- [ ] 🟢 Pełny przegląd performance vs targets (CPA, ROAS, volume) — *dashboard-kpis + trends*
- [ ] 🟢 Porównanie MoM i YoY — *compare-periods z t-testem*
- [ ] 🟢 **N-gram analysis** — jakie frazy/słowa powtarzają się w converting/non-converting terms? — *ngram-analysis (1/2/3-gramy)*
- [ ] 🟢 **Wasted spend audit** — keywords z wydatkami >X i 0 konwersji → pauza/negatyw — *wasted-spend analysis + rekomendacja PAUSE_KEYWORD*
- [ ] **Keyword expansion** — nowe tematy, long-tail, pytania
- [ ] 🟢 **Ad copy refresh** — wymień najsłabsze nagłówki/opisy — *RSA analysis identyfikuje WORST ads + rekomendacja PAUSE_AD*
- [ ] **Landing page test** — A/B test nowego LP jeśli CVR spada
- [ ] 🟢 **Bid strategy review** — czy obecna strategia nadal optymalna? — *bidding-advisor: analiza konwersji + rekomendacja upgrade/change*
- [ ] **Negative keyword cleanup** — czy negatywy nie blokują dobrego ruchu?
- [ ] 🟢 **Device/Geo/Time analysis** — realokacja budżetu — *device-breakdown + geo-breakdown + dayparting*

---

## FAZA 6: ZAAWANSOWANA OPTYMALIZACJA

### 6.1 Quality Score (QS) optymalizacja
- [ ] 🟢 Zidentyfikuj keywords z QS < 5 (priorytet: high-spend + low QS) — *quality-score-audit z listą issues*
- [ ] 🟢 QS składniki:
  - [ ] 🟢 **Expected CTR** → lepsze ad copy, bardziej relevantne nagłówki — *historical_search_predicted_ctr w modelu*
  - [ ] 🟢 **Ad Relevance** → keyword w nagłówku, tematyczna spójność grupy — *historical_creative_quality w modelu*
  - [ ] 🟢 **Landing Page Experience** → szybkość, relevance, mobile UX — *historical_landing_page_quality w modelu*
- [ ] Keyword z QS 3-4 i dużym spend → przenieś do nowej, ciaśniejszej ad group
- [ ] 🟢 QS 1-2 → rozważ pauzę (Google karze Cię wyższym CPC) — *rekomendacja PAUSE_KEYWORD dla high-spend zero-conv*

### 6.2 Impression Share & SOV
- [ ] 🟢 Search Impression Share — ile rynku masz? — *impression-share endpoint + kampania/keyword level IS*
- [ ] 🟢 Lost IS (Budget) → zwiększ budżet lub zawęź targeting — *search_budget_lost_is tracked*
- [ ] 🟢 Lost IS (Rank) → popraw QS, zwiększ bidy, lepsze reklamy — *search_rank_lost_is tracked*
- [ ] 🟢 Absolute Top IS — dla brand terms celuj w >90% — *search_abs_top_impression_share tracked*
- [ ] Competitor conquest — monitoruj ich IS vs Twoje

### 6.3 Audience layering (Observation mode)
- [ ] RLSA: all visitors, converters, cart abandoners (bid +20-50%)
- [ ] In-market audiences relevantne dla branży
- [ ] Custom segments (keyword-based, URL-based)
- [ ] Similar/Lookalike audiences (jeśli dostępne)
- [ ] Customer Match (1st party lists)
- [ ] Ustaw w trybie "Observation" → zbieraj dane → potem "Targeting" dla best performers

### 6.4 Dayparting (Ad Schedule)
- [ ] 🟢 Przeanalizuj konwersje per godzina i dzień tygodnia (min. 30 dni danych) — *dayparting (dzień tygodnia) + hourly-dayparting (heatmap 0-23h)*
- [ ] Wyłącz lub obniż bidy w godzinach z zerową konwersją i wysokim kosztem
- [ ] Podwyższ bidy w peak hours (np. B2B: pon-pt 9-17)
- [ ] Uwaga: Smart Bidding robi to automatycznie — manual schedule ma sens przy Manual CPC

### 6.5 Geo-targeting
- [ ] "People IN or REGULARLY IN" (nie "interested in" — to łapie turystów)
- [ ] 🟢 Przeanalizuj performance per region/miasto — *geo-breakdown z top cities*
- [ ] Wyklucz lokalizacje z zerowym ROI
- [ ] Podwyższ bidy w top-performing regionach
- [ ] Rozważ oddzielne kampanie dla top 3-5 miast (osobny budżet + copy)

---

## FAZA 7: TESTOWANIE

### 7.1 Ad copy testing
- [ ] Testuj 2-3 RSA per ad group (rotacja "Optimize")
- [ ] Zmieniaj JEDNĄ zmienną naraz (nagłówek, CTA, USP)
- [ ] Min. 1000 impressions / 100 clicks przed wyciąganiem wniosków
- [ ] Statystyczna istotność (95% confidence) — nie reaguj na szum
- [ ] 🟡 Winner stays, loser gets replaced → ciągły cykl testowy — *RSA analysis identyfikuje BEST/WORST + PAUSE_AD rekomendacja*

### 7.2 Landing page testing
- [ ] A/B test z Google Optimize / VWO / Unbounce
- [ ] Testuj: headline, CTA button, form length, social proof placement
- [ ] Nie testuj koloru buttona — testuj VALUE PROPOSITION
- [ ] Min. 200 konwersji per variant dla statystycznej istotności
- [ ] Zwycięzca staje się nowym kontrolnym

### 7.3 Bid strategy experiments
- [ ] Google Ads Experiments (Campaign Experiments)
- [ ] Test A: obecna strategia vs Test B: nowa strategia
- [ ] 50/50 traffic split, min. 4 tygodnie
- [ ] Porównuj: CPA, conversion volume, ROAS

---

## FAZA 8: REPORTING & ANALIZA

### 8.1 KPI Framework
| Poziom | Metryki |
|--------|---------|
| Business | Revenue, Profit, LTV, CAC |
| Account | 🟢 Total Conv, CPA, ROAS, Spend — *dashboard-kpis* |
| Campaign | 🟢 Conv Rate, CPA, Impression Share — *analytics/campaigns + impression-share* |
| Ad Group | 🟢 CTR, QS, CPC, Conv Rate — *keywords + RSA analysis* |
| Keyword | 🟢 QS, CPC, CTR, Conv, CPA — *keywords endpoint + quality-score-audit* |
| Ad | 🟢 CTR, Conv Rate, Ad Strength — *RSA analysis* |
| Search Term | 🟢 CTR, Conv, Relevance — *search-terms + segmented* |

### 8.2 Raporty do przygotowania
- [ ] 🟢 Weekly performance snapshot (spend, conv, CPA, ROAS vs target) — *dashboard-kpis + trends*
- [ ] 🟢 Monthly deep dive (trends, insights, actions taken, plan) — *trends + compare-periods + action history*
- [ ] Quarterly strategy review (market changes, new opportunities, budget reallocation)
- [ ] 🟢 Search terms hygiene report (added/excluded terms) — *search-terms/segmented + export*
- [ ] Competitive landscape (Auction Insights trends)

### 8.3 Alerting
- [ ] 🟢 Spend > 120% dziennego budżetu → natychmiastowy alert — *anomaly detection SPEND_SPIKE*
- [ ] 🟢 CPA > 150% target przez 3 dni → alert — *anomaly detection Rule 4: CPA_SUSTAINED*
- [ ] 🟢 Conversion drop > 50% day-over-day → alert — *anomaly detection CONVERSION_DROP*
- [ ] 🟢 CTR drop > 30% week-over-week → alert — *anomaly detection CTR_DROP*
- [ ] 🟢 Impression Share drop > 20pp → alert (nowy competitor?) — *impression-share tracking*
- [ ] 🟢 Disapproved ads → alert (ruch się zatrzymuje!) — *anomaly detection Rule 5: DISAPPROVED_ADS*

---

## FAZA 9: SKALOWANIE

### 9.1 Kiedy skalować?
- [ ] 🟢 CPA stabilnie < target przez 2+ tygodnie — *trends + compare-periods*
- [ ] 🟢 ROAS stabilnie > target — *trends + compare-periods*
- [ ] 🟢 Impression Share < 80% (jest jeszcze rynek do wzięcia) — *impression-share endpoint*
- [ ] 🟢 Konwersje nie spadają przy wzroście budżetu — *trends + forecast*

### 9.2 Jak skalować bezpiecznie?
- [ ] 🟢 Budżet: zwiększaj max 20-30% na raz, czekaj 7-14 dni — *safety limit MAX_BUDGET_CHANGE_PCT = 0.30*
- [ ] Nowe keywords: dodawaj stopniowo, monitoruj CPA
- [ ] Nowe match types: broad match + Smart Bidding (ale monitoruj search terms!)
- [ ] Nowe lokalizacje: testuj w osobnej kampanii najpierw
- [ ] Nowe audiences: observation → targeting po zebraniu danych
- [ ] NIGDY nie skaluj kampanii, która nie spełnia targets

### 9.3 Diminishing returns — kiedy przestać?
- [ ] CPA rośnie mimo stałego impression share → rynek nasycony
- [ ] Marginal CPA nowych konwersji > lifetime value
- [ ] 🟢 Impression Share > 95% → nie ma więcej ruchu do wzięcia — *impression-share tracking*
- [ ] W tym momencie: optymalizuj, nie skaluj (lub otwórz nowe kanały)

---

## FAZA 10: CHECKLIST RED FLAGS (natychmiastowa reakcja!)

- [ ] 🟢 🔴 Kampania wydaje budżet a ma 0 konwersji > 7 dni — *anomaly detection + rekomendacja PAUSE_KEYWORD*
- [ ] 🟢 🔴 CPA > 3× target — *health score + rekomendacja DECREASE_BID*
- [ ] 🟢 🔴 Broad match keywords łapią totalnie irrelevant search terms — *search-terms/segmented IRRELEVANT + ADD_NEGATIVE*
- [ ] 🟢 🔴 Quality Score = 1-2 na high-spend keyword — *quality-score-audit flaguje "very low QS"*
- [ ] 🟢 🔴 Reklama odrzucona (disapproved) → 0 ruchu — *anomaly detection Rule 5: DISAPPROVED_ADS alert + approval_status badge*
- [ ] 🔴 Search Partners generuje >30% spend z niskim CVR
- [ ] 🔴 Conversion tracking broken (nagle 0 konwersji w całym koncie)
- [ ] 🔴 Competitor biduje na Twój brand a nie masz brand campaign
- [ ] 🔴 Landing page 404 / timeout
- [ ] 🟢 🔴 Duplicated keywords cannibalizują się (ten sam term, różne kampanie) — *account-structure audit: cannibalization detection*
- [ ] 🟢 🔴 Budget capped na kampanii z najlepszym CPA w koncie — *budget-pacing + REALLOCATE_BUDGET*
- [ ] 🔴 Auto-applied recommendations włączone (Google optymalizuje pod SIEBIE, nie pod Ciebie)

---

## GOLDEN RULES (Wydrukuj i powieś nad biurkiem)

1. **Data > Intuicja.** Każda decyzja oparta na liczbach, nie "wydaje mi się".
2. **Search Terms Report jest królem.** Jeśli robisz jedną rzecz tygodniowo — rób to.
3. **Nie optymalizuj za wcześnie.** Min. 2 tygodnie / 30 konwersji przed wnioskami.
4. **Struktura > Taktyka.** Źle zbudowane konto nie da się zoptymalizować reklamami.
5. **Quality Score to efekt, nie cel.** Popraw relevance i LP — QS pójdzie w górę.
6. **Smart Bidding potrzebuje danych.** < 30 conv/miesiąc = manual lub maximize clicks.
7. **Testuj jedno na raz.** Zmiana 5 rzeczy = brak wiedzy co zadziałało.
8. **Landing page = połowa sukcesu.** Najlepsza reklama nie sprzeda na złym LP.
9. **Nie walcz z algorytmem.** Daj mu dane (konwersje, wartości, audiences) i pozwól działać.
10. **Wyłącz auto-applied recommendations.** Zawsze. Bez wyjątku.
