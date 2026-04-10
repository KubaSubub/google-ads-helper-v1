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
- **Status:** STARTED
