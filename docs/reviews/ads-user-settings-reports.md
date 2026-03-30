# Notatki Marka — SETTINGS + REPORTS

**Reviewer**: Marek, specjalista Google Ads (6 lat, 8 kont)
**Data**: 2026-03-29
**Wersja**: review z screenshotow + kod zrodlowy

---

## SETTINGS (Ustawienia klienta)

### Co widze
- Formularz "Ustawienia klienta" z czterema sekcjami: Informacje ogolne, Strategia i konkurencja, Reguly biznesowe, Limity bezpieczenstwa.
- Na dole jest jeszcze "Twardy reset danych klienta" — strefy niebezpiecznej z potwierdzeniem nazwa klienta.
- Informacje ogolne: nazwa, branza, strona www, Google Customer ID (read-only), notatki.
- Strategia: target audience (textarea), USP (textarea), lista konkurentow jako pill-tagi z X do usuwania i "+ Dodaj".
- Reguly biznesowe: minimalny ROAS, max budzet dzienny (USD).
- Limity bezpieczenstwa: 6 parametrow — max zmiana stawki %, max zmiana budzetu %, min/max stawka USD, max pause keywords/dzien %, max negatywow/dzien. Kazdy z placeholderem "domyslnie: X".
- Przycisk "Zapisz" w gornym prawym rogu. Warning bar "Niezapisane zmiany" pojawia sie kiedy dirty.
- Sekcja MCC Accounts laduje sie automatycznie jesli klient ma customer_id — tabela z kontami podrzednymi.

### Co moge zrobic
- Edytowac profil klienta (nazwa, branza, www, notatki).
- Opisac target audience i USP — to moze potem karmic AI rekomendacje.
- Dodawac/usuwac konkurentow (pill-tagi) — promptem w przegladarce.
- Ustawic min ROAS i max budzet dzienny jako progi alarmowe.
- Nadpisac domyslne limity bezpieczenstwa per klient — to chroni przed zbyt agresywnymi zmianami automatycznymi.
- Zrobic twardy reset danych klienta (z potwierdzeniem).
- Zobaczyc konta MCC powiazane z tym customer ID.

### Wiecej niz Google Ads
- **Kontekst biznesowy w jednym miejscu** — Google Ads UI nie ma pola na "target audience", "USP", "notatki o kliencie". W agencji trzymam to w Notion / arkuszach. Tu jest przy koncie.
- **Limity bezpieczenstwa** — Google Ads nie ma circuit breaker na "max zmiana stawki na raz". To jest przydatne jesli narzedzie bedzie robic zmiany automatycznie.
- **Konkurenci jako tagi** — szybki dostep, moga karmic auction insights / search terms review.
- **Twardy reset** — czyste kasowanie lokalnych danych bez ruszania credentials. W Google Ads takiej opcji nie ma (i nie powinna byc), ale tu to inna baza lokalna, wiec sensowne.

### Brakuje vs Google Ads
1. **Conversion tracking setup** — w Google Ads w Settings widze: conversions, enhanced conversions, Google Analytics linking, auto-tagging. Tu nic z tego.
2. **Billing / platnosci** — w Google Ads Settings mam payment method, billing threshold, invoice history. Tu nie widze (moze celowo — lokalna aplikacja).
3. **Account access / permissions** — w Google Ads moge zarzadzac kto ma dostep (email-level). Brak.
4. **Auto-tagging** — status auto-tagging (on/off) — kluczowe dla GA4 integracji.
5. **Linked accounts** — Google Analytics, Merchant Center, YouTube, Search Console, Firebase — w Google Ads Settings jest cala sekcja "Linked accounts". Tu zero.
6. **IP exclusions** — lista IP do wykluczenia z klikow. Brak.
7. **Brand restrictions / guidelines** — Google Ads ma brand safety settings (Display/Video). Brak.
8. **Notification preferences** — w Google Ads moge ustawic alerty email. Tu nie ma notification settings.
9. **Call tracking / extensions defaults** — brak.

