"""Central constants for the KARDS collection package."""

from __future__ import annotations

# === URLs ===
BASE_URL = "https://www.kards.com"

# === Known Mappings (translation IDs on the KARDS website) ===
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

# Internal field names used to extract data from card dicts
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

# === Database ===
DEFAULT_DB_PATH = "collection.db"

# === Deck Import ===
DECK_CARD_PATTERN = r"^(\d+)x\s+\((\d+)K\)\s+(.+)$"
DECK_METADATA_KEYS: dict[str, str] = {
    "Major power": "major_power",
    "Ally": "ally",
    "HQ": "hq",
}

# === Deck Export ===
DECK_COLUMN_WIDTHS: list[int] = [30, 18, 14, 12, 10, 10]
