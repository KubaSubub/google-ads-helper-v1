# Scripts System — P0 + P1 Fixes

**Status:** Ready for /build
**Source:** CEO review 2026-04-12 (4 parallel agents: backend, frontend, domain, UX live test)
**Scope:** Naprawić wszystkie krytyczne i poważne problemy wykryte w review systemu Scripts (6 skryptów P0: A1, A2, A6, B1, C2, D1).

## Dlaczego

Live test (TestClient + client_id=4 Sushi Naka Naka) wykazał że 6/6 endpointów dry-run zwraca 200 OK, ale:
- **2 bugi P0** blokują poprawne działanie execute() (D1 + A2)
- **1 systemowa luka P1** — circuit breaker/validate_action nie działa dla scripts pipeline
- **3 skrypty bez brand/keyword protection** mogą wykluczać własne keywordy lub branded terms
- **Frontend race condition** w refreshCounts może nadpisywać counts
- **Zero test coverage** na 2,669 liniach kodu skryptów

Te naprawy są wymagane PRZED tym jak system może być oznaczony jako production-ready dla realnego klienta.

## User stories

1. **Jako PPC manager chcę** żeby D1 n-gram negative blokował waste we WSZYSTKICH kampaniach gdzie n-gram generuje koszt, nie tylko w jednej losowej — bo inaczej skrypt jest nieskuteczny.
2. **Jako PPC manager chcę** żeby A2 AD_GROUP negative level faktycznie tworzył negative na poziomie ad group w Google Ads API — nie na poziomie kampanii, jak teraz.
3. **Jako PPC manager chcę** żeby żaden skrypt NIE mógł przekroczyć dziennego limitu negatywów (`MAX_NEGATIVES_PER_DAY`) — żeby circuit breaker działał.
4. **Jako PPC manager chcę** żeby A1, A6, C2 chroniły brand terms i własne keywordy przed wykluczeniem — tak jak A2 i D1.
5. **Jako PPC manager chcę** żeby szybka zmiana clienta w /scripts nie zostawiała "brudnych" counts z poprzedniego clienta.

## Acceptance criteria

### P0 — krytyczne bugi

#### AC1. D1 cross-campaign negative push
- **Plik:** `backend/app/services/scripts/d1_ngram_waste.py`
- **Obecnie (bug linia 220-221):** `best_camp_id = max(s["campaign_ids"], key=lambda c: 1)` → losowo wybiera 1 kampanię z setu
- **Po fix:**
  - `action_payload` musi zawierać `campaign_ids: List[int]` (wszystkie kampanie gdzie n-gram generuje waste) zamiast pojedynczego `campaign_id`
  - `execute()` musi iterować po WSZYSTKICH `campaign_ids` i pushować negative do KAŻDEJ z nich
  - Keyword protection (`_check_keyword_conflict`) już jest per-kampania — zostaje bez zmian
  - ActionLog musi zapisać osobny wpis per (ngram, campaign_id) pair
  - Liczba `applied` w response = liczba campaign-ngram pairs (nie liczba unikalnych ngrams)
- **Dry_run response:** item.action_payload zawiera `campaign_ids: [1,2,3]` + `campaign_count: 3` (dla UI wyświetlenia)
- **Test:** unit test sprawdza że n-gram "dostawa" występujący w 3 kampaniach generuje 3 NegativeKeyword rows + 3 ActionLog entries.

#### AC2. A2 AD_GROUP negative branching w execute()
- **Plik:** `backend/app/services/scripts/a2_irrelevant_dictionary.py`
- **Obecnie (bug linia 481-486):** execute() zawsze wywołuje `batch_add_campaign_negatives`, nawet gdy item.action_payload.negative_level == "AD_GROUP"
- **Po fix:**
  - execute() musi rozdzielić items na 2 buckety: `campaign_level_items` i `ad_group_level_items` po `action_payload.get("negative_level")`
  - Ad-group-level items: wywołać `batch_add_ad_group_negatives(...)` z `ad_group_id` z payload
  - Campaign-level items: wywołać `batch_add_campaign_negatives(...)` (jak obecnie)
  - DB NegativeKeyword.ad_group_id i .campaign_id muszą być zgodne z tym co pushujemy do API
