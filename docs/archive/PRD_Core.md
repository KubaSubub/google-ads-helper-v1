# Product Requirements Document (PRD)
## Google Ads Helper - Core Specification

**Version:** 1.0  
**Last Updated:** 2025-02-16  
**Status:** Approved for Development  
**Owner:** Product Manager (PM)  
**Developer:** AI Assistant (Senior Full-Stack)

---

## 📋 Document Purpose

This PRD defines the **Minimum Viable Product (MVP)** for Google Ads Helper - a local-first desktop application that automates Google Ads optimization tasks, replacing 80% of manual specialist work.

**Target Audience:**
- AI Developer (implementation guide)
- Product Owner (feature validation)
- Future stakeholders (if product scales)

---

# PART 1: PRODUCT VISION

## 1.1 Problem Statement

**Current Reality:**
- Managing 2-10 Google Ads client accounts manually
- Time-consuming tasks: search terms review, bid adjustments, pausing poor performers
- Repetitive decisions that could be automated
- Manual work = "just clicking OK on obvious changes"

**Pain Points:**
1. **Time waste:** Hours spent on routine optimization tasks
2. **Cognitive load:** Remembering what to check for each client
3. **Inconsistency:** Manual process = sometimes miss important changes
4. **Scalability:** More clients = linear time increase

**Current Workarounds:**
- Manual daily/weekly reviews in Google Ads UI
- Spreadsheet tracking (if any)
- Mental checklists of what to optimize

## 1.2 Solution

**Google Ads Helper** = Local desktop application that:
1. **Automates data collection** from Google Ads API
2. **Analyzes performance** using proven optimization rules
3. **Generates recommendations** (pause keywords, add negatives, adjust bids)
4. **Enables 1-click actions** with safety mechanisms (confirmation + rollback)

**Core Value Proposition:**
> "The app that replaces 80% of a Google Ads specialist's routine work, while keeping 100% of data private and local."

## 1.3 Success Metrics

### Primary Metrics (MVP Launch - Month 1)

| Metric | Current State | MVP Target | Measurement |
|--------|--------------|------------|-------------|
| **Time Spent on Optimization** | Variable (hours/week) | <50% current time | Self-reported tracking |
| **Recommendations Generated** | 0 | 20-50 per client/week | System count |
| **Actions Applied** | N/A | 50+ in first month | Action log |
| **System Stability** | N/A | Zero crashes for 7 days | Error logs |

### Secondary Metrics (Month 2-3)

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| **Wasted Spend Reduction** | TBD | -10% to -20% | Campaign data analysis |
| **Quality Score Improvement** | TBD | +0.5 to +1.0 avg | Google Ads data |
| **CPA Reduction** | TBD | -15% | Campaign performance |
| **Time Saved per Client** | TBD | >30 min/week | Time tracking |

### Success Definition

**MVP is "ready to use" when:**
- ✅ Successfully synced all client accounts (2-10 accounts)
- ✅ Generated meaningful recommendations for each client
- ✅ Applied 50+ actions without errors
- ✅ Rollback tested and working
- ✅ Zero crashes during 7 days of usage
- ✅ User reports >1 hour time saved in first week

---

# PART 2: USER PERSONA

## 2.1 Primary User Profile

**Name:** You (Solo PPC Specialist)

**Role:** Google Ads Specialist / Freelancer / Agency Owner

**Technical Profile:**
- Windows user
- Familiar with Google Ads UI and concepts (MCC, campaigns, keywords, search terms)
- Has Google Ads API credentials (developer token)
- Previous experience with Google Ads API integrations
- Tech-savvy enough to run desktop apps

**Account Management:**
- Uses MCC (Manager Account) + some standalone accounts
- Manages 2-10 client accounts simultaneously
- Account sizes: Small to Medium (1-50 campaigns, <10k keywords per client)
- Budget range: Variable (implied professional accounts)

**Work Style:**
- Ad-hoc checking (not daily routine, but when time permits)
- Prefers automation over manual repetition
- Values: Speed, accuracy, privacy
- Risk tolerance: Paranoid (wants confirmation before changes)

**Goals:**
1. **Primary:** Save time on routine optimization tasks
2. **Secondary:** Improve campaign performance (lower CPA, higher ROAS)
3. **Tertiary:** Maintain full control and visibility (no black box)

**Frustrations:**
- Manual work that "could be automated"
- Having to "just click OK" on obvious changes
- Time doesn't scale with more clients

**Tools Currently Used:**
- Google Ads UI (primary)
- MCC account for multi-client management
- (Implied: manual spreadsheets or mental tracking)

## 2.2 Anti-Personas (Out of Scope for MVP)

**NOT building for:**
- ❌ Enterprise teams (multi-user, collaboration features)
- ❌ Complete beginners (assumes Google Ads expertise)
- ❌ SaaS users expecting cloud sync
- ❌ Mac/Linux users (Windows-first MVP)

