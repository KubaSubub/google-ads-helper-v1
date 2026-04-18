# PHASE 9 — DevOps / Developer Experience Audit

**Verdict:** **C+ / 5.5 out of 10.** The Claude-Code integration is the most mature piece of the developer toolchain — 7 hooks, 25+ commands, 6 skills, all cleanly tiered. Everything around it (CI, cross-platform, onboarding, migrations) is missing or manual.

**Headline findings:**
- Zero automated CI/CD pipeline — validation lives entirely inside Claude Code hooks.
- Windows-only lock-in: `keyring` → Windows Credential Manager hard dependency breaks macOS/Linux dev.
- No migrations framework (Alembic is installed and unused) — schema changes require DB reseed.
- No English `README.md` — first-run friction for anyone outside Jakub's head.
- `git push` gated by `pm-check` pass → adds 2–3 min per release cycle (feature, not bug, but needs nuance).

---

## Developer journey timeline (cold start → running UI)

| Step | Time | Friction | Notes |
|------|------|----------|-------|
| Clone | 2 min | Low | `.gitignore` excludes `node_modules`, `venv`, `data/` |
| Read `CLAUDE.md` | 5 min | Low | Clear Polish policy document |
| Backend `pip install -r requirements.txt` | 3–5 min | Low | Heavy ML libs (pandas, scikit-learn, sentence-transformers) |
| Frontend `npm install` | 1–2 min | Low | ~250 MB `node_modules` |
| DB init | 2 min | **Medium** | No `alembic init`; seed hardcoded in `database.py` — first failure here is confusing |
| Start backend (`uvicorn app.main:app --reload`) | 1 min | Low | Needs `PYTHONIOENCODING=utf-8` on Windows |
| Start frontend (`npm run dev`) | 1 min | Low | Vite proxy handles `/api` |
| Verify `/health` + UI | 2 min | Low | — |
| First edit + test | 3 min | **Medium** | Post-edit-test hook fires pytest/build + smart-quote check |
| `git push` | 1 min | **High** | Blocked by `pm-check` gate (score ≥ 7/10 required) |
| `python build.py` | 5 min | Medium | PyInstaller → `dist/Google Ads Helper.exe` ~150 MB |
| **Total cold start** | **28–35 min** | **Moderate** | |

---

## CI/CD — currently zero

| Component | Status |
|-----------|--------|
| GitHub Actions | ❌ no `.github/workflows/` |
| GitLab CI | ❌ no `.gitlab-ci.yml` |
| Pre-commit (standard) | ❌ only Claude hooks |
| Linting (black / flake8 / eslint) | ❌ |
| Automated tests on PR | ❌ manual (`pytest`, `npm run build`) |
| Pre-push gate | ✅ **Claude-driven** (`pm-check` + `pre-push.sh`) |
| Code signing | ❌ unsigned `.exe` → SmartScreen warnings |

All validation runs **locally and only on the maintainer's machine**. There's no "PR can't be merged unless CI is green" protection.

---

## Claude-Code integration — this is the mature bit

### Hooks (7)

| Hook | Trigger | Time | Notes |
|------|---------|------|-------|
| `session-start.sh` | Session open | ~1 s | Shows TODO count, uncommitted files |
| `post-edit-test.sh` | After Edit/Write | 5–15 s | Smart-quote scan + frontend build or pytest |
| `post-commit.sh` | After Bash | ~2 s | Purpose unclear from code (worth auditing) |
| `pre-compact.sh` | Before memory compression | ~1 s | Saves context to `last-session-context.md` |
| `task-completed.sh` | TodoWrite done | ~1 s | Reminder to update `PROGRESS.md` |
| `stop.sh` | Session ends | ~2 s | Reports uncommitted/staged/untracked |
| **`pre-push.sh`** | Before `git push` | N/A | **Blocking gate — requires `pm-check` pass within last 30 min** |

### Commands (25)

Five tiers, minimal overlap:

- **Orchestrators:** `/ceo`, `/cto`, `/build`
- **Implementation:** `/feature`, `/bugfix`, `/endpoint`, `/frontend-page`, `/refactor`
- **QA / shipping:** `/review`, `/pm-check`, `/done`, `/commit`, `/docs-sync`
- **Ads-review pipeline:** `/ads-user`, `/ads-expert`, `/ads-verify`, `/ads-check`, `/sprint`
- **Analysis:** `/audit`, `/audit-deep`, `/debug`, `/intelligence`, `/strategist`, `/competitor`, `/sync-check`, `/visual-check`, `/seed`, `/start`

### Skills (6)