- **Test:** unit test sprawdza że item z `negative_level="AD_GROUP"` tworzy NegativeKeyword z non-null ad_group_id I wywołuje `batch_add_ad_group_negatives` (mock), nie `batch_add_campaign_negatives`.

### P1 — poważne

#### AC3. validate_action wired w całym scripts pipeline
- **Pliki:** wszystkie 6 skryptów + ewentualnie helper w base.py
- **Obecnie:** żaden skrypt nie wywołuje `validate_action("ADD_NEGATIVE")` ani `validate_action("ADD_KEYWORD")` przed API push. Dzienny limit `MAX_NEGATIVES_PER_DAY` z `action_executor.py` jest martwy.
- **Po fix:**
  - Dodać metodę w `ScriptBase` (base.py): `_validate_batch(self, db, action_type, count) -> Tuple[int, List[str]]` która zwraca `(allowed_count, errors)`. Wewnętrznie pyta `validate_action(db, action_type, ...)` dla każdego item i zatrzymuje się po osiągnięciu limitu.
  - Każdy skrypt przed pushem do API wywołuje `_validate_batch` — jeśli allowed_count < len(items), trymuje items do allowed_count i dopisuje error do response
  - Response execute() zawiera `circuit_breaker_limit: int` jeśli limit został osiągnięty (dla UI toast "Osiągnięto dzienny limit X negatywów")
- **Test:** unit test sprawdza że gdy `MAX_NEGATIVES_PER_DAY=5` a skrypt próbuje dodać 10 negatywów, tylko 5 jest faktycznie pushowanych + response zawiera circuit_breaker_limit=5.

#### AC4. Brand + keyword protection w A1, A6, C2
- **Pliki:**
  - `backend/app/services/scripts/a1_zero_conv_waste.py`
  - `backend/app/services/scripts/a6_non_latin_script.py`
  - `backend/app/services/scripts/c2_duplicate_coverage.py`
- **Refactor first:** przenieść `_build_brand_patterns`, `_is_brand_term`, `_check_keyword_conflict` z `a2_irrelevant_dictionary.py` do NOWEGO pliku `backend/app/services/scripts/_helpers.py` (lub dodać jako metody w `base.py`). A2 musi dalej działać bez zmian semantycznych.
- **A1 po fix:**
  - W dry_run: dodać brand protection check (`_is_brand_term`) — term matching brand pattern jest pomijany
  - W dry_run: dodać `_check_keyword_conflict` — jeśli BLOCK → pomiń term, jeśli EXACT → force match_type="EXACT"
  - params_used: dodać `brand_protection: bool` i `custom_brand_words: str` (jak w A2)
- **A6 po fix:** same logic jak A1 (brand + keyword protection)
- **C2 po fix:**
  - W dry_run: brand protection dla "loser" locations — jeśli term matching brand, pomiń cały term (nie tworzymy negative dla brandu nigdzie)
  - W dry_run: keyword protection per loser campaign — jeśli conflict BLOCK → pomiń loser location dla tego terma; jeśli EXACT (już jest default) → OK
- **A1 conversion lag guard (bonus):**
  - params_used: dodać `conversion_lag_days: int = 7` (default)
  - Jeśli `date_to >= today - conversion_lag_days` → dry_run zwraca warning w response: `warnings: ["Zakres dat obejmuje ostatnie 7 dni — zero-conv może być artefaktem conversion lag"]`
  - Termy z `date_to` w ostatnich lag_days są pomijane lub oznaczone flagą `recent: true` (decyzja: pomijać żeby nie oznaczać jako waste)
- **Test:** 3 unit testy — po 1 per skrypt, każdy sprawdza że branded term jest pomijany.

