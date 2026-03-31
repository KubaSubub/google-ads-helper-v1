# Google Ads Helper — Pełny Audyt Wizualny Aplikacji

> Data: 2026-03-28
> Metoda: Playwright screenshoty 15 zakładek na żywym backendzie + seed data
> Klient testowy: Demo Meble Sp. z o.o. (client_id=1)
> Playwright: 15/15 passed, 0 JS errors, 0 crashy

---

## Podsumowanie

| Metryka | Wartość |
|---------|--------|
| Zakładki przetestowane | 15/15 |
| Zakładki z danymi | 14/15 |
| Zakładki z pustym stanem | 1 (Raporty — "Brak zapisanych raportów", poprawne) |
| JS errors | 0 |
| Crashe | 0 |
| Design system compliance | 15/15 |
| Polskie labele | 15/15 |

---

## Wyniki per zakładka

### 1. Pulpit (Dashboard) ✅ OK
- **KPI cards:** 8 kart (Kliknięcia, Koszt, Konwersje, ROAS, Wyświetlenia, CTR, CPA, Wasted Spend)
- **Health Score:** 55/100 z listą problemów (żółty gauge — realistyczne)
- **Quality Score:** 6.7/10, 4 słowa z niskim QS
- **Dane:** Pełne — 20 553 kliknięć, 41 431 zł, 899 konwersji, ROAS 3.68x
- **Delty:** Widoczne (↘ 16.8%, ↘ 20.0% etc.) — poprawne
- **Filtry:** Typ kampanii + Status + Szukaj + date picker (30 dni)
- **Problemy:** Brak

### 2. Poranny Przegląd (Daily Audit) ✅ OK
- **Nagłówek:** "Ostatnie 3 dni · 7 kampanii · 28 słów kluczowych"
- **Alerty:** 6 alertów wymaga uwagi (czerwony banner) — 3 odrzucone reklamy + budżet
- **KPI:** Wydatki 0 zł, Kliknięcia 0, Konwersje 0 (↘ 100% vs poprz.) — to dane z "ostatnich 3 dni" z seeda, poprawne
- **Rekomendacje:** 54 oczekujących, podgrupowane (Obniż stawkę 7 HIGH, QS Alert 4 HIGH)
- **Szybkie skrypty:** Dropdown z zaawansowanymi akcjami
- **Problemy:** KPI 0 zł za 3 dni mogą mylić — seed data generuje dane historyczne, nie "dzisiejsze"

### 3. Kampanie ✅ OK
- **Lista:** 8 kampanii w sidebar z metrykami (koszt, konwersje, ROAS)
- **Detail:** Branded Search wybrany — KPI cards (Kliknięcia 2176, Koszt 4146 zł, Konwersje 114, ROAS 4.75x)
- **Rola kampanii:** Auto: Brand, Protection HIGH, Confidence 85%
- **Sortowanie:** Dropdown (Koszt, domyślne) + ikony sortowania
- **Linki:** "Słowa kluczowe" + "Wyszukiwane frazy" per kampania
- **Problemy:** Brak

### 4. Słowa kluczowe (Keywords) ✅ OK
- **Tabela:** 28 słów, kolumny: Słowo, Kampania, Dopasowanie (PHRASE/EXACT/BROAD badges), Kliknięcia, Wyświetlenia, Koszt, Konwersje, CTR, Avg CPC
- **Taby:** Słowa kluczowe, Wykluczenia, Listy, Ekspansja, Audyt QS
- **Filtry:** Wszystkie/EXACT/PHRASE/BROAD pills + "Pokaż usunięte" checkbox
- **Eksport:** CSV + XLSX przyciski
- **Statusy:** Badges "Mało zapytań", "Rzadko", "Bid za niski" — kolorowe i czytelne
- **Problemy:** Brak

### 5. Wyszukiwane frazy (Search Terms) ✅ OK
- **Widoki:** Segmenty (domyślny), Lista, Trendy, Warianty
- **Segmenty:** Top Performerzy (23), Strata (0), Nieistotne (0), Inne (27) — karty z kolorami
- **Tabela:** Segment badge, Fraza, Kampania, Kliknięcia, Koszt, Konwersje, CVR, Powód
- **Eksport:** CSV + XLSX
- **Checkboxes:** Bulk selection dla masowych akcji
- **Dane:** 51 wyszukiwań — realistyczne
- **Problemy:** Brak

