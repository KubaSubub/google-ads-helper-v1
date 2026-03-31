# Google Ads Expert Audit — Encyklopedyczny przegląd aplikacji

> **Audytor:** Symulowany specjalista Google Ads z 10+ lat doświadczenia w zarządzaniu kontami e-commerce (budżety 50k-500k zł/mies.)
> **Data:** 2026-03-28
> **Wersja aplikacji:** v1.0 (branch `ceo/ads-verify-sprint-2026-03-27`)
> **Klient testowy:** Sushi Naka Naka (client_id=3) / Demo Meble Sp. z o.o. (client_id=1)
> **Source of truth:** `google_ads_optimization_playbook.md`

---

## PART 0: EXECUTIVE SUMMARY

### Tabela ocen stron

| # | Strona | Relevance | Completeness | Value vs Google Ads UI | Actionability | Score /10 | Verdict |
|---|--------|-----------|-------------|----------------------|---------------|-----------|---------|
| 1 | Dashboard | HIGH | 7/10 | 7/10 — Health Score + Wasted Spend nie istnieją w Google Ads | 4/10 — read-only z linkami | **7.0** | KEEP |
| 2 | Daily Audit | CRITICAL | 8/10 | 9/10 — Quick Scripts to killer feature | 8/10 — bulk execute | **8.5** | KEEP |
| 3 | Campaigns | HIGH | 7/10 | 5/10 — Google Ads ma lepszy detail | 5/10 — role override + bidding target | **6.0** | IMPROVE |
| 4 | Keywords | CRITICAL | 8/10 | 7/10 — action hints + negative lists | 7/10 — pause/bid/negative actions | **7.5** | KEEP |
| 5 | Search Terms | CRITICAL | 8/10 | 9/10 — segmentacja + bulk ops | 9/10 — bulk add negative/keyword | **8.5** | KEEP |
| 6 | Search Optimization (CC) | HIGH | 9/10 | 9/10 — 35 sekcji analytics | 3/10 — prawie read-only | **7.0** | IMPROVE |
| 7 | Quality Score | CRITICAL | 7/10 | 8/10 — QS audit nie istnieje w Google Ads | 3/10 — read-only | **6.5** | IMPROVE |
| 8 | Recommendations | CRITICAL | 9/10 | 8/10 — 40+ reguł + context blocking | 9/10 — execute/dismiss/bulk | **8.5** | KEEP |
| 9 | Action History | IMPORTANT | 8/10 | 8/10 — unified timeline + revert | 7/10 — revert actions | **7.5** | KEEP |
| 10 | Alerts | IMPORTANT | 6/10 | 6/10 — z-score baseline | 3/10 — resolve only | **5.5** | IMPROVE |
| 11 | Reports | NICE | 5/10 | 4/10 — Google Ads Reports lepsze | 2/10 — generate only | **4.0** | REDESIGN |
| 12 | Agent (AI) | NICE | 4/10 | 5/10 — natural language queries | 3/10 — chat only | **4.0** | IMPROVE |
| 13 | Forecast | NICE | 4/10 | 3/10 — linear regression = zbyt prymitywne | 1/10 — read-only | **3.5** | REDESIGN |
| 14 | Semantic | IMPORTANT | 5/10 | 8/10 — clustering nie istnieje w Google Ads | 5/10 — bulk add negatives | **6.0** | IMPROVE |
| 15 | Settings | IMPORTANT | 7/10 | 7/10 — safety limits + business context | 6/10 — full CRUD | **7.0** | KEEP |

**Średnia:** 6.4/10

---

### TOP 5 mocnych stron (co bije Google Ads UI)

1. **Search Terms Segmentation + Bulk Ops** — Google Ads wymaga ręcznego przeglądania; tu masz instant segment (HIGH_PERFORMER / WASTE / IRRELEVANT) + bulk add negative/keyword. To oszczędza 2-3h tygodniowo na koncie z 500+ search terms.

2. **Recommendations Engine z 40+ regułami + Context Blocking** — Google Ads ma "Recommendations" ale są generyczne i często szkodliwe. Tu masz playbook-aligned rules z confidence/risk scoring i blocking reasons. Specjalista widzi DLACZEGO coś jest zablokowane — to rewolucja.

3. **Daily Audit Quick Scripts** — "Clean Waste", "Pause Burning", "Boost Winners" z dry-run preview. Google Ads nie ma niczego podobnego. To jest morning routine w 5 minut zamiast 30.

4. **Quality Score Audit** — Google Ads pokazuje QS per keyword ale nie ma widoku audytowego (rozkład, issue breakdown, spend on low QS). Tu masz pełny obraz zdrowia QS konta.

5. **Search Optimization Command Center (35 sekcji)** — Dayparting, N-gram, RSA analysis, Match Type analysis, Smart Bidding readiness, PMax channels, Auction Insights — wszystko w jednym miejscu. W Google Ads to 15 różnych raportów.

---

### TOP 5 krytycznych luk

1. **Brak Ad Copy Management** — Playbook wymaga: "Pause ads with CTR < 50% of best performer", testowanie wariantów RSA, A/B testing headlines. Apka nie ma strony do zarządzania reklamami (tworzenie, edycja, pauzowanie, A/B test).

2. **Brak Budget Reallocation Workflow** — Playbook: "Move from low ROAS to high ROAS campaigns". Jest analiza (scaling opportunities, pareto), ale nie ma UI do masowego przesunięcia budżetów między kampaniami.

3. **Brak Landing Page Testing/Integration** — Playbook: "Landing page analysis monthly". SearchOptimization ma sekcję Landing Pages ale jest read-only, nie integruje się z GA4 ani nie sugeruje zmian.

4. **Search Optimization jest read-only monolitem** — 35 sekcji analitycznych ale prawie żadnych akcji. Specjalista widzi problem, ale musi iść do innej strony żeby coś zrobić. Brakuje inline actions.

5. **Brak Audience Management** — Playbook: "Audience analysis by demographics, devices, locations" weekly. Jest analiza (demographics, audience performance) ale nie ma audience CRUD, bid adjustments per audience, ani remarketing list management.

---

### Kill List (co usunąć lub drastycznie przerobić)

| Element | Strona | Powód |
|---------|--------|-------|
| Forecast (linear regression) | Forecast | R² = 0.00 na screenshocie. Linear regression na danych Google Ads to żart. Albo zastąpić Prophet/ARIMA albo usunąć. |
| Reports (AI narrative) | Reports | "Brak zapisanych raportów" — wymaga Claude CLI auth, zbyt niezawodne. Google Ads ma Reports i Looker Studio. Nie konkuruj. |
| Agent (AI chat) | Agent | Ciekawy eksperyment ale niezawodny. Lepiej zainwestować czas w inline actions na istniejących stronach. |

---

### Missing Features (czego nie ma nigdzie w apce a playbook wymaga)

| Feature | Playbook Reference | Priority | Opis |
|---------|-------------------|----------|------|
| Ad Copy Management | §1 Weekly: "Ad copy testing" | P0 | Tworzenie, edycja, A/B test RSA, pauzowanie słabych ads |
| Budget Reallocation UI | §1 Weekly: "Budget reallocation" | P0 | Masowe przesunięcie budżetów z low-ROAS do high-ROAS |
| Competitor Dashboard | §1 Monthly: "Competitor analysis (Auction Insights)" | P1 | Dedykowana strona z trendami IS vs competitors |
| Attribution Analysis | §1 Monthly: "Attribution analysis" | P1 | Model attribution, ścieżki konwersji, assisted conversions |
| Landing Page Optimization | §1 Monthly: "Landing page analysis" | P1 | GA4 integration, bounce rate, page speed, sugestie |
| Automated Rules Engine | §6 v2: "Automated rules engine" | P2 | User-defined rules (IF metric > threshold THEN action) |
| Ad Copy Generation AI | §6 v2: "AI-powered ad copy generation" | P2 | Generowanie headlines/descriptions z AI |
| Device Bid Adjustments | §1 Weekly: "Audience analysis by devices" | P1 | UI do modyfikacji bid modifiers per device |
| Location Bid Adjustments | §1 Weekly: "Audience analysis by locations" | P1 | UI do modyfikacji bid modifiers per location |
| Scheduling (Ad Schedule) | §4: Dayparting | P2 | Ustawianie ad schedule na podstawie dayparting analysis |

---

## PART 1: METODOLOGIA

### Rating System

| Rating | Znaczenie | Kryterium |
|--------|-----------|-----------|
| **CRITICAL** | Must-have dla specjalisty Google Ads | Bez tego nie da się efektywnie zarządzać kontem |
| **IMPORTANT** | Bardzo przydatne, oszczędza czas | Specjalista używa tego 1-5x/tydzień |
| **NICE** | Miło mieć, ale nie essentialne | Alternatywa istnieje w Google Ads UI |
| **USELESS** | Nie wnosi wartości | Specjalista to ignoruje |

### Verdict System

| Verdict | Znaczenie |
|---------|-----------|
| **KEEP** | Gotowe do użytku, drobne poprawki |
| **IMPROVE** | Solidna baza, wymaga konkretnych usprawnień |
| **REDESIGN** | Koncepcja OK, ale wykonanie wymaga przebudowy |
| **REMOVE** | Nie wnosi wartości, zabiera uwagę |

### Cross-reference notation

- `[PB §1.D]` = Playbook, Część 1, Daily tasks
- `[PB §2.M]` = Playbook, Część 2, Metrics & Thresholds
- `[PB §4.1]` = Playbook, Część 4.1, Search Terms Intelligence
- `[PB §5]` = Playbook, Część 5, Advanced Features

### Actionability classification

- **READ-ONLY** — Element wyświetla dane, nie ma żadnych akcji
- **HAS ACTIONS** — Element umożliwia wykonanie operacji (bid change, pause, add negative, etc.)
- **NAVIGATES** — Element linkuje do strony z akcjami

---

## PART 2: AUDYT STRONA PO STRONIE

---

### 2.1 DASHBOARD

**Score: 7.0/10 | Verdict: KEEP | Playbook: §1.D (Daily monitoring)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Dashboard | Status |
|--------------|-------------------|--------|
| Budget monitoring (spend > 150% avg) | HealthScoreCard + Budget Pacing | ✅ COVERED |
| Anomaly detection (CTR drops, CPC spikes) | HealthScoreCard issues list | ✅ COVERED |
| Zero conversions alert | HealthScoreCard (może wykryć) | ⚠️ PARTIAL — nie jest explicit |
| Search Terms Review | Wasted Spend KPI card → link do SearchTerms | ✅ COVERED (nawigacja) |
| Pause poor performers | Nie ma — wymaga przejścia do Keywords | ❌ MISSING |
| Performance comparison WoW | WoWChart component | ✅ COVERED |
| Quality Score tracking | QS Health Widget (avg QS, low count, spend %) | ✅ COVERED |

#### Element-by-element audit

**1. Health Score Card (circular gauge 0-100)**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.D] — anomaly detection, budget monitoring
- Expert opinion: Doskonały element. Google Ads nie ma niczego podobnego. Health Score agreguje alerty w jedną cyfrę — specjalista w 1 sekundę wie czy konto jest OK.
- What's good: Klikalny → Alerts page; issues list z severity; budget pacing alert w środku
- What's wrong: Score = 50/100 na screenshocie ale nie wiadomo jak jest kalkulowany. Brak transparency = brak zaufania.
- Fix: Dodaj tooltip "Jak obliczamy Health Score" z wagami per kategoria (budget: 30%, conversions: 25%, QS: 20%, waste: 15%, IS: 10%)
- Priority: **P2**
- Actionability: NAVIGATES (→ Alerts)

**2. KPI Cards Row 1 (Clicks, Cost, Conversions, ROAS)**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — Key Performance Metrics
- Expert opinion: Standard, poprawnie zrobione. % change vs previous period to must-have.
- What's good: 4 najważniejsze metryki na wierzchu; color-coded change (green/red); inverted logic for Cost (red = up)
- What's wrong: Brak sparklines. Same cyfry bez kontekstu trendu za 7/30 dni.
- Fix: Dodaj miniaturowy sparkline (7-day trend) pod każdym KPI. Wzorzec: `<LineChart width={72} height={24}>` (już istnieje w codebase)
- Priority: **P2**
- Actionability: READ-ONLY

**3. KPI Cards Row 2 (Impressions, CTR, CPA, Wasted Spend)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §2.M] — metrics; [PB §4.1] — waste
- Expert opinion: Wasted Spend card to złoto — bezpośredni link do SearchTerms z filtrem WASTE. CPA z inverted logic poprawne.
- What's good: Wasted Spend klikalny → SearchTerms?segment=WASTE; CPA inverted (red = higher cost)
- What's wrong: Impressions i CTR nie są actionable. Zajmują miejsce a nic nie wnoszą.
- Fix: Zamień Impressions na "Impression Share" (bardziej actionable — niski IS = zwiększ budget/bid). CTR zostaw.
- Priority: **P3**
- Actionability: NAVIGATES (Wasted Spend only)

**4. QS Health Widget**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.3] — Quality Score Optimization
- Expert opinion: Fantastyczny widget. "4 słów z niskim QS + 23% budżetu" — to od razu mówi specjaliście: "masz problem z QS i marnujesz 23% kasy".
- What's good: Avg QS, low QS count, low QS spend % — kompaktowe 3 metryki; klikalny → QualityScore
- What's wrong: Nic istotnego. Mógłby mieć trend arrow (QS w górę/dół vs tydzień temu).
- Fix: Dodaj trend indicator (↑↓→) obok avg QS
- Priority: **P3**
- Actionability: NAVIGATES (→ QualityScore)

**5. InsightsFeed component**
- Rating: **IMPORTANT**
- Playbook ref: [PB §5] — Automated Recommendations Engine
- Expert opinion: "2 nowe insighty" na screenshocie — ale co to za insighty? Jeśli to linki do recommendations to OK. Jeśli to generic "your CTR dropped" to USELESS.
- What's good: Kompaktowe powiadomienia na dashboardzie
- What's wrong: Brak widoczności co to za insighty bez kliknięcia. Powinien być mini-preview.
- Fix: Pokaż 1-2 linie tekstu per insight zamiast tylko badge z liczbą
- Priority: **P2**
- Actionability: NAVIGATES

**6. TrendExplorer component**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — Performance comparison (Last 7d vs Previous 7d)
- Expert opinion: Solidna wizualizacja trendów. Dual-axis chart z filtrowaniem po kampaniach.
- What's good: Multi-metric overlay; period comparison; campaign filtering
- What's wrong: Na dashboardzie jest za duży. Dashboard powinien być scannable w 10 sekund. TrendExplorer to deep-dive tool.
- Fix: Domyślnie collapsed, expandable. Lub przenieś do Campaigns page.
- Priority: **P3**
- Actionability: READ-ONLY

**7. WoWChart (Week-over-Week comparison)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — Weekly comparison
- Expert opinion: Must-have dla weekly check. Porównanie tydzień do tygodnia to bread-and-butter optimization.
- What's good: Clear visual comparison; highlights positive/negative changes
- What's wrong: Powinien mieć wybór metryk (teraz pewnie hardcoded set)
- Fix: Dodaj metric selector (clicks/cost/conversions/ROAS)
- Priority: **P2**
- Actionability: READ-ONLY

**8. Campaign Table**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.D] — daily campaign overview
- Expert opinion: Standardowa tabela. Sortowanie po cost, conversions, ROAS — standard.
- What's good: Sortable; sparkline trends; filterable by type/status; link to campaign detail
- What's wrong: Brak inline actions. Specjalista widzi kampanię z zerowym ROAS ale musi klikać 3 razy żeby ją zapauzować.
- Fix: Dodaj inline "Pause" button dla kampanii z 0 conversions i cost > threshold
- Priority: **P1**
- Actionability: NAVIGATES (→ Campaigns)

#### Missing from playbook on Dashboard

| Playbook Task | Status |
|--------------|--------|
| Device breakdown summary | ✅ Loaded via API (getDeviceBreakdown) ale nie widoczne na screenshocie |
| Geographic breakdown summary | ✅ Loaded via API (getGeoBreakdown) ale nie widoczne |
| Recent actions feed | ✅ getActionHistory(limit:5) loaded |
| PMax channels | ✅ getPmaxChannels loaded |

Dashboard ładuje dużo danych ale nie wszystkie są widoczne. To dobrze — lepiej mieć dane ready niż lazy-load.

---

### 2.2 DAILY AUDIT (Poranny Przegląd)

**Score: 8.5/10 | Verdict: KEEP | Playbook: §1.D (Daily routine, core feature)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Daily Audit | Status |
|--------------|----------------------|--------|
| Budget monitoring (spend > 150% avg) | KPI chips + critical alerts | ✅ COVERED |
| Anomaly detection | Critical/Medium/Low alerts section | ✅ COVERED |
| Search Terms Review | Quick Script: "Clean Waste" | ✅ COVERED |
| Pause poor performers | Quick Script: "Pause Burning" | ✅ COVERED |
| Zero conversions identification | Alert: "Brak konwersji: PMax" | ✅ COVERED |
| Daily time check (15-30 min) | Designed for 5-minute scan | ✅ EXCEEDED |

