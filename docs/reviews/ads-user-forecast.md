# ads-user: Forecast (Prognozowanie)

**Tester:** Marek, specjalista Google Ads (6 lat, 8 kont)
**Data:** 2026-03-29
**Klient testowy:** Demo Meble Sp. z o.o.

---

## Co widzę

Zakładka "Prognozowanie" z ciemnym, czytelnym interfejsem. Na górze mam:
- Wybór horyzontu prognozy: 7d / 14d / 30d (pill-buttony)
- Dropdown z listą kampanii (widzę "Branded Search" wybraną)
- Link "Kampanie ->" do szybkiego przejścia
- Pill-buttony metryk: Koszt / Kliknięcia / Konwersje / CTR

Poniżej cztery KPI-karty:
1. **Trend (30 dni)** — procentowa zmiana prognozy vs ostatnie 30 dni (+30.6%, zielony)
2. **Prognoza (Średnia)** — przewidywana dzienna wartość (194.15)
3. **Pewność modelu (R2)** — jakość dopasowania (0.03 z badge "LOW", czerwony)
4. **Slope (Wzrost/Dzień)** — tempo zmiany dziennej (0.77 jednostek)

Na dole wykres — linia niebieska (dane historyczne, ~60 dni), linia zielona przerywana (prognoza na kolejne 30 dni), widoczny zielony band przedziału ufności.

---

## Co mogę zrobić

- Przełączać horyzont prognozy (7/14/30 dni)
- Zmieniać kampanię z dropdowna
- Przełączać metrykę (koszt, kliknięcia, konwersje, CTR)
- Odczytać trend procentowy i kierunek
- Zobaczyć pewność modelu (R2) i ocenić czy prognoza jest wiarygodna
- Przejść do widoku kampanii jednym kliknięciem
- Najechać na punkty wykresu i zobaczyć tooltip z wartościami

---

## Co daje więcej niż Google Ads

1. **Prostota** — Google Ads ma "Performance Planner", ale to ciężkie narzędzie, wymaga konfiguracji scenariuszy budżetowych. Tu dostaję prognozę od ręki, jednym kliknięciem.
2. **Pewność modelu (R2)** — Google Ads nie mówi mi wprost "ta prognoza jest słaba". Tu widzę badge "LOW" przy R2=0.03 i od razu wiem, że to niemal losowe dopasowanie — to uczciwe.
3. **Granularność per kampania** — Performance Planner działa na poziomie grup kampanii / budżetów. Tu wybieram jedną kampanię i widzę jej prognozę izolowaną.
4. **Slope per day** — nigdzie w Google Ads nie zobaczę "o ile jednostek dziennie rośnie metryka". Przydatne do szybkiej oceny dynamiki.
5. **Przedział ufności na wykresie** — zielony band CI jest fajny wizualnie, od razu widzę, jak szeroki jest rozrzut predykcji.

---

## Brakuje vs Google Ads

1. **Brak scenariuszy "what-if"** — Performance Planner pozwala zadać pytanie "co jeśli zwiększę budżet o 20%?". Tu nie mogę symulować zmian budżetu/stawek i zobaczyć ich wpływu na prognozę. To KLUCZOWA różnica.
2. **Brak prognozy na poziomie konta/grupy kampanii** — mogę wybrać tylko jedną kampanię. Nie widzę zagregowanej prognozy dla całego konta lub wybranego podzbioru kampanii.
3. **Brak prognozy ROAS / CPA** — mam koszt, kliknięcia, konwersje i CTR, ale brakuje ROAS i CPA, które są kluczowe dla e-commerce i lead-gen.
4. **Brak prognozy budżetowej** — "czy mój miesięczny budżet się wyczerpie?" / "kiedy osiągnę limit?" — takiego sygnału tu nie ma.
5. **Brak prognozy sezonowej** — model liniowy nie uwzględnia sezonowości. Dla e-commerce (Black Friday, Boże Narodzenie) to poważny brak. Performance Planner przynajmniej próbuje to modelować.
6. **Brak porównania prognoza vs rzeczywistość** — nie widzę, jak trafne były poprzednie prognozy. Brak historii trafności (accuracy tracking).
7. **Brak alertów prognostycznych** — "prognoza wskazuje, że koszty wzrosną o 30% — rozważ korektę budżetu" — takiego actionable insightu nie ma.

---

## Irytuje

