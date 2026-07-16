"""Central constants for the KARDS collection package."""

from __future__ import annotations

# === URLs ===
BASE_URL = "https://www.kards.com"
COLLECTION_URL = "https://www.kards.com/en/decks/collection"

# === GraphQL API ===
GRAPHQL_URL = "https://api.kards.com/graphql"
GRAPHQL_HEADERS: dict[str, str] = {
    "referer": "https://www.kards.com/",
    "accept": "*/*",
    "content-type": "application/json",
}
GRAPHQL_QUERY = """
query getCards(
  $language: String,
  $offset: Int,
  $nationIds: [Int],
  $kredits: [Int],
  $q: String,
  $type: [String],
  $rarity: [String],
  $set: [String],
  $showSpawnables: Boolean,
  $showExiles: Boolean,
  $showReserved: Boolean,
) {
  cards(
    language: $language
    first: 20
    offset: $offset
    nationIds: $nationIds
    kredits: $kredits
    q: $q
    type: $type
    set: $set
    rarity: $rarity
    showSpawnables: $showSpawnables
    showExiles: $showExiles
    showReserved: $showReserved
  ) {
    pageInfo {
      count
      hasNextPage
      __typename
    }
    edges {
      node {
        id
        cardId
        importId
        json
        reserved
        imageUrl: image(language: $language)
        thumbUrl: image(type: thumb, language: $language)
        __typename
      }
      __typename
    }
    __typename
  }
}
"""
GRAPHQL_VARIABLES: dict = {
    "showSpawnables": True,
    "showExiles": False,
    "showReserved": True,
}

# Internal field names for the 12-column collection XLSX export. The order
# mirrors the web collection table (kardscm/web/templates/_table.html) exactly.
COLLECTION_TABLE_FIELDS: list[str] = [
    "faction",
    "title",
    "type",
    "rarity",
    "abilities",
    "extra_abilities",
    "set",
    "quantity",
    "kredits",
    "operationCost",
    "attack",
    "defense",
]

# Column widths for the collection XLSX, keyed by field name so width stays
# co-located with its column regardless of order.
COLLECTION_COLUMN_WIDTHS: dict[str, int] = {
    "faction": 15,
    "title": 35,
    "type": 18,
    "rarity": 15,
    "abilities": 18,
    "extra_abilities": 18,
    "set": 20,
    "quantity": 10,
    "kredits": 10,
    "operationCost": 8,
    "attack": 8,
    "defense": 8,
}

# === Abilities ===
# Canonical ability keys — match [abilities] section of en.toml and DB column names.
# DB column: f"ability_{key}" (e.g. ability_guard, ability_heavyArmor1).
KNOWN_ABILITIES: tuple[str, ...] = (
    "alpine",
    "ambush",
    "blitz",
    "bond",
    "covert",
    "fury",
    "guard",
    "heavyArmor1",
    "heavyArmor2",
    "heavyArmor3",
    "intel1",
    "intel2",
    "intel3",
    "mobilize",
    "salvage",
    "shock",
    "smokescreen",
)

# === Extra abilities ===
# Manually-curated tags that are visible only in the game client UI and don't
# come from the GraphQL API. Membership of cards-per-ability is stored in
# kardscm/data/extra_abilities.toml and applied to extra_ability_<key>
# columns during `kardscm sync`.
KNOWN_EXTRA_ABILITIES: tuple[str, ...] = (
    "pincer",
    "resistance",
    "legions",
    "sissi",
    "destruction",
    "naval",
)

# === Database ===
DEFAULT_DB_PATH = "collection.db"

# === Deck Import ===
DECK_CARD_PATTERN = r"^(\d+)x\s+\((\d+)K\)\s+(.+)$"
DECK_METADATA_KEYS: dict[str, str] = {
    "Major power": "major_power",
    "Ally": "ally",
    "HQ": "hq",
}

# Maps lowercase deck-file nation keys to API faction names.
# Language-agnostic: identical across all locales.
DECK_NATION_TO_DB: dict[str, str] = {
    "soviet": "Soviet",
    "usa": "USA",
    "britain": "Britain",
    "germany": "Germany",
    "japan": "Japan",
    "france": "France",
    "italy": "Italy",
    "poland": "Poland",
    "finland": "Finland",
}

# === Rarity limits ===
# Maximum copies of a card per rarity tier (API values, language-agnostic).
RARITY_MAX_QUANTITY: dict[str, int] = {
    "Standard": 4,
    "Limited": 3,
    "Special": 2,
    "Elite": 1,
}

# === Deck Export ===
DECK_COLUMN_WIDTHS: list[int] = [30, 18, 14, 12, 10, 10]
