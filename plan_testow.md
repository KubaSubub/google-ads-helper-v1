# PLAN TESTÓW — Google Ads Helper
## Kompletna procedura testowania (Faza 1 → 2 → 3)

**Data:** 2025-02-17
**Środowisko:** Zbudowany .exe (PyWebView + PyInstaller)
**Konto testowe:** MCC z kilkoma klientami (prawdziwe dane Google Ads)
**Źródło kryteriów:** PRD_Core.md §6.1, Implementation_Blueprint.md §6, Blueprint_Patch_v2_1.md §Integration Checklist

---

# ⚠️ PRZED ROZPOCZĘCIEM TESTÓW

### Przygotowanie

1. **Zamknij** wszystkie instancje aplikacji (jeśli uruchomione)
2. **Sprawdź** czy .exe jest aktualny (po ostatnim buildzie)
3. **Przygotuj** dane Google Ads OAuth:
   - `GOOGLE_CLIENT_ID` (z Google Cloud Console)
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_DEVELOPER_TOKEN`
   - MCC Customer ID
4. **Otwórz** przeglądarkę (będzie potrzebna do OAuth callback)
5. **Otwórz** Google Ads UI w drugiej karcie (do weryfikacji zmian)

### Narzędzia do logowania wyników

Dla każdego testu: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL + notatka co nie działa

---

# ═══════════════════════════════════════════════════════
# FAZA 1: SMOKE TEST (15-20 minut)
# Cel: "Czy apka w ogóle działa?"
# Przerywa dalsze testy jeśli cokolwiek tu FAIL
# ═══════════════════════════════════════════════════════

## S-01: Uruchomienie .exe

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 1 | Double-click na `Google Ads Helper.exe` | Okno aplikacji się otwiera (natywne PyWebView, nie przeglądarka) | ☐ |
| 2 | Czas ładowania | Okno pojawia się w < 10 sekund | ☐ |
| 3 | Brak console window | Nie pojawia się czarne okno CMD | ☐ |
| 4 | UI się renderuje | Widać sidebar + main content area (dark mode) | ☐ |
| 5 | Brak białego ekranu | Strona nie jest pusta / nie "Loading..." w nieskończoność | ☐ |

**Jeśli S-01 FAIL:** Sprawdź logi w `data/logs/` obok .exe. Prawdopodobnie problem z PyWebView lub budowaniem frontend/dist.

---

## S-02: Podstawowa nawigacja

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 6 | Kliknij każdy link w sidebar | Każda strona się ładuje bez błędów (Pulpit, Klienci, Kampanie, Słowa kluczowe, Wyszukiwane frazy, Rekomendacje, Historia akcji, Alerty, Ustawienia) | ☐ |
| 7 | Strony po polsku | Cały UI po polsku (sidebar, nagłówki, przyciski) | ☐ |
| 8 | Dark mode | Ciemne tło (#0F172A), jasny tekst, accent blue (#3B82F6) | ☐ |
| 9 | Responsive | Zmień rozmiar okna — layout się dostosowuje, sidebar nie znika | ☐ |

---

## S-03: OAuth — połączenie z Google Ads

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 10 | Kliknij "Zaloguj" / "Połącz konto" na stronie Settings/Auth | Otwiera się przeglądarka z Google OAuth consent screen | ☐ |
| 11 | Zaloguj się kontem Google (MCC) | Consent screen wyświetla scope "Google Ads" | ☐ |
| 12 | Akceptuj uprawnienia | Redirect do callback → strona "Authentication successful!" | ☐ |
| 13 | Wróć do aplikacji | Status auth zmienił się na "Połączono" / authenticated = true | ☐ |
| 14 | Zamknij i otwórz .exe ponownie | Po restarcie — nadal zalogowany (token w Windows Credential Manager) | ☐ |

**Jeśli S-03 FAIL:** 
- Brak refresh_token → Idź do https://myaccount.google.com/permissions, cofnij dostęp, spróbuj ponownie
- "No developer token" → Sprawdź .env / config

---

## S-04: Pierwszy Sync

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 15 | Wybierz klienta z MCC | Lista klientów się ładuje | ☐ |
| 16 | Kliknij "Synchronizuj" | Spinner/loading indicator się pojawia | ☐ |
| 17 | Sync zakończony | Toast/komunikat "Synchronizacja zakończona" | ☐ |
| 18 | Czas sync | < 5 minut (dla typowego konta: 10 kampanii, 1k keywordów) | ☐ |
| 19 | Dane się pojawiają | Dashboard pokazuje KPI (spend, clicks, conversions ≠ 0) | ☐ |
| 20 | Kampanie widoczne | Strona "Kampanie" pokazuje listę z danymi | ☐ |

**Jeśli S-04 FAIL:**
- "API Error" → Sprawdź czy developer token ma dostęp do tego MCC
- Timeout → Konto za duże lub wolne łącze

---

## DECYZJA PO FAZIE 1

- **Wszystkie S-01 → S-04 PASS** → Przejdź do Fazy 2
- **Jakikolwiek S-01 FAIL** → STOP. Naprawa .exe / PyWebView
- **S-03 FAIL** → STOP. Naprawa OAuth flow
- **S-04 FAIL** → STOP. Naprawa Sync Service

---

# ═══════════════════════════════════════════════════════
# FAZA 2: PEŁNY TEST MANUALNY (60-90 minut)
# Cel: Przetestować KAŻDY feature z PRD
# 7 features × acceptance criteria
# ═══════════════════════════════════════════════════════

## Feature 1: Sync & Data (PRD Feature 1)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 21 | Sync klient #1 | Kampanie, keywords, search terms załadowane | ☐ |
| 22 | Sync klient #2 (inny) | Dane klienta #2 oddzielone od #1 | ☐ |
| 23 | Przełącz klienta w sidebar dropdown | Dane zmieniają się na odpowiednie dla wybranego klienta | ☐ |
| 24 | Last synced timestamp | Sidebar/klient pokazuje "Ostatnia sync: [data/czas]" | ☐ |
| 25 | Sync ponownie (ten sam klient) | Dane zaktualizowane, brak duplikatów | ☐ |
| 26 | Sync z niepoprawnym klientem | Graceful error — toast/komunikat, nie crash | ☐ |

---

## Feature 2: Apply Action + Confirmation Modal (PRD Feature 2)

**Przygotowanie:** Upewnij się że masz przynajmniej 1 rekomendację PENDING.

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 27 | Przejdź do "Rekomendacje" | Lista rekomendacji załadowana (HIGH/MEDIUM badge) | ☐ |
| 28 | Kliknij "Zastosuj" na rekomendacji | Otwiera się ConfirmationModal (NIE wykonuje od razu!) | ☐ |
| 29 | Modal — dry_run preview | Modal pokazuje: typ akcji, obiekt, przed → po, powód | ☐ |
| 30 | Modal — kliknij "Anuluj" | Modal się zamyka, nic się nie dzieje | ☐ |
| 31 | Modal — kliknij "Potwierdź" | Akcja się wykonuje → toast "Akcja wykonana" | ☐ |
| 32 | Rekomendacja znika z listy | Status zmieniony na "applied" — nie widać w pending | ☐ |
| 33 | Sprawdź w Google Ads UI | Zmiana rzeczywiście widoczna (np. keyword paused) | ☐ |

**⚠️ UWAGA:** Test 33 wymaga ostrożności — wykonujesz PRAWDZIWĄ akcję na koncie! Wybierz mało ważny keyword do testu.

---

## Feature 3: Recommendations (PRD Feature 3)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 34 | Filtr: "Wszystkie" | Widać HIGH + MEDIUM rekomendacje | ☐ |
| 35 | Filtr: "HIGH" | Widać tylko HIGH priority | ☐ |
| 36 | Filtr: "MEDIUM" | Widać tylko MEDIUM priority | ☐ |
| 37 | Summary badge | Na górze strony: "X HIGH, Y MEDIUM rekomendacji" | ☐ |
| 38 | Każda rekomendacja ma: | Typ, priority badge, reason, entity name | ☐ |
| 39 | Kliknij "Odrzuć" (Dismiss) | Rekomendacja znika, status → dismissed | ☐ |
| 40 | Odrzucona NIE wraca | Po odświeżeniu — odrzucona nie pojawia się ponownie | ☐ |
| 41 | Ilość rekomendacji | 20+ rekomendacji na klienta z >30 dni danych | ☐ |

---

## Feature 4: Action History & Undo (PRD Feature 4)

**Przygotowanie:** Musisz mieć przynajmniej 1 wykonaną akcję (z Feature 2 testu).

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 42 | Przejdź do "Historia akcji" | Tabela z akcjami — data, typ, entity, status | ☐ |
| 43 | Najnowsza akcja na górze | Sortowanie: newest first | ☐ |
| 44 | Akcja z Feature 2 widoczna | Widzisz akcję którą właśnie wykonałeś | ☐ |
| 45 | Status badge | SUCCESS (zielony), FAILED (czerwony), REVERTED (szary) | ☐ |
| 46 | Przycisk "Cofnij" widoczny | Widoczny TYLKO dla: SUCCESS + < 24h + nie ADD_NEGATIVE | ☐ |
| 47 | Kliknij "Cofnij" | ConfirmationModal: "Cofnij akcję?" | ☐ |
| 48 | Potwierdź cofnięcie | Akcja cofnięta → toast sukcesu | ☐ |
| 49 | Status zmieniony | Oryginalna akcja: status → REVERTED (szary) | ☐ |
| 50 | Sprawdź w Google Ads UI | Keyword ponownie ENABLED (lub bid przywrócony) | ☐ |
| 51 | Cofnięta akcja — brak "Cofnij" | Przycisk "Cofnij" znika po cofnięciu | ☐ |

---

## Feature 5: Search Terms Intelligence (PRD Feature 5)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 52 | Przejdź do "Wyszukiwane frazy" | Strona ładuje się z danymi | ☐ |
| 53 | 4 karty segmentów | HIGH_PERFORMER (zielony), WASTE (czerwony), IRRELEVANT (pomarańczowy), OTHER (szary) | ☐ |
| 54 | Każda karta pokazuje | Ilość, łączny koszt, kliknięcia | ☐ |
| 55 | Kliknij segment | Filtruje tabelę do tego segmentu | ☐ |
| 56 | Tabela — kolumny | Query text, Clicks, Cost (zł), Conversions, CTR%, Segment badge | ☐ |
| 57 | Waluta w PLN | Koszty wyświetlane jako "zł" nie "$" | ☐ |
| 58 | Wyszukiwarka działa | Wpisz fragment frazy → filtruje | ☐ |
| 59 | HIGH_PERFORMER poprawne | Frazy z conv ≥ 3 i CVR > avg kampanii | ☐ |
| 60 | WASTE poprawne | Frazy z clicks ≥ 5, conv = 0, CTR < 1% | ☐ |
| 61 | IRRELEVANT poprawne | Frazy zawierające "darmowe", "forum", "youtube" itp. | ☐ |
| 62 | Sortowanie | Kliknij nagłówek kolumny → sortuje | ☐ |

---

## Feature 6: Dashboard KPIs (PRD Feature 6)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 63 | Przejdź do "Pulpit" | KPI cards załadowane | ☐ |
| 64 | KPI: Wydatki | Suma spend ze wszystkich kampanii (zł) | ☐ |
| 65 | KPI: Kliknięcia | Suma clicks | ☐ |
| 66 | KPI: Konwersje | Suma conversions | ☐ |
| 67 | KPI: CTR | Średni CTR (%) | ☐ |
| 68 | KPI: CPC | Średni CPC (zł) | ☐ |
| 69 | KPI: CPA | Koszt na konwersję (zł) | ☐ |
| 70 | Dane ≠ 0 | Żadne KPI nie jest "0" lub "NaN" (jeśli konto ma dane) | ☐ |
| 71 | Porównaj z Google Ads UI | Wartości ± 5% zbieżne z Google Ads dashboard | ☐ |

---

## Feature 7: Anomaly Detection (PRD Feature 7)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 72 | Przejdź do "Alerty" | Strona z zakładkami: Nierozwiązane / Rozwiązane | ☐ |
| 73 | Po sync — alerty wygenerowane | Jeśli dane mają anomalie → alerty się pojawiają | ☐ |
| 74 | Alert card zawiera | Severity badge (HIGH/MEDIUM), typ, tytuł, opis, timestamp | ☐ |
| 75 | Alert badge w sidebar | Liczba przy "Alerty" (np. "3") jeśli są nierozwiązane | ☐ |
| 76 | Kliknij "Rozwiąż" | Alert przeniesiony do zakładki "Rozwiązane" | ☐ |
| 77 | Badge się aktualizuje | Po rozwiązaniu — badge zmniejsza się o 1 | ☐ |
| 78 | Zakładka "Rozwiązane" | Rozwiązane alerty widoczne z datą rozwiązania | ☐ |

---

## Testy cross-cutting (bezpieczeństwo + edge cases)

| # | Test | Oczekiwany rezultat | Wynik |
|---|------|---------------------|-------|
| 79 | Circuit breaker — bid > 50% | Próba zmiany bidu o >50% → blokada z komunikatem | ☐ |
| 80 | Circuit breaker — budget > 30% | Próba zmiany budżetu o >30% → blokada | ☐ |
| 81 | Revert po 24h | Przycisk "Cofnij" NIE pojawia się na starych akcjach (>24h) | ☐ |
| 82 | ADD_NEGATIVE — brak revert | Akcja "Add Negative" nie ma przycisku "Cofnij" (IRREVERSIBLE) | ☐ |
| 83 | Logout | Kliknij "Wyloguj" → token usunięty, status = nie zalogowany | ☐ |
| 84 | Restart po logout | Uruchom .exe → wymaga ponownego OAuth | ☐ |
| 85 | 2 szybkie kliknięcia "Zastosuj" | Nie wykonuje akcji 2 razy (debounce / disabled button) | ☐ |
| 86 | Sync w trakcie sync | Nie startuje drugiego synca (button disabled podczas sync) | ☐ |
| 87 | Brak internetu | Graceful error — komunikat "Brak połączenia", nie crash | ☐ |
| 88 | Pusta kampania (0 keywords) | Strona keywords pokazuje EmptyState, nie crash | ☐ |
| 89 | Klient bez search terms | Strona Search Terms pokazuje EmptyState | ☐ |

---

## DECYZJA PO FAZIE 2

- **Wszystkie 21-89 PASS** → Przejdź do Fazy 3 (testy automatyczne)
- **FAIL w Feature 2/4 (Apply/Undo)** → 🔴 KRYTYCZNY — naprawa natychmiast
- **FAIL w Feature 7 (Alerts)** → 🟠 POWAŻNY — ale nie blokuje release
- **FAIL w UI (język, waluta)** → 🟡 KOSMETYCZNY — napraw po Fazie 3

---

# ═══════════════════════════════════════════════════════
# FAZA 3: TESTY AUTOMATYCZNE
# Cel: Pytest backend + regression prevention
# Daj ten plan Claude Code do implementacji
# ═══════════════════════════════════════════════════════

## 3A: Backend unit tests (pytest)

Plik: `backend/tests/` — jeśli nie istnieje, utwórz.

### test_safety_limits.py — Circuit Breaker

```python
# TESTY DLA validate_action()
def test_bid_change_51pct_blocked():
    """Bid change > 50% → SafetyViolationError"""

