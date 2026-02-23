# PLIK NAPRAWCZY — Frontend + Backend
## Google Ads Helper — Kompletna lista poprawek dla Claude Code

**Data:** 2025-02-17
**Wersja:** 1.0
**Priorytet:** Wykonaj w kolejności sekcji (BACKEND najpierw, potem FRONTEND)
**Źródło prawdy:** Implementation_Blueprint.md > Blueprint_Patch_v2_1.md > Technical_Spec.md > PRD_Core.md

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ A: BACKEND — POPRAWKI KRYTYCZNE
# ═══════════════════════════════════════════════════════

## 🔴 B-01: ADR-002 — Float → BigInteger dla wartości pieniężnych

**Dotkniętość:** WSZYSTKIE modele z polami pieniężnymi
**Ryzyko:** Błędy zaokrągleń, niezgodność z Google Ads API (zwraca micros)

### Problem
Wszystkie kolumny pieniężne w `models.py` używają `Float`:
- `Campaign.budget_amount`
- `Keyword.cost`, `Keyword.avg_cpc`, `Keyword.cpc_bid`
- `SearchTerm.cost`, `SearchTerm.cost_per_conversion`
- `Ad.cost`
- `MetricDaily.cost`, `MetricDaily.cost_per_conversion`, `MetricDaily.avg_cpc`
- `AdGroup.cpc_bid`

### Wymagana zmiana
```python
# ZAMIAST:
budget_amount = Column(Float)

# POWINNO BYĆ:
budget_amount_micros = Column(BigInteger, default=0)  # przechowuj w micros
```

Konwersja na float TYLKO w schematach Pydantic:
```python
# W schemas/campaign.py
from pydantic import computed_field

class CampaignResponse(BaseModel):
    budget_amount_micros: int

    @computed_field
    @property
    def budget_amount(self) -> float:
        return self.budget_amount_micros / 1_000_000
```

### Pliki do zmiany
- `backend/app/models.py` → rozbić na `models/*.py` (patrz B-04) + zmienić typy
- `backend/app/schemas.py` → rozbić na `schemas/*.py` + dodać `@computed_field`
- `backend/app/seed.py` → wartości seed * 1_000_000
- `backend/app/routers/*.py` → dostosować do nowych nazw pól
- `backend/app/services/*.py` → dostosować do micros

---

## 🔴 B-02: Brakujące modele wymagane przez Blueprint

### Problem
Brakuje 3 modeli zdefiniowanych w Blueprint:

**a) ActionLog** — wymagany do Feature 4 (Undo)
```python
# models/action_log.py
class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    action_type = Column(String, nullable=False)  # PAUSE_KEYWORD, SET_BID, etc.
    entity_type = Column(String, nullable=False)   # keyword, ad, campaign
    entity_id = Column(Integer, nullable=False)
    old_value_json = Column(Text)      # JSON z poprzednim stanem
    new_value_json = Column(Text)      # JSON z nowym stanem
    status = Column(String, default="SUCCESS")  # SUCCESS, FAILED, REVERTED
    reverted_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=func.now())
```

**b) Alert** — wymagany do Feature 7 (Anomaly Detection)
```python
# models/alert.py
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    alert_type = Column(String, nullable=False)   # ANOMALY, BUDGET_OVERSPEND, etc.
    severity = Column(String, default="MEDIUM")
    title = Column(String, nullable=False)
    description = Column(Text)
    metric = Column(String)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
```

**c) Recommendation (persystowany)** — wymagany do Apply/Dismiss
```python
# models/recommendation.py
class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    type = Column(String, nullable=False)           # PAUSE_KEYWORD, INCREASE_BID, etc.
    priority = Column(String, default="MEDIUM")     # HIGH, MEDIUM, LOW
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)
    entity_name = Column(String)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    reason = Column(Text)
    recommended_action = Column(String)
    current_value = Column(String, nullable=True)
    status = Column(String, default="PENDING")      # PENDING, APPLIED, DISMISSED
    created_at = Column(DateTime, default=func.now())
    applied_at = Column(DateTime, nullable=True)
```

