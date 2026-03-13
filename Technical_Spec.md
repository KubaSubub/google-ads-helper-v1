> [!IMPORTANT]
> 2026-03-12 update:
> - Keyword API now returns `campaign_id`, `campaign_name`, `ad_group_name`, and uses keyword `status` as the primary lifecycle field.
> - `serving_status` is now presentation-only helper data for delivery issues.
> - Runtime SQLite path is canonicalized to `<repo>/data/google_ads_app.db` in source mode, with one-time migration from legacy `backend/data/` if needed.
> - Hard reset endpoint keeps the client profile but wipes only that client's local runtime cache after explicit typed-name confirmation in Settings.

> [!WARNING]
> LEGACY DOCUMENT NOTICE
> This file is a historical snapshot from 2025-02-17 and is not the active Source of Truth.
> Active SoT: `docs/SOURCE_OF_TRUTH.md` and `docs/API_ENDPOINTS.md`.
># Technical Specification v1.0
## Google Ads Helper â€” Frontend + API Contract

**Version:** 1.0
**Date:** 2025-02-17
**Status:** Source of Truth for Frontend Development
**Complements:** Implementation_Blueprint.md (backend) + Blueprint_Patch_v2_1.md

---

# SECTION 1: FRONTEND ARCHITECTURE

## 1.1 Stack

```
React 18.2 + Vite 5
React Router 6 (client-side routing)
Tailwind CSS 3.4 (dark mode, utility-first)
Recharts 2.12 (charts)
@tanstack/react-table 8 (data tables)
Axios (HTTP client)
lucide-react (icons)
```

## 1.2 Project Structure

```
frontend/src/
â”śâ”€â”€ main.jsx              # ReactDOM.createRoot, BrowserRouter
â”śâ”€â”€ App.jsx               # Layout (Sidebar + main content area) + Routes
â”śâ”€â”€ api.js                # Axios instance, interceptors, error handling
â”śâ”€â”€ index.css             # Tailwind imports + custom dark theme
â”‚
â”śâ”€â”€ components/           # Reusable UI components
â”‚   â”śâ”€â”€ Sidebar.jsx       # Navigation sidebar with route links + alert badge
â”‚   â”śâ”€â”€ KPICard.jsx       # Metric card: value, label, trend arrow, % change
â”‚   â”śâ”€â”€ Charts.jsx        # Recharts wrappers: SpendChart, ConversionsChart, CTRChart
â”‚   â”śâ”€â”€ DataTable.jsx     # TanStack Table wrapper with sorting, filtering, pagination
â”‚   â”śâ”€â”€ ConfirmationModal.jsx  # Before/After preview modal for actions
â”‚   â”śâ”€â”€ Toast.jsx         # Success/Error notifications (auto-dismiss)
â”‚   â”śâ”€â”€ SegmentBadge.jsx  # Color-coded badge (GREEN/RED/ORANGE/GRAY)
â”‚   â”śâ”€â”€ PriorityBadge.jsx # HIGH (red) / MEDIUM (amber) badge
â”‚   â”śâ”€â”€ StatusBadge.jsx   # ENABLED/PAUSED/REMOVED badges
â”‚   â”śâ”€â”€ SyncButton.jsx    # Refresh button with loading spinner
â”‚   â”śâ”€â”€ EmptyState.jsx    # "No data" placeholder with icon
â”‚   â””â”€â”€ LoadingSpinner.jsx
â”‚
â”śâ”€â”€ pages/
â”‚   â”śâ”€â”€ Dashboard.jsx     # Multi-client overview + client drilldown
â”‚   â”śâ”€â”€ Clients.jsx       # Client list, add client, sync all
â”‚   â”śâ”€â”€ Campaigns.jsx     # Campaign table per selected client
â”‚   â”śâ”€â”€ Keywords.jsx      # Keyword table with QS badges, performance
â”‚   â”śâ”€â”€ SearchTerms.jsx   # Segment cards (4) + filterable term list
â”‚   â”śâ”€â”€ Recommendations.jsx # Priority-sorted list, Apply/Dismiss buttons
â”‚   â”śâ”€â”€ ActionHistory.jsx # Chronological action log + Undo button
â”‚   â”śâ”€â”€ Alerts.jsx        # Unresolved/Resolved tabs
â”‚   â””â”€â”€ Settings.jsx      # OAuth status, connected accounts
â”‚
â””â”€â”€ hooks/
    â”śâ”€â”€ useClients.js     # Fetch/cache client list, selected client state
    â”śâ”€â”€ useRecommendations.js  # Fetch recs, apply, dismiss
    â”śâ”€â”€ useSync.js        # Trigger sync, track progress
    â”śâ”€â”€ useAlerts.js      # Fetch alert count for sidebar badge
    â””â”€â”€ useToast.js       # Toast notification state
```

