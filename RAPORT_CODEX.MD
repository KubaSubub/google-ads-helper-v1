# RAPORT_CODEX

## 1. Executive Summary

**Werdykt:** aplikacja ma solidny szkielet produktowy i sporo zaawansowanych funkcji, ale obecnie nie spełnia w pełni własnej zasady `financial safety first` dla wszystkich ścieżek mutacji Google Ads. Największe ryzyka dotyczą automatycznych reguł, niespójnych write pathów, rozjazdu lokalnego stanu z Google Ads oraz dokumentacji, która przestała być wiarygodnym source of truth.

Stan ogólny oceniam jako **średnio-wysoki potencjał, ale z istotnym długiem operacyjnym i bezpieczeństwa wykonania**. Produkt wygląda na rozwijany szybko i szeroko, natomiast warstwa kontroli zmian i spójności kontraktów nie nadąża za zakresem funkcji.

Najważniejsze pozytywne sygnały:

- Sekrety są scentralizowane w `backend/app/services/credentials_service.py` i oparte o `keyring`, co jest zgodne z guardrailami.
- Istnieje kanoniczny pipeline wykonania akcji z `validate_action()` i logowaniem w `backend/app/services/action_executor.py`.
- Ochrona routerów przez `require_session` jest wpięta centralnie w `backend/app/main.py`.
- Repo ma szeroki surface testów backendowych i rozbudowane E2E Playwright po stronie frontendu, choć ich wartość jest ograniczana przez blokery środowiskowe i luki strategii testowej.

Najważniejsze ryzyka:

- **Krytyczne:** Automated Rules omijają `ActionExecutor`, `validate_action()`, demo guard i audit trail, a część akcji wykonują tylko lokalnie.
- **Krytyczne:** deklaracja "Every write path goes through preconditions and `validate_action()`" jest nieprawdziwa dla części realnych endpointów.
- **Wysokie:** endpoint zmiany bidding target zapisuje lokalnie przed potwierdzeniem z Google Ads, więc stan może się rozjechać.
- **Wysokie:** dokumentacja statusu i source of truth jest materialnie nieaktualna.
- **Średnie:** uruchamialność i pipeline weryfikacji są kruche; w obecnym środowisku nie udało się uruchomić backend tests ani frontend build/test.

## 2. Metodyka i ograniczenia audytu

### Metodyka

- Przegląd top-down repo: backend entrypoint, routery, serwisy, modele, security, scheduler, sync, rules, analytics.
- Przegląd frontendu: routing, app shell, API client, duże strony, test surface.
- Przegląd dokumentacji: `PROGRESS.md`, `DECISIONS.md`, `docs/FEATURE_SET.md`, `docs/SOURCE_OF_TRUTH.md`, `docs/COMPLETED_FEATURES.md`, `docs/API_ENDPOINTS.md`.
- Statyczne wyszukiwanie ścieżek `validate_action`, demo guardów, router registration, tras i stubów.
- Próba uruchomienia checków runtime tam, gdzie środowisko pozwala.

### Ograniczenia

- **Potwierdzone przez uruchomienie:** tylko blokery runtime/build/test.
- **Potwierdzone statycznie:** większość findings architektonicznych, bezpieczeństwa i spójności kontraktów.
- **Niezweryfikowane z powodu ograniczeń środowiska:** pełny pass backend tests, frontend build/test, realne mutacje Google Ads na żywym koncie.

### Ograniczenia środowiskowe w tym przebiegu

- `backend\venv\Scripts\python.exe -m pytest -q` kończy się błędem `Odmowa dostępu`.
- `npm.cmd run build` kończy się `Error: spawn EPERM` przy starcie `esbuild`.
- `npm.cmd test -- --run` kończy się `Error: spawn EPERM` przy ładowaniu `vite.config.js`.
- Audyt odbywał się na brudnym worktree; raport opisuje stan zastany i nie ingeruje w istniejące zmiany użytkownika.

## 3. Stan repo i obserwacje bazowe

- Backend rejestruje **17 routerów** w `backend/app/main.py:103-119`.
- Frontend ma **25 page components** i **28 route entries** w `frontend/src/app/routes.jsx:42-69` (w tym redirecty).
- `PROGRESS.md` deklaruje 25 tras i 17 routerów, ale `docs/SOURCE_OF_TRUTH.md` nadal deklaruje 15 routerów i 15 stron.
- Backend ma około **101 plików aplikacyjnych** i około **29k LOC**; frontend `src` około **132 plików** i około **22k LOC**.
- Backend test surface to **45 plików testowych**. Frontend ma tylko **8 testów unit/component-like** oraz **16 speców Playwright**.
- Największe moduły backendowe i frontendowe są już monolitami:
  - `backend/app/services/google_ads.py` ok. 5140 linii
  - `backend/app/services/analytics_service.py` ok. 4596 linii
  - `backend/app/routers/analytics.py` ok. 2192 linii
  - `frontend/src/features/rules/RulesPage.jsx` 903 linii
  - `frontend/src/pages/Reports.jsx` 899 linii
  - `frontend/src/api.js` 319 linii jako scentralizowany, szeroki klient API