### Obecny `ExecutionQueueItem` NIE zastępuje ActionLog — brak `old_value_json`, brak `reverted_at`, brak statusu REVERTED.

---

## 🔴 B-03: ADR-004 — Brakujący credentials_service.py

### Problem
Tokeny czytane bezpośrednio z `.env` przez pydantic-settings w `google_ads.py`. Blueprint wymaga dedykowanego `credentials_service.py` z biblioteką `keyring`.

### Wymagana zmiana
```python
# backend/app/services/credentials_service.py
import keyring

SERVICE_NAME = "GoogleAdsHelper"

class CredentialsService:
    @staticmethod
    def get_token(key: str) -> str | None:
        return keyring.get_password(SERVICE_NAME, key)

    @staticmethod
    def set_token(key: str, value: str):
        keyring.set_password(SERVICE_NAME, key, value)

    @staticmethod
    def delete_token(key: str):
        keyring.delete_password(SERVICE_NAME, key)
```

ADR-004: "credentials_service.py is the ONLY file that reads/writes tokens"

---

## 🟠 B-04: Struktura plików niezgodna z Blueprint

### Problem
Monolityczne `models.py` i `schemas.py` zamiast osobnych plików.

### Wymagana struktura (z Blueprint §1):
```
backend/app/
├── models/
│   ├── __init__.py          # eksportuje wszystkie modele
│   ├── client.py
│   ├── campaign.py
│   ├── keyword.py
│   ├── search_term.py
│   ├── recommendation.py
│   ├── action_log.py
│   └── alert.py
├── schemas/
│   ├── __init__.py
│   ├── common.py            # Enumy: Priority, ActionStatus, Segment
│   ├── client.py
│   ├── campaign.py
│   ├── recommendation.py
│   └── search_term.py
```

Blueprint reguła: "Create files EXACTLY in the locations shown. Zero improvisation."

---

## 🟠 B-05: Brak Circuit Breaker (validate_action)

### Problem
`google_ads.py apply_action()` wykonuje mutacje (PAUSE_KEYWORD, SET_BID) bez walidacji.

### Wymagana zmiana (z CLAUDE.md Reguła 4):
```python
# backend/app/services/action_executor.py

def validate_action(self, action_type: str, entity_id: int, params: dict) -> dict:
    """
    KAŻDY zapis do Google Ads API MUSI przejść przez tę funkcję.
    Sprawdza:
    - Czy akcja jest dozwolona
    - Czy nie przekracza limitów bezpieczeństwa (SAFETY_LIMITS)
    - Czy dry_run → tylko symulacja
    Zwraca: { allowed: bool, reason: str, old_value_json: dict }
    """

def execute_action(self, action_type, entity_id, params, dry_run=False):
    validation = self.validate_action(action_type, entity_id, params)
    if not validation["allowed"]:
        raise ValueError(validation["reason"])
    if dry_run:
        return {"dry_run": True, "preview": validation}
    # ... faktyczne wykonanie
    # ... zapis do action_log z old_value_json

def revert_action(self, action_log_id: int):
    """Cofnij akcję z action_log (< 24h, nie cofnięta wcześniej)"""
```

---

## 🟠 B-06: Brakujące pliki serwisowe z Blueprint

### Problem
Logika biznesowa w routerach zamiast w serwisach. Brakujące pliki:

| Plik | Status | Opis |
|------|--------|------|
| `services/search_terms_service.py` | ❌ BRAK | Segmentacja (150+ linii inline w routerze) |
| `services/analytics_service.py` | ❌ BRAK | KPI + anomalie + quality score + forecast |
| `services/action_executor.py` | ❌ BRAK | validate_action() + revert_action() |
| `services/credentials_service.py` | ❌ BRAK | Jedyne miejsce na tokeny (ADR-004) |
| `services/recommendations_engine.py` | ❌ BRAK | 7 reguł z Playbooka, oddzielony od routerów |

