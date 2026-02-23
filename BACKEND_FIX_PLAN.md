# PLAN NAPRAWCZY — Backend (szczegółowy)
## Google Ads Helper — Instrukcje krok po kroku dla Claude Code

**Data:** 2025-02-17
**Wersja:** 1.0
**Zakres:** TYLKO backend (18 issues, 4 sprinty)
**Źródło prawdy:** Implementation_Blueprint.md > Blueprint_Patch_v2_1.md > Technical_Spec.md > PRD_Core.md
**Reguła:** Blueprint wygrywa z PRD. Patch v2.1 wygrywa z Blueprint v2.0.

---

# ═══════════════════════════════════════════════════════
# SPRINT 1: INFRASTRUKTURA (B-01 → B-04)
# Fundament — bez tego nic dalej nie zadziała
# ═══════════════════════════════════════════════════════

## 🔴 B-01: ADR-002 — Float → BigInteger (micros) dla WSZYSTKICH wartości pieniężnych

**Priorytet:** KRYTYCZNY (blokujący)
**Naruszony wymóg:** ADR-002, CLAUDE.md Reguła 3+7, Blueprint_Patch_v2_1 §CONSISTENCY RULE
**Ryzyko:** Błędy zaokrągleń w kalkulacjach finansowych, niezgodność z Google Ads API

### Stan obecny

Wszystkie kolumny pieniężne w `backend/app/models.py` używają `Float`:

```python
# models.py — OBECNE (ZŁE)
class Campaign(Base):
    budget_amount = Column(Float)          # ← Float

class Keyword(Base):
    cost = Column(Float, default=0)        # ← Float
    avg_cpc = Column(Float, default=0)     # ← Float
    cpc_bid = Column(Float, default=0)     # ← Float

class SearchTerm(Base):
    cost = Column(Float, default=0)        # ← Float
    cost_per_conversion = Column(Float)    # ← Float

class Ad(Base):
    cost = Column(Float, default=0)        # ← Float

class MetricDaily(Base):
    cost = Column(Float, default=0)        # ← Float
    cost_per_conversion = Column(Float)    # ← Float
    avg_cpc = Column(Float, default=0)     # ← Float

class AdGroup(Base):
    cpc_bid = Column(Float, default=0)     # ← Float
```

### Wymagany stan (z Blueprint + Technical_Spec §8)

```python
# PRAWIDŁOWE — BigInteger (micros)
class Campaign(Base):
    budget_micros = Column(BigInteger, default=0)       # 1 USD = 1_000_000

class Keyword(Base):
    cost_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)
    bid_micros = Column(BigInteger, default=0)
    cpa_micros = Column(BigInteger, default=0)

class SearchTerm(Base):
    cost_micros = Column(BigInteger, default=0)

class Ad(Base):
    cost_micros = Column(BigInteger, default=0)

class MetricDaily(Base):
    cost_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)

class AdGroup(Base):
    bid_micros = Column(BigInteger, default=0)
```

### Kroki implementacji

1. **Zmień nazwy kolumn** (dodaj `_micros` suffix) + typ na `BigInteger`
2. **Usuń kolumny `cost_per_conversion`** — to wartość obliczana (cost_micros / conversions), nie przechowywana
3. **Zaktualizuj `seed.py`** — wartości seed * 1_000_000:
   ```python
   # ZAMIAST:
   budget_amount=random.uniform(50, 500)
   # POWINNO BYĆ:
   budget_micros=int(random.uniform(50, 500) * 1_000_000)
   ```
4. **Zaktualizuj schemas** — konwersja micros→float TYLKO tutaj:
   ```python
   # schemas/campaign.py
   from pydantic import computed_field

   class CampaignRead(BaseModel):
       budget_micros: int

       @computed_field
       @property
       def budget_usd(self) -> float:
           return round(self.budget_micros / 1_000_000, 2)

       class Config:
           from_attributes = True
   ```
5. **Zaktualizuj WSZYSTKIE routery/serwisy** — zamień `cost` na `cost_micros`, `cpc_bid` na `bid_micros` itd.
6. **Zaktualizuj `sync_service.py`** — wartości z API już są w micros, NIE dziel przez 1M

### Pliki do zmiany
- `backend/app/models.py` → rozbić na `models/*.py` (patrz B-04) + zmienić typy
- `backend/app/schemas.py` → rozbić na `schemas/*.py` + dodać `@computed_field`
- `backend/app/seed.py` → wartości seed * 1_000_000
- `backend/app/routers/*.py` → nowe nazwy pól
- `backend/app/services/*.py` → operacje na micros

### Reguła

> **NIGDY** nie przechowuj float w bazie dla wartości pieniężnych. Konwersja na float TYLKO w Pydantic schemas.

---

## 🔴 B-02: Brakujące modele — ActionLog, Alert, Recommendation

**Priorytet:** KRYTYCZNY (blokujący)
**Naruszony wymóg:** Blueprint §3, Patch v2.1, PRD Feature 4+7
**Ryzyko:** Feature 4 (Undo) i Feature 7 (Anomaly Detection) nie mogą istnieć bez tych tabel

### Stan obecny

Model `ExecutionQueueItem` CZĘŚCIOWO pokrywa action log, ale:
- ❌ Brak kolumny `old_value_json` → revert niemożliwy
- ❌ Brak kolumny `reverted_at` → nie wiadomo co cofnięto
- ❌ Brak statusu `REVERTED`
- ❌ Brak modeli `Alert` i `Recommendation` (persisted)

### Wymagane modele (z Technical_Spec §8 + Blueprint)

**a) ActionLog** — Feature 4: Undo

```python
# backend/app/models/action_log.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class ActionLog(Base):
    __tablename__ = "action_log"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    action_type = Column(String, nullable=False)       # PAUSE_KEYWORD, UPDATE_BID, ADD_NEGATIVE, etc.
    entity_type = Column(String, nullable=False)        # keyword, ad, campaign, search_term
    entity_id = Column(String, nullable=False)          # Google Ads entity ID
    old_value_json = Column(Text, nullable=True)        # JSON: {"bid_micros": 1500000, "status": "ENABLED"}
    new_value_json = Column(Text, nullable=True)        # JSON: {"bid_micros": 2000000}
    status = Column(String, default="SUCCESS")          # SUCCESS, FAILED, REVERTED
    error_message = Column(Text, nullable=True)
    reverted_at = Column(DateTime, nullable=True)       # kiedy cofnięto
    executed_at = Column(DateTime, server_default=func.now())
```

**Kluczowe:** `old_value_json` MUSI być zapisany PRZED wykonaniem akcji — bez tego revert jest niemożliwy.

**b) Alert** — Feature 7: Anomaly Detection

