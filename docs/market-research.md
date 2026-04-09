# Market Research — CEO Brief

```json
{
  "generated_at": "2026-04-10T12:00:00Z",
  "triggered_by": "manual",
  "top_actions": [
    "Dodaj detekcje nieautoryzowanych zmian Google (re-enabling paused keywords, auto-applied recs) — bol #1 w PPC community, GAH ma ChangeEvent ale brak alertu/dashboardu 'co Google zmienil bez mojej zgody'",
    "Upgrade SDK do 30.0.0 + sledzenie miesiecznych minor releases (v23.1, v23.2) — nowe pola/metryki dostepne szybciej, AI Max text guidelines w v23.1",
    "Rozpoznawanie kampanii AI Max for Search — nowy typ kampanii (globalny rollout luty 2026), GAH powinien klasyfikowac i audytowac"
  ],
  "competitor_insights": [
    { "tool": "Adalysis", "signal": "Per-asset RSA/PMax performance (clicks/conv per headline) + daily task list z team assignment", "gah_impact": "high" },
    { "tool": "Google Platform", "signal": "AI Max for Search — keyword-free campaigns + text guidelines, globalny rollout", "gah_impact": "high" },
    { "tool": "Groas", "signal": "Autonomiczne AI agenty (bidy/budgety/negatywne) w petli 24/7, $499/mies", "gah_impact": "medium" },
    { "tool": "Ryze AI", "signal": "Claude MCP integration — zarzadzanie Google+Meta Ads z czatu, white-label raporty", "gah_impact": "medium" },
    { "tool": "PPC.io", "signal": "10 AI audit agents za $16.99/mies — N-gram, landing page audit", "gah_impact": "low" }
  ],
  "user_pains": [
    { "pain": "Google auto-applies recs + re-enables paused keywords bez ostrzezenia (Low activity bulk changes)", "frequency": "high", "gah_solves": "partial" },
    { "pain": "20-40% search terms ukryte + broad match drift generuje niekonwertujace klikniecia", "frequency": "high", "gah_solves": "partial" },
    { "pain": "Wasted spend z braku negative keyword strategy — 20-30% budzetu na fixable mistakes", "frequency": "high", "gah_solves": "yes" },
    { "pain": "Budget pacing bez push alertow (email/Slack) i hourly granularity", "frequency": "medium", "gah_solves": "partial" },
    { "pain": "Cross-account bulk operations i porownanie kont A vs B", "frequency": "medium", "gah_solves": "partial" }
  ],
  "platform_alerts": [
    { "change": "SDK 30.0.0 wydany 2026-03-25 (GAH ma 29.1.0) — nowe pola z v23.1/v23.2", "priority": "high", "action_required": false },
    { "change": "Google Ads API — miesieczny cykl wydawniczy od v23 (minor wersje addytywne)", "priority": "high", "action_required": false },
    { "change": "AI Max for Search — nowy typ kampanii, text guidelines w API v23.1", "priority": "high", "action_required": false },
    { "change": "Oficjalny Google Ads MCP Server (read-only) — google-marketing-solutions/google_ads_mcp", "priority": "info", "action_required": false },
    { "change": "V23 sunset ok. styczen 2027 — 9 miesiecy zapasu", "priority": "info", "action_required": false }
  ],
  "market_summary": "Rynek PPC tools przesuwa sie w strone autonomicznych agentow AI (Groas, Ryze, PPC.io) i chat-first interfejsow. Najwiekszy bol uzytkownikow to niekontrolowane zmiany Google (auto-applied recs, re-enabling paused keywords). GAH ma solidna baze do wykrywania tych zmian (ChangeEvent, circuit breaker) ale brakuje alertu/dashboardu. API v23 stabilne, brak CRITICAL alertow, ale warto upgrade SDK do 30.0.0 i sledzic miesieczne releases.",
  "confidence": "high"
}
```

## Competitor Insights

### 1. Adalysis — Per-asset RSA/PMax performance + task list (HIGH)
Q1 2026: metryki per-asset dla RSA i PMax (klikniecia, konwersje, CTR per headline/description/image), plus daily task list z przydzielaniem zadan i przypomnieniami. GAH ma Audit Center i Daily Audit, ale nie ma widoku per-asset performance ani task assignment.

### 2. Google — AI Max for Search (HIGH)
AI Max for Search (keyword-free campaigns) globalny rollout. Text guidelines (brand exclusions, messaging restrictions) weszly w lutym 2026. GAH nie ma narzedzi do monitorowania/audytu kampanii AI Max.

### 3. Groas — Autonomiczne AI agenty ($499/mies) (MEDIUM)
Wyspecjalizowane AI agenty: bidy, budgety, negatywne slowa — 24/7 bez zatwierdzania. GAH = "safety-first helper z dry-run", Groas = "autopilot". Roznica w modelu.

### 4. Ryze AI — Claude MCP + Google/Meta Ads (MEDIUM)
2000+ marketerow, $500M+ ad spend. Integracja z Claude przez MCP — zarzadzanie kontami z czatu.

### 5. PPC.io — AI audit agents $16.99/mies (LOW)
10 gotowych AI agentow. GAH juz ma wiekszosc tych funkcji. Zagrozenie cenowe dla segmentu solo freelancer.

## User Pains

### 1. Auto-applied recommendations + re-enabled keywords (HIGH)
53% advertiserow uwaza zarzadzanie Google Ads za trudniejsze niz 2 lata temu. Google automatycznie reaktywuje wstrzymane slowa kluczowe przez "Low activity system bulk changes". GAH: ma ChangeEvent tracking ale brakuje alertu "co Google zmienil bez mojej zgody".

### 2. Hidden search terms 20-40% + broad match drift (HIGH)
Google ukrywa 20-40% search terms. Broad match rozszerzyl sie do synonimow. GAH: ma Search Terms Intelligence, segmentacja, semantic clustering, ngram. Brakuje: estymator ukrytych queries, alert "broad match drift".

### 3. Wasted spend — negative keyword strategy (HIGH, GAH SOLVES)
5-10 oczywistych winowajcow = 30-40% zmarnowanego budzetu. GAH: wasted-spend analysis, NKL CRUD, bulk actions, ngram — jeden z najsilniejszych obszarow.

### 4. Budget pacing without alerts (MEDIUM)
GAH: ma BudgetPacingModule z progami 75%/120%, MCC pacing. Brakuje: push alerty, hourly granularity, pacing forecast.

### 5. Cross-account bulk operations (MEDIUM)
GAH: ma MCC Overview, shared NKL. Brakuje: bulk operations cross-account, cross-account comparison.

## Platform Alerts

### 1. SDK 30.0.0 available (HIGH)
Wydany 2026-03-25. GAH ma 29.1.0 (ADR-019). Nowe pola z v23.1/v23.2.

### 2. Monthly release cycle (HIGH)
Od stycznia 2026 Google wydaje minor wersje co miesiac.

### 3. AI Max for Search (HIGH)
Nowy typ kampanii. API v23.1. GAH nie obsluguje AI Max-specific controls.

### 4. Official Google Ads MCP Server (INFO)
Google opublikowal oficjalny MCP server (read-only). Repo: google-marketing-solutions/google_ads_mcp.

### 5. V23 sunset ~Jan 2027 (INFO)
9 miesiecy zapasu. Brak pilnych deprecations.