## 4. Findings

## Krytyczne

### K1. Automated Rules omijają kanoniczny pipeline bezpieczeństwa i nie wykonują pełnej mutacji Google Ads

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** najwyższy. Funkcja opisana jako automatyczne wykonywanie akcji nie przechodzi przez centralne guardraile. To podważa główną zasadę bezpieczeństwa finansowego aplikacji i rozbija spójność modelu operacyjnego.
- **Dowód:**
  - `backend/app/routers/rules.py:270-285` wykonuje regułę "for real" przez bezpośrednie `execute_rule(rule, db, dry_run=False)`.
  - `backend/app/services/rules_engine.py:156-171` pauzuje encję przez bezpośrednie `entity.status = "PAUSED"`.
  - `backend/app/services/rules_engine.py:174-222` dodaje negative keyword lokalnie przez `db.add(neg)`.
  - `backend/app/services/rules_engine.py:249-302` kończy się lokalnym `db.commit()`.
  - Statyczne wyszukiwanie w `backend/app/routers/rules.py` i `backend/app/services/rules_engine.py` nie zwróciło odwołań do `validate_action`, `ActionExecutor`, `allow_demo_write`, `ensure_demo_write_allowed` ani `action_log`.
- **Ocena ryzyka:** krytyczne. Obecny kod miesza semantykę "automation" z lokalnym stanem DB bez pełnego execution contract i bez spójnego audytu akcji.
- **Rekomendowany kierunek naprawy:** zablokować live execute dla reguł albo przepiąć wszystkie akcje reguł przez `ActionExecutor` i jego logikę preconditions/safety/demo/audit. Do czasu naprawy funkcję traktować jako preview/local workflow, nie jako bezpieczną automatyzację produkcyjną.

### K2. Kontrakt "every write path goes through validate_action()" jest fałszywy dla części realnych write pathów

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** krytyczny, bo użytkownik i dokumentacja dostają fałszywe poczucie bezpieczeństwa. Część mutacji omija centralny circuit breaker.
- **Dowód:**
  - `docs/FEATURE_SET.md:99` deklaruje: `Every write path goes through preconditions and validate_action().`
  - Globalne wyszukiwanie `validate_action(` pokazuje realne użycia tylko w:
    - `backend/app/services/action_executor.py:182`
    - `backend/app/services/google_ads.py:3726`
    - `backend/app/services/google_ads.py:3898`
  - `backend/app/routers/analytics.py:1858-1885` wywołuje `google_ads_service.add_placement_exclusion(...)` bez `validate_action`.
  - `backend/app/services/google_ads.py:1313-1340` wykonuje zewnętrzną mutację placement exclusion bez ścieżki `validate_action`.
  - `backend/app/routers/campaigns.py:231-282` zmienia bidding target poza `ActionExecutor`.
  - `backend/app/routers/rules.py` plus `backend/app/services/rules_engine.py` omijają cały pipeline bezpieczeństwa.
- **Ocena ryzyka:** krytyczne. Invariant architektoniczny i komunikat bezpieczeństwa nie pokrywają rzeczywistości implementacyjnej.
- **Rekomendowany kierunek naprawy:** zdefiniować jedną listę dozwolonych write pathów i wymusić wspólną warstwę wykonania. Wszystkie endpointy mutujące powinny albo iść przez `ActionExecutor`, albo przez równie restrykcyjny adapter z tym samym zestawem guardrailów.

## Wysokie

### H1. Zmiana bidding target zapisuje lokalny stan przed potwierdzeniem z Google Ads

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** wysoki. Lokalna baza może twierdzić, że kampania ma nowy target CPA/ROAS, mimo że Google Ads odrzucił albo nie wykonał mutacji.
- **Dowód:**
  - `backend/app/routers/campaigns.py:257-260` robi lokalny update i `db.commit()`.
  - Dopiero potem `backend/app/routers/campaigns.py:267-273` próbuje push do Google Ads.
  - Endpoint jawnie zwraca `api_synced` i `api_error` w `backend/app/routers/campaigns.py:275-282`, więc sam kod potwierdza możliwość rozjazdu.
