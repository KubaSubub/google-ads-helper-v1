# Roadmap rozwoju optymalizacji — Google Ads Helper v1

> **Cel:** Specjalista Google Ads wchodzi do aplikacji i w 15-30 minut przeprowadza
> kompletny codzienny audyt + optymalizację kont Search, DSA i PMax (kanał search).
>
> Poniżej: analiza luk między obecnym stanem aplikacji a pełnym workflow specjalisty.

---

## LEGENDA STATUSÓW

| Status | Znaczenie |
|--------|-----------|
| ✅ DONE | W pełni zaimplementowane |
| 🟡 PARTIAL | Częściowo — działa, ale brakuje elementów |
| ❌ BRAK | Nie istnieje w aplikacji |

---

## A. CODZIENNY AUDYT — "Morning Check" (brakujące elementy)

### A1. ❌ Panel "Daily Audit" (nowa strona)
**Co:** Jeden ekran, który agreguje WSZYSTKIE codzienne kontrole w jednym widoku.
Zamiast klikania po 5 stronach, specjalista widzi od razu:
- Budget pacing (wszystkie kampanie — wykres % wydania vs dzień miesiąca)
- Anomalie z ostatnich 24h (spikes, dropy konwersji, CTR)
- Odrzucone reklamy (disapproved ads)
- Kampanie z `Limited by Budget` + dobry CPA
- Nowe search terms wymagające decyzji (WASTE/IRRELEVANT z ostatnich 24h)
- Zmiany w koncie wykonane przez Google (auto-applied recommendations)

**Dlaczego:** Adalysis i Optmyzr mają daily task dashboards — to #1 feature, który odróżnia "narzędzie do analizy" od "narzędzia do pracy".

**Nakład:** Średni — większość danych już jest w API, trzeba je zagregować w jednym widoku.

### A2. ❌ Change History Monitor
**Co:** Pobieranie `change_event` z Google Ads API (dostępne przez API, max 30 dni wstecz):
- Kto zmienił co (user vs system vs API)
- Wykrywanie zmian z `change_client_type = GOOGLE_ADS_RECOMMENDATIONS_SUBSCRIPTION` → auto-applied recommendations
- Alert: "Google automatycznie dodał 15 broad match keywords wczoraj"
- Alert: "Google automatycznie zmienił bidding strategy"

**Dlaczego:** Golden Rule #10 z workflow: "Wyłącz auto-applied recommendations. Zawsze." — ale klienci tego nie robią, więc trzeba monitorować.

**API:** `google.ads.googleads.v19.services.GoogleAdsService` → `change_event` resource

**Nakład:** Średni — nowy sync + model + UI widok.

### A3. ❌ Conversion Tracking Health Check
**Co:** Automatyczna weryfikacja stanu śledzenia konwersji:
- Czy tagi konwersji są aktywne (status per conversion action)
- Czy enhanced conversions jest włączony
- Jakie modele atrybucji są ustawione (flagowanie last-click)
- Ile konwersji przychodzi z modelingu (consent mode) vs tagów
- Czy conversion lag powoduje zaniżone raportowanie

**Dlaczego:** "Tracking & Atrybucja" (Faza 1.3 w workflow) jest całkowicie poza aplikacją. Bez tego optymalizujemy na potencjalnie złych danych.

**API:** `customer.conversion_tracking_setting`, `conversion_action` resource

**Nakład:** Średni — nowy endpoint + widget na Dashboard/Daily Audit.

---

## B. SEARCH TERMS — rozszerzenia

### B1. 🟡 → ✅ Bulk Actions na Search Terms
**Co:** Obecnie: segmentacja (WASTE/HIGH_PERFORMER/IRRELEVANT) + rekomendacja.
Brakuje: zaznaczanie wielu search terms → "Dodaj jako negative" / "Dodaj jako keyword" jednym klikiem z poziomu listy.
- Checkbox selection na tabeli search terms
- Bulk "Add as Negative" (z wyborem poziomu: campaign / ad group / shared list)
- Bulk "Add as Keyword" (z wyborem ad group + match type)
- Preview zmian przed zatwierdzeniem

**Dlaczego:** To jest #1 zadanie tygodniowe specjalisty. Bez bulk actions musi to robić ręcznie w Google Ads.

**Nakład:** Średni — backend `apply_action` już obsługuje ADD_NEGATIVE i ADD_KEYWORD pojedynczo, trzeba bulk + UI.

### B2. ❌ Search Terms Trend Analysis
**Co:** Porównanie search terms między okresami:
- "Nowe search terms, których nie było tydzień temu"
- "Search terms, które zaczęły kosztować więcej"
- "Search terms, które przestały konwertować"
- Trend volume per search term (sparklines)

