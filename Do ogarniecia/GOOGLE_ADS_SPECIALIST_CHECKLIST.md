# Checklist Specjalisty Google Ads

Kompletna lista czynnosci, ktore specjalista Google Ads wykonuje na koncie klienta.
Uzywaj tego dokumentu jako benchmarku operacyjnego, a nie jako kanonicznej specyfikacji funkcji aplikacji.

Stan synchronizacji z repozytorium: 2026-03-30.

## Jak czytac ten dokument

- To jest lista pracy specjalisty, nie lista gwarantowanych funkcji wykonywalnych.
- Kanoniczny zakres produktu jest opisany w `docs/FEATURE_SET.md` i `PROGRESS.md`.
- Kazda potencjalna akcja w aplikacji musi przejsc przez pipeline bezpieczenstwa write:
  `ensure_demo_write_allowed()` -> `validate_action()` -> `ActionLog`.
- Progi kwotowe ponizej sa heurystykami roboczymi. W implementacji nalezy je normalizowac do waluty konta i celu biznesowego.

### Legenda mapowania do aplikacji

- `ACTION` - aplikacja potrafi wykonac akcje lub wspiera ja end-to-end.
- `INSIGHT_ONLY` - aplikacja potrafi wykryc lub opisac problem, ale nie wykonuje zmiany automatycznie.
- `PARTIAL` - aplikacja wspiera tylko czesc workflow.
- `OUT_OF_SCOPE` - poza obecnym zakresem v1.

---

## CODZIENNIE (15-30 min/konto)

### Monitoring budzetowy

- Sprawdzenie dziennego wydatku vs plan
- Alerty: kampanie, ktore przekroczyly 150% sredniego dziennego spendu
- Kampanie `limited by budget` - czy to celowe?
- Sprawdzenie shared budgets - czy dobrze sie rozkladaja

### Anomalie

- CTR drop > 30% vs srednia 7d
- CPC spike > 50% vs srednia 7d
- Konwersje = 0 przy normalnym ruchu
- Nagle zmiany w Impression Share
- Odrzucone reklamy (policy violations)

### Search Terms (najwazniejsze codzienne zadanie)

- Przeglad nowych search terms z ostatnich 24h
- Dodanie negatywow dla irrelevant queries
- Identyfikacja nowych keywordow z high-performing terms
- Regula: term z > 3 konwersjami i CVR > srednia kampanii -> kandydat do dodania jako keyword
- Regula: term z > 5 kliknieciami, 0 konwersji i CTR < 1% -> kandydat do dodania jako negatyw

### Szybkie akcje

- Pauza keywordow: koszt > prog roboczy, brak konwersji, wystarczajacy wolumen klikniec
- Pauza keywordow: CTR < 0.5% przy > 1000 impressions
- Pauza keywordow: Quality Score < 3 i wysoki koszt
- Pauza reklam: CTR < 50% najlepszej reklamy w grupie

---

## CO TYDZIEN (1-2 godziny/konto)

### Performance Analysis

- Porownanie last 7d vs previous 7d: Spend, Clicks, CTR, CPC, Conv, CVR, CPA, ROAS
- Identyfikacja trendow wzrostu i spadku
- Top 10 keywordow po koszcie - czy sie zwracaja?
- Bottom 10 keywordow po CVR - co z nimi zrobic?

### Keyword Optimization

- Bid adjustments: high performers (CVR > avg, CPA < target) -> +10-20%
- Bid adjustments: low performers -> -20% lub pause
- Match type review: broad z niskim CTR -> phrase lub exact
- Match type review: phrase z duzym waste -> dodaj negatywy
- Nowe keyword opportunities z Search Terms

### Ad Copy Testing

- Przeglad A/B testow - ktore reklamy wygrywaja?
- Pauza reklam z CTR < 50% best performer przy min. 500 impressions
- Tworzenie nowych wariantow: 3-4 ads per ad group
- Testowanie roznych CTA, headlines i descriptions
- RSA asset performance - ktore kombinacje dzialaja?

### Audience Analysis

- Wyniki po demographics: wiek, plec
- Wyniki po devices: mobile vs desktop
- Wyniki po locations: geografia
- Bid adjustments na segmenty: top performers plus, slabe minus
- Audience exclusions - kto klika, a nie konwertuje?

### Budget Reallocation

- ROAS per kampania - przesuniecie budzetu z low do high ROAS
- Regula: ROAS 800% vs ROAS 200% -> rozwaz przeniesienie czesci budzetu
- Sprawdzenie, czy budzety nie blokuja dobrych kampanii