```python
# backend/app/models/alert.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    alert_type = Column(String, nullable=False)         # SPEND_SPIKE, CONVERSION_DROP, CTR_DROP
    severity = Column(String, default="MEDIUM")         # HIGH, MEDIUM
    title = Column(String, nullable=False)
    description = Column(Text)
    metric_value = Column(String, nullable=True)        # "Spend: $500 (avg: $200)"
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**c) Recommendation (persisted)**

```python
# backend/app/models/recommendation.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    rule_id = Column(String, nullable=False)            # "rule_1_waste_spend", "rule_2_low_qs" etc.
    entity_type = Column(String, nullable=False)        # keyword, campaign, search_term
    entity_id = Column(String, nullable=False)          # Google Ads entity ID
    priority = Column(String, default="MEDIUM")         # HIGH, MEDIUM
    reason = Column(Text, nullable=False)               # "High spend ($50) with 0 conversions"
    suggested_action = Column(Text, nullable=False)     # JSON: {"type": "PAUSE_KEYWORD", "keyword_id": "123"}
    status = Column(String, default="pending")          # pending, applied, dismissed
    created_at = Column(DateTime, server_default=func.now())
    applied_at = Column(DateTime, nullable=True)
```

### Decyzja o obecnym `ExecutionQueueItem`

`ExecutionQueueItem` można **usunąć** po migracji — `ActionLog` go zastępuje i jest nadwysokiem.
Alternatywnie zachowaj jako oddzielny model kolejki (jeśli planujesz batch execution).

---

## 🔴 B-03: ADR-004 — Brakujący credentials_service.py

**Priorytet:** KRYTYCZNY (blokujący)
**Naruszony wymóg:** ADR-004, CLAUDE.md Reguła 5
**Ryzyko:** Tokeny w plaintext .env → wyciek credentials przy git push

### Stan obecny

```python
# google_ads.py — OBECNE (ZŁE)
# Czyta tokeny wprost z pydantic-settings → .env
settings = get_settings()
credentials = {
    "developer_token": settings.google_ads_developer_token,
    "client_id": settings.google_ads_client_id,
    # ...
}
```

### Wymagana implementacja (z Blueprint §5)

```python
# backend/app/services/credentials_service.py
"""
JEDYNE miejsce na odczyt/zapis tokenów.
ADR-004: Windows Credential Manager via keyring.
"""
import keyring
from typing import Optional
from app.utils.logger import logger

SERVICE_NAME = "GoogleAdsHelper"

class CredentialsService:
    """Wrapper na Windows Credential Manager (keyring)."""

    # Klucze przechowywane w Credential Manager:
    REFRESH_TOKEN = "refresh_token"
    CLIENT_ID = "client_id"
    CLIENT_SECRET = "client_secret"
    DEVELOPER_TOKEN = "developer_token"

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Pobierz credential z Windows Credential Manager."""
        try:
            value = keyring.get_password(SERVICE_NAME, key)
            return value
        except Exception as e:
            logger.error(f"Failed to read credential '{key}': {e}")
            return None

    @staticmethod
    def set(key: str, value: str) -> bool:
        """Zapisz credential do Windows Credential Manager."""
        try:
            keyring.set_password(SERVICE_NAME, key, value)
            logger.info(f"Credential '{key}' saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save credential '{key}': {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Usuń credential z Windows Credential Manager."""
        try:
            keyring.delete_password(SERVICE_NAME, key)
            return True
        except keyring.errors.PasswordDeleteError:
            return False  # już nie istnieje
        except Exception as e:
            logger.error(f"Failed to delete credential '{key}': {e}")
            return False

    @classmethod
    def exists(cls) -> bool:
        """Czy refresh_token istnieje (= user jest zalogowany)?"""
        return cls.get(cls.REFRESH_TOKEN) is not None

    @classmethod
    def get_google_ads_credentials(cls) -> dict:
        """Zwróć dict z credentials dla Google Ads API."""
        return {
            "developer_token": cls.get(cls.DEVELOPER_TOKEN),
            "client_id": cls.get(cls.CLIENT_ID),
            "client_secret": cls.get(cls.CLIENT_SECRET),
            "refresh_token": cls.get(cls.REFRESH_TOKEN),
        }

    @classmethod
    def clear_all(cls):
        """Usuń wszystkie credentials (logout)."""
        for key in [cls.REFRESH_TOKEN, cls.CLIENT_ID, cls.CLIENT_SECRET, cls.DEVELOPER_TOKEN]:
            cls.delete(key)
```

### Pliki do zmiany po utworzeniu

1. `routers/auth.py` → zapisuj `refresh_token` przez `CredentialsService.set()` w callback
2. `services/google_ads_client.py` → pobieraj credentials przez `CredentialsService.get_google_ads_credentials()`
3. `config.py` → USUŃ pola `google_ads_*` z Settings (nie czytaj tokenów z .env)

### Fallback na development

Dla łatwego developmentu (bez Windows), dodaj fallback:
```python
# Na górze credentials_service.py
import os
if os.getenv("DEV_MODE") == "1":
    # W DEV_MODE używaj .env zamiast keyring
    # (np. na Linux/Mac gdzie keyring może nie działać)
    pass
```

---

## 🟠 B-04: Struktura plików niezgodna z Blueprint

**Priorytet:** POWAŻNY
**Naruszony wymóg:** CLAUDE.md Reguła 1, Blueprint §1
**Ryzyko:** Utrudnione utrzymanie, niezgodność z "Create files EXACTLY in the locations shown"

### Stan obecny

```
backend/app/
├── models.py        # JEDEN monolityczny plik ze WSZYSTKIMI modelami
├── schemas.py       # JEDEN monolityczny plik ze WSZYSTKIMI schematami
├── services/
│   ├── google_ads.py      # brak credentials_service, action_executor
│   ├── sync_service.py
│   ├── recommendations.py
│   ├── cache.py
│   └── semantic.py        # bonus, nie w Blueprint
└── routers/
    ├── clients.py
    ├── campaigns.py
    ├── keywords.py
    ├── search_terms.py
    ├── recommendations.py
    ├── analytics.py
    ├── actions.py
    ├── auth.py
    ├── export.py          # bonus, nie w Blueprint
    └── health.py          # bonus, nie w Blueprint