---

# PART 3: MVP SCOPE

## 3.1 Core Features (MUST HAVE)

### **Feature 1: Google Ads Data Sync** 🔴 P0
**Priority Rank:** #1

**Description:**  
Automated synchronization of Google Ads data to local SQLite database via Google Ads API.

**Functional Requirements:**
- Connect to Google Ads API using OAuth2 (via MCC or standalone accounts)
- Sync data entities:
  - Campaigns (name, status, budget, performance metrics)
  - Ad Groups (name, status, bids)
  - Keywords (text, match type, bid, Quality Score, performance)
  - Ads (headlines, descriptions, status, performance)
  - Search Terms (query text, clicks, cost, conversions - last 30 days)
- Store in local SQLite database
- Support multiple clients (2-10 accounts)
- Manual sync trigger ("Refresh" button)
- Sync status indicator ("Last synced: X hours ago")

**Technical Requirements:**
- OAuth2 flow using Windows browser redirect
- Credentials stored in Windows Credential Manager (keyring library)
- API calls: batch requests to minimize API quota usage
- Date range: Last 30 days for search terms, current state for campaigns/keywords
- Error handling: retry logic with exponential backoff

**User Stories:**
- As a user, I want to connect my MCC account once, so I can access all client data
- As a user, I want to manually refresh data on-demand, so I see latest performance
- As a user, I want to see when data was last synced, so I know data freshness

**Acceptance Criteria:**
- [ ] OAuth flow completes successfully (redirect to localhost, token stored)
- [ ] Syncs all 2-10 client accounts without errors
- [ ] Database populated with campaigns, keywords, ads, search terms
- [ ] "Last synced" timestamp updates after successful sync
- [ ] Sync completes in <5 minutes for average account (10 campaigns, 1k keywords)

---

### **Feature 2: Apply Actions (1-Click Optimization)** 🔴 P0
**Priority Rank:** #2

**Description:**  
Execute optimization actions directly through Google Ads API with one click, applying recommendations automatically.

**Functional Requirements:**
- Action types supported:
  1. **Pause Keyword** (set status to PAUSED)
  2. **Add Negative Keyword** (campaign or account level)
  3. **Increase/Decrease Bid** (modify max CPC)
  4. **Pause Ad** (set ad status to PAUSED)
  5. **Adjust Campaign Budget** (increase/decrease daily budget)
- Confirmation modal before each action (paranoid mode)
  - Show: What will change, Current value → New value, Reason
  - Options: "Apply", "Cancel"
- Action execution via Google Ads API (write operations)
- Log all actions in database (action_log table)
- Show success/error toast notification

**Technical Requirements:**
- Google Ads API services:
  - AdGroupCriterionService (keywords, bids)
  - CampaignCriterionService (negative keywords)
  - AdGroupAdService (ads)
  - CampaignService (budgets)
- Error handling: API errors displayed to user with retry option
- Transaction logging: Before/after state captured

**User Stories:**
- As a user, I want to pause a poor-performing keyword with one click, so I stop wasting spend
- As a user, I want to add a search term as negative keyword, so irrelevant traffic is blocked
- As a user, I want to see confirmation before any change, so I avoid mistakes

**Acceptance Criteria:**
- [ ] Clicking "Apply" on recommendation shows confirmation modal
- [ ] Modal displays: action type, entity (keyword/ad), current vs new state, reason
- [ ] After confirmation, action executes via API
- [ ] Success: Toast notification "Keyword paused successfully"
- [ ] Error: Toast notification with error details + retry button
- [ ] Action logged in action_log table with timestamp, user action, before/after state
- [ ] Change reflected in Google Ads account (verifiable in Google Ads UI)

---

### **Feature 3: Recommendations Engine** 🔴 P0
**Priority Rank:** #3

**Description:**  
Automated analysis of account data to generate actionable optimization recommendations based on 7 proven rules from the Optimization Playbook.

**Functional Requirements:**
- **7 Rules Implemented:**

**Rule 1: Pause Keyword** (HIGH priority)
```
IF (Keyword.spend > 2 × avg_keyword_spend_in_campaign 
    AND Keyword.conversions = 0 
    AND Keyword.clicks > 10)
→ RECOMMEND: Pause keyword
REASON: "High spend ($X) with no conversions after Y clicks"
```

**Rule 2: Increase Bid** (MEDIUM priority)
```
IF (Keyword.conversions > 5 
    AND Keyword.cvr > campaign.avg_cvr × 1.5)
→ RECOMMEND: Increase bid by 20%
REASON: "High performer: Z conversions, CVR X% (campaign avg: Y%)"
```

**Rule 3: Decrease Bid** (MEDIUM priority)
```
IF (Keyword.cpa > campaign.avg_cpa × 2 
    AND Keyword.spend > $50)
→ RECOMMEND: Decrease bid by 20%
REASON: "CPA $X is 2× campaign average ($Y)"
```