### Router `search_terms.py` ma ~150 linii logiki segmentacji — to powinien być service.

---

## 🟠 B-07: Nieprawidłowa formuła ROAS w analytics.py

### Problem
```python
# Obecne (ZŁE):
roas = conversions / cost  # to jest conversion rate per dollar

# Prawidłowe:
roas = revenue / cost
# gdzie revenue = conversions * avg_order_value (z client.business_rules)
```

`seed.py` używa: `roas = conversions * 150 / cost` (zakłada AOV=150 PLN)
`analytics.py` używa: `roas = conversions / cost` — NIEZGODNOŚĆ

---

## 🟠 B-08: seed.py — crash risk

### Problem
```python
# Linia z zagnieżdżonym random.choice/db.query(Campaign).get()
# może rzucić IndexError jeśli brak kampanii
```

Dodatkowo `db.query(Campaign).get()` jest deprecated w SQLAlchemy 2.0.

### Poprawka
```python
# Użyj db.get(Campaign, id) zamiast db.query(Campaign).get(id)
# Dodaj sprawdzenie czy lista kampanii nie jest pusta
```

---

## 🟡 B-09: Deprecated datetime.utcnow

### Problem
Modele używają `default=datetime.utcnow` (deprecated od Python 3.12+).

### Poprawka
```python
# ZAMIAST:
created_at = Column(DateTime, default=datetime.utcnow)

# POWINNO BYĆ:
created_at = Column(DateTime, server_default=func.now())
# LUB:
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

---

## 🟡 B-10: Importy na dole plików

### Problem
`main.py` i `analytics.py` mają importy po kodzie z `# noqa: E402`

### Poprawka
Przenieś importy na górę pliku. Jeśli circular import — refaktoruj.

---

## 🟡 B-11: Brak audit logging w actions.py

### Problem
`apply_recommendation` nie loguje do `AccessLog` ani `ActionLog`.
Model `AccessLog` istnieje ale jest nieużywany.

---

## 🟡 B-12: semantic.py — thread-safety

### Problem
Lazy loading `_model` bez lock (race condition przy wielu requestach):
```python
# Obecne:
if _model is None:
    _model = load_model()  # BEZ LOCKA

# Poprawka:
import threading
_lock = threading.Lock()
def get_model():
    global _model
    with _lock:
        if _model is None:
            _model = load_model()
    return _model
```

---

## 🟡 B-13: cache.py — misleading TTL API

### Problem
`set_cached()` akceptuje parametr `ttl` ale `cachetools.TTLCache` nie wspiera per-key TTL. Parametr jest ignorowany.

### Poprawka
Usuń parametr `ttl` z `set_cached()` lub dodaj komentarz wyjaśniający.

---

## 🟡 B-14: Hardcoded IRRELEVANT_WORDS w search_terms.py

### Problem
Lista stop-words hardcoded w kodzie. Powinna być konfigurowalna per-client.

### Poprawka
Przenieś do `Client.business_rules` lub `utils/constants.py`.

---

## 🟢 B-15: export.py — brak walidacji

`export.py` nie sprawdza czy `campaign_id`/`client_id` istnieje → zwraca pusty plik bez błędu.

## 🟢 B-16: PaginatedResponse — brak generycznego typowania

`items: list` bez parametru typu → traci walidację Pydantic.

## 🟢 B-17: Brak katalogu tests/

`pytest` w `requirements.txt` ale brak `tests/` katalogu.

## 🟢 B-18: config.py — side effect w property

`data_dir` property tworzy katalog w getterze. Powinno być w lifespan event.

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ B: FRONTEND — POPRAWKI
# ═══════════════════════════════════════════════════════

## 🔴 F-01: Brakujące wymagane strony (Blueprint §1)

### Problem
Blueprint i Technical_Spec wymagają tych stron, których NIE MA w kodzie:

| Strona | Status | Wymagania |
|--------|--------|-----------|
| `pages/Clients.jsx` | ❌ BRAK | Lista klientów, dodawanie, sync all, selektor klienta |
| `pages/ActionHistory.jsx` | ❌ BRAK | Chronologiczna lista akcji + przycisk Undo (Feature 4) |
| `pages/Alerts.jsx` | ❌ BRAK | Zakładki: Nierozwiązane/Rozwiązane (Feature 7) |

### Strony NADMIAROWE (nie w Blueprint, mogą zostać jako bonus):
- `pages/Semantic.jsx` — klastry semantyczne (post-MVP, ale użyteczne)
- `pages/QualityScore.jsx` — audyt QS (post-MVP)
- `pages/Forecast.jsx` — prognozowanie (post-MVP)

**Decyzja:** Zachowaj nadmiarowe strony, ale NAJPIERW utwórz brakujące.

---

## 🔴 F-02: Brak komponentu ConfirmationModal

### Problem
Technical_Spec §2.5 wymaga `ConfirmationModal.jsx` — modal potwierdzenia PRZED każdą akcją:
- Wyświetla: co się zmieni, obecna wartość → nowa wartość, powód
- Przyciski: "Apply" / "Cancel"
- Stan ładowania na przycisku

### Obecny stan
`Recommendations.jsx` wykonuje akcje BEZ potwierdzenia (bezpośredni `handleApply`). To narusza PRD Feature 2 ("Confirmation modal before each action — paranoid mode").

### Wymagana implementacja
```jsx
// components/ConfirmationModal.jsx
export default function ConfirmationModal({
    isOpen, onClose, onConfirm,
    title,           // "Pause Keyword?"
    actionType,      // "PAUSE_KEYWORD"
    entity,          // "'nike shoes' in Campaign X"
    beforeState,     // { status: "ENABLED", bid: "$1.50" }
    afterState,      // { status: "PAUSED" }
    reason,          // "High spend ($50) with 0 conversions"
    isLoading
}) { ... }
```

---

## 🔴 F-03: Brak komponentu Toast (oddzielny)

### Problem
Technical_Spec wymaga `components/Toast.jsx` — osobny komponent powiadomień.
Obecny kod ma toast wbudowany inline w `Recommendations.jsx` (lokalne `useState`).

### Wymagana implementacja
Reużywalny system toast z auto-dismiss, używany globalnie.
Najlepiej: `hooks/useToast.js` + `components/Toast.jsx` renderowany w `App.jsx`.

---

## 🔴 F-04: Brak hooks/ katalogu

### Problem
Technical_Spec §1.2 i Blueprint wymagają:
```
hooks/
├── useClients.js          # Fetch/cache client list, selected client
├── useRecommendations.js  # Fetch recs, apply, dismiss
├── useSync.js             # Trigger sync, track progress
├── useAlerts.js           # Fetch alert count for sidebar badge
└── useToast.js            # Toast notification state
```

ZERO custom hooks istnieje w kodzie.

---

## 🔴 F-05: Brak Global State (selectedClientId)

### Problem
Technical_Spec §1.4 wymaga:
- `selectedClientId` w React Context (persisted w localStorage)
- `alertCount` dla sidebar badge

### Obecny stan
`clientId = 1` HARDCODED w `Dashboard.jsx`, `Keywords.jsx`, `SearchTerms.jsx`, `Settings.jsx`, etc.

### Wymagana implementacja
```jsx
// contexts/AppContext.jsx
const AppContext = createContext();

export function AppProvider({ children }) {
    const [selectedClientId, setSelectedClientId] = useState(
        () => localStorage.getItem('selectedClientId') || null
    );
    const [alertCount, setAlertCount] = useState(0);

    useEffect(() => {
        if (selectedClientId) {
            localStorage.setItem('selectedClientId', selectedClientId);
        }
    }, [selectedClientId]);

    return (
        <AppContext.Provider value={{
            selectedClientId, setSelectedClientId,
            alertCount, setAlertCount
        }}>
            {children}
        </AppContext.Provider>
    );
}

export const useApp = () => useContext(AppContext);
```

