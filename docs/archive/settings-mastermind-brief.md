# Feature Spec: Settings — Marketing Mastermind Brief
generated: 2026-04-10 | author: PM Agent | status: ready

## Skad to przyszlo
CEO Decision (PIVOT from settings-hub-p0-fixes): "Settings przestaje być operational hub
(który był w 80% duplikatem Dashboard/Daily Audit/Kampanie/Monitoring/Historia zmian)
i staje się marketing mastermind brief — miejsce pure strategic context: kim jest
klient, jaka jest nasza strategia, co działa/nie działa, tone of voice, roadmap,
log decyzji AI."

User feedback bezpośredni: "Ja tu nie chce żadnych wyników, czy syncrho działa to
jest w innym miejscu. Potrzebuję masterminda marketingowego na temat klienta — jak
byśmy go briefowali."

5 odpowiedzi usera na CEO pytania:
1. DELETE częściowy: Konto/Synchronizacja/Połączenia cards usunięte. Konwersje zostaje ALE jako interfejs celów (checkbox priority_conversions).
2. Storage: nowa JSON kolumna `strategy_context` (separacja od business_rules).
3. Scope: Full 5 sekcji, L task ~6-7h — user explicitly approved.
4. Raw textarea dla Strategia/Roadmap z myślą o przyszłej Obsidian integration (markdown-friendly).
5. Log decyzji READ-ONLY w MVP, pisany przez AI w v2 ("nie przeze mnie tylko AI").

Intelligence signal: Gap analysis vs inne zakładki wykazał że strategiczny kontekst
klienta (strategia narrative, decision log z uzasadnieniem, lessons learned, brand
voice, roadmap) **nie jest nigdzie w aplikacji**. Jedyne pola zbliżone to
`target_audience` i `usp` (pojedyncze stringi) + `notes` (free text). Żadnej struktury,
żadnego loga decyzji, żadnej wiedzy instytucjonalnej. To jest unikalna wartość którą
Settings może przynieść bez duplikowania reszty aplikacji.

## User Story
Jako Kuba zarządzający 15 kontami klientów, gdzie każdy klient ma unikalną strategię,
brand, tone of voice i historię decyzji,
chcę mieć w jednym miejscu kompletny brief strategiczny o kliencie (strategia, roadmap,
wnioski, brand voice, zakazy, cele konwersji) zapisany jako structured context,
żeby w 60 sekund zbriefować się (lub nowego członka zespołu) po tygodniu nieobecności
i żeby przyszły AI agent miał całkowity kontekst klienta do rekomendacji i raportów,
bez powielania danych operacyjnych które już są w Dashboard/Kampanie/Rekomendacje.

## Architektura — kluczowe decyzje

**Storage:** Nowa JSON kolumna `strategy_context` na `Client` model. Dodawana automatycznie
przez `_ensure_sqlite_columns()` w `database.py` przy starcie (wzór: `currency`). Zero
manualnej migracji. Istniejące klienty dostaną default empty dict.

**Separacja semantyczna od business_rules:**
- `business_rules` = operational constraints (min_roas, max_daily_budget, target_cpa,
  target_roas, ltv, margin, brand_terms, priority_conversions, safety_limits)
- `strategy_context` = strategic narrative + journal (strategy_narrative, roadmap,
  decisions_log, lessons_learned, brand_voice, restrictions)

Dwa różne use cases: business_rules jest konsumowany przez rules engine i walidatory
operacyjne; strategy_context jest konsumowany przez LLM jako prompt context i przez
Obsidian sync w przyszłości.

**Endpoint `/clients/{id}/health` — zachowujemy** (ma działające testy, nie usuwamy
working code). Frontend używa tylko sekcji `conversion_tracking` z response'u dla
`ConversionGoalsSection`. Sekcje `sync_health` i `account_metadata` zostają w response
ale nie są konsumowane przez UI.

**ClientHealthSection.jsx → ConversionGoalsSection.jsx** — rename pliku, całkowita
zmiana zawartości. Stary komponent wyświetlał 4 karty operacyjne; nowy jest sekcją
full-width pełniącą rolę goal-setting interface.

## Acceptance Criteria

### Backend — strategy_context storage

