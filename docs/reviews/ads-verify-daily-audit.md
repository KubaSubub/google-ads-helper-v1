# Plan implementacji — Poranny Przegląd (Daily Audit)
> Na podstawie: docs/reviews/ads-expert-daily-audit.md
> Data weryfikacji: 2026-04-10

---

## Podsumowanie

- Elementów z raportu: 11
- DONE: 1 | PARTIAL: 3 | MISSING: 7 | NOT_NEEDED: 0
- Szacowany nakład łączny: **średni** (Sprint 1: ~1.5h, Sprint 2: ~3h, Sprint 3: ~4h)

---

## Status każdego elementu

### KRYTYCZNE (must implement)

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| K1 | CPA w KPI snapshot | MISSING | `_build_kpi_snapshot()` zwraca cost, clicks, conversions. `MetricDaily` ma `cost_micros` + `conversions`. | Backend: dodać `cpa` = cost/conversions do `_agg()` i do response dict. Frontend: 4. `KpiChip` z `invertColor=false`, suffix=" zł". | S |
| K2 | ROAS w KPI snapshot | PARTIAL | `MetricDaily` ma `conversion_value_micros` i kolumnę `roas` (Float). Model gotowy. | Backend: dodać `func.sum(MetricDaily.conversion_value_micros)` do `_agg()`, obliczyć ROAS = conv_value / cost. Frontend: 5. `KpiChip` z suffix="x". | S |
| K3 | CTR w KPI snapshot | PARTIAL | `MetricDaily` ma `impressions` (Integer). Model gotowy. | Backend: dodać `func.sum(MetricDaily.impressions)` do `_agg()`, obliczyć CTR = clicks/impressions * 100. Frontend: 6. `KpiChip` z suffix="%". | S |
| K4 | Auto-expand skryptów gdy akcje > 0 | PARTIAL | `loadScriptCounts()` wywołuje `setScriptsExpanded(prev => prev === null ? true : prev)` (DailyAudit.jsx:250). Logika jest, ale `useState(null)` + asynchroniczne ustawienie może nie działać przy pierwszym renderze. | Frontend: zmienić inicjalizację `useState(null)` → `useState(false)`, a w `loadScriptCounts` po obliczeniu total: `if (total > 0) setScriptsExpanded(true)` (bez sprawdzenia `prev`). | S |
| K5 | Timestamp ostatniego synca | MISSING | `SyncLog` model ma `finished_at`. Router `sync.py:536` już pobiera last_sync dla klienta. `daily_audit.py` nie odpytuje `SyncLog`. | Backend: dodać query `SyncLog` w `daily_audit()` — pobierz ostatni sukces/partial dla client_id, dodaj `last_sync_at` do response. Frontend: wyświetlić w nagłówku obok "Odśwież" jako szary tekst "Dane z: HH:MM". | S |

---

### NICE TO HAVE