```

### Wymagana struktura (z Blueprint §1 + CLAUDE.md)

```
backend/app/
├── __init__.py
├── main.py
├── config.py
├── database.py
│
├── models/                        # Rozbić models.py → 7 plików
│   ├── __init__.py                # from .client import Client; from .campaign import Campaign; etc.
│   ├── client.py
│   ├── campaign.py
│   ├── keyword.py
│   ├── search_term.py
│   ├── recommendation.py          # NOWY (B-02)
│   ├── action_log.py              # NOWY (B-02)
│   └── alert.py                   # NOWY (B-02)
│
├── schemas/                       # Rozbić schemas.py → 5 plików
│   ├── __init__.py
│   ├── common.py                  # Enumy: Priority, ActionStatus, Segment, ActionType
│   ├── client.py
│   ├── campaign.py                # Konwersja micros→USD TUTAJ
│   ├── recommendation.py
│   └── search_term.py
│
├── routers/                       # Większość OK, dodaj brakujące
│   ├── __init__.py
│   ├── auth.py
│   ├── clients.py
│   ├── campaigns.py
│   ├── keywords.py
│   ├── search_terms.py
│   ├── recommendations.py
│   ├── actions.py
│   └── analytics.py
│
├── services/                      # Dodaj brakujące serwisy
│   ├── __init__.py
│   ├── credentials_service.py     # NOWY (B-03)
│   ├── google_ads_client.py       # renamed z google_ads.py
│   ├── sync_service.py
│   ├── recommendations_engine.py  # renamed z recommendations.py
│   ├── action_executor.py         # NOWY (B-05)
│   ├── analytics_service.py       # NOWY (B-06)
│   ├── search_terms_service.py    # NOWY (B-06)
│   └── cache.py                   # zachowaj
│
└── utils/
    ├── __init__.py
    ├── logger.py
    ├── constants.py               # NOWY — SAFETY_LIMITS + IRRELEVANT_KEYWORDS
    └── formatters.py              # NOWY — micros_to_currency(), currency_to_micros()
```

### Procedura rozbijania models.py

1. Utwórz `backend/app/models/` katalog
2. Przenieś każdą klasę modelu do osobnego pliku
3. Utwórz `__init__.py` który re-eksportuje wszystko:
   ```python
   # backend/app/models/__init__.py
   from .client import Client
   from .campaign import Campaign
   from .keyword import Keyword
   from .search_term import SearchTerm
   from .recommendation import Recommendation
   from .action_log import ActionLog
   from .alert import Alert

   __all__ = [
       "Client", "Campaign", "Keyword", "SearchTerm",
       "Recommendation", "ActionLog", "Alert"
   ]
   ```
4. Zaktualizuj wszystkie importy w routerach i serwisach:
   ```python
   # ZAMIAST:
   from app.models import Campaign, Keyword
   # TO SAMO (dzięki __init__.py):
   from app.models import Campaign, Keyword
   ```
5. **USUŃ** stary `backend/app/models.py`

### Procedura rozbijania schemas.py

Analogicznie — rozbij na `schemas/common.py`, `schemas/client.py`, `schemas/campaign.py`, etc.

Dodaj `@computed_field` dla konwersji micros→float:
```python
# schemas/campaign.py
from pydantic import BaseModel, computed_field

class CampaignRead(BaseModel):
    id: int
    client_id: int
    name: str
    status: str
    budget_micros: int
    spend_micros: int
    conversions: float
    clicks: int
    impressions: int
    ctr: float
    roas: float

    @computed_field
    @property
    def budget_usd(self) -> float:
        return round(self.budget_micros / 1_000_000, 2)

    @computed_field
    @property
    def spend_usd(self) -> float:
        return round(self.spend_micros / 1_000_000, 2)

    class Config:
        from_attributes = True
```

### Nowe pliki utils/

```python
# backend/app/utils/constants.py
"""Safety limits and constants — centralised config."""

SAFETY_LIMITS = {
    "MAX_BID_CHANGE_PCT": 0.50,        # Max 50% bid change per action
    "MIN_BID_USD": 0.10,
    "MAX_BID_USD": 100.00,
    "MAX_BUDGET_CHANGE_PCT": 0.30,     # Max 30% budget change
    "MAX_KEYWORD_PAUSE_PCT": 0.20,     # Max 20% keywords paused/day/campaign
    "MAX_NEGATIVES_PER_DAY": 100,
    "MAX_ACTIONS_PER_BATCH": 50,
    "PAUSE_KEYWORD_MIN_CLICKS": 10,
    "ADD_KEYWORD_MIN_CONV": 3,
    "ADD_NEGATIVE_MIN_CLICKS": 5,
    "HIGH_PERFORMER_CVR_MULTIPLIER": 1.5,
    "LOW_PERFORMER_CPA_MULTIPLIER": 2.0,
}

IRRELEVANT_KEYWORDS = [
    "darmowe", "free", "za darmo", "recenzja", "opinie",
    "jak", "co to", "wikipedia", "forum", "allegro",
    "olx", "youtube", "pdf", "praca", "oferta pracy",
]
```

```python
# backend/app/utils/formatters.py
"""Conversion helpers for micros ↔ currency."""

def micros_to_currency(micros: int) -> float:
    """Convert micros (BigInteger) to float for display."""
    return round((micros or 0) / 1_000_000, 2)

def currency_to_micros(amount: float) -> int:
    """Convert float amount to micros for storage."""
    return int(round(amount * 1_000_000))
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 2: SERWISY (B-05 → B-08)
# Logika biznesowa — circuit breaker, revert, analytics
# ═══════════════════════════════════════════════════════

## 🟠 B-05: Brak Circuit Breaker — validate_action()

**Priorytet:** POWAŻNY
**Naruszony wymóg:** CLAUDE.md Reguła 4, Blueprint §6
**Ryzyko:** Akcja może wyłączyć WSZYSTKIE keywordy lub ustawić bid $100 bez zabezpieczenia

### Stan obecny

`google_ads.py apply_action()` wykonuje mutacje BEZ walidacji:
```python
# OBECNE (ZŁE):
def apply_action(self, action_type, entity_id, params):
    if action_type == "PAUSE_KEYWORD":
        self._pause_keyword(entity_id)  # BEZ validate_action()!
    elif action_type == "SET_BID":
        self._set_bid(entity_id, params["new_bid"])  # BEZ walidacji limitów!
```

### Wymagana implementacja (z Blueprint §6 + Patch v2.1)

Utwórz `backend/app/services/action_executor.py`:

```python
# backend/app/services/action_executor.py
"""
Executes actions on Google Ads API.
REGUŁA: validate_action() MUSI być wywołana przed KAŻDYM zapisem.
REGUŁA: KAŻDA akcja MUSI być zalogowana w action_log.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.recommendation import Recommendation
from app.models.action_log import ActionLog
from app.models.keyword import Keyword
from app.models.client import Client
from app.services.google_ads_client import GoogleAdsClient
from app.services.credentials_service import CredentialsService
from app.utils.constants import SAFETY_LIMITS
from app.utils.logger import logger


class SafetyViolationError(Exception):
    """Rzucany gdy akcja narusza SAFETY_LIMITS."""
    pass


def validate_action(action_type: str, current_val: float,
                    new_val: float, context: dict) -> None:
    """
    Circuit breaker. Raises SafetyViolationError if action is unsafe.
    Wartości w USD (nie micros).
    """
    if action_type in ("UPDATE_BID", "SET_BID"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change bid: current bid is 0 or None")
        pct_change = abs(new_val - current_val) / current_val
        if pct_change > SAFETY_LIMITS["MAX_BID_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Bid change {pct_change:.0%} exceeds {SAFETY_LIMITS['MAX_BID_CHANGE_PCT']:.0%} limit. "
                f"${current_val:.2f} → ${new_val:.2f}"
            )
        if new_val < SAFETY_LIMITS["MIN_BID_USD"]:
            raise SafetyViolationError(
                f"New bid ${new_val:.2f} below minimum ${SAFETY_LIMITS['MIN_BID_USD']:.2f}"
            )
        if new_val > SAFETY_LIMITS["MAX_BID_USD"]:
            raise SafetyViolationError(
                f"New bid ${new_val:.2f} above maximum ${SAFETY_LIMITS['MAX_BID_USD']:.2f}"
            )

    if action_type in ("INCREASE_BUDGET", "SET_BUDGET"):
        if not current_val or current_val == 0:
            raise SafetyViolationError("Cannot change budget: current budget is 0 or None")
        pct_change = abs(new_val - current_val) / current_val
        if pct_change > SAFETY_LIMITS["MAX_BUDGET_CHANGE_PCT"]:
            raise SafetyViolationError(
                f"Budget change {pct_change:.0%} exceeds "
                f"{SAFETY_LIMITS['MAX_BUDGET_CHANGE_PCT']:.0%} limit"
            )

    if action_type == "PAUSE_KEYWORD":
        total = context.get("total_keywords_in_campaign", 0)
        paused_today = context.get("keywords_paused_today_in_campaign", 0)
        if total > 0 and (paused_today + 1) / total > SAFETY_LIMITS["MAX_KEYWORD_PAUSE_PCT"]:
            raise SafetyViolationError(
                f"Already paused {paused_today}/{total} keywords today. "
                f"Limit: {SAFETY_LIMITS['MAX_KEYWORD_PAUSE_PCT']:.0%}"
            )

    if action_type == "ADD_NEGATIVE":
        negatives_today = context.get("negatives_added_today", 0)
        if negatives_today >= SAFETY_LIMITS["MAX_NEGATIVES_PER_DAY"]:
            raise SafetyViolationError(
                f"Daily negative limit reached: "
                f"{negatives_today}/{SAFETY_LIMITS['MAX_NEGATIVES_PER_DAY']}"
            )


class ActionExecutor:
    """Wykonuje akcje na Google Ads API z walidacją i logowaniem."""

    def __init__(self, db: Session):
        self.db = db

    def apply_recommendation(self, recommendation_id: int, client_id: int,
                             dry_run: bool = False) -> dict:
        """
        Apply recommendation via Google Ads API.
        
        Flow:
        1. Fetch recommendation from DB
        2. Build context for validation
        3. validate_action() — circuit breaker
        4. If dry_run → return preview
        5. Execute via Google Ads API
        6. Log to action_log
        7. Update recommendation status
        """
        rec = self.db.query(Recommendation).filter(
            Recommendation.id == recommendation_id,
            Recommendation.client_id == client_id,
            Recommendation.status == 'pending'
        ).first()

        if not rec:
            return {"status": "error", "message": "Recommendation not found or already applied"}

        action = json.loads(rec.suggested_action)
        action_type = action["type"]
        context = self._build_context(action, client_id)
        current_val, new_val = self._extract_values(action)

        # CIRCUIT BREAKER
        try:
            validate_action(action_type, current_val, new_val, context)
        except SafetyViolationError as e:
            logger.warning(f"Safety violation for rec {recommendation_id}: {e}")
            return {"status": "blocked", "reason": str(e)}

        # DRY RUN → preview
        if dry_run:
            return {
                "status": "dry_run",
                "action": action,
                "current_val": current_val,
                "new_val": new_val,
                "message": "Dry run — action NOT applied."
            }

        # EXECUTE
        try:
            creds = CredentialsService.get_google_ads_credentials()
            client = Client.query.get(client_id)  # TODO: use db.get()
            ads_client = GoogleAdsClient(creds, client.google_ads_customer_id)

            old_value_json = json.dumps({"current_val": current_val})
            result = ads_client.execute(action)

            # LOG SUCCESS
            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=action_type,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=action.get("entity_id", ""),
                old_value_json=old_value_json,
                new_value_json=json.dumps({"new_val": new_val}),
                status="SUCCESS"
            )
            self.db.add(log_entry)

            # UPDATE RECOMMENDATION
            rec.status = "applied"
            rec.applied_at = datetime.utcnow()
            self.db.commit()

            return {"status": "success", "action_type": action_type, "message": "Action applied"}

        except Exception as e:
            self.db.rollback()
            # LOG FAILURE
            log_entry = ActionLog(
                client_id=client_id,
                recommendation_id=recommendation_id,
                action_type=action_type,
                entity_type=action.get("entity_type", "keyword"),
                entity_id=action.get("entity_id", ""),
                status="FAILED",
                error_message=str(e)
            )
            self.db.add(log_entry)
            self.db.commit()
            logger.error(f"Action failed for rec {recommendation_id}: {e}")
            return {"status": "error", "message": str(e)}

    def revert_action(self, action_log_id: int) -> dict:
        """
        Cofnij akcję z action_log.
        
        Reguły (z ADR-007 + Patch v2.1):
        - Akcja < 24h
        - Status = SUCCESS (nie FAILED, nie REVERTED)
        - ADD_NEGATIVE jest NIEREVERSOWALNE
        """
        # Pełna implementacja — patrz Patch v2.1 PATCH 1: ROLLBACK
        original = self.db.query(ActionLog).filter(
            ActionLog.id == action_log_id
        ).first()

        if not original:
            return {"status": "error", "message": "Action not found"}

        # Validate revertable
        if original.status == "REVERTED":
            return {"status": "error", "message": "Already reverted"}
        if original.status != "SUCCESS":
            return {"status": "error", "message": f"Cannot revert {original.status} action"}

        time_elapsed = datetime.utcnow() - original.executed_at
        if time_elapsed > timedelta(hours=24):
            return {"status": "error", "message": "Revert window (24h) expired"}

        IRREVERSIBLE = ["ADD_NEGATIVE"]
        if original.action_type in IRREVERSIBLE:
            return {"status": "error", "message": f"{original.action_type} cannot be reverted"}

        if not original.old_value_json:
            return {"status": "error", "message": "Missing previous state — cannot revert"}

        # Execute reverse (implementacja z Patch v2.1)
        try:
            old_state = json.loads(original.old_value_json)
            # ... build reverse action, execute via API ...

            # Mark as reverted
            original.status = "REVERTED"
            original.reverted_at = datetime.utcnow()

            # Log revert
            revert_log = ActionLog(
                client_id=original.client_id,
                action_type=f"REVERT_{original.action_type}",
                entity_type=original.entity_type,
                entity_id=original.entity_id,
                old_value_json=original.new_value_json,
                new_value_json=original.old_value_json,
                status="SUCCESS"
            )
            self.db.add(revert_log)
            self.db.commit()

            return {"status": "success", "message": f"Reverted: {original.action_type}"}

        except Exception as e:
            self.db.rollback()
            logger.error(f"Revert failed for action {action_log_id}: {e}")
            return {"status": "error", "message": f"Revert failed: {str(e)}"}

    def _build_context(self, action: dict, client_id: int) -> dict:
        """Build context dict for validate_action()."""
        context = {}
        # Count keywords paused today in same campaign
        if action.get("campaign_id"):
            from app.models.keyword import Keyword
            today = datetime.utcnow().date()
            context["total_keywords_in_campaign"] = self.db.query(Keyword).filter(
                Keyword.campaign_id == action["campaign_id"]
            ).count()
            context["keywords_paused_today_in_campaign"] = self.db.query(ActionLog).filter(
                ActionLog.client_id == client_id,
                ActionLog.action_type == "PAUSE_KEYWORD",
                func.date(ActionLog.executed_at) == today
            ).count()
        # Count negatives added today
        today = datetime.utcnow().date()
        context["negatives_added_today"] = self.db.query(ActionLog).filter(
            ActionLog.client_id == client_id,
            ActionLog.action_type == "ADD_NEGATIVE",
            func.date(ActionLog.executed_at) == today
        ).count()
        return context

    def _extract_values(self, action: dict) -> tuple:
        """Extract current and new values from action payload."""
        current = action.get("current_value", 0)
        new = action.get("new_value", 0)
        return (current, new)
```

---

## 🟠 B-06: Brakujące serwisy z Blueprint

**Priorytet:** POWAŻNY
**Naruszony wymóg:** Blueprint §5, Patch v2.1
**Ryzyko:** Logika biznesowa w routerach → brak testowalności, duplikacja

### Brakujące pliki serwisowe

| Plik | Status | Opis |
|------|--------|------|
| `services/action_executor.py` | ❌ BRAK | patrz B-05 powyżej |
| `services/search_terms_service.py` | ❌ BRAK | Logika segmentacji (150+ linii inline w routerze) |
| `services/analytics_service.py` | ❌ BRAK | KPI + anomaly detection |
| `services/credentials_service.py` | ❌ BRAK | patrz B-03 powyżej |

### a) search_terms_service.py (z Patch v2.1 PATCH 3)

Przenieś CAŁĄ logikę segmentacji z `routers/search_terms.py` do serwisu:

```python
# backend/app/services/search_terms_service.py
"""Search term segmentation logic (Feature 5)."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.search_term import SearchTerm
from app.models.campaign import Campaign
from app.utils.constants import IRRELEVANT_KEYWORDS
from app.utils.logger import logger


class SearchTermsService:

    def __init__(self, db: Session):
        self.db = db

    def segment_search_terms(self, client_id: int) -> int:
        """
        Assign segments to all search terms for a client.
        Called during sync Phase 4.
        
        Segments (ordered — first match wins):
        1. IRRELEVANT — query contains IRRELEVANT_KEYWORDS
        2. HIGH_PERFORMER — conv ≥ 3 AND CVR > campaign avg CVR
        3. WASTE — clicks ≥ 5 AND conv = 0 AND CTR < 1%
        4. OTHER — default
        
        Returns: count of terms segmented.
        """
        terms = self.db.query(SearchTerm).filter(
            SearchTerm.client_id == client_id
        ).all()

        # Pre-compute campaign avg CVR
        campaign_cvrs = self._get_campaign_avg_cvrs(client_id)
        segmented = 0

        for term in terms:
            old_segment = term.segment
            term.segment = self._classify(term, campaign_cvrs)
            if term.segment != old_segment:
                segmented += 1

        self.db.commit()
        logger.info(f"Segmented {segmented}/{len(terms)} search terms for client {client_id}")
        return segmented

    def get_segmented_search_terms(self, client_id: int) -> dict:
        """
        Return search terms grouped by segment with stats.
        Used by frontend SearchTerms.jsx segment cards.
        """
        segments = {}
        for seg in ["HIGH_PERFORMER", "WASTE", "IRRELEVANT", "OTHER"]:
            terms = self.db.query(SearchTerm).filter(
                SearchTerm.client_id == client_id,
                SearchTerm.segment == seg
            ).order_by(SearchTerm.cost_micros.desc()).all()

            total_cost = sum(t.cost_micros or 0 for t in terms)
            total_clicks = sum(t.clicks or 0 for t in terms)
            total_conv = sum(t.conversions or 0 for t in terms)

            segments[seg] = {
                "count": len(terms),
                "total_cost_usd": round(total_cost / 1_000_000, 2),
                "total_clicks": total_clicks,
                "total_conversions": total_conv,
                "terms": [
                    {
                        "id": t.id,
                        "query_text": t.query_text,
                        "clicks": t.clicks or 0,
                        "cost_usd": round((t.cost_micros or 0) / 1_000_000, 2),
                        "conversions": t.conversions or 0,
                        "ctr_pct": round((t.ctr or 0) * 100, 2),
                        "segment": t.segment or "OTHER"
                    }
                    for t in terms
                ]
            }

        return segments

    def _classify(self, term: SearchTerm, campaign_cvrs: dict) -> str:
        """Classify single search term into segment."""
        query_lower = (term.query_text or "").lower()

        # 1. IRRELEVANT
        if any(kw in query_lower for kw in IRRELEVANT_KEYWORDS):
            return "IRRELEVANT"

        # 2. HIGH_PERFORMER
        if (term.conversions or 0) >= 3:
            campaign_cvr = campaign_cvrs.get(term.campaign_id, 0)
            term_cvr = (term.conversions / term.clicks) if term.clicks else 0
            if term_cvr > campaign_cvr:
                return "HIGH_PERFORMER"

        # 3. WASTE
        if (term.clicks or 0) >= 5 and (term.conversions or 0) == 0:
            if (term.ctr or 0) < 0.01:
                return "WASTE"

        # 4. OTHER
        return "OTHER"

    def _get_campaign_avg_cvrs(self, client_id: int) -> dict:
        """Pre-compute avg CVR per campaign for segmentation."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id
        ).all()

        cvrs = {}
        for c in campaigns:
            if c.clicks and c.clicks > 0:
                cvrs[c.id] = (c.conversions or 0) / c.clicks
            else:
                cvrs[c.id] = 0
        return cvrs
```

**Po utworzeniu:** Refaktoruj `routers/search_terms.py` — zamień inline logikę na:
```python
@router.get("/segmented")
def get_segmented(client_id: int, db: Session = Depends(get_db)):
    service = SearchTermsService(db)
    return service.get_segmented_search_terms(client_id)
```

### b) analytics_service.py (z Patch v2.1 PATCH 2)

