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

## 6) Documentation Order

Read in this order when context is needed:
1. `AGENTS.md`
2. `PROGRESS.md`
3. `DECISIONS.md`
4. `docs/API_ENDPOINTS.md`
5. `docs/COMPLETED_FEATURES.md`
6. `docs/SOURCE_OF_TRUTH.md`
7. `docs/FEATURE_SET.md`
8. `google_ads_optimization_playbook.md`
9. `SEARCH_CAMPAIGN_WORKFLOW.md`

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
- `docs-sync.md` — synchronizacja dokumentacji z kodem
- `pm-check.md` — PM review (kod jako zrodlo prawdy)
- `done.md` — zamkniecie zadania: testy → commit → docs-sync → push (z PM gate)
- `ads-user.md` — symulacja specjalisty PPC klikajacego po zakladce (UX review oczami end-usera)
- `ads-expert.md` — ocena zakladki przez specjaliste Google Ads (potrzebnosc, kompletnosc, wartosc vs Google Ads UI)
- `ads-verify.md` — weryfikacja co z raportu ads-expert juz istnieje w kodzie + plan implementacji
- `ads-check.md` �� weryfikacja czy taski z ads-verify zostaly wdrozone (QA gate)

Use them as workflow helpers, but keep behavior aligned with `AGENTS.md`.

## 7a) Automation Pipeline

Po zakonczeniu zadania uzyj `/done`. Pipeline:
```
/done
  ├─ pytest (fail = stop)
  ├─ git commit
  ├─ /docs-sync (aktualizacja PROGRESS.md, API_ENDPOINTS.md)
  ├─ git commit docs
  └─ git push
       └─ pre-push hook: /pm-check (blokuje jesli ocena < 7/10)
```

Hooki automatyczne:
- `SessionStart` — wyswietla status projektu (ostatnie commity, TODO count, niezcommitowane pliki)
- `Stop` — wyswietla podsumowanie sesji (zmienione pliki, przypomnienie o /done)
- `post-commit` (git) — odpala /docs-sync w tle
- `pre-push` (git) — odpala /pm-check, blokuje push jesli < 7/10

## 7b) Ads Review Pipeline

Pipeline do oceny i iteracji zakladek z perspektywy specjalisty Google Ads:
```
/ads-user {tab}          ← symulacja PPCowca, notatki UX
  └─ /ads-expert {tab}   ← automatycznie: ocena ekspercka 4 kryteria
       └─ /ads-verify {tab}  ← automatycznie: plan implementacji
            └─ [dev implementuje sprinty]
                 └─ /ads-check {tab}  ← QA: czy taski wdrozone?
                      └─ /ads-user {tab}  ← automatycznie jesli GOTOWE: re-test
```

Raporty zapisywane w `docs/reviews/`:
- `ads-user-{tab}.md` — notatki usera
- `ads-expert-{tab}.md` — raport eksperta
- `ads-verify-{tab}.md` — plan implementacji ze statusami
- `ads-check-{tab}.md` — wynik weryfikacji QA

## 8) Current State

See `PROGRESS.md` for up-to-date delivery status and open work.
See `docs/DEVELOPMENT_ROADMAP_OPTIMIZATION.md` for v1.1+ roadmap with implementation status.