### 6. Rekomendacje ✅ OK
- **Nagłówek:** 52 aktywne rekomendacje
- **Summary pills:** Łącznie 52, Do wykonania 1, Pilne 13, Akcje 30, Zablokowane 0
- **Filtry:** Priority (ALL/HIGH/MEDIUM/LOW), Source (Playbook/Analytics/Google Ads/Hybrid), Type (ALL/EXECUTABLE/ALERTS), Category (Wszystkie/Rekomendacje/Alerty)
- **Karty rekomendacji:** Severity badge (MEDIUM), typ akcji ("Wstrzymaj reklamę"), entity name, kampania, confidence/risk, spend/clicks/impressions metrics
- **Przycisk "Zaznacz wykonalne":** Bulk action
- **Eksport + Odśwież**
- **Problemy:** Brak

### 7. Historia zmian (Action History) ✅ OK
- **Taby:** Nasze akcje, Zewnętrzne, Wszystko, Wpływ zmian, Wpływ strategii licytacji
- **Quick stats:** Dzisiaj 0, Łącznie 5, Cofnięte 1, Zablokowane 0
- **Filtry:** Presety dat (Dzisiaj/7 dni/30 dni), date pickery, dropdown "Typ akcji"
- **Tabela:** Data, Akcja (polskie etykiety!), Encja (klikalna — niebieski link!), Kampania, Status (kolorowy — SUCCESS zielony, REVERTED szary)
- **Eksport:** CSV + XLSX przyciski w nagłówku
- **Problemy:** Brak — paginacja i eksport dodane w tym sprincie działają

### 8. Monitoring (Alerts) ✅ OK
- **Taby:** Alerty / Anomalie (z-score)
- **Filtry:** Nierozwiązane (4) / Rozwiązane
- **Karty alertów:** Severity badge (WYSOKI czerwony, ŚREDNI żółty), typ (SPEND_SPIKE, CONVERSION_DROP, CTR_DROP), opis po polsku, przycisk "Rozwiąż"
- **Dane:** 4 nierozwiązane alerty — realistyczne opisy
- **Problemy:** Brak

### 9. Asystent AI (Agent) ✅ OK
- **Status:** "Claude dostępny" (zielony badge)
- **Chat:** Pole input "Zadaj pytanie o kampanie..."
- **Quick reports:** 6 przycisków (Raport tygodniowy, Analiza kampanii, Analiza budżetów, Wyszukiwane frazy, Słowa kluczowe, Alerty i anomalie)
- **Empty state:** "Wybierz typ raportu lub zadaj pytanie o swoje kampanie"
- **Problemy:** Brak — poprawny empty state

### 10. Raporty ✅ OK (empty state)
- **Status:** "Claude dostępny" (zielony badge)
- **Typy:** Miesięczny, Tygodniowy, Zdrowie konta — taby
- **Okres:** Dropdown "Marzec 2026" + przycisk "Generuj"
- **Zapisane raporty:** "Brak zapisanych raportów" — poprawny empty state
- **Problemy:** Brak — to normalne przed pierwszym wygenerowaniem raportu

### 11. Optymalizacja SEARCH ✅ OK
- **Nagłówek:** "Optymalizacja SEARCH — Analiza 30 dni — 25 narzędzi optymalizacji kampanii"
- **Zmarnowany budżet:** 287 zł / 41431 zł = 0.7% waste — WIDOCZNE i CZYTELNE
  - Słowa kluczowe (3): demo meble sklep 137 zł, demo meble 38 zł, meble demo 33 zł
  - Reklamy (1): Demo Meble – Darmowa Dostawa 79 zł
- **Harmonogram (dni tygodnia):** SEARCH, Pn-Nd widoczne, Sb/Nd czerwone
- **Dane załadowane poprawnie** — to kluczowa zakładka i renderuje się bez problemów
- **Problemy:** Brak wizualnych — nowe sekcje (Auction Insights, Shopping, etc.) wymagają scrolla

### 12. Prognozowanie (Forecast) ✅ OK
- **Selektory:** 7d/14d/30d, kampania (Branded Search), metryka (Koszt/Kliknięcia/Konwersje/CTR)
- **KPI:** Trend +16.5%, Prognoza 173.15, Pewność R² 0.00 (LOW badge), Slope 0.23
- **Wykres:** Linia historyczna (90 dni) + zielone kropki prognozy (7 dni) — czytelne
- **Problemy:** R²=0.00 z badge "LOW" — poprawne dla seed data z szumem

### 13. Klastry Semantyczne (Semantic) ✅ OK
- **Nagłówek:** "24 wyrażeń w 9 klastrach tematycznych"
- **Filtry kosztów:** Wszystkie / >10 zł / >50 zł / >100 zł
- **Szukaj w klastrach:** Input field
- **Klastry:** Karty z ikoną, nazwą, liczbą wyrażeń, wyświetleniami, kosztem i konwersjami
  - "łóżko drewniane do sypialni" 5 wyrażeń, 3400 zł, 61.3 conv
  - "narożnik rozkładany z funkcją spania" 4 wyrażeń, 2115 zł