### Irytuje
1. **Dodawanie konkurenta przez `prompt()`** — to jest window.prompt przegladarki! Wyglada jak z 2005 roku. Powinien byc inline input albo modal.
2. **Waluta USD hardcoded** — ja pracuje w PLN. Labele mowia "Max budżet dzienny (USD)", ale w raportach widze "PLN". Niespojnosc.
3. **Brak informacji o ostatnim syncu** — nie widze kiedy ostatnio zsynchronizowano dane z Google Ads API. W Settings powinno byc "Ostatnia synchronizacja: 2 godziny temu".
4. **Brak walidacji URL** — moge wpisac byle co w "Strona WWW" — nie waliduje formatu URL.
5. **Google Customer ID read-only bez wyjasnienia** — dlaczego nie moge go zmienic? Brak tooltipa.
6. **Brak autosave / Ctrl+S** — musze klikac Zapisz. W dluzszym formularzu moglby byc skrot klawiaturowy.
7. **Sekcja MCC na samym dole** — jesli mam MCC z 15 kontami, musze przewinac caly formularz zeby do niej dojsc.

### Chcialbym
1. **Sync status & controls** — data ostatniego synca, przycisk "Synchronizuj teraz", harmonogram synca (co ile godzin).
2. **Conversion actions list** — wyswietl jakie konwersje sa skonfigurowane na koncie i ich status.
3. **Linked accounts overview** — GA4, Merchant Center, YouTube — chociaz read-only.
4. **Waluta konta** — pobierz z Google Ads API i wyswietl. Nie zakodowuj USD na sztywno.
5. **Inline input dla konkurentow** — zamiast window.prompt.
6. **Keyboard shortcut Ctrl+S** do zapisu.
7. **Sekcja "Konto Google Ads"** na gorze — customer ID, status konta, waluta, strefa czasowa, typ konta (MCC/standard).

### Verdykt
**6/10** — Solidna strona konfiguracji z unikalnym kontekstem biznesowym (target audience, USP, limity bezpieczenstwa). Ale brakuje kluczowych informacji ktore specjalista Google Ads oczekuje w "Settings" — conversion tracking, linked accounts, sync status, waluta. Dodawanie konkurentow przez window.prompt to wstyd. Ogolnie: dobra baza, ale potrzebuje wiecej "Google Ads awareness".

### Pytania @ads-expert
1. Czy sekcja "Strategia i konkurencja" (target audience, USP, konkurenci) jest wystarczajaca dla AI do generowania kontekstowych rekomendacji, czy potrzebne sa dodatkowe pola (sezonowosc, KPI priorytety, brand vs non-brand split)?
2. Limity bezpieczenstwa — czy 6 parametrow wystarczy? Brakuje np. "max budget increase per day in absolute USD", "minimum conversion volume before auto-bid changes".
3. Czy "Twardy reset" powinien byc w Settings, czy raczej w ukrytym panelu admin? Przecietny user moze sie przestraszyc.
4. Czy powinna byc sekcja "Conversion tracking health" w Settings, czy to lepiej pasuje do osobnej zakladki "Diagnostyka"?

---

## REPORTS (Raporty)

### Co widze
- Strona "Raporty" z lewym panelem (lista zapisanych raportow) i glownym obszarem (podglad wybranego raportu).
- Gorny toolbar: typ raportu (Miesiezny / Tygodniowy / Zdrowie konta), selektor okresu (dropdown miesiecy), przycisk "Generuj", "PDF / Drukuj".
- Badge "Claude dostepny" / "Claude niedostepny" — informuje czy AI agent jest online.
- Lista raportow po lewej: kazdy z tytulem (np. "Zdrowie 2026-03-29"), statusem pill (Gotowy/Generowanie/Blad), data, typ (TYG. / ZDROWIE).
- Podglad raportu: naglowek z datami + status, potem sekcje strukturalne:
  - **Porownanie miesiaz do miesiaca** — KPI cards (Wydatki, Klikniecia, Konwersje, CPA, ROAS) z delta vs poprzedni okres.
  - **Kampanie** — tabela ze statusem, budzetem, wydatkami, konwersjami, CPA, ROAS, IS%.
  - **Zmiany na koncie** — historia zmian z podziamem na typ operacji i resource.
  - **Wplyw zmian na wyniki** — before/after 7d per zmiana.
  - **Realizacja budzetow** — pacing per kampania z progress barem.
  - **Analiza AI i Rekomendacje** — narracja markdown od Claude (audyt zdrowia konta: structure, quality score, conversion tracking).
