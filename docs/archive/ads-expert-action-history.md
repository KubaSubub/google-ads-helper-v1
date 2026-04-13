# Ocena eksperta Google Ads — Historia akcji (Action History)
> Data: 2026-03-26 | Srednia ocena: 7.3/10 | Werdykt: ZMODYFIKOWAC

## TL;DR

Zakładka "Historia akcji" to jeden z najsilniejszych wyróżników aplikacji — unified timeline, pomiar wpływu zmian i cofanie akcji to funkcje których Google Ads UI nie oferuje w takiej formie. Backend i logika bezpieczeństwa (circuit breaker, 24h revert window) są solidne. Główne problemy: crash zakładki "Zewnętrzne", brak kluczowych filtrów (kampania, typ akcji), surowe kody zamiast polskich etykiet, oraz puste widoki na demo data dające złe pierwsze wrażenie.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 8/10 | Audit trail to "must have" w każdym narzędziu modyfikującym konto GAds. Playbook sekcja 11 wymaga śledzenia wpływu zmian. Specjalista potrzebuje tego codziennie. |
| Kompletność | 6/10 | 5 tabów zaimplementowanych, ale "Zewnętrzne" crashuje, brak filtra kampanii, brak paginacji UI, etykiety surowe (PAUSE_KEYWORD). Tabele Impact/Strategy poprawne ale puste bez realnych danych. |
| Wartość dodana vs Google Ads UI | 9/10 | Unified timeline, automatyczny pomiar delta po 7/14 dniach, cofanie akcji, diff view before/after, logowanie BLOCKED/DRY_RUN — tego nie ma w natywnym UI. Wyraźna przewaga. |
| Priorytet MVP | 6/10 | Ważna ale nie krytyczna na dzień 1. Specjalista najpierw potrzebuje dashboard + rekomendacje + keywords. Historia staje się kluczowa po 2-3 tygodniach aktywnego użytkowania. |
| **ŚREDNIA** | **7.3/10** | |

## Co robi dobrze