---

## CO MIESIAC (3-5 godzin/konto)

### Competitor Analysis

- Auction Insights - kto wygrywa aukcje?
- Impression Share analysis - gdzie tracimy udzial?
- Overlap rate - z kim konkurujemy najczesciej?
- Strategie odpowiedzi: budzet, bidy, nowe kampanie

### Landing Page Analysis

- Bounce rate per kampania lub grupa reklamowa
- Czas na stronie per landing page
- Konwersje per landing page
- Rekomendacje CRO dla webmastera
- Mobile vs desktop experience na landing pages

### Account Structure Audit

- Czy kampanie sa logicznie podzielone? Brand vs generic vs competitor
- Ad groups - czy sa tematycznie spojne? Docelowo < 20 keywordow per grupa
- Negative keyword lists - aktualizacja i utrzymanie
- Shared negative lists - cross-campaign management
- Campaign naming convention - czy jest czytelna?

### Quality Score Deep Dive

- Lista keywordow z QS < 5
- Analiza skladowych: Expected CTR, Ad Relevance, Landing Page Experience
- Plan naprawy per keyword: ad relevance, landing page, expected CTR

### Attribution Analysis

- Porownanie modeli atrybucji: last-click vs data-driven
- Assisted conversions - ktore kampanie pomagaja, a nie domykaja?
- Conversion lag analysis - ile dni od klikniecia do konwersji?
- Cross-device conversions - czy sa poprawnie trackowane?

---

## CO KWARTAL (5-8 godzin/konto)

### Strategy Review

- Przeglad celow biznesowych klienta - czy sie zmienily?
- Analiza sezonowosci - co nas czeka w nastepnym kwartale?
- Competitor landscape - nowi gracze, zmiany strategii
- Budget planning na nastepny kwartal

### Full Account Audit

- Kampanie bez konwersji przez 30+ dni -> pause lub restructure
- Keywordy z zerowym ruchem przez 30+ dni -> pause lub zmiana match type
- Reklamy starsze niz 90 dni bez testowania -> odswiezenie
- Extensions lub assets audit - czy wszystkie sa aktualne?
- Conversion tracking audit - czy wszystko dziala?

### Nowe mozliwosci

- Nowe typy kampanii do przetestowania: PMax, Demand Gen, Video
- Nowe audience signals
- Nowe rozszerzenia reklam
- Automatyczne strategie bidowania - czy czas przetestowac?
- Skrypty Google Ads - automatyzacja powtarzalnych taskow

### Raportowanie

- Raport miesieczny dla klienta: KPI, trendy, akcje, plan
- Porownanie z benchmarkami branzy
- ROI analysis - ile klient zarobil na kazdej zlotowce w Ads
- Recommendations log - co zrobilismy, co planujemy dalej

---

## AKCJE JEDNORAZOWE (przy onboardingu konta)

### Setup i konfiguracja

- Conversion tracking setup: Google Tag, GA4 import
- Remarketing audiences setup
- Google Analytics 4 linkowanie
- Google Merchant Center linkowanie dla e-commerce
- Google Business Profile linkowanie dla local
- Brand Safety settings i content exclusions

### Struktura konta

- Kampanie wg celow biznesowych: brand, generic, competitor, remarketing
- Ad groups tematyczne: max 15-20 keywordow per grupa
- Negative keyword lists: brand, competitors, irrelevant
- Shared budgets, jesli potrzebne
- Labels i custom columns

### Kreacja

- RSA z min. 10 headlinami i 4 descriptions per grupa
- Sitelink extensions: min. 4
- Callout extensions
- Structured snippets
- Image extensions
- Call extensions, jesli potrzebne

---

## METRYKI - PRZYKLADOWE PROGI DECYZYJNE

Ponizsza tabela to benchmark specjalisty. Nie jest to automatyczna matryca wykonania 1:1.
W aplikacji v1 liczy sie takze kontekst kampanii, poziom ochrony, waluta konta i wynik walidacji akcji.