- **Ocena ryzyka:** wysokie. To ryzyko stanu niekanonicznego i błędnych decyzji operatora na bazie lokalnych danych.
- **Rekomendowany kierunek naprawy:** przejść na model transactional/outbox albo remote-first z lokalnym commit po potwierdzeniu mutacji. Minimum: oznaczać rekord jako pending_sync zamiast traktować go jako dokonany stan.

### H2. Dokumentacja statusu i source of truth jest materialnie nieaktualna

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** wysoki. Zespół traci wiarygodny punkt odniesienia do onboarding, review, planowania i regresji.
- **Dowód:**
  - `docs/SOURCE_OF_TRUTH.md:24-26` nadal mówi o `Backend routers: 15` i `Frontend pages: 15`.
  - Realny backend ma 17 routerów w `backend/app/main.py:103-119`.
  - Realny frontend ma 25 page components i 28 route entries w `frontend/src/app/routes.jsx:42-69`.
  - `PROGRESS.md:46` i `docs/COMPLETED_FEATURES.md:329` opisują scheduler jako APScheduler-based.
  - `backend/app/services/scheduler.py:1-4` mówi wprost: `Simple asyncio-based background scheduler` i `No external packages`.
  - `docs/FEATURE_SET.md:99` deklaruje write-path invariant, który nie jest spełniony.
- **Ocena ryzyka:** wysokie. Dokumentacja w kilku kluczowych miejscach nie opisuje już systemu, tylko jego wcześniejszą wersję lub intencję.
- **Rekomendowany kierunek naprawy:** rozdzielić dokumentację "aspirational" od "as-built". `SOURCE_OF_TRUTH`, `FEATURE_SET`, `COMPLETED_FEATURES` i `PROGRESS` wymagają jednorazowego porządkowania i potem dyscypliny aktualizacji przy każdym feature.

### H3. Offline conversions są opisane jak ukończona funkcja, ale endpoint upload jest stubem

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** wysoki. UI i dokumentacja mogą sugerować, że upload działa, podczas gdy router nie wykonuje właściwej operacji.
- **Dowód:**
  - `docs/API_ENDPOINTS.md:197-198` opisuje `POST /analytics/offline-conversions/upload?client_id=X` jako upload offline conversions.
  - `PROGRESS.md:161` deklaruje: `Offline Conversions: model OfflineConversion + upload method + endpoints`.
  - `backend/app/services/google_ads.py:1148-1215` ma zaimplementowaną metodę uploadu.
  - `backend/app/routers/analytics.py:2179-2184` nie używa tej metody i zwraca tylko status `info` z komunikatem instrukcyjnym.
- **Ocena ryzyka:** wysokie. To typowy przypadek feature declared, not proven.
- **Rekomendowany kierunek naprawy:** albo dokończyć endpoint, albo natychmiast skorygować dokumentację i UI, żeby nie komunikować gotowości funkcji.

## Średnie

### M1. Warstwa danych opiera się na `create_all()` i ręcznych `ALTER TABLE` przy starcie aplikacji

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** średni do wysokiego. To rośnie źle wraz ze złożonością schema evolution i utrudnia przewidywalne migracje.
- **Dowód:**
  - `backend/app/database.py:216-221` uruchamia `Base.metadata.create_all(...)` oraz `_ensure_sqlite_columns()`.
  - `backend/app/database.py:101-215` zawiera ręczne `ALTER TABLE`, `CREATE INDEX`, `UPDATE` i naprawy danych wykonywane na starcie.
- **Ocena ryzyka:** średnie. Działa dopóki zmiany są względnie proste, ale jest to kruche operacyjnie i trudne do odtworzenia w różnych środowiskach.
- **Rekomendowany kierunek naprawy:** przejść na jawne migracje wersjonowane. Nawet przy SQLite potrzebny jest kontrolowany mechanizm zmian schematu i data migrations.

### M2. Auth/session ma rozjazd między konfiguracją a implementacją

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** średni. Nie wygląda na natychmiastowy exploit, ale utrudnia zrozumienie i przewidywalność warstwy auth.
- **Dowód:**
  - `backend/app/config.py:48-50` definiuje `app_secret_key`, `session_ttl_hours`, `oauth_allow_insecure_transport`.
  - `backend/app/services/session_service.py:1-18` używa wyłącznie in-memory store i hardcoded `SESSION_TTL_MINUTES = 60`.
  - `backend/app/routers/auth.py:7-8` ustawia `OAUTHLIB_INSECURE_TRANSPORT=1` niezależnie od config.
  - `backend/app/routers/auth.py:44-46` opiera cookie max_age o `SESSION_TTL_MINUTES`, nie o `session_ttl_hours`.
