# CEO Decision Log

## [2026-04-09] MCC Overview: Sprint 1 fixes + E2E lock
- **Powod:** User chce domknac MCC overview — naprawic 4 quick wins z ads-verify i zablokowac widok testami przed regresja
- **Intelligence used:** NIE (task specyficzny, nie wymagal market research)
- **Naklad:** S (4 fixy) + M (comprehensive lock tests)
- **Delegacja:** bezposrednia implementacja — SKIP PM (istniejacy plan ads-verify-mcc-overview.md)
- **Scope:**
  - Z1: ROAS 0% consistency fix (backend)
  - Z2: IS auto-hide gdy brak danych (frontend)
  - N3: Pacing tooltip z budżet/wydano (frontend)
  - N4: Health score kolumna (backend + frontend)
  - LOCK: rozbudowane testy backend + frontend E2E
- **Status:** DONE
- **Wynik:** 4 fixy Sprint 1 + 22 nowych lock tests = 45 MCC testów, 532 total backend, build OK

## [2026-04-09] Wave 5: Settings tab UX overhaul
- **Powód:** Settings to daily-use tab — ma UX issues: prompt() do konkurentów, brak polskich znaków, brak info o sync, brak reset defaults dla safety limits
- **Intelligence used:** TAK — competitor insight: Adalysis ma task list + scheduled features; user pain: zarządzanie wieloma kontami wymaga dobrego Settings UX
- **Nakład:** M
- **Delegacja:** /pm build settings-ux-overhaul → /cto → /feature
- **Status:** DONE
- **Wynik:** 7/7 AC zrealizowanych, review 8/10 PASS, build OK, 532 testów OK

## [2026-04-10] MCC Overview: Sprint 2 — waluta + sparkline
- **Powód:** User poprosił o Sprint 2 z ads-verify-mcc-overview.md (N2 waluta przy kwotach, N5 sparkline trendu wydatków)
- **Intelligence used:** TAK — competitor insight: Adalysis dodał per-asset breakdown; user pain: cross-account management wymaga szybkiego porównania trendów
- **Nakład:** M (N2 wymaga currency na Client model + reseed; N5 wymaga nowy endpoint + Recharts)
- **Delegacja:** SKIP PM (istniejący plan ads-verify) → /build mcc-overview-sprint2
- **Status:** DONE
- **Wynik:** N2 currency + N5 sparkline zaimplementowane, 7 nowych lock tests, 539 total backend, build OK. Review: security 7.5/10, domain 8/10. Mixed-currency KPI naprawiony po review.

## [2026-04-10] Settings: Client Info Hub + AI Context store
- **Powód:** User re-frame Settings — to nie jest formularz edycji klienta, tylko persistent context hub dla klienta (ustawienia + info). Dane stąd będą konsumowane przez: rekomendacje, raporty, i przyszły AI agent. Ads-user review (2026-03-29, 6/10) wskazał 4 brakujące obszary: conversion tracking visibility, linked accounts, account metadata, currency spójność. Settings UX overhaul (2026-04-09) naprawił kosmetykę — teraz czas na warstwę informacyjną świadomą Google Ads.
- **Intelligence used:** TAK — user_pains z market-research.md (auto-applied changes, wasted spend, cross-account confusion) są pośrednio adresowane przez lepszy client context visibility. Competitor gap: żaden z konkurentów (Adalysis, Groas, Ryze, PPC.io) nie ma dedykowanego "client info hub" — unique angle dla GAH.
- **Nakład:** M (3-4h)
- **Delegacja:** /pm build settings-client-info-hub → /cto --spec {path}
- **Scope:**
  1. Health & Metadata (NOWA sekcja u góry Settings) — read-only z Google Ads API:
     - Account metadata: timezone, currency, account_status, auto_tagging, tracking_url_template
     - Sync health: last sync + freshness badge (green <6h / yellow <24h / red >24h)
     - Conversion tracking: count aktywnych ConversionAction + attribution model + enhanced conversions flag
     - Linked accounts shell (B2): GA4/GMC/YT/Search Console detected z Google Ads API linked resources, status "linked ✓" / "not linked" (bez głębokich danych z external API)
  2. AI Context — strukturyzacja business context (rozszerzenie istniejącej sekcji "Reguły biznesowe"):
     - target_cpa, target_roas, ltv_per_customer, profit_margin_pct (numeric)
     - priority_conversions (multi-select z aktywnych ConversionAction)
     - brand_terms (tag input)
     - Wszystko w istniejącym business_rules JSON → zero DB migration
  3. Currency fix: usunięcie hardcoded USD w Settings.jsx, użycie client.currency wszędzie
  4. Composite endpoint /clients/{id}/health agregujący wszystko z (1) — jeden call zamiast 4
