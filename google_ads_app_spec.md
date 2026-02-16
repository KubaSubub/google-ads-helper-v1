# Aplikacja do Zarządzania i Optymalizacji Google Ads
## Kompletna Specyfikacja Projektu

---

## 1. WIZJA PROJEKTU

### Cel
Wykoksowana aplikacja do zarządzania kampaniami Google Ads z automatyzacją i zaawansowaną analityką, która wykonuje wszystkie zadania analityczne i optymalizacyjne, które normalnie robisz ręcznie.

### Kluczowe Założenia
- **Lokalność pierwsza** - wszystko działa lokalnie, dane klientów NIE wychodzą na zewnątrz
- **Kontrola użytkownika** - automatyzacje wymagają ręcznego zatwierdzenia (przycisk "WYKONAJ")
- **Zaawansowana analityka** - macierze korelacji, porównania czasowe, semantic analysis
- **AI jako asystent** - pomaga w analizie, nie zastępuje analityka
- **Możliwość pracy zdalnej** - opcjonalnie deployment na VPS z dostępem przez VPN

---

## 2. CZY POTRZEBUJESZ OLLAMA (LLM)?

### Alternatywy dla Ollama

**Lokalne narzędzia LLM:**
1. **LM Studio** - GUI, łatwe w użyciu, desktop app (Windows/Mac)
2. **text-generation-webui** - najbardziej rozbudowane, interfejs web, wiele formatów modeli
3. **GPT4All** - prosty setup, gotowy GUI out-of-the-box
4. **LocalAI** - OpenAI API compatible, świetne dla integracji z kodem
5. **vLLM** - najszybsze, dla produkcji, wymaga GPU
6. **Llamafile** - pojedynczy plik wykonywalny, najprostsza instalacja
7. **Jan** - all-in-one solution, multi-platform

**Czy w ogóle potrzebujesz lokalnego LLM?**

### Opcja A: BEZ LLM - Klasyczne NLP

Dla Twojego use case możesz całkowicie pominąć LLM i użyć tradycyjnych narzędzi NLP:

**spaCy** (zalecane dla Ciebie):
- Szybkie, production-ready
- Named Entity Recognition (NER)
- Dependency parsing
- Semantic similarity (word vectors)
- Świetne do semantic analysis search terms
- Działa offline, zero latencji

**NLTK**:
- Bardziej akademickie
- Większa elastyczność
- Wolniejsze niż spaCy
- Lepsze dla research, gorsze dla production

**Gensim**:
- Topic modeling
- Document similarity
- Word2Vec, Doc2Vec

**TextBlob**:
- Prosty API
- Sentiment analysis
- Translation

**Przykładowy use case: Semantic Clustering Search Terms BEZ LLM**
```python
import spacy
from sklearn.cluster import DBSCAN

nlp = spacy.load("en_core_web_lg")  # Large model z word vectors

search_terms = ["drewniane łóżko sypialniane", "łóżko do sypialni drewniane", ...]

# Konwersja do wektorów
vectors = [nlp(term).vector for term in search_terms]

# Clustering
clustering = DBSCAN(eps=0.3, min_samples=2).fit(vectors)

# Grupuj podobne
for label in set(clustering.labels_):
    cluster = [term for term, l in zip(search_terms, clustering.labels_) if l == label]
    print(f"Grupa {label}: {cluster}")
```

**Zalety podejścia bez LLM:**
- SZYBKOŚĆ - milisekundy zamiast sekund
- DETERMINISTYCZNE - zawsze ten sam wynik
- ZERO LATENCJI - nie czekasz na inference
- NISKIE WYMAGANIA - działa na CPU, nie potrzeba GPU
- PRECYZJA - dla semantic similarity często lepsze niż LLM

### Opcja B: Z LLM - Dla Bardziej Złożonych Analiz

**Kiedy LLM ma sens:**
- Analiza intencji użytkownika (informational vs transactional)
- Matching search term ↔ landing page content (zrozumienie kontekstu)
- Generowanie insights w języku naturalnym
- Diagnostyka problemów (high CTR low conversions - DLACZEGO?)

**Najlepsze opcje dla Twojego projektu:**

1. **LM Studio** (zalecane na start)
   - GUI desktop
   - Proste, kliknij i działa
   - Dobra integracja przez local API
   - Model browser wbudowany

2. **Ollama + Open WebUI** (jeśli wolisz CLI)
   - Lekkie, szybkie
   - Kompatybilne z OpenAI API
   - Łatwa integracja z Python

