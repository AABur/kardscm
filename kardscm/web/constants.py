"""Shared filter and display constants for the kardscm web UI."""

from __future__ import annotations

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES
from kardscm.storage.database import ADMIN_DB_COLUMNS

EDIT_MODE_COOKIE = "kardscm_edit"

EXPORT_MIME_TYPES: dict[str, str] = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
    "json": "application/json",
}

FACTIONS = [
    "Soviet",
    "USA",
    "Britain",
    "Germany",
    "Japan",
    "France",
    "Italy",
    "Poland",
    "Finland",
    "Neutral",
]
TYPES = ["infantry", "tank", "artillery", "fighter", "bomber", "order", "countermeasure"]
RARITIES = ["Standard", "Limited", "Special", "Elite"]
SETS = [
    "Base",
    "Allegiance",
    "TheatersOfWar",
    "Breakthrough",
    "WorldAtWar",
    "CovertOps",
    "BloodAndIron",
    "Legions",
    "NavalWarfare",
    "Homefront",
    "WinterWar",
    "BrothersInArms",
    "Special",
    "OnlySpawnable",
]
KREDITS_RANGE = list(range(0, 11))

_ABILITY_COLS = ", ".join(f"ability_{a}" for a in KNOWN_ABILITIES)
_EXTRA_ABILITY_COLS = ", ".join(f"extra_ability_{a}" for a in KNOWN_EXTRA_ABILITIES)
CARD_COLUMNS = (
    'cardId, importId, imageUrl, thumbUrl, faction, type, rarity, "set", '
    f"title, text, kredits, attack, defense, {_ABILITY_COLS}, "
    f"{_EXTRA_ABILITY_COLS}, operationCost, "
    "reserved, image, can_create, exile, quantity, updated_at"
)

# Form-side allow-list: DB columns the admin form can write directly,
# plus the locale-merged title/text fields the form exposes.
_ADMIN_FORM_FIELDS: frozenset[str] = ADMIN_DB_COLUMNS | {"title", "text"}
