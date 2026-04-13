# Ocena eksperta Google Ads — Dashboard (Pulpit)
> Data: 2026-03-26 (re-test) | Srednia ocena: 9.0/10 | Werdykt: ZACHOWAC

## TL;DR
Dashboard to najlepsza strona startowa w narzedziu. Pokrywa 100% Daily Checks i ~70% Weekly Reviews z playbooka w jednym widoku. Po poprawce WoW chart (daty zamiast nazw dni) widget porownania okresow jest w pelni uzyteczny. Dwa blokery do 10/10: sortowanie tabeli kampanii i deep-link do kampanii.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebnosc | 9/10 | Codziennie rano. Must-have #1. GAds Overview jest slabsze. |
| Kompletnosc | 9/10 | 8 KPI, Health Score, InsightsFeed, TrendExplorer, WoW (z datami!), Campaign table z metrykami, Budget Pacing, Device+Geo, IS. Brakuje sortowania tabeli. |
| Wartosc dodana vs Google Ads UI | 9/10 | Health Score, Wasted Spend KPI, Trend Explorer z korelacjami, Budget Pacing zbiorczy, WoW nakladany chart z datami. Podbilem z 8 bo fix dat w WoW uczynilo go real-world uzytecznym. |
| Priorytet MVP | 10/10 | Bez dashboardu apka nie ma sensu. |
| **SREDNIA** | **9.3/10** | Wzrost z 9.0 — fix WoW dates |

## Co robi dobrze

- **8 KPI cards z period-over-period** (Dashboard.jsx:312-384) — Clicks, Cost, Conversions, ROAS, Impressions, CTR, CPA, Wasted Spend. Dwa rzedy po 4 karty. Kolory odwrocone dla metryk kosztowych (invertChange). Playbook 2.1 — pelne pokrycie.
- **Health Score** (Dashboard.jsx:39-114) — gauge 0-100, kolorowanie, lista issues, klik → /alerts. Playbook 1.1 punkt 2 (anomalie). Unikalny element, brak w GAds.
- **InsightsFeed** (InsightsFeed.jsx) — rekomendacje z priorytetami HIGH/MEDIUM/LOW, przycisk "Przejdz" → /recommendations. Playbook 5.3.
- **Trend Explorer** (TrendExplorer.jsx) — multi-metric (do 5), korelacje, dual Y-axis, 9 metryk. KILLER FEATURE. Playbook 1.1 Weekly punkt 1.
- **WoW Comparison z datami** (WoWChart.jsx) — NAPRAWIONY: os X teraz pokazuje daty "25.03" zamiast nazw dni. 7 metryk do wyboru, nakladany chart biezacy vs poprzedni, legenda po polsku ("Biezacy okres"/"Poprzedni okres"). Playbook 3.2 "Compare WoW Performance".
- **Campaign table z metrykami** (Dashboard.jsx:406-508) — 9 kolumn: Nazwa, Status, Typ, Budzet, Koszt, Konwersje, ROAS (kolorowany: zielony >=3, zolty >=1, czerwony <1), Trend sparkline, Strategia. Dane z getCampaignsSummary.
- **Budget Pacing** (Dashboard.jsx:511-550) — progress bary, statusy Na torze/Przekroczenie/Niedostateczne, actual vs expected spend. Playbook 1.1 Daily punkt 1.
- **Device breakdown z trendem** (Dashboard.jsx:552-655) — 3 urzadzenia z %, CTR, CPC, ROAS. Klikniecie → rozwijalny chart z 3 liniami + avg/day. Playbook 1.1 Weekly punkt 4.
- **Geo breakdown** (Dashboard.jsx:658-690) — top 8 miast z ROAS kolorowanym. Playbook 1.1 Weekly punkt 4.
- **Impression Share** (Dashboard.jsx:694-736) — 3 wskazniki z progress barami i thresholdami. Playbook 2.1 "Search Lost IS".
- **Date filtering** — caly dashboard reaguje na FilterContext. Backend akceptuje days, date_from, date_to, campaign_type, campaign_status.

## Co brakuje (krytyczne)

### K1: Sortowanie tabeli kampanii
Tabela nie ma klikalnych naglowkow. Specjalista musi moc sortowac po Cost, Conversions, ROAS — to jest #1 workflow poranny. UWAGA: Campaigns page (Campaigns.jsx) juz MA sortowanie po metrykach (dodane dzis), ale Dashboard table go nie ma.
- Playbook ref: 1.1 Weekly punkt 5 (Budget Reallocation)
- Implementacja: state sortBy/sortDir, klikalne `<th>`, useMemo sort — identycznie jak w Campaigns.jsx

