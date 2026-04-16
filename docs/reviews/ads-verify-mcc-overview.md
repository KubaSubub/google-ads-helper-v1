# Plan implementacji — MCC Overview
> Na podstawie: docs/reviews/ads-expert-mcc-overview.md
> Data weryfikacji: 2026-04-14

---

## Podsumowanie

- Elementow z raportu: 11
- DONE: 0 | PARTIAL: 2 | MISSING: 8 | NOT_NEEDED: 1
- Szacowany naklad: sredni (lacznie ~6-8h)

---

## Status kazdego elementu

### KRYTYCZNE (P0/P1)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 1 | ROAS jako mnoznik (x) zamiast procent | MISSING | `mcc_service.py:368` oblicza `roas_pct = conv/spend*100`, UI wyswietla `{acc.roas_pct.toFixed(0)}%` z progami 400/200 | Zmiana obliczenia (usunac `*100`), rename pola na `roas`, zmiana UI i progow kolorow, aktualizacja testow lock | M |
| 2 | Filtr kont aktywnych vs nieaktywnych | MISSING | Brak parametru `active_only` w `GET /mcc/overview` (`routers/mcc.py:22`) i w `MCCService.get_overview()` | Dodac param do routera, logike do serwisu, pill-toggle w UI | M |
| 3 | Bell-ikona alertow klikalna → `/alerts` | PARTIAL | Sciezka `/alerts` istnieje w routerze (`routes.jsx:59`), `handleDeepLink` jest zaimplementowany (`MCCOverviewPage.jsx:279`), ale bell ma `onClick={e => e.stopPropagation()}` bez nawigacji | Jedna linia: zmienic `onClick` z `stopPropagation` na `handleDeepLink(acc, '/alerts', e)`, dodac `cursor: pointer` | S |
| 4 | Eksport CSV tabeli kont | MISSING | Brak jakiejkolwiek funkcji eksportu w `MCCOverviewPage.jsx` i `routers/mcc.py` | Dodac funkcje `handleExportCSV` generujaca CSV z `accounts` array po stronie frontendu (bez backendu), dodac przycisk w headerze | S |
| 5 | Health Score drill-down do skladowych | PARTIAL | Backend `mcc_service.py:596-601` zwraca `health.pillars` (dict 6 filarow), ale `_build_account_data:487` przekazuje tylko `health.get("score")` — pillars nie sa w response; UI na `MCCOverviewPage.jsx:659` ma tylko `title` tooltip, brak `onClick` i brak renderowania filarow | (A) Dodac `"health_pillars": health.get("pillars") if health else None` do response dict w `mcc_service.py:487-488`; (B) Dodac `onClick` i popover w UI z 6 filarami | M |
| 6 | IS kolumna zawsze widoczna (nie tylko gdy dane) | MISSING | `MCCOverviewPage.jsx:392` warunkuje cala kolumne na `hasAnyIS`; w dev bez seed IS kolumna znika | Zmienic logike: zawsze renderowac kolumne IS w expanded mode (`!compactMode`), pokazywac `—` gdy brak danych | S |

### NICE TO HAVE (P2/P3)

