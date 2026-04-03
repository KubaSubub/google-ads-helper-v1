# Ocena eksperta Google Ads — MCC Overview (re-test po sprintach)
> Data: 2026-04-02 | Średnia ocena: 8.8/10 | Werdykt: ZACHOWAĆ (minor polish needed)

## TL;DR

MCC Overview przeszedł z 7.5/10 do 8.8/10 — z prostej tabeli wydatków w kompletny poranny dashboard z 11 sortowalnymi metrykami, health breakdown, dismiss rekomendacji, billing status i compact toggle. Teraz realnie konkuruje z Google Ads MCC i daje wartości których natywny UI nie oferuje. Pozostałe issues to polish (KPI zera z seed data, billing tooltip, filtr okresu).

## Oceny

| Kryterium | Ocena | Komentarz |
|-----------|-------|-----------|
| Potrzebność | 9/10 | Poranny dashboard dla specjalisty z wieloma kontami — must have. Playbook: "15-30 min/konto na daily checks" — ten widok skraca triaging do 2 min. |
| Kompletność | 8/10 | 11 metryk + pacing + health + billing + alerts + new access + dismiss recs + NKL. Brakuje filtra okresu i impression share. |
| Wartość dodana vs Google Ads UI | 9/10 | 7 unikalnych wartości których GAds MCC nie ma (health breakdown, external changes, new access alert, one-click dismiss, compact toggle, NKL cross-account, pacing per konto). |
| Priorytet MVP | 9/10 | Landing page = first impression. Musi być dobry. Jest. |
| **ŚREDNIA** | **8.8/10** | |

## Co robi dobrze

- **Pełne metryki jak w GAds MCC** — clicks, impressions, CTR, CPC, conversions, CVR, conv value, CPA, ROAS. Specjalista nie musi otwierać GAds żeby zobaczyć performance.
- **Health score z tooltip breakdown** — hover na kółku pokazuje 6 filarów (Wyniki, Jakość, Efektywność, Zasięg, Stabilność, Struktura). GAds nie ma nic porównywalnego.
- **External changes detection** — "X zewn." z żółtym wyróżnieniem. Krytyczne dla agencji — natychmiast widzę że klient grzebał na koncie.
- **New access alert (UserPlus)** — żółta ikona gdy nowy email pojawił się w Change History. Wykrywanie nieautoryzowanego dostępu.
- **One-click dismiss rekomendacji Google** — X button per konto. W GAds to multi-click per rekomendacja per konto.
- **Compact mode toggle** — ukrywa 6 kolumn drugorzędnych. Ratuje UX przy wielu kolumnach.
- **Deep-links z kolumn** — kliknięcie "Zmiany" → Action History, "Rek." → Recommendations, Bell → Alerts. Zero navigation overhead.
- **Dwie sekcje NKL** — MCC-level i per-account. Rozdzielenie jest prawidłowe — inne zakresy list.
- **Billing status column** — ikona karty kredytowej per konto. Nawet jeśli API nie daje pełnych danych, sam fakt że widok to uwzględnia jest ważny.

## Co brakuje (krytyczne)

### K1: Filtr okresu
Tabela jest hardcoded na 30d. Specjalista potrzebuje przełączać: 7d (szybki scan), 14d (trend), 30d (standard), bieżący miesiąc (budget review).
- **Playbook ref:** "Performance Analysis — Porównanie Last 7 days vs Previous 7 days"
- **Implementacja:** `_aggregate_metrics()` już przyjmuje start/end — wystarczy dodać period selector w UI i parametr do `GET /mcc/overview?days=X`
- **Nakład:** S

### K2: KPI cards z zerami
"Kliknięcia: 0" i "Wyświetlenia: 0" przy $60k wydatków to red flag dla usera. Seed data prawdopodobnie nie ma clicks/impressions w MetricDaily dla niektórych kont.
- **Rozwiązanie:** Albo doseedować clicks/impressions (jednorazowo), albo ukryć KPI card gdy wartość = 0 i spend > 0.
- **Nakład:** S

## Co brakuje (nice to have)

### N1: Impression Share per konto
Mówi czy konto wykorzystuje potencjał. Dane w MetricDaily (search_impression_share). Agregacja jak inne metryki.

### N2: Billing tooltip
Szare ikony CreditCard nie mówią co oznaczają. Dodać tooltip "Płatności OK" / "Brak billing setup" / "Brak dostępu do API billing".

### N3: Domyślny compact mode
17 kolumn w full mode wymaga scrolla. Compact (11 kolumn) jest czytelniejszy. Rozważyć jako domyślny.

