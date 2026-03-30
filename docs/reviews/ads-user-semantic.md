# Ads User Review: Klastry Semantyczne (Inteligencja Semantyczna)

**Reviewer:** Marek, specjalista Google Ads (6 lat, 8 kont)
**Data:** 2026-03-29
**Klient testowy:** Demo Meble Sp. z o.o.
**Zakres dat:** 30 dni

---

## Co widzę

Zakładka "Klastry Semantyczne" — lista tematycznych grup wyszukiwanych fraz, pogrupowanych automatycznie po sensie semantycznym (nie po słowach kluczowych w kampanii, ale po wpisywanych frazach). Widzę:

1. **Nagłówek z metrykami sumarycznymi** — "Zgrupowano 24 wyrażeń w 9 klastrów tematycznych" — od razu wiem jaka jest skala.
2. **Filtr kosztu** — progi: Wszystkie / >10 zł / >50 zł / >100 zł — mogę szybko odfiltrować drobnicę.
3. **Wyszukiwarka** w klastrach — szukam po nazwie klastra lub po frazie wewnątrz.
4. **Lista klastrów** — każdy wiersz pokazuje:
   - Nazwa klastra (najlepsza fraza z grupy)
   - Ile wyrażeń w klastrze + ile kliknięć
   - Koszt sumaryczny (zł)
   - Konwersje (z 1 decymalnym)
   - Strzałka do rozwinięcia
5. **Rozwinięty klaster** — widzę "chipsy" z frazami, każdy z kosztem. Hover pokazuje detale (koszt, kliknięcia).
6. **is_waste marker** — klastry oznaczone jako "Potencjalna strata" (czerwony badge) — koszt >100 zł i 0 konwersji.
7. **Akcja: "Dodaj jako negatywy"** — przycisk per klaster waste, dodaje wszystkie frazy jako EXACT negative.
8. **Bulk select + floating action bar** — checkboxy na klastrach waste, na dole sticky bar z "Wyklucz wszystkie".

## Co moge zrobic

- Filtrować klastry po progu kosztu (4 progi).
- Szukać konkretnych fraz/klastrów.
- Rozwinąć klaster zeby zobaczyc frazy wewnatrz.
- Dodac caly klaster jako negatywy EXACT (per klaster).
- Zaznaczyc wiele waste-klastrow i wyklucz hurtowo przez floating bar.
- Zmieniac zakres dat (globalny filtr 30 dni w sidebarze).

## Wiecej niz Google Ads

To jest **killer feature** — w Google Ads nic takiego nie istnieje. Google Ads daje mi:

- Search Terms report — plaska lista fraz, zero grupowania
- Moge recznie sortowac/filtrowac, ale nigdy nie zobacze "te 5 fraz dotyczy tego samego tematu i razem kosztowaly 3400 zł"
- Muszę manualnie w Excelu robic n-gramy albo uzywac zewnetrznych narzedzi (np. PPC Samurai, Optmyzr) zeby dostac cokolwiek podobnego

Tutaj mam:
1. **Automatyczne grupowanie semantyczne** (SentenceTransformer + AgglomerativeClustering) — to nie proste n-gramy, to prawdziwe zrozumienie sensu
2. **Waste detection** — algorytm sam wskazuje klastry z kosztem >100 zł i 0 konwersji
3. **One-click negative exclusion** — z klastra prosto do negatywow, bez kopiowania do arkusza
4. **Bulk exclusion** — zaznacz kilka klastrow, wyklucz jednym klikiem

W Google Ads UI musialby to zrobic tak: eksport search terms -> Excel -> reczne grupowanie -> identyfikacja waste -> reczne dodawanie negatywow -> 2-3h roboty. Tu mam to w 30 sekund.

## Brakuje vs Google Ads

1. **Brak filtra po kampanii/grupie reklam** — nie moge zobaczyc klastrow tylko dla jednej kampanii. W GAds moge filtrowac search terms per kampania. Tutaj globalny filtr campaignType z sidebara NIE jest przekazywany do API `/semantic/clusters`.
2. **Brak match type choice** — negatywy dodawane zawsze jako EXACT. Czasem chce PHRASE albo BROAD. W GAds mam wybor.
3. **Brak informacji o CTR/CPC per klaster** — widzę koszt i konwersje, ale nie widzę sreniego CPC ani CTR klastra. W search terms report w GAds mam te metryki.
4. **Brak CPA/ROAS per klaster** — dla klastrow z konwersjami nie widze kosztu konwersji. To klucz do oceny efektywnosci.
5. **Brak informacji o obecnych negatywach** — nie wiem czy frazy z klastra sa juz wykluczone. Moge dodac duplikat.
6. **Brak historii akcji** — po dodaniu negatywow nie mam potwierdzenia w UI co dokladnie zostalo dodane. Toast znika.
7. **Brak eksportu** — nie moge wyeksportowac klastrow do CSV/Excela zeby omowic z klientem.