### P1 — frontend

#### AC5. Race condition w refreshCounts (ScriptsPage)
- **Plik:** `frontend/src/features/scripts/ScriptsPage.jsx` (linia ~820)
- **Obecnie:** `refreshCounts` używa `Promise.allSettled` bez AbortController. Szybka zmiana clienta → stary wynik nadpisuje nowy.
- **Po fix:** użyć wzorca `let cancelled = false; return () => { cancelled = true }` w useEffect — jak w DashboardPage.jsx. Przed każdym setState sprawdzać `if (cancelled) return`.
- **Test:** brak (E2E trudne dla race condition). Wystarczy manualna weryfikacja: zmiana clienta 3× szybko → counts ustawia się na ostatni client.

### P2 — test coverage (nie blokuje ship, ale w tym samym sprincie)

#### AC6. Unit testy dla skryptów
- **Nowe pliki:**
  - `backend/tests/test_scripts_a1.py`
  - `backend/tests/test_scripts_a2.py`
  - `backend/tests/test_scripts_a6.py`
  - `backend/tests/test_scripts_b1.py`
  - `backend/tests/test_scripts_c2.py`
  - `backend/tests/test_scripts_d1.py`
  - `backend/tests/test_scripts_helpers.py` (dla `_helpers.py`)
- **Minimum coverage per skrypt:**
  - dry_run happy path (zwraca items)
  - dry_run z brand protection (branded term skipped)
  - dry_run z keyword protection (term ⊂ keyword → EXACT force)
  - execute() happy path (mock google_ads_service.is_connected=True)
  - execute() blocked (mock google_ads_service.is_connected=False → error)
  - circuit breaker (mock validate_action zwraca False po N itemach)
- **D1 specific:** test że n-gram w 3 kampaniach generuje 3 NegativeKeyword rows
- **A2 specific:** test że AD_GROUP level item wywołuje `batch_add_ad_group_negatives`
- **Fixture:** stwórz `backend/tests/fixtures/scripts_fixtures.py` z pomocnikiem: `create_test_client_with_data(db)` → zwraca client + campaigns + ad_groups + search_terms + keywords.

## Out of scope (odkładamy na później)

- B1 per-item ad_group scoping (P1 z review) — wymaga refactoru response contract, osobny sprint
- B1 `min_conversions=3` + `CVR > avg` wymóg — delikatne policy change, wymaga decyzji produktowej
- A2 short-word filter tuning — cosmetic
- D1 stop words PL expansion — cosmetic
- C2 keeper CPA tiebreaker — cosmetic
- A2 latency profiling (2.25s) — pod progiem 3s, odkładamy
- ScriptsPage.jsx refactor (985 linii → mniejsze komponenty) — osobny sprint, strukturalny
- Dead code cleanup w DashboardPage (legacy Quick Scripts state) — minor, osobny commit

## Definition of Done

- [ ] 2 P0 bugfixes zaimplementowane (D1 cross-campaign + A2 AD_GROUP branching)
- [ ] validate_action wired w 6 skryptach (base.py helper + call sites)
- [ ] Brand + keyword protection w A1, A6, C2 (z refactorem helperów do `_helpers.py`)
- [ ] A1 conversion lag guard (7-dniowy warning w dry_run)
- [ ] Frontend: race condition w refreshCounts fixed
- [ ] Unit testy: po 5+ testów per skrypt (min 30+ nowych testów)
- [ ] `cd backend && pytest` → zielony
- [ ] `cd frontend && npm run build` → OK
- [ ] Live dry-run 6/6 skryptów na client_id=4 → 200 OK, kompletność jak przed fix
- [ ] Review agenty: code-quality ≥7/10, security ≥7/10, domain ≥8/10
- [ ] Commit + push (po pm-check gate)

## Gate 7/10

Spec score: **8.5/10** (konkretne AC, exact line numbers, test plan, DoD, scope control). Gotowe do `/build`.