### N4: Row selection + bulk actions
Checkbox per wiersz → "Synchronizuj zaznaczone" / "Odrzuć rek. zaznaczonych". Przy 15+ kontach oszczędza czas.

## Co usunąć/zmienić

- **KPI "Avg. CTR: —"** — jeśli clicks=0, ten KPI jest bezwartościowy. Ukryć lub zamienić na coś użytecznego (np. "Aktywne kampanie" sumarycznie).
- **Sekcja "Listy wykluczeń MCC" gdy pusta** — pokazuje pustą sekcję. Dodać info "Połącz konto MCC aby zobaczyć listy wykluczeń managera" zamiast pustego "Brak list".

## Porównanie z Google Ads UI

| Funkcja | Google Ads MCC | Nasza apka | Werdykt |
|---------|---------------|------------|---------|
| Lista kont z metrykami | ✅ Tabela z kolumnami | ✅ Tabela z 11 metrykami | **IDENTYCZNE+** (mamy więcej) |
| Health score per konto | ❌ Brak | ✅ Kółko 0-100 + tooltip 6 filarów | **LEPSZE** |
| Pacing per konto | ❌ Brak (per kampania) | ✅ Zagregowany status | **LEPSZE** |
| Zewnętrzne zmiany | ❌ Ręczne filtrowanie | ✅ Auto-count + badge | **LEPSZE** |
| New access detection | ❌ Brak | ✅ UserPlus badge | **LEPSZE** |
| Dismiss rekomendacji | ✅ Per konto multi-click | ✅ One-click X button | **LEPSZE** |
| Compact/full toggle | ❌ Brak | ✅ Toggle button | **LEPSZE** |
| Filtr okresu | ✅ Dowolny zakres dat | ❌ Hardcoded 30d | **GORSZE** |
| Impression Share | ✅ Dodawalna kolumna | ❌ Brak | **GORSZE** |
| Status płatności | ✅ Widoczny inline | ⚠️ Ikona bez tooltipa | **CZĘŚCIOWO** |
| Bulk actions | ✅ Checkboxy + menu | ❌ Brak | **GORSZE** |
| NKL cross-account | ✅ Shared Sets manager | ✅ 2 sekcje (MCC + per konto) | **LEPSZE** |

**Bilans: 7 LEPSZE, 1 IDENTYCZNE+, 3 GORSZE, 1 CZĘŚCIOWO**

## Nawigacja i kontekst

- **Skąd user trafia:** Landing page — / redirectuje do /mcc-overview
- **Dokąd przechodzi:** Kliknięcie wiersza → /dashboard, deep-links → /action-history, /recommendations, /alerts, /keywords
- **Co działa dobrze:** Breadcrumb "← Wszystkie konta" na Dashboard. Deep-links z kolumn. Link do Google Ads external.
- **Co brakuje:** Link z health score → deep dive health page (np. /quality-score z pre-selected clientem)

## Odpowiedzi na pytania @ads-user

1. **KPI zera** — prawdopodobnie seed data issue. MetricDaily dla niektórych kont ma cost_micros ale clicks=0 i impressions=0. Trzeba albo doseedować albo ukryć zerowe KPI.
2. **Billing szare ikony** — API zwraca "unknown" bo google_ads_service nie jest połączony w dev. Na produkcji z pełnym API powinno pokazać status. Tooltip jest ustawiony w atrybucie `title` — powinien się pojawić na hover (może być zbyt subtelny).
3. **Compact domyślny** — rekomendacja: TAK, compact jako default. User może rozwinąć jeśli chce.
4. **Filtr okresu** — KRYTYCZNE na następny sprint. Backend jest gotowy (parametr days), brakuje UI selectora.
5. **MCC NKL puste** — expected w dev bez manager account. Dodać lepszą empty state message.

## Rekomendacja końcowa

**ZACHOWAĆ** — widok przeszedł pełną ewolucję od prostej tabeli do kompletnego MCC dashboard. Teraz daje 7 unikalnych wartości których Google Ads MCC nie oferuje, przy zachowaniu pełnego zestawu metryk z GAds. Pozostałe issues (filtr okresu, KPI zera, billing tooltip) to polish — żadne nie blokuje codziennego użycia.

**Priorytet next sprint:**
1. Filtr okresu (S) — jedyny "GORSZE" który jest łatwy do naprawienia
2. KPI zera fix (S) — seed data + conditional rendering
3. Billing tooltip (S) — CSS title jest, ale warto dodać styled tooltip
