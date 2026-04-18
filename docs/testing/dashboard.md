# Dashboard (Pulpit) — notatki testowe

> Ręczne testowanie widoku `/dashboard`. Wpisuj obserwacje w **Historia**, destyluj do **Do zrobienia**.
> Plik hardlinkowany z `[repo]/docs/testing/dashboard.md` — CEO czyta stąd zadania.

---

## 🔨 Do zrobienia

*Czekają na CEO — /ceo przeczyta i wykona.*

- [ ]

---

## 🔄 W toku

- [ ]

---

## ✅ Zrealizowane

*Po wdrożeniu: przenoś tu z "Do zrobienia" dla historii.*

- [x] Dashboard consolidation (2026-04-11, commit `646a265`) — Quick Scripts preview flow, header filters, zunifikowane filtry daty
- [x] Komponenty wyekstraktowane (commit `3ecdfdc`) — AnomalyAlerts, BudgetPacing, ScriptRun
- [x] Performance: `/scripts/counts` bulk endpoint 60s TTL cache (commit `ce1a8fa`)
- [x] 9/9 ads-check (2026-03-26) — sort kampanii, deep-link, Wasted Spend clickable, IS per kampania, sparkline tooltip

---

## 📝 Historia obserwacji

*Wpisuj co widzisz podczas klikania — data + co zauważyłeś.*

### 2026-03-29 — ads-user review #3 (Marek, 6 lat GAds)
- Health Score 50 w żółtym kole (z 3 alertami wysokiej wagi)
- "Meble Biurowe" przepala budżet 376% przy 94% miesiąca
- 8 kart KPI w siatce 4+4 czytelne
- Quality Score widget: średni 6.7/10, 4 słowa low QS zjadają 23.9% budżetu
- Insighty zwinięte w accordion z badge "2" — user nie widzi treści bez klikania
- Werdykt: wszystko działa, są insights ponad Google Ads UI

###
