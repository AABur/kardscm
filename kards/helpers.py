"""Utility helper functions."""

from __future__ import annotations


def parse_int(value: str | None) -> int | None:
    """Parse string to integer, returning None on failure.

    Args:
        value: String value to parse.

    Returns:
        Parsed integer or None.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def to_text(value: object | None) -> str:
    """Convert value to string, returning empty string for None.

    Args:
        value: Value to convert.

    Returns:
        String representation or empty string.
    """
    if value is None:
        return ""
    return str(value)
