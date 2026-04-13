# Ocena eksperta Google Ads — Raporty
> Data: 2026-03-27 | Srednia ocena: 6.5/10 | Werdykt: ZMODYFIKOWAC

## TL;DR

Zakladka Raporty to potencjalnie najsilniejsza funkcja aplikacji — automatyczne raporty z AI narracja to cos, czego Google Ads UI nie oferuje. Jednakze **dwa bugi blokuja podstawowe uzycie** (ladowanie zapisanych raportow + brak przycisku drukuj), brakuje selektora okresu, a brak seed data sprawia ze nowy uzytkownik widzi pusty, niezachecajacy ekran. Koncept 9/10, wykonanie 4/10.

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebnosc | 8/10 | Generowanie raportow to kluczowy task specjalisty — playbook wymienia go w sekcji miesiecznej (3-5h/konto). Automatyzacja narracji AI to realny game-changer |
| Kompletnosc | 5/10 | Generowanie dziala (streaming SSE), ale ladowanie zapisanych raportow jest zlamane (API bug). Brak selektora miesiaca, brak eksportu PDF, brak seed data |
| Wartosc dodana vs Google Ads UI | 8/10 | Google Ads nie generuje pisemnych raportow z rekomendacjami. Porownanie m/m + change impact + budget pacing + AI narracja — to unikalna kombinacja |
| Priorytet MVP | 5/10 | Raporty sa wazne, ale nie codzienne. Specjalista generuje je raz w tygodniu/miesiacu. Dashboard/Keywords/Search Terms sa wazniejsze na co dzien |
| **SREDNIA** | **6.5/10** | |

## Co robi dobrze

1. **3 typy raportow** — miesieczny, tygodniowy, health check. Kazdy ma wlasny zestaw sekcji danych (`REPORT_DATA_MAP` w `agent_service.py:82-98`). Miesiezny: 8 sekcji (month_comparison, campaigns_detail, change_history, change_impact, budget_pacing, wasted_spend, alerts, health). Health: 6 sekcji z audytem konwersji, QS i struktury konta. To dobrze pokrywa playbook sekcje miesieczna i tygodniowa

2. **SSE streaming z progress barem** — dane strukturalne pojawiaja sie w trakcie generowania (65% progressu), potem AI narracja streamuje sie w realtime (65-95%). User nie czeka na czarny ekran — widzi postep i dane zanim AI skonczy

3. **Change Impact Analysis** (`agent_service.py:731-826`) — porownuje metryki 7 dni przed i 7 dni po zmianie budzetu/biddingu/statusu. To odpowiada wprost na playbook sekcje "Competitor Analysis" i "Performance Analysis" — specjalista widzi wplyw swoich decyzji

4. **Prompty AI sa dobrze zaprojektowane** — MONTHLY_PROMPT (`agent_service.py:141-161`) wyrazinie zabrania duplikowania metryk miedzy sekcjami ("Kazda metryka pojawia sie DOKLADNIE raz"). Prompty sa w jezyku polskim, co pasuje do target usera

5. **Token usage transparency** — user widzi koszt generowania (input/output/cache tokens + $ cost + czas). To buduje zaufanie do narzedzia AI

6. **Budget pacing per kampania** — progress bary z kolorowym statusem (on_track/underspend/overspend). W Google Ads nie ma takiego zagregowanego widoku realizacji budzetow

## Co brakuje (krytyczne)

### BUG 1: `getReport()` nie przekazuje `client_id` — SHOWSTOPPER
- **Plik:** `frontend/src/api.js:270-271`
- **Problem:** `getReport(reportId)` wywoluje `GET /reports/{report_id}` BEZ query param `client_id`. Backend wymaga go obligatoryjnie (`Query(...)` w `reports.py:274`)
- **Efekt:** Kazde ladowanie zapisanego raportu zwraca 422 Validation Error. Auto-load po wejsciu na strone tez jest zlamany
- **Fix:** Zmiana `getReport` na `getReport(reportId, clientId)` i dodanie `params: { client_id: clientId }` do zapytania
- **Priorytet:** P0 — bez tego zakladka jest niefunkcjonalna

### BUG 2: Przycisk "PDF / Drukuj" uzywa niezdefiniowanej zmiennej
- **Plik:** `frontend/src/pages/Reports.jsx:627`
- **Problem:** Warunek `{selectedReport && !generating && (` uzywa `selectedReport` ktora nie istnieje. Komponent definiuje `activeReport` (linia 387)
- **Efekt:** Przycisk PDF nigdy sie nie renderuje, nawet gdy raport jest zaladowany
- **Fix:** Zmiana `selectedReport` na `activeReport`
- **Priorytet:** P0 — eksport PDF to kluczowa funkcja raportow

### BRAK 3: Selektor okresu (miesiaca/tygodnia)
- **Problem:** Raport miesieczny generuje sie ZAWSZE za biezacy miesiac (`reports.py:77-84`). Jest logika na `req.year`/`req.month` w backendzie, ale frontend nie przekazuje tych parametrow — `handleGenerate()` wysyla tylko `{ report_type }` (`Reports.jsx:472`)
- **Playbook ref:** Sekcja 1.1 "Miesieczne" — specjalista potrzebuje raportu za DOWOLNY miesiac, nie tylko biezacy
- **Priorytet:** P1 — bez tego nie mozna generowac raportow historycznych