## Irytuje

1. **Nazewnictwo klastrow** — nazwy to po prostu najlepsza fraza z grupy. Klaster "demo meble sklep" albo "lozko drewniane do sypialni" — ok, ale nie jest to *nazwa tematyczna*. Wolalbym "Meble ogolne", "Lozka drewniane", "Narożniki". Przy wiekszej liczbie klastrow trudno sie orientowac.
2. **Brak sortowania** — nie moge posortowac klastrow po konwersjach, po liczbie fraz, po impressions. Zawsze sortowane po koszcie malejaco.
3. **Waste heuristic jest prostacki** — koszt >100 zł i 0 konwersji. A co z klastrem za 95 zł z 0 konwersji? Albo klastrem za 2000 zł z 0.5 konwersji (tez waste!)? Progi powinny byc konfigurowalne albo algorytm bardziej zaawansowany (CPA threshold).
4. **Brak informacji o impressions share** — nie wiem czy klaster to duzy temat czy niszowy.
5. **Brak paginacji** — jesli bedzie 100+ klastrow, strona bedzie bardzo dluga.
6. **Rozwiniety klaster — brak sortowania chipow** — frazy w chipsach nie sa posortowane po koszcie. Chce widziec najdrozsze na gorze.
7. **Negatywy scope: CAMPAIGN** — w kodzie hardcoded, ale nie wiadomo *ktora* kampania. Powinna byc opcja: campaign vs account level.

## Chcialbym

1. **Filtr po kampanii** — "Pokaz klastry tylko z kampanii Search Meble 2026". Podpiecie do globalnego FilterContext (campaignType przynajmniej).
2. **CPA/ROAS w metrykach klastra** — kolumna CPA (koszt/konwersje) i ROAS (conversion_value/koszt).
3. **Konfigurowalne progi waste** — slider: "Oznacz jako waste jesli koszt > X i konwersje < Y".
4. **Lepsze nazwy klastrow** — moze LLM streszczenie? Albo przynajmniej n-gram z fraz zamiast jednej frazy.
5. **Sortowanie klastrow** — dropdown: po koszcie, konwersjach, CPA, liczbie fraz.
6. **Eksport do CSV** — klastry z frazami, metryki, status waste.
7. **Podglad negatywow juz istniejacych** — ikona/badge jesli fraza jest juz na liscie negatywow.
8. **Match type picker przy wykluczaniu** — EXACT / PHRASE / BROAD.
9. **Sparkline trendu kosztow** — mini wykres jak klaster rosnie/maleje w czasie.
10. **Porownanie okresow** — klaster ktory w tym miesiacu kosztuje 2x wiecej niz w poprzednim.

## Verdykt

**8/10** — To jest jedna z najlepszych zakladek w aplikacji. Robi cos, czego Google Ads UI w ogole nie oferuje. Semantyczne grupowanie search terms + waste detection + one-click exclusion — to jest realna wartosc. PPCowiec oszczedza godziny pracy.

Ale:
- Brak filtra po kampanii to duzy minus dla kont z wieloma kampaniami.
- Brak CPA/ROAS sprawia ze nie widze pelnego obrazu efektywnosci.
- Waste heuristic jest zbyt uproszczony — moze dawac false negatives.
- Match type EXACT only ogranicza przydatnosc akcji wykluczania.

Mimo to — zakladka juz teraz jest uzyteczna w codziennej pracy. Moglaby byc "gwiazdą" aplikacji po dopracowaniu metryk i filtrow.

## Pytania @ads-expert

1. Czy algorytm clusteringu (all-MiniLM-L6-v2 + AgglomerativeClustering, distance_threshold=1.0) jest optymalny dla polskich fraz e-commerce? Czy nie lepiej uzyc multilingual model?
2. Czy waste heuristic (cost >100 + conv=0) ma sens? Jaki powinien byc threshold? Moze % budzetu?
3. Czy negatywy EXACT sa zawsze poprawne? Kiedy PHRASE bylby lepszy?
4. Jak powinno wygladac filtrowanie po kampanii — osobne klastry per kampania czy jeden widok z filterem?
5. Czy brakuje tu jakis metryk, ktore ekspert uwaza za krytyczne (Quality Score kontekstu, impression share)?
6. Czy klastry powinny miec sugerowane akcje poza "wyklucz"? Np. "rozbuduj ten temat" dla klastrow z dobrym CPA?
