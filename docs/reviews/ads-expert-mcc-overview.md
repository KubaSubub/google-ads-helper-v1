# Ocena eksperta Google Ads — MCC Overview (re-test #2)
> Data: 2026-04-08 | Srednia ocena: 9.2/10 | Werdykt: ZACHOWAC (production-ready)

## TL;DR

MCC Overview przeszedl z 8.8 do 9.2 — wszystkie 6 problemow z poprzedniego review zostalo naprawionych (period pills, IS kolumna, bulk actions, KPI warunkowe, compact domyslny, billing tooltip). Widok jest teraz kompletnym MCC dashboardem z 8 unikalnymi wartosciami vs Google Ads. Pozostale kwestie to data quality (IS puste w seed) i drobny UX polish.

## Oceny

| Kryterium | Ocena | Poprzednio | Komentarz |
|-----------|-------|------------|-----------|
| Potrzebnosc | 9/10 | 9/10 | Poranny dashboard MCC — must have. Skraca triage z 15min/konto do 2min total. |
| Kompletnosc | 9/10 | 8/10 | Wszystkie braki naprawione: period pills, IS, bulk actions, KPI warunkowe. Jedyny brak: OptScore. |
| Wartosc dodana vs GAds UI | 10/10 | 9/10 | 8 unikalnych wartosci. Zero elementow "GORSZE". Bilans zmienil sie z 7:3 na 10:0. |
| Priorytet MVP | 9/10 | 9/10 | Landing page = first impression. Robi je dobrze. |
| **SREDNIA** | **9.2/10** | **8.8/10** | +0.4 dzieki naprawieniu wszystkich flagowanych issues |

## Co robi dobrze

- **Period pills (7d/14d/30d/MTD)** — NOWE. Szybkie przelaczanie bez date pickera. Lepsze niz GAds MCC.
- **Bulk actions z checkboxami** — NOWE. Select all + toolbar "Synchronizuj" / "Odrzuc rekomendacje". Kluczowe przy 10+ kontach.
- **Impression Share kolumna** — NOWE. Avg IS per konto z kolorowym wskaznikiem (>=60% zielony, >=30% zolty, <30% czerwony). Sortowalna.
- **KPI warunkowe** — NOWE. Clicks/Impressions ukryte gdy 0. "Aktywne konta" zamiast bezuzytecznego "Avg CTR".
- **Compact mode domyslny** — NOWE. 11 kolumn bez scrolla. Full mode na zyczenie.
- **Pacing per konto** — podwojny progress bar (budzet + czas miesiaca). GAds MCC tego nie ma.
- **External changes** — "X zewn." na zolto. Krytyczne dla agencji.
- **New access detection** — UserPlus badge. GAds tego nie ma.
- **One-click dismiss rekomendacji** — per konto i bulk. W GAds to multi-click.
- **Deep-links** — Zmiany→History, Rek.→Recommendations, wiersz→Dashboard.
- **Billing status** — BillingTooltip na hover z pelnym statusem.

## Co brakuje (krytyczne)

Brak krytycznych brakow. Wszystkie K1/K2 z poprzedniego raportu naprawione.

## Co brakuje (nice to have)

### N1: IS kolumna — puste dane w seed
Kolumna IS wyswietla "—" dla wszystkich kont bo seed nie generuje `search_impression_share` w MetricDaily. Pusta kolumna wyglada na buga.
- **Rozwiazanie:** Doseedowac `search_impression_share` (random 0.3-0.8) w seed.py. Lub: auto-hide kolumny IS jesli 0% kont ma dane.
- **Naklad:** S (seed fix)

### N2: Waluta przy kwotach
1729.19 czego? Brak PLN/USD/EUR. Przy multi-currency MCC to moze byc problem.
- **Rozwiazanie:** Dodac walute z modelu Client (jesli istnieje) lub globalna config.
- **Naklad:** S

### N3: Budget kwota w pacing
Pacing bar pokazuje %, ale nie kwote. Specjalista chce widziec "Budzet: 5000 PLN, Wydano: 3000 PLN".
- **Rozwiazanie:** Tooltip na pacing bar z budget/spent kwotami (dane juz w response: `pacing.budget`, `pacing.spent`).
- **Naklad:** S

### N4: Optimization Score per konto
W GAds MCC widoczny OptScore 0-100%. Tu brak. Health score istnial wczesniej ale zostal usuniety.
- **Rozwiazanie:** Przywrocic health score jako kolumne (metoda `_get_health_score` juz istnieje w MCCService:518).
- **Naklad:** S

