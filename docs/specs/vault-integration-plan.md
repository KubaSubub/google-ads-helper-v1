---
type: design-doc
status: v2
created: 2026-04-16
updated: 2026-04-16
vision_source: "[[GAH - Wizja samouczącego systemu]]"
tags: [gah, vault, integration, ai, architecture]
---

# GAH × Obsidian Vault — plan integracji (v2)

> Poprzednia wersja proponowała generyczne "curated bridges".
> Ta wersja wynika bezpośrednio z [[GAH - Wizja samouczącego systemu]] — Obsidian jako **sejf operacyjny** self-learning system.

---

## Zasada nadrzędna

**Obsidian to MÓZG długoterminowy. SQLite to PAMIĘĆ ROBOCZA.**

```
SQLite (GAH)       Obsidian vault
───────────        ──────────────
Aktualny stan      Historia działań
Cache API          Wnioski końcowe
Live metrics       Lessons learned
Queue akcji        Strategia per klient
Config skryptów    Rekomendacje AI (proposed + outcome)
```

**Co NIE trafia do Obsidiana:**
- Całe SQL (za dużo, niepotrzebne)
- Raw dane z API (zostają w cache SQLite)
- Live state kampanii (zmienny, nieistotny historycznie)

**Co TRAFIA:**
- **Wnioski końcowe** każdej optymalizacji
- **Decyzje** (co i dlaczego zrobiliśmy)
- **Ewaluacja** (czy zadziałało, co się zmieniło)
- **Rekomendacje** (proposed + outcome + user verdict)

---

## Jak wykorzystujemy istniejącą infrastrukturę GAH

**Dobra wiadomość:** nie budujemy od zera. W GAH jest już:

| Element | Status | Rola w integracji |
|---|---|---|
| `Client.strategy_context` (JSON column) | ✅ zbudowane | ↔ Obsidian sync per klient |
| `StrategyContext` schema (6 pól) | ✅ zbudowane | Format danych bridge |
| Action History (historia zmian) | ✅ zbudowane | Write-back do Obsidiana per akcja |
| `agent_service.py` (Claude integrated) | ✅ zbudowane | Będzie czytał Obsidian dla kontekstu |
| Scripts engine (9 skryptów) | ✅ zbudowane | Output → vault zapis |
| Recommendation engine (34 reguły) | ✅ zbudowane | Input: vault context + API data |

**Co dobudowujemy:**
1. Sync mechanism (vault_service)
2. Write-back paths (GAH → vault)
3. Context reader (vault → AI prompt)
4. Trust/evaluation layer (v3+)

---

## Mapowanie: co gdzie zapisujemy

### 1. Brief klienta (`StrategyContext`)

**W GAH:** Settings → Mastermind Brief → edytuje 6 pól
**W Obsidian:** `02_Areas/PPC/Klienci/[klient].md` zawiera sekcje które mapują się 1:1 na `StrategyContext`:

```markdown
## 🎯 Strategia marketingowa
[strategy_narrative]

## 📅 Plan działań / Roadmap
[roadmap]

## 🗣️ Brand voice
[brand_voice]

## 🚫 Zakazy / Restrictions
[restrictions]

## 📖 Log decyzji (AI-written)
[decisions_log - lista]

## 💡 Wnioski / Lessons learned
[lessons_learned - win/loss/test]
```

**Sync:** bi-directional
- Edytujesz w Obsidianie (wygodniej pisać długie markdown) → sync do SQLite
- AI dopisuje do `decisions_log` / `lessons_learned` → widoczne w Obsidianie
- Konflikt: last-write-wins z timestampem (Obsidian ma `mtime`, SQLite ma `updated_at`)

### 2. Historia zmian (Action History)

**W GAH:** każda akcja (budget change, keyword pause, script execution) → SQLite tabela `action_history`
**W Obsidian:** zapisywane do **Daily Notes per dzień**:

`Daily Notes/2026-04-16.md`:
```markdown
## 🤖 Akcje GAH (automatycznie)

### 09:45 — Sklep XYZ
- **Skrypt A1** (zero-konwersje): spauzowano 3 słowa kluczowe
- Uzasadnienie: 14 dni > 100 kliknięć, 0 konwersji
- Koszt zaoszczędzony: ~230 zł/mies

### 14:20 — Firma ABC
- **Akcja ręczna**: zwiększono budżet PMax z 100 zł → 150 zł
- Uzasadnienie: ROAS 440% vs target 350%
- Status: waiting for 7d evaluation
```