| # | Element | Status | Co istnieje | Co brakuje | Nakład |
|---|---------|--------|-------------|------------|--------|
| N1 | Top moverzy (biggest changes per campaign) | MISSING | `MetricDaily` ma dane per campaign. `_build_kpi_snapshot()` agreguje wszystkie kampanie razem. | Backend: nowa funkcja `_build_top_movers()` — query MetricDaily per campaign_id, porównanie current vs previous period, sort by abs delta conversions, limit 5. Frontend: nowa sekcja "Największe zmiany" po KPI. | M |
| N2 | Mini-sparklines przy KPI (7-dniowy trend) | MISSING | Brak — `_build_kpi_snapshot()` zwraca tylko 2 okresy, nie dane dzienne. | Backend: nowa funkcja `_build_kpi_trend(days=7)` — per-day aggregation MetricDaily. Frontend: `<LineChart>` (recharts) per KpiChip, podobnie jak w Dashboard/TrendExplorer. | M |
| N3 | Interpretacja automatyczna zmian (CPA summary) | MISSING | Brak. | Frontend: prosty computed string po dodaniu K1 CPA — `delta_CPA < ±10% → "CPA stabilny"`. Jedno zdanie w subtittle nagłówka. Pure frontend, bez zmian backend. | S |
| N4 | Konfigurowalny okres porównania (integracja z date pickerem) | MISSING | `period_days=3` hardcoded w `_build_kpi_snapshot()`. Sidebar ma globalny FilterContext z `days`. | Backend: dodać `period_days: int = Query(3)` do endpointu `/daily-audit/`. Frontend: przekazać `days` z `useFilter()` jako param do `getDailyAudit()`. | S |
| N5 | Historia audytów (trend alertów) | MISSING | Brak tabeli `audit_snapshots`. | Wymaga nowego modelu DB + seed + endpoint. V2 feature — pominąć teraz. | L |
| N6 | Budget pacing wyżej w layoucie (przed rekomendacjami) | MISSING | ROW 4 w DailyAudit.jsx. | Frontend: przestawić `<BudgetPacingModule>` z ROW 4 → ROW 2 (po KPI, przed skryptami). Czysta zmiana kolejności JSX. | S |

---

### ZMIANY/USUNIĘCIA

| # | Element | Status | Aktualny stan | Rekomendacja | Nakład |
|---|---------|--------|---------------|--------------|--------|
| Z1 | Kolorowanie spadku kosztów — inwersja koloru | PARTIAL | `KpiCard.jsx` ma już `invertColor` prop + `DeltaIndicator` obsługuje `invertColor`. W `size="sm"` (DailyAudit) brak obsługi `invertColor` — linia 58 bezpośrednio używa `C.success`/`C.danger` bez sprawdzenia prop. | Frontend: w `KpiCard.jsx` sekcja `isSm` (linia 54-62) dodać logikę `invertColor`: `const isGood = invertColor ? computedDelta < 0 : computedDelta > 0`. Potem w DailyAudit.jsx dodać `invertColor` do KpiChip Wydatki. | S |
| Z2 | Zmienna `cost_usd` — rename na `cost` | DONE | Backend daily_audit.py:356: pole nazwane `cost_usd`. Frontend DailyAudit.jsx:479 używa `t.cost_usd`. Bug semantyczny (USD vs zł), ale nie powoduje błędu runtime. | Backend: zmienić `"cost_usd"` → `"cost"` w `_build_search_terms_needing_action()`. Frontend: zmienić `t.cost_usd` → `t.cost`. Prosta zmiana nazwy. | S |
| Z3 | Przycisk "Szczegóły" → nawigacja do konkretnego alertu | MISSING | DailyAudit.jsx:381: `navigate('/alerts')` bez parametrów. | Frontend: zmienić na `navigate('/alerts', { state: { highlightSeverity: 'high' } })` lub `navigate('/alerts?severity=high')`. Wymaga sprawdzenia czy Alerts page obsługuje query params (weryfikacja osobno). | S |
| Z4 | Usunąć label "(zaawansowane)" ze skryptów | MISSING | DailyAudit.jsx:425: `<span>(zaawansowane)</span>`. | Frontend: usunąć ten `<span>`. Jedna linia. | S |

---

## Kolejność implementacji (rekomendowana)