3. **LocalAI** (dla developerów)
   - Drop-in replacement dla OpenAI API
   - Jeden endpoint, wiele modeli
   - Docker-ready

**Polecane modele (2025):**
- **Llama 3.1 8B** - dobry balans, szybki
- **Mistral 7B** - świetny do reasoning
- **DeepSeek Coder** - jeśli AI ma generować kod/skrypty
- **Qwen 2.5** - dobry multilingual

### Opcja C: HYBRID - Najlepszy z obu światów (REKOMENDACJA)

**Co kiedy używać:**

1. **spaCy/klasyczne NLP** dla:
   - Tokenization, POS tagging
   - Semantic similarity (clustering search terms)
   - Named Entity Recognition
   - Fast pattern matching
   - Wszystko co wymaga szybkości i deterministyczności

2. **LLM** dla:
   - Landing page content analysis (scrape → summarize → match z search term)
   - Intent classification (bardziej nuanced niż klasyczne NLP)
   - Generating natural language insights/reports
   - Diagnostics ("dlaczego kampania X ma problem Y?")

**Przykład: Search Terms Analysis - HYBRID**
```python
# 1. SZYBKIE CLUSTERING - spaCy
semantic_clusters = cluster_with_spacy(search_terms)

# 2. GŁĘBSZA ANALIZA - LLM (tylko dla top clusters)
for cluster in semantic_clusters[:5]:  # Top 5 grup
    intent_analysis = llm_analyze_intent(cluster)
    landing_page_match = llm_match_to_landing_page(cluster, landing_page_content)
```

---

## 3. DECYZJA TECHNOLOGICZNA - STACK

### Backend

**Python + FastAPI**
- FastAPI dla REST API
- Google Ads API (oficjalna biblioteka Python)
- PostgreSQL jako główna baza danych
- Redis dla cache i rate limiting

**Biblioteki Analityczne:**
```python
pandas          # Manipulacja danymi
numpy           # Obliczenia numeryczne
scipy           # Statystyka (correlation, t-tests)
scikit-learn    # Clustering, anomaly detection
spacy           # NLP, semantic analysis
beautifulsoup4  # Scraping landing pages
playwright      # Alternatywnie do scraping (renderuje JS)
```

**Opcjonalnie - jeśli decydujesz się na LLM:**
```python
# Wybierz JEDNO:
ollama-python   # Jeśli Ollama
openai          # Jeśli LocalAI (OpenAI compatible)
```

**Task Scheduling:**
```python
APScheduler     # Cron-like jobs (fetch data co 6h)
```

### Frontend

**Desktop App - Electron (ZALECANE dla Ciebie)**
```
Electron        # Desktop wrapper
React           # UI framework
TanStack Table  # Zaawansowane tabele z sortowaniem/filtrowaniem
Recharts        # Wykresy i wizualizacje
Tailwind CSS    # Styling
shadcn/ui       # Komponenty (buttons, dialogs, cards)
```

**Alternatywnie - Web App:**
```
React + Vite
Same biblioteki co wyżej
```

### Baza Danych

**PostgreSQL**
- Relacyjna struktura (kampanie → ad groups → keywords → search terms)
- Transakcje ACID
- Zaawansowane query (JOIN, agregacje, window functions)
- Full-text search (dla notatek klientów)

**Schema (przykład):**
```sql
clients
  - id, name, industry, notes, business_context

campaigns
  - id, client_id, google_campaign_id, name, status, budget

ad_groups
  - id, campaign_id, google_ad_group_id, name

keywords
  - id, ad_group_id, text, match_type

search_terms
  - id, keyword_id, text, clicks, impressions, cost, conversions, date

metrics_daily
  - campaign_id, date, clicks, impressions, ctr, conversions, cost, roas

automated_rules
  - id, name, conditions, actions, status, last_run

execution_queue
  - id, rule_id, action_type, params, status, created_at
```

**Redis (Cache)**
```
- Google Ads API responses (TTL: 30min - 6h)
- Rate limiting counters
- Session data
```

---

## 4. ARCHITEKTURA APLIKACJI