---

## 🟠 F-06: api.js — fetch zamiast Axios

### Problem
Technical_Spec §4 wymaga Axios z interceptorami:
```javascript
// Technical_Spec wymaga:
import axios from 'axios';
const api = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' }
});
api.interceptors.response.use(...)
```

### Obecny stan
Używa natywnego `fetch()` z ręcznym wrapper `fetchAPI()`.

### Decyzja
`fetch` działa, ale:
1. Brak automatycznego timeout (sync może trwać długo)
2. Brak interceptorów do globalnej obsługi błędów
3. NIEZGODNOŚĆ z Blueprint

**Poprawka:** Zainstaluj axios (`npm install axios`) i przepisz `api.js` wg Technical_Spec §4.

---

## 🟠 F-07: Brak DataTable.jsx (TanStack Table wrapper)

### Problem
Technical_Spec §2.4 wymaga `DataTable.jsx` — reużywalny wrapper na @tanstack/react-table z:
- sortowaniem po kolumnach
- globalnym search
- paginacją

### Obecny stan
Każda strona (`Keywords.jsx`, `SearchTerms.jsx`) buduje tabele od zera z ręcznymi `<table>` elementami. MASYWNA duplikacja kodu.

### Wymagana implementacja
```jsx
// components/DataTable.jsx
export default function DataTable({
    data, columns,
    searchable = false,
    searchPlaceholder = "Szukaj...",
    pageSize = 25,
    onRowClick,
    emptyMessage = "Brak danych"
}) {
    // użyj @tanstack/react-table
}
```

---

## 🟠 F-08: Brak komponentów z Blueprint

| Komponent | Status | Wymaganie |
|-----------|--------|-----------|
| `components/DataTable.jsx` | ❌ BRAK | TanStack Table wrapper |
| `components/ConfirmationModal.jsx` | ❌ BRAK | Before/After preview |
| `components/Toast.jsx` | ❌ BRAK | Global notifications |
| `components/SegmentBadge.jsx` | ❌ BRAK | Color-coded segment labels |
| `components/PriorityBadge.jsx` | ❌ BRAK | HIGH (red) / MEDIUM (amber) |
| `components/SyncButton.jsx` | ❌ BRAK | Refresh z loading spinner |
| `components/EmptyState.jsx` | ❌ BRAK | "No data" placeholder |

Obecne `UI.jsx` zawiera `Badge`, `StatusBadge`, `LoadingSpinner`, `ErrorMessage`, `PageHeader` — te są OK ale powinny być rozbite na osobne pliki.

---

## 🟠 F-09: Sidebar — brak client selector i sync

### Problem
Technical_Spec §2.2 wymaga:
- Client dropdown na dole sidebara
- Sync button + last synced timestamp
- Alert count badge

### Obecny stan
- Hardcoded "Demo Meble Sp. z o.o." zamiast dropdown
- Brak sync button
- Brak alert badge

---

## 🟠 F-10: Recommendations.jsx — brak Dismiss, brak dry_run

### Problem
1. Brak przycisku "Dismiss" na rekomendacjach (wymagane przez Technical_Spec)
2. Brak dry_run preview przed Apply
3. Brak ConfirmationModal przed Apply (PRD Feature 2)
4. Mieszanka polskiego i angielskiego UI ("Apply", "Applying..." ale "Odśwież", "Wszystkie Typy")

### API wg Technical_Spec:
```javascript
// Wymagane:
applyRecommendation = (id, clientId, dryRun) =>
    api.post(`/recommendations/${id}/apply`, null, { params: { client_id: clientId, dry_run: dryRun } });
dismissRecommendation = (id) =>
    api.post(`/recommendations/${id}/dismiss`);
```

---

## 🟠 F-11: vite.config.js — proxy niezgodny z Blueprint