`build`, `review`, `docs-sync`, `ads-user`, `ads-expert`, `pm-check` — plus `fix-bug`, `audit-deep`, `intelligence`, `pm`, `obsidian`.

**Overlaps:** minor. `/feature` vs `/cto {feature}` — `/cto` routes to `/feature`. `/audit` vs `/audit-deep` — clear (deep has meta-review). No meaningful redundancy.

**Under-documented:** `/seed`, `/debug`, `/visual-check` — each needs 1–2 sentences in `KOMENDY.md`.

---

## Build & packaging

`build.py` workflow:
1. Verify `frontend/` + `backend/` exist.
2. `npm install` + `npm run build` → `frontend/dist/`.
3. Clean `dist/`, `build/`, `*.spec`.
4. PyInstaller `--onefile --windowed` with `--add-data frontend/dist;frontend/dist` and `--exclude-module pytest,scipy,sklearn,matplotlib`.
5. Report size.

| Property | Value |
|----------|-------|
| Format | Single `.exe` (portable, no installer) |
| Size | ~150 MB |
| Code signing | **None** |
| Compression | None |
| Installer | None (no Start Menu / uninstall) |
| Distribution | Manual copy |

**Gaps:** no version bumping, no changelog generation, no notarisation. Windows SmartScreen will warn "unknown publisher" on first run — ~30–50 % of users abandon at that step in consumer software.

---

## Hot reload & dev ergonomics

- **Backend:** `uvicorn --reload` + watchfiles. Schema changes still require manual DB drop because `database.py` imports `seed.py` at init (Alembic not used).
- **Frontend:** Vite HMR for JSX/CSS. Smart-quote detector fires on save — annoying if you have "smart quotes" auto-insert on in your editor.
- **Vite proxy** routes `/api/*` to `:8000`. Fine.

---

## Database reseed workflow

Today:

1. Delete `backend/data/google_ads_app.db`.
2. Restart backend → `database.py` runs `seed.py` → DB recreated with default clients (Sushi Naka, Klimfix).

Pain points:

- No Alembic despite being in `requirements.txt`.
- Hardcoded seed in `database.py` → can't skip seeding or run incremental migrations.
- No dev/prod toggle on DB path (same relative path for both).
- No rollback; seed corruption → manual intervention.

`/seed` command exists but not documented in `KOMENDY.md`.

---

## Testing ergonomics

### Backend (pytest)

| Aspect | Status |
|--------|--------|
| Runner | `pytest` 8.3.4 |
| Tests | **701** |
| Watch mode | ❌ (must re-run manually) |
| Parallel | ❌ |
| Filter by name | ✅ `pytest -k` |
| Coverage | ❌ no `coverage.py` |
| `pytest.ini` / `pyproject.toml` config | ❌ |
| Async | ✅ `pytest-asyncio` |

### Frontend

| Aspect | Status |
|--------|--------|
| Unit | ✅ vitest |
| E2E | ✅ Playwright (Chromium only, screenshot-on-fail, traces) |
| Watch | ❌ one-shot vitest |
| Parallel | ✅ Playwright workers |
| Multi-browser | ❌ Chromium only |

Running a single test:

```bash
cd backend && pytest tests/test_analytics_endpoints.py::test_cost_weighted_penalty_smaller_for_tiny_campaign -xvs
```

**Friction:** no watch mode anywhere → no tight TDD loop. No coverage gate → can't enforce ≥ 80%.

---

## Cross-platform viability — Windows-only today

| Component | Windows | macOS | Linux | Blocker |
|-----------|---------|-------|-------|---------|
| PyWebView | ✅ | ✅ | ✅ (GTK) | None |
| FastAPI + uvicorn | ✅ | ✅ | ✅ | None |
| React + Vite | ✅ | ✅ | ✅ | None |
| `keyring` → Windows Credential Manager | ✅ | ❌ | ❌ | **Critical** |
| `.bat` launchers | ✅ | ❌ | ❌ | Medium (needs `.sh` twins) |
| PyInstaller `.exe` | ✅ | ❌ (needs `.app`) | ❌ (needs AppImage) | Medium |

**Failure mode on macOS/Linux:**
1. Clone + install dependencies succeed.
2. Run `main.py`.
3. `backend/app/dependencies/auth.py` hits `keyring.get_password(...)`.
4. Mac/Linux `keyring` backend can't resolve → crash.

**Fix (4–6 hours):**
- Abstract credential storage behind a `CredentialProvider` interface.
- Windows → `keyring` backend.
- Elsewhere → `python-dotenv` encrypted file.
- `INSTALL.md` with per-platform steps.

---

## Environment management