**Rule 4: Add Search Term as Keyword** (HIGH priority)
```
IF (SearchTerm.conversions >= 3 
    AND SearchTerm.text NOT IN campaign.keywords 
    AND SearchTerm.cvr > campaign.avg_cvr)
→ RECOMMEND: Add as EXACT match keyword
REASON: "High-performing query: X conversions, CVR Y%"
```

**Rule 5: Add Negative Keyword** (HIGH priority)
```
IF (SearchTerm.clicks > 5 
    AND SearchTerm.conversions = 0 
    AND SearchTerm.ctr < 1%)
→ RECOMMEND: Add as negative keyword (campaign level)
REASON: "Wasted spend: $X on Y clicks, 0 conversions"

OR

IF SearchTerm.text contains ["free", "cheap", "how to", "why", "job", "salary"]
→ RECOMMEND: Add as negative keyword (account level)
REASON: "Irrelevant intent detected"
```

**Rule 6: Pause Ad** (MEDIUM priority)
```
IF (Ad.impressions > 500 
    AND Ad.ctr < best_ad_in_group.ctr × 0.5)
→ RECOMMEND: Pause ad
REASON: "CTR X% is 50% below best ad (Y%)"
```

**Rule 7: Reallocate Budget** (HIGH priority)
```
IF (CampaignA.roas > account.avg_roas × 2 
    AND CampaignA.lost_impression_share_budget > 30%)
→ RECOMMEND: Increase CampaignA budget by 30%
REASON: "High ROAS (X%) losing 30% impressions to budget"
```

**Technical Requirements:**
- Daily scan of all accounts (after sync)
- Generate recommendations per client
- Store in recommendations table (client_id, type, priority, reason, entity_id, status)
- API endpoint: `GET /recommendations?client_id=X`
- Filter by: priority (HIGH/MEDIUM), status (pending/applied/dismissed)
- Summary counts for UI badges

**User Stories:**
- As a user, I want to see all pending recommendations for a client, sorted by priority
- As a user, I want to understand WHY each recommendation is made (reason + data)
- As a user, I want to dismiss recommendations I disagree with

**Acceptance Criteria:**
- [ ] Recommendations generated for each client after sync
- [ ] Recommendations list shows: type, priority badge, reason, entity name, action button
- [ ] HIGH priority recommendations (20-30 per client) displayed prominently
- [ ] Clicking recommendation expands details (full metrics, before/after preview)
- [ ] "Apply" button triggers confirmation modal (Feature 2)
- [ ] "Dismiss" button removes from list (marks as dismissed in DB)
- [ ] Summary badge shows count (e.g., "25 HIGH, 10 MEDIUM")

---

### **Feature 4: Action History & Rollback** 🔴 P0
**Priority Rank:** #7 (Lower priority, but MUST HAVE for safety)

**Description:**  
Log all applied actions with ability to view history and rollback (undo) last action if needed.

**Functional Requirements:**
- Log every applied action in `action_log` table:
  - Timestamp
  - Client ID
  - Action type (pause_keyword, add_negative, etc.)
  - Entity ID (keyword ID, ad ID, etc.)
  - Previous state (JSON: {status: "ENABLED", bid: 1.50})
  - New state (JSON: {status: "PAUSED", bid: null})
  - Recommendation ID (link to recommendation)
- Action History UI:
  - Chronological list (newest first)
  - Filter by: client, action type, date range
  - Show: "Paused keyword 'nike shoes' in Campaign X" with timestamp
- Rollback functionality:
  - "Undo" button on recent actions (<24 hours)
  - Restores previous state via API
  - Logs rollback as separate action

**Technical Requirements:**
- Database table: action_log (id, timestamp, client_id, action_type, entity_id, previous_state, new_state, reverted_at)
- Rollback API call: Reverse the action (PAUSED → ENABLED, restore bid)
- UI: Action History page with table (filterable, paginated)

**User Stories:**
- As a user, I want to see all actions I've taken, so I can audit changes
- As a user, I want to undo a mistake (e.g., accidentally paused wrong keyword), so I can recover quickly
- As a user, I want to see what state an entity was in before I changed it

**Acceptance Criteria:**
- [ ] Every applied action logged in action_log table with full before/after state
- [ ] Action History page shows chronological list of actions
- [ ] "Undo" button available for recent actions (<24h)
- [ ] Clicking "Undo" shows confirmation: "Revert keyword to ENABLED?"
- [ ] After undo, entity restored in Google Ads (verifiable in UI)
- [ ] Rollback itself logged as separate action (type: "rollback")

---

### **Feature 5: Search Terms Intelligence** 🔴 P0
**Priority Rank:** #4

**Description:**  
Segment and analyze search terms (actual user queries) into actionable categories based on performance and intent.

**Functional Requirements:**
- Fetch search terms data (last 30 days) during sync
- Segment into 4 categories:

