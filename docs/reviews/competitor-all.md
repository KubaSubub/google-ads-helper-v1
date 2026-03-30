# Raport Konkurenta — Full App
> Data: 2026-03-30 | Srednia: 4.8/10 | Werdykt: "Desktop toy z ambicjami SaaS-a — solidny fundament, ale w obecnej formie nie przetrwa zderzenia z rynkiem"

---

*Autor: Marek K. — CTO AdPilot.io, ex-Google Ads Platform, 12 lat w adtechu*

---

## 2.1 Pierwsze wrazenie (30-sekundowy test)

Otwieram apke. Czarny interfejs, wyglada profesjonalnie. Sidebar z klientami, filtry kampanii — ok, widze ze to narzedzie do Google Ads. Pierwszy problem: **muszam ZAINSTALOWAC to na Windowsie**. Nie ma SaaS-a. Nie ma URL-a. Nie moge wyslac linka klientowi. W 2026 roku to dyskwalifikacja.

Dashboard laduje sie, widze KPI, Health Score gauge, bento grid z kartami. Wyglada ladnie. Ale po 30 sekundach pytam: **"co to robi czego Google Ads UI nie robi?"** I nie mam jednoznacznej odpowiedzi. Widze te same metryki co w Google Ads, tylko w ciemnym motywie. Health Score? Fajny gadget, ale nie wiem jak jest liczony i czy moge mu zaufac.

**Killer feature?** Bento grid z 35 kartami audytu — to jest ciekawe. Nikt tego nie ma w jednym widoku. Ale to insight, nie action. Patrze na dane, nie moge z nimi nic zrobic inline.

**Werdykt 30s:** Ladny dashboard do ogladania danych. Nie widze powodu zeby przestac uzywac Google Ads UI + skrypty.

---

## 2.2 Glowne slabosci (ranked by severity)

### [KRYTYCZNE] #1 — Aplikacja desktopowa, nie SaaS
**Co:** Cala architektura oparta na PyWebView + SQLite + localhost. Jeden user, jedna maszyna, Windows only.
**Dlaczego to problem:** W 2026 roku KAZDE narzedzie do Google Ads jest SaaS-em. Optmyzr, Opteo, Adalysis, WordStream — wszystko w przegladarce. Agencja z 5 specjalistami nie moze wspoldzielic danych. Klient nie moze zobaczyc raportu przez link. Nie ma historii na innej maszynie. Laptop padl — dane stracone.
**Co ja bym zrobil:** Od dnia zero budowalbym na Next.js + PostgreSQL + multi-tenant auth. SQLite to prototyp, nie produkt.
**Plik/obszar:** `main.py` (PyWebView wrapper), `backend/app/models/database.py` (SQLite), brak multi-user w calym stacku

### [KRYTYCZNE] #2 — Brak prawdziwych akcji masowych (bulk operations)
**Co:** Tabele sa read-only. Nie moge edytowac bidow inline, nie moge zaznaczyc 50 keywords i zmienic im match type, nie moge bulk-pausowac kampanii. Jedyne bulk to "dodaj negatywy z search termow" i "uruchom quick script".
**Dlaczego to problem:** Specjalista Google Ads spedza 60% czasu na bulk edycji. Google Ads Editor istnieje WYLACZNIE po to. Jesli twoje narzedzie nie pozwala na masowe zmiany — to lookbook, nie narzedzie pracy.
**Co ja bym zrobil:** Inline editable tables (jak Airtable). Zaznacz wiersze → dropdown "Zmien bid o +10%", "Pausuj", "Zmien match type". Keyboard shortcuts na bulk.
**Plik/obszar:** `frontend/src/components/DataTable.jsx` (view-only), brak `BulkEditor` komponentu, `frontend/src/pages/` (zadna strona nie ma inline edit)

