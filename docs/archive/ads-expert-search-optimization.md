# Ocena eksperta Google Ads — Optymalizacja (Search Optimization)
> Data: 2026-03-28 | Średnia ocena: 8.0/10 | Werdykt: ZACHOWAĆ + ZMODYFIKOWAĆ

## TL;DR

Najsilniejsza zakładka w aplikacji — pokrywa ~80% zadań optymalizacyjnych z playbooka w jednym widoku. 33 sekcje analityczne to więcej niż jakiekolwiek narzędzie Google Ads na rynku. Główna słabość: prawie całkowity brak write actions (1/33 sekcji). Dodanie quick actions i filtra kampanii podniesie to z "świetnej analityki" na "narzędzie codziennej pracy".

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 9/10 | Pokrywa 25/30 zadań z playbooka. Specjalista potrzebuje tych danych codziennie. |
| Kompletność | 8/10 | 33 sekcji = bardzo kompletne. Brak: write actions, filtr kampanii, lazy loading. |
| Wartość dodana vs Google Ads UI | 9/10 | N-gram, PMax cannibalization, auction trend, wasted spend %, Pareto — tego nie ma w GAds. |
| Priorytet MVP | 6/10 | Analityka jest "nice to have" w MVP, ale ta jest tak bogata że daje realną wartość od dnia 1. |
| **ŚREDNIA** | **8.0/10** | |

## Co robi dobrze

1. **Wasted Spend z kwotą + %** — specjalista widzi ile pieniędzy "ucieka" bez ręcznego liczenia. Jedyny write action ("Wyklucz") jest tu gdzie trzeba.

2. **N-gram Analysis** — unikalne na rynku. Pozwala odkryć wzorce w search terms bez eksportu do arkusza. Tri/bi/unigram split to pro-level analiza.

3. **PMax ↔ Search Cannibalization** — krytyczne dla każdego konta z PMax. Tabela z "Zwycięzcą" per fraza to coś czego nie ma nigdzie.

4. **Auction Insights z trendem** — ewolucja IS konkurentów na wykresie to insighty niedostępne w GAds (tam tylko tabelka za wybrany okres).

5. **Bid Modifiers w jednym widoku** — device/location/schedule w jednej tabeli z kolorowymi modyfikatorami. W GAds trzeba klikać per kampania.

6. **Smart Bidding Health suite** — Target vs Actual + Learning Status + Portfolio Health — trzy sekcje dające pełny obraz stanu Smart Bidding. W GAds to rozsiane po kampaniach.

7. **Shopping Product Groups** — ROAS per product group w tabeli z kolorowaniem. Szybka identyfikacja produktów poniżej/powyżej progu rentowności.

8. **Placement Performance** — top 50 miejsc z klikalnymi linkami + video metrics. Szybka identyfikacja waste na Display.

## Co brakuje (krytyczne)

1. **Write actions w tabelach** — Pause keyword, change bid, exclude placement powinny być dostępne z poziomu sekcji
   - Playbook ref: Każda sekcja audytowa powinna kończyć się "action step"
   - Implementacja: Dodać buttony w wierszach tabeli, podłączyć do istniejących endpoints (keywords_ads, campaigns)

2. **Filtr kampanii** — globalny dropdown na górze strony, filtrujący wszystkie sekcje
   - Playbook ref: Specjalista zawsze pracuje w kontekście kampanii
   - Implementacja: campaign_id param przekazywany do wszystkich API calls

3. **Grupowanie sekcji** — 33 sekcji potrzebuje kategoryzacji: "Search", "PMax", "Display/Video", "Bidding", "Konwersje", "Konkurencja"
   - Implementacja: Tab bar lub sidebar nav z kotwicami

## Co brakuje (nice to have)

1. **Porównanie okresów** — "ten tydzień vs poprzedni" per sekcja (delta %)
2. **Export PDF** — cały raport optymalizacji do pliku
3. **"Top 3 priorities"** — banner na górze z najważniejszymi 3 akcjami do podjęcia
4. **Lazy loading** — ładuj dane sekcji dopiero po otwarciu akordeon (34 API calls to dużo)
5. **Tooltips** na metrykach Auction Insights — "Position above rate" = "jak często konkurent był wyżej od Ciebie"

## Co usunąć/zmienić

1. **Nazwa strony** — "Optymalizacja SEARCH" → "Optymalizacja" (bo obejmuje Display, Video, Shopping, PMax)
2. **Google Recommendations bez akcji** — albo dodać Apply/Dismiss, albo usunąć sekcję (stub bez wartości)
3. **Duplicate icons** — Crosshair używany dla Target vs Actual I Auction Insights. Box dla Asset Groups I Shopping.

## Porównanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Wasted spend aggregation | Ręczne filtry + arkusz | Automatyczny % + kwota | **LEPSZE** |
| N-gram analysis | Brak | Uni/bi/trigramy | **LEPSZE** |
| PMax cannibalization | Brak | Tabela z "Zwycięzcą" | **LEPSZE** |
| Auction insights trend | Tabelka per okres | Wykres liniowy IS | **LEPSZE** |
| Match type breakdown | Raport per kampania | Zbiorcza tabela | **LEPSZE** |
| Dayparting heatmap | Raport per kampania | Heatmap + tabela | **LEPSZE** |
| Bid modifiers overview | Per kampania | Zbiorcza tabela | **LEPSZE** |
| Placements top list | Per kampania | Top 50 z ROAS | **LEPSZE** |
| Topic performance | Per kampania | Zbiorcza tabela | **LEPSZE** |
| Product group ROAS | Shopping tab | Tabela z kolorowaniem | **LEPSZE** |
| Smart Bidding diagnostics | Per kampania | 3 sekcje zbiorcze | **LEPSZE** |
| Quick actions (pause/bid) | Bezpośrednie | Brak (1 akcja) | **GORSZE** |
| Filtr per kampania | Natywny | Brak | **GORSZE** |
| Ad schedule editing | Bezpośrednie | Read-only | **GORSZE** |
| Placement exclusions | Bezpośrednie | Brak z tego widoku | **GORSZE** |

## Nawigacja i kontekst

- **Skąd user trafia:** Sidebar → ANALIZA → "Optymalizacja"
- **Dokąd powinien móc przejść:** Keywords (z wasted spend), Search Terms (z n-gram), Campaigns (z bid advisor), Quality Score (z RSA)
- **Brakujące połączenia:** Klikniecie keyword w tabeli powinno prowadzić do /keywords?search=X. Klikniecie kampanii do /campaigns.

## Rekomendacja końcowa

**ZACHOWAĆ + ZMODYFIKOWAĆ**

To jest flagship feature aplikacji. 33 sekcji analitycznych w jednym widoku to unikalna wartość na rynku. Trzy krytyczne zmiany: (1) dodać write actions w tabelach, (2) dodać filtr kampanii, (3) pogrupować sekcje w kategorie. Po tych zmianach to narzędzie zastąpi 80% codziennej pracy specjalisty w Google Ads UI.
