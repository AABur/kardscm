"""Shared filter and display constants for the kardscm web UI."""

from __future__ import annotations

from kardscm.storage.database import ADMIN_DB_COLUMNS

EDIT_MODE_COOKIE = "kardscm_edit"

EXPORT_MIME_TYPES: dict[str, str] = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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

# Form-side allow-list: DB columns the admin form can write directly,
# plus the locale-merged title/text fields the form exposes.
_ADMIN_FORM_FIELDS: frozenset[str] = ADMIN_DB_COLUMNS | {"title", "text"}