- **AI-ready framing:** Pola z punktu (2) są strukturalne — LLM może je czytać bezpośrednio bez parsowania notatek. To fundament pod przyszły AI agent (plan v2/v3 z project_agent_sdk_vision.md).
- **Status:** DONE
- **Wynik:** GET /clients/{id}/health + client_health_service.py + ClientHealthSection.jsx + 6 AI context fields (target_cpa, target_roas, ltv, margin, brand_terms, priority_conversions) + currency fix. 596 backend tests, 4 E2E, build OK. Review 8/10. GAQL injection guard, freshness 12h threshold, MANAGER/CLIENT terminology (API v23).
- **Post-ship hotfix (commit e384cd1):** ClientHealthSection nie renderowało się na realnym backendzie — `setHealth(r.data)` zamiast `setHealth(data)` (api.js interceptor już unwrapuje response.data). Fix + 2 nowe E2E asercujące DOM (złapałyby bug). Weryfikacja wizualna przez Playwright na real backend — karty widoczne z danymi Sushi Naka Naka.

## [2026-04-10] Settings: Mastermind brief pivot (anty-duplikacja + strategic context)
- **Powód:** Początkowo plan P0/P1 bugfix sprint (konwersje + linked accounts + attribution + sync badge) — ale głęboki gap analysis wykazał że ClientHealthSection (wdrożony wczoraj) w 100% duplikuje dane z Dashboard / Daily Audit / Kampanie / Monitoring / Historia zmian. Technical recon v23 SDK potwierdził że linked accounts (GA4/YT/SC) NIE są queryable. User pivot: "Ja tu nie chce żadnych wyników, czy syncrho działa to jest w innym miejscu. Musisz zobaczyć co już jest w przeglądach i danych kampanii bo powielasz mi działanie. Potrzebuję masterminda marketingowego na temat klienta — jak byśmy go briefowali."
- **Intelligence used:** TAK — gap analysis + pm-context (Kuba brief style), Obsidian integration jako future operational brain.
- **Nakład:** L (6-7h) — user eksplicytnie zatwierdził Option 1 (full 5 sekcji).
- **Delegacja:** /pm build settings-mastermind-brief → /cto --spec {path}
- **Scope (zatwierdzony przez usera, 5 pytań × 5 odpowiedzi):**
  1. **DELETE częściowo ClientHealthSection** — usuwamy karty Konto, Synchronizacja, Połączenia (100% duplikat istniejących sekcji Settings + Dashboard/Daily Audit). **KEEP Konwersje card ALE REFRAME** jako "Cele konwersji" — checkbox selection przy każdej konwersji mapowany do istniejącego `business_rules.priority_conversions`. User: "konwersje mogą zostać bo to są nasze CELE, które tutaj też będziemy określać".
  2. **Storage: Option B** — nowa JSON kolumna `strategy_context` na Client model, dodawana automatycznie przez `_ensure_sqlite_columns` (wzór: `currency`). Clean semantic separation od business_rules.
  3. **Scope: Option 1 (pełne 5 sekcji)** — user chce kompletną wizję, nie MVP.
  4. **Raw textarea** dla Strategia/Roadmap, z myślą o przyszłej integracji z Obsidian ("osobny mózg operacyjny"). Pola powinny być markdown-friendly (do exportu/synca z Obsidian w przyszłości).
  5. **Log decyzji — READ-ONLY dla MVP**. User: "Log decyzji będzie pisany nie przeze mnie tylko AI który będzie proponował rozwiązania i sprawdzał poprawność zmian". Dla MVP: empty state z labelem "AI zostanie dołączony w v2". Struktura AI-friendly (JSON list z timestamp, action_type, entity, rationale, validation_result).
