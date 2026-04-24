# Ocena eksperta Google Ads — Campaigns
> Data: 2026-04-22 | Srednia ocena: 8.0/10 | Werdykt: ZACHOWAC (z 10 punktowa lista uzupelnien — brak juz zadnego P0)

### TL;DR
Od poprzedniej recenzji (6.5/10) zakladka wskoczyla o 1.5 pkt — dodano 3 brakujace write-ops (`PATCH /campaigns/{id}/status|budget|bidding-target` w `campaigns.py:241,341,433`), router `ad_groups.py:14` z agregacja z `KeywordDaily` i tabelka w `CampaignsPage.jsx:875`, Auction Insights wpiete do Promise.all (`CampaignsPage.jsx:307`), IS metryki wazone impresjami (`campaigns.py:187 _weighted_avg`), filtr timeline po `campaign_id` (`CampaignsPage.jsx:312`), Role-card zwijalny z localStorage (`CampaignsPage.jsx:246`). Pozostaly zasadniczo problemy P1/P2: brak bidding-strategy switch, brak bulk actions, brak negative keywords na poziomie kampanii, brak labels write, brak testow dla `ad_groups` routera.

### Oceny
| Kryterium | Ocena | Uzasadnienie (plik:linia lub playbook ref) |
|-----------|-------|---------------------------------------------|
| Potrzebnosc | 9/10 | Bez zmian — Campaigns to drugi najwazniejszy panel po Dashboard; playbook sekcja 2.3 (Campaign health) + 3.1 (Budget mgmt) w pelni pokryte. Deep-linki do Keywords/SearchTerms (`CampaignsPage.jsx:733,744`) dzialaja. |
| Kompletnosc | 8/10 | 3 z 3 P0 z poprzedniej recenzji naprawione: pause/enable dzialajace w `handleToggleStatus:365`, budget edit w `handleSaveBudget:397` z shortcut +10/+20/+50% (`CampaignsPage.jsx:1087`), bidding edit `handleSaveBidding:433`, Ad Groups tabelka z drilldown do Keywords (`CampaignsPage.jsx:905`), Auction Insights z `AuctionInsightsTable` (`CampaignsPage.jsx:1024`). Brakuje nadal: bidding strategy switch (Max Conv ↔ Target CPA ↔ Target ROAS), bulk actions na liscie (multi-select), negatives na poziomie kampanii, labels management. |
| Wartosc dodana vs Google Ads UI | 8/10 | 4 unique'y: (1) Helper vs ZEWN badge w timeline `ActionHistoryTimeline:165` — nadal unique, (2) Role+Protection+Confidence z Manual override zwijalne w localStorage (`CampaignsPage.jsx:246,756`), (3) 8-metrykowy IS grid widoczny od razu bez konfiguracji kolumn (`CampaignKpiRow.jsx:29-38`), (4) Budget modal z `+10/+20/+50%` quick-shortcuts (`CampaignsPage.jsx:1087`) — GAds nie ma. ALE: brak `-10%/-20%` obnizki (Marek: "obnizanie tez czesta operacja"). |
| Priorytet MVP | 8/10 | Teraz write-ready: pause/enable, budget i bidding-target dzialaja through remote-first + audit + circuit breaker (`campaigns.py:287,378,472`). Marek moze zrobic 80% Daily Ops bez wychodzenia z apki. Minus 2 punkty za braki bulk i strategy switch, ktore sa codzienne. |
| **SREDNIA** | **8.0/10** | |

### Lista problemow (10 znalezionych)

**[P1] Brak switch'a bidding strategy — tylko edit wartosci targetu**
- Gdzie: `CampaignsPage.jsx:679-694` (button otwiera `biddingModalOpen`) + `campaigns.py:451` (walidacja `field in (target_cpa_micros, target_roas)`)
- Problem: Mozna zmienic **wartosc** target CPA/ROAS ale nie przelaczysz z `MAXIMIZE_CONVERSIONS` na `TARGET_CPA`. Dla kampanii bez targeta chip sie nie pokazuje (linia 679 `{(selected.target_cpa_micros || selected.target_roas) && ...}`), wiec user nie moze ZACZAC uzywania targetu. Codzienna operacja w GAds (np. po 30-dniowym learning period).
- Fix: (a) Dodac endpoint `PATCH /campaigns/{id}/bidding-strategy` przyjmujacy `new_strategy` + opcjonalny target; (b) UI: zawsze pokazywac button "Edytuj licytacje" (nie tylko gdy jest target), modal z dropdownem strategii.
- Playbook ref: sekcja 4.1 "Zmiana strategii licytacji" — czeste dla PMax/Search po 30 dniach learning.