```
┌──────────────────────────────────────────────────────┐
│              FRONTEND (Electron/React)               │
│  ┌────────────┬────────────┬─────────────────────┐  │
│  │ Dashboard  │ Campaigns  │ Search Terms        │  │
│  │ KPIs       │ Analyzer   │ Intelligence        │  │
│  ├────────────┼────────────┼─────────────────────┤  │
│  │ Ad Copy    │ Automated  │ Client Context      │  │
│  │ Analyzer   │ Rules      │ Manager             │  │
│  ├────────────┴────────────┴─────────────────────┤  │
│  │         AI Insights Panel (Optional)          │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────┬───────────────────────────────────┘
                   │ REST API
┌──────────────────▼───────────────────────────────────┐
│            BACKEND API (FastAPI)                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Endpoints:                                  │   │
│  │  - /campaigns, /search-terms, /rules         │   │
│  │  - /analytics/correlation                    │   │
│  │  - /ai/semantic-cluster (optional)           │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  Services:                                   │   │
│  │  - GoogleAdsService (API wrapper)            │   │
│  │  - AnalyticsService (stats, correlations)    │   │
│  │  - SemanticService (spaCy/LLM)               │   │
│  │  - AutomationService (rules engine)          │   │
│  └──────────────────────────────────────────────┘   │
└──────┬───────────────┬───────────────┬──────────────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PostgreSQL  │ │   Redis     │ │ Google Ads  │
│   (Data)    │ │  (Cache)    │ │     API     │
└─────────────┘ └─────────────┘ └─────────────┘
       ▲
       │
┌──────┴──────────┐
│  APScheduler    │ ← Automated data fetch (co 6h)
│  (Background    │   Rule execution check
│   Tasks)        │
└─────────────────┘

OPCJONALNIE:
┌─────────────────┐
│  LLM Service    │ ← LM Studio / Ollama / LocalAI
│  (Semantic      │   (tylko gdy potrzebujesz)
│   Analysis)     │
└─────────────────┘
```

---

## 5. FRONTEND - MODUŁY I WIDOKI

### 1. Dashboard Overview
**Co pokazuje:**
- KPI Cards: Spend, ROAS, Conversions, CTR (current vs previous period)
- Trend charts: Daily spend, conversions timeline
- Alerts panel: Anomalie (spike w cost, drop w conversions)
- Quick actions: Pause worst performers, boost best campaigns

**Technologie:**
- Recharts dla wykresów (LineChart, AreaChart)
- Cards z animacjami (Tailwind + Framer Motion)
- Real-time updates (WebSocket opcjonalnie)

### 2. Campaign Analyzer
**Funkcje:**
- Tabela kampanii (TanStack Table) - sortowanie, filtrowanie, search
- **MACIERZ KORELACJI** - heatmapa pokazująca korelacje między metrykami
  - Scatter plots: CTR vs Conversion Rate, Cost vs ROAS
  - Bubble chart: 3 wymiary (np. Cost, Conversions, CTR)
- **Comparison Tool**: Porównaj kampanie A vs B side-by-side
- **Time-series comparison**: Ten miesiąc vs poprzedni (tabela + wykresy)
- **Performance clustering**: Grupuj kampanie według wydajności (k-means)

**Widoki:**
- Table view (główny)
- Matrix view (correlation heatmap)
- Chart view (multi-line charts dla wielu kampanii)
- Comparison view (split screen A vs B)

### 3. Search Terms Intelligence (KLUCZOWY MODUŁ)
**Funkcje:**
- Lista search terms z metrykami (clicks, impressions, cost, conversions, CTR, ROAS)
- Filtry: date range, kampanie, min cost, min clicks
- **SEMANTIC ANALYSIS** (spaCy lub LLM):
  - Button: "Cluster Semantically"
  - Wynik: Grupy podobnych terminów
  - Highlight duplikaty (różne frazy, ta sama intencja)
  - Wykryj kanibalizację (te same terms w różnych kampaniach)
- **Landing Page Match Score**:
  - Scrape landing page content
  - Compare z search term (semantic similarity)
  - Score 1-10 + reasoning
- **Exclusion Queue**:
  - Checkbox przy każdym termie
  - "Add to Exclusion Queue" → pending actions
- **Intent Classification** (opcjonalnie z LLM):
  - Informational, Transactional, Navigational, Commercial

**UI:**
- Main table: Sortable, filterable
- Sidebar: Filters + actions
- Modal: Semantic groups (expandable list)
- Bottom panel: Pending actions queue

### 4. Ad Copy Analyzer
**Funkcje:**
- Lista reklam z performance (CTR, conversions, cost)
- **Element Performance Matrix**:
  - Rozłóż reklamy na elementy: Headlines, Descriptions, Paths
  - Pokaż które elementy mają najlepszy CTR / Conv Rate
  - Przykład: "Free Shipping" w headline → avg CTR 3.2%
