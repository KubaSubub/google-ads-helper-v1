# PLAN NAPRAWCZY — Frontend (szczegółowy)
## Google Ads Helper — Instrukcje krok po kroku dla Claude Code

**Data:** 2025-02-17
**Wersja:** 1.0
**Zakres:** TYLKO frontend (16 issues, 4 sprinty)
**Warunek wstępny:** Backend UKOŃCZONY (18 issues, 31 testów przechodzi)
**Źródło prawdy:** Technical_Spec.md > Implementation_Blueprint.md > Blueprint_Patch_v2_1.md > PRD_Core.md

---

# ⚠️ WAŻNE: BACKEND JUŻ NAPRAWIONY

Backend ma teraz:
- **BigInteger (micros)** w DB → API zwraca pola `_micros` + computed `_usd` (np. `cost_micros` + `cost_usd`)
- **Nowe modele:** `ActionLog`, `Alert`, `Recommendation` (persisted w DB)
- **Nowe endpointy:** `/actions/revert/{id}`, `/analytics/anomalies`, `/analytics/detect`, `/recommendations/{id}/dismiss`
- **Circuit breaker:** `validate_action()` + `dry_run` w `/recommendations/{id}/apply`
- **Segmentacja:** `/search-terms/segmented` zwraca 4 grupy z stats

Frontend MUSI być zgodny z tym API. Poniższe endpointy to **kontrakt API** do którego frontend się podłącza.

### Kontrakt API (po naprawie backendu)

```
GET  /auth/status                              → {authenticated: bool}
GET  /auth/login                               → {auth_url: str}
GET  /auth/callback?code=X                     → HTML success page
POST /auth/logout

GET  /clients                                  → [{id, name, google_ads_customer_id, last_synced_at}]
GET  /clients/{id}                             → client detail
POST /clients/{id}/sync                        → {status, message}

GET  /campaigns?client_id=X                    → [{id, name, status, budget_micros, budget_usd, spend_micros, spend_usd, ...}]
GET  /keywords?campaign_id=X                   → [{id, text, match_type, status, bid_micros, cost_micros, ...}]

GET  /search-terms/segmented?client_id=X       → {HIGH_PERFORMER: {count, terms, ...}, WASTE: {...}, ...}
GET  /search-terms/?client_id=X&segment=X      → {terms: [...], total, limit, offset}

GET  /recommendations?client_id=X&status=X     → [{id, rule_id, priority, reason, suggested_action, status}]
GET  /recommendations/summary?client_id=X      → {high: int, medium: int, total: int}
POST /recommendations/{id}/apply?client_id=X&dry_run=false → {status, action_type, message}
POST /recommendations/{id}/dismiss             → {status: "dismissed"}

GET  /actions/?client_id=X&limit=50&offset=0   → {actions: [...], total}
POST /actions/revert/{action_log_id}?client_id=X → {status, message}

GET  /analytics/kpis?client_id=X               → {total_spend_usd, total_clicks, avg_ctr_pct, ...}
GET  /analytics/campaigns?client_id=X          → campaign performance data
GET  /analytics/anomalies?client_id=X&status=unresolved → [{id, alert_type, severity, title, description, ...}]
POST /analytics/anomalies/{alert_id}/resolve?client_id=X
POST /analytics/detect?client_id=X             → triggers anomaly detection

GET  /health                                   → {status: "ok"}
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 1: FUNDAMENT (F-16, F-06, F-05, F-04)
# Axios, global state, hooks — bez tego nic nie zadziała
# ═══════════════════════════════════════════════════════

## 🟡 F-16: Zainstaluj axios

**Priorytet:** ŚREDNI (ale wymagany przed F-06)

```bash
cd frontend && npm install axios
```

Sprawdź czy `package.json` ma `"axios"` w dependencies.

---

## 🟠 F-06: Przepisz api.js — fetch → Axios

**Priorytet:** POWAŻNY
**Naruszony wymóg:** Technical_Spec §4
**Ryzyko:** Brak timeout (sync trwa długo), brak globalnych interceptorów

### Stan obecny

```javascript
// OBECNE (ZŁE) — natywny fetch z ręcznym wrapperem:
export async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`/api/v1${endpoint}`, options);
    if (!response.ok) throw new Error(...);
    return response.json();
}
```

### Wymagana implementacja (z Technical_Spec §4)

```javascript
// frontend/src/api.js
import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000',
    timeout: 30000,  // 30s — sync może trwać długo
    headers: { 'Content-Type': 'application/json' }
});

// Response interceptor: wyciągnij data, obsłuż błędy
api.interceptors.response.use(
    (response) => response.data,
    (error) => {
        const message = error.response?.data?.detail || error.message || 'Nieznany błąd';
        console.error('API Error:', message);
        return Promise.reject({ message, status: error.response?.status });
    }
);

export default api;

// ═══════ API Functions ═══════

// Auth
export const getAuthStatus = () => api.get('/auth/status');
export const getLoginUrl = () => api.get('/auth/login');
export const logout = () => api.post('/auth/logout');

// Clients
export const getClients = () => api.get('/clients');
export const getClient = (id) => api.get(`/clients/${id}`);
export const syncClient = (id) => api.post(`/clients/${id}/sync`);

// Campaigns
export const getCampaigns = (clientId) =>
    api.get('/campaigns', { params: { client_id: clientId } });

// Keywords
export const getKeywords = (campaignId) =>
    api.get('/keywords', { params: { campaign_id: campaignId } });

// Search Terms
export const getSegmentedSearchTerms = (clientId) =>
    api.get('/search-terms/segmented', { params: { client_id: clientId } });