```python
# backend/app/services/analytics_service.py
"""KPI calculations + Anomaly Detection (Feature 7)."""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.campaign import Campaign
from app.models.keyword import Keyword
from app.models.alert import Alert
from app.utils.logger import logger


class AnalyticsService:

    def __init__(self, db: Session):
        self.db = db

    def get_kpis(self, client_id: int) -> dict:
        """Aggregate KPIs across all campaigns for a client."""
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id
        ).all()

        total_spend = sum(c.spend_micros or 0 for c in campaigns)
        total_clicks = sum(c.clicks or 0 for c in campaigns)
        total_impressions = sum(c.impressions or 0 for c in campaigns)
        total_conversions = sum(c.conversions or 0 for c in campaigns)

        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
        avg_cpc = (total_spend / total_clicks) if total_clicks else 0
        cpa = (total_spend / total_conversions) if total_conversions else 0

        return {
            "total_spend_usd": round(total_spend / 1_000_000, 2),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "avg_ctr_pct": round(avg_ctr, 2),
            "avg_cpc_usd": round(avg_cpc / 1_000_000, 2),
            "cpa_usd": round(cpa / 1_000_000, 2),
            "active_campaigns": len([c for c in campaigns if c.status == "ENABLED"]),
        }

    def detect_anomalies(self, client_id: int) -> list:
        """
        Run anomaly detection rules (Feature 7, PRD).
        Called after sync.
        
        Rules:
        1. SPEND_SPIKE: campaign spend > 3× proportional share
        2. CONVERSION_DROP: daily avg ≥ 3 but total < daily_avg × 15
        3. CTR_DROP: campaign CTR < 0.5% with impressions > 1000
        """
        alerts_created = []
        campaigns = self.db.query(Campaign).filter(
            Campaign.client_id == client_id,
            Campaign.status == "ENABLED"
        ).all()

        if not campaigns:
            return alerts_created

        total_spend = sum(c.spend_micros or 0 for c in campaigns)
        avg_spend = total_spend / len(campaigns) if campaigns else 0

        for campaign in campaigns:
            # Rule 1: SPEND_SPIKE
            if avg_spend > 0 and (campaign.spend_micros or 0) > avg_spend * 3:
                alert = self._create_alert(
                    client_id=client_id,
                    campaign_id=campaign.id,
                    alert_type="SPEND_SPIKE",
                    severity="HIGH",
                    title=f"Spend spike: {campaign.name}",
                    description=(
                        f"Campaign spend ${(campaign.spend_micros or 0)/1_000_000:.2f} "
                        f"is 3× above average ${avg_spend/1_000_000:.2f}"
                    )
                )
                if alert:
                    alerts_created.append(alert)

            # Rule 2: CONVERSION_DROP
            daily_avg_conv = (campaign.conversions or 0) / 30  # 30-day data
            if daily_avg_conv >= 3 and (campaign.conversions or 0) < daily_avg_conv * 15:
                alert = self._create_alert(
                    client_id=client_id,
                    campaign_id=campaign.id,
                    alert_type="CONVERSION_DROP",
                    severity="HIGH",
                    title=f"Conversion drop: {campaign.name}",
                    description=f"Expected ~{daily_avg_conv:.0f}/day, got much less"
                )
                if alert:
                    alerts_created.append(alert)

            # Rule 3: CTR_DROP
            if (campaign.impressions or 0) > 1000 and (campaign.ctr or 0) < 0.005:
                alert = self._create_alert(
                    client_id=client_id,
                    campaign_id=campaign.id,
                    alert_type="CTR_DROP",
                    severity="MEDIUM",
                    title=f"Low CTR: {campaign.name}",
                    description=f"CTR {(campaign.ctr or 0)*100:.2f}% below 0.5% threshold"
                )
                if alert:
                    alerts_created.append(alert)

        self.db.commit()
        return alerts_created

    def _create_alert(self, **kwargs) -> Alert | None:
        """Create alert if not already exists (deduplicate)."""
        existing = self.db.query(Alert).filter(
            Alert.client_id == kwargs["client_id"],
            Alert.campaign_id == kwargs.get("campaign_id"),
            Alert.alert_type == kwargs["alert_type"],
            Alert.resolved_at.is_(None)  # only unresolved
        ).first()

        if existing:
            return None  # already reported

        alert = Alert(**kwargs)
        self.db.add(alert)
        return alert
```

---

## 🟠 B-07: ROAS obliczane nieprawidłowo w analytics.py

**Priorytet:** POWAŻNY
**Naruszony wymóg:** Definicja ROAS
**Ryzyko:** Nieprawidłowe dane → złe decyzje optymalizacyjne

### Stan obecny

```python
# routers/analytics.py — OBECNE (ZŁE):
"roas": round((total_conversions / total_cost) if total_cost else 0, 2)
# To jest Conversion Rate per Dollar, NIE ROAS!
```

### Prawidłowa formuła

```
ROAS = Revenue / Cost
Revenue = Conversions × Average Order Value (AOV)
```

Seed.py hint: `roas = conversions * 150 / cost` (AOV = 150 PLN)

### Wymagana zmiana

Opcja A (prosta): Użyj stałego AOV z konfiguracji klienta:
```python
# W analytics_service.py:
aov = 150  # TODO: pobrać z client.business_rules lub config
revenue = total_conversions * aov
roas = round(revenue / (total_spend_usd), 2) if total_spend_usd else 0
```

Opcja B (docelowa): Dodaj pole `avg_order_value` do modelu `Client` i pozwól userowi je ustawić.

---

## 🟠 B-08: seed.py — crash risk + deprecated API

**Priorytet:** POWAŻNY
**Ryzyko:** Crash przy pustej konfiguracji kampanii

### Problem

```python
# Zagnieżdżone wyrażenie — trudne do debugowania, crash jeśli pusta lista:
keyword_text=random.choice([kw_text for kw_text, _ in ad_groups_config.get(
    db.query(Campaign).get(ag.campaign_id).name, [("", [])]) ...
```

Dodatkowo `db.query(Campaign).get(id)` → deprecated w SQLAlchemy 2.0.

### Wymagana zmiana

```python
# ZAMIAST db.query(Campaign).get(id):
campaign = db.get(Campaign, ag.campaign_id)

# Uprość wyrażenie:
campaign_name = campaign.name if campaign else ""
keywords_for_campaign = ad_groups_config.get(campaign_name, [])
if keywords_for_campaign:
    keyword_text = random.choice([kw for kw, _ in keywords_for_campaign])
else:
    keyword_text = "generic keyword"
```

Zaktualizuj WSZYSTKIE wartości pieniężne na micros (B-01):
```python
# ZAMIAST:
budget_amount=random.uniform(50, 500)
# POWINNO BYĆ:
budget_micros=int(random.uniform(50, 500) * 1_000_000)
```

---

# ═══════════════════════════════════════════════════════
# SPRINT 3: JAKOŚĆ KODU (B-09 → B-14)
# Dług techniczny — deprecated API, thread-safety, audit
# ═══════════════════════════════════════════════════════

## 🟡 B-09: Deprecated datetime.utcnow → func.now()

**Priorytet:** ŚREDNI
**Ryzyko:** Warning od Python 3.12+, potencjalnie błędne timezone

### Stan obecny

```python
# We WSZYSTKICH modelach:
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### Wymagana zmiana

```python
from sqlalchemy.sql import func

# Opcja 1 (preferowana — server-side):
created_at = Column(DateTime, server_default=func.now())
updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Opcja 2 (python-side, ale nie deprecated):
from datetime import datetime, timezone
created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

