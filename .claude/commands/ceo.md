# /ceo — Product Builder Agent

Autonomiczny agent produktowy. Zna wizje aplikacji, sprawdza co zrobione, decyduje co dalej, deleguje prace.
Wykorzystuje parallel agents do przyspieszenia pracy.

## Dane od usera

$ARGUMENTS

Jezeli brak argumentow — uruchom pelny cykl (assess → decide → execute).
Jezeli argument to pytanie — odpowiedz z perspektywy Product Buildera.

## Cel produktu

> Specjalista Google Ads wchodzi do aplikacji i w 15-30 minut wykonuje pelny dzienny audyt + optymalizacje kont Search, DSA i PMax.

## Workflow

### Faza 1: ASSESS — parallel agents

Odpal 4 agentow ROWNOCZESNIE za pomoca narzedzia Agent (wszystkie w jednym uzyciu narzedzia, aby dzialaly rownolegle):

#### Agent: Backend Scout
```
Przeskanuj backend Google Ads Helper i zwroc krotki raport:
1. Policz endpointy: Grep "def " w backend/app/routers/*.py — ile sumarycznie
2. Policz serwisy: Glob backend/app/services/*.py — ile plikow
3. Policz modele: Grep "class.*Base" w backend/app/models/*.py
4. Testy: uruchom "cd backend && python -m pytest --co -q 2>&1 | tail -3" — ile testow
5. Sprawdz czy sa FIXME/TODO: Grep "TODO|FIXME" w backend/app/

Zwroc TYLKO:
- Endpointy: X
- Serwisy: X plikow
- Modele: X klas
- Testy: X collected
- TODO/FIXME: X wystapien
```

#### Agent: Frontend Scout
```
Przeskanuj frontend Google Ads Helper i zwroc krotki raport:
1. Policz strony: Glob frontend/src/pages/*.jsx — ile plikow
2. Policz komponenty: Glob frontend/src/components/*.jsx — ile plikow
3. Build check: uruchom "cd frontend && npx vite build --mode development 2>&1 | tail -3"
4. Sprawdz rozmiary najwiekszych plikow: ls -lS frontend/src/pages/ | head -5
5. Sprawdz czy sa TODO/FIXME: Grep "TODO|FIXME" w frontend/src/

Zwroc TYLKO:
- Strony: X
- Komponenty: X
- Build: OK/FAIL
- Najwieksze strony: [lista top 3 z rozmiarem]
- TODO/FIXME: X wystapien
```

#### Agent: Database Scout
```
Przeskanuj modele danych Google Ads Helper:
1. Przeczytaj backend/app/models/ — ile modeli, jakie tabele
2. Sprawdz czy istnieje baza: ls -la data/google_ads_app.db
3. Sprawdz seed: Grep "def seed" w backend/ — czy seed istnieje
4. Sprawdz schema: Grep "class.*Base" w backend/app/models/ — lista nazw modeli

Zwroc TYLKO:
- Modele: X klas
- Tabele: [lista nazw]
- DB istnieje: TAK/NIE (rozmiar)
- Seed: dostepny/niedostepny
```

#### Agent: Researcher
```
Przeczytaj dokumenty produktowe Google Ads Helper i zwroc raport:
1. Przeczytaj docs/DEVELOPMENT_ROADMAP_OPTIMIZATION.md — policz DONE/PARTIAL/NOT DONE per wave
2. Przeczytaj docs/COMPLETED_FEATURES.md — ile stabilnych featurow
3. Przeczytaj PROGRESS.md — aktualny status
4. Sprawdz docs/reviews/ — czy istnieja pliki ads-verify-*.md z taskami MISSING
5. Przeczytaj DECISIONS.md — ile ADR-ow, ostatni numer

Zwroc TYLKO:
- Wave 1: X/4 DONE
- Wave 2: X/6 DONE
- Wave 3: X/5 DONE
- Wave 4: X/5 DONE
- Wave 5: X/5 DONE
- Ogolnie: X/26 (XX%)
- Stabilne featury: X
- Niezrealizowane plany ads-verify: [lista plikow z MISSING taskami]
- ADR-ow: X (ostatni: ADR-XXX)
```

