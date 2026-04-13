# ads-check: Quality Score (Wynik jakości)
> Data: 2026-03-27 | Plan z: 2026-03-26 | Wynik: 12/15 tasków wdrożonych

## Podsumowanie
- Tasków w planie: 15 (bez NOT_NEEDED)
- DONE: 12 | PARTIAL: 1 | STILL_MISSING: 2 | SKIPPED: 0
- Verdykt: **PRAWIE** (80% complete)

## Status tasków

### Wdrożone (DONE)

| # | Task | Dowód |
|---|------|-------|
| #1 | Ad Group w tabeli | QualityScore.jsx:538 — campaign/ad_group inline |
| #2 | Regulowany próg QS | QualityScore.jsx:334-340 — DarkSelect QS < 3..7 |
| #3 | Eksport CSV/XLSX | QualityScore.jsx:246-250 + export.py:296-350 |
| #4 | Filtrowanie po dacie | QualityScore.jsx:11,92-93 — FilterContext |
| #6 | Grupowanie po ad group | QualityScore.jsx:77,361-365 — toggle "Grupuj" |
| #8 | Deep link do Google Ads | QualityScore.jsx:605-613 — ExternalLink ads.google.com |
| #10 | Legenda CTR/Ad/LP | QualityScore.jsx:508-512 — 3 kolumny |
| #11 | Label IS utracony + tooltip | QualityScore.jsx:312-315 — tooltip z wyjaśnieniem |
| #12 | Waluta w tabeli | QualityScore.jsx:308,516 — "Koszt (zł)" |
| #13 | CheckCircle dla QS 7+ | QualityScore.jsx:597 — zielona ikona |
| #14a | Dashboard QS widget | Dashboard.jsx:426 — klikalna karta → /quality-score |
| #14b | Keywords → Audyt QS | Keywords.jsx:1022-1023 — przycisk z Award icon |

### Częściowe (PARTIAL)

| # | Task | Co jest | Co brakuje |
|---|------|---------|------------|
| #7 | Rekomendacje kontekstowe | analytics.py:383-410 — basic _build_recommendation | Głębsza logika (industry, bid strategy, A/B test) |

### Brakujące (STILL_MISSING)

| # | Task | Priorytet | Nakład |
|---|------|-----------|--------|
| #5 | Trend QS w czasie | NICE TO HAVE | L (schema change) |
| #9 | Przycisk pauzy per wiersz | NICE TO HAVE | M |

## Następne kroki
Wdrożono 12 z 15 tasków (80%). Brakujące:
- #5 trend QS — wymaga nowego modelu/tabeli, odłożone na v1.1+
- #9 przycisk pauzy — średni nakład, warte zrobienia
- #7 smartniejsze rekomendacje — stopniowa poprawa
