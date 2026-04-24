# Plan implementacji — Campaigns
> Na podstawie: docs/reviews/ads-expert-campaigns.md (Srednia 8.0/10)
> Data weryfikacji: 2026-04-22

### Podsumowanie
- Elementow z raportu: 10
- DONE: 0 | PARTIAL: 3 | MISSING: 7 | NOT_NEEDED: 0
- Szacowany naklad: sredni (3 sprinty, lacznie ~8-10h)

Wszystkie 3 P0 z poprzedniego cyklu review sa **DONE** (pause/enable, budget edit, ad_groups drilldown + auction insights). Raport 8.0/10 zawiera juz tylko P1/P2/P3 — brak zadnego P0.

### Status kazdego elementu

#### KRYTYCZNE (P1 — must implement dla v1.1)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 1 | Bidding strategy switch (Max Conv <-> Target CPA <-> Target ROAS) | MISSING | `PATCH /campaigns/{id}/bidding-target` (tylko VALUE) w `campaigns.py:433`; brak endpointa na change strategy | Nowy endpoint `PATCH /campaigns/{id}/bidding-strategy`; rozszerzenie `_mutate_campaign_bidding_target` w `google_ads.py`; UI: zawsze-widoczny button + dropdown w modalu | L |
| 2 | Bulk actions — multi-select + pause/enable/budget | MISSING | Pojedyncze selectCampaign w `CampaignsPage.jsx:626`; backend: pojedyncze PATCH endpoints | Stan `selectedIds: Set`, checkboxy w liscie (`CampaignsPage.jsx:624`), toolbar nad lista, client-side loop przez istniejace endpointy (akceptowalne <50 kampanii) | L |
| 3 | Testy dla `ad_groups` router | MISSING | `backend/app/routers/ad_groups.py:14` (100 linii), brak `test_ad_groups.py` | Utworzyc `backend/tests/test_ad_groups.py` z 5+ testami: happy-path, 404 campaign, zero-metrics ad_group, date filter, ordering | M |
| 4 | Labels add/remove z UI | MISSING | `filters.campaignLabel` jest read-only filter w `CampaignsPage.jsx:478`; model `Campaign.labels` (JSON) istnieje | Endpoint `PATCH /campaigns/{id}/labels` z akcja add/remove; UI: chip z labelami + picker | M |
| 5 | Unified-timeline: filtr po `campaign_id` zamiast JS post-filter | PARTIAL | Endpoint `/history/unified-timeline` (`history.py:125`) akceptuje `campaign_name` ale NIE `campaign_id`; UI pobiera 200 i filtruje w JS (`CampaignsPage.jsx:306,312`) | (a) Dodac `campaign_id: Optional[int]` w `history.py:131`; (b) Zmienic `CampaignsPage.jsx:306` na `{ campaign_id: campaign.id, limit: 50 }`; (c) Usunac `.filter()` na 312 | S |
| 6 | Naming spojnosc `cost` vs `cost_usd` | PARTIAL | `GET /campaigns/{id}/kpis` -> `cost` (`campaigns.py:203`); `GET /analytics/campaigns-summary` -> `cost_usd`; frontend zmieszany (`:495,:650,:1013`) | Decyzja: `cost` canonical; dodac alias `cost_usd` (deprecated) w summary endpoint; migrowac 3 miejsca w `CampaignsPage.jsx` | S |

#### NICE TO HAVE (P2/P3)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 7 | Budget modal: -10/-20/-50% shortcuty | PARTIAL | Linia `CampaignsPage.jsx:1088` `[10, 20, 50].map` — tylko + | Zamienic na `[-50, -20, -10, 10, 20, 50]` (pojedynczy grid) lub 2 linie | S |
| 8 | AuctionInsights: backend `limit` param + UI "Pokaz wiecej" | PARTIAL | `_auction.py:16` brak `limit`, zwraca wszystkich; `AuctionInsightsTable` limit={8} w UI | (a) `limit: int = Query(20)` w `_auction.py:19`; (b) UI: pokazuj toggle "Pokaz wszystkich N" w `AuctionInsightsTable` gdy rows > limit | S |
| 9 | `_weighted_avg` dla `click_share` — dokumentacja spojnosci wag | PARTIAL | `campaigns.py:216` `weight_field="clicks"` vs reszta po `impressions` | Dodac w docstringu + opcjonalnie `_weight_metadata` w response. Mozna tez ujednolicic do impressions | S |
| 10 | CampaignKpiRow responsive (1280px overflow risk) | MISSING | `CampaignKpiRow.jsx:43` fixed `repeat(5, 1fr)`, wartosc 16px (`:63`) | Zamienic na `repeat(auto-fill, minmax(140px, 1fr))` lub `clamp(12px, 1.2vw, 16px)` na wartosci | S |

