# ads-check: Campaigns
> Data: 2026-04-22 | Plan z: 2026-04-22 (ads-verify-campaigns.md) | Wynik: 13/13 taskow wdrozonych (skipped #15 deferred per plan)

## Podsumowanie
- Taskow w planie do sprawdzenia: 13 (pomijajac #6 NOT_NEEDED i #15 DEFERRED)
- DONE: 13 | PARTIAL: 0 | STILL_MISSING: 0 | SKIPPED: 0 | DIFFERENT: 0
- Verdykt: **GOTOWE (100%)**

## Status taskow

### Wdrozone (DONE)

| # | Task | Dowod |
|---|------|-------|
| #1 | Pause/Enable kampanii — mutator | `google_ads_mutations.py:639` — `def _mutate_campaign_status(self, campaign, db, new_status)` (CampaignService.mutate_campaigns z CampaignStatusEnum) |
| #1 | Pause/Enable kampanii — endpoint | `campaigns.py:241` — `@router.patch("/{campaign_id}/status")` z `pattern="^(ENABLED|PAUSED)$"`, remote-first + demo_guard + audit log |
| #1 | Pause/Enable kampanii — UI | `CampaignsPage.jsx:712` — button Pause/Play w header (dynamic label "Wstrzymaj"/"Wznow"), `handleToggleStatus()` (linia 365) z confirmation modal |
| #2 | Budget endpoint | `campaigns.py:341` — `@router.patch("/{campaign_id}/budget")` z `budget_micros` query param (gt=0), uzywa `_mutate_campaign_budget`, revert local on API fail |
| #2 | Budget UI | `CampaignsPage.jsx:1114` — modal `handleSaveBudget()` (linia 397), quick buttons +10/+20/+50%, warning >30% |
| #3 | Auction Insights w Campaigns | Nowy komponent `components/AuctionInsightsTable.jsx` (132 linii, compact=true, limit=8). `CampaignsPage.jsx:1027` — sekcja z Trophy icon po Device/Geo |
| #3 | Auction Insights — data fetch | `CampaignsPage.jsx` — 4-ty Promise w `selectCampaign`: `getAuctionInsights(clientId, {...allParams, campaign_id: campaign.id})` |
| #4 | Ad Groups router | Nowy plik `backend/app/routers/ad_groups.py` (99 linii) — `GET /ad_groups?campaign_id&date_from&date_to`, aggregacja z KeywordDaily joined via Keyword.ad_group_id, derived CTR/CPC/CPA/ROAS |
| #4 | Ad Groups — rejestracja | `main.py:116` — `app.include_router(ad_groups.router, ...)` |
| #4 | Ad Groups — UI | `CampaignsPage.jsx` — sekcja "Grupy reklam" po KPI (linia 884), click row navigate `/keywords?campaign_id=X&ad_group_id=Y`. API helper `getCampaignAdGroups` w `api.js` (linia 350) |
| #5 | Timeline campaign_id — actions.py | `actions.py:67-103` — `_enrich_batch` zwraca `"campaign_id": campaign_id` dla keyword oraz campaign entity_type |
| #5 | Timeline campaign_id — history.py | `history.py:48` — `_enrich_action` zwraca `campaign_id`. Linia 165-172: batch-load `camp_name_to_id` dict dla external ChangeEvent path. Linia 189+215: obie sciezki emituja `"campaign_id"` |
| #5 | Timeline campaign_id — frontend | `CampaignsPage.jsx` (selectCampaign) — filter: `e.campaign_id === campaign.id || e.campaign_name === campaign.name` (fallback) |
| #7 | Cache pacing | `CampaignsPage.jsx:280` — `selectCampaign(campaign, pacingOverride = null)` — pacingSource z `pacingOverride \|\| pacingAll`. Linia 297 — filter lokalny (`.find(c => c.campaign_id === campaign.id)`). `loadCampaigns` ladujе pacing 1x per client |
| #8 | IS dla SHOPPING | `CampaignKpiRow.jsx:29` — `const isItems = ['SEARCH', 'SHOPPING'].includes(campaignType) ? [...] : []` |
| #9 | Bidding target UI | `CampaignsPage.jsx:433` — `handleSaveBidding()`, dedicated button w header (Pencil icon) pokazuje CPA lub ROAS, `updateBiddingTarget` w api.js |
| #10 | Role card collapsible | `CampaignsPage.jsx:246` — `showRoleCard` state z localStorage (`campaignShowRole`). Linia 253: useEffect persist. Compact badge `Role · Protection · Confidence` widoczny gdy collapsed (linia 762) |
| #11 | Tooltip Protection | `CampaignsPage.jsx:55` — `PROTECTION_TOOLTIPS` map (HIGH/MEDIUM/LOW z opisem). Linia 782: `title={PROTECTION_TOOLTIPS[...]}` na badge + `cursor: 'help'` |
| #12 | Empty-state Device/Geo | `CampaignsPage.jsx:949-955` — zawsze-renderowany grid 2-col, 3 states: loading ("Ladowanie..."), empty ("Brak danych urzadzen/geograficznych..."), data |
| #13 | Testy bidding-target + budget + status | Nowy plik `backend/tests/test_campaigns.py` (194 linii) — 12 test cases: bidding (5), budget (3), status (4). Wszystkie 12/12 PASS (potwierdzone: `48/48 campaigns tests` — w tym 36 istniejacych + 12 nowych) |
| #14 | Weighted average IS | `campaigns.py:187` — nowy helper `def _weighted_avg(field, weight_field="impressions")`. Linie 211-218: 8 IS metryk uzywa weighted_avg; `search_click_share` z `weight_field="clicks"` (per Google Ads doc) |

### Czesciowe (PARTIAL)
*Brak.*

### Brakujace (STILL_MISSING)
*Brak.*

### Zmienione (DIFFERENT)
*Brak.*

### Pominiete (SKIPPED/NOT_NEEDED/DEFERRED)
| # | Task | Powod |
|---|------|-------|
| #6 | TrendExplorer ignoruje globalny date filter | NOT_NEEDED — plan ads-verify zweryfikowal jako false positive (`TrendExplorer.jsx:433` uzywa filters.dateFrom/dateTo z useFilter()) |
| #15 | cost_usd legacy naming | DEFERRED per plan — cross-cutting refactor naming, zostawione do dedykowanej sesji P3 (nie blokujace) |

## Dodatkowe walidacje

- Frontend build: **OK** (`vite build --mode development`, 7.78s, 0 errors)
- Backend testy: **48/48 PASS** (test_campaigns + test_campaigns_summary + test_campaigns_clients_crud + test_campaign_roles = 12+2+24+10)
- Lint warnings: tylko zewnetrzny file `ShoppingPage.jsx` (nie dotyczy tego sprintu)

## Nastepne kroki

Zakladka GOTOWA (100%). Odpalam `/ads-user Campaigns` jako obowiazkowy re-test.
