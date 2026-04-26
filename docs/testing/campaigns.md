# Campaigns (Kampanie) — notatki testowe

> Ręczne testowanie widoku `/campaigns`. Wpisuj obserwacje w **Historia**, destyluj do **Do zrobienia**.
> Plik hardlinkowany z `[repo]/docs/testing/campaigns.md` — CEO czyta stąd zadania.

---

## 🔨 Do zrobienia

*Czekają na CEO — /ceo przeczyta i wykona.*

- [ ]

---

## 🔄 W toku

- [ ]

---

## ✅ Zrealizowane

*Po wdrożeniu: przenoś tu z "Do zrobienia" dla historii.*

- [x] Pause/Enable kampanii — endpoint + UI + confirm z daily ruchem (`campaigns.py:241`, `CampaignsPage.jsx:712`)
- [x] Edycja budżetu dziennego — modal z +10/+20/+50% shortcuts (`campaigns.py:341`, `CampaignsPage.jsx:1114`)
- [x] Edycja target CPA/ROAS — modal (`campaigns.py:433`, `CampaignsPage.jsx:1131`)
- [x] Ad Groups drilldown — tabelka inline + click → Keywords z pre-filtrem (`ad_groups.py:14`, `CampaignsPage.jsx:884`)
- [x] Auction Insights embedded w widoku kampanii (`CampaignsPage.jsx:1027`)
- [x] Timeline `campaign_id` enrichment — filter po kampanii w unified history (`actions.py:67`, `history.py:48`)
- [x] IS grid 8 metryk dla SEARCH+SHOPPING (`CampaignKpiRow.jsx:29`)
- [x] Role card zwijalny z localStorage (`CampaignsPage.jsx:246`)
- [x] Protection level tooltip HIGH/MEDIUM/LOW (`CampaignsPage.jsx:55, 782`)
- [x] Weighted average IS metrics — impressions jako waga (`campaigns.py:187`)
- [x] 48/48 backend testów (campaigns + roles + clients_crud + summary)
- [x] ads-check 13/13 DONE (2026-04-22) — 100% planu z ads-verify

---

## 📝 Historia obserwacji

*Wpisuj co widzisz podczas klikania — data + co zauważyłeś.*

### 2026-04-22 — ads-user review (Marek, 6 lat GAds)
- Lista 260px + detail scrollable, sort po 6 metrykach, filter metryka ≥/≤ threshold
- Wchodziłbym tu codziennie — review Brand+Prospecting + szybkie pause/resume
- **Braki blockery:**
  - Multi-select kampanii + bulk action (pause/resume/budget +X%) — codzienna operacja
  - Switch bidding strategy (Max Conv ↔ Target CPA ↔ Target ROAS) — częste po 30-dniowym learning
  - Optimization Score kolumna na liście
  - Campaign Settings (locations, schedule, network, device bid modifier)
  - Labels add/remove z UI (read-only filter tylko)
- **Irytujące drobiazgi:**
  - Ołówek 9px przy budżecie i target — nie wiadomo czy kliknąć chip czy ikonę
  - `+10/+20/+50%` w modalu budżetu — brak `-10/-20/-50%`
  - Brak ikonek typu kampanii na liście (Search/PMax/Shopping — tekstem)
  - Auction Insights `limit={8}` — w realnych kontach 20+ konkurentów
- **Werdykt:** 80% Daily Ops bez wychodzenia z apki, 20% wciąż przez GAds UI

### 2026-04-22 — ads-expert 8.0/10 (ZACHOWAĆ)
- Od poprzedniej 6.5 → 8.0 (3 z 3 P0 zamknięte: pause/enable, budget, ad_groups)
- Unique vs GAds: Role/Protection, HELPER vs ZEWN timeline, 8-IS grid, inline Auction Insights, budget +X% shortcuts
- Kolejne P1 (do wdrożenia):
  - Bulk actions + bidding strategy switch (1-2 dni)
  - Tests dla `ad_groups` router + unified-timeline po `campaign_id` jako query param (0.5 dnia)
  - Budget `-X%` shortcuts + Labels write + `cost` vs `cost_usd` cleanup (1 dzień)

###
