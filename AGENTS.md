# AGENTS.md - Google Ads Helper (Canonical Agent Guide)

This file is the canonical instruction set for coding agents in this repository.
Keep it concise, specific, and executable.

## 1) Scope and Priority

- Scope: whole repository.
- If a deeper instruction file exists for a subdirectory, the deeper file wins for that subtree.
- If instructions conflict, follow: direct user request -> safety constraints -> this file -> other docs.

## 2) Project Snapshot

- Product: local-first Windows desktop app for Google Ads optimization.
- Stack: FastAPI (backend), React + Vite (frontend), SQLite, PyWebView.
- Key principle: financial safety first for all write operations.

## 3) Quickstart Commands

```bash
# Backend (from repo root)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Backend tests
cd backend
pytest

# Frontend
cd frontend
npm install
npm run dev
npm run build

# Desktop wrapper
python main.py
```

## 4) Critical Guardrails

- Never run destructive git commands without explicit user request:
  - `git reset --hard`
  - `git checkout -- <path>`
  - `git clean -fd` or stronger variants
- Do not auto-commit or auto-push.
- Do not run `git push` or `git push --force` without explicit user approval.
- Do not amend commits unless user explicitly asks for amend.
- Do not modify `.env`, credentials, or token storage flow without explicit request.
- Do not add new dependencies (`pip` or `npm`) without user approval.
- Do not remove files you did not create in the current task unless asked.

## 5) Architecture Invariants

- Import direction must stay one-way:
  - `utils -> config -> models -> schemas -> services -> routers -> app/main.py -> main.py`
- Monetary values from Google Ads API are micros.
  - Store in DB as integer micros (`BigInteger` style).
  - Convert to float/currency only in API schema/serialization layer.
- Every write to Google Ads API must go through action validation/circuit breaker (`validate_action()` path).
- Credentials/tokens must be stored only via Windows Credential Manager (`keyring`), never in SQLite/logs/plain `.env`.

## 6) Protected Areas and Change Policy

- Before changing already completed features, check:
  - `docs/COMPLETED_FEATURES.md`
- For large refactors, prefer incremental changes and preserve behavior.
- If a DB schema change is required, state clearly that reseed/migration impact exists.

## 7) Testing Expectations

- Minimum: run targeted tests for touched backend modules.
- Prefer full backend test pass when touching core services:
  - `backend/tests/test_security_hardening.py`
  - `backend/tests/test_safety_limits.py`
  - `backend/tests/test_analytics.py`
- For sync/analytics behavior, validate with a real client account before calling work done.
- Never report success without saying what was actually tested.

## 8) Delivery Format

- Communication with user: Polish.
- Code identifiers/comments: English.
- For each change, provide:
  - what changed,
  - why,
  - what was tested,
  - known risks or follow-ups.

## 9) Task Checklist (Definition of Done)

- Requirements satisfied with minimal, focused diff.
- No architecture invariant broken.
- No secrets exposed.
- Relevant tests/build checks executed (or explicitly noted if not run).
- Documentation updated when behavior or architecture changed:
  - `PROGRESS.md` for progress/status updates
  - `DECISIONS.md` for architecture decisions

## 9a) Post-Feature Update Loop (Required)

After implementing any new functionality, run this loop before marking task done:

1. Implement feature + tests (or state test gap explicitly).
2. Update runtime/API docs that changed:
   - `docs/API_ENDPOINTS.md` (if endpoint/params/response changed)
3. Update project tracking docs:
   - `PROGRESS.md` (what was delivered, current status)
   - `DECISIONS.md` (only if architectural decision/tradeoff was made)
   - `docs/COMPLETED_FEATURES.md` (if feature moved to completed state)
4. Re-run relevant checks and report exactly what was tested.
5. In delivery note always include:
   - what changed,
   - why,
   - what was tested,
   - known risks/follow-ups.

## 10) Project Context Map

- `CLAUDE.md` - Claude-specific adapter + workflow notes.
- `PROGRESS.md` - current implementation status.
- `DECISIONS.md` - ADR-style decisions.
- `docs/API_ENDPOINTS.md` - API reference.
- `google_ads_optimization_playbook.md` - domain optimization logic.
- `docs/archive/` - zarchiwizowane dokumenty (SOURCE_OF_TRUTH, FEATURE_SET, itp.) — nie czytaj automatycznie.
