# Technical Specification v1.0
## Google Ads Helper — Frontend + API Contract

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
├── main.jsx              # ReactDOM.createRoot, BrowserRouter
├── App.jsx               # Layout (Sidebar + main content area) + Routes
├── api.js                # Axios instance, interceptors, error handling
├── index.css             # Tailwind imports + custom dark theme
│
├── components/           # Reusable UI components
│   ├── Sidebar.jsx       # Navigation sidebar with route links + alert badge
│   ├── KPICard.jsx       # Metric card: value, label, trend arrow, % change
│   ├── Charts.jsx        # Recharts wrappers: SpendChart, ConversionsChart, CTRChart
│   ├── DataTable.jsx     # TanStack Table wrapper with sorting, filtering, pagination
│   ├── ConfirmationModal.jsx  # Before/After preview modal for actions
│   ├── Toast.jsx         # Success/Error notifications (auto-dismiss)
│   ├── SegmentBadge.jsx  # Color-coded badge (GREEN/RED/ORANGE/GRAY)
│   ├── PriorityBadge.jsx # HIGH (red) / MEDIUM (amber) badge
│   ├── StatusBadge.jsx   # ENABLED/PAUSED/REMOVED badges
│   ├── SyncButton.jsx    # Refresh button with loading spinner
│   ├── EmptyState.jsx    # "No data" placeholder with icon
│   └── LoadingSpinner.jsx
│
├── pages/
│   ├── Dashboard.jsx     # Multi-client overview + client drilldown
│   ├── Clients.jsx       # Client list, add client, sync all
│   ├── Campaigns.jsx     # Campaign table per selected client
│   ├── Keywords.jsx      # Keyword table with QS badges, performance
│   ├── SearchTerms.jsx   # Segment cards (4) + filterable term list
│   ├── Recommendations.jsx # Priority-sorted list, Apply/Dismiss buttons
│   ├── ActionHistory.jsx # Chronological action log + Undo button
│   ├── Alerts.jsx        # Unresolved/Resolved tabs
│   └── Settings.jsx      # OAuth status, connected accounts
│
└── hooks/
    ├── useClients.js     # Fetch/cache client list, selected client state
    ├── useRecommendations.js  # Fetch recs, apply, dismiss
    ├── useSync.js        # Trigger sync, track progress
    ├── useAlerts.js      # Fetch alert count for sidebar badge
    └── useToast.js       # Toast notification state
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
- `selectedClientId` — currently selected client (persisted in localStorage)
- `isAuthenticated` — OAuth status
- `alertCount` — for sidebar badge

**Local state** (via useState in each page):
- Table filters, sorting, pagination
- Modal open/close
- Form inputs

**No Redux/Zustand needed.** See DECISIONS.md ADR-009.

---

# SECTION 2: COMPONENT SPECIFICATIONS

## 2.1 Layout (App.jsx)

```
┌─────────────────────────────────────────────────────┐
│  SIDEBAR (240px)  │        MAIN CONTENT              │
│                   │                                   │
│  🏠 Dashboard     │   [Page Header + Breadcrumb]      │
│  👥 Clients       │                                   │
│  📊 Campaigns     │   [Page Content]                  │
│  🔤 Keywords      │                                   │
│  🔍 Search Terms  │                                   │
│  💡 Recommendations│                                  │
│  📜 History       │                                   │
│  🔔 Alerts (3)    │                                   │
│  ⚙️ Settings      │                                   │
│                   │                                   │
│  ── Client ──     │                                   │
│  [Dropdown]       │                                   │
│  Last sync: 2h ago│                                   │
│  [🔄 Sync]        │                                   │
└─────────────────────────────────────────────────────┘
```

- Sidebar always visible (no collapse for MVP)
- Client selector dropdown at bottom of sidebar
- Sync button + last synced timestamp in sidebar
- Alert count badge next to 🔔 Alerts link

## 2.2 Sidebar.jsx

**Props:** none (uses context for selectedClient, alertCount)