**Dlaczego:** Jednorazowy snapshot search terms nie pokazuje dynamiki. Specjalista potrzebuje wiedzieć CO SIĘ ZMIENIŁO.

**Nakład:** Średni — wymaga przechowywania historii search terms (model SearchTermDaily lub timestamped snapshots).

### B3. ❌ Close Variant Analysis
**Co:** Wykrywanie, gdy exact match keywords łapią search terms zbyt odległe od oryginalnego keyword:
- Mapowanie: keyword → jakie search terms matchuje
- Scoring odległości (Levenshtein / semantic similarity)
- Flagowanie: "Twój exact [buty skórzane] matchuje 'skórzane kurtki damskie'"

**Dlaczego:** Close variants w Google Ads rozszerzają się coraz agresywniej. Punkt 2.2 w workflow: "Sprawdź close variants — czy exact match nie łapie śmieci?"

**Nakład:** Średni — analiza na istniejących danych search_term ↔ keyword.

---

## C. DSA (Dynamic Search Ads) — BRAK WSPARCIA

### C1. ❌ DSA Targets Analysis
**Co:**
- Import i analiza DSA targets (webpage categories, URLs, page feeds)
- Performance per DSA target (CTR, CPA, ROAS)
- Rekomendacje: "Ten target kosztuje dużo a nie konwertuje → wyklucz"
- Porównanie: DSA coverage vs ręczne keywords (overlap detection)

**API:** `dynamic_search_ads_search_term_view`, `webpage` criterion

**Nakład:** Duży — nowe modele, sync, analiza, UI.

### C2. ❌ DSA Auto-Generated Headlines Audit
**Co:**
- Raport: jakie nagłówki Google automatycznie generuje dla DSA
- Flagowanie nagłówków niespójnych z landing page
- Scoring message match (headline ↔ landing page title)

**Dlaczego:** DSA automatycznie generuje nagłówki z treści strony. Bez kontroli mogą być nieodpowiednie.

**Nakład:** Średni — wymaga pobrania ad preview / creative z API.

### C3. ❌ DSA ↔ Standard Search Overlap
**Co:**
- Wykrywanie search terms, które matchują zarówno DSA jak i standardowe kampanie Search
- Rekomendacja: dodaj negatyw w DSA dla terms pokrytych przez ręczne keywords
- "DSA kradnie ruch z Twoich exact match keywords"

**Dlaczego:** Kanibalizacja DSA ↔ Search to jeden z najczęstszych problemów.

**Nakład:** Średni — cross-referencing istniejących danych.

---

## D. PMAX (Performance Max) — rozszerzenia kanału Search

### D1. 🟡 → ✅ PMax Channel Performance Breakdown
**Co:** Obecnie: sync `pmax_search_terms`. Brakuje:
- Breakdown wydatków per channel (Search vs Display vs YouTube vs Discover vs Shopping)
- Porównanie: ile % budżetu PMax idzie na Search vs inne kanały
- Alerting: "80% budżetu PMax idzie na Display, a konwersje generuje Search"

**API:** `segments.ad_network_type` na campaign/asset_group performance

**Nakład:** Średni — rozszerzenie sync + nowy widok.

### D2. ❌ Asset Group Performance Analysis
**Co:**
- Performance per asset group (nie per kampania PMax)
- Asset strength + individual asset performance (text, image, video)
- Rekomendacje: "Ten asset group ma 'Poor' strength — dodaj 5 nagłówków"
- Best/worst performing combinations

**API:** `asset_group`, `asset_group_asset`, `asset_group_listing_group_filter`

**Dlaczego:** PMax optymalizacja = optymalizacja asset groups. Bez tego nie wiadomo co działa.

**Nakład:** Duży — nowe modele, sync, UI.

### D3. ❌ PMax vs Search Cannibalization
**Co:**
- Wykrywanie, gdy PMax i kampanie Search walczą o te same zapytania
- Analiza: CPA/ROAS per search term w PMax vs Search
- Rekomendacja: "Dodaj brand terms jako negative w PMax" / "Przenieś budget na Search"

**Dlaczego:** Od 2025 PMax ma rozszerzony search term reporting. Kanibalizacja PMax ↔ Search to top problem.

**Nakład:** Średni — cross-referencing istniejących search terms z PMax i Search.

---

## E. GOTOWE RAPORTY (one-click reports)

### E1. ❌ Weekly Performance Report
**Co:** Automatycznie generowany raport tygodniowy w formacie gotowym do wysłania klientowi:
- KPI vs target (CPA, ROAS, spend, conversions)
- Top 5 zmian w performance (co wzrosło/spadło)
- Wykonane działania (z action history)
- Search terms added/excluded (z action history)
- Plan na następny tydzień (z rekomendacji)

