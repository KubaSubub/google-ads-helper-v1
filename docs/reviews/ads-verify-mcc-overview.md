# Plan implementacji — MCC Overview (re-test po sprintach)
> Na podstawie: docs/reviews/ads-expert-mcc-overview.md (2026-04-02, ocena 8.8/10)
> Data weryfikacji: 2026-04-02

## Podsumowanie
- Elementów z raportu: 9
- DONE: 3 | PARTIAL: 1 | MISSING: 4 | NOT_NEEDED: 1
- Szacowany nakład: mały (Sprint 1 = ~1h)

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| K1 | Filtr okresu (days) | MISSING | `_aggregate_metrics()` przyjmuje start/end. `GET /mcc/new-access` ma param `days`. | Param `days` w `GET /mcc/overview`. UI selector (pills 7d/14d/30d/miesiąc). | S |
| K2 | KPI cards z zerami | PARTIAL | Tabela obsługuje null/0 z myślnikiem. KPI cards zawsze widoczne. | Warunkowo ukryć KPI card gdy suma=0 a spend>0 (clicks, impressions). Zamienić "Avg. CTR" na "Aktywne kampanie" gdy clicks=0. | S |

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| N1 | Impression Share per konto | MISSING | MetricDaily ma `search_impression_share`. `_aggregate_metrics()` nie agreguje IS. | Dodać avg IS do agregacji + kolumna w tabeli. | S |
| N2 | Billing tooltip (styled) | DONE | `BillingBadge` ma `title` attr na każdy status (Płatności OK / Brak billing / etc). | — (native tooltip działa, styled tooltip byłby lepszy ale nie krytyczny) | — |
| N3 | Domyślny compact mode | DONE | `compactMode` default `false`. Toggle działa. | Zmienić `useState(false)` → `useState(true)`. | trivial |
| N4 | Row selection + bulk actions | MISSING | Brak checkboxów i bulk menu. | Checkbox per wiersz + toolbar "Synchronizuj X" / "Odrzuć rek. X". | M |

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Empty state MCC NKL — lepsza wiadomość | DONE | "Brak list wykluczeń na poziomie MCC." | Można poprawić na "Połącz konto MCC..." ale obecna jest ok. | — |
| Z2 | Health deep-link | MISSING | Health kółko ma tooltip (hover) ale cursor: default, brak onClick. | Dodać onClick → navigate('/dashboard') z pre-selected clientem. | S |

## Kolejność implementacji (rekomendowana)

```
Sprint 1 (quick wins — nakład S, ~1h):
  [ ] K1 — Filtr okresu: param `days` w overview endpoint + pills UI (7d/14d/30d)
  [ ] K2 — KPI cards: ukryć zerowe, zamienić Avg CTR → Aktywne konta
  [ ] N3 — Compact mode domyślny: zmienić useState(false) → useState(true)
  [ ] Z2 — Health deep-link: onClick na kółku → navigate('/dashboard')

Sprint 2 (nice to have — nakład S/M):
  [ ] N1 — Impression Share: avg IS w _aggregate_metrics + kolumna
  [ ] N4 — Row selection + bulk actions (M)
```

## Szczegóły implementacji

### K1: Filtr okresu

**Backend — `backend/app/routers/mcc.py`:**
```python
@router.get("/overview")
def mcc_overview(days: int = Query(30, ge=7, le=90), db: Session = Depends(get_db)):
    return MCCService(db).get_overview(days=days)
```

**Backend — `backend/app/services/mcc_service.py`:**
Zmienić `get_overview()` aby przyjmował `days` i przekazywał do `_build_account_data()`.
Zmienić hardcoded `timedelta(days=30)` → `timedelta(days=days)`.

**Frontend — `MCCOverviewPage.jsx`:**
Dodać state `period` (7/14/30) + pills pod tytułem. Przekazać do `getMccOverview(days)`.

**Frontend — `api.js`:**
```javascript
export const getMccOverview = (days = 30) => api.get('/mcc/overview', { params: { days } })
```

**Testy:** Dodać `test_mcc_overview_custom_period` — 7d vs 30d daje różne wyniki.

### K2: KPI cards z zerami

**Frontend — `MCCOverviewPage.jsx`:**
Filtrować KPI array: jeśli totalClicks=0 i totalSpend>0, nie pokazywać "Kliknięcia" i "Wyświetlenia".
Zamienić "Avg. CTR" na "Aktywne konta" (count of accounts with spend > 0).

### N3: Compact mode domyślny

**Frontend — `MCCOverviewPage.jsx`:**
Zmiana jednej linii: `useState(false)` → `useState(true)`.

### Z2: Health deep-link

**Frontend — `MCCOverviewPage.jsx`:**
Na `<span>` health kółka dodać:
```jsx
onClick={(e) => handleDeepLink(acc, '/dashboard', e)}
style={{ cursor: 'pointer' }}
```