**Elements:**
- Logo/title: "Google Ads Helper"
- Navigation links (NavLink from react-router-dom, active state highlighted)
- Client dropdown: shows all clients, selecting one updates context
- Sync button: triggers POST /clients/{id}/sync, shows spinner while syncing
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
┌──────────────────────────────────┐
│  ⚠️  Pause Keyword?              │
│                                  │
│  Entity: 'nike shoes'            │
│  Campaign: Brand Campaign        │
│                                  │
│  ┌────────────┬───────────────┐  │
│  │   BEFORE   │    AFTER      │  │
│  │ ENABLED    │  PAUSED       │  │
│  │ Bid: $1.50 │  Bid: $1.50   │  │
│  └────────────┴───────────────┘  │
│                                  │
│  Reason: High spend ($50)...     │
│                                  │
│        [Cancel]  [✓ Apply]       │
└──────────────────────────────────┘
```

## 2.6 SegmentBadge.jsx

**Props:** `{ segment: "HIGH_PERFORMER" | "WASTE" | "IRRELEVANT" | "OTHER" }`

**Colors:**
- HIGH_PERFORMER → green-500 bg, green-900 text, label "High Performer"
- WASTE → red-500 bg, red-900 text, label "Waste"
- IRRELEVANT → amber-500 bg, amber-900 text, label "Irrelevant"
- OTHER → slate-500 bg, slate-300 text, label "Other"

## 2.7 Toast.jsx

**Types:** success (green), error (red), warning (amber), info (blue)
**Auto-dismiss:** 5 seconds (success), 10 seconds (error), manual dismiss button
**Position:** Top-right, stacked

---

# SECTION 3: PAGE SPECIFICATIONS

## 3.1 Dashboard.jsx

**API calls:**
- `GET /analytics/kpis?client_id=X` → KPI cards
- `GET /analytics/campaigns?client_id=X` → campaign breakdown table
- `GET /recommendations/summary?client_id=X` → badge counts
- `GET /analytics/anomalies?client_id=X&status=unresolved` → alert count

**Layout:**
1. **Top row:** 4 KPI cards (Spend, Conversions, CPA, CTR)
2. **Middle:** Campaign breakdown table (name, status, budget, spend, conversions, CTR, CPA)
3. **Bottom row:** Quick links
   - Recommendations badge: "25 HIGH, 10 MEDIUM pending" → link to /recommendations
   - Alerts badge: "3 unresolved alerts" → link to /alerts

## 3.2 Clients.jsx

**API calls:**
- `GET /clients` → client list
- `POST /clients/{id}/sync` → trigger sync

**Layout:**
- Table: Client name, Customer ID, Last synced, Status, Actions
- Actions column: [Sync] button per client
- Add client form (simple: name + Google Ads Customer ID + optional MCC ID)

## 3.3 SearchTerms.jsx — KEY PAGE

**API calls:**
- `GET /search-terms/segmented?client_id=X` → segments + stats

**Layout:**

**Top: 4 Segment Cards**
```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 🟢 HIGH PERF │ │ 🔴 WASTE     │ │ 🟠 IRRELEVANT│ │ ⚪ OTHER     │
│    45 terms  │ │   120 terms  │ │    30 terms  │ │   800 terms  │
│ $1,234 spend │ │ $5,678 waste │ │ $890 spend   │ │ $12,345      │
│ 89 conv      │ │ 0 conv       │ │ 2 conv       │ │ 45 conv      │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**Clicking a card filters the table below to that segment.**

**Bottom: Filterable Table**
- Columns: Query Text, Clicks, Cost ($), Conversions, CTR%, CVR%, Segment Badge, Action
- Action buttons:
  - HIGH_PERFORMER → "Add as Keyword" (green button)
  - WASTE → "Add as Negative" (red button)
  - IRRELEVANT → "Add as Negative" (red button)
  - OTHER → no action
- Clicking action → ConfirmationModal → POST /recommendations/{id}/apply

## 3.4 Recommendations.jsx

**API calls:**
- `GET /recommendations?client_id=X&status=pending` → recommendation list
- `POST /recommendations/{id}/apply?client_id=X` → apply
- `POST /recommendations/{id}/dismiss` → dismiss

**Layout:**
- Filter tabs: [All] [HIGH] [MEDIUM]
- List of RecommendationCards:
  ```
  ┌─────────────────────────────────────────────────────┐
  │ [HIGH] PAUSE_KEYWORD                                │
  │                                                     │
  │ Keyword: "nike shoes free"                          │
  │ Campaign: Brand Campaign                            │
  │                                                     │
  │ Reason: Spent $50 with 0 conversions (30 clicks)    │
  │                                                     │
  │                    [Dismiss]  [✓ Apply]              │
  └─────────────────────────────────────────────────────┘
  ```
- Apply → ConfirmationModal → executes → Toast success/error
- Dismiss → marks as dismissed, removes from list
- Summary at top: "25 HIGH, 10 MEDIUM recommendations pending"

## 3.5 ActionHistory.jsx

**API calls:**
- `GET /actions/?client_id=X&limit=50&offset=0`
- `POST /actions/revert/{action_log_id}?client_id=X` → undo

**Layout:**
- Chronological table (newest first)
- Columns: Timestamp, Action Type, Entity, Before→After, Status, Actions
- Status badges: SUCCESS (green), FAILED (red), REVERTED (gray)
- Undo button: visible only if status=SUCCESS AND age < 24h AND type ≠ ADD_NEGATIVE
- Clicking Undo → ConfirmationModal → POST revert → Toast

## 3.6 Alerts.jsx

**API calls:**
- `GET /analytics/anomalies?client_id=X&status=unresolved`
- `POST /analytics/anomalies/{alert_id}/resolve?client_id=X`

**Layout:**
- Tabs: [Unresolved (3)] [Resolved]
- Alert cards:
  ```
  ┌─────────────────────────────────────────────────────┐
  │ [HIGH] SPEND_SPIKE                    2 hours ago   │
  │                                                     │
  │ Campaign 'Brand' has disproportionate spend:        │
  │ $5,678 total (30d) vs expected $2,000.              │
  │ Review budget settings.                             │
  │                                                     │
  │                              [Mark as Reviewed ✓]   │
  └─────────────────────────────────────────────────────┘
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

# SECTION 6: BACKEND ↔ FRONTEND INTEGRATION

## 6.1 Production Mode (PyWebView)

FastAPI serves the React build as static files:

```python
# backend/app/main.py — add after router registration
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
# → opens http://localhost:5173, proxies API calls to :8000
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

**END OF TECHNICAL SPECIFICATION**

This document + Implementation_Blueprint.md + Blueprint_Patch_v2_1.md = complete source of truth for implementation.
