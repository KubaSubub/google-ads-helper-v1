# Notatki usera: Poranny Przegląd (Daily Audit) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doświadczenia, 8 kont
**Testowane na:** Demo Meble Sp. z o.o. (client_id=3), seed data
**Data:** 2026-03-29

---

## Co widzę po wejściu

Nagłówek "Poranny Przegląd" z podtytułem "Ostatnie 3 dni / 10 kampanii / 28 słów kluczowych". W prawym górnym rogu czerwony pill badge "3 krytyczne" i przycisk "Odśwież".

Pod spodem:

1. **Alert banner** — czerwone tło, "10 alertów wymaga uwagi". Widoczne tagi: SPEND SPIKE, CONVERSION DROP (x2), jedna odrzucona reklama ("Demo Meble — Darmowa D..." — ucięte), "+6 więcej". Przycisk "Szczegóły >" na prawo.
2. **3 kafelki KPI** — Wydatki (6 222,83 zł, -27.1%), Kliknięcia (3173, -18.3%), Konwersje (124,04, -28.2%). Wszystkie na minus, wszystkie w czerwonym kolorze trendu.
3. **Szybkie skrypty optymalizacji** — accordion, label "(zaawansowane)", na screenshocie zwinięty.
4. **Dwie kolumny**:
   - Lewa: **Frazy do przejrzenia (0)** — pusta, "Brak fraz wymagających akcji". Link "Wszystkie" do /search-terms.
   - Prawa: **Oczekujące rekomendacje (61)** — 3 grupy widoczne: "Obniż stawkę" (7 HIGH, top items: narożnik do salonu 8 konw., łóżko drewniane 27 konw., łóżko sklep 18 konw., +4 więcej), "Qs Alert" (4 HIGH, top items: kanapa narożna 24 konw., biurko do domu 22 konw., biurko regulowane 7 konw., +1 więcej), "Disapproved Ad Alert" (3 HIGH — ucięte na dole screena).
5. **Pacing budżetu** — nie widoczny na screenshocie (pod scrollem), ale potwierdzony w kodzie: tabela z kampaniami, budżetem dziennym, wydanym, progress bar pacing %, status LIMITED.

Sidebar: globalny date picker ustawiony na "30 dni", filtry typu kampanii: Wszystkie / Search / PMax / Shopping / Display / Video.

---

## Co mogę zrobić

- **Odświeżyć dane** — przycisk "Odśwież" przeładowuje cały audit + zlicza akcje w skryptach.
- **Przejść do szczegółów alertów** — "Szczegóły" w bannerze nawiguje do /alerts.
- **Rozwinąć szybkie skrypty** — accordion odsłania 4 przyciski: "Wyczyść śmieci" (add negatives), "Pauzuj spalające" (pause high-cost no-conv keywords), "Boost winnerów" (increase budget for good CPA), "Hamulec awaryjny" (lower bids, pause extreme CPA). Każdy pokazuje count. Klik = bulk-apply z modalem wyników.
- **Przejść do fraz** — link "Wszystkie" przy sekcji frazy.
- **Przejść do rekomendacji** — link "Wszystkie" przy sekcji rekomendacji.
- **Scrollować do pacing budżetu** — tabelka z kampaniami, legendą kolorów, tooltipem IS.

---

## Co mam WIĘCEJ niż w Google Ads UI

1. **Poranny checklist w jednym scrollu.** W Google Ads muszę oddzielnie sprawdzać: Overview (zmiany wydatków), Recommendations, Search Terms, odrzucone reklamy, budget status. Tu mam 5 sekcji w jednym widoku. Przy 8 kontach to realna oszczędność 20-30 minut dziennie.
2. **Szybkie skrypty optymalizacji.** Google Ads ma "Apply all" w Recommendations, ale nie ma jednego przycisku "pauzuj wszystko co spala bez konwersji" albo "dodaj negatywy na śmieciowe frazy". Bulk-action z dry-run preview to unikalna wartość.
3. **Prefiltrowane frazy do przejrzenia.** W Google Ads muszę sam ustawić filtry (clicks >= 3, conversions = 0). Tutaj gotowy shortlist.
4. **Rekomendacje pogrupowane po typie z priorytetem HIGH/MEDIUM/LOW.** W Google Ads Recommendations są pogrupowane po kategorii optymalizacji (Ads, Bidding, Keywords). Tu widzę je przez pryzmat pilności.
5. **Health badge (3 krytyczne) w headerze.** Natychmiastowy triage — otwieram, widzę czerwony → kopię dalej. Zielony → śniadanie.
6. **Alert banner z typami alertów.** W Google Ads nie ma jednego miejsca gdzie widzę: anomalie + odrzucone reklamy + budget-capped kampanie razem.