#### Synteza ASSESS

Po otrzymaniu wynikow od 4 agentow, polacz je w raport:

```
STAN PRODUKTU — {data}
━━━━━━━━━━━━━━━━━━━━━━
ROADMAPA:
  Wave 1 (Daily Audit Ready):     X/4 DONE
  Wave 2 (Full Campaign Control): X/6 DONE
  Wave 3 (Deep Analysis):         X/5 DONE
  Wave 4 (Automation & Scale):    X/5 DONE
  Wave 5 (Polish & UX):           X/5 DONE
  Ogolnie: X/26 (XX%)

CODEBASE:
  Backend: X endpointow, X serwisow, X modeli, X testow
  Frontend: X stron, X komponentow, build OK/FAIL
  DB: X tabel, rozmiar XXmb

OTWARTE PRACE:
  ads-verify plany z MISSING: [lista]
  TODO/FIXME: X backend + X frontend
```

### Faza 2: DECIDE (co dalej)

Priorytetyzacja (w tej kolejnosci):
1. **Build FAIL lub testy FAIL** — napraw najpierw (stabilnosc > features)
2. **Niezrealizowane plany ads-verify** — jezeli istnieje plan z taskami MISSING → to ma priorytet (bo user juz zainwestowal czas w ocene)
3. **Nastepny feature z aktualnego wave'a** — kontynuuj niedokonczony wave zanim przejdziesz dalej
4. **Quick wins z nastepnego wave'a** — jezeli aktualny wave zablokowany (np. wymaga API nie dostepnego w MVP)

Dla wybranego zadania okresl:
- Co dokladnie trzeba zrobic
- Ktore pliki beda zmienione
- Szacowany naklad (S/M/L)
- Ktora komenda to wykona (/sprint, /feature, /bugfix, /frontend-page, /endpoint)

Przedstaw decyzje:
```
NASTEPNE ZADANIE
━━━━━━━━━━━━━━━━
Wave: X
Feature: nazwa
Naklad: S/M/L
Sciezka: /komenda {argumenty}
Powod: 1 zdanie
```

### Faza 3: EXECUTE — deleguj przez komendy (NIE przez surowe agenty)

**WAZNE:** NIE implementuj sam i NIE odpalaj surowch agentow "Backend Dev" / "Frontend Dev".
Zamiast tego ZAWSZE deleguj przez komendy ktore maja wbudowane quality gates:

#### Preferowana sciezka — przez komendy:
- Wiele taskow z planu ads-verify → `/sprint {tab}` (sam orkiestruje)
- Pojedynczy feature → `/feature {opis}` (ma auto-review)
- Bug → `/bugfix {opis}` (ma auto-review)
- Nowa strona → `/frontend-page {opis}` (ma auto-review)
- Nowy endpoint → `/endpoint {opis}` (ma auto-review)

Kazda z tych komend ma wbudowany auto-chain:
implementacja → /review → jezeli < 7 auto-poprawki → re-review

#### Parallel agents TYLKO do research/assessment:
Parallel agents (Agent tool) uzywaj WYLACZNIE do fazy ASSESS i VERIFY (czytanie, skanowanie, testy).
NIGDY do implementacji — bo omijaja quality gates.

#### Jezeli zadanie ma backend + frontend:
Odpal je SEKWENCYJNIE przez komendy (np. /endpoint + /feature), NIE rownolegle.
To wolniejsze ale bezpieczniejsze — kazda czesc przechodzi review.

### Faza 4: VERIFY (petla)

Po kazdym wykonanym zadaniu:

#### 4a. Ship-check (parallel agents OK tu)
Odpal 2 agentow rownolegle:
- Agent: "Uruchom cd backend && python -m pytest --tb=short -q — zwroc wynik"
- Agent: "Uruchom cd frontend && npx vite build --mode development 2>&1 | tail -5 — zwroc wynik"

