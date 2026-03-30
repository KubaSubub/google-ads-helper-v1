# Mapa Aplikacji — Google Ads Helper v1

Mapa funkcjonalnosci z perspektywy specjalisty Google Ads.
Otwórz w VS Code z rozszerzeniem "Markdown Preview Mermaid Support" lub wklej na [mermaid.live](https://mermaid.live).

---

## 1. Co robi aplikacja — widok z lotu ptaka

```mermaid
graph TB
    subgraph GADS["Google Ads API"]
        API_DATA["Dane konta:<br/>kampanie, grupy reklamowe,<br/>slowa kluczowe, wyszukiwania,<br/>metryki dzienne, konwersje,<br/>auction insights, change history"]
    end

    subgraph APP["Google Ads Helper"]
        SYNC["Synchronizacja<br/>pobiera dane z konta<br/>za ostatnie 90 dni"]
        ANALYSIS["Silnik analityczny<br/>50+ analiz automatycznych"]
        RECO["Silnik rekomendacji<br/>generuje zalecenia optymalizacyjne"]
        RULES["Reguly automatyczne<br/>warunki + akcje cykliczne"]
        ACTIONS["Wykonywanie zmian<br/>z mozliwoscia cofniecia"]
        AI["Asystent AI<br/>raporty + chat"]
    end

    subgraph USER["Specjalista Google Ads"]
        DASH_U["Przeglada dashboard"]
        OPTIM["Optymalizuje kampanie"]
        REPORT["Generuje raporty"]
        MONITOR["Monitoruje anomalie"]
    end

    API_DATA -->|sync co X godzin| SYNC
    SYNC --> ANALYSIS
    ANALYSIS --> RECO
    RECO --> ACTIONS
    ACTIONS -->|mutacje przez API| API_DATA
    RULES -->|automatycznie| ACTIONS

    DASH_U --> ANALYSIS
    OPTIM --> RECO
    OPTIM --> ACTIONS
    REPORT --> AI
    MONITOR --> ANALYSIS
```

---

## 2. Zakladki aplikacji — co gdzie znajdziesz

```mermaid
graph LR
    subgraph MONITORING["Monitoring konta"]
        DASH["Dashboard<br/>━━━━━━━━━━━━━<br/>Health Score konta<br/>KPI: koszty, klikniecia, konwersje, ROAS<br/>Porownanie tydzien do tygodnia<br/>Trendy kampanii<br/>Budget pacing<br/>Udzial w wyswietleniach<br/>Zmarnowany budzet<br/>Ostatnie akcje"]
        ALERTS["Alerty<br/>━━━━━━━━━━━━━<br/>Anomalie w metrykach<br/>Spadki CTR, wzrosty CPA<br/>Przekroczenia budzetowe<br/>Z-score detection"]
    end

    subgraph KAMPANIE["Zarzadzanie kampaniami"]
        CAMP["Kampanie<br/>━━━━━━━━━━━━━<br/>Lista kampanii z KPI<br/>Filtrowanie: typ, status<br/>Edycja budzetow i stawek<br/>Target CPA / Target ROAS<br/>Trendy per kampania<br/>Historia zmian"]
        XCAM["Cross-Campaign<br/>━━━━━━━━━━━━━<br/>Nakladanie sie slow kluczowych<br/>Alokacja budzetow<br/>Porownanie kampanii"]
        PMAX["Performance Max<br/>━━━━━━━━━━━━━<br/>Kanaly PMax<br/>Asset groups<br/>Search themes<br/>Kanibalizacja Search vs PMax"]
        DSA["DSA<br/>━━━━━━━━━━━━━<br/>Cele DSA + wydajnosc<br/>Pokrycie tematyczne<br/>Naglowki dynamiczne<br/>Nakladanie z Search"]
        SHOP["Shopping<br/>━━━━━━━━━━━━━<br/>Grupy produktowe<br/>Wydajnosc per grupa"]
        DISP["Display<br/>━━━━━━━━━━━━━<br/>Placements<br/>Tematy<br/>Wykluczenia"]
        VIDEO["Video<br/>━━━━━━━━━━━━━<br/>Metryki kampanii video"]
    end

    subgraph SLOWA["Slowa kluczowe i wyszukiwania"]
        KW["Slowa kluczowe<br/>━━━━━━━━━━━━━<br/>Lista ze Quality Score<br/>Metryki dzienne<br/>Negatywne slowa<br/>Listy wykluczajace<br/>Propozycje nowych slow"]
        ST["Wyszukiwania<br/>━━━━━━━━━━━━━<br/>Search terms z segmentacja<br/>TOP / WASTE / NEW / LONG TAIL<br/>Dodawanie jako negatywne<br/>Trendy wyszukiwan"]
        SEM["Klastry semantyczne<br/>━━━━━━━━━━━━━<br/>Grupowanie wyszukiwan NLP<br/>Tematy + intencje<br/>Masowe wykluczanie"]
    end

    subgraph OPTYMALIZACJA["Optymalizacja"]
        REC["Rekomendacje<br/>━━━━━━━━━━━━━<br/>Zalecenia optymalizacyjne<br/>Priorytetyzacja + scoring<br/>Zastosuj jednym klikiem<br/>Bulk apply per kategoria<br/>Odrzucanie nieistotnych"]
        QS["Quality Score<br/>━━━━━━━━━━━━━<br/>Audyt QS per slowo<br/>Trafnosc reklamy<br/>Jakosc strony docelowej<br/>Oczekiwany CTR"]
        AUDIT["Audit Center<br/>━━━━━━━━━━━━━<br/>25+ sekcji audytowych:<br/>Wasted spend, Dayparting<br/>Match types, N-gramy<br/>RSA analiza, Landing pages<br/>Smart Bidding health<br/>Pareto 80/20, Skalowanie<br/>Demografia, Audiences<br/>Rozszerzenia reklam<br/>Target vs Actual"]
        RULES_P["Reguly automatyczne<br/>━━━━━━━━━━━━━<br/>Warunki: CPA > X, CTR < Y<br/>Akcje: pauza, zmiana stawki<br/>Dry-run przed wykonaniem<br/>Log wykonan"]
        FORE["Prognoza<br/>━━━━━━━━━━━━━<br/>Forecast per kampanie<br/>Metryka: clicks, cost, conv<br/>Przedzial ufnosci"]
    end

    subgraph KONKURENCJA["Analiza konkurencji"]
        COMP["Auction Insights<br/>━━━━━━━━━━━━━<br/>Udzial w aukcjach<br/>Overlap rate<br/>Position above rate"]
        BENCH["Benchmarki<br/>━━━━━━━━━━━━━<br/>Porownanie z branza<br/>Porownanie miedzy klientami"]
    end

    subgraph RAPORTY["Raportowanie"]
        REP["Raporty AI<br/>━━━━━━━━━━━━━<br/>Raport miesieczny<br/>Raport tygodniowy<br/>Raport zdrowia konta<br/>Generowane przez Claude"]
        HIST["Historia akcji<br/>━━━━━━━━━━━━━<br/>Log wszystkich zmian<br/>Cofanie akcji<br/>Timeline: zmiany + Google"]
        EXP["Eksport<br/>━━━━━━━━━━━━━<br/>CSV / XLSX<br/>Kampanie, slowa, wyszukiwania<br/>Rekomendacje, Quality Score"]
    end

    subgraph USTAWIENIA["Konfiguracja"]
        SET["Ustawienia klienta<br/>━━━━━━━━━━━━━<br/>Nazwa, branza, cele<br/>Strategia licytacji<br/>Limity bezpieczenstwa<br/>Reguly biznesowe"]
        AGENT_P["Czat z AI<br/>━━━━━━━━━━━━━<br/>Pytania o konto<br/>Analiza na zadanie"]
    end
```

---

## 3. Cykl pracy specjalisty — dzien z zycia PPCowca

```mermaid
graph TD
    subgraph RANO["Poranek — przeglad konta"]
        A1["Otworz Dashboard"] --> A2["Sprawdz Health Score"]
        A2 --> A3["Przejrzyj alerty i anomalie"]
        A3 --> A4{Cos sie pali?}
        A4 -->|Tak| A5["Przejdz do kampanii / slow kluczowych"]
        A4 -->|Nie| A6["Sprawdz budget pacing"]
    end

    subgraph OPTYM["Optymalizacja — glowna praca"]
        B1["Otworz Rekomendacje"] --> B2["Przejrzyj priorytetowe zalecenia"]
        B2 --> B3["Zastosuj / odrzuc rekomendacje"]
        B3 --> B4["Otworz Search Terms"]
        B4 --> B5["Przejrzyj segmenty: WASTE, NEW"]
        B5 --> B6["Dodaj negatywne slowa kluczowe"]
        B6 --> B7["Sprawdz Quality Score"]
        B7 --> B8["Otworz Audit Center"]
        B8 --> B9["Przeanalizuj 25+ sekcji audytu"]
    end

    subgraph ZAAWAN["Zaawansowane — co tydzien"]
        C1["Cross-Campaign: overlap slow"]
        C2["Auction Insights: konkurencja"]
        C3["Benchmarki: porownanie z branza"]
        C4["Prognoza: co bedzie za 30 dni"]
        C5["Reguly automatyczne: setup"]
    end

    subgraph RAPORT["Raportowanie — koniec tygodnia"]
        D1["Wygeneruj raport AI"] --> D2["Przejrzyj historie akcji"]
        D2 --> D3["Eksport danych do XLSX"]
    end

    A5 --> OPTYM
    A6 --> OPTYM
    OPTYM --> ZAAWAN
    ZAAWAN --> RAPORT
```

---

## 4. Skad biora sie dane — pipeline synchronizacji

```mermaid
sequenceDiagram
    participant PPC as Specjalista PPC
    participant APP as Aplikacja
    participant GADS as Google Ads API

    PPC->>APP: Kliknij "Synchronizuj" (lub automatycznie co X h)

    Note over APP,GADS: Pobieranie danych za ostatnie 90 dni

    APP->>GADS: Pobierz kampanie (Search, PMax, Shopping, DSA, Display, Video)
    GADS-->>APP: Kampanie + budzety + strategie licytacji

    APP->>GADS: Pobierz grupy reklamowe + reklamy
    GADS-->>APP: Ad groups + RSA headlines/descriptions + status zatwierdzenia

    APP->>GADS: Pobierz slowa kluczowe + Quality Score
    GADS-->>APP: Slowa + match type + QS + bid + impression share

    APP->>GADS: Pobierz metryki dzienne (clicks, impressions, cost, conversions)
    GADS-->>APP: MetricDaily per kampania + KeywordDaily per slowo

    APP->>GADS: Pobierz wyszukiwania (search terms)
    GADS-->>APP: Search terms + metryki + kampania/grupa zrodlowa

    APP->>GADS: Pobierz segmenty (device, geo, hour, audience)
    GADS-->>APP: Metryki per segment

    APP->>GADS: Pobierz auction insights, change history, audiences, extensions
    GADS-->>APP: Dane konkurencji + historia zmian + grupy odbiorcow

    Note over APP: Dane zapisane lokalnie — analizy dzialaja offline

    APP->>APP: Uruchom 50+ analiz automatycznych
    APP->>APP: Wygeneruj rekomendacje optymalizacyjne
    APP->>APP: Wykryj anomalie (Z-score)

    APP-->>PPC: Dashboard gotowy — Health Score, KPI, alerty
```

---

## 5. Jak dzialaja rekomendacje i akcje

```mermaid
sequenceDiagram
    participant PPC as Specjalista PPC
    participant APP as Silnik rekomendacji
    participant GADS as Google Ads API

    Note over APP: Silnik analizuje lokalne dane

    APP->>APP: Sprawdz wasted spend (search terms z kosztami bez konwersji)
    APP->>APP: Sprawdz Quality Score < 5
    APP->>APP: Sprawdz brakujace rozszerzenia reklam
    APP->>APP: Sprawdz nierownomierny podzial budzetow
    APP->>APP: Sprawdz nakładajace sie slowa kluczowe
    APP->>APP: Sprawdz strategie licytacji (learning, target vs actual)
    APP->>APP: ...i 20+ innych regul

    APP-->>PPC: Lista rekomendacji (posortowana wg priorytetu + impact)

    PPC->>APP: "Zastosuj rekomendacje #12: dodaj negatywne slowo"

    APP->>GADS: Mutacja: dodaj negative keyword "darmowe" do kampanii X
    GADS-->>APP: OK — zmiana zastosowana

    APP->>APP: Zapisz w historii: co zmieniono, stara wartosc, nowa wartosc

    Note over PPC: Za tydzien — efekty nie takie jak oczekiwano?

    PPC->>APP: "Cofnij akcje #12"
    APP->>GADS: Mutacja: usun negative keyword "darmowe" z kampanii X
    GADS-->>APP: OK — zmiana cofnieta
```

---

## 6. Audit Center — co dokladnie sprawdza

```mermaid
mindmap
  root(("Audit Center<br/>25+ analiz"))
    Budzet i koszty
      Wasted Spend<br/>frazy bez konwersji ktore generuja koszty
      Budget Pacing<br/>tempo wydawania vs plan miesieczny
      Pareto 80/20<br/>ktore 20% kampanii generuje 80% wynikow
      Scaling Opportunities<br/>kampanie z przestrzenia do skalowania
    Slowa kluczowe
      Match Type Analysis<br/>rozklad broad/phrase/exact i wydajnosc
      N-gram Analysis<br/>najczestsze frazy w wyszukiwaniach
      Close Variants<br/>jak Google interpretuje Twoje slowa
      Keyword Expansion<br/>propozycje nowych slow z search terms
    Reklamy
      RSA Analysis<br/>sila reklam, kombinacje naglowkow
      Landing Pages<br/>bounce rate i konwersje per strona
      Missing Extensions<br/>jakich rozszerzen brakuje
      Extension Performance<br/>CTR i konwersje per rozszerzenie
    Czas i miejsce
      Dayparting<br/>wydajnosc per godzina i dzien tygodnia
      Hourly Heatmap<br/>mapa cieplna godzin
      Device Breakdown<br/>mobile vs desktop vs tablet
      Geo Breakdown<br/>wydajnosc per lokalizacja
      Demographics<br/>wiek, plec, dochod
    Licytacje
      Smart Bidding Health<br/>czy strategie automatyczne dzialaja
      Target vs Actual<br/>target CPA/ROAS vs rzeczywistosc
      Learning Status<br/>kampanie w fazie uczenia
      Portfolio Health<br/>przeglad strategii portfolio
      Bid Modifiers<br/>korekty stawek: device, geo, audience
      Bidding Advisor<br/>sugestie zmiany strategii
    Struktura konta
      Account Structure<br/>kampanie, grupy, slowa — proporcje
      Ad Group Health<br/>rozmiar grup, pokrycie reklam
      Audience Performance<br/>wydajnosc grup odbiorcow
    Konwersje
      Conversion Quality<br/>wartosc i jakosc konwersji
      Conversion Value Rules<br/>reguly wartosci konwersji
      Offline Conversions<br/>import konwersji offline
    Konkurencja
      Google Recommendations<br/>zalecenia natywne z Google Ads
      PMax Cannibalization<br/>czy PMax kradnie ruch Search
```

---

## 7. Typy kampanii — co aplikacja obsluguje

```mermaid
graph TB
    subgraph SEARCH["Search Campaigns"]
        S1["Slowa kluczowe + Quality Score"]
        S2["Grupy reklamowe + RSA"]
        S3["Wyszukiwania + negatywne"]
        S4["Metryki dzienne"]
        S5["Rozszerzenia reklam"]
        S6["Auction Insights"]
    end

    subgraph PMAX_C["Performance Max"]
        P1["Asset Groups + assety"]
        P2["Kanaly: Search, Display, Video, Discovery, Gmail, Maps"]
        P3["Search Themes"]
        P4["Kanibalizacja z Search"]
        P5["Channel-level metrics"]
    end

    subgraph DSA_C["Dynamic Search Ads"]
        D1["Cele DSA (URL targets)"]
        D2["Dynamiczne naglowki"]
        D3["Pokrycie tematyczne"]
        D4["Nakladanie z Search campaigns"]
    end

    subgraph SHOPPING_C["Shopping"]
        SH1["Grupy produktowe"]
        SH2["Wydajnosc per grupa"]
    end

    subgraph DISPLAY_C["Display"]
        DI1["Placements + wykluczenia"]
        DI2["Tematy"]
        DI3["Grupy odbiorcow"]
    end

    subgraph VIDEO_C["Video"]
        V1["Metryki kampanii video"]
    end

    subgraph WSPOLNE["Wspolne dla wszystkich typow"]
        W1["Budget pacing"]
        W2["Strategie licytacji"]
        W3["Device / Geo / Time segmentacja"]
        W4["Historia zmian"]
        W5["Rekomendacje"]
        W6["Reguly automatyczne"]
    end

    SEARCH --> WSPOLNE
    PMAX_C --> WSPOLNE
    DSA_C --> WSPOLNE
    SHOPPING_C --> WSPOLNE
    DISPLAY_C --> WSPOLNE
    VIDEO_C --> WSPOLNE
```

---

## 8. Struktura danych — co aplikacja przechowuje

```mermaid
erDiagram
    KLIENT ||--o{ KAMPANIA : "zarzadza"
    KLIENT ||--o{ SLOWO_NEGATYWNE : "posiada"
    KLIENT ||--o{ LISTA_WYKLUCZAJACA : "posiada"
    KLIENT ||--o{ ALERT : "otrzymuje"
    KLIENT ||--o{ REKOMENDACJA : "otrzymuje"
    KLIENT ||--o{ REGULA : "konfiguruje"
    KLIENT ||--o{ RAPORT : "generuje"

    KAMPANIA ||--o{ GRUPA_REKLAMOWA : "zawiera"
    KAMPANIA ||--o{ METRYKA_DZIENNA : "mierzona przez"
    KAMPANIA ||--o{ WYSZUKIWANIE : "generuje"
    KAMPANIA ||--o{ ASSET_GROUP : "PMax"

    GRUPA_REKLAMOWA ||--o{ SLOWO_KLUCZOWE : "zawiera"
    GRUPA_REKLAMOWA ||--o{ REKLAMA : "zawiera"

    SLOWO_KLUCZOWE ||--o{ METRYKA_SLOWA : "dzienne dane"

    REKOMENDACJA ||--o{ LOG_AKCJI : "wykonana przez"

    KLIENT {
        string Google_Customer_ID
        string Nazwa
        string Branza
        string Strategia
    }

    KAMPANIA {
        string Nazwa
        string Typ "Search / PMax / Shopping / DSA / Display / Video"
        string Status "Enabled / Paused / Removed"
        money Budzet_dzienny
        money Target_CPA
        float Target_ROAS
        string Strategia_licytacji
    }

    GRUPA_REKLAMOWA {
        string Nazwa
        string Status
        money Max_CPC
    }

    SLOWO_KLUCZOWE {
        string Tekst
        string Match_Type "Broad / Phrase / Exact"
        int Quality_Score "1-10"
        float Oczekiwany_CTR "Below / Average / Above"
        float Trafnosc_reklamy "Below / Average / Above"
        float Jakosc_landing "Below / Average / Above"
        money Stawka
        float Impression_Share
    }

    METRYKA_SLOWA {
        date Data
        int Klikniecia
        int Wyswietlenia
        money Koszt
        float Konwersje
        money Wartosc_konwersji
    }

    METRYKA_DZIENNA {
        date Data
        int Klikniecia
        int Wyswietlenia
        money Koszt
        float Konwersje
        float ROAS
        float Search_Impression_Share
        float Search_Top_IS
        float Lost_IS_Budget
    }

    WYSZUKIWANIE {
        string Fraza
        int Klikniecia
        int Wyswietlenia
        money Koszt
        float Konwersje
        string Segment "TOP / WASTE / NEW / LONG_TAIL"
    }

    REKLAMA {
        string Typ "RSA / ETA / DSA"
        string Naglowki "do 15 naglowkow RSA"
        string Opisy "do 4 opisow RSA"
        string Status_zatwierdzenia
        string Landing_page
    }

    REKOMENDACJA {
        string Kategoria "budget / keyword / bid / negative / extension / ..."
        string Priorytet "critical / high / medium / low"
        string Status "pending / applied / dismissed"
        string Zrodlo "engine / google_native"
        money Szacowany_impact
    }

    LOG_AKCJI {
        string Typ_akcji "add_negative / change_bid / pause_campaign / ..."
        string Status "success / failed / reverted"
        json Stara_wartosc
        json Nowa_wartosc
        datetime Kiedy
    }

    ALERT {
        string Typ "cpa_spike / ctr_drop / budget_exceeded / ..."
        string Poziom "critical / warning / info"
        string Opis
        datetime Wykryty
        datetime Rozwiazany
    }

    REGULA {
        string Nazwa
        string Warunki "np. CPA > 50 PLN AND conversions < 2"
        string Akcja "pause_keyword / lower_bid / notify"
        int Interwol_godziny
        bool Aktywna
    }

    RAPORT {
        string Typ "miesieczny / tygodniowy / health"
        string Okres
        string Narracja_AI "opis wygenerowany przez Claude"
    }
```

---

## 9. Filtry globalne — jak wplywaja na dane

```mermaid
graph TD
    subgraph FILTRY["Pasek filtrow globalnych"]
        F1["Typ kampanii<br/>Search / PMax / Shopping / DSA / Display / Video"]
        F2["Status kampanii<br/>Enabled / Paused / All"]
        F3["Zakres dat<br/>7d / 14d / 30d / 90d / custom"]
        F4["Nazwa kampanii<br/>wyszukiwanie tekstowe"]
    end

    subgraph ZAKLADKI_Z_FILTRAMI["Zakladki z filtrami"]
        Z1["Dashboard"]
        Z2["Kampanie"]
        Z3["Slowa kluczowe"]
        Z4["Wyszukiwania"]
        Z5["Audit Center"]
        Z6["Rekomendacje"]
        Z7["Shopping / PMax / Display / Video"]
        Z8["Competitive / Cross-Campaign / Benchmarki"]
        Z9["DSA"]
    end

    subgraph BEZ_FILTROW["Zakladki bez filtrow"]
        B1["Alerty — osobny widok"]
        B2["Agent — czat AI"]
        B3["Raporty — generowane per klient"]
        B4["Ustawienia — konfiguracja klienta"]
        B5["Historia akcji — calosc konta"]
        B6["Reguly — konfiguracja"]
    end

    F1 & F2 & F3 & F4 --> ZAKLADKI_Z_FILTRAMI

    style FILTRY fill:#1a1f2e,stroke:#4F8EF7,color:#fff
    style ZAKLADKI_Z_FILTRAMI fill:#1a1f2e,stroke:#4ADE80,color:#fff
    style BEZ_FILTROW fill:#1a1f2e,stroke:#FBBF24,color:#fff
```

---

> **Tip:** Zainstaluj rozszerzenie VS Code **"Markdown Preview Mermaid Support"** (`bierner.markdown-mermaid`) zeby renderowac diagramy bezposrednio w edytorze. Alternatywnie wklej na [mermaid.live](https://mermaid.live).