def test_bid_change_49pct_passes():
    """Bid change < 50% → OK"""

def test_bid_zero_current_blocked():
    """current_val = 0 → SafetyViolationError (no div by zero)"""

def test_bid_below_minimum_blocked():
    """new bid < $0.10 → SafetyViolationError"""

def test_bid_above_maximum_blocked():
    """new bid > $100 → SafetyViolationError"""

def test_budget_change_31pct_blocked():
    """Budget change > 30% → SafetyViolationError"""

def test_budget_change_29pct_passes():
    """Budget change < 30% → OK"""

def test_pause_keyword_over_20pct_blocked():
    """21st keyword of 100 paused today → SafetyViolationError"""

def test_pause_keyword_under_20pct_passes():
    """19th keyword of 100 paused today → OK"""

def test_add_negative_limit_101_blocked():
    """101st negative today → SafetyViolationError"""

def test_add_negative_limit_99_passes():
    """99th negative today → OK"""
```

### test_segmentation.py — Search Terms

```python
# TESTY DLA SearchTermsService._classify()
def test_irrelevant_keyword_darmowe():
    """'buty darmowe' → IRRELEVANT"""

def test_irrelevant_keyword_youtube():
    """'nike youtube' → IRRELEVANT"""

def test_high_performer():
    """conv=5, clicks=20, cvr > campaign avg → HIGH_PERFORMER"""

