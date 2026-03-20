# Silnik rekomendacji dla Google Ads Helper

## Kontekst i kryteria sukcesu

Wasz produkt jest zaprojektowany jako lokalny, “safety-first” helper do optymalizacji kont Google Ads: kluczowa ścieżka wartości to **sync → insight → apply/revert → history** (a reszta modułów to warstwa rozszerzeń). citeturn26view0turn27view0turn28view1 To bardzo dobry punkt wyjścia do budowy silnika rekomendacji, bo wymusza trzy właściwości:

Po pierwsze, rekomendacje muszą być **wykonywalne i weryfikowalne** – użytkownik ma dostać propozycję zmiany, zobaczyć podgląd (dry-run), świadomie zatwierdzić i mieć możliwość bezpiecznego cofnięcia w krótkim oknie. citeturn30view0turn20view0turn28view0

Po drugie, rekomendacje muszą być **bezpieczne finansowo** (ograniczenia na zmiany stawek/budżetów, limity akcji dziennie itp.) i każda mutacja ma przechodzić przez centralną walidację/circuit breaker. citeturn20view0turn41view0turn28view1

Po trzecie, rekomendacje muszą być **jasno uzasadnione** (“dlaczego to widzę?”) oraz **przybliżać wpływ** (“co zyskam/ryzykuję?”). To jest szczególnie istotne w Google Ads, gdzie “rekomendacje” (także te natywne od Google) mogą zmieniać się nawet kilka razy dziennie i stawać się nieaktualne po pobraniu – dlatego liczy się szybki cykl: wykryj → pokaż → zatwierdź → wykonaj. citeturn34view0turn34view2

## Stan obecny w repo

W repo macie już znaczną część “silnika rekomendacji” i to w bardzo sensownej architekturze: regułowy generator rekomendacji + persystencja + endpointy + UI z trybem “preview/confirm” oraz logowaniem akcji. citeturn26view0turn27view0turn25view0

### Model rekomendacji i kategorie

W backendzie generator (RecommendationsEngine) buduje obiekty rekomendacji z polami: `type`, `priority`, `entity_type`, `entity_id`, `entity_name`, `campaign_name`, `reason`, opcjonalnie `current_value`, `recommended_action`, `estimated_impact`, `metadata`, oraz rozróżnieniem kategorii `RECOMMENDATION` vs `ALERT`. citeturn32view0

W bazie persystujecie rekomendacje w tabeli `recommendations`: `rule_id`, `entity_type`, `entity_id`, `entity_name`, `priority`, `category`, `reason`, `suggested_action` (JSON), `status` (pending/applied/dismissed) i timestampy. citeturn19view0

### Reguły i zakres

Silnik ma **17 aktywnych reguł** (R1–R13 oraz R15–R18), priorytety HIGH/MEDIUM/LOW, oraz listę “irrelevant words” po EN+PL do automatycznych negatywów. citeturn32view0turn26view0turn27view0 W playbooku domenowym macie z kolei spójne uzasadnienie dlaczego te obszary są “core” (Search Terms Review jako najważniejsze, pauzowanie słabych, korekty stawek, budżety, testy reklam, QS, itp.). citeturn35view0turn35view2turn35view3

### API i UI workflow

API ma komplet endpointów potrzebnych do UX: pobranie listy rekomendacji, summary do badge, apply z parametrem `dry_run`, dismiss oraz eksport. citeturn26view1turn38view0

Frontend Recommendations ma już dojrzały flow:
- wyświetla tylko `pending` (hook wymusza `status: pending`),
- ma summary (Razem/Wysoki/Średni),
- filtr priorytetu,
- bulk apply/dismiss,
- **apply jest dwuetapowe**: najpierw `dry_run=true`, potem modal potwierdzenia i dopiero execute. citeturn39view0turn30view2turn30view0

To jest bardzo mocna baza pod “silnik rekomendacji”, bo UX jest gotowy na bezpieczne wdrażanie zmian. citeturn30view0turn20view0

## Luki i ryzyka w obecnym rozwiązaniu

Poniżej najważniejsze punkty, które – z perspektywy “silnika rekomendacji” – trzeba dopiąć, bo dziś mogą blokować skuteczne wdrożenia.