- **A/B Testing Visualization**:
  - Compare ads w tej samej grupie
  - Statistical significance test (t-test)
- **Suggestions** (LLM opcjonalnie):
  - Generate new ad variants based on top performers

**Widoki:**
- Table view (ads list)
- Elements matrix (breakdown by headline/description)
- Performance comparison (side-by-side ads)

### 5. Keyword Strategy
**Funkcje:**
- Lista keywords z metrykami
- Match type performance comparison (Exact vs Phrase vs Broad)
- Bid optimization suggestions (statistical model)
- **Negative Keywords Queue**:
  - Based on rules (clicks > X, conversions = 0)
  - Semantic analysis (irrelevant terms)
  - Manual additions

### 6. Automated Rules Manager
**Funkcje:**
- Lista reguł (aktywne/nieaktywne/paused)
- Create new rule wizard:
  - IF conditions (metric thresholds, date ranges)
  - THEN actions (pause, change bid, add negative keyword)
  - Frequency (daily, weekly, manual)
- **DRY RUN mode**:
  - "Preview" button
  - Shows: Co by się stało gdyby reguła była aktywna w przeszłości
  - Symulacja na historical data
- **Execution Queue**:
  - Pending actions czekają na approval
  - Button: **"EXECUTE"** (tylko ty możesz kliknąć)
  - Confirmation dialog z summary
- **Execution History Log**:
  - Timestamp, rule name, action, result
  - Rollback option (gdzie możliwe)

**UI:**
- List view: Active rules cards
- Create wizard: Multi-step form
- Execution queue: Bottom drawer z pending actions count badge
- History: Timeline view z entries

### 7. Client Context Manager
**Funkcje:**
- Client profile form:
  - Basic info (name, industry, website)
  - Business context (USP, target audience, competitors)
  - Sezonowość (Black Friday, święta → adjust bids)
  - Business rules (nigdy nie bid poniżej X, max daily budget Y)
- Notes section:
  - Rich text editor (QuillJS)
  - AI-generated insights (opcjonalnie)
  - Tagging system (urgent, idea, competitor-intel)
- Files upload (logos, product photos dla reference)

**Struktura danych:**
```json
{
  "client_id": "...",
  "industry": "E-commerce - Meble",
  "target_audience": "Młode małżeństwa, 25-40 lat",
  "usp": "Darmowa dostawa, montaż gratis",
  "competitors": ["X.pl", "Y.com"],
  "seasonality": [
    {"period": "Black Friday", "multiplier": 2.5},
    {"period": "Q1", "multiplier": 0.7}
  ],
  "business_rules": {
    "min_roas": 3.0,
    "max_daily_budget": 500,
    "excluded_geos": ["ZA"]
  },
  "notes": [...]
}
```

### 8. Reports Generator
**Funkcje:**
- Template selector (Weekly summary, Monthly deep-dive, Custom)
- Date range picker
- Campaigns/metrics selector
- **AI Summary** (LLM opcjonalnie):
  - "Co się działo w tym okresie?"
  - Highlights: Best/worst performers, trends, anomalies
- Export: PDF (WeasyPrint), Excel (openpyxl), CSV

### 9. AI Insights Panel (Opcjonalny)
**Funkcje:**
- Chat interface z LLM
- Context selector:
  - Checkboxes: Which campaigns, date range, metrics
  - "Load context" → wysyła dane do LLM
- Preset prompts (buttons):
  - "Find worst performers"
  - "Compare this month vs last month"
  - "Analyze search terms for Campaign X"
  - "Diagnose low ROAS in Campaign Y"
- Response z actions:
  - LLM sugeruje: "Exclude keywords A, B, C"
  - Button: "Add to Queue"

**UI:**
- Sidebar panel (toggle on/off)
- Chat messages
- Context display (compact)
- Action buttons inline w response

---

## 6. BACKEND - SZCZEGÓŁOWE FUNKCJONALNOŚCI

### Google Ads API Integration

**Endpoints:**
```python
# Fetch data
GET /api/campaigns?client_id=X&date_from=Y&date_to=Z
GET /api/search-terms?campaign_id=X&min_cost=Y
GET /api/ads?ad_group_id=X

# Execute mutations
POST /api/keywords/exclude
  Body: {campaign_id, keywords: [...], dry_run: true/false}
POST /api/campaigns/pause
  Body: {campaign_ids: [...], dry_run: true/false}
```

