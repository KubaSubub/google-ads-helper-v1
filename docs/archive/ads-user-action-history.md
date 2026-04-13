# Notatki usera: Historia zmian (Action History) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** seed data / Demo Meble Sp. z o.o.
**Data:** 2026-03-28

---

## Co widzę po wejściu

Wchodzę na "Historia zmian" i widzę przejrzysty layout z 5 tabami: **Nasze akcje**, **Zewnętrzne**, **Wszystko**, **Wpływ zmian**, **Wpływ strategii licytacji**. Domyślnie "Nasze akcje".

Pod tabami: **quick stats banner** — Dzisiaj, Łącznie, Cofnięte, Zablokowane. Od razu wiem ile się działo.

Pasek filtrów: presety dat (Dzisiaj, 7 dni, 30 dni), date pickery, dropdown typu akcji. Na External/Unified: filtr kampanii + typ zasobu + użytkownik + źródło.

Tabela: Data, Akcja (po polsku), Encja (klikalna → link do /keywords lub /campaigns), Kampania, Status (kolorowy + tooltip na hover), przycisk Cofnij.

Prawy górny róg: **CSV + XLSX** export. Dół: **paginacja** (1-50 z X, prev/next).

## Co mogę zrobić

1. Przełączać 5 tabów
2. Filtrować po datach (presety + custom)
3. Filtrować po typie akcji (Helper tab)
4. Filtrować po kampanii/użytkowniku/źródle (External/Unified)
5. Cofnąć akcję (24h limit)
6. Kliknąć encję → deep link do strony
7. Eksportować CSV/XLSX
8. Paginacja (50/stronę, prev/next)

## Co mam WIĘCEJ niż w Google Ads UI

1. **Unified timeline** — akcje z Helpera + z Google Ads UI + API w jednym widoku z badge'ami źródła
2. **Cofnij akcję** — w GAds nie ma cofania, tu klikam "Cofnij" i gotowe
3. **Quick stats** — ile dziś, ile cofniętych, ile zablokowanych
4. **Wpływ zmian** — korelacja zmiana → efekt na KPI
5. **Wpływ strategii licytacji** — jak zmiana strategii wpłynęła na konwersje/CPA/ROAS
6. **Polskie etykiety** — "Wstrzymano keyword" zamiast "PAUSE_KEYWORD"
7. **Deep links** — klik na keyword → /keywords?search=X
8. **Eksport jednym klikiem** — CSV lub XLSX

## Czego MI BRAKUJE vs Google Ads UI

1. **Filtr kampanii na Helper tab** — External ma, Helper nie
2. **Bulk revert** — nie mogę cofnąć wielu akcji naraz

## Co mnie irytuje / myli

1. Timeline zamiast tabeli na External/Unified — wolałbym tabelę z sortowaniem
2. Brak konfigurowalnej page size (25/50/100)

## Co bym chciał

1. Filtr kampanii na Helper tab
2. Bulk revert (checkbox + "Cofnij zaznaczone")
3. Page size selector
4. Alert po cofnięciu ("czy pomogło?")

## Verdykt

Bardzo dobra zakładka — **lepsza niż Historia zmian w GAds**. Unified timeline, cofanie, quick stats, filtry, eksport. Otwierałbym to codziennie rano. **8.5/10**.

---

## Pytania do @ads-expert

1. Dlaczego Helper tab nie ma filtra kampanii? External/Unified mają.
2. Timeline vs tabela na External/Unified — co lepsze?
3. Bulk revert — planowany?
4. Eksport CSV — dane z aktualnego taba czy z wszystkich?
