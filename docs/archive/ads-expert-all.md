# Ocena eksperta Google Ads — WSZYSTKIE ZAKŁADKI
> Data: 2026-03-25 | Przegląd: 15 zakładek | Werdykt zbiorczy: APLIKACJA SOLIDNA, 4 ZAKŁADKI DO MODYFIKACJI

## TL;DR
Aplikacja pokrywa ~85% codziennych potrzeb specjalisty Google Ads. Silne strony: SearchOptimization (25 narzędzi!), Dashboard (po sprintach 1-3), Campaigns detail view, SearchTerms z bulk actions. Słabe punkty: Forecast (beta z bugiem), Semantic (hardcoded daty, brak akcji), brak cross-navigation między zakładkami.

---

## Oceny zbiorcze

| # | Zakładka | Potrzebność | Kompletność | Wartość vs GAds | Priorytet MVP | Średnia | Werdykt |
|---|----------|-------------|-------------|-----------------|---------------|---------|---------|
| 1 | **Dashboard** (Pulpit) | 9 | 9 | 8 | 10 | **9.0** | ZACHOWAC |
| 2 | **Campaigns** | 9 | 9 | 8 | 9 | **8.8** | ZACHOWAC |
| 3 | **Keywords** | 9 | 9 | 8 | 9 | **8.8** | ZACHOWAC |
| 4 | **SearchTerms** | 10 | 9 | 9 | 10 | **9.5** | ZACHOWAC |
| 5 | **Recommendations** | 9 | 8 | 8 | 9 | **8.5** | ZACHOWAC |
| 6 | **DailyAudit** | 8 | 7 | 9 | 8 | **8.0** | ZMODYFIKOWAC |
| 7 | **Alerts** | 7 | 7 | 7 | 7 | **7.0** | ZACHOWAC |
| 8 | **ActionHistory** | 6 | 8 | 7 | 5 | **6.5** | ZACHOWAC |
| 9 | **SearchOptimization** | 10 | 9 | 10 | 8 | **9.3** | ZACHOWAC |
| 10 | **Forecast** | 6 | 4 | 5 | 4 | **4.8** | ZMODYFIKOWAC |
| 11 | **Semantic** | 7 | 5 | 7 | 5 | **6.0** | ZMODYFIKOWAC |
| 12 | **QualityScore** | 8 | 7 | 7 | 6 | **7.0** | ZACHOWAC |
| 13 | **Agent** | 7 | 8 | 9 | 6 | **7.5** | ZACHOWAC |
| 14 | **Reports** | 7 | 8 | 8 | 5 | **7.0** | ZACHOWAC |
| 15 | **Settings** | 5 | 6 | 3 | 4 | **4.5** | ZMODYFIKOWAC |

---

## Szczegółowa ocena per zakładka

### 1. Dashboard (Pulpit) — 9.0/10
**Werdykt: ZACHOWAC**

Po sprintach 1-3 dashboard jest kompletny: 7 KPI cards (clicks, cost, conversions, ROAS, impressions, CTR, CPA + Wasted Spend), Health Score z nawigacją do /alerts, InsightsFeed z przyciskami "Przejdź →", TrendExplorer, WoW comparison chart, tabela kampanii z metrykami performance (cost, conversions, ROAS), Budget Pacing, Device/Geo breakdown z share_cost_pct, Impression Share widget.

- Playbook coverage: Daily Checks (1.1) — pełne
- Brakuje: Impression Share Lost IS per campaign w tabeli (minor)

### 2. Campaigns — 8.8/10
**Werdykt: ZACHOWAC**

Bardzo bogaty detail view: 10 KPI metryk (w tym IS, Top IS, Lost IS Budget/Rank), Trend Explorer z action markers, Action History Timeline, Campaign Role Management, Device + Geo breakdowns per kampania. Nawigacja do Keywords i SearchTerms z filtrem campaign_id. Filtrowanie po dacie, typie, statusie.

- Playbook coverage: Weekly Reviews (1.1) — pełne
- Brakuje: Sortowanie tabeli kampanii na liście bocznej

### 3. Keywords — 8.8/10
**Werdykt: ZACHOWAC**

4 zakładki: Positive Keywords (sortowalna tabela z QS, IS, smart hints Pause/Bid Up/Bid Down), Negative Keywords (CRUD z modali), Negative Keyword Lists (accordion + apply to campaigns), Keyword Expansion (sugestie z priority score). Export CSV/XLSX. Filtrowanie po match type, scope, campaign.

- Playbook coverage: Keyword Optimization (1.1 Weekly), Search Terms Intelligence (4.1) — pełne
- Smart hints realizują playbook reguły 1-3 (pause/bid up/bid down)