### [KRYTYCZNE] #3 — SQLite jako "produkcyjna" baza
**Co:** Cala aplikacja na SQLite. Jeden plik .db. Brak migracji (Alembic wylaczony — zmiana schematu = kasowanie bazy i reseed). Brak concurrent access. Brak backupow.
**Dlaczego to problem:** Jeden crash i tracisz wszystko. Nie mozesz miec dwoch uzytkownikow. Nie mozesz skalowac. A przede wszystkim: **schema change = DELETE ALL DATA + reseed**. To nie jest architektura produkcyjna, to prototyp.
**Co ja bym zrobil:** PostgreSQL od startu. Alembic migracje. Automatyczne backupy. Nawet jesli local-first — przynajmniej SQLite z WAL + Litestream do S3.
**Plik/obszar:** `backend/app/models/database.py` (brak Alembic, `_ensure_sqlite_columns()` hack), `DECISIONS.md` (ADR-001)

### [KRYTYCZNE] #4 — Brak multi-account overview (MCC dashboard)
**Co:** Widze jednego klienta naraz. Przelaczam w sidebar. Nie ma widoku "wszystkie konta" — porownania miedzy kontami, zbiorczych KPI, alertow cross-account.
**Dlaczego to problem:** Kazdy specjalista PPC zarzadza 5-20 kontami. Optmyzr ma MCC dashboard. Adalysis ma cross-account rules. Tu musisz klikac klient po kliencie jak w Google Ads UI z 2015 roku.
**Co ja bym zrobil:** MCC-first architecture. Dashboard z lista kont, traffic-light statusy (zielony/zolty/czerwony), aggregate KPIs. "Which account needs attention right now?"
**Plik/obszar:** `frontend/src/contexts/AppContext.jsx` (`selectedClientId` — single client paradigm), brak `MccDashboard` page

### [POWAZNE] #5 — Monolityczny backend (5879-linijkowy plik)
**Co:** `google_ads.py` ma 5879 linii. `recommendations.py` ma 3250 linii. To sa pliki-molochy ktore robia wszystko.
**Dlaczego to problem:** Nie mozesz tego testowac granularnie. Nie mozesz tego refaktorowac bez ryzyka regresji. Nowy developer otwiera plik i zamyka IDE.
**Co ja bym zrobil:** `google_ads.py` → `sync_service.py` + `mutation_service.py` + `google_ads_client.py`. `recommendations.py` → osobna klasa per regula (`rules/r01_low_ctr.py`, `rules/r02_high_cvr.py`, etc.). Strategy pattern.
**Plik/obszar:** `backend/app/services/google_ads.py:1-5879`, `backend/app/services/recommendations.py:1-3250`

### [POWAZNE] #6 — Brak zarzadzania tresciami reklamowymi
**Co:** Nie ma edytora RSA (Responsive Search Ads). Nie ma testowania naglowkow/opisow. Nie ma ad copy performance comparison. Widze reklamy ale nie moge ich edytowac ani analizowac A/B.
**Dlaczego to problem:** Ad copy to 50% sukcesu w Search. Google Ads UI ma slaby edytor. Optmyzr ma Ad Copy Lab. Adalysis ma automatic A/B testing z stat significance. Tu jest ZERO.
**Co ja bym zrobil:** RSA editor z drag & drop pinowania. Automatyczne testy stat significance miedzy wariantami. Sugestie naglowkow z AI (GPT/Claude).
**Plik/obszar:** `backend/app/routers/keywords_ads.py` (endpoint `/ads/` jest GET only — read-only), brak `AdEditor` komponentu

### [POWAZNE] #7 — Rekomendacje bez kontekstu biznesowego
**Co:** 34 reguly (R1-R31) z hardcodowanymi progami. $50 spend threshold, 0.5% CTR, 1.5x CVR average. Te same progi dla e-commerce z ROAS 500% i dla lead-gen z CPA 200 PLN.
**Dlaczego to problem:** Opteo uczy sie z historii konta. Optmyzr pozwala customizowac progi. Tu jest "one size fits all" z wartosciami ktore ktos wymyslil. Specjalista z 5-letnim doswiadczeniem nie zaufa rekomendacjom z arbitralnymi progami.
**Co ja bym zrobil:** Adaptive thresholds (percentyle z historii konta, nie absolutne wartosci). UI do konfiguracji progow per klient. A/B testing rekomendacji (track accept/dismiss ratio per rule).
**Plik/obszar:** `backend/app/services/recommendations.py` (hardcoded: `spend > 50`, `ctr < 0.005`, `cvr > 1.5 * avg`), `backend/app/utils/constants.py` (safety limits — OK, ale progi decyzyjne — nie)

