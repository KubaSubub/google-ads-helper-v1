# Notatki usera: Kampanie

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** seed data (brak screenshota campaigns.png — pracowałem z kodu komponentu)
**Data:** 2026-04-22

---

## Co widzę po wejściu

Dwie kolumny. Z lewej wąska lista kampanii (260px) — nazwa, typ, budżet dzienny, pod spodem metryki (koszt, konwersje, ROAS z kolorem). Na górze listy dropdown sortowania (Koszt / Konwersje / ROAS / Kliknięcia / CTR / Budżet), strzałka kierunku i lejek filtra. Lejek rozwija drugi rząd: metryka + operator (≥ / ≤) + wartość.

Po prawej szczegół wybranej kampanii. Nagłówek: nazwa, status (z kropką), strategia licytacji, chip z Target CPA/ROAS (edytowalny ołówkiem), chip z budżetem dziennym (edytowalny ołówkiem), po prawej żółty/zielony przycisk Wstrzymaj/Wznów.

Pod nagłówkiem dwie pigułki: "Słowa kluczowe" i "Wyszukiwane frazy" — deep link z pre-filtrem na tę kampanię.

Karta Rola kampanii — Auto / Final, Manual override + Reset to auto, chip Protection HIGH/MED/LOW z tooltipem wyjaśniającym automatyzację, Confidence %.

Potem 5×N KPI tiles (kliknięcia, wyśw, koszt, konwersje, wart. konw., CTR, CPC, CPA, CVR, ROAS) + dla SEARCH/SHOPPING dodatkowe 8 kafli IS (Impr. Share, Top IS, Abs Top IS, Budget Lost IS, Rank Lost IS, Click Share, Abs Top %, Top Impr %). Każdy kafel z delta % vs poprzedni okres.

Niżej tabela Grup reklam (nazwa, status, kliknięcia, koszt, konw., CPA, ROAS) — klikalna, prowadzi do keywords z pre-filtrem ad_group_id.

Potem Trend Explorer scoped do kampanii, Budget Pacing, dwie karty side-by-side (Urządzenia + Top miasta), Auction Insights, na dole timeline historii zmian (HELPER vs ZEWN. z before→after).

## Co mogę zrobić

- Wybrać kampanię z listy
- Sortować listę po 6 metrykach, kierunek ↑/↓
- Filtrować listę metryką z progiem (≥/≤)
- Filtrować po nazwie i etykiecie (przez global filter bar — poza stroną)
- Edytować budżet dzienny (modal z shortcutami +10/+20/+50%, ostrzeżenie przy >30%)
- Edytować target CPA/ROAS (modal)
- Wstrzymać / wznowić kampanię (z confirmem pokazującym średni dzienny ruch)
- Ustawić manual override roli kampanii (Brand/Generic/Prospecting/Remarketing/PMax/Local/Unknown) i zresetować
- Zwinąć/rozwinąć kartę Roli (stan w localStorage)
- Skoczyć do Keywords / SearchTerms z pre-filtrem kampanii lub grupy reklam
- Kliknąć wiersz w tabeli grup reklam → keywords z pre-filtrem grupy

## Co mam WIĘCEJ niż w Google Ads UI

- **Budget Pacing na kampanii** — w GAds muszę ręcznie liczyć % wykorzystania budżetu miesięcznego. Tu jest z gotowym modułem.
- **Klasyfikacja Role + Protection level** — w GAds nie ma czegoś takiego jak "Brand", "Generic", "Prospecting" z poziomem ochrony. Sam to tagujemy w Excelu albo w labelach. Tu masz auto-klasyfikację z confidence score i override.
- **HELPER vs ZEWN. timeline** — GAds pokazuje change history ale bez rozróżnienia "kto zmienił — user, skrypt, narzędzie". Tu widzę czy zmiana była z tej apki czy spoza niej.
- **Auction Insights embedowane w widoku kampanii** — w GAds to osobna karta z rozwijaniem, tu mam bezpośrednio przy kampanii.
- **IS tiles widoczne na pierwszy rzut oka (8 metryk IS jednym blokiem)** — w GAds muszę dodać kolumny do tabeli kampanii albo wejść w raporty.
- **Before→after diff dla każdej zmiany w timeline** — "Stawka: 1.50 → 2.00 zł", "Budżet: 100 → 150 zł". W GAds change history pokazuje tylko event type, trzeba klikać żeby zobaczyć szczegóły.
- **Pre-filter deep-link z Campaign → Keywords/SearchTerms** — jedno kliknięcie i widzę słowa tej konkretnej kampanii. W GAds też tak jest ale musisz wejść w kampanię, potem w zakładkę.
- **Confirm na pauzie z szacowanym dziennym ruchem** — "Wstrzymać? Średni dzienny ruch: ~340 kliknięć". GAds pyta tylko "Are you sure" bez kontekstu.
- **+10/+20/+50% quick shortcuts w modalu budżetu** — przyspiesza typową operację "podnieść budżet o 20%".
- **Manual role override blokuje auto-sync** — fajny safety net dla ręcznych klasyfikacji.