**Rate Limiting:**
- Implementacja: Token bucket algorithm (Python `ratelimit` lib)
- Per-client limits (track w Redis)
- Retry logic: Exponential backoff (Google Ads SDK ma to wbudowane)
- Batch operations: Grupuj mutacje (max 10k ops per request)

### Analytics Service

**Statystyka:**
```python
# Correlation matrix
POST /api/analytics/correlation
  Body: {metrics: ['ctr', 'conversions', 'cost'], campaigns: [...]}
  Returns: Matrix + heatmap data

# Trend analysis
GET /api/analytics/trend?metric=ctr&campaign_id=X&days=30
  Returns: {trend: 'up'/'down'/'stable', slope, p_value}

# Anomaly detection
GET /api/analytics/anomalies?metric=cost&threshold=2.5
  Returns: [{date, campaign_id, value, z_score}]
```

**Implementacja:**
```python
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, ttest_ind

def correlation_matrix(df, metrics):
    corr = df[metrics].corr(method='pearson')
    return corr.to_dict()

def detect_anomalies(series, threshold=2.5):
    mean = series.mean()
    std = series.std()
    z_scores = (series - mean) / std
    return series[abs(z_scores) > threshold]
```

### Semantic Service

**Bez LLM (spaCy):**
```python
POST /api/semantic/cluster-search-terms
  Body: {search_terms: [{text, clicks, cost}, ...]}
  Returns: {
    clusters: [
      {cluster_id, terms: [...], centroid_term},
      ...
    ]
  }
```

**Implementacja:**
```python
import spacy
from sklearn.cluster import DBSCAN

nlp = spacy.load("en_core_web_lg")

def cluster_terms(terms_list):
    docs = [nlp(term['text']) for term in terms_list]
    vectors = [doc.vector for doc in docs]
    
    clustering = DBSCAN(eps=0.3, min_samples=2).fit(vectors)
    
    clusters = {}
    for idx, label in enumerate(clustering.labels_):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(terms_list[idx])
    
    return clusters
```

**Z LLM (opcjonalnie):**
```python
POST /api/semantic/analyze-intent
  Body: {search_term: "...", landing_page_url: "..."}
  Returns: {
    intent: 'transactional',
    confidence: 0.85,
    landing_page_match_score: 7,
    reasoning: "..."
  }
```

### Automation Service

**Rules Engine:**
```python
# Create rule
POST /api/rules
  Body: {
    name: "Pause high-cost low-conv keywords",
    conditions: {
      metric: 'cost',
      operator: '>',
      value: 100,
      AND: {
        metric: 'conversions',
        operator: '=',
        value: 0
      },
      lookback_days: 30
    },
    actions: [{type: 'pause_keyword', target: 'keyword_id'}],
    frequency: 'weekly',
    require_approval: true
  }

# Dry run
POST /api/rules/{rule_id}/dry-run
  Returns: {
    affected_entities: [...],
    estimated_impact: {cost_saved: X, impressions_lost: Y}
  }

# Execute (from queue)
POST /api/execution-queue/execute
  Body: {queue_item_ids: [...]}
  Returns: {success: true, executed: [...], failed: [...]}
```

**Implementacja:**
```python
class Rule:
    def evaluate(self, data):
        # Check conditions against data
        matches = []
        for entity in data:
            if self._check_conditions(entity, self.conditions):
                matches.append(entity)
        return matches
    
    def generate_actions(self, matches):
        actions = []
        for entity in matches:
            for action_template in self.actions:
                action = {
                    'type': action_template['type'],
                    'target_id': entity['id'],
                    'params': action_template.get('params', {})
                }
                actions.append(action)
        return actions

# Execution queue
class ExecutionQueue:
    def add(self, rule_id, actions):
        for action in actions:
            db.insert('execution_queue', {
                'rule_id': rule_id,
                'action_type': action['type'],
                'params': json.dumps(action),
                'status': 'pending',
                'created_at': datetime.now()
            })
    
    def execute_batch(self, queue_item_ids):
        items = db.query('SELECT * FROM execution_queue WHERE id IN (?)', queue_item_ids)
        results = []
        
        for item in items:
            try:
                result = self._execute_action(item)
                db.update('execution_queue', item['id'], {'status': 'executed', 'executed_at': datetime.now()})
                results.append({'id': item['id'], 'success': True, 'result': result})
            except Exception as e:
                db.update('execution_queue', item['id'], {'status': 'failed', 'error': str(e)})
                results.append({'id': item['id'], 'success': False, 'error': str(e)})
        
        return results
```

