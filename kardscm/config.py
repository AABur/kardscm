"""Language configuration management."""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass, field
from pathlib import Path

from kardscm.constants import BASE_URL

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"


@dataclass(frozen=True)
class LanguageConfig:
    """Language-specific configuration."""

    code: str
    name: str
    keys: tuple[str, ...]
    lang_index: int
    collection_url: str
    export_headers: list[str] = field(default_factory=list)
    faction_names: dict[str, str] = field(default_factory=dict)
    deck_nation_to_db: dict[str, str] = field(default_factory=dict)
    nation_display_names: dict[str, str] = field(default_factory=dict)
    deck_headers: list[str] = field(default_factory=list)
    deck_metadata_labels: list[str] = field(default_factory=list)
    collection_sheet_name: str = "Collection"


LANGUAGE_EN = LanguageConfig(
    code="en",
    name="English",
    keys=("en", "en-EN"),
    lang_index=0,
    collection_url=f"{BASE_URL}/en/decks/collection",
    export_headers=[
        "Nation",
        "Name",
        "Type",
        "Rarity",
        "Abilities",
        "Set",
        "Quantity",
        "Credits",
        "Attack",
        "Defense",
        "Description",
    ],
    faction_names={
        "Soviet": "Soviet Union",
        "USA": "USA",
        "Britain": "Britain",
        "Germany": "Germany",
        "Japan": "Japan",
        "France": "France",
        "Italy": "Italy",
        "Poland": "Poland",
        "Finland": "Finland",
    },
    deck_nation_to_db={
        "soviet": "Soviet Union",
        "usa": "USA",
        "britain": "Britain",
        "germany": "Germany",
        "japan": "Japan",
        "france": "France",
        "italy": "Italy",
        "poland": "Poland",
        "finland": "Finland",
    },
    nation_display_names={
        "soviet": "Soviet",
        "usa": "American",
        "britain": "British",
        "germany": "German",
        "japan": "Japanese",
        "france": "French",
        "italy": "Italian",
        "poland": "Polish",
        "finland": "Finnish",
    },
    deck_headers=["Card", "Type", "Quantity", "Credits", "Attack", "Defense"],
    deck_metadata_labels=["Name", "Major power", "Ally", "HQ", "Code"],
    collection_sheet_name="Collection",
)


LANGUAGE_RU = LanguageConfig(
    code="ru",
    name="Russian",
    keys=("ru", "ru-RU"),
    lang_index=9,
    collection_url=f"{BASE_URL}/ru/decks/collection",
    export_headers=[
        "Нация",
        "Название",
        "Тип",
        "Редкость",
        "Способности",
        "Сет",
        "Количество",
        "Кредиты",
        "Атака",
        "Защита",
        "Описание",
    ],
    faction_names={
        "Soviet": "Советский Союз",
        "USA": "США",
        "Britain": "Великобритания",
        "Germany": "Германия",
        "Japan": "Япония",
        "France": "Франция",
        "Italy": "Италия",
        "Poland": "Польша",
        "Finland": "Финляндия",
    },
    deck_nation_to_db={
        "soviet": "Советский Союз",
        "usa": "США",
        "britain": "Великобритания",
        "germany": "Германия",
        "japan": "Япония",
        "france": "Франция",
        "italy": "Италия",
        "poland": "Польша",
        "finland": "Финляндия",
    },
    nation_display_names={
        "soviet": "Советские",
        "usa": "Американские",
        "britain": "Британские",
        "germany": "Германские",
        "japan": "Японские",
        "france": "Французские",
        "italy": "Итальянские",
        "poland": "Польские",
    },
    deck_headers=["Карта", "Тип", "Количество", "Кредиты", "Атака", "Защита"],
    deck_metadata_labels=[
        "Название",
        "Основная нация",
        "Союзная нация",
        "Штаб",
        "Код",
    ],
    collection_sheet_name="Коллекция",
)


LANGUAGES: dict[str, LanguageConfig] = {
    "en": LANGUAGE_EN,
    "ru": LANGUAGE_RU,
}


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