- Na dole: collapsible "Szczegoly techniczne" — model, token usage, koszt, czas generowania.

### Co moge zrobic
- Wybrac typ raportu: mieseczny, tygodniowy, zdrowie konta.
- Wybrac okres (miesiac) z dropdown ostatnich 12 miesiecy.
- Kliknac "Generuj" — raport generuje sie przez SSE streaming z progress barem i live AI text.
- Przegladac zapisane raporty z listy po lewej.
- Wydrukowac / eksportowac do PDF przyciskiem "PDF / Drukuj" (window.print).
- Zobaczyc szczegoly techniczne: model, tokeny, koszt, czas.

### Wiecej niz Google Ads
- **AI narracja + rekomendacje** — Google Ads daje suche dane w raportach. Tu mam pelny audyt tekstowy od AI: "2 grupy reklam maja tylko 1 RSA — dodaj warianty", "8 keywords z QS < 5 generuje 18% kosztow", "Priorytet: popraw landing pages". To jest mega wartosc.
- **Change impact analysis** — Google Ads nie llaczy zmian z ich wplywem. Tu widze "zmiana budzetu X -> wynik przed/po 7 dni". To jest cos czego nie ma nigdzie out-of-the-box.
- **Health score** — "Ogolny wynik: 74/100" z breakdown (Struktura 82/100, QS 6.2 avg) — to jest jak miniaudyt. Google Ads nie daje takiego score.
- **Budget pacing z wizualizacja** — progress bar per kampania. Google Ads pokazuje pacing, ale nie tak czytelnie.
- **SSE streaming** — widze raport generowany na zywo, tekst pojawia sie w real-time. Dobre UX.
- **3 typy raportow** — miesieczny, tygodniowy, zdrowie. Google Ads ma jeden typ raportu i musisz sam go sklejac.
- **Token usage transparency** — widze ile kosztowalo wygenerowanie raportu. To buduje zaufanie.

### Brakuje vs Google Ads
1. **Custom date range** — moge tylko wybrac miesiac. W Google Ads moge zrobic raport za dowolny zakres dat (np. kampania promocyjna 15.03-22.03). Tu tylko preset miesieczny.
2. **Scheduled reports** — w Google Ads moge ustawic automatyczne raporty email co tydzien/miesiac. Tu musze recznie kliknac "Generuj".
3. **Filtry w raporcie** — nie moge przefilterowac raportu po konkretnej kampanii, typie kampanii, statusie. Zawsze cale konto.
4. **Segmentacja** — Google Ads raporty moga byc segmentowane po device, network, location, audience. Tu zero segmentacji.
5. **Kolumny do wyboru** — w Google Ads customizuje kolumny raportu. Tu dostajesz fixed set KPI.
6. **Export do CSV/Excel** — tylko PDF/Print. Brak CSV/Excel export.
7. **Wykres trendu** — raport miesieczny powinien miec wykres daily/weekly spend + conversions. Teraz sa tylko sumaryczne KPI bez wizualizacji trendu.
8. **Porownanie wiecej niz m/m** — w Google Ads moge porownac Q1 vs Q1 YoY. Tu tylko m/m.
9. **Search terms insights w raporcie** — Google Ads reports maja breakdown po search terms. Tu sekcja search terms jest oddzielna zakladka, ale nie wpada do raportu.
10. **Audience performance w raporcie** — brak danych o grupach odbiorcow.

