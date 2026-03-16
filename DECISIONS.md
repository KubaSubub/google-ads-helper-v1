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

## ADR-013: Canonical runtime SQLite path
**Decision:** Resolve SQLite runtime data to a single canonical path independent of current working directory.
**Why:** The previous relative `./data/google_ads_app.db` created two different databases depending on whether the app started from repo root or `backend/`.
**Rule:** Source mode uses `<repo>/data/google_ads_app.db`; frozen mode uses `<exe_dir>/data/google_ads_app.db`.
**Migration:** If the canonical DB does not exist and legacy `backend/data/google_ads_app.db` does, move the DB and SQLite sidecar files once before engine startup.

## ADR-014: Missing rows after successful sync become REMOVED, not deleted
**Decision:** Campaigns, ad groups, and keywords missing from a successful full sync are marked `REMOVED` locally.
**Why:** We need historical/debug visibility without polluting default working views with stale cache rows.
**UI rule:** Default keyword list hides `REMOVED`; users can opt in via `include_removed` / local toggle.
**Trade-off:** Local DB keeps tombstones longer, but behavior is explainable and safer than hard-deleting rows.

## ADR-015: Positive and negative keywords use separate canonical caches
**Decision:** Keep positive keywords in `keywords` and negative keyword criteria in `negative_keywords`; do not merge them into one table.
**Why:** Positive keywords carry bids, serving state, and performance metrics that do not apply cleanly to negatives. A unified table would increase null-heavy ambiguity and repeat the exact class of bug that caused the incident.
**Rule:** Both caches expose explicit `criterion_kind` values (`POSITIVE`, `NEGATIVE`), and positive sync must reject `negative=true` rows at query, mapping, and before-save layers.
**Scope:** `negative_keywords` is canonical for campaign-level and ad-group negative keyword criteria. No account-level negative cache in the current milestone.

## ADR-016: AI report generation uses local Claude CLI streaming
**Decision:** Integrate AI report generation through local Claude CLI (`claude -p --output-format stream-json`) invoked as a backend subprocess.
**Why:** The app is local-first and desktop-oriented; local CLI integration avoids adding a second remote LLM credential/token flow into app storage and keeps runtime behavior aligned with user-managed Claude installation.
**Rule:** Backend streams generated content to frontend via SSE and treats CLI availability as runtime capability (`/api/v1/agent/status`), not as a startup hard dependency.
**Trade-off:** Behavior depends on local CLI installation/version and PATH correctness; failure paths must degrade gracefully with explicit user-facing error events.

## ADR-017: AI report generation is single-flight per backend process
**Decision:** Allow only one active AI report generation at a time using an in-memory `asyncio.Lock`.
**Why:** The product is single-user desktop-first; parallel report generation provides limited user value but increases risk of resource contention, overlapping stream handling, and degraded UX stability.
**Rule:** If generation is already in progress, the next request returns a busy SSE error and closes with `done`.
**Trade-off:** No concurrent report generation in the same backend process; users must retry after completion.
**Revisit if:** Multi-user/server mode or queued background report jobs become a product requirement.