### 4. SearchTerms — 9.5/10 ⭐
**Werdykt: ZACHOWAC** — najlepsza zakładka

4 widoki: Segments (High Performers/Waste/Irrelevant/Other z bulk actions), List (paginated + sortable), Trends, Close Variants. Bulk "Add as negatives" i "Add as keywords" z dialogiem ad group. Waste callout alert z sugestiami. Export CSV/XLSX.

- Playbook coverage: Search Terms Intelligence (4.1 "⭐ NAJWAŻNIEJSZE") — pełne
- Realizuje playbook reguły 4 i 5 (add keyword, add negative) jako one-click bulk actions

### 5. Recommendations — 8.5/10
**Werdykt: ZACHOWAC**

Karty rekomendacji z priorytetyzacją HIGH/MEDIUM/LOW, Apply z dry-run preview, Dismiss, Bulk select + apply. Filtrowanie po priority, source, executability, category. Export CSV. Summary KPIs (total, high priority, executable, success rate).

- Playbook coverage: Automated Recommendations (5.3) — pełne
- Brakuje: Scheduling rekomendacji (auto-apply w przyszłości)

### 6. DailyAudit (Poranny przegląd) — 8.0/10
**Werdykt: ZMODYFIKOWAC**

KPI summary (current vs previous), 4 Quick Scripts (Clean Waste, Pause Burning, Boost Winners, Emergency Brake) z dry-run → confirm flow.

- Playbook coverage: Daily Optimization Flow (3.1) — częściowe
- Co brakuje (krytyczne):
  - **Brak date filtering** — snapshot only, specjalista chce porównać wczoraj vs przedwczoraj
  - **Brak search terms review** — playbook mówi "⭐ NAJWAŻNIEJSZE" ale DailyAudit nie linkuje do SearchTerms
  - **Brak anomaly summary** — powinien wyświetlać alerty z Alerts bez konieczności nawigacji
- Co dodać: link do SearchTerms (new waste terms), mini-alert feed, date selector

### 7. Alerts (Monitoring) — 7.0/10
**Werdykt: ZACHOWAC**

2 zakładki: Business Alerts (resolve/unresolve) i Z-Score Anomalies (metric/threshold/period selector). Anomaly detection z configurable σ threshold.

- Playbook coverage: Anomaly Detection (5.1) — pełne
- Brakuje: Alert rules configuration (user-defined thresholds), notification system

### 8. ActionHistory — 6.5/10
**Werdykt: ZACHOWAC**

5 zakładek: Helper, External, Unified timeline, Impact (cost changes), Strategy (bid strategy changes). Revert actions, diff view. Date filtering.

- Playbook coverage: Rule history & rollback (v2 features) — częściowe
- Priorytet MVP: NISKI — specjalista rzadko przegląda historię, ale jest potrzebna do audytu

### 9. SearchOptimization — 9.3/10 ⭐
**Werdykt: ZACHOWAC** — najbardziej zaawansowana zakładka

25 narzędzi w sekcjach zwijanych: Wasted Spend, Dayparting, Match Type Analysis, N-gram Analysis, RSA Analysis, Landing Pages, Hourly Dayparting, Account Structure Audit, Bidding Strategy Advisor, Conversion Tracking Health, Ad Group Health, Smart Bidding Health, Pareto 80/20, Scaling Opportunities, Target vs Actual, Learning Status, Portfolio Health, Conversion Quality, Demographics, PMax Channels, Asset Groups, PMax Search Themes, Audience Performance, Missing Extensions, Extension Performance.

- Playbook coverage: CAŁA CZĘŚĆ 2 (metryki), CZĘŚĆ 3 (workflow), CZĘŚĆ 4 (strategie specjalizowane) — niemal kompletna
- Jedyna zakładka pokrywająca Monthly Deep Dives (1.1)
- Brakuje: Sortowanie w tabelach, inline actions (np. pause keyword z wasted spend)

### 10. Forecast (Prognoza) — 4.8/10
**Werdykt: ZMODYFIKOWAC** — najsłabsza zakładka

Linear regression forecast (7 dni) z confidence interval. Campaign selector + metric pills. 4 KPI cards (trend, forecast avg, R², slope).

- Playbook coverage: Predictive Analytics (5.2) — minimalne
- Problemy krytyczne:
  - **BUG**: Retry button odwołuje się do niezdefiniowanej funkcji `loadForecast()`
  - **Hardcoded 7 dni** — brak wyboru horyzontu prognozy
  - **Brak date filtering** — nie reaguje na FilterContext
  - **Tylko linear regression** — zbyt prosty model