| Decyzja specjalisty | Przykladowy warunek roboczy | Oczekiwana akcja | Mapowanie do aplikacji v1 |
| --- | --- | --- | --- |
| Pauza keywordu | Koszt > rownowartosc 50 w walucie konta, Conv = 0, Clicks > 30 | PAUSE | `ACTION` -> `PAUSE_KEYWORD` |
| Pauza keywordu | CTR < 0.5%, Impr > 1000 | PAUSE | `ACTION` lub `INSIGHT_ONLY`, zaleznie od kontekstu |
| Pauza keywordu | QS < 3, wysoki koszt | PAUSE | `ACTION` lub `INSIGHT_ONLY`, zaleznie od kontekstu |
| Zwieksz bid | CVR > avg * 1.2, CPA < target * 0.8 | +20% bid | `ACTION` -> `UPDATE_BID` |
| Zwieksz bid | IS < 50%, Lost IS Rank > 30% | +15% bid | `ACTION` -> `UPDATE_BID` przy zdrowym kontekscie |
| Zmniejsz bid | CPA > target * 1.5, istotny spend | -20% bid | `ACTION` -> `UPDATE_BID` |
| Dodaj keyword | Search term: Conv >= 3, CVR > avg | Exact match | `ACTION` dla Search, `INSIGHT_ONLY` dla PMax |
| Dodaj keyword | Search term: Clicks > 10, CTR > 5% | Phrase match | `ACTION` lub `INSIGHT_ONLY`, zaleznie od typu kampanii |
| Dodaj negatyw | Search term: Clicks > 5, Conv = 0, CTR < 1% | Negative | `ACTION` dla scope kampania lub ad group |
| Dodaj negatyw | Search term zawiera waste words | Negative | `INSIGHT_ONLY` dla sugestii account-level lub n-gram |
| Pauza reklamy | CTR < 50% best ad, Impr > 500 | PAUSE | `ACTION` -> `PAUSE_AD` |
| Zwieksz budzet | Lost IS z dobrym CPA lub ROAS | INCREASE_BUDGET | `ACTION` tylko dla healthy branch |
| Przenies budzet | Slaba kampania finansuje mocniejsza | REALLOCATE | `INSIGHT_ONLY` lub `BLOCKED_BY_CONTEXT` |

---

## NARZEDZIA SPECJALISTY A NASZA APKA

Ocena ponizej dotyczy stanu repozytorium na 2026-03-30.

| Czynnosc | Google Ads UI | Skrypty | Narzedzia 3rd party | Nasza apka |
| --- | --- | --- | --- | --- |
| Search terms review | TAK, wolne i manualne | TAK, auto-negatywy | Optmyzr, Opteo | `TAK` - przeglad, trendy, wasted spend, bulk add negative, bulk add keyword |
| Keyword bidding | TAK, manualne | TAK, auto-bid rules | Adalysis | `PARTIAL` - rekomendacje `UPDATE_BID` i write dla target CPA lub ROAS, bez pelnego bulk editora keyword bids |
| Budget monitoring | TAK, basic alerts | TAK, custom alerts | Optmyzr | `TAK` - daily audit, pacing, budget guardrails, lost IS insights |
| A/B testing ads | TAK, Experiments | NIE | Adalysis | `PARTIAL` - analiza reklam i RSA, pauza slabych reklam, brak pelnego frameworka eksperymentow |
| Quality Score tracking | TAK, brak historii w UI | TAK, custom logging | Opteo | `TAK` - analiza QS, alerty, widoki jakosci i rekomendacje |
| Anomaly detection | Ograniczone | TAK, custom | Opteo, Optmyzr | `TAK` - alerts i `z-score anomalies` |
| Cross-account dashboards | TAK, MCC | NIE | Supermetrics, Looker | `TAK` - benchmarks, client comparison, MCC sync i diagnostyka |
| Competitor analysis | TAK, Auction Insights | TAK, eksporty | SEMrush, SpyFu | `TAK` - Auction Insights, Competitive page, rank i overlap visibility |
| Automated rules | TAK, limited | TAK, full power | Optmyzr | `TAK` - Rules CRUD, dry-run i execute |
| Bulk edits | TAK, Editor | TAK | Optmyzr | `PARTIAL` - bulk actions dla search terms i negatywow, bez odpowiednika pelnego Google Ads Editor |
| Reporting | TAK, basic | NIE | Supermetrics, Looker | `TAK` - raporty, SSE generation, zapis, print i widoki historii |

---

## Wnioski dla roadmapy

- Najmocniejsze pokrycie v1: search terms, alerty, rekomendacje, budzet, konkurencja, reguly, raportowanie.
- Obszary nadal czesciowe: pelny bulk editing, eksperymenty reklam, pelne keyword-level manual bidding UX.
- Wszystkie przyszle write actions musza zachowac rozdzial `ACTION` vs `INSIGHT_ONLY` i przechodzic przez safety pipeline.