**Zakres:** Wszystkie pliki w `models/` (po rozbiciu B-04).

---

## 🟡 B-10: Importy na dole plików — antypattern

**Priorytet:** ŚREDNI

### Problem

```python
# main.py — importy na DOLE pliku:
from app.routers import clients, campaigns, keywords  # noqa: E402

# analytics.py — importy na DOLE pliku:
from app.models import Keyword, AdGroup  # noqa: E402
```

### Poprawka

Przenieś importy na górę. Jeśli circular import → refaktoruj (po rozbiciu models/ w B-04 circular imports powinny zniknąć).

---

## 🟡 B-11: Brak audit logging w actions.py

**Priorytet:** ŚREDNI
**Ryzyko:** Brak śladu audytowego — kto co zrobił

### Problem

- `apply_recommendation` w routerze NIE loguje do `ActionLog`
- Model `AccessLog` istnieje ale jest NIGDZIE nieużywany
- Po wdrożeniu `ActionExecutor` (B-05) problem zniknie — tam jest logowanie

### Poprawka

Po B-05: upewnij się że router `recommendations.py` wywołuje `ActionExecutor.apply_recommendation()` zamiast bezpośrednio google_ads_client.

---

## 🟡 B-12: semantic.py — brak thread-safety

**Priorytet:** ŚREDNI
**Ryzyko:** Race condition przy lazy loading modelu ML

### Problem

```python
# OBECNE:
class SemanticService:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = SentenceTransformer('all-MiniLM-L6-v2')  # BEZ LOCKA
        return cls._model
```

### Poprawka

```python
import threading

class SemanticService:
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls):
        if cls._model is None:
            with cls._lock:
                if cls._model is None:  # double-check locking
                    cls._model = SentenceTransformer('all-MiniLM-L6-v2')
        return cls._model
```

---

## 🟡 B-13: cache.py — misleading TTL API

**Priorytet:** ŚREDNI

### Problem

```python
# OBECNE:
def set_cached(key: str, value: Any, ttl: int = 300):
    cache[key] = value  # ttl parametr jest IGNOROWANY
```

`cachetools.TTLCache` ma globalny TTL, nie per-key.

### Poprawka

Opcja A: Usuń parametr `ttl` z `set_cached()`:
```python
def set_cached(key: str, value: Any):
    """Cache value. TTL is global (set in TTLCache constructor)."""
    cache[key] = value
```

Opcja B: Dodaj komentarz wyjaśniający:
```python
def set_cached(key: str, value: Any, ttl: int = 300):
    """Cache value. NOTE: ttl param is ignored — TTLCache uses global TTL."""
    cache[key] = value
```

---

## 🟡 B-14: Hardcoded IRRELEVANT_WORDS w search_terms.py

**Priorytet:** ŚREDNI

### Problem

Lista stop-words hardcoded w routerze `search_terms.py`. Powinna być konfigurowalna.

### Poprawka

1. Przenieś do `utils/constants.py` (B-04 — już zrobione)
2. Docelowo: dodaj `business_rules` JSON field do modelu `Client` z customowymi stop-words per klient

---

# ═══════════════════════════════════════════════════════
# SPRINT 4: POPRAWKI DROBNE (B-15 → B-18)
# ═══════════════════════════════════════════════════════

## 🟢 B-15: export.py — brak walidacji istnienia klienta/kampanii

**Priorytet:** DROBNY

### Problem
Export nie sprawdza czy `client_id`/`campaign_id` istnieje → zwraca puste dane bez błędu.

### Poprawka
```python
@router.get("/export/campaigns")
def export_campaigns(client_id: int, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
    # ...
```

---

## 🟢 B-16: PaginatedResponse — brak generycznego typowania

**Priorytet:** DROBNY

### Problem
```python
# OBECNE:
class PaginatedResponse(BaseModel):
    items: list       # brak typowania → traci walidację

# POWINNO BYĆ:
from typing import Generic, TypeVar
T = TypeVar('T')
class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

---

## 🟢 B-17: Brak katalogu tests/

**Priorytet:** DROBNY (ale ważny długoterminowo)

### Problem
`pytest` w `requirements.txt` ale brak `tests/` katalogu.

### Minimalne testy

```
backend/tests/
├── __init__.py
├── conftest.py              # fixture z test DB (SQLite in-memory)
├── test_models.py           # Czy modele się tworzą
├── test_safety_limits.py    # Czy validate_action() blokuje niebezpieczne akcje
├── test_segmentation.py     # Czy search terms segmentacja działa poprawnie
└── test_analytics.py        # Czy KPI obliczenia są prawidłowe
```

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

```python
# backend/tests/test_safety_limits.py
import pytest
from app.services.action_executor import validate_action, SafetyViolationError

def test_bid_change_over_50pct_blocked():
    with pytest.raises(SafetyViolationError):
        validate_action("SET_BID", current_val=1.0, new_val=2.0, context={})

def test_bid_change_under_50pct_passes():
    validate_action("SET_BID", current_val=1.0, new_val=1.40, context={})

def test_bid_zero_current_blocked():
    with pytest.raises(SafetyViolationError):
        validate_action("SET_BID", current_val=0, new_val=1.0, context={})

def test_pause_keyword_limit():
    context = {"total_keywords_in_campaign": 100, "keywords_paused_today_in_campaign": 20}
    with pytest.raises(SafetyViolationError):
        validate_action("PAUSE_KEYWORD", current_val=0, new_val=0, context=context)
```

---

## 🟢 B-18: config.py — side effect w property getter

**Priorytet:** DROBNY

### Problem
```python
# OBECNE:
@property
def data_dir(self):
    path = Path("data")
    path.mkdir(exist_ok=True)  # side effect w getterze!
    return path
```

### Poprawka
Przenieś `mkdir` do lifespan event w `main.py`:
```python
# main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(exist_ok=True)  # tutaj
    yield
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ C: PLAN SPRINTÓW (KOLEJNOŚĆ WYKONANIA)
# ═══════════════════════════════════════════════════════

## Sprint 1: Infrastruktura (NAJPIERW — fundament)

```
 1. B-04: Utwórz katalog models/ i rozbij models.py na 7 plików
 2. B-02: Dodaj brakujące modele (ActionLog, Alert, Recommendation)
 3. B-01: Zmień Float → BigInteger (micros) we WSZYSTKICH modelach
 4. B-04: Utwórz katalog schemas/ i rozbij schemas.py + dodaj @computed_field
 5. B-09: Zamień datetime.utcnow → func.now() we wszystkich modelach
 6. B-10: Napraw importy (przenieś na górę plików)
 7. B-04: Utwórz utils/constants.py i utils/formatters.py
```

**Test po Sprint 1:** `python -c "from app.models import *; print('OK')"` — importy działają

## Sprint 2: Serwisy (logika biznesowa)

