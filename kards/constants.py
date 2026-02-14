"""Central constants for the KARDS collection package."""

from __future__ import annotations

# === URLs ===
BASE_URL = "https://www.kards.com"
COLLECTION_URL = f"{BASE_URL}/ru/decks/collection"

# === Language ===
LANGUAGE_CODE = "ru"
LANGUAGE_NAME = "Russian"

RU_KEYS = ("ru", "ru-RU")
EN_KEYS = ("en", "en-EN")

RU_LANG_INDEX = 9

# === Known Mappings ===
KNOWN_MAPPINGS: dict[str, dict[str, str]] = {
    "type": {
        "infantry": "llkqn9",
        "tank": "QIFcAI",
        "armor": "QIFcAI",
        "artillery": "ziY9j1",
        "fighter": "al73ht",
        "air": "al73ht",
        "order": "UYUgdb",
        "countermeasure": "qM208o",
    },
    "faction": {
        "Soviet": "iROGPL",
        "USA": "Mqy/Zy",
        "Japan": "A1ET6E",
        "Germany": "XTtR6a",
        "Britain": "OICU0U",
        "France": "+gY+iO",
        "Italy": "MFljzs",
        "Poland": "sfwBnA",
    },
    "rarity": {
        "Standard": "TJBHlP",
        "Limited": "HhURN3",
        "Special": "qBFI6F",
        "Elite": "JEzmqf",
    },
    "set": {
        "Base": "Nzwli2",
        "Allegiance": "bPobF4",
        "TheatersOfWar": "MPVNE8",
        "Breakthrough": "paHq3y",
        "WorldAtWar": "tkXxPO",
        "CovertOps": "/Adfjf",
        "BloodAndIron": "vhFlLC",
        "Legions": "a6nh/L",
        "NavalWarfare": "6bDKSi",
        "Homefront": "5rE6vr",
        "WinterWar": "wDZgXG",
    },
}

# === Export ===
SUPPORTED_EXPORT_FORMATS: list[str] = ["xlsx", "csv", "json"]

EXPORT_FIELD_NAMES: list[str] = [
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
]

RUSSIAN_HEADERS: list[str] = [
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
]

# === Database ===
DEFAULT_DB_PATH = "collection.db"

# === Deck Import ===
DECK_CARD_PATTERN = r"^(\d+)x\s+\((\d+)K\)\s+(.+)$"
DECK_METADATA_KEYS: dict[str, str] = {
    "Major power": "major_power",
    "Ally": "ally",
    "HQ": "hq",
}

DECK_NATION_TO_DB: dict[str, str] = {
    "soviet": "Soviet",
    "usa": "USA",
    "britain": "Britain",
    "germany": "Germany",
    "japan": "Japan",
    "france": "France",
    "italy": "Italy",
    "poland": "Poland",
}

NATION_DISPLAY_NAMES: dict[str, str] = {
    "soviet": "Советские",
    "usa": "Американские",
    "britain": "Британские",
    "germany": "Германские",
    "japan": "Японские",
    "france": "Французские",
    "italy": "Итальянские",
    "poland": "Польские",
}

DECK_HEADERS_RU: list[str] = ["Карта", "Тип", "Кол-во", "Стоим.", "Атака", "Защита"]
DECK_METADATA_LABELS: list[str] = [
    "Название",
    "Основная нация",
    "Союзная нация",
    "Штаб",
    "Код",
]
DECK_COLUMN_WIDTHS: list[int] = [30, 18, 10, 10, 10, 10]
