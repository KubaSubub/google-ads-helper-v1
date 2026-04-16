# /ads-user — Trend Explorer

**Kto:** Marek, specjalista Google Ads, 6 lat doświadczenia (e-commerce + lead gen)
**Testowane na:** Trend Explorer w Dashboardzie (komponent `frontend/src/components/TrendExplorer.jsx`, mount w `features/dashboard/DashboardPage.jsx:382`)
**Data:** 2026-04-15
**Uwaga:** review bez screenshota — w `frontend/e2e-screenshots/` nie ma zrzutu Trend Explorera, tylko dashboard/MCC. Piszę z kodu + własnej pamięci jak to wygląda na ekranie.

**WAŻNY KONTEKST — dwa warianty Trend Explorera w apce:**
1. **Dashboard → TrendExplorer** (ten review) — widok agregacyjny, 9 metryk, dla całego konta + globalnego filtra.
2. **Kampanie → CampaignTrendExplorer** ([frontend/src/features/campaigns/components/CampaignTrendExplorer.jsx](frontend/src/features/campaigns/components/CampaignTrendExplorer.jsx)) — widok per-kampania, **17 metryk** (w tym Search Impression Share, Click Share, Top IS, Abs Top IS, Budget/Rank Lost IS, Abs Top %, Top Impr %), uruchamiany z wybranej kampanii na tabeli.

To jest kluczowe dla reszty raportu: brak per-campaign splitu w dashboardowym Trend Explorerze **nie jest brakiem** — jest świadomą separacją. Per-campaign analityka żyje w drugiej zakładce i ma nawet więcej metryk niż ta na dashboardzie.

---

## Co widzę po wejściu

Wchodzę w Dashboard, scrolluję do sekcji "Trend Explorer". Karta w ciemnym motywie (v2-card, rgba white 0.03), header po lewej z tytułem i podtytułem "Porównaj metryki w czasie". Po prawej pigułki aktywnych metryk — domyślnie `Koszt` i `Kliknięcia`, każda z X-em do usunięcia, obok pigułka `+ Dodaj metrykę` która rozwija listę pozostałych. Pod spodem wykres 220px wysokości, linie smooth, bez kropek. Jak dodam trzecią metrykę i mieszają się procenty z liczbami (np. `CTR` + `Koszt`), pojawia się druga oś Y z prawej — sam sobie to włącza, nie muszę klikać.

Jak tylko mam 2+ metryki, w headerze wyskakuje badge `Kor. +0.87 (30 par)` albo podobny — to najsilniejsza para Pearsona. Klik → otwiera się popup z pełną macierzą korelacji, kolorowaną (|r|>0.7 zielony, |r|>0.4 żółty, reszta szara) i opisem słownym "silna dodatnia" / "słaba ujemna" itd.

Na samym wykresie mam niebieskie przerywane pionowe linie z kropką u góry — to są **akcje z Action History** tamtego dnia. Hover na kropkę i widzę w tooltipie: "Zmiana stawki", nazwa keywordu/kampanii, before/after (np. `0,45 → 0,62 zł`), godzina. Pod wykresem legenda: `Zmiana na koncie • 12 akcji w okresie`.

Filtry (date range, campaign_type, status) czytam z globalnego Sidebara — nie mam ich w samym widżecie.

---

## Co mogę zrobić

- Dodać do 5 metryk z puli 9: `koszt, kliknięcia, wyświetlenia, konwersje, CTR, CPC, ROAS, CPA, CVR`.
- Usunąć metrykę X-em.
- Kliknąć badge korelacji → popup z macierzą.
- Hover na punkt wykresu → tooltip z wartościami wszystkich aktywnych metryk + eventy akcji z tego dnia (pokazuje max 4, potem "+X więcej").
- Zmienić zakres dat w Sidebarze (global date picker) → wykres się przeładowuje.
- Filtrować po typie kampanii / statusie → też z Sidebara.

---

## Co mam WIĘCEJ niż w Google Ads UI

To jest sedno i chce, żeby ads-expert to zobaczył:

