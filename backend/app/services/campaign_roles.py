"""Deterministic campaign role classification and override helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
from urllib.parse import urlparse

from app.models.campaign import Campaign
from app.models.client import Client


CAMPAIGN_ROLE_VALUES = (
    "BRAND",
    "GENERIC",
    "PROSPECTING",
    "REMARKETING",
    "PMAX",
    "LOCAL",
    "UNKNOWN",
)

ROLE_SOURCE_AUTO = "AUTO"
ROLE_SOURCE_MANUAL = "MANUAL"

PROTECTION_BY_ROLE = {
    "BRAND": "HIGH",
    "REMARKETING": "HIGH",
    "PMAX": "MEDIUM",
    "LOCAL": "MEDIUM",
    "GENERIC": "LOW",
    "PROSPECTING": "LOW",
    "UNKNOWN": "HIGH",
}

LOCAL_CHANNEL_TYPES = {"LOCAL", "LOCAL_SERVICES"}
LOCAL_TOKENS = {
    "local",
    "lokalna",
    "lokalne",
    "maps",
    "mapy",
    "store",
    "stores",
    "wizyty",
}
REMARKETING_TOKENS = {
    "remarketing",
    "remarketingowa",
    "remarketingowe",
    "remarketingu",
    "retarget",
    "retargeting",
    "rlsa",
}
PROSPECTING_TOKENS = {
    "acq",
    "acquisition",
    "cold",
    "coldtraffic",
    "newcustomer",
    "newcustomers",
    "nonbrand",
    "nonbranded",
    "prospecting",
    "prospectingowa",
    "prospectingowe",
}
BRAND_HINT_TOKENS = {"brand", "branded", "marka"}
NON_BRAND_HINT_TOKENS = {"generic", "non-brand", "nonbrand", "prospecting"}

GENERIC_BRAND_TOKENS = {
    "ads",
    "adwords",
    "brand",
    "campaign",
    "company",
    "com",
    "display",
    "eu",
    "google",
    "helper",
    "home",
    "local",
    "marketing",
    "meble",
    "online",
    "performance",
    "pl",
    "remarketing",
    "retargeting",
    "search",
    "service",
    "services",
    "shop",
    "shopping",
    "sklep",
    "store",
    "video",
    "you",
}

STOPWORDS = {
    "and",
    "dla",
    "group",
    "helper",
    "kampania",
    "kampanie",
    "of",
    "or",
    "the",
    "www",
}


@dataclass(frozen=True)
class RoleClassification:
    role: str
    confidence: float
    matched_signals: list[str]


def normalize_role(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    if normalized not in CAMPAIGN_ROLE_VALUES:
        raise ValueError(f"Unsupported campaign role: {value}")
    return normalized


def normalize_role_source(value: str | None) -> str:
    return ROLE_SOURCE_MANUAL if str(value or "").upper() == ROLE_SOURCE_MANUAL else ROLE_SOURCE_AUTO


def protection_level_for_role(role: str | None) -> str:
    return PROTECTION_BY_ROLE.get(normalize_role(role) or "UNKNOWN", "HIGH")


def _ascii_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii")


def normalize_text(value: str | None) -> str:
    text = _ascii_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: str | None) -> str:
    return normalize_text(value).replace(" ", "")


def tokenize(value: str | None) -> list[str]:
    normalized = normalize_text(value)
    return [token for token in normalized.split() if token]


def _extract_domain_parts(website: str | None) -> tuple[list[str], str]:
    if not website:
        return ([], "")
    parsed = urlparse(website if "://" in website else f"https://{website}")
    hostname = (parsed.netloc or parsed.path or "").lower().strip()
    hostname = hostname.split("@")[-1]
    hostname = hostname.split(":")[0]
    if hostname.startswith("www."):
        hostname = hostname[4:]
    domain_ascii = _ascii_text(hostname)
    parts = [part for part in re.split(r"[^a-z0-9]+", domain_ascii.lower()) if part]
    return (parts, compact_text(domain_ascii))


def _is_brand_token(token: str) -> bool:
    if len(token) < 4:
        return False
    if token in STOPWORDS or token in GENERIC_BRAND_TOKENS:
        return False
    if token.isdigit():
        return False
    return True


@lru_cache(maxsize=512)
def _tokenize_cached(value: str) -> tuple[str, ...]:
    return tuple(tokenize(value))


def extract_brand_signals(client: Client | None) -> tuple[set[str], set[str]]:
    if not client:
        return (set(), set())

    name_tokens = {token for token in _tokenize_cached(str(client.name or "")) if _is_brand_token(token)}
    domain_tokens, compact_domain = _extract_domain_parts(getattr(client, "website", None))
    domain_tokens = {token for token in domain_tokens if _is_brand_token(token)}

    compact_name = compact_text(client.name or "")
    phrases = {
        phrase
        for phrase in {compact_name, compact_domain}
        if len(phrase) >= 5 and phrase not in GENERIC_BRAND_TOKENS
    }
    return (name_tokens | domain_tokens, phrases)


def classify_campaign_role(campaign: Campaign, client: Client | None = None) -> RoleClassification:
    campaign_type = str(campaign.campaign_type or "").upper()
    name_tokens = set(tokenize(campaign.name))
    compact_name = compact_text(campaign.name)

    if campaign_type in LOCAL_CHANNEL_TYPES or LOCAL_TOKENS.intersection(name_tokens):
        return RoleClassification(role="LOCAL", confidence=0.95, matched_signals=["campaign_type_or_name"])

    if campaign_type == "PERFORMANCE_MAX":
        return RoleClassification(role="PMAX", confidence=0.95, matched_signals=["campaign_type"])

    candidates: list[tuple[str, float, str]] = []

    if REMARKETING_TOKENS.intersection(name_tokens):
        candidates.append(("REMARKETING", 0.85, "remarketing_tokens"))

    brand_tokens, brand_phrases = extract_brand_signals(client)
    if not NON_BRAND_HINT_TOKENS.intersection(name_tokens):
        matched_brand_tokens = brand_tokens.intersection(name_tokens)
        matched_brand_phrase = next((phrase for phrase in brand_phrases if phrase and phrase in compact_name), None)
        if matched_brand_tokens or matched_brand_phrase or BRAND_HINT_TOKENS.intersection(name_tokens):
            candidates.append(("BRAND", 0.85, "brand_tokens"))

    if PROSPECTING_TOKENS.intersection(name_tokens):
        candidates.append(("PROSPECTING", 0.85, "prospecting_tokens"))

    if candidates:
        ordered = ["REMARKETING", "BRAND", "PROSPECTING"]
        by_role = {role: (confidence, signal) for role, confidence, signal in candidates}
        chosen_role = next(role for role in ordered if role in by_role)
        confidence, signal = by_role[chosen_role]
        if len({role for role, _, _ in candidates}) > 1:
            confidence = max(0.40, round(confidence - 0.20, 2))
        return RoleClassification(role=chosen_role, confidence=confidence, matched_signals=[signal])

    if campaign_type == "SEARCH":
        return RoleClassification(role="GENERIC", confidence=0.65, matched_signals=["search_fallback"])

    return RoleClassification(role="UNKNOWN", confidence=0.30, matched_signals=["unknown"])


def apply_role_classification(campaign: Campaign, client: Client | None = None) -> bool:
    classification = classify_campaign_role(campaign, client)
    changed = False

    if campaign.campaign_role_auto != classification.role:
        campaign.campaign_role_auto = classification.role
        changed = True

    if campaign.role_confidence != classification.confidence:
        campaign.role_confidence = classification.confidence
        changed = True

    role_source = normalize_role_source(getattr(campaign, "role_source", None))
    if role_source != getattr(campaign, "role_source", None):
        campaign.role_source = role_source
        changed = True

    if role_source == ROLE_SOURCE_MANUAL and campaign.campaign_role_final:
        final_role = normalize_role(campaign.campaign_role_final) or classification.role
    else:
        final_role = classification.role
        if campaign.campaign_role_final != final_role:
            campaign.campaign_role_final = final_role
            changed = True
        if campaign.role_source != ROLE_SOURCE_AUTO:
            campaign.role_source = ROLE_SOURCE_AUTO
            changed = True

    protection = protection_level_for_role(final_role)
    if campaign.protection_level != protection:
        campaign.protection_level = protection
        changed = True

    return changed


def apply_manual_role_override(campaign: Campaign, role: str | None, client: Client | None = None) -> None:
    classification = classify_campaign_role(campaign, client)

    if campaign.campaign_role_auto != classification.role:
        campaign.campaign_role_auto = classification.role
    if campaign.role_confidence != classification.confidence:
        campaign.role_confidence = classification.confidence

    normalized_role = normalize_role(role)
    if normalized_role is None or normalized_role == classification.role:
        campaign.campaign_role_final = classification.role
        campaign.role_source = ROLE_SOURCE_AUTO
    else:
        campaign.campaign_role_final = normalized_role
        campaign.role_source = ROLE_SOURCE_MANUAL

    campaign.protection_level = protection_level_for_role(campaign.campaign_role_final)


def ensure_campaign_roles(campaigns: Iterable[Campaign], client: Client | None = None) -> bool:
    changed = False
    for campaign in campaigns:
        changed = apply_role_classification(campaign, client) or changed
    return changed