#### Element-by-element audit

**1. KPI Chips (6 cards: Cost, Clicks, Conversions, CPA, ROAS, Health Score)**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.D] — daily monitoring metrics
- Expert opinion: Doskonałe. 6 metryki w jednym rzędzie z % change. Specjalista skanuje w 3 sekundy.
- What's good: Compact; % change with color coding; covers all daily-check metrics
- What's wrong: Na screenshocie "0 zł, -100%, 0 kliknięć, -100%" — albo dane z dzisiaj (nie ma jeszcze danych) albo seed data problem. W prodzie może zmylić usera.
- Fix: Jeśli dane = 0 for today, pokaż "Brak danych za dziś — pokazuję wczoraj" z auto-fallback
- Priority: **P1**
- Actionability: READ-ONLY

**2. Critical Alerts Section**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.D] — anomaly detection
- Expert opinion: "6 alertów wymaga uwagi" z podziałem na severity — idealne. Specjalista wie co gasić first.
- What's good: Severity-based grouping; clear call-to-action; campaign-specific alerts
- What's wrong: Alert texts powinny mieć impact (ile to kosztuje). "Nagły wzrost kosztów: Łóżka" — ile? 100 zł czy 5000 zł?
- Fix: Dodaj estimated impact (zł) do każdego alertu
- Priority: **P1**
- Actionability: READ-ONLY (brak "resolve" inline)

**3. Quick Script: "Wyczyść śmieci" (Clean Waste)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — Search Terms waste elimination
- Expert opinion: **KILLER FEATURE**. Jedno kliknięcie → wyczyść waste search terms + ads. Z dry-run preview. To oszczędza 30-60 minut tygodniowo na średnim koncie.
- What's good: Dry-run first → confirm → execute; shows applied/failed/skipped counts; estimated savings
- What's wrong: Brak granularity — "wyczyść wszystko" nie zawsze jest dobry pomysł. Specjalista chce widzieć LISTĘ co będzie wyczyszczone PRZED kliknięciem.
- Fix: Dry-run powinien pokazać tabelę z każdym elementem do wyczyszczenia + checkbox per item
- Priority: **P1**
- Actionability: **HAS ACTIONS** (execute scripts)

**4. Quick Script: "Pauzuj spalające" (Pause Burning)**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — "PAUSE keyword: Spend > $50 & Conversions = 0"
- Expert opinion: Bezpośrednia implementacja reguły z playbooka. Perfekcyjne.
- What's good: Threshold-based (> $50, 0 conversions); dry-run; batch operation
- What's wrong: Threshold $50 powinien być configurable per client (Settings)
- Fix: Czytaj threshold z Settings → safety limits zamiast hardcode
- Priority: **P2**
- Actionability: **HAS ACTIONS**

**5. Quick Script: "Boost winnerów" (Boost Winners)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §2.M] — "INCREASE bid: CVR > Avg × 1.2 & CPA < Target × 0.8"
- Expert opinion: Dobry koncept ale ryzykowny. Automatyczne bid increases bez kontekstu (Learning period? Budget cap?) mogą narobić szkód.
- What's good: Identifies high-ROAS campaigns; suggests bid increase
- What's wrong: Brak kontekstu Smart Bidding — jeśli kampania jest na Target ROAS, bid increase jest ignorowany przez Google. Script powinien to wiedzieć.
- Fix: Filtruj: boost only Manual CPC / eCPC campaigns; skip Smart Bidding campaigns z warning
- Priority: **P1**
- Actionability: **HAS ACTIONS**

**6. Quick Script: "Hamulec awaryjny" (Emergency Brake)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.D] — Budget monitoring (spend > 150% avg)
- Expert opinion: Dobry safety net. W sytuacji kryzysowej (hacked account, runaway budget) to jest must-have.
- What's good: One-click pause all; threshold-based activation
- What's wrong: "Pause all campaigns" to NUCLEAR OPTION. Powinien być recovery plan — jak wznowić po emergency brake?
- Fix: Po emergency brake → log event + alert "Kampanie zapauzowane awaryjnie — kliknij aby wznowić" (revert functionality)
- Priority: **P2**
- Actionability: **HAS ACTIONS**

**7. Recommendation Summary (60 pending)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §5] — Automated Recommendations Engine
- Expert opinion: "60 oczekujących rekomendacji" z podziałem na typ (Obniż stawkę: 7 HIGH, QS Alert: 4 HIGH) — specjalista wie co robić.
- What's good: Priority-ordered; category breakdown; count per type; HIGH priority flagging
- What's wrong: Brak "Apply top 5 HIGH" batch action inline. Specjalista musi iść do Recommendations page.
- Fix: Dodaj "Apply all HIGH priority" button z dry-run inline
- Priority: **P1**
- Actionability: NAVIGATES (→ Recommendations)

---

### 2.3 CAMPAIGNS

**Score: 6.0/10 | Verdict: IMPROVE | Playbook: §1.W (Weekly campaign review)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Campaigns | Status |
|--------------|---------------------|--------|
| Performance comparison 7d vs 7d | KPI cards z % change | ✅ COVERED |
| Keyword bid adjustments | Link do Keywords per campaign | ⚠️ PARTIAL — nawigacja, nie inline |
| Budget reallocation | Brak UI do mass budget change | ❌ MISSING |
| Impression Share management | IS metrics w KPI + detail | ✅ COVERED |
| Campaign role classification | Auto-detection + manual override | ✅ COVERED |
| Device performance analysis | Device Breakdown expandable | ✅ COVERED |
| Geo performance analysis | Geographic Breakdown | ✅ COVERED |

#### Element-by-element audit

**1. Campaign List (left panel)**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.W] — weekly campaign overview
- Expert opinion: Master-detail layout (lista + panel) to dobry wzorzec. Sortowanie po Cost — standard.
- What's good: Sortable; shows Type + Budget + Key metrics (cost, conversions, ROAS); status indicators
- What's wrong: Lista ma 5 kampanii na screenshocie — co z kontami z 50+ kampanii? Brak search, brak grupowania po typie.
- Fix: Dodaj campaign search input w liście; dodaj grouping by campaign_type (collapsible)
- Priority: **P2**
- Actionability: NAVIGATES (→ campaign detail)

**2. Campaign Detail Panel (right)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — detailed campaign review
- Expert opinion: Solidny detail. 8 KPIs z % change, linki do Keywords i Search Terms.
- What's good: Quick nav to Keywords/Search Terms per campaign; role classification visible; bidding strategy badge
- What's wrong: Brak akcji. Specjalista widzi kampanię z CPA 200% over target ale nie może nic zrobić — no pause, no budget change, no bid adjust.
- Fix: Dodaj action buttons: Pause Campaign, Change Budget (slider), Change Bidding Target
- Priority: **P0**
- Actionability: READ-ONLY (poza role override)

**3. CampaignTrendExplorer (chart)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §3] — weekly performance tracking
- Expert opinion: Dual-axis chart z correlation indicator (Pearson r) — zaawansowane. Lepsze niż Google Ads.
- What's good: Multi-metric overlay; correlation calculation; action events on timeline; reference lines
- What's wrong: 5-metric limit jest dobry. Ale brak highlight anomalies on chart (spike/dip markers).
- Fix: Dodaj anomaly markers (red dots) na outlier data points (z-score > 2)
- Priority: **P3**
- Actionability: READ-ONLY

**4. Campaign Role Classification**
- Rating: **NICE**
- Playbook ref: No direct playbook reference
- Expert opinion: Auto-detection (BRAND, GENERIC, PROSPECTING, REMARKETING, PMAX) to nice-to-have. Pomaga w budget allocation ale nie jest standard w branży.
- What's good: Auto-detection; manual override; protection level concept
- What's wrong: Protection level (HIGH/MEDIUM/LOW) nie jest jasne co robi. Czy blokuje pauzowanie? Czy to safety limit?
- Fix: Dodaj tooltip wyjaśniający co protection level oznacza w praktyce
- Priority: **P3**
- Actionability: HAS ACTIONS (role override, protection level)

**5. Device Breakdown**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — "Audience analysis by devices"
- Expert opinion: Desktop/Mobile/Tablet breakdown ze wszystkimi metrykami — standard. Ale brak bid adjustments.
- What's good: Complete metrics per device (clicks, impressions, cost, conversions)
- What's wrong: READ-ONLY. Specjalista widzi że Mobile ma CPA 3x wyższe ale nie może ustawić bid modifier -50% na Mobile.
- Fix: Dodaj bid modifier controls per device (slider -100% to +300%)
- Priority: **P1**
- Actionability: READ-ONLY

**6. Geographic Breakdown**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — "Audience analysis by locations"
- Expert opinion: Identyczny problem jak Device — read-only.
- What's good: Complete metrics per location
- What's wrong: Brak bid modifier controls per location
- Fix: Dodaj location bid modifier controls
- Priority: **P1**
- Actionability: READ-ONLY

**7. Budget Pacing**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.D] — Budget monitoring
- Expert opinion: "29% underspend at 90% of month" — to alert. Ale czy jest widoczny? Na screenshocie widać to w HealthScore.
- What's good: Progress bar per campaign; status coloring (on_track/underspend/overspend)
- What's wrong: Brak inline budget adjustment. Widzisz underspend → chcesz zwiększyć budget → musisz to zrobić w Google Ads.
- Fix: Dodaj quick budget adjust button (±10%, ±25%, custom) obok każdej kampanii
- Priority: **P0**
- Actionability: READ-ONLY

---

### 2.4 KEYWORDS

**Score: 7.5/10 | Verdict: KEEP | Playbook: §2.M, §4.3 (bid management, QS)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Keywords | Status |
|--------------|-------------------|--------|
| Keyword bid adjustments | Action hints (Bid Up/Down) + buttons | ✅ COVERED |
| Pause poor performers (Spend>$50, 0 conv) | Action hint "Pause" | ✅ COVERED |
| Quality Score per keyword | QS badge (color-coded) | ✅ COVERED |
| Negative keyword management | Dedicated Negatives tab + lists | ✅ COVERED |
| Match type analysis | Match type filter (EXACT/PHRASE/BROAD) | ✅ COVERED |
| Serving status monitoring | Serving status badge | ✅ COVERED |
| Impression share per keyword | IS % column | ✅ COVERED |

#### Element-by-element audit

**1. Positive Keywords Table**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — all keyword metrics
- Expert opinion: Kompletna tabela. Keyword, Campaign, Match Type, Clicks, Impressions, Cost, Conversions, CTR, Avg CPC, QS, Status, ROAS, IS — to prawie wszystko co trzeba.
- What's good: Full metric coverage; sortable; paginated (50/page); campaign filter; match type filter; export CSV/XLSX
- What's wrong: (1) Brak kolumny "Conversion Value" — ROAS bez CV jest nieprzejrzysty. (2) Brak kolumny "CPA" — muszę liczyć w głowie.
- Fix: Dodaj kolumny Conversion Value i CPA (lub toggle "show extended metrics")
- Priority: **P2**
- Actionability: HAS ACTIONS (pause, bid up, bid down)

**2. Action Hints (Pause, Bid Up, Bid Down)**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — Decision Rules
- Expert opinion: Dokładna implementacja playbook rules. Cost > 50 + 0 conv + ≥10 clicks = Pause. ≥5 conv + CVR > 5% = Bid Up. To rewelacja.
- What's good: Context-sensitive (shows only when applicable); clear thresholds; direct action buttons
- What's wrong: Thresholds hardcoded. Branża meblowa ma inne thresholds niż SaaS. Settings safety limits powinny je kontrolować.
- Fix: Czytaj thresholds z client Settings (min_roas, max_daily_budget) lub dodaj "Keyword Rules" section w Settings
- Priority: **P1**
- Actionability: **HAS ACTIONS**

**3. QS Badge (color-coded per keyword)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.3] — Quality Score Optimization
- Expert opinion: 1-3 red, 4-6 yellow, 7-10 green — standard. Ale brak sub-component display inline (Expected CTR, Ad Relevance, Landing Page).
- What's good: Instant visual QS assessment; click navigates to QualityScore page
- What's wrong: Sub-components dostępne dopiero na QualityScore page. Specjalista chce widzieć je inline.
- Fix: Dodaj tooltip na QS badge z 3 sub-components (dots: below avg, avg, above avg)
- Priority: **P2**
- Actionability: NAVIGATES (→ QualityScore)

**4. Negative Keywords Tab**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — Negative keyword management
- Expert opinion: Kompletna sekcja. Add modal, scope filter (Campaign/Ad Group), match type, search, show removed, negative keyword LISTS with apply functionality.
- What's good: Full CRUD; list management (create, add items, apply to campaigns); scope management; duplicate detection
- What's wrong: Brak "suggested negatives" based on search terms analysis. User musi sam wiedzieć co dodać.
- Fix: Dodaj "Suggested Negatives" section na górze (from SearchTerms WASTE segment)
- Priority: **P1**
- Actionability: **HAS ACTIONS** (full CRUD + list management)

**5. Keyword Expansion Section**
- Rating: **NICE**
- Playbook ref: [PB §4.1] — keyword discovery
- Expert opinion: Related keywords i eCPC recommendations — ciekawe ale mało wartościowe bez Google Keyword Planner data.
- What's good: Concept of expansion from existing keywords
- What's wrong: Bazuje na wewnętrznych danych, nie na Google Keyword Planner. Sugestie mogą być nieadekwatne.
- Fix: Oznacz jako "Based on account data" i dodaj disclaimer
- Priority: **P3**
- Actionability: READ-ONLY

**6. Export (CSV/XLSX)**
- Rating: **IMPORTANT**
- Playbook ref: No direct ref — operational necessity
- Expert opinion: Must-have dla raportowania do klienta. Standard.
- What's good: Both formats; includes all visible columns
- What's wrong: Brak custom column selection. Export all or nothing.
- Fix: Low priority — current implementation sufficient
- Priority: **P3**
- Actionability: HAS ACTIONS (export)

---

### 2.5 SEARCH TERMS

**Score: 8.5/10 | Verdict: KEEP | Playbook: §4.1 (Search Terms Intelligence — core feature)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Search Terms | Status |
|--------------|----------------------|--------|
| Identify negative words | Segments: WASTE + IRRELEVANT | ✅ COVERED |
| Identify high-performing terms | Segments: HIGH_PERFORMER | ✅ COVERED |
| Semantic clustering | Variants view + Semantic page | ✅ COVERED |
| Bulk operations | Bulk add negative/keyword | ✅ COVERED |
| Trend monitoring | Trends view | ✅ COVERED |
| Close variant analysis | Variants view | ✅ COVERED |

#### Element-by-element audit

**1. Segment View (4 cards: Top Performers, Waste, Irrelevant, Other)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — Search Terms segmentation
- Expert opinion: **BEST FEATURE IN THE APP**. Instant segmentacja — specjalista widzi 23 top performers, X waste, 1 irrelevant, 27 other. W Google Ads to wymagałoby ręcznego filtrowania 100+ search terms.
- What's good: Color-coded cards; count per segment; waste cost callout ("Zmarnowany budżet X zł — Y% spend"); filterable tables per segment; inline actions
- What's wrong: Segmentation rules nie są widoczne. Co definiuje "Waste"? Clicks > 5 & conversions = 0? Specjalista powinien widzieć i móc modyfikować progi.
- Fix: Dodaj "Segment Rules" icon z tooltip showing thresholds per segment
- Priority: **P2**
- Actionability: NAVIGATES (→ per-segment actions)

**2. Waste Callout Banner**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — Waste identification
- Expert opinion: "Zmarnowany budżet 287 zł — 0.7% spend" — instant visibility. To powinno być na Dashboard too.
- What's good: Prominent placement; absolute + relative values
- What's wrong: 0.7% is low — but is 287 zł a lot for this account? Brak kontekstu (daily budget, monthly spend).
- Fix: Dodaj kontekst: "287 zł = X dni budżetu kampanii Y"
- Priority: **P3**
- Actionability: READ-ONLY

**3. Bulk Action Bar (sticky)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — One-click actions on search terms
- Expert opinion: Select terms → bulk add as negatives (EXACT, CAMPAIGN) lub bulk add as keywords (with ad group picker). Dokładnie to co specjalista potrzebuje.
- What's good: Sticky bar (stays visible); shows selected count; two bulk actions; AdGroup picker for keyword addition; match type selection
- What's wrong: Match type defaultuje do EXACT. Dla negatives OK, ale dla keywords dodawanie wszystkiego jako EXACT to zbyt restrykcyjne.
- Fix: Dla "Add as Keywords" — sugeruj match type per term based on performance (high volume = PHRASE, niche = EXACT)
- Priority: **P2**
- Actionability: **HAS ACTIONS** (bulk add negative, bulk add keyword)

