"""Centralized sync phase registry and presets.

Every sync phase is described here with metadata used by the SSE trigger,
the sync modal (frontend), and the incremental date resolution logic.
"""

from __future__ import annotations

# Pattern A = structural snapshot (no date range, always full fetch)
# Pattern B = time-series metrics (date_from / date_to)
# Pattern C = special (change_events, days param, API-capped)

PHASE_REGISTRY: dict[str, dict] = {
    # ── Structure ───────────────────────────────────────────────────
    "campaigns":           {"pattern": "A", "label": "Kampanie",                "group": "structure",  "max_days": None,  "critical": True},
    "impression_share":    {"pattern": "A", "label": "Impression share",        "group": "structure",  "max_days": 30,    "critical": False},
    "ad_groups":           {"pattern": "A", "label": "Grupy reklam",            "group": "structure",  "max_days": None,  "critical": True},
    "keywords":            {"pattern": "A", "label": "Słowa kluczowe",          "group": "structure",  "max_days": None,  "critical": True,  "depends_on": "ad_groups"},
    "negative_keywords":   {"pattern": "A", "label": "Wykluczenia",             "group": "structure",  "max_days": None,  "critical": False, "depends_on": "ad_groups"},
    # ── Metrics ─────────────────────────────────────────────────────
    "keyword_daily":       {"pattern": "B", "label": "Metryki słów kluczowych", "group": "metrics",    "max_days": 1095,  "critical": False, "depends_on": "keywords"},
    "daily_metrics":       {"pattern": "B", "label": "Metryki kampanii",        "group": "metrics",    "max_days": 1095,  "critical": False},
    "search_terms":        {"pattern": "B", "label": "Wyszukiwane frazy",       "group": "metrics",    "max_days": 180,   "critical": False, "depends_on": "ad_groups"},
    "pmax_terms":          {"pattern": "B", "label": "Frazy PMax",              "group": "metrics",    "max_days": 180,   "critical": False},
    "device_metrics":      {"pattern": "B", "label": "Metryki urządzeń",        "group": "metrics",    "max_days": 1095,  "critical": False},
    "geo_metrics":         {"pattern": "B", "label": "Metryki geograficzne",    "group": "metrics",    "max_days": 1095,  "critical": False},
    # ── Enrichment ──────────────────────────────────────────────────
    "change_events":       {"pattern": "C", "label": "Historia zmian",          "group": "enrichment", "max_days": 28,    "critical": False},
    "conversion_actions":  {"pattern": "A", "label": "Konwersje",               "group": "enrichment", "max_days": None,  "critical": False},
    "age_metrics":         {"pattern": "B", "label": "Metryki wiekowe",         "group": "enrichment", "max_days": 1095,  "critical": False},
    "gender_metrics":      {"pattern": "B", "label": "Metryki płci",            "group": "enrichment", "max_days": 1095,  "critical": False},
    # ── PMax ────────────────────────────────────────────────────────
    "pmax_channel_metrics":{"pattern": "B", "label": "Kanały PMax",             "group": "pmax",       "max_days": 1095,  "critical": False},
    "asset_groups":        {"pattern": "A", "label": "Asset groups",            "group": "pmax",       "max_days": None,  "critical": False},
    "asset_group_daily":   {"pattern": "B", "label": "Asset group daily",       "group": "pmax",       "max_days": 1095,  "critical": False},
    "asset_group_assets":  {"pattern": "A", "label": "Assety grup",             "group": "pmax",       "max_days": None,  "critical": False},
    "asset_group_signals": {"pattern": "A", "label": "Sygnały grup",            "group": "pmax",       "max_days": None,  "critical": False},
    "campaign_audiences":  {"pattern": "B", "label": "Odbiorcy kampanii",       "group": "pmax",       "max_days": 1095,  "critical": False},
    "campaign_assets":     {"pattern": "A", "label": "Assety kampanii",         "group": "pmax",       "max_days": None,  "critical": False},
}

# Ordered list of phase names (execution order matches current sync.py)
PHASE_ORDER: list[str] = list(PHASE_REGISTRY.keys())

# Group labels for UI
GROUP_LABELS = {
    "structure":  "Struktura",
    "metrics":    "Metryki",
    "enrichment": "Wzbogacanie",
    "pmax":       "PMax",
}

# Presets
_ALL_PHASES = PHASE_ORDER
_METRICS_PHASES = [k for k, v in PHASE_REGISTRY.items() if v["pattern"] in ("B", "C")]

SYNC_PRESETS: dict[str, dict] = {
    "full": {
        "label": "Pełny sync",
        "description": "Wszystkie dane, maksymalny zakres wg limitów API",
        "phases": _ALL_PHASES,
        "mode": "full",
    },
    "incremental": {
        "label": "Aktualizacja",
        "description": "Uzupełnij od ostatniego sync do wczoraj",
        "phases": _ALL_PHASES,
        "mode": "incremental",
    },
    "quick": {
        "label": "Szybka aktualizacja",
        "description": "Ostatnie 7 dni, wszystkie fazy",
        "phases": _ALL_PHASES,
        "mode": "fixed",
        "days": 7,
    },
    "metrics_only": {
        "label": "Tylko metryki",
        "description": "Metryki bez struktury, od ostatniego sync",
        "phases": _METRICS_PHASES,
        "mode": "incremental",
    },
}