## 1.3 Routing

```jsx
// App.jsx routes
<Routes>
  <Route path="/" element={<Dashboard />} />
  <Route path="/clients" element={<Clients />} />
  <Route path="/campaigns" element={<Campaigns />} />
  <Route path="/keywords" element={<Keywords />} />
  <Route path="/search-terms" element={<SearchTerms />} />
  <Route path="/recommendations" element={<Recommendations />} />
  <Route path="/history" element={<ActionHistory />} />
  <Route path="/alerts" element={<Alerts />} />
  <Route path="/settings" element={<Settings />} />
</Routes>
```

## 1.4 State Management

**Global state** (via React Context):
- `selectedClientId` â€” currently selected client (persisted in localStorage)
- `isAuthenticated` â€” OAuth status
- `alertCount` â€” for sidebar badge

**Local state** (via useState in each page):
- Table filters, sorting, pagination
- Modal open/close
- Form inputs

**No Redux/Zustand needed.** See DECISIONS.md ADR-009.

---

# SECTION 2: COMPONENT SPECIFICATIONS

## 2.1 Layout (App.jsx)

```
â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  SIDEBAR (240px)  â”‚        MAIN CONTENT              â”‚
â”‚                   â”‚                                   â”‚
â”‚  đźŹ  Dashboard     â”‚   [Page Header + Breadcrumb]      â”‚
â”‚  đź‘Ą Clients       â”‚                                   â”‚
â”‚  đź“Š Campaigns     â”‚   [Page Content]                  â”‚
â”‚  đź”¤ Keywords      â”‚                                   â”‚
â”‚  đź”Ť Search Terms  â”‚                                   â”‚
â”‚  đź’ˇ Recommendationsâ”‚                                  â”‚
â”‚  đź“ś History       â”‚                                   â”‚
â”‚  đź”” Alerts (3)    â”‚                                   â”‚
â”‚  âš™ď¸Ź Settings      â”‚                                   â”‚
â”‚                   â”‚                                   â”‚
â”‚  â”€â”€ Client â”€â”€     â”‚                                   â”‚
â”‚  [Dropdown]       â”‚                                   â”‚
â”‚  Last sync: 2h agoâ”‚                                   â”‚
â”‚  [đź”„ Sync]        â”‚                                   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
```

- Sidebar always visible (no collapse for MVP)
- Client selector dropdown at bottom of sidebar
- Sync button + last synced timestamp in sidebar
- Alert count badge next to đź”” Alerts link

## 2.2 Sidebar.jsx

**Props:** none (uses context for selectedClient, alertCount)

**Elements:**
- Logo/title: "Google Ads Helper"
- Navigation links (NavLink from react-router-dom, active state highlighted)
- Client dropdown: shows all clients, selecting one updates context
- Sync button: triggers POST /sync/trigger?client_id={id}&days=30, shows spinner while syncing
- Last synced: relative time ("2 hours ago", "Never")
- Alert badge: red circle with count if > 0

## 2.3 KPICard.jsx

**Props:**
```typescript
{
  label: string           // "Total Spend"
  value: string           // "$12,345.67"
  previousValue?: string  // "$11,200.00" (for comparison)
  changePercent?: number  // 10.2 or -5.3
  icon?: ReactNode        // lucide icon
  format?: "currency" | "number" | "percent"
}
```

**Display:**
- Large value text
- Label below
- Arrow up (green) or down (red) with % change
- Icon top-right

## 2.4 DataTable.jsx (TanStack Table wrapper)

**Props:**
```typescript
{
  data: any[]
  columns: ColumnDef[]
  searchable?: boolean      // Show search input
  searchPlaceholder?: string
  pageSize?: number         // Default 25
  onRowClick?: (row) => void
  emptyMessage?: string
}
```

**Features:**
- Column sorting (click header)
- Global search filter
- Pagination (previous/next + page numbers)
- Responsive: horizontal scroll on overflow

## 2.5 ConfirmationModal.jsx