**4. List View (tabela z search, sort, pagination)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.1] — Term-level analysis
- Expert opinion: Standard data table. Search, sort, pagination — all correct.
- What's good: All key metrics (Clicks, Impressions, Cost, Conversions, CTR, CVR, Segment); searchable; sortable
- What's wrong: Brak "Reason" column explaining WHY a term is in its segment. Na screenshocie widać "Niewystarczające dane" — to dobry start.
- Fix: Already has reason column — verify it's populated for all segments
- Priority: **P3**
- Actionability: HAS ACTIONS (per-row add negative/keyword)

**5. Trends View (line chart)**
- Rating: **NICE**
- Playbook ref: [PB §3] — Trend monitoring
- Expert opinion: Przydatne do identyfikacji sezonowości search terms. Ale niszowe.
- What's good: Time series of search term volume/cost
- What's wrong: Aggregate trend czy per-term? Jeśli aggregate to mało wartościowe.
- Fix: Allow selecting individual terms for comparison
- Priority: **P3**
- Actionability: READ-ONLY

**6. Variants View (close variant analysis)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.1] — Close variant grouping
- Expert opinion: Google Ads increasingly matches close variants. Widzenie "łóżko drewniane" vs "drewniane łóżko" vs "łóżka drewniane" z porównaniem performance — very useful.
- What's good: Groups variants together; shows performance comparison
- What's wrong: Brak actionability. Co z tym zrobię? Potrzebuję "Consolidate — add exact match for best performer, negative for rest"
- Fix: Dodaj "Consolidate Variants" action — picks best performer as keyword, rests as negatives
- Priority: **P1**
- Actionability: READ-ONLY

---

### 2.6 SEARCH OPTIMIZATION (Command Center)

**Score: 7.0/10 | Verdict: IMPROVE | Playbook: Comprehensive coverage of §1-§5**

#### Playbook Alignment Matrix

| Playbook Task | Sekcja w Command Center | Status |
|--------------|------------------------|--------|
| Budget monitoring | Wasted Spend section | ✅ COVERED |
| Dayparting analysis | Dayparting + Hourly Dayparting | ✅ COVERED |
| Match type analysis | Match Type Analysis section | ✅ COVERED |
| N-gram analysis | N-Gram Analysis section | ✅ COVERED |
| RSA analysis | RSA Analysis section | ✅ COVERED |
| Landing page analysis | Landing Pages section | ✅ COVERED |
| Account structure audit | Account Structure section | ✅ COVERED |
| Bidding strategy | Bidding Strategy Analysis | ✅ COVERED |
| Conversion tracking health | Conversion Health section | ✅ COVERED |
| Ad group health | Ad Group Health section | ✅ COVERED |
| Smart Bidding readiness | Smart Bidding Readiness | ✅ COVERED |
| Scaling opportunities | Scaling Opportunities | ✅ COVERED |
| PMax channels | PMax Channels + Trends | ✅ COVERED |
| Demographics | Demographics section | ✅ COVERED |
| Auction Insights | Auction Insights section | ✅ COVERED |
| Missing extensions | Missing Extensions section | ✅ COVERED |
| Shopping product groups | Shopping Product Groups | ✅ COVERED |

**Coverage: 35/35 sekcji — COMPLETE playbook coverage**

#### Element-by-element audit

**1. Overview Grid (cards with status indicators)**
- Rating: **CRITICAL**
- Playbook ref: All sections
- Expert opinion: Grid kart z green/red/blue indicators — genialny wzorzec. "3 problemy wymagają uwagi: Strategia bidowania, Jakość konwersji, Smart Bidding" — specjalista wie od razu.
- What's good: Status-at-glance (green=OK, red=problem, blue=info); problem count; one-click expand to section
- What's wrong: 35 sekcji to za dużo. Information overload. Specjalista nie wie od czego zacząć.
- Fix: Dodaj priority sorting — problemy (red) na górze, OK (green) na dole. Lub filter "Show problems only"
- Priority: **P0**
- Actionability: NAVIGATES (→ expanded sections)

**2. Wasted Spend Section**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.1] — Waste elimination
- Expert opinion: "287 zł (0.7%)" z rozbiciem na kategorie (keywords: 208 zł, ads: 79 zł) — excellent.
- What's good: Category breakdown; individual items with cost; inline add negative action
- What's wrong: "Add negative" to jedyna akcja. Brak "Pause keyword" inline, brak "Pause ad" inline.
- Fix: Dodaj inline Pause buttons obok każdego wasted keyword/ad
- Priority: **P1**
- Actionability: HAS ACTIONS (add negative only)

**3. Dayparting (Day of Week)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §3] — Time-based optimization
- Expert opinion: Day-of-week bars (clicks, conversions, CPA), weekend highlighting — standard i przydatne.
- What's good: Visual bars; CPA by day; weekend differentiation
- What's wrong: READ-ONLY. Specjalista widzi że sobota ma 3x wyższe CPA ale nie może ustawić ad schedule.
- Fix: Dodaj "Apply Ad Schedule" action — suggest bid modifiers per day based on CPA pattern
- Priority: **P2**
- Actionability: READ-ONLY

**4. Hourly Dayparting**
- Rating: **NICE**
- Playbook ref: [PB §3] — Hour-level optimization
- Expert opinion: 24-hour breakdown — useful for B2B (wyłącz 22:00-06:00) ale niszowe.
- What's good: Granular time analysis
- What's wrong: Same problem — read-only, no ad schedule setting
- Fix: Combine with day-of-week into heatmap (day × hour) + suggest schedule
- Priority: **P3**
- Actionability: READ-ONLY

**5. Match Type Analysis**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — Match type performance
- Expert opinion: Tabela EXACT/PHRASE/BROAD × all metrics (clicks, cost, conversions, CTR, CPC, CPA, CVR, ROAS, cost share %) — comprehensive.
- What's good: Full metric matrix; cost share % shows budget distribution; identifies underperforming match types
- What's wrong: Brak recommendation. "BROAD has 40% of cost but 10% of conversions" → should suggest "Consider reducing BROAD spend"
- Fix: Dodaj inline insights per match type based on ROAS comparison
- Priority: **P2**
- Actionability: READ-ONLY

**6. N-Gram Analysis**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.1] — Search term intelligence
- Expert opinion: 1-gram/2-gram/3-gram analysis z metrykami — Google Ads nie ma tego. Identyfikacja waste patterns ("darmowe", "jak", "czy").
- What's good: Size toggle; sortable; frequency + cost; identifies waste n-grams
- What's wrong: Brak "Add as negative" button per n-gram
- Fix: Dodaj inline "Add as Negative" per n-gram (creates negative for each n-gram)
- Priority: **P1**
- Actionability: READ-ONLY

**7. RSA Analysis**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.W] — "Ad copy testing"
- Expert opinion: RSA strength + headline/description performance — valuable. Google Ads shows this but scattered.
- What's good: Consolidated RSA view; ad strength grades; component performance
- What's wrong: READ-ONLY. No "Pause ad" or "Create variant" actions.
- Fix: Dodaj actions: Pause weak ads, duplicate strong ads for testing
- Priority: **P1**
- Actionability: READ-ONLY

**8. Smart Bidding Readiness**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.4] — Bid Strategy Optimization
- Expert opinion: "Data sufficiency, conversion tracking, volatility" check — excellent advisory tool.
- What's good: Multi-criteria assessment; clear pass/fail indicators; learning status tracking
- What's wrong: Na screenshocie "2 krytyczne, 1 niski wolumen" — but what should I DO? No action recommendations.
- Fix: Dodaj specific recommendations per issue (e.g., "Increase budget to get 30 conv/month for Target CPA")
- Priority: **P2**
- Actionability: READ-ONLY

**9. Scaling Opportunities**
- Rating: **IMPORTANT**
- Playbook ref: [PB §2.M] — "REALLOCATE budget: Campaign_A.ROAS > Campaign_B.ROAS × 2"
- Expert opinion: High-ROAS campaigns/ad groups identification — good. This is budget reallocation input.
- What's good: Identifies candidates; shows metrics
- What's wrong: No "Increase Budget" action. Identifies opportunity but can't act on it.
- Fix: Dodaj "Increase Budget +25%" inline button per scaling candidate
- Priority: **P0**
- Actionability: READ-ONLY

**10. PMax Channels (5 sekcji PMax)**
- Rating: **IMPORTANT**
- Playbook ref: No direct playbook ref (PMax is newer)
- Expert opinion: Channel breakdown, trends, asset groups, search themes, cannibalization — comprehensive PMax audit.
- What's good: Multi-dimensional PMax analysis; search cannibalization detection is gold
- What's wrong: PMax is largely a black box. Most insights here are interesting but not actionable (Google controls PMax allocation).
- Fix: Focus on actionable PMax insights: search cannibalization (→ add negatives to Search campaigns), asset group strength (→ improve weak assets)
- Priority: **P2**
- Actionability: READ-ONLY (mostly)

**11. Auction Insights**
- Rating: **IMPORTANT**
- Playbook ref: [PB §1.M] — "Competitor analysis (Auction Insights)"
- Expert opinion: Top competitors, impression share — monthly must-have.
- What's good: Competitor list with IS metrics
- What's wrong: Snapshot only. No trend (are competitors gaining or losing IS over time?).
- Fix: Dodaj competitor IS trend chart (30/60/90 day)
- Priority: **P2**
- Actionability: READ-ONLY

**12-35. Remaining sections** (Conversion Health, Ad Group Health, Learning Status, Portfolio Health, Demographics, Asset Groups, Audiences, Extensions, Shopping, Placements, Bid Modifiers, Topics, Google Recommendations, Conversion Value Rules, Offline Conversions, Audiences List)
- Rating: **IMPORTANT to NICE** (varies)
- Expert opinion: These are deep-dive analytics that most specialists check monthly. Having them all in one place saves significant time vs navigating Google Ads UI.
- Common issue: ALL are read-only. This is the fundamental problem with Command Center — it's an analytics dashboard, not an optimization tool.

#### Critical Assessment of Command Center

Command Center jest **najbardziej comprehensive analytics suite** jaki widziałem w narzędziu Google Ads. 35 sekcji pokrywających 100% playbooka to impressive.

**ALE**: Jest prawie CAŁKOWICIE read-only. To jest jak dashboard medyczny — pokazuje wyniki badań ale nie przepisuje leków. Specjalista musi:
1. Otworzyć Command Center
2. Zidentyfikować problem
3. Zamknąć Command Center
4. Otworzyć odpowiednią stronę (Keywords, Search Terms, etc.)
5. Znaleźć ten sam element
6. Wykonać akcję

To 6 kroków zamiast 2. **Priority P0: dodaj inline actions do top 10 sekcji Command Center.**

---

### 2.7 QUALITY SCORE

**Score: 6.5/10 | Verdict: IMPROVE | Playbook: §4.3 (Quality Score Optimization)**

#### Playbook Alignment Matrix

| Playbook Task | Element w QualityScore | Status |
|--------------|----------------------|--------|
| Identify keywords with QS < 5 | Low QS tab + threshold filter | ✅ COVERED |
| Track sub-components | Sub-component columns (CTR, Relevance, LP) | ✅ COVERED |
| QS distribution view | Distribution bar chart | ✅ COVERED |
| Issue breakdown (CTR vs Relevance vs LP) | Issue Breakdown horizontal bars | ✅ COVERED |
| Repair process (SKAGs, keyword in ad copy) | Brak sugestii naprawczych | ❌ MISSING |
| QS-weighted budget analysis | "Wydatki na niski QS: 17.3%" | ✅ COVERED |

#### Element-by-element audit

**1. KPI Cards (5: Avg QS, Low QS count, High QS count, Low QS spend %, IS Lost)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.3]
- Expert opinion: "Avg QS 6.7, 4 keywords need attention, 17.3% budget on low QS" — perfect summary.
- What's good: 5 critical QS metrics; IS Lost Ranking — excellent addition (shows QS impact on visibility)
- What's wrong: Brak trend. QS was 5.8 last month → 6.7 now? That's great progress! Without trend, no context.
- Fix: Dodaj trend indicators (30d change) per KPI card
- Priority: **P2**
- Actionability: READ-ONLY

**2. Distribution Chart**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.3] — QS distribution analysis
- Expert opinion: Bar chart 1-10 z color coding — standard visualization.
- What's good: Visual; color-coded (red/yellow/green bands)
- What's wrong: Nie rozróżnia QS z dużym spend od QS z zerowym spend. QS=3 z wydatkami 5000 zł to kryzys. QS=3 z wydatkami 2 zł to nic.
- Fix: Dodaj second series "Spend by QS" — weighted distribution
- Priority: **P2**
- Actionability: READ-ONLY

**3. Issue Breakdown (horizontal bars)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.3] — "3 factors: Expected CTR (50%), Ad Relevance (25%), Landing Page (25%)"
- Expert opinion: "Expected CTR: 15, Ad Relevance: 7, Landing Page: 4" — shows where to focus. Playbook says CTR has 50% weight so this is critical.
- What's good: Clear breakdown; counts per issue type; subtitle explains criteria
- What's wrong: Brak prioritization. "Expected CTR: 15 keywords" — ale ile z nich ma duże spend? Pokaż spend-weighted priority.
- Fix: Dodaj spend amount per issue type; sort by spend not count
- Priority: **P1**
- Actionability: READ-ONLY

**4. Keywords Table (sortable)**
- Rating: **CRITICAL**
- Playbook ref: [PB §4.3] — keyword-level QS analysis
- Expert opinion: Full QS detail per keyword z sub-components (dots), primary issue, cost — comprehensive.
- What's good: Sub-component display (dots: 1/2/3 = below/avg/above); primary issue label; cost and conversions for prioritization; campaign/ad group context
- What's wrong: (1) READ-ONLY — no actions. Specjalista widzi keyword z QS=2 ale nie może pause/bid down inline. (2) Brak "Fix Suggestions" per keyword (playbook §4.3: "SKAGs, keyword in ad copy, landing page improvements")
- Fix: (1) Dodaj action buttons (Pause, Bid Down); (2) Dodaj "Suggested Fix" column based on primary issue
- Priority: **P0**
- Actionability: READ-ONLY

**5. Campaign Filter + Match Type Filter**
- Rating: **IMPORTANT**
- Expert opinion: Standard filters, work correctly.
- What's good: Allows drilling into specific campaign/match type
- Fix: None needed
- Actionability: READ-ONLY (filter controls)

**6. Group by Ad Group toggle**
- Rating: **NICE**
- Expert opinion: Groups keywords by ad group z avg QS per group — useful for identifying problematic ad groups.
- What's good: Avg QS per ad group; count; total spend
- What's wrong: Brak "Create SKAG" suggestion for ad groups with low avg QS
- Fix: Low priority — current implementation OK
- Priority: **P3**
- Actionability: READ-ONLY

---

### 2.8 RECOMMENDATIONS

**Score: 8.5/10 | Verdict: KEEP | Playbook: §5 (Automated Recommendations Engine)**

#### Playbook Alignment Matrix

| Playbook Task | Element w Recommendations | Status |
|--------------|--------------------------|--------|
| Pause keyword (Spend>$50, 0 conv) | PAUSE_KEYWORD rule | ✅ COVERED |
| Update bid (CVR>Avg×1.2) | UPDATE_BID rule | ✅ COVERED |
| Add keyword (Search_Term.Conv≥3) | ADD_KEYWORD rule | ✅ COVERED |
| Add negative (Clicks>5, 0 conv) | ADD_NEGATIVE rule | ✅ COVERED |
| Pause ad (CTR<Best×0.5) | PAUSE_AD rule | ✅ COVERED |
| Increase budget (underspend) | INCREASE_BUDGET rule | ✅ COVERED |
| Reallocate budget | REALLOCATE_BUDGET rule | ✅ COVERED |
| QS alert (QS<5) | QS_ALERT rule | ✅ COVERED |
| IS alerts (budget/rank) | IS_BUDGET_ALERT, IS_RANK_ALERT | ✅ COVERED |
| Device/Geo anomaly | DEVICE_ANOMALY, GEO_ANOMALY | ✅ COVERED |
| Ad group health | AD_GROUP_HEALTH rules | ✅ COVERED |
| Smart bidding issues | SMART_BIDDING rules | ✅ COVERED |
| PMax issues | PMAX_CHANNEL_IMBALANCE etc. | ✅ COVERED |

**Coverage: 40+ rules — COMPLETE playbook coverage**

#### Element-by-element audit

**1. Summary Stats (5 boxes)**
- Rating: **IMPORTANT**
- Expert opinion: "58 total, 1 executable, 13 full, 30 actions, X blocked" — instant status.
- What's good: Quick overview; differentiates between executable/blocked/insight-only
- What's wrong: "1 executable" z 58 total = 1.7% execution rate. Czy to design (high safety) czy problem (too many false positives)?
- Fix: Track execution rate over time; alert if consistently < 10%
- Priority: **P3**
- Actionability: READ-ONLY