1. **Action annotations z before/after nałożone na wykres** — w Google Ads Change History siedzi w osobnej zakładce, nie zobaczysz jej nigdy na wykresie "Performance over time". Tutaj widzę od razu "spadek CTR w środę" i że tego samego dnia ktoś zmienił stawki na 12 keywordach. To jest killer feature, w agencji to by był game changer dla debugowania "co się stało w tym tygodniu".
2. **Pearson correlation jednym kliknięciem na cały dashboard** — w Google Ads musiałbym eksportować dzienne dane do Sheets i liczyć `CORREL()` ręcznie, albo do Looker Studio. Tu mam macierz w popupie.
3. **Dual axis automatyczny** — Google Ads Explorer wymaga ręcznego przełączania metryk na drugą oś. Tutaj widżet sam wykrywa że `CTR + koszt` potrzebuje dwóch osi i włącza.
4. **Tooltip mixujący metryki + akcje w jednym miejscu** — w Google Ads to dwa osobne raporty.
5. **Siostrzany CampaignTrendExplorer (zakładka Kampanie) ma 17 metryk z Search IS / Click Share / Top IS / Abs Top IS / Budget Lost IS / Rank Lost IS** — Google Ads pokazuje te metryki w Auction Insights albo Segments, nigdy razem z kosztem/klikami na jednym wykresie per kampania. Z punktu widzenia całej apki to jest mocny duet: dashboard widok "co się dzieje ogólnie" + Kampanie "dlaczego konkretnie ta jedna spada".

To razem daje fajną rzecz: "co się działo na koncie + co z tego wyszło" w jednym widoku, a per-kampania pogłębiam w drugiej zakładce.

---

## Czego brakuje vs Google Ads

(Per-campaign split świadomie pominięty — jest w zakładce Kampanie → CampaignTrendExplorer, tam pogłębiam analizę konkretnej kampanii z 17 metrykami. To separacja zamierzona, nie brak.)

1. **Brak period-over-period overlay.** W Google Ads zaznaczam "porównaj z poprzednim okresem" i dostaję kropkowaną linię poprzednich 30 dni nałożoną na aktualne. Tu mam osobny WoWChart obok, ale w samym Trend Explorerze nie porównam.
2. **Brak segmentacji po urządzeniu / sieci / płci / godzinie dnia.** W Google Ads Explorer mogę posegmentować wykres kolorami per device. Tu tego nie ma ani w dashboardowym, ani w kampaniowym wariancie.
3. **Brak benchmarku / średniej branży.** Google Ads pokazuje paski "Optimization score" i średnie — tu żadnych punktów odniesienia.
4. **Brak zoom / pan na osi czasu.** Jak mam 90 dni i chcę wyzoomować na 7 dni w okolicach spadku CTR — muszę iść do Sidebara i zmienić range. Nie mogę drag-select na wykresie.
5. **Brak save preset kombinacji metryk.** Codziennie wchodzę i za każdym razem klikam te same metryki (`Koszt, Konwersje, ROAS, CPA`). Powinno się dać to zapisać jako "mój zestaw poranny".
6. **Discoverability drugiego wariantu.** Dashboardowy Trend Explorer nigdzie nie mówi "chcesz per-kampania? wejdź w Kampanie". Pierwszy raz nowy user (ja po dwóch dniach używania) w ogóle nie wie że istnieje CampaignTrendExplorer z 17 metrykami. Ten fakt trzeba komuś powiedzieć, nie da się go odkryć.

---

## Irytacje (pomniejsze rzeczy które mnie drażnią)

- **Limit 5 metryk to za mało.** Chcę jednocześnie `koszt + kliki + konwersje + CTR + CPA + ROAS = 6`. Rozumiem że wykres z 10 liniami to bałagan, ale 6 dałoby radę.
- **Korelacja jest globalna dla całego okresu.** Jak mam 90 dni i w ostatnim tygodniu CPA poleciało razem z konwersjami (zła zmiana stawek), to w korelacji 90-dniowej tego nie widzę bo poprzednie 83 dni mówią co innego. Chciałbym rolling 14-day correlation albo korelację tylko dla widocznego okna.
- **Brak kropek na linii (`dot={false}`).** Jak chcę wskazać konkretny dzień i powiedzieć klientowi "o, tu masz piątek 4.04" — muszę hover, nie widzę punktów. Dla prezentacji to słabe.
- **Action markers to 1 kropka na dzień.** Jak tego dnia było 20 akcji, to widzę jedną kropkę, tooltip pokazuje pierwsze 4 + "+16 więcej". Nie wchodzi się w nic klikalnego, nie ma "Pokaż wszystkie" → muszę iść do Action History i ręcznie filtrować po dacie.
- **Brak klikania w action marker.** Logiczne byłoby: klikam kropkę → otwiera mi się Action History z prefiltrem na ten dzień. Tego nie ma.
- **Tooltip potrafi zasłonić wykres** gdy mam 5 metryk + 3 eventy akcji — robi się duży kafel który zjada pół karty.
- **Banner mock data** jest pomarańczowy — dobrze że jest, ale nie mówi KTÓRE dane są mockowe. Wszystkie? Tylko część? Nie wiem.