export const getSearchTerms = (clientId, params) =>
    api.get('/search-terms/', { params: { client_id: clientId, ...params } });

// Recommendations
export const getRecommendations = (clientId, params) =>
    api.get('/recommendations', { params: { client_id: clientId, ...params } });
export const getRecommendationsSummary = (clientId) =>
    api.get('/recommendations/summary', { params: { client_id: clientId } });
export const applyRecommendation = (id, clientId, dryRun = false) =>
    api.post(`/recommendations/${id}/apply`, null, {
        params: { client_id: clientId, dry_run: dryRun }
    });
export const dismissRecommendation = (id) =>
    api.post(`/recommendations/${id}/dismiss`);

// Actions
export const getActionHistory = (clientId, params) =>
    api.get('/actions/', { params: { client_id: clientId, ...params } });
export const revertAction = (actionLogId, clientId) =>
    api.post(`/actions/revert/${actionLogId}`, null, {
        params: { client_id: clientId }
    });

// Analytics
export const getKPIs = (clientId) =>
    api.get('/analytics/kpis', { params: { client_id: clientId } });
export const getCampaignAnalytics = (clientId) =>
    api.get('/analytics/campaigns', { params: { client_id: clientId } });
export const getAnomalies = (clientId, status = 'unresolved') =>
    api.get('/analytics/anomalies', {
        params: { client_id: clientId, status }
    });
export const resolveAnomaly = (alertId, clientId) =>
    api.post(`/analytics/anomalies/${alertId}/resolve`, null, {
        params: { client_id: clientId }
    });
export const detectAnomalies = (clientId) =>
    api.post('/analytics/detect', null, {
        params: { client_id: clientId }
    });

// Health
export const getHealth = () => api.get('/health');
```

### Pliki do zmiany po przepisaniu api.js

KAŻDA strona i hook który importuje `fetchAPI` musi zmienić import:
```javascript
// ZAMIAST:
import { fetchAPI } from '../api';
const data = await fetchAPI('/campaigns?client_id=1');