### Irytuje
1. **PDF/Drukuj = window.print()** — to nie jest prawdziwy PDF export. Drukuje strone przegladarki z navbarem, sidebarem, itd. Potrzebny dedykowany PDF generator.
2. **Brak usuwania raportow** — lista raportow po lewej rosnie bez konca. Nie moge usunac starego raportu.
3. **Brak porownywania raportow** — nie moge zestawic dwoch raportow obok siebie (np. marzec vs luty).
4. **Selektor okresu tylko dla monthly** — przy "Tygodniowy" nie moge wybrac ktory tydzien. Przy "Zdrowie" nie moge wybrac daty.
5. **Brak auto-refresh listy** — po wygenerowaniu raportu musze recznie odswiezyc liste (choc kod robi loadReports po report_id event — ale UX nie jest oczywisty).
6. **Waluta PLN/USD mieszana** — w KPI widze "PLN" ale w Settings jest "USD". Niespojnosc miedzy zakladkami.
7. **"Claude niedostepny" bez wyjasnienia** — gdy agent jest offline, widze czerwony badge ale nie wiem co zrobic. Brak instrukcji jak uruchomic Claude.

### Chcialbym
1. **Dedykowany PDF export** — czysty, branded PDF z logo klienta, bez elementow UI. Idealny do wyslania klientowi.
2. **Scheduled reports** — "Generuj automatycznie co poniedzialek" albo "1-go kazdego miesiaca".
3. **Custom date range** — nie tylko miesiac, ale dowolny zakres.
4. **Wykres trendu w raporcie** — daily spend/conversions line chart za okres raportu.
5. **Porownanie raportow side-by-side** — wybierz 2 raporty i porownaj KPI.
6. **Search terms top performers/wasters w raporcie** — top 10 najlepszych i 10 najgorszych search terms za okres.
7. **Eksport CSV/Excel** — obok PDF.
8. **Usuwanie starych raportow** — garbage collection.
9. **Template raportow** — "Raport dla klienta" (bez tech details) vs "Raport wewnetrzny" (pelne dane).
10. **Email/share** — wyslij raport na email klienta bezposrednio z UI.

### Verdykt
**8/10** — Najlepsza zakladka w aplikacji. AI narracja z audytem zdrowia konta, change impact analysis, budget pacing — to jest realna wartosc ktorej nie daje Google Ads UI ani Google Looker Studio. Streaming SSE i progress bar to dobre UX. Brakuje customizacji (date range, segmentacja, kolumny), dedykowanego PDF exportu i scheduled reports — ale core jest mocny. To jest feature ktory moze sprzedac caly produkt.

### Pytania @ads-expert
1. Czy raport "Zdrowie konta" powinien byc generowany automatycznie raz w tygodniu i wysylac alert jesli score spadnie ponizej progu?
2. Czy sekcja "Wplyw zmian na wyniki" (before/after 7d) jest wystarczajaco wiarygodna statystycznie, czy potrzebna jest dluzsza perspektywa (14d/30d)?
3. Czy AI narracja powinna byc bardziej actionable — np. "Kliknij tutaj aby wstrzymac keyword X" zamiast "Priorytet: wstrzymaj keyword X"?
4. Czy warto dodac "Executive summary" — 3 zdania na gorze raportu dla managera/klienta ktory nie czyta szczegolol?
5. Token usage / koszt — czy to powinno byc widoczne dla end-usera, czy tylko admin? Klient moze sie przestraszyc ze "kazdy raport kosztuje $0.XX".

---

## Podsumowanie obu zakladek

| Zakladka | Ocena | Kluczowa wartosc | Glowny brak |
|----------|-------|-------------------|-------------|
| Settings | 6/10 | Kontekst biznesowy + limity bezpieczenstwa | Brak integration z Google Ads settings (conversions, linked accounts, sync status) |
| Reports | 8/10 | AI narracja + change impact + health score | Brak custom date range, PDF export, scheduled reports |

**Settings** to "CRM-owa" strona konfiguracji — przydatna, ale nie daje tego czego oczekuje specjalista w "Settings" konta reklamowego. Potrzebuje wiecej danych z Google Ads API.

**Reports** to killer feature calego produktu. AI-driven audyt konta z actionable insights, change impact analysis, budget pacing — to jest cos za co agencje placa konsultantom. Trzeba doszlifowac export i customizacje, ale fundament jest mocny.