---

## Wishlist (co bym chciał dodać)

1. **Period-over-period overlay** — kropkowana linia z poprzedniego okresu (prev 30 / YoY).
2. **Rolling correlation** — korelacja liczona w oknie 14-dniowym, pokazana jako mini-linia pod wykresem głównym. Wtedy widzę KIEDY korelacja się zerwała.
3. **"Co się zmieniło po X?"** — automatyczna analiza delta przed/po action marker. Klikam marker → widżet liczy średnią 7 dni przed vs 7 dni po i pokazuje "CTR -12%, CPA +18%". Tego NIKT nie ma, bo Google Ads tego nie potrafi.
4. **Save preset** — zapamiętaj moje ulubione kombinacje metryk (osobne presety dla Dashboard vs Campaigns).
5. **Zoom brush na osi czasu** — drag-select do zoomu, ESC do resetu.
6. **Forecast ghost line** — prosta ekstrapolacja 7 dni w przód na bazie trendu (nawet linear, byle było).
7. **Klikalne action markery** → deeplink do Action History z prefiltrem na dzień.
8. **Device / network / daypart segmentacja** — chociaż device (mobile vs desktop) jako kolorowe linie. To musi być w obu wariantach.
9. **Cross-link między wariantami** — na dashboardzie Trend Explorer: przycisk/link "Rozbij per kampania" który prowadzi do zakładki Kampanie. I odwrotnie — z CampaignTrendExplorer link "Pokaż na tle całego konta".
10. **Ujednolicić zestaw metryk Dashboard vs Campaigns.** Dashboard ma 9, Campaigns ma 17. Dlaczego Dashboard nie ma Search IS / Click Share? Dla kogoś kto patrzy na całe konto to też ważne.

---

## Pytania do ads-expert

1. Limit **5 metryk** — wystarczy, czy podnieść do 6-7? Z punktu widzenia Google Ads playbooka które metryki są must-have razem?
2. **Globalna korelacja Pearson na całym okresie** — czy to może wprowadzać w błąd przy długich zakresach (stałe trendy vs sezonowość)? Czy rolling correlation to must czy nice-to-have?
3. **Action markery bez klikalności** — czy to blocker do codziennego uzytku, czy da się żyć?
4. **Rozjazd metryk Dashboard (9) vs Campaigns (17)** — czy Dashboard powinien też mieć Search IS / Click Share / Top IS? Czy te metryki mają sens tylko per-kampania?
5. **Discoverability drugiego wariantu** — że CampaignTrendExplorer istnieje na innej zakładce z większym zestawem metryk. Jak to zakomunikować użytkownikowi żeby nie przeoczył?
6. **Period-over-period overlay** — czy to must-have dla review'ów z klientem, czy WoWChart obok wystarcza?
7. **Czy jest coś co w Google Ads UI jest standardem a tutaj tego nie ma i mnie by to zabolało po miesiącu?** (np. segmentacja per conversion action, auction insights overlay, anomaly detection).

---

## Werdykt Marka

**"Wchodzę tu codziennie rano przed kawą."**

Action annotations + correlation popup to dwa powody dla których zostawiam zakładkę otwartą w przeglądarce. Tego nie ma nigdzie indziej. Gdy chcę pogłębić jedną kampanię — mam CampaignTrendExplorer w zakładce Kampanie z 17 metrykami (Search IS, Click Share, Top IS — tych Dashboard nie ma). Duet działa. **Ale** brak period-over-period overlay i discoverability drugiego wariantu to dwie rzeczy które wypychają mnie z powrotem do Google Ads Explorera raz na 2-3 dni.

**Top highlight:** Action annotations z before/after w tooltipie — jedyne miejsce na świecie gdzie widzę "co ktoś zrobił" + "jaki to miało efekt" na jednym ekranie. Plus duet Dashboard + Campaigns Trend Explorer pokrywający "ogólnie" i "per kampania z Auction Insights".
**Top blocker:** Brak period-over-period overlay — dla cotygodniowych przeglądów z klientem "to ostatnie 7 dni vs poprzednie 7 dni" to must-have, a w samym Trend Explorerze go nie ma. Plus nikt mnie nie poinformował że jest druga wersja w Kampaniach — odkryłem ją przypadkiem.