### [POWAZNE] #8 — Forecast na regresji liniowej
**Co:** Prognozowanie oparte na prostej regresji liniowej. Bez sezonowosci, bez day-of-week, bez event detection.
**Dlaczego to problem:** Google Ads ma wbudowany Performance Planner z machine learning. Twoj "forecast" z regresja liniowa to zabawka przy tym. Specjalista otworzy Google Ads → Performance Planner i dostanie lepsze prognozy za darmo.
**Co ja bym zrobil:** Prophet (Facebook) lub STL decomposition minimum. Uwzglednienie sezonowosci (swieta, weekendy, Black Friday). Porownanie z Google Performance Planner jako baseline.
**Plik/obszar:** `frontend/src/pages/Forecast.jsx` (explicit "linear" model), `backend/app/routers/analytics.py` (forecast endpoint)

### [POWAZNE] #9 — Brak CI/CD i production-grade infra
**Co:** Nie widze GitHub Actions, Docker, health checks, Sentry, monitoring. Testy sa (477 pytest) ale nie sa odpalane automatycznie. Brak staging environment.
**Dlaczego to problem:** "Dziala na moim laptopie" to nie produkt. Jeden push moze zepsuc cala apke i nikt sie nie dowie. Brak monitoring = brak wiedzy o bledach uzytkownikow.
**Co ja bym zrobil:** GitHub Actions (lint + test + build na PR). Docker Compose dla local dev. Sentry dla error tracking. Uptime monitoring na endpointach.
**Plik/obszar:** Brak `.github/workflows/`, brak `Dockerfile`, brak `docker-compose.yml`, brak konfiguracji Sentry

### [IRYTUJACE] #10 — Z-score anomalies z sigma notation
**Co:** Detekcja anomalii uzywa notacji sigma (1.5σ, 2.0σ, 2.5σ, 3.0σ). Specjalista PPC nie wie co to sigma.
**Dlaczego to problem:** Twoj user to marketer, nie statystyk. "2 sigma" nic mu nie mowi. Opteo mowi "unusual drop in conversions — 80% confidence". To jest zrozumiale.
**Co ja bym zrobil:** Przetlumacz na ludzki jezyk: "Niezwykle niski wynik (99% pewnosci)" zamiast "3.0σ". Dodaj visual context — sparkline z zaznaczonym outlierem.
**Plik/obszar:** `frontend/src/pages/Alerts.jsx` (threshold picker z sigma notation)

### [IRYTUJACE] #11 — 60+ typow rekomendacji bez priorytetyzacji UX
**Co:** System rekomendacji ma 60+ typow (PAUSE_KEYWORD, UPDATE_BID, QS_ALERT, DEVICE_ANOMALY, NGRAM_NEGATIVE...). Uzytkownik widzi liste z badgami ktore nic mu nie mowia.
**Dlaczego to problem:** Information overload. Opteo pokazuje 3-5 top akcji dziennie z jasnym "do this, save X PLN". Tu jest lista 60+ typow i uzytkownik musi sam decydowac co jest wazne.
**Co ja bym zrobil:** "Top 5 actions today" — ranked by estimated impact in PLN. Reszta schowana za "Show all". Kazda rekomendacja: "Zrob X → oszczedzisz Y PLN/miesiac".
**Plik/obszar:** `frontend/src/pages/Recommendations.jsx` (flat list, no impact-ranked view)

---

## 2.3 Co bym ukradl (uczciwie)

