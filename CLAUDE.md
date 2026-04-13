# CLAUDE.md - Google Ads Helper (Claude adapter)

This file is optimized for Claude Code sessions.
Canonical repo-wide instructions live in `AGENTS.md`.
If there is any mismatch, follow `AGENTS.md`.

## 0) Execution Policy — READ FIRST

**EXECUTE IMMEDIATELY. DO NOT ASK PERMISSION.**

- Start working on the task without asking "should I proceed?", "can I continue?", or "do you want me to...?"
- If ambiguity exists — pick the most likely interpretation and proceed. Mention assumptions briefly AFTER delivery.
- Never pause mid-implementation to check in. Do the full work, then report.
- ONLY stop and ask before: deleting files, removing functions, force-pushing, DB reseed, credentials changes.

**VERIFY IN BROWSER BEFORE CLAIMING DONE (frontend changes):**
1. Run `npm run build` — zero errors required.
2. Confirm no white screen / broken imports by checking the JSX export chain.
3. Never report "done" on a frontend task based on tests alone — tests can pass while UI is broken.

**STRAIGHT ASCII QUOTES ONLY in all code:**
- Never use smart quotes: `'` `'` `"` `"` — they cause build errors.
- Use: `'` `"` only.

**POLISH UI — all user-facing strings must use correct Polish diacritics:**
- ą ć ę ł ń ó ś ź ż — always, in every label, tooltip, and message.

---

## 1) Working Language

- User communication: Polish.
- Code, identifiers, and commit messages: English.

## 1a) Execution Style

- Execute tasks immediately without asking for permission or confirmation.
- Do not pause to ask questions mid-implementation — just do the work.
- If ambiguity exists, pick the most likely interpretation and proceed. Mention assumptions briefly after delivery.
- EXCEPTION — always ask before deleting files, removing functions, or dropping significant blocks of code. Adding and editing freely, deleting only with approval.
- EXCEPTION — /ceo has its own multi-phase pipeline (ASSESS → DECIDE → /pm → /cto → /build). "Execute immediately" means execute the PIPELINE immediately, NOT skip pipeline phases to code faster. CEO must produce artifacts (ceo-log.md entry + PM spec) before any implementation begins. This is non-negotiable.

## 1b) Project Structure Map

Use this to navigate the codebase — do not explore aimlessly:
```
backend/
  app/
    routers/    → API endpoints (analytics, campaigns, keywords_ads, search_terms, sync, history, export, ...)
    services/   → Business logic (google_ads, analytics_service, recommendations, sync_config, ...)
    models/     → SQLAlchemy models
    schemas/    → Pydantic schemas
  tests/        → pytest tests (test_{router/service}.py)

frontend/
  src/
    pages/      → Route pages (Dashboard, Keywords, SearchTerms, QualityScore, Campaigns, ...)
    components/ → Shared UI (Sidebar, SyncModal, DataTable, GlobalFilterBar, TrendExplorer, ...)
    contexts/   → React contexts (AppContext, FilterContext)
    api.js      → All API calls
  e2e/          → Playwright tests
```

## 1c) UI Verification Checklist

After ANY frontend change, verify before reporting "done":
1. Component is exported from its file (named export or default).
2. Component is imported in parent (page or App.jsx).
3. Component is rendered in JSX tree (not just imported).
4. Props match what parent passes (no undefined data).
5. No console errors — run `npm run build` to catch compile issues.

## 1d) Pattern Matching Rule

Before building new UI features:
1. Find 2-3 similar existing components in `frontend/src/` (use Grep/Glob).
2. Follow the same patterns (state management, API calls, styling, filters).
3. If existing features have controls (checkboxes, dropdowns, toggles) — new features in the same area should have them too.

## 2) Core Rules (Do Not Break)

- Keep import flow one-way:
  - `utils -> config -> models -> schemas -> services -> routers -> app/main.py -> main.py`
- Keep Google Ads money values in micros at storage level.
- Route every Google Ads write through action validation/circuit breaker.
- Store credentials only via Windows Credential Manager (`keyring`).
- Do not auto-commit or auto-push mid-task. Use `/done` to close a completed task (commit + docs-sync + push with PM gate).
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

## 6) Documentation Order — JIT (Just-In-Time)

Czytaj plik TYLKO gdy jest faktycznie potrzebny do zadania. Nie czytaj wszystkiego na starcie.

| Plik | Czytaj TYLKO gdy |
|------|-----------------|
| `AGENTS.md` | Nowa sesja z nieznanego obszaru lub konflikt z instrukcjami |
| `PROGRESS.md` | `/ceo`, `/pm`, `/done`, pytanie o status projektu |
| `DECISIONS.md` | Architektura, ADR, spór o design, nowe podejście techniczne |
| `docs/API_ENDPOINTS.md` | Nowy endpoint, zmiana API, praca z routerami |
| `docs/COMPLETED_FEATURES.md` | "Czy to już jest?" / `/pm-check` / weryfikacja zakresu |
| `google_ads_optimization_playbook.md` | `/ads-expert`, `/ads-user` — wyłącznie |
| `SEARCH_CAMPAIGN_WORKFLOW.md` | Praca z kampaniami Search, keyword strategy |