- Co naprawić: fix bug, dodać date filtering, dodać wybór horyzontu (7/14/30 dni)

### 11. Semantic (Inteligencja) — 6.0/10
**Werdykt: ZMODYFIKOWAC**

Semantic clustering search terms z cost filtering (>10/>50/>100 zł). Expandable cluster cards z listą termów.

- Playbook coverage: Semantic Clustering (4.1 krok 2) — częściowe
- Problemy:
  - **Hardcoded dates** — `days: 30` w kodzie, nie reaguje na FilterContext
  - **Brak akcji** — waste clusters wykryte ale brak "Add as negative" bulk action
  - **Brak search** — nie można szukać konkretnego termu w klastrach
- Co naprawić: podpiąć FilterContext, dodać bulk negative action per cluster

### 12. QualityScore — 7.0/10
**Werdykt: ZACHOWAC**

QS audit: rozkład 1-10 (bar chart), avg QS, low QS keywords z diagnostyką + rekomendacjami.

- Playbook coverage: Quality Score Optimization (4.3) — częściowe
- Brakuje: QS trend over time, CPC impact prediction, inline actions (fix QS)
- Snapshot only — brak date filtering (QS jest snapshotem z natury, więc OK)

### 13. Agent (Raport AI) — 7.5/10
**Werdykt: ZACHOWAC**

Chat z AI (Claude via SSE streaming). 6 quick prompts, token usage, markdown rendering.

- Unikalna wartość: free-form pytania do danych konta
- Mature implementation: SSE, auto-scroll, error handling, timeout
- Brakuje: Chat history persistence (po odświeżeniu ginie)

### 14. Reports (Raporty) — 7.0/10
**Werdykt: ZACHOWAC**

Generator raportów (Monthly/Weekly/Health) z SSE streaming + saved report browser. Sekcje: Month Comparison, Campaign Detail, Change History, Change Impact, Budget Pacing, AI Narrative.

- Unikalna wartość: automatyczne raporty z AI podsumowaniem
- Brakuje: Export do PDF, scheduled generation, email delivery

### 15. Settings (Ustawienia) — 4.5/10
**Werdykt: ZMODYFIKOWAC**

Client config: info, strategy, business rules, safety limits, hard reset.

- Problemy:
  - **Brak form validation** — można wpisać ujemne wartości, brak min/max
  - **Brak dirty state tracking** — nie ostrzega o niezapisanych zmianach
  - **Niska wartość dla specjalisty** — ustawienia raz konfiguruje się na początku
- Co naprawić: walidacja formularza, dirty state warning, grouping sekcji

---

## Ranking zakładek wg priorytetu MVP

| Priorytet | Zakładki | Uzasadnienie |
|-----------|----------|-------------|
| **TIER 1 — Must Have** | Dashboard, Campaigns, Keywords, SearchTerms, Recommendations | Codzienne narzędzia specjalisty. Bez nich apka jest bezużyteczna. |
| **TIER 2 — High Value** | SearchOptimization, DailyAudit, Alerts | Tygodniowe/comiesięczne analizy. Ogromna wartość dodana vs Google Ads UI. |
| **TIER 3 — Nice to Have** | Agent, Reports, QualityScore | Przydatne ale nie krytyczne na co dzień. |
| **TIER 4 — Optional** | Forecast, Semantic, ActionHistory, Settings | Rzadko używane lub wymagające dopracowania. |

---

## Cross-navigation — brakujące połączenia

| Z | Do | Jak powinno działać |
|---|----|--------------------|
| DailyAudit | SearchTerms | "Nowe waste terms →" link do segmented view z filtrem WASTE |
| DailyAudit | Alerts | Mini-feed alertów lub "X aktywnych alertów →" |
| QualityScore | Keywords | Kliknięcie keyword z niskim QS → Keywords z filtrem |
| Semantic | SearchTerms | Kliknięcie waste cluster → bulk add as negative |
| Forecast | Campaigns | Kliknięcie kampanii w forecaście → Campaign detail |
| Alerts | Campaigns | Kliknięcie alertu z campaign_id → Campaign detail |

---

## Top 5 rekomendacji (priorytet)

1. **FIX: Forecast retry bug** — `loadForecast()` undefined, 5 min fix
2. **FIX: Semantic + Forecast date filtering** — podpiąć do FilterContext zamiast hardcoded values
3. **ADD: DailyAudit cross-links** — link do SearchTerms (waste), mini-alert feed
4. **ADD: SearchOptimization inline actions** — "Pause keyword" z Wasted Spend, "Add negative" z N-gram
5. **ADD: Form validation w Settings** — min/max constraints, dirty state warning