1. **R2 = 0.03 a prognoza i tak się wyświetla z pełną powagą** — mam zielony "+30.6%" i "194.15 średnia dzienna" wyświetlone dużym fontem, jakby to były wiarygodne dane, a tymczasem model ma R2 praktycznie zerowe. To niebezpieczne — ktoś mniej uważny podejmie decyzje na podstawie śmieci. Powinno być wyraźne ostrzeżenie typu "prognoza niewiarygodna — za mało danych / zbyt losowy wzorzec".
2. **"Slope" i "R2" to terminy techniczne** — PPC-owiec nie jest data scientistem. "Slope" nic mu nie mówi. Lepiej: "Zmiana dzienna" lub "Tempo wzrostu". "R2" mogłoby być zastąpione przez "Trafność prognozy" z opisem ludzkim (wysoka/średnia/niska).
3. **Brak jednostek przy KPI** — "Prognoza (Średnia): 194.15" — 194.15 CZEGO? Złotych? Kliknięć? Muszę pamiętać, jaką metrykę wybrałem. Powinno pisać "194.15 PLN" lub "194.15 kliknięć".
4. **Brak filtra typu kampanii w samym widoku** — w sidebarze mam filtry Search/PMax/Shopping, ale dropdown kampanii nie filtruje po typie. Jeśli mam 50 kampanii, muszę scrollować cały dropdown.
5. **Model liniowy — zbyt prosty** — napisane jest "(model liniowy)". Dla kampanii z sezonowością, weekendowymi wzorcami, czy zmianami budżetowymi — prosta regresja liniowa jest praktycznie bezużyteczna. Przynajmniej moving average czy ARIMA byłyby sensowniejsze.
6. **Wykres nie rozróżnia wizualnie przejścia historia->prognoza** — jest zmiana z ciągłej na przerywaną linię, ale brakuje wyraźnej linii separatora "dziś" albo pionowej kreski dzielącej okresy.

---

## Chciałbym

1. **Ostrzeżenie przy niskim R2** — poniżej 0.3 wyświetlaj baner: "Prognoza ma niską pewność — traktuj wyłącznie orientacyjnie". Najlepiej zbluruj lub wyszarz KPI karty.
2. **Jednostki przy wartościach** — "194.15 PLN/dzień" albo "194.15 klik./dzień" — kontekst metryki przy liczbie.
3. **Scenariusze budżetowe** — suwak "budżet +/- 20%" z dynamicznym przeliczeniem prognozy. Nawet uproszczony byłby cenny.
4. **Prognoza sumaryczna (konto)** — obok dropdown kampanii: opcja "Wszystkie kampanie" z zagregowaną prognozą.
5. **Dodatkowe metryki: ROAS, CPA** — kluczowe dla decyzji biznesowych.
6. **Linia "DZIŚ"** — pionowa linia na wykresie oddzielająca historię od prognozy, najlepiej z etykietą.
7. **Prognoza budżetowa** — "przy obecnym tempie budżet wyczerpie się dnia X" / "zostanie Y% budżetu na koniec miesiąca".
8. **Trafność historyczna** — mały wskaźnik "poprzednia prognoza 7d trafiła z dokładnością 85%" — buduje zaufanie do narzędzia.
9. **Lepszy model** — chociaż opcja wyboru: "regresja liniowa" vs "średnia krocząca" vs "sezonowy". Nie musi być ML, wystarczy coś co łapie wzorce tygodniowe.
10. **Eksport prognozy** — CSV z prognozą do wklejenia w raport dla klienta.

---

## Verdykt

**5/10** — Zakładka działa, wygląda ładnie i jest szybka. Ale jako specjalista Google Ads muszę być szczery: **w obecnej formie to gadżet, nie narzędzie do podejmowania decyzji**. Główne problemy:

- Model liniowy z R2=0.03 generuje prognozy, które wyglądają wiarygodnie, ale nimi nie są. To najgorszy scenariusz — narzędzie, które wygląda profesjonalnie, ale może prowadzić do złych decyzji.
- Brak scenariuszy "what-if" sprawia, że nie zastąpi Performance Plannera w żadnym przypadku użycia, w którym klient pyta "co jeśli zwiększę budżet?".
- Brakuje kontekstu (jednostek, ostrzeżeń, linii "dziś") który odróżnia narzędzie użyteczne od ładnej wizualizacji.

**Potencjał jest** — bo idea prostej, szybkiej prognozy per kampania to coś, czego brakuje w Google Ads. Ale wymaga: (1) uczciwego komunikowania niepewności, (2) przynajmniej jednego scenariusza what-if, (3) kontekstu metryki przy wartościach.

---

## Pytania @ads-expert

1. Czy model liniowy w ogóle ma sens dla danych Google Ads, które z natury są cykliczne (weekendy, miesiące) i szumowe? Jaki model byłby minimum viable?
2. Czy warto pokazywać prognozę przy R2 < 0.2? Może lepiej wyświetlić "brak wystarczających danych do prognozy" zamiast wprowadzać w błąd?
3. Czy scenariusze budżetowe (what-if) da się sensownie zaimplementować bez dostępu do Google Ads Performance Planner API? Jest tam `planning_service` w API — czy to jest opcja?
4. Prognoza na poziomie konta (zagregowana) — sumować prognozy per kampania, czy robić osobny model na zagregowanych danych?
5. Czy forecast powinien uwzględniać zmiany stawek/budżetów z historii (np. "2 tygodnie temu podniesiono budżet o 50%") jako zmienną objaśniającą?
6. Jak traktować kampanie z <30 dni danych? Czy 60 dni historii (domyślna) to wystarczająca baza?
