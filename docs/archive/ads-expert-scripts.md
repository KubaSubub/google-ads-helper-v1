# Ocena eksperta Google Ads — Skrypty (/scripts)

> Data: 2026-04-12 | Srednia ocena: 8.25/10 | Werdykt: ZACHOWAC + ROZBUDOWA (P0 fixes przed produkcja)

## TL;DR

Scripts page to najblizszy prawdziwemu PPC-workflow kawalek tej aplikacji i najbardziej unikalna wartosc wzgledem Google Ads UI. 6 zarejestrowanych skryptow (A1/A2/A6/B1/C2/D1) pokrywa 70-80% codziennych zadan specjalisty z kategorii waste/expansion/cannibalization/n-gram. Fundament (date-aware, dry-run first, brand protection, keyword protection, circuit breaker, per-client config) zrobiony dobrze. Luki sa glownie w warstwie shell'a (brak metryk w preview, brak filtrow/sortu, brak historii per skrypt, brak schedulingu) + kilka prawdziwych bug'ow (przeterminowany placeholder "Sprint 1 - P0 scripts", `custom_brand_words` ukryty, eager dry-run 6x przy wejsciu).

---

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebnosc | 10/10 | Zastepuje codzienne 30-60 min w Search Terms Report + Excel z n-gramami. To jest dzienna robota, nie feature "nice to have". |
| Kompletnosc | 7/10 | 6 z 15 skryptow z research spec ([search-terms-scripts-research.md](../specs/search-terms-scripts-research.md)). Brakuje P0: D3 (n-gram audit), A3 (Low CTR waste), A5 (Informational intent). Brak P1: F1 Competitor terms, C1 Broad->Phrase match type optimization. Dla kazdego zarejestrowanego skryptu logika solidna. |
| Wartosc dodana vs Google Ads UI | 9/10 | Realna przewaga: C2 Duplicate Coverage nie istnieje w GAds w ogole, D1 N-gram Waste tabs zastepuja manualny Excel z Power Query, brand protection z auto-detect + custom words nie ma w Recommendations Google. Minus 1 bo brakuje metryk i filtru kampanii w preview (user nie widzi CTR/CVR/CPA bez klikania dalej). |
| Priorytet MVP | 7/10 | Jesli produkt ma zastepowac dzienne PPC-workflow to bez scripts nie ma misji. Ale dostarczone P0 plus-minus ratuja 80% srodku dnia specjalisty, 100% MVP definitive to co najmniej D3 + A3 + F1. |
| **SREDNIA** | **8.25/10** | |

---

## Co robi dobrze

