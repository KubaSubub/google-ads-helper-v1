# Feature Spec: Settings Tab UX Overhaul
generated: 2026-04-09 | author: PM Agent | status: ready

## Skad to przyszlo
CEO Decision: "Settings to daily-use tab — ma UX issues: prompt() do konkurentow, brak polskich znakow, brak info o sync, brak reset defaults dla safety limits"
Intelligence signal: "Adalysis ma task list + scheduling; user pain: brak alertow o anomaliach (high freq); MCC management partial"

## User Story
Jako Kuba zarzadzajacy kampaniami klienta,
chce miec Settings tab ktory jest dopracowany i pokazuje status synchronizacji,
zeby nie musiec sprawdzac osobno czy dane sa aktualne i nie irytowac sie prompt() dialogami.

## Acceptance Criteria
- [ ] AC1: Dodawanie konkurentow dziala przez inline input (text field + Enter/button), NIE przez prompt()
- [ ] AC2: Wszystkie polskie labele maja poprawne znaki diakrytyczne (Reguly→Reguly biznesowe z ogonkami, ogolne→ogolne z ogonkami, bezpieczenstwa→bezpieczenstwa z ogonkami, itd.)
- [ ] AC3: Sekcja "Ostatnia synchronizacja" pokazuje: date ostatniego synca, status (success/failed/partial), czas trwania — dane z GET /sync/logs?client_id={id}&limit=1
- [ ] AC4: Przycisk "Przywroc domyslne" w sekcji safety limits resetuje wszystkie pola do GLOBAL_DEFAULTS (czysc client overrides)
- [ ] AC5: Sekcja MCC uzywa tego samego section header pattern co pozostale sekcje (ikona + h3 + opis)
- [ ] AC6: Sekcja "Zaplanowana synchronizacja" z toggle enabled/disabled + interval select — dane z GET/POST /sync/schedule
- [ ] AC7: Build przechodzi bez bledow (npm run build OK)

## Edge Cases
- Brak logow synca (nowy klient, nigdy nie syncowany) → sekcja sync pokazuje "Jeszcze nie synchronizowano" z przyciskiem "Synchronizuj teraz"
- Brak ScheduledSyncConfig dla klienta → sekcja scheduled sync pokazuje disabled toggle z domyslnym intervalem 24h
- Usuwanie ostatniego konkurenta → lista staje sie pusta, inline input nadal widoczny
- Safety limits wszystkie puste po reset → placeholder pokazuje wartosc domyslna (juz dziala)
- Klient bez google_customer_id → sekcja MCC ukryta (juz dziala)

## Out of Scope (V1)
- Tab structure / refactor Settings na multi-tab (przesadna komplikacja na 6 fixow)
- Alert thresholds configuration (osobny feature)
- Sync logs history table (osobny feature — tu tylko ostatni sync)
- Bulk MCC operations z Settings

## Success Metric
Kuba otwiera Settings, widzi kiedy ostatnio dane byly zsynchronizowane, dodaje konkurenta bez prompt() dialogu, i wszystkie labele sa po polsku z ogonkami.

## Szacowana zlozonosc
Medium — 7 taskow (6 UI zmian + 2 API calls w api.js)

## Zaleznosci
- API endpoints (ISTNIEJACE — nie trzeba nowych):
  - GET /sync/logs?client_id={id}&limit=1 — ostatni sync
  - GET /sync/schedule?client_id={id} — scheduled sync config
  - POST /sync/schedule — update schedule
- Frontend:
  - Settings.jsx — glowny plik do edycji
  - api.js — dodanie 3 API calls (getSyncLogs, getScheduledSync, updateScheduledSync)
