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
    "language": "en",
    "showSpawnables": True,
    "showExiles": False,
    "showReserved": True,
}

# Internal field names used to extract data from card dicts for export
EXPORT_FIELD_NAMES: list[str] = [
    "faction",
    "title",
    "type",
    "rarity",
    "attributes",
    "set",
    "quantity",
    "kredits",
    "attack",
    "defense",
    "text",
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
