# DECISIONS.md — Architecture Decision Records
# Documents WHY specific decisions were made. Do NOT reverse these without PM approval.

---

## ADR-001: SQLite over PostgreSQL
**Decision:** Use SQLite for local database
**Why:** Local-first app for 1 user, 2-10 clients, <500MB data. No server needed. PostgreSQL adds install complexity for zero benefit at this scale.
**Trade-off:** No concurrent writes (acceptable — single user app).
**Revisit if:** App becomes multi-user or SaaS.

## ADR-002: BigInteger (micros) over REAL for monetary values
**Decision:** Store ALL money as BigInteger in micros (1 USD = 1,000,000 micros)
**Why:** REAL/float causes rounding errors in financial calculations. Google Ads API returns micros natively.
**Rule:** Convert to float ONLY in Pydantic schemas (API response layer). Never in models or services.
**Note:** PRD Section 4.3 incorrectly suggests `REAL` — IGNORE that. Blueprint Patch v2.1 overrides it.

## ADR-003: PyWebView over Electron
**Decision:** Use PyWebView (Edge WebView2 on Windows) for desktop wrapper
**Why:** Same Python backend, no Node.js dependency, smaller bundle (~35MB vs ~120MB). Native-feeling window. Can migrate to Electron later if needed.
**Trade-off:** Less ecosystem than Electron, Windows-only rendering engine.

## ADR-004: Windows Credential Manager (keyring) over .env files
**Decision:** Store OAuth tokens in Windows Credential Manager via `keyring` library
**Why:** Encrypted at OS level. .env files are plaintext, easily leaked via git or file access.
**Rule:** `credentials_service.py` is the ONLY file that reads/writes tokens. No exceptions.

## ADR-005: Manual sync over auto-sync (MVP)
**Decision:** Sync triggered manually via "Refresh" button only
**Why:** Simpler architecture, no background scheduler needed, user controls when data refreshes.
**Future:** Add APScheduler for daily auto-sync in v1.1 if requested.

## ADR-006: Segment after sync (batch) over during sync (real-time)
**Decision:** Search term segmentation runs as Phase 4 AFTER sync completes
**Why:** Keeps sync fast (just store data), decouples business logic from data ingestion.
**Trade-off:** User sees unsegmented data briefly after sync. Acceptable for MVP.

## ADR-007: 24-hour revert window
**Decision:** Actions can only be undone within 24 hours
**Why:** After 24h, the account state may have changed due to external factors (Google auto-optimizations, other users editing). Reverting old actions is unsafe.
**Exception:** ADD_NEGATIVE is NEVER revertable (removing negatives immediately re-enables bad traffic).

## ADR-008: Threshold-based anomaly detection over statistical (MVP)
**Decision:** Use simple thresholds (1.5× spend, 0.5% CTR floor) instead of Z-score/IQR
**Why:** MVP simplicity. Statistical methods need sufficient historical daily data which we don't store per-day in MVP schema (only 30-day aggregates).
**Future:** v1.1 will add daily metrics table → enable proper statistical detection.

## ADR-009: React hooks over Redux/Zustand
**Decision:** Use useState + useContext for state management
**Why:** App has simple state (selected client, sync status, recommendations list). No global state complexity warrants a state library.
**Revisit if:** App grows to 15+ pages with shared cross-page state.

## ADR-010: FastAPI serves React build in production
**Decision:** In production, FastAPI serves the built React app (`frontend/dist/`) as static files
**Why:** Single process = simpler PyWebView integration. No CORS issues. One port (8000).
**Dev mode:** React runs on port 5173 (Vite dev server), proxied to FastAPI on 8000.

## ADR-011: No Alembic migrations for MVP
**Decision:** Use `Base.metadata.create_all()` for schema creation
**Why:** Single user, no production database to migrate. If schema changes, user can re-sync (data comes from Google Ads API anyway).
**Future:** Add Alembic when schema is stable and user has historical data worth preserving.

## ADR-012: Dark mode only (MVP)
**Decision:** Dark mode default, no light mode toggle
**Why:** Faster development, consistent design. Target user works long hours — dark mode preferred.
**Future:** Add toggle in v1.1 Settings page.
