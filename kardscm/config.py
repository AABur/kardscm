"""Language configuration management."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from kardscm.locales import LANGUAGE_EN, LANGUAGES, LanguageConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"

__all__ = ["LanguageConfig", "get_language_config", "CONFIG_FILE"]


def get_language_config(config_path: str = CONFIG_FILE) -> LanguageConfig:
    """Load language configuration from config.ini.

    Returns:
        LanguageConfig for the configured language. Defaults to English.
    """
    path = Path(config_path)

    if not path.exists():
        return LANGUAGE_EN

    config = configparser.ConfigParser()
    config.read(path)

    code = config.get("settings", "language", fallback="en").strip().lower()
    if code not in LANGUAGES:
        logger.warning("Unsupported language '%s', falling back to English", code)
        return LANGUAGE_EN

    return LANGUAGES[code]
