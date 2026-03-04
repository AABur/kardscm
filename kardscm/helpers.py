"""Utility helper functions."""

from __future__ import annotations

import re

ESCAPE_RE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|r|n|t|\\|\"|')")


def parse_int(value: str | int | None) -> int | None:
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


def decode_escapes(text: str) -> str:
    """Decode common escape sequences without altering other characters.

    Args:
        text: Text possibly containing escape sequences.

    Returns:
        Text with escape sequences decoded.
    """
    if not text:
        return text

    _simple_escapes = {"r": "\r", "n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'"}

    def replace_match(match: re.Match[str]) -> str:
        token = match.group(1)
        if token in _simple_escapes:
            return _simple_escapes[token]
        if token[0] in "xuU":
            return chr(int(token[1:], 16))
        return match.group(0)

    return ESCAPE_RE.sub(replace_match, text)


def sanitize_text(text: str) -> str:
    """Sanitize text by decoding escapes and normalizing whitespace.

    Args:
        text: Text to sanitize.

    Returns:
        Sanitized text with escape sequences decoded, newlines replaced
        with spaces, and duplicate spaces removed.
    """
    if not text:
        return text
    text = decode_escapes(text)
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    return text