**2. Filter Pills (Priority, Source, Status)**
- Rating: **IMPORTANT**
- Expert opinion: HIGH/MEDIUM/LOW priority + source filter (Playbook/Analytics/Google Ads/Hybrid) — good.
- What's good: Multi-dimensional filtering; clear active state
- What's wrong: Brak "urgency" sort. HIGH priority + expiring soon should be on top.
- Fix: Dodaj sort by "urgency" (priority × days to expiry)
- Priority: **P3**
- Actionability: READ-ONLY (filter controls)

**3. Recommendation Cards (individual)**
- Rating: **CRITICAL**
- Playbook ref: [PB §5] — Recommendation display
- Expert opinion: Rich cards z: type pill, priority badge, title, description, metadata pills (Spend, Clicks, Conv), impact estimate, outcome badge, action buttons. This is EXCELLENT.
- What's good: (1) Context outcome (ACTION vs INSIGHT_ONLY vs BLOCKED) — specjalista wie czy można execute. (2) Blocking reasons visible — transparency. (3) Confidence + Risk scores. (4) Impact estimation (estimated savings). (5) Source labeling (Playbook vs Analytics vs Google).
- What's wrong: (1) Expiry date visible but no "urgency" indicator. (2) Individual cards take too much vertical space — hard to scan 58 recommendations.
- Fix: (1) Add urgency badge (red "Expires in 2 days"). (2) Add compact view toggle (table vs cards).
- Priority: **P2**
- Actionability: HAS ACTIONS (execute, dismiss)

**4. Execute/Dismiss Actions**
- Rating: **CRITICAL**
- Playbook ref: [PB §5] — Action execution
- Expert opinion: Execute → applies action (bid change, pause, add negative, etc.) with dry-run preview. Dismiss → marks as reviewed. This is the CORE value of the app.
- What's good: Dry-run before execution; blocking reasons prevent unsafe actions; audit trail via ActionLog
- What's wrong: Bulk execute is available but not prominent. Specjalista chce "Apply all HIGH priority executable" button.
- Fix: Dodaj prominent "Bulk Apply" button at top for filtered selection
- Priority: **P1**
- Actionability: **HAS ACTIONS** (execute, dismiss, bulk apply)

**5. Context Panel (blocking reasons)**
- Rating: **CRITICAL**
- Expert opinion: When a recommendation is BLOCKED, showing WHY is revolutionary. "Blocked because: campaign in learning period" — specjalista understands and trusts the system.
- What's good: Transparent; shows blocking + allowing reasons; helps education
- What's wrong: Nothing — this is perfectly designed
- Fix: None
- Actionability: READ-ONLY (informational)

---

### 2.9 ACTION HISTORY

**Score: 7.5/10 | Verdict: KEEP | Playbook: No direct ref — operational necessity**

#### Element-by-element audit

**1. Tab Navigation (Nasze akcje / Zewnętrzne / Wszystko / Wpływ zmian / Strategia licytacji)**
- Rating: **IMPORTANT**
- Expert opinion: Separating "Our actions" from "External actions" (Google Ads UI changes) is brilliant. Unified view merges both. "Change Impact" and "Bid Strategy Impact" are deep-dive analytics.
- What's good: 5 views cover all angles; clear separation of sources
- What's wrong: "Wpływ strategii licytacji" is very niche — could be merged into "Wpływ zmian"
- Fix: Consider merging into fewer tabs (3 instead of 5)
- Priority: **P3**
- Actionability: READ-ONLY (tab controls)

**2. Timeline Entries with DiffView**
- Rating: **CRITICAL**
- Expert opinion: Expandable entries showing before/after JSON diff — this is exactly what auditors need.
- What's good: Source badge (Helper/Google Ads UI/API); status badge (SUCCESS/FAILED/REVERTED); before/after values; timestamp
- What's wrong: "Wstrzyamno keyword" — typo in action label (should be "Wstrzymano"). Polish labels need QA pass.
- Fix: Fix Polish labels across all action types
- Priority: **P1**
- Actionability: HAS ACTIONS (revert)

**3. Revert Functionality**
- Rating: **CRITICAL**
- Expert opinion: "Undo" for actions — critical safety feature. If a bid change went wrong, one-click revert.
- What's good: Revert restores old_value_json; creates audit trail; REVERTED status visible
- What's wrong: Na screenshocie widać 1 REVERTED action — the feature works. No issues.
- Fix: None needed
- Actionability: **HAS ACTIONS** (revert)

**4. Change Impact View**
- Rating: **IMPORTANT**
- Expert opinion: Before/after metrics per change — shows whether an action improved or degraded performance.
- What's good: Concrete metric comparison; campaign-level aggregation
- What's wrong: Impact measurement requires time delay (7+ days after change). Does the UI handle "too early to measure"?
- Fix: Dodaj "Insufficient data" badge for changes < 7 days old
- Priority: **P2**
- Actionability: READ-ONLY

---

### 2.10 ALERTS (Monitoring)

**Score: 5.5/10 | Verdict: IMPROVE | Playbook: §1.D (Anomaly detection), §5 (Anomaly Detection)**

#### Element-by-element audit

**1. Business Alerts Tab (Nierozwiązane/Rozwiązane)**
- Rating: **CRITICAL**
- Playbook ref: [PB §1.D] — "Anomaly detection (CTR drops, CPC spikes, zero conversions)"
- Expert opinion: 4 alerts visible: SPEND_SPIKE, CONVERSION_DROP ×2, CTR_DROP. Severity-based (WYSOKI/ŚREDNI). Clear descriptions.
- What's good: Severity badges; clear descriptions with specifics ("3.2x więcej", "420 zł bez konwersji"); Resolve button
- What's wrong: (1) "Resolve" marks as resolved but doesn't FIX the problem. No suggested actions. (2) Brak auto-link to the affected campaign/keyword page. (3) No escalation rules (if unresolved > 24h, what happens?).
- Fix: (1) Dodaj "Suggested Action" per alert (e.g., "Pause campaign" / "Decrease budget" / "Check landing page"). (2) Make campaign name clickable → navigate to Campaigns. (3) Add "Snooze" option (remind in 24h).
- Priority: **P0**
- Actionability: HAS ACTIONS (resolve only — insufficient)

**2. Anomalies Tab (Z-score detection)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §5] — "Anomaly Detection: Z-Score method"
- Expert opinion: Statistical anomaly detection z configurable z-score threshold (1.5σ to 3.0σ) — advanced and correct.
- What's good: Metric selector; threshold control; period control (30/60/90d); KPI cards (count, mean, std dev); z-score coloring; direction icons (spike/dip)
- What's wrong: (1) No auto-alert creation for detected anomalies. Detection happens but then what? (2) No campaign context — just "date, campaign, value, z-score" table.
- Fix: (1) "Create Alert" button per anomaly. (2) Add context: what was normal for this campaign (mean ± std).
- Priority: **P1**
- Actionability: READ-ONLY (z-score analysis is informational)

---

### 2.11 REPORTS

**Score: 4.0/10 | Verdict: REDESIGN | Playbook: No direct ref**

#### Element-by-element audit

**1. Report Type Tabs (Monthly/Weekly/Health)**
- Rating: **NICE**
- Expert opinion: Good structure. Monthly reports are industry standard for client communication.
- What's good: Three report types covering different cadences
- What's wrong: ALL require AI generation (Claude CLI). "Brak zapisanych raportów" on screenshot means the feature barely works.
- Fix: Generate reports from DATA, not AI. AI narrative is nice-to-have, not the core.
- Priority: **P1** (if keeping the page)
- Actionability: HAS ACTIONS (generate)

**2. Report Content (when generated)**
- Rating: **IMPORTANT** (in theory)
- Expert opinion: Month comparison KPIs, campaign detail, change history, budget pacing — comprehensive report structure.
- What's good: Covers all key reporting areas; change impact analysis built-in
- What's wrong: Depends on Claude CLI authentication which is unreliable. No fallback for when AI is unavailable.
- Fix: Implement data-only report (tables + charts, no AI narrative) as default. AI narrative as enhancement.
- Priority: **P0** (if keeping the page)
- Actionability: READ-ONLY (view report)

**3. Overall Assessment**
Reports page tries to compete with Google Ads Reports + Looker Studio. It can't win. Google has better data access, more visualization options, and scheduling. The unique value would be: **automated playbook-based insights** in the report (what changed, what needs attention, recommended next steps). Without that, it's a weaker Google Ads Reports clone.

---

### 2.12 AGENT (AI Assistant)

**Score: 4.0/10 | Verdict: IMPROVE | Playbook: No direct ref**

#### Element-by-element audit

**1. Quick Report Buttons (6)**
- Rating: **NICE**
- Expert opinion: "Weekly report", "Campaign analysis", "Budget analysis" — useful shortcuts. But they just pre-fill a chat message.
- What's good: Reduces typing; covers common analysis requests
- What's wrong: Natural language interaction is slower than clicking through UI. Why chat "analyze my campaigns" when you can just GO to Campaigns page?
- Fix: Quick reports should generate instant structured output, not conversational chat
- Priority: **P2**
- Actionability: HAS ACTIONS (send message)

**2. Chat Interface**
- Rating: **NICE**
- Expert opinion: Standard chat UI. Token usage display is transparent.
- What's good: Streaming response; markdown rendering; session persistence (localStorage)
- What's wrong: Depends on Claude CLI. When unavailable, entire page is useless. Also, chat is ephemeral — no way to save/share insights.
- Fix: (1) Save important responses to a "Saved Insights" section. (2) Fallback: redirect to relevant page when AI unavailable.
- Priority: **P2**
- Actionability: HAS ACTIONS (chat)

---

### 2.13 FORECAST

**Score: 3.5/10 | Verdict: REDESIGN | Playbook: §5 — "Predictive Analytics: Linear regression"**

#### Element-by-element audit

**1. Forecast Chart (historical + prediction)**
- Rating: **NICE**
- Playbook ref: [PB §5] — Predictive Analytics
- Expert opinion: Linear regression on Google Ads data is fundamentally flawed. Ad data has: (1) weekday/weekend seasonality, (2) budget caps, (3) auction dynamics, (4) competitor changes. Linear regression captures NONE of these.
- What's good: Visual clarity; confidence interval band; historical + forecast separation
- What's wrong: **R² = 0.00 on screenshot**. The model explains 0% of variance. This is literally random noise. Showing this to a specialist destroys credibility.
- Fix: Either: (A) Replace with Prophet/ARIMA (handles seasonality), or (B) Remove page entirely, or (C) Rebrand as "Budget Simulator" (if I increase budget X%, what happens based on IS data)
- Priority: **P0** (fix or remove)
- Actionability: READ-ONLY

**2. KPI Cards (Trend, Forecast, R², Slope)**
- Rating: **USELESS** (with current model)
- Expert opinion: "Trend +16.5%, Forecast 173.15, R² 0.00, Slope 0.23" — contradictory. Positive trend but zero model confidence? This confuses users.
- What's good: Layout is clean
- What's wrong: Showing R²=0.00 with a "forecast" is dishonest. Low R² should suppress the forecast entirely.
- Fix: If R² < 0.3, show "Insufficient model quality — forecast not reliable" instead of numbers
- Priority: **P0**
- Actionability: READ-ONLY

---

### 2.14 SEMANTIC (Klastry Semantyczne)

**Score: 6.0/10 | Verdict: IMPROVE | Playbook: §4.1 — Semantic clustering**

#### Element-by-element audit

**1. Cluster Cards (expandable)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.1] — "Semantic clustering to group similar search terms by intent"
- Expert opinion: 9 clusters from 24 terms. "łóżko drewniane do sypialni" (5 terms, 3480 zł, 61 conversions) — useful grouping.
- What's good: Cluster name, term count, metrics (cost, conversions); waste indicator; expandable to see individual terms
- What's wrong: (1) Only 24 terms in 9 clusters — feels like too few. Full account might have 500+ terms. (2) Clustering quality depends on algorithm — no way to verify.
- Fix: (1) Increase default top_n to show more terms. (2) Add "clustering quality" indicator.
- Priority: **P2**
- Actionability: HAS ACTIONS (bulk add negatives for waste clusters)

**2. Min Cost Filter**
- Rating: **NICE**
- Expert opinion: "> 10 zł, > 50 zł, > 100 zł" — useful for focusing on high-spend clusters.
- What's good: Quick filter buttons
- What's wrong: Could also filter by "waste only" toggle
- Fix: Add "Waste only" toggle
- Priority: **P3**
- Actionability: READ-ONLY (filter control)

**3. Bulk Add Negatives (per waste cluster)**
- Rating: **IMPORTANT**
- Playbook ref: [PB §4.1] — "Actions based on intent: Irrelevant → add as negatives"
- Expert opinion: One-click add all terms in waste cluster as negatives (EXACT, CAMPAIGN scope) — good.
- What's good: Bulk operation per cluster; clear waste identification
- What's wrong: EXACT match only. Some waste patterns need PHRASE match (e.g., "darmowe" should block all "darmowe [anything]").
- Fix: Add match type selector per cluster (default PHRASE for single-word waste, EXACT for multi-word)
- Priority: **P1**
- Actionability: **HAS ACTIONS** (bulk add negatives)

---

### 2.15 SETTINGS

**Score: 7.0/10 | Verdict: KEEP | Playbook: §7 — Account setup**

#### Element-by-element audit

**1. General Information (name, industry, website, Google Customer ID, notes)**
- Rating: **IMPORTANT**
- Expert opinion: Standard client metadata. "Notes" field with "Kluczowy klient. Fokus na branded search i kanapa/łóżka. Sezon wysyski: wrzesień-grudzień." — useful context for AI/recommendations.
- What's good: Editable; Google Customer ID visible; notes for context
- What's wrong: Notes should be more structured (e.g., seasons, focus products, KPI targets as separate fields)
- Fix: Add structured fields: Primary Season (months), Focus Categories (tags), Monthly Budget Target
- Priority: **P2**
- Actionability: HAS ACTIONS (edit + save)

**2. Strategy & Competition**
- Rating: **IMPORTANT**
- Expert opinion: Target Audience, USP, Competitors tags — good for context-aware recommendations.
- What's good: Competitors as tags (add/remove); USP text; target audience description
- What's wrong: Competitors are just names. Should link to Auction Insights data for those competitors.
- Fix: Cross-reference competitor names with Auction Insights; show IS overlap
- Priority: **P2**
- Actionability: HAS ACTIONS (edit)

**3. Business Rules (Min ROAS, Max Daily Budget)**
- Rating: **CRITICAL**
- Playbook ref: [PB §2.M] — Thresholds
- Expert opinion: Min ROAS and Max Daily Budget drive recommendations. If Min ROAS = 400%, recommendations with ROAS < 400% get flagged. Essential.
- What's good: Client-specific thresholds; drives recommendation engine
- What's wrong: Only 2 rules. Playbook has 7+ decision rules (target CPA, min CTR, max CPC, etc.). Should have more configurable thresholds.
- Fix: Add: Target CPA, Min CTR, Min Quality Score, Max CPC, Max Waste %
- Priority: **P1**
- Actionability: HAS ACTIONS (edit)

**4. Safety Limits (6 limits)**
- Rating: **CRITICAL**
- Expert opinion: "Max bid change %, Max budget change %, Min/Max bid USD, Max keyword pause %/day, Max negatives/day" — excellent safety net for automation.
- What's good: Prevents runaway automation; per-client configuration; sensible defaults
- What's wrong: Limits are "override defaults or leave empty" — what ARE the defaults? Should be visible.
- Fix: Show current default values as placeholder text in empty fields
- Priority: **P2**
- Actionability: HAS ACTIONS (edit)

**5. Hard Reset**
- Rating: **NICE**
- Expert opinion: Nuclear option — delete all local data. Confirmation required (type client name). Correctly implemented safety-wise.
- What's good: Confirmation input; clear warning text; describes what gets deleted
- What's wrong: Nothing — correctly implemented for a dangerous operation
- Fix: None
- Actionability: HAS ACTIONS (destructive)

**6. MCC Accounts**
- Rating: **NICE**
- Expert opinion: MCC sub-account listing — useful for agencies managing multiple clients.
- What's good: Shows linked accounts with status
- What's wrong: Read-only list. Can't add/remove MCC links.
- Fix: Low priority — MCC management better done in Google Ads UI
- Priority: **P3**
- Actionability: READ-ONLY

---

## PART 3: ANALIZA CROSS-CUTTING

### 3.1 Global Filter Bar — podwójna filtracja problem

**Problem:** GlobalFilterBar (campaignType, status, period, dateFrom, dateTo) AND Sidebar campaign type pills BOTH filter content. Confusion: if user selects "SEARCH" in Sidebar but "PMAX" in GlobalFilterBar → what happens?

**Impact:** Specjalista nie wie który filtr jest aktywny. Dwa sources of truth = bugs.

**Assessment:**
- Sidebar pills → filter navigation items visibility (which pages show)
- GlobalFilterBar → filter DATA on current page

