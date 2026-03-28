# GENERATE_FEATURE_LIST.md
## Instrukcja dla Claude Code — wygeneruj dokument testowania manualnego

**Zadanie:** Przejrzyj cały kod projektu i wygeneruj plik `MANUAL_TESTING_GUIDE.md` zawierający KOMPLETNĄ listę wszystkich funkcjonalności aplikacji Google Ads Helper — od A do Z — w formacie gotowym do ręcznego testowania.

---

## Jak wykonać to zadanie

### Krok 1 — Przeczytaj te pliki (kontekst projektu)
```
CLAUDE.md
PROGRESS.md
DECISIONS.md
backend/app/main.py
backend/app/models.py
backend/app/routers/  (wszystkie pliki)
frontend/src/App.jsx
frontend/src/components/Sidebar.jsx
frontend/src/pages/  (wszystkie pliki)
frontend/src/api.js
```

### Krok 2 — Zidentyfikuj WSZYSTKIE funkcjonalności

Dla każdego pliku w `backend/app/routers/` — wypisz każdy endpoint.  
Dla każdego pliku w `frontend/src/pages/` — wypisz każdą stronę i jej elementy UI.  
Dla `backend/app/services/recommendations.py` — wypisz każdą regułę engine.  
Dla `backend/app/services/analytics_service.py` — wypisz każdą metodę analityczną.

### Krok 3 — Wygeneruj plik `MANUAL_TESTING_GUIDE.md`

Struktura pliku opisana poniżej. Zapisz go w root repo.

---

## Wymagana struktura `MANUAL_TESTING_GUIDE.md`

