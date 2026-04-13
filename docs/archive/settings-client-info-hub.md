# Feature Spec: Settings — Client Info Hub + AI Context
generated: 2026-04-10 | author: PM Agent | status: ready

## Skad to przyszlo
CEO Decision: "Settings przestaje być formularzem edycji klienta — staje się persistent context hub
konsumowanym przez rekomendacje, raporty i przyszły AI agent. Brakujące warstwy po UX overhaul
(2026-04-09): conversion tracking visibility, linked accounts, account metadata, currency fix."

Intelligence signal: "Auto-applied changes (HIGH pain, 53% advertiserów) można wykrywać tylko
gdy mamy baseline klienta — linked accounts + conversion tracking jako source-of-truth w Settings.
Adalysis competitive threat: per-asset tracking + task list = GAH potrzebuje structured client context
żeby rekomendacje były personalizowane, nie generyczne."

## User Story
Jako specjalista Google Ads zarządzający kampaniami klienta,
chcę widzieć pełen kontekst konta (metadata, freshness synca, aktywne konwersje, linki do GA4/GMC)
oraz zapisać strukturalne dane biznesowe (target CPA, ROAS, LTV, brand terms) w jednym miejscu,
żeby rekomendacje i raporty mogły używać tych danych bez pytania mnie za każdym razem.

## Architektura — kluczowe odkrycie z recon

**ConversionAction jest JUŻ w DB** (sync_conversion_actions w google_ads.py linia 4122).
Endpoint /clients/{id}/health NIE musi wołać Google Ads API dla conversion tracking —
czyta z tabeli conversion_action lokalnie. Redukuje to punkty awarii i czas odpowiedzi.

**Podział źródeł danych:**
| Sekcja | Źródło | API call? |
|--------|---------|-----------|
| account_metadata | Client model (DB) + opcjonalnie Google Ads API (timezone, auto_tagging) | opcjonalny |
| sync_health | SyncLog (DB, ostatni wpis) | NIE |
| conversion_tracking | ConversionAction table (DB, już zsynchronizowana) | NIE |
| linked_accounts | Google Ads API (product_link, customer_client) | TAK (z graceful fallback) |

## Acceptance Criteria
- [ ] AC1: GET /api/v1/clients/{id}/health zwraca HTTP 200 z 4 kluczami: `account_metadata`, `sync_health`, `conversion_tracking`, `linked_accounts` + `errors: []` — dla klienta z danymi w DB
- [ ] AC2: Gdy Google Ads API nie ready → endpoint nadal zwraca 200 z: account_metadata z DB (client.name, currency, customer_id), sync_health z SyncLog, conversion_tracking z ConversionAction table, linked_accounts: [] — z `errors: ["google_ads_api_unavailable"]`
- [ ] AC3: conversion_tracking zwraca listę aktywnych ConversionAction z pól: name, category, status, include_in_conversions_metric, attribution_model (z pierwszej aktywnej)
- [ ] AC4: sync_health.freshness przyjmuje wartości "green" (< 6h), "yellow" (< 24h), "red" (≥ 24h lub brak synca)
- [ ] AC5: ClientHealthSection renderuje się NA GÓRZE Settings.jsx (przed sekcją Informacje ogólne), pokazuje 4 karty w horizontal grid, nie wymaga scrollowania na 13" (max ~180px wysokości sekcji)
- [ ] AC6: Currency w CAŁYM Settings.jsx używa client.currency — brak hardcoded "USD" / "$" w renderowanym HTML po zmianie currency klienta na PLN
- [ ] AC7: Nowe pola business_rules zapisują się przez istniejący PATCH /api/v1/clients/{id} i odczytują przez GET — dotyczy: target_cpa, target_roas, ltv_per_customer, profit_margin_pct, priority_conversions (lista stringów), brand_terms (lista stringów)
- [ ] AC8: Walidacja backend: profit_margin_pct poza zakresem 0-100 → HTTP 422; target_cpa < 0 → 422; brand_terms.length > 50 → 422
- [ ] AC9: Backend testy ≥ 6 (test_client_health.py: happy path, api_unavailable, partial_data, freshness_logic, conversion_from_db, business_rules_validation) + E2E testy ≥ 4
- [ ] AC10: Vite build OK + pytest 544+ passed