**Category 1: HIGH_PERFORMER**
```
Criteria: conversions >= 3 AND cvr > campaign.avg_cvr
Color badge: Green
Action: "Add as Keyword" button
```

**Category 2: WASTE**
```
Criteria: clicks >= 5 AND conversions = 0 AND ctr < 1%
Color badge: Red
Action: "Add as Negative" button
```

**Category 3: IRRELEVANT**
```
Criteria: text contains ["free", "cheap", "how to", "why", "job", "salary", "download"]
Color badge: Orange
Action: "Add as Negative" button (auto-suggest account level)
```

**Category 4: TESTING / OTHER**
```
Criteria: clicks 1-5, insufficient data
Color badge: Gray
Action: None (observe)
```

- Search Terms UI:
  - Toggle view: Segments (4 cards) vs List (all terms, filterable)
  - Segment cards show: Count, total cost, conversion rate
  - List view: Table with columns (query, clicks, cost, conv, cvr, ctr, segment badge)
  - Filter by: segment, campaign, date range
  - Search box: find specific query text

**Technical Requirements:**
- Endpoint: `GET /search-terms/segmented?client_id=X`
- Response includes segment assignments + aggregated stats per segment
- Frontend: SearchTerms.jsx with tabs (Segments / List)

**User Stories:**
- As a user, I want to quickly see which search terms are wasting money, so I can add them as negatives
- As a user, I want to identify high-performing queries not yet added as keywords, so I can capture more traffic
- As a user, I want to filter irrelevant intent automatically (e.g., "free" queries), so I save time on review

**Acceptance Criteria:**
- [ ] Search terms synced from Google Ads (last 30 days)
- [ ] Segmented into 4 categories correctly based on rules
- [ ] Segments view shows 4 cards with counts and stats
- [ ] List view shows all terms with colored badges
- [ ] "Add as Keyword" button (HIGH_PERFORMER) → triggers Add Keyword action (with confirmation)
- [ ] "Add as Negative" button (WASTE/IRRELEVANT) → triggers Add Negative action
- [ ] Search and filter work correctly (no performance issues for 1000+ terms)

---

### **Feature 6: Dashboard (KPIs + Trends)** 🟡 P1
**Priority Rank:** #5

**Description:**  
Overview dashboard showing key performance indicators (KPIs) and trends for quick health check per client.

**Functional Requirements:**
- Multi-client overview:
  - Table of all clients with: Name, Spend (today), Conversions (today), ROAS, CPA
  - Click client row → drilldown to client-specific dashboard
- Client-specific dashboard:
  - KPI cards (top row):
    - Total Spend (today vs yesterday %)
    - Conversions (today vs yesterday %)
    - ROAS (today vs yesterday %)
    - CPA (today vs yesterday %)
  - Trend charts (last 30 days):
    - Daily Spend (line chart)
    - Daily Conversions (bar chart)
    - CTR trend (line chart)
  - Recommendations summary:
    - Badge: "25 HIGH, 10 MEDIUM pending"
    - Quick link to Recommendations page

**Technical Requirements:**
- Endpoint: `GET /analytics/kpis?client_id=X`
- Endpoint: `GET /analytics/trends?client_id=X&metric=spend&days=30`
- Frontend: Recharts for visualizations (line chart, bar chart)
- Components: KPICard.jsx (reusable), Charts.jsx

**User Stories:**
- As a user, I want to see all my clients' performance at a glance, so I can prioritize which to review
- As a user, I want to see spend trends, so I can spot anomalies (spikes/drops)
- As a user, I want to quickly navigate to recommendations from dashboard

**Acceptance Criteria:**
- [ ] Dashboard loads in <2 seconds (with cached data)
- [ ] Multi-client table shows correct metrics for each client
- [ ] Client drilldown shows KPI cards with correct YoY comparison
- [ ] Trend charts display last 30 days data accurately
- [ ] Clicking "Recommendations" badge navigates to Recommendations page

---

### **Feature 7: Anomaly Detection (Alerts)** 🟡 P1
**Priority Rank:** #6

**Description:**  
Automated detection of unusual performance changes (spikes, drops) to alert user of issues requiring attention.

**Functional Requirements:**
- Anomaly detection rules (triggered after sync):

**Anomaly 1: Spend Spike**
```
IF (today_spend > avg_daily_spend_30d × 1.5)
→ ALERT: "Client X: Spend spike +50% ($Y vs avg $Z)"
Priority: HIGH
```

**Anomaly 2: Conversion Drop**
```
IF (today_conversions = 0 AND avg_conversions_30d >= 3)
→ ALERT: "Client X: Zero conversions today (expected ~Y)"
Priority: HIGH
```

**Anomaly 3: CTR Drop**
```
IF (today_ctr < avg_ctr_30d × 0.7)
→ ALERT: "Client X: CTR drop -30% (X% vs avg Y%)"
Priority: MEDIUM
```