**Format:** Markdown/HTML/PDF eksport.

**Nakład:** Średni — agregacja istniejących danych + template + eksport.

### E2. ❌ Monthly Deep Dive Report
**Co:** Raport miesięczny z głęboką analizą:
- MoM i YoY porównanie (dane już są w compare-periods)
- Breakdown per kampania z trendami
- N-gram analysis highlights
- Wasted spend summary
- Quality Score changes
- Device/Geo/Time shifts
- Budget utilization
- Rekomendacje na następny miesiąc

**Nakład:** Średni — podobnie jak E1, plus formatowanie.

### E3. ❌ Account Health Report (Audyt)
**Co:** Kompleksowy audyt konta z scoringiem:
- Struktura konta (score 0-100)
- Keyword coverage & match type balance
- Ad copy coverage (ile ad groups ma <2 RSA?)
- Extension/asset coverage
- Quality Score distribution
- Negative keyword coverage
- Conversion tracking health
- Budget efficiency
- Porównanie z benchmarkami branżowymi

**Nakład:** Duży — wymaga wielu nowych analiz + scoring algorithm.

---

## F. SKRYPTY I AUTOMATYZACJE

### F1. ❌ Scheduled Sync & Alert Pipeline
**Co:** Automatyczny sync danych + generowanie alertów bez ręcznego odpalania:
- Cron/scheduler: sync co 6h (lub konfigurowalne)
- Po sync → automatyczne generowanie rekomendacji
- Po sync → anomaly detection
- Notyfikacje: email / Slack / in-app o krytycznych alertach

**Dlaczego:** Specjalista nie powinien klikać "Sync" ręcznie. Dane powinny czekać rano.

**Nakład:** Średni — scheduling (APScheduler/Celery) + notification system.

### F2. ❌ Quick Optimization Scripts (one-click actions)
**Co:** Zestaw "szybkich skryptów" dostępnych z UI:
- **"Wyczyść search terms"** — auto-apply wszystkich rekomendacji ADD_NEGATIVE z kategorii IRRELEVANT (z preview)
- **"Pauza spalających keywords"** — auto-apply PAUSE_KEYWORD dla all zero-conv high-spend keywords
- **"Boost winners"** — zwiększ budżet kampaniom z CPA < target i IS < 80%
- **"Emergency brake"** — pauza kampanii/keywords z CPA > 3× target
- **"Negative keyword propagation"** — dodaj negative z jednej kampanii do wszystkich kampanii z tym samym tematem

**Dlaczego:** Adalysis ma "one-click apply" — to oszczędza godziny tygodniowo.

**Nakład:** Średni — UI bulk actions + confirmation flow + istniejący apply_action backend.

### F3. ❌ Automated Rules Engine
**Co:** Konfigurowane reguły, które wykonują się automatycznie:
- "Jeśli keyword ma >50 zł spend i 0 konwersji przez 14 dni → pauza"
- "Jeśli search term pojawia się >3 razy z CTR < 1% → add negative"
- "Jeśli kampania ma IS Lost Budget > 20% i CPA < target → alert zwiększ budżet"
- Edytor reguł w UI (condition → action → threshold)

**Dlaczego:** Google Ads ma Automated Rules, ale są ograniczone. Custom rules engine daje pełną kontrolę.

**Nakład:** Duży — rules engine + scheduler + UI builder.

---

## G. ZAAWANSOWANA ANALIZA

### G1. ❌ Auction Insights Tracking
**Co:**
- Import Auction Insights z API (impression share, overlap rate, outranking share per competitor)
- Trend: "Competitor X zyskuje IS — wzrost o 15pp w tym miesiącu"
- Alert: "Nowy competitor pojawił się w Twoich aukcjach"
- Porównanie: Twoja pozycja vs top 3 competitors over time

**API:** `auction_insights` report via Google Ads API / `search_term_insight`

**Nakład:** Duży — nowy sync + model + trending UI.

### G2. ❌ Keyword Expansion Suggestions
**Co:**
- Na podstawie converting search terms → sugestie nowych keyword do dodania
- Keyword grouping (clustering) — propozycja nowych ad groups
- Gap analysis: "Te search terms konwertują, ale nie masz ich jako keywords"
- Long-tail expansion: dodaj warianty z pytaniami ("jak", "najlepszy", "porównanie")

**Dlaczego:** Punkt 2.1 workflow: "Keyword research — analiza search terms to złoto w danych!"