| # | Element | Status | Co istnieje | Co brakuje | Naklad |
|---|---------|--------|-------------|------------|--------|
| 7 | Zapamiętanie sortowania w localStorage | MISSING | `MCCOverviewPage.jsx:211-212` uzywa zwykłego `useState` dla `sortBy`, `sortDir`, `compactMode` | Hook `useLocalStorage` lub bezposredni `localStorage.getItem/setItem`, brak hooka w projekcie | S |
| 8 | KPI strip: klikniecia zaokraglone do int | MISSING | `MCCOverviewPage.jsx:495` — `fmtNum(totalClicks)` (decimals=0 wystarczy, ale moze byc float po agregacji); backend model `MetricDaily.clicks = Column(Integer)` jest poprawny | Dodac `Math.round()` przy liczeniu `totalClicks` w reduce: `accounts.reduce((s, a) => s + Math.round(a.clicks || 0), 0)` | S |
| 9 | IS weighted average po wydatkach | MISSING | `mcc_service.py:502` uzywa `func.avg(MetricDaily.search_impression_share)` — prosta srednia | Zmienic query na dwa agregaty: `sum(cost_micros * IS)` / `sum(cost_micros)` dla weighted average | M |
| 10 | Test: IS = null gdy brak danych | MISSING | `test_mcc.py:460` pokrywa case z danymi, brak testu dla braku IS | Dodac `test_mcc_overview_IS_none_when_no_data` w `test_mcc.py` | S |
| 11 | "Odkryj konta" przycisk — nizszy wizualny priorytet | NOT_NEEDED | Przyciski juz roznia sie stylem: Sync ma `C.infoBg/B.info`, Discover ma `C.w04/B.subtle` — subtelna roznica istnieje. Marek nie zglosil tego jako bloker — cosmetics | Ewentualnie: ukryc tekst i zostawic tylko ikone z tooltipem; nie blokuje | S |

---

## Kolejnosc implementacji (rekomendowana)

```
Sprint 1 — quick wins (naklad S, lacznie ~1.5h):
  [ ] Bell klikalna → /alerts — MCCOverviewPage.jsx:610 (jedna linia)
  [ ] IS zawsze widoczna w expanded mode — MCCOverviewPage.jsx:392 i :564
  [ ] Eksport CSV — MCCOverviewPage.jsx (nowa funkcja + przycisk, ~20 linii)
  [ ] Klikniecia zaokraglone — MCCOverviewPage.jsx:388 (Math.round w reduce)
  [ ] Zapamiętanie sortowania w localStorage — MCCOverviewPage.jsx:211-213
  [ ] Test IS null — test_mcc.py (nowa funkcja testowa)

Sprint 2 — sredni naklad (naklad M, lacznie ~3.5h):
  [ ] ROAS: mnoznik zamiast procent — mcc_service.py:368 + MCCOverviewPage.jsx:644 + testy
  [ ] Filtr aktywnych kont — mcc.py router + MCCService + MCCOverviewPage.jsx header
  [ ] Health Score pillars w response + drill-down popover — mcc_service.py:487 + MCCOverviewPage.jsx:659

Sprint 3 — refactor (naklad M, ~1h):
  [ ] IS weighted average — mcc_service.py:492-511 (nowy sposob agregacji)
```

---

## Szczegoly implementacji

### Sprint 1

#### Bell → /alerts (S)
- **Plik**: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:610`
- **Zmiana frontend**: `onClick={e => e.stopPropagation()}` → `onClick={(e) => handleDeepLink(acc, '/alerts', e)}`; `cursor: 'default'` → `cursor: 'pointer'`
- **Testy**: nie potrzebne (nawigacja)

#### IS zawsze w expanded mode (S)
- **Plik**: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`
- **Zmiana frontend**:
  - Linia 392: `const hasAnyIS = accounts.some(...)` — zostawic dla info, ale nie warunkowac tym kolumny
  - Linia 564 (naglowek): `{hasAnyIS && <SortHeader label="IS" ...>}` → `{!compactMode && <SortHeader label="IS" ...>}`
  - Linia 649 (komorka): `{hasAnyIS && (<td ...>` → `{!compactMode && (<td ...>` (dane juz sa renderowane warunkowo wewnatrz)
- **Testy**: nie potrzebne

