"""Conversion helpers for micros ↔ currency.

Google Ads API returns all monetary values in micros (1 USD = 1,000,000 micros).
We store micros as BigInteger in DB.
We convert to float ONLY in Pydantic schemas for API responses.
"""


def micros_to_currency(micros: int) -> float:
    """Convert micros (BigInteger) to float for display.

    Args:
        micros: Amount in micros (e.g., 1_500_000)

    Returns:
        Amount in USD/currency (e.g., 1.50)

    Example:
        >>> micros_to_currency(1_500_000)
        1.5
    """
    return round((micros or 0) / 1_000_000, 2)


def currency_to_micros(amount: float) -> int:
    """Convert float amount to micros for storage.

    Args:
        amount: Amount in USD/currency (e.g., 1.50)

    Returns:
        Amount in micros (e.g., 1_500_000)

    Example:
        >>> currency_to_micros(1.50)
        1500000
    """
    return int(round(amount * 1_000_000))