**Fix:** Unify. Sidebar pill should SET the GlobalFilterBar campaign type (single source of truth). Remove campaign type from GlobalFilterBar dropdown.

**Priority: P1**

### 3.2 Nawigacja i cross-references

**Strengths:**
- Dashboard → Alerts (HealthScore click)
- Dashboard → SearchTerms?segment=WASTE (Wasted Spend click)
- Dashboard → QualityScore (QS widget click)
- Keywords → Campaigns (campaign name link)
- Campaigns → Keywords per campaign (button)
- Campaigns → Search Terms per campaign (button)

**Weaknesses:**
- Command Center → Nothing. 35 sekcji analytics bez linków do stron akcji
- QualityScore → Keywords (no link to fix specific keyword)
- Alerts → Campaigns (no link to affected campaign)
- Semantic → Search Terms (no link to view terms in context)

**Fix:** Add "Go to [Page]" navigation links from every analytical section to its corresponding action page. Priority: **P1**

### 3.3 Data Freshness & Sync

**Assessment:**
- Sync is manual (trigger button per client)
- No auto-sync scheduling (no cron, no daily refresh)
- Data age visible in Client Drawer (last sync timestamp + data range)
- Daily Audit shows "yesterday" data → requires sync to have run today

**Problem:** If user forgets to sync, ALL data is stale. Recommendations, alerts, audits — all based on old data.

**Fix:** Implement auto-sync scheduling (daily at 6:00 AM local time, before morning audit). Priority: **P0**

### 3.4 Export Audit

**Coverage:**
| Page | CSV | XLSX | Notes |
|------|-----|------|-------|
| Keywords | ✅ | ✅ | Full keyword data |
| Search Terms | ✅ | ✅ | All terms |
| Quality Score | ✅ | ✅ | QS audit |
| Recommendations | ✅ | ✅ | With evidence |
| Action History | ✅ | ✅ | With diff data |
| Campaign Metrics | ✅ | ✅ | Daily metrics |
| Dashboard | ❌ | ❌ | No export |
| Daily Audit | ❌ | ❌ | No export |
| Command Center | ❌ | ❌ | No export |
| Alerts | ❌ | ❌ | No export |
| Reports | ❌ | ❌ | No export (ironic) |

**Fix:** Add export to Dashboard (KPI summary), Alerts (alert list), Command Center (section data). Priority: **P2**

### 3.5 Actionability Audit (Write Operations)

| Page | Write Operations | Assessment |
|------|-----------------|------------|
| Dashboard | 0 | ❌ Read-only hub |
| Daily Audit | 4 (Quick Scripts) | ✅ Excellent |
| Campaigns | 2 (role override, bidding target) | ⚠️ Insufficient — needs pause, budget change |
| Keywords | 6 (pause, bid up/down, add/remove negative, list management) | ✅ Comprehensive |
| Search Terms | 2 (bulk add negative, bulk add keyword) | ✅ Good |
| Command Center | 2 (add negative, add placement exclusion) | ❌ 35 sections but only 2 actions |
| Quality Score | 0 | ❌ Read-only audit |
| Recommendations | 3 (execute, dismiss, bulk apply) | ✅ Core feature |
| Action History | 1 (revert) | ✅ Good |
| Alerts | 1 (resolve) | ⚠️ Resolve ≠ Fix |
| Reports | 1 (generate) | ⚠️ Limited |
| Agent | 1 (chat) | ⚠️ Indirect |
| Forecast | 0 | ❌ Read-only |
| Semantic | 1 (bulk add negatives) | ⚠️ Limited |
| Settings | Full CRUD | ✅ Good |

**Total write operations across app: ~22**
**Pages with 0 actions: 3 (Dashboard, QualityScore, Forecast)**
**Pages with insufficient actions: 4 (Campaigns, Command Center, Alerts, Semantic)**

**Critical pattern:** The app is approximately 70% analytics / 30% actions. For a specialist who needs to ACT on insights, this ratio should be closer to 50/50.

### 3.6 Threshold Compliance

| Playbook Threshold | Implemented? | Where |
|-------------------|-------------|-------|
| PAUSE: Spend > $50 & Conv = 0 | ✅ | Keywords action hints, Recommendations |
| PAUSE: CTR < 0.5% | ✅ | Recommendations (LOW_CTR_KEYWORD) |
| PAUSE: QS < 3 | ⚠️ | QualityScore shows but no auto-pause recommendation |
| INCREASE bid: CVR > Avg×1.2 & CPA < Target×0.8 | ✅ | Recommendations (UPDATE_BID) |
| DECREASE bid: CPA > Target×1.5 | ✅ | Recommendations (UPDATE_BID) |
| ADD keyword: Search_Term.Conv ≥ 3 & CVR > Avg | ✅ | Recommendations (ADD_KEYWORD) |
| ADD negative: Clicks > 5 & Conv = 0 & CTR < 1% | ✅ | Recommendations (ADD_NEGATIVE) |
| PAUSE ad: CTR < Best×0.5 | ✅ | Recommendations (PAUSE_AD) |
| REALLOCATE: ROAS_A > ROAS_B × 2 | ✅ | Recommendations (REALLOCATE_BUDGET) |
| CTR benchmark: > 2% branded, > 1% non-branded | ⚠️ | Not differentiated by campaign role |
| QS benchmark: 7-10 good, < 5 problem | ✅ | QualityScore thresholds |
| IS benchmark: > 80% brand, > 50% generic | ⚠️ | Not differentiated by campaign role |

**Fix:** Differentiate thresholds by campaign role (BRAND vs GENERIC) for CTR, IS benchmarks. Priority: **P1**

---

## PART 4: PLAYBOOK COVERAGE MATRIX

### Daily Tasks (15-30 min/account)

| Task | Covered | Page(s) | Quality |
|------|---------|---------|---------|
| Budget monitoring (spend > 150% avg) | ✅ | Dashboard (HealthScore), Daily Audit (KPIs), Alerts (SPEND_SPIKE) | ⭐⭐⭐⭐ Excellent — multi-layer coverage |
| Anomaly detection (CTR drops) | ✅ | Alerts (CTR_DROP), Dashboard (HealthScore) | ⭐⭐⭐ Good — z-score detection |
| Anomaly detection (CPC spikes) | ⚠️ | Not explicit alert type | ⭐⭐ Partial — could be caught by z-score |
| Anomaly detection (zero conversions) | ✅ | Alerts (CONVERSION_DROP) | ⭐⭐⭐⭐ Explicit alert |
| Search Terms Review | ✅ | Search Terms (segments), Daily Audit (Clean Waste) | ⭐⭐⭐⭐⭐ Best-in-class |
| Identify negatives from search terms | ✅ | Search Terms (bulk add negative), Recommendations (ADD_NEGATIVE) | ⭐⭐⭐⭐⭐ Automated + manual |
| Identify high-performing terms | ✅ | Search Terms (HIGH_PERFORMER segment) | ⭐⭐⭐⭐ Clear segmentation |
| Pause poor performers | ✅ | Keywords (action hints), Daily Audit (Pause Burning), Recommendations | ⭐⭐⭐⭐ Multi-path |

### Weekly Tasks (1-2 hours/account)

| Task | Covered | Page(s) | Quality |
|------|---------|---------|---------|
| Performance comparison (7d vs 7d) | ✅ | Dashboard (WoW), Campaigns (KPIs with % change) | ⭐⭐⭐⭐ Good |
| Keyword bid adjustments | ✅ | Keywords (Bid Up/Down), Recommendations (UPDATE_BID) | ⭐⭐⭐⭐ Direct actions |
| Ad copy testing | ⚠️ | Command Center (RSA Analysis) — read-only | ⭐⭐ Analysis only, no management |
| Audience analysis (demographics) | ⚠️ | Command Center (Demographics) — read-only | ⭐⭐ Analysis only, no bid modifiers |
| Audience analysis (devices) | ⚠️ | Campaigns (Device Breakdown) — read-only | ⭐⭐ No bid modifier controls |
| Audience analysis (locations) | ⚠️ | Campaigns (Geo Breakdown) — read-only | ⭐⭐ No bid modifier controls |
| Budget reallocation | ⚠️ | Command Center (Scaling Opp.) — read-only | ⭐ Analysis but no action |

### Monthly Tasks (3-5 hours/account)

| Task | Covered | Page(s) | Quality |
|------|---------|---------|---------|
| Competitor analysis (Auction Insights) | ⚠️ | Command Center (Auction Insights) — snapshot | ⭐⭐ No trend, no competitive strategy |
| Landing page analysis | ⚠️ | Command Center (Landing Pages) — read-only | ⭐⭐ Metrics only, no GA4 integration |
| Account structure audit | ✅ | Command Center (Account Structure, Ad Group Health) | ⭐⭐⭐ Good analysis |
| Quality Score deep dive | ✅ | QualityScore (dedicated page) | ⭐⭐⭐⭐ Comprehensive audit |
| Attribution analysis | ❌ | Not implemented | — |

### Specialized Strategies

| Strategy | Covered | Page(s) | Quality |
|---------|---------|---------|---------|
| Search Terms Intelligence | ✅ | Search Terms + Semantic | ⭐⭐⭐⭐⭐ Best feature |
| Correlation Matrix | ✅ | Campaigns (TrendExplorer, Pearson r) | ⭐⭐⭐ Good |
| Quality Score Optimization | ✅ | QualityScore + Recommendations (QS_ALERT) | ⭐⭐⭐⭐ Comprehensive |
| Bid Strategy Optimization | ⚠️ | Command Center (multiple sections) — read-only | ⭐⭐⭐ Good analysis, limited action |

### Advanced Features

| Feature | Covered | Page(s) | Quality |
|---------|---------|---------|---------|
| Anomaly Detection (Z-Score) | ✅ | Alerts (Anomalies tab) | ⭐⭐⭐ Basic but functional |
| Predictive Analytics | ⚠️ | Forecast (linear regression) | ⭐ Broken (R²=0.00) |
| Automated Recommendations | ✅ | Recommendations (40+ rules) | ⭐⭐⭐⭐⭐ Comprehensive |

### Coverage Summary

| Category | Tasks | Fully Covered | Partially | Missing |
|----------|-------|--------------|-----------|---------|
| Daily | 8 | 7 (88%) | 1 (12%) | 0 |
| Weekly | 7 | 2 (29%) | 5 (71%) | 0 |
| Monthly | 5 | 2 (40%) | 2 (40%) | 1 (20%) |
| Specialized | 4 | 2 (50%) | 2 (50%) | 0 |
| Advanced | 3 | 2 (67%) | 1 (33%) | 0 |
| **TOTAL** | **27** | **15 (56%)** | **11 (41%)** | **1 (4%)** |

**Key insight:** Daily tasks are well covered (88%). Weekly tasks are the weak point (only 29% fully covered) because most analytics are read-only without action capabilities.

---

## PART 5: PRIORITIZED ACTION PLAN

### P0 — Fix Before Next Release (Critical blockers)

| # | Fix | Page | File(s) | What to do |
|---|-----|------|---------|------------|
| P0-1 | **Campaign actions: Pause, Budget Change** | Campaigns | `Campaigns.jsx`, `campaigns.py` | Dodaj inline buttons: Pause Campaign, Change Budget (±10%/±25%/custom), Change Bidding Target. Te operacje są CORE specjalisty — brak ich to deal-breaker. |
| P0-2 | **Command Center inline actions** | SearchOptimization | `SearchOptimization.jsx` | Top 10 sekcji: dodaj inline action buttons. Wasted Spend → Pause keyword/ad. N-gram → Add as negative. Scaling → Increase budget. RSA → Pause weak ad. |
| P0-3 | **Fix or remove Forecast** | Forecast | `Forecast.jsx` | R²=0.00 destroys credibility. Options: (A) Prophet/ARIMA model, (B) Budget Simulator (IS-based), (C) Remove page. Minimum: suppress forecast when R² < 0.3. |
| P0-4 | **Alert actions (not just "resolve")** | Alerts | `Alerts.jsx` | Per alert: add "Suggested Action" button (Pause campaign / Decrease budget / Check LP). Make campaign name clickable → navigate to campaign detail. |
| P0-5 | **QualityScore actions** | QualityScore | `QualityScore.jsx` | Dodaj per-keyword actions: Pause (if QS ≤ 3), Bid Down (if QS ≤ 5), "View Fix Suggestions" (based on primary issue: CTR → rewrite ad, Relevance → SKAG, LP → fix landing page). |
| P0-6 | **Auto-sync scheduling** | Backend | `sync.py`, new scheduler | Implement daily auto-sync at configurable time. Without fresh data, entire app is unreliable. |
| P0-7 | **Command Center: filter problems first** | SearchOptimization | `SearchOptimization.jsx` | Add "Show problems only" toggle + sort by severity. Red items first, green items hidden/collapsed. |

### P1 — Next Sprint (Important improvements)

| # | Fix | Page | File(s) | What to do |
|---|-----|------|---------|------------|
| P1-1 | **Device/Geo bid modifiers** | Campaigns | `Campaigns.jsx`, `campaigns.py` | Dodaj bid modifier sliders (-100% to +300%) per device and location. |
| P1-2 | **Unify filter sources** | Global | `Sidebar.jsx`, `GlobalFilterBar.jsx` | Sidebar campaign type pill → sets GlobalFilterBar campaignType. One source of truth. |
| P1-3 | **Daily Audit: alert impacts** | DailyAudit | `DailyAudit.jsx` | Add estimated cost impact (zł) to each critical alert. |
| P1-4 | **Daily Audit: smart script filtering** | DailyAudit | `DailyAudit.jsx` | "Boost Winners" script: skip Smart Bidding campaigns. Read thresholds from Settings. |
| P1-5 | **Keywords: suggested negatives** | Keywords | `Keywords.jsx` | On Negatives tab, add "Suggested Negatives" section pulling from SearchTerms WASTE. |
| P1-6 | **Recommendations: bulk apply prominent** | Recommendations | `Recommendations.jsx` | Add prominent "Apply all HIGH priority" button at top of page. |
| P1-7 | **Cross-page navigation links** | Multiple | All analytical pages | Add "Go to [Page]" links from Command Center sections, QualityScore keywords, Alerts campaigns. |
| P1-8 | **Threshold differentiation by campaign role** | Recommendations | `recommendations.py` | CTR benchmark: > 2% (BRAND), > 1% (GENERIC). IS: > 80% (BRAND), > 50% (GENERIC). |
| P1-9 | **Search Terms: consolidate variants** | SearchTerms | `SearchTerms.jsx` | Variants view: add "Consolidate" action (best performer → keyword, rest → negatives). |
| P1-10 | **N-gram: add as negative** | SearchOptimization | `SearchOptimization.jsx` | Per n-gram row: inline "Add as Negative" button (PHRASE match). |
| P1-11 | **QS issue breakdown: sort by spend** | QualityScore | `QualityScore.jsx` | Sort issue types by spend impact, not keyword count. |
| P1-12 | **Action History: fix Polish labels** | ActionHistory | `ActionHistory.jsx` | Fix "Wstrzyamno" → "Wstrzymano" and QA all action type labels. |
| P1-13 | **Semantic: match type selector** | Semantic | `Semantic.jsx` | Per-cluster add negative: allow PHRASE/EXACT match type selection. |
| P1-14 | **Settings: more business rules** | Settings | `Settings.jsx` | Add: Target CPA, Min CTR, Min QS, Max CPC, Max Waste %. |

### P2 — Backlog (Nice improvements)

| # | Fix | Page | What to do |
|---|-----|------|------------|
| P2-1 | Dashboard KPI sparklines | Dashboard | Add 7-day sparklines under each KPI card |
| P2-2 | Dashboard: replace Impressions with IS | Dashboard | Show Impression Share instead of raw Impressions |
| P2-3 | Health Score transparency | Dashboard | Tooltip with scoring weights per category |
| P2-4 | InsightsFeed: show preview text | Dashboard | Show 1-2 lines per insight instead of just badge |
| P2-5 | WoW metric selector | Dashboard | Let user choose which metrics to compare WoW |
| P2-6 | Campaign list: search + grouping | Campaigns | Search input + group by campaign_type |
| P2-7 | CampaignTrendExplorer: anomaly markers | Campaigns | Red dots on outlier data points (z-score > 2) |
| P2-8 | Keywords: CPA + Conversion Value columns | Keywords | Add extended metrics toggle |
| P2-9 | Keywords: QS tooltip with sub-components | Keywords | Hover QS badge → show CTR/Relevance/LP dots |
| P2-10 | Search Terms: segment rules tooltip | SearchTerms | Show segmentation thresholds per segment |
| P2-11 | QS: trend indicators | QualityScore | 30d change per KPI card |
| P2-12 | QS: spend-weighted distribution chart | QualityScore | Second series showing spend by QS band |
| P2-13 | Anomalies: create alert from anomaly | Alerts | "Create Alert" button per detected anomaly |
| P2-14 | Action History: "too early" badge | ActionHistory | For changes < 7 days: show "Insufficient data for impact" |
| P2-15 | Reports: data-only fallback | Reports | Generate tables/charts without AI narrative |
| P2-16 | Semantic: clustering quality | Semantic | Show clustering quality indicator |
| P2-17 | Settings: show default limits | Settings | Placeholder text showing current defaults |
| P2-18 | Settings: structured notes | Settings | Separate fields for Season, Categories, Budget Target |
| P2-19 | Export: add to Dashboard, Alerts, CC | Multiple | CSV/XLSX export buttons on remaining pages |
| P2-20 | Auction Insights: competitor trend | CommandCenter | 30/60/90d IS trend chart per competitor |
| P2-21 | Command Center: dayparting → ad schedule action | CommandCenter | "Apply Ad Schedule" based on CPA pattern |
| P2-22 | Smart Bidding: specific recommendations | CommandCenter | Per-issue recommendation text |
| P2-23 | Keywords: configurable thresholds | Keywords | Read action hint thresholds from Settings |
| P2-24 | Daily Audit: today fallback | DailyAudit | If today = 0 data, show yesterday with banner |
| P2-25 | Bulk script granularity | DailyAudit | Show item-level preview before bulk execute |