- **Finalna struktura Settings:**
  1. Cele konwersji (NEW — reworked z Konwersje card, checkbox priority_conversions)
  2. Informacje ogólne (existing)
  3. Strategia i konkurencja (existing)
  4. Strategia marketingowa (NEW, textarea raw, markdown-friendly)
  5. Plan działań / Roadmap (NEW, textarea raw, markdown-friendly)
  6. Log decyzji (NEW, AI-written, MVP read-only empty state)
  7. Wnioski i lessons learned (NEW, structured list wins/losses/tests)
  8. Brand voice & zakazy (NEW, 2 textarea)
  9. Reguły biznesowe (existing, AI context fields)
  10. Limity bezpieczeństwa (existing)
  11. Synchronizacja (existing, scheduled config)
  12. Konta MCC (existing)
  13. Twardy reset (existing)
- **DELETE konkretnie:**
  - Z Settings.jsx: 3 karty z ClientHealthSection (Konto + Synchronizacja + Połączenia), imports unused
  - ClientHealthSection.jsx — keep file, reduce do pojedynczej "Cele konwersji" sekcji, rename pliku na `ConversionGoalsSection.jsx`
  - Backend `/clients/{id}/health` endpoint — ZOSTAWIAMY (ma testy, może się przydać w przyszłości, nie usuwamy working code)
  - Obsolete spec `settings-hub-p0-fixes.md` — overwrite z nową spec `settings-mastermind-brief.md` (same file reuse)
- **AI-ready framing:** Wszystkie 5 nowych sekcji + existing business_rules fields tworzą STRUCTURED CONTEXT BRIEF który AI agent (z project_agent_sdk_vision.md) będzie konsumował do: (a) generowania rekomendacji, (b) pisania raportów, (c) walidacji zmian, (d) auto-dodawania wpisów do Log decyzji. Obsidian sync planned dla Strategia + Roadmap w przyszłości (bi-directional).
- **OUT OF SCOPE (V1):**
  - Markdown editor z toolbar (MVP = raw textarea)
  - Obsidian integration (future feature)
  - AI auto-write do Log decyzji (wymaga AI agent który jeszcze nie istnieje)
  - Historical performance vs strategy comparison
  - Cross-client strategy templating
- **Status:** DONE
- **Wynik:** 607 backend tests passed (+11 nowych dla strategy_context), 10/10 E2E settings-mastermind-brief (+ 4 istniejące settings-client-info-hub), vite build OK. Review iter 2: code 8/10, security 7/10, domain 8/10 po fixach CRITICAL findings (PATCH null-noop, primary_for_goal column w UI + schema, description min 10 chars backend+frontend, remove lesson E2E test, unused imports cleanup). Wizualna weryfikacja przeciwko realnemu backendowi: wszystkie 9 nowych elementów DOM renderuje się dla Sushi Naka Naka (18 real conversion actions). Obsolete `ClientHealthSection.jsx` pozostawiony jako dead code (sandbox denied delete, user can remove manually). Obsolete spec `settings-hub-p0-fixes.md` pozostawiony jako draft (zastąpiony przez settings-mastermind-brief.md).

