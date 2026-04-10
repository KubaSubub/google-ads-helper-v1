# Ocena eksperta Google Ads — Poranny Przegląd (Daily Audit)
> Data: 2026-04-10 | Średnia ocena: 7.5/10 | Werdykt: ZMODYFIKOWAC

---

### TL;DR
Poranny Przegląd to najbardziej wartościowa zakladka w aplikacji — jako konsolidator codziennego triage'u KPI + alertów + rekomendacji + search terms w jednym scrollu realnie oszczędza 20-30 min dziennie przy obsłudze wielu kont. Krytyczny problem: brak CPA, ROAS i CTR w KPI sprawia, że specjalista widzi zmianę wolumenu, ale nie wie czy efektywność rośnie czy spada — bez tych metryk poranny przegląd jest niekompletny na poziomie podstaw playbooka (Część 2.1: Kluczowe Metryki).

---

### Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebnosc | 10/10 | Codzienne narzędzie pracy — Daily Checks to rdzeń playbooka (Część 1.1), 15-30 min/konto/dzień. Żadna inna zakladka nie zastępuje porannego triage'u |
| Kompletnosc | 6/10 | Core sekcje działają (alerty, rekomendacje, pacing, search terms), ale brak CPA/ROAS/CTR w KPI to krytyczna luka vs. playbook Część 2.1 |
| Wartosc dodana vs Google Ads UI | 8/10 | Unikalna konsolidacja 5 obszarów w jednym widoku + szybkie skrypty bulk-action — tego nie ma w Google Ads UI w żadnej formie |
| Priorytet MVP | 8/10 | Must-have zakladka dla produktu, który ma zastąpić codzienną rutynę specjalisty. Bez daily audit cały produkt traci sens jako "asystent poranny" |
| **SREDNIA** | **8.0/10** | _(korygowana w dół za braki KPI)_ → prezentowana: **7.5/10** |

---

### Co robi dobrze

- **Konsolidacja porannego triage** — alert banner + status badge (krytyczne/OK) + rekomendacje pogrupowane po priorytecie + budget pacing + search terms w jednym widoku. Playbook Część 1.1: "Codzienne Daily Checks" — 5 z 4 wymaganych kroków pokryte w jednym scrollu. Realnie eliminuje konieczność otwierania 4-5 zakładek Google Ads każdego ranka.
- **Szybkie skrypty optymalizacji** — `clean_waste`, `pause_burning`, `boost_winners`, `emergency_brake` jako bulk-apply z modal preview. Playbook Część 1.1 (pkt 3-4): "Search Terms Review" + "Pause Poor Performers" z jednym kliknięciem. Unikalna wartość — Google Ads nie ma odpowiednika.
- **Alert banner z typologią alertów** — rozróżnienie `anomaly` / `disapproved` / `budget_capped` w jednym miejscu. Playbook Część 5.1: Anomaly Detection — zaimplementowane.
- **Pending recommendations z priorytetyzacją** — grupy HIGH/MEDIUM/LOW z preview top 3 itemy per group. Playbook Część 5.3: Recommendation Engine — zaimplementowane.
- **Budget pacing z IS lost** — tabela z `pacing_pct`, `is_limited`, `budget_lost_is`. Playbook Reguła 7: "When to REALLOCATE budget" wymaga znajomości IS lost — jest.
- **Prefiltrowane search terms** — filtr: `clicks >= 3 AND conversions = 0 OR cost > 5 USD AND conversions = 0`. Playbook Reguła 5: kiedy dodać negative keyword — threshold zgodny.

---

### Co brakuje (krytyczne)

- **CPA w KPI snapshot** — `_build_kpi_snapshot()` (daily_audit.py:482) zwraca tylko `cost`, `clicks`, `conversions`. Brakuje `cost/conversions`. Playbook Część 2.1: CPA to podstawowa metryka. Specjalista bez CPA nie może ocenić czy -28% konwersji i -27% kosztów = problem czy OK. Implementacja: dodać `current_cpa` i `previous_cpa` do `_agg()`, wyświetlić jako 4. KpiChip w frontend DailyAudit.jsx:407-409.
- **ROAS w KPI snapshot** — dla klientów e-commerce (Demo Meble, Sushi Naka Naka) ROAS ważniejszy niż liczba konwersji. Playbook Część 2.1: ROAS >400% dla e-commerce. Backend nie zwraca `conversion_value_micros` z MetricDaily — trzeba dodać do `_agg()` i do modelu MetricDaily, jeśli kolumna istnieje.
- **CTR w KPI snapshot** — `clicks/impressions` to standard poranny. Playbook Część 2.1: CTR >2% branded, >1% non-branded. `_agg()` nie agreguje `impressions` z MetricDaily. Implementacja prosta: dodać `func.sum(MetricDaily.impressions)` do query.
- **Skrypty zwinięte gdy są akcje** — `loadScriptCounts()` ustawia `setScriptsExpanded(true)` gdy `total > 0`, ale Marek widzi zwinięte (bug: stan nullable `null → true` może być rozwiązany zbyt późno po renderze). Kluczowy problem UX: przy 3 krytycznych alertach akcje powinny być widoczne od razu. DailyAudit.jsx:249-250.
- **Brak timestamp ostatniego synca** — w `_build_health_summary()` lub nagłówku brakuje info kiedy dane były ostatnio zsynchronizowane z Google Ads. Rano specjalista musi wiedzieć czy ogląda dane z 22:00 czy z 06:00. Krytyczne dla wiarygodności całego auditu.

