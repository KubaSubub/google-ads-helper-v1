# Feature Spec: MCC Overview — Synchronizacja kont
generated: 2026-04-14 | author: PM Agent | status: ready

## Skad to przyszlo
CEO Decision: "Synchronizacja kont widok mcc-overview — MCC Overview ma KPIs/sparklines ale brak
zarządzania synchem per konto — specjalista nie może sprawdzić statusu syncu / wymusić syncu bez
wchodzenia w Settings każdego klienta osobno."
Intelligence signal: n/a

## User Story
Jako Kuba zarządzający kampaniami kilku klientów,
chcę widzieć w MCC Overview aktualność danych każdego konta oraz uruchamiać sync
bezpośrednio z tego widoku,
żeby nie wchodzić do Settings każdego klienta osobno i mieć pewność że
analizuję świeże dane.

## Co JUZ istnieje (nie przebudowywac)
- `last_synced_at` per konto w `/mcc/overview` response
- `SyncIndicator` komponent (spinning ikona + data DD.MM.YYYY)
- Przycisk "Synchronizuj nieaktualne" (stale = >6h)
- Per-row sync button w tabeli
- `SyncLog` model: `status`, `phases` (JSON), `started_at`, `finished_at`, `total_synced`, `total_errors`
- `SyncCoverage` model: per-resource `data_from/data_to`, `last_sync_at`, `last_status`

## Co BRAKUJE (zakres tej specyfikacji)

### 1. Freshness badge (zamiast surowej daty)
- Aktualnie: "13.04.2026" — nie wiadomo czy stare bez przeliczenia w głowie
- Potrzeba: kolorowy badge wskazujący świeżość: "Aktualne" / "Stare" / "Niezsynchronizowane"

### 2. Historia syncow per konto (drawer/panel)
- Aktualnie: brak — nie wiadomo czy ostatni sync się udał, ile faz przeszedł, ile rekordów
- Potrzeba: kliknij w badge → otwiera się panel z listą ostatnich 5 syncow (status, czas trwania, fazy)

### 3. Endpoint /mcc/sync-history
- Aktualnie: brak — SyncLog istnieje ale nikt go nie eksponuje dla MCC view
- Potrzeba: `GET /mcc/sync-history?client_id=X&limit=5`

### 4. Progress bulk sync
- Aktualnie: "Synchronizuj nieaktualne" uruchamia N syncow sekwencyjnie, brak feedbacku poza toast'em na końcu
- Potrzeba: toast z counter progress "Synchronizowanie 2/4..." podczas trwania

## Acceptance Criteria

- [ ] AC1: Kolumna "Sync" w tabeli MCC pokazuje kolorowy freshness badge zamiast surowej daty:
  - Zielony "Świeże" — last_synced_at < 6h temu
  - Zółty "Stare (Xh)" — last_synced_at 6–48h temu, gdzie X = ile godzin temu
  - Czerwony "Nieaktualne" — last_synced_at > 48h lub null
  - Podczas syncu: spinner (stan obecny — zachowany)

- [ ] AC2: Kliknięcie w freshness badge otwiera panel historii syncow dla danego konta,
  pokazujący max 5 ostatnich syncow z: status (success/partial/failed), czas trwania,
  total_synced rekordów, total_errors, timestamp. Panel zamyka się kliknięciem X lub Escape.

- [ ] AC3: Nowy endpoint `GET /mcc/sync-history?client_id=X&limit=5` zwraca:
  `[{id, client_id, started_at, finished_at, status, total_synced, total_errors, duration_s}]`
  — dane z istniejącego `SyncLog` model, posortowane `finished_at DESC`.

- [ ] AC4: Przycisk "Synchronizuj nieaktualne" pokazuje toast z progress counter:
  "Synchronizowanie kont 1/3..." → "Synchronizowanie kont 2/3..." → "Zsynchronizowano 3/3 kont".
  Toast aktualizuje się w miejscu (nie stos toastów).

- [ ] AC5: Po zakończeniu sync (per-row lub bulk) freshness badge automatycznie aktualizuje się
  (refresh `/mcc/overview` lub lokalna aktualizacja `last_synced_at` w state).

- [ ] AC6: Panel historii wyświetla "Brak historii syncow" jeśli konto nigdy nie było synchronizowane.

- [ ] AC7: Endpoint `/mcc/sync-history` zwraca 200 z pustą listą `[]` gdy brak syncow dla klienta
  (nie 404). Zwraca 404 gdy `client_id` nie istnieje w bazie.

## Edge Cases

- Konto nigdy nie zsynchronizowane (null last_synced_at) → badge czerwony "Nieaktualne", panel pokazuje "Brak historii syncow"
- Sync w trakcie (syncing=true) → spinner jak teraz, po zakończeniu badge odświeża się
- Błąd sync (SyncLog.status = "failed") → w panelu historii wpis ze statusem "Błąd" (czerwony), badge bazuje tylko na last successful/partial (istniejąca logika — bez zmian)
- Limit param w /mcc/sync-history: max 20 (ponad to zwraca 400), default 5
- Użytkownik kliknie w badge podczas aktywnego syncu → panel otwiera się z historią (nie blokuje syncu)
- Jeden klient, wiele syncow jednocześnie (edge case API) → wyświetl najnowszy jako "w trakcie"

## Out of Scope (V1)

- Selective phase sync (np. "tylko kampanie") — pełny sync pozostaje jedyną opcją
- Real-time SSE streaming progress faz w panelu historii
- SyncCoverage breakdown (per resource type) — to osobny feature
- Anulowanie aktywnego syncu
- Retry automatyczny przy błędzie
- Notyfikacje email/desktop o zakończeniu syncu

## Success Metric

Kuba otwiera MCC Overview, jednym rzutem oka widzi które z 4 kont mają stare dane
(czerwony/żółty badge), klika "Synchronizuj nieaktualne" i widzi counter 1/2, 2/2 zanim przejdzie
do analizy — bez wchodzenia w Settings.

## Szacowana zlozonosc

Medium — 5 taskow:
1. Backend: `GET /mcc/sync-history` endpoint + unit testy (mcc_service + router)
2. Frontend: freshness badge komponent (zastąpienie SyncIndicator)
3. Frontend: SyncHistoryPanel (drawer) + api.js call
4. Frontend: progress toast update podczas bulk sync
5. Lock testy: 2 backend contract testy + 2 E2E

## Zaleznosci

### Istniejące (do wykorzystania):
- `SyncLog` model (`backend/app/models/sync_log.py`) — główne źródło danych
- `MCCService._build_account_data()` — already queries `SyncLog.finished_at`
- `MCCOverviewPage.jsx` `handleSyncAll()` — dodać counter state
- `showToast` z AppContext — zaktualizować live toast
- C (kolory) z MCCOverviewPage.jsx — `C.success`, `C.warning`, `C.danger`

### Nowe:
- `GET /mcc/sync-history?client_id=X&limit=N` — nowy endpoint w `mcc.py`
- `getMccSyncHistory(clientId, limit)` — nowa funkcja w `api.js`
- `SyncHistoryPanel.jsx` — nowy komponent (lub inline w MCCOverviewPage)
- Freshness badge — zastąpienie `SyncIndicator` lub rozszerzenie go
