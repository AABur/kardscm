"""Language configuration management."""

from __future__ import annotations

import logging

from kardscm.locales import LANGUAGE_EN, LANGUAGES, LanguageConfig

logger = logging.getLogger(__name__)

__all__ = ["LanguageConfig", "get_language_config"]


def get_language_config(lang: str | None = None) -> LanguageConfig:
    """Return the LanguageConfig for the given code.

    Args:
        lang: Language code (e.g. "en", "ru", "zh-Hant"). When None or empty,
            English is returned. Unknown codes log a warning and fall back
            to English.

    Returns:
        LanguageConfig from the registry, or LANGUAGE_EN as a fallback.
    """
    code = (lang or "en").strip()
    if not code:
        return LANGUAGE_EN
    if code not in LANGUAGES:
        logger.warning("Unsupported language '%s', falling back to English", code)
        return LANGUAGE_EN
    return LANGUAGES[code]