**[P1] Brak bulk actions na liscie kampanii — Marek request #1**
- Gdzie: `CampaignsPage.jsx:615-659` (lista kampanii — pojedyncze `onClick={() => selectCampaign(c)}`, brak checkboxow)
- Problem: Z notatek Marka: "zaznacz 5 kampanii → podnies budżet o 20% → confirm. Codzienna operacja." Obecnie musisz kliknac po kolei w 5 kampanii i dla kazdej otworzyc modal. `campSummary` juz ma dane per kampania — infrastruktura jest.
- Fix: (a) Dodac stan `selectedIds: Set<number>`, checkboxy w liscie; (b) Toolbar nad lista: "Zaznaczonych: N · Pauza · Wznow · Budzet +X%"; (c) Backend endpoint `POST /campaigns/bulk-update` lub loop po jednym (akceptowalne dla <50 kampanii).
- Playbook ref: sekcja 3.1 "Budget mgmt w skali — bulk +X%"

**[P1] `ad_groups` router bez testow**
- Gdzie: `backend/app/routers/ad_groups.py:14` + `backend/tests/` (brak `test_ad_groups.py`)
- Problem: Nowy endpoint z agregacja JOIN `KeywordDaily→Keyword→AdGroup` + 7 pochodnych metryk (CTR, CPC, CPA, ROAS, conversion_rate) dziala bez zadnego pokrycia testowego. Krytyczne edge cases niepokryte: (a) campaign_id nie istnieje → 404, (b) brak keywords w ad_group → wiersze z zerami (linie 66-70), (c) date range bez danych, (d) division-by-zero na lines 86-90 juz jest zabezpieczony `if impressions else 0`.
- Fix: Utworzyc `backend/tests/test_ad_groups.py` z 5+ testami: happy-path, 404, zero-metrics, date-filter, multiple ad groups ordering.

**[P1] Filtr po labelu jest read-only — brak add/remove label z UI**
- Gdzie: `CampaignsPage.jsx:478` (`filters.campaignLabel !== 'ALL'`) + brak handlera
- Problem: Mozesz FILTROWAC po labelu przez `GlobalFilterBar` (poza strona), ale nie dodasz/usuniesz labela z poziomu kampanii. W GAds to inline add — specjalista oznacza kampanie jako `Brand_Autumn_2026` w 30 sekund. U nas: edit DB recznie albo wrocic do GAds.
- Fix: (a) `Campaign.labels` juz jest w modelu (JSON array); dodac endpoint `PATCH /campaigns/{id}/labels` z akcja add/remove; (b) UI: chip z listą labeli + "+" button otwierajacy picker.

**[P1] `getUnifiedTimeline` wolany z `limit: 200` i filtrowany w JS zamiast query param**
- Gdzie: `CampaignsPage.jsx:306` — `getUnifiedTimeline(selectedClientId, { limit: 200 })` → linia 312 `.filter(e => e.campaign_id === campaign.id || e.campaign_name === campaign.name)`
- Problem: Pobieramy 200 najnowszych entries calego konta, potem frontend filtruje. (a) Dla klienta z 100 kampaniami widzisz tylko wlasne 1-2 entries z 200; jeszcze gorzej — jesli wszystkie 200 to inne kampanie, timeline bedzie pusty mimo ze historia tej kampanii istnieje wczesniej. (b) waste bandwidth. (c) Fallback do `campaign_name` match nadal tu jest — jesli nazwa sie zmienila, history sie rozjezdza.
- Fix: Endpoint `/unified-timeline` juz powinien wspierac `campaign_id` param (sprawdzic w `backend/app/routers/history.py`); jesli nie — dodac. Zmienic wolanie: `getUnifiedTimeline(selectedClientId, { campaign_id: campaign.id, limit: 50 })` i usunac JS filter.