- Alerts UI:
  - Badge on sidebar: "🔴 3 alerts"
  - Alerts page: List of all alerts (unresolved)
  - Alert card: Client name, alert type, message, timestamp, "Mark as Reviewed" button
  - After review: moves to "Resolved" tab (hidden from main view)

**Technical Requirements:**
- Statistical analysis: Z-score or simple threshold-based (for MVP: threshold is OK)
- Database table: alerts (id, client_id, alert_type, message, priority, created_at, resolved_at)
- Endpoint: `GET /analytics/anomalies?client_id=X&status=unresolved`

**User Stories:**
- As a user, I want to be alerted when spend suddenly increases, so I can investigate before it gets out of control
- As a user, I want to know if conversions drop to zero, so I can check if tracking broke
- As a user, I want to dismiss alerts after reviewing, so my alert list stays clean

**Acceptance Criteria:**
- [ ] Anomalies detected correctly after sync (based on 30-day baseline)
- [ ] Alerts badge shows unresolved count (e.g., "3")
- [ ] Alerts page lists all unresolved alerts sorted by priority then timestamp
- [ ] "Mark as Reviewed" button marks alert as resolved (moves to Resolved tab)
- [ ] No false positives (spend spike on Monday after weekend = OK, not an anomaly)

---

## 3.2 Features EXCLUDED from MVP (v1.1+)

These features are documented in the Playbook but explicitly CUT from MVP to ship faster:

❌ **Semantic Clustering (v1.1)**
- AI-powered grouping of search terms by intent
- Requires: sentence-transformers model, K-means clustering
- Reason for cut: High complexity, nice-to-have not must-have

❌ **Quality Score Audit UI (v1.1)**
- Backend endpoint exists, frontend not built
- Visual: histogram of QS distribution, flagged keywords
- Reason for cut: Backend done, UI can wait

❌ **Forecasting UI (v1.1)**
- Backend endpoint exists (linear regression), frontend not built
- Visual: 7-day forecast chart with confidence score
- Reason for cut: Backend done, UI can wait

❌ **Ad Copy Analyzer (v2.0)**
- GPT-powered ad copy suggestions
- Requires: Claude API or local LLM
- Reason for cut: Advanced feature, requires external API

❌ **Correlation Matrix (v2.0)**
- Campaign interdependency analysis
- Visual: heatmap of campaign correlations
- Reason for cut: Advanced analytics, niche use case

❌ **Automated Rules (v1.1)**
- User-defined rules ("Auto-pause if spend > $50 and conv = 0")
- Requires: Rule builder UI + cron execution
- Reason for cut: Recommendations cover 80% use case, rules = edge case optimization

---

## 3.3 Non-Functional Requirements

### Performance
- **Sync time:** <5 minutes for average account (10 campaigns, 1k keywords, 5k search terms)
- **Dashboard load:** <2 seconds (with cached data)
- **Recommendations generation:** <30 seconds per client
- **UI responsiveness:** <100ms for user interactions (clicks, filters)

### Reliability
- **Uptime:** N/A (local app, not SaaS)
- **Crash rate:** Zero crashes during 7-day testing period
- **Data integrity:** Database backup before every Apply action
- **API error handling:** Graceful degradation (show error, allow retry)

### Security
- **Credentials storage:** Windows Credential Manager (encrypted)
- **Database encryption:** Plaintext SQLite (local disk, credentials-only encrypted)
- **Logging:** Errors + API calls (NO credentials logged)
- **Telemetry:** ZERO (no data sent to external servers)

### Scalability
- **Accounts supported:** 2-10 clients (MVP scope)
- **Data volume:** Up to 50 campaigns, 10k keywords, 50k search terms per client
- **Database size:** ~50MB per client × 10 = 500MB total (acceptable)

### Usability
- **First-time setup:** <10 minutes (OAuth + first sync)
- **Daily workflow:** <10 minutes per client (review recommendations + apply)
- **Learning curve:** <30 minutes (assumes Google Ads expertise)

---

# PART 4: TECHNICAL DECISIONS SUMMARY

## 4.1 Architecture

**Application Type:** Local-first desktop application

**Distribution Method:** PyWebView + PyInstaller
- Backend: FastAPI (Python 3.10+)
- Frontend: React 18 + Vite
- Wrapping: PyWebView (native window using Edge WebView2 on Windows)
- Packaging: PyInstaller (single .exe, ~35MB)

**Why PyWebView?**
- ✅ Best balance: native look + simple development
- ✅ Windows Credential Manager integration
- ✅ Minimal code changes (AI dev already knows FastAPI + React)
- ✅ Scalable (can migrate to Electron later if needed)

## 4.2 Technology Stack

### Backend
```
Language: Python 3.10+
Framework: FastAPI 0.100+
Database: SQLite 3 (local file)
ORM: SQLAlchemy 2.0+
Google Ads: google-ads 23.0+
Analytics: pandas, numpy, scipy, scikit-learn
Authentication: keyring (Windows Credential Manager)
Scheduling: APScheduler (optional, for future auto-sync)
```

