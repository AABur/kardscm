"""Language configuration management."""

from __future__ import annotations

import configparser
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.ini"


@dataclass(frozen=True)
class LanguageConfig:
    """Language-specific configuration."""

    code: str
    name: str
    locale_key: str
    export_headers: list[str] = field(default_factory=list)
    faction_names: dict[str, str] = field(default_factory=dict)
    type_names: dict[str, str] = field(default_factory=dict)
    rarity_names: dict[str, str] = field(default_factory=dict)
    set_names: dict[str, str] = field(default_factory=dict)
    nation_display_names: dict[str, str] = field(default_factory=dict)
    deck_headers: list[str] = field(default_factory=list)
    deck_metadata_labels: list[str] = field(default_factory=list)
    collection_sheet_name: str = "Collection"
    ability_names: dict[str, str] = field(default_factory=dict)
    diff_headers: dict[str, str] = field(default_factory=dict)
    ui_strings: dict[str, str] = field(default_factory=dict)
    fallback_warnings: list[str] = field(default_factory=list)


LANGUAGE_EN = LanguageConfig(
    code="en",
    name="English",
    locale_key="en-EN",
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
    type_names={
        "infantry": "Infantry",
        "tank": "Tank",
        "artillery": "Artillery",
        "fighter": "Fighter",
        "order": "Order",
        "countermeasure": "Countermeasure",
    },
    rarity_names={
        "Standard": "Standard",
        "Limited": "Limited",
        "Special": "Special",
        "Elite": "Elite",
    },
    set_names={
        "Base": "Base",
        "Allegiance": "Allegiance",
        "TheatersOfWar": "Theaters of War",
        "Breakthrough": "Breakthrough",
        "WorldAtWar": "World at War",
        "CovertOps": "Covert Ops",
        "BloodAndIron": "Blood and Iron",
        "Legions": "Legions",
        "NavalWarfare": "Naval Warfare",
        "Homefront": "Homefront",
        "WinterWar": "Winter War",
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
    ability_names={
        "alpine": "Alpine",
        "ambush": "Ambush",
        "blitz": "Blitz",
        "bond": "Bond",
        "covert": "Covert",
        "fury": "Fury",
        "guard": "Guard",
        "heavyArmor1": "Heavy Armor 1",
        "heavyArmor2": "Heavy Armor 2",
        "heavyArmor3": "Heavy Armor 3",
        "intel1": "Intel 1",
        "intel2": "Intel 2",
        "intel3": "Intel 3",
        "mobilize": "Mobilize",
        "salvage": "Salvage",
        "shock": "Shock",
        "smokescreen": "Smokescreen",
    },
    diff_headers={
        "title": "Sync diff",
        "new": "New cards",
        "changed": "Changed characteristics",
        "reserved_in": "Moved to reserve",
        "reserved_out": "Returned from reserve",
        "removed": "Removed cards",
    },
    ui_strings={
        "page_title": "kardscm collection",
        "search_placeholder": "search by name…",
        "toggle_spawnable": "spawnable",
        "toggle_reserved": "reserved",
        "toggle_owned": "only owned",
        "col_cost": "Cost",
        "card_id_label": "cardId",
        "saved_hint": "saves automatically (Tab/Enter)",
        "modal_close": "close",
    },
)


LANGUAGE_RU = LanguageConfig(
    code="ru",
    name="Russian",
    locale_key="ru-RU",
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
    type_names={
        "infantry": "Пехота",
        "tank": "Танк",
        "artillery": "Артиллерия",
        "fighter": "Истребитель",
        "order": "Приказ",
        "countermeasure": "Контрмера",
    },
    rarity_names={
        "Standard": "Стандартная",
        "Limited": "Лимитированная",
        "Special": "Специальная",
        "Elite": "Элитная",
    },
    set_names={
        "Base": "Базовый",
        "Allegiance": "Верность",
        "TheatersOfWar": "Театры войны",
        "Breakthrough": "Прорыв",
        "WorldAtWar": "Мировая война",
        "CovertOps": "Тайные операции",
        "BloodAndIron": "Кровь и железо",
        "Legions": "Легионы",
        "NavalWarfare": "Морская война",
        "Homefront": "Тыл",
        "WinterWar": "Зимняя война",
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
    ability_names={
        "alpine": "Альпийский",
        "ambush": "Засада",
        "blitz": "Блиц",
        "bond": "Узы",
        "covert": "Скрытность",
        "fury": "Ярость",
        "guard": "Охрана",
        "heavyArmor1": "Тяжёлая броня 1",
        "heavyArmor2": "Тяжёлая броня 2",
        "heavyArmor3": "Тяжёлая броня 3",
        "intel1": "Разведка 1",
        "intel2": "Разведка 2",
        "intel3": "Разведка 3",
        "mobilize": "Моблизация",
        "salvage": "Утилизауия",
        "shock": "Штурм",
        "smokescreen": "Дымовая завеса",
    },
    diff_headers={
        "title": "Изменения синхронизации",
        "new": "Новые карты",
        "changed": "Изменённые характеристики",
        "reserved_in": "Ушли в резерв",
        "reserved_out": "Вернулись из резерва",
        "removed": "Удалённые карты",
    },
    ui_strings={
        "page_title": "Коллекция kardscm",
        "search_placeholder": "поиск по названию…",
        "toggle_spawnable": "спаунятся",
        "toggle_reserved": "в резерве",
        "toggle_owned": "только мои",
        "col_cost": "Стоимость",
        "card_id_label": "cardId",
        "saved_hint": "сохраняется автоматически (Tab/Enter)",
        "modal_close": "закрыть",
    },
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