def test_waste():
    """clicks=10, conv=0, ctr=0.5% → WASTE"""

def test_other_insufficient_data():
    """clicks=2, conv=0 → OTHER (za mało danych)"""

def test_high_performer_not_if_low_cvr():
    """conv=3 ale cvr < campaign avg → OTHER (nie HIGH_PERFORMER)"""

def test_waste_not_if_has_conversions():
    """clicks=10, conv=1 → OTHER (nie WASTE — ma konwersje)"""

def test_classification_priority():
    """'darmowe buty' z conv=5 → IRRELEVANT (first match wins, nie HIGH_PERFORMER)"""
```

### test_analytics.py — KPI & Anomalies

```python
# TESTY DLA AnalyticsService
def test_kpis_basic():
    """2 kampanie → prawidłowe sumy spend, clicks, conv"""

def test_kpis_zero_division():
    """0 clicks → CTR = 0, CPC = 0 (nie crash)"""

def test_roas_formula():
    """ROAS = revenue/cost, nie conversions/cost"""

def test_anomaly_spend_spike():
    """Kampania z 3x avg spend → alert SPEND_SPIKE created"""

def test_anomaly_ctr_drop():
    """Kampania z CTR < 0.5% i impressions > 1000 → alert CTR_DROP"""

def test_anomaly_no_duplicate():
    """Ten sam alert nie tworzy się 2 razy (deduplikacja)"""