**Sync:** write-only (GAH → Obsidian, nigdy odwrotnie)

### 3. Rekomendacje AI

**W GAH:** generator tworzy rekomendację → tabela `recommendations` w SQLite
**W Obsidian:** per klient w sekcji `## 🔮 Rekomendacje aktywne`:

```markdown
## 🔮 Rekomendacje aktywne

### 2026-04-16 — Podnieś budżet PMax
- **Confidence:** High
- **Uzasadnienie:** ROAS 440% > target 350% przez 14 dni
- **Proponowana akcja:** +50 zł budget dzienny
- **Status:** PROPOSED (oczekuje akceptacji)

### 2026-04-14 — Wyklucz "tanie" placements
- **Confidence:** Medium
- **Status:** ACCEPTED (wykonano 14.04, ewaluacja za 7 dni)
```

**Sync:** GAH zapisuje PROPOSED. User ręcznie w Obsidianie może dodawać uwagi. GAH aktualizuje status (ACCEPTED/REJECTED/EVALUATED).

### 4. Ewaluacja (self-learning core)

**W GAH:** nowy `evaluation_service` który:
- Dla każdej zaakceptowanej rekomendacji z datą T, sprawdza wyniki w T+7 dni
- Oblicza: czy metryki się poprawiły (ROAS, CPA, CTR, konwersje)?
- Zapisuje wynik w SQLite `recommendation_outcomes`
- **Zapisuje w Obsidianie:** per klient w `## 📊 Ewaluacje`

```markdown
## 📊 Ewaluacje

### 2026-04-09 — Pauzowanie 5 słów (A1)
- **Wynik (po 7d):** ROAS +12%, koszty -18%, konwersje bez zmian
- **Werdykt:** ✅ Zadziałało
- **Lesson:** Reguła A1 na tym kliencie jest wiarygodna

### 2026-04-02 — Zwiększenie bid +20% na "meble loft"
- **Wynik (po 7d):** ROAS -8%, koszty +35%, konwersje +5%
- **Werdykt:** ⚠️ Nie zadziałało jak planowane
- **Lesson:** Ten klient nie ma elastyczności na agresywny bidding — revert przy następnej okazji
```

Te lessons wchodzą do `decisions_log` i są dostępne dla AI przy następnej rekomendacji.

---

## Plan wdrożenia — 4 fazy

### Faza 1 — Read-only sync (MVP, 3-5 dni)

Minimum viable integration:

1. **`vault_service.py`** w GAH backend:
   - `read_client_brief(client_id)` — parsuje `02_Areas/PPC/Klienci/[name].md` → `StrategyContext`
   - `read_recent_actions(client_id, days=7)` — wyciąga z Daily Notes
   - `read_lessons(client_id)` — lessons_learned z brief

2. **Konfiguracja:** `VAULT_PATH` w `.env`

3. **Integracja z `agent_service.py`:** przed generowaniem raportu/rekomendacji → wrzuć vault context do promptu

4. **Endpoint `/vault/sync/client/<id>`:** manual trigger sync vault → SQLite

**Sukces:** rekomendacje AI są **wzbogacone** o Twój brief i ostatnie akcje.

### Faza 2 — Write-back (5-7 dni)

GAH zapisuje do vault:

1. **Akcja wykonana → Daily Notes append**
   - Hook w `action_executor.py` po sukcesie akcji
   - Zapis do `[VAULT]/Daily Notes/[data].md` (append do sekcji `## Akcje GAH`)

2. **Rekomendacja wygenerowana → per-klient dopisanie**
   - Hook w `recommendations.py`
   - Dopisanie do `02_Areas/PPC/Klienci/[name].md` w sekcji `## Rekomendacje aktywne`

3. **Status update rekomendacji → vault update**
   - User w GAH UI akceptuje/odrzuca → aktualizacja w vault

**Sukces:** vault rośnie automatycznie. Każda akcja GAH ma ślad.