### Frontend
```
Language: JavaScript (React 18)
Build Tool: Vite 5
UI Framework: Tailwind CSS 3
Components: shadcn/ui (optional)
Charts: Recharts 2.5+
Tables: @tanstack/react-table 8
Icons: lucide-react
HTTP Client: Axios or fetch
State Management: React hooks (useState, useContext)
```

### Desktop Wrapping
```
PyWebView: 4.4+
Rendering: Edge WebView2 (Windows 10+ native)
Packaging: PyInstaller 6.0+
Installer: (optional) Inno Setup for Windows installer
```

## 4.3 Data Model (High-Level)

**Core Tables:**

```sql
clients (
  id INTEGER PRIMARY KEY,
  name TEXT,
  customer_id TEXT,  -- Google Ads customer ID
  mcc_id TEXT,       -- Parent MCC (if applicable)
  created_at TIMESTAMP
)

campaigns (
  id INTEGER PRIMARY KEY,
  client_id INTEGER,
  campaign_id TEXT,  -- Google Ads campaign ID
  name TEXT,
  status TEXT,
  budget REAL,
  spend REAL,
  conversions INTEGER,
  roas REAL,
  updated_at TIMESTAMP
)

keywords (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER,
  keyword_id TEXT,
  text TEXT,
  match_type TEXT,
  status TEXT,
  bid REAL,
  quality_score INTEGER,
  clicks INTEGER,
  cost REAL,
  conversions INTEGER,
  ctr REAL,
  cvr REAL,
  cpa REAL,
  updated_at TIMESTAMP
)

search_terms (
  id INTEGER PRIMARY KEY,
  campaign_id INTEGER,
  keyword_id INTEGER,  -- Which keyword triggered this
  query TEXT,
  clicks INTEGER,
  cost REAL,
  conversions INTEGER,
  ctr REAL,
  cvr REAL,
  segment TEXT,  -- HIGH_PERFORMER, WASTE, IRRELEVANT, OTHER
  date DATE
)

recommendations (
  id INTEGER PRIMARY KEY,
  client_id INTEGER,
  type TEXT,  -- pause_keyword, add_negative, increase_bid, etc.
  priority TEXT,  -- HIGH, MEDIUM
  entity_id TEXT,  -- keyword_id, ad_id, etc.
  reason TEXT,
  current_value JSON,
  recommended_value JSON,
  status TEXT,  -- pending, applied, dismissed
  created_at TIMESTAMP
)

action_log (
  id INTEGER PRIMARY KEY,
  client_id INTEGER,
  action_type TEXT,
  entity_id TEXT,
  previous_state JSON,
  new_state JSON,
  recommendation_id INTEGER,  -- Link to recommendation
  applied_at TIMESTAMP,
  reverted_at TIMESTAMP
)

alerts (
  id INTEGER PRIMARY KEY,
  client_id INTEGER,
  alert_type TEXT,  -- spend_spike, conversion_drop, ctr_drop
  message TEXT,
  priority TEXT,  -- HIGH, MEDIUM
  created_at TIMESTAMP,
  resolved_at TIMESTAMP
)
```

## 4.4 API Endpoints (Backend)

**Authentication:**
- `POST /auth/google` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/status` - Check if authenticated

**Clients:**
- `GET /clients` - List all connected clients
- `GET /clients/{id}` - Get client details
- `POST /clients/sync` - Trigger sync for specific client

**Campaigns:**
- `GET /campaigns?client_id=X` - List campaigns for client
- `GET /campaigns/{id}` - Get campaign details

**Keywords:**
- `GET /keywords?campaign_id=X` - List keywords for campaign
- `GET /keywords/{id}` - Get keyword details

**Search Terms:**
- `GET /search-terms?client_id=X` - List all search terms
- `GET /search-terms/segmented?client_id=X` - Get segmented search terms

**Recommendations:**
- `GET /recommendations?client_id=X` - List recommendations (filterable by priority, status)
- `GET /recommendations/summary?client_id=X` - Get counts (HIGH/MEDIUM pending)
- `POST /recommendations/apply` - Apply a recommendation
- `POST /recommendations/dismiss` - Dismiss a recommendation

**Actions:**
- `GET /actions?client_id=X` - Action history (filterable)
- `POST /actions/rollback/{id}` - Rollback an action

**Analytics:**
- `GET /analytics/kpis?client_id=X` - Get KPIs (spend, conversions, ROAS, CPA)
- `GET /analytics/trends?client_id=X&metric=spend&days=30` - Get trend data
- `GET /analytics/anomalies?client_id=X&status=unresolved` - Get anomaly alerts

## 4.5 Security Implementation

**Credentials Storage:**
```python
# Windows Credential Manager (via keyring library)
import keyring