```

### test_action_executor.py — Apply & Revert

```python
# TESTY DLA ActionExecutor
def test_dry_run_returns_preview():
    """dry_run=True → status 'dry_run', nie wykonuje akcji"""

def test_apply_logs_to_action_log():
    """Po apply → nowy wpis w action_log z old_value_json"""

def test_revert_within_24h():
    """Revert < 24h → sukces"""

def test_revert_after_24h_blocked():
    """Revert > 24h → error 'window expired'"""

def test_revert_already_reverted():
    """Revert na REVERTED → error 'already reverted'"""

def test_revert_add_negative_blocked():
    """Revert ADD_NEGATIVE → error 'irreversible'"""

def test_revert_failed_action_blocked():
    """Revert FAILED → error 'cannot revert failed'"""
```

### test_models.py — Podstawowe

```python
def test_all_monetary_columns_are_biginteger():
    """Żadna kolumna pieniężna nie jest Float"""

def test_action_log_has_reverted_at():
    """ActionLog ma kolumnę reverted_at"""

def test_alert_has_resolved_at():
    """Alert ma kolumnę resolved_at"""

def test_recommendation_statuses():
    """Recommendation.status in ('pending', 'applied', 'dismissed')"""
```

---

## 3B: API integration tests

```python
# test_api_endpoints.py — httpx TestClient
def test_health_endpoint():
    """GET /health → 200 + {status: 'ok'}"""