**Props:**
```typescript
{
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string             // "Pause Keyword?"
  actionType: string        // "PAUSE_KEYWORD"
  entity: string            // "'nike shoes' in Campaign X"
  beforeState: object       // { status: "ENABLED", bid: "$1.50" }
  afterState: object        // { status: "PAUSED" }
  reason: string            // "High spend ($50) with 0 conversions"
  isLoading: boolean        // Show spinner on confirm button
}
```

**Layout:**
```
â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  âš ď¸Ź  Pause Keyword?              â”‚
â”‚                                  â”‚
â”‚  Entity: 'nike shoes'            â”‚
â”‚  Campaign: Brand Campaign        â”‚
â”‚                                  â”‚
â”‚  â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚   BEFORE   â”‚    AFTER      â”‚  â”‚
â”‚  â”‚ ENABLED    â”‚  PAUSED       â”‚  â”‚
â”‚  â”‚ Bid: $1.50 â”‚  Bid: $1.50   â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚                                  â”‚
â”‚  Reason: High spend ($50)...     â”‚
â”‚                                  â”‚
â”‚        [Cancel]  [âś“ Apply]       â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
```

## 2.6 SegmentBadge.jsx

**Props:** `{ segment: "HIGH_PERFORMER" | "WASTE" | "IRRELEVANT" | "OTHER" }`

**Colors:**
- HIGH_PERFORMER â†’ green-500 bg, green-900 text, label "High Performer"
- WASTE â†’ red-500 bg, red-900 text, label "Waste"
- IRRELEVANT â†’ amber-500 bg, amber-900 text, label "Irrelevant"
- OTHER â†’ slate-500 bg, slate-300 text, label "Other"

## 2.7 Toast.jsx

**Types:** success (green), error (red), warning (amber), info (blue)
**Auto-dismiss:** 5 seconds (success), 10 seconds (error), manual dismiss button
**Position:** Top-right, stacked

---

# SECTION 3: PAGE SPECIFICATIONS

## 3.1 Dashboard.jsx

**API calls:**
- `GET /analytics/kpis?client_id=X` â†’ KPI cards
- `GET /analytics/campaigns?client_id=X` â†’ campaign breakdown table
- `GET /recommendations/summary?client_id=X` â†’ badge counts
- `GET /analytics/anomalies?client_id=X&status=unresolved` â†’ alert count

**Layout:**
1. **Top row:** 4 KPI cards (Spend, Conversions, CPA, CTR)
2. **Middle:** Campaign breakdown table (name, status, budget, spend, conversions, CTR, CPA)
3. **Bottom row:** Quick links
   - Recommendations badge: "25 HIGH, 10 MEDIUM pending" â†’ link to /recommendations
   - Alerts badge: "3 unresolved alerts" â†’ link to /alerts

## 3.2 Clients.jsx

**API calls:**
- `GET /clients` â†’ client list
- `POST /sync/trigger?client_id={id}&days=30` â†’ trigger sync

**Layout:**
- Table: Client name, Customer ID, Last synced, Status, Actions
- Actions column: [Sync] button per client
- Add client form (simple: name + Google Ads Customer ID + optional MCC ID)

## 3.3 SearchTerms.jsx â€” KEY PAGE

**API calls:**
- `GET /search-terms/segmented?client_id=X` â†’ segments + stats

**Layout:**

**Top: 4 Segment Cards**
```
â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ đźź˘ HIGH PERF â”‚ â”‚ đź”´ WASTE     â”‚ â”‚ đźź  IRRELEVANTâ”‚ â”‚ âšŞ OTHER     â”‚
â”‚    45 terms  â”‚ â”‚   120 terms  â”‚ â”‚    30 terms  â”‚ â”‚   800 terms  â”‚
â”‚ $1,234 spend â”‚ â”‚ $5,678 waste â”‚ â”‚ $890 spend   â”‚ â”‚ $12,345      â”‚
â”‚ 89 conv      â”‚ â”‚ 0 conv       â”‚ â”‚ 2 conv       â”‚ â”‚ 45 conv      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
```

**Clicking a card filters the table below to that segment.**

**Bottom: Filterable Table**
- Columns: Query Text, Clicks, Cost ($), Conversions, CTR%, CVR%, Segment Badge, Action
- Action buttons:
  - HIGH_PERFORMER â†’ "Add as Keyword" (green button)
  - WASTE â†’ "Add as Negative" (red button)
  - IRRELEVANT â†’ "Add as Negative" (red button)
  - OTHER â†’ no action
