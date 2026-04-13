# Notatki usera: Raporty (Reports) — RE-TEST #2

**Kto:** Marek, specjalista GAds, 6 lat doswiadczenia, 8 kont
**Testowane na:** seed data / client widoczny w sidebar
**Data:** 2026-03-27 (re-test)

---

## Co widze po wejsciu

Nagłówek "Raporty" z ikonką + badge "Claude dostępny/niedostępny". Po prawej: pille typu raportu (Miesięczny/Tygodniowy/Zdrowie konta), selektor okresu (dropdown z 12 ostatnich miesięcy), przycisk "Generuj" z gradientem + "PDF / Drukuj". Layout dwukolumnowy: po lewej lista zapisanych raportów (260px), po prawej treść aktywnego raportu.

Widać że to zaawansowany feature — generowanie raportów AI z SSE streamingiem, progress bar, token usage badge.

## Co moge zrobic

- **Wybrać typ raportu** — Miesięczny, Tygodniowy, Zdrowie konta (3 pille)
- **Wybrać okres** — dropdown z ostatnich 12 miesięcy (tylko dla Miesięcznego)
- **Generować raport** — przycisk "Generuj", streamuje przez SSE z progress barem
- **Przeglądać zapisane** — lista po lewej z datami, statusami (Gotowy/Generowanie/Błąd)
- **Drukować/PDF** — przycisk "PDF / Drukuj" (window.print())
- **Widzieć strukturalne sekcje** — porównanie m/m (KPI karty z delta), tabela kampanii, zmiany na koncie, wpływ zmian, pacing budżetów
- **Token usage** — badge z modelem, input/output tokens, koszt

## Co mam WIECEJ niz w Google Ads UI

1. **AI-generowany raport narracyjny** — w GAds mogę wyeksportować surowe dane. Tu dostaję narrację z wnioskami, porównaniami, rekomendacjami. To oszczędza mi 1-2h na pisaniu raportu dla klienta.
2. **3 typy raportów** — Miesięczny (deep dive), Tygodniowy (quick check), Zdrowie konta (audit). W GAds mam tylko "Custom reports" z tabelkami.
3. **Strukturalne sekcje** — porównanie m/m z delta indicators, tabela kampanii z m/m zmianami, change impact analysis. Dane + narracja + wizualizacja razem.
4. **Change Impact Analysis** — "Wpływ zmian na wyniki" z before/after 7 dni. W GAds nie ma czegoś takiego automatycznie.
5. **Przycisk PDF/Drukuj** — jednym klikiem. Mogę wysłać klientowi.
6. **Historia raportów** — widzę zapisane raporty po lewej, mogę wrócić do dowolnego.

## Czego MI BRAKUJE vs Google Ads UI

1. **Brak filtra kampanii** — generuję raport dla WSZYSTKICH kampanii. Klient pyta "jak idzie kampania X?" — nie mogę wygenerować raportu TYLKO dla niej.
2. **Brak porównania raportów** — mam listę raportów z różnych miesięcy po lewej, ale nie mogę ich nałożyć na siebie. "Czy styczeń był lepszy od grudnia?"
3. **Token usage badge** — jako specjalista GAds nie wiem co to "input tokens: 45,230". To info dla developera, nie dla mnie. Myli.

## Co mnie irytuje / myli

1. **Token usage badge widoczny** — pokazuje model AI, tokeny, koszt w dolarach. Dla mnie jako usera to jest szum. Nie obchodzi mnie ile tokenów zużyło — obchodzi mnie czy raport jest dobry.
2. **"Claude niedostępny" bez wyjaśnienia** — gdy Claude nie jest dostępny, widzę czerwony badge ale nie wiem CO zrobić. Brak instrukcji "Skonfiguruj klucz API" albo "Sprawdź ustawienia".
3. **Brak preview przed generowaniem** — klikam "Generuj" i czekam. Nie wiem z góry jakie dane zostaną użyte, jaki zakres dat.

## Co bym chcial

1. **Filtr kampanii przy generowaniu** — dropdown "Wszystkie kampanie" / "Tylko: Kampania X".
2. **Ukrycie token usage** — albo za togglem "Pokaż szczegóły techniczne", albo usunąć z UI usera.
3. **Automatyczne raporty cykliczne** — scheduler "co poniedziałek tygodniowy, co 1-go miesięczny".
4. **Email delivery** — "Wyślij raport na email klienta".

## Verdykt

Zakładka Reports to prawdziwa wartość dodana — AI generuje narracyjny raport którego pisanie zajęłoby mi 1-2h. 3 typy raportów pokrywają moje potrzeby. PDF/Drukuj działa. Brakuje filtra kampanii i schedulera, ale nawet bez nich to jest 10x lepsze niż Custom Reports w GAds. Token usage badge to jedyna rzecz która razi — powinna być ukryta lub opcjonalna.

**Ocena: 8/10**

---

## Pytania do @ads-expert

1. Filtr kampanii przy generowaniu — czy dane w backendzie pozwalają na raport per kampania?
2. Token usage badge — celowo widoczny dla usera czy to developer debug info które zostało?
3. Scheduler — "generuj raport co tydzień automatycznie" — jak blisko jest to w architekturze?
4. Porównanie raportów — side-by-side marzec vs luty — realistyczne do implementacji?
