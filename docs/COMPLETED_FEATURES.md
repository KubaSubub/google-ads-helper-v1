# Completed Features — DO NOT MODIFY UNLESS ASKED

These features are done and tested. Do NOT refactor, "improve", or touch them without explicit user request.

---

## PMax Search Terms
- `sync_pmax_search_terms()` uses `campaign_search_term_view` (NOT `search_term_view`, NOT `campaign_search_term_insight`)
- CRITICAL: Do NOT add `segments.keyword.info.*` to campaign_search_term_view queries — it filters out PMax data
- SearchTerm model: `ad_group_id` is nullable (PMax has no ad_groups), `campaign_id` FK for PMax direct link, `source` column ("SEARCH"/"PMAX")
- Sync Phase 5b calls `sync_pmax_search_terms()` after standard `sync_search_terms()`

## Global Date Range Picker
- DateRangePicker component lives in Sidebar.jsx (after client selector, before nav)
- FilterContext exposes: `filters.period`, `filters.dateFrom`, `filters.dateTo`, computed `days`
- Period preset (7/14/30/90) auto-sets dateFrom/dateTo. Custom dates clear period to null.
- Pages using dates: Dashboard (`days`), Campaigns (`days`), TrendExplorer (`days`), SearchTerms (`date_from`/`date_to`), Keywords (`date_from`/`date_to` via KeywordDaily)
- Campaigns list: snapshot data — NO date filtering
- Keywords: date filtering aggregates from `keywords_daily` table (SUM per keyword); without dates falls back to Keyword snapshot
- FilterBar period pills hidden (`hidePeriod`) since dates are global in sidebar

## AppContext — Centralized Client State
- `clients`, `clientsLoading`, `refreshClients` live in AppContext (NOT useClients hook)
- Sidebar.jsx reads clients from useApp(), NOT from useClients()
- After discover, clients appear immediately in sidebar dropdown

## Auth Setup Wizard
- `GET /auth/setup-status`, `POST /auth/setup` endpoints in auth.py
- Login.jsx has step-by-step credential setup before Google OAuth
- All tokens stored in Windows Credential Manager via keyring

## KeywordDaily (Date Aggregation)
- Model `KeywordDaily`: keyword_id + date → clicks, impressions, cost_micros, conversions, conversion_value_micros, avg_cpc_micros
- Router `keywords_ads.py`: two paths — daily aggregation (with date_from/date_to) vs snapshot (without dates)
- Seed: 90 days per keyword with trend + dow + noise factors
- Summable metrics in KeywordDaily; snapshot metrics (quality_score, impression_share, bid) stay on Keyword model

## SEARCH Optimization Page
- `SearchOptimization.jsx` — 6 collapsible analysis sections
- Endpoints: dayparting, rsa-analysis, ngram-analysis, match-type-analysis, landing-pages, wasted-spend
- Backend: 6 methods in analytics_service.py + 6 routes in analytics.py
- Sidebar nav: "Optymalizacja" (Zap icon) in ANALIZA group

## Keyword Lifecycle Cleanup + Canonical SQLite
- Successful sync of campaigns, ad groups, and keywords now marks unseen local rows as `REMOVED`.
- Keyword list hides `REMOVED` by default and can include them explicitly via `include_removed` / `Pokaz usuniete`.
- Keyword API returns campaign and ad group context directly (`campaign_id`, `campaign_name`, `ad_group_name`).
- Runtime SQLite path is canonicalized to `<repo>/data/google_ads_app.db`; legacy `backend/data/google_ads_app.db` is migrated once if needed.

## Negative Keyword Hardening
- Positive keywords and negative keyword criteria are cached separately: `keywords` vs `negative_keywords`.
- Both caches use explicit `criterion_kind` values (`POSITIVE`, `NEGATIVE`).
- Positive sync has multi-layer guards against `negative=true` rows.
- Negative keyword sync now covers campaign-level and ad-group negatives and stores them in `negative_keywords`.
- Backend exposes `GET /negative-keywords/` and source-of-truth debug differentiates DB positive vs DB negative rows.

## Client Hard Reset
- `POST /clients/{id}/hard-reset` deletes only the selected client's local runtime data and keeps the client record.
- Settings page requires exact-name confirmation before reset.
- Reset clears campaigns and cascaded cache data plus direct client tables like recommendations, action logs, alerts, change events, negatives, and sync logs.

## AI Agent (Raport AI)
- Claude Code headless integration via subprocess (`claude -p --output-format stream-json`).
- Backend: `AgentService` gathers data from existing services (KPIs, campaigns, keywords, search terms, alerts, recommendations, budget pacing), builds prompt, streams response via SSE.
- Router: `agent.py` with `/agent/status` and `/agent/chat` endpoints, single-request lock prevents concurrent generation.
- Frontend: `Agent.jsx` — chat interface with quick report buttons, SSE stream parsing, markdown rendering.
- Quick report types: weekly, campaigns, keywords, search_terms, budget, alerts, freeform.

