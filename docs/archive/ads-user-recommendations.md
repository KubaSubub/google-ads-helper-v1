# Notatki usera: Rekomendacje (Recommendations) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** Demo Meble Sp. z o.o. (seed data)
**Data:** 2026-03-29

---

## Co widze po wejsciu

Naglowek "Rekomendacje" — po polsku, dobrze! Podtytul "61 aktywnych rekomendacji". W prawym gornym rogu dwa przyciski: "Eksport" (zielony, XLSX) i "Odswierz" (szary). Nad filtrami widze summary w postaci 5 kart-licznikow:

- **Lacznie: 61** — pelna pula
- **Do wykonania: 1** — executable, zielony
- **Pilne: 13** — HIGH priority, czerwony
- **Akcje: 32** — context_outcome = ACTION
- **Zablokowane: 0** — context_outcome = BLOCKED

Pod spodem dwa rzedy filtrow pill-button:
1. Priorytet: ALL / HIGH / MEDIUM / LOW
2. Zrodlo: Wszystkie zrodla / Playbook / Analytics / Google Ads / Hybrid
3. Executability: ALL / EXECUTABLE / ALERTS
4. Kategoria: Wszystkie / Rekomendacje / Alerty

Przycisk "Zaznacz wykonalne" — bulk select. Ponizej karty pogrupowane w sekcje: EXECUTABLE (1) i domyslnie ALERTS nizej.

Widoczna karta: "Demo Meble – Darmowa Dostawa", kampania "Lozka – Generic". Pille: MEDIUM, Wstrzymaj reklame, Ad. Meta: ACTION / Playbook / Executable / Confidence 65% / Risk 45% / Expires 1.04.2026. Metryki: Spend 79.31, Clicks 81, Impr 1502, Conv 0.0. Powod: "Spent $79.31 with 0 conversions." Przyciski: "Zastosuj" (niebieski) i "Odrzuc" (szary).

---

## Co moge zrobic

1. **Filtrowac** — 4 niezalezne osie filtrow (priorytet, zrodlo, executable, kategoria). Filtry sa pill-buttons z kolorami — latwo odroznic co jest aktywne.
2. **Przegladac karty** — kazda rekomendacja to karta z priorytetem, typem, entity, kampania, metryki, powod, confidence/risk score, data wygasniecia.
3. **Zaznaczac checkboxami** — pojedynczo lub "Zaznacz wykonalne" (bulk select).
4. **Zastosuj (Apply)** — dry-run preview z modalem potwierdzenia (before/after state), potem faktyczne wykonanie. To SUPER — nie znam zadnego innego narzedzia ktore robi dry-run na rekomendacjach GAds.
5. **Odrzuc (Dismiss)** — pojedynczo lub bulk dismiss zaznaczonych.
6. **Bulk apply** — zaznacz kilka executable i "Apply selected".
7. **Eksport XLSX** — eksport calej listy do pliku.
8. **Odswierz** — recalc/refetch rekomendacji.

---

## Wiecej niz Google Ads UI

1. **Dry-run preview z before/after** — w Google Ads klikasz "Apply" i modlisz sie. Tu widzisz co sie zmieni ZANIM klikniesz.
2. **Context-aware guardrails** — system wie o rolach kampanii (Brand/Generic/PMax), protection levels, budget headroom. Blokuje glupia realokacje budzetu miedzy Brand a Generic.
3. **30+ typow rekomendacji z roznych zrodel** — Playbook, Analytics, Google Ads API, Hybrid. Google Ads UI ma swoje recs, ale nie laczy ich z wlasna analityka.
4. **Confidence + Risk score** — kazda rekomendacja ma procentowy confidence i risk. W Google Ads dostajesz "estimated impact" ale bez granulacji pewnosci.
5. **Explanation panel** — "Allowed because", "Blocked because", "Trade-offs", "Risk note", "Next best action". To jest transparentnosc jakiej NIE MA w Google Ads.
6. **Bulk apply/dismiss** — Google Ads tez ma bulk, ale bez dry-run i bez context checks.
7. **Expiration date** — kazda rekomendacja ma TTL. Nie gromadza sie badziewie sprzed 3 miesiecy.
8. **4 niezalezne osie filtrow** — w Google Ads masz "All" / "Category". Tu mam priorytet, zrodlo, executable, kategorie osobno.

---

## Brakuje vs Google Ads UI

1. **Szacowany wplyw finansowy (estimated impact)** — Google Ads pokazuje "estimated weekly impact" per rekomendacja (np. "+15% clicks", "+$200/week"). Tu mam generyczny "Impact ~X.XX" ale nie na kazdej karcie i nie w walucie klienta.
2. **Score optymalizacji konta (Optimization Score)** — Google Ads ma globalny % score z rozkladem per kategoria. Tu nie widze tego nigdzie.
3. **Grupowanie rekomendacji per typ** — w Google Ads recs sa pogrupowane: "Ads & extensions", "Bidding", "Keywords", "Repairs". Tu mam flat list z filtrem, ale nie widze grupowania po typie akcji.
4. **Podglad reklamy** — Google Ads pokazuje preview reklamy w rekomendacji "add responsive search ad". Tu brak podgladu.
5. **Auto-apply settings** — Google Ads pozwala wlaczyc auto-apply na wybranych typach rekomendacji. Tu nie widze takiej opcji.
6. **Historyczna skutecznosc rekomendacji** — "You applied 15 recommendations in the last 30 days, account score improved by 8%". Tu nie widze trackingu skutecznosci zastosowan.
7. **Dismissed history** — w Google Ads dismissed recs mozna przegladac. Tu dismissed znika (filtr `status: pending` domyslny).
8. **Sortowanie** — nie ma mozliwosci sortowania kart (np. po priorytecie, impact, confidence, dacie). Kolejnosc zalezy od backendu.