### P3 — Nice to Have

| # | Fix | Page | What to do |
|---|-----|------|------------|
| P3-1 | Dashboard: TrendExplorer default collapsed | Dashboard | Collapse by default, expand on click |
| P3-2 | Campaign role tooltip | Campaigns | Explain protection levels |
| P3-3 | Keywords: export column selection | Keywords | Choose columns before export |
| P3-4 | Search Terms: waste context | SearchTerms | "287 zł = X dni budżetu kampanii Y" |
| P3-5 | Keyword Expansion disclaimer | Keywords | "Based on account data" label |
| P3-6 | Action History: fewer tabs | ActionHistory | Merge 5 tabs → 3 (Our/External/Impact) |
| P3-7 | Agent: save insights | Agent | "Saved Insights" section for important responses |
| P3-8 | QS: ad group SKAG suggestion | QualityScore | Suggest SKAG for low-QS ad groups |
| P3-9 | PMax: focus on actionable insights | CommandCenter | Highlight cannibalization + asset strength |
| P3-10 | Match Type Analysis: inline insights | CommandCenter | "Consider reducing BROAD spend" type insights |
| P3-11 | Recommendations: urgency sort | Recommendations | Priority × days to expiry ordering |
| P3-12 | Recommendations: compact view | Recommendations | Table view toggle (vs cards) |
| P3-13 | Semantic: "waste only" toggle | Semantic | Filter to show only waste clusters |
| P3-14 | Settings: competitor IS cross-reference | Settings | Link competitors to Auction Insights data |
| P3-15 | Dashboard: Campaign table inline Pause | Dashboard | Quick pause for 0-conversion campaigns |

### Kill List

| Element | Current State | Recommendation |
|---------|--------------|----------------|
| Forecast (linear regression) | R²=0.00, misleading | **REMOVE** or replace with Budget Simulator |
| Reports (AI-generated) | Requires Claude CLI, "Brak raportów" | **REDESIGN** as data-only reports with optional AI |
| Agent (AI chat) | Depends on Claude CLI availability | **DEPRIORITIZE** — invest in inline actions instead |

---

## APPENDIX: Element Inventory Count

| Page | UI Elements | Actions | API Calls |
|------|------------|---------|-----------|
| Dashboard | 8 | 0 | 14 |
| Daily Audit | 7 | 4 | 2 |
| Campaigns | 7 | 2 | 9 |
| Keywords | 6 | 6 | 12 |
| Search Terms | 6 | 2 | 6 |
| Search Optimization | 35+ | 2 | 37 |
| Quality Score | 6 | 0 | 1 |
| Recommendations | 5 | 3 | 3 |
| Action History | 4 | 1 | 7 |
| Alerts | 2 | 1 | 3 |
| Reports | 3 | 1 | 3 |
| Agent | 2 | 1 | 2 |
| Forecast | 2 | 0 | 2 |
| Semantic | 3 | 1 | 2 |
| Settings | 6 | 5 | 4 |
| **TOTAL** | **~102** | **~29** | **~107** |

---

## PART 6: BEYOND PLAYBOOK — Perspektywa eksperta e-commerce z 10+ lat doświadczenia

> Playbook to baseline. Poniżej rzeczy, o których żaden playbook nie pisze, a które decydują o sukcesie e-commerce w Google Ads. To wiedza z okopów — z setek kont meblowych, odzieżowych, elektronicznych.

---

### 6.1 SHOPPING / PLA — Kompletny blind spot aplikacji

**Severity: CRITICAL**

Aplikacja ma typ kampanii SHOPPING w filterze, ma nawet `getShoppingProductGroups()` endpoint. Ale nie ma **ŻADNEJ dedykowanej strony do zarządzania Shopping**.

W e-commerce meblowym (jak Demo Meble) Shopping/PLA to zwykle **40-60% revenue**. To nie jest "nice to have" — to jest fundament.

#### Czego brakuje — strona "Shopping / PLA"

| Element | Opis | Dlaczego krytyczne |
|---------|------|-------------------|
| **Product Group Performance** | Tabela: Product Group → Clicks, Cost, Conversions, ROAS, CPA | Bez tego nie wiesz które kategorie produktów generują profit a które marnują budżet |
| **Product-level Performance** | Drill-down: konkretny SKU → metryki | "Łóżko dębowe 160x200" ma ROAS 800% ale "Łóżko sosnowe 90x200" ma ROAS 50% — musisz to widzieć |
| **Feed Health Dashboard** | Disapproved products count, missing attributes, feed errors | Google Merchant Center nie jest widoczny w Google Ads UI — trzeba osobno się logować. Integracja = ogromna wartość |
| **Bid adjustments per product group** | Slider ±% per category/brand/product type | "Łóżka" mają ROAS 600% → bid up. "Akcesoria" mają ROAS 80% → bid down |
| **Title/Description optimization** | Podgląd product titles z sugestiami | Tytuł produktu = najważniejszy element Shopping. "Łóżko" vs "Łóżko dębowe 160x200 z materacem — darmowa dostawa" — 3x różnica CTR |
| **Competitive pricing** | Benchmark price vs competitors | Google Merchant Center Price Competitiveness report — jeśli twoja cena jest 20% wyższa, CTR spada |
| **Search Terms per product** | Jakie frazy triggernowały który produkt | "kanapa narożna" → wyświetlił się fotel. Mapping search terms → products = gold |
| **Supplemental Feed Management** | Custom labels, promotions, sale prices | Custom label 0-4 to secret weapon dla segmentacji Shopping |

**Estymowany impact:** Dodanie dedykowanej strony Shopping to prawdopodobnie **najwyższa wartość per feature** jaka może powstać w tej apce. Dla e-commerce meblowego to 40-60% konta.

**Nowa strona: `Shopping.jsx`**
- Priority: **P0-BEYOND**
- Backend: `shopping.py` router + rozszerzenie `analytics_service.py`
- API: Google Ads API `shopping_performance_view`, `product_group_view`

---

### 6.2 PMax Feed-Only — Trend 2025/2026

**Severity: IMPORTANT**

PMax Feed-Only (Performance Max z samym feedem produktowym, bez asset group) to **dominujący trend** w e-commerce Google Ads w 2025-2026. Większość agencji przeszła z Standard Shopping → PMax Feed-Only.

#### Dlaczego to ważne

Standard Shopping jest de facto deprecated przez Google. PMax z feedem + minimalnym asset group to nowy standard. Ale PMax jest czarną skrzynką — aplikacja ma 5 sekcji PMax w Command Center ale brakuje:

| Element | Opis |
|---------|------|
| **PMax vs Standard Shopping comparison** | Jeśli klient ma oba — pokaż ROAS, CPA, conv volume side by side |
| **Asset Group → Feed connection** | Który asset group wyciąga z którego feed segmentu |
| **Listing Group (dawne product groups) management** | PMax ma "listing groups" zamiast product groups — trzeba je segmentować |
| **URL expansion control** | PMax rozszerza URL-e — to może słać traffic na nieoptymalne strony. Monitoring + control |
| **Search categories analysis** | PMax Google daje "search categories" zamiast search terms — trzeba to pokazać |
| **Final URL performance** | Gdzie PMax kieruje traffic — czy na produkt czy na kategorię |

**Nowa sekcja w Command Center lub osobna strona**
- Priority: **P1-BEYOND**

---

### 6.3 Google Merchant Center Integration

**Severity: CRITICAL (dla e-commerce)**

Żadne narzędzie Google Ads nie jest kompletne dla e-commerce bez integracji z Merchant Center.

| Element | Opis | API |
|---------|------|-----|
| **Feed diagnostics** | Ile produktów aktywnych/disapproved/pending | Merchant Center API |
| **Disapproved products list** | Z powodami (price, policy, missing attributes) | Merchant Center API |
| **Feed freshness** | Ostatni upload, następny scheduled | Merchant Center API |
| **Product count by status** | Active / Expiring / Pending / Disapproved | Merchant Center API |
| **Price competitiveness** | Benchmark vs rynek | `PriceCompetitiveness` report |
| **Best sellers** | Top products w kategorii | `BestSellers` report |
| **Click potential** | Produkty z niskim wyświetlaniem | `ProductPerformance` report |

**Impact:** Jeśli feed ma 30% disapproved products, cała optymalizacja kampanii Shopping jest bez sensu — bo 30% asortymentu nie jest widoczne. Specjalista musi to wiedzieć PRZED optymalizacją bidów.

- Priority: **P1-BEYOND**
- Wymaga: Google Merchant Center API (Content API for Shopping v2.1)
- Nowa strona: `MerchantCenter.jsx` lub sekcja w Settings

---

### 6.4 Sezonowość e-commerce — brakujący wymiar

**Severity: IMPORTANT**

Demo Meble ma notatkę: "Sezon wysyski: wrzesień-grudzień". Ale aplikacja **nie ma żadnego mechanizmu sezonowości**.

#### Czego brakuje

| Element | Opis |
|---------|------|
| **Seasonal calendar** | Konfiguracja per klient: Black Friday, Boże Narodzenie, wyprzedaże letnie, back-to-school |
| **YoY comparison** | Marzec 2026 vs Marzec 2025 — jedyny uczciwy benchmark dla sezonowego biznesu. MoM porównanie (luty vs marzec) jest misleading |
| **Seasonal budget planner** | "W Q4 historycznie wydajesz 3x więcej — zaplanuj budżet" |
| **Pre-season alerts** | "Za 2 tygodnie zaczyna się sezon — czy budżety są gotowe? Czy kampanie sezonowe są odpauzowane?" |
| **Post-season cleanup** | "Sezon się skończył — te kampanie sezonowe nadal wydają. Zapauzować?" |
| **Seasonal bid strategy switch** | "W szczycie sezonu przejdź z Target CPA na Maximize Conversions (volume > efficiency)" |

**Impact:** E-commerce meblowy ma 40% obrotu w Q4. Jeśli narzędzie nie wie o sezonach, recommendations engine może sugerować "pause this keyword" w październiku — właśnie gdy ten keyword zaczyna performować.

- Priority: **P1-BEYOND**
- Implementacja: pole `seasonal_calendar` w Settings → reference w recommendations engine
- Nowa sekcja w Dashboard: "Seasonal Context"

---

### 6.5 Customer Lifetime Value & New vs Returning

**Severity: IMPORTANT**

Playbook traktuje każdą konwersję równo. Ekspert e-commerce wie, że **nowy klient jest 5-10x cenniejszy niż powracający** (bo powracający kupuje też bez reklamy).

#### Czego brakuje

| Element | Opis |
|---------|------|
| **New vs Returning customer split** | Per kampania: ile konwersji to nowi vs powracający klienci |
| **Adjusted ROAS** | ROAS corrected for new customer value (nowy klient × LTV multiplier) |
| **Customer acquisition cost** | CPA ale tylko dla NOWYCH klientów |
| **Remarketing efficiency** | Czy remarketing (Kanapy - Retarget) generuje inkrementalne zakupy czy kanibalizuje organic? |
| **First-party data health** | Rozmiar audience list, match rate Customer Match, freshness |

**Dlaczego to zmienia decyzje:**
- Kampania "Branded Search" ma CPA 36 zł i ROAS 5.24x → wygląda świetnie
- ALE: 90% tych konwersji to powracający klienci, którzy kupiliby i bez reklamy
- Prawdziwy inkrementalny ROAS branded = 1.2x → nie tak świetnie
- Kampania "Łóżka - Generic" ma CPA 50 zł i ROAS 3.8x → wygląda gorzej
- ALE: 80% to nowi klienci z LTV 3x → adjusted ROAS = 11.4x → dużo lepsze

Bez tej perspektywy specjalista podejmuje złe decyzje budżetowe.

- Priority: **P2-BEYOND**
- Wymaga: Google Ads conversion tracking z new customer dimension, lub GA4 integration
- Nowa sekcja w Campaigns: "Customer Value Analysis"

---

### 6.6 Dynamic Remarketing — niewidoczny kanał

**Severity: IMPORTANT**

Na liście kampanii widać "Kanapy - Retarget" (Search remarketing) i "Display - Remarketing". Ale nie ma **żadnej analizy efektywności remarketingu** jako strategii.

#### Czego brakuje

| Element | Opis |
|---------|------|
| **Remarketing funnel** | Visitors → Add to Cart → Abandoned → Remarketed → Purchased |
| **Audience overlap analysis** | Czy remarketing audience pokrywa się z Search audience? (kanibalizacja) |
| **Dynamic ad performance** | Które produkty w dynamic remarketing mają najwyższy CTR/Conv |
| **Frequency cap analysis** | Ile razy user widział reklamę zanim kupił / zrezygnował |
| **Time-to-conversion** | Ile dni od pierwszej wizyty do konwersji (per kampania type) |
| **Assisted conversions** | Remarketing jako assisted (nie last-click) — prawdziwa wartość |

- Priority: **P2-BEYOND**
- Nowa strona: `Remarketing.jsx` lub sekcja w Campaigns

---

### 6.7 Conversion Value Optimization — nie tylko "ile konwersji"

**Severity: CRITICAL**

Aplikacja śledzi `conversions` (count) i `conversion_value` (revenue). Ale w e-commerce **wartość konwersji jest ważniejsza niż ilość**.

#### Problem obecnej apki

Recommendation "PAUSE_KEYWORD" sprawdza: `Spend > $50 & Conversions = 0`. Ale co jeśli keyword ma 2 konwersje o wartości 5 zł (razem 10 zł) i spend 200 zł? To ROAS 0.05x — gorsze niż 0 konwersji z 50 zł spend (bo marnuje 5x więcej). Reguły powinny operować na VALUE, nie COUNT.

#### Czego brakuje

| Element | Opis |
|---------|------|
| **Revenue-based segmentation** | Zamiast "0 conversions = waste" → "ROAS < min_roas = waste" |
| **AOV (Average Order Value) tracking** | Per kampania / keyword / search term — jaka średnia wartość zamówienia |
| **High-value conversion identification** | Które keywords generują zamówienia > 1000 zł vs < 100 zł |
| **Conversion value rules monitoring** | Command Center ma sekcję ale brak dashboardu efektywności reguł |
| **Profit margin integration** | ROAS 400% przy marży 20% = break even. ROAS 200% przy marży 50% = profit. Bez marży ROAS jest niepełny |
| **Cart/basket analysis** | Jakie produkty kupują razem (cross-sell opportunities) |

- Priority: **P1-BEYOND**
- Implementacja: (1) Dodaj AOV column do Keywords i Search Terms. (2) Revenue-based rules w recommendations engine. (3) Margin input w Settings.

---

### 6.8 Competitor Intelligence — poza Auction Insights

**Severity: IMPORTANT**

Auction Insights to minimum. Prawdziwy ekspert e-commerce monitoruje:

| Element | Opis |
|---------|------|
| **Competitor price monitoring** | Czy konkurent obniżył cenę? (wpływa na CTR Shopping) |
| **Competitor ad copy analysis** | Jakie USP komunikują konkurenci (darmowa dostawa, -20%, etc.) |
| **Competitor IS trends** | Nie snapshot — trend 90 dni. Czy nowy competitor wchodzi na rynek? |
| **Category-level competitive landscape** | W "łóżkach" mamy 80% IS ale w "kanapach" tylko 30% — dlaczego? |
| **Competitive SERP analysis** | Ile organic vs paid results? Czy Featured Snippets kanibalizują? |
| **Market share estimation** | IS × Search Volume ≈ your market share. Track over time |

Częściowo jest w Command Center (Auction Insights), ale brak trendu i kontekstu. Potrzeba dedykowanej strony.

- Priority: **P2-BEYOND**
- Nowa strona: `CompetitiveAnalysis.jsx`

---

### 6.9 Landing Page & CRO — most między Google Ads a stroną

