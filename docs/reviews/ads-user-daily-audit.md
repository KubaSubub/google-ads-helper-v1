# Notatki usera: Poranny Przegląd (Daily Audit) — RE-TEST #2

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-27 (re-test)

---

## Co widze po wejsciu

Nagłówek "Poranny Przegląd" z badge'm health status (Critical/Warning/OK), liczbą aktywnych kampanii i keywords. Alert banner z liczbą krytycznych alertów (anomalie, odrzucone reklamy, budget-capped kampanie). 3 karty KPI: Spend (zł), Kliknięcia, Konwersje — z % zmianą vs poprzedni okres. Collapsible sekcja "Quick Optimization Scripts" z 4 przyciskami. Dwukolumnowy layout: Frazy do przejrzenia (top 10 search terms) + Oczekujące rekomendacje (pogrupowane po typie). Na dole: Budget Pacing overview z tabelą kampanii.

To jest mój **poranny workflow w jednym widoku**.

## Co moge zrobic

- **Status badge** — natychmiast widzę Critical/Warning/OK
- **Alert banner** — klikam "Szczegóły" → /alerts
- **3 KPI** — Spend, Kliknięcia, Konwersje z trendem
- **Quick Scripts** (4 przyciski):
  1. "Wyczyść śmieci" — bulk add negatives na irrelevant search terms
  2. "Pauzuj spalające" — pause low-converting high-cost keywords
  3. "Boost winnerów" — increase budget for good CPA campaigns
  4. "Hamulec awaryjny" — lower bids + pause extreme CPA cases
- **Frazy do przejrzenia** — top 10 search terms z kliknięciami i kosztem + "Wszystkie" → /search-terms
- **Oczekujące rekomendacje** — pogrupowane z priority badges + "Wszystkie" → /recommendations
- **Budget Pacing** — per kampania: budżet, wydane, pacing %, limited status

## Co mam WIECEJ niz w Google Ads UI

1. **Poranny checklist w jednym widoku** — GAds nie ma czegoś takiego. Muszę otwierać 5 zakładek: Overview, Keywords, Search Terms, Recommendations, Budget. Tu mam to w 1 ekranie.
2. **Quick Scripts** — jednym klikiem "wyczyść śmieci" dodaje negatywy, "pauzuj spalające" wstrzymuje złe keywords. W GAds to 15 minut ręcznej pracy.
3. **Health status badge** — Critical/Warning/OK. Otwieram rano, widzę zielony — spoko. Czerwony — kopię dalej.
4. **Alert banner** — ile anomalii, ile odrzuconych reklam, ile budget-capped. W GAds muszę szukać w 3 miejscach.
5. **Search terms needing action** — top 10 z kosztem. Quick glance "co marnuje pieniądze".
6. **Rekomendacje pogrupowane z priority** — HIGH/MEDIUM/LOW z linkiem do pełnej listy.

## Czego MI BRAKUJE vs Google Ads UI

1. **Brak eksportu** — nie mogę wyeksportować porannego briefingu jako PDF/email.
2. **Brak historii audytów** — nie widzę "jak wyglądał audit wczoraj". Nie mogę porównać.
3. **Scripts dry-run modal** — modal wyników jest OK ale nie pokazuje progress w real-time.

## Co mnie irytuje / myli

1. **Quick Scripts domyślnie zamknięte** — to jest najważniejsza sekcja! Jeśli mam 15 akcji do wykonania, chcę widzieć to od razu.
2. **Cost wyświetlony jako "zł" ale zmienna "cost_usd"** — potencjalny bug jeśli dane są w USD a nie PLN.

## Verdykt

To jest zakładka którą otwierałbym PIERWSZĄ każdego ranka. Health badge + KPI + alert banner + quick scripts + search terms + recommendations + budget pacing — cały poranny workflow w 1 widoku. Quick Scripts to game-changer: "wyczyść śmieci" jednym klikiem zamiast 15 minut ręcznej pracy. W GAds nie ma nic porównywalnego.

**Ocena: 9/10**

---

## Pytania do @ads-expert

1. Quick Scripts domyślnie zamknięte — celowe? Przy > 0 akcji powinny się otwierać.
2. Eksport porannego briefingu jako PDF/email — planowany?
3. Historia audytów — "wczoraj było 3 alerty, dziś 7" — realistyczne?