1. **Audit Center z bento grid (35 kart)** — to jest naprawde dobre. Jeden ekran, wszystkie problemy konta. Nikt tego nie ma w takiej formie. Optmyzr ma "Account Health Score" ale nie w grid layout z pinowaniem. Ukradlbym ten koncept.

2. **Campaign Role Classification** — automatyczne tagowanie kampanii jako Brand/Generic/Prospecting/Remarketing z confidence score i protection levels. Inteligentne — zapobiega przypadkowemu pauzowaniu brand kampanii. Opteo tego nie ma.

3. **Safety guardrails na mutacjach** — circuit breaker, daily limits, demo lock, dry-run, audit trail z revert. To jest enterprise-grade safety. Lepsze niz 90% narzedzi na rynku ktore po prostu pushuja zmiany bez walidacji.

4. **Search Terms Intelligence** — segmentacja (HIGH_PERFORMER/WASTE/IRRELEVANT), semantic clustering, close variant detection, trend analysis. To jest kompletny workflow do search termow. Dobrze zrobione.

5. **Polskie UI** — pelna lokalizacja, polskie etykiety, pluralizacja (jeden/kilka/wiele). Na polskim rynku to advantage — Optmyzr jest tylko po angielsku.

6. **Keyboard shortcuts** — 1-9 nawigacja, `/` search, `?` help. Power user friendly. Wiekszosci narzedzi tego brakuje.

---

## 2.4 Brakujace "table stakes" (must-have ktorych nie ma)

### TERAZ (blokuje adopcje):

| # | Feature | Kto to ma | Dlaczego must-have |
|---|---------|-----------|-------------------|
| 1 | **SaaS / web deployment** | Wszyscy konkurenci | Desktop = brak wspolpracy, brak mobile, brak sharingu |
| 2 | **Multi-user / team** | Optmyzr, Adalysis, WordStream | Agencja = team. Jeden user = zabawka |
| 3 | **Bulk editor (inline)** | Google Ads Editor, Optmyzr | 60% pracy specjalisty to bulk edycja |
| 4 | **MCC dashboard** | Optmyzr, Marin, Kenshoo | Specjalista ma 5-20 kont |
| 5 | **Scheduled reports (email)** | Optmyzr, Adalysis, nawet Google Ads | Klient chce raport w mailu w poniedzialek rano |
| 6 | **Ad copy editor + A/B testing** | Optmyzr (Ad Copy Lab), Adalysis | Reklamy = 50% sukcesu |

### MOZE POCZEKAC (nice-to-have):

| # | Feature | Kto to ma | Komentarz |
|---|---------|-----------|-----------|
| 7 | Custom dashboards | Supermetrics, Looker Studio | Power users chca wlasne widoki |
| 8 | Google Analytics integration | Optmyzr, WordStream | Landing page + bounce rate |
| 9 | Change approval workflow | Marin, Kenshoo | Dla agencji z klientami |
| 10 | Automated rules scheduling | Google Ads Scripts, Optmyzr | "Pausuj jesli CPA > X przez 7 dni" — auto |
| 11 | Competitor keyword research | SEMrush, SpyFu | Nie core ale expected |
| 12 | Attribution modeling | GA4, Funnel.io | Cross-channel value |

---

## 2.5 Architektura i tech debt (z perspektywy CTO)

### Decyzje ktore beda bolec w skali:

1. **SQLite + brak migracji = bomba zegarowa**
   - Kazda zmiana schematu to `DELETE DB + RESEED`. To znaczy ze uzytkownik **traci historie akcji, rekomendacji i alertow** przy kazdym uaktualnieniu.
   - `backend/app/models/database.py` ma hack `_ensure_sqlite_columns()` ktory probuje dodawac kolumny bez migracji. To sie zlamie przy rename/drop kolumny.
   - **Fix:** Alembic teraz, nie "kiedys". Kazdy dzien bez migracji to dzien w ktorym nie mozesz bezpiecznie updateowac produkcji.