### BRAK 4: Seed data raportow
- **Problem:** Tabela `reports` nie jest seedowana. Nowy uzytkownik widzi pusty ekran z "Brak zapisanych raportow". Nie wie co raport zawiera, jak wyglada, ile trwa generowanie
- **Priorytet:** P1 — pierwszy kontakt z zakladka jest niezachecajacy

## Co brakuje (nice to have)

1. **Scheduler raportow** — automatyczne generowanie co tydzien/miesiac (playbook: "3-5h/konto" na miesieczny przeglad)
2. **White-label PDF** — eksport z logiem agencji, formatowanie drukowania, header/footer
3. **Porownanie dwoch raportow obok siebie** — np. styczen vs luty
4. **Filtr per kampania / typ kampanii** — raport per klient pokrywa wszystko; czasem potrzeba per kampania
5. **Historyczne raporty per klient** — wykres trendu sredniej oceny health score z miesiacna na miesiac
6. **Email delivery** — wyslij raport na podany adres email
7. **Custom sekcje** — user wybiera ktore sekcje chce w raporcie (bez change history, tylko KPI + AI)

## Co usunac/zmienic

1. **Nazwa zakladki** — "Raporty" obok "Raport AI" w sekcji AI sidebara to mylace. Propozycje:
   - Zmiana "Raport AI" (agent) na "Asystent AI" lub "Chat AI"
   - LUB polaczenie obu zakladek w jedna z dwoma trybami (chat + raporty)
2. **Badge "Claude dostepny"** — dla specjalisty GAds to techniczna babelka. Zamienilbym na bardziej user-friendly komunikat lub ukriwalbym jesli available
3. **Lock per app zamiast per client** (`_reports_lock` w `reports.py:22`) — jeden globalny lock blokuje generowanie dla wszystkich klientow. Przy 8 kontach to problem. Powinien byc lock per client_id
4. **Label "PLN" przy `cost_usd`** — frontend wyswietla "PLN" (`Reports.jsx:96`) ale zmienna to `cost_usd`. Nalezy ujednolicic naming

## Porownanie z Google Ads UI

| Funkcja | Google Ads | Nasza apka | Werdykt |
|---------|-----------|------------|---------|
| Raport miesieczny | Recznie: eksportuj dane, pisz w Wordzie/Sheets | Auto-generowany z AI narracja + dane strukturalne | **LEPSZE** |
| Porownanie m/m | Tak (zmiana okresu w date picker) | Tak (KPI karty z deltami) | IDENTYCZNE |
| Budget pacing | Brak zagregowanego widoku | Progress bary per kampania z % | **LEPSZE** |
| Change impact | Change History bez korelacji z metrykami | Before/after analiza 7d per zmiana | **LEPSZE** |
| Eksport PDF | Reports > Export (CSV/PDF gotowe) | Zlamany przycisk (bug) | **GORSZE** |
| Selektor okresu | Dowolny zakres dat | Tylko biezacy miesiac | **GORSZE** |
| Scheduled reports | Tak (Reports > Schedule, email delivery) | Brak | **GORSZE** |
| Custom raporty | Reports Builder z drag & drop | Brak (3 predefiniowane typy) | **GORSZE** |
| AI interpretacja | Performance Max Insights (ograniczone) | Pelna narracja z rekomendacjami | **LEPSZE** |

## Nawigacja i kontekst

- **Skad user trafia:** Sidebar > AI > Raporty
- **Dokad powinien moc przejsc:**
  - Z sekcji "Kampanie" raportu → zakladka Campaigns ze szczegolami kampanii
  - Z sekcji "Rekomendacje" → zakladka Recommendations z apply actions
  - Z sekcji "Budget pacing" → Dashboard z budzetem
  - Z sekcji "Change Impact" → Action History z pelna historia zmian
- **Brakujace polaczenia:**
  - Brak deep-linkow z danych strukturalnych do szczegolowych zakladek
  - Brak linku "Wygeneruj raport" z Dashboard (naturalny flow: dashboard → chetny na wiecej detali → raport)
  - Brak integracji z Monitoring/Alerts — alert moglby sugerowac "wygeneruj health check"

## Rekomendacja koncowa

**ZMODYFIKOWAC** — zakladka ma realny potencjal i unikalna wartosc (auto-raporty z AI narracja), ale wymaga pilnych fixow:

1. **P0:** Naprawic `getReport()` + przycisk PDF (2 proste fixy, kazdy 1 linia kodu)
2. **P1:** Dodac selektor miesiaca/tygodnia (frontend date picker + przekazanie year/month do backendu)
3. **P1:** Dodac 1-2 przykladowe raporty w seedzie zeby nowy user widzial wartosc zakladki
4. **P2:** Rozroznic nazwy "Raport AI" vs "Raporty" w sidebar
5. **P2:** Lock per client_id zamiast per app
