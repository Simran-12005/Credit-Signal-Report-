"""Small date helpers shared by scoring and feature building."""

from datetime import date


def parse_date(value: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD), tolerating extra time components.

    Returns None on missing/unparseable input — callers treat that as "signal absent".
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def age_years(value: str | None, *, as_of: date | None = None) -> float | None:
    """Whole-ish age in years from an ISO date to `as_of` (today by default)."""
    d = parse_date(value)
    if d is None:
        return None
    ref = as_of or date.today()
    return round(max(0.0, (ref - d).days / 365.25), 1)
