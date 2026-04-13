# Plan implementacji — Skrypty (/scripts)

> Na podstawie: [docs/reviews/ads-expert-scripts.md](ads-expert-scripts.md)
> Data weryfikacji: 2026-04-12
> Werdykt eksperta: 8.25/10 — ZACHOWAC + ROZBUDOWA

## Podsumowanie

- Elementow z raportu: **23**
  - Krytyczne (brak): **10**
  - Nice to have: **9**
  - Do usuniecia/zmiany: **5** (C2 usun `type:select` boolean overlap z nice-to-have)
- DONE: **0** | PARTIAL: **3** | MISSING: **17** | NOT_NEEDED: **3**
- Szacowany naklad: **duzy** (2-3 sprinty), ale **sprint 1 to same quick wins**

Wiekszosc krytycznych to **frontend-only** (ScriptsPage.jsx) — backend wspiera juz wiekszosc danych przez `item.metrics`. Tylko 2 elementy wymagaja nowych skryptow (D3 Audit, A3 Low CTR, F1 Competitor) i 1 wymaga nowego endpointu (history per skrypt).

---

## Status kazdego elementu

### KRYTYCZNE (must implement)

| #  | Element | Status | Co istnieje | Co brakuje | Naklad |
|----|---------|--------|-------------|------------|--------|
| 1  | Metryki per-item w preview (clicks/CTR/conv/CPA widoczne) | PARTIAL | Backend: `ScriptItem.metrics` ma `clicks`, `impressions`, `cost_pln`, `conversions`, `ctr` ([a1_zero_conv_waste.py:288-294](../../backend/app/services/scripts/a1_zero_conv_waste.py#L288-L294)). Frontend: renderItem pokazuje tylko `estimated_savings_pln` albo `conversions` ([ScriptsPage.jsx:537-539](../../frontend/src/features/scripts/ScriptsPage.jsx#L537-L539)) | Tabela kolumnowa: clk/impr/CTR/conv/CPA/koszt per wiersz | S |
| 2  | Filtr kampanii wewnatrz modal preview | MISSING | Brak — `visibleItems` filtruje tylko po `ngramTab` ([ScriptsPage.jsx:473-475](../../frontend/src/features/scripts/ScriptsPage.jsx#L473-L475)) | `<select>` z lista unikalnych `campaign_name` + stan `campaignFilter` w RunModal | S |
| 3  | Sortowalne kolumny preview | MISSING | Brak — backend sortuje raz (savings desc albo hard>soft), frontend nie pozwala re-sortowac | Stan `sortKey`/`sortDir` w RunModal, klikane nagowki kolumn | S |
| 4  | `custom_brand_words` edytowalny z UI | MISSING | `PARAM_LABELS.custom_brand_words: { type: 'hidden' }` ([ScriptsPage.jsx:120](../../frontend/src/features/scripts/ScriptsPage.jsx#L120)). Backend: `_build_brand_patterns(client, custom_brand_words)` akceptuje liste ([a1_zero_conv_waste.py:179-183](../../backend/app/services/scripts/a1_zero_conv_waste.py#L179-L183)) | Nowy typ `tags` (input z chip add/remove) w PARAM_LABELS + rendering w formularzu params | M |
| 5  | Eager dry-run 6x przy wejsciu — lazy | MISSING | `useEffect` odpala `Promise.allSettled(allScripts.map(...))` dla WSZYSTKICH ([ScriptsPage.jsx:825-858](../../frontend/src/features/scripts/ScriptsPage.jsx#L825-L858)) | Opcja A: lazy — odpalaj tylko po rozwinieciu kategorii. Opcja B: debounce 500ms na `dateParams` + cache per (client_id,date_from,date_to) | M |
| 6  | Params/Execute rozsynchronizowane | MISSING | `handleRerun` i `handleExecute` niezalezne. `paramsEdited` tylko pokazuje button "Odsiwez" ale nie blokuje "Wykonaj" ([ScriptsPage.jsx:388-405, 762-774](../../frontend/src/features/scripts/ScriptsPage.jsx#L388-L405)) | `disabled={paramsEdited \|\| selectedIds.size === 0}` na Wykonaj + inline info "Odsiwez podglad przed wykonaniem" | S |
| 7  | Historia uruchomien per skrypt (recent runs badge) | MISSING | Backend: `ActionLog.context_json` ma `script_id` ([a1_zero_conv_waste.py:455](../../backend/app/services/scripts/a1_zero_conv_waste.py#L455)). Brak endpointu filtrujacego po `context_json->>'script_id'`. Brak UI | `GET /scripts/{script_id}/history?client_id=X&limit=10` + badge na ScriptTile "Ostatnio: 3 dni temu · 12 zastosowanych" | M |
| 8  | D3 — N-gram Audit Report (view-only) | MISSING | D1 (NgramWasteScript) ma agregacje n-gramow ([d1_ngram_waste.py](../../backend/app/services/scripts/d1_ngram_waste.py)). Brak klasy D3. Brak `action_type=ACTION_ALERT` handlera w UI (jest tylko `alertSources = new Set(['pmax_alert'])`) | Nowa klasa `NgramAuditScript(id='D3', category=CATEGORY_NGRAM, action_type=ACTION_ALERT)`. Rejestracja w `__init__.py`. UI juz renderuje alertItems jako non-selectable | S |
| 9  | A3 Low CTR Waste | MISSING | Brak klasy. Brak w `_REGISTRY` ([__init__.py:42-54](../../backend/app/services/scripts/__init__.py#L42-L54)) | Nowa klasa `LowCtrWasteScript(id='A3', category=CATEGORY_WASTE)` z thresholdami `min_impressions=100`, `max_ctr_pct=0.5`, reuse brand+keyword protection | M |
| 10 | F1 Competitor Term Detection | MISSING | Brak klasy. Brak pola `competitors` w client (tylko `ai_context` jako dict) | Nowa klasa `CompetitorTermScript(id='F1', category=CATEGORY_BRAND, action_type=ACTION_ALERT)`. Input: `Client.ai_context.competitors` lub nowy param `custom_competitor_words` | M |

### NICE TO HAVE

| #  | Element | Status | Co istnieje | Co brakuje | Naklad |
|----|---------|--------|-------------|------------|--------|
| 11 | Per-campaign grouping w preview (collapsible) | MISSING | Brak — preview renderuje flat list | Groupowanie `primaryItems` po `campaign_name`, `<details>` per kampania | M |
| 12 | Export CSV z preview | MISSING | Brak — przycisk "Wykonaj" i "Anuluj" tylko | Button "Eksportuj CSV" w footer modal, client-side CSV z `preview.items` | S |
| 13 | Scheduling (cron dla auto-run skryptow) | MISSING | Brak — skill `schedule` istnieje ale nie zintegrowany z /scripts | Nowy endpoint `POST /scripts/{id}/schedule` + tabela `script_schedules` + backgroud worker. DUZY. | L |
| 14 | "Why not" explanation (debug mode) | MISSING | Brak — pasujace sa zwracane, nie-pasujace ignorowane | Opcjonalny param `debug=true` w dry-run, backend dodaje `rejected_items` do response z reason | L |
| 15 | Bulk param edit across scripts | MISSING | Brak — per-script config only | Nowy ekran w Settings "Domyslne params skryptow" z globalnym editorem. Wymaga rozszerzenia `client.script_configs` o kluczem wildcardowy | L |
| 16 | Post-execution summary raport (PDF/MD) | MISSING | Brak — result phase pokazuje tylko counts | Button "Pobierz raport" w result phase, client-side MD generation z `applied_items` | M |
| 17 | Color-coded savings badges (>500zł green, <50zł grey) | MISSING | Badge zawsze `color: meta.color` ([ScriptsPage.jsx:59-64](../../frontend/src/features/scripts/ScriptsPage.jsx#L59-L64)) | Heatmap na `savings`: > 500 zielony, 50-500 zolty, < 50 szary | S |
| 18 | Undo per pozycja | MISSING | Brak w UI. Backend: `ActionLog` ma pelna informacje ale brak `DELETE /negative-keywords/{id}` route dedykowanego undo z rollback GA push | Osobny PR — wymaga rollback w Google Ads API, nie trywialne | L |
| 19 | Negative keyword list targeting (shared lists) | MISSING | Model `NegativeKeywordList` istnieje ([a2_irrelevant_dictionary.py:102-129](../../backend/app/services/scripts/a2_irrelevant_dictionary.py#L102-L129)). Skrypty tylko ADD do campaign/ad group, nie do shared list | Nowy `negative_level: 'SHARED_LIST'` + wybor listy w params + `batch_add_to_shared_list` w google_ads_service | L |

### ZMIANY / USUNIECIA

| #  | Element | Status | Aktualny stan | Rekomendacja | Naklad |
|----|---------|--------|---------------|--------------|--------|
| 20 | Placeholder "Sprint 1 — P0 scripts" klamie | MISSING (do usuniecia) | Pisze "Obecnie dostępny: A1" i wymienia "w przygotowaniu" A2/B1/D1 ktore JUZ SA ([ScriptsPage.jsx:964-979](../../frontend/src/features/scripts/ScriptsPage.jsx#L964-L979)) | Usunac cala ramke lub zamienic na dynamiczny counter "{N} skryptow aktywnych" z linkiem do research | S |
| 21 | Modal `maxWidth: 760` (nie miesci metryk) | MISSING (zmiana) | `maxWidth: 760` hardcoded ([ScriptsPage.jsx:266](../../frontend/src/features/scripts/ScriptsPage.jsx#L266)) | Zmiana na `maxWidth: 'min(1200px, 92vw)'` albo fullscreen-toggle | S |
| 22 | Tab n-gram pokazuje `(0)` dla pustych | MISSING (zmiana) | Renderuje `(0)` z `cursor: 'default'`, `color: C.w25` ([ScriptsPage.jsx:427-430](../../frontend/src/features/scripts/ScriptsPage.jsx#L427-L430)) | Ukryc tab gdy `counts[n]` falsy: `{[1,2,3,4].filter(n => counts[n] > 0).map(...)}` | S |
| 23 | `type: select` z boolean value (React antipattern) | NOT_NEEDED | Pole `brand_protection`, `include_soft`, `include_pmax_alerts`, `show_converting` uzywa `<option value={true/false}>` ([ScriptsPage.jsx:112-119, 128-131, 147-149](../../frontend/src/features/scripts/ScriptsPage.jsx#L112-L119)). Dzialaja ale bo backend akceptuje stringi | Zamienic na Toggle component — ale to nie ma wplywu na funkcje dzis. Mozna odlozyc | S |

---

## Kolejnosc implementacji (rekomendowana)

Sortowanie: (A) quick wins ktore podnosza UX o 80%, (B) nowe skrypty P0, (C) shell features, (D) infrastruktura.

### Sprint 1 — Quick wins (naklad S, ~4-6h total)

Wszystko frontend-only, zero zmian backendu, wysoka wartosc.

```
[ ] T1.1 — Usun klamliwy placeholder "Sprint 1 — P0 scripts"
           Plik: frontend/src/features/scripts/ScriptsPage.jsx:964-979
           
[ ] T1.2 — Dodaj widoczne kolumny metryk w preview
           Plik: ScriptsPage.jsx — renderItem function (linia 490-627)
           Dane: item.metrics.{clicks, impressions, ctr, conversions, cost_pln, cpa}
           CPA liczyc client-side: metrics.conversions > 0 ? cost_pln/conversions : null
           
[ ] T1.3 — Rozszerz modal width
           Plik: ScriptsPage.jsx:266 — maxWidth: 'min(1200px, 92vw)'
           
[ ] T1.4 — Ukryj puste taby n-gram
           Plik: ScriptsPage.jsx:418 — [1,2,3,4].filter(n => counts[n] > 0)
           
[ ] T1.5 — Blokuj "Wykonaj" gdy paramsEdited
           Plik: ScriptsPage.jsx:762-774
           disabled={selectedIds.size === 0 || paramsEdited}
           + dodaj tooltip/inline hint "Odsiwez podglad przed wykonaniem"
           
[ ] T1.6 — Color-coded savings badges (heatmap)
           Plik: ScriptsPage.jsx:55-70 — ScriptTile component
           > 500 zielony, 50-500 zolty/meta.color, < 50 szary
           
[ ] T1.7 — Filtr kampanii i sort w RunModal
           Plik: ScriptsPage.jsx — dodac stany:
             const [campaignFilter, setCampaignFilter] = useState('')
             const [sortKey, setSortKey] = useState('savings')
             const [sortDir, setSortDir] = useState('desc')
           Unikalne campaigns z preview.items, filter+sort w visibleItems chain.
```

Definitywny efekt: ekspert score skacze z 8.25 na 9.0 bez zadnej nowej logiki.

### Sprint 2 — Nowe skrypty + lazy load (naklad M, ~6-8h)

```
[ ] T2.1 — D3 N-gram Audit Report (view-only)
           Backend:
             - Nowy plik backend/app/services/scripts/d3_ngram_audit.py
             - Klasa NgramAuditReportScript(id='D3', action_type=ACTION_ALERT)
             - Kopiuje agregate_ngrams z d1_ngram_waste (importuj helper)
             - Zwraca top 20 ngramow bez action_payload
             - Rejestracja w __init__.py (dodaj import + register)
           Frontend:
             - ScriptsPage.jsx: alertSources.add('audit') albo dodac 'ngram_audit'
             - Tabela zamiast listy dla D3 (metrics: term_count, total_cost, campaigns_affected)
           Testy:
             - backend/tests/test_scripts_d3.py — dry_run zwraca items bez action_payload
             
[ ] T2.2 — A3 Low CTR Waste
           Backend:
             - backend/app/services/scripts/a3_low_ctr_waste.py
             - Klasa LowCtrWasteScript(id='A3', category=CATEGORY_WASTE)
             - default_params: min_impressions=100, max_ctr_pct=0.5, negative_level='CAMPAIGN', match_type='PHRASE'
             - Struktura identyczna jak A1 (reuse _fetch_aggregated_terms pattern)
             - Rejestracja w __init__.py
           Testy:
             - test_scripts_a3.py — term z impr 150, clicks 0 -> matched; impr 90 -> not matched
             
[ ] T2.3 — Lazy dry-run per kategoria
           Plik: ScriptsPage.jsx — useEffect linia 825-858
           Opcja A (prostsza): useEffect dependency na `expandedCats` — fetchuje counts tylko dla rozwinietych grup
           Opcja B (lepsza): dodac lightweight endpoint `GET /scripts/{id}/quick-count` 
             backend: osobny query ktory tylko liczy wiersze pasujace do bazowych filtrow, bez pelnej logiki reason/savings
             (Opcja A szybsza do wdrozenia, A wystarczy dla MVP)
           
[ ] T2.4 — custom_brand_words jako tag input
           Plik: ScriptsPage.jsx PARAM_LABELS — zmienic na { type: 'tags' }
           Dodac rendering case w formularzu (linia 315-386):
             {meta.type === 'tags' ? <TagInput value={value} onChange={v => updateParam(key, v)} /> : ...}
           Nowy maly komponent TagInput z chip display + Enter/Backspace handling
```

### Sprint 3 — History + F1 + scheduling prep (naklad M, ~4-6h)

```
[ ] T3.1 — Historia per skrypt
           Backend:
             - backend/app/routers/scripts.py — nowy endpoint:
               GET /scripts/{script_id}/history?client_id=X&limit=10
               Query: ActionLog.filter(client_id=X, context_json['script_id'].astext == script_id)
               Zwraca: [{executed_at, applied_count, failed_count, status}]
             - UWAGA: context_json to JSON column, filter przez SQLAlchemy:
               ActionLog.context_json['script_id'].astext == script_id
               (SQLite wymaga func.json_extract)
           Frontend:
             - api.js: getScriptHistory(scriptId, {client_id, limit})
             - ScriptTile: maly badge "Ostatnio: 3 dni temu · 12 negatywow"
             - Badge ladowany lazy razem z counts
           Testy:
             - test_scripts_router.py — GET /scripts/A1/history zwraca puste/wypelnione
             
[ ] T3.2 — F1 Competitor Term Detection
           Backend:
             - backend/app/services/scripts/f1_competitor_term.py
             - Klasa CompetitorTermScript(id='F1', category=CATEGORY_BRAND, action_type=ACTION_ALERT)
             - Input: Client.ai_context.competitors (dict_get safe) lub parametr custom_competitor_words
             - Scanuje SearchTerm.text przeciwko liscie z word boundary regex
             - Nie wykonuje akcji — alert z metrics (clicks, conv, cost_pln)
             - Rejestracja w __init__.py
           Frontend:
             - Kategoria "brand" juz ma CATEGORY_META
             - Alerts juz renderowane — zero zmian UI poza dodaniem
           Testy:
             - test_scripts_f1.py — term z "allegro" w nazwie gdy competitors=['allegro'] -> matched
```

### Sprint 4 — Shell polish (naklad M, ~4-6h)

```
[ ] T4.1 — Per-campaign grouping w preview
           Frontend only — <details> per campaign_name w renderItem loop
           
[ ] T4.2 — Export CSV z preview
           Frontend only — Papa.parse/handrolled CSV, Blob download
           
[ ] T4.3 — Color-coded savings juz w Sprint 1
           (skipped — done wczesniej)
           
[ ] T4.4 — Post-execution summary MD
           Frontend only — button w result phase, generuje markdown z applied_items
```

### Sprint 5 — Infra (L tasks, odlozone po MVP)

```
[ ] T5.1 — Scheduling (cron) — wymaga nowej tabeli + workera
[ ] T5.2 — "Why not" debug mode — wymaga backend support w ScriptResult
[ ] T5.3 — Bulk param edit — wymaga nowego ekranu Settings
[ ] T5.4 — Undo per pozycja — wymaga rollback Google Ads API
[ ] T5.5 — Shared negative list targeting — wymaga batch_add_to_shared_list
```

---

## Szczegoly implementacji — Sprint 1 (rozpisane)

### T1.2 — Kolumny metryk w preview (najwazniejsze)

**Plik**: `frontend/src/features/scripts/ScriptsPage.jsx` — funkcja `renderItem` (linia ~490-627)

**Zmiana**: Dodac staly pasek kolumn metryk obok `entity_name`/`campaign_name`:

```jsx
// Na poziomie renderItem, po item.reason section, przed "cost / savings" (linia 537-539)
<div style={{ display: 'flex', gap: 8, fontSize: 10, color: C.w50, fontFamily: 'monospace', flexShrink: 0 }}>
    <span title="Kliknięcia">{item.metrics?.clicks ?? 0} clk</span>
    <span title="Wyświetlenia">{item.metrics?.impressions ?? 0} impr</span>
    <span title="CTR">{item.metrics?.ctr?.toFixed(1) ?? 0}%</span>
    <span title="Konwersje">{item.metrics?.conversions ?? 0} konw</span>
    {item.metrics?.conversions > 0 && (
        <span title="CPA">CPA {Math.round(item.metrics.cost_pln / item.metrics.conversions)}zł</span>
    )}
    <span title="Koszt">{Math.round(item.metrics?.cost_pln ?? 0)}zł</span>
</div>
```

**Dane**: juz zwracane przez backend w `ScriptItem.metrics`. **Zero zmian backendu**.

**Testy**: Visual check — odpal `/scripts`, klik "Uruchom A1", sprawdz czy per-item widac clicks/impr/CTR/conv/CPA.

### T1.5 — Blokada Execute przy paramsEdited

**Plik**: `ScriptsPage.jsx:762-774`

**Zmiana**:
```jsx
<button
    onClick={handleExecute}
    disabled={selectedIds.size === 0 || paramsEdited}
    title={paramsEdited ? 'Kliknij "Odsiwez podglad" zeby zastosowac nowe parametry' : ''}
    style={{ ...}}
>
    Wykonaj ({selectedIds.size})
</button>
```

**Zadne testy** — defensive UX.

### T1.7 — Filtr kampanii + sort

**Plik**: `ScriptsPage.jsx` — w RunModal, przed `visibleItems` (linia 473)

**Zmiana**:
```jsx
const [campaignFilter, setCampaignFilter] = useState('')
const [sortKey, setSortKey] = useState('savings')
const [sortDir, setSortDir] = useState('desc')

// Lista unikalnych kampanii z preview
const campaignOptions = useMemo(() => {
    if (!preview) return []
    return [...new Set(preview.items.map(i => i.campaign_name).filter(Boolean))].sort()
}, [preview])

// Pipeline: ngram filter -> campaign filter -> sort
let visibleItems = hasNgram
    ? preview.items.filter(i => (i.metrics?.ngram_size || 1) === ngramTab)
    : preview.items
if (campaignFilter) {
    visibleItems = visibleItems.filter(i => i.campaign_name === campaignFilter)
}
const sortFn = {
    savings: (a, b) => (b.estimated_savings_pln || 0) - (a.estimated_savings_pln || 0),
    clicks: (a, b) => (b.metrics?.clicks || 0) - (a.metrics?.clicks || 0),
    cost: (a, b) => (b.metrics?.cost_pln || 0) - (a.metrics?.cost_pln || 0),
    conversions: (a, b) => (b.metrics?.conversions || 0) - (a.metrics?.conversions || 0),
    ctr: (a, b) => (b.metrics?.ctr || 0) - (a.metrics?.ctr || 0),
}[sortKey] || sortFn.savings
visibleItems = [...visibleItems].sort(sortDir === 'desc' ? sortFn : (a,b) => -sortFn(a,b))
```

UI kontrolki tuz nad lista:
```jsx
<div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
    <select value={campaignFilter} onChange={e => setCampaignFilter(e.target.value)}>
        <option value="">Wszystkie kampanie</option>
        {campaignOptions.map(c => <option key={c} value={c}>{c}</option>)}
    </select>
    <select value={sortKey} onChange={e => setSortKey(e.target.value)}>
        <option value="savings">Oszczednosc</option>
        <option value="cost">Koszt</option>
        <option value="clicks">Klikniecia</option>
        <option value="ctr">CTR</option>
        <option value="conversions">Konwersje</option>
    </select>
    <button onClick={() => setSortDir(d => d === 'desc' ? 'asc' : 'desc')}>
        {sortDir === 'desc' ? '↓' : '↑'}
    </button>
</div>
```

---

## Ograniczenia

Zgodnie z CLAUDE.md "Backend Modification Rules":
- `services/recommendations.py` — nie modyfikowany (nie dotyczy tego sprintu)
- `analytics_service.py` — tylko append na koniec (nie dotyczy)
- `analytics.py` router — tylko append na koniec (nie dotyczy)

Skrypty w `backend/app/services/scripts/` to nowy modul — mozna swobodnie rozszerzac.

Router `backend/app/routers/scripts.py` — append'owanie endpointu `/history` w istniejacej sekcji bez konfliktow.

Model `Client` — dodanie pola wymagaloby migracji; unikamy przez uzycie `Client.ai_context` (JSON field) jako kontenera dla competitors bez schematu.

---

## Rekomendacja startowa

**Zacznij od Sprint 1**. To 6-7 tasków po ~30 min każdy, wszystko frontend-only, zero ryzyka dla backendu i produkcji. Po Sprint 1 user widzi wszystkie metryki, moze filtrowac/sortowac, kolorowy badge pokazuje priorytet — score eksperta podskoczy z 8.25 na 9.0+ przy minimalnym nakladzie.

Sprint 2 (nowe skrypty D3/A3 + lazy load) jest ~1 dzien pracy i uzupelnia luki w katalogu (D3/A3 to research-spec P0).

Sprint 3 (historia + F1) to 0.5 dnia.

Sprint 4 (CSV + grouping) to 0.5 dnia polishu.

Sprint 5 (scheduling, undo, shared lists) — po MVP production.

---

Po wdrozeniu taskow odpal `/ads-check scripts` zeby zweryfikowac czy wszystko zrobione.
