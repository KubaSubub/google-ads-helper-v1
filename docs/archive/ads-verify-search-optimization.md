# Plan implementacji — Optymalizacja (Search Optimization)
> Na podstawie: docs/reviews/ads-expert-search-optimization.md
> Data weryfikacji: 2026-03-28

## Podsumowanie
- Elementów z raportu: **13**
- DONE: **0** | PARTIAL: **2** | MISSING: **11** | NOT_NEEDED: **0**
- Szacowany nakład: **duży** (3 sprinty)

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| K1 | Write actions w tabelach | MISSING | Tylko "Wyklucz" w Wasted Spend (SearchOptimization.jsx:123) | Pause/bid/exclude buttons w sekcjach: N-gram, Placements, Bid Modifiers, Shopping | L |
| K2 | Filtr kampanii | MISSING | Brak dropdownu kampanii. Dane nie są filtrowane po campaign_id | Globalny dropdown kampanii na górze strony + campaign_id param we wszystkich API calls | M |
| K3 | Grupowanie sekcji | MISSING | 33 sekcji renderowanych liniowo bez kategorii | Tab bar lub nav boczny: "Search", "PMax", "Display/Video", "Bidding", "Konwersje" | M |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| N1 | Porównanie okresów | MISSING | Brak logiki delta/previous period | Dodać period comparison z delta % do KPI sekcji | L |
| N2 | Export PDF | MISSING | Brak eksportu | Nowy endpoint + przycisk "Eksport raportu" | M |
| N3 | Top 3 priorities banner | MISSING | Brak banneru priorytetów | Banner na górze z top 3 rekomendacji z najwyższym impact | M |
| N4 | Lazy loading per sekcja | MISSING | 34 API calls w Promise.all() na wejście | Ładować dane sekcji dopiero po otwarciu akordeonu | M |
| N5 | Tooltips na Auction Insights | PARTIAL | Nagłówki kolumn bez title attr | Dodać title attr z wyjaśnieniami metryk | S |

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Nazwa strony | PARTIAL | "Optymalizacja SEARCH" | Zmienić na "Optymalizacja" | S |
| Z2 | Google Recs bez akcji | MISSING | Tabela Type/Campaign/Status bez przycisków | Dodać Apply/Dismiss lub oznaczyć jako "preview" | M |
| Z3 | Duplicate ikony | FOUND | Crosshair × 2, Box × 2 | Zmienić ikony: Auction→Eye, Shopping→ShoppingCart | S |

### NAWIGACJA

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| NAV1 | Keyword → /keywords | MISSING | Keywords jako plain text | Link/navigate do /keywords?search=X | S |
| NAV2 | Campaign → /campaigns | MISSING | Campaign names jako plain text | Link do /campaigns z filtrem | S |

## Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, ~1-2h):
  [ ] Z1 — Zmienić "Optymalizacja SEARCH" → "Optymalizacja"
  [ ] Z3 — Fix duplicate ikony (Crosshair → Eye dla Auction, Box → ShoppingCart dla Shopping)
  [ ] N5 — Tooltips na nagłówkach Auction Insights
  [ ] NAV1 — Keyword click → /keywords?search=X
  [ ] NAV2 — Campaign click → /campaigns

Sprint 2 (średni nakład — M, ~4-6h):
  [ ] K2 — Filtr kampanii (globalny dropdown + API params)
  [ ] K3 — Grupowanie sekcji (tab bar z kategoriami)
  [ ] Z2 — Google Recommendations Apply/Dismiss

Sprint 3 (duży nakład — L, ~8-12h):
  [ ] K1 — Write actions w tabelach (pause, bid change, exclude buttons)
  [ ] N4 — Lazy loading (ładuj dane sekcji on-expand)
  [ ] N3 — Top 3 priorities banner
  [ ] N1 — Porównanie okresów (delta %)
  [ ] N2 — Export PDF raportu