## Czego MI BRAKUJE vs Google Ads UI

- **Multi-select kampanii + bulk action** (pauza/wznowienie wielu jednocześnie, bulk edit budżetu +X%). W GAds zaznaczam checkboxami i mam "Edit → Change budget".
- **Kolumna "Optimization Score"** — w GAds widzę od razu % optymalizacji na liście kampanii. Tu nie widzę.
- **Experiment / Draft + A/B test** — w GAds mogę z poziomu kampanii klonować jako experiment. Tu nic.
- **Zmiana bidding strategy** — widzę strategię, mogę edytować target CPA/ROAS, ale nie przełączę z "Maximize conversions" na "Target ROAS" (a to częsta operacja).
- **Ustawienia kampanii** — locations targeting, language, ad schedule, network settings, device bid adjustments. Nic z tego nie widzę/nie zmienię.
- **Negative keyword lists na poziomie kampanii** — brak, muszę iść w Keywords.
- **Shared budgets** — nie widać czy kampania ma shared budget, nie mogę przypiąć.
- **Conversion actions przypisane do kampanii** (i custom conversion goals) — brak.
- **Assets / extensions (sitelinki, callouty, snippets, logo, images)** — w GAds na poziomie kampanii sekcja "Assets" jest kluczowa, tu nic.
- **Audience signals / custom audiences** dla PMax i Display — brak.
- **Wykres koszt vs konwersje w czasie z drugą osią** — Trend Explorer jest, ale GAds ma też porównanie dwóch metryk na jednym wykresie z dwoma osiami.
- **Pokaż zmiany w czasie (annotations)** — GAds ma annotations, tu timeline jest ale bez overlay na wykres.
- **Budget recommendation z GAds** ("zwiększ budżet o X zł aby uniknąć Lost IS") — w GAds jest w Recommendations. Tu nie widzę tego na kampanii, być może jest w Recommendations page — ale brakuje linku "zobacz rekomendacje dla tej kampanii".

## Co mnie irytuje / myli

- **Sortowanie domyślne po koszcie — ale widzę "10 000 zł" i "5 conv" obok siebie i muszę liczyć CPA w głowie**. Byłoby prościej mieć CPA jako kolumnę listy od razu.
- **Brak wizualnego odróżnienia typu kampanii na liście** — "Search" / "PMax" są tekstem. W GAds są ikonki (lupa, gwiazdka PMax, shopping bag). Tu na szybko nie odfiltruję wzrokiem.
- **Jak lista ma 50 kampanii i wybiorę jedną na dole, scroll szczegółu jest osobny** — muszę pamiętać że `maxHeight: calc(100vh - 160px)`. Jak mam małe okno to ginie.
- **Modal budżetu — shortcut +10%/+20%/+50%, ale nie ma +X zł ani -10%** (obniżanie budżetu w GAds zdarza się równie często).
- **Chip "Budzet 100 zł/d" z ołówkiem — ale ikonka ołówka ma 9px, ledwo widać**. Nie wiem czy kliknąć w chip czy w ikonkę.
- **"Target CPA" / "Target ROAS" pokazuje tylko jedno naraz** — jak kampania używa Maximize conversions bez targeta, chip się nie pokazuje, ale wtedy nie mogę w ogóle ustawić targeta z UI.
- **Karta "Rola kampanii" z Manual/Auto/Confidence to sporo real-estate** na górze. Ma przycisk zwijania, ale domyślnie jest rozwinięta — przy 20 wejściach dziennie to dużo scrollowania.
- **Nagłówki tabeli grup reklam** — "Konw." skrót jest ok, ale "Kliknięcia" pełne słowo obok — niespójne.
- **"CPA: 2.00 zł" — w seed data widzę fraktalne wartości**, jak w produkcji będzie 150 zł to ok, w seed wygląda jak bug.
- **Auction Insights chowa się gdy brak danych** — ok, ale jak pierwszy raz wchodzę nie wiem czy ten widget w ogóle istnieje dla tej kampanii. Lepszy empty-state.
- **Brak info "kiedy ostatni sync"** dla tej kampanii — widzę timeline ale metadata o ostatnim syncu z GAds API nie ma.
- **Timeline ma HELPER/ZEWN. ale jak filtruję po kampanii dostaję wąski zbiór** — pewne zmiany ogólne konta mogą być relewantne (np. zmiana bidding strategy globalnie), filtr to odcina.