```markdown
# Manual Testing Guide — Google Ads Helper
**Wersja:** [odczytaj z PROGRESS.md]
**Data wygenerowania:** [dzisiejsza data]
**Jak używać:** Przejdź przez każdą sekcję, przetestuj ręcznie, wpisz wynik: ✅ OK | ❌ BUG | ⚠️ Uwaga

---

## SEKCJA 1 — Onboarding & Konfiguracja

### 1.1 Pierwsze uruchomienie
[Opisz kroki: uruchomienie appki, pierwsze okno, co widać]

Kroki testowania:
1. [konkretny krok]
2. [konkretny krok]

Oczekiwany wynik: [co powinno się stać]
Wynik testu: ___________

### 1.2 Dodawanie klienta
[...]

### 1.3 Konfiguracja Google Ads credentials
[...]

---

## SEKCJA 2 — Synchronizacja danych

### 2.1 Ręczny sync (przycisk Refresh)
### 2.2 Które dane są synchronizowane (lista)
### 2.3 Status synchronizacji — gdzie to widać
### 2.4 Obsługa błędów sync

---

## SEKCJA 3 — Dashboard

[Dla każdego widgetau/elementu na stronie Dashboard — osobny punkt testowy]

### 3.1 KPI summary (dzisiejsze metryki)
### 3.2 Porównanie z poprzednim okresem
### 3.3 GlobalFilterBar — zmiana zakresu dat
### 3.4 GlobalFilterBar — filtr campaign type
### 3.5 GlobalFilterBar — filtr campaign status
### 3.N [każdy element osobno]

---

## SEKCJA 4 — Kampanie

[Każda kolumna, każdy filtr, każda akcja — osobny punkt]

### 4.1 Lista kampanii
### 4.2 Kolumny i sortowanie
### 4.3 Campaign Roles — auto-classification
### 4.4 Campaign Roles — manual override
### 4.5 Ochrona kampanii (protection level)
### 4.N [...]

---

## SEKCJA 5 — Słowa kluczowe

### 5.1 Lista keywords z filtrami
### 5.2 Status badges (Enabled/Paused/Removed)
### 5.3 Ukrywanie/pokazywanie usuniętych
### 5.4 Export keywords
### 5.5 Match type display
### 5.N [...]

---

## SEKCJA 6 — Search Terms

### 6.1 Lista search terms
### 6.2 Filtrowanie i wyszukiwanie
### 6.3 Bulk add negative — wybór terminów
### 6.4 Bulk add negative — wybór poziomu (campaign/ad group)
### 6.5 Bulk add keyword — wybór ad group
### 6.6 Bulk preview przed akcją
### 6.7 Search Term Trends (rosnące/spadające)
### 6.8 Close Variant Analysis
### 6.N [...]

---

## SEKCJA 7 — Rekomendacje Engine

[Dla KAŻDEJ reguły osobny punkt — przeczytaj recommendations.py i wypisz wszystkie]

### 7.1 R1 — Pause Keyword: wysoki koszt bez konwersji
**Warunek wyzwolenia:** cost ≥ $50, conv = 0, clicks ≥ 30
**Jak przetestować:** [opis]
**Apply button:** ✅/❌ działa
**Confirmation modal:** ✅/❌ wyświetla
**Rollback:** ✅/❌ możliwy
Wynik: ___________

### 7.2 R1b — Pause Keyword: niski CTR
### 7.3 R2 — Increase Bid
### 7.4 R3 — Decrease Bid
### 7.5 R4 — Add Keyword
### 7.6 R5 — Add Negative
### 7.7 R6 — Pause Ad
### 7.8 R7 — Reallocate Budget
### 7.9 R8 — Quality Score Alert
### 7.10 R9 — IS Lost to Budget
### 7.11 R10 — IS Lost to Rank
### 7.12 R11 — Low CTR Keyword
### 7.13 R12 — Wasted Spend Alert
### 7.14 R13 — PMax Cannibalization
### 7.15 R15 — Device Anomaly
### 7.16 R16 — Geo Anomaly
### 7.17 R17 — Budget Pacing
### 7.18 R18 — N-gram Negative
### 7.19 Smart Bidding Data Starvation
### 7.20 Single Ad Alert
### 7.21 Oversized Ad Group
### 7.22 Zero Conv Ad Group
### 7.N [każda reguła którą znajdziesz w kodzie]

Widok listy rekomendacji:
### 7.X Filtr: Rekomendacje vs Alerty (taby)
### 7.X Sortowanie po priorytecie
### 7.X Dismiss rekomendacji
### 7.X Context outcome badge
### 7.X Explanation (why_allowed / why_blocked)
### 7.X Disabled Apply dla INSIGHT_ONLY / BLOCKED_BY_CONTEXT

---

## SEKCJA 8 — Daily Audit

### 8.1 Otwarcie Daily Audit — co widać
### 8.2 Budget pacing per kampania
### 8.3 Unresolved anomaly alerts (last 24h)
### 8.4 Disapproved / approved-limited ads
### 8.5 Budget-capped kampanie z wysokim CPA
### 8.6 Top wasted search terms (last 7 days)
### 8.7 Pending recommendations summary
### 8.8 Health score
### 8.9 Today vs yesterday snapshot

---

## SEKCJA 9 — Negative Keywords

### 9.1 Lista negative keywords per klient
### 9.2 Tworzenie nowej listy negatywnych
### 9.3 Dodawanie keywords do listy
### 9.4 Usuwanie z listy
### 9.5 Bulk-apply listy na kampanie/ad groups
### 9.6 Podgląd które kampanie mają podpiętą listę

---

## SEKCJA 10 — Analytics Deep Dive

### 10.1 Device Breakdown (CPA per urządzenie)
### 10.2 Geo Breakdown (CPA per lokalizacja)
### 10.3 Budget Pacing view
### 10.4 N-gram Analysis
### 10.5 Keyword Expansion suggestions
### 10.6 Landing Page Analysis
### 10.7 Conversion Health
### 10.8 Search Term Trends
### 10.9 Close Variant Analysis

---

## SEKCJA 11 — Wpływ Zmian (Change Impact)

### 11.1 Lista wykonanych akcji z datami
### 11.2 Delta KPI: before vs after (7 dni)
### 11.3 Verdict: POSITIVE / NEGATIVE / NEUTRAL
### 11.4 Akcje zbyt świeże (< 7 dni) — oznaczenie
### 11.5 Expandowanie szczegółów akcji

---

## SEKCJA 12 — Pareto / 80-20 Analysis

### 12.1 Pareto per kampania (konwersje)
### 12.2 Pareto per keyword
### 12.3 Flagi: HERO / MAIN / TAIL
### 12.4 Alert: hero kampania ograniczona budżetem
### 12.5 Zmiana metryki (conversions / cost / roas)

---

## SEKCJA 13 — Bid Strategy Health

### 13.1 Lista kampanii z Smart Bidding
### 13.2 Target CPA vs Actual CPA per kampania
### 13.3 Target ROAS vs Actual ROAS
### 13.4 Verdict: ON_TARGET / TOO_AGGRESSIVE / TOO_LOOSE
### 13.5 Alert: kampania nie dowozi targetu (>14 dni)
### 13.6 Alert: target zbyt łagodny (>14 dni)
### 13.7 Alert: ECPC deprecated → Manual CPC
### 13.8 Alert: Learning period extended

---

## SEKCJA 14 — Monitoring & Anomalie

### 14.1 Lista anomalii
### 14.2 Resolve anomalii
### 14.3 Alert thresholds
### 14.4 Severity levels

---

## SEKCJA 15 — Forecast

### 15.1 Otwarcie Forecast
### 15.2 Prognoza kosztów
### 15.3 Prognoza konwersji
### 15.4 Zakres dat

---

## SEKCJA 16 — Raporty AI (Agent)

### 16.1 Generowanie raportu tygodniowego
### 16.2 Generowanie raportu kampanii
### 16.3 Generowanie raportu keywords
### 16.4 Generowanie raportu search terms
### 16.5 Generowanie raportu budżetu
### 16.6 Generowanie raportu alertów
### 16.7 Freeform zapytanie
### 16.8 SSE streaming — czy tekst pojawia się na bieżąco
### 16.9 Markdown rendering w odpowiedzi
### 16.10 Agent status (czy Claude CLI dostępny)
### 16.11 Saved reports — lista poprzednich raportów

---

## SEKCJA 17 — Action History

### 17.1 Lista wszystkich wykonanych akcji
### 17.2 Filtrowanie po typie akcji
### 17.3 Filtrowanie po kampanii
### 17.4 Status akcji (completed / failed / reverted)
### 17.5 Revert akcji (rollback)
### 17.6 Dry-run mode

---

## SEKCJA 18 — Ustawienia (Settings)

### 18.1 Lista klientów
### 18.2 Dodawanie klienta
### 18.3 Edycja klienta
### 18.4 Usuwanie klienta
### 18.5 Hard reset danych klienta (z potwierdzeniem przez wpisanie nazwy)
### 18.6 Demo write lock — czy demo klienta jest chroniony

---

## SEKCJA 19 — Multi-Account (jeśli wdrożone)

### 19.1 Przełączanie między klientami
### 19.2 Czy dane się odświeżają przy zmianie klienta
### 19.3 Czy GlobalFilterBar resetuje się przy zmianie klienta

---

## SEKCJA 20 — Bezpieczeństwo akcji

### 20.1 Confirmation modal przy każdej nieodwracalnej akcji
### 20.2 Rollback window — czy można cofnąć akcję
### 20.3 DEMO write lock — czy blokuje akcje na demo koncie
### 20.4 Dry-run mode — czy pokazuje co by zrobiło bez wykonania

---

## SEKCJA 21 — Edge Cases & Error Handling

### 21.1 Brak danych (nowy klient bez sync) — co widać
### 21.2 Błąd API Google Ads — komunikat błędu
### 21.3 Timeout sync — co się dzieje
### 21.4 Pusta lista rekomendacji — empty state
### 21.5 Filtr dający 0 wyników — empty state
### 21.6 Bardzo długie nazwy kampanii — czy UI się nie psuje
### 21.7 Polskie znaki diakrytyczne — czy wyświetlają się poprawnie (ą ę ó ś ź ż ć ń ł)

---

## PODSUMOWANIE TESTOWANIA

| Sekcja | Przetestowano | OK | Bugi | Uwagi |
|--------|--------------|-----|------|-------|
| 1. Onboarding | | | | |
| 2. Sync | | | | |
| 3. Dashboard | | | | |
| ... | | | | |

**Łączna liczba znalezionych bugów:** ___
**Krytyczne:** ___
**Do poprawy:** ___
**Uwagi ogólne:** ___
```

---

## Wymagania jakości dla wygenerowanego dokumentu

1. **Każda funkcjonalność = osobny punkt testowy** z polem "Wynik: ___________"
2. **Dla każdej reguły recommendations** — napisz konkretny warunek wyzwolenia (skopiuj z kodu) żeby tester wiedział kiedy reguła powinna się pojawić
3. **Dla każdego endpointu backend** — sprawdź czy ma odpowiadający UI w frontend; jeśli nie — zaznacz "(backend only, brak UI)"
4. **Polskie opisy** — cały dokument po polsku
5. **Nie pomijaj NIC** — nawet małe przyciski, badge'e, tooltips zasługują na osobny punkt jeśli są istotne dla UX

## Po wygenerowaniu

Zapisz plik jako `MANUAL_TESTING_GUIDE.md` w root repo i zrób commit:
```
docs: add manual testing guide - complete feature list for QA
```