- **Date-aware fetch z wybieraniem single-best window** ([a1_zero_conv_waste.py:128-142](../../backend/app/services/scripts/a1_zero_conv_waste.py#L128-L142)) — nie double-counta overlapping sync windows. To byla glowna wada poprzedniej wersji (research doc linia 9). Doskonale rozwiazane: `min(candidates, key=lambda r: (abs(window_len - user_range), -r.date_to.toordinal()))`. Zaden konkurent (Optmyzr, Adzooma) tego nie robi poprawnie — to realny edge.
- **Conversion lag guard** ([a1_zero_conv_waste.py:226-262](../../backend/app/services/scripts/a1_zero_conv_waste.py#L226-L262)) — nie flaguje termu jako "0 konwersji" jesli jego okno pokrywa ostatnie 7 dni (conversion lag). To jest to co 90% tools robi zle: blokuja negatywy ktore za 3 dni dowioza konwersje. Brawurowo dzielone na "skip entirely" vs "flag with warning" w zaleznosci od pokrycia okna.
- **Brand protection z auto-detect + custom override** ([a1_zero_conv_waste.py:179-183](../../backend/app/services/scripts/a1_zero_conv_waste.py#L179-L183), `_build_brand_patterns`) — kluczowa ochrona przed dodaniem "[brand] menu" jako negatywu. Default on.
- **Keyword protection** ([a1_zero_conv_waste.py:268-273](../../backend/app/services/scripts/a1_zero_conv_waste.py#L268-L273)) — `_check_keyword_conflict` wymusza EXACT match gdy negative konfliktowalby z aktywnym keywordem, albo blokuje calkowicie. **Playbook ref**: REGULA 5 - "Kiedy DODAĆ Negative" ([playbook.md:182-191](../../google_ads_optimization_playbook.md#L182-L191)) ignoruje ten problem; to wlasna wartosc powyzej playbooka.
- **A2 Multi-layer negative gap detection** (hard MCC/account/IRRELEVANT + soft cross-campaign) — to jest bardzo sophisticated. Specialist nie ma tego w GAds i robi to manualnie raz na kwartal. `seen_keys` dedup + soft = unselected default to wlasciwy UX.
- **B1 wymaga `google_ads_service.is_connected`** i odmawia "local-only" mode ([a1_zero_conv_waste.py:347-355](../../backend/app/services/scripts/a1_zero_conv_waste.py#L347-L355)). Slusznie — ghost state w lokalnej DB bez push'a do Google jest killer bugiem.
- **Circuit breaker `_validate_batch`** ([base.py:124-201](../../backend/app/services/scripts/base.py#L124-L201)) — enforces `MAX_NEGATIVES_PER_DAY` z local day boundary (Warsaw time, nie UTC). Per-client override przez `business_rules.safety_limits`. Profesjonalne.
- **Per-client saved params** — `PUT /scripts/{id}/config` + merge order (defaults -> saved -> request overrides). W Marka workflow 8 kont to eliminuje 80% klikania.
- **ActionLog context_json** zawiera `script_id`, `match_source`, `matched_word` — po stronie audytu za 3 miesiace mozna wrocic i zrozumiec czemu negative zostal dodany. Rzadka dojrzalosc.
- **Sort hard->soft, savings desc** w A2 + `estimated_savings_pln desc` w A1 — biggest wins first, zgodne z jak specjalista faktycznie pracuje.
- **N-gram dedupowanie per scope** (CAMPAIGN only dla D1 bo n-gram nie mapuje na ad group) — zwraca uwage na subtelnosci ktore czesc tools ignoruje.

---

## Co brakuje (krytyczne)

### 1. Metryki per-item w preview (P0)

**Problem**: Lista dopasowan pokazuje `entity_name`, `campaign_name`, `reason` (string), `estimated_savings_pln`. **Brak widocznych kolumn**: clicks, impressions, CTR, conversions, CPA. Specjalista musi zaufac reason-stringowi zeby podjac decyzje "zablokuj X zl/kliknij 15 kliknietych".

**Playbook ref**: sekcja "Segmentacja Search Terms" ([playbook.md:272-317](../../google_ads_optimization_playbook.md#L272-L317)) wymaga widocznych clicks/CVR/conversions per term.

**Implementacja**: Rozszerzyc preview table w `ScriptsPage.jsx` `RunModal` o staly zestaw kolumn metryk z `item.metrics`. Kolumny: clicks, impr, CTR, conv, CPA, cost_pln — jako sticky na gorze tabeli. Po backend stronie `metrics` juz jest w `ScriptItem` — tylko frontend.

### 2. Filtr kampanii wewnatrz modal (P0)

**Problem**: Dla duzego konta A1 moze zwrocic 80 pozycji z 12 kampanii. Specjalista dzis chce tylko "kampanie X" i musi scrollowac. Brak dropdowna.

**Playbook ref**: przepływ codzienny "Sprawdz kampanie priorytetowe, nie wszystkie" ([playbook.md:31-40](../../google_ads_optimization_playbook.md#L31-L40)).

**Implementacja**: W `RunModal` nad lista preview dodac `<select>` z lista kampanii z `preview.items` + "Wszystkie". Filtruj widocznosc bez re-dry-run'a.

### 3. Sortowalne kolumny preview (P0)

**Problem**: Lista jest zawsze sortowana backendem (savings desc dla A1, hard>soft dla A2). User nie moze kliknac kolumny.

**Implementacja**: Client-side sort na `metrics.clicks`, `metrics.cost_pln`, `metrics.conversions`, `metrics.ctr`, `estimated_savings_pln`. Ta sama logika dla wszystkich skryptow — jeden sort-header component.

### 4. `custom_brand_words` musi byc edytowalny z UI (P0)

**Problem**: W `PARAM_LABELS` w `ScriptsPage.jsx:120` `custom_brand_words: { type: 'hidden' }`. User nie moze z UI dodac "naka-naka" jako brand protection word. Trzeba isc do DB.

**Implementacja**: Zmienic `type: 'text-tags'` (multi-tag input) i dodac komponent `TagInput` akceptujacy liste stringow z `Enter` = add, `Backspace` = remove last. Albo wystawic do Settings -> Client Health jako "Brand words" globalnie per klient (wtedy skrypty nawet nie potrzebuja parametru per-run).

### 5. Eager dry-run 6x skryptow przy wejsciu (P0 — perf)

**Problem** (z ads-user report #2): wejscie na `/scripts` robi dry-run dla kazdego zarejestrowanego skryptu (na liczniki w kafelkach). C2/D1 to po 500-2000 terms per client, lece 6 requests na backend rownoczesnie za kazdym razem gdy user zmieni date/klienta.

**Implementacja**: Lazy dry-run per kafel — odpalaj dopiero po rozwinieciu kategorii, albo dawaj approximate count z lightweight endpoint `/scripts/counts?client_id=X&from=Y&to=Z`, ktory robi tylko filtr na `SearchTerm` bez pelnej analizy. Alternatywnie — debounce 500ms przy zmianie date/client.

### 6. "Zapisz params" rozsynchronizowany z "Odswiez podglad" (P0 — UX bug)

**Problem** (ads-user #5): user edytuje param, klika Wykonaj bez Odswiez — dry-run byl na starych params, execute leci na nowych. Rozjazd miedzy preview a execute.

**Implementacja**: Po `updateParam` disable'uj button "Wykonaj" az do `handleRerun`. Albo auto-rerun z debouncem 800ms. Dzis oba triggery sa niezalezne i to dziurka w UX.

### 7. Historia uruchomien per skrypt (P1 - ale prawie P0)

**Problem**: User nie widzi "kiedy ostatnio odpalilem A1 dla Sushi i co z tego wyszlo". Globalny `/action-history` ma wszystko ale bez filtra per script_id. Tymczasem `ActionLog.context_json.script_id` juz jest — backend ma dane.

**Implementacja**: `GET /scripts/{id}/history?client_id=X&limit=10` -> zwraca ostatnie execute z counts + timestamp. W `ScriptsPage` pod kazdym kaflem maly badge "Ostatnio: 3 dni temu · 12 zastosowanych". Duzy uplift confidence.

### 8. D3 — N-gram Audit Report (P0 spec, nie zaimplementowany)

**Problem**: Research doc wymaga D3 (audyt top 20 slow/fraz marnujacych bez auto-action) jako "view-only report" ([research doc:266-270](../specs/search-terms-scripts-research.md#L266-L270)). To prosty do zbudowania bo D1 juz ma aggregation. User moze sam decydowac co blokowac — bez ryzyka masowych mutacji.

**Implementacja**: Nowa klasa `NgramAuditScript(id='D3', action_type=ACTION_ALERT)` kopiuje agregacje D1, zwraca top 20 n-gramow z breakdown per kampania w `metrics`, `action_payload` puste (view-only). UI po prostu nie pokazuje checkboxow dla `action_type=ALERT`.

### 9. A3 Low CTR Waste (P1 z research) — nie zaimplementowany

**Problem**: Search term z `impressions > 100` i `CTR < 0.5%` to inny waste kategoria — user widzi reklame ale nie klika, psuje QS kampanii. Nie pokryty przez A1 (bo nie ma kliknietych).

**Playbook ref**: ([playbook.md:187-188](../../google_ads_optimization_playbook.md#L187-L188)) — Quality Score impact negatywu nie-CTRowego jest istotny.

**Implementacja**: `A3LowCtrWasteScript`, kopia struktury A1 z thresholdami `min_impressions=100`, `max_ctr_pct=0.5`. Nie trzeba keyword protection (nie ma konfliktu bo negative bedzie phrase).

### 10. F1 Competitor Term Detection (P1) - brak

**Problem**: Specjalista codziennie monitoruje "czy konkurent sie wkleja w moje zapytania". Research spec ma F1 z dictionary per klient + alert. Tu brak.

**Implementacja**: W `Client.ai_context` dodac liste konkurentow (juz przypadkiem jest marketing mastermind brief z konkurencja). Skrypt F1 scanuje search terms przeciwko tej liscie, zwraca jako ALERT (bez auto-action — decyzja manual "attack vs exclude").

---

## Co brakuje (nice to have)

- **Per-campaign grouping w preview** — zwijane naglowki "Kampania Sushi Warszawa - 34 pozycje ~230 zl". Duzo uzytkownikow tak myśli.
- **Export CSV z preview** — agencje czesto musza pokazac kolejnosc zatwierdzen klientowi przed wykonaniem.
- **Scheduling (cron)** — "Uruchamiaj A1 co poniedzialek, jesli >10 pozycji -> powiadom". To moze zyc jako separate feature; Google Ads Scripts to ma.
- **"Why not" explanation** — dlaczego dany term sie nie zakwalifikowal (debug mode). Przydatne przy pomocy technicznej.
- **Bulk param edit** — "min_clicks=10 dla wszystkich waste scripts". Dzis per-script only.
- **Post-execution summary raport** — markdown/PDF dla klienta: "Wykonano A1: dodano 34 negatywow, szacowana oszczednosc 340 zl/mies".
- **Kolorowanie "ile oszczednosci"** — badge > 500 zl zielony, < 50 zl szary. Dzis niebieski zawsze.
- **Undo per pozycja** — usun negative ktory przed chwila dodales bez wyjscia ze skryptu.
- **Negative keyword list targeting** — Google pozwala dodac do shared negative list. Tu tylko campaign/ad group scope.

---

## Co usunac/zmienic

- **Placeholder "Sprint 1 - P0 scripts" ktory pisze "obecnie dostepny: A1"** (ads-user bug #1) — to klamstwo, zarejestrowanych jest 6 skryptow. **Usunac ten blok caly** albo zamienic na dynamiczny counter "{N} skryptow dostepnych, {M} w sprincie 2".
- **`custom_brand_words: { type: 'hidden' }`** — juz opisane, zmienic na tag input.
- **Modal `maxWidth: 760`** (ads-user #8) — przy 12 kolumnach metryk nie miesci sie. Zmienic na `maxWidth: '90vw'` albo fullscreen dla preview.
- **Tab n-gram pokazuje `(0)` dla pustych** (ads-user #9) — albo schowac, albo greyout bez placeholder (0).
- **`type: select` z boolean `value: true/false`** — React-owy antipattern bo `<option value={true}>` konwertuje na string "true". Obecnie dziala dzieki temu ze backend akceptuje str/bool, ale zepsuje sie przy pierwszym strict validation. Zmienic na toggle component.

---

## Porownanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Zero-conv waste search terms | Filtr w Search Terms Report (ale bez brand protection) | A1 z brand + keyword protection + circuit breaker + lag guard | **LEPSZE** |
| Multi-layer negative gaps (MCC + account + cross-campaign) | BRAK - GAds nie wykrywa "ten term jest excluded w kampanii X ale nie w Y" | A2 z hard/soft matches, sort po savings, per-campaign dedup | **BRAK w GAds** |
| Non-Latin script detection | Manual filtrowanie regex lub GPL script | A6 z Unicode script buckets (LATIN/CYRILLIC/CJK/...) per client whitelist | **BRAK w GAds** |
| High-conv term promotion do keywordu | Recommendations panel "Add keyword" (czesto myli ad groupy) | B1 z automatycznym match-to-ad-group + override dropdown | **LEPSZE** |
| Duplicate coverage detection | **BRAK** - GAds pokazuje "overlapping keywords" tylko per kampania, nie cross-campaign na search term level | C2 z pick-keeper UX + EXACT force | **BRAK w GAds** |
| N-gram waste analysis | BRAK - specjalisci robia to w Excel/Power Query | D1 z tabs 1/2/3/4-gram + cross-term aggregation | **BRAK w GAds** |
| Per-client saved thresholds | BRAK - kazde filtrowanie per sesja | PUT /scripts/{id}/config | **LEPSZE** |
| Dry-run first / preview | Jest w niektorych Recommendations, nie wszedzie | Consistent dla wszystkich skryptow | **LEPSZE** |
| Per-item opt-out przed execute | Jest w Recommendations bulk apply | Jest, z hard selected / soft unselected | **IDENTYCZNE** |
| Sortowanie preview kolumn | Jest w GAds tabelach | **BRAK** | **GORSZE** |
| Filtr kampanii w preview | Jest w GAds (native filtering) | **BRAK** | **GORSZE** |
| Historia operacji per skrypt | Change History z 30-day window | Globalny /action-history, brak per-script view | **GORSZE** |
| Scheduling auto-run | Google Ads Scripts (JS, dev-only) | **BRAK** | **GORSZE** |
| Widoczne metryki (CTR/CVR/CPA) per term w preview | Jest, pelna tabela | Tylko reason-string + koszt | **GORSZE** |
| Circuit breaker / daily limit | Jest jako enforced API quota | Jest jako custom `_validate_batch` per action_type | **IDENTYCZNE** |
| Estimated savings PLN/month | Rough estimate z Recommendations | Per-item i aggregate w zlotowkach | **LEPSZE** |
| Conversion lag guard | Nie wystawione userowi — GAds po prostu uwaza ze dane sa final | Jawna flaga lag_days + warning dla okien siegajacych N dni | **LEPSZE** |

**Stosunek**: 9x LEPSZE/BRAK-w-GAds, 2x IDENTYCZNE, 5x GORSZE. Bilans zdecydowanie pozytywny — braki sa UX polish (sort/filter/metryki widoczne), **fundamenty i unikalne wartosci** sa po stronie naszej apki.

---

## Beyond the playbook

Playbook ([google_ads_optimization_playbook.md](../../google_ads_optimization_playbook.md)) jest zbyt plytki na to co ten feature oferuje. Regula 5 ([linia 184-191](../../google_ads_optimization_playbook.md#L184-L191)) to 3 one-liner'y. Tu mamy:

- **Conversion lag** — playbook nie wspomina
- **Keyword conflict protection** — playbook nie wspomina
- **Multi-layer negative inheritance** — playbook nie wspomina
- **Cross-term n-gram aggregation** — playbook nie wspomina
- **Circuit breaker daily limits** — playbook nie wspomina
- **Single-best-window selection przy overlapping syncs** — playbook nie wspomina

To znaczy ze trzeba:
1. **Zaktualizowac playbook** zeby odzwierciedlal co faktycznie robimy (ADR na to przed nastepnym sprintem; bez tego decyzje pipeline'u sa niedokumentowane)
2. **Dodac do skryptow rzeczy ktore sa poza playbook ale widac z doswiadczenia**:
   - **PLA feed quality alerts** — PMax/Shopping szuka produktow z issues, nie tylko search terms. Ale to inny katalog, poza zakresem Scripts tab.
   - **Sezonowosc flag** — term konwertowal 60 dni temu, teraz milczy — zostaw z alertem, nie blokuj. E1/E2 z research (P2, TBD).
   - **Impression share velocity** — jesli IS spada tydzien do tygodnia to budget/bid limit hit, nie waste. Poza tym co robia skrypty.

---

## Rekomendacja koncowa

**ZACHOWAC + ROZBUDOWA**. To najbardziej value-driven feature w aplikacji. Zaden konkurent (ani GAds native, ani Optmyzr, ani Adzooma) nie ma tej kombinacji: date-aware + conversion lag + keyword protection + multi-layer negatives + duplicate coverage + n-gram z per-client thresholds.

**Przed production launch**:
1. **Naprawic 6 P0 bugow**: placeholder, `custom_brand_words` hidden, eager dry-run, params/execute rozjazd, modal width, tab `(0)` display (wszystko maly frontend nakladkowy).
2. **Dodac widoczne metryki w preview table** (clicks/CTR/conv/CPA z `item.metrics`) — to 1 sprint na ScriptsPage, zero backendu.
3. **Dodac filtr kampanii i sort kolumn w modal** — client-side, lightweight.
4. **Dodac D3 (N-gram Audit)** — trywialne bo D1 agregacje juz sa, zmiana action_type na ALERT.
5. **Per-script recent runs badge** — wymaga `GET /scripts/{id}/history?client_id=X` endpoint zwracajacy ostatnie 5 execute z `ActionLog` gdzie `context_json.script_id = X`.

**Po tym mozna isc do sprintu 3**: A3 Low CTR, A5 Informational intent, F1 Competitors, C1 Broad→Phrase. Z tym compleciem feature zastapi 90% codziennej roboty specjalisty w Search Terms.

**Nie trzeba**: schedulingu (to wlasny feature project), scheduled reports (PDF), "why not" explaination (debug mode), undo granularny. Te moga pojsc po MVP production.

**Dlaczego 8.25 a nie 9**: fundament 10/10, ale shell 6/10 (brak widocznych metryk, filtrow, sortu, historii) oznacza ze user dzis klika w skrypty jakby to byl SQL query builder zamiast workflow tool. Popraw te 5 rzeczy z listy P0 i nastepna ocena bedzie 9.5.