## [2026-04-12] Scripts System: P0 + P1 fixes po full review
- **Powod:** CEO review (4 parallel agents: backend/frontend/domain/UX live test) wykryl 2 bugi P0 (D1 cross-campaign negative push + A2 AD_GROUP branching) i systemowa luke P1 (validate_action nie wired w scripts pipeline) + brakujace brand/keyword protection w A1/A6/C2. Bez tych napraw execute() ma funkcjonalne bledy i circuit breaker jest martwy dla calego scripts flow. User wymaga "110%" naprawy przed shipem.
- **Intelligence used:** NIE (task specyficzny — naprawy wykryte we wlasnym review, nie wymagaja market research)
- **Nakład:** L (6 plikow skryptow + base.py refactor + nowy _helpers.py + frontend ScriptsPage + 7 plikow testowych)
- **SKIP PM:** spec juz istnieje (`docs/specs/scripts-p0-p1-fixes.md`) — zostala wygenerowana bezposrednio z raportu review z exact line numbers, AC, test plan i DoD. Gate score 8.5/10. Nie ma potrzeby drugiego przejscia przez /pm.
- **Delegacja:** /build --spec docs/specs/scripts-p0-p1-fixes.md — pipeline 6 faz (plan/build/verify/test/domain/ship)
- **Scope:**
  - P0: D1 cross-campaign push (all campaign_ids, nie losowy 1), A2 AD_GROUP branching w execute()
  - P1 globalnie: validate_action wired w ScriptBase helper + wywolania w 6 skryptach
  - P1 protection: brand + keyword protection w A1/A6/C2 (refactor helperow z a2 → `_helpers.py`)
  - P1 A1: conversion lag guard (7 dni warning w dry_run)
  - P1 frontend: race condition w refreshCounts (AbortController/cancelled flag)
  - P2 testy: unit testy per skrypt (min 5 per script, 30+ lacznie) + test_scripts_helpers.py
- **Out of scope (swiadomie odlozone):** B1 per-item ad_group scoping, B1 min_conversions=3 policy change, A2 short-word tuning, D1 stop words PL expansion, C2 keeper CPA tiebreaker, ScriptsPage.jsx 985→refactor, dead code cleanup w DashboardPage legacy Quick Scripts state
- **Status:** DONE
- **Wynik:** 648/648 backend pytest passed (+41 nowych testów dla scripts: helpers + 6 skryptów, shared scripts_fixtures factory). Vite build OK. 3 parallel review (FAZA 3): code-quality 7/10, security 8/10, domain 7.5/10. Iteracja 2: naprawione wszystkie CRITICAL/HIGH findings — A6 EXACT force-match + AD_GROUP wiring, `circuit_breaker_limit` field w ScriptExecuteResult, _check_keyword_conflict reverse-subset, D1 restricted to CAMPAIGN-only, A1 lag guard refinement (window fully-inside vs partial), A2/A6 AD_GROUP fallback guard, _validate_batch local time (Warsaw), router params size cap 16KB (DoS), canonical script.id in save_config, _helpers allow 2-char brand tokens. Commit 1addab6 (squashed z WIP 3ba0bcd). Spec archived: docs/specs/scripts-p0-p1-fixes.md (pozostawiony aktywny dla referencji, nie przeniesiony do archive).

