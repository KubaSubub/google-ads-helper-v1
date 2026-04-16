---
type: vision
status: canonical
created: 2026-04-16
source: "[[2026-04-16 - Jakub dyktuje wizję GAH+Obsidian]]"
tags: [gah, vision, obsidian, self-learning, architecture]
---

# GAH — wizja samouczącego się systemu

> *"Ja jako specjalista Google Ads, wersji automatycznej w komputerze."*
> — Jakub, 2026-04-16

## Jednym zdaniem

GAH to **ja sam** w formie aplikacji — która robi to co ja robię ręcznie w panelu Google Ads, ale **sama**, uczy się z wcześniejszych działań przez pamięć w Obsidianie, i wykonuje rekomendacje po mojej akceptacji.

## Three-layer architecture

```
┌─────────────────────────────────────────────────────┐
│  GOOGLE ADS (panel przeglądarki — "świat zewnętrzny")│
└──────────────────────┬──────────────────────────────┘
                       │ API (read/write)
┌──────────────────────▼──────────────────────────────┐
│  GAH APPLICATION                                    │
│  • Akcje ręczne (jak w panelu)                      │
│  • Skrypty i automatyzacje (moje, wymyślone)        │
│  • AI wewnątrz (Claude, zintegrowany)               │
│  • Dane operacyjne → SQLite                         │
└──────────────────────┬──────────────────────────────┘
                       │ czyta + zapisuje
┌──────────────────────▼──────────────────────────────┐
│  OBSIDIAN VAULT (sejf — "operacyjny mózg")          │
│  • Historia zmian (co robiłem, kiedy, dlaczego)     │
│  • Wnioski końcowe (co działało, co nie)            │
│  • Rekomendacje AI (co proponowane)                 │
│  • Brief klienta (strategia, cele, zasady)          │
│  • Używane przez AI do pisania raportów + rekom.    │
└─────────────────────────────────────────────────────┘
```

## Rola każdej warstwy

| Warstwa | Co trzyma | Kto edytuje |
|---|---|---|
| **Google Ads API** | Aktualny stan kampanii, metryki | Google (źródło prawdy zewnętrzne) |
| **GAH SQLite** | Cache API + stan aplikacji + konfiguracja skryptów | GAH (operacyjny layer) |
| **Obsidian Vault** | Historia decyzji, wnioski, rekomendacje, brief | AI + Jakub (mózg) |

## Co NIE jest duplikowane

- **Całe SQL / raw data z Google Ads** → zostaje w SQLite (za dużo, nie ma sensu)
- **Metryki kampanii** → Google Ads API + GAH cache
- **Live state** → SQLite
- **Do Obsidiana** → tylko **wnioski końcowe**: co zrobiono, co zadziałało, co zmienić

## Flagowy workflow: przycisk "OPTYMALIZUJ"

Docelowa (v8-v10) forma pracy z GAH:

```
User klika "Optymalizuj"
        │
        ▼
  1. AI patrzy na ostatnie 7 dni — bez pracy, co się stało samo
        │
        ▼
  2. Odpalają się skrypty i automatyzacje (9+ aktualnie)
        │
        ▼
  3. Czyta Obsidian — co my tu robiliśmy wcześniej, jakie były decyzje
        │
        ▼
  4. Ewaluacja:
     • Czy poprzednie zmiany działały? (konwersje w górę? CPC w dół?)
     • Czy prognoza się sprawdziła?
     • Czy kierunek ma sens, czy pivot?
        │
        ▼
  5. AI pisze rekomendacje: "Zrób X, Y, Z, bo to a tamto"
        │
        ▼
  6. Jakub ocenia:
     ┌─ "Ufam" → AI wykonuje przez API Google Ads → DZIEJE SIĘ SAMO
     └─ "Nie ufam" → Jakub robi ręcznie lub odrzuca
        │
        ▼
  7. Wynik → zapisany w Obsidian (wejście do kroku 3 następnej optymalizacji)
```

Każdy obrót pętli = kolejny "epizod" w pamięci systemu. Po kilkudziesięciu obrotach AI ma wystarczający kontekst żeby proponować coraz lepsze rzeczy.

## Dlaczego to jest "samouczący się"

Nie w sensie ML (nie trenujemy modelu). W sensie **akumulacji doświadczenia**:

- System pamięta co zadziałało / nie zadziałało
- Decyzje są uzasadniane i zapisywane
- Następna rekomendacja korzysta z poprzednich epizodów
- Po roku: AI "wie" o danym kliencie więcej niż początkujący specjalista