def test_auth_status_unauthenticated():
    """GET /auth/status bez credentials → {authenticated: false}"""

def test_clients_list():
    """GET /clients → 200 + lista klientów"""

def test_recommendations_require_client_id():
    """GET /recommendations bez client_id → 422 validation error"""

def test_apply_nonexistent_recommendation():
    """POST /recommendations/999/apply → 404 lub error message"""

def test_revert_nonexistent_action():
    """POST /actions/revert/999 → error message"""
```

---

## 3C: Polecenie dla Claude Code

```
Przeczytaj PLAN_TESTOW.md (sekcja Faza 3).
Utwórz testy pytest w backend/tests/ zgodnie z opisanymi test case'ami.
Użyj SQLite in-memory w conftest.py.
Uruchom pytest i napraw wszystkie FAIL.
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ D: RAPORT Z TESTÓW (szablon)
# ═══════════════════════════════════════════════════════

Wypełnij po zakończeniu każdej fazy:

## Faza 1: Smoke Test

| Sekcja | PASS | FAIL | Notatki |
|--------|------|------|---------|
| S-01 Uruchomienie | /5 | | |
| S-02 Nawigacja | /4 | | |
| S-03 OAuth | /5 | | |
| S-04 Sync | /6 | | |
| **RAZEM** | **/20** | | |