- Clicking action â†’ ConfirmationModal â†’ POST /recommendations/{id}/apply

## 3.4 Recommendations.jsx

**API calls:**
- `GET /recommendations?client_id=X&status=pending` â†’ recommendation list
- `POST /recommendations/{id}/apply?client_id=X` â†’ apply
- `POST /recommendations/{id}/dismiss` â†’ dismiss

**Layout:**
- Filter tabs: [All] [HIGH] [MEDIUM]
- List of RecommendationCards:
  ```
  â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ [HIGH] PAUSE_KEYWORD                                â”‚
  â”‚                                                     â”‚
  â”‚ Keyword: "nike shoes free"                          â”‚
  â”‚ Campaign: Brand Campaign                            â”‚
  â”‚                                                     â”‚
  â”‚ Reason: Spent $50 with 0 conversions (30 clicks)    â”‚
  â”‚                                                     â”‚
  â”‚                    [Dismiss]  [âś“ Apply]              â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  ```
- Apply â†’ ConfirmationModal â†’ executes â†’ Toast success/error
- Dismiss â†’ marks as dismissed, removes from list
- Summary at top: "25 HIGH, 10 MEDIUM recommendations pending"

## 3.5 ActionHistory.jsx

**API calls:**
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X` â†’ undo

**Layout:**
- Chronological table (newest first)
- Columns: Timestamp, Action Type, Entity, Beforeâ†’After, Status, Actions
- Status badges: SUCCESS (green), FAILED (red), REVERTED (gray)
- Undo button: visible only if status=SUCCESS AND age < 24h AND type â‰  ADD_NEGATIVE
- Clicking Undo â†’ ConfirmationModal â†’ POST revert â†’ Toast

## 3.6 Alerts.jsx

**API calls:**
- `GET /analytics/anomalies?client_id=X&status=unresolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`

**Layout:**
- Tabs: [Unresolved (3)] [Resolved]
- Alert cards:
  ```
  â”Śâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  â”‚ [HIGH] SPEND_SPIKE                    2 hours ago   â”‚
  â”‚                                                     â”‚
  â”‚ Campaign 'Brand' has disproportionate spend:        â”‚
  â”‚ $5,678 total (30d) vs expected $2,000.              â”‚
  â”‚ Review budget settings.                             â”‚
  â”‚                                                     â”‚
  â”‚                              [Mark as Reviewed âś“]   â”‚
  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
  ```

---

# SECTION 4: API CLIENT (api.js)

```javascript
// frontend/src/api.js
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,  // 30s (sync can be slow)
  headers: { 'Content-Type': 'application/json' }
});

// Response interceptor: extract data, handle errors
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Unknown error';
    console.error('API Error:', message);
    return Promise.reject({ message, status: error.response?.status });
  }
);

export default api;

// === API Functions ===

// Auth
export const getAuthStatus = () => api.get('/auth/status');
export const getLoginUrl = () => api.get('/auth/login');
export const logout = () => api.post('/auth/logout');

// Clients
export const getClients = () => api.get('/clients');
export const getClient = (id) => api.get(`/clients/${id}`);
export const syncClient = (id) => api.post(`/clients/${id}/sync`);

// Campaigns
export const getCampaigns = (clientId) => api.get('/campaigns', { params: { client_id: clientId } });

// Keywords
export const getKeywords = (campaignId) => api.get('/keywords', { params: { campaign_id: campaignId } });

// Search Terms
export const getSegmentedSearchTerms = (clientId) => api.get('/search-terms/segmented', { params: { client_id: clientId } });
export const getSearchTerms = (clientId, params) => api.get('/search-terms/', { params: { client_id: clientId, ...params } });

// Recommendations
export const getRecommendations = (clientId, params) => api.get('/recommendations', { params: { client_id: clientId, ...params } });
export const getRecommendationsSummary = (clientId) => api.get('/recommendations/summary', { params: { client_id: clientId } });
export const applyRecommendation = (id, clientId, dryRun = false) => api.post(`/recommendations/${id}/apply`, null, { params: { client_id: clientId, dry_run: dryRun } });
export const dismissRecommendation = (id) => api.post(`/recommendations/${id}/dismiss`);