## Edge Cases
- **Brak synca** (nowy klient, nigdy nie synchronizowany) → sync_health.freshness = "red", last_synced_at = null, last_status = null; karta sync wyświetla "Brak danych — uruchom synchronizację"
- **Zero aktywnych konwersji** → conversion_tracking.active_count = 0, actions = []; karta konwersji wyświetla "Brak aktywnych konwersji — sprawdź konfigurację konta"
- **Brak Google Ads API przy pobieraniu linked accounts** → linked_accounts = [], errors zawiera "google_ads_api_unavailable"; karty linked accounts wyświetla "Dane niedostępne — Google Ads API niegotowe" (nie crash)
- **client.currency = null lub puste** → fallback do "PLN" (identycznie jak Client model default)
- **business_rules = null w DB** → Settings inicjuje pola jako null/undefined, zapisuje tylko przy jawnym wypełnieniu przez usera (nie nadpisuje pustym JSONem przy GET)
- **priority_conversions w multi-select z wartościami spoza current ConversionAction list** → Settings pokazuje wartości jako "nieznana konwersja (ID)" i pozwala usunąć; nie blokuje zapisu
- **Settings na 13" laptop** → sekcja ClientHealthSection max 180px height; jeśli 4 karty nie mieszczą się w 1 wierszu → 2×2 grid (nie vertical stack)

## Struktura komponentu ClientHealthSection

```
ClientHealthSection.jsx (ok. 120-150 linii)
├── Karta 1: Konto (account_metadata)
│   ├── customer_id (read-only)
│   ├── account_type (MCC / Standard)
│   ├── currency (z DB)
│   ├── timezone (jeśli z API, else "-")
│   └── auto_tagging (yes/no badge)
├── Karta 2: Synchronizacja (sync_health)
│   ├── freshness badge (zielony/żółty/czerwony)
│   ├── last_synced_at (relative: "2 godziny temu")
│   ├── last_status (success/partial/failed)
│   └── last_duration_seconds
├── Karta 3: Śledzenie konwersji (conversion_tracking)
│   ├── active_count (liczba badge)
│   ├── attribution_model (primary)
│   ├── enhanced_conversions (yes/no)
│   └── lista nazw aktywnych konwersji (max 3, "+ X więcej")
└── Karta 4: Połączenia (linked_accounts)
    ├── GA4 (linked ✓ / not linked)
    ├── Merchant Center (linked ✓ / not linked)
    ├── YouTube (linked ✓ / not linked)
    └── Search Console (linked ✓ / not linked)
```

Layout: `display: grid, gridTemplateColumns: 'repeat(4, 1fr)', gap: 12px`
Na wąskim viewport: `repeat(2, 1fr)` (media query lub matchMedia hook).

## Nowe pola w sekcji "Reguły biznesowe"

```
Istniejące:      Min ROAS (min_roas) | Max dzienny budżet (max_daily_budget)
Nowe — Cele:     Target CPA [{currency}]  |  Target ROAS [x]
Nowe — Wartość:  LTV klienta [{currency}]  |  Marża zysku [%] (0-100)
Nowe — Strategia: Priorytetowe konwersje [multi-select z ConversionAction.name]
                   Brand terms [tag input jak competitors pills]
```

`priority_conversions` multi-select: wartości pobierane z `health.conversion_tracking.actions`
(frontend fetchuje getClientHealth przy mount Settings, przekazuje do business rules section).

## Nowe pliki

```
backend/app/services/client_health_service.py  — nowy serwis
backend/tests/test_client_health.py             — nowe testy
frontend/src/components/settings/               — nowy katalog
frontend/src/components/settings/ClientHealthSection.jsx  — nowy komponent
frontend/e2e/settings-client-info-hub.spec.js   — nowe E2E testy
```

## Zmodyfikowane pliki

```
backend/app/routers/clients.py  — nowy endpoint GET /clients/{id}/health
backend/app/schemas/client.py   — nowy ClientHealthResponse Pydantic schema
frontend/src/pages/Settings.jsx — integracja ClientHealthSection + currency fix + nowe pola
frontend/src/api.js             — getClientHealth(clientId)
```

## Endpoint spec

