# Ocena eksperta Google Ads — MCC Overview
> Data: 2026-04-02 | Średnia ocena: 7.3/10 | Werdykt: ZMODYFIKOWAĆ

## TL;DR

MCC Overview to wartościowy widok którego brakuje w standardowym Google Ads MCC. Agregacja health score, pacing i zewnętrznych zmian per konto w jednej tabeli realnie oszczędza czas rano. Jednak brak konwersji/CPA/ROAS jest krytyczny — specjalista nie podejmie decyzji o priorytetyzacji kont bez metryk wynikowych.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 9/10 | Specjalista z 8+ kontami POTRZEBUJE szybkiego przeglądu zanim wchodzi w detale. Playbook mówi 15-30 min/konto na daily checks — ten widok skraca triaging do 2 min. |
| Kompletność | 5/10 | Brakuje metryk wynikowych (konwersje, CPA, ROAS). Brak sortowania. Brak quick actions. NKL read-only. Tabela jest informacyjna ale nie actionable. |
| Wartość dodana vs Google Ads UI | 8/10 | Google Ads MCC ma ubogi widok listy kont — brak health score, brak pacing per konto, brak wykrywania zewnętrznych zmian. Te 3 rzeczy to realny game-changer. |
| Priorytet MVP | 8/10 | Landing page aplikacji = pierwsze co widzi user. Musi być dobry. Przy wielu kontach to "must have". |
| **ŚREDNIA** | **7.5/10** | |

## Co robi dobrze

- **Health score per konto w jednym widoku** — w Google Ads MCC nie istnieje. Specjalista musi wchodzić w każde konto i sam oceniać stan. Tu ma kółko 0-100 na pierwszy rzut oka.
- **Pacing zagregowany per klient** — Google Ads pokazuje pacing per kampania. Agregacja do poziomu konta to wartościowy insight ("konto X jako całość underspenduje").
- **Wykrywanie zewnętrznych zmian** — kolumna "Zmiany" z wyróżnieniem "zewn." to coś czego GAds nie oferuje bez ręcznego filtrowania Change History. Dla agencji zarządzającej kontami klientów to krytyczne.
- **Czysty sidebar na MCC** — ukrycie selektora klienta i kampanii na tej stronie to prawidłowa decyzja UX. MCC to inny poziom nawigacji.
- **Lazy-load NKL** — ładowanie danych NKL dopiero po rozwinięciu sekcji — dobra optymalizacja.

## Co brakuje (krytyczne)

### K1: Konwersje i CPA/ROAS per konto
**Specjalista priorytetyzuje konta po wynikach, nie po wydatkach.** Konto z $60k spend i 0 konwersji to pożar. Konto z $1k spend i ROAS 800% to złoto. Bez tych metryk tabela jest jak pulpit samochodu bez prędkościomierza.

- **Dane dostępne:** MetricDaily ma `conversions`, `conversion_value_micros` — wystarczy je zagregować per klient analogicznie do `_sum_spend()`.
- **Kolumny do dodania:** `Konwersje 30d`, `CPA` (spend/conversions), `ROAS` (conv_value/spend)
- **Playbook ref:** "Sprawdzenie wydatku" + "Performance Analysis" — ZAWSZE obok spend jest conversions i CPA/ROAS
- **Nakład:** S — dodanie 3 metryk do `_build_account_data()` + 3 kolumny w tabeli

### K2: Sortowanie tabeli
Tabela 4 kont jest ok bez sortowania. Tabela 15 kont bez sortowania to chaos. Specjalista chce posortować: po spend desc (gdzie idą pieniądze), po health asc (co wymaga uwagi), po rekomendacjach desc (co actionable).

- **Nakład:** S — state `sortBy`/`sortDir` + `accounts.sort()` w render

### K3: Tooltip na health score
Kółko z "68" nic nie mówi. Specjalista potrzebuje wiedzieć: "Performance: 75%, Quality: 45%, Efficiency: 82%". Kliknięcie lub hover powinien pokazać breakdown 6 filarów.

- **Dane dostępne:** `get_health_score()` zwraca pełny breakdown — wystarczy go przekazać do frontendu zamiast samego `score`
- **Nakład:** S — zmiana w `_get_health_score()` + tooltip/popover w UI

## Co brakuje (nice to have)

### N1: Sparkline wydatków
Mini wykres trendu 30d w kolumnie spend. Daje kontekst: spend rośnie czy maleje? Strzałka z % jest ok ale sparkline jest lepszy.

### N2: Link "Otwórz w Google Ads"
Button per wiersz → `ads.google.com/aw/overview?ocid={google_customer_id}`. Quick jump do natywnego UI.