---

## 7. KLUCZOWE FUNKCJE - MACIERZE I ANALIZA

### Macierz Korelacji Metryk

**Co pokazuje:**
- Korelacje Pearsona między metrykami (CTR, Conversions, Cost, ROAS, ...)
- Heatmapa (kolor = siła korelacji)

**Implementacja:**
```python
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# Pobierz dane
df = pd.DataFrame(campaigns_data)

# Wybierz metryki numeryczne
metrics = ['clicks', 'impressions', 'ctr', 'conversions', 'cost', 'roas']

# Correlation matrix
corr_matrix = df[metrics].corr(method='pearson')

# Generuj heatmap (dla UI: zwróć JSON, frontend renderuje)
# Tutaj przykład z matplotlib (tylko dla ilustracji)
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0)
plt.savefig('correlation_heatmap.png')

# Return dla frontend
return corr_matrix.to_dict()
```

**Frontend (Recharts):**
```jsx
// Pseudo-kod
<ResponsiveContainer width="100%" height={400}>
  <Heatmap data={correlationMatrix} />
</ResponsiveContainer>
```

### Campaign Overlap Matrix

**Co pokazuje:**
- % wspólnych search terms między kampaniami
- Wykrywa kanibalizację

**Implementacja:**
```python
def campaign_overlap_matrix(campaigns):
    # Pobierz search terms dla każdej kampanii
    campaign_terms = {}
    for campaign in campaigns:
        terms = db.query('SELECT DISTINCT search_term FROM search_terms WHERE campaign_id = ?', campaign['id'])
        campaign_terms[campaign['id']] = set([t['search_term'] for t in terms])
    
    # Oblicz overlap
    overlap_matrix = {}
    for c1 in campaign_terms:
        overlap_matrix[c1] = {}
        for c2 in campaign_terms:
            if c1 == c2:
                overlap_matrix[c1][c2] = 100.0
            else:
                intersection = len(campaign_terms[c1] & campaign_terms[c2])
                union = len(campaign_terms[c1] | campaign_terms[c2])
                overlap_pct = (intersection / union * 100) if union > 0 else 0
                overlap_matrix[c1][c2] = round(overlap_pct, 1)
    
    return overlap_matrix
```

### Time-series Comparison

**Co pokazuje:**
- Porównanie metryk between periods (np. ten miesiąc vs poprzedni)
- % change, trend direction, statistical significance

**Implementacja:**
```python
from scipy.stats import ttest_ind

def compare_periods(metric, period_a_data, period_b_data):
    mean_a = np.mean(period_a_data)
    mean_b = np.mean(period_b_data)
    
    pct_change = ((mean_b - mean_a) / mean_a * 100) if mean_a > 0 else 0
    
    # T-test dla significance
    t_stat, p_value = ttest_ind(period_a_data, period_b_data)
    is_significant = p_value < 0.05
    
    return {
        'period_a_mean': mean_a,
        'period_b_mean': mean_b,
        'change_pct': pct_change,
        'trend': 'up' if mean_b > mean_a else 'down',
        'is_significant': is_significant,
        'p_value': p_value
    }
```

---

## 8. DEPLOYMENT I INFRASTRUKTURA

### Opcja A: Desktop App (Electron) - LOKALNA

**Build:**
```bash
# Frontend (React)
cd frontend
npm run build

# Backend (FastAPI) - pakuj w standalone
cd backend
pyinstaller --onefile main.py

# Electron - bundle wszystko
cd electron-app
npm run package  # Tworzy .exe/.app/.AppImage
```

**Struktura:**
```
my-app.exe (Windows) / my-app.app (Mac)
├── frontend/ (React build - statyczne pliki)
├── backend/ (Python embedded)
│   ├── main.exe (FastAPI server)
│   └── models/ (spaCy models, jeśli używane)
└── database/ (SQLite lub embedded PostgreSQL)
```

**Uruchomienie:**
1. User klika app icon
2. Electron window otwiera się
3. W tle: Electron uruchamia FastAPI server (localhost:8000)
4. Frontend komunikuje się z backend przez localhost

**Dane:**
- SQLite (prostsze) lub portable PostgreSQL
- Pliki w `%APPDATA%/GoogleAdsApp/` (Windows) lub `~/Library/Application Support/GoogleAdsApp/` (Mac)

### Opcja B: Online (VPS) - REMOTE ACCESS

**Stack:**
```
Docker Compose:
  - FastAPI container