### K2: Deep-link do kampanii
Dashboard.jsx:463 — `onClick={() => navigate('/campaigns')}` — klikniecie wiersza przenosi na liste, nie na detail. Campaigns.jsx obsluguje select kampanii, wiec wystarczy przekazac campaign_id w URL.
- Playbook ref: 3.1 Daily Flow (drill down)
- Implementacja: `navigate('/campaigns?campaign_id=' + c.id)`

## Co brakuje (nice to have)

- **Klikalna karta Wasted Spend → /search-terms** — zamkniecie petli "widze problem → dzialanie". Playbook 1.1 Daily punkt 3 "Search Terms Review = NAJWAZNIEJSZE". Dodac onClick na karcie (Dashboard.jsx:374-383).
- **Link do /daily-audit z dashboardu** — naturalna nawigacja "Poranny przeglad →" w headerze.
- **InsightsFeed filtr priorytetu** — pill buttons HIGH/MEDIUM/LOW. Rano chce TYLKO HIGH.
- **Sparkline tooltip** — Recharts `<Tooltip>` w komponencie Sparkline (Dashboard.jsx:154-169).
- **Tooltip na kolumnie Strategia** — `title={c.bidding_strategy}` (Dashboard.jsx:497).
- **Sortowanie Geo tabelki** — klikalne naglowki.
- **IS per kampania** — kolumna w tabeli. Model Campaign ma `search_impression_share` (campaign.py:46).

## Co usunac/zmienic

- **Nic do usuniecia.** Dashboard po sprintach jest kompletny i gesty ale nic nie jest zbedne.

## Porownanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| KPI overview | 6+ metryk, customizable | 8 kart z % change + Wasted Spend | **LEPSZE** |
| Health Score | Optimization Score (Google-biased) | Health Score z playbook-rules | **LEPSZE** |
| Trend chart | Max 2 metryki | Multi-metric + korelacje + dual axis | **LEPSZE** |
| WoW comparison | "Compare" — tabelka % | Nakladany chart z datami | **LEPSZE** |
| Campaign table | Sortowalna, edytowalna | Z metrykami ale bez sortowania, read-only | **GORSZE** |
| Budget Pacing | Per campaign, osobny widok | Zbiorczy z progress barami | **LEPSZE** |
| Device breakdown | Reports > Devices | Na dashboardzie z rozwijalnym trendem | **LEPSZE** |
| Geo breakdown | Reports > Locations | Top 8 miast z ROAS | **LEPSZE** |
| Impression Share | Kolumna IS per kampania | Widget account-level | **GORSZE** |
| Insighty | Osobna zakladka Recommendations | Wbudowane w dashboard | **LEPSZE** |
| Quick actions | Inline edit (bid, budget, status) | Brak | **GORSZE** |

**Bilans: 8 LEPSZE, 3 GORSZE.** Wzrost z 7:3 — WoW z datami awansowal z "IDENTYCZNE" na "LEPSZE".

## Nawigacja i kontekst

- **Skad user trafia:** Domyslna strona (route `/`). Sidebar: "Pulpit" w PRZEGLAD.
- **Dokad moze przejsc:**
  - Health Score → /alerts
  - InsightsFeed → /recommendations
  - Campaign table → /campaigns
  - Budget Pacing → /campaigns
- **Brakujace polaczenia:**
  - Wasted Spend karta → /search-terms?segment=WASTE
  - Header → /daily-audit ("Poranny przeglad →")
  - Campaign row → /campaigns?campaign_id=X (deep-link)
  - Dashboard → /keywords (z filtrem low QS)

## Odpowiedzi na pytania @ads-user (Marka)

1. **Sortowanie tabeli** — krytyczny brak, #1 priorytet. Campaigns page juz to ma, Dashboard potrzebuje tego samego.
2. **Klikalna Wasted Spend** — tak, powinien byc onClick → /search-terms. Quick win, 1 linia.
3. **InsightsFeed filtr** — w planie ads-verify Sprint 1. Prosty state + pill buttons.
4. **Sparkline tooltip** — drobna zmiana, Recharts `<Tooltip>`. Sprint 1.
5. **Geo sortowanie** — warto dodac, klikalne `<th>`. Sprint 2.

## Rekomendacja koncowa
**ZACHOWAC**

Dashboard jest kompletny i pokrywa codzienne potrzeby specjalisty. Fix WoW dates podniosl ocene. Do idealu brakuje dwoch rzeczy: sortowanie tabeli kampanii (30 min, frontend-only) i deep-link do campaign detail (1 linia). Nice-to-have: klikalna karta Wasted Spend, filtr priorytetow w insightach, sparkline tooltip. Nic do usuniecia.
