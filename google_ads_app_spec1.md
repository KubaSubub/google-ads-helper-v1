volumes:
  postgres_data:
  ollama_data:
```

**Deployment na VPS:**
```bash
# Serwer (np. Hetzner, DigitalOcean)
ssh user@your-vps

# Setup
git clone your-repo
cd google-ads-app
docker-compose up -d

# Dostęp z domu/pracy: Tailscale VPN (bezpieczny tunel)
# Instalacja Tailscale na VPS i lokalnej maszynie
# Połączenie przez internal IP (100.x.x.x)
```

**Bezpieczeństwo:**
- **Tailscale VPN** - prywatna sieć, zero-config, szyfrowane
- Alternatywnie: WireGuard VPN
- **NIE** wystawiaj publicznie na internet (bez reverse proxy + auth)
- OAuth tokens w environment variables (nigdy w kodzie)
- PostgreSQL connection string w .env file (dodaj do .gitignore)

### Opcja C: HYBRID (Najlepsze z obu światów)

**Primary:** Desktop app (Electron) - praca lokalna  
**Secondary:** VPS deployment - remote access kiedy potrzeba

**Synchronizacja:**
- Local database jako primary
- Periodic backup do VPS (encrypted)
- Albo: Local działa offline, sync z cloud DB gdy online

---

## 9. BEZPIECZEŃSTWO I DANE

### OAuth 2.0 - Refresh Tokens

**Aktualny plan:** OAuth co włączenie  
**Problem:** Użytkownik musi logować się za każdym razem

**Lepsze rozwiązanie:**
```python
# Przy pierwszym logowaniu:
# 1. User authorizes app → dostaje access_token + refresh_token
# 2. Zapisz refresh_token lokalnie (ENCRYPTED)

from cryptography.fernet import Fernet
import keyring  # System keychain (Windows Credential Manager, macOS Keychain)

# Generate encryption key (once, store securely)
key = Fernet.generate_key()
cipher = Fernet(key)

# Encrypt refresh token
encrypted_token = cipher.encrypt(refresh_token.encode())

# Store in system keychain
keyring.set_password("GoogleAdsApp", "refresh_token", encrypted_token.decode())

# Przy każdym uruchomieniu:
# 1. Load encrypted refresh_token z keychain
# 2. Decrypt
# 3. Use to get new access_token (Google Ads SDK robi to automatycznie)

encrypted = keyring.get_password("GoogleAdsApp", "refresh_token")
refresh_token = cipher.decrypt(encrypted.encode()).decode()
```

**Developer Token:**
- Zarejestruj app w Google Ads API Center
- Czekaj na approval (może trwać kilka dni)
- **Basic Access**: 15k operations/day - wystarczy na start
- **Standard Access**: Unlimited - potrzebujesz jeśli >10 klientów

### Szyfrowanie Danych

**Database:**
```bash
# PostgreSQL - encryption at rest
# Opcja 1: Zaszyfrowany dysk (LUKS na Linux, BitLocker Windows)
# Opcja 2: PostgreSQL pgcrypto extension

CREATE EXTENSION pgcrypto;

-- Szyfrowanie wrażliwych kolumn
INSERT INTO clients (name, notes_encrypted)
VALUES ('Client A', pgp_sym_encrypt('sensitive notes', 'your-secret-key'));

-- Odczyt
SELECT name, pgp_sym_decrypt(notes_encrypted::bytea, 'your-secret-key') AS notes
FROM clients;
```

**Backup:**
```bash
# Automated backup (cron)
0 2 * * * pg_dump googleads | gpg --encrypt --recipient your@email.com > backup.sql.gpg

# Upload do cloud (encrypted)
rclone copy backup.sql.gpg remote:backups/
```

### RODO Compliance

**Wymagania:**
1. **Data minimization** - zbieraj tylko potrzebne dane
2. **Right to erasure** - możliwość usunięcia danych klienta
3. **Access logs** - kto i kiedy miał dostęp do danych
4. **Retention policy** - automatyczne usuwanie starych danych

**Implementacja:**
```python
# Endpoint do usunięcia danych klienta
DELETE /api/clients/{client_id}
  - Usuwa wszystko: campaigns, search terms, metrics, notes
  - Cascade delete w PostgreSQL
  - Log operacji

# Access log
CREATE TABLE access_log (
  id SERIAL PRIMARY KEY,
  user_id INT,
  action VARCHAR(50),
  resource_type VARCHAR(50),
  resource_id INT,
  timestamp TIMESTAMP DEFAULT NOW()
);