```
 8. B-03: Utwórz credentials_service.py (keyring wrapper)
 9. B-05: Utwórz action_executor.py (validate_action + revert_action)
10. B-06: Utwórz search_terms_service.py (segmentacja → wyciągnij z routera)
11. B-06: Utwórz analytics_service.py (KPI + anomaly detection)
12. B-07: Napraw formułę ROAS (revenue/cost, nie conversions/cost)
13. B-08: Napraw seed.py (uproszczenie + micros + db.get())
14. B-11: Podłącz ActionExecutor w routerze recommendations.py
```

**Test po Sprint 2:** `python -m pytest tests/test_safety_limits.py` — circuit breaker działa

## Sprint 3: Jakość kodu (tech debt)

```
15. B-12: Dodaj threading.Lock do semantic.py
16. B-13: Napraw cache.py TTL API
17. B-14: Przenieś IRRELEVANT_WORDS do constants.py
18. B-06: Refaktoruj routery — zamień inline logikę na wywołania serwisów
```

## Sprint 4: Testy + drobne poprawki

```
19. B-17: Utwórz tests/ z conftest.py i podstawowymi testami
20. B-15: Dodaj walidację w export.py
21. B-16: Dodaj typowanie generyczne do PaginatedResponse
22. B-18: Przenieś mkdir z config.py property do lifespan
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ D: PLIKI DO UTWORZENIA / ZMODYFIKOWANIA
# ═══════════════════════════════════════════════════════

## NOWE pliki (do utworzenia)

```
backend/app/models/__init__.py
backend/app/models/client.py
backend/app/models/campaign.py
backend/app/models/keyword.py
backend/app/models/search_term.py
backend/app/models/recommendation.py          ← NOWY MODEL
backend/app/models/action_log.py              ← NOWY MODEL
backend/app/models/alert.py                   ← NOWY MODEL

backend/app/schemas/__init__.py
backend/app/schemas/common.py                 ← Enumy: Priority, ActionStatus, Segment
backend/app/schemas/client.py
backend/app/schemas/campaign.py               ← micros→USD @computed_field
backend/app/schemas/recommendation.py
backend/app/schemas/search_term.py

backend/app/services/credentials_service.py   ← ADR-004 (keyring)
backend/app/services/action_executor.py       ← Circuit breaker + revert
backend/app/services/search_terms_service.py  ← Segmentacja
backend/app/services/analytics_service.py     ← KPI + anomaly detection

backend/app/utils/constants.py                ← SAFETY_LIMITS + IRRELEVANT_KEYWORDS
backend/app/utils/formatters.py               ← micros_to_currency(), currency_to_micros()

backend/tests/__init__.py
backend/tests/conftest.py
backend/tests/test_safety_limits.py
backend/tests/test_segmentation.py
backend/tests/test_models.py
```

## Pliki do USUNIĘCIA po migracji

```
backend/app/models.py          → zastąpiony przez models/
backend/app/schemas.py         → zastąpiony przez schemas/
```

## Pliki do CIĘŻKIEJ EDYCJI

```
backend/app/seed.py            → micros + db.get() + uproszczenie
backend/app/main.py            → importy na górę + router rejestracja
backend/app/config.py          → usuń google_ads credentials, napraw data_dir
backend/app/services/google_ads.py → rename na google_ads_client.py + use CredentialsService
backend/app/services/sync_service.py → dodaj Phase 4 (segmentacja) i Phase 5 (anomalie)
backend/app/services/recommendations.py → rename na recommendations_engine.py
backend/app/routers/search_terms.py → wyciągnij logikę do SearchTermsService
backend/app/routers/analytics.py → wyciągnij logikę do AnalyticsService
backend/app/routers/recommendations.py → użyj ActionExecutor zamiast bezpośredniego google_ads
backend/app/routers/actions.py → dodaj endpoint revert + użyj ActionExecutor
```

## Pliki do LEKKIEJ EDYCJI

```
backend/app/services/cache.py    → napraw TTL API
backend/app/services/semantic.py → dodaj Lock
backend/app/routers/export.py    → dodaj walidację istnienia klienta
```

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ E: PODSUMOWANIE PRIORYTETÓW
# ═══════════════════════════════════════════════════════

| Priorytet | Ilość | ID | Opis |
|-----------|-------|----|------|
| 🔴 Krytyczny | 3 | B-01, B-02, B-03 | Float→BigInteger, brakujące modele, credentials_service |
| 🟠 Poważny | 5 | B-04, B-05, B-06, B-07, B-08 | Struktura plików, circuit breaker, serwisy, ROAS, seed.py |
| 🟡 Średni | 6 | B-09→B-14 | deprecated utcnow, importy, audit, thread-safety, cache, hardcoded words |
| 🟢 Drobny | 4 | B-15→B-18 | Walidacja, typowanie, testy, side effects |
| **RAZEM** | **18** | | |

---

# ═══════════════════════════════════════════════════════
# CZĘŚĆ F: CHECKLIST WERYFIKACJI
# ═══════════════════════════════════════════════════════

Po zakończeniu wszystkich sprintów, sprawdź:

### Modele
- [ ] ZERO kolumn typu `Float` dla wartości pieniężnych
- [ ] Wszystkie kolumny pieniężne mają suffix `_micros` i typ `BigInteger`
- [ ] Model `ActionLog` ma `old_value_json`, `reverted_at`, status `REVERTED`
- [ ] Model `Alert` ma `resolved_at`, `alert_type`, `severity`
- [ ] Model `Recommendation` ma `status` (pending/applied/dismissed)
- [ ] `datetime.utcnow` → `func.now()` wszędzie

### Serwisy
- [ ] `credentials_service.py` istnieje i jest JEDYNYM miejscem na tokeny
- [ ] `action_executor.py` ma `validate_action()` + `revert_action()`
- [ ] `validate_action()` blokuje bid change > 50%, budget change > 30%, etc.
- [ ] `search_terms_service.py` ma pełną logikę segmentacji
- [ ] `analytics_service.py` ma KPI + detect_anomalies()
- [ ] ROAS = Revenue / Cost (nie Conversions / Cost)

### Routery
- [ ] ZERO logiki biznesowej w routerach (thin layer)
- [ ] Recommendations router używa `ActionExecutor` (nie bezpośrednio google_ads)
- [ ] Actions router ma endpoint `POST /actions/revert/{id}`
- [ ] Analytics router wywołuje `AnalyticsService`

### Bezpieczeństwo
- [ ] KAŻDY zapis do Google Ads API przechodzi przez `validate_action()`
- [ ] ZERO tokenów w .env, SQLite, lub logach
- [ ] Keyring jest jedynym źródłem credentials
- [ ] Revert nie działa po 24h (ADR-007)
- [ ] ADD_NEGATIVE jest niereversowalne

### Testy
- [ ] `pytest` przechodzi bez błędów
- [ ] validate_action() ma testy dla KAŻDEGO warunku
- [ ] Segmentacja search terms ma testy dla 4 segmentów

---

**KONIEC PLANU NAPRAWCZEGO BACKENDU**
**Rozpocznij od Sprint 1 krok 1: Utwórz models/ katalog i rozbij models.py**