### Problem
```javascript
// Obecne:
proxy: { '/api': { target: 'http://127.0.0.1:8000' } }

// Technical_Spec wymaga osobne proxy per ścieżka:
proxy: {
    '/auth': 'http://localhost:8000',
    '/clients': 'http://localhost:8000',
    '/campaigns': 'http://localhost:8000',
    '/keywords': 'http://localhost:8000',
    '/search-terms': 'http://localhost:8000',
    '/recommendations': 'http://localhost:8000',
    '/actions': 'http://localhost:8000',
    '/analytics': 'http://localhost:8000',
    '/health': 'http://localhost:8000',
}
```

**LUB** upewnij się że backend używa prefiksu `/api/v1` konsekwentnie. Obecny frontend zakłada `/api/v1` ale Technical_Spec tego nie wymaga.

**Decyzja:** Ujednolicić — albo WSZĘDZIE `/api/v1` (obecne podejście) albo BEZ prefiksu (Blueprint). Rekomendacja: zachować `/api/v1` i zaktualizować proxy.

---

## 🟠 F-12: tailwind.config.js — brakujące kolory z Technical_Spec

### Problem
Technical_Spec §5.2 definiuje kolory:
```javascript
'app-bg': '#0F172A',
'app-sidebar': '#1E293B',
'app-card': '#334155',
'app-text': '#F1F5F9',
'app-muted': '#94A3B8',
'app-accent': '#3B82F6',
'app-success': '#10B981',
'app-warning': '#F59E0B',
'app-danger': '#EF4444',
```

Obecny config używa `brand` i `surface` zamiast `app-*`. To OK jeśli świadoma decyzja, ale kolory się różnią.

**Decyzja:** Zachować obecne `brand`/`surface` (wyglądają lepiej) ale DODAĆ brakujące `app-*` aliasy dla kompatybilności z Blueprint.

---

## 🟡 F-13: Dashboard — hardcoded clientId = 1

Każda strona ma `const clientId = 1`. Powinno brać z kontekstu (patrz F-05).

## 🟡 F-14: Brak i18n / niespójny język

Mieszanka PL i EN w UI. Rekomendacja: WSZYSTKO po polsku (user preference) LUB spójnie dwujęzyczne.

Przykłady niespójności:
- Sidebar: "Kampanie", "Słowa kluczowe" (PL) ale "Search Terms", "Quality Score" (EN)
- Recommendations: "Apply", "Applying..." (EN) ale "Odśwież", "Wszystkie Typy" (PL)
- SearchTerms: "$" symbol zamiast "zł" w segmented view

## 🟡 F-15: SearchTerms — $ zamiast zł

```jsx
// Obecne (ZŁE):
<td>...${t.cost?.toFixed(2)}</td>

// Poprawne:
<td>...{t.cost?.toFixed(2)} zł</td>
```

Dotyczy: `SearchTerms.jsx` (segmented view), `Recommendations.jsx`

## 🟡 F-16: Brak package axios w package.json