## [2026-04-13] Scripts System: Sprint 1-4 UX + A3/D3/F1 + history
- **Powod:** Po P0+P1 fixes ads-user/ads-expert wykrył UX blocker (custom_brand_words hidden w UI, fałszywy placeholder "Sprint 1 — A1 only") + plan na 16 usprawnień w docs/reviews/ads-verify-scripts.md (Sprint 1-4). User wymagał "wszystko razem" — pełen lot bez cząstkowych shipów.
- **Intelligence used:** NIE (plan pochodził z własnego /ads-expert review, nie potrzebował market research)
- **Nakład:** L (~16 taskow frontend+backend+testy, dwie iteracje review)
- **SKIP PM:** spec już istniał (docs/reviews/ads-verify-scripts.md zawiera pełen plan Sprint 1-5 z ads-expert/ads-verify pipeline). Sprint 5 (scheduling, undo, shared lists) świadomie odłożony per plan.
- **Delegacja:** /build wewnętrzny (FAZA 1-6), 2 iteracje review po implementacji Sprint 1-4.
- **Scope:**
  - Sprint 1 UX: usunięcie fałszywego placeholdera, szeroki modal 1200px, metric columns (clk/impr/CTR/conv/CPA/cost/savings), savings heatmap (>500zł green, >50 warning, <50 muted), ukrycie pustych n-gram tabs, blokada Execute przy paramsEdited, filter kampanii + sort, grupowanie po kampanii, CSV export, markdown post-exec report
  - Sprint 2 skrypty: A3 Low CTR Waste (mirror A1 z CTR threshold), D3 N-gram Audit Report (view-only top-N, grouped by text+campaign), lazy dry-run per category z useRef guard
  - Sprint 2 UX: TagInput component — custom_brand_words + custom_competitor_words edytowalne przez chip UI (był hidden)
  - Sprint 3: GET /scripts/{id}/history endpoint (JSON filter + Python fallback) + badge "Ostatnio: 3 dni temu · N zast." w ScriptTile + F1 Competitor Term Detection (ACTION_ALERT, reads Client.competitors)
  - Sprint 4: per-campaign grouping, CSV export, MD post-execute summary (bundled w Sprint 1)
- **Iteracja 2 — review fixes:**
  - F1 używa `Client.competitors` (istniejąca kolumna) zamiast nieistniejącego `ai_context.competitors` (P1 data bug)
  - D3 dedup po (text, campaign_id) zamiast samego text — zapobiega double-counting cost/conv_value gdy term w wielu kampaniach
  - _helpers.py: extract `fetch_aggregated_terms` (A1 + A3 delegate, 60+ linii deduplikatu usunięte)
  - ScriptsPage useRef dla fetched guards zamiast counts/history w deps (eliminuje O(N) re-fetch loops)
  - History endpoint: `func.json_extract` zamiast in-memory filter (SQLite 3.38+, fallback bezpieczny)
  - MATCH_SOURCE_HARD/SOFT/SEARCH_ACTION/PMAX_ALERT/AUDIT/COMPETITOR constants w base.py, frontend alertSources sync
  - D3 top_n hard-cap 500 (DoS), A3 lag-guard warning path + batch_size w context_json
- **Out of scope (świadomie odłożone):** Sprint 5 — scheduling/cron, undo per item, shared negative lists, "why not" debug mode, bulk param edit (wymagają nowych tabel/workers — po MVP production)
- **Status:** DONE
- **Wynik:** 663/663 backend pytest passed (+19 nowych testów: test_scripts_a3, test_scripts_d3, test_scripts_f1, test_scripts_router_history). Vite build OK. Review iter 1: code 7.5/10, security 7.5/10, domain 7.5/10 (9 findings: 2 CRITICAL, 4 HIGH, 3 WARN/P2). Iteracja 2: wszystkie CRITICAL/HIGH naprawione (F1 data source, D3 dedup, history JSON filter, useRef guards, shared fetch helper, match_source constants, D3 top_n cap, A3 warnings/batch_size). Commit 25dbbc9. Spec docs/reviews/ads-verify-scripts.md — 16 z 23 elementów done (Sprint 1-4), 5 odłożonych (Sprint 5 infrastructure), 2 NOT_NEEDED (C2 select antipattern, undo).

## [2026-04-13] Status Meeting + Dashboard Widgets: porządki wip + dokończenie zerwanego wątku
- **Powód:** Prezes zwołał spotkanie statusowe. CEO ASSESS (4 scouty równolegle) wykrył 28 plików wip w 3 wątkach: (1) Dashboard widgets — 3 kompletne komponenty (AnomalyAlertsCard, BudgetPacingCard, ScriptRunModal) nie podpięte do Dashboard.jsx; (2) Scripts ads reviews — 3 niezacommitowane pliki docs/reviews; (3) Open specs — settings-hub-p0-fixes.md i search-terms-scripts-research.md. Przed nowym featurem trzeba zrobić porządek, żeby repo nie mieszało wątków. Decyzja Prezesa (AskUserQuestion): klasyfikuj i commituj w chunkach, potem dokończyć Dashboard widgets (zero nowych frontów).
- **Intelligence used:** NIE (task to porządki + dokończenie wip, nie nowy feature). Brief świeży (2026-04-10) — top action #1 (Google auto-apply detection) zostaje w backlogu na następny sprint.
- **Nakład:** S (porządki w 4-5 chunkach) + S-M (widgets integration, zależnie od stanu backendu endpointów)
- **SKIP PM:** integration/refactor work + widgets już napisane (nie wymagają nowego design). Jeśli brakuje backend endpointów → escalate do /build.
- **Delegacja:** bezpośrednie porządki git + integration work; w razie braku endpointu /build dashboard-widgets.
- **Scope:**
  - Chunk A: commit docs/reviews/ads-{user,expert,verify}-scripts.md
  - Chunk B: commit docs/specs/{settings-hub-p0-fixes,search-terms-scripts-research}.md
  - Chunk C: .gitignore dla frontend/diag-* artifacts
  - Chunk D: commit backend/app/routers/analytics.py (trends 365d clamp bugfix)
  - Chunk E: przejrzeć database.py, main.py, models/client.py, services/action_executor.py — commit lub odrzucić
  - Chunk F: przejrzeć frontend context/routing/widgets zmiany — prawdopodobnie związane z Dashboard widgets
  - Krok 2: sprawdzić Dashboard.jsx render + API endpointy (getAnomalies, getBudgetPacing, bulk-apply), dokończyć integrację, build+test+review
- **Status:** STARTED

## [2026-04-13] Review: Google Ads Coverage Audit + Specialist Checklist
- **Powód:** W vault Obsidian znaleziono dwa kluczowe dokumenty oceniające stan pokrycia Google Ads przez aplikację: `GOOGLE_ADS_COVERAGE.md` i `GOOGLE_ADS_SPECIALIST_CHECKLIST.md`. Nie były częścią roadmapy — wymagają przeglądu przez CEO i wciągnięcia braków na roadmapę v1.1/v2.
- **Intelligence used:** NIE (analiza istniejących dokumentów)
- **Nakład:** zadanie REVIEW (nie implementacja) — następna sesja /ceo
- **Delegacja:** CEO w następnej sesji porówna te pliki ze stanem aplikacji (PROGRESS.md + COMPLETED_FEATURES.md) i zdecyduje co wchodzi na roadmapę v1.1.
- **Pliki do przeczytania:**
  - `docs/GOOGLE_ADS_COVERAGE.md` — co app pokrywa TAK / CZĘŚCIOWO / NIE per typ kampanii
  - `docs/GOOGLE_ADS_SPECIALIST_CHECKLIST.md` — dzienny + tygodniowy workflow PPC specjalisty jako benchmark
- **Kluczowe luki zidentyfikowane wstępnie:**
  - Shopping: NIE (tylko podstawowe metryki list, brak optymalizacji)
  - Display: NIE (brak wsparcia)
  - Video: NIE (brak wsparcia)
  - RSA: CZĘŚCIOWO (brak synca asset performance z API)
  - Audiences: CZĘŚCIOWO (brak zarządzania listami, bid adjustment, In-Market)
  - DSA: NIE (brak zarządzania celami stron, landing pages)
  - Checklist daily: budżet OK, anomalies OK, search terms OK — ale "szybkie pauzy" i RSA rotacja do weryfikacji
- **Status:** PENDING REVIEW — następna sesja /ceo musi to sprawdzić