### N3: Alerty per konto
Ikona alertu przy koncie z aktywnymi anomaliami/alertami. Dane z tabeli `alerts` — COUNT WHERE client_id = X AND status = 'unresolved'.

### N4: Filtrowanie/wyszukiwanie kont
Przy 20+ kontach potrzeba wyszukiwarki i filtrów (branża, status, wielkość). Przy <10 kont to overkill.

### N5: NKL akcje z poziomu MCC
Tworzenie/edycja list NKL, kopiowanie listy z jednego konta na inne. "Shared negative lists" cross-account to realny use case dla agencji.

### N6: Kolumna "Impression Share"
Zagregowany search IS per konto — mówi czy konto w ogóle wykorzystuje potencjał.

## Co usunąć/zmienić

- **Pacing progi** — 80%/115% jest zbyt agresywne. W praktyce pacing 85% to norma (weekendy, godziny nocne). Sugeruję **75%/120%** żeby zmniejszyć false positive "Niedowydanie".
- **KPI "Rek. Google"** — w karcie KPI na górze widać "9" ale nie wiadomo ile per konto jest krytycznych. Rozważ podział na "high priority" vs "low priority".

## Porównanie z Google Ads UI

| Funkcja | Google Ads MCC | Nasza apka | Werdykt |
|---------|---------------|------------|---------|
| Lista kont | Tabela z spend, clicks, conv | Tabela ze spend, pacing, health, changes | **INNE** — komplementarne metryki |
| Health score per konto | BRAK | ✅ Kółko 0-100 | **LEPSZE** |
| Pacing per konto | BRAK (per kampania) | ✅ Zagregowany status | **LEPSZE** |
| Zewnętrzne zmiany | Change History per konto z ręcznym filtrem | ✅ Zliczone automatycznie | **LEPSZE** |
| Konwersje per konto | ✅ Kolumna w tabeli | ❌ BRAK | **GORSZE** |
| CPA/ROAS per konto | ✅ Kolumna w tabeli | ❌ BRAK | **GORSZE** |
| Sortowanie | ✅ Po każdej kolumnie | ❌ BRAK | **GORSZE** |
| NKL cross-account | ✅ Shared Sets manager | ✅ Read-only podgląd | **GORSZE** (brak edycji) |
| Alerty/powiadomienia | ✅ Per konto | ❌ BRAK | **GORSZE** |
| Quick actions | ✅ Menu kontekstowe | ❌ BRAK (tylko kliknięcie w wiersz) | **GORSZE** |

**Bilans: 3 LEPSZE, 1 INNE, 5 GORSZE** — ale te 3 LEPSZE (health, pacing, external changes) to unikalne wartości których Google Ads nie oferuje.

## Nawigacja i kontekst

- **Skąd user trafia:** Landing page — otwiera się jako / → redirect do /mcc-overview
- **Dokąd może przejść:** Kliknięcie wiersza → /dashboard z breadcrumb "← Wszystkie konta"
- **Brakujące połączenia:**
  - Z health score → do strony Health Score danego konta (deep dive)
  - Z kolumny "Rek. Google" → do strony Rekomendacje danego konta
  - Z kolumny "Zmiany" → do Historia zmian danego konta
  - Z NKL → do strony Keywords/NKL danego konta

## Odpowiedzi na pytania @ads-user

1. **Konwersje/CPA/ROAS** — to KRYTYCZNE. Must-have w następnym sprincie. Dane istnieją w MetricDaily.
2. **Health score tooltip** — tak, hover powinien pokazywać 6 filarów. Backend już zwraca breakdown.
3. **Pacing progi** — zgadzam się, 80% to za agresywne. 75%/120% będzie lepsze.
4. **NKL edycja z MCC** — nice to have v1.1. Na MVP read-only jest ok.
5. **Sortowanie** — trivial do dodania, powinno być w następnym sprincie.
6. **Breakdown zmian** — nice to have. Na start wystarczy total + external.

## Rekomendacja końcowa

**ZMODYFIKOWAĆ** — widok ma silne fundamenty (health, pacing, external changes) które dają realną wartość. Ale brak konwersji/CPA/ROAS to showstopper który trzeba naprawić w następnym sprincie. Po dodaniu metryk wynikowych + sortowania, ten widok stanie się obowiązkowym porannym dashboardem każdego specjalisty Google Ads zarządzającego wieloma kontami.

**Priorytet implementacji:**
1. **SPRINT 1 (must):** Konwersje + CPA + ROAS w tabeli, sortowanie, health tooltip
2. **SPRINT 2 (should):** Deep-link z kolumn do stron per-konto, alerty per konto, sparkline
3. **SPRINT 3 (could):** NKL edycja, kopiowanie list cross-account, filtrowanie kont