#### Eksport CSV (S)
- **Plik**: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`
- **Zmiana frontend**: Dodac funkcje przed `return`:
  ```js
  const handleExportCSV = () => {
      const cols = ['Konto', 'Wydatki', 'Kliknięcia', 'Wyświetlenia', 'CTR%', 'CPC', 'Konwersje', 'CVR%', 'CPA', 'ROAS%', 'IS%', 'Health', 'Sync']
      const rows = accounts.map(a => [
          a.client_name, a.spend, a.clicks, a.impressions,
          a.ctr_pct, a.avg_cpc, a.conversions, a.conversion_rate_pct,
          a.cpa, a.roas_pct, a.search_impression_share_pct,
          a.health_score, a.last_synced_at ? a.last_synced_at.slice(0, 10) : '',
      ])
      const csv = [cols, ...rows].map(r => r.map(v => v ?? '').join(';')).join('\n')
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `mcc-overview-${new Date().toISOString().slice(0,10)}.csv`
      a.click(); URL.revokeObjectURL(url)
  }
  ```
- Dodac przycisk w headerze obok Columns toggle (ikona Download z lucide-react)
- **Testy**: nie potrzebne

#### Klikniecia zaokraglone (S)
- **Plik**: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:388`
- **Zmiana frontend**: `accounts.reduce((s, a) => s + (a.clicks || 0), 0)` → `accounts.reduce((s, a) => s + Math.round(a.clicks || 0), 0)`
- **Testy**: nie potrzebne

#### Zapamiętanie sortowania (S)
- **Plik**: `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:211-213`
- **Zmiana frontend**: Zastapic `useState` bezposrednim localStorage:
  ```js
  const [sortBy, setSortBy] = useState(() => localStorage.getItem('mcc-sort-by') || 'spend')
  const [sortDir, setSortDir] = useState(() => localStorage.getItem('mcc-sort-dir') || 'desc')
  const [compactMode, setCompactMode] = useState(() => localStorage.getItem('mcc-compact') !== 'false')
  ```
  Wrappery setterow:
  ```js
  const handleSort = (field) => {
      if (sortBy === field) {
          const next = sortDir === 'asc' ? 'desc' : 'asc'
          setSortDir(next); localStorage.setItem('mcc-sort-dir', next)
      } else {
          setSortBy(field); localStorage.setItem('mcc-sort-by', field)
          setSortDir('desc'); localStorage.setItem('mcc-sort-dir', 'desc')
      }
  }
  // compactMode toggle: dodac localStorage.setItem('mcc-compact', String(!compactMode))
  ```
- **Testy**: nie potrzebne

#### Test IS null (S)
- **Plik**: `backend/tests/test_mcc.py` — dodac na koncu pliku:
  ```python
  def test_mcc_overview_IS_none_when_no_data(db):
      """search_impression_share_pct must be None (not 0) when no IS data exists."""
      client = _client(db, "NoIS", "999")
      camp = _campaign(db, client.id)
      today = date.today()
      db.add(MetricDaily(
          campaign_id=camp.id, date=today,
          clicks=10, impressions=100, cost_micros=1_000_000,
          # search_impression_share intentionally omitted
      ))
      db.commit()
      svc = MCCService(db)
      result = svc.get_overview(date_from=today, date_to=today)
      acc = result["accounts"][0]
      assert acc["search_impression_share_pct"] is None, "IS should be None, not 0, when no data"
  ```

---

### Sprint 2

#### ROAS — mnoznik (M)
- **Pliki**: `backend/app/services/mcc_service.py:368,471`, `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:563,644-646`, `backend/tests/test_mcc.py` (lock tests na `roas_pct`)
- **Zmiana backend** (`mcc_service.py:368`):
  ```python
  # PRZED:
  roas = round(conv_value / spend * 100, 1) if spend > 0 and conv_value > 0 else None
  # PO:
  roas = round(conv_value / spend, 2) if spend > 0 and conv_value > 0 else None
  ```
- **Zmiana backend** (`mcc_service.py:471`): `"roas_pct": roas` → `"roas": roas`
- **Zmiana frontend** (`MCCOverviewPage.jsx:563`): `<SortHeader label="ROAS" field="roas_pct" ...>` → `field="roas"`
- **Zmiana frontend** (`MCCOverviewPage.jsx:644-646`):
  ```jsx
  {acc.roas != null
      ? <span style={{ color: acc.roas >= 4.0 ? C.success : acc.roas >= 2.0 ? C.accentBlue : C.warning }}>{acc.roas.toFixed(2)}x</span>
      : '—'}
  ```