SERVICE_NAME = "GoogleAdsHelper"

# Store
keyring.set_password(SERVICE_NAME, "client_123_credentials", json.dumps({
    "developer_token": "xxx",
    "client_id": "yyy",
    "client_secret": "zzz",
    "refresh_token": "aaa"
}))

# Retrieve
creds = json.loads(keyring.get_password(SERVICE_NAME, "client_123_credentials"))
```

**Database Security:**
- SQLite: Plaintext (local disk, user's computer)
- Location: User-selected folder (e.g., Dropbox for backup)
- Permissions: Default OS file permissions

**Backup Strategy:**
- Auto-backup before every Apply action
- Format: `database_backup_YYYYMMDD_HHMMSS.db`
- Location: `/backups` subfolder
- Retention: Last 7 backups (auto-delete older)

**Logging:**
- Errors: Full stack trace (NO credentials)
- API calls: Success/failure (NO request/response bodies with PII)
- Actions: User actions logged (for audit trail)
- Location: `/logs/app.log` (rotating, 10MB max, 5 files)

**Network Security:**
- ONLY communicates with: Google Ads API (https://googleads.googleapis.com)
- NO telemetry, NO analytics, NO external services

## 4.6 User Interface Design

**Layout:** Sidebar Navigation
```
┌─────────────┬──────────────────────────────┐
│   SIDEBAR   │         MAIN CONTENT         │
│             │                              │
│ 🏠 Dashboard│   [Selected page content]    │
│ 👥 Clients  │                              │
│   - Client A│                              │
│   - Client B│                              │
│ 💡 Recommend│                              │
│ 🔍 Search   │                              │
│ 📊 Analytics│                              │
│ 🔔 Alerts   │                              │
│ 📜 History  │                              │
│ ⚙️  Settings│                              │
└─────────────┴──────────────────────────────┘
```

**Color Scheme:** Dark Mode (Default)
- Background: #0F172A (slate-900)
- Sidebar: #1E293B (slate-800)
- Cards: #334155 (slate-700)
- Text: #F1F5F9 (slate-100)
- Accent: #3B82F6 (blue-500)
- Success: #10B981 (green-500)
- Warning: #F59E0B (amber-500)
- Danger: #EF4444 (red-500)

**Design References:** Linear, Vercel Dashboard (clean, modern, data-focused)

**Key Components:**
- KPICard: Metric + trend indicator (↑↓)
- RecommendationCard: Type badge, priority, reason, action button
- SearchTermsTable: Sortable, filterable, segment badges
- ConfirmationModal: "Are you sure?" with before/after preview
- Toast Notifications: Success/error feedback

---

# PART 5: PROJECT CONSTRAINTS & ASSUMPTIONS

## 5.1 Constraints

**Timeline:**
- No hard deadline ("when it's ready")
- Expected MVP completion: 4-6 weeks (AI dev, full-time)

**Budget:**
- Internal development (AI assistant = no cost)
- Infrastructure: $0 (local-first, no cloud)
- Optional future costs: Code signing certificate ($100-300/year)

**Resources:**
- Developer: 1 (AI assistant, senior full-stack)
- Designer: None (Tailwind templates + shadcn/ui)
- Product Owner: You (user research, testing, feedback)

**Technical:**
- Platform: Windows only (MVP)
- Python version: 3.10+ (for modern typing)
- Google Ads API: v17 (current stable)
- No mobile support (desktop-only)

## 5.2 Assumptions

**User Assumptions:**
- User has Google Ads API developer token (already obtained)
- User is familiar with Google Ads concepts (campaigns, keywords, QS, etc.)
- User has 2-10 client accounts (small to medium size)
- User is comfortable installing desktop apps (.exe files)
- User has Windows 10+ (for Edge WebView2)

**Technical Assumptions:**
- Google Ads API stable (no breaking changes during MVP development)
- API rate limits sufficient (15,000 requests/day = OK for 10 clients)
- SQLite performance acceptable (no need for PostgreSQL at this scale)
- Windows Credential Manager reliable (no known issues)

**Data Assumptions:**
- Client accounts have historical data (at least 30 days)
- Conversion tracking enabled in Google Ads
- Search terms data available (not all accounts have this)

## 5.3 Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Google Ads API rate limit hit** | High (sync fails) | Low | Batch requests, caching, throttling |
| **OAuth token expiry** | Medium (re-auth needed) | Medium | Auto-refresh, graceful error handling |
| **Database corruption** | High (data loss) | Low | Auto-backup before Apply actions |
| **PyWebView rendering issues** | Medium (UI broken) | Low | Fallback to browser-based (localhost) |
| **Windows Credential Manager failure** | High (can't auth) | Very Low | Fallback to encrypted .env (less secure) |
| **AI dev misunderstanding requirements** | Medium (rework) | Medium | Detailed PRD + code reviews + testing |

---

# PART 6: SUCCESS CRITERIA & DEFINITION OF DONE

## 6.1 MVP "Ready to Use" Checklist

**Development Complete When:**
- [x] All 7 core features implemented (sync, apply, recommendations, search terms, dashboard, anomalies, action history)
- [x] OAuth flow working (can connect Google Ads account)
- [x] Database schema complete (all tables created)
- [x] All API endpoints functional (tested via Postman/curl)
- [x] Frontend pages built (all routes accessible)
- [x] PyWebView wrapper working (native window opens)
- [x] PyInstaller bundle created (google_ads_helper.exe)

**Testing Complete When:**
- [x] OAuth tested with real Google Ads account (MCC + standalone)
- [x] Synced 2-10 client accounts successfully
- [x] Generated recommendations for all clients (20+ per client)
- [x] Applied 50+ actions without errors
- [x] Rollback tested (undo last action successfully)
- [x] Zero crashes during 7 days of usage
- [x] Logs reviewed (no critical errors, only expected warnings)

**User Acceptance When:**
- [x] User reports >1 hour time saved in first week
- [x] User confirms recommendations are accurate and useful
- [x] User comfortable with UI (no major usability complaints)
- [x] User trusts safety mechanisms (confirmation modals, rollback)

## 6.2 Post-MVP (v1.1) Scope

**If MVP successful, next features to add:**
1. **Automated Rules** (user-defined automation)
2. **Semantic Clustering** (AI grouping of search terms)
3. **QS Audit UI** (frontend for existing backend)
4. **Forecasting UI** (frontend for existing backend)
5. **Multi-platform** (Mac/Linux support via PyWebView)

**If scaling to other users:**
1. Landing page + marketing site
2. User onboarding wizard (improved first-time experience)
3. In-app documentation / help tooltips
4. Crash reporting (Sentry, opt-in)
5. Auto-update mechanism (via GitHub releases)

---

# APPENDIX A: GLOSSARY

**Google Ads Terms:**
- **MCC (Manager Account):** Multi-client account that manages multiple Google Ads accounts
- **Campaign:** Top-level structure in Google Ads (e.g., "Brand Campaign")
- **Ad Group:** Container for keywords and ads within a campaign
- **Keyword:** Search term you're bidding on
- **Search Term:** Actual query a user typed (may differ from keyword due to match types)
- **Match Type:** How closely keyword must match search term (Exact, Phrase, Broad)
- **Quality Score (QS):** Google's rating (1-10) of keyword relevance (affects CPC)
- **CTR (Click-Through Rate):** Clicks / Impressions
- **CVR (Conversion Rate):** Conversions / Clicks
- **CPA (Cost Per Acquisition):** Cost / Conversions
- **ROAS (Return on Ad Spend):** Revenue / Cost
- **Impression Share:** % of available impressions your ads received
- **Lost IS (Budget):** % impressions lost due to insufficient budget
- **Lost IS (Rank):** % impressions lost due to low ad rank (bid too low)

**Application Terms:**
- **Recommendation:** Suggested optimization action generated by rules
- **Apply Action:** Execute recommendation via Google Ads API
- **Rollback:** Undo a previously applied action
- **Segment:** Category for search terms (HIGH_PERFORMER, WASTE, etc.)
- **Anomaly:** Unusual performance change detected by statistical analysis
- **Sync:** Process of fetching data from Google Ads API to local database

---

# APPENDIX B: OPEN QUESTIONS

**Questions for Product Owner (to be answered before development):**

1. **Sync Frequency Decision:**
   - Current: Manual sync only
   - Question: In future, add auto-sync (daily at 6 AM)?
   - Impact: Requires APScheduler + background process management
   - Decision: TBD (can add post-MVP if needed)

2. **Multi-Language Support:**
   - Current: English only
   - Question: Polish language support needed? (given user is in Poland)
   - Impact: i18n library + translations
   - Decision: TBD (probably not MVP, but easy to add)

3. **Reporting Feature:**
   - Current: Not in scope
   - Question: Future need for PDF/CSV reports for clients?
   - Impact: Reporting library (ReportLab / pandas to_csv)
   - Decision: TBD (v1.1 feature if needed)

4. **Mobile Companion:**
   - Current: Desktop only
   - Question: Future mobile app (iOS/Android) for "check on the go"?
   - Impact: Separate development track (React Native?)
   - Decision: TBD (probably no - desktop is primary use case)

---

# DOCUMENT SIGN-OFF

**Product Manager:** Approved ✅  
**Developer (AI Assistant):** Ready to implement ✅  
**Product Owner (User):** _Awaiting feedback_ ⏳

---

**Next Steps:**
1. Review this PRD and provide feedback/changes
2. Once approved, proceed to Technical_Spec.md (detailed implementation guide)
3. Begin Sprint 1: Infrastructure & OAuth setup

**Questions? Feedback? Let's discuss before moving to Technical Spec!** 🚀