// Actions
export const getActionHistory = (clientId, params) => api.get('/actions/', { params: { client_id: clientId, ...params } });
export const revertAction = (actionLogId, clientId) => api.post(`/actions/revert/${actionLogId}`, null, { params: { client_id: clientId } });

// Analytics
export const getKPIs = (clientId) => api.get('/analytics/kpis', { params: { client_id: clientId } });
export const getCampaignBreakdown = (clientId) => api.get('/analytics/campaigns', { params: { client_id: clientId } });
export const getAnomalies = (clientId, status = 'unresolved') => api.get('/analytics/anomalies', { params: { client_id: clientId, status } });
export const resolveAlert = (alertId, clientId) => api.post(`/analytics/anomalies/${alertId}/resolve`, null, { params: { client_id: clientId } });
export const runAnomalyDetection = (clientId) => api.post('/analytics/detect', null, { params: { client_id: clientId } });
```

---

# SECTION 5: FRONTEND BUILD CONFIG

## 5.1 vite.config.js

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
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
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
});
```

## 5.2 tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Custom dark theme (Linear/Vercel inspired)
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
    },
  },
  plugins: [],
};
```

## 5.3 postcss.config.js

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

## 5.4 index.css

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Dark mode always on */
:root {
  color-scheme: dark;
}

body {
  @apply bg-app-bg text-app-text;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  @apply bg-app-bg;
}
::-webkit-scrollbar-thumb {
  @apply bg-slate-600 rounded;
}
```

---

# SECTION 6: BACKEND â†” FRONTEND INTEGRATION

## 6.1 Production Mode (PyWebView)

FastAPI serves the React build as static files:

```python
# backend/app/main.py â€” add after router registration
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Serve React build in production
frontend_dist = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'dist')
if os.path.isdir(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        """Catch-all: serve React index.html for client-side routing"""
        index = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
```

## 6.2 Development Mode

```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend (Vite dev server with proxy)
cd frontend && npm run dev
# â†’ opens http://localhost:5173, proxies API calls to :8000
```

## 6.3 CORS Configuration

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

# SECTION 7: PYDANTIC SCHEMAS (API Response Shapes)

## 7.1 Common Enums

```python
# backend/app/schemas/common.py
from enum import Enum

class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"

class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"

class ActionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REVERTED = "REVERTED"

class Segment(str, Enum):
    HIGH_PERFORMER = "HIGH_PERFORMER"
    WASTE = "WASTE"
    IRRELEVANT = "IRRELEVANT"
    OTHER = "OTHER"
```

## 7.2 Client Schemas

```python
# backend/app/schemas/client.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ClientRead(BaseModel):
    id: int
    name: str
    google_ads_customer_id: str
    manager_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ClientCreate(BaseModel):
    name: str
    google_ads_customer_id: str
    manager_id: Optional[str] = None
```

## 7.3 Campaign Schemas

```python
# backend/app/schemas/campaign.py
from pydantic import BaseModel, computed_field
from typing import Optional

class CampaignRead(BaseModel):
    id: int
    google_id: str
    name: str
    status: str
    budget_micros: int
    spend_micros: int
    conversions: Optional[float] = 0
    clicks: Optional[int] = 0
    impressions: Optional[int] = 0
    ctr: Optional[float] = 0
    roas: Optional[float] = 0

    @computed_field
    @property
    def budget_usd(self) -> float:
        return round((self.budget_micros or 0) / 1_000_000, 2)

    @computed_field
    @property
    def spend_usd(self) -> float:
        return round((self.spend_micros or 0) / 1_000_000, 2)

    @computed_field
    @property
    def cpa_usd(self) -> float:
        if self.conversions and self.conversions > 0:
            return round(self.spend_usd / self.conversions, 2)
        return 0

    class Config:
        from_attributes = True
```

## 7.4 Recommendation Schemas

```python
# backend/app/schemas/recommendation.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RecommendationRead(BaseModel):
    id: int
    client_id: int
    rule_id: str
    entity_type: str
    entity_id: str
    priority: str
    reason: str
    suggested_action: str  # JSON string
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecommendationSummary(BaseModel):
    high: int
    medium: int
    total: int

class ApplyResult(BaseModel):
    status: str
    action_type: Optional[str] = None
    message: Optional[str] = None
    reason: Optional[str] = None  # If blocked by safety
```

## 7.5 Search Term Schemas

