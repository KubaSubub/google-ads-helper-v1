# Trend Explorer — Mapa integracji z modułami

## Status integracji

| Moduł | Integracja | Priorytet |
|-------|-----------|-----------|
| Prognoza | ✅ Planowana (szczegóły poniżej) | v1.1 |
| Monitoring (Anomalie) | ✅ Planowana (szczegóły poniżej) | v1.1 |
| Rekomendacje | ⏳ Pośrednia | v1.2 |
| Raport AI | ⏳ Planowana | v1.2 |
| Raporty | ⏳ Planowana | v1.2 |
| Kampanie | ⏳ Opcjonalna | v2.0 |

---

## 1. Trend Explorer ↔ Prognoza

### Co łączy te moduły
Trend Explorer pokazuje dane historyczne + korelacje.  
Prognoza pokazuje 7-dniową projekcję z regresji liniowej.  
To naturalny ciąg: **co było → co będzie**.

### Wariant A — Przycisk "Pokaż prognozę" (prosty)
- W Trend Explorerze: przycisk/link `→ Prognoza` obok badge korelacji
- Kliknięcie przenosi do `/forecast` z zachowaniem aktywnego klienta i zakresu dat
- Opcjonalnie: przekazuje pierwszą wybraną metrykę przez URL param (`/forecast?metric=cost`)

```
URL: /forecast?metric=cost&from=2025-02-20&to=2025-03-21
```

### Wariant B — Mini-prognoza na wykresie Trend Explorera (zaawansowany)
- Po prawej stronie osi X: kropkowana linia kontynuacji (+7 dni)
- Szary obszar confidence interval
- Tooltip: "Prognoza regresji liniowej — kliknij po szczegóły"
- Kliknięcie otwiera modal lub przechodzi do `/forecast`

### Rekomendacja
Wariant A — szybki w implementacji, wystarczający dla MVP. Wariant B robi wrażenie na kliencie ale wymaga 2× więcej pracy.

---

## 2. Trend Explorer ↔ Monitoring (Anomalie)

### Co łączy te moduły
Monitoring wykrywa anomalie statystyczne (z-score).  
Trend Explorer pokazuje przebieg metryk w czasie.  
Anomalia widoczna na wykresie = kontekst który teraz brakuje.

### Integracja: Markery anomalii na wykresie

**Kierunek 1 — z Monitoring → Trend Explorer:**
- Kliknięcie alertu w Monitoring otwiera Trend Explorer z datą anomalii oznaczoną pionową linią
- URL: `/` (Pulpit) + `?highlight_date=2025-03-05&metric=cost`
- Pionowa linia z ikoną ⚠️ na wykresie i tooltipem: "Anomalia: Koszt +2.4σ powyżej normy"

**Kierunek 2 — w Trend Explorerze (pasywny):**
- Trend Explorer przy renderowaniu wykresu odpytuje backend o anomalie dla aktywnego klienta w widocznym zakresie dat
- Rysuje małe markery (dot/triangle) na osi X w dniach z alertami
- Hover pokazuje: typ anomalii, wartość, z-score

### Endpoint backend
```
GET /alerts?client_id={id}&date_from={d}&date_to={d}&resolved=false
→ zwraca alerty z polem `detected_date`
```

---

## 3. Trend Explorer ↔ Rekomendacje (pośrednia)

### Co łączy
Silna korelacja CTR ↔ Konwersje (r=0.63) = sygnał do rekomendacji optymalizacji kreacji.  
Słaba korelacja Koszt ↔ Konwersje = sygnał do rekomendacji audytu budżetu.

### Integracja
Nie wymaga UI linku — **engine rekomendacji może czytać korelacje z bazy** i generować rekomendację kontekstową:

```
Reguła: jeśli r(cost, conversions) < 0.3 przez ostatnie 30d
→ ALERT: "Wzrost kosztu nie przekłada się na konwersje — sprawdź Quality Score i strony docelowe"
```

Wymaga zapisywania wyników `/correlation` do tabeli `correlation_results` (nowa tabela lub pole w metrics_daily).

---

## 4. Trend Explorer → Raport AI / Raporty (future)

*Do implementacji w v1.2 — opisane skrótowo jako scope.*

### Raport AI (`/agent`)
- Dane z Trend Explorera (top korelacje, trendy) dodane do kontekstu promptu agenta
- Użytkownik może zapytać: "Dlaczego mój CTR spada mimo rosnącego kosztu?" → agent dostaje r(CTR, koszt) = -0.49 jako input

### Raporty (`/reports`)
- Sekcja "Trendy i korelacje" w raportach tygodniowym/miesięcznym
- Dane: top 3 korelacje za okres + wykres PNG eksportowany z Trend Explorera
- Wymaga: endpoint `GET /trend-explorer/export?client_id=...` zwracający dane do chart.js po stronie raportu

---

## Kolejność implementacji

```
v1.1:
  1. Trend Explorer → Prognoza (Wariant A, przycisk/link)        ~2h
  2. Monitoring → Trend Explorer (highlight daty po kliknięciu)  ~3h
  3. Markery anomalii na wykresie Trend Explorer                 ~4h

v1.2:
  4. Korelacje → silnik rekomendacji (nowa reguła)               ~4h
  5. Trend Explorer w Raport AI (kontekst dla agenta)            ~3h
  6. Trend Explorer w Raporty (sekcja trendów)                   ~5h

v2.0:
  7. Mini-prognoza na wykresie (Wariant B)                       ~8h
  8. Filtrowanie Trend Explorera per kampania                    ~6h
```

---

## Uwagi techniczne

- Trend Explorer żyje na Pulpicie (`/`) — integracje nie wymagają przeniesienia komponentu, tylko dodania linków/callbacków
- Przekazywanie stanu między modułami: URL params (proste) lub React Context (jeśli potrzebna głębsza integracja)
- Anomalie: backend już zwraca `detected_date` w `/alerts` — frontend wymaga tylko warstwy wizualizacji