### Faza 3 — Self-evaluation (7-10 dni)

Core wartość self-learning system:

1. **`evaluation_service.py`:**
   - Background job: co 24h sprawdza zaakceptowane rekomendacje starsze niż 7 dni
   - Porównuje metryki z T-7 vs T
   - Decyduje: zadziałało / nie / neutralne
   - Zapisuje w SQLite + vault

2. **UI:** nowa sekcja w GAH "Ewaluacje" — tabela + filtry (per klient, per typ akcji)

3. **AI prompt enhancement:** przy generowaniu nowej rekomendacji, AI dostaje historię ewaluacji — wie które typy akcji działały, które nie

**Sukces:** rekomendacje się **poprawiają** bo uczą się z historii.

### Faza 4 — "Optymalizuj" button (miesiące)

Duża roboty, ale wtedy GAH osiąga wizję v5+:

1. **Orchestrator service:** jeden endpoint `/optimize/run/<client_id>` który:
   - Odpala wszystkie skrypty
   - Czyta vault (historia, lessons, brief)
   - Generuje rekomendacje
   - Ewaluuje poprzednie
   - Zwraca pełny brief: "oto co zrobiłem, oto co proponuję"

2. **Trust tiers:**
   - Niski (negatywne słowa) → auto-execute
   - Średni → 1-click approval
   - Wysoki (budget >20%, bidding strategy) → manual review

**Sukces:** click "Optymalizuj" → pełna pętla działa.

---

## Kluczowe decyzje techniczne

### Jak synchronizujemy: filesystem vs DB

**MVP (Faza 1-2):** **Direct filesystem reads/writes.**

- GAH backend ma ścieżkę do vault
- Parsuje `.md` (markdown + frontmatter)
- Zapisuje nowe `.md` lub appenduje do istniejących
- Zero dodatkowej infrastruktury

**Later (Faza 3+):** rozważyć cache layer w SQLite dla speed (ale source of truth = vault files).

### Format bridges: frontmatter + sekcje

Każdy plik klienta w vault ma **strukturowany frontmatter** dla GAH:

```yaml
---
type: client
klient: Sklep XYZ
gah_client_id: 3
branża: e-commerce
budżet: 5000
status: aktywny
tagi-kampanii: [search, pmax]
---
```

I **nagłówki H2** oznaczone jako "bridge sections":
- `## 🎯 Strategia marketingowa` → `strategy_narrative`
- `## 📅 Plan działań / Roadmap` → `roadmap`
- itd.

GAH parsuje tylko te sekcje. Reszta pliku (notatki Twoje, myśli, meetingi) — **GAH ignoruje**.

### Identyfikator klienta

Vault używa **nazwy klienta** (human-friendly).
GAH używa **client_id** (numeryczne).

Mapowanie przez pole `gah_client_id` w frontmatter. Jeśli brak — sync nie działa (świadomie, żeby nie zgadywać).

---

## Ryzyka

| Ryzyko | Mitigacja |
|---|---|
| Konflikt: zmieniam w GAH i Obsidianie równocześnie | Last-write-wins z timestampem. Rzadkie w praktyce (solo user). |
| Zepsuty parse markdown → crash sync | Graceful: log error, zwróć pustą wartość, powiadom usera. |
| Vault niedostępny | GAH działa bez vault context (fallback do generycznego promptu). |
| Jakub zmieni strukturę vault | Wersjonowanie schematu + test health check. |
| Duża historia → wolne parse | Filtr po dacie, limit N ostatnich akcji. |

---

## Zakazy (explicit)

- **NIE synchronizować raw SQL** do Obsidiana
- **NIE pisać w vault arbitrarily** — tylko do oznaczonych sekcji (bridges)
- **NIE czytać arbitrarily** z vault — tylko `02_Areas/PPC/Klienci/` i `Daily Notes/`
- **NIE multi-tenant nigdy** — vault jest jeden, Jakuba

---

## Powiązane

- [[GAH - Wizja samouczącego systemu]] — wizja źródłowa
- [[GAH - Wizja i cel]] — krótka wersja
- [[GAH - Architektura]] — aktualny stan techniczny
- [[Profile klienta zamiast RAG]] — dlaczego taki design
- [[GAH]] — hub projektu