**Nakład:** Średni — analiza na istniejących search terms + keyword deduplication.

### G3. ❌ Landing Page Performance Audit
**Co:** Obecne: `landing-pages` endpoint grupuje metryki per URL. Brakuje:
- Page speed check (Core Web Vitals via PageSpeed Insights API)
- Mobile-friendliness score
- Message match scoring (ad headline vs LP title — semantic similarity)
- A/B test tracking (jeśli LP ma warianty)
- Alert: "Ten LP ma bounce rate 80% — sprawdź"

**Nakład:** Duży — integracja z PageSpeed API + semantic analysis.

### G4. ❌ Cross-Campaign Analysis
**Co:**
- Keyword overlap między kampaniami (rozszerzona kanibalizacja)
- Budget allocation optimizer: "Przenieś 500 zł z kampanii A (CPA 120 zł) do kampanii B (CPA 45 zł)"
- Shared vs isolated performance: które kampanie pomagają/szkodzą innym
- Portfolio view: performance per business line/product

**Nakład:** Średni — cross-referencing istniejących danych + optimizer algorithm.

### G5. ❌ Ad Extensions (Assets) Audit
**Co:**
- Import i analiza rozszerzeń (sitelinks, callouts, structured snippets, call, image)
- Coverage check: "3 ad groups nie mają sitelinks"
- Performance per extension type
- Rekomendacje: "Dodaj image extensions — zwiększa CTR 5-15%"

**API:** `asset`, `campaign_asset`, `ad_group_asset`

**Nakład:** Duży — nowe modele, sync, analiza.

---

## H. UX / WORKFLOW IMPROVEMENTS

### H1. ❌ Task Queue / Action Plan
**Co:**
- Kolejka zadań do wykonania (na podstawie rekomendacji)
- Priorytetyzacja: co zrobić NAJPIERW (highest impact)
- Checklist z progress tracking
- "Dzisiaj do zrobienia: 3 negatywy, 1 bid change, 2 ad pauses"

**Dlaczego:** Optmyzr i Adalysis mają "task-based workflow" — to różnica między "dashboardem" a "narzędziem pracy".

### H2. ❌ Comparison / Benchmark Panel
**Co:**
- Benchmarki branżowe (średnie CTR, CPC, CPA per branża)
- Porównanie kont: "Klient A vs Klient B — kto performuje lepiej?"
- Porównanie kampanii: side-by-side per metryka
- Historyczne benchmarki konta (vs własny baseline)

### H3. ❌ Keyboard Shortcuts & Speed Workflow
**Co:**
- Quick search: Ctrl+K → szukaj keyword/kampanię/search term
- Keyboard navigation między sekcjami
- Quick actions: "N" = add negative, "P" = pause, "B" = bid change

---

## PRIORYTETY — REKOMENDOWANA KOLEJNOŚĆ IMPLEMENTACJI

### Fala 1: "Daily Audit Ready" (najwyższy impact)
| # | Feature | Nakład | Impact |
|---|---------|--------|--------|
| 1 | **A1** Daily Audit Panel | Średni | 🔴 Krytyczny |
| 2 | **B1** Bulk Actions na Search Terms | Średni | 🔴 Krytyczny |
| 3 | **F2** Quick Optimization Scripts | Średni | 🔴 Krytyczny |
| 4 | **E1** Weekly Performance Report | Średni | 🟠 Wysoki |

### Fala 2: "Full Campaign Control"
| # | Feature | Nakład | Impact |
|---|---------|--------|--------|
| 5 | **A2** Change History Monitor | Średni | 🟠 Wysoki |
| 6 | **D1** PMax Channel Breakdown | Średni | 🟠 Wysoki |
| 7 | **D3** PMax vs Search Cannibalization | Średni | 🟠 Wysoki |
| 8 | **B3** Close Variant Analysis | Średni | 🟠 Wysoki |
| 9 | **G2** Keyword Expansion Suggestions | Średni | 🟠 Wysoki |

### Fala 3: "Deep Analysis"
| # | Feature | Nakład | Impact |
|---|---------|--------|--------|
| 10 | **A3** Conversion Tracking Health | Średni | 🟠 Wysoki |
| 11 | **E3** Account Health Report | Duży | 🟠 Wysoki |
| 12 | **G1** Auction Insights | Duży | 🟡 Średni |
| 13 | **C1** DSA Targets Analysis | Duży | 🟡 Średni |
| 14 | **B2** Search Terms Trend Analysis | Średni | 🟡 Średni |