| Concern | Today |
|---------|-------|
| Google OAuth credentials | Windows Credential Manager (`keyring`) ✅ |
| Google Ads secrets | `backend/.env` — git-ignored ✅ |
| DB path | Hardcoded relative ⚠️ |
| API port | Hardcoded 8000 ⚠️ |
| Frontend port | Hardcoded 5173 ⚠️ |
| Dev vs prod toggle | Implicit (demo_guard) ⚠️ |
| `.env.example` in repo | ❌ (`KONFIGURACJA_GOOGLE_ADS.bat` creates it) |

No `--port` flag, no `--debug` flag. Port collision → silent hang or cryptic error.

---

## Debug workflow

- Backend: loguru + uvicorn logs → stdout. No structured JSON export by default.
- Frontend: console + DevTools.
- FastAPI Swagger at `/docs`.
- `/debug` Claude command for triage.
- **Missing:** `--debug` CLI flag, request-ID tracking, crash reporter on frontend.

---

## Onboarding friction

| What exists | What's missing |
|-------------|----------------|
| `CLAUDE.md` (Polish) | `README.md` (English, top-level) |
| `AGENTS.md`, `KOMENDY.md` | `INSTALL.md` (per-platform) |
| `JAK_ZDOBYC_CREDENTIALS.md` | `DEV_SETUP.md` ("first 30 minutes") |
| `URUCHOM_APLIKACJE.bat` + `/start` command (redundant) | Architecture diagram |
| `PROGRESS.md` (82 KB) | Unified "start here" entry point |

English-speaking developer lands on the repo root, sees `.bat` files and Polish READMEs, and stalls. Writing an English `README.md` is **the single highest-impact DX change in this audit** — 2 hours of work, opens the codebase to a ~10× larger contributor pool.

---

## Top 10 DX fixes (impact × effort)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Write top-level `README.md` (English, "clone → dev server in 5 min") | 2 h | High — removes "where do I start?" |
| 2 | Add GitHub Actions: pytest on PR + build `.exe` + upload artifact | 12 h | High — prevents broken pushes, enables releases |
| 3 | Cross-platform credential abstraction (keyring + dotenv fallback) | 4 h | High — unblocks macOS/Linux devs |
| 4 | Alembic migrations (replace hardcoded seed) | 8 h | High — zero-downtime schema evolution |
| 5 | Port-collision auto-kill or `--port` flag | 2 h | Medium — saves 5–10 min per stalled startup |
| 6 | pytest watch mode (pytest-watch or entr) + `npm run test:watch` | 1 h | Medium — enables TDD |
| 7 | Code signing + `.msi` installer (WiX or signtool) | 6 h | Medium — removes SmartScreen warning for non-technical users |
| 8 | Deduplicate startup (retire `URUCHOM_APLIKACJE.bat` in favour of `/start`) | 30 min | Low — reduces confusion |
| 9 | Allow `pre-push` gate bypass on draft PRs / feature branches | 1 h | Low — cuts feature-branch friction |
| 10 | Structured JSON logging + `--log-level` flag | 2 h | Low — improves debugging |

**This week:** #1, #3, #5, #6 — seven hours of work, dramatically better DX.
**Next sprint:** #2, #4 — another 20 hours; now you have a CI and migrations.

---

## Command cleanup recommendations

- Document `/seed`, `/debug`, `/visual-check` in `KOMENDY.md` (one line each).
- Keep `/feature` and `/cto {feature}` both — `/cto` is a router, valid pattern.
- Archive `/competitor` if unused after 90 days (used once on 2026-03-30).
- Clarify whether `/sprint` is independent of `/ads-verify` or a step inside it — rename if the latter.

---

## Scorecard

| Dimension | Status | Score |
|-----------|--------|-------|
| Time-to-first-run | 25–35 min | 6/10 |
| CI/CD | None | 2/10 |
| Build automation | `build.py` works | 7/10 |
| Hot reload | Good (uvicorn + vite) | 8/10 |
| Testing UX | 701 tests, no watch | 5/10 |
| Reseed workflow | Manual + hardcoded | 3/10 |
| Cross-platform | Windows-only | 2/10 |
| Onboarding docs | Polish-only, fragmented | 5/10 |
| Claude integration | Mature, tiered | 9/10 |
| Dependencies | pip + npm, no uv/pnpm | 6/10 |
| **Overall DX** | | **5.5 / 10 (C+)** |

---

## Bottom line

Claude Code is doing the job of a CI pipeline here, and doing it well — but the project has reached the size where that's no longer enough. The three foundational gaps (no README, no real CI, no cross-platform support) are each a half-day of work and together unlock almost everything else: external contributors, external code review, external tooling. Write the README first.