`axios` nie jest w dependencies. Trzeba dodać:
```bash
npm install axios
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ C: KOLEJNOŚĆ IMPLEMENTACJI
# ═══════════════════════════════════════════════════════

## Sprint 1: Backend Infrastructure Fix (NAJPIERW)

```
1. B-04: Rozbij models.py → models/*.py (zachowaj dane w DB)
2. B-01: Float → BigInteger (migracja + seed update)
3. B-02: Dodaj brakujące modele (ActionLog, Alert, Recommendation)
4. B-04: Rozbij schemas.py → schemas/*.py + @computed_field
5. B-09: datetime.utcnow → func.now()
6. B-10: Napraw importy
```

## Sprint 2: Backend Services Fix

```
7.  B-03: Utwórz credentials_service.py
8.  B-06: Utwórz brakujące serwisy (action_executor, search_terms_service, analytics_service)
9.  B-05: Dodaj validate_action() circuit breaker
10. B-07: Napraw formułę ROAS
11. B-08: Napraw seed.py crash risk
12. B-11: Dodaj audit logging
13. B-12: Thread-safety w semantic.py
14. B-13: Napraw cache.py API
```

## Sprint 3: Frontend Foundation Fix

```
15. F-16: npm install axios
16. F-06: Przepisz api.js na axios (wg Technical_Spec §4)
17. F-05: Dodaj AppContext (selectedClientId, alertCount)
18. F-04: Utwórz hooks/ (useClients, useToast, useSync, useAlerts)
19. F-03: Utwórz components/Toast.jsx (globalny)
20. F-02: Utwórz components/ConfirmationModal.jsx
21. F-07: Utwórz components/DataTable.jsx
22. F-08: Utwórz brakujące komponenty (SegmentBadge, PriorityBadge, SyncButton, EmptyState)
```

## Sprint 4: Frontend Pages Fix

```
23. F-01: Utwórz pages/Clients.jsx
24. F-01: Utwórz pages/ActionHistory.jsx (z Undo)
25. F-01: Utwórz pages/Alerts.jsx (Unresolved/Resolved tabs)
26. F-09: Napraw Sidebar (client dropdown, sync, alert badge)
27. F-10: Napraw Recommendations.jsx (Dismiss, ConfirmationModal, dry_run)
28. F-13: Zamień hardcoded clientId na useApp() context
29. F-14/F-15: Ujednolicić język i walutę
30. F-11: Napraw vite.config proxy
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ D: PLIKI DO UTWORZENIA (kompletna lista)
# ═══════════════════════════════════════════════════════

## Backend — NOWE pliki

```
backend/app/models/__init__.py
backend/app/models/client.py
backend/app/models/campaign.py
backend/app/models/keyword.py
backend/app/models/search_term.py
backend/app/models/recommendation.py
backend/app/models/action_log.py
backend/app/models/alert.py

backend/app/schemas/__init__.py
backend/app/schemas/common.py
backend/app/schemas/client.py
backend/app/schemas/campaign.py
backend/app/schemas/recommendation.py
backend/app/schemas/search_term.py

backend/app/services/credentials_service.py
backend/app/services/action_executor.py
backend/app/services/search_terms_service.py
backend/app/services/analytics_service.py
backend/app/services/recommendations_engine.py

backend/tests/__init__.py
backend/tests/test_models.py
backend/tests/test_services.py
```

## Backend — pliki do USUNIĘCIA po migracji

```
backend/app/models.py          → zastąpiony przez models/
backend/app/schemas.py         → zastąpiony przez schemas/
```

## Frontend — NOWE pliki

```
frontend/src/contexts/AppContext.jsx

frontend/src/hooks/useClients.js
frontend/src/hooks/useRecommendations.js
frontend/src/hooks/useSync.js
frontend/src/hooks/useAlerts.js
frontend/src/hooks/useToast.js

frontend/src/components/ConfirmationModal.jsx
frontend/src/components/Toast.jsx
frontend/src/components/DataTable.jsx
frontend/src/components/SegmentBadge.jsx
frontend/src/components/PriorityBadge.jsx
frontend/src/components/SyncButton.jsx
frontend/src/components/EmptyState.jsx

frontend/src/pages/Clients.jsx
frontend/src/pages/ActionHistory.jsx
frontend/src/pages/Alerts.jsx
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ E: PODSUMOWANIE PRIORYTETÓW
# ═══════════════════════════════════════════════════════

| Priorytet | Backend | Frontend | Suma |
|-----------|---------|----------|------|
| 🔴 Krytyczny (blokujący) | 3 (B-01, B-02, B-03) | 5 (F-01 do F-05) | **8** |
| 🟠 Poważny (must fix) | 5 (B-04 do B-08) | 7 (F-06 do F-12) | **12** |
| 🟡 Średni (tech debt) | 6 (B-09 do B-14) | 4 (F-13 do F-16) | **10** |
| 🟢 Drobny (improvement) | 4 (B-15 do B-18) | — | **4** |
| **RAZEM** | **18** | **16** | **34** |

---

**KONIEC PLIKU NAPRAWCZEGO**
**Rozpocznij od Sprint 1 (Backend Infrastructure Fix)**