```

## Szczegóły implementacji

### Sprint 1

#### Z1 — Zmienić nazwę strony
- **Plik:** `frontend/src/pages/SearchOptimization.jsx` linia ~1496
- **Zmiana:** "Optymalizacja SEARCH" → "Optymalizacja"

#### Z3 — Fix duplicate ikony
- **Plik:** `frontend/src/pages/SearchOptimization.jsx`
- **Zmiana:** Import `Eye, ShoppingCart` z lucide-react
  - Auction Insights: `Crosshair` → `Eye`
  - Shopping Product Groups: `Box` → `ShoppingCart`

#### N5 — Tooltips Auction Insights
- **Plik:** `frontend/src/pages/SearchOptimization.jsx` linia ~1737-1744
- **Zmiana:** Dodać `title` attr na `<th>`:
  - "IS %" → title="Impression Share — jak często Twoja reklama się wyświetlała"
  - "Overlap %" → title="Overlap Rate — jak często konkurent wyświetlał się razem z Tobą"
  - "Pozycja wyżej %" → title="Position Above Rate — jak często konkurent był wyżej od Ciebie"
  - "Outranking %" → title="Outranking Share — jak często byłeś wyżej lub wyświetlałeś się gdy konkurent nie"
  - "Top strony %" → title="Top of Page Rate — jak często reklama była na górze strony"
  - "Abs. top %" → title="Absolute Top — jak często reklama była na pozycji #1"

#### NAV1 — Keyword click → /keywords
- **Plik:** `frontend/src/pages/SearchOptimization.jsx`
- **Zmiana:** W sekcji Wasted Spend, zamienić `<span>{item.text}</span>` na `<Link to={'/keywords?search=' + encodeURIComponent(item.text)}>{item.text}</Link>`
- **Import:** Dodać `import { Link } from 'react-router-dom'`

#### NAV2 — Campaign click → /campaigns
- **Plik:** `frontend/src/pages/SearchOptimization.jsx`
- **Zmiana:** Campaign names w tabelach zamienić na `<Link to="/campaigns">{campaign_name}</Link>`

### Sprint 2

#### K2 — Filtr kampanii
- **Frontend:** Dodać `campaignFilter` state + DarkSelect dropdown na górze strony
- **API:** Przekazywać `campaign_id` param do loadAll → każdy API call
- **Backend:** Większość endpoints już przyjmuje `campaign_id` — zweryfikować i dodać brakujące

#### K3 — Grupowanie sekcji
- **Frontend:** Tab bar z kategoriami: Search (waste, daypart, match, ngram, rsa, landing, structure), PMax (channels, assets, themes, cannibalization), Display/Video (placements, topics), Bidding (bidding advisor, smart bidding, target vs actual, modifiers, portfolio), Konwersje (conv health, conv quality), Konkurencja (auction insights, demographics)
- **Zmiana:** Filtrować `sections` po wybranej kategorii

#### Z2 — Google Recommendations Apply/Dismiss
- **Backend:** Endpoint POST /analytics/google-recommendations/{id}/apply + dismiss (via Google Ads API recommendation service)
- **Frontend:** Przyciski "Zastosuj" / "Odrzuć" per wiersz w tabeli

### Sprint 3

#### K1 — Write actions w tabelach
- **Sekcje:** N-gram (→ add negative), Placements (→ exclude), Bid Modifiers (→ edit modifier), Shopping (→ change bid)
- **Backend:** Istniejące endpoints: negative keyword, placement exclusion. Brakujące: bid modifier write, product group bid write
- **Frontend:** Przyciski inline per wiersz tabeli

#### N4 — Lazy loading
- **Zmiana:** Przenieść API calls z Promise.all do useEffect per sekcja (trigger gdy `sections.X === true`)
- **Cache:** Nie ładuj ponownie jeśli dane już załadowane (flag per sekcja)

Po wdrożeniu tasków odpal `/ads-check search-optimization` żeby zweryfikować czy wszystko zrobione.