// POWINNO BYĆ:
import { getCampaigns } from '../api';
const data = await getCampaigns(clientId);
```

### UWAGA: Prefix /api/v1

Obecny frontend używa `/api/v1` prefix. Nowy backend (po naprawie) NIE MA tego prefixu — endpointy to np. `/clients`, `/campaigns`, nie `/api/v1/clients`.

Jeśli backend ma `/api/v1` prefix w routerach — zachowaj go w `baseURL`:
```javascript
baseURL: 'http://localhost:8000/api/v1'
```

Jeśli backend NIE MA prefixu — użyj:
```javascript
baseURL: 'http://localhost:8000'
```

**Sprawdź w `backend/app/main.py`** jak routery są zarejestrowane.

---

## 🔴 F-05: Global State — AppContext (selectedClientId)

**Priorytet:** KRYTYCZNY
**Naruszony wymóg:** Technical_Spec §1.4
**Ryzyko:** `clientId = 1` hardcoded na KAŻDEJ stronie → app nie działa z >1 klientem

### Stan obecny

```javascript
// Dashboard.jsx, Keywords.jsx, SearchTerms.jsx, Settings.jsx — WSZĘDZIE:
const clientId = 1;  // HARDCODED!
```

### Wymagana implementacja

```jsx
// frontend/src/contexts/AppContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [selectedClientId, setSelectedClientId] = useState(
        () => {
            const saved = localStorage.getItem('selectedClientId');
            return saved ? parseInt(saved, 10) : null;
        }
    );
    const [alertCount, setAlertCount] = useState(0);

    useEffect(() => {
        if (selectedClientId) {
            localStorage.setItem('selectedClientId', String(selectedClientId));
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

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be inside AppProvider');
    return ctx;
}
```

### Podłączenie w App.jsx

```jsx
// App.jsx
import { AppProvider } from './contexts/AppContext';

function App() {
    return (
        <AppProvider>
            <BrowserRouter>
                {/* ... Sidebar + Routes */}
            </BrowserRouter>
        </AppProvider>
    );
}
```

### Wymiana hardcoded clientId — KAŻDA strona

```javascript
// ZAMIAST:
const clientId = 1;

// POWINNO BYĆ:
import { useApp } from '../contexts/AppContext';
const { selectedClientId } = useApp();

// + guard:
if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;
```

---

## 🔴 F-04: Utwórz hooks/ — 5 custom hooks

**Priorytet:** KRYTYCZNY
**Naruszony wymóg:** Technical_Spec §1.2
**Ryzyko:** Cała logika inline w komponentach → duplikacja, brak testowalności

### Wymagane hooks

**a) hooks/useClients.js**
```javascript
import { useState, useEffect } from 'react';
import { getClients } from '../api';

export function useClients() {
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchClients = async () => {
        try {
            setLoading(true);
            const data = await getClients();
            setClients(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchClients(); }, []);

    return { clients, loading, error, refetch: fetchClients };
}
```

**b) hooks/useToast.js**
```javascript
import { useState, useCallback } from 'react';

export function useToast() {
    const [toast, setToast] = useState(null);

    const showToast = useCallback((message, type = 'success', duration = 3000) => {
        setToast({ message, type, id: Date.now() });
        setTimeout(() => setToast(null), duration);
    }, []);

    const hideToast = useCallback(() => setToast(null), []);

    return { toast, showToast, hideToast };
}
```

**c) hooks/useSync.js**
```javascript
import { useState } from 'react';
import { syncClient } from '../api';

export function useSync() {
    const [syncing, setSyncing] = useState(false);
    const [error, setError] = useState(null);

    const sync = async (clientId) => {
        try {
            setSyncing(true);
            setError(null);
            const result = await syncClient(clientId);
            return result;
        } catch (err) {
            setError(err.message);
            throw err;
        } finally {
            setSyncing(false);
        }
    };

    return { sync, syncing, error };
}
```

**d) hooks/useAlerts.js**
```javascript
import { useState, useEffect, useCallback } from 'react';
import { getAnomalies } from '../api';

export function useAlerts(clientId) {
    const [alertCount, setAlertCount] = useState(0);

    const fetchCount = useCallback(async () => {
        if (!clientId) return;
        try {
            const data = await getAnomalies(clientId, 'unresolved');
            setAlertCount(data.length || 0);
        } catch {
            setAlertCount(0);
        }
    }, [clientId]);

    useEffect(() => { fetchCount(); }, [fetchCount]);

    return { alertCount, refetchAlerts: fetchCount };
}
```

**e) hooks/useRecommendations.js**
```javascript
import { useState, useEffect, useCallback } from 'react';
import {
    getRecommendations, getRecommendationsSummary,
    applyRecommendation, dismissRecommendation
} from '../api';

export function useRecommendations(clientId) {
    const [recommendations, setRecommendations] = useState([]);
    const [summary, setSummary] = useState({ high: 0, medium: 0, total: 0 });
    const [loading, setLoading] = useState(true);

    const fetch = useCallback(async (params = {}) => {
        if (!clientId) return;
        try {
            setLoading(true);
            const [recs, sum] = await Promise.all([
                getRecommendations(clientId, { status: 'pending', ...params }),
                getRecommendationsSummary(clientId)
            ]);
            setRecommendations(recs);
            setSummary(sum);
        } catch (err) {
            console.error('Failed to fetch recommendations:', err);
        } finally {
            setLoading(false);
        }
    }, [clientId]);

    useEffect(() => { fetch(); }, [fetch]);

    const apply = async (recId, dryRun = false) => {
        return await applyRecommendation(recId, clientId, dryRun);
    };

    const dismiss = async (recId) => {
        await dismissRecommendation(recId);
        await fetch();  // refetch after dismiss
    };

    return { recommendations, summary, loading, refetch: fetch, apply, dismiss };
}
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 2: KOMPONENTY (F-03, F-02, F-07, F-08)
# Reużywalne bloki UI — Toast, Modal, DataTable, badges
# ═══════════════════════════════════════════════════════

## 🔴 F-03: Utwórz components/Toast.jsx

**Priorytet:** KRYTYCZNY
**Naruszony wymóg:** Technical_Spec §2.6

### Stan obecny
Toast inline w `Recommendations.jsx` — lokalne `useState`, NIE reużywalne.

### Wymagana implementacja

```jsx
// frontend/src/components/Toast.jsx
import { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

const ICONS = {
    success: CheckCircle,
    error: AlertCircle,
    info: Info,
};

const COLORS = {
    success: 'bg-green-500/20 border-green-500/50 text-green-300',
    error: 'bg-red-500/20 border-red-500/50 text-red-300',
    info: 'bg-blue-500/20 border-blue-500/50 text-blue-300',
};

export default function Toast({ toast, onClose }) {
    if (!toast) return null;

    const Icon = ICONS[toast.type] || Info;

    return (
        <div className="fixed bottom-4 right-4 z-50 animate-slide-up">
            <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${COLORS[toast.type]}`}>
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{toast.message}</span>
                <button onClick={onClose} className="ml-2 hover:opacity-70">
                    <X className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}
```

### Podłączenie w App.jsx

```jsx
import Toast from './components/Toast';
import { useToast } from './hooks/useToast';

function App() {
    const { toast, showToast, hideToast } = useToast();

    return (
        <AppProvider>
            <ToastContext.Provider value={{ showToast }}>
                {/* routes */}
                <Toast toast={toast} onClose={hideToast} />
            </ToastContext.Provider>
        </AppProvider>
    );
}
```

Lub dodaj `showToast` do `AppContext` żeby był dostępny wszędzie.

---

## 🔴 F-02: Utwórz components/ConfirmationModal.jsx

**Priorytet:** KRYTYCZNY
**Naruszony wymóg:** Technical_Spec §2.5, PRD Feature 2
**Ryzyko:** Akcje wykonywane BEZ potwierdzenia → użytkownik nie widzi co się zmieni

### Stan obecny
`Recommendations.jsx` wykonuje Apply BEZ modala. PRD mówi: "Confirmation modal before each action — paranoid mode".

### Wymagana implementacja

```jsx
// frontend/src/components/ConfirmationModal.jsx
import { AlertTriangle, X } from 'lucide-react';

export default function ConfirmationModal({
    isOpen,
    onClose,
    onConfirm,
    title = 'Potwierdź akcję',
    actionType,         // "PAUSE_KEYWORD"
    entity,             // "'nike shoes' w kampanii Brand"
    beforeState,        // { status: "ENABLED", bid: "$1.50" }
    afterState,         // { status: "PAUSED" }
    reason,             // "Wysoki koszt ($50) bez konwersji"
    isLoading = false,
}) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/60" onClick={onClose} />

            {/* Modal */}
            <div className="relative bg-app-card border border-white/10 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-400" />
                        <h3 className="text-lg font-semibold text-app-text">{title}</h3>
                    </div>
                    <button onClick={onClose} className="text-app-muted hover:text-app-text">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Typ akcji */}
                <div className="mb-4">
                    <span className="inline-block px-2 py-1 text-xs font-mono bg-blue-500/20 text-blue-300 rounded">
                        {actionType}
                    </span>
                </div>

                {/* Entity */}
                {entity && (
                    <p className="text-sm text-app-muted mb-4">
                        Obiekt: <span className="text-app-text font-medium">{entity}</span>
                    </p>
                )}

                {/* Before → After */}
                {(beforeState || afterState) && (
                    <div className="grid grid-cols-2 gap-4 mb-4 p-3 bg-white/5 rounded-lg">
                        <div>
                            <p className="text-xs text-app-muted mb-1">Przed</p>
                            {beforeState && Object.entries(beforeState).map(([k, v]) => (
                                <p key={k} className="text-sm text-red-300">
                                    {k}: {v}
                                </p>
                            ))}
                        </div>
                        <div>
                            <p className="text-xs text-app-muted mb-1">Po</p>
                            {afterState && Object.entries(afterState).map(([k, v]) => (
                                <p key={k} className="text-sm text-green-300">
                                    {k}: {v}
                                </p>
                            ))}
                        </div>
                    </div>
                )}

                {/* Reason */}
                {reason && (
                    <p className="text-sm text-app-muted mb-6">
                        Powód: {reason}
                    </p>
                )}

                {/* Buttons */}
                <div className="flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-app-muted hover:text-app-text rounded-lg border border-white/10"
                        disabled={isLoading}
                    >
                        Anuluj
                    </button>
                    <button
                        onClick={onConfirm}
                        className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Wykonuję...' : 'Potwierdź'}
                    </button>
                </div>
            </div>
        </div>
    );
}
```

---

## 🟠 F-07: Utwórz components/DataTable.jsx

**Priorytet:** POWAŻNY
**Naruszony wymóg:** Technical_Spec §2.4

### Stan obecny
Każda strona buduje tabele ręcznie z `<table>` elementami. Masywna duplikacja.

### Wymagana implementacja

```jsx
// frontend/src/components/DataTable.jsx
import { useState, useMemo } from 'react';
import {
    useReactTable, getCoreRowModel,
    getSortedRowModel, getFilteredRowModel,
    getPaginationRowModel, flexRender
} from '@tanstack/react-table';
import { ChevronUp, ChevronDown, Search } from 'lucide-react';