# Przy każdym API request
def log_access(user_id, action, resource_type, resource_id):
    db.insert('access_log', {...})

# Retention policy (delete data older than 2 years)
DELETE FROM metrics_daily WHERE date < NOW() - INTERVAL '2 years';
```

---

## 10. OLLAMA / LLM - SZCZEGÓŁY IMPLEMENTACJI

### Jeśli decydujesz się na LLM

**Wybór modelu:**
1. **Llama 3.1 8B** (uniwersalny, dobry reasoning)
2. **Mistral 7B** (szybki, dobry do klasyfikacji)
3. **Qwen 2.5 7B** (multilingual, jeśli polskie search terms)

**Instalacja (Ollama przykład):**
```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download z ollama.com

# Pull model
ollama pull llama3.1

# Test
ollama run llama3.1 "Analyze this search term: 'buty do biegania nike'"
```

**Integracja z Python:**
```python
# backend/services/llm_service.py
import requests
import json

class LLMService:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
    
    def analyze_search_term_intent(self, search_term, landing_page_content):
        prompt = f"""
You are a Google Ads expert. Analyze this search term and landing page.

Search Term: "{search_term}"
Landing Page Content: {landing_page_content[:1000]}  # Limit context

Tasks:
1. Classify intent (informational / transactional / navigational / commercial investigation)
2. Rate landing page match 1-10
3. Suggest if this search term should be excluded (yes/no + reasoning)

Respond ONLY with valid JSON:
{{
  "intent": "...",
  "intent_confidence": 0.0-1.0,
  "landing_page_match_score": 1-10,
  "match_reasoning": "...",
  "should_exclude": true/false,
  "exclusion_reasoning": "..."
}}
"""
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": "llama3.1",
                "prompt": prompt,
                "stream": False,
                "format": "json"  # Force JSON output
            }
        )
        
        result = response.json()
        # Parse LLM response
        llm_output = json.loads(result['response'])
        return llm_output
    
    def cluster_search_terms_semantic(self, search_terms_list):
        # Format terms
        terms_str = "\n".join([f"- {t['text']} (clicks: {t['clicks']}, cost: {t['cost']})" for t in search_terms_list])
        
        prompt = f"""
Group these search terms by semantic similarity. Find duplicates (same intent, different wording).

Search Terms:
{terms_str}

Respond ONLY with valid JSON:
{{
  "clusters": [
    {{
      "cluster_id": 1,
      "primary_term": "...",
      "related_terms": ["...", "..."],
      "intent": "...",
      "suggested_action": "consolidate/keep_separate"
    }},
    ...
  ]
}}
"""
        
        # Similar API call as above
        # Return parsed JSON
