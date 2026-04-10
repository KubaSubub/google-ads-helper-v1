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