export default function DataTable({
    data,
    columns,
    searchable = false,
    searchPlaceholder = 'Szukaj...',
    pageSize = 25,
    onRowClick,
    emptyMessage = 'Brak danych',
}) {
    const [sorting, setSorting] = useState([]);
    const [globalFilter, setGlobalFilter] = useState('');

    const table = useReactTable({
        data,
        columns,
        state: { sorting, globalFilter },
        onSortingChange: setSorting,
        onGlobalFilterChange: setGlobalFilter,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        initialState: { pagination: { pageSize } },
    });

    return (
        <div>
            {/* Search */}
            {searchable && (
                <div className="relative mb-4">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-app-muted" />
                    <input
                        type="text"
                        value={globalFilter}
                        onChange={(e) => setGlobalFilter(e.target.value)}
                        placeholder={searchPlaceholder}
                        className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-app-text placeholder:text-app-muted focus:outline-none focus:border-app-accent"
                    />
                </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto rounded-lg border border-white/10">
                <table className="w-full text-sm">
                    <thead className="bg-white/5">
                        {table.getHeaderGroups().map(hg => (
                            <tr key={hg.id}>
                                {hg.headers.map(header => (
                                    <th
                                        key={header.id}
                                        className="px-4 py-3 text-left text-xs font-medium text-app-muted uppercase tracking-wider cursor-pointer hover:text-app-text"
                                        onClick={header.column.getToggleSortingHandler()}
                                    >
                                        <div className="flex items-center gap-1">
                                            {flexRender(header.column.columnDef.header, header.getContext())}
                                            {header.column.getIsSorted() === 'asc' && <ChevronUp className="w-3 h-3" />}
                                            {header.column.getIsSorted() === 'desc' && <ChevronDown className="w-3 h-3" />}
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        ))}
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {table.getRowModel().rows.length === 0 ? (
                            <tr>
                                <td colSpan={columns.length} className="px-4 py-8 text-center text-app-muted">
                                    {emptyMessage}
                                </td>
                            </tr>
                        ) : (
                            table.getRowModel().rows.map(row => (
                                <tr
                                    key={row.id}
                                    className={`hover:bg-white/5 ${onRowClick ? 'cursor-pointer' : ''}`}
                                    onClick={() => onRowClick?.(row.original)}
                                >
                                    {row.getVisibleCells().map(cell => (
                                        <td key={cell.id} className="px-4 py-3 text-app-text">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {table.getPageCount() > 1 && (
                <div className="flex items-center justify-between mt-4 text-sm text-app-muted">
                    <span>
                        Strona {table.getState().pagination.pageIndex + 1} z {table.getPageCount()}
                    </span>
                    <div className="flex gap-2">
                        <button
                            onClick={() => table.previousPage()}
                            disabled={!table.getCanPreviousPage()}
                            className="px-3 py-1 rounded border border-white/10 disabled:opacity-30"
                        >
                            Poprzednia
                        </button>
                        <button
                            onClick={() => table.nextPage()}
                            disabled={!table.getCanNextPage()}
                            className="px-3 py-1 rounded border border-white/10 disabled:opacity-30"
                        >
                            Następna
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
```

### Zależność

```bash
cd frontend && npm install @tanstack/react-table
```

---

## 🟠 F-08: Utwórz brakujące komponenty

**Priorytet:** POWAŻNY
**Naruszony wymóg:** Technical_Spec §1.2, §2.x

### a) components/SegmentBadge.jsx

```jsx
const COLORS = {
    HIGH_PERFORMER: 'bg-green-500/20 text-green-300 border-green-500/30',
    WASTE: 'bg-red-500/20 text-red-300 border-red-500/30',
    IRRELEVANT: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    OTHER: 'bg-gray-500/20 text-gray-300 border-gray-500/30',
};

const LABELS = {
    HIGH_PERFORMER: 'Wysoka wydajność',
    WASTE: 'Marnowanie',
    IRRELEVANT: 'Nieistotne',
    OTHER: 'Inne',
};

export default function SegmentBadge({ segment }) {
    return (
        <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded border ${COLORS[segment] || COLORS.OTHER}`}>
            {LABELS[segment] || segment}
        </span>
    );
}
```

### b) components/PriorityBadge.jsx

```jsx
const COLORS = {
    HIGH: 'bg-red-500/20 text-red-300',
    MEDIUM: 'bg-amber-500/20 text-amber-300',
};

export default function PriorityBadge({ priority }) {
    return (
        <span className={`inline-flex px-2 py-0.5 text-xs font-bold rounded ${COLORS[priority] || 'bg-gray-500/20 text-gray-300'}`}>
            {priority}
        </span>
    );
}
```

### c) components/SyncButton.jsx

```jsx
import { RefreshCw } from 'lucide-react';

export default function SyncButton({ onClick, loading = false, lastSynced }) {
    return (
        <div className="flex items-center gap-2">
            <button
                onClick={onClick}
                disabled={loading}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-app-accent/20 text-app-accent rounded-lg hover:bg-app-accent/30 disabled:opacity-50"
            >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Synchronizacja...' : 'Synchronizuj'}
            </button>
            {lastSynced && (
                <span className="text-xs text-app-muted">
                    Ostatnia: {new Date(lastSynced).toLocaleString('pl-PL')}
                </span>
            )}
        </div>
    );
}
```

### d) components/EmptyState.jsx

```jsx
import { Inbox } from 'lucide-react';

export default function EmptyState({
    message = 'Brak danych',
    icon: Icon = Inbox,
    action,
    actionLabel,
}) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-app-muted">
            <Icon className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm mb-4">{message}</p>
            {action && (
                <button
                    onClick={action}
                    className="px-4 py-2 text-sm bg-app-accent/20 text-app-accent rounded-lg hover:bg-app-accent/30"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
}
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 3: BRAKUJĄCE STRONY (F-01)
# Clients, ActionHistory, Alerts — rdzeń brakujących feature'ów
# ═══════════════════════════════════════════════════════

## 🔴 F-01a: Utwórz pages/Clients.jsx

**Priorytet:** KRYTYCZNY
**Wymóg:** Technical_Spec §3.1, PRD Feature 1

```jsx
// frontend/src/pages/Clients.jsx
import { useClients } from '../hooks/useClients';
import { useSync } from '../hooks/useSync';
import { useApp } from '../contexts/AppContext';
import SyncButton from '../components/SyncButton';
import EmptyState from '../components/EmptyState';

export default function Clients() {
    const { clients, loading, refetch } = useClients();
    const { sync, syncing } = useSync();
    const { selectedClientId, setSelectedClientId } = useApp();

    const handleSync = async (clientId) => {
        await sync(clientId);
        refetch();
    };

    if (loading) return <LoadingSpinner />;
    if (!clients.length) return <EmptyState message="Brak klientów. Połącz konto Google Ads." />;

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-app-text mb-6">Klienci</h1>
            <div className="grid gap-4">
                {clients.map(client => (
                    <div
                        key={client.id}
                        className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                            selectedClientId === client.id
                                ? 'border-app-accent bg-app-accent/10'
                                : 'border-white/10 bg-app-card hover:border-white/20'
                        }`}
                        onClick={() => setSelectedClientId(client.id)}
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <h3 className="font-medium text-app-text">{client.name}</h3>
                                <p className="text-xs text-app-muted">ID: {client.google_ads_customer_id}</p>
                            </div>
                            <SyncButton
                                onClick={(e) => { e.stopPropagation(); handleSync(client.id); }}
                                loading={syncing}
                                lastSynced={client.last_synced_at}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

---

## 🔴 F-01b: Utwórz pages/ActionHistory.jsx

**Priorytet:** KRYTYCZNY
**Wymóg:** Technical_Spec §3.5, PRD Feature 4

```jsx
// frontend/src/pages/ActionHistory.jsx
import { useState, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import { getActionHistory, revertAction } from '../api';
import ConfirmationModal from '../components/ConfirmationModal';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import { Undo2 } from 'lucide-react';

export default function ActionHistory() {
    const { selectedClientId } = useApp();
    const [actions, setActions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [revertModal, setRevertModal] = useState(null);
    const [reverting, setReverting] = useState(false);

    const fetchActions = async () => {
        if (!selectedClientId) return;
        setLoading(true);
        try {
            const data = await getActionHistory(selectedClientId, { limit: 100 });
            setActions(data.actions || []);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchActions(); }, [selectedClientId]);

    const canRevert = (action) => {
        if (action.status !== 'SUCCESS') return false;
        if (action.action_type === 'ADD_NEGATIVE') return false;
        const age = Date.now() - new Date(action.executed_at).getTime();
        return age < 24 * 60 * 60 * 1000; // < 24h
    };

    const handleRevert = async () => {
        if (!revertModal) return;
        setReverting(true);
        try {
            await revertAction(revertModal.id, selectedClientId);
            setRevertModal(null);
            await fetchActions();
        } catch (err) {
            alert('Błąd cofania: ' + err.message);
        } finally {
            setReverting(false);
        }
    };

    const STATUS_COLORS = {
        SUCCESS: 'text-green-400',
        FAILED: 'text-red-400',
        REVERTED: 'text-gray-400',
    };

    const columns = [
        { accessorKey: 'executed_at', header: 'Data',
          cell: ({ getValue }) => new Date(getValue()).toLocaleString('pl-PL') },
        { accessorKey: 'action_type', header: 'Akcja' },
        { accessorKey: 'entity_type', header: 'Typ' },
        { accessorKey: 'entity_id', header: 'Entity ID' },
        { accessorKey: 'status', header: 'Status',
          cell: ({ getValue }) => (
            <span className={STATUS_COLORS[getValue()] || 'text-app-muted'}>{getValue()}</span>
          )},
        { id: 'actions', header: '',
          cell: ({ row }) => canRevert(row.original) ? (
            <button
                onClick={(e) => { e.stopPropagation(); setRevertModal(row.original); }}
                className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300"
            >
                <Undo2 className="w-3 h-3" /> Cofnij
            </button>
          ) : null
        },
    ];

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-app-text mb-6">Historia akcji</h1>
            <DataTable data={actions} columns={columns} searchable emptyMessage="Brak wykonanych akcji" />

            <ConfirmationModal
                isOpen={!!revertModal}
                onClose={() => setRevertModal(null)}
                onConfirm={handleRevert}
                title="Cofnij akcję?"
                actionType={revertModal?.action_type}
                entity={revertModal?.entity_id}
                reason="Akcja zostanie cofnięta do poprzedniego stanu"
                isLoading={reverting}
            />
        </div>
    );
}
```

---

## 🔴 F-01c: Utwórz pages/Alerts.jsx

**Priorytet:** KRYTYCZNY
**Wymóg:** Technical_Spec §3.6, PRD Feature 7

```jsx
// frontend/src/pages/Alerts.jsx
import { useState, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import { getAnomalies, resolveAnomaly } from '../api';
import EmptyState from '../components/EmptyState';
import PriorityBadge from '../components/PriorityBadge';
import { Bell, CheckCircle } from 'lucide-react';

export default function Alerts() {
    const { selectedClientId, setAlertCount } = useApp();
    const [tab, setTab] = useState('unresolved');
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAlerts = async () => {
        if (!selectedClientId) return;
        setLoading(true);
        try {
            const data = await getAnomalies(selectedClientId, tab);
            setAlerts(data || []);
            if (tab === 'unresolved') setAlertCount(data?.length || 0);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAlerts(); }, [selectedClientId, tab]);

    const handleResolve = async (alertId) => {
        await resolveAnomaly(alertId, selectedClientId);
        fetchAlerts();
    };

    if (!selectedClientId) return <EmptyState message="Wybierz klienta" />;

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold text-app-text mb-6">Alerty</h1>

            {/* Tabs */}
            <div className="flex gap-2 mb-6">
                {['unresolved', 'resolved'].map(t => (
                    <button
                        key={t}
                        onClick={() => setTab(t)}
                        className={`px-4 py-2 text-sm rounded-lg ${
                            tab === t ? 'bg-app-accent text-white' : 'bg-white/5 text-app-muted hover:text-app-text'
                        }`}
                    >
                        {t === 'unresolved' ? `Nierozwiązane (${alerts.length})` : 'Rozwiązane'}
                    </button>
                ))}
            </div>

            {/* Alert list */}
            {alerts.length === 0 ? (
                <EmptyState
                    message={tab === 'unresolved' ? 'Brak alertów — wszystko OK!' : 'Brak rozwiązanych alertów'}
                    icon={Bell}
                />
            ) : (
                <div className="grid gap-4">
                    {alerts.map(alert => (
                        <div key={alert.id} className="p-4 rounded-lg border border-white/10 bg-app-card">
                            <div className="flex items-start justify-between">
                                <div>
                                    <div className="flex items-center gap-2 mb-2">
                                        <PriorityBadge priority={alert.severity} />
                                        <span className="text-xs text-app-muted uppercase">{alert.alert_type}</span>
                                    </div>
                                    <h3 className="font-medium text-app-text mb-1">{alert.title}</h3>
                                    <p className="text-sm text-app-muted">{alert.description}</p>
                                </div>
                                {tab === 'unresolved' && (
                                    <button
                                        onClick={() => handleResolve(alert.id)}
                                        className="flex items-center gap-1 px-3 py-1.5 text-xs bg-green-500/20 text-green-300 rounded-lg hover:bg-green-500/30"
                                    >
                                        <CheckCircle className="w-3 h-3" /> Rozwiąż
                                    </button>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 4: NAPRAWA ISTNIEJĄCYCH (F-09 → F-15)
# Sidebar, Recommendations, hardcoded values, język
# ═══════════════════════════════════════════════════════

## 🟠 F-09: Napraw Sidebar

**Wymóg:** Technical_Spec §2.2

Dodaj do Sidebar:
1. **Client dropdown** na dole (zamiast hardcoded "Demo Meble Sp. z o.o.")
2. **Sync button** + last synced timestamp
3. **Alert badge** przy linku "Alerty"

```jsx
// W Sidebar.jsx — na dole:
import { useApp } from '../contexts/AppContext';
import { useClients } from '../hooks/useClients';
import { useAlerts } from '../hooks/useAlerts';

const { selectedClientId, setSelectedClientId, alertCount } = useApp();
const { clients } = useClients();

// Client dropdown:
<select
    value={selectedClientId || ''}
    onChange={(e) => setSelectedClientId(Number(e.target.value))}
    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-app-text"
>
    <option value="">Wybierz klienta...</option>
    {clients.map(c => (
        <option key={c.id} value={c.id}>{c.name}</option>
    ))}
</select>

// Alert badge przy linku Alerty:
{alertCount > 0 && (
    <span className="ml-auto bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full">
        {alertCount}
    </span>
)}
```

---

## 🟠 F-10: Napraw Recommendations.jsx

**Wymóg:** Technical_Spec §3.4, PRD Feature 2+3

Dodaj:
1. **Przycisk Dismiss** na każdej rekomendacji
2. **dry_run preview** przed Apply (wywołaj z `dry_run=true` najpierw)
3. **ConfirmationModal** z danymi z dry_run preview
4. Użyj `useRecommendations` hook zamiast inline fetch

Flow po kliknięciu Apply:
```
1. User klika "Zastosuj"
2. Frontend wywołuje: POST /recommendations/{id}/apply?dry_run=true
3. Backend zwraca preview: {status: "dry_run", current_val, new_val, action}
4. Frontend otwiera ConfirmationModal z tymi danymi
5. User klika "Potwierdź"
6. Frontend wywołuje: POST /recommendations/{id}/apply?dry_run=false
7. Backend wykonuje akcję → loguje do action_log
8. Frontend pokazuje Toast "Akcja wykonana"
```

---

## 🟡 F-13: Zamień WSZYSTKIE hardcoded clientId

Po F-05 (AppContext) — zamień w KAŻDYM pliku:

```javascript
// PLIKI DO ZMIANY:
// Dashboard.jsx, Keywords.jsx, SearchTerms.jsx, Settings.jsx,
// Campaigns.jsx, Recommendations.jsx + wszystkie nowe strony

// ZAMIAST:
const clientId = 1;

// POWINNO BYĆ:
const { selectedClientId } = useApp();
if (!selectedClientId) return <EmptyState message="Wybierz klienta w sidebarze" />;
```

---

## 🟡 F-14: Ujednolicenie języka → POLSKI

Cały UI powinien być po polsku (użytkownik docelowy = polski specjalista Google Ads).

| Obecne (mieszane) | Docelowe (PL) |
|---|---|
| "Apply" | "Zastosuj" |
| "Applying..." | "Wykonuję..." |
| "Dismiss" | "Odrzuć" |
| "Search Terms" (sidebar) | "Wyszukiwane frazy" |
| "Campaigns" (sidebar) | "Kampanie" |
| "Keywords" (sidebar) | "Słowa kluczowe" |
| "Recommendations" | "Rekomendacje" |
| "Action History" | "Historia akcji" |
| "Dashboard" | "Pulpit" |
| "Settings" | "Ustawienia" |
| "Alerts" | "Alerty" |
| "Clients" | "Klienci" |

---

## 🟡 F-15: Waluta → PLN (zł) zamiast $

SearchTerms i inne strony wyświetlają `$` zamiast `zł`.

```javascript
// helper do formatowania kwot:
export function formatCurrency(amount) {
    return new Intl.NumberFormat('pl-PL', {
        style: 'currency',
        currency: 'PLN',
    }).format(amount);
}

// Użycie:
formatCurrency(15.50)  // "15,50 zł"
```

**UWAGA:** Backend zwraca wartości w USD (micros / 1M). Jeśli klient ma konto w PLN — waluta powinna być konfigurowalna (pole `currency` w modelu `Client`). Na MVP zakładamy PLN.

---

## 🟠 F-11: Napraw vite.config.js proxy

**Stan obecny:**
```javascript
proxy: { '/api': { target: 'http://127.0.0.1:8000' } }
```

**Wymagane:** Dopasuj do aktualnych endpointów backendu. Sprawdź czy backend ma prefix `/api/v1` czy nie.

Jeśli backend NIE MA prefixu:
```javascript
proxy: {
    '/auth': { target: 'http://127.0.0.1:8000' },
    '/clients': { target: 'http://127.0.0.1:8000' },
    '/campaigns': { target: 'http://127.0.0.1:8000' },
    '/keywords': { target: 'http://127.0.0.1:8000' },
    '/search-terms': { target: 'http://127.0.0.1:8000' },
    '/recommendations': { target: 'http://127.0.0.1:8000' },
    '/actions': { target: 'http://127.0.0.1:8000' },
    '/analytics': { target: 'http://127.0.0.1:8000' },
    '/health': { target: 'http://127.0.0.1:8000' },
}
```

Jeśli backend MA prefix `/api/v1`:
```javascript
proxy: { '/api/v1': { target: 'http://127.0.0.1:8000' } }
```

---

## 🟠 F-12: Kolory Tailwind — dodaj aliasy app-*

Technical_Spec §5.2 definiuje kolory app-*. Obecny `tailwind.config.js` używa brand/surface.

**Poprawka:** Zachowaj obecne + dodaj aliasy:
```javascript
// tailwind.config.js
colors: {
    // Obecne (zachowaj):
    brand: { ... },
    surface: { ... },
    // DODAJ aliasy z Technical_Spec:
    'app-bg': '#0F172A',
    'app-sidebar': '#1E293B',
    'app-card': '#334155',
    'app-text': '#F1F5F9',
    'app-muted': '#94A3B8',
    'app-accent': '#3B82F6',
    'app-success': '#10B981',
    'app-warning': '#F59E0B',
    'app-danger': '#EF4444',
}
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ C: PLAN SPRINTÓW (KOLEJNOŚĆ WYKONANIA)
# ═══════════════════════════════════════════════════════

## Sprint 1: Fundament (NAJPIERW)

```
 1. F-16: npm install axios @tanstack/react-table
 2. F-06: Przepisz api.js na Axios (kontrakt API z początku dokumentu)
 3. F-05: Utwórz contexts/AppContext.jsx (selectedClientId + alertCount)
 4. F-04: Utwórz hooks/ (useClients, useToast, useSync, useAlerts, useRecommendations)
 5. F-12: Dodaj kolory app-* do tailwind.config.js
```

**Test po Sprint 1:** Apka się kompiluje (`npm run dev`), importy nie padają

## Sprint 2: Komponenty

```
 6. F-03: Utwórz components/Toast.jsx + podłącz w App.jsx
 7. F-02: Utwórz components/ConfirmationModal.jsx
 8. F-07: Utwórz components/DataTable.jsx (TanStack Table)
 9. F-08: Utwórz SegmentBadge, PriorityBadge, SyncButton, EmptyState
```

**Test po Sprint 2:** Komponenty renderują się w izolacji (no errors w konsoli)

## Sprint 3: Brakujące strony

```
10. F-01a: Utwórz pages/Clients.jsx (lista + sync + selektor)
11. F-01b: Utwórz pages/ActionHistory.jsx (tabela + Undo + ConfirmationModal)
12. F-01c: Utwórz pages/Alerts.jsx (Unresolved/Resolved tabs)
13. Dodaj nowe routes w App.jsx: /clients, /action-history, /alerts
14. Dodaj linki w Sidebar.jsx do nowych stron
```

**Test po Sprint 3:** Nowe strony otwierają się, fetchują dane z API

## Sprint 4: Naprawa istniejących

```
15. F-09: Napraw Sidebar (client dropdown, sync button, alert badge)
16. F-10: Napraw Recommendations.jsx (Dismiss, dry_run, ConfirmationModal)
17. F-13: Zamień hardcoded clientId=1 na useApp() w KAŻDEJ stronie
18. F-14: Ujednolicić UI na język polski
19. F-15: Zmień walutę na PLN (zł)
20. F-11: Napraw vite.config.js proxy
```

**Test po Sprint 4:** Pełna apka działa end-to-end z backendem

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ D: PLIKI DO UTWORZENIA / ZMODYFIKOWANIA
# ═══════════════════════════════════════════════════════

## NOWE pliki (do utworzenia)

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

**Razem: 17 nowych plików**

## Pliki do CIĘŻKIEJ EDYCJI

```
frontend/src/api.js                    → PRZEPISAĆ na Axios (F-06)
frontend/src/App.jsx                   → AppProvider + Toast + nowe routes
frontend/src/components/Sidebar.jsx    → Client dropdown, sync, alert badge
frontend/src/pages/Recommendations.jsx → Dismiss, dry_run, ConfirmationModal
frontend/src/pages/Dashboard.jsx       → useApp() zamiast clientId=1
frontend/src/pages/Keywords.jsx        → useApp() + DataTable
frontend/src/pages/SearchTerms.jsx     → useApp() + SegmentBadge + PLN
```

## Pliki do LEKKIEJ EDYCJI

```
frontend/src/pages/Campaigns.jsx       → useApp() zamiast clientId=1
frontend/src/pages/Settings.jsx        → useApp() zamiast clientId=1
frontend/vite.config.js                → proxy endpoints
frontend/tailwind.config.js            → dodaj app-* kolory
frontend/package.json                  → (auto po npm install)
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ E: PODSUMOWANIE PRIORYTETÓW
# ═══════════════════════════════════════════════════════

| Priorytet | Ilość | ID | Opis |
|-----------|-------|----|------|
| 🔴 Krytyczny | 5 | F-01, F-02, F-03, F-04, F-05 | Brakujące strony, ConfirmationModal, Toast, hooks, global state |
| 🟠 Poważny | 7 | F-06→F-12 | Axios, DataTable, komponenty, Sidebar, Recommendations, proxy, kolory |
| 🟡 Średni | 4 | F-13→F-16 | hardcoded clientId, język PL, waluta PLN, axios package |
| **RAZEM** | **16** | | |

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ F: CHECKLIST WERYFIKACJI
# ═══════════════════════════════════════════════════════

### Fundament
- [ ] `npm install` przechodzi bez błędów
- [ ] `npm run dev` uruchamia devserver bez błędów
- [ ] Axios zaimportowany, api.js przepisany
- [ ] AppContext działa — selectedClientId persystowany w localStorage
- [ ] Wszystkie 5 hooks istnieją i importują się

### Komponenty
- [ ] ConfirmationModal otwiera się z before/after preview
- [ ] Toast pojawia się i znika po 3s (auto-dismiss)
- [ ] DataTable renderuje dane z sortowaniem i paginacją
- [ ] SegmentBadge, PriorityBadge, SyncButton, EmptyState renderują się poprawnie

### Strony
- [ ] /clients — lista klientów, kliknięcie wybiera klienta
- [ ] /action-history — tabela akcji, Undo działa (< 24h, SUCCESS, nie ADD_NEGATIVE)
- [ ] /alerts — zakładki Unresolved/Resolved, "Rozwiąż" działa

### Naprawa istniejących
- [ ] Sidebar ma client dropdown + alert badge
- [ ] Recommendations ma Dismiss + dry_run preview + ConfirmationModal
- [ ] ZERO hardcoded `clientId = 1` w kodzie
- [ ] Cały UI po polsku (żadnego "Apply", "Dismiss" po angielsku)
- [ ] Kwoty wyświetlane w PLN (zł), nie $
- [ ] Proxy w vite.config odpowiada endpointom backendu

### End-to-end
- [ ] Wybierz klienta → Dashboard ładuje KPI
- [ ] Sync → dane odświeżone
- [ ] Recommendations → dry_run → Confirm → Toast "Zastosuj"
- [ ] Action History → widać nową akcję → Undo → cofnięte
- [ ] Alerts → nowy alert po sync → "Rozwiąż" → przeniesione do Resolved

---

**KONIEC PLANU NAPRAWCZEGO FRONTENDU**
**Rozpocznij od Sprint 1 krok 1: npm install axios @tanstack/react-table**