### Wykonalność niektórych typów rekomendacji

Router buduje `suggested_action` z `metadata`, zakładając że np. `ADD_KEYWORD` ma `ad_group_id`, a `ADD_NEGATIVE` ma `campaign_id`. citeturn38view0 Tymczasem w silniku reguła “Add Search Term as Keyword” generuje `metadata` z `match_type`, `conversions`, `cvr` itd., ale **nie dokłada `ad_group_id` ani nawet `campaign_id` w metadata** (mimo że query je wyciąga). citeturn33view0turn33view1 To w praktyce oznacza, że “Zastosuj” dla ADD_KEYWORD może kończyć się błędem “Missing ad_group_id or text” w `apply_action`. citeturn22view2turn38view0

Podobnie dla negatywów: `apply_action` w GoogleAdsService ma komentarz, że negatywy wymagają dedykowanego modelu w przyszłości i aktualnie de facto tylko loguje. citeturn22view2turn41view0 Czyli nawet jeśli rekomendacja jest dobra merytorycznie, silnik wykonawczy nie dowozi wartości dla użytkownika (bo realna zmiana w Google Ads nie zachodzi). citeturn22view2turn27view0

### Deduplication: możliwe “zjadanie” rekomendacji

Klucz deduplikacji w `_unique_key` to `type|entity_type|entity_id|entity_name`. citeturn38view0 Dla search termów `entity_id` jest ustawiane na 0, a `entity_name` to tekst frazy. citeturn33view3turn32view0 Jeśli ta sama fraza pojawi się w kilku kampaniach, rekomendacje mogą się nadpisywać/scalać mimo że kontekst (kampania/źródło) jest inny. To jest typowy błąd w silnikach rekomendacji opartych o “text key” bez uwzględnienia scope. citeturn38view0turn33view0

### Mutacje API są częściowo “local-only”

W `apply_action` część mutacji aktualizuje DB i (czasem) wywołuje Google Ads API (np. pauza keyword, update bid), ale inne działania – np. ADD_KEYWORD czy ADD_NEGATIVE – nie wykonują pełnej mutacji (ADD_KEYWORD tworzy lokalny keyword z “local-...” ID, a nie obiekt w Google Ads; ADD_NEGATIVE tylko loguje). citeturn22view2turn21view0turn20view0 To oznacza, że “silnik rekomendacji” jest dziś w części typów silnikiem “doradczym”, a nie wykonawczym.

### Interpretacja metryk: CVR > 100%

Na screenie rekomendacji widać przypadki CVR powyżej 100%. To nie musi być błąd: w Google Ads conversion rate może przekroczyć 100%, jeśli liczycie “Every” (wiele konwersji na jedną interakcję) lub macie kilka akcji konwersji. citeturn43view2 Warto to wprost oswoić w modelu i UI (np. tooltip “CVR może być >100%”). To zwiększa zaufanie i obniża ryzyko, że użytkownik uzna rekomendacje za “podejrzane”. citeturn43view2turn29view0

## Proponowany model danych rekomendacji

Dla “silnika rekomendacji” najważniejsze jest, żeby rekomendacja była **jednocześnie**: (a) czytelna w UI, (b) jednoznacznie wykonywalna, (c) bezpiecznie walidowalna, (d) audytowalna w historii.

Wasz obecny model jest blisko, ale rekomenduję doprecyzować go do dwóch warstw:

### Warstwa decyzji (Recommendation)

To obiekt “dlaczego i po co”, czyli to, co widzi user:

- `recommendation_id` (DB id) + **`stable_key`** (idempotency/dedup; koniecznie z pełnym scope: np. `type|client_id|campaign_id|ad_group_id|entity_id|term_hash`). citeturn38view0turn19view0  
- `source`: `PLAYBOOK_RULES` vs `GOOGLE_ADS_API` vs `HYBRID` (to przygotowuje grunt pod integrację z natywnymi rekomendacjami Google). citeturn37view4turn34view3  
- `scope`: `client_id`, `campaign_id`, `ad_group_id`, `network/source` (SEARCH/PMAX), ewentualnie `geo/device` jeśli to rekomendacja segmentowa. citeturn27view0turn25view0turn22view0  
- `type` (tak jak macie: ADD_KEYWORD, ADD_NEGATIVE, itd.) oraz `category` (RECOMMENDATION/ALERT). citeturn32view0turn27view0  
- `priority` (HIGH/MEDIUM/LOW), ale liczone ze **scoringu** (o tym niżej), nie tylko “twardo w regule”. citeturn32view0turn29view0  
- `evidence` (czyli dzisiejsze `metadata` + jednoznaczne wskazanie okna czasowego: np. `date_from/date_to`, źródło raportu, liczności). citeturn27view0turn41view1  
- `explanation`:  
  - `reason_short` (1 zdanie, UI),  
  - `reason_detail` (np. 3–5 bulletów “dlaczego”, “co sprawdziliśmy”, “co może pójść źle”). citeturn35view0turn43view0  
- `impact_estimate`: numericzny, nie tylko tekst – np. `expected_savings_micros`, `expected_additional_conversions`, + zakres niepewności. Google w swoich rekomendacjach pokazuje impact estimates (szczególnie w “Bidding and budgets”). citeturn34view3turn34view0  
- `confidence`: 0–1 (lub LOW/MED/HIGH), wynikający z danych (liczba klików/konwersji, stabilność trendu, zgodność z innymi sygnałami). To jest fundament pod przyszłe ML i pod uczciwą komunikację. citeturn42search11turn43view0

### Warstwa wykonawcza (Action)

To obiekt “co dokładnie zrobimy” – i tu warto być bezkompromisowym: akcja musi zawierać wszystko, żeby executor nie musiał “zgadywać”.

- `action_type` (kanoniczny: PAUSE_KEYWORD, UPDATE_BID, ADD_NEGATIVE, ADD_KEYWORD, INCREASE_BUDGET…) oraz mapowanie business→canonical jak w `action_types.py`. citeturn20view1turn20view0  
- `target`: `customer_id` (Google), `campaign_id`, `ad_group_id`, `criterion_id` – w zależności od typu. citeturn21view0turn22view2  
- `params`: np. `match_type`, `negative_level` (ACCOUNT/CAMPAIGN/AD_GROUP), `bid_amount_micros`/`change_pct`, `shared_set_id` dla list negatywów, itp. citeturn38view0turn37view4  
- `preconditions`: “wykonaj tylko jeśli…” (np. keyword nadal ENABLED, budżet nadal ogranicza IS, fraza nie została już dodana). To chroni przed nieaktualnością rekomendacji między sync a kliknięciem “Zastosuj”. citeturn34view0turn20view0  
- `safety_context`: kontekst do walidacji (liczba już spauzowanych keywordów w kampanii dziś, liczba negatywów dziś itd.) – u Was to już istnieje, ale warto uczynić to jawne w modelu. citeturn20view0turn41view0  
- `revertability`: czy można cofnąć (i jak) + ograniczenie czasowe (u Was: 24h). citeturn20view0turn28view0

Efekt: backend nie tylko “generuje opis”, ale generuje kompletną, idempotentną komendę do wykonania.

## Proponowana architektura silnika rekomendacji

Najbardziej praktyczny (i spójny z Waszym repo) będzie model hybrydowy: **Rule Engine jako kandydat generator + Scoring/Ranking + Action Builder + Executor**.

### Warstwa danych

Wasz sync i modele już dostarczają większość potrzebnych danych: kampanie/keywords/ads/search terms + dzienne metryki + segmenty device/geo + change events. citeturn27view0turn25view0turn26view1 Warto jednak pamiętać o dwóch rzeczach:

- Google Ads operuje w mikrosach; przechowujcie je jako int i dopiero na warstwie API/UI konwertujcie do “waluty”. To macie jako ADR i utils. citeturn28view0turn41view1  
- Dla PMax search terms używacie `campaign_search_term_view` i uważacie na pola, które filtrują wyniki (w repo to już ujęte jako ważna zasada). citeturn25view0turn22view2turn27view0  

### Kandydaci: skąd biorą się rekomendacje

Źródła kandydatów są trzy i one się dobrze uzupełniają:

- **Wasz playbook/reguły**: świetne dla “twardych” rzeczy typu wasted spend, negatywy, przerzucanie budżetu, QS audit, pacing. citeturn35view3turn32view0  
- **Natywne rekomendacje Google Ads API**: dają dostęp do rekomendacji, których trudno uczciwie odtworzyć lokalnie (np. ad assets / RSA improvements / strategie smart bidding/budżety z symulacjami). Google udostępnia pobieranie, apply i dismiss, subskrypcje auto-apply, a także ostrzega że rekomendacje potrafią szybko się dezaktualizować. citeturn37view4turn34view3turn34view0  
- **Analityczne “insighty”**: dziś generujecie je w frontendzie jako osobne heurystyki (np. kampanie powyżej średniego kosztu bez konwersji; rozbieżność CTR vs konwersje; liczba HIGH rekomendacji). To jest wartościowe, ale docelowo sensowniej byłoby zasilać to jednym systemem (np. jako `ALERT`/`INFO` w tym samym modelu). citeturn31view0turn32view0turn27view0  

### Scoring i priorytetyzacja

W regułowych silnikach PPC największym problemem nie jest “wymyślenie kolejnych reguł”, tylko **priorytetyzacja** (co jest warte czasu użytkownika).

Proponuję policzyć dla każdej rekomendacji trzy liczby:

- `impact_score` – oczekiwany wpływ (np. oszczędność lub potencjalny wzrost konwersji / ROAS), najlepiej w mikrosach + przeliczenie na “per miesiąc” (u Was już pojawiają się teksty typu `Save ~$X/month`). citeturn32view0turn29view0  
- `confidence_score` – pewność: rośnie z liczbą klików/konwersji i stabilnością trendu; spada jeśli to edge-case (np. mało danych). citeturn43view0turn35view3  
- `risk_score` – ryzyko szkody: np. broad match bez smart bidding, negatyw na poziomie konta (ryzyko “zbyt szerokiego” wycięcia), duża zmiana bid/budżetu (u Was ograniczana safety limits). citeturn41view0turn43view1turn20view0  

Z tego mapujecie `priority` (HIGH/MEDIUM/LOW) jako proste progi. To sprawia, że priorytet staje się transparentny i spójny między typami rekomendacji (a nie “ręcznie” zaszyty w regułach).

W perspektywie “deep research” da się pójść krok dalej: jeśli kiedyś będziecie chcieli optymalizować nie tylko performance, ale też **adoption** (czy użytkownik wdroży rekomendację), to literatura na temat systemów rekomendacji w reklamie pokazuje podejścia contextual bandit / reinforcement learning do równoważenia eksploracji i eksploatacji. citeturn42search4turn42search12 To jednak ma sens dopiero, kiedy macie feedback loop i dane o skutkach zmian (holding periods, kontrola). citeturn20view0turn28view0  

### Action Builder i “freshness”

Google Ads API podkreśla, że rekomendacje mogą stać się przeterminowane, a przeterminowane apply rzuca błędem; dobrą praktyką jest działanie krótko po pobraniu. citeturn34view0turn34view2 W Waszym silniku regułowym problem jest analogiczny: po sync i po kilku godzinach sytuacja może się zmienić.

Dlatego Action Builder powinien zawsze:
- wypełniać `preconditions` (sprawdź stan encji przed wykonaniem),
- oraz mieć `expires_at` lub “valid_for_days”, zwłaszcza dla rekomendacji typu bid/budget. citeturn34view0turn20view0

## Biblioteka rekomendacji: co wdrażać i jak to liczyć

Ponieważ macie już szeroki zakres 17 reguł, w praktyce największy zwrot dadzą 2–3 poprawki “silnikowe”, które zwiększą skuteczność wykonania i wiarygodność, a dopiero potem nowe reguły.

### Krytyczne typy z punktu widzenia Search Terms

Google definiuje Search Terms Report jako narzędzie do:  
- znajdowania skutecznych fraz do dodania jako keywordy,  
- oraz znajdowania mniej trafnych zapytań do dodania jako negatywy. citeturn43view0turn43view1  

To dokładnie odpowiada Waszym regułom R4 i R5/R18. citeturn32view0turn35view0