- [ ] **AC1 — Auto-migration**: Nowa kolumna `strategy_context TEXT` dodawana automatycznie przez `_ensure_sqlite_columns()` w `backend/app/database.py`. Istniejące klienty mają wartość default `{}` po pierwszym starcie. Nowa kolumna nie powoduje startup errorów dla istniejących baz.
- [ ] **AC2 — Client model field**: `Client.strategy_context` jako `Column(JSON, nullable=True, default=dict)` w `backend/app/models/client.py`.
- [ ] **AC3 — Pydantic schemas**: W `backend/app/schemas/client.py` dodać:
  - `LessonEntry` (`type: Literal["win","loss","test"]`, `title ≤ 200`, `description ≤ 2000`, `date: date`)
  - `DecisionLogEntry` (`timestamp: datetime`, `title ≤ 200`, `decision ≤ 500`, `rationale ≤ 2000`, `validation_result: Optional[str]`)
  - `StrategyContext` (`strategy_narrative ≤ 10000`, `roadmap ≤ 10000`, `decisions_log: list[DecisionLogEntry] (max 500)`, `lessons_learned: list[LessonEntry] (max 200)`, `brand_voice ≤ 5000`, `restrictions ≤ 5000`)
  - `ClientBase`, `ClientUpdate`, `ClientResponse` zaktualizowane o `strategy_context: Optional[StrategyContext] = None`
- [ ] **AC4 — Round-trip via PATCH/GET**: `PATCH /clients/{id}` z dowolnym fragmentem `strategy_context` (np. tylko `strategy_narrative`) poprawnie mergeuje z istniejącym stanem i zwraca pełny `strategy_context` przy następnym `GET /clients/{id}`. Partial update nie nadpisuje innych pól.
- [ ] **AC5 — Length validation**: 
  - `strategy_narrative > 10000 chars` → HTTP 422
  - `roadmap > 10000 chars` → HTTP 422
  - `brand_voice > 5000 chars` → HTTP 422
  - `restrictions > 5000 chars` → HTTP 422
  - `lessons_learned: [{description: "x" * 2001}]` → HTTP 422
  - `len(lessons_learned) > 200` → HTTP 422
  - `len(decisions_log) > 500` → HTTP 422
- [ ] **AC6 — Enum validation**: `LessonEntry.type` poza `{"win","loss","test"}` → HTTP 422.
- [ ] **AC7 — DecisionLog AI write path**: PATCH z `decisions_log: [{timestamp: "2026-04-10T10:00:00Z", title: "AI decided X", decision: "pause campaign Y", rationale: "CPA > target", validation_result: null}]` zapisuje i zwraca poprawnie — path pod przyszłe AI-pisanie.

### Frontend — ConversionGoalsSection (reworked Konwersje)

- [ ] **AC8 — ConversionGoalsSection renders**: Nowy komponent `frontend/src/components/settings/ConversionGoalsSection.jsx` renderuje się na górze Settings.jsx jako full-width sekcja z tytułem "Cele konwersji". Komponent fetchuje dane przez istniejący `getClientHealth(clientId)`, używa tylko `conversion_tracking.actions`.
- [ ] **AC9 — Checkbox selection bound to priority_conversions**: Każdy wiersz listy ma checkbox. Checked state = obecność `action.name` w `formData.business_rules.priority_conversions` (prop passed from Settings.jsx). Toggle przechodzi przez callback `onTogglePriority(name)` który w Settings.jsx updatuje `formData.business_rules.priority_conversions` i ustawia `isDirty=true`. Zapis dopiero po kliknięciu "Zapisz" (używamy istniejącego save flow, nie auto-save).
- [ ] **AC10 — Sort by priority first**: Lista sortowana tak że wszystkie `priority_conversions` są na górze, pozostałe poniżej. Sortowanie stabilne (nie skacze przy toggle).
- [ ] **AC11 — Empty state**: Gdy `conversion_tracking.actions` jest puste, sekcja pokazuje `"Brak aktywnych konwersji — sprawdź konfigurację konta w Google Ads"`.
- [ ] **AC12 — No duplication of removed cards**: Sekcje "Konto", "Synchronizacja" (jako karta), "Połączenia" NIE istnieją w `ConversionGoalsSection.jsx`. Żadne z tych danych (customer_id, timezone, last_sync, linked_accounts) nie są renderowane w komponencie.