- **Testy**: Zaktualizowac testy w `test_mcc.py` ktore sprawdzaja `roas_pct` — zmienic na `roas`; sprawdzic grep:
  ```
  grep -n "roas_pct" backend/tests/test_mcc.py
  ```
- **UWAGA**: Sprawdzic tez `test_mcc_router_contract.py` pod katem `roas_pct`

#### Filtr aktywnych kont (M)
- **Pliki**: `backend/app/routers/mcc.py:21-30`, `backend/app/services/mcc_service.py:42-64`, `frontend/src/features/mcc-overview/MCCOverviewPage.jsx`
- **Zmiana backend router** (`mcc.py`):
  ```python
  @router.get("/overview")
  def mcc_overview(
      date_from: str = Query(None),
      date_to: str = Query(None),
      active_only: bool = Query(False, description="Filter accounts with spend > 0 in period"),
      db: Session = Depends(get_db),
  ):
      ...
      return MCCService(db).get_overview(date_from=d_from, date_to=d_to, active_only=active_only)
  ```
- **Zmiana backend serwis** (`mcc_service.py:42`):
  ```python
  def get_overview(self, date_from=None, date_to=None, active_only: bool = False) -> dict:
      ...
      accounts = []
      for client in clients:
          acc = self._build_account_data(client, date_from, date_to)
          if active_only and acc["spend"] == 0:
              continue
          accounts.append(acc)
  ```
- **Zmiana frontend** (`MCCOverviewPage.jsx`):
  - Nowy state: `const [activeOnly, setActiveOnly] = useState(false)`
  - Przekazac do API: `getMccOverview({ ...dateParams, active_only: activeOnly })`
  - Dodac pill-toggle "Wszystkie / Aktywne" w sekcji headerowej (obok PERIODS)
- **Testy**: Dodac `test_mcc_overview_active_only_filters_zero_spend` w `test_mcc.py`

#### Health Score pillars drill-down (M)
- **Pliki**: `backend/app/services/mcc_service.py:487-488`, `frontend/src/features/mcc-overview/MCCOverviewPage.jsx:659-678`
- **Zmiana backend** (`mcc_service.py` po linii 487):
  ```python
  "health_score": health.get("score") if health else None,
  "health_pillars": health.get("pillars") if health else None,
  ```
- **Zmiana frontend** (`MCCOverviewPage.jsx`):
  - Nowy state: `const [hoveredHealth, setHoveredHealth] = useState(null)`
  - Owinac kolo SVG w `<span style={{ position: 'relative', cursor: acc.health_pillars ? 'pointer' : 'default' }} onMouseEnter/Leave>` z popoverem pokazujacym 6 filarow z `acc.health_pillars`
  - Popover: tabela 6 wierszy (nazwa filaru: Performance, Quality, Efficiency, Coverage, Stability, Structure + wartosc/100)
- **Testy**: Dodac test ze `health_pillars` jest obecny w response gdy health score jest obliczony

---

### Sprint 3

#### IS weighted average (M)
- **Plik**: `backend/app/services/mcc_service.py:492-511`
- **Zmiana backend** (`_aggregate_metrics`): Zastapic `func.avg(MetricDaily.search_impression_share)` dwoma agregatami:
  ```python
  func.sum(MetricDaily.cost_micros * MetricDaily.search_impression_share),
  func.sum(case((MetricDaily.search_impression_share.isnot(None), MetricDaily.cost_micros), else_=0)),
  ```
  Obliczenie: `weighted_is = weighted_sum / total_cost_with_is if total_cost_with_is > 0 else None`
- **Zmiana testu**: Zaktualizowac `test_mcc_overview_impression_share` zeby weryfikowac weighted avg, nie plain avg
- **Import**: Dodac `from sqlalchemy import case` do importow w `mcc_service.py`
