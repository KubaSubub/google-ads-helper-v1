# GAH Build Pipeline — Strategia FINAL
*Wersja: 2.0 | Data: 2026-04-09 | Status: gotowe do implementacji w Claude Code*

---

## Decyzje strategiczne (zamknięte)

| # | Wątpliwość | Decyzja |
|---|---|---|
| 1 | Kto decyduje o scope V1? | PM decyduje samodzielnie — dowozi bez approval gate |
| 2 | Intelligence TTL | On-demand (trigger ręczny lub CEO) — cron opcjonalnie w przyszłości |
| 3 | Ocena jakości Intelligence | CEO loguje prosty flag: czy brief wpłynął na decyzję (tak/nie) |
| 4 | Stare specyfikacje | Auto-archiwizacja po SHIP → `docs/specs/archive/` |
| 5 | Approval CEO przed Engineering | CEO decyduje samodzielnie — brak veto Kuby |
| 6 | Model kosztowy przy skalowaniu | Ignorujemy — narzędzie wewnętrzne |

---

## Twoja rola w systemie

Nie jesteś częścią pipeline'u — jesteś **nad nim**.

| Rola | Co robisz |
|---|---|
| **Prezes Zarządu** | Ustalasz kierunek, akceptujesz wyniki, wchodzisz tylko przy eskalacji |
| **End User** | Używasz GAH codziennie — twoja perspektywa zakodowana w `pm-context.md` |

Wchodzisz gdy: (1) loop wyczerpał max iteracje i eskaluje, (2) chcesz dać nowy kierunek do CEO.

---

## Org chart — 5 działów

```
Kuba (Prezes + End User)
  └── CEO Agent
        ├── Intelligence    ← NOWY
        ├── Product / PM    ← NOWY (krytyczna luka)
        ├── Engineering     ← istnieje
        ├── Quality         ← istnieje
        └── Domain          ← istnieje
```

---

## CEO Agent ✅ (zaktualizowany)

**Rola:** Nie koduje. Czyta stan projektu + Intelligence brief, decyduje co budować, deleguje do PM.

**Wejścia:**
- `PROGRESS.md`
- `docs/reviews/`
- `docs/market-research.md` ← z Intelligence
- `DECISIONS.md`, `DEVELOPMENT_ROADMAP`, `FEATURE_SET.md`

**Logika na starcie sesji:**
```
1. Sprawdź czy docs/market-research.md istnieje i jest świeży
   → Jeśli brak lub ręczny trigger → wywołaj /intelligence (fork, czekaj)
   → Jeśli świeży → wczytaj JSON brief bezpośrednio
2. Przeanalizuj wszystkie dokumenty + brief
3. Zdecyduj CO budować i DLACZEGO
4. Zapisz do docs/ceo-log.md:
   - data, task, powód, czy brief wpłynął na decyzję (flag: tak/nie), status: STARTED
5. Deleguj do PM: "/pm build {task} — powód: {reason}"
```

**Wyjście do `docs/ceo-log.md`:**
```
[2026-04-09] Task: PDF Export | Powód: r/PPC pain + brak u konkurencji
Intelligence used: TAK | Status: STARTED → (aktualizowane na DONE/FAILED po SHIP)
```

---

## Dział Intelligence 🆕

### Architektura

```
ręczny trigger / CEO na starcie
  → /intelligence (orchestrator, fork)
      ├── Competitor Scout   (sub-fork, Haiku→Sonnet)
      ├── User Pain Scout    (sub-fork, Haiku→Sonnet)
      └── Platform Scout     (sub-fork, Sonnet)
            ↓ 3× string → merge + kompresja
      → CEO Brief JSON (~1500 tokenów)
      → zapis: docs/market-research.md + Supabase (pełny raport)
```

**Trigger:** on-demand. Brak automatycznego cron na razie.
Wywołanie: `/intelligence` lub automatycznie gdy CEO stwierdzi że brief jest nieaktualny.

### Sub-agent 1 — Competitor Scout
**Model:** Haiku (search) → Sonnet (synteza)
**Przeszukuje:** Optmyzr changelog, Adalysis release notes, Google Ads AI Max updates, ProductHunt "ppc", Groas.ai / Synter / PPC.io
**Pytania kluczowe:**
- Czy ktoś wypuścił feature który mamy w backlogu?
- Czy pojawił się nowy gracz?
- Jakie luki w rynku nadal są niezamknięte?

**Output:** max 5 insights → `[narzędzie] [co nowego] [wpływ na GAH: high/medium/low]`

### Sub-agent 2 — User Pain Scout
**Model:** Haiku (search) → Sonnet (synteza)
**Przeszukuje:** r/PPC (ostatnie 7 dni), G2 negatywne reviews Optmyzr/Adalysis, Twitter/X `#GoogleAds`, PPC Hero
**Filtr w system prompt:**
- Ignoruj: SEO content "top 10 tips"
- Priorytet: konkretne bóle operacyjne powtarzające się 2×+
- Ignoruj: pojedyncze anegdoty bez potwierdzenia

