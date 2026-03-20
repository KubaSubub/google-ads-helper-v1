"""Date resolution utilities for consistent filtering across endpoints."""

from datetime import date, timedelta


def resolve_dates(
    days: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    default_days: int = 30,
) -> tuple[date, date]:
    """Resolve date range from either explicit dates or lookback days.

    Priority: date_from/date_to > days > default_days.
    """
    if date_from and date_to:
        return date_from, date_to
    lookback = days or default_days
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=lookback))
    return start, end