**Severity: IMPORTANT**

Playbook mówi "Landing page analysis monthly". Apka ma sekcję Landing Pages w Command Center. Ale to jest **surface level**.

#### Czego brakuje (wymaga GA4 integration)

| Element | Opis |
|---------|------|
| **Bounce rate per landing page per campaign** | Czy traffic z "Łóżka - Generic" bounce'uje na stronie kategorii? |
| **Page speed per URL** | Core Web Vitals (LCP, FID, CLS) — wpływa na QS component "Landing Page Experience" |
| **A/B test results** | Jeśli klient testuje 2 wersje LP — który ma wyższy CVR z Google Ads traffic? |
| **Conversion path analysis** | Landing page → product page → cart → checkout → purchase — gdzie odpada traffic? |
| **Mobile vs Desktop per LP** | Strona może dobrze działać na desktop ale źle na mobile (UI/UX issues) |
| **LP → QS correlation** | Które landing pages mają keywords z niskim LP QS score? |

- Priority: **P2-BEYOND**
- Wymaga: GA4 Data API integration
- Nowa sekcja w Command Center lub osobna strona

---

### 6.10 Struktura konta e-commerce — brakujący advisor

**Severity: IMPORTANT**

E-commerce meblowy powinien mieć specyficzną strukturę konta:

```
[BRAND] Branded Search           — 150 zł/d — Target ROAS 800%
[GENERIC] Kategoria: Łóżka       — 300 zł/d — Target CPA 45 zł
[GENERIC] Kategoria: Kanapy      — 200 zł/d — Target CPA 50 zł
[GENERIC] Kategoria: Biurka      — 100 zł/d — Target CPA 40 zł
[SHOPPING] Standard Shopping      — 500 zł/d — Target ROAS 400%
[PMAX] PMax - Feed Only          — 350 zł/d — Target ROAS 350%
[REMARKETING] Display Remarketing — 100 zł/d — Target ROAS 600%
[DSA] Dynamic Search Ads         — 50 zł/d  — discovery
```

#### Czego apka nie robi:

| Element | Opis |
|---------|------|
| **Structure advisor** | "Masz 9 kampanii — ale nie masz DSA. DSA odkrywa nowe keywords z 0 maintenance" |
| **Budget allocation advisor** | "Branded Search ma ROAS 5x ale bierze 15% budżetu. Generic ma ROAS 3.8x i bierze 30%. Przenieś 10% z Generic do Branded" |
| **Campaign type coverage check** | "Nie masz kampanii Video. Czy rozważałeś YouTube Ads?" |
| **Category coverage gap** | "Masz 'Łóżka', 'Kanapy' ale nie masz 'Meble ogrodowe' — a to sezonowa szansa" |
| **SKAG vs STAG advisor** | "Masz 28 keywords w jednej ad group — rozważ podział na STAG (Single Theme Ad Groups)" |
| **Funnel coverage** | "Masz BOTTOM (Shopping, Branded) i MIDDLE (Generic) ale brak TOP (Display prospecting, YouTube)" |

- Priority: **P2-BEYOND**
- Implementacja: reguły w recommendations engine oparte na account structure analysis

---

### 6.11 Cross-channel Cannibalization — krytyczny problem e-commerce

**Severity: CRITICAL**

Demo Meble ma: Branded Search, Generic Search (Łóżka, Kanapy, Biurka), PMax, Shopping, Display Remarketing. **Te kampanie kanibalizują się nawzajem.**

| Kanibalizacja | Problem | Jak wykryć |
|--------------|---------|-----------|
| PMax vs Search | PMax kradnie branded traffic z Search | Compare PMax search terms vs Branded Search keywords |
| PMax vs Shopping | PMax zastępuje Standard Shopping | Before/after ROAS comparison |
| Remarketing vs Branded | User szuka "demo meble" → klika remarketing ad zamiast branded | Check: czy branded search volume spada gdy remarketing rośnie? |
| Generic vs Shopping | "łóżko drewniane" triggeruje i Search i Shopping | Auction overlap analysis |
| DSA vs Generic | DSA triggeruje te same frazy co manual keywords | Search term overlap |

Command Center ma sekcję "PMax Search Cannibalization" — to dobry start. Ale potrzeba **szerszej analizy cross-channel**.

- Priority: **P1-BEYOND**
- Nowa sekcja: "Cross-Channel Cannibalization Dashboard"
- Data: search terms overlap matrix, impression share overlap, before/after ROAS per channel

---

### 6.12 Promotion & Sale Management

**Severity: IMPORTANT (sezonowo CRITICAL)**

E-commerce żyje promocjami. Black Friday, Dzień Darmowej Dostawy, wyprzedaże sezonowe. Aplikacja nie ma żadnego zarządzania promocjami.

| Element | Opis |
|---------|------|
| **Promotion calendar** | Planowane promocje z datami start/end, budżetem, target KPIs |
| **Pre-promotion checklist** | "Budżety podniesione? Kampanie sezonowe odpauzowane? Feed updated z sale prices? Extensions z promotion?" |
| **During-promotion monitoring** | Real-time dashboard: spend vs plan, konwersje vs target, stock levels |
| **Post-promotion analysis** | Promotion ROAS, nowi vs powracający, canibalized organic, total incrementality |
| **Merchant Center promotions** | Sale price annotations w Shopping — czy są aktywne? |

- Priority: **P2-BEYOND**
- Nowa strona: `Promotions.jsx`

---

### 6.13 KOMPLETNY PRZEGLĄD WSZYSTKICH TYPÓW KAMPANII GOOGLE ADS

Google Ads w 2026 ma **14 typów/podtypów kampanii**. Aplikacja obsługuje 5 w filtrze (SEARCH, PERFORMANCE_MAX, SHOPPING, DISPLAY, VIDEO). Poniżej — pełna mapa każdego typu z oceną co apka ma, czego nie ma, i co powinien widzieć specjalista.

---

#### A. SEARCH (Standard Search)

**Status w apce: ⭐⭐⭐⭐⭐ EXCELLENT — core feature**

Apka jest zbudowana wokół Search. Keywords, Search Terms, QS Audit, N-gram, Match Type analysis — to wszystko to Search territory. Recommendations engine ma 30+ reguł dla Search.

| Element | Status | Komentarz |
|---------|--------|-----------|
| Keyword management | ✅ Full | Pause, bid up/down, action hints, QS, IS |
| Search term analysis | ✅ Full | Segmentation, bulk ops, variants, n-gram |
| Ad management (RSA) | ⚠️ Read-only | RSA Analysis w CC, ale brak create/edit/pause ads |
| Quality Score | ✅ Full | Dedykowana strona, sub-components, distribution |
| Negative keywords | ✅ Full | CRUD + lists + bulk + apply |
| Match type analysis | ✅ Full | CC sekcja + filter |
| Extensions/Assets | ⚠️ Read-only | Missing extensions + performance w CC |
| Ad scheduling | ❌ Missing | Dayparting analysis jest, ale brak ustawiania schedule |
| RLSA (Remarketing Lists for Search) | ❌ Missing | Brak zarządzania audience lists per Search kampania |

**Brakujące elementy krytyczne:**
1. **Ad management UI** — tworzenie/edycja RSA, pauzowanie słabych ads, A/B testing
2. **Ad scheduling** — apply dayparting insights as bid modifiers per hour/day
3. **RLSA management** — audience bid adjustments for Search campaigns

---

#### B. DYNAMIC SEARCH ADS (DSA)

**Status w apce: ❌ ZERO SUPPORT**

DSA to kampanie Search, które automatycznie generują headlines na podstawie contentu strony. Nie wymagają keywords — Google crawluje stronę i sam decyduje na co wyświetlić reklamę.

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **DSA target pages** | Lista stron/kategorii targetowanych przez DSA | Specjalista musi widzieć które strony są w scope |
| **Auto-generated headlines** | Przegląd headlines generowanych przez Google | Czy Google generuje sensowne tytuły? Czy nie wyciąga śmieci? |
| **Search term → Page mapping** | Która fraza trafiła na którą stronę | DSA może wysłać "łóżko dla psa" na stronę "łóżka" — trzeba to monitorować |
| **Page feed management** | Custom feed stron dla DSA | Kontrola co DSA targetuje |
| **Negative page targets** | Wyklucz strony (blog, regulamin, polityka prywatności) | DSA bez exclusions reklamuje stronę "Regulamin" |
| **DSA vs Manual keyword overlap** | Które frazy DSA pokrywają się z manualnymi keywords | Kanibalizacja — DSA kradnie traffic od lepiej zoptymalizowanych manual campaigns |
| **Auto-target analysis** | Jak Google kategoryzuje stronę (categories, URLs, page titles) | Kontrola automatycznych targetsów |

**Impact:** DSA to "keyword discovery machine" — specjaliści e-commerce używają DSA do odkrywania fraz, których nie mają w manual campaigns. Dla sklepu meblowego z 5000 produktów, DSA znajduje long-tail queries które nigdy nie przyszłyby do głowy.

**Rekomendacja:** Nowa sekcja w Command Center "DSA Analysis" + filtry DSA w Search Terms page
- Priority: **P1-BEYOND**

---

#### C. SHOPPING (Standard Shopping / PLA)

**Status w apce: ⭐ MINIMAL — critical gap**

Opisane szczegółowo w §6.1. Apka ma `getShoppingProductGroups()` endpoint ale nie ma dedykowanej strony.

**Dodatkowe elementy per typ Shopping:**

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **Product group tree** | Hierarchia: All Products → Category → Brand → Product Type → Item ID | Tak specjalista zarządza bidami w Shopping |
| **Product group bid management** | Bid per product group (manual CPC) lub excluded | Core operacja w Standard Shopping |
| **Product partition analysis** | "Other" catch-all groups — ile traffic idzie na "Other"? | "Other" = niekontrolowany traffic. Powinno być < 10% |
| **Search term → Product mapping** | Która fraza wyświetliła który produkt | "kanapa narożna" wyświetliła fotel → problem z feedem |
| **Product status** | Active, Disapproved, Pending, Expiring per product | Merchant Center sync |
| **Product-level ROAS** | ROAS per SKU, nie per product group | Granularne decyzje: ten konkretny model łóżka jest profitable? |
| **Inventory-aware bidding** | Stock level → bid adjustment (niski stock = obniż bid) | Po co reklamować produkt którego nie masz na stanie? |
| **Price competitiveness** | Twoja cena vs rynek per product | Jeśli jesteś 30% droższy, CTR będzie niski niezależnie od bida |

**Rekomendacja:** Dedykowana strona `Shopping.jsx` — P0-BEYOND (powtarzam z §6.1 bo to CRITICAL)

---

#### D. PERFORMANCE MAX (PMax)

**Status w apce: ⭐⭐⭐ PARTIAL — analytics OK, management missing**

Command Center ma 5 sekcji PMax (Channels, Channel Trends, Asset Groups, Search Themes, Cannibalization). To dobra analityka. Ale brakuje zarządzania.

**PMax w 2026 — co apka MUSI obsługiwać:**

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **Asset Group management** | Create/edit/pause asset groups | Core zarządzanie PMax |
| **Asset performance** | Per asset: headline, description, image → performance rating | Google daje asset-level reporting — trzeba to pokazać |
| **Ad Strength indicator** | Per asset group: Poor/Average/Good/Excellent | Google każe utrzymywać "Excellent" — trzeba monitorować |
| **Signal management** | Audience signals per asset group (custom segments, interests, demographics) | Signals sterują algorytmem PMax |
| **Listing group management** | Product feed segmentation (odpowiednik product groups w Shopping) | Feed-only PMax wymaga listing group optimization |
| **URL expansion control** | On/Off per kampania + monitoring final URLs | PMax rozszerza URL-e — może słać traffic na blog zamiast produkt |
| **Search categories** | Google Reports API search categories (zamiast search terms) | PMax nie daje pełnych search terms — daje "categories" |
| **Channel budget allocation** | Ile PMax wydaje na Search vs Display vs YouTube vs Gmail vs Discover | Black box transparency |
| **Brand exclusions** | Brand keyword exclusions w PMax | PMax kradnie branded traffic — exclusions to must-have |
| **New customer acquisition goal** | Toggle + value w PMax | PMax ma wbudowany "new customer" mode — trzeba go monitorować |

**PMax subtypes w 2026:**

| Subtype | Opis | Specyfika |
|---------|------|-----------|
| **PMax Feed-Only** | Tylko feed, brak/minimalny asset group | Zastępuje Standard Shopping. Listing groups = key |
| **PMax Full (Feed + Assets)** | Feed + full creative assets | Pełny multi-channel. Asset quality = key |
| **PMax No-Feed** | Bez feed, lead gen/services | Dla non-e-commerce. Audience signals = key |
| **PMax Travel** | Specjalny dla hoteli/lotów | Integracja z hotel feeds |
| **PMax Store Goals** | Offline visits/sales | Local inventory ads integration |

Apka powinna rozróżniać subtypes i pokazywać relevant sekcje per subtype.

**Rekomendacja:** Rozszerzyć Command Center PMax sections + dodać asset/listing group management
- Priority: **P1-BEYOND**

---

#### E. DISPLAY (Standard Display)

**Status w apce: ⭐⭐ MINIMAL**

Apka ma `DISPLAY` w filtrze, ma `getPlacementPerformance()` i `getTopicPerformance()` w CC. Ale to surface level.

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **Placement management** | Whitelist/blacklist placement sites | "Moja reklama wyświetla się na spam stronie" — trzeba to kontrolować |
| **Placement exclusion lists** | Shared placement exclusion lists per konto/MCC | Każde konto e-commerce ma exclusion list 500+ stron |
| **Audience targeting** | In-market, affinity, custom intent audiences per kampania | Display bez audience targeting = waste |
| **Responsive Display Ads** | Asset management (images, logos, headlines, descriptions) | RDA to domyślny format Display |
| **Ad preview** | Jak wygląda reklama na różnych placements | Specjalista chce widzieć preview |
| **Viewability metrics** | Active View: viewable impressions, viewable CTR | 50% Display impressions jest niewidocznych (below fold) |
| **Brand safety** | Content exclusions (tragedy, conflict, sensitive) | Dla dużych marek to compliance requirement |
| **Frequency management** | Frequency per user per day/week | Za dużo wyświetleń = user burnout, za mało = brak impact |
| **Conversion lag analysis** | Display ma 7-30 day conversion lag | Attribution window critical for correct ROAS |

**Rekomendacja:** Rozszerzyć CC + dedykowana sekcja Display management
- Priority: **P2-BEYOND**

---

#### F. VIDEO (YouTube Ads)

**Status w apce: ⭐ MINIMAL**

Apka ma `VIDEO` w filtrze. W CC brak dedykowanych Video sekcji. Dla e-commerce meblowego YouTube to zwykle 5-15% budżetu (awareness/consideration).

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **Video campaign subtypes** | In-Stream (skippable/non-skip), In-Feed, Bumper, Shorts | Każdy subtype ma inne metryki i optimization levers |
| **View rate** | % users who watched 30s / completion | Kluczowa metryka Video (zamiast CTR) |
| **Video completion rate** | % watched to end per video creative | Które video działa? |
| **Earned actions** | Subscribes, shares, playlist adds | Video engagement beyond clicks |
| **Brand Lift** | Survey-based lift measurement | Jedyny sposób mierzenia awareness impact |
| **YouTube audience management** | Custom intent, in-market, remarketing z YouTube viewers | YouTube remarketing = ludzie którzy obejrzeli video |
| **Creative performance** | Which video creative → best view rate/CTR/conversion | A/B testing video |
| **YouTube placement analysis** | Na jakich kanałach/video się wyświetla | Kontrola kontekstu wyświetlania |
| **Shorts performance** | YouTube Shorts to osobny format z innym behavior | 2025/2026 — Shorts rosną 50% YoY |
| **Connected TV (CTV)** | TV screens per YouTube → osobna analiza | CTV to nowy kanał w Google Ads video |
| **Companion banner CTR** | Banner wyświetlany obok video | Dodatkowy engagement metric |

**Video subtypes w Google Ads 2026:**

| Subtype | Cel | Metryki |
|---------|-----|---------|
| **Video Action (TrueView for Action)** | Conversions | CPA, Conv Rate, Cost/Conv |
| **Video Reach (Bumper + In-Stream)** | Awareness (CPM) | CPM, Reach, Frequency, View Rate |
| **Video View (In-Feed + In-Stream)** | Consideration | CPV, View Rate, Watch Time |
| **Video Shorts** | Short-form engagement | Views, Swipe Rate, Engagement |
| **Demand Gen (was Discovery)** | Mid-funnel | Conversions, Engagement, CTR |

**Rekomendacja:** Dedykowana sekcja Video w CC z view rate, completion, creative performance
- Priority: **P2-BEYOND**

---

#### G. DEMAND GEN (dawniej Discovery)

**Status w apce: ❌ ZERO SUPPORT**