**Metafora:** to jak stażysta który prowadzi pamiętnik. Po roku zostaje senior specjalistą, nawet jeśli nikt go bezpośrednio nie szkolił — bo refleksja + doświadczenie.

## Co to JEST, a co NIE jest

### ✅ JEST
- Narzędzie **dla Jakuba** — osobiście, na jego laptopie
- **Desktop app** — włączana lokalnie, dane nie wychodzą
- **Extended Google Ads panel** — wszystko co zrobisz w panelu + więcej
- **Obsidian jako pamięć długoterminowa**
- **AI jako asystent** który czyta pamięć i proponuje
- **Self-learning przez doświadczenie** (nie ML)

### ❌ NIE JEST
- **NIE SaaS** — zero sprzedaży
- **NIE multi-user / multi-tenant** — nie da się udostępnić
- **NIE dla innych agencji / freelancerów** — świadomie
- **NIE produkt komercyjny** — *"to ma mi pomagać, nie ludziom"*
- **NIE replacement panelu Google Ads** — rozszerzenie, nie zamiana

## Biznesowy model

Nie produkt. Jakub monetyzuje **siebie wspieranego przez GAH**:
- Obsługuje więcej klientów w tym samym czasie
- Podnosi jakość optymalizacji (system pamięta, nie zapomni)
- Buduje osobistą przewagę konkurencyjną ("mam własne narzędzie")
- Zarabia na obsłudze klientów PPC + konsultacjach + content (PPC+AI)

Nie sprzedaje GAH. Sprzedaje **rezultaty które GAH mu umożliwia**.

## Stan obecny (v1.0, kwiecień 2026)

**Zbudowane:**
- Backend (175 endpointów), Frontend (28 stron)
- 9 skryptów automatyzacyjnych
- Silnik rekomendacji (34 typy reguł)
- `Client.strategy_context` schema (Mastermind Brief — infrastruktura pod Obsidian sync)
- Agent service (Claude integrated) — pisze raporty, podsumowania
- Action history, audit center, search terms intelligence

**NIE zbudowane:**
- Sync GAH ↔ Obsidian (pamięć)
- Przycisk "Optymalizuj" (orchestracja pełnego flow)
- Self-evaluation (czy poprzednie rekomendacje zadziałały?)
- Trust mechanism (kiedy AI dostaje permission na auto-execute?)

## Droga do tej wizji

### v1.0 (teraz) — Manual operational
GAH ma wszystkie features, ale jest **operowany ręcznie**. User klika poszczególne funkcje, AI pisze raporty na żądanie.

### v2.0 — Obsidian sync (najbliższy milestone)
- Bi-directional sync wybranych danych GAH ↔ vault
- Action history → vault (każda zmiana zapisana w `Daily Notes/` lub per-klient)
- StrategyContext ↔ vault (Strategia + Roadmap edytowalne w Obsidianie)
- AI w GAH czyta vault przy pisaniu raportów/rekomendacji

### v3.0+ — Self-evaluation
- Każdą rekomendację GAH tagujesz jako "wdrożona" / "pominięta"
- AI po N dniach ewaluuje: czy wdrożone działały?
- Statystyki per typ rekomendacji → ranking "jakich AI słuchać bardziej"

### v5.0+ — Orchestrated optimization ("Optymalizuj" button)
- Jeden przycisk odpala pełny flow (scripts + evaluation + recommendations)
- Output: "oto co zrobiłem, oto co proponuję, czy wykonać?"

### v8.0+ — Trust-based autonomy
- Akcje niskiego ryzyka (negatywne słowa, exclude placements) → auto-execute po cichu
- Średniego ryzyka → wymaga 1-click approval
- Wysokiego (budget, bidding strategy) → zawsze manual review

## Powiązane

- [[GAH - Wizja i cel]] — top-level vision (aktualizowane po tej dyktacji)
- [[GAH - ewolucja wizji]] — historyczna ewolucja myślenia (synteza z 410 rozmów)
- [[GAH x Vault - plan integracji]] — plan techniczny (do aktualizacji po tej wizji)
- [[2026-04-16 - Jakub dyktuje wizję GAH+Obsidian]] — raw source
- [[GAH - Architektura]] — aktualna architektura techniczna
- [[Profile klienta zamiast RAG]] — dlaczego vault a nie vector DB
