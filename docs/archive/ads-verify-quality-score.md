# Plan implementacji — Wynik jakości (Quality Score)
> Na podstawie: docs/reviews/ads-expert-quality-score.md
> Data weryfikacji: 2026-03-26 | ads-check: 2026-03-27 — **12/15 DONE**

## Podsumowanie
- Elementów z raportu: 14
- DONE: 14 | PARTIAL: 0 | MISSING: 0 (+ #5 Trend QS odroczone — schema change) | NOT_NEEDED: 1
- ads-check: 2026-03-28 — **14/15 DONE** (1 odroczone: #5 trend QS wymaga schema change)

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| 1 | Ad Group w tabeli | PARTIAL | Backend ma join AdGroup→Campaign (analytics.py:437-444), model AdGroup.name istnieje (ad_group.py:15) | Endpoint nie zwraca ad_group_name. Frontend nie ma kolumny. | S |
| 2 | Regulowany próg QS z UI | PARTIAL | Backend przyjmuje `qs_threshold` param (analytics.py:396). Frontend wyświetla `data.qs_threshold` (QualityScore.jsx:137,248) | Frontend nie wysyła `qs_threshold` do API — brak selecta/slidera w filter bar | S |
| 3 | Eksport CSV | MISSING | Wzorzec eksportu istnieje w SearchTerms.jsx:247-249 (`handleExport` → `window.location.href`). Brak backend endpoint eksportu QS. | Potrzeba: backend endpoint `/export/quality-score` + przycisk w headerze | M |
| 4 | Filtrowanie po dacie | MISSING | FilterContext istnieje globalnie (useFilter). QS endpoint nie przyjmuje dat. Koszty z snapshot Keyword.cost_micros, nie z KeywordDaily. | Backend: dodać date_from/date_to params, agregować z KeywordDaily. Frontend: podłączyć FilterContext | L |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| 5 | Trend QS w czasie | MISSING | KeywordDaily nie ma kolumny quality_score — tylko metryki performance | Nowy model/tabela QS snapshot per dzień + endpoint + wykres liniowy | L |
| 6 | Grupowanie po ad group | MISSING | Brak | Nowy widok/toggle: flat list vs grouped by ad group z avg QS per grupa | M |
| 7 | Rekomendacje kontekstowe | DONE | _build_recommendation (analytics.py:383-409) uwzględnia CTR, cost, convs, IS lost. Generuje kontekstowe reko: SKAG, DKI, LP speed. | ✅ Już zaimplementowane po ads-verify. | M |
| 8 | Deep link do Google Ads UI | MISSING | Model Keyword ma `google_keyword_id` (keyword.py:14). Model Campaign ma `google_campaign_id`. | Zbudować URL `https://ads.google.com/aw/keywords?keywordId=XXX`, dodać ikonę linku w tabeli | S |
| 9 | Akcje z poziomu tabeli (pauza) | MISSING | System action validation/circuit breaker istnieje w app. Brak przycisku pauzy w QS tabeli. | Dodać przycisk "Pauza" per wiersz dla QS < 3, podłączyć do keyword pause endpoint | M |

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| 10 | Legenda kolumny "CTR / Ad / LP" | MISSING | 3 kropki bez opisu, tooltip wymaga hovera (QualityScore.jsx:424-426) | Dodać mini-podpisy pod kropkami lub rozbić na 3 osobne kolumny z ikonami | S |
| 11 | Label "IS utracony (rank)" | MISSING | Tekst "IS utracony (rank)" bez tooltipa (QualityScore.jsx:284) | Zmienić na "IS utracony (ranking)" + tooltip wyjaśniający | S |
| 12 | Koszt w tabeli bez waluty | MISSING | Kolumna "Koszt" wyświetla `item.cost_usd.toFixed(2)` bez "zł" (QualityScore.jsx:482) | Dodać "zł" suffix lub zmienić header na "Koszt (zł)" | S |
| 13 | Rekomendacja "OK" dla QS 7+ | MISSING | Kolumna pokazuje kursywne "OK" (QualityScore.jsx:508) | Zamienić na zieloną ikonkę CheckCircle lub pustą komórkę | S |

### NAWIGACJA

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| 14a | Dashboard → QS widget | DONE | Dashboard ma widget "QS Health" (linia 424+) z avg QS, low_qs_count, linkiem do /quality-score. | ✅ Już zaimplementowane. | M |
| 14b | Keywords → "Audyt QS" button | MISSING | Keywords.jsx ma QSBadge per keyword, ale brak linku do /quality-score | Dodać przycisk/link "Audyt QS" w headerze Keywords | S |
| 14c | Recommendations → QS link | NOT_NEEDED | Rule 8 (QS alerts) jest w recommendations.py (protected). Recommendations.jsx nie wspomina /quality-score | Nie modyfikujemy recommendations.py (protected). Frontend-only link możliwy, ale niski priorytet | — |

## Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, ~1-2h):
  [x] #1  Ad Group w tabeli ✅ DONE (already in code — ad_group shown in keyword row)
  [x] #2  Regulowany próg QS ✅ DONE (already in code — DarkSelect with 3/4/5/6/7)
  [x] #10 Legenda subkomponentów ✅ DONE (already in code — CTR/Ad/LP labels)
  [x] #11 Label IS utracony ✅ DONE (already in code — "IS utracony (ranking)" + tooltip)
  [x] #12 Waluta w tabeli ✅ DONE (already in code — header "Koszt (zł)")
  [x] #13 Rekomendacja OK → ikona ✅ DONE (already in code — CheckCircle icon)
  [x] #14b Keywords → link do QS ✅ DONE (already in code — "Audyt QS" button)

Sprint 2 (średni nakład — M, ~3-4h):
  [x] #3  Eksport CSV ✅ DONE (already in code — CSV + XLSX export buttons)
  [x] #7  Rekomendacje kontekstowe ✅ DONE (already in code — CTR/cost/convs/IS-aware)
  [x] #8  Deep link do Google Ads UI ✅ DONE (already in code — ExternalLink per row)

Sprint 3 (duży nakład — L, ~5-8h):
  [x] #4  Filtrowanie po dacie ✅ DONE (already in code — FilterContext integrated)
  [x] #6  Grupowanie po ad group ✅ DONE (already in code — groupByAg toggle + grid view)
  [x] #14a Dashboard QS widget ✅ DONE (already in code — avg QS + low_qs_count + link)

Odroczone (wymaga schema change):
  [ ] #5  Trend QS w czasie — nowy model QS snapshot + endpoint + wykres
```

## Szczegóły implementacji

### Sprint 1

#### #1 Ad Group w tabeli
- **Backend** (`backend/app/routers/analytics.py`):
  - W lookup (linia 437-444) dodać `AdGroup.name` do query: `db.query(AdGroup.id, AdGroup.name, Campaign.id, Campaign.name)`
  - Dodać `ag_name_by_ag = {ag_id: ag_name for ag_id, ag_name, cid, cname in rows}`
  - W kw_dict dodać: `"ad_group": ag_name_by_ag.get(kw.ad_group_id, "Unknown")`
- **Frontend** (`frontend/src/pages/QualityScore.jsx`):
  - W kolumnie keyword/campaign, dodać ad_group pod kampanią (fontSize: 10, kolor: rgba(255,255,255,0.25))
  - Lub: osobna kolumna "Grupa reklam" po kampanii
- **Testy**: Sprawdzić czy response zawiera pole `ad_group` w pytest

#### #2 Regulowany próg QS
- **Frontend** (`frontend/src/pages/QualityScore.jsx`):
  - Dodać state: `const [qsThreshold, setQsThreshold] = useState(5)`
  - Dodać DarkSelect do filter bar z opcjami: `[{value: '3', label: 'QS < 3'}, {value: '4', label: 'QS < 4'}, {value: '5', label: 'QS < 5'}, {value: '6', label: 'QS < 6'}, {value: '7', label: 'QS < 7'}]`
  - W `loadData` params: `if (qsThreshold !== 5) params.qs_threshold = qsThreshold`
  - Dodać `qsThreshold` do dependency array `loadData`
- **Backend**: Już gotowy — przyjmuje `qs_threshold` param

#### #10 Legenda subkomponentów
- **Frontend** (`frontend/src/pages/QualityScore.jsx`):
  - Zmienić header z `CTR / Ad / LP` na trzy mini-labele w `<th>`:
  ```jsx
  <th style={{ ...TH_STYLE, cursor: 'default', textAlign: 'center' }}>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 8, fontSize: 9 }}>
          <span>CTR</span><span>Ad</span><span>LP</span>
      </div>
  </th>
  ```

#### #11 Label IS utracony
- **Frontend** (`frontend/src/pages/QualityScore.jsx`):
  - Zmienić tytuł karty na "IS utracony (ranking)"
  - Dodać `title="Impression Share utracony z powodu niskiego rankingu reklamy (QS + bid)"` na div karty

#### #12 Waluta w tabeli
- **Frontend** (`frontend/src/pages/QualityScore.jsx` linia 482):
  - Zmienić `{item.cost_usd.toFixed(2)}` na `{item.cost_usd.toFixed(2)} zł`

#### #13 Rekomendacja OK → ikona
- **Frontend** (`frontend/src/pages/QualityScore.jsx` linia 508):
  - Zmienić `<span style={{ ... }}>OK</span>` na `<CheckCircle size={14} style={{ color: 'rgba(74,222,128,0.4)' }} />`

#### #14b Keywords → link do QS
- **Frontend** (`frontend/src/pages/Keywords.jsx`):
  - W headerze obok tytułu dodać przycisk:
  ```jsx
  <button onClick={() => navigateTo('quality-score')} style={{ fontSize: 11, ... }}>
      <Award size={12} /> Audyt QS
  </button>
  ```

### Sprint 2

#### #3 Eksport CSV
- **Backend**: Nowy endpoint w `backend/app/routers/analytics.py` (na końcu pliku):
  ```python
  @router.get("/export/quality-score")
  def export_quality_score_csv(client_id: int = Query(...), ...):
      # Reuse quality_score_audit logic, return StreamingResponse with CSV
  ```
- **Frontend**: Przycisk "Eksport CSV" w headerze (wzorzec z SearchTerms.jsx:342-347)
  ```jsx
  <button onClick={() => handleExport('csv')} ...><Download size={11} />CSV</button>
  ```

#### #7 Rekomendacje kontekstowe
- **Backend** (`backend/app/routers/analytics.py`, funkcja `_build_recommendation`):
  - Rozbudować o kontekst: uwzględnić `kw.ctr`, `kw.cost_micros`, `kw.search_rank_lost_is`
  - Np.: "CTR=14% ale Expected CTR poniżej średniej — rozważ SKAG lub DKI"
  - Dodać playbook-owe kroki per subkomponent: SKAG, DKI, LP speed < 3s

#### #8 Deep link do Google Ads UI
- **Frontend** (`frontend/src/pages/QualityScore.jsx`):
  - Dodać ikonę ExternalLink per wiersz
  - URL builder: potrzebuje `customer_id` (z klienta) + `google_keyword_id`
  - Dodać `google_keyword_id` do response endpointu
  - Format: `https://ads.google.com/aw/keywords?ocid=XXX&kwId=YYY`
