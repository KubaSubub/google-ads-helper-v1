# Bugfix Spec: Settings Client Info Hub — P0/P1 fixes
generated: 2026-04-10 | author: PM Agent | status: ready

## Skad to przyszlo
CEO Decision: "Post-ship ads-user (Marek) + ads-expert review wykryły 4 bugi w Settings Client
Info Hub. User complaints bezpośrednie: (1) 'Nie widzę wszystkich konwersji' — 2/18 visible;
(2) 'Nie widzę czy połączenie jest czy go nie ma' — wszystko hardcoded shell. Scope B."

Intelligence signal: "Marek pain — brak visibility konwersji blokuje codzienny workflow PPC
specialist. Google Ads API v23 (SDK 29.1) wspiera `product_link` — realne zapytanie możliwe,
ALE dla ograniczonego zestawu typów (MERCHANT_CENTER, HOTEL_CENTER, GOOGLE_ADS,
DATA_PARTNER, ADVERTISING_PARTNER). GA4/YouTube/Search Console NIE są dostępne w Google Ads
API — wymagają oddzielnych integracji (Google Analytics Admin API itd.)."

## KLUCZOWE ODKRYCIE Z TECHNICAL RECON (scope revision)

Oryginalny brief CEO zakładał że wszystkie 4 integracje (GA4, MERCHANT_CENTER, YOUTUBE,
SEARCH_CONSOLE) są queryable przez `product_link` resource. **To jest NIEPRAWDA dla v23.**

Rzeczywista zawartość v23 SDK:
- `product_link.LinkedProductType` enum: `MERCHANT_CENTER`, `HOTEL_CENTER`, `GOOGLE_ADS`,
  `DATA_PARTNER`, `ADVERTISING_PARTNER`, `UNKNOWN`
- `account_link.LinkedAccountType` enum: tylko `THIRD_PARTY_APP_ANALYTICS` (mobile analytics)
- `data_link.DataLinkType` enum: tylko `VIDEO` (YouTube videos linked TO campaigns, nie
  YouTube channel linking)
- **Brak** jakiegokolwiek resource'u dla GA4 web property, YouTube channel link, Search Console

**Konsekwencje dla scope:**
- MERCHANT_CENTER: **realne query DZIAŁA** — pokażemy prawdziwy status
- GA4, YOUTUBE, SEARCH_CONSOLE: **niemożliwe do zweryfikowania** przez Google Ads API v23
- Honest UI approach: pokaż MERCHANT_CENTER z realnymi danymi, a GA4/YT/SC z jasnym
  labelem `ℹ Niedostępne przez Google Ads API` + tooltip wyjaśniający że wymaga separate
  integration w przyszłości

**To nie jest regresja vs oryginalny plan** — to jest uczciwsza implementacja tego samego
planu. User widzi prawdziwy status MERCHANT_CENTER (kluczowa integracja dla e-commerce jak
Sushi Naka Naka) i jasną informację dlaczego pozostałe nie są pokazane.

## User Story
Jako Kuba zarządzający 15 kontami klientów dziennie,
chcę widzieć pełną listę aktywnych konwersji (wszystkie 18 Sushi Naka Naka, nie 2/18) oraz
realny status integracji Merchant Center,
żeby szybko zweryfikować czy conversion tracking i feed produktowy działają bez
przełączania się do Google Ads UI.

## Problem

Obecny ClientHealthSection ma 4 zidentyfikowane bugi:

**P0-1: Konwersje truncation — `slice(0, 2)`** ([ClientHealthSection.jsx:214](frontend/src/components/settings/ClientHealthSection.jsx#L214))
User widzi tylko 2 pierwsze konwersje + statyczny text "+ 16 więcej" bez żadnej interakcji.
Real data Sushi Naka Naka: 22 total / 18 enabled ConversionActions. Musi przełączać się
do Google Ads UI żeby zobaczyć wszystkie — neguje sens narzędzia.

**P0-2: Linked accounts — pure hardcoded shell** ([client_health_service.py:119](backend/app/services/client_health_service.py#L119))
`_build_linked_accounts_shell()` zwraca zawsze `status="not_linked"` dla 4 typów BEZ
żadnego API call. User nie wie czy "sprawdzono i brak", "API niedostępne", czy "feature
nie zaimplementowany". UI pokazuje `— Dane niedostępne` co jest mylące.

**P1-3: Attribution model legacy enum**
DB zawiera `GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN` (pre-v15 API). Frontend robi
`.replace(/_/g, ' ')` → wyświetla "GOOGLE SEARCH ATTRIBUTION DATA DRIVEN" — ugly +
niezgodne z v23 (powinno być `DATA_DRIVEN`).

**P1-4: Partial sync pokazuje green "Aktualny" badge**
`_freshness()` patrzy tylko na czas, ignoruje `last_status`. Sushi Naka Naka ma partial
sync 2h temu → badge green "Aktualny" mimo że synchronizacja była tylko częściowa.
Specjalista widzi "Aktualny" + "Częściowy" jednocześnie = niespójność + utrata zaufania.

## Acceptance Criteria

### Backend (`/clients/{id}/health`)

- [ ] **AC1 — Real product_link query for Merchant Center**: Nowa metoda
  `google_ads_service.get_product_links(customer_id: str) -> list[dict]` wykonuje GAQL
  `SELECT product_link.resource_name, product_link.type, product_link.status FROM product_link`.
  Zwraca listę dictów: `[{type: "MERCHANT_CENTER"|..., status: "ENABLED"|..., resource_name: str}, ...]`.
- [ ] **AC2 — Linked accounts with real MC status**: `_build_linked_accounts()` zwraca
  4 wpisy (MERCHANT_CENTER, GA4, YOUTUBE, SEARCH_CONSOLE) gdzie:
  - MERCHANT_CENTER ma `status="linked"` jeśli query zwraca wpis ze statusem ENABLED dla tego typu, else `"not_linked"`
  - GA4, YOUTUBE, SEARCH_CONSOLE mają `status="unsupported"` z `unsupported_reason="not_in_google_ads_api_v23"`
  - Gdy Google Ads API not ready → MERCHANT_CENTER ma `status="api_unavailable"`, trzy pozostałe nadal `"unsupported"`
  - Gdy product_link query rzuca exception → MC ma `status="api_unavailable"`, errors[] zawiera `"linked_accounts_fetch_error"`
- [ ] **AC3 — Attribution model normalization**: Helper
  `_normalize_attribution_model(raw: str | None) -> str | None` w client_health_service.py
  mapuje legacy enumy → v23. Response API nie zawiera żadnego stringa zaczynającego się od
  `GOOGLE_SEARCH_ATTRIBUTION_`. Wartości null/puste passthrough jako null.
- [ ] **AC4 — Freshness label in SyncHealth**: `SyncHealth` schema dostaje nowe pole
  `freshness_label: str`. `_build_sync_health()` decyduje o label centralnie:
  - `last_status == "failed"` → freshness=`"red"`, label=`"Błąd"`
  - `last_status == "partial"` → freshness=`"yellow"`, label=`"Częściowy"`
  - `last_status == "running"` → freshness=`"yellow"`, label=`"W toku"`
  - `last_status == "success"` → freshness wg hours (green <6h, yellow 6-12h, red ≥12h),
    label odpowiednio `"Aktualny"` / `"Starszy niż 6h"` / `"Nieaktualny"`
  - `last_status is None` (brak syncu) → freshness=`"red"`, label=`"Brak synchronizacji"`

### Frontend (`ClientHealthSection.jsx`)

- [ ] **AC5 — Konwersje inline expand**: Usunąć `slice(0, 2)` hardcoded truncation.
  Karta "Konwersje" pokazuje nadal 2 pierwsze nazwy + button "Pokaż wszystkie (N)" gdzie
  N = `conv.active_count`. Po kliknięciu button: state `expandedConversions` przełącza się
  na true, pod gridem 4 kart (NIE wewnątrz karty Konwersje) renderuje się sekcja
  "Aktywne konwersje (N)" z tabelą wszystkich `conv.actions`. Kolumny tabeli: Nazwa,
  Kategoria, Status, Include in conversions, Primary for goal. Tabela: design system v2,
  gęste wiersze (font 11px), uppercase 10px headers, zebra stripes z `C.w03`. Button ma
  `aria-expanded` i przełącza między "Pokaż wszystkie (N)" i "Zwiń".
- [ ] **AC6 — Linked accounts 4 stany**: Komponent `LinkedRow` renderuje jeden z 4 stanów
  na podstawie `status`:
  - `"linked"` → `✓ Połączone` (green, C.success)
  - `"not_linked"` → `✗ Brak połączenia` (gray, C.textMuted — NIE "—")
  - `"api_unavailable"` → `⚠ API niedostępne` (yellow, C.warning, ikona AlertCircle)
  - `"unsupported"` → `ℹ Niedostępne w API v23` (dim gray, ikona Info, title={unsupported_reason} jako tooltip)
- [ ] **AC7 — Freshness badge uses backend label**: `FreshnessBadge` używa
  `sync.freshness_label` (z backendu) jeśli dostępny, fallback na istniejący
  `FRESHNESS[sync.freshness].label` dla back-compat.
- [ ] **AC8 — Attribution model cleanup**: Frontend usuwa
  `.replace('GOOGLE_SEARCH_ATTRIBUTION_', '')` hack. Zamiast tego wyświetla
  `conv.attribution_model.replace(/_/g, ' ')` jeśli wartość niepusta, else nic.
  Backend normalizacja gwarantuje że wartość to już v23 enum.

### Tests

- [ ] **AC9 — Backend tests ≥ 6 new**:
  - `test_linked_accounts_api_unavailable` (monkeypatch diagnostics ready=False → MC status=api_unavailable, GA4/YT/SC unsupported)
  - `test_linked_accounts_query_success` (monkeypatch get_product_links → MC linked)
  - `test_linked_accounts_query_exception` (monkeypatch raises → MC api_unavailable + errors[])
  - `test_attribution_model_normalization` (parametrized, 6 legacy→v23 mappings + passthrough for already-v23)
  - `test_sync_badge_partial_yields_yellow_czesciowy` (partial sync 2h old → freshness=yellow label=Częściowy)
  - `test_sync_badge_failed_yields_red_blad` (failed sync → freshness=red label=Błąd)
  - Update `_seed` to accept `num_conversions` param, add test `test_conversion_tracking_returns_all_18_actions` for regression
- [ ] **AC10 — E2E tests ≥ 4 new (DOM-based, nie network-only)**:
  - `Konwersje card: expand button reveals all 18 conversions in table below grid`
    (mock z 18 actions, assert `text=/Pokaż wszystkie \(18\)/`, click, assert 18 rows)
  - `Konwersje card: collapse button hides the table again`
  - `Linked accounts: MERCHANT_CENTER linked state renders ✓ Połączone`
    (mock z product_link data)
  - `Linked accounts: API unavailable yields ⚠ API niedostępne` (mock errors[])
  - `Linked accounts: unsupported types (GA4/YT/SC) render info state with tooltip`
  - `Partial sync shows yellow Częściowy badge even when recent` (mock last_status=partial, 2h old)

## Edge Cases

- **Brak aktywnych konwersji** (active_count=0) → button "Pokaż wszystkie (0)" ukryty, karta pokazuje "Brak aktywnych konwersji — sprawdź konfigurację konta" (istniejące zachowanie preserved)
- **Jeden aktywny konwersji** (active_count=1) → pokazuje 1 nazwę, button "Pokaż wszystkie (1)" nadal działa ale expansia pokazuje 1 wiersz w tabeli
- **Wszystkie konwersje ≤ 2** (active_count=2) → nie pokazuje button expand (nic by nie dodał), karta zachowuje istniejący widok 2 nazw
- **Długie nazwy konwersji** (np. "NakaNaka Upmenu (web) begin_checkout" 30+ znaków) → tabela ma `word-break: break-word` lub `text-overflow: ellipsis` z title={full name}
- **product_link query timeout** (Google Ads API slow) → exception caught, errors[] zawiera "linked_accounts_fetch_error", MC pokazuje api_unavailable (edge: czy czekać 30s czy fail fast? decyzja: default SDK timeout, no explicit override)
- **Partial sync z hours_since_sync = null** (brak finished_at) → freshness=yellow label=Częściowy (status wygrywa nad missing hours)
- **Failed sync wiele dni temu** → freshness=red label=Błąd (status wygrywa nad "starego czasu")
- **Attribution model = null lub pusty string** → backend `_normalize_attribution_model(None) → None`, frontend nie renderuje wiersza atrybucji
- **Nieznany legacy enum** (spoza mapy) → passthrough as-is (nie crashuje, tylko nie normalizuje)
- **MERCHANT_CENTER w product_link ale status=REMOVED lub SUSPENDED** → traktuj jako "not_linked" (tylko status=ENABLED liczy się jako linked)

## Out of Scope (V1)

- **GA4, YouTube, Search Console real integration** — wymaga Google Analytics Admin API, Content API, Search Console API z dodatkowymi OAuth scopes. To osobny sprint (L task), nie P0.
- **HOTEL_CENTER, DATA_PARTNER, ADVERTISING_PARTNER** — inne typy z product_link; pokażemy tylko MERCHANT_CENTER bo jest relevant dla aktualnych klientów (Sushi, Klimfix etc.). Można dodać w v1.2 jeśli klient hotelowy się pojawi.
- **Conversion table filtering/sorting** — statyczna tabela w MVP. Filtry (per kategoria, tylko primary, itp.) w v1.2.
- **Conversion value column** — nie pokazujemy `all_conversions_value_micros` w tabeli MVP (dodatkowa complexity, nie jest must-have dla "czy widzę konwersje").
- **Cache 60s TTL na /health endpoint** — nadal nie potrzebne (ConversionAction z DB jest szybkie; product_link query to max ~200ms dodatkowo).
- **Account status field** (active/suspended/closed) — to osobny task.
- **Realtime sync progress** (np. WebSocket updates freshness) — poza scope.
- **Modal view konwersji** — user explicitly wybrał inline.

## Success Metric

Kuba otwiera Settings dla Sushi Naka Naka i w ciągu 5 sekund:
1. widzi przycisk "Pokaż wszystkie (18)" zamiast "+ 16 więcej" static text
2. kliknięcie rozwija tabelę 18 konwersji z kategoriami (PURCHASE, LEAD, PHONE_CALL_LEAD...) w miejscu (bez przeskoku do modala)
3. karta "Połączenia" pokazuje Merchant Center z ✓ Połączone LUB ✗ Brak połączenia (realny status z Google Ads API)
4. GA4/YouTube/Search Console mają ℹ Niedostępne w API v23 z tooltipem wyjaśniającym (nie mylące "—")
5. Badge synchronizacji pokazuje "Częściowy" żółty (zamiast "Aktualny" zielony) dla partial sync

## Szacowana zlozonosc

Medium (6-8 tasków):
1. Backend: `get_product_links()` w google_ads.py (~1h)
2. Backend: `_build_linked_accounts()` + `_normalize_attribution_model()` + sync badge logic w client_health_service.py (~1h)
3. Backend: schema update (LinkedAccount status enum, SyncHealth.freshness_label) (~15min)
4. Backend: testy ≥ 6 nowych + update seed dla 18 konwersji (~1h)
5. Frontend: ClientHealthSection.jsx — inline expand + linked accounts 4 stany + badge label from backend (~1.5h)
6. Frontend: e2e testy ≥ 4 nowe (~45min)
7. Weryfikacja wizualna przeciwko realnemu backendowi (~15min)

Total ~4-5h. Mieści się w scope M.

## Zaleznosci

Istniejące:
- `backend/app/services/google_ads.py` — GoogleAdsService singleton z `client.get_service("GoogleAdsService")` pattern dla GAQL queries (użyty już w sync_conversion_actions linia 4122)
- `backend/app/services/client_health_service.py` — istniejąca struktura z `_try_google_ads_metadata` (wzorzec do skopiowania dla linked accounts)
- `backend/app/schemas/client.py` — istniejące LinkedAccount, SyncHealth, ConversionTracking schemas
- `frontend/src/components/settings/ClientHealthSection.jsx` — istniejący komponent, zmiany na miejscu (nie nowy plik)
- `backend/tests/test_client_health.py` — istniejący fixture `_seed(db)`, dodanie parametru `num_conversions`
- `frontend/e2e/settings-client-info-hub.spec.js` — istniejący MOCK_HEALTH fixture, dodanie nowych test cases

Nowe:
- `google_ads_service.get_product_links(customer_id)` — nowa metoda publiczna
- `client_health_service._build_linked_accounts(client)` — rename z `_build_linked_accounts_shell`, real implementation
- `client_health_service._normalize_attribution_model(raw)` — nowa funkcja helper
- `LinkedAccount.status` pydantic type — dodaj "api_unavailable", "unsupported"
- `SyncHealth.freshness_label` — nowe pole

Zero DB migration — wszystkie zmiany na poziomie service + schema + UI.