**Output:** max 5 pain points → `[ból] [częstość: high/medium] [GAH rozwiązuje: tak/nie/częściowo]`

### Sub-agent 3 — Platform Scout
**Model:** Sonnet (deprecation API może zniszczyć GAH — precyzja > koszt)
**Przeszukuje:** Google Ads API changelog (oficjalny), deprecation notices, AI Max/PMax zmiany, Google Marketing Live, MCP server updates
**Priorytety alertów:**
- 🔴 Krytyczny: deprecation API które GAH używa → action_required: true
- 🟡 Wysoki: nowe pola w raportach, nowe typy kampanii
- 🟢 Informacja: zmiany behawioralne
- ⚪ Ignoruj: UI-only zmiany

**Output:** max 5 signals → `[zmiana] [priority: critical/high/info] [action_required: true/false]`

### CEO Brief — format JSON

```json
{
  "generated_at": "2026-04-09T07:00:00",
  "triggered_by": "manual | ceo-auto",
  "top_actions": [
    "Optmyzr wypuścił search term review AI — nasz backlog priorytet 1",
    "Google Ads API v18 deprecuje reports.query w sierpniu"
  ],
  "competitor_insights": [
    { "tool": "Optmyzr", "signal": "...", "gah_impact": "high" }
  ],
  "user_pains": [
    { "pain": "search term review za wolny", "frequency": "high", "gah_solves": "partial" }
  ],
  "platform_alerts": [
    { "change": "...", "priority": "critical", "action_required": true }
  ],
  "market_summary": "2-3 zdania dla CEO. Konkretne, actionable.",
  "confidence": "high"
}
```

**Zasada kompresji:** sub-agenty eksplorują szeroko → orchestrator kompresuje → CEO dostaje wąskie + priorytetowe. CEO nigdy nie widzi surowych search results.

---

## Dział Product / PM Agent 🆕 ← KRYTYCZNA LUKA

### Dlaczego to największy problem

Bez PM: CEO mówi "zrób PDF export" → Engineering zgaduje co to znaczy (które kolumny, jaki format, edge casy, kiedy "done"). Builder albo pyta w trakcie i traci tempo, albo dostarcza coś co nie spełnia potrzeby.

### Pozycja w pipeline

```
CEO → "build X, powód: Y"
  → PM Agent (fork)
      czyta: CEO decision + market-research.md + FEATURE_SET.md + pm-context.md + PROGRESS.md
      pisze: docs/specs/{feature-slug}.md
      auto-ewaluuje spec (gate 7/10, max 2 iteracje)
  → /cto dostaje: zadanie + ścieżka do spec
```

**Spec = kontrakt dla całego pipeline'u.** Każda kolejna faza sprawdza się względem niej.

### PM Agent

**Model:** Sonnet
**Uprawnienia:** read + write (tylko `docs/specs/`)
**Scope V1:** PM decyduje samodzielnie co wchodzi — sekcja "Out of Scope" jest jego odpowiedzialnością. Brak approval gate.

### Format spec

```markdown
# Feature Spec: {nazwa}
generated: {data} | author: PM Agent | status: draft

## Skąd to przyszło
CEO Decision: "{decyzja}"
Intelligence signal: "{co mówił rynek — lub 'n/a' jeśli brief nie był dostępny}"

## User Story
Jako Kuba zarządzający kampaniami klienta,
chcę {akcja}
żeby {cel biznesowy}.

## Acceptance Criteria
- [ ] Kryterium 1 (mierzalne)
- [ ] Kryterium 2
- [ ] Kryterium 3 (minimum 3)

## Edge Cases
- Scenariusz 1 → expected behavior
- Scenariusz 2 → expected behavior (minimum 2)

## Out of Scope (V1)
- Co celowo NIE jest w tej wersji (PM decyduje samodzielnie)

## Success Metric
Jedno zdanie: jak Kuba wie że to działa bez dodatkowego pytania.

## Szacowana złożoność
Low / Medium / High — szacowana liczba tasków w FAZA 2

## Zależności
- API endpoints których wymaga (istniejące lub nowe)
- Frontend komponenty których dotyka
```

### Gate PM agenta (auto-ewaluacja)

| Kryterium | Wymagane |
|---|---|
| User story obecna | tak |
| Acceptance Criteria ≥ 3 | tak |
| Edge Cases ≥ 2 | tak |
| Out of Scope zdefiniowane | tak |
| Success Metric obecny | tak |
| pm-context.md wzięty pod uwagę | tak |

**Score < 7/10 → PM przepisuje spec (max 2 iteracje, potem eskalacja do Kuby)**