Demand Gen to kampanie na YouTube Home Feed, Gmail, Discover Feed. W 2026 to **najszybciej rosnący typ kampanii** w Google Ads. Google rebranded Discovery → Demand Gen w 2024 z dodaniem video i lookalike audiences.

| Element | Co powinno być | Dlaczego ważne |
|---------|---------------|----------------|
| **Placements breakdown** | YouTube / Gmail / Discover — ile traffic z każdego | Kontrola channel mix |
| **Creative performance** | Single image, carousel, video per placement | Demand Gen ma unique creative formats |
| **Lookalike audiences** | Seed list → lookalike performance | Demand Gen unique feature — lookalike targeting |
| **Product feed integration** | Demand Gen + product feed = dynamic product ads | E-commerce Demand Gen musi mieć feed |
| **Engagement metrics** | Gmail opens, Discover swipes, YouTube scrolls | Non-click engagement = value signal |
| **A/B creative testing** | Asset-level reporting per placement | Optimize per surface |

**Dlaczego to ważne dla e-commerce:**
Demand Gen z product feed = dynamic product discovery na YouTube, Gmail, Discover. Użytkownik który przeglądał "łóżka" na YouTube widzi carousel łóżek w Gmail. To jest przyszłość upper-funnel e-commerce.

**Rekomendacja:** Dodaj `DEMAND_GEN` do campaign type filtra + sekcja w CC
- Priority: **P2-BEYOND**

---

#### H. APP CAMPAIGNS

**Status w apce: ❌ ZERO SUPPORT (uzasadnione — Demo Meble nie ma appki)**

Ale: App campaigns to **#2 typ kampanii pod względem wydatków** globalnie w Google Ads. Jeśli aplikacja ma być uniwersalna (nie tylko e-commerce meblowe), potrzebuje:

| Element | Co powinno być |
|---------|---------------|
| **Install tracking** | CPI (Cost per Install), Install Volume |
| **In-app action tracking** | Cost per in-app action (purchase, registration, level) |
| **Creative asset performance** | Which text/image/video → best installs |
| **Audience signals** | Similar users, custom intent for apps |
| **Campaign subtypes** | App Installs, App Engagement, App Pre-Registration |

**Rekomendacja:** Pominąć w v1 (Demo Meble focus). Dodać w v2 jeśli apka ma być multi-vertical.
- Priority: **P3-BEYOND** (skip for e-commerce)

---

#### I. LOCAL CAMPAIGNS / LOCAL SERVICES ADS

**Status w apce: ❌ ZERO SUPPORT**

Local campaigns promują fizyczne lokalizacje (sklepy, restauracje). Demo Meble może mieć showroom.

| Element | Co powinno być |
|---------|---------------|
| **Store visits tracking** | Visits po zobaczeniu reklamy |
| **Direction actions** | "Get directions" clicks |
| **Call tracking** | Phone calls from ads |
| **Local inventory ads** | Pokaż "w magazynie w Twoim sklepie" |
| **Business Profile integration** | Google Business Profile reviews, hours, photos |

**Rekomendacja:** Pominąć w v1 chyba że klient ma physical stores.
- Priority: **P3-BEYOND**

---

#### J. SMART CAMPAIGNS

**Status w apce: ❌ ZERO SUPPORT (uzasadnione)**

Smart Campaigns to uproszczony typ dla małych firm. Zero optimization levers. Ekspert Google Ads nigdy nie używa Smart Campaigns — migruje klienta na Standard.

**Rekomendacja:** Nie implementować. Dodać alert: "Masz Smart Campaign — rozważ migrację na Standard Search/Shopping."
- Priority: **P3-BEYOND** (alert only)

---

#### K. HOTEL CAMPAIGNS

**Status w apce: ❌ ZERO SUPPORT (branch-specific)**

| Element | Co powinno być |
|---------|---------------|
| **Hotel price feed** | Integration z hotel booking system |
| **Booking window analysis** | Ile dni przed check-in user bookuje |
| **Length of stay analysis** | Performance per nights count |
| **Rate competitiveness** | Twoja cena vs OTAs (Booking.com, Expedia) |
| **Bid adjustments** | Per check-in date, length of stay, device, location |

**Rekomendacja:** Nie implementować w v1 (nie dotyczy Demo Meble).
- Priority: **SKIP** (vertical-specific)

---

#### L. TRAVEL CAMPAIGNS

**Status w apce: ❌ ZERO SUPPORT (branch-specific)**

Things to Do, Vacation Rentals — Google travel vertical. Pominąć w v1.

---

#### M. BRAND CAMPAIGNS (nowy typ 2025)

**Status w apce: ❌ ZERO SUPPORT**

Google w 2025 wprowadził **Brand Campaigns** — dedykowany typ kampanii do ochrony branded keywords z advanced brand controls.

| Element | Co powinno być |
|---------|---------------|
| **Brand keyword ownership** | Które brand terms triggernują Twoje ads |
| **Competitor brand bidding** | Czy konkurenci bidują na Twój brand |
| **Brand IS protection** | Alert jeśli branded IS < 90% |
| **Brand safety controls** | Exclusion of negative brand associations |

**Rekomendacja:** Dodaj `BRAND` rozpoznawanie w campaign role classification (już częściowo jest) + Brand IS monitoring
- Priority: **P2-BEYOND**

---

#### PODSUMOWANIE: Wszystkie typy kampanii Google Ads vs Apka

| # | Typ kampanii | Apka: filter | Apka: dedykowana strona | Apka: sekcja w CC | Apka: akcje | Ocena | Priority |
|---|-------------|-------------|------------------------|-------------------|-------------|-------|----------|
| A | **Search** | ✅ | Keywords, SearchTerms, QS | 10+ sekcji | ✅ Pełne | ⭐⭐⭐⭐⭐ | — (done) |
| B | **DSA** | ❌ (pod Search) | ❌ | ❌ | ❌ | ⭐ | P1-BEYOND |
| C | **Shopping/PLA** | ✅ | ❌ | 1 sekcja | ❌ | ⭐ | **P0-BEYOND** |
| D | **PMax** | ✅ | ❌ | 5 sekcji | ❌ | ⭐⭐⭐ | P1-BEYOND |
| E | **Display** | ✅ | ❌ | 2 sekcje | 1 (placement excl.) | ⭐⭐ | P2-BEYOND |
| F | **Video/YouTube** | ✅ | ❌ | ❌ | ❌ | ⭐ | P2-BEYOND |
| G | **Demand Gen** | ❌ | ❌ | ❌ | ❌ | ❌ | P2-BEYOND |
| H | **App** | ❌ | ❌ | ❌ | ❌ | ❌ | P3 (skip v1) |
| I | **Local** | ❌ | ❌ | ❌ | ❌ | ❌ | P3 (skip v1) |
| J | **Smart** | ❌ | ❌ | ❌ | ❌ | ❌ | P3 (alert only) |
| K | **Hotel** | ❌ | ❌ | ❌ | ❌ | ❌ | SKIP |
| L | **Travel** | ❌ | ❌ | ❌ | ❌ | ❌ | SKIP |
| M | **Brand** | ❌ | ❌ | ❌ | ❌ | ❌ | P2-BEYOND |

**Coverage: 5/14 typów w filtrze (36%), 1/14 z pełnym wsparciem (7% = tylko Search)**

**Wnioski:**
- Apka to **Search-first tool** — i to robi dobrze
- Shopping (P0) i PMax management (P1) to dwa biggest gaps
- DSA, Display, Video, Demand Gen to następna fala (P2)
- App, Local, Smart, Hotel, Travel — pominąć w v1 (vertical-specific lub nie relevant)
- Brand campaigns — nowy typ, warto dodać brand protection monitoring

---

### 6.14 Brakujące strony — podsumowanie (ZAKTUALIZOWANE z pełnym przeglądem typów kampanii)

**Nowe strony:**

| # | Strona | Typ | Priority | Impact |
|---|--------|-----|----------|--------|
| 1 | **Shopping / PLA** | Nowa strona | P0-BEYOND | 40-60% revenue e-commerce. Product groups, SKU-level ROAS, feed health |
| 2 | **Merchant Center** | Nowa strona/sekcja | P1-BEYOND | Feed diagnostics, disapprovals, price competitiveness |
| 3 | **DSA Analysis** | Nowa sekcja CC + SearchTerms | P1-BEYOND | Auto-headlines, page targeting, keyword overlap |
| 4 | **Video/YouTube** | Nowa sekcja CC | P2-BEYOND | View rate, completion, creative performance, Shorts |
| 5 | **Demand Gen** | Nowa sekcja CC | P2-BEYOND | YouTube/Gmail/Discover placements, lookalike, product feed |
| 6 | **Competitive Analysis** | Nowa strona | P2-BEYOND | Beyond Auction Insights — price, IS trends, market share |
| 7 | **Remarketing** | Nowa strona/sekcja | P2-BEYOND | Funnel, frequency, assisted conversions, incrementality |
| 8 | **Promotions** | Nowa strona | P2-BEYOND | Seasonal calendar, pre/during/post-promo management |

**Rozszerzenia istniejących stron/sekcji:**

| # | Sekcja/Feature | Typ | Priority | Impact |
|---|---------------|-----|----------|--------|
| 1 | **PMax full management** | Rozszerzenie CC + asset groups, listing groups, signals, brand exclusions | P1-BEYOND | PMax = dominant type 2026 |
| 2 | **Display management** | Rozszerzenie CC + placement lists, audience, frequency, viewability | P2-BEYOND | Brand safety + reach control |
| 3 | **Seasonal calendar + YoY** | Rozszerzenie Settings + Dashboard | P1-BEYOND | Correct benchmarking |
| 4 | **Conversion value optimization** | Rozszerzenie Recommendations | P1-BEYOND | Revenue-based rules, AOV, margins |
| 5 | **Cross-channel cannibalization** | Nowa sekcja CC | P1-BEYOND | PMax vs Search vs Shopping overlap |
| 6 | **Account structure advisor** | Rozszerzenie Recommendations | P2-BEYOND | DSA gap, funnel coverage, category gaps |
| 7 | **New vs Returning customer** | Rozszerzenie Campaigns | P2-BEYOND | LTV-based optimization |
| 8 | **Landing Page + CRO** | Rozszerzenie CC + GA4 | P2-BEYOND | Full funnel CRO |
| 9 | **Brand protection monitoring** | Rozszerzenie Alerts/Dashboard | P2-BEYOND | Brand IS, competitor brand bidding |
| 10 | **Smart Campaign migration alert** | Alert w Recommendations | P3-BEYOND | "Migrate to Standard" advisory |

---

### 6.14 Brutalna prawda — co ekspert powiedziałby na spotkaniu

> "Ta aplikacja jest **świetna dla Search campaigns**. Naprawdę. Search Terms Intelligence, Quality Score Audit, N-gram analysis, 40 reguł w Recommendations — to bije Google Ads UI na głowę.
>
> **ALE** — to jest aplikacja dla 2020 roku, nie 2026. W 2026 roku e-commerce Google Ads to:
> - **60% Shopping/PMax** (a wy macie 0 dedykowanych stron)
> - **Feed quality** decyduje o IS w Shopping (a wy nie macie Merchant Center)
> - **Cross-channel budżetowanie** (a wy analizujecie kampanie w izolacji)
> - **Sezonowość** steruje 40% rocznych przychodów (a wy nie macie kalendarza)
>
> Gdybym miał 3 miesiące, zrobiłbym w tej kolejności:
> 1. **Shopping page** z product group performance (miesiąc 1)
> 2. **Inline actions w Command Center** — bo 35 sekcji analytics bez akcji to encyklopedia, nie narzędzie (miesiąc 1-2)
> 3. **Merchant Center integration** — feed health (miesiąc 2)
> 4. **Sezonowość + YoY** — bo bez tego benchmarki są kłamstwem (miesiąc 2-3)
> 5. **Cross-channel cannibalization dashboard** (miesiąc 3)
>
> Dopiero wtedy ta aplikacja byłaby **kompletna dla e-commerce 2026**."

---

## PART 7: ZAKTUALIZOWANE PODSUMOWANIE

### Pełna lista braków (Playbook + Beyond Playbook + Campaign Types)

| Źródło | Covered | Partially | Missing | Total |
|--------|---------|-----------|---------|-------|
| Playbook tasks (§1-§5) | 15 (56%) | 11 (41%) | 1 (4%) | 27 |
| Beyond Playbook — e-commerce (§6.1-6.12) | 2 (15%) | 3 (23%) | 8 (62%) | 13 |
| Campaign type coverage (§6.13) | 1 (7%) | 4 (29%) | 9 (64%) | 14 |
| **COMBINED** | **18 (33%)** | **18 (33%)** | **18 (33%)** | **54** |

### Zaktualizowana ocena per typ kampanii

| Typ kampanii | Ocena | Co jest | Czego brakuje |
|-------------|-------|--------|--------------|
| **Search** | **8.5/10** | Keywords, Search Terms, QS, N-gram, RSA, Recommendations | Ad management, ad scheduling, RLSA |
| **DSA** | **0/10** | Nic | Wszystko: page targets, auto-headlines, overlap |
| **Shopping/PLA** | **1/10** | 1 endpoint (product groups) | Strona, product-level ROAS, bid management, feed |
| **PMax** | **5/10** | 5 sekcji analytics w CC | Asset/listing group management, signals, brand exclusions |
| **Display** | **2/10** | Placement + topic performance | Placement lists, audience mgmt, frequency, viewability |
| **Video/YouTube** | **1/10** | Typ w filtrze | View rate, completion, creative, Shorts, CTV |
| **Demand Gen** | **0/10** | Nic | Placements, lookalike, product feed, engagement |
| **App** | **0/10** | — | Pominąć w v1 |
| **Local** | **0/10** | — | Pominąć w v1 |
| **Smart** | **0/10** | — | Migration alert only |
| **Hotel** | **0/10** | — | Skip (vertical) |
| **Travel** | **0/10** | — | Skip (vertical) |
| **Brand** | **0/10** | Partial (campaign role BRAND) | Brand IS protection, competitor bidding alerts |

### Zaktualizowana ocena per wymiar

| Wymiar | Ocena | Komentarz |
|--------|-------|-----------|
| Search campaign management | **8.5/10** | Best-in-class. Lepsza niż Google Ads UI. |
| Shopping/PLA management | **1/10** | Prawie zerowe. Krytyczny blind spot. |
| PMax management | **5/10** | Analytics OK, management zero, feed-only nieobsługiwany |
| Display management | **2/10** | Placement + topic w CC, ale brak zarządzania |
| Video/YouTube management | **1/10** | Tylko typ w filtrze |
| Demand Gen | **0/10** | Nie istnieje w apce |
| DSA management | **0/10** | Nie istnieje w apce |
| Cross-channel optimization | **3/10** | PMax cannibalization sekcja, ale brak holistycznego widoku |
| E-commerce specifics | **2/10** | Brak: feed, seasonal, promotions, LTV, AOV |
| Automation/Actions | **5/10** | Recommendations engine świetny, ale za mało inline actions |
| Analytics depth | **9/10** | 35 sekcji w CC + dedykowane strony. Comprehensive. |
| Campaign type coverage | **2/10** | 1/14 typów z pełnym wsparciem (Search only) |

### Finalna ocena: **4.5/10** (z perspektywą pełnego Google Ads 2026)

- Playbook-only: 6.4/10
- Z e-commerce perspective: 5.5/10
- Z pełnym campaign type coverage: **4.5/10**

Ocena spada bo apka obsługuje **1 z 14 typów kampanii na pełnym poziomie**. To nie jest "Google Ads Helper" — to jest "Google Ads Search Helper". I to robi dobrze. Ale reszta ekosystemu Google Ads jest praktycznie niewidoczna.

**Ale:** Foundation jest solidny. Architecture jest czysta (routers → services → models). 107 API endpoints, 40+ reguł. Dodanie kolejnych typów kampanii to kwestia rozbudowy, nie przebudowy. Apka ma wzorce (filtry, tabele, karty, CC sekcje) które można replikować na nowe typy.

### Roadmap realistyczny (6 miesięcy)

| Miesiąc | Focus | Ocena po |
|---------|-------|----------|
| 1 | Shopping page + inline actions CC + auto-sync | 5.5/10 |
| 2 | Merchant Center + PMax management + sezonowość | 6.5/10 |
| 3 | DSA + cross-channel cannibalization + ad management | 7.0/10 |
| 4 | Display management + Video basics + Demand Gen filter | 7.5/10 |
| 5 | Conversion value optimization + LTV + promotions | 8.0/10 |
| 6 | Competitive analysis + CRO/GA4 + brand protection | 8.5/10 |

---

*Dokument wygenerowany jako kompletny audyt ekspercki. Pokrywa: 102 elementy UI na 15 stronach + playbook coverage (27 tasków) + beyond-playbook e-commerce perspective (13 wymiarów) + pełny przegląd 14 typów kampanii Google Ads. Łącznie 54 wymiary oceny.*