### Fala 4: "Automation & Scale"
| # | Feature | Nakład | Impact |
|---|---------|--------|--------|
| 15 | **F1** Scheduled Sync & Alerts | Średni | 🟠 Wysoki |
| 16 | **F3** Automated Rules Engine | Duży | 🟡 Średni |
| 17 | **D2** Asset Group Performance | Duży | 🟡 Średni |
| 18 | **G5** Ad Extensions Audit | Duży | 🟡 Średni |
| 19 | **G3** Landing Page Audit | Duży | 🟡 Średni |

### Fala 5: "Polish & UX"
| # | Feature | Nakład | Impact |
|---|---------|--------|--------|
| 20 | **H1** Task Queue / Action Plan | Średni | 🟡 Średni |
| 21 | **G4** Cross-Campaign Analysis | Średni | 🟡 Średni |
| 22 | **E2** Monthly Deep Dive Report | Średni | 🟡 Średni |
| 23 | **H2** Benchmarks | Średni | 🟢 Nice-to-have |
| 24 | **H3** Keyboard Shortcuts | Mały | 🟢 Nice-to-have |
| 25 | **C2** DSA Headlines Audit | Średni | 🟢 Nice-to-have |
| 26 | **C3** DSA ↔ Search Overlap | Średni | 🟢 Nice-to-have |

---

## PODSUMOWANIE: CO JUŻ MAMY vs CZEGO BRAKUJE

### ✅ Mocne strony obecnej aplikacji:
- Solidna analityka: KPIs, trends, compare-periods, forecast
- Kompletna analiza keywords: QS audit, match type, wasted spend, n-gram
- Search terms: segmentacja, n-gram, rekomendacje
- RSA analysis z best/worst
- Anomaly detection (5 typów)
- 18 reguł rekomendacji
- Device/Geo/Dayparting breakdown
- Impression share tracking
- Budget pacing
- Action execution + revert + history
- AI Agent (Claude) do rozmów o danych

### ❌ Kluczowe luki:
1. **Brak "daily workflow" view** — dane są, ale rozrzucone po stronach
2. **Brak bulk actions** — specjalista musi aplikować rekomendacje po jednej
3. **Brak DSA support** — zero funkcji dla dynamicznych reklam
4. **PMax ograniczone do search terms** — brak channel breakdown i asset analysis
5. **Brak change history monitoring** — nie widać co Google zmienił w koncie
6. **Brak conversion tracking audit** — optymalizujemy potencjalnie na złych danych
7. **Brak gotowych raportów** — eksport jest, ale nie ma "kliknij i wyślij klientowi"
8. **Brak schedulingu** — sync manualny, alerty nie przychodzą proaktywnie
9. **Brak auction insights** — nie widać konkurencji
10. **Brak ad extensions audit** — rozszerzenia reklam to łatwy win, a nie są monitorowane

---

## ŹRÓDŁA

- [Google Ads Audit Checklist 2025 – Promodo](https://www.promodo.com/blog/google-ads-audit-checklist)
- [Google Ads Optimization Checklist 2026 – Vehnta](https://vehnta.com/google-ads-optimization-checklist-2026/)
- [Google Ads Scripts Worth Using 2026 – PPC.io](https://ppc.io/blog/google-ads-scripts)
- [21 Killer Google Ads Scripts – KlientBoost](https://www.klientboost.com/google/google-ads-scripts/)
- [Top PMax Optimization Tips 2026 – Search Engine Land](https://searchengineland.com/top-performance-max-optimization-tips-461913/)
- [Google Search Ads Audit 2026 – Search Engine Land](https://searchengineland.com/google-search-ads-require-different-audit-471457)
- [Google Ads API Change Event](https://developers.google.com/google-ads/api/docs/change-event)
- [PMax Asset Group Reporting – Google Developers](https://developers.google.com/google-ads/api/performance-max/asset-group-reporting)
- [PMax Channel Performance – Search Engine Land](https://searchengineland.com/google-channel-performance-report-pmax-campaigns-466298)
- [Adalysis PPC Audit Tools](https://adalysis.com/ppc-audit-analysis-tools/)
- [7 Best PPC Audit Tools 2026 – PPC.io](https://ppc.io/blog/ppc-audit-tools)
- [Google Ads API v23 Monthly Releases – Marc LaClear](https://marclaclear.com/google-ads-api-v23-releases/)
- [Google Ads Conversion Tracking 2026 – Groas.ai](https://groas.ai/post/google-ads-conversion-tracking-setup-2026-the-complete-guide-ga4-enhanced-conversions-consent-mode)
- [DSA Guide 2026 – WebAppick](https://webappick.com/google-dynamic-search-ads/)
- [Google Ads Optimization Schedule – Savvy Revenue](https://savvyrevenue.com/blog/adwords-optimization-calendar/)