Żeby te rekomendacje były “produkcyjne”, potrzebujecie jednak doprecyzować model wykonania:

- **ADD_KEYWORD (z search term)**: rekomendacja musi zawierać `ad_group_id` (a dla PMax jasno określić, czy w ogóle wspieracie auto-dodanie do Search, czy to jest tylko insight). Obecnie engine tego nie dostarcza, a executor tego wymaga. citeturn33view0turn38view0turn22view2  
- **ADD_NEGATIVE**: trzeba zdecydować poziom (account/campaign/ad group) i typ dopasowania negatywu. W engine macie rozróżnienie “account level” vs “campaign level” w opisie, ale action payload realnie jeszcze tego nie realizuje, a sam executor nie wykonuje mutacji. citeturn33view3turn22view2turn41view0  

### Bid/Budget i bezpieczeństwo

Wasz circuit breaker jest bardzo dobry kierunkowo: ogranicza % zmiany bid/budżetu, minimalny/maksymalny bid, limity pauz i negatywów, a do tego wspiera dry-run i revert z oknem 24h (z sensownym wyjątkiem dla ADD_NEGATIVE). citeturn20view0turn41view0turn28view0

To jest też spójne z ideą, że “rekomendacje” nie mają działać jak auto-optymalizator, tylko jak kontrolowany system decyzyjny.

Warto natomiast pamiętać, że Google ma swoje “auto-apply recommendations” oraz API do subskrypcji (RecommendationSubscriptionService). Jeśli kiedyś zintegrujecie tę warstwę, to śledzenie zmian wymaga czytania change_event i filtrowania `GOOGLE_ADS_RECOMMENDATIONS_SUBSCRIPTION`. citeturn37view4turn36search12

### Metryki i wyjaśnialność

Wasz frontend wyświetla “metric pills” z metadata (koszt, kliknięcia, wyświetlenia, konwersje, CVR/CTR, match type itd.), a reason jest tłumaczony z angielskiego wzorca reguły. citeturn29view0turn32view0 To działa, ale docelowo model rekomendacji powinien mieć:
- “proof” (konkretne liczby),
- “why” (reguła),
- “what” (akcja),
- “risk” (dlaczego to może zaszkodzić),
- “when” (okno danych). citeturn42search11turn43view2turn34view0  

To są elementy, które literatura o wyjaśnialnych systemach decision-support uważa za kluczowe dla zaufania i adopcji. citeturn42search11

## Rekomendowana sekwencja wdrożenia zmian w silniku

Ponieważ cel to “wdrożyć model i silnik rekomendacji” realnie działający w Google Ads Helper, najkrótsza ścieżka do wysokiej wartości wygląda tak:

Najpierw domykacie **execution correctness**:
- Uzupełnienie `metadata`/`action payload` o brakujące identyfikatory (np. `ad_group_id`, `campaign_id`) tam, gdzie executor ich wymaga. citeturn38view0turn22view2turn33view0  
- Poprawa dedupu (`stable_key`) tak, by uwzględniał scope i nie zjadał rekomendacji między kampaniami. citeturn38view0turn33view3  
- Dokończenie realnych mutacji Google Ads API dla co najmniej: ADD_NEGATIVE i ADD_KEYWORD (żeby “Zastosuj” dawało realną zmianę na koncie, nie tylko w lokalnej bazie). citeturn22view2turn27view0turn37view4  

Potem wzmacniacie **model rekomendacji**:
- dodajecie numeric `impact_estimate`, `confidence`, `risk`, `expires_at`,  
- oraz persistujecie krytyczne pola do audytu (dziś DB trzyma głównie reason + suggested_action). citeturn19view0turn34view0turn20view0  

Na końcu dopinacie **hybrydę z Google Ads API Recommendations**, jeśli chcecie zwiększyć pokrycie typów rekomendacji (RSA assets, bidding/budget symulacje, itp.). Integracja jest dobrze opisana w dokumentacji (retrieve → apply/dismiss, auto-apply przez subscriptions), z istotnym ostrzeżeniem o szybko przeterminowujących się resource_name. citeturn37view4turn34view0turn37view1