---

## Czego MI BRAKUJE vs Google Ads UI

1. **CPA / ROAS w KPI.** Widzę wydatki (6222 zł), kliknięcia (3173), konwersje (124,04) — ale NIE widzę CPA ani ROAS. To jest PODSTAWOWA metryka porannego przeglądu. 6222 zł / 124,04 = CPA 50,18 zł. Ale czy to dobrze? Spadek konwersji -28,2% przy spadku kosztów -27,1% = CPA prawie bez zmian. Tego NIE WIDAĆ bez CPA.
2. **CTR w KPI.** Spadek kliknięć -18,3% przy spadku kosztów -27,1% sugeruje, że CTR mogło wzrosnąć — ale nie wiem tego. CTR to basic metric.
3. **Conversion Value / przychód.** Dla e-commerce (Demo Meble) wartość zamówień jest ważniejsza niż liczba transakcji. 124 konwersje po 50 zł to nie to samo co 124 konwersje po 200 zł.
4. **Impression Share.** Nie widzę IS% na poziomie konta. Spadek IS = tracę aukcje. W Google Ads Overview widzę IS od razu.
5. **Dane per campaign type.** Agregat 10 kampanii nie mówi, czy -28% konwersji to Search, PMax czy Shopping. Filtry typu kampanii w sidebarze NIE wpływają na audit endpoint.
6. **Top moverzy — kampanie z największą zmianą.** Google Ads Overview ma "Biggest changes". Chcę widzieć: która kampania straciła 80% konwersji, a która zyskała.
7. **Change history / log zmian.** Rano sprawdzam, czy nocna reguła albo kolega nie zmieniło czegoś. Tu nie mam logów.
8. **Quality Score overview.** "Qs Alert" jest w rekomendacjach, ale nie widzę średniego QS konta ani rozkładu.
9. **Auction insights / sygnały od konkurencji.** IS lost to rank, nowi gracze w aukcji — tego tu nie ma.
10. **Okres porównania niekonfigurowalny.** Hardcoded "ostatnie 3 dni vs poprzednie 3". Nie mogę zmienić na wczoraj vs dzień wcześniej, ani 7 vs 7.
11. **Eksport / email.** Nie mogę wysłać porannego briefingu klientowi jako PDF albo email.
12. **Historia audytów.** Nie widzę "wczoraj było 3 alerty, dziś 10". Brak trendu alertów.

---

## Co mnie irytuje / myli

1. **Kolorowanie spadku wydatków na czerwono.** -27% wydatki wyświetla się identycznie jak -28% konwersje — obie czerwone ze strzałką w dół. Ale spadek kosztów MOŻE być dobrą wiadomością (jeśli CPA się poprawił). System powinien interpretować: koszty w dół + konwersje stabilne = zielony. Koszty w dół + konwersje w dół jeszcze bardziej = czerwony.
2. **"Frazy do przejrzenia (0)" — puste przy 3173 kliknięciach.** Albo seed data nie generuje search terms z clicks >= 3 i 0 conversions, albo filtr jest za ciasny. Przy prawdziwym koncie to byłoby 20-50 fraz. Nowy user zobaczy pustą sekcję i pomyśli, że narzędzie nie działa.
3. **Skrypty domyślnie zwinięte mimo 3 krytycznych alertów.** Kod mówi: auto-expand gdy count > 0. Ale na screenshocie sekcja jest zwinięta. Jeśli mam 3 krytyczne — chcę widzieć akcje od razu.
4. **Rekomendacja "Obniż stawkę" + "8 konw." — brakuje kontekstu.** Keyword "narożnik do salonu" z 8 konwersjami powinien mieć obniżoną stawkę? Dlaczego? Brakuje CPA tego keywordu vs target CPA. Same konwersje nie mówią, czy stawka jest za wysoka.
5. **Label "zł" przy polu `cost_usd` w kodzie.** Zmienna w kodzie to `cost_usd` ale wyświetlane jest "zł". Jeśli dane to USD a wyświetlam PLN — to bug. Jeśli dane to PLN — nazwa zmiennej myli.
6. **Brak timestampa ostatniego synca.** Nie wiem czy patrzę na dane sprzed godziny czy sprzed 12h. Rano o 8:00 mogę widzieć dane z 22:00 — bez tej info nie wiem.
7. **Alert banner ucina tekst alertów.** "Odrzucona: Demo Meble — Darmowa D..." — ucięte, nie mogę kliknąć w konkretny alert. "Szczegóły" prowadzi do ogólnej strony /alerts, nie do tego alertu.
8. **Brak pacing budżetu na first screen.** Muszę scrollować żeby zobaczyć budget pacing — a to jest moja PIERWSZA rzecz rano. Powinien być wyżej niż rekomendacje.