```
GET /api/v1/clients/{client_id}/health

Response 200:
{
  "account_metadata": {
    "customer_id": "123-456-7890",
    "name": "Sushi Naka Naka",
    "account_type": "STANDARD",   // "MCC" jeśli ma child accounts
    "currency": "PLN",            // z client.currency (DB)
    "timezone": "Europe/Warsaw",  // z Google Ads API jeśli ready, else null
    "auto_tagging_enabled": true, // z Google Ads API jeśli ready, else null
    "tracking_url_template": null
  },
  "sync_health": {
    "last_synced_at": "2026-04-10T08:00:00Z",
    "hours_since_sync": 4.2,
    "freshness": "green",         // "green" | "yellow" | "red"
    "last_status": "success",     // "success" | "partial" | "failed" | null
    "last_duration_seconds": 35
  },
  "conversion_tracking": {
    "active_count": 3,
    "attribution_model": "GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN",
    "enhanced_conversions_enabled": null,  // nieznane z DB — null MVP
    "actions": [
      { "name": "Zakup", "category": "PURCHASE", "status": "ENABLED",
        "include_in_conversions": true }
    ]
  },
  "linked_accounts": [
    { "type": "GA4", "status": "not_linked", "resource_name": null, "detected_via": "google_ads_api" },
    { "type": "MERCHANT_CENTER", "status": "not_linked", "resource_name": null, "detected_via": "google_ads_api" },
    { "type": "YOUTUBE", "status": "not_linked", "resource_name": null, "detected_via": "google_ads_api" },
    { "type": "SEARCH_CONSOLE", "status": "not_linked", "resource_name": null, "detected_via": "google_ads_api" }
  ],
  "errors": []
}
```

## AI-Ready Forward Note (poza scope MVP)

Pola `business_rules.target_cpa`, `target_roas`, `ltv_per_customer`, `profit_margin_pct`,
`priority_conversions`, `brand_terms` są strukturalne i gotowe do konsumowania przez:
- `recommendations.py` — zamiast parsowania `notes` przy budowaniu kontekstu rekomendacji
- `reports.py` — jako dane do personalizacji narracji w raportach AI
- przyszły AI agent (project_agent_sdk_vision.md) — jako prompt context per client

Integracja tych pól z recommendations/reports to OSOBNY task — nie jest scope tej specyfikacji.
Engineering NIE ma implementować tej integracji w ramach tego taska.

## Out of Scope (V1)
- Pełny redesign Settings na tab-y (Option A — v1.2)
- Integracja z external API: GA4 Data API, Content API (Shopping), Search Console API (Option B3)
- AI integracja business_rules z recommendations/reports (osobny task)
- Notification preferences (email/Slack alerty per client)
- Cache TTL per-endpoint (60s TTL może być wdrożone w v1.1 jeśli uderzenie w API okaże się problemem — MVP bez cache, bo ConversionAction z DB jest szybkie i linked_accounts to rzadki call)
- Migracja istniejących kolumn Client model — WSZYSTKO zostaje w business_rules JSON
- Zmiana sekcji: Hard Reset, MCC accounts, scheduled sync — bez modyfikacji

## Success Metric
Kuba otwiera Settings dla dowolnego klienta i w ciągu 3 sekund widzi: kiedy ostatnio był sync
(kolor badge), ile konwersji jest aktywnych, czy currency to PLN — bez klikania, bez scrollowania.

## Szacowana zlozonosc
Medium (6-8 tasków w FAZA 2)

## Zaleznosci

Istniejące backendu (gotowe do użycia):
- `/api/v1/clients/{id}` GET/PATCH — Client data + business_rules JSON
- ConversionAction model + sync_conversion_actions() — dane konwersji w DB
- SyncLog model — historia syncronizacji
- google_ads_service.get_connection_diagnostics() — check czy API ready
- customer_client queries (linia 1096-1101 google_ads.py) — MCC hierarchy

Nowe:
- `/api/v1/clients/{id}/health` GET — nowy endpoint (clients.py)
- `client_health_service.py` — nowy serwis
- `ClientHealthResponse` Pydantic schema
- `ClientHealthSection.jsx` — nowy komponent
- `getClientHealth(id)` w api.js

Frontend dotykane:
- `frontend/src/pages/Settings.jsx` (848 linii) — integracja + currency fix + nowe pola BR
- `frontend/src/api.js` — 1 nowa funkcja