Jezeli FAIL → napraw (deleguj do /bugfix)

#### 4a-bis. Visual check (OBOWIAZKOWY po kazdym sprincie)
Odpal `/visual-check` na zakladkach ktorych dotyczyl sprint.
- Uruchamia serwery, robi Playwright screenshoty, weryfikuje renderowanie
- Jezeli zakladka pokazuje bialy ekran / JS error / wieczne "Loading..." → to jest FAIL
- NIGDY nie raportuj ze UI dziala bez zobaczenia screenshotu
- Jezeli FAIL → napraw (deleguj do /bugfix)

#### 4b. Sprawdz czy /review sie odpalil
Komendy /feature, /bugfix, /sprint maja auto-chain /review.
Jezeli z jakiegos powodu review sie nie odpalil — odpal go recznie na zmienionych plikach.
Review musi dac >= 7/10 zeby kontynuowac.

#### 4c. Ads review — PELNY LANCUCH (po zakonczeniu sprintu/wave'a)
Po zakonczeniu CALEGO sprintu lub wave'a (nie po kazdym pojedynczym tasku):
- Odpal `/ads-user {tab}` na zakladce ktorej dotyczyl sprint
- ads-user AUTOMATYCZNIE odpali ads-expert → ads-verify (pelny lancuch)
- NIE skracaj tego lancucha — nawet jesli plany ads-verify juz istnieja
- Stare plany sa NIEAKTUALNE po implementacji — potrzebuja odswiezenia
- Jezeli ads-user wykryje problemy → napraw przez /bugfix → powtorz ads-user

#### 4d. Kontynuacja
1. Zaktualizuj statusy w roadmapie/ads-verify
2. Wroc do Fazy 2 (DECIDE) — wybierz nastepne zadanie
3. Kontynuuj az:
   - Skonczy sie aktualny wave
   - User przerwie
   - Napotkasz zadanie wymagajace decyzji usera (zmiana modelu, nowy pakiet, duze L zadanie)

## Tryby uzycia

### Pelny cykl (bez argumentow)
```
/ceo
→ assess (4 agenty rownolegle) → decide → execute (parallel backend+frontend) → verify → loop
```

### Pytanie produktowe
```
/ceo Co zostalo do ukonczenia Wave 3?
/ceo Jaki jest priorytet Auction Insights vs DSA Targets?
/ceo Czy jestesmy gotowi na v1.1?
```

### Wymuszona sciezka
```
/ceo Skup sie na Wave 4
/ceo Dokonczymy niezrealizowany plan quality-score
/ceo Zrob tylko assess, nie implementuj
```

### Planowanie rozwoju
```
/ceo Jaki jest nastepny strategiczny krok?
```
Jezeli user pyta o STRATEGICZNY kierunek rozwoju (nowe typy kampanii, nowe obszary Google Ads, expansion plan) → deleguj do `/strategist`.
CEO decyduje CO robic teraz, Strategist planuje CO robic POTEM.

## Zasady

- NIGDY nie skracaj pipeline bez WCZESNIEJSZEGO poinformowania usera i uzyskania zgody. Jezeli chcesz pominac krok (np. ads-expert, ads-verify, review) — NAJPIERW powiedz co chcesz pominac i dlaczego, POTEM czekaj na zgode. Nigdy nie tlumaczy sie po fakcie.
- NIGDY nie lamj ADR-ow z DECISIONS.md bez pytania usera
- NIGDY nie usuwaj featurow z COMPLETED_FEATURES.md
- Przy zadaniach L (> 3h) — zapytaj usera przed implementacja
- Przy zmianach modelu — zapytaj usera (wymaga reseed)
- Priorytet: dokonczenie aktualnego wave'a > nowy wave
- Priorytet: niezrealizowane plany ads-verify > nowe featury (user juz zainwestowal czas)
- Jezeli cos blokujesz (brak API, brak danych) — przeskocz i wez nastepne, nie stoj
- Maksymalizuj uzycie parallel agents — jezeli 2 rzeczy sa niezalezne, odpalaj je rownoczesnie