---

## Co bym chciał

1. **KPI: dodać CPA, ROAS, CTR, Conversion Value.** To jest absolutne minimum. Opcjonalnie: Avg. CPC, Impression Share.
2. **Interpretacja zmian.** Zamiast "Wydatki -27%, Konwersje -28%" → "CPA stabilny (50,18 zł, zmiana -1.5%). Spadek wolumenu, efektywność OK."
3. **Konfigurowalny okres porównania.** Wczoraj vs dzień wcześniej, 7 vs 7, 30 vs 30, custom.
4. **Budget pacing wyżej** — bezpośrednio pod KPI, przed rekomendacjami i frazami.
5. **Top moverzy** — 3-5 kampanii z największą zmianą w konwersjach / kosztach.
6. **Mini-sparkline przy KPI** — linia z 7-14 dni zamiast samego "teraz vs poprzednio".
7. **Filtrowanie auditu po typie kampanii** (Search / PMax / Shopping) — albo podsumowanie per typ.
8. **Timestamp ostatniego synca** w nagłówku.
9. **Eksport porannego briefingu** — PDF / clipboard / email.
10. **Historia audytów** — "7 dni temu: 2 alerty, dziś: 10" → trend problematyczności konta.

---

## Verdykt

**7/10 — dobra baza operacyjna, brakuje kluczowych metryk efektywności.**

Poranny Przegląd robi dobrze jedną rzecz: konsoliduje alertowe sygnały w jeden widok. Alert banner + badge krytyczności + rekomendacje pogrupowane po priorytecie + pacing budżetu — to realnie oszczędza czas i tego nie ma w Google Ads UI w jednym miejscu. Szybkie skrypty to unikalna wartość dodana.

ALE: jako specjalista, rano patrzę przede wszystkim na CPA, ROAS i trendy. Wydatki + kliknięcia + konwersje bez CPA/ROAS to jak termometr bez skali — widzę zmianę, ale nie wiem czy gorączka czy schłodzenie. Spadek kosztów -27% i konwersji -28% na czerwono wygląda jak katastrofa, a w rzeczywistości CPA się prawie nie zmienił — ale narzędzie tego nie pokazuje.

Gdybym miał 8 kont — użyłbym Porannego Przeglądu do szybkiego triage (kto critical, kto OK), ale po metryki efektywności i tak musiałbym wejść w Google Ads. To nie powinno tak wyglądać.

Poprzedni re-test dawał 9/10 — obniżam do 7/10 bo z perspektywy codziennego użytku brak CPA/ROAS mocno ogranicza wartość dashboardu. Dobrze to co jest. Brakuje tego co powinno być oczywiste.

---

## Pytania do @ads-expert

1. Czy poranny przegląd powinien mieć osobny date range niezależny od globalnego filtra, czy integrować się z globalnym date pickerem?
2. Jakie KPI powinny być w nagłówku auditu — top 5-6 metryk dla porannego PPC check? Moja propozycja: Spend, Conversions, CPA, ROAS, CTR, Impression Share.
3. Czy szybkie skrypty powinny mieć obowiązkowy dry-run preview przed wykonaniem, czy obecny model "klik = execution" jest akceptowalny?
4. Czy "top moverzy" (campaigns with biggest change) to must-have dla daily auditu, czy nice-to-have?
5. Interpretacja zmian (auto-generated summary "CPA stabilny, wolumen spadł") — czy to realnie pomaga, czy rodzi ryzyko błędnych wniosków?
6. Budget pacing: tabelka (jak teraz) vs wizualizacja (gauge/heatmap per kampania) — co lepsze operacyjnie?
