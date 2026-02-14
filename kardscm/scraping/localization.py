"""Localization and text processing for card data."""

from __future__ import annotations

import logging
import re

import httpx

from kardscm.config import LanguageConfig
from kardscm.constants import BASE_URL, KNOWN_MAPPINGS

logger = logging.getLogger(__name__)

ESCAPE_RE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|r|n|t|\\|\"|')")

EN_FALLBACK_KEYS = ("en", "en-EN")


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


def extract_localized_field(
    field_data: dict[str, str] | str,
    lang_config: LanguageConfig,
    field_name: str = "",
) -> str:
    """Extract localized field value with fallback logic.

    Priority: configured language -> English -> empty string.

    Args:
        field_data: Dictionary with language codes as keys or string value.
        lang_config: Language configuration.
        field_name: Field name for debug logging.

    Returns:
        Localized string value or empty string if not found.
    """
    if not isinstance(field_data, dict):
        return str(field_data) if field_data else ""

    for key in lang_config.keys:
        if key in field_data:
            return field_data[key]

    for key in EN_FALLBACK_KEYS:
        if key in field_data:
            logger.debug(
                "%s not available in %s, using English fallback",
                field_name,
                lang_config.name,
            )
            return field_data[key]

    return ""


def translate_value(
    category: str,
    value: str,
    translations: dict[str, str],
) -> str:
    """Translate a value using loaded translations.

    Args:
        category: Category name (type, faction, rarity, set).
        value: Original value from API.
        translations: Translation dictionary.

    Returns:
        Translated value or original if not found.
    """
    if not value:
        return ""

    normalized = value.strip()
    category_map = KNOWN_MAPPINGS.get(category, {})
    trans_id = category_map.get(normalized)

    if not trans_id:
        for key, tid in category_map.items():
            if key.lower() == normalized.lower():
                trans_id = tid
                break

    if trans_id and trans_id in translations:
        translated = decode_escapes(translations[trans_id])
        return translated

    return normalized


async def load_translations(lang_config: LanguageConfig) -> dict[str, str]:
    """Load translations from website JS files.

    Args:
        lang_config: Language configuration.

    Returns:
        Translation dictionary for the configured language.
    """
    logger.info("Loading translations for %s...", lang_config.name)
    translations: dict[str, str] = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(lang_config.collection_url)
            html = response.text

            js_urls = re.findall(r'/_next/static/chunks/[^"\']+\.js', html)
            translation_content = ""
            for js_url in js_urls:
                if "2840-" in js_url:
                    js_response = await client.get(f"{BASE_URL}{js_url}")
                    translation_content = js_response.text
                    break

            if translation_content:
                translations = _parse_translations(
                    translation_content, lang_config.lang_index
                )
                logger.info("Loaded %s translation keys", len(translations))
            else:
                logger.warning("Translation JS file not found, using fallback")

    except Exception as exc:
        logger.warning("Failed to load translations dynamically: %s", exc)
        logger.info("Using fallback translations")

    return translations


def _parse_translations(js_content: str, lang_index: int) -> dict[str, str]:
    """Parse translations from JS content.

    Args:
        js_content: JavaScript file content.
        lang_index: Index of target language in translations array.

    Returns:
        Mapping from translation ID to localized text.
    """
    translations: dict[str, str] = {}

    all_ids: set[str] = set()
    for category_mappings in KNOWN_MAPPINGS.values():
        all_ids.update(category_mappings.values())

    for trans_id in all_ids:
        pattern = re.compile(rf'"{re.escape(trans_id)}":"([^"]*)"')
        matches = pattern.findall(js_content)

        if matches and lang_index < len(matches):
            translations[trans_id] = matches[lang_index]
        elif matches:
            translations[trans_id] = matches[-1]

    return translations
