"""Safety limits and constants — centralized config.

These constants are used by:
- action_executor.py: validate_action() circuit breaker
- recommendations_engine.py: rule thresholds
"""

SAFETY_LIMITS = {
    "MAX_BID_CHANGE_PCT": 0.50,        # Max 50% bid change per action
    "MIN_BID_USD": 0.10,               # Minimum bid in USD
    "MAX_BID_USD": 100.00,             # Maximum bid in USD
    "MAX_BUDGET_CHANGE_PCT": 0.30,     # Max 30% budget change per action
    "MAX_KEYWORD_PAUSE_PCT": 0.20,     # Max 20% keywords paused/day/campaign
    "MAX_NEGATIVES_PER_DAY": 100,      # Max negative keywords added per day
    "MAX_ACTIONS_PER_BATCH": 50,       # Max actions in one batch

    # Recommendation thresholds
    "PAUSE_KEYWORD_MIN_CLICKS": 10,    # Min clicks before pause recommendation
    "ADD_KEYWORD_MIN_CONV": 3,         # Min conversions to add as keyword
    "ADD_NEGATIVE_MIN_CLICKS": 5,      # Min clicks to add as negative
    "HIGH_PERFORMER_CVR_MULTIPLIER": 1.5,  # CVR must be 1.5× campaign avg
    "LOW_PERFORMER_CPA_MULTIPLIER": 2.0,   # CPA must be 2× campaign avg
}

IRRELEVANT_KEYWORDS = [
    # Polish irrelevant terms
    "darmowe",
    "free",
    "za darmo",
    "recenzja",
    "opinie",
    "jak",
    "co to",
    "wikipedia",
    "forum",
    "allegro",
    "olx",
    "youtube",
    "pdf",
    "praca",
    "oferta pracy",
    # Add more as needed
]