---

### Co brakuje (nice to have)

- **Top moverzy (biggest changes per campaign)** — playbook Część 1.1 pkt 2: "identyfikacja anomalii" to kluczowy krok. Teraz widać konto jako całość, nie które kampanie straciły 80% konwersji. Backend: zapytanie na MetricDaily per campaign z porównaniem current vs previous period. 5 kampanii z biggest delta.
- **Mini-sparklines przy KPI** — 7-dniowa linia trendu zamiast tylko "teraz vs poprzednio". Marek słusznie pyta — zmiana jednorazowa (spike) vs trend strukturalny to różne diagnozy.
- **Interpretacja automatyczna zmian** — np. "CPA stabilny (-1.5%), spadek wolumenu". Ryzykowne jeśli zrobione naiwnie, ale przy prostej logice (CPA zmiana <10% = stabilny) daje wartość. Playbook Część 3.1: Daily Optimization Flow zakłada ocenę anomalii.
- **Konfigurowalny okres porównania** — hardcoded 3 dni (`period_days=3` w `_build_kpi_snapshot()`). Dodać query param `period` albo integrację z globalnym date pickerem sidebara. Playbook Część 1.1: "Last 7 days vs Previous 7 days" dla tygodniowych.
- **Historia audytów** — "7 dni temu: 2 alerty, dziś: 10" — trend problematyczności konta. Wymaga tabeli `audit_snapshots` w DB — v2 feature.
- **Budget pacing wyżej w layoucie** — Marek słusznie zwraca uwagę: budget pacing to najważniejsza pierwsza rzecz rano ("Czy jesteśmy w budżecie?" — playbook pkt 1). Aktualnie jest w ROW 4 (pod KPI, skryptami, search terms i rekomendacjami). Prosta zmiana layoutu w DailyAudit.jsx.

---

### Co usunąć/zmienić

- **Kolorowanie spadku kosztów na czerwono** — `-27% wydatki` w KpiChip wyświetla się tak samo jak `-28% konwersje`. KpiChip nie rozróżnia metryk gdzie "w dół = dobrze" (koszty) od "w dół = źle" (konwersje). Wymaga albo: (a) props `inverseColor` na KpiChip, albo (b) wyświetlanie CPA zamiast raw cost (CPA stabilny = nic się nie dzieje). Obecne kolorowanie aktywnie wprowadza w błąd.
- **Zmienna `cost_usd` przy labelce "zł"** — DailyAudit.jsx:479: `{t.cost_usd?.toFixed(2)} zł`. Backend daily_audit.py:356: `"cost_usd": round(micros_to_currency(st.cost_micros), 2)`. Jeśli seed/przeliczenie jest poprawne (1:1 z lokalną walutą PLN) — zmienić nazwę pola na `cost` lub `cost_pln` w backend i frontend. Semantyczne wprowadzanie w błąd i potencjalny bug przy multi-walutowych kontach.
- **Przycisk "Szczegóły" w alert bannerze** — nawiguje do `/alerts` zamiast do konkretnego alertu. DailyAudit.jsx:381. Traci kontekst. Mała poprawa: przekazać `?alert_id=X` do Alerts page i auto-scroll/highlight do konkretnego alertu.
- **Usunąć label "(zaawansowane)"** obok "Szybkie skrypty optymalizacji" — sugeruje że to coś niebezpiecznego lub opcjonalnego. Te skrypty to rdzeń wartości produktu. Etykieta zniechęca do klikania zamiast zachęcać.

---

### Porównanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Spend/Clicks/Conversions overview | Overview tab, osobna zakładka | Inline w audit | LEPSZE (jeden widok) |
| CPA w porannym check | Overview tab | BRAK | GORSZE |
| ROAS overview | Overview tab | BRAK | GORSZE |
| CTR w overview | Overview tab | BRAK | GORSZE |
| Alert o disapproved ads | Kolumna w Ads tab | Alert banner | LEPSZE (proaktywne) |
| Budget capped campaigns | Campaign tab + IS columns | Inline w audit | LEPSZE (automatyczny triage) |
| Search terms wasteful spend | Search terms tab + ręczne filtry | Prefiltrowane | LEPSZE |
| Bulk pause no-conv keywords | Ręcznie per keyword | Jeden klik z preview | LEPSZE |
| Bulk add negatives | Ręcznie per term | Jeden klik z preview | LEPSZE |
| Biggest changes (top movers) | "Biggest changes" w Overview | BRAK | GORSZE |
| Budget pacing % | Brak (trzeba liczyć ręcznie) | Progress bar | LEPSZE |
| Impression Share lost w kontekście pacing | Kolumny w Campaign tab | Inline w pacing table | LEPSZE |
| Audit history / trend alertów | BRAK | BRAK | IDENTYCZNE (oboje nie mają) |
| Timestamp ostatniego synca | Widoczny w UI | BRAK | GORSZE |
| Quick performance interpretation | BRAK | BRAK | IDENTYCZNE |

---

### Odpowiedzi na pytania Marka (@ads-user)

1. **Date range niezależny vs globalny?** — Globalny date picker powinien kontrolować KPI snapshot (zamienić hardcoded `period_days=3` na `days` z FilterContext), ale anomalie 24h i disapproved ads powinny być zawsze "ostatnie 24h" niezależnie od filtra. Dwa tryby: "alerty operacyjne" = zawsze fresh, "KPI" = date-filtered.

2. **Top 5-6 KPI dla porannego check?** — Priorytet: **Spend, CPA, Conversions, ROAS, CTR, Impression Share**. CPA i ROAS są ważniejsze niż raw Spend i Conversions, bo mówią o efektywności. Spend bez CPA to liczba bez kontekstu.

3. **Dry-run preview przed skryptami?** — Obecny model (klik → modal z dry-run → confirm) jest POPRAWNY. Dry-run jest robiony (`dryRun=true` w `loadScriptCounts()`), ale w `runScript()` od razu wywołuje `dryRun=false`. Sugestia: dodać krok pośredni — najpierw klik pokazuje dry-run modal, drugi klik wykonuje. To obowiązek przy bulk-apply na prawdziwych kontach.

4. **Top moverzy — must-have czy nice-to-have?** — **Must-have na poziomie dobrego produktu, nice-to-have na MVP.** Playbook pkt 2 daily checks: "identyfikacja anomalii" = często oznacza "która kampania się zepsuta". Bez top movers specjalista musi wejść do Campaigns tab. Priorytet: v1.1.

5. **Auto-interpretacja zmian — pomaga czy ryzykowna?** — Pomaga, ale tylko przy prostej logice: `delta_CPA < ±10%` → "CPA stabilny". Bardziej złożona interpretacja rodzi false confidence. Implementować jako jedno zdanie w nagłówku, nie jako "diagnozę". Zawsze pokazuj surowe liczby obok.

6. **Budget pacing: tabela vs gauge/heatmap?** — Tabela jest lepsza operacyjnie dla >5 kampanii. Gauge jest czytelniejszy dla ≤3 kampanii. Pozostawić tabelę, ale dodać color-coded row highlighting (czerwony >95% pacing, żółty 85-95%, zielony <85%).

---

### Rekomendacja końcowa

**ZMODYFIKOWAC** — priorytet WYSOKI, następny sprint.

Poranny Przegląd to prawdopodobnie zakladka z najwyższym ROI dla specjalisty PPC w całej aplikacji — konsoliduje codzienną rutynę i dostarcza unikalną wartość vs Google Ads UI. Jednak bez CPA i ROAS w KPI snapshot produkt obiecuje "poranny przegląd efektywności" a dostarcza "poranny przegląd wolumenu". To różnica między narzędziem do podejmowania decyzji a narzędziem do ogłądania liczb. Trzy krytyczne zmiany wystarczą żeby wejść na poziom 9/10: (1) dodać CPA+ROAS+CTR do KPI, (2) naprawić bug z auto-expand skryptów, (3) dodać timestamp ostatniego synca. Budget pacing wyżej w layoucie i usunięcie mylącego czerwonego kolorowania kosztów to bonus.
