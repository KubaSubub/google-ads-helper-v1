# AI Company — Instrukcja obslugi

Masz do dyspozycji 6-warstwowy system agentow AI z parallel processing, ktory dziala jak firma technologiczna.

---

## Szybki start

```
Nie wiesz co robic?          →  /ceo
Wiesz co chcesz ale nie jak? →  /cto popraw filtrowanie w Keywords
Wiesz dokladnie co?          →  /bugfix brak danych w tabeli. Plik: pages/Keywords.jsx
Skonczyles prace?             →  /done
```

---

## Struktura firmy

```
┌─────────────────────────────────────────────────────────────────┐
│  /ceo — CEO / Product Builder (z parallel agents)                │
│  Zna cala wizje produktu. Odpala 4 agentow rownolegle:          │
│                                                                 │
│    Backend Scout  — endpointy, serwisy, testy                    │
│    Frontend Scout — strony, komponenty, build                    │
│    Database Scout — modele, tabele, seed                         │
│    Researcher     — roadmapa, plany, statusy                     │
│                                                                 │
│  Potem decyduje co dalej i deleguje implementacje                │
│  (backend + frontend moga pracowac rownolegle).                  │
│                                                                 │
│  Kiedy: chcesz zeby AI sam poprowadzil rozwoj produktu           │
│  Uzycie: /ceo                                                   │
│          /ceo Co zostalo do Wave 3?                              │
│          /ceo Skup sie na Wave 4                                 │
├─────────────────────────────────────────────────────────────────┤
│  /cto — CTO / Smart Router                                      │
│  Sluchasz Ty mowisz po polsku co chcesz, on wybiera komende.    │
│                                                                 │
│  Kiedy: wiesz co chcesz ale nie pamietasz ktorej komendy uzyc   │
│  Uzycie: /cto {opis po polsku}                                  │
├─────────────────────────────────────────────────────────────────┤
│  /sprint — Tech Lead / Orkiestrator                              │
│  Bierze gotowy plan (ads-verify) i implementuje go task po       │
│  tasku, sprint po sprincie. Sam wybiera /feature czy /bugfix.    │
│                                                                 │
│  Kiedy: masz gotowy plan z /ads-verify i chcesz go wdrozyc      │
│  Uzycie: /sprint quality-score                                   │
│          /sprint dashboard                                       │
├─────────────────────────────────────────────────────────────────┤
│  ZESPOL WYKONAWCZY (warstwa 2)                                   │
│                                                                 │
│  /bugfix {opis}        — naprawia bugi (logika, dane, UI)        │
│  /feature {opis}       — dodaje do istniejacej strony            │
│  /endpoint {opis}      — nowy endpoint API (tylko backend)       │
│  /frontend-page {opis} — nowa cala strona + route + sidebar      │
│  /refactor {opis}      — porzadki w kodzie bez zmiany zachowania │
│  /debug {opis}         — szuka przyczyny gdy nie wiesz co zepsute │
│                                                                 │
│  Kazdy z nich po zakonczeniu automatycznie odpala /review.       │
│  Jezeli review < 7/10 → sam poprawia i powtarza review.          │
├─────────────────────────────────────────────────────────────────┤
│  KONTROLA JAKOSCI (warstwa 1)                                    │
│                                                                 │
│  /review     — code review, ocena X/10                           │
│  /audit      — pelny audyt projektu                              │
│  /pm-check   — ocena PM, gate do push (>= 7/10)                 │
│  /sync-check — czy dokumentacja = kod                            │
│  /docs-sync  — napraw rozbieznosci w dokumentacji                │
│  /commit     — smart commit (analiza zmian, conventional msg)    │
│  /done       — ship-check → commit → docs-sync → pm-check → push│
├─────────────────────────────────────────────────────────────────┤
│  PIPELINE ADS REVIEW (specjalistyczny)                           │
│                                                                 │
│  /ads-user {tab}   — symulacja PPCowca (UX review)               │
│  /ads-expert {tab} — ocena eksperta Google Ads (auto po ads-user)│
│  /ads-verify {tab} — plan implementacji (auto po ads-expert)     │
│  /ads-check {tab}  — QA: czy taski wdrozone                     │
│                                                                 │
│  Wystarczy odpalic /ads-user — reszta odpala sie sama.           │
├─────────────────────────────────────────────────────────────────┤
│  INFRASTRUKTURA (warstwa 0)                                      │
│                                                                 │
│  /seed       — reset bazy danych                                 │
│  /start      — uruchomienie serwerow dev                         │
│  SessionStart hook — pokazuje status projektu + dostepne komendy │
│  Auto-review hook — review odpala sie po kazdej implementacji    │
│  Ship-check  — pytest + build check przed kazdym commitem        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Zespol agentow (parallel processing)

Gdy CEO lub CTO potrzebuje informacji albo implementacji, odpala wyspecjalizowanych agentow rownolegle:

```
┌─ ASSESS (4 agenty rownolegle) ─────────────────────────────────┐
│                                                                 │
│  Backend Scout     Frontend Scout    DB Scout      Researcher   │
│  ─────────────     ──────────────    ────────      ──────────   │
│  endpointy         strony            modele        roadmapa     │
│  serwisy           komponenty        tabele        ads-verify   │
│  testy             build status      seed          PROGRESS     │
│  TODO/FIXME        rozmiary          rozmiar DB    ADR-y        │
│                                                                 │
│  → 4 raporty wracaja jednoczesnie do CEO                        │
└─────────────────────────────────────────────────────────────────┘