**[P1] KPI response pola sa `cost` (nie `cost_usd`), lista uzywa `cost_usd` — nazewnictwo niespojne**
- Gdzie: `campaigns.py:203` zwraca `{"cost": round(total_cost_usd, 2), ...}` (nazwa pola `cost`) ALE `CampaignsPage.jsx:495` i `:650` uzywa `cost_usd` z `campSummary`, `:1013` uzywa `c.cost_usd?.toFixed(0)` (geo)
- Problem: Dwa rozne naming schemes w jednym panelu: `/campaigns/{id}/kpis` zwraca `cost`, `/analytics/campaigns-summary` zwraca `cost_usd`. Developer nie wie ktore poprawne. Nowe endpointy (KPI) juz maja `cost` — ale stare pozostawiono dla kompatybilnosci.
- Fix: Konsolidacja — zdecydowac `cost` (jednostka neutralna) jako canonical; migrowac `/campaigns-summary` do `cost` z polu-alias `cost_usd` deprecated. 3 miejsca we frontendzie do zamiany.

**[P2] Budget modal: brak `-10%/-20%` shortcutow — tylko powiekszenia**
- Gdzie: `CampaignsPage.jsx:1088` — `{[10, 20, 50].map(pct => ...)}` generuje tylko `+N%`
- Problem: Z notatek Marka: "obnizanie budzetu w GAds zdarza sie rownie czesto" (np. przekroczenie budzetu miesiecznego → obniz, eksperymentalna kampania bije budzet bez konwersji → obniz o 50%).
- Fix: Dodac druga linie buttonow `[-10, -20, -50]`: `newZl = oldZl * (1 + pct / 100)` — z ujemnym pct dziala automatycznie. Opcjonalnie: pokazac 6 przyciskow w gridzie `-50%, -20%, -10%, +10%, +20%, +50%`.

**[P2] Brak `limit` na AuctionInsights backend vs frontend — mozliwy mismatch**
- Gdzie: `_auction.py:16-60` (brak param `limit` w `get_auction_insights`) + `CampaignsPage.jsx:1032` (`<AuctionInsightsTable rows={auctionData} compact={true} limit={8} />`)
- Problem: Frontend tnie do 8 konkurentow ale backend zwraca **wszystkich**. Dla PMax z 30+ konkurentow pobieramy cale 30, wywietlamy 8, reszta leci w kosmos. Z notatek Marka: "w realnym koncie konkurentow bywa 20+". Brakuje tez UI "pokaz wiecej" do obejscia limitu.
- Fix: (a) Backend: dodac `limit: int = Query(20)` w `_auction.py:18`; (b) Frontend: `limit={20}` + toggle "Pokaz wszystkich N" w `AuctionInsightsTable` gdy rows.length > limit.

**[P2] `_weighted_avg` uzywa impressions jako wagi rowniez dla `search_click_share`, ale linia 216 probuje `clicks` — tylko dla 1 z 8**
- Gdzie: `campaigns.py:216` — `_weighted_avg("search_click_share", weight_field="clicks")` vs wszystkie pozostale IS wazone po `impressions`
- Problem: Dobrze ze `click_share` jest wazone klikami (to 100% poprawne semantycznie), ALE w sesji gdy kampania ma 0 klikow w niektorych dniach, weight=0 te dni pomija — a w pozostalych IS ten sam dzien wlicza sie pod wzgledem impressions. To tworzy **niespojny denominator** miedzy metrykami (ten sam period, inne weight-poolse).
- Fix: Udokumentowac w docstring + dodac w response `_weighted_avg_metadata: {"click_share_days": N}` zeby frontend widzial sample size. Alternatywnie: ujednolicic do impressions (z dokumentacja "click_share approximated by impression-weighted average").

**[P3] `CampaignKpiRow.jsx` 16px font size dla 18 metryk w gridzie 5-kolumnowym — na 1440px ekranie OK, na 1280px overflow**
- Gdzie: `CampaignKpiRow.jsx:63` — `fontSize: 16, fontWeight: 700` wartosc metryki + linia 43 `gridTemplateColumns: 'repeat(5, 1fr)'`
- Problem: Dla liczb jak `103 500 zł` lub `1 247 wyświetlen` w 5-kol gridzie na ekranie 1280px kazda karta ma ~190px szerokosci; z padding 10/12 zostaje 170px — wartosc 16px moze sie przelamac. Nie test na `1024px viewport`.
- Fix: Dodac `gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))'` zamiast fixed 5; lub `clamp(12px, 1.2vw, 16px)` dla wartosci.