```
Sprint 1 — quick wins (nakład S, łączny ~1.5h):
  [ ] K4 — Auto-expand skryptów: zmienić useState(null) → useState(false) [DailyAudit.jsx:225]
  [ ] Z4 — Usunąć "(zaawansowane)" [DailyAudit.jsx:425]
  [ ] Z2 — Rename cost_usd → cost [daily_audit.py:356, DailyAudit.jsx:479]
  [ ] Z1 — invertColor dla KpiChip Wydatki [KpiCard.jsx:54-62 + DailyAudit.jsx:407]
  [ ] N3 — Interpretacja CPA (po dodaniu K1) [DailyAudit.jsx — computed string w subtitle]

Sprint 2 — KPI rozszerzenie (nakład S+S+S = ~2h łącznie):
  [ ] K1 — CPA w KPI: backend _agg() + response dict + KpiChip [daily_audit.py:511-529 + DailyAudit.jsx:407-409]
  [ ] K2 — ROAS w KPI: backend + KpiChip [daily_audit.py:511-529 + DailyAudit.jsx:407-409]
  [ ] K3 — CTR w KPI: backend + KpiChip [daily_audit.py:511-529 + DailyAudit.jsx:407-409]
  [ ] K5 — Timestamp synca: backend query SyncLog + frontend header [daily_audit.py:40-127 + DailyAudit.jsx:314-349]

Sprint 3 — strukturalne (nakład M+S+S = ~3h łącznie):
  [ ] N6 — Budget pacing wyżej: przestawienie BudgetPacingModule z ROW 4 → ROW 2 [DailyAudit.jsx:557-562]
  [ ] N4 — Konfigurowalny okres: Query param period_days + FilterContext [daily_audit.py + DailyAudit.jsx]
  [ ] Z3 — Alert navigate z params [DailyAudit.jsx:381 + Alerts.jsx — sprawdzić obsługę]
  [ ] N1 — Top moverzy: nowa funkcja _build_top_movers() + sekcja UI [daily_audit.py + DailyAudit.jsx]

Sprint 4 — future / v2:
  [ ] N2 — Sparklines: per-day trend data (nowy endpoint lub rozszerzenie) + recharts
  [ ] N5 — Historia audytów: nowy model audit_snapshots (wymaga DB reseed)
```

---

## Szczegóły implementacji

### K1 — CPA w KPI snapshot

**Pliki do modyfikacji:**
- `backend/app/routers/daily_audit.py`
- `frontend/src/pages/DailyAudit.jsx`

**Zmiany backend** (`daily_audit.py`, funkcja `_agg()`, linia ~511):
```python
# W _agg() — dodać do return dict:
cpa = round(spend / conversions, 2) if conversions > 0 else None

return {
    "spend": ...,
    "clicks": ...,
    "conversions": ...,
    "impressions": int(row.impressions or 0) if row else 0,
    "conversion_value": round(micros_to_currency(row.conv_value or 0), 2) if row else 0.0,
    "cpa": cpa,
    "roas": ...,
    "ctr": ...,
}
```
Dodać do query: `func.sum(MetricDaily.impressions).label("impressions")`, `func.sum(MetricDaily.conversion_value_micros).label("conv_value")`.

Do response dict `_build_kpi_snapshot()` dodać:
```python
"current_cpa": current["cpa"],
"previous_cpa": previous["cpa"],
"current_roas": current["roas"],
"previous_roas": previous["roas"],
"current_ctr": current["ctr"],
"previous_ctr": previous["ctr"],
```

**Zmiany frontend** (`DailyAudit.jsx`, sekcja KPI, linia ~407-409):
```jsx
<KpiChip label="CPA" current={kpi.current_cpa} previous={kpi.previous_cpa} suffix=" zł" size="sm" invertColor />
<KpiChip label="ROAS" current={kpi.current_roas} previous={kpi.previous_roas} suffix="x" size="sm" />
<KpiChip label="CTR" current={kpi.current_ctr} previous={kpi.previous_ctr} suffix="%" size="sm" />
```

**Dane:** MetricDaily ma `conversion_value_micros` i `impressions` — brak zmian modelu.
**Testy:** Brak istniejącego testu dla daily_audit — opcjonalnie dodać `test_daily_audit_kpi_includes_cpa()`.

---

### K5 — Timestamp ostatniego synca

**Pliki do modyfikacji:**
- `backend/app/routers/daily_audit.py`
- `frontend/src/pages/DailyAudit.jsx`

