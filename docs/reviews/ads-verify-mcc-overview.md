# Plan implementacji — MCC Overview (re-test #2)
> Na podstawie: docs/reviews/ads-expert-mcc-overview.md (2026-04-08, ocena 9.2/10)
> Data weryfikacji: 2026-04-08

## Podsumowanie
- Elementow z raportu: 7
- DONE: 0 | PARTIAL: 2 | MISSING: 3 | NOT_NEEDED: 2
- Szacowany naklad: maly (Sprint 1 = 4 taski S)

## Status kazdego elementu

### KRYTYCZNE (must implement)

Brak — wszystkie krytyczne z poprzedniego raportu naprawione.

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| N1 | IS seed data | NOT_NEEDED | Seed generuje IS ale tylko dla Demo Meble (wykluczone z MCC). Konta z API maja IS jesli zsynchronizowane. | W dev widac "—" bo brak realnych danych. Nie bug — data issue. | — |
| N2 | Waluta przy kwotach | MISSING | Model Client nie ma pola currency. OfflineConversion ma currency_code="PLN". | Pole currency na Client + wyswietlanie w tabeli. | M |
| N3 | Budget kwota w pacing | PARTIAL | Response ma `pacing.budget` i `pacing.spent`. Frontend renderuje progress bar bez tooltipa. | Tooltip na pacing z "Budzet: X, Wydano: Y". | S |
| N4 | Optimization Score per konto | PARTIAL | `_get_health_score()` istnieje w MCCService:518. Nie jest wolana w `_build_account_data`. | Wywolac metode + dodac kolumne w UI. | S |
| N5 | Sparkline trendu wydatkow | MISSING | Brak. Recharts LineChart uzywany na innych stronach (Dashboard, Forecast). | Nowy endpoint z daily spend data + mini LineChart. | M |

### ZMIANY/USUNIECIA

| # | Element | Status | Aktualny stan | Rekomendacja | Naklad |
|---|---------|--------|---------------|--------------|--------|
| Z1 | ROAS 0% przy braku konwersji | MISSING | `roas = conv_value/spend*100 if spend>0` — zwraca 0 gdy conv=0. CPA poprawnie zwraca None. | Dodac warunek `and conv_value > 0` lub zostawic (GAds tez pokazuje 0%). Decyzja produktowa. | S |
| Z2 | IS auto-hide gdy brak danych | MISSING | Kolumna IS zawsze widoczna. | Sprawdzac czy ktorekolwiek konto ma IS — jesli nie, ukryc kolumne. | S |

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — naklad S, ~1.5h):
  [ ] N3 — Pacing tooltip: dodac title attr z "Budzet: X, Wydano: Y" na pacing bar
  [ ] N4 — Health score kolumna: wywolac _get_health_score + kolumna w tabeli
  [ ] Z1 — ROAS consistency: dodac `and conv_value > 0` do warunku
  [ ] Z2 — IS auto-hide: sprawdzac dane, ukryc kolumne gdy brak

Sprint 2 (sredni naklad — M, v1.1+):
  [ ] N2 — Waluta: pole currency na Client + wyswietlanie (wymaga reseed)
  [ ] N5 — Sparkline: endpoint daily_spend + mini LineChart per konto
```

## Szczegoly implementacji

### N3: Pacing tooltip z kwotami

**Frontend — `MCCOverviewPage.jsx`:**
Na div z pacing bar dodac `title`:
```jsx
<div title={`Budżet: ${fmtMoney(acc.pacing?.budget)} | Wydano: ${fmtMoney(acc.pacing?.spent)}`}>
```
Dane `pacing.budget` i `pacing.spent` juz sa w API response.

### N4: Health score kolumna

**Backend — `mcc_service.py`:**
W `_build_account_data`, dodac:
```python
health = self._get_health_score(cid)
```
I w return dict:
```python
"health_score": health.get("score") if health else None,
```

**Frontend — `MCCOverviewPage.jsx`:**
Dodac kolumne po IS:
```jsx
<SortHeader label="Health" field="health_score" ... />
```
Cell: kolko SVG z kolorem (>=80 zielony, >=50 zolty, <50 czerwony).

### Z1: ROAS consistency

**Backend — `mcc_service.py:306`:**
```python
# Przed:
roas = round(conv_value / spend * 100, 1) if spend > 0 else None
# Po:
roas = round(conv_value / spend * 100, 1) if spend > 0 and conv_value > 0 else None
```

### Z2: IS auto-hide

**Frontend — `MCCOverviewPage.jsx`:**
```jsx
const hasAnyIS = accounts.some(a => a.search_impression_share_pct != null)
```
Warunkowo renderowac kolumne IS tylko gdy `hasAnyIS`.