### Frontend — Brief mastermind sekcje (5)

- [ ] **AC13 — Sekcja 1 "Strategia marketingowa"**: Jeden textarea (min 8 rows, max 40 rows z auto-resize) bound do `formData.strategy_context.strategy_narrative`. Placeholder: "Jaka jest nasza strategia dla tego klienta? Positioning, target personas, GTM approach, długoterminowe cele...". Description: "Narrative dla teamu i AI — markdown dozwolony, w przyszłości sync z Obsidian".
- [ ] **AC14 — Sekcja 2 "Plan działań / Roadmap"**: Identyczny textarea bound do `formData.strategy_context.roadmap`. Placeholder: "Co planujemy w najbliższych tygodniach/kwartale? Nadchodzące testy, seasonal campaigns, priorytety...".
- [ ] **AC15 — Sekcja 3 "Log decyzji" read-only**: Sekcja renderuje listę wpisów z `formData.strategy_context.decisions_log`. Gdy lista pusta → pokazuje info banner: "Log decyzji jest zapisywany automatycznie przez AI agent po każdej analizie i zmianie. AI zostanie dołączony w v2 — obecnie sekcja jest pusta." Brak UI do manualnego dodawania/edycji wpisów. Gdy lista niepusta (AI w v2) — każdy wpis ma: timestamp sformatowany w pl-PL, title jako h4, decision jako paragraf, rationale jako mniejszy tekst, validation_result jako badge jeśli obecny.
- [ ] **AC16 — Sekcja 4 "Wnioski i lessons learned"**: 
  - Form "Dodaj wniosek": dropdown `type` (Win ✓ / Loss ✗ / Test ⚗), input `title`, textarea `description`, date picker `date` (default today), przycisk "Dodaj"
  - Walidacja frontend: title required, description required (min 10 chars), max 200 title, max 2000 description
  - Po kliknięciu "Dodaj" wpis dodaje się do `formData.strategy_context.lessons_learned` (formularz resetuje), `isDirty=true`, zapis dopiero po "Zapisz"
  - Lista istniejących wpisów grouped by type (Wins pierwsza, Losses druga, Tests trzecia), sortowana descending by date w każdej grupie
  - Każdy wpis: ikona type + title + description (truncated do 150 chars, expand on click) + data + przycisk "Usuń" z window.confirm
  - Przycisk "Usuń" usuwa entry z array, `isDirty=true`, zapis po "Zapisz"
  - Brak edycji istniejących wpisów (append-only model)
- [ ] **AC17 — Sekcja 5 "Brand voice & zakazy"**: 2 textareas w grid `1fr 1fr` (desktop) / `1fr` (mobile):
  - Lewa: "Tone of voice" bound do `strategy_context.brand_voice`, min 4 rows, placeholder "Jak piszemy reklamy dla tego klienta? Język, styl, energia..."
  - Prawa: "Ograniczenia / Zakazy" bound do `strategy_context.restrictions`, min 4 rows, placeholder "Czego unikamy? Forbidden claims, competitors nieakceptowani, zakazane słowa..."

### Frontend — Settings.jsx integration

- [ ] **AC18 — Porządek sekcji Settings.jsx**: Sekcje renderowane w dokładnie tym porządku:
  1. Cele konwersji (ConversionGoalsSection)
  2. Informacje ogólne (existing)
  3. Strategia i konkurencja (existing)
  4. Strategia marketingowa (NEW)
  5. Plan działań / Roadmap (NEW)
  6. Log decyzji (NEW)
  7. Wnioski i lessons learned (NEW)
  8. Brand voice & zakazy (NEW)
  9. Reguły biznesowe (existing)
  10. Limity bezpieczeństwa (existing)
  11. Synchronizacja (existing scheduled config — nie mylić z usuniętą kartą z ClientHealthSection)
  12. Konta MCC (existing)
  13. Twardy reset (existing)