- **Ocena ryzyka:** średnie. Problem jest bardziej o spójność i odporność niż o samą podstawową funkcjonalność.
- **Rekomendowany kierunek naprawy:** spiąć auth/session z jednym źródłem konfiguracji, usunąć martwe ustawienia albo zacząć ich używać. Jawnie zdecydować, czy sesje mają być wyłącznie in-memory, czy przetrwałe między restartami.

### M3. Strategia testowa ma luki jakościowe, a obecne środowisko nie pozwala potwierdzić stanu build/test

- **Status weryfikacji:** częściowo potwierdzone przez uruchomienie, częściowo statycznie
- **Wpływ biznesowy/techniczny:** średni. Testy istnieją, ale nie wszystkie sprawdzają to, co system deklaruje jako krytyczne.
- **Dowód:**
  - `backend/tests/conftest.py:40-52` nadpisuje `require_session` dla większości testów poza `test_auth_session.py` i `test_security_hardening.py`.
  - Backend ma 45 plików testowych, ale nie znaleziono dedykowanego coverage dla automated rules execution path porównywalnego z coverage `ActionExecutor`.
  - Frontend ma tylko 8 testów unit/component-like przy dużej powierzchni modułów oraz 16 speców Playwright.
  - Checki uruchomieniowe w tym audycie były zablokowane:
    - backend pytest: `Odmowa dostępu`
    - frontend build/test: `spawn EPERM`
- **Ocena ryzyka:** średnie. Największe ryzyko to fałszywie pozytywne poczucie bezpieczeństwa i brak szybkiego feedback loop przy regresjach.
- **Rekomendowany kierunek naprawy:** dodać testy integracyjne dla rules write pathów i bidding-target sync flow, ograniczyć globalny auth bypass, a pipeline CI uruchamiać w środowisku, które realnie pozwala odpalić Python/Vite/esbuild.

### M4. Największe moduły backendu i frontendu są już trudne do bezpiecznej ewolucji

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** średni. Obniża szybkość review, zwiększa ryzyko regresji i sprzyja broad catchom oraz mieszaniu odpowiedzialności.
- **Dowód:**
  - `backend/app/services/google_ads.py` ok. 5140 linii.
  - `backend/app/services/analytics_service.py` ok. 4596 linii.
  - `backend/app/routers/analytics.py` ok. 2192 linii.
  - `frontend/src/features/rules/RulesPage.jsx` 903 linii.
  - `frontend/src/pages/Reports.jsx` 899 linii.
  - `frontend/src/api.js` 319 linii jako szeroki wspólny klient.
- **Ocena ryzyka:** średnie. Nie jest to bug sam w sobie, ale tworzy podatny grunt pod kolejne.
- **Rekomendowany kierunek naprawy:** rozcinać po capability, nie po pliku. Najpierw rules, analytics write paths, report generation i Google Ads mutations.

## Niskie

### L1. Część konfiguracji i komunikatów architektonicznych wygląda na pozostałość po wcześniejszych iteracjach

- **Status weryfikacji:** potwierdzone statycznie
- **Wpływ biznesowy/techniczny:** niskie, ale koszt kumuluje się w czasie.
- **Dowód:**
  - `backend/app/config.py:48` zawiera domyślne `app_secret_key`, które nie uczestniczy w bieżącej logice sesji.
  - `DECISIONS.md:31-32` i część dokumentacji mieszają decyzję "future" z "implemented".
  - Nazewnictwo i opis niektórych feature flag/pathów nie odróżniają już jasno intencji od stanu faktycznego.
- **Ocena ryzyka:** niskie bezpośrednio, średnie długofalowo.
- **Rekomendowany kierunek naprawy:** usunąć martwe elementy konfiguracyjne i uporządkować język dokumentacji tak, by opisywał system as-built.

## 5. Macierz warstw

| Warstwa | Status | Ocena |
|---|---|---|
| Backend | sprawdzone | Solidna baza i szeroki zakres funkcji, ale write pathy są niespójne i część omija wspólny execution contract. |
| Frontend | sprawdzone | Routing i shell są czytelne, ale duże strony i mały unit-test surface zwiększają koszt zmian. |
| Bezpieczeństwo | częściowo sprawdzone | Dobre podstawy dla credential storage i auth gating, ale bezpieczeństwo write pathów nie jest egzekwowane jednolicie. |
| Dane / DB | sprawdzone | Model danych jest bogaty, lecz schema evolution przy starcie aplikacji jest ryzykowna operacyjnie. |
| Testy | częściowo sprawdzone | Testów jest sporo, ale coverage krytycznych scenariuszy jest nierówny, a runtime verification została zablokowana środowiskowo. |
| Dokumentacja | sprawdzone | Największy rozjazd między deklaracją a implementacją; obecnie nie może pełnić roli wiarygodnego source of truth bez porządków. |
| Uruchamialność | zablokowane środowiskowo | Backend pytest i frontend build/test nie uruchomiły się w obecnym środowisku wykonawczym. |