- **Rozwijalne:** Chevron per klaster
- **Problemy:** Brak

### 14. Audyt Quality Score ✅ OK
- **KPI cards:** Średni QS 6.7/10, Niski QS(<5) 4 wymaga uwagi, Wysoki QS(8-10) 11, Wydatki na niski QS 17.3%, IS utracony 17.1%
- **Filtry:** Wszystkie kampanie, Wszystkie typy, Wszystkie problemy, QS < 5 dropdown
- **Widoki:** Wszystkie / Niski QS / Wysoki QS / Grupuj — pill buttons
- **Wykres:** Rozkład QS (bar chart 1-10, kolorowany: czerwony 1-3, żółty 4-6, zielony 7-10)
- **Główne problemy:** Oczekiwany CTR 15, Trafność reklamy 7, Strona docelowa 4
- **Eksport:** CSV + XLSX + Odśwież
- **Problemy:** Brak — jedno z najlepszych UI w aplikacji

### 15. Ustawienia (Settings) ✅ OK
- **Informacje ogólne:** Nazwa klienta, Branża, Strona WWW, Google Customer ID — wszystko wypełnione
- **Strategia i konkurencja:** Target audience, USP, Konkurencja (pills z "×")
- **Notatki:** Edytowalne pole tekstowe
- **Przycisk "Zapisz"**
- **Problemy:** Brak

---

## Design System Compliance

| Element | Status | Uwagi |
|---------|--------|-------|
| Ciemne tło (#0D0F14) | ✅ | Wszystkie strony |
| Sidebar (#111318) | ✅ | Spójny |
| Karty v2-card | ✅ | rgba(255,255,255,0.03) bg, 0.07 border |
| Font Syne (nagłówki) | ✅ | Pulpit, KPI, tytuły stron |
| Font DM Sans (body) | ✅ | Tabele, opisy |
| Accent blue #4F8EF7 | ✅ | Linki, aktywne taby, ikony |
| Success green #4ADE80 | ✅ | Konwersje, SUCCESS status |
| Warning yellow #FBBF24 | ✅ | MEDIUM badge, cofnięte |
| Danger red #F87171 | ✅ | Alertyy HIGH, brak konwersji |
| Pill buttons (borderRadius 999) | ✅ | Taby, filtry, segmenty |
| Table headers (uppercase 10px) | ✅ | Spójne we wszystkich tabelach |

---

## Problemy znalezione

### Krytyczne: 0

### Wizualne (niskie): 2
1. **Daily Audit KPI "0 zł"** — seed data nie generuje danych "na dziś", więc poranny przegląd pokazuje 0 zł / 0 kliknięć / 0 konwersji z ↘ 100%. To poprawne zachowanie ale może mylić usera — warto dodać info "Dane z dzisiaj mogą być niekompletne".
2. **Optymalizacja — nazwa "SEARCH"** — strona nazywa się "Optymalizacja SEARCH" ale zawiera sekcje Display/Video/Shopping/PMax. Zmiana nazwy na "Optymalizacja" jest w backlogu (ads-verify-search-optimization Sprint 1).

### Brakujące dane (oczekiwane): 3
Nowe sekcje w Optymalizacji (Auction Insights, Shopping Groups, Placements, Topics, Bid Modifiers, Google Recommendations) — wymagają sync z nowymi fazami. Domyślnie pokazują "Brak danych..." co jest poprawne, ale user musi wiedzieć że musi odpalić sync.

---

## Porównanie z poprzednim audytem

Aplikacja renderuje się **poprawnie na wszystkich 15 zakładkach** z załadowanymi danymi. Żaden screenshot nie pokazuje białego ekranu, wiecznego loadera, ani JS error.

Zmiany widoczne od ostatniego audytu:
- ✅ Action History: CSV/XLSX przyciski widoczne w nagłówku
- ✅ Action History: Quick stats banner (Dzisiaj/Łącznie/Cofnięte/Zablokowane)
- ✅ Action History: Polskie etykiety akcji, kolorowe statusy z tooltipami
- ✅ Action History: Deep links na encjach (niebieskie klikalne linki)
- ✅ Optymalizacja: Sekcja "Zmarnowany budżet" z danymi (287 zł waste)
- ✅ Optymalizacja: Harmonogram z dniami tygodnia (Sb/Nd czerwone)

---

## Verdict

**Aplikacja jest w pełni funkcjonalna wizualnie.** 15/15 zakładek renderuje się bez crashy, z załadowanymi danymi, w spójnym design systemie v2, z polskimi labelami. Jedyne "problemy" to nazewnictwo ("SEARCH" zamiast ogólnej "Optymalizacji") i brak danych w nowych sekcjach wymagających dodatkowego sync — oba w backlogu.

**Ocena wizualna: 9/10**