- [ ] **AC19 — Visual grouping**: Pomiędzy sekcją 8 a 9 pojawia się wizualny separator + nieklikalny header "Execution" (lub równoważny) oddzielający brief strategiczny od konfiguracji operacyjnej. Pomiędzy headerem strony a sekcją 1 pojawia się header "Brief kliencki".
- [ ] **AC20 — isDirty + Zapisz**: Każda zmiana w którejkolwiek z nowych sekcji (textarea input, lesson add/remove, priority_conversion toggle) ustawia `isDirty=true`. Przycisk "Zapisz" u góry Settings wysyła pełny `strategy_context` przez PATCH (razem z business_rules i resztą formData jak dotychczas).

### Tests

- [ ] **AC21 — Backend tests ≥ 6 new** w nowym pliku `backend/tests/test_client_strategy.py`:
  - `test_strategy_context_default_empty_for_new_client`
  - `test_strategy_context_round_trip_strategy_narrative`
  - `test_strategy_context_round_trip_lessons_add_and_remove`
  - `test_strategy_context_validation_narrative_too_long` (>10000 chars → 422)
  - `test_strategy_context_validation_lesson_invalid_type` (type="invalid" → 422)
  - `test_strategy_context_validation_too_many_lessons` (>200 entries → 422)
  - `test_strategy_context_partial_update_preserves_other_fields` (PATCH tylko roadmap, asercja że strategy_narrative i lessons_learned nie zostały wymazane)
  - `test_strategy_context_decisions_log_ai_write_path` (PATCH z decisions_log entry, asercja że zapisuje i zwraca)
- [ ] **AC22 — E2E tests ≥ 6 new** w `frontend/e2e/settings-mastermind-brief.spec.js` (nowy plik — **nie usuwaj starego settings-client-info-hub.spec.js, zamiast tego skasuj obsolete testy z poprzedniego pliku które dotyczyły usuniętych kart**):
  - `Cele konwersji section renders list with checkboxes`
  - `Toggling a conversion checkbox updates isDirty state`
  - `Strategia marketingowa textarea: type text, save, reload, verify persisted`
  - `Lessons learned: add win entry via form, verify it appears in list`
  - `Lessons learned: remove entry after confirm`
  - `Log decyzji empty state shows AI coming soon banner`
  - `Brand voice + restrictions: both textareas save round-trip`

### Ship criteria

- [ ] **AC23 — Backend pytest**: 596+ passed (nie psujemy istniejących), ≥ 6 nowych pass.
- [ ] **AC24 — Frontend vite build**: OK bez errorów i warningów (poza istniejącymi deprecation warnings).
- [ ] **AC25 — Review score**: ≥ 7/10 (code quality + security + domain).

## Edge Cases

- **Nowy klient bez strategy_context w DB** → backend zwraca `strategy_context: {strategy_narrative: null, roadmap: null, decisions_log: [], lessons_learned: [], brand_voice: null, restrictions: null}` (wszystkie optional fields są null/empty, nie missing). Frontend renderuje wszystkie sekcje z empty statami.
- **Istniejący klient z już zapisanym strategy_context przed deploymentem** (scenariusz: już ktoś ręcznie zapisał JSON w tej kolumnie) → deserializacja nie powinna crashnąć. Jeśli format nie matchuje Pydantic schema → Pydantic default + errors[] do loga backend, frontend dostaje default empty values.
- **PATCH z `strategy_context: null`** (user chce wyczyścić) → backend interpretuje jako "nie zmieniaj" (nie reset do null). Żeby wyczyścić pojedyncze pole, user wysyła `strategy_context: {strategy_narrative: null}`.
- **Strategy_narrative dokładnie 10000 chars** → akceptowany. 10001 → 422.
- **Lesson z `date` w przyszłości** → akceptowany (user może planować lessons z testów które dopiero nastąpią). Walidacja tylko format ISO date.
- **Lesson z `date` sprzed 10 lat** → akceptowany (lessons historyczne).
- **Toggle priority_conversion na konwersji która już nie istnieje w DB** (rzadki case: konwersja została usunięta w Google Ads, a my mamy ją w priority_conversions) → frontend pokazuje `⚠ Nieznana konwersja: {name}` + checkbox pozostaje enabled (można usunąć). Backend nie waliduje że nazwy są w aktualnej liście ConversionAction (to nie jest FK).
- **Duża liczba konwersji** (np. 50+ dla dużego e-commerce) → lista w ConversionGoalsSection jest skrolowalna (max-height 400px, overflow-y auto). Nie używamy virtual scroll (50 elementów nie wymaga).
- **Bardzo długa strategy_narrative (9000+ chars)** → textarea auto-resize do max 40 rows, potem scroll wewnątrz. Nie blokuje UI.
- **Usuwanie wpisu z lessons_learned tuż przed "Zapisz"** → user kliknął "Usuń", potem "Anuluj zmiany" (wróć do originalData) — wpis wraca.
- **Dwa równoległe PATCH-e na tego samego klienta** (rzadki race) → ostatni wygrywa (no optimistic locking, istniejące zachowanie). Nie adresujemy w tym sprincie.
- **AI zapisuje decisions_log entry podczas gdy user edytuje strategy_narrative** → frontend widzi stary stan decisions_log dopóki nie przeładuje klienta. Nie jest to blocker bo w MVP AI jest off.