```

**Frontend integration:**
```jsx
// React component
const SearchTermsAnalyzer = () => {
  const [analyzing, setAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  
  const handleSemanticAnalysis = async () => {
    setAnalyzing(true);
    const response = await fetch('/api/semantic/cluster-search-terms', {
      method: 'POST',
      body: JSON.stringify({ search_terms: selectedTerms })
    });
    const data = await response.json();
    setResults(data.clusters);
    setAnalyzing(false);
  };
  
  return (
    <div>
      <button onClick={handleSemanticAnalysis} disabled={analyzing}>
        {analyzing ? 'Analyzing...' : 'Cluster Semantically'}
      </button>
      {results && <ClusterResults clusters={results} />}
    </div>
  );
};
```

### Optymalizacja Performance

**Problem:** LLM inference jest wolny (5-30s na odpowiedź)

**Rozwiązania:**
1. **Async processing:**
   ```python
   from fastapi import BackgroundTasks
   
   @app.post("/api/semantic/analyze-async")
   async def analyze_async(data: dict, background_tasks: BackgroundTasks):
       task_id = generate_task_id()
       background_tasks.add_task(run_llm_analysis, task_id, data)
       return {"task_id": task_id, "status": "processing"}
   
   @app.get("/api/tasks/{task_id}")
   async def get_task_status(task_id: str):
       result = redis.get(f"task:{task_id}")
       return json.loads(result) if result else {"status": "processing"}
   ```

2. **Batch processing:**
   - Grupuj wiele search terms w jednym prompcie
   - Zamiast 100 requestów → 1 request z 100 terminami

3. **Caching:**
   ```python
   # Cache LLM results
   cache_key = f"intent:{search_term}"
   cached = redis.get(cache_key)
   if cached:
       return json.loads(cached)
   
   result = llm_service.analyze(search_term)
   redis.setex(cache_key, 86400, json.dumps(result))  # TTL 24h
   return result
   ```

4. **Quantization:**
   - Użyj Q4 lub Q5 quantized models (4-bit, 5-bit)
   - 2-3x szybsze niż full precision
   - Minimalna strata jakości

5. **GPU acceleration:**
   - NVIDIA GPU (RTX 3060+) → 10-50x szybsze niż CPU
   - VRAM minimum: 8GB dla 7B models, 16GB dla 13B+

---

## 11. SPACY - IMPLEMENTACJA (BEZ LLM)

### Setup

```bash
pip install spacy
python -m spacy download en_core_web_lg  # Angielski
python -m spacy download pl_core_news_lg  # Polski (jeśli polskie search terms)
```

### Use Cases

**1. Semantic Similarity (Search Terms Clustering)**

```python
import spacy
import numpy as np
from sklearn.cluster import DBSCAN

nlp = spacy.load("pl_core_news_lg")  # Albo en_core_web_lg

def cluster_search_terms(terms_data):
    """
    terms_data: [{"text": "...", "clicks": X, "cost": Y}, ...]
    """
    # Create doc objects
    docs = [nlp(term['text']) for term in terms_data]
    
    # Extract vectors
    vectors = np.array([doc.vector for doc in docs])
    
    # DBSCAN clustering (density-based, finds arbitrary shapes)
    # eps: max distance between samples in same cluster
    # min_samples: min cluster size
    clustering = DBSCAN(eps=0.35, min_samples=2, metric='cosine').fit(vectors)
    
    # Group by cluster
    clusters = {}
    for idx, label in enumerate(clustering.labels_):
        if label == -1:  # Noise (unclustered)
            continue
        if label not in clusters:
            clusters[label] = []
        clusters[label].append({
            'text': terms_data[idx]['text'],
            'clicks': terms_data[idx]['clicks'],
            'cost': terms_data[idx]['cost']
        })
    
    # Find centroid (most representative term) for each cluster
    results = []
    for cluster_id, terms in clusters.items():
        cluster_vectors = [nlp(t['text']).vector for t in terms]
        centroid = np.mean(cluster_vectors, axis=0)
        
        # Find term closest to centroid
        similarities = [np.dot(centroid, vec) / (np.linalg.norm(centroid) * np.linalg.norm(vec)) 
                       for vec in cluster_vectors]
        primary_idx = np.argmax(similarities)
        
        results.append({
            'cluster_id': cluster_id,
            'primary_term': terms[primary_idx]['text'],
            'related_terms': [t['text'] for t in terms],
            'total_clicks': sum(t['clicks'] for t in terms),
            'total_cost': sum(t['cost'] for t in terms)
        })
    
    return results

# Example
terms = [
    {"text": "buty do biegania nike", "clicks": 45, "cost": 120},
    {"text": "nike buty biegowe", "clicks": 38, "cost": 95},
    {"text": "adidasy do joggingu", "clicks": 22, "cost": 60},
    {"text": "łóżko drewniane sypialniane", "clicks": 15, "cost": 80}
]

clusters = cluster_search_terms(terms)
print(clusters)
# Output: Grupy semantycznie podobnych terminów
```

**2. Named Entity Recognition (Extract Brands/Products)**

```python
def extract_entities(search_terms):
    """
    Wyciąga brand names, product types z search terms
    """
    results = []
    for term in search_terms:
        doc = nlp(term['text'])
        
        entities = {
            'brands': [],
            'products': [],
            'attributes': []
        }
        
        for ent in doc.ents:
            if ent.label_ == 'ORG':  # Organization (often brands)
                entities['brands'].append(ent.text)
            elif ent.label_ == 'PRODUCT':
                entities['products'].append(ent.text)
        
        # Custom logic: detect product types (można dodać własne reguły)
        # Np. "buty" w termie → product type = "buty"
        
        results.append({
            'search_term': term['text'],
            'entities': entities
        })
    
    return results
```

**3. Keyword Intent Classification (Rule-based)**

```python
def classify_intent(search_term):
    """
    Simple rule-based intent classification
    """
    doc = nlp(search_term.lower())
    
    # Informational signals
    info_words = ['jak', 'co to', 'czym jest', 'dlaczego', 'tutorial', 'guide']
    # Transactional signals
    trans_words = ['kup', 'sklep', 'cena', 'tani', 'promocja', 'dostawa']
    # Navigational signals
    nav_words = ['nike.com', 'allegro', 'strona', 'login']
    
    intent = 'commercial_investigation'  # Default
    
    if any(word in search_term for word in info_words):
        intent = 'informational'
    elif any(word in search_term for word in trans_words):
        intent = 'transactional'
    elif any(word in search_term for word in nav_words):
        intent = 'navigational'
    
    return intent
```

**4. Landing Page Content Matching**

```python
from bs4 import BeautifulSoup
import requests

def scrape_landing_page(url):
    """
    Scrape and extract main content from landing page
    """
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text (remove scripts, styles)
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        return text[:5000]  # Limit to 5000 chars
    except:
        return ""

def calculate_landing_page_match(search_term, landing_page_url):
    """
    Calculate semantic similarity between search term and landing page
    """
    # Get landing page content
    page_content = scrape_landing_page(landing_page_url)
    if not page_content:
        return {'score': 0, 'reason': 'Failed to scrape page'}
    
    # Create docs
    search_doc = nlp(search_term)
    page_doc = nlp(page_content)
    
    # Similarity (cosine similarity of doc vectors)
    similarity = search_doc.similarity(page_doc)
    
    # Convert to 1-10 scale
    score = int(similarity * 10)
    
    # Check if key terms from search are in page
    search_tokens = [token.text.lower() for token in search_doc if not token.is_stop]
    page_text_lower = page_content.lower()
    
    matches = sum(1 for token in search_tokens if token in page_text_lower)
    coverage = matches / len(search_tokens) if search_tokens else 0
    
    reasoning = f"Similarity: {similarity:.2f}, Term coverage: {coverage:.0%}"
    
    return {
        'score': max(score, int(coverage * 10)),  # Use max of both metrics
        'similarity': similarity,
        'term_coverage': coverage,
        'reasoning': reasoning
    }
```

### Endpoint (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class SearchTermsRequest(BaseModel):
    terms: list[dict]  # [{"text": "...", "clicks": X, "cost": Y}]

@app.post("/api/semantic/cluster")
async def cluster_endpoint(request: SearchTermsRequest):
    try:
        clusters = cluster_search_terms(request.terms)
        return {"clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/semantic/landing-page-match")
async def landing_page_match(search_term: str, url: str):
    result = calculate_landing_page_match(search_term, url)
    return result
```

---

## 12. AUTOMATED RULES - PRZYKŁADY

### Rule 1: Pause High-Cost Low-Converting Keywords

```python
{
  "name": "Pause expensive keywords without conversions",
  "conditions": {
    "all": [
      {"metric": "cost", "operator": ">", "value": 200},
      {"metric": "conversions", "operator": "=", "value": 0},
      {"metric": "clicks", "operator": ">", "value": 50}
    ],
    "lookback_days": 30
  },
  "actions": [
    {"type": "pause_keyword"}
  ],
  "frequency": "weekly",
  "require_approval": true
}
```

### Rule 2: Increase Bids for High-ROAS Keywords

```python
{
  "name": "Boost bids for top performers",
  "conditions": {
    "all": [
      {"metric": "roas", "operator": ">", "value": 5.0},
      {"metric": "conversions", "operator": ">", "value": 10}
    ],
    "lookback_days": 7
  },
  "actions": [
    {
      "type": "adjust_bid",
      "params": {"adjustment_type": "multiply", "value": 1.2}  # +20%
    }
  ],
  "frequency": "daily",
  "require_approval": false  # Auto-execute (careful!)
}
```

### Rule 3: Add Negative Keywords from Search Terms

```python
{
  "name": "Auto-exclude irrelevant search terms",
  "conditions": {
    "all": [
      {"metric": "clicks", "operator": ">", "value": 20},
      {"metric": "ctr", "operator": "<", "value": 0.5},  # <0.5%
      {"metric": "conversions", "operator": "=", "value": 0}
    ],
    "lookback_days": 60,
    "entity_type": "search_term"
  },
  "actions": [
    {
      "type": "add_negative_keyword",
      "params": {"match_type": "phrase"}
    }
  ],
  "frequency": "weekly",
  "require_approval": true
}
```

### Rule 4: Budget Alerts

```python
{
  "name": "Alert when budget 80% spent",
  "conditions": {
    "all": [
      {"metric": "budget_spent_pct", "operator": ">", "value": 80}
    ],
    "lookback_days": 1,  # Today
    "entity_type": "campaign"
  },
  "actions": [
    {
      "type": "send_notification",
      "params": {
        "channel": "email",
        "message": "Campaign {{campaign_name}} has spent {{budget_spent_pct}}% of daily budget"
      }
    }
  ],
  "frequency": "hourly",
  "require_approval": false
}
```

### Implementation: Rules Evaluator

```python
class RulesEvaluator:
    def __init__(self, db):
        self.db = db
    
    def evaluate_rule(self, rule):
        """
        Evaluate single rule against current data
        """
        # Fetch relevant entities (keywords, campaigns, etc.)
        entities = self._fetch_entities(
            entity_type=rule['conditions'].get('entity_type', 'keyword'),
            lookback_days=rule['conditions']['lookback_days']
        )
        
        # Filter entities matching conditions
        matches = []
        for entity in entities:
            if self._check_conditions(entity, rule['conditions']):
                matches.append(entity)
        
        # Generate actions for matches
        actions = []
        for entity in matches:
            for action_template in rule['actions']:
                action = self._build_action(entity, action_template)
                actions.append(action)
        
        return {'rule_id': rule['id'], 'matches': len(matches), 'actions': actions}
    
    def _check_conditions(self, entity, conditions):
        """
        Check if entity meets all conditions
        """
        if 'all' in conditions:
            return all(self._check_condition(entity, cond) for cond in conditions['all'])
        elif 'any' in conditions:
            return any(self._check_condition(entity, cond) for cond in conditions['any'])
        else:
            return self._check_condition(entity, conditions)
    
    def _check_condition(self, entity, condition):
        metric_value = entity.get(condition['metric'])
        target_value = condition['value']
        operator = condition['operator']
        
        if operator == '>':
            return metric_value > target_value
        elif operator == '<':
            return metric_value < target_value
        elif operator == '=':
            return metric_value == target_value
        elif operator == '>=':
            return metric_value >= target_value
        elif operator == '<=':
            return metric_value <= target_value
        else:
            return False
```

---

## 13. ROADMAP - PLAN WDROŻENIA

### Faza 1: MVP (4-6 tygodni)

**Week 1-2: Setup & Infrastructure**
- [ ] Setup projektu (React + FastAPI + PostgreSQL)
- [ ] Google Ads API integration (OAuth, basic fetching)
- [ ] Database schema design & migrations
- [ ] Basic UI layout (Electron wrapper)

**Week 3-4: Core Features**
- [ ] Dashboard z KPIs
- [ ] Campaign list + basic filters
- [ ] Search terms table
- [ ] Data sync (Google Ads API → DB)
- [ ] Background scheduler (fetch data co 6h)

**Week 5-6: Basic Analytics**
- [ ] Time-series charts (Recharts)
- [ ] Simple comparison (this month vs last month)
- [ ] Export reports (CSV/Excel)

### Faza 2: Advanced Analytics (4-6 tygodni)

**Week 1-2: Matrices & Correlations**
- [ ] Correlation matrix (metrics)
- [ ] Campaign overlap matrix
- [ ] Statistical significance tests

**Week 3-4: Semantic Analysis**
- [ ] spaCy integration
- [ ] Search terms clustering
- [ ] Landing page scraping + matching

**Week 5-6: UI Polish**
- [ ] Interactive heatmaps
- [ ] Scatter plots (multi-dimensional)
- [ ] Advanced filters & search

### Faza 3: Automation (3-4 tygodnie)

**Week 1-2: Rules Engine**
- [ ] Create/edit/delete rules
- [ ] Rules evaluator (dry-run mode)
- [ ] Execution queue

**Week 3-4: Actions & Execution**
- [ ] Google Ads mutations (pause, bid changes, negative keywords)
- [ ] "EXECUTE" button + confirmation
- [ ] Execution history log
- [ ] Rollback mechanism (gdzie możliwe)

### Faza 4: AI Integration (opcjonalna, 2-3 tygodnie)

**Week 1: LLM Setup**
- [ ] Wybór: Ollama/LM Studio/LocalAI
- [ ] Model selection & testing
- [ ] API integration

**Week 2-3: AI Features**
- [ ] Intent classification
- [ ] Landing page analysis (LLM-powered)
- [ ] Natural language insights
- [ ] AI chat panel

### Faza 5: Production & Deployment (2 tygodnie)

**Week 1: Testing**
- [ ] Unit tests (backend)
- [ ] Integration tests (API)
- [ ] UI tests (Playwright)
- [ ] Performance testing

**Week 2: Deployment**
- [ ] Electron packaging (.exe/.app)
- [ ] User documentation
- [ ] Opcjonalnie: VPS deployment (Docker)

---

## 14. POTENCJALNE PROBLEMY I ROZWIĄZANIA

### Problem 1: Google Ads API Rate Limits
**Objaw:** Błędy RESOURCE_EXHAUSTED  
**Rozwiązanie:**
- Batch operations (grupuj mutacje)
- Implementuj exponential backoff
- Cache często używanych danych (Redis, TTL 30min-6h)
- Monitor usage (dashboard z current QPS)

### Problem 2: Wolne LLM Inference
**Objaw:** UI freezes, long loading times  
**Rozwiązanie:**
- Async processing (background tasks)
- Loading indicators + progress bars
- Użyj spaCy zamiast LLM gdzie możliwe
- Quantized models (Q4/Q5)
- GPU jeśli dostępne

### Problem 3: Large Dataset Performance
**Objaw:** Slow queries, UI lag  
**Rozwiązanie:**
- Database indexing (CREATE INDEX na często filtrowanych kolumnach)
- Pagination (limit 100-500 rows per page)
- Lazy loading (fetch data on scroll)
- Agregacje w DB, nie w Python
```sql
-- Przykład: Index na search_terms
CREATE INDEX idx_search_terms_cost ON search_terms(cost DESC);
CREATE INDEX idx_search_terms_date ON search_terms(date);
```

### Problem 4: Automatyzacje Psują Kampanie
**Objaw:** Unexpected drops w performance  
**Rozwiązanie:**
- **ZAWSZE** require approval dla destructive actions (pause, exclude)
- Dry-run mode mandatory
- Detailed logging (co, kiedy, dlaczego)
- Rollback mechanism
- Alert system (email notifications)

### Problem 5: Data Synchronization (Local ↔ Cloud)
**Objaw:** Conflicts, data loss  
**Rozwiązanie:**
- Single source of truth (Google Ads API)
- Local DB jako cache/mirror
- Periodic full refresh (overnight)
- Conflict resolution strategy (last-write-wins lub manual merge)

### Problem 6: Cross-Platform Compatibility (Electron)
**Objaw:** App działa na Windows, nie działa na Mac  
**Rozwiązanie:**
- Test na wielu platformach wcześnie
- Użyj electron-builder (obsługuje multi-platform)
- Unikaj platform-specific dependencies
- CI/CD z testami na Windows/Mac/Linux

---

## 15. NARZĘDZIA I BIBLIOTEKI - PEŁNA LISTA

### Backend (Python)

```txt
# requirements.txt

# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0

# Google Ads
google-ads==23.1.0

# Database
psycopg2-binary==2.9.9  # PostgreSQL
sqlalchemy==2.0.25
alembic==1.13.1  # Migrations

# Cache
redis==5.0.1

# Data processing
pandas==2.1.4
numpy==1.26.3
scipy==1.11.4
scikit-learn==1.3.2

# NLP (choose ONE approach)
spacy==3.7.2  # Option A: Classic NLP
# ollama-python==0.1.5  # Option B: LLM

# Web scraping
beautifulsoup4==4.12.3
requests==2.31.0
playwright==1.40.0  # Alternative to requests (renders JS)

# Visualization data prep
plotly==5.18.0  # For generating chart data

# Task scheduling
apscheduler==3.10.4

# Security
cryptography==41.0.7
python-jose[cryptography]==3.3.0
keyring==24.3.0

# Utilities
python-dotenv==1.0.0
pydantic-settings==2.1.0

# Export
openpyxl==3.1.2  # Excel
weasyprint==60.2  # PDF

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0  # For testing FastAPI
```

### Frontend (React)

```json
// package.json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    
    // UI Components
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-select": "^2.0.0",
    "lucide-react": "^0.303.0",
    
    // Tables
    "@tanstack/react-table": "^8.11.3",
    
    // Charts
    "recharts": "^2.10.3",# Aplikacja do Zarządzania i Optymalizacji Google Ads
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
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/googleads
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=yourpassword
  
  redis:
    image: redis:7-alpine
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
  
  # Opcjonalnie - jeśli używasz LLM
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

volumes:
  postgres_data:
  ollama_data: