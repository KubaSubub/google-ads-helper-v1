# Sciaga — komendy Claude Code

## Najwyzszy poziom — autopilot

```
/ceo                              — pelny cykl: assess → decide → execute → verify → loop
/ceo Co zostalo do Wave 3?        — pytanie produktowe
/ceo Skup sie na Wave 4           — wymuszona sciezka
```

> CEO zna cala wizje produktu (roadmapa, feature set, decyzje). Sam sprawdza co zrobione, wybiera nastepne zadanie, deleguje i weryfikuje.

## Nie wiesz ktorej komendy uzyc?

```
/cto {napisz po polsku co chcesz}
```

CTO sam zdecyduje ktora komende odpalic. Przykłady:
- `/cto Nie dziala filtrowanie w Keywords` → odpali `/bugfix`
- `/cto Dodaj wykres trendow do Dashboard` → odpali `/feature`
- `/cto Popraw zakladke Quality Score` → odpali `/sprint quality-score`

## Codzienne uzywanie

| Komenda | Kiedy uzyc | Przyklad |
|---------|-----------|----------|
| `/bugfix` | Kazdy bug (logika, dane, UI, wizualny) | `/bugfix Sync nie zapisuje keyword daily` |
| `/feature` | Nowa funkcjonalnosc do istniejącej strony | `/feature Dodaj eksport CSV do Keywords` |
| `/debug` | Nie wiesz co jest zepsute | `/debug Strona Keywords bialy ekran` |

> Podaj pliki jesli wiesz gdzie problem: `/bugfix Filtr nie dziala. Pliki: routers/campaigns.py, pages/Campaigns.jsx`
> Nie wiesz? Napisz tylko opis — Claude znajdzie sam przez mape projektu.

## Tworzenie nowych rzeczy

| Komenda | Kiedy uzyc | Przyklad |
|---------|-----------|----------|
| `/endpoint` | Nowy endpoint API (tylko backend) | `/endpoint GET /api/v1/campaigns/{id}/history` |
| `/frontend-page` | Nowa cala strona/zakladka + route + sidebar | `/frontend-page Forecast — prognoza budzetu` |
| `/refactor` | Porzadki w kodzie (bez zmiany zachowania) | `/refactor Wydziel wspolne style z Dashboard` |
| `/seed` | Odswiezenie bazy danych | `/seed` (po zmianach modeli) |
| `/start` | Uruchomienie serwerow dev | `/start` |

## Zamykanie pracy

| Komenda | Kiedy uzyc | Co robi |
|---------|-----------|---------|
| `/commit` | Sam commit bez push | Analizuje zmiany, tworzy conventional commit |
| `/done` | Zamkniecie zadania | pytest → commit → docs-sync → push (z PM gate) |
| `/docs-sync` | Aktualizacja dokumentacji | Skanuje kod, aktualizuje PROGRESS.md, API_ENDPOINTS.md |

## Przeglady i audyty

| Komenda | Kiedy uzyc | Co generuje |
|---------|-----------|-------------|
| `/review` | Code review zmian | Raport: [CRITICAL/WARNING/INFO] + ocena X/10 |
| `/audit` | Pelny audyt projektu | Przeglad: docs, backend, frontend, security |
| `/pm-check` | Ocena PM/PO | Raport PM + gate do push (>= 7/10) |
| `/sync-check` | Czy docs = kod? (raport) | Tabela rozbieznosci docs vs kod |

> `/review` odpala sie automatycznie po `/bugfix`, `/feature`, `/endpoint`, `/frontend-page`, `/refactor`

## Pipeline Ads Review (tylko ocena)

```
/ads-user {zakladka}        — symulacja PPCowca, notatki UX
  └─ /ads-expert             — automatycznie: ocena ekspercka
       └─ /ads-verify         — automatycznie: plan implementacji
```

> Wystarczy odpalic `/ads-user {tab}` — reszta odpala sie automatycznie.

## Sprint (ocena + implementacja)

```
/sprint {zakladka}           — bierze plan z ads-verify i implementuje
  ├─ per task: /feature lub /bugfix (auto)
  │    └─ /review (auto-chain)
  ├─ po sprintach: /ads-check (auto)
  └─ raport koncowy → czeka na /done
```

> Jezeli nie ma jeszcze planu ads-verify, sprint sam odpali caly pipeline (ads-user → ads-expert → ads-verify).

| Komenda | Co robi |
|---------|---------|
| `/ads-user {tab}` | Tylko ocena zakladki (bez zmian w kodzie) |
| `/sprint {tab}` | Ocena + implementacja + weryfikacja |
| `/ads-check {tab}` | QA — czy taski wdrozone |

## Auto-chain (co sie odpala samo)

```
/bugfix → /review → raport
/feature → /review → raport
/endpoint → /review → raport
/frontend-page → /review → raport
/refactor → /review → raport
/debug → /bugfix → /review → raport
/done → pytest → /commit → /docs-sync → /pm-check → push
/ads-user → /ads-expert → /ads-verify
/sprint → per task: /feature|/bugfix → /review → /ads-check
```

## Deprecated (przekierowane)

| Stara | Nowa | Powod |
|-------|------|-------|
| `/fix` | `/bugfix` | bugfix robi to samo + wiecej |
| `/ui-fix` | `/bugfix` | bugfix obsluguje tez bugi wizualne |
| `/progress` | `/docs-sync` | docs-sync aktualizuje PROGRESS.md + reszta docs |

## Strategia i planowanie

| Komenda | Kiedy uzyc | Przyklad |
|---------|-----------|----------|
| `/strategist` | Planowanie rozwoju, nowe typy kampanii | `/strategist shopping` |
| `/strategist` | Gap analysis vs Google Ads | `/strategist` (pelna analiza) |
| `/strategist` | Pytanie strategiczne | `/strategist Czy warto dodac Display przed Video?` |

> Strategist NIE implementuje — tylko planuje. Wynik zapisuje do `docs/PRODUCT_STRATEGY.md`.

## Pelna architektura agentow

```
Warstwa 5:  /ceo              ← Product Builder (assess → decide → execute → loop)
Warstwa 4:  /cto              ← Smart Router (wybiera komende za Ciebie)
Warstwa 3:  /sprint            ← Orkiestrator (implementuje plan ads-verify)
Warstwa 2:  /feature /bugfix   ← Executory (z auto-review)
Warstwa 1:  /review /commit    ← Narzedzia
Warstwa 0:  hooks, CLAUDE.md   ← Guardrails
```

## Najkrotsza sciezka

```
Autopilot           → /ceo
Nie wiem co chce    → /cto {opis}
Napraw bug          → /bugfix {opis}
Dodaj feature       → /feature {opis}
Popraw zakladke     → /sprint {nazwa}
Zamknij prace       → /done
```