## 6. Backlog naprawczy

### Quick Wins

- Wyłączyć live execute dla Automated Rules albo jasno oznaczyć funkcję jako local-only preview do czasu przepięcia na bezpieczny pipeline.
- Natychmiast zaktualizować `docs/SOURCE_OF_TRUTH.md`, `docs/FEATURE_SET.md`, `docs/COMPLETED_FEATURES.md`, `PROGRESS.md` do stanu as-built.
- Ujednolicić komunikację wokół offline conversions: albo działający endpoint, albo uczciwy opis jako stub/in progress.
- Dodać ostrzeżenie w UI/API dla bidding-target update, jeśli `api_synced=false`.

### Stabilizacja

- Przepiąć wszystkie mutacje Google Ads przez wspólną warstwę wykonania z:
  - preconditions
  - `validate_action()`
  - demo guard
  - action log / audit trail
- Dodać testy integracyjne dla:
  - `rules.py` + `rules_engine.py`
  - `PATCH /campaigns/{campaign_id}/bidding-target`
  - `POST /analytics/placement-exclusion`
- Ograniczyć globalny bypass auth w testach i zostawić go tylko tam, gdzie naprawdę jest potrzebny.
- Naprawić środowisko build/test tak, aby Python i Vite/esbuild uruchamiały się bez błędów uprawnień.

### Refaktoryzacja

- Rozbić `google_ads.py`, `analytics_service.py`, `analytics.py`, `RulesPage.jsx`, `Reports.jsx`.
- Wydzielić osobny moduł dla write operations vs read/reporting.
- Zastąpić startupowe `ALTER TABLE` wersjonowanymi migracjami.
- Uporządkować auth/session config i usunąć martwe ustawienia.

### Ryzyka strategiczne

- Jeżeli aplikacja ma wykonywać realne mutacje finansowe, obecna niespójność write pathów jest ryzykiem produktowym, nie tylko technicznym.
- Jeżeli dokumentacja ma pełnić rolę kontraktu zespołowego, wymaga procesu utrzymania, nie jednorazowego update.
- Jeżeli desktop/local-first ma być podstawowym modelem, pipeline testowy musi być odporny na lokalne ograniczenia Windows i polityki uruchamiania procesów.

## 7. Appendix

### Uruchomione checki

1. `backend\venv\Scripts\python.exe -m pytest -q`
   Wynik: **failed**. Błąd procesu: `Unable to create process ... Odmowa dostępu`.

2. `npm.cmd run build` w `frontend`
   Wynik: **failed**. Vite nie załadował configu, `esbuild` kończy się `Error: spawn EPERM`.

3. `npm.cmd test -- --run` w `frontend`
   Wynik: **failed**. Startup error przy ładowaniu `vite.config.js`, `Error: spawn EPERM`.

### Najważniejsze miejsca dowodowe użyte w audycie

- `backend/app/main.py:65-74, 103-119`
- `backend/app/services/action_executor.py:58-117, 125-199`
- `backend/app/services/google_ads.py:92-139, 1148-1215, 1313-1340`
- `backend/app/routers/campaigns.py:231-282`
- `backend/app/routers/analytics.py:1858-1885, 2160-2184`
- `backend/app/routers/rules.py:252-285`
- `backend/app/services/rules_engine.py:156-222, 249-302`
- `backend/app/services/scheduler.py:1-5, 196-225`
- `backend/app/database.py:101-221`
- `backend/app/config.py:43-50`
- `backend/app/services/session_service.py:1-18, 64-92`
- `backend/tests/conftest.py:40-52`
- `frontend/src/app/routes.jsx:33-70`
- `docs/FEATURE_SET.md:99`
- `docs/SOURCE_OF_TRUTH.md:24-26`
- `docs/API_ENDPOINTS.md:197-198`
- `PROGRESS.md:8-11, 46, 161`
- `docs/COMPLETED_FEATURES.md:216, 329, 334, 338`

### Podsumowanie audytowe w jednym zdaniu

Największy problem aplikacji nie leży dziś w braku funkcji, tylko w tym, że część funkcji mutujących omija własne kontrakty bezpieczeństwa i jest opisana w dokumentacji pewniej, niż wynika to z realnej implementacji.