## Co bym chciał

- **Bulk action: zaznacz 5 kampanii → podnieś budżet o 20% → confirm**. Codzienna operacja.
- **Bid simulator embedded** — "jeśli podniosę target CPA z 50 zł na 60 zł, spodziewany wzrost konwersji +18%, koszt +15%". GAds ma to w bidding section, tu brak.
- **Optimization Score z actionable recommendations** embedded na kampanii (nie linia do oddzielnej strony Recommendations).
- **"Top mover" widget** — które kampanie z konta miały największy % change vs poprzedni okres (WoW/MoM). Sortowanie pomaga ale widget z highlightem "uwaga, konwersje spadły 40%" byłby mocny.
- **Shared budget warning** — "Ta kampania jest w shared budget 'Brand Pool' razem z 3 innymi".
- **Labels multi-select z listy** — zamiast sortowania po cost_usd chciałbym "pokaż tylko Brand + Remarketing".
- **Conversions breakdown** — ta kampania 10 konwersji, ale których action? Purchase / Lead / Add to cart. Kluczowe dla wielo-celowych setupów.
- **Device bid modifier** — prosty widok "mobile: -20%, desktop: +0%" + edycja.
- **Day/Hour schedule** — widzę że w app jest Dayparting na dashboardzie, ale na kampanii chciałbym zobaczyć schedule i edytować.
- **"Show removed" toggle** — REMOVED kampanie są w STATUS_CONFIG ale filtrowanie chyba je wyklucza. Explicit toggle się przyda.

## Verdykt

**Tak, wchodziłbym tu codziennie.** Szczególnie na review Brand + Prospecting i szybkie pauzowanie/wznawianie. To jedno z lepszych "headline views" dla kampanii jakie widziałem — dużo informacji bez przeciążenia. Blocker to brak bulk actions i edycji settings kampanii (locations, schedule, assets) — bez tego wciąż muszę wracać do GAds UI na 30% operacji.

---

## Pytania do @ads-expert

1. Czy Protection HIGH dla Brand/PMax jest deterministyczny czy jest jakiś automat podnoszący HIGH gdy kampania ma np. >50% konta cost? Widzę tooltip ale nie widzę jak protection się wylicza.
2. Czy `Manual override` roli blokuje TYLKO role auto-sync, czy blokuje też Protection level? Jeśli setuję Brand manualnie, czy Protection automatycznie staje się HIGH?
3. Czy Budget Pacing pokazuje projekcję month-end czy tylko daily spend rate? Brakuje info "projekcja do końca miesiąca: X zł vs budget Y zł".
4. Auction Insights w seed ma mało podmiotów — czy w realnym koncie tych konkurentów bywa 20+? Jeśli tak, `limit={8}` jest za mało (powinno być "+ pokaż więcej").
5. Czy `getCampaignsSummary` zwraca dane tylko dla aktualnie wyfiltrowanych (campaignParams) czy całego konta? Jeśli całego, to filtr po metryce pokazuje "10 000 zł koszt" dla kampanii która w wybranym okresie miała 500 — mylące.
6. Brak "bidding strategy switch" (Max conv ↔ Target CPA ↔ Target ROAS) — czy to świadoma decyzja (zbyt ryzykowne z poziomu apki) czy brak?
7. IS metrics: `search_impression_share` w backend jest 0.0-1.0 czy 0-100? Widzę `isPct && raw * 100` — ok, ale `search_top_impression_share` też? Jeden punkt prawdy czy jest ryzyko niespójności?
8. "Grupy reklam" pokazuje wszystkie ad groups kampanii w zakresie dat — co z grupami REMOVED lub bez kliknięć? Filtrowane out czy wiersze z zerami?
