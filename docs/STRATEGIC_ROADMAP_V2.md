# Strategic Roadmap v2 — Google Ads Helper

> Wygenerowane 2026-03-27 przez burzę mózgów Strategist + CTO agents.
> Status: DRAFT — pomysł na przyszłość, do weryfikacji z userem.

## Stan wyjściowy (2026-03-27)

- Roadmapa v1: 16/25 done (64%), Wave 1-2 complete
- Codebase: 195 endpoints, 16 serwisów, 26 modeli, 477 testów
- Frontend: 16 stron, 18 komponentów, build OK
- DB: 26 tabel, 10MB SQLite
- 0 TODO/FIXME, 17 ADR-ów

## Główna teza

Przejście z "narzędzia analitycznego" → "proaktywnego asystenta PPC z AI w core".
Trzy fundamentalne braki: proaktywność (manual sync), inteligencja (AI jako add-on), skalowalność (single-user).

---

## FAZA I — Quick Wins + Fundament (tydzień 1-2)

### 1. SQLite WAL + indeksy
- **Kategoria:** PERFORMANCE | **Nakład:** S (1-2h) | **Risk:** LOW
- PRAGMA journal_mode=WAL, synchronous=NORMAL, cache_size=-64000
- Indeksy: MetricDaily(campaign_id, date), KeywordDaily(keyword_id, date), SearchTerm(client_id, campaign_id)

### 2. Code splitting + lazy loading
- **Kategoria:** PERFORMANCE | **Nakład:** S (2-3h) | **Risk:** LOW
- React.lazy() na 16 stronach, Suspense z skeleton loader
- Vendor chunks: recharts, @tanstack/react-table osobno
- Bundle 600→150kB initial load

### 3. AI Prompt Cache + Structured Output
- **Kategoria:** AI | **Nakład:** M (4-6h) | **Risk:** LOW
- AIProvider protocol (abstraction layer)
- Cache: sha256(prompt) → response, TTL 1h
- Structured JSON output → Pydantic → render Markdown w froncie

### 4. Claude API Direct Integration
- **Kategoria:** AI | **Nakład:** M (4-6h) | **Risk:** LOW
- anthropic SDK zamiast/obok subprocess `claude -p`
- Kontrola: model, temperature, max_tokens
- API key w keyring (wzorzec ADR-004)
- Fallback chain: API → CLI → error

---

## FAZA II — Proaktywność (tydzień 2-4)

### 5. Background Scheduler (APScheduler)
- **Kategoria:** AUTOMATION | **Nakład:** M (6-8h) | **Risk:** MEDIUM
- APScheduler AsyncIOScheduler w FastAPI lifespan
- Sync co 6h (konfigurowalne per client)
- Chain: sync → recommendations → anomalies → health score
- Job store: SQLAlchemyJobStore na SQLite

### 6. AI Morning Brief (Autonomous Digest)
- **Kategoria:** AI + AUTOMATION | **Nakład:** M (4-6h) | **Priorytet:** P0
- Po scheduled sync: AI generuje brief z anomaliami, waste, priorytetami
- Windows toast notification + in-app
- "3 anomalie, 2 kampanie przekroczyły budżet, priorytet #1: ..."

### 7. AI Anomaly Narratives
- **Kategoria:** AI | **Nakład:** M (4-6h) | **Risk:** LOW
- Batch alerty per client → 1 LLM call → narrative z root cause
- Kontekst: ChangeEvent + keywords + search terms
- Cache 24h, max 10 alertów per narrative

### 8. Rules Engine (JSON-driven)
- **Kategoria:** AUTOMATION | **Nakład:** L (2-3d) | **Risk:** MEDIUM
- Model AutoRule: condition_json (AND/OR tree) + action_type + cooldown
- Actions: PAUSE_KEYWORD, ADD_NEGATIVE, ALERT, ADJUST_BID
- 5 presetów (clean_waste, pause_burning, etc.)
- Evaluator po każdym sync, przez circuit breaker

---

## FAZA III — Inteligencja + Skala (tydzień 4-7)

### 9. Multi-Account Portfolio Dashboard
- **Kategoria:** SCALE | **Nakład:** M (6-8h) | **Priorytet:** P0
- Widok "wszystkie konta": KPI per client, traffic light, drill-down
- Sortowalna tabela z health score, alert count, spend, CPA, ROAS

### 10. AI Task Queue z priorytetyzacją
- **Kategoria:** AI + UX | **Nakład:** M (6-8h)
- AI-ranked: "zrób NAJPIERW te 3 (oszczędzisz 2000zł/tydz)"
- Uczy się z historii — które akcje miały najlepszy ROI

### 11. Predictive Budget Optimizer
- **Kategoria:** AI | **Nakład:** L (1-2d)
- Regression na KeywordDaily (90 dni danych)
- What-if simulation: "przesuń 500zł z A do B → +12 konwersji"

### 12. Auction Insights + Competitive Intel
- **Kategoria:** AI + AUTOMATION | **Nakład:** L (1-2d)
- Nowy sync phase, model Competitor
- Tracking competitors over time, alerty o nowych graczach

---

## FAZA IV — Monetyzacja + Moat (tydzień 7-10)

### 13. Client-Facing Report Portal
- **Kategoria:** SCALE + UX | **Nakład:** M (6-8h)
- Branded PDF/HTML export z logo klienta
- Opcjonalnie: hosted link (static page)

### 14. Cross-Account Learning Engine
- **Kategoria:** AI + SCALE | **Nakład:** L (2-3d)
- Transfer patterns między kontami
- "W 8/12 kont e-commerce, broad match < 2zł konwertuje lepiej"
- Efekt sieciowy — im więcej kont, tym lepsze rekomendacje

### 15. Notifications (Toast + Webhook + Slack)
- **Kategoria:** AUTOMATION | **Nakład:** M (4-6h)
- Windows toast (plyer), webhook URL (Slack/Discord/Zapier)
- Rate limit: max 1/h/typ

---

## Mapa zależności

```
[1] SQLite WAL
[2] Code Splitting
[3] AI Cache ──► [7] Anomaly Narratives, [10] AI Task Queue, [11] Budget Optimizer
[4] Claude API ──► [14] Cross-Account Learning
[5] APScheduler ──► [6] Morning Brief, [8] Rules Engine, [15] Notifications
[9] Portfolio ──► [13] Report Portal
```

## Competitive Moat

| Cecha | Optmyzr ($250) | Adalysis ($150) | My (docelowo) |
|-------|---------------|----------------|---------------|
| Native AI (nie chatbot) | Nie | Nie | Tak |
| What-if budget simulation | Nie | Nie | Krok 11 |
| AI root cause analysis | Nie | Nie | Krok 7 |
| Cross-account learning | Nie | Nie | Krok 14 |
| Desktop (offline) | Nie | Nie | Tak |

## Monetyzacja (docelowa)

| Tier | Cena | Zawiera |
|------|------|---------|
| Solo | $49/msc | 3 konta, manual sync, raporty, rekomendacje |
| Agency | $149/msc | 15 kont, scheduler, rules, portfolio, reports |
| Enterprise | $299/msc | Unlimited, cross-account AI, white-label, webhooks |

## Łączny nakład

~60-80h roboczych (3-4 tygodnie solo, 1.5-2 tygodnie z AI-assisted coding)