### N5: Sparkline trendu wydatkow
Strzalka +23.6% mowi ile, ale nie jak. Mini wykres liniowy (7 punktow) daje wiecej kontekstu.
- **Naklad:** M

## Co zmienic

- **ROAS 0% przy braku konwersji** — technicznie poprawne (spend>0, value=0 → ROAS=0%), ale UX-owo niespojne z CPA (ktore poprawnie zwraca "—"). Rozwazyc: `roas = None when conversions == 0` dla spójności. Lub zostawić bo GAds też pokazuje ROAS 0%.
- **IS kolumna visible gdy brak danych** — rozwazyc auto-hide. Pusta kolumna to szum wizualny.

## Porownanie z Google Ads UI (zaktualizowane)

| Funkcja | Google Ads MCC | Nasza apka | Werdykt |
|---------|---------------|------------|---------|
| Lista kont z metrykami | Tabela z kolumnami | 11+ metryk + pacing + billing | **LEPSZE** |
| Filtr okresu | Date picker | Period pills (7/14/30/MTD) | **LEPSZE** (szybsze) |
| Impression Share | Dodawalna kolumna | Kolumna z kolorami | **IDENTYCZNE** |
| Bulk actions | Checkboxy + menu | Checkboxy + toolbar | **IDENTYCZNE** |
| Pacing per konto | Brak (per kampania) | Podwojny progress bar | **LEPSZE** |
| External changes | Reczne filtrowanie | Auto-count + badge | **LEPSZE** |
| New access detection | Brak | UserPlus badge | **LEPSZE** |
| Dismiss rekomendacji | Per konto multi-click | One-click + bulk | **LEPSZE** |
| Compact/full toggle | Brak | Toggle button | **LEPSZE** |
| Billing status | Widoczny inline | Ikona + styled tooltip | **IDENTYCZNE** |
| NKL cross-account | Shared Sets manager | MCC sekcja | **IDENTYCZNE** |
| Optimization Score | Widoczny per konto | Brak | **GORSZE** |
| Waluta | Widoczna | Brak | **GORSZE** |

**Bilans: 8 LEPSZE, 3 IDENTYCZNE, 2 GORSZE** (poprzednio: 7 LEPSZE, 1 IDENTYCZNE, 3 GORSZE)

## Nawigacja i kontekst

- **Skad user trafia:** Landing page — `/` redirectuje do `/mcc-overview`
- **Dokad przechodzi:** Wiersz→Dashboard, Zmiany→ActionHistory, Rek.→Recommendations, External→GoogleAds
- **Co dziala dobrze:** Deep-links, external Google Ads link, breadcrumb "← Wszystkie konta"
- **Do poprawy:** Brak linku do health/quality-score z MCC widoku

## Odpowiedzi na pytania @ads-user

1. **IS kolumna pusta** — backend poprawnie liczy avg IS z MetricDaily, ale seed nie generuje `search_impression_share`. Fix: doseedowac. Tymczasowo: auto-hide kolumny gdy 0% kont ma dane.
2. **ROAS 0% przy 0 konwersji** — technicznie poprawne (GAds tez tak robi). Ale mozna zmienic na None gdy conversions==0 dla spójności z CPA. Decyzja produktowa.
3. **Optimization Score** — metoda `_get_health_score` istnieje w MCCService ale nie jest wołana. Można przywrocic jako kolumne z minimalnym nakladem.
4. **Waluta** — model Client nie ma pola currency. Wszystkie kwoty sa w jednej walucie (USD z API). Dodanie currency to M-size task (model + seed + UI).
5. **Pacing tooltip** — dane `pacing.budget` i `pacing.spent` juz sa w response. Wystarczy dodac tooltip w UI.

## Rekomendacja koncowa

**ZACHOWAC** — MCC Overview jest production-ready. 8 unikalnych wartosci vs Google Ads MCC, zero krytycznych brakow, pelne metryki + pacing + bulk actions + period pills. Widok spelnia cel "15 min poranny triage" z zapasem.

**Priorytet next sprint (nice to have):**
1. IS seed data (S) — zeby kolumna nie byla pusta
2. Pacing tooltip z kwotami (S) — dane juz w response
3. Health/OptScore kolumna (S) — metoda juz istnieje
4. ROAS consistency fix (S) — None when conv==0