2. **Monolity serwisowe**
   - `google_ads.py` (5879 linii) robi: sync, mutacje, query building, error handling, caching — wszystko w jednym pliku.
   - `recommendations.py` (3250 linii) ma 34 regul w jednej klasie. Dodanie nowej reguly = edycja 3250-linijkowego pliku.
   - **Fix:** Strategy pattern dla regul. Osobne moduły sync/mutate/query.

3. **Brak caching layer**
   - Kazdy request odpytuje SQLite od nowa. KPI dashboard przy 10 klientach x 100 kampanii x 30 dni = setki tysiecy wierszy na request.
   - `cachetools` jest w requirements ale uzyty minimalnie.
   - **Fix:** Redis/in-memory cache z TTL na read-heavy endpoints (KPI, dashboard, health score).

4. **Singleton Google Ads Service**
   - `google_ads_service` zainicjalizowany na poziomie modulu. Credentials jednego klienta w pamieci.
   - Przelaczenie klienta = reinicjalizacja? Race condition przy concurrent requests?
   - **Fix:** Per-request client instantiation z connection pool.

5. **Brak rate limiting na API**
   - Endpointy nie maja throttlingu. Jesli frontend ma bug z infinite loop — backend padnie.
   - **Fix:** SlowAPI middleware, 100 req/min per endpoint.

6. **Frontend — mixed styling (Tailwind + inline styles)**
   - Czesc komponentow uzywa Tailwind classes, czesc inline `style={{}}`. Brak design tokens. Kolory hardcodowane w wielu plikach.
   - **Fix:** Design tokens w CSS variables. Jeden zrodlo prawdy dla kolorow/spacing.

### Copy-paste / nie DRY:

- Error handling pattern `try { ... } catch(e) { setError(e.message) }` powtorzony w KAZDEJ stronie
- Parametry filtrowania budowane recznie w wielu routerach zamiast shared utility
- Severity color maps (`SEVERITY_COLORS`, `CATEGORY_COLORS`) zduplikowane miedzy komponentami
- Polish pluralization logic powielona (choć jest utility)

---

## 2.6 UX / Design killers

1. **Brak onboardingu** — nowy user widzi pusty dashboard. Brak tutorial, walkthrough, sample data. "Select client in sidebar" to nie onboarding.

2. **Tabele read-only** — patrze na keyword z CPA 500 PLN i QS 2/10. Chce go spausowac. Nie moge. Musze isc do Recommendations, znalezc rekomendacje, kliknac "Apply". 5 klikniec zamiast jednego.

3. **Brak breadcrumbs** — jestem na Quality Score → Keyword detail → nie wiem jak wrocic. Brak nawigacji wstecz w kontekscie.

4. **Sigma notation na anomaliach** — uzytkownik widzi "2.5σ" i nie wie co to znaczy. Zero tooltipow, zero wyjasnien.

5. **Quick Scripts bez preview** — "Clean Waste" na Daily Audit — klikam i nie wiem co dokladnie zostanie spausowane. Dry-run jest ale moglby byc bardziej wizualny (lista z checkboxami, nie modal z tekstem).

6. **Brak mobile responsiveness** — sidebar ma `hidden lg:flex`. Na tablecie (ktory specjalista PPC czesto uzywa na spotkaniach z klientem) — polowa UI jest uciona.

7. **Toast notifications znikaja po 3s** — "Dodano 12 negatywow" — zniklo. Nie moge kliknac zeby zobaczyc szczegoly. Brak notification center.

8. **Forecast z "linear model" label** — to jest jak napisac "ten produkt jest slaby". Nie mow uzytkownikowi ze model jest prosty — albo zrob lepszy model, albo nie pokazuj nazwy modelu.

9. **60+ recommendation types w flat list** — information overload. Brak grupowania, brak "top 5 dzisiaj", brak estimated PLN impact w widocznym miejscu.

10. **Brak dark/light mode toggle** — dark mode jest domyslny i jedyny. Niektorzy specjalisci pracuja w jasnym biurze z refleksami — potrzebuja light mode.

---

## 2.7 Moj plan ataku (jak bym was pokonanal)

