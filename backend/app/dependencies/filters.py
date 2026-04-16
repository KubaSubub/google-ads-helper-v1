"""Canonical filter contract for data endpoints.

Every data-returning endpoint that filters by client / date / campaign uses
`Depends(common_filters)` to get a `CommonFilters` value object. This keeps
parameter names, types, and defaults identical across the API surface.

Adding a new filter endpoint: declare `filters: CommonFilters = Depends(common_filters)`
as the first argument. Do NOT re-declare `client_id`, `date_from`, `date_to`,
`campaign_type`, or `campaign_status` as top-level Query params.

Legacy support:
- `days` param is accepted and resolved into `date_from`/`date_to` via `resolve_dates()`.
- `status` param is accepted as a deprecated alias for `campaign_status` — prefer the latter.
- Value "ALL" (case-insensitive) on `campaign_type`/`campaign_status` is normalized to None.
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Optional

from fastapi import Query

from app.utils.date_utils import resolve_dates


@dataclass(frozen=True)
class CommonFilters:
    """Canonical filter bundle for data endpoints.

    Fields are normalized:
    - dates always resolved (never both None)
    - campaign_type/campaign_status uppercase or None (no "ALL" sentinel)
    - client_id optional (endpoint decides if required via campaign_id fallback)
    """

    client_id: Optional[int]
    date_from: date
    date_to: date
    campaign_type: Optional[str]
    campaign_status: Optional[str]
    campaign_id: Optional[int]
    ad_group_id: Optional[int]
    dates_explicit: bool  # True when caller sent days/date_from/date_to; False when falling back to default

    @property
    def period_days(self) -> int:
        return (self.date_to - self.date_from).days


def _normalize_enum(value: Optional[str]) -> Optional[str]:
    """Normalize campaign_type / campaign_status — strip, uppercase, drop 'ALL'."""
    if not value:
        return None
    v = value.strip().upper()
    if v in ("", "ALL"):
        return None
    return v


def common_filters(
    client_id: Annotated[Optional[int], Query(description="Client ID")] = None,
    days: Annotated[Optional[int], Query(ge=1, le=365, description="Lookback days (fallback when date_from/date_to not given)")] = None,
    date_from: Annotated[Optional[date], Query(description="Start date (ISO 8601)")] = None,
    date_to: Annotated[Optional[date], Query(description="End date (ISO 8601)")] = None,
    campaign_type: Annotated[Optional[str], Query(description="SEARCH, PERFORMANCE_MAX, etc. or None for all")] = None,
    campaign_status: Annotated[Optional[str], Query(description="ENABLED, PAUSED, REMOVED or None for all")] = None,
    status: Annotated[Optional[str], Query(include_in_schema=False, description="DEPRECATED alias for campaign_status")] = None,
    campaign_id: Annotated[Optional[int], Query(description="Narrow to a single campaign")] = None,
    ad_group_id: Annotated[Optional[int], Query(description="Narrow to a single ad group")] = None,
) -> CommonFilters:
    """Canonical filter parser — use as `Depends(common_filters)`."""
    dates_explicit = (days is not None) or (date_from is not None) or (date_to is not None)
    start, end = resolve_dates(days, date_from, date_to)
    return CommonFilters(
        client_id=client_id,
        date_from=start,
        date_to=end,
        campaign_type=_normalize_enum(campaign_type),
        campaign_status=_normalize_enum(campaign_status or status),
        campaign_id=campaign_id,
        ad_group_id=ad_group_id,
        dates_explicit=dates_explicit,
    )