### Skip paths

| Sytuacja | PM robi |
|---|---|
| Bugfix (jasno zdefiniowany) | Uproszczona spec: tylko AC + edge cases |
| Refactor (bez nowych feature'ów) | Skip całkowicie |
| Hotfix (krytyczny bug) | Skip całkowicie |
| Gotowa spec od Kuby | Weryfikuje i uzupełnia, nie pisze od zera |

### Archiwizacja spec

Po zakończeniu FAZA 6 (SHIP) — `docs/specs/{feature}.md` automatycznie przenoszony do `docs/specs/archive/{feature}.md`. Aktywne specs w `docs/specs/` = tylko to co jest w toku.

---

## `docs/pm-context.md` — plik do napisania przez Kubę (raz, ręcznie)

To jedyny plik w całym pipeline'u którego AI nie może wygenerować. Zakodowujesz w nim co dla ciebie znaczy "done" i czego klienci oczekują.

```markdown
# PM Context — Kuba & GAH

## Kuba jako użytkownik
- PPC expert, 10+ lat, zarządza wieloma klientami jednocześnie
- Czas = główny zasób którego brakuje
- Każdy klik extra = friction który irytuje
- Nie potrzebuje tutoriali ani hand-holdingu
- Klientom wysyła raporty — oni są nietech, chcą czytelności i prostych liczb

## Definicja "done" dla typowych feature'ów
- Raport: zawiera ROAS, CPC, CTR, wydatki, konwersje. Bez tych 5 → niekompletne.
- Alert: musi mieć próg, powód i rekomendowaną akcję. Bez akcji → bezużyteczny.
- Eksport: pobieralny jednym kliknięciem, bez logowania, gotowy do wysłania.
- Dashboard widget: czytelny na laptopie 13" bez scrollowania.

## Czego Kuba NIE chce
- Feature'ów wymagających konfiguracji przed użyciem
- Powiadomień bez kontekstu ("Twoja kampania ma problem" → do śmietnika)
- "Inteligentnych" decyzji których nie można odwrócić

## Client personas (odbiorcy outputów GAH)
- Klienci agencji: nietech, czytają raporty, chcą prostych liczb i wniosków
- Kuba jako manager: efektywność > estetyka, szybkość > kompletność

## [UZUPEŁNIJ] Aktualne priorytety produktowe
<!-- Wpisz co teraz jest najważniejsze z perspektywy twojej agencji -->

## [UZUPEŁNIJ] Top 3 bóle które GAH musi rozwiązać
<!-- Konkretne rzeczy które teraz robisz ręcznie a nie powinieneś -->
```

---

## Dział Engineering ✅

- `/cto` — router (Sonnet, main context)
- **FAZA 1:** 3× Explore scouci równolegle (fork, read-only) — czytają spec z PM
  - Backend Scout: routers/, services/, models/ + spec
  - Frontend Scout: pages/, components/ + spec
  - Test Scout: tests/, e2e/ + jakie testy wynikają ze spec
- **FAZA 2:** Builder (main context)
  - Implementacja task-by-task względem Acceptance Criteria ze spec
  - PostToolUse hook: auto-test po każdej edycji (timeout 60s)
  - WIP commit po zakończeniu: `git commit -m "wip: phase-2 {task}"`

---

## Dział Quality ✅

- **FAZA 3:** 3× review agenty równolegle (fork, read-only) — sprawdzają względem spec
  - Code Quality Reviewer (Sonnet)
  - Security Reviewer (Sonnet)
  - Domain Code Reviewer (Sonnet)
  - Gate: średnia ≥ 7/10, max 3 iteracje, potem eskalacja do Kuby
- **FAZA 4:** Full test suite (pytest, timeout 600s)
  - Gate: 100% green, max 3 iteracje, potem eskalacja do Kuby

---

## Dział Domain ✅

- **FAZA 5:** 2× perspektywy równolegle (fork) — sprawdzają względem Success Metric ze spec
  - ads-user (Marek persona)
  - ads-expert (GA Partner, `criteria.md`)
  - Gate: ≥ 7/10, max 2 iteracje
  - Skip: bugfix, refactor, backend-only

---

## Ops / Ship ✅ (zaktualizowany)

**FAZA 6:**
1. Squash WIP commits: `git log --oneline | grep "^wip:" | wc -l` → `git reset --soft HEAD~N`
2. Czysty commit message z listy tasków + numer spec
3. Pre-push hook: sprawdza PM gate marker
4. Docs sync: `PROGRESS.md`, `API_ENDPOINTS.md`
5. **Archiwizacja spec:** `mv docs/specs/{feature}.md docs/specs/archive/`
6. `git push`
7. Aktualizacja `docs/ceo-log.md`: status STARTED → DONE

---

## Kompletny przepływ — end to end

```
Kuba (prezes)
  ↓ daje kierunek lub akceptuje wynik
CEO Agent
  ↓ 1. sprawdza docs/market-research.md (świeży?)
  ↓    jeśli nie/brak → /intelligence → 3× scouci → CEO Brief JSON
  ↓ 2. czyta docs + brief → decyduje CO budować
  ↓ 3. zapisuje ceo-log.md (task + powód + intelligence_used flag)
  ↓ 4. deleguje: "/pm build {task} — powód: {reason}"
PM Agent (fork)
  ↓ czyta: CEO decision + market-research.md + pm-context.md + FEATURE_SET.md + PROGRESS.md
  ↓ pisze: docs/specs/{feature-slug}.md
  ↓ auto-ewaluuje (gate 7/10, max 2 iteracje)
/cto (routing)
  ↓ task + spec path → wybiera workflow
FAZA 1 — Plan (3× scouci fork, read-only, czytają spec)
  ↓ → plan implementacji zgodny ze spec
FAZA 2 — Build (main context)
  ↓ implementacja wg Acceptance Criteria
  ↓ PostToolUse hook: auto-test (60s) → FAIL = stop
  ↓ WIP commit po zakończeniu
FAZA 3 — Verify (3× fork, równolegle, sprawdzają vs spec)
  ↓ Gate: ≥ 7/10 (max 3 iteracje → eskalacja)
FAZA 4 — Test (full suite, 600s)
  ↓ Gate: 100% green (max 3 iteracje → eskalacja)
FAZA 5 — Domain (2× fork, sprawdzają vs Success Metric ze spec)
  ↓ Gate: ≥ 7/10 (max 2 iteracje → eskalacja)  [skip: refactor/bugfix]
FAZA 6 — Ship
  ↓ squash WIP → commit → pre-push hook → docs sync
  ↓ archiwizacja spec → docs/specs/archive/
  ↓ git push
  ↓ ceo-log.md: DONE
```

---

## Nowe pliki do stworzenia

| Plik | Kto tworzy | Kiedy |
|---|---|---|
| `docs/pm-context.md` | **Kuba — ręcznie (raz przed pierwszym użyciem PM)** | Przed implementacją |
| `docs/market-research.md` | Intelligence orchestrator | Przy pierwszym /intelligence |
| `docs/specs/{feature}.md` | PM Agent | Przy każdym build |
| `docs/specs/archive/` | FAZA 6 (auto) | Po każdym SHIP |
| `docs/ceo-log.md` | CEO Agent | Przy każdej sesji |
| `.claude/skills/intelligence/SKILL.md` | Claude Code | Implementacja |
| `.claude/skills/pm/SKILL.md` | Claude Code | Implementacja |

---

## Co istnieje vs co dodać

| Komponent | Status | Uwagi |
|---|---|---|
| CEO Agent | ✅ zaktualizować | Dodać: intelligence check + ceo-log flag |
| /cto router | ✅ zaktualizować | Przyjmuje teraz task + spec path |
| 3× scouci FAZA 1 | ✅ zaktualizować | Muszą czytać spec |
| Builder + hook FAZA 2 | ✅ istnieje | Bez zmian |
| 3× review FAZA 3 | ✅ zaktualizować | Weryfikują vs spec |
| Full test suite FAZA 4 | ✅ istnieje | Bez zmian |
| Domain check FAZA 5 | ✅ zaktualizować | Weryfikuje vs Success Metric ze spec |
| Ship FAZA 6 | ✅ zaktualizować | Dodać: archiwizacja spec |
| Intelligence dept | 🆕 zbudować | Nowy SKILL.md |
| PM Agent | 🆕 zbudować | Nowy SKILL.md — priorytet #1 |
| `docs/pm-context.md` | ✍️ Kuba pisze ręcznie | Bez tego PM nie działa poprawnie |

---

## Instrukcja dla Claude Code

Implementuj w kolejności:

1. **`docs/pm-context.md`** — poczekaj na wersję od Kuby lub stwórz szkielet do uzupełnienia
2. **`.claude/skills/pm/SKILL.md`** — PM Agent (najważniejszy brakujący element)
3. **Zaktualizuj CEO** (`ceo.md`) — dodaj intelligence check + ceo-log flag
4. **`.claude/skills/intelligence/SKILL.md`** — Intelligence orchestrator + 3 sub-agenty
5. **Zaktualizuj pozostałe komendy** — /cto, scouci, reviewers, FAZA 5, FAZA 6 — żeby przyjmowały i weryfikowały spec

Przy każdej aktualizacji istniejącej komendy: zachowaj istniejącą logikę, dodaj tylko nowe kroki.

---

*Strategia zatwierdzona. Wszystkie decyzje zamknięte. Gotowe do implementacji.*
