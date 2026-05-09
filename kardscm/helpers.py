"""Utility helper functions."""

from __future__ import annotations

import json
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


def extract_locale(
    raw: object,
    locale_key: str,
    *,
    default: str = "",
    en_fallback: bool = False,
) -> str:
    """Decode a locale-keyed JSON blob and return the value for ``locale_key``.

    Args:
        raw: The JSON-encoded locale dict, typically the value of a
            locale-keyed DB column. Empty/None returns ``default``.
            Non-string values are converted via ``str()``.
        locale_key: Locale key (e.g. ``"ru-RU"``) to look up in the
            decoded dict.
        default: Returned on empty input, decode failure, non-dict
            shape, or when neither ``locale_key`` nor (optionally)
            ``"en-EN"`` is present.
        en_fallback: When True, fall back to ``"en-EN"`` if
            ``locale_key`` is missing or its value is empty. Default
            False so accidental adoption at a new call site does not
            silently change semantics.

    Returns:
        The locale-specific string, the en-EN fallback, or ``default``.
    """
    if not raw:
        return default
    if not isinstance(raw, str):
        return str(raw)
    try:
        decoded = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default
    if not isinstance(decoded, dict):
        return default
    value = decoded.get(locale_key)
    if value:
        return str(value)
    if en_fallback:
        en_value = decoded.get("en-EN")
        if en_value:
            return str(en_value)
    return default


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