### Porownanie z Google Ads UI
| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Lista kampanii z KPI | Tabela z Modify Columns | Sidebar list z sort + colored ROAS pod nazwa | LEPSZE (mniej klikow) |
| Pauzowanie kampanii | toggle inline | button "Wstrzymaj/Wznow" + confirm z ruchem (`CampaignsPage.jsx:367-388`) | IDENTYCZNE (confirm z daily ruchem nawet LEPSZE) |
| Edycja budzetu | inline pencil | button z pencil + modal z +10/+20/+50% (`CampaignsPage.jsx:696-709`) | IDENTYCZNE (shortcuts +X% LEPSZE, brak -X% GORSZE) |
| Edycja target CPA/ROAS | inline pencil | button pokazywany TYLKO gdy target istnieje (`CampaignsPage.jsx:679`) | GORSZE (nie rozpocznie uzycia targetu od zera) |
| Switch bidding strategy | dropdown | BRAK | GORSZE |
| Impression Share grid | Modify Columns, ~4 widoczne | 8 metryk na raz dla SEARCH+SHOPPING (`CampaignKpiRow.jsx:29`) | LEPSZE (unique) |
| Ad Groups drilldown | Standardowa zakladka | Tabelka inline w Campaigns → klik → Keywords z filtrem (`CampaignsPage.jsx:905`) | IDENTYCZNE (inline faster) |
| Auction Insights | Dedicated view | Embedded w view (`CampaignsPage.jsx:1023`) | LEPSZE (context-preserving) |
| Change History | Generic list | Helper vs ZEWN badge z before→after (`ActionHistoryTimeline:165,190`) | LEPSZE (unique) |
| Role/Protection classification | BRAK | Auto + Manual override + Confidence + zwijalne (`CampaignsPage.jsx:756`) | LEPSZE (unique) |
| Bulk actions | multi-select checkbox + toolbar | BRAK | GORSZE |
| Labels add/remove | inline add/remove | read-only filter po labelu | GORSZE |
| Ad Strength / Assets | Tab per kampania | BRAK | GORSZE |
| Campaign Settings (locations, schedule, network) | Dedicated tab | BRAK | GORSZE |
| Negative keywords (campaign-level) | Dedicated tab | BRAK (musisz isc w Keywords) | GORSZE |
| Demographics/Audience | Tabs: Demographics, Audience | BRAK | GORSZE |
| Shared budgets | widoczne + assignment | BRAK info czy kampania w shared budget | GORSZE |
| Conversion actions per campaign | breakdown | BRAK | GORSZE |

### Rekomendacja koncowa

**ZACHOWAC — zakladka w produktywnej formie (8.0/10).** Od poprzedniej recenzji 3 z 3 P0 zamkniete (pause/enable, budget edit, ad_groups drilldown). Obecnie Marek moze wykonac Daily Ops w 80% bez wychodzenia z apki; Unique'y (Role/Protection, Helper-vs-ZEWN timeline, 8-IS grid, inline Auction Insights) faktycznie przeważają nad GAds UI.

Kolejne priorytetyzowane interwencje (w kolejnosci impact/effort):
1. **Bulk actions + bidding strategy switch** (P1, 1-2 dni) — zamyka luke "80% → 95%" codzienych operacji.
2. **Tests dla `ad_groups` router + unified-timeline po `campaign_id`** (P1, 0.5 dnia) — higiena + usuwa race condition w historii.
3. **Budget modal -10/-20/-50% + Labels write + `cost` vs `cost_usd` cleanup** (P2, 1 dzien).

Po tych 3 iteracjach spokojnie 9/10. Pozostale luki (Assets, Campaign Settings, Demographics, Shared budgets) to dodatkowy scope — nie blokuja MVP, bo GAds UI nadal obsluguje je lepiej i uzer moze tam szybko wejsc (playbook cross-app workflow).