**Zmiany backend** — dodać w `daily_audit()` (linia ~50, po deklaracjach dat):
```python
from app.models import SyncLog  # już importowany przez __init__

last_sync = (
    db.query(SyncLog)
    .filter(SyncLog.client_id == client_id, SyncLog.status.in_(["success", "partial"]))
    .order_by(SyncLog.finished_at.desc())
    .first()
)
last_sync_at = last_sync.finished_at.isoformat() if last_sync and last_sync.finished_at else None
```
Dodać do response: `"last_sync_at": last_sync_at`

**Zmiany frontend** — w nagłówku (`DailyAudit.jsx`, linia ~323, obok przycisk Odśwież):
```jsx
{d.last_sync_at && (
    <span style={{ fontSize: 10, color: C.w30 }}>
        Dane z: {new Date(d.last_sync_at).toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' })}
    </span>
)}
```

---

### K4 — Auto-expand skryptów

**Plik:** `frontend/src/pages/DailyAudit.jsx`, linia 225.

**Zmiana:**
```jsx
// PRZED:
const [scriptsExpanded, setScriptsExpanded] = useState(null)
// ...
if (total > 0) setScriptsExpanded(prev => prev === null ? true : prev)

// PO:
const [scriptsExpanded, setScriptsExpanded] = useState(false)
// ...
if (total > 0) setScriptsExpanded(true)
```
Uwaga: toggle `onClick` musi nadal działać — `setScriptsExpanded(prev => !prev)` pozostaje bez zmian.

---

### Z1 — invertColor dla KpiChip Wydatki (rozmiar sm)

**Plik:** `frontend/src/components/modules/KpiCard.jsx`, linia 54-62.

**Zmiana — dodać prop `invertColor` do size="sm" branch:**
```jsx
// PRZED (linia 58):
color: computedDelta > 0 ? C.success : computedDelta < 0 ? C.danger : C.w25 }}>
{computedDelta > 0 ? <TrendingUp size={10} /> : computedDelta < 0 ? <TrendingDown size={10} /> : null}

// PO:
const isGoodSm = invertColor ? computedDelta < 0 : computedDelta > 0
// ... color: isGoodSm ? C.success : (computedDelta === 0 ? C.w25 : C.danger)
// ... icon: computedDelta > 0 ? <TrendingUp/> : computedDelta < 0 ? <TrendingDown/> : null
```

**Plik:** `frontend/src/pages/DailyAudit.jsx`, linia 407 — dodać `invertColor`:
```jsx
<KpiChip label="Wydatki" current={kpi.current_spend} previous={kpi.previous_spend} suffix=" zł" size="sm" invertColor />
```

---

### N6 — Budget pacing wyżej (ROW 2, po KPI)

**Plik:** `frontend/src/pages/DailyAudit.jsx`

Przestawić blok `<BudgetPacingModule>` (linia 557-562) z pozycji ROW 4 na pozycję bezpośrednio po bloku KPI (linia ~411), przed ROW 2 (skrypty). Efekt: KPI → Pacing → Skrypty → Search Terms + Rekomendacje.

---

### N4 — Konfigurowalny okres porównania

**Pliki:**
- `backend/app/routers/daily_audit.py` — dodać `period_days: int = Query(3, ge=1, le=30)`
- `frontend/src/pages/DailyAudit.jsx` — dodać `useFilter()`, przekazać `days` do `getDailyAudit()`

**Backend** (linia 39-40):
```python
@router.get("/")
def daily_audit(
    client_id: int = Query(...),
    period_days: int = Query(3, ge=1, le=30),
    db: Session = Depends(get_db),
):
```
Przekazać `period_days` do `_build_kpi_snapshot(db, enabled_campaign_ids, today, period_days)`.

**Frontend** (`getDailyAudit` linia 16):
```js
const getDailyAudit = (clientId, days = 3) =>
    api.get('/daily-audit/', { params: { client_id: clientId, period_days: days } })
```
W komponencie: `const { days } = useFilter()` + `getDailyAudit(selectedClientId, days || 3)`.