#### ZMIANY/USUNIECIA

Brak rekomendacji usuniec — raport 8.0/10 zatwierdza zakladke do ZACHOWAC w calosci.

### Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, ~1h):
  [ ] Task 5  — unified-timeline: campaign_id param (backend + frontend)
  [ ] Task 6  — cost vs cost_usd cleanup
  [ ] Task 7  — budget modal -10/-20/-50% shortcuts
  [ ] Task 8  — AuctionInsights limit param + UI "Pokaz wiecej"
  [ ] Task 9  — _weighted_avg dokumentacja
  [ ] Task 10 — CampaignKpiRow responsive grid

Sprint 2 (sredni naklad — M, ~2-3h):
  [ ] Task 3  — test_ad_groups.py (5+ testow)
  [ ] Task 4  — labels add/remove (endpoint + UI chip picker)

Sprint 3 (duzy naklad — L, ~4-5h):
  [ ] Task 2  — Bulk actions (multi-select + toolbar)
  [ ] Task 1  — Bidding strategy switch (endpoint + UI)
```

### Szczegoly implementacji

#### Task 1 — Bidding strategy switch [L]

- **Pliki**:
  - `backend/app/routers/campaigns.py` — nowy endpoint po `update_bidding_target:433`
  - `backend/app/services/google_ads.py` — nowa metoda `_mutate_campaign_bidding_strategy`
  - `backend/app/schemas/campaign.py` — opcjonalnie nowy schema `BiddingStrategyUpdate`
  - `frontend/src/features/campaigns/CampaignsPage.jsx:679-694` (button + modal)
  - `frontend/src/api.js` — nowa funkcja `updateBiddingStrategy`
- **Backend**: `PATCH /campaigns/{id}/bidding-strategy` — body `{ bidding_strategy: 'MAXIMIZE_CONVERSIONS'|'TARGET_CPA'|'TARGET_ROAS'|'MANUAL_CPC', target_cpa_micros?: int, target_roas?: float }`. Remote-first, audit, demo guard — jak w `update_bidding_target:433`.
- **Frontend**: (a) Zawsze renderuj button "Licytacja" (nie tylko gdy target istnieje — usuwamy warunek z `:679`); (b) Modal z dropdownem strategii + conditional pole target; (c) Po zapisie wywolac `mergeCampaignState`.
- **Dane**: `Campaign.bidding_strategy` juz istnieje (column).
- **Testy**: 5 testow w `test_campaigns.py` — happy path per strategy, walidacja ze target nie moze byc przy MANUAL_CPC, 502 na API fail.

#### Task 2 — Bulk actions [L]

- **Pliki**:
  - `frontend/src/features/campaigns/CampaignsPage.jsx` — stan `selectedIds: Set`, toolbar, checkboxy
  - Opcjonalny endpoint `POST /campaigns/bulk-update` w `campaigns.py` (lub loop client-side po istniejacych endpointach)
- **Frontend**: (a) `const [selectedIds, setSelectedIds] = useState(new Set())`; (b) checkbox w liscie `CampaignsPage.jsx:624` (obok radioselect); (c) conditional toolbar nad lista gdy `selectedIds.size > 0`: "Zaznaczonych N · Pauza / Wznow / Budzet +10% / +20% / +50%"; (d) po kliknieciu: iteracja `for (const id of selectedIds) await updateCampaignStatus(...)` + toast progress.
- **Backend**: Na start — bez nowego endpointa (loop client-side); w Sprint 3+ dodac bulk endpoint jesli potrzeba.
- **Testy**: Playwright e2e test w `frontend/e2e/`: wybierz 3 kampanie -> podnies budzet +20% -> verify 3 modalki audit log.

#### Task 3 — Tests ad_groups [M]

- **Plik**: `backend/tests/test_ad_groups.py` (nowy)
- **Testy**:
  1. `test_list_ad_groups_happy_path` — seed 2 ad groups, 1 keyword each, KeywordDaily 7 dni -> verify aggregacja clicks/cost/conv/CTR
  2. `test_404_when_campaign_not_found` — call z nieistniejacym campaign_id
  3. `test_zero_metrics_ad_group` — ad_group bez keywords -> clicks=0, cpa=0, roas=0 (no div-by-zero crash)
  4. `test_date_filter_excludes_outside` — KeywordDaily poza zakresem
  5. `test_multiple_ad_groups_ordered_by_name` — sortowanie w `ad_groups.py:40`

#### Task 4 — Labels add/remove [M]

- **Pliki**:
  - `backend/app/routers/campaigns.py` — nowy endpoint `PATCH /campaigns/{id}/labels`
  - `frontend/src/features/campaigns/CampaignsPage.jsx` — chip z labelami w headerze (po linii 730)
  - `frontend/src/api.js` — nowa funkcja `updateCampaignLabels`
- **Backend**: `PATCH /campaigns/{id}/labels` — body `{ action: 'add'|'remove'|'replace', labels: string[] }`. Modyfikuje `campaign.labels` (JSON). Demo guard + audit. Remote push opcjonalny (labels w GAds to LabelService — dolozyc w v1.2).
- **Frontend**: Chip z labelami + "+" button -> popover z input + suggestions z innych kampanii.
- **Testy**: 3 testy w test_campaigns.py (add, remove, replace).

#### Task 5 — Unified-timeline campaign_id [S]

- **Pliki**:
  - `backend/app/routers/history.py:131` — dodac `campaign_id: Optional[int] = Query(None)`
  - `CampaignsPage.jsx:306` — zmienic wolanie
  - `CampaignsPage.jsx:312` — usunac JS filter
- **Backend**: W filterach events (`history.py:160`) juz jest `campaign_name` — po campaign_id trzeba: (a) dla actions: `_enrich_action` zwraca campaign_id, wiec filter on enriched list PO query; (b) dla events: query `db.query(ChangeEvent).filter(ChangeEvent.campaign_name == camp_name)` gdzie camp_name z `db.get(Campaign, campaign_id).name`. Alternatywa: zmienic schema events by mial campaign_id FK (wiekszy scope).
- **Frontend**: Po zmianie endpointa, `getUnifiedTimeline(selectedClientId, { campaign_id: campaign.id, limit: 50 })`.
- **Testy**: 1 test w `test_history.py` — verify filter.

#### Task 6 — cost vs cost_usd cleanup [S]

- **Pliki**:
  - `backend/app/routers/analytics/` — sprawdzic `campaigns_summary` endpoint (prawdopodobnie w `_summary.py` lub `_campaigns.py`)
  - `CampaignsPage.jsx:495,650` oraz `:1013` — dostosowac do nowego canonical field name
- **Backend**: Dodac pole alias `cost: ...` obok `cost_usd: ...` w response (deprecated w changelogu) — bez breaking change.
- **Frontend**: 3 replaces `cost_usd -> cost` w CampaignsPage.

#### Task 7 — Budget modal -N% [S]

- **Plik**: `CampaignsPage.jsx:1088`
- **Change**: `{[10, 20, 50].map(...)}` -> `{[-50, -20, -10, 10, 20, 50].map(pct => ...)}` — formula `newZl = oldZl * (1 + pct / 100)` dziala dla obu stron. Dla ujemnych pct zmienic styling buttonu (czerwony border) gdy pct < 0.

#### Task 8 — AuctionInsights limit [S]

- **Pliki**: `backend/app/routers/analytics/_auction.py:16`, `frontend/src/components/AuctionInsightsTable.jsx`
- **Backend**: `limit: int = Query(20, ge=1, le=100)`; `.limit(limit)` na query.
- **Frontend**: W `AuctionInsightsTable` dodac stan `showAll`, gdy rows.length > limit pokazac button "Pokaz wszystkich N".

#### Task 9 — _weighted_avg dokumentacja [S]

- **Plik**: `campaigns.py:187` docstring oraz opcjonalnie `_weighted_avg_metadata` w response.
- **Change**: Dodac komentarz: `# click_share uzywa klikow jako wag (semantycznie poprawne), pozostale IS — impresji. W zakresach gdy kampania ma 0 klikow w niektorych dniach weight=0 -> dzien pominiety.`

#### Task 10 — CampaignKpiRow responsive [S]

- **Plik**: `CampaignKpiRow.jsx:43`
- **Change**: `gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))'` zamiast `repeat(5, 1fr)`. Opcjonalnie `fontSize: 'clamp(12px, 1.2vw, 16px)'` na linia 63.

---

## Nastepny krok

Po wdrozeniu Sprintu 1 (quick wins) uruchom `/ads-check campaigns` — zweryfikuje ze 6 szybkich poprawek zostalo faktycznie wprowadzonych przed przejsciem do Sprint 2.
