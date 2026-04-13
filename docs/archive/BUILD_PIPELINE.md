# BUILD PIPELINE — Google Ads Helper v1
# Raport + Architektura Pipeline'u Budowy Aplikacji
# Data: 2026-04-08

---

## SPIS TRESCI

1. [Diagnoza — dlaczego "cos nie wypala"](#1-diagnoza)
2. [Co masz do dyspozycji w Claude Code](#2-narzedzia)
3. [Architektura pipeline'u — diagram](#3-architektura)
4. [Fazy pipeline'u — szczegolowy opis](#4-fazy)
5. [Implementacja — co zmienic](#5-implementacja)
6. [Pipeline Flow — petle i branche](#6-flow)
7. [Checklist wdrozeniowy](#7-checklist)

---

## 1. DIAGNOZA — dlaczego "cos nie wypala" {#1-diagnoza}

### Problem 1: Auto-chaining opiera sie na "probie" a nie na egzekucji

Teraz `/ads-user` konczy sie instrukcja "teraz odpal /ads-expert". Ale to jest **prosba do Claude**, nie mechanizm. Claude moze:
- Zignorowac (za duzo kontekstu)
- Zapomniéc po compaction
- Zrobic cos innego jesli user wejdzie z nowym promptem

**Fix:** Uzyj hooków `Stop` + `TaskCompleted` do wymuszania chain'ow, albo zamien na JEDEN skill ktory robi caly flow.

### Problem 2: Komendy sa w starym formacie `.claude/commands/` zamiast `.claude/skills/`

Format `commands/` to legacy. Nowoczesny format `skills/` daje:
- **Frontmatter** — model, effort, tools, context isolation
- **Supporting files** — dodatkowe pliki zaladowane na zadanie
- **Auto-invocation** — Claude sam odpala skill gdy task pasuje do opisu
- **Scoped hooks** — hooki aktywne tylko gdy skill jest aktywny
- **Tool restrictions** — np. skill review NIE moze edytowac plikow

### Problem 3: Brak izolacji kontekstu

Wszystkie komendy dzialaja w glownym oknie konwersacji. To znaczy:
- Kazdy `/review` + `/ads-expert` + `/docs-sync` **zuzywa kontekst glownej sesji**
- Po 3-4 komendach jestes na granicy compaction
- Po compaction tracisz kontekst wczesniejszych krokow

**Fix:** Skills z `context: fork` — review, docs-sync, ads-expert dzialaja jako subagencie w izolacji. Wynik wraca jako podsumowanie.

### Problem 4: Brak Task Tracking

Nie wiesz gdzie jestes w pipeline. Kazdy krok to osobne polecenie, nie ma:
- Listy krokow z postepem
- Mozliwosci wznowienia od kroku X
- Historii co przeszlo a co nie

**Fix:** System taskow (`TaskCreate/TaskUpdate`) jako kregoslup pipeline'u.

### Problem 5: Zero rownoleglej pracy

Wszystko jest sekwencyjne. A mozna:
- Backend tests + Frontend build **rownolegle**
- Security review + Code quality review + Performance review **rownolegle** (3 agenty)
- Backend scout + Frontend scout + DB scout **rownolegle** (CEO pattern)

**Fix:** Agenty w workingach (worktrees) + parallel spawning.

### Problem 6: Hooki sa "ciche" — nie wiadomo co zadzialo

Hooki dzialaja w tle, user nie widzi ich efektu w kontekscie. Post-edit-test czesto nie pokazuje wynikow bo timeout 30s jest za krotki na build.

**Fix:** Dlusze timeouty + hookSpecificOutput z czytelnym statusem.

---

## 2. CO MASZ DO DYSPOZYCJI W CLAUDE CODE {#2-narzedzia}

### Warstwa 1: HOOKS (automatyczne, event-driven)

| Hook Event | Blokujacy? | Uzycie w build pipeline |
|---|---|---|
| `SessionStart` | Nie | Status projektu, ladowanie kontekstu |
| `UserPromptSubmit` | **TAK** | Walidacja inputu (np. wymuszenie /cto jako router) |
| `PreToolUse` | **TAK** | Gate na git push, gate na niebezpieczne komendy |
| `PostToolUse` | Nie | Auto-test po edycji, trigger chain'ow |
| `Stop` | **TAK** | Wymuszenie /done jesli sa uncommitted changes |
| `SubagentStop` | **TAK** | Walidacja outputu subagenta |
| `TaskCompleted` | **TAK** | Trigger nastepnego kroku pipeline |
| `PreCompact` | Nie | Zapis kontekstu przed kompresja |

### Warstwa 2: SKILLS (workflow jako prompt)

| Feature | Stary format (commands/) | Nowy format (skills/) |
|---|---|---|
| Frontmatter | Brak | model, effort, tools, context |
| Izolacja kontekstu | Nie | `context: fork` |
| Auto-invocation | Nie | Tak (matching po description) |
| Scoped hooks | Nie | Tak |
| Supporting files | Nie | Tak (reference.md, etc.) |
| Tool restrictions | Nie | `allowed-tools: Read Grep Glob` |

### Warstwa 3: AGENTS (izolowane sub-procesy)

| Typ | Narzedzia | Uzycie |
|---|---|---|
| `Explore` | Read, Grep, Glob (read-only) | Skanowanie kodu, research |
| `Plan` | Read, Grep, Glob (read-only) | Planowanie implementacji |
| `feature-dev:code-explorer` | Read, Grep, Glob, Bash | Analiza istniejacego kodu |
| `feature-dev:code-architect` | Read, Grep, Glob, Bash | Projektowanie architektury |
| `feature-dev:code-reviewer` | Read, Grep, Glob, Bash | Code review z confidence filtering |
| `general-purpose` | Wszystkie | Ogolne zadania |
| Custom (`.claude/agents/`) | Konfigurowalne | Twoje wlasne agenty |

### Warstwa 4: TASK SYSTEM (sledzenie postepu)

```
TaskCreate → TaskGet → TaskUpdate → TaskCompleted hook
```

Kazdy task ma: name, status (pending/running/done/failed), output.
**Mozna budowac pipeline jako liste taskow z zaleznosciami.**

### Warstwa 5: WORKTREES (izolacja plikow)

```
Agent z isolation: "worktree" → oddzielna kopia repo → zmiany na osobnym branchu
```

Idealne do: parallel reviews, eksperymentalnych zmian, testow ktore moga zepsuc stan.

### Warstwa 6: CRON (periodyczne zadania w sesji)

```
/loop 5m /visual-check    ← co 5 minut sprawdza UI
/loop 10m pytest           ← co 10 minut pelen test suite
```

Dobre do: monitoring w trakcie dlugiej sesji budowania.

---

## 3. ARCHITEKTURA PIPELINE'U — DIAGRAM {#3-architektura}

### 3.1 MASTER PIPELINE — Pelny cykl budowy feature'a

```
                         ┌─────────────────────┐
                         │   USER REQUEST       │
                         │   (opis feature'a)   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         /cto (ROUTER)          │
                    │  Analizuje request, wybiera    │
                    │  sciezke i deleguje            │
                    └───────────────┬───────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                   │
                 ▼                  ▼                   ▼
         ┌──────────────┐ ┌──────────────┐  ┌──────────────┐
         │  /feature    │ │  /bugfix     │  │  /endpoint   │
         │  /front-page │ │  /debug      │  │  /refactor   │
         └──────┬───────┘ └──────┬───────┘  └──────┬───────┘
                │                │                  │
                └────────────────┼──────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 1: PLAN                 │
              │  (Plan Mode — read-only analysis)     │
              │                                       │
              │  ┌─────────┐ ┌─────────┐ ┌────────┐  │
              │  │ Backend │ │Frontend │ │ Testy  │  │
              │  │ Scout   │ │ Scout   │ │ Scout  │  │
              │  │(Explore)│ │(Explore)│ │(Explore│  │
              │  └────┬────┘ └────┬────┘ └───┬────┘  │
              │       └───────────┼──────────┘       │
              │                   ▼                   │
              │         Plan implementacji            │
              │         (lista taskow)                │
              └──────────────────┬────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 2: BUILD                │
              │  (implementacja kodu)                  │
              │                                       │
              │  Task 1 → Task 2 → Task 3 → ...      │
              │                                       │
              │  Po KAZDYM TASKU:                     │
              │  ┌──────────────────────────────────┐ │
              │  │ PostToolUse hook (auto-test)     │ │
              │  │ • Python → pytest matching test  │ │
              │  │ • JSX → vite build check         │ │
              │  └──────────────────────────────────┘ │
              └──────────────────┬────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 3: VERIFY               │
              │  (rownolegle 3 agenty)                │
              │                                       │
              │  ┌──────────┐┌──────────┐┌─────────┐ │
              │  │ CODE     ││ SECURITY ││ DOMAIN  │ │
              │  │ REVIEW   ││ REVIEW   ││ EXPERT  │ │
              │  │(reviewer)││(reviewer)││(custom) │ │
              │  │          ││          ││         │ │
              │  │ Jakosc   ││ OWASP    ││ Google  │ │
              │  │ Patterns ││ Injections│ Ads     │ │
              │  │ DRY/SOLID││ XSS/CSRF ││ Domain  │ │
              │  └────┬─────┘└────┬─────┘└────┬────┘ │
              │       └───────────┼───────────┘      │
              │                   ▼                   │
              │         Merged Review Report          │
              │         Score >= 7/10 ?               │
              │         TAK → dalej                   │
              │         NIE → wroc do FAZA 2          │
              └──────────────────┬────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 4: TEST                  │
              │  (pelny test suite, rownolegle)        │
              │                                       │
              │  ┌──────────┐  ┌───────────────────┐  │
              │  │ BACKEND  │  │   FRONTEND         │  │
              │  │ pytest   │  │   npm run build    │  │
              │  │ (503+    │  │   + Playwright     │  │
              │  │  testow) │  │   screenshots      │  │
              │  └────┬─────┘  └────────┬──────────┘  │
              │       └─────────────────┘             │
              │       Oba PASS? → dalej               │
              │       Ktorykolwiek FAIL? → FAZA 2     │
              └──────────────────┬────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 5: DOMAIN CHECK          │
              │  (specjalisci Google Ads)              │
              │  OPCJONALNIE — tylko dla UI features   │
              │                                       │
              │  /ads-user {tab}                       │
              │       │                               │
              │       ▼                               │
              │  /ads-expert {tab}                     │
              │       │                               │
              │       ▼                               │
              │  Ocena >= 7/10?                       │
              │  TAK → dalej                          │
              │  NIE → generuj plan /ads-verify       │
              │        wroc do FAZA 2 ze sprintem     │
              └──────────────────┬────────────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │          FAZA 6: SHIP                  │
              │  (/done pipeline)                      │
              │                                       │
              │  1. /commit (smart commit)             │
              │  2. /docs-sync (fork → izolowany)      │
              │  3. git commit docs                    │
              │  4. /pm-check (score >= 7/10?)         │
              │     ├─ TAK → git push                  │
              │     └─ NIE → wroc do FAZA 2            │
              └──────────────────────────────────────┘
```

### 3.2 VERIFY PHASE — Parallel Agent Architecture

```
              ┌─────────── MAIN CONTEXT ───────────┐
              │                                     │
              │   "Zrob review zmian z tego taska"  │
              │                                     │
              │   ┌─────────────────────────────┐   │
              │   │     Agent Tool (parallel)    │   │
              │   │     3 agenty naraz            │   │
              │   └──┬──────────┬──────────┬────┘   │
              │      │          │          │        │
              └──────┼──────────┼──────────┼────────┘
                     │          │          │
         ┌───────────┘          │          └───────────┐
         ▼                      ▼                      ▼
┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│  CODE QUALITY  │   │   SECURITY     │   │  DOMAIN EXPERT │
│  AGENT         │   │   AGENT        │   │  AGENT         │
│                │   │                │   │                │
│  context: fork │   │  context: fork │   │  context: fork │
│  tools: Read,  │   │  tools: Read,  │   │  tools: Read,  │
│  Grep, Glob    │   │  Grep, Glob    │   │  Grep, Glob    │
│                │   │                │   │                │
│  Sprawdza:     │   │  Sprawdza:     │   │  Sprawdza:     │
│  • Pattern     │   │  • SQL inject  │   │  • Micros OK?  │
│    matching    │   │  • XSS         │   │  • Conversions │
│  • DRY/SOLID   │   │  • CSRF        │   │    as float?   │
│  • Naming      │   │  • Auth bypass │   │  • Circuit     │
│  • Error       │   │  • Secrets in  │   │    breaker?    │
│    handling    │   │    code        │   │  • Keyring     │
│  • Dead code   │   │  • OWASP top10 │   │    storage?    │
│                │   │                │   │  • Playbook    │
│  Score: X/10   │   │  Score: X/10   │   │    alignment?  │
└───────┬────────┘   └───────┬────────┘   └───────┬────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │   MERGED REPORT              │
              │   Code: 8/10                 │
              │   Security: 9/10             │
              │   Domain: 7/10               │
              │   ─────────────────          │
              │   OVERALL: 8/10 → PASS       │
              │                              │
              │   3 findings:                │
              │   • WARNING: XYZ pattern     │
              │   • INFO: could use ABC      │
              │   • OK: domain rules met     │
              └──────────────────────────────┘
```

### 3.3 DOMAIN EXPERT PIPELINE — Ads Review Cycle

```
   ┌─────────────────────────────────────────────────────┐
   │              DOMAIN EXPERT PIPELINE                  │
   │   (tylko dla zmian w UI / frontend features)         │
   └─────────────────────────┬───────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  /ads-user {tab}             │
              │  Agent: Marek (PPC, 6 lat)   │
              │  context: fork               │
              │                              │
              │  Input:                      │
              │  • Screenshot (Playwright)   │
              │  • Frontend component        │
              │  • Backend endpoints         │
              │  • Seed data sample          │
              │                              │
              │  Output:                     │
              │  docs/reviews/ads-user-X.md  │
              └──────────────┬───────────────┘
                             │ (auto-chain)
                             ▼
              ┌──────────────────────────────┐
              │  /ads-expert {tab}           │
              │  Agent: Senior GA partner    │
              │  context: fork               │
              │                              │
              │  Input:                      │
              │  • ads-user report           │
              │  • Playbook                  │
              │  • Actual code               │
              │                              │
              │  Output:                     │
              │  docs/reviews/ads-expert-X.md│
              │  Score: N/10                 │
              └──────────────┬───────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
               Score >= 7         Score < 7
                    │                 │
                    ▼                 ▼
              ┌──────────┐    ┌──────────────────┐
              │  PASS    │    │ /ads-verify {tab} │
              │  → Ship  │    │ Generuj plan      │
              └──────────┘    │ implementacji     │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ /sprint {tab}    │
                              │ Auto-implement   │
                              │ taskow z planu   │
                              └────────┬─────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ /ads-check {tab} │
                              │ QA weryfikacja   │
                              └────────┬─────────┘
                                       │
                              ┌────────┴────────┐
                              │                 │
                           GOTOWE          BRAKUJE
                              │                 │
                              ▼                 ▼
                        ┌──────────┐    ┌──────────────┐
                        │ /ads-user│    │ Wroc do      │
                        │ re-test  │    │ /sprint      │
                        └──────────┘    └──────────────┘
```

### 3.4 TASK TRACKING — Wewnatrz kazdej fazy

```
   ┌──────────────── TASK SYSTEM ────────────────┐
   │                                              │
   │  Pipeline: "Feature: MCC billing alerts"     │
   │                                              │
   │  ┌──────────────────────────────────────┐    │
   │  │ Task 1: Plan [✓ DONE]               │    │
   │  │ Task 2: Backend service [✓ DONE]     │    │
   │  │ Task 3: Backend tests [▶ RUNNING]    │    │
   │  │ Task 4: Frontend component [○ PENDING│    │
   │  │ Task 5: Review (3 agents) [○ PENDING]│    │
   │  │ Task 6: Full test suite [○ PENDING]  │    │
   │  │ Task 7: Domain check [○ PENDING]     │    │
   │  │ Task 8: Ship (/done) [○ PENDING]     │    │
   │  └──────────────────────────────────────┘    │
   │                                              │
   │  TaskCompleted hook → trigger nastepny task  │
   │  TaskFailed → alert + retry/skip decision    │
   └──────────────────────────────────────────────┘
```

---

## 4. FAZY PIPELINE'U — SZCZEGOLOWY OPIS {#4-fazy}

### FAZA 0: ROUTING (/cto)

**Cel:** Kazdy request uzywa tego samego entry point. /cto analizuje i deleguje.

**Mechanizm:** Skill z auto-invocation
```yaml
---
name: cto
description: Route any development request to the right workflow
user-invocable: true
effort: low
model: sonnet  # szybki routing, nie potrzeba Opus
---
```

**Input:** Opis zadania od usera
**Output:** Delegacja do /feature, /bugfix, /endpoint, /refactor, /frontend-page

### FAZA 1: PLAN (read-only scouting)

**Cel:** Zanim napiszesz linie kodu — zrozum kontekst. 3 agenty rownolegle skanuja codebase.

**Mechanizm:** 3x Agent tool z `subagent_type: Explore` (parallel)

| Agent | Skanuje | Szuka |
|---|---|---|
| Backend Scout | routers/, services/, models/ | Istniejace patterny, podobne endpointy, testy |
| Frontend Scout | pages/, components/, api.js | Podobne komponenty, stan, style |
| Test Scout | tests/, e2e/ | Pokrycie, istniejace testy, fixtures |

**Output:** Plan implementacji z lista taskow, plikow do modyfikacji, patternow do nasledowania.

**Dlaczego to wazne:** Spełnia regule CLAUDE.md "Pattern Matching Rule" — znajdz 2-3 podobne komponenty ZANIM zaczniesz budowac.

### FAZA 2: BUILD (implementacja)

**Cel:** Napisz kod. Kazda zmiana jest task'iem. Hooki auto-testuja.

**Mechanizm:**
- `TaskCreate` dla kazdego kroku
- `PostToolUse` hook (post-edit-test.sh) odpala testy po kazdym Edit/Write
- Jesli test FAIL → napraw przed kolejnym taskiem

**Typowe taski:**
1. Backend model/schema (jesli nowe)
2. Backend service (logika)
3. Backend router/endpoint
4. Backend tests
5. Frontend component
6. Frontend integration (import w parent, routing)

**Regula:** Po kazdym tasku — hook uruchamia odpowiedni test. Nie idziesz dalej jesli test FAIL.

### FAZA 3: VERIFY (3 rownolegle review agenty)

**Cel:** Niezalezna weryfikacja jakosci przez 3 specjalistow. Kazdy w izolowanym kontekscie.

**Mechanizm:** 3x Agent tool, parallel, kazdy z `context: fork` + read-only tools

#### Agent 1: Code Quality Reviewer
```
Sprawdza: DRY, SOLID, naming, dead code, error handling, pattern consistency
Referencje: istniejace komponenty w repo (pattern matching)
Score: 1-10
```

#### Agent 2: Security Reviewer
```
Sprawdza: SQL injection, XSS, CSRF, auth bypass, secrets in code, OWASP top 10
Referencje: AGENTS.md guardrails
Score: 1-10
```

#### Agent 3: Domain Expert (Google Ads)
```
Sprawdza: micros handling, conversions as float, circuit breaker on writes,
          keyring storage, playbook alignment, API limits policy
Referencje: CLAUDE.md core rules, google_ads_optimization_playbook.md
Score: 1-10
```

**Gate:** Srednia >= 7/10. Jesli < 7, wypisz findings i wroc do FAZA 2.

### FAZA 4: TEST (pelny test suite)

**Cel:** End-to-end weryfikacja — backend + frontend + visual.

**Mechanizm:** 2x parallel Bash:
1. `cd backend && pytest` (pelny suite, 503+ testow)
2. `cd frontend && npm run build` (catch compile/type errors)

**Opcjonalnie:** `/visual-check {tab}` — Playwright screenshots zmienionej zakladki.

**Gate:** Oba PASS. Jesli ktorykolwiek FAIL → wroc do FAZA 2 z informacja co sie zepsulo.

### FAZA 5: DOMAIN CHECK (specjalisci Google Ads)

**Cel:** Weryfikacja przez "prawdziwego" specjaliste PPC. Tylko dla zmian UI.

**Kiedy aktywna:** Jesli zmiana dotyka `frontend/src/` (nowa strona, nowy komponent, zmiana widoku).

**Mechanizm:** Skill chain: `/ads-user` → `/ads-expert` → ewentualnie `/ads-verify` + `/sprint`

**Gate:** Ocena ads-expert >= 7/10 w kazdym z 4 kryteriow. Jesli < 7 w ktorymkolwiek → generuj plan naprawczy.

### FAZA 6: SHIP (/done)

**Cel:** Commit, dokumentacja, push z PM gate.

**Mechanizm:** Skill `/done` z nastepujacymi krokami:
1. `/commit` — inteligentny commit z conventional prefix
2. `/docs-sync` (**w izolowanym agencie** — context: fork) — aktualizacja PROGRESS.md, API_ENDPOINTS.md
3. `git commit docs` — osobny commit na docs
4. `/pm-check` — ocena PM >= 7/10 → tworzy `.claude/pm-review-pass`
5. `git push` — pre-push hook sprawdza marker

**Gate:** PM score >= 7/10. Jesli < 7 → lista problemow, wroc do FAZA 2.

---

## 5. IMPLEMENTACJA — CO ZMIENIC {#5-implementacja}

### 5.1 Migracja z commands/ do skills/

**Priorytetowe skill'e do migracji** (te ktore powinny dzialac w izolacji):

```
.claude/skills/
├── review/
│   └── SKILL.md          # context: fork, tools: Read Grep Glob (read-only!)
├── docs-sync/
│   └── SKILL.md          # context: fork, tools: Read Grep Glob Write Edit
├── ads-user/
│   └── SKILL.md          # context: fork
│   └── persona-marek.md  # supporting file z persona
├── ads-expert/
│   └── SKILL.md          # context: fork
│   └── criteria.md       # supporting file z kryteriami oceny
├── pm-check/
│   └── SKILL.md          # context: fork, tools: Read Grep Glob
└── security-review/
    └── SKILL.md          # context: fork, NOWY skill
```

**Skill'e ktore zostaja jako commands/** (bo musza edytowac pliki w glownym kontekscie):
```
.claude/commands/
├── cto.md        # router — musi delegowac w main context
├── feature.md    # implementacja — edytuje pliki
├── bugfix.md     # implementacja — edytuje pliki
├── endpoint.md   # implementacja — edytuje pliki
├── done.md       # orchestrator — wywoluje inne skill'e
├── start.md      # utility
├── seed.md       # utility
├── commit.md     # utility
└── sprint.md     # orchestrator
```

### 5.2 Nowe custom agenty

Stworz `.claude/agents/` z wyspecjalizowanymi agentami:

#### `.claude/agents/code-quality.md`
```yaml
---
name: code-quality-reviewer
description: Reviews code quality, patterns, DRY/SOLID, naming conventions
model: sonnet
tools: Read Grep Glob
effort: high
---

Jestes code quality reviewer dla Google Ads Helper.

## Kontekst projektu
- Stack: FastAPI + React + Vite + SQLite
- Pattern matching rule: kazda nowa feature powinna nasledowac 2-3 istniejace
- Import flow: utils -> config -> models -> schemas -> services -> routers

## Co sprawdzasz
1. Czy nowy kod nasleduje patterny istniejacych komponentow
2. DRY — czy nie duplikuje logiki z innego pliku
3. Naming — czy nazwy sa spojne z reszta codebase
4. Error handling — czy obsluguje edge cases
5. Dead code — czy nie zostawia zakomentowanego kodu

## Output
Zwroc JSON:
{
  "score": 8,
  "findings": [
    {"severity": "WARNING", "file": "path", "line": 42, "message": "..."},
  ],
  "summary": "Krotkie podsumowanie"
}
```

#### `.claude/agents/security-reviewer.md`
```yaml
---
name: security-reviewer
description: Reviews code for security vulnerabilities, OWASP top 10, secrets
model: sonnet
tools: Read Grep Glob
effort: high
---

Jestes security reviewer dla Google Ads Helper.

## Kontekst projektu
- Credentials: TYLKO przez Windows Credential Manager (keyring)
- Monetary values: micros (BigInteger) — conversion to float only in schema layer
- Writes: MUSZA isc przez circuit breaker (validate_action)
- DB: SQLite — unikaj SQL injection przez raw queries

## Co sprawdzasz (OWASP Top 10 + domain)
1. SQL Injection — czy uzywa ORM a nie raw SQL
2. XSS — czy React escapuje poprawnie
3. CSRF — czy endpointy maja odpowiednie guards
4. Auth bypass — czy endpointy sprawdzaja authentication
5. Secrets in code — czy nie ma hardcoded credentials
6. Monetary safety — czy micros sa poprawnie handled
7. Write safety — czy mutacje ida przez validate_action

## Output
{
  "score": 9,
  "findings": [...],
  "summary": "..."
}
```

#### `.claude/agents/domain-expert.md`
```yaml
---
name: google-ads-domain-expert
description: Reviews code for Google Ads domain correctness, playbook alignment
model: sonnet
tools: Read Grep Glob
effort: high
---

Jestes Google Ads domain expert reviewer.

## Kontekst
- Playbook: google_ads_optimization_playbook.md
- API limits: zawsze max dozwolone zakresy dat per resource type
- Conversions: MUSZA byc float (API zwraca frakcyjne)
- Cost/bid: micros (÷1,000,000)
- Writes: circuit breaker + validation

## Co sprawdzasz
1. Metryki — czy nowe endpointy zwracaja poprawne metryki GA
2. Micros — czy cost/bid w DB to integer micros
3. Conversions — czy to float a nie int
4. API version — czy uzywa poprawnej wersji (v23)
5. Playbook alignment — czy feature jest zgodna z best practices

## Output
{
  "score": 7,
  "findings": [...],
  "summary": "..."
}
```

### 5.3 Nowy orchestrator — `/build` skill

Jeden skill ktory odpala caly pipeline:

#### `.claude/skills/build/SKILL.md`
```yaml
---
name: build
description: Full build pipeline — plan, implement, verify, test, ship
user-invocable: true
effort: max
---

# BUILD PIPELINE

Jestes orchestratorem budowy feature'ow w Google Ads Helper.

## INPUT
$ARGUMENTS — opis feature'a lub buga

## PIPELINE

### KROK 1: PLAN
Uzyj 3 agentow Explore ROWNOLEGLE:
- Backend Scout: przeskanuj backend/ pod katem istniejacych patternow
- Frontend Scout: przeskanuj frontend/src/ pod katem podobnych komponentow
- Test Scout: przeskanuj backend/tests/ i frontend/e2e/ pod katem pokrycia

Na podstawie wynikow:
- Stworz liste TaskCreate z krokami implementacji
- Pokaz plan userowi, poczekaj na akceptacje

### KROK 2: BUILD
Dla kazdego taska:
- Implementuj zmiane
- PostToolUse hook auto-testuje
- TaskUpdate status na done

### KROK 3: VERIFY
Uzyj 3 agentow ROWNOLEGLE:
- code-quality-reviewer (custom agent)
- security-reviewer (custom agent)
- google-ads-domain-expert (custom agent)

Zbierz wyniki. Jesli srednia < 7/10 — napraw findings i powtorz VERIFY.

### KROK 4: TEST
Rownolegle:
- `cd backend && pytest`
- `cd frontend && npm run build`

Jesli FAIL — napraw i powtorz od KROK 2.

### KROK 5: DOMAIN CHECK (opcjonalnie)
Jesli zmiana dotyczyla frontend/:
- Odpal /ads-user na zmienionej zakladce
- Jesli ads-expert score < 7 → /ads-verify → wroc do KROK 2

### KROK 6: SHIP
- /commit (smart commit)
- /docs-sync (w fork context)
- /pm-check
- Jesli PM >= 7/10 → git push
- Jesli PM < 7/10 → pokaz problemy
```

### 5.4 Usprawnienia hookow

#### Nowy hook: `SubagentStop` — walidacja outputu agentow review

Dodaj do `settings.json`:
```json
{
  "hooks": {
    "SubagentStop": [{
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/subagent-validate.sh",
        "timeout": 5,
        "statusMessage": "Walidacja wyniku agenta..."
      }]
    }]
  }
}
```

Hook sprawdza czy agent zwrocil wymagany format (JSON ze score).

#### Ulepszony post-edit-test.sh — dluzszy timeout

Zmien timeout z 30s na 60s w settings.json. Build frontendu trwa > 30s na wiekszych projektach.

### 5.5 Przykladowy skill z izolacja: `/review`

#### `.claude/skills/review/SKILL.md`
```yaml
---
name: review
description: Code review with quality scoring - run after any code change
user-invocable: true
context: fork
allowed-tools: Read Grep Glob Agent
effort: high
model: sonnet
---

# CODE REVIEW

Przeprowadz review zmian w Google Ads Helper.

## METODA

1. Sprawdz `git diff HEAD~1` aby zobaczyc co sie zmienilo
2. Odpal 3 review agentow ROWNOLEGLE:
   - code-quality-reviewer
   - security-reviewer
   - google-ads-domain-expert
3. Zbierz wyniki i stworz merged report

## OUTPUT FORMAT

### Review Report
| Kryterium | Score | Findings |
|---|---|---|
| Code Quality | X/10 | ... |
| Security | X/10 | ... |
| Domain | X/10 | ... |
| **OVERALL** | **X/10** | |

### Findings (posortowane wg severity)
CRITICAL > WARNING > INFO

### Verdict
PASS (>= 7/10) lub FAIL (< 7/10) z lista co naprawic
```

---

## 6. PIPELINE FLOW — PETLE I BRANCHE {#6-flow}

### 6.1 Flowchart decyzji

```
START
  │
  ▼
/cto (routing)
  │
  ├─ "nowa feature" ──────────────────────────────┐
  ├─ "bug" ────────────────────────────────────────┤
  ├─ "endpoint" ───────────────────────────────────┤
  ├─ "refactor" ───────────────────────────────────┤
  │                                                │
  ▼                                                ▼
PLAN (3 scouts parallel)                    PLAN (3 scouts)
  │                                                │
  ▼                                                ▼
BUILD (task-by-task)                        BUILD
  │                                                │
  ▼                                                ▼
VERIFY (3 reviewers parallel) ◄─────────── VERIFY
  │                                                │
  ├── Score < 7 → FIX → VERIFY (loop max 3x)      │
  │                                                │
  ▼                                                ▼
TEST (pytest + build parallel)              TEST
  │                                                │
  ├── FAIL → FIX → TEST (loop max 3x)             │
  │                                                │
  ▼                                                ▼
Zmiana dotyka frontend/?                    Ship path
  │                                                │
  ├── TAK → DOMAIN CHECK ──────────────────────────┤
  │   ├── Score < 7 → /ads-verify → BUILD (loop)   │
  │   └── Score >= 7 → dalej                       │
  │                                                │
  ├── NIE ──────────────────────────────────────────┤
  │                                                │
  ▼                                                ▼
SHIP (/done)                                SHIP
  │
  ├── PM < 7 → FIX → SHIP (loop max 2x)
  │
  ▼
DONE ✓
```

### 6.2 Limity petli (zabezpieczenie przed nieskonczonymi cyklami)

| Petla | Max iteracji | Co jesli limit? |
|---|---|---|
| VERIFY loop | 3 | Pokaz findings userowi, zapytaj czy kontynuowac |
| TEST loop | 3 | Pokaz bledy, zapytaj usera |
| DOMAIN loop | 2 | Pokaz raport, zapytaj usera |
| PM loop | 2 | Pokaz problemy, zapytaj usera |

### 6.3 Skroty (skip paths)

| Warunek | Mozna pominac |
|---|---|
| Tylko backend zmiana (no frontend) | Pomin DOMAIN CHECK |
| Tylko docs/tests zmiana | Pomin VERIFY (3 agenty), zrob basic review |
| Hotfix (user mowi "szybki fix") | Pomin PLAN, minimalne VERIFY |
| Refactor (no new features) | Pomin DOMAIN CHECK |

---

## 7. CHECKLIST WDROZENIOWY {#7-checklist}

### Faza 1: Quick Wins (dzis)

- [ ] Zmien timeout post-edit-test.sh z 30s na 60s
- [ ] Stworz `.claude/agents/` z 3 review agentami (code-quality, security, domain-expert)
- [ ] Zaktualizuj CLAUDE.md sekcje 7 z nowym pipeline'em

### Faza 2: Migracja Skills (1-2 sesje)

- [ ] Stworz `.claude/skills/review/SKILL.md` z `context: fork`
- [ ] Stworz `.claude/skills/docs-sync/SKILL.md` z `context: fork`
- [ ] Stworz `.claude/skills/ads-user/SKILL.md` z `context: fork` + persona.md
- [ ] Stworz `.claude/skills/ads-expert/SKILL.md` z `context: fork` + criteria.md
- [ ] Stworz `.claude/skills/pm-check/SKILL.md` z `context: fork`
- [ ] Stworz `.claude/skills/security-review/SKILL.md` z `context: fork`

### Faza 3: Orchestrator (1 sesja)

- [ ] Stworz `.claude/skills/build/SKILL.md` — master orchestrator
- [ ] Dodaj SubagentStop hook do walidacji outputu agentow
- [ ] Przetestuj pelny pipeline na prostym feature'ze

### Faza 4: Polish (ongoing)

- [ ] Dodaj `/loop` monitoring do dlugich sesji
- [ ] Stworz `.worktreeinclude` z .env i data/
- [ ] Zoptymalizuj CLAUDE.md (< 200 linii, reszta do .claude/rules/)

---

## PODSUMOWANIE

### Przed (teraz):
```
User → /feature → (implementacja w main context) → /review (main context)
  → /done → /commit → /docs-sync (main context) → git push

Problem: Wszystko w jednym kontekscie, brak izolacji, brak paralelizmu,
         chain'y oparte na "probach" nie na mechanizmach
```

### Po (docelowo):
```
User → /cto (router)
  → PLAN (3 Explore agents parallel, fork)
  → BUILD (task tracking, auto-test hooks)
  → VERIFY (3 review agents parallel, fork, read-only)
  → TEST (pytest + build parallel)
  → DOMAIN CHECK (ads-user + ads-expert, fork, opcjonalne)
  → SHIP (/done → commit → docs-sync fork → pm-check fork → push)

Korzysci:
  ✓ 3x mniej zuzycia kontekstu (fork isolation)
  ✓ 2-3x szybciej (parallel agents)
  ✓ Zawsze 3 niezalezne review (code + security + domain)
  ✓ Task tracking — wiesz gdzie jestes
  ✓ Mechaniczne chain'y (hooks) zamiast "prob" (prompts)
  ✓ Gate'y na kazdym etapie (7/10 minimum)
```