┌─ EXECUTE (2 agenty rownolegle gdy mozliwe) ─────────────────────┐
│                                                                 │
│  Backend Dev                      Frontend Dev                   │
│  ───────────                      ────────────                   │
│  model/schema/service/router      component/page/api.js          │
│  pytest po implementacji          build + UI checklist           │
│                                                                 │
│  → wyniki lacza sie, CEO sprawdza integracje                     │
└─────────────────────────────────────────────────────────────────┘

┌─ VERIFY (2 agenty rownolegle) ─────────────────────────────────┐
│                                                                 │
│  Test Runner                      Build Checker                  │
│  ───────────                      ─────────────                  │
│  pytest --tb=short -q             vite build                     │
│                                                                 │
│  → oba zielone = kontynuuj, FAIL = /bugfix                       │
└─────────────────────────────────────────────────────────────────┘
```

Dzieki temu CEO nie czyta 20 plikow sekwencyjnie — 4 agenty robia to rownolegle i zwracaja krotkie podsumowania. Oszczedza kontekst i czas.

---

## 5 scenariuszy codziennego uzycia

### 1. "Chce zeby AI sam poprowadzil" (autopilot)

```
/ceo
```

CEO przeczyta roadmape, sprawdzi co zrobione, wybierze nastepne zadanie z najwyzszym priorytetem, zaimplementuje, zreviewuje i przejdzie do nastepnego. Zatrzyma sie przy duzych zadaniach i zmianach modelu.

### 2. "Wiem co chce, nie pamietam komendy"

```
/cto Dodaj wykres trendow do Quality Score
```

CTO zdecyduje ze to `/feature`, znajdzie pliki, zaimplementuje, odpal review. Ty dostajesz gotowy wynik.

### 3. "Jest bug"

```
/bugfix Filtrowanie nie dziala w Keywords
```

Albo jesli znasz plik:

```
/bugfix Filtrowanie nie dziala. Plik: pages/Keywords.jsx, routers/keywords_ads.py
```

### 4. "Chce ocenic i poprawic zakladke"

Tylko ocena (bez zmian w kodzie):
```
/ads-user quality-score
```

Ocena + automatyczna implementacja:
```
/sprint quality-score
```

### 5. "Skonczylem, chce zamknac"

```
/done
```

Pipeline: ship-check (pytest + build) → commit → docs-sync → pm-check → push.

---

## Jak to dziala w praktyce — pelny flow

```
Ty: /ceo

CEO: Czytam roadmape...
     Wave 1: 4/4 DONE
     Wave 2: 5/6 DONE (brakuje PMax Channel Breakdown)
     Wave 3: 3/5 DONE (brakuje Auction Insights, DSA Targets)

     DECYZJA: Dokonczenie Wave 2 — PMax Channel Breakdown
     Deleguje do /feature...

     [Claude implementuje backend + frontend]

     AUTO-REVIEW: 8/10 — OK
     Sprint Wave 2 kompletny.

     Nastepne zadanie: Wave 3 — Auction Insights
     Naklad: L (> 3h)
     To duze zadanie — kontynuowac?

Ty: tak

     [Claude implementuje]
     [Auto-review → poprawki → re-review]

     Raport: Auction Insights DONE. Wave 3: 4/5.
     Nastepne: DSA Targets Analysis. Kontynuowac?

Ty: nie, /done

     Ship-check: pytest 445 passed, build OK
     Commit: feat: add Auction Insights + PMax Channel Breakdown
     Docs-sync: PROGRESS.md updated
     PM-check: 8/10
     Pushowac?

Ty: tak
```

**Twoje interakcje: 4.** Reszta zrobila sie sama.

---

## Zasady bezpieczenstwa

| Co | Zabezpieczenie |
|---|---|
| Push do repo | Zawsze pyta o zgode |
| Usuwanie kodu/plikow | Zawsze pyta o zgode |
| Zmiana modelu DB | Pyta (wymaga reseed) |
| Nowe zaleznosci | Pyta przed instalacja |
| Review < 7/10 | Auto-poprawia i powtarza |
| PM-check < 7/10 | Blokuje push |
| Testy FAIL | Blokuje commit |
| Build FAIL | Blokuje commit |

---

## Architektura auto-chain

Co odpala sie automatycznie po czym:

```
/debug       → /bugfix (po znalezieniu przyczyny)
/bugfix      → /review (po naprawie)
/feature     → /review (po implementacji)
/endpoint    → /review (po implementacji)
/frontend-page → /review (po implementacji)
/refactor    → /review (po implementacji)
/review < 7  → auto-poprawki → re-review
/ads-user    → /ads-expert → /ads-verify
/sprint      → per task: /feature|/bugfix → /review → /ads-check
/done        → ship-check → /commit → /docs-sync → /pm-check → push
```

---

## Skrocona sciaga (wydrukuj i przyklej obok monitora)

```
┌────────────────────────────────────────┐
│         GOOGLE ADS HELPER AI           │
│                                        │
│  /ceo          autopilot               │
│  /cto {opis}   nie wiem ktorej komendy │
│  /bugfix       napraw bug              │
│  /feature      dodaj do strony         │
│  /sprint {tab} ocen + wdroz zakladke   │
│  /done         zamknij i pushuj        │
│                                        │
│  /ads-user     tylko ocen zakladke     │
│  /frontend-page  nowa cala strona      │
│  /endpoint       nowy endpoint API     │
│  /refactor       porzadki w kodzie     │
└────────────────────────────────────────┘
```