## Out of Scope (V1)

- Markdown editor z toolbar (bold, italic, headers) — raw textarea only. Markdown pisany ręcznie działa w preview (jeśli dodamy) lub jako plain text.
- Markdown preview / render mode — textarea zostaje jako plain text edytor.
- Obsidian bi-directional sync — planowany w osobnym sprincie, raw text format ułatwia tę integrację.
- AI auto-write do decisions_log — backend path istnieje, frontend renderuje wpisy, ale aktywacja AI agenta jest w v2 (project_agent_sdk_vision.md).
- Strategy versioning (git-like history) — nie zapisujemy historii edycji pól, tylko current state.
- Export do PDF/markdown/JSON — nie w MVP. Manualny kopiuj-wklej wystarcza.
- Cross-client strategy templates ("zastosuj ten sam brand voice dla 5 klientów") — per-client only.
- Drag-drop reordering w lessons_learned — entries sortowane automatycznie by date.
- Search/filter w decisions_log — użyje się gdy będzie miał wiele wpisów (po aktywacji AI).
- Auto-save on blur — używamy istniejącego przycisku Zapisz dla spójności z innymi sekcjami.
- Rich text preview dla lesson descriptions — plain text only.
- Attachment support (screenshoty, pliki) — nie w MVP.
- Wysyłka decisions_log jako prompt context do AI (aktywacja konsumpcji) — sam storage jest gotowy, aktywacja w v2.
- Retroactive import danych z notes field — user przepisuje ręcznie jeśli chce.
- Edycja istniejących wpisów lessons_learned — append-only by design (per user).
- Per-section permissions (np. tylko admin edytuje brand_voice) — brak ról w aplikacji.

## Success Metric

Kuba otwiera Settings dla klienta którego nie ruszał tydzień i w mniej niż 60 sekund
widzi pełen strategiczny brief: zaznaczone cele konwersji, strategię marketingową,
roadmap na ten kwartał, ostatnie wnioski z testów, tone of voice. Nie przełącza się
do żadnej innej zakładki ani do zewnętrznych dokumentów (Google Docs, Notion,
Obsidian) żeby to ogarnąć. Po 5 minutach edycji Kuba klika "Zapisz" i wszystko
persistuje przez reload.

## Szacowana zlozonosc

**High (L, 6-7h, 8-10 tasków)** — user explicitly approved this as Option 1.

Breakdown:
1. Backend: column + model + auto-migration (~30min)
2. Backend: Pydantic schemas (StrategyContext, LessonEntry, DecisionLogEntry) + validators (~45min)
3. Backend: ClientBase/ClientUpdate/ClientResponse integration + partial update logic (~30min)
4. Backend: test_client_strategy.py (8 testów) (~45min)
5. Frontend: rename ClientHealthSection.jsx → ConversionGoalsSection.jsx + całkowita rewrite (~1h)
6. Frontend: integration w Settings.jsx — remove old, add conversion goals prop wiring (~30min)
7. Frontend: 5 nowych sekcji w Settings.jsx — JSX + state bindings + lesson form handlers (~1.5h)
8. Frontend: visual separatory + nieklikalne headers grouping "Brief kliencki" / "Execution" (~15min)
9. Frontend: settings-mastermind-brief.spec.js (7 testów) + cleanup starych obsolete testów (~45min)
10. Weryfikacja wizualna przeciwko realnemu backendowi + fix jakichkolwiek issues (~20min)

