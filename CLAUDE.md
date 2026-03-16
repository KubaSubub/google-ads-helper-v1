# CLAUDE.md - Google Ads Helper (Claude adapter)

This file is optimized for Claude Code sessions.
Canonical repo-wide instructions live in `AGENTS.md`.
If there is any mismatch, follow `AGENTS.md`.

## 1) Working Language

- User communication: Polish.
- Code, identifiers, and commit messages: English.

## 2) Core Rules (Do Not Break)

- Keep import flow one-way:
  - `utils -> config -> models -> schemas -> services -> routers -> app/main.py -> main.py`
- Keep Google Ads money values in micros at storage level.
- Route every Google Ads write through action validation/circuit breaker.
- Store credentials only via Windows Credential Manager (`keyring`).
- Do not auto-commit or auto-push.
- Never run destructive git commands without explicit request (`git reset --hard`, `git checkout --`, `git clean -fd`).

## 3) Runtime Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Tests
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

## 4) Real-Client Validation Defaults

- Primary test client: Sushi Naka Naka (`client_id=3`).
- Backup test client: Klimfix (`client_id=2`).
- For sync/analytics changes, do not mark done without real-client verification.

## 5) Protected/High-Risk Operations

Always ask user before:
- `git push` / `git push --force`
- DB reseed or DB file removal
- `.env` / credentials changes
- dependency installation (`pip install`, `npm install` for new packages)

## 6) Documentation Order

Read in this order when context is needed:
1. `AGENTS.md`
2. `PROGRESS.md`
3. `DECISIONS.md`
4. `docs/API_ENDPOINTS.md`
5. `docs/COMPLETED_FEATURES.md`
6. `Technical_Spec.md`
7. `google_ads_optimization_playbook.md`
8. `SEARCH_CAMPAIGN_WORKFLOW.md`

## 7) Claude Slash Commands

Project command prompts are stored in `.claude/commands/`:
- `start.md`
- `debug.md`
- `fix.md`
- `review.md`
- `refactor.md`
- `endpoint.md`
- `frontend-page.md`
- `sync-check.md`
- `seed.md`
- `audit.md`
- `progress.md`
- `commit.md`

Use them as workflow helpers, but keep behavior aligned with `AGENTS.md`.

## 8) Recent Delivered Snapshot (2026-03-16)

- AI Agent feature delivered:
  - backend router `agent.py` (`/api/v1/agent/status`, `/api/v1/agent/chat`)
  - service orchestration in `agent_service.py` (data gather -> prompt -> Claude CLI stream)
  - frontend page `Agent.jsx` with SSE streaming and markdown rendering
  - navigation + route wiring for `/agent`
- AI Agent stabilization in current workspace:
  - single-flight lock flow hardened in stream path
  - 7d vs 7d KPI comparison fixed
  - campaign summary/detail aggregation switched from per-campaign queries to grouped batch queries
  - Claude subprocess verbosity/noise reduced and error output simplified
  - frontend SSE handshake now dispatches `auth:unauthorized` on 401
- Test context:
  - `backend/tests/test_agent.py` added for agent API/service behavior
  - broader test expansion already committed (`1c555ea`, +81 tests)
  - pre-existing regression test repairs committed (`60b24cb`)
- Current source-of-truth pointers for these changes:
  - `PROGRESS.md` (delivery + validation timeline)
  - `DECISIONS.md` (ADR-016, ADR-017)
  - `docs/API_ENDPOINTS.md` (endpoint index)
  - `Technical_Spec.md` (API addendum 2026-03-16)