## 7) Skills & Commands

### Skills (`.claude/skills/` — izolowane, z frontmatter)

Skill'e dzialaja w **fork context** — nie zjadaja glownego okna konwersacji:

| Skill | Opis | Izolacja |
|-------|------|----------|
| `/build {opis}` | **MASTER PIPELINE** — plan → build → verify → test → domain → ship | main context (orchestrator) |
| `/review` | Parallel review: 3 agenty (code-quality + security + domain) | `context: fork` |
| `/docs-sync` | Synchronizacja PROGRESS.md, API_ENDPOINTS.md z kodem | `context: fork` |
| `/ads-user {tab}` | Symulacja PPC specjalisty (persona Marek) | `context: fork` |
| `/ads-expert {tab}` | Ocena eksperta Google Ads (4 kryteria) | `context: fork` |
| `/pm-check` | PM gate — skanuje kod, score >= 7/10 pozwala na push | `context: fork` |

### Custom Agents (`.claude/agents/` — wyspecjalizowane review)

| Agent | Rola | Tools |
|-------|------|-------|
| `code-quality-reviewer` | Pattern matching, DRY/SOLID, naming, dead code | Read, Grep, Glob |
| `security-reviewer` | OWASP top 10, SQL injection, XSS, secrets | Read, Grep, Glob |
| `domain-expert` | Micros, conversions float, circuit breaker, playbook | Read, Grep, Glob |

### Commands (`.claude/commands/` — legacy, main context)

Komendy ktore MUSZA edytowac pliki w glownym kontekscie:
- `/cto` — smart router, deleguje do /feature, /bugfix, /endpoint
- `/feature`, `/bugfix`, `/endpoint`, `/frontend-page`, `/refactor` — implementacja
- `/done` — zamkniecie zadania (orchestruje /commit + /docs-sync + push)
- `/commit`, `/start`, `/seed`, `/debug` — utility
- `/sprint {tab}`, `/ads-verify {tab}`, `/ads-check {tab}` — implementation pipeline
- `/audit`, `/sync-check`, `/visual-check`, `/competitor`, `/strategist`, `/ceo` — analityczne

## 7a) Build Pipeline (GLOWNY)

**Uzyj `/build {opis}` dla kazdego nowego zadania.** Pipeline:

```
/build {feature/bug/endpoint}
  │
  ├─ FAZA 1: PLAN (3 Explore agents ‖)
  │   ├─ Backend Scout
  │   ├─ Frontend Scout
  │   └─ Test Scout
  │
  ├─ FAZA 2: BUILD (task-by-task + auto-test hooks)
  │
  ├─ FAZA 3: VERIFY (3 review agents ‖)
  │   ├─ code-quality-reviewer
  │   ├─ security-reviewer
  │   └─ domain-expert
  │   └─ Gate: srednia >= 7/10
  │
  ├─ FAZA 4: TEST (‖ pytest + npm build)
  │
  ├─ FAZA 5: DOMAIN CHECK (opcjonalne, UI only)
  │   └─ /ads-user → /ads-expert
  │
  └─ FAZA 6: SHIP
      ├─ /commit
      ├─ /docs-sync (fork)
      ├─ /pm-check (fork, gate >= 7/10)
      └─ git push
```

## 7b) Hooks (automatyczne)

| Hook | Event | Timeout | Dzialanie |
|------|-------|---------|-----------|
| `session-start.sh` | SessionStart | 10s | Status projektu |
| `stop.sh` | Stop | 10s | Podsumowanie sesji |
| `post-edit-test.sh` | PostToolUse (Write/Edit) | 60s | Auto-test po edycji |
| `pre-push.sh` | PreToolUse (Bash) | 10s | Gate: wymaga pm-review-pass |
| `pre-compact.sh` | PreCompact | 10s | Zapis kontekstu |
| `task-completed.sh` | TaskCompleted | 10s | Auto-commit taskow |

## 7c) Ads Review Pipeline

```
/ads-user {tab} (fork) → /ads-expert {tab} (fork) → /ads-verify {tab} → /sprint {tab}
  → /ads-check {tab} → jesli GOTOWE: /ads-user re-test
```

Raporty w `docs/reviews/`: ads-user-{tab}.md, ads-expert-{tab}.md, ads-verify-{tab}.md, ads-check-{tab}.md

## 8) Current State

See `PROGRESS.md` for up-to-date delivery status and open work.
See `docs/DEVELOPMENT_ROADMAP_OPTIMIZATION.md` for v1.1+ roadmap with implementation status.