### 3 rzeczy ktore bym zbudowal:

**1. "One-Click Optimization" — AI-driven daily action plan**
Codziennie rano specjalista otwiera moj tool i widzi: "Dzis 5 akcji, szacowany zysk: +2,340 PLN/msc". Klikniecie "Zastosuj wszystkie" pushuje zmiany do Google Ads. Nie lista 60 rekomendacji — 5 najwazniejszych z kwota w PLN. To jest killer feature ktorej nikt nie ma dobrze.

**2. "Client Portal" — sharing link dla klienta**
Specjalista generuje link, klient widzi dashboard z KPI, trendy, wykonane akcje. Read-only, branded. Zero instalacji. To zamyka "dlaczego placimy agencji?" na jednym URL-u. Wy tego nie mozecie zrobic bo jestescie desktopowi.

**3. "Smart Rules Engine" z natural language**
"Pausuj keyword jesli CPA > 200 PLN przez 7 dni i conversions < 2" — wpisane po polsku, AI parsuje na rule. Optmyzr ma rules ale po angielsku i z UI formularza. Po polsku z natural language = polski rynek na talerzu.

### Dlaczego wasz produkt NIE wygra w obecnym stanie:

Jestescie **desktop-only narzedziem dla jednego usera**. W swiecie gdzie Optmyzr kosztuje $249/msc i dziala w przegladarce z teamem, wy proponujecie instalacje na Windows. To nie jest kwestia feature gap — to jest kwestia **distribution**. Nawet jesli macie lepsze features (a nie macie), nikt was nie znajdzie, nie wyprobuje, nie podzieli sie z teamem.

### Co musielibyscie zrobic w 30 dni zebym zaczal sie was bac:

1. **Tydzien 1-2:** Deploy backend na cloud (Railway/Fly.io). Frontend na Vercel. PostgreSQL zamiast SQLite. Jedno konto testowe dostepne przez URL.
2. **Tydzien 2-3:** Multi-user auth (email + Google login). Team workspace. Shared client access.
3. **Tydzien 3-4:** "Top 5 actions today" view z PLN impact. One-click apply all. Scheduled daily email digest.

Jesli w 30 dni postawicie to w cloudzie z multi-user — zaczynam sie martwic. Jesli dalej bedziecie polishowac desktop app — idę spac spokojnie.

---

## Krok 3: Scorecard

| Kategoria | Ocena | Komentarz (1 zdanie) |
|-----------|-------|----------------------|
| Wartosc dla specjalisty | 5/10 | Duzo danych, malo akcji — to lookbook, nie narzedzie pracy |
| Kompletnosc vs konkurencja | 4/10 | Brak bulk edit, ad copy, MCC dashboard, scheduled reports — brakuje table stakes |
| UX/Design | 6/10 | Ladny dark theme i bento grid, ale read-only tabele i brak onboardingu zabijaja UX |
| Tech quality | 5/10 | Solidne safety guardrails, ale monolity 5k+ linii, SQLite bez migracji, brak CI/CD |
| Unikatowa wartosc (moat) | 4/10 | Audit Center z 35 kartami jest unikalny, ale latwy do skopiowania; brak network effects |
| Gotowosc rynkowa | 3/10 | Desktop-only, single-user, brak onboardingu — to prototyp, nie produkt rynkowy |
| **SREDNIA** | **4.5/10** | |

---

## Krok 4: Werdykt koncowy

> "Gdybym byl inwestorem, widzialbym zespol ktory zbudowal solidny backend z 159 endpointami, 477 testami i przemyslanymi safety guardrails — ale zapakowano to w format dystrybucji z 2010 roku. To jest silnik Porsche w karoserii Malucha. Dopoki nie postawicie tego w cloudzie z multi-user, jestescie narzedziem dla jednego dewelopera, nie produktem dla rynku. Mam 30 dni przewagi i zamierzam je wykorzystac."

---

*Marek K., CTO AdPilot.io*
*"We ship SaaS, not installers."*
