# Notatki usera: Rekomendacje (Recommendations) — RE-TEST #2

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-27 (re-test)

---

## Co widze po wejsciu

Nagłówek "Recommendations" (po angielsku!). Pod nim "X active recommendations" (angielski!). Rząd summary kart: Total, Executable, High, Action, Blocked — WSZYSTKO po angielsku. Dalej rzędy filtrów: ALL/HIGH/MEDIUM/LOW, All sources/Playbook/Analytics/etc., ALL/EXECUTABLE/ALERTS, Wszystkie/Rekomendacje/Alerty (tu wreszcie po polsku). Przycisk "Select executable"/"Unselect executable". Karty rekomendacji z pillami typu, priorytetu, outcome. Przyciski "Apply" i "Dismiss".

Funkcjonalnie: to jest potężna zakładka. 30+ typów rekomendacji, context-aware budget guardrails, dry-run preview, bulk apply/dismiss. Ale UX jest mocno techniczny i w 80% po angielsku.

## Co moge zrobic

- **Filtrować** po priorytecie (HIGH/MEDIUM/LOW), źródle (Playbook/Analytics/Google Ads), executable vs alerts, kategorii
- **Zaznaczać** rekomendacje checkboxami + bulk select executable
- **Apply** — dry-run preview → potwierdzenie → wykonanie (z action validation)
- **Dismiss** — odrzucenie pojedyncze lub bulk
- **Export XLSX** — eksport rekomendacji
- **Refresh** — odświeżenie listy

## Co mam WIECEJ niz w Google Ads UI

1. **30+ typów rekomendacji z playbooka** — GAds Recommendations to "increase budget", "add keywords" generowane przez algorytm Google. Tu mam rules z prawdziwego playbooka optymalizacji: PMax kanibalizacja, Smart Bidding data starvation, ECPC deprecation, device/geo anomalie.
2. **Context-aware guardrails** — rekomendacja "zwiększ budżet" jest blokowana jeśli kampania jest Brand vs Generic. "Allowed because" / "Blocked because" z konkretnymi powodami. W GAds nie ma nic takiego.
3. **Dry-run preview** — klikam Apply → widzę podgląd co się zmieni ZANIM zmiana nastąpi. W GAds klikam Apply i zmiana od razu leci.
4. **Outcome classification** — ACTION / INSIGHT_ONLY / BLOCKED_BY_CONTEXT. Wiem od razu co mogę zrobić automatycznie a co wymaga ręcznego review.
5. **Bulk apply z selekcją** — zaznaczam 5 rekomendacji → Apply all. W GAds Apply All nie daje mi kontroli nad selekcją.
6. **Confidence + Risk scores** — widzę "Confidence 85%, Risk 12%". W GAds nie ma nic porównywalnego.

## Czego MI BRAKUJE vs Google Ads UI

1. **Polskie UI** — 80% tekstu jest po angielsku. "Recommendations", "active recommendations", "Total", "Executable", "Apply", "Dismiss", "Refresh", "Export", "Running...", "Manual review", "Allowed because", "Blocked or downgraded because", "Trade-offs", "Risk note", "Next best action", "Campaign:", "Confidence", "Expires". To jest polski produkt!
2. **Grupowanie po kampanii** — w GAds mogę filtrować rekomendacje po kampanii. Tu widzę flat listę bez podziału na kampanie.
3. **Brak impact estimate w PLN** — Impact pisze "Impact ~ 5.23" — 5.23 czego? PLN? Mikro? Brak jednostki.

## Co mnie irytuje / myli

1. **ANGIELSKI UI** — to jest showstopper. Mój klient nie mówi po angielsku. "Blocked by context", "Trade-offs", "Risk note" — to jest jargon nawet po angielsku. Reszta aplikacji jest po polsku, ta zakładka wygląda jak z innego produktu.
2. **Za dużo filtrów** — 4 rzędy filtrów pill buttons: priorytet, źródło, executable/alerts, kategoria. Część się pokrywa (ALERTS vs alerts w kategorii). Myli.
3. **MetaRow zbyt techniczny** — "Executable", "Confidence 85%", "Risk 12%", "Expires No expiry" — to jest info dla developera. Jako specjalista GAds chcę wiedzieć: "ważne czy nie" + "co zysk".
4. **"Select executable" / "Unselect executable"** — angielski w przyciskach akcji.

## Co bym chcial

1. **Polskie UI** — cała zakładka po polsku. "Rekomendacje", "Zastosuj", "Odrzuć", "Dozwolone ponieważ", "Zablokowane ponieważ" itp.
2. **Uproszczony widok** — toggle "Prosty / Zaawansowany". Prosty: priorytet + typ + opis + Apply/Dismiss. Zaawansowany: pełne context/explanation panels.
3. **Grupowanie po kampanii** — "Kampania X: 3 rekomendacje" z collapsible listą.

## Verdykt

Funkcjonalnie to jest najsilniejsza zakładka w całej aplikacji — 30+ typów reguł, context-aware guardrails, dry-run, bulk apply. GAds Recommendations to zabawka w porównaniu. ALE: angielski UI + techniczny jargon sprawiają że dla polskiego specjalisty to jest ciężkie w użyciu. Gdyby to było po polsku z prostszym default widokiem — ocena byłaby 9/10.

**Ocena: 6.5/10** (z powodu angielskiego UI — funkcjonalnie 9.5/10)

---

## Pytania do @ads-expert

1. Angielski UI — to celowa decyzja ("specjaliści GAds znają angielski") czy zaplanowana lokalizacja?
2. "Impact ~ 5.23" — w jakiej jednostce? PLN? Czy brakuje formatowania?
3. Filtr po kampanii — planowany?
4. Uproszczony widok dla mniej technicznych userów — rozważany?
