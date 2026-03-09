"""Canonical action types and mapping from business actions to API actions."""

from enum import Enum


class ActionType(str, Enum):
    PAUSE_KEYWORD = "PAUSE_KEYWORD"
    ENABLE_KEYWORD = "ENABLE_KEYWORD"
    UPDATE_BID = "UPDATE_BID"
    SET_KEYWORD_BID = "SET_KEYWORD_BID"
    PAUSE_AD = "PAUSE_AD"
    ADD_NEGATIVE = "ADD_NEGATIVE"
    ADD_KEYWORD = "ADD_KEYWORD"
    INCREASE_BUDGET = "INCREASE_BUDGET"


BUSINESS_TO_ACTION = {
    "INCREASE_BID": ActionType.UPDATE_BID,
    "DECREASE_BID": ActionType.UPDATE_BID,
    "UPDATE_BID": ActionType.UPDATE_BID,
    "SET_KEYWORD_BID": ActionType.SET_KEYWORD_BID,
    "PAUSE_KEYWORD": ActionType.PAUSE_KEYWORD,
    "ENABLE_KEYWORD": ActionType.ENABLE_KEYWORD,
    "PAUSE_AD": ActionType.PAUSE_AD,
    "ADD_NEGATIVE": ActionType.ADD_NEGATIVE,
    "ADD_KEYWORD": ActionType.ADD_KEYWORD,
    "INCREASE_BUDGET": ActionType.INCREASE_BUDGET,
}


def map_action_type(action_type: str) -> ActionType:
    mapped = BUSINESS_TO_ACTION.get(action_type)
    if mapped is None:
        raise ValueError(f"Unsupported action type: {action_type}")
    return mapped