1. **Unified timeline** ([ActionHistory.jsx:468-486](frontend/src/pages/ActionHistory.jsx#L468-L486)) — łączenie akcji Helpera z change eventami z Google Ads API w jeden chronologiczny widok. Google Ads Change History nie pokazuje kontekstu akcji z API/narzędzi zewnętrznych. Unikalna wartość.

2. **Pomiar wpływu zmian (Wpływ zmian)** — automatyczne delty KPI (koszt, konwersje, CPA, CTR, ROAS) po 7 dniach od akcji. Playbook sekcja 11.2 wymaga "Delta KPI: before vs after (7 dni)". Zaimplementowane w [analytics_service.py:2345-2394](backend/app/services/analytics_service.py#L2345-L2394). Specjalista normalnie liczy to ręcznie w arkuszu.

3. **Cofanie akcji z safety guardem** — [action_executor.py:295-365](backend/app/services/action_executor.py#L295-L365): 24h window (ADR-007), REVERSIBLE_ACTIONS dict, blokada cofania ADD_NEGATIVE. Solidna implementacja ze wszystkimi edge case'ami.

4. **Circuit breaker** — [action_executor.py:58-117](backend/app/services/action_executor.py#L58-L117): MAX_BID_CHANGE_PCT, MAX_KEYWORD_PAUSE_PCT, MAX_NEGATIVES_PER_DAY. Logowanie BLOCKED akcji z pełnym kontekstem walidacji w `context_json`. To profesjonalny audit trail.

5. **Diff view** ([DiffView.jsx](frontend/src/components/DiffView.jsx)) — rozwinięcie wpisu pokazuje diff before/after z automatyczną konwersją micros na PLN. Google Ads Change History pokazuje "bid changed" bez wartości.

6. **Wpływ strategii licytacji** — porównanie performance 14 dni przed/po zmianie strategii (MANUAL_CPC → TARGET_CPA). Playbook sekcja 4.4 definiuje kiedy zmieniać strategię — tu specjalista widzi czy zmiana zadziałała.

7. **Test coverage** — [test_history_router.py](backend/tests/test_history_router.py) (173 linii) + [test_actions_router.py](backend/tests/test_actions_router.py) (249 linii): unified timeline merge, revertability logic, enrichment, pagination.

## Co brakuje (krytyczne)

1. **Crash zakładki "Zewnętrzne"** — po kliknięciu taba "Zewnętrzne" strona renderuje czarny ekran. Potencjalna przyczyna: [ActionHistory.jsx:425](frontend/src/pages/ActionHistory.jsx#L425) `setExternalEvents(data.events || [])` — jeśli API zwraca pole `items` zamiast `events`, lub response interceptor nie unwrapuje `.data`. Brak try-catch wokół `groupByDate()` w useMemo ([linia 468](frontend/src/pages/ActionHistory.jsx#L468)).
   - **Playbook ref:** Śledzenie zmian zewnętrznych to podstawa audytu konta
   - **Fix:** Dodać error boundary + sprawdzić mapping pól API response vs frontend expectations

2. **Brak filtra po kampanii** — w Google Ads Change History filtrowanie po kampanii to podstawowa funkcja. W Helper mam "Typ zasobu" ale nie kampanię. Przy koncie z 8+ kampaniami to showstopper.
   - **Playbook ref:** Analiza per kampania to core workflow specjalisty
   - **Implementacja:** Endpoint `/history/` już przyjmuje `campaign_id` w query params ([history.py](backend/app/routers/history.py)), brakuje tylko dropdown w UI

3. **Surowe kody akcji w tabeli Helper** — kolumna AKCJA pokazuje `PAUSE_KEYWORD`, `UPDATE_BID` zamiast polskich etykiet. Tłumaczenia ISTNIEJĄ w `OP_LABELS` ([ActionHistory.jsx:47-61](frontend/src/pages/ActionHistory.jsx#L47-L61)) ale nie są używane w renderingu tabeli DataTable ([linia 660+](frontend/src/pages/ActionHistory.jsx#L660)).
   - **Fix:** W definicji kolumn DataTable użyć `OP_LABELS[row.action_type] || row.action_type`

4. **Niespójność nazewnictwa** — sidebar: "Historia akcji", tytuł strony: "Historia zmian". To myli użytkownika.
   - **Fix:** Ujednolicić na "Historia zmian" wszędzie (bardziej inkluzywne — obejmuje zmiany z Helpera I zewnętrzne)

## Co brakuje (nice to have)

1. **Paginacja w UI** — API zwraca `limit=50` ale brak przycisków "następna strona" ani info "1-50 z 230". Przy aktywnym koncie 50 akcji dziennie to problem.

2. **Eksport CSV** — raportowanie klientowi "co zrobiliśmy w tym miesiącu" wymaga eksportu. Playbook wspomina o weekly reports (DEVELOPMENT_ROADMAP sekcja E1) które powinny zawierać "wykonane działania (z action history)".

3. **Presety dat** — date pickery mają placeholder "dd.mm.yyyy" ale brak presetów (Dzisiaj, Wczoraj, 7 dni, 30 dni). Google Ads ma wygodne presety.

4. **Quick stats banner** — na górze: "Akcji dzisiaj: 3 | Cofniętych: 1 | Oszczędność: 45 PLN". Daje natychmiastowy kontekst.

5. **Filtr po typie akcji** — w tabeli Helper nie mogę filtrować np. tylko PAUSE_KEYWORD. Search bar to nie to samo co filtr.

6. **Alerty post-revert** — jeśli cofnąłem PAUSE_KEYWORD, po 7 dniach powiadomienie czy keyword znowu generuje koszty.

## Co usunąć/zmienić

1. **Domyślny tab "Wszystko"** — otwiera się z pustym widokiem na demo data. Zmienić domyślny na "Helper" (tam przynajmniej widać kolumny tabeli) lub "Wszystko" z fallbackiem na dane Helper jeśli brak external events.

2. **Label "Wpływ strategii"** — niejasny. Zmienić na "Wpływ strategii licytacji" — doprecyzowuje o co chodzi.

3. **Tooltips na statusach** — SUCCESS/FAILED/BLOCKED/DRY_RUN bez tooltipów. Nowy user nie wie co znaczy "BLOCKED" (=akcja zablokowana przez circuit breaker). Dodać tooltips z 1-zdaniowym wyjaśnieniem.

## Porównanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Change history lista | TAK — filtrowana po kampanii, dacie, typie zasobu | TAK — ale brak filtra kampanii, crash Zewnętrzne | GORSZE (bugi) |
| Cofanie zmian | NIE — musisz ręcznie znaleźć i przywrócić | TAK — 1 klik z 24h window | LEPSZE |
| Unified timeline (helper + manualne) | NIE — widzisz tylko swoje zmiany | TAK — łączy Helper + GAds UI + API | LEPSZE |
| Pomiar wpływu zmian (delta KPI) | NIE — musisz liczyć ręcznie | TAK — automatyczne delty po 7 dniach | LEPSZE |
| Wpływ strategii licytacji | NIE — musisz porównywać okres ręcznie | TAK — 14-dniowe porównanie | LEPSZE |
| Diff before/after | CZEŚCIOWO — "bid changed" bez wartości | TAK — pełen JSON diff z konwersją micros→PLN | LEPSZE |
| Logowanie prób nieudanych | NIE — widzisz tylko zrealizowane | TAK — BLOCKED, DRY_RUN, FAILED | LEPSZE |
| Eksport CSV/Sheets | TAK — wbudowany | NIE | GORSZE |
| Filtr po kampanii | TAK | NIE | GORSZE |
| Filtr po typie zmiany | TAK | Tylko search bar | GORSZE |

**Bilans: 6 LEPSZE, 4 GORSZE**

## Nawigacja i kontekst

- **Skąd user trafia:** Sidebar → DZIAŁANIA → Historia akcji. Także po kliknięciu "Zastosuj" w Rekomendacjach (akcja pojawia się w historii).
- **Dokąd powinien móc przejść:**
  - Z wpisu akcji → do keywordu/kampanii w odpowiedniej zakładce (deep link)
  - Z "Wpływ zmian" → do Rekomendacji (jeśli wpływ negatywny, sugestia cofnięcia)
  - Z tabeli Helper → do konkretnej rekomendacji (link po recommendation_id)
- **Brakujące połączenia:**
  - Brak deep linków do encji (kliknięcie nazwy keywordu nie przenosi do Keywords)
  - Brak linku z Dashboard → Historia akcji ("Ostatnie akcje" widget)
  - Brak linku z Rekomendacji → do historii zastosowania (po kliknięciu "applied" rekomendacji)

## Rekomendacja końcowa

**ZMODYFIKOWAC**

Zakładka ma silny fundament — unified timeline, pomiar wpływu i cofanie akcji to unikalne wartości których Google Ads UI nie oferuje. Backend (circuit breaker, revert logic, test coverage) jest profesjonalny. Główne blocker: naprawić crash "Zewnętrzne", dodać filtr kampanii, użyć polskich etykiet zamiast surowych kodów. Po tych 3 fixach zakładka staje się codziennym narzędziem kontrolnym. Nice-to-have (eksport, paginacja, presety dat) mogą poczekać na kolejne sprinty.