## Faza 2: Pełny test manualny

| Feature | PASS | FAIL | Blocker? | Notatki |
|---------|------|------|----------|---------|
| F1 Sync & Data | /6 | | | |
| F2 Apply + Modal | /7 | | 🔴 | |
| F3 Recommendations | /8 | | | |
| F4 Action History & Undo | /10 | | 🔴 | |
| F5 Search Terms | /11 | | | |
| F6 Dashboard KPIs | /9 | | | |
| F7 Anomaly Detection | /7 | | | |
| Cross-cutting | /11 | | | |
| **RAZEM** | **/69** | | | |

## Faza 3: Testy automatyczne

| Plik | Tests | Pass | Fail |
|------|-------|------|------|
| test_safety_limits.py | | | |
| test_segmentation.py | | | |
| test_analytics.py | | | |
| test_action_executor.py | | | |
| test_models.py | | | |
| test_api_endpoints.py | | | |
| **RAZEM** | | | |

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ E: ŚCIEŻKA PO TESTACH
# ═══════════════════════════════════════════════════════

### Jeśli wszystko PASS:
1. ✅ MVP gotowe do użytku
2. Zacznij 7-dniowy test w produkcji (PRD §6.1: "Zero crashes during 7 days of usage")
3. Po 7 dniach → release v1.0

### Jeśli FAIL w Fazie 1:
→ STOP. Napraw fundamenty (.exe, OAuth, sync). Nie testuj dalej.

### Jeśli FAIL w Fazie 2 (krytyczne):
→ Zbierz listę FAILi → daj Claude Code do naprawy → retestuj TYLKO te które FAILowały

### Jeśli FAIL w Fazie 2 (kosmetyczne):
→ Kontynuuj Fazę 3. Napraw kosmetykę po testach automatycznych.

### Jeśli FAIL w Fazie 3:
→ Claude Code naprawia kod + testy. Retestuj do 100% PASS.

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ F: ZNANE RYZYKA
# ═══════════════════════════════════════════════════════

| Ryzyko | Prawdopodobieństwo | Impact | Co robić |
|--------|-------------------|--------|----------|
| OAuth nie zwraca refresh_token | Średnie | Blokujący | Cofnij dostęp na myaccount.google.com + retry |
| MCC wymaga login_customer_id | Wysokie | Blokujący | Upewnij się że GoogleAdsClient używa login_customer_id dla MCC |
| Rate limit Google Ads API | Niskie | Blokujący sync | Nie syncuj >3 klientów naraz |
| Search terms puste | Średnie | Nie blokujący | Niektóre konta nie mają search terms — EmptyState powinien się pokazać |
| PyWebView biały ekran | Niskie | Blokujący | Sprawdź czy Edge WebView2 zainstalowany na Windows |
| SQLite locked (plik otwarty) | Niskie | Crash | Zamknij DB Browser jeśli otwarty |
| Rekomendacje = 0 | Średnie | Nie blokujący | Konto z < 30 dni danych może nie generować rekomendacji |

---

**KONIEC PLANU TESTÓW**
**Zacznij od Fazy 1 → S-01: Double-click na .exe**