```python
# backend/app/schemas/search_term.py
from pydantic import BaseModel, computed_field
from typing import Optional

class SearchTermRead(BaseModel):
    id: int
    query_text: str
    clicks: int = 0
    impressions: int = 0
    cost_micros: int = 0
    conversions: float = 0
    ctr: Optional[float] = 0
    segment: str = "OTHER"
    campaign_id: Optional[int] = None

    @computed_field
    @property
    def cost_usd(self) -> float:
        return round((self.cost_micros or 0) / 1_000_000, 2)

    @computed_field
    @property
    def cvr_pct(self) -> float:
        if self.clicks and self.clicks > 0:
            return round(self.conversions / self.clicks * 100, 2)
        return 0

    class Config:
        from_attributes = True
```

---

# SECTION 8: DATABASE MODELS (Complete)

All models use BigInteger for monetary values. PRD Section 4.3 REAL types are overridden.

```python
# backend/app/models/client.py
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base
from datetime import datetime

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    google_ads_customer_id = Column(String, nullable=False, unique=True)
    manager_id = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/campaign.py
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    google_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    budget_micros = Column(BigInteger, default=0)       # BigInteger!
    spend_micros = Column(BigInteger, default=0)         # BigInteger!
    conversions = Column(Float, default=0)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0)
    roas = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/keyword.py
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    google_id = Column(String, nullable=False, index=True)
    text = Column(String, nullable=False)
    match_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    bid_micros = Column(BigInteger, default=0)           # BigInteger!
    quality_score = Column(Integer, nullable=True)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)          # BigInteger!
    conversions = Column(Float, default=0)
    ctr = Column(Float, default=0)
    cpa_micros = Column(BigInteger, default=0)           # BigInteger!
    ad_group_id = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/search_term.py
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class SearchTerm(Base):
    __tablename__ = "search_terms"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    query_text = Column(String, nullable=False)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)          # BigInteger!
    conversions = Column(Float, default=0)
    ctr = Column(Float, default=0)
    segment = Column(String, default="OTHER")            # HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/recommendation.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    rule_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=False)      # JSON string
    status = Column(String, default="pending", index=True) # pending, applied, dismissed
    created_at = Column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/models/action_log.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    action_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False)
    old_value_json = Column(Text, nullable=True)
    new_value_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, index=True)  # SUCCESS, FAILED, REVERTED
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    reverted_at = Column(DateTime, nullable=True)        # Set when action is undone
```

```python
# backend/app/models/alert.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.database import Base
from datetime import datetime

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)          # SPEND_SPIKE, CONVERSION_DROP, CTR_DROP
    priority = Column(String, nullable=False)             # HIGH, MEDIUM
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
```

---

## API Contract Addendum (2026-03-13)

- New protected endpoint:
  - `POST /api/v1/clients/{id}/restore-runtime-from-legacy`
  - Optional query param: `source_client_id`
- Purpose: restore local runtime data for one client from legacy SQLite (`backend/data/google_ads_app.db`) into canonical runtime DB (`data/google_ads_app.db`) without mixing data from another live client.
- Response contains source/target metadata plus per-table restored counts.

- New protected endpoint:
  - `POST /api/v1/clients/{id}/seed-demo-showcase`
  - Query params: `days` (14-90), `allow_demo_write`
- Purpose: generate local-only showcase data for DEMO views (RSA ads, recent `keywords_daily`, helper `action_log`, curated `search_terms`) without using data from other clients.
- Seeder adds a small controlled set of zero-conversion spend patterns for presentation quality in `wasted-spend` / Search Optimization cards.
- Constraint: endpoint is DEMO-only (`is_demo_protected_client` gate) and still requires explicit write override.

- DEMO write-lock contract:
  - Settings: `demo_protection_enabled`, `demo_client_id`, `demo_google_customer_id`
  - Default matching uses `demo_google_customer_id`; `demo_client_id` is optional hard pin (`None` by default).
  - Protected write endpoints require explicit `allow_demo_write=true` for DEMO client mutations.
  - Default behavior is hard lock (`423 Locked`) for DEMO writes; reads are unchanged.

- Forecast contract update:
  - `GET /api/v1/analytics/forecast` accepts friendly aliases:
    - `metric=cost` maps to `cost_micros`
    - `metric=cpc` maps to `avg_cpc_micros`
  - Micros metrics are normalized to currency units in forecast response values.

**END OF TECHNICAL SPECIFICATION**

This document + Implementation_Blueprint.md + Blueprint_Patch_v2_1.md = complete source of truth for implementation.




