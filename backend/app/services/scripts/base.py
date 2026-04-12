"""Base classes and dataclasses for optimization scripts."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session


# ── Category constants (for UI grouping) ────────────────────────────────────
CATEGORY_WASTE = "waste_elimination"
CATEGORY_EXPANSION = "expansion"
CATEGORY_MATCH_TYPE = "match_type"
CATEGORY_NGRAM = "ngram"
CATEGORY_TEMPORAL = "temporal"
CATEGORY_BRAND = "brand"

CATEGORY_LABELS_PL = {
    CATEGORY_WASTE: "Eliminacja marnotrawstwa",
    CATEGORY_EXPANSION: "Rozszerzenie",
    CATEGORY_MATCH_TYPE: "Match Type Optimization",
    CATEGORY_NGRAM: "N-gram Analysis",
    CATEGORY_TEMPORAL: "Temporal / Trending",
    CATEGORY_BRAND: "Brand / Competitor",
}

# ── Action type constants ───────────────────────────────────────────────────
ACTION_NEGATIVE = "NEGATIVE"       # add as negative keyword
ACTION_KEYWORD = "KEYWORD"         # promote search term to keyword
ACTION_BID_INCREASE = "BID_UP"     # raise bid
ACTION_BID_DECREASE = "BID_DOWN"   # lower bid
ACTION_ALERT = "ALERT"             # view-only, no auto-action


@dataclass
class ScriptItem:
    """One match produced by a dry-run."""

    id: Any                 # unique identifier (usually search_term_id)
    entity_name: str        # display name (search term text or keyword)
    campaign_id: Optional[int]
    campaign_name: str
    reason: str             # human-readable why this matched
    metrics: dict           # clicks, impressions, cost_pln, conversions, ctr...
    estimated_savings_pln: float = 0.0
    action_payload: dict = field(default_factory=dict)  # data needed to execute


@dataclass
class ScriptResult:
    """Dry-run output — list of matches + aggregated summary."""

    script_id: str
    total_matching: int
    items: list[ScriptItem]
    estimated_savings_pln: float = 0.0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ScriptExecuteResult:
    """Execute output — counts + per-item status for UI."""

    script_id: str
    applied: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    applied_items: list[dict] = field(default_factory=list)
    # Set when _validate_batch trims the batch because a daily safety cap
    # was reached. Frontend uses this to render a dedicated toast instead of
    # parsing a freetext error message.
    circuit_breaker_limit: Optional[int] = None


class ScriptBase:
    """Base class for optimization scripts.

    Subclasses must override class attributes (id, name, category, ...) and
    implement `dry_run` and `execute`. Default params are merged with user
    overrides at call time — always read from the `params` dict inside the
    method, not from `self.default_params`.
    """

    # Override in subclass
    id: str = ""
    name: str = ""                     # Polish user-facing label
    category: str = ""                 # one of CATEGORY_*
    description: str = ""              # Polish short description
    action_type: str = ""              # one of ACTION_*
    default_params: dict = {}

    def dry_run(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
    ) -> ScriptResult:
        raise NotImplementedError

    def execute(
        self,
        db: Session,
        client_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        params: Optional[dict] = None,
        item_ids: Optional[list[Any]] = None,
    ) -> ScriptExecuteResult:
        raise NotImplementedError

    def to_catalog_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "category_label": CATEGORY_LABELS_PL.get(self.category, self.category),
            "description": self.description,
            "action_type": self.action_type,
            "default_params": self.default_params,
        }

    def _validate_batch(
        self,
        db: Session,
        client_id: int,
        action_type: str,
        requested_count: int,
    ) -> tuple[int, Optional[str], Optional[int]]:
        """Enforce daily safety caps on batched mutations.

        Counts ActionLog entries logged SUCCESS today (local day boundary) for
        this client and the given action_type, compares against the effective
        SAFETY_LIMITS, and returns how many new actions may still be applied.

        Day boundary is local time (matches the desktop tool's Polish target
        market) so a specialist working past UTC midnight does not get a
        fresh daily quota in the same Warsaw business day.

        Returns:
            (allowed_count, error_message, cap)
            - allowed_count: 0..requested_count — how many items to push
            - error_message: None if nothing trimmed; otherwise a user-facing
              message explaining which limit kicked in
            - cap: the configured daily limit when a cap applies, else None
        """
        if requested_count <= 0:
            return 0, None, None

        from app.models.action_log import ActionLog
        from app.models.client import Client
        from app.services.action_executor import get_effective_limits
        from app.utils.constants import SAFETY_LIMITS

        client = db.get(Client, client_id)
        client_limits = None
        if client and client.business_rules:
            client_limits = (client.business_rules or {}).get("safety_limits")
        limits = get_effective_limits(client_limits)

        limit_key = None
        if action_type == "ADD_NEGATIVE":
            limit_key = "MAX_NEGATIVES_PER_DAY"
        elif action_type == "ADD_KEYWORD":
            # No dedicated daily cap today — use MAX_ACTIONS_PER_BATCH as a
            # rolling day cap so runaway promotions cannot flood the API.
            limit_key = "MAX_ACTIONS_PER_BATCH"

        if not limit_key:
            return requested_count, None, None

        limit = limits.get(limit_key, SAFETY_LIMITS.get(limit_key, 0))
        if limit <= 0:
            return requested_count, None, None

        start_of_day = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        applied_today = (
            db.query(ActionLog)
            .filter(
                ActionLog.client_id == client_id,
                ActionLog.action_type == action_type,
                ActionLog.status == "SUCCESS",
                ActionLog.execution_mode == "LIVE",
                ActionLog.executed_at >= start_of_day,
            )
            .count()
        )

        remaining = max(0, limit - applied_today)
        if requested_count <= remaining:
            return requested_count, None, None

        msg = (
            f"Dzienny limit {limit_key} osiągnięty: {applied_today}/{limit}. "
            f"Zastosowano {remaining} z {requested_count} akcji — pozostałe zostaną dostępne jutro."
        )
        return remaining, msg, int(limit)
