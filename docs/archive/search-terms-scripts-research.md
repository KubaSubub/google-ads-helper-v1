# Research: Search Terms Scripts — katalog akcji i spec implementacji

**Status**: Research / Pre-spec
**Data**: 2026-04-11
**Autor**: Claude + Kuba

## Skąd to przyszło

Po code review obecnej wersji Quick Scripts (`clean_waste`, `pause_burning`, `boost_winners`, `emergency_brake`) okazało się że **reguły ignorują filtr daty** — `_rule_5_add_negative`, `_rule_1_pause_keywords` itd. przyjmują parametr `days: int` ale nigdy go nie używają. Agregują ALL-TIME snapshot z tabeli `SearchTerm`/`Keyword`, więc count "1 do wykonania" jest ten sam dla filtra 7, 30, 90 dni i `all_time`.

Decyzja: **zablokować obecne skrypty i całą stronę /recommendations** do czasu przepisania + **zbudować nowy katalog skryptów specjalnie dla Search Terms**, które realnie działają na wybranym lookback window.

Obecny stan to wersja "we made it work for demo" — teraz robimy wersję "ma realną wartość dla specjalisty PPC".

## Co już mamy w infrastrukturze

**Dobre wiadomości — wiele już istnieje:**

- `SearchTerm` table ma `date_from` / `date_to` per wiersz (kolumny migracyjne)
- `SearchTermsService._fetch_terms(client_id, date_from, date_to, campaign_type, campaign_status)` — **już obsługuje date overlap logic** ([search_terms_service.py:92](backend/app/services/search_terms_service.py#L92)). Używa:
  ```python
  q1 = q1.filter(SearchTerm.date_to >= date_from)  # term overlaps window start
  q1 = q1.filter(SearchTerm.date_from <= date_to)  # term overlaps window end
  ```
- `NegativeKeyword` model + relacje z campaign/ad_group
- `POST /search-terms/bulk-add-negative` — atomic batch add ([search_terms.py:208](backend/app/routers/search_terms.py#L208))
- `POST /search-terms/bulk-add-keyword` — promote term to keyword ([search_terms.py:316](backend/app/routers/search_terms.py#L316))
- `POST /search-terms/bulk-preview` — dry run preview ([search_terms.py:395](backend/app/routers/search_terms.py#L395))
- `ActionExecutor.apply_add_negative_batch()` — routing przez circuit breaker + ActionHistory log
- Frontend: `SearchTermsPage` z filtrami, sortowaniem, segmentacją

**Czego brakuje:**

- Reguły rekomendacji nie konsumują date-aware path — trzeba je przepisać
- Brak n-gram analizy (pojedyncze słowa agregowane cross-terms)
- Brak detekcji "new terms" (trending)
- Brak detekcji "disappearing terms" (was converting, stopped)
- Brak scripted pipeline — każdy skrypt osobną logiką, nie framework

## Kategorie problemów które specjalista realnie rozwiązuje

Po przeglądzie [playbook'a](../../google_ads_optimization_playbook.md), code'u i standardów branżowych (agency best practices, SKAG vs STAG approach, Google Ads Help Center):

### A) WASTE ELIMINATION (dodaj negatywy)

Najczęstsza codzienna czynność. Specjalista spędza 30-60 min dziennie na przeglądaniu listy search terms.

### B) EXPANSION (dodaj jako keyword)

Odnajdywanie "hidden gems" — zapytań które konwertują dobrze ale nie są jeszcze targetowane jako keyword.

### C) MATCH TYPE OPTIMIZATION

Promocje match type na podstawie performance (broad → phrase → exact).

### D) DUPLICATE / CANNIBALIZATION

Wykrycie gdy to samo search term jest matchowane przez wiele ad groups/kampanii.

### E) TEMPORAL / TRENDING

Wykrycie nowych, znikających, sezonowych patternów.

### F) N-GRAM ANALYSIS

Analiza pojedynczych słów i fraz zamiast całych terms.

---

## KATALOG SKRYPTÓW

Każdy skrypt ma:
- **ID** (kod jednoznaczny)
- **Nazwa** (polska etykieta UI)
- **Opis** (co robi)
- **Kryteria** (threshold'y, domyślne wartości)
- **Wymagane dane** (tabele + kolumny)
- **Akcja** (NEGATIVE / KEYWORD / BID / OBSERVE)
- **Priorytet impl** (P0 must-have / P1 should / P2 nice-to-have)
- **Cost of wrong action** (co się stanie jak źle zadziała)

---

### A. WASTE ELIMINATION

#### A1. Zero-Conversion Waste
**ID**: `waste_zero_conv`
**Nazwa**: Zero konwersji przy wysokim koszcie
**Opis**: Search term wygenerował N+ kliknięć i/lub X+ PLN wydatku, 0 konwersji w wybranym okresie.
**Kryteria (konfigurowalne)**:
- `min_clicks`: 5 (default)
- `min_cost_pln`: 20 (default)
- `conversions`: 0 (hard)
- `lookback_days`: user-selected
**Dane**: `SearchTerm` (clicks, cost_micros, conversions) z date overlap filter
**Akcja**: Add as CAMPAIGN or AD_GROUP negative (exact or phrase match)
**Priorytet**: P0
**Cost of wrong action**: Średni — blokujemy query które mogło jeszcze dowieźć konwersję (mitigation: threshold w statystyce, nie tylko koszt)

#### A2. Irrelevant Keyword Detection (dictionary)
**ID**: `waste_irrelevant_dict`
**Nazwa**: Nieistotne słowa ze słownika
**Opis**: Search term zawiera słowo ze słownika negatywnego (free, darmowy, jak, tutorial, opinie, używany, cheap, job, praca, DIY, zrób, tania, najtańsze, vs, porównanie, recenzja…).
**Kryteria**:
- `dictionary`: lista editable per klient (global default + client overrides)
- `min_clicks`: 1 (agresywne — nie czekamy)
- Match: word boundary regex, case-insensitive
**Dane**: `SearchTerm.text` + user-maintained dictionary (nowa tabela `negative_dictionary`)
**Akcja**: Add as CAMPAIGN negative (phrase match z triggering word)
**Priorytet**: P0
**Cost of wrong action**: Niski — słowa "free/tutorial" prawie nigdy nie konwertują w commercial campaigns. Mitigation: whitelist per klient (np. agencja reklamująca darmowe konsultacje)

#### A3. Low CTR Waste
**ID**: `waste_low_ctr`
**Nazwa**: Bardzo niski CTR przy wysokich impression
**Opis**: Search term ma impresje > X, ale CTR < Y% — znaczy że user widzi reklamę, nie klika, bo reklama nie pasuje do intent'u. Marnowanie budżetu na zbieranie low-quality impressions (wpływa też na QS kampanii).
**Kryteria**:
- `min_impressions`: 100
- `max_ctr_pct`: 0.5 (0.5%)
- `lookback_days`: user-selected
**Dane**: `SearchTerm` (impressions, clicks)
**Akcja**: Add as CAMPAIGN negative (phrase match)
**Priorytet**: P1
**Cost of wrong action**: Średni — może ucinać brand awareness queries. Mitigation: exclude gdy term zawiera brand name z client settings

#### A4. High Cost No ROAS (shopping/pmax)
**ID**: `waste_high_cost_no_roas`
**Nazwa**: Wysoki koszt bez zwrotu (PMax/Shopping)
**Opis**: Search term/search theme wydał X PLN, ROAS poniżej progu (np. < 1.0 = tracący pieniądze).
**Kryteria**:
- `min_cost_pln`: 100
- `max_roas`: 1.0
- `min_clicks`: 10 (statistical significance)
**Dane**: `SearchTerm` (cost_micros, conversion_value_micros, clicks, source='PMAX')
**Akcja**: Dla SEARCH → negative keyword. Dla PMAX → brand exclusion (wymaga v21+ API) LUB manual review alert.
**Priorytet**: P1
**Cost of wrong action**: Średni — ROAS < 1 może być OK dla brand awareness / re-engagement. Mitigation: oznaczyć jako alert nie auto-apply

#### A5. Informational Intent Detection
**ID**: `waste_informational_intent`
**Nazwa**: Zapytania informacyjne w kampaniach commercial
**Opis**: Search term zaczyna się od "jak", "co to", "dlaczego", "gdzie", "kiedy", "who is", "what is", "how to", "why does" — to intent informacyjny, użytkownik nie chce kupić, tylko wiedzieć.
**Kryteria**:
- `patterns`: lista regexów (pl + en + de configurable per rynek)
- Wyklucz kampanie typu "Content" / "Awareness" (tag kampanii lub nazwa)
- `min_clicks`: 1
**Dane**: `SearchTerm.text`, `Campaign.name` (dla exclude)
**Akcja**: Add as CAMPAIGN negative (phrase match z pierwszych 2 słów)
**Priorytet**: P1
**Cost of wrong action**: Niski. Mitigation: whitelist dla kampanii typu "awareness"

---

### B. EXPANSION (promote to keyword)

#### B1. High-Converting Term Promotion
**ID**: `expand_high_conv`
**Nazwa**: Promocja top performerów do keywords
**Opis**: Search term ma N+ konwersji, CVR wyższy niż średnia kampanii, CPA poniżej target — a nie jest jeszcze jako keyword. Dodaj jako exact match keyword żeby:
1. Lepiej kontrolować bid
2. Nie płacić premium za broad match matching
3. Zapewnić ciągłe targetowanie

**Kryteria**:
- `min_conversions`: 3
- `cvr_multiplier`: 1.5 (CVR termu >= 1.5× CVR kampanii)
- `max_cpa_pct_of_target`: 100 (CPA <= target)
- `lookback_days`: user-selected (zazwyczaj 30-90)
- **Nie jest już** w `Keyword` table (check przez text normalization)
**Dane**: `SearchTerm`, `Campaign`, `Keyword` (do check duplicates)
**Akcja**: Add as EXACT match keyword do najbliższego pasującego ad group (match przez similarity / campaign name)
**Priorytet**: P0 (to jest "money maker" — hidden gems are what specialists love to find)
**Cost of wrong action**: Niski — dodanie exact match do już działającego query nie zepsuje niczego (możliwe tylko lekkie double-counting bidów)

#### B2. Rising Star — New Converting Terms
**ID**: `expand_rising_star`
**Nazwa**: Nowe konwertujące zapytania
**Opis**: Term pojawił się dopiero w ostatnich 14 dniach (nie ma wcześniejszych rekordów w SearchTerm z tego klienta), już konwertuje.
**Kryteria**:
- `first_seen_within_days`: 14
- `min_conversions`: 1
- `min_impressions`: 20
**Dane**: `SearchTerm` z agregacją po `date_from` (historical check)
**Akcja**: Alert "Check manually" + option to promote
**Priorytet**: P2
**Cost of wrong action**: Niski (tylko alert, nie auto-apply)

#### B3. Volume Scaling Opportunity
**ID**: `expand_scale_volume`
**Nazwa**: Możliwość skalowania wolumenu
**Opis**: Term konwertuje, CTR > średnia, ale impresje nisko — znaczy że jesteśmy limitowani przez bid/budget, można zwiększyć.
**Kryteria**:
- `conversions >= 1`
- `ctr_multiplier`: 1.2 (CTR >= 1.2× avg)
- `impression_share < 50%` (jeśli dostępne dla search terms)
**Dane**: `SearchTerm`, `Campaign.search_impression_share`
**Akcja**: Alert + recommendation "increase bid by X% on ad group containing this keyword"
**Priorytet**: P2
**Cost of wrong action**: Średni (zwiększanie bidu kosztuje)

---

### C. MATCH TYPE OPTIMIZATION

#### C1. Broad Match Waste → Phrase
**ID**: `match_broad_to_phrase`
**Nazwa**: Broad match traci pieniądze — promocja do phrase
**Opis**: Keyword w broad match generuje waste > X PLN (terms że nijak się ma do keyword). Propozycja: zmień match type na phrase, albo dodaj keyword jako phrase + wyłącz broad.
**Kryteria**:
- Keyword match_type = 'BROAD'
- Suma cost na waste terms (zero conv) > 50 PLN w lookback
- At least 3 different waste terms matched
**Dane**: `SearchTerm`, `Keyword` (join przez `keyword_text`)
**Akcja**: Alert z action "change match type" (wymaga osobnego ActionExecutor method)
**Priorytet**: P2 (więcej pracy nad routerem akcji)
**Cost of wrong action**: Wysoki (phrase ogranicza zasięg). Mitigation: tylko alert, manual confirm

#### C2. Duplicate Coverage Detection
**ID**: `dup_coverage`
**Nazwa**: Duplikat matchowania (cannibalization)
**Opis**: Ten sam search term jest matchowany przez >1 ad group (lub >1 keyword). Powoduje cannibalization bidów — 2 keywordy płacą za to samo query.
**Kryteria**:
- Search term z >= 2 różnymi `ad_group_id` w historycznych danych
- Kryteria na obie kopie: clicks > 5
**Dane**: `SearchTerm` (grouped by text), `AdGroup`
**Akcja**: Alert + recommendation "add negative to losing ad group"
**Priorytet**: P1
**Cost of wrong action**: Niski (tylko alert)

---

### D. N-GRAM ANALYSIS (systemic waste)

#### D1. Single Word Waste (unigram)
**ID**: `ngram_unigram`
**Nazwa**: Pojedyncze słowa marnujące budżet
**Opis**: Agregacja: podziel wszystkie search terms na słowa, zgrupuj po słowach, znajdź słowa które:
- Pojawiają się w wielu terms (>= 5)
- Łączny koszt > X PLN
- Łączna liczba konwersji = 0
Przykład: słowo "tani" pojawia się w 12 różnych terms, wydały razem 200 PLN, 0 konwersji → dodaj "tani" jako phrase negative.

**Kryteria**:
- `min_term_count`: 5 (ile różnych terms zawiera słowo)
- `min_total_cost`: 50 PLN
- `max_conversions`: 0
- Stop words excluded (i, w, na, z, dla, the, a, is, of)
- Case-insensitive, stemming opcjonalnie
**Dane**: `SearchTerm.text` split + aggregate
**Akcja**: Add word as phrase negative at CAMPAIGN level
**Priorytet**: P0 (to jest killer feature — specjaliści to robią ręcznie w Excelu)
**Cost of wrong action**: Średni — słowo może być legit w innym kontekście. Mitigation: whitelist per klient + preview list of all terms that would be affected

#### D2. Bigram / Trigram Waste
**ID**: `ngram_bigram`
**Nazwa**: Frazy 2-3 słowne marnujące budżet
**Opis**: Jak D1 ale dla par/trójek słów. Często bardziej precyzyjne niż pojedyncze słowa (np. "work from home" jako bigram zamiast "work" jako unigram).
**Kryteria**: jak D1 + n=2 i n=3
**Dane**: `SearchTerm.text`
**Akcja**: Add bigram/trigram as phrase negative
**Priorytet**: P1
**Cost of wrong action**: Niski (bigramy są specyficzne)

#### D3. Top Waste Words Report (no action, audit)
**ID**: `ngram_audit`
**Nazwa**: Raport słów marnujących budżet (tylko audyt)
**Opis**: Jak D1/D2 ale bez auto-action — tylko raport top 20 słów/fraz marnujących najwięcej, z breakdown per kampania.
**Akcja**: View-only report
**Priorytet**: P0 (prosty do zbudowania, user może sam decydować)

---

### E. TEMPORAL / TRENDING

#### E1. Sudden Drop Detection
**ID**: `temporal_drop`
**Nazwa**: Nagły spadek konwersji na znanym termie
**Opis**: Term konwertował przez poprzednie N dni, ostatnie K dni — spadek > 50%.
**Kryteria**:
- Window 1: previous N days (e.g. 30)
- Window 2: last K days (e.g. 7)
- `conv_drop_pct`: 50
- Minimum convs in window 1: 3
**Dane**: `SearchTerm` z historical date_from segmentation
**Akcja**: Alert (manual review)
**Priorytet**: P2
**Cost of wrong action**: Niski (tylko alert)

#### E2. Seasonal Deadweight
**ID**: `temporal_seasonal`
**Nazwa**: Sezonowe zombie keywords
**Opis**: Term nie konwertuje od 60+ dni, ale historycznie konwertował. Prawdopodobnie sezonowy.
**Akcja**: Alert z history graph
**Priorytet**: P2

---

### F. BRAND / COMPETITOR

#### F1. Competitor Term Detection
**ID**: `brand_competitor`
**Nazwa**: Search terms zawierające konkurenta
**Opis**: Term zawiera nazwę konkurenta ze słownika. Specjalista decyduje czy zostawić (atak na konkurenta) czy wykluczyć (reklama ich bronda).
**Kryteria**:
- Dictionary per klient: lista nazw konkurentów
- Match: word boundary, case-insensitive
**Dane**: `SearchTerm.text` + nowa tabela `competitor_dictionary` lub client.ai_context
**Akcja**: Alert z kontekstem (CPA / conversions)
**Priorytet**: P1
**Cost of wrong action**: Wysoki (auto-add jako negative może uciąć valuable prospecting)

---

## Priorytety implementacji (sprint plan)

### Sprint 1 — Foundations (2-3 dni)
1. **Nowy router** `/scripts` — osobny od `/recommendations` (ten zostaje wyłączony)
2. **Nowa tabela** `negative_dictionary` (client_id + text + source_global/client + created_at)
3. **Framework**: `ScriptsService` z base class, rejestr skryptów, dry-run first pattern
4. **Date-aware query** → każdy skrypt konsumuje `date_from`/`date_to` z request
5. **Akcja = POST /scripts/{script_id}/dry-run** → preview results
6. **Akcja = POST /scripts/{script_id}/execute** → apply z item_ids filter (jak w bulk-apply)

### Sprint 2 — P0 Scripts (3-4 dni)
1. **A1 — Zero-Conversion Waste** (najprostszy, proof of concept)
2. **A2 — Irrelevant Dictionary** (wymaga dict table)
3. **B1 — High-Converting Promotion** (wymaga routingu do ad group)
4. **D1 — Unigram Waste Aggregation** (wymaga nowej agregacji)
5. **D3 — N-gram Audit Report** (tylko view)

### Sprint 3 — P1 Scripts (3-4 dni)
6. A3 — Low CTR Waste
7. A4 — High Cost No ROAS
8. A5 — Informational Intent
9. D2 — Bigram/Trigram Waste
10. C2 — Duplicate Coverage Detection
11. F1 — Competitor Term Detection

### Sprint 4 — P2 Scripts + polish
12. B2 — Rising Star
13. B3 — Volume Scaling
14. C1 — Broad Match Waste → Phrase (wymaga match type mutation)
15. E1/E2 — Temporal analysis

## Frontend

### Nowa strona `/scripts`

**Layout**:
```
┌─ Header: "Skrypty Search Terms" ──────────────────────────┐
│  [Filtr daty]  [Kampanie]  [Odśwież]                      │
└────────────────────────────────────────────────────────────┘

┌─ Waste Elimination ────────────────────────────────────────┐
│  [A1] Zero Conv Waste         42 terms  ~320 zł   [Run]    │
│  [A2] Irrelevant Dictionary   18 terms  ~140 zł   [Run]    │
│  [A3] Low CTR Waste            7 terms   ~90 zł   [Run]    │
│  [A5] Informational Intent    12 terms   ~60 zł   [Run]    │
└────────────────────────────────────────────────────────────┘

┌─ Expansion ────────────────────────────────────────────────┐
│  [B1] High Converting Promotion    4 terms  ~500 zł/m [Run]│
│  [B2] Rising Stars                 2 terms   ~80 zł/m [Alert]│
└────────────────────────────────────────────────────────────┘

┌─ N-gram Analysis ──────────────────────────────────────────┐
│  [D1] Single Word Waste       8 words    ~240 zł   [Run]   │
│  [D2] Bigram Waste            3 phrases  ~120 zł   [Run]   │
│  [D3] Full Audit Report                           [View]   │
└────────────────────────────────────────────────────────────┘
```

**Kliknięcie [Run]** → modal z:
1. Opis skryptu + parametry (editable przed run)
2. Preview list (dry-run result) z checkboxami per item
3. Szacowany impact: koszt/oszczędność, liczba itemów
4. Confirm → execute z zaznaczonymi
5. Result: success/failed breakdown + link do historii

**Parametry konfigurowane per skrypt**:
- Lookback window (dziedziczony z global filter, override możliwy)
- Thresholdy (min_clicks, min_cost, min_impressions itd.)
- Scope (CAMPAIGN vs AD_GROUP negative)
- Campaign filter (lista do wykluczenia/włączenia)

### Dictionary Management

**Nowy tab w Settings**: "Słowniki" — tam user edytuje:
1. **Negative dictionary** (A2) — globalny seed + per-klient override
2. **Competitor dictionary** (F1) — per klient
3. **Brand exclusions** (A3 mitigation) — per klient
4. **Whitelist** (zachowaj term mimo że pasuje do negatywu)

## Open Questions

1. **Czy używamy `SearchTerm.date_from`/`date_to` overlap czy filtrujemy inaczej?**
   Obecny overlap może dawać double-count gdy term ma 3 różne okna synców. Rozwiązanie: dedup przez `(campaign_id, ad_group_id, text)` + SUM metryk, a overlap tylko do filter'a "czy term był aktywny w okresie".

2. **Gdzie przechowujemy dictionaries?** Tabela DB (edytowalna w UI) vs YAML file (wersjonowane w git). Decyzja: tabela DB + possibility to seed z globalnego YAML defaults.

3. **Jak routing negative: AD_GROUP czy CAMPAIGN level?**
   Domyślnie CAMPAIGN (szerszy zasięg, prostszy). AD_GROUP tylko gdy user explicitly zaznaczy.

4. **Match type dla negatywu?**
   Playbook sugeruje PHRASE. Dla specific terms EXACT. Decyzja: default PHRASE (bezpieczniej niż EXACT który łapie tylko 1:1, szerszy niż BROAD który może uciąć za dużo).

5. **Circuit breaker / safety limits na auto-execute?**
   Proponuję: max 50 negatives per script run, max 200 per dzień per klient, required dry-run before execute. Już mamy `ActionExecutor` safety.

6. **Czy wyłączyć stary Recommendations engine kompletnie czy tylko zablokować UI?**
   Obecnie zablokowałem tylko UI. Engine nadal regeneruje w background przy fetch'u `/recommendations`. Decyzja TBD — oszczędność CPU vs ryzyko psucia istniejących flows.

## Metrics / Success Criteria

Po wdrożeniu v1 Scripts chcemy mierzyć:

1. **Time to waste identification**: specjalista znajduje top 10 waste words w < 30 sekund (dziś: 10-15 min w Excelu)
2. **Action volume**: min 50 negatives dodanych / klient / tydzień (dziś: 10-20 manualnie)
3. **False positive rate**: < 5% negatives dodanych skryptem jest manually cofniętych w ciągu 7 dni
4. **Coverage**: skrypty adresują >= 80% sytuacji które specjalista rozwiązuje ręcznie
5. **User trust**: po 2 tygodniach używania user loguje się 1-2× dziennie żeby odpalić skrypty, zamiast manualnie przeglądać każdy term

## Decyzje do podjęcia (przed implementacją)

- [ ] Czy budujemy wszystkie P0 naraz czy jeden po drugim z review po każdym?
- [ ] Czy dictionary jest globalne (one seed) czy per klient od razu?
- [ ] Czy integrujemy z istniejącym `/search-terms/bulk-*` czy budujemy osobny flow w `/scripts/*`?
- [ ] Czy /recommendations page zostaje (z innym content'em) czy usuwamy z nawigacji?
- [ ] Nazwa finalna: "Skrypty" vs "Akcje" vs "Optymalizacje" vs "Automatyzacja"?

---

## Załącznik: What competitors do

Briefowo, żeby nie reinventować:

- **Optmyzr**: ma "Rule Engine" gdzie user tworzy własne reguły (N clicks + 0 conv + Y dni → negative). My możemy zacząć od predefined rules, dodać custom później.
- **Adzooma**: "Opportunities" feed — AI-powered recommendations, głównie na n-gram waste.
- **Marin**: "Bid Optimization" + "Query Mining" — agreguje queries per n-gram, pokazuje waste.
- **Google Ads native Recommendations**: pokazuje "Add negative keywords" z suggested items, ale nie tłumaczy dlaczego (black box). My dajemy pełny "why" panel.

Konkluzja: **nasza przewaga to**
1. Real date-aware analysis (wiele tools operuje na snapshot)
2. Transparency — każda akcja ma "why" + dokładne liczby
3. Per-klient dictionaries (adaptacja do branży)
4. Dry-run first (zero-risk workflow)
