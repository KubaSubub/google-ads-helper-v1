# Notatki usera: Wynik jakości (Quality Score) — RE-TEST #3

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / Demo Meble Sp. z o.o. (client widoczny w sidebar)
**Data:** 2026-03-29 (re-test #3)
**Screenshot:** `frontend/e2e-screenshots/quality-score.png`

---

## Co widze po wejsciu

Nagłówek "Audyt Quality Score" z liczbą analizowanych keywords (28 słów kluczowych). Cel: średni QS powyżej 7.0 — widoczny w prawym górnym rogu. Przyciski eksportu CSV / XLSX (XLSX wyróżniony zielonym kolorem) + Odśwież.

5 kart KPI w jednym rzędzie:
- **Średni QS** — 6.7/10 (kolor żółty = sredni zakres, poprawny)
- **Niski QS (<5)** — 4 wymaga uwagi (czerwony, uwaga alarmowa)
- **Wysoki QS (8-10)** — 11 (zielony)
- **Wydatki na niski QS** — 16.7%, 832.72 zł z budżetu (żółte ostrzeżenie)
- **IS utracony (ranking)** — 17.1%, średnia utrata z powodu QS + bid (fioletowy)

Pasek filtrów z 4 dropdownami: kampania, typ dopasowania, rodzaj problemu, próg QS. Po prawej stronie pill buttons: Wszystkie / Niski QS / Wysoki QS + Grupuj.

2 wykresy obok siebie:
- **Rozkład QS** — bar chart 1-10 z kolorami (czerwony 1-3, żółty 4-6, zielony 7-10). Wyraźna dominacja QS 7-9 — wizualnie czytelne.
- **Główne problemy** — Oczekiwany CTR (15), Trafność reklamy (7), Strona docelowa (4). Paski poziome z liczbami. Od razu widzę że CTR to dominujący problem.

Pod wykresami — tabela słów kluczowych z sortowaniem.

Całość po polsku. Design spójny z resztą aplikacji (dark mode, Syne font, v2-card).

## Co moge zrobic

- **5 KPI kart** z kolorowaniem per zakres (czerwony/żółty/zielony/fioletowy) — natychmiastowy odczyt stanu konta
- **Filtrować** po kampanii (dropdown z listą kampanii klienta), match type (dokładne/do wyrażenia/przybliżone), rodzaju problemu (CTR/trafność/strona), progu QS (konfiguralny < 3 do < 7)
- **Quick view pills** — Wszystkie / Niski QS / Wysoki QS — szybki toggle bez grzebania w filtrach
- **Grupuj po ad group** — karty z średnim QS per grupa reklam, posortowane od najsłabszej. Widzę od razu które ad groupy wymagają interwencji
- **Sortować tabelę** — po słowie kluczowym, QS, CTR%, koszt, impressions, konwersje, IS lost
- **Eksport CSV/XLSX** — export pełnych danych do arkusza, np. do przekazania klientowi
- **Deep link do Google Ads** — ikona ExternalLink per keyword, otwiera bezpośrednio w natywnym GAds
- **Kliknięcie wiersza** — nawigacja do strony /keywords (zarządzanie słowami)
- **Subcomponent dots** — 3 kolorowe kropki per keyword (CTR / Ad Relevance / Landing Page) — szybki wizualny scan bez czytania wartości
- **Kolumna Rekomendacja** — per keyword tekstowa sugestia co poprawić. Jeśli keyword OK — zielony checkmark
- **Odśwież** — ręczne przeładowanie danych bez F5

## Co mam WIECEJ niz w Google Ads UI

1. **Audyt QS z KPI** — Google Ads pokazuje QS per keyword w kolumnie, ale nie daje żadnego podsumowania: ile słów z niskim QS, ile budżetu na nie idzie, jaki jest średni QS na koncie. Tu to mam od razu w 5 kartach.
2. **Issue breakdown** — wykres "główne problemy" z podziałem na CTR vs Ad Relevance vs Landing Page z liczbami. W GAds muszę sam zliczać — tu mam natychmiast.
3. **Wydatki na niski QS** — karta "16.7% budżetu na niski QS" — tego nie ma nigdzie w GAds. Kluczowa metryka dla argumentacji wobec klienta.
4. **IS utracony z powodu rankingu** — średnia dla konta. W GAds mam to per keyword/kampania, ale nie jako zagregowane KPI.
5. **Grupowanie po ad group** — widzę które ad groupy "ciągną w dół" średni QS. W GAds muszę to sam zestawiać ręcznie.
6. **Rekomendacja per keyword** — GAds daje ogólne recommendations, ale nie kontekstową sugestię per keyword bazującą na subkomponentach.
7. **Eksport XLSX z audytem** — mogę wygenerować raport do klienta jednym kliknięciem. W GAds muszę sam budować raporty.
8. **Konfigurowalny próg QS** — mogę ustawić próg na < 3, < 5, < 7 — w GAds nie ma takiego filtra natywnie.

## Czego MI BRAKUJE vs Google Ads UI

1. **Trend QS w czasie** — nie widzę jak QS zmieniał się w ciągu ostatnich 30/60/90 dni. Pytanie "czy moje optymalizacje landing page poprawiły QS?" nie ma odpowiedzi. To jedyna poważna luka — `historical_quality_score` jest w modelu, ale nie ma chart'u z trendem.
2. **Bid adjustment suggestions** — wiem że QS jest niski, wiem że IS tracę, ale nie widzę sugestii "podnieś bid o X%" albo "obniż bid bo QS za niski, marnujesz budżet". Rekomendacje są tekstowe, ale nie actionable z liczbami.
3. **Porównanie QS vs konkurencja** — Google Ads daje auction insights; tu nie widzę jak mój QS wypada vs inne reklamy w tej aukcji.
4. **Filtr po statusie keyword** — nie widzę czy keyword jest enabled/paused. Jeśli mam 4 słowa z niskim QS, ale 2 są paused, to nie jest pilne.
5. **Paginacja tabeli** — przy koncie z 500+ keywords tabela może być bardzo długa. Brak lazy loading lub paginacji.

## Co mnie irytuje / myli

1. **Waluta "zł" w kolumnie "Koszt (zł)"** ale dane z API to `cost_usd` — nazwa pola sugeruje dolary, UI pokazuje złotówki. Mały mismatch nazewnictwa (kosmetyka, nie UX-breaker).
2. **Kliknięcie wiersza → /keywords** — za ogólne. Chciałbym przejść do konkretnego keyword'a, nie do ogólnej listy. Teraz tracę kontekst.
3. **Próg QS domyślnie < 5** — dla większości kont bardziej przydatny byłby próg < 6 lub < 7 jako default. QS 5 to nadal słowo wymagające uwagi.

## Chcialbym jeszcze

1. **Trend QS mini-chart** — sparkline przy KPI "Średni QS" pokazujący trend z 30 dni. Albo osobna sekcja "QS trend".
2. **Top 5 worst keywords** — wyróżniona sekcja z 5 najgorszymi słowami (lowest QS + highest spend) — priorytetyzacja dla specjalisty.
3. **Quick action: pause keyword** — dla keywords z QS 1-2 i wysokim spend, opcja "pause" bezpośrednio z audytu.
4. **A/B porównanie okresów** — "QS w tym miesiącu vs poprzedni miesiąc" — czy robię postęp?

## Verdykt

Najlepsza zakładka w całej aplikacji pod względem kompletności i wartości dla specjalisty GAds. KPI karty dają natychmiastowy odczyt stanu konta. Issue breakdown pozwala priorytetyzować działania. Ad group grouping i deep links to features których brakuje w natywnym GAds. Eksport XLSX zamyka pętlę — mogę raportować klientowi.

Jedyny poważny brak to trend QS w czasie — bez niego nie mogę ocenić czy moje optymalizacje przynoszą efekt.

**Ocena: 9/10** (utrzymuję z re-testu #2; brak trendu QS to jedyny poważny minus)

---

## Pytania do @ads-expert

1. **Trend QS** — `historical_quality_score` jest w modelu `Keyword`. Czy to wystarczy do budowy trendu, czy potrzebujemy snapshot'ów QS per dzień w `KeywordDaily`?
2. **Bid suggestions** — czy rekomendacje powinny zawierać konkretne wartości bid, czy wystarczą kierunkowe sugestie (podnieś/obniż)?
3. **Auction insights integration** — czy warto dodać porównanie QS vs competition z auction insights, czy to za dużo dla v1?
4. **Domyślny próg QS** — czy < 5 to dobry default, czy lepiej < 6 (bardziej restrykcyjny)?
5. **Paginacja** — przy ilu keywords tabela zaczyna być nieużywalna? 50? 100? 500?