---

## Co irytuje

1. **Mieszanka jezykowa** — tytul "Rekomendacje" po polsku, ale sekcje "EXECUTABLE" / "ALERTS" po angielsku. Meta row: "Playbook / Executable / Confidence 65% / Risk 45% / Expires" — to angielski. "Zaznacz wykonalne" po polsku, ale "Apply selected" / "Dismiss selected" / "X selected" po angielsku. Powod karty: "Spent $79.31 with 0 conversions" — angielski. Niech bedzie konsekwentnie — albo PL albo EN.
2. **Sekcja "Do wykonania: 1" ale "Akcje: 32"** — to jest mylace. "Do wykonania" to executable count, "Akcje" to context_outcome=ACTION. Urzytkownik nie wie jaka jest roznica. Albo przynajmniej tooltip.
3. **Filtrowanie jest powolne wizualnie** — jest 4 rzedy filtrow pill-button, to duzo miejsca. Moze 2-3 wiersze zamiast 4? Albo dropdown na zrodlo?
4. **"Reczna weryfikacja" na disabled button** — button jest szary z napisem "Reczna weryfikacja" ale wyglada na disabled/nieklikalny. Jesli to ma byc CTA to powinno kierowac gdzies (np. do kampanii/slowa).
5. **Brak paginacji** — jesli jest 61 rekomendacji i scroll nieskonczone, to przy 200+ bedzie problem.
6. **Brak wizualnego odruznienia pilnosci** — HIGH i MEDIUM recs wygladaja prawie tak samo (rozowy vs zolty pill). Cala karta mogla miec subteline tlo kolorowe dla HIGH.

---

## Chcialbym

1. **Optimization Score** — duzy gauge na gorze z % i rozkladem per kategoria (bidding, keywords, ads, extensions). Jak w Google Ads ale z wlasnym algorytmem.
2. **Sortowanie kart** — po priorytecie, impact, confidence, dacie utworzenia, dacie wygasniecia. Chociaz dropdown "Sortuj wg".
3. **Grupowanie per typ** — zamiast flat list, sekcje per typ: "Budzet", "Slowa kluczowe", "Reklamy", "Smart Bidding" etc.
4. **Dismissed tab** — zakladka albo filtr do przegladu odrzuconych rekomendacji.
5. **Applied history summary** — "W ostatnich 30 dniach zastosowayles 12 rekomendacji. CTR wzrosl o 8%."
6. **Deep link do entity** — klikniecie na nazwe kampanii/slowa kluczowego przenosi do odpowiedniej zakladki.
7. **Kolumny waluty klienta** — "Spend: 79.31 PLN" zamiast "$79.31".
8. **Auto-apply scheduler** — "Automatycznie stosuj LOW-risk rekomendacje typu PAUSE_KEYWORD codziennie o 8:00".
9. **Tooltip na summary cards** — "Do wykonania = rekomendacje mozliwe do automatycznego zastosowania" vs "Akcje = rekomendacje z kontekstem pozwalajacym na dzialanie".
10. **Bulk grouping** — zaznaczam 5 rekomendacji dotyczacych budzetow i widze preview calkowitego przesuniecia.

---

## Verdykt

**8/10** — to MOCNA zakladka. 30+ typow rekomendacji, context-aware guardrails z transparentnym explanation, dry-run preview, bulk actions, 4 osie filtrow, eksport. Daje wiecej niz Google Ads UI pod wzgledem transparentnosci decyzji (why allowed/blocked, confidence/risk). Glowne bolaczki to: brak Optimization Score, mieszanka PL/EN, brak sortowania, brak estimated impact per karta. Ale core jest solidny — to zakladka ktora naprawde bym uzywal codziennie.

**Porownanie z Google Ads UI:**
- Lepsze: dry-run, context guardrails, explanation panel, confidence/risk scoring, multi-source (Playbook + GAds API + Analytics)
- Slabsze: brak Optimization Score, brak estimated impact w walucie, brak auto-apply, brak grupowania per typ
- Na rowni: filtry, bulk actions, dismiss/apply flow

---

## Pytania do @ads-expert

1. Czy 30+ typow regul pokrywa wszystkie standardowe kategorie GAds recs (bidding, keywords, ads, extensions, repairs)?
2. Czy context guardrails (campaign roles, protection, headroom) sa dobrze skalibrowane — czy nie blokuja za duzo / za malo?
3. Czy confidence/risk scoring jest walidowane na real data — czy to heurystyka czy ML?
4. Czy brak Optimization Score to swiadoma decyzja czy luka do uzupelnienia?
5. Czy recommendation engine uruchamia sie on-demand (Odswierz) czy tez cyklicznie w tle?
6. Jak wyglada "apply" realnie na Google Ads API — ktore typy rekomendacji sa naprawde executable vs alert-only?
7. Czy jest rate limiting na bulk apply (np. max 10 na minute)?
