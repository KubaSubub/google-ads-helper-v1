"""Search Terms / Keyword optimization scripts.

This package contains date-aware optimization scripts that analyze search terms
and keywords and propose (or execute) actions like adding negatives, promoting
to keywords, or adjusting bids.

Each script:
- accepts a `date_from`/`date_to` window and honors it when querying data
- provides a `dry_run` that returns a list of matches with reasons
- provides an `execute` that applies actions for a subset of matches

Scripts are registered at import time. See `register()` + `list_scripts()`.
"""

from typing import Optional

from app.services.scripts.base import (
    ScriptBase,
    ScriptItem,
    ScriptResult,
    ScriptExecuteResult,
)

# Registry — populated at import time below
_REGISTRY: dict[str, ScriptBase] = {}


def register(script_instance: ScriptBase) -> None:
    """Register a script instance. Idempotent — re-registering replaces."""
    _REGISTRY[script_instance.id] = script_instance


def get_script(script_id: str) -> Optional[ScriptBase]:
    return _REGISTRY.get(script_id)


def list_scripts() -> list[ScriptBase]:
    return list(_REGISTRY.values())


# ── Auto-register all scripts ───────────────────────────────────────────────
from app.services.scripts import a1_zero_conv_waste  # noqa: E402, F401
from app.services.scripts import a2_irrelevant_dictionary  # noqa: E402, F401
from app.services.scripts import a3_low_ctr_waste  # noqa: E402, F401
from app.services.scripts import a6_non_latin_script  # noqa: E402, F401
from app.services.scripts import b1_high_conv_promotion  # noqa: E402, F401
from app.services.scripts import c2_duplicate_coverage  # noqa: E402, F401
from app.services.scripts import d1_ngram_waste  # noqa: E402, F401
from app.services.scripts import d3_ngram_audit  # noqa: E402, F401
from app.services.scripts import f1_competitor_term  # noqa: E402, F401

register(a1_zero_conv_waste.ZeroConvWasteScript())
register(a2_irrelevant_dictionary.IrrelevantDictionaryScript())
register(a3_low_ctr_waste.LowCtrWasteScript())
register(a6_non_latin_script.NonLatinScriptScript())
register(b1_high_conv_promotion.HighConvPromotionScript())
register(c2_duplicate_coverage.DuplicateCoverageScript())
register(d1_ngram_waste.NgramWasteScript())
register(d3_ngram_audit.NgramAuditReportScript())
register(f1_competitor_term.CompetitorTermScript())


__all__ = [
    "ScriptBase",
    "ScriptItem",
    "ScriptResult",
    "ScriptExecuteResult",
    "register",
    "get_script",
    "list_scripts",
]