## Zaleznosci

### Existing (do reuse)

- `backend/app/database.py` — `_ensure_sqlite_columns()` mechanism dla auto-migration (wzór: `clients.currency`)
- `backend/app/models/client.py` — istniejący model Client z JSON columns (business_rules, seasonality, competitors)
- `backend/app/schemas/client.py` — istniejące ClientBase/Update/Response + `field_validator` pattern dla business_rules
- `backend/app/routers/clients.py` — istniejący `GET /clients/{id}`, `PATCH /clients/{id}` endpointy (nie zmieniamy)
- `backend/app/routers/clients.py` — istniejący `GET /clients/{id}/health` endpoint (zachowujemy dla conversion_tracking source)
- `backend/app/services/client_health_service.py` — istniejący serwis dla `conversion_tracking` section (nie zmieniamy)
- `backend/tests/test_client_health.py` — istniejące testy zostają (nie regresuje)
- `frontend/src/pages/Settings.jsx` — istniejący komponent z pattern `formData` / `handleChange` / `isDirty`
- `frontend/src/components/settings/ClientHealthSection.jsx` — RENAME to ConversionGoalsSection.jsx (not delete; git rename preserves history)
- `frontend/src/api.js` — istniejące `getClient(id)`, `updateClient(id, data)`, `getClientHealth(id)` (nie zmieniamy signatures)
- `frontend/src/constants/designTokens.js` — istniejące `C`, `T`, `S`, `R`, `FONT` dla styling
- `frontend/e2e/helpers.js` — istniejące `mockAuthAndClient`, `mockEmptyApi`

### New

- `backend/app/database.py` — nowy wpis w `schema_updates["clients"]["strategy_context"] = "TEXT"`
- `backend/app/models/client.py` — nowa kolumna `strategy_context = Column(JSON, nullable=True, default=dict)`
- `backend/app/schemas/client.py` — nowe klasy `LessonEntry`, `DecisionLogEntry`, `StrategyContext` + integracja w Base/Update/Response
- `backend/tests/test_client_strategy.py` — nowy plik testowy (8 testów)
- `frontend/src/components/settings/ConversionGoalsSection.jsx` — rename + rewrite z ClientHealthSection.jsx
- `frontend/e2e/settings-mastermind-brief.spec.js` — nowy plik testowy (7 testów)
- `frontend/e2e/settings-client-info-hub.spec.js` — cleanup obsolete testów (keep file dla back-compat, delete testy dotyczące usuniętych kart)

### NOT changed

- `/clients/{id}/health` backend endpoint — pozostaje jako read source dla conversion_tracking
- `client_health_service.py` — pozostaje bez zmian
- `test_client_health.py` — istniejące testy działają
- Inne zakładki aplikacji (Dashboard, Daily Audit, Kampanie, Rekomendacje, Monitoring, Historia zmian)
- Wszystkie inne istniejące sekcje Settings.jsx (Informacje ogólne, Strategia i konkurencja, Reguły biznesowe, Limity bezpieczeństwa, Synchronizacja, Konta MCC, Twardy reset)

## Auto-evaluation (gate)

| Kryterium | Status |
|---|---|
| User story | ✓ (konkretna persona + motywacja + cel) |
| Acceptance Criteria ≥ 3 | ✓ (25 AC, wszystkie mierzalne) |
| Edge Cases ≥ 2 | ✓ (11 edge cases z expected behavior) |
| Out of Scope zdefiniowane | ✓ (15 wyłączeń z uzasadnieniem) |
| Success Metric obecny | ✓ (konkretny: 60 sekund, no tab switching, persist na reload) |
| pm-context.md wzięty pod uwagę | ✓ (1-click "Zapisz", minimum friction, AI-ready structure, no config required) |

**Gate score: 9/10** — szczegółowa spec z 25 AC, precyzyjnymi length limits, explicit auto-migration path, AI-ready framing, zero ambiguity w scope.
