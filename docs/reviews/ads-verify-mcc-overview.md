# Plan implementacji — MCC Overview (re-test #2)
> Na podstawie: docs/reviews/ads-expert-mcc-overview.md (2026-04-08, ocena 9.2/10)
> Data weryfikacji: 2026-04-08

## Podsumowanie
- Elementow z raportu: 7
- DONE: 6 | PARTIAL: 0 | MISSING: 0 | NOT_NEEDED: 2 (Sprint 1+2 COMPLETE)
- E2E LOCK: 52 backend tests (29 lock tests), 539 total backend, build OK

## Status kazdego elementu

### KRYTYCZNE (must implement)

Brak — wszystkie krytyczne z poprzedniego raportu naprawione.

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| N1 | IS seed data | NOT_NEEDED | Seed generuje IS ale tylko dla Demo Meble (wykluczone z MCC). Konta z API maja IS jesli zsynchronizowane. | W dev widac "—" bo brak realnych danych. Nie bug — data issue. | — |
| N2 | Waluta przy kwotach | DONE | Client.currency (String(3), default "PLN") + auto-migration. fmtMoneyC() w MCCOverviewPage z symbolem (zł/$/€). Spend, CPC, CPA, conv value, pacing tooltip. | — | — |
| N3 | Budget kwota w pacing | DONE | Pacing cell ma `title` attr: "Budżet: X \| Wydano: Y". Dane z API response. | — | — |
| N4 | Optimization Score per konto | DONE | `_get_health_score()` wywołana w `_build_account_data`. SVG gauge w tabeli (zielony >=80, żółty >=50, czerwony <50). | — | — |
| N5 | Sparkline trendu wydatkow | DONE | spend_trend embedded w /mcc/overview response (daily GROUP BY). SpendSparkline 56×20 Recharts LineChart, accentBlue, no dots. | — | — |

### ZMIANY/USUNIECIA

| # | Element | Status | Aktualny stan | Rekomendacja | Naklad |
|---|---------|--------|---------------|--------------|--------|
| Z1 | ROAS 0% przy braku konwersji | DONE | `roas = ... if spend > 0 and conv_value > 0 else None`. Zwraca None zamiast 0% — czytelniejsze. | — | — |
| Z2 | IS auto-hide gdy brak danych | DONE | `hasAnyIS = accounts.some(a => a.search_impression_share_pct != null)`. Header + cell warunkowo renderowane. | — | — |

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 (quick wins — DONE 2026-04-09):
  [x] N3 — Pacing tooltip: title attr z "Budżet: X | Wydano: Y" na pacing cell
  [x] N4 — Health score kolumna: _get_health_score + SVG gauge w tabeli
  [x] Z1 — ROAS consistency: `and conv_value > 0` — returns None not 0%
  [x] Z2 — IS auto-hide: hasAnyIS computed, kolumna ukryta gdy brak danych

Sprint 2 (DONE 2026-04-10):
  [x] N2 — Waluta: currency na Client model + fmtMoneyC() z symbolem + auto-migration
  [x] N5 — Sparkline: spend_trend embedded w overview + mini LineChart (Recharts 56×20)
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
