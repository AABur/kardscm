"""Main scraping orchestration."""

from __future__ import annotations

import logging
from typing import Any

from kards.constants import COLLECTION_URL
from kards.scraping.browser import collect_api_data
from kards.scraping.localization import (
    extract_localized_field,
    load_translations,
    sanitize_text,
    translate_value,
)

logger = logging.getLogger(__name__)


def parse_api_data(
    api_data: list[dict[str, Any]],
    translations: dict[str, str],
) -> list[dict[str, str]]:
    """Parse API data to extract cards.

    Args:
        api_data: Collected API responses.
        translations: Translation dictionary.

    Returns:
        List of card dictionaries.
    """
    logger.info("Parsing %s API responses...", len(api_data))
    cards: list[dict[str, str]] = []
    card_ids: set[str] = set()

    for api_response in api_data:
        try:
            data = api_response.get("data")
            if not isinstance(data, dict):
                continue

            for value in data.values():
                if isinstance(value, dict) and "edges" in value:
                    edges = value.get("edges", [])
                    for edge in edges:
                        node = edge.get("node")
                        if not isinstance(node, dict):
                            continue
                        card_id = node.get("cardId", "")
                        if not card_id or card_id in card_ids:
                            continue
                        card_info = build_card(node, card_id, translations)
                        if card_info:
                            cards.append(card_info)
                            card_ids.add(card_id)
        except Exception as exc:
            logger.warning("Error parsing response: %s", exc)

    logger.info("Total cards extracted: %s", len(cards))
    return cards


def build_card(
    card_node: dict[str, Any],
    card_id: str,
    translations: dict[str, str],
) -> dict[str, str] | None:
    """Build a card dictionary from API node data.

    Args:
        card_node: Card node data from API.
        card_id: Card identifier from API.
        translations: Translation dictionary.

    Returns:
        Card dictionary or None if required fields are missing.
    """
    json_data = card_node.get("json", {})

    title = extract_localized_field(json_data.get("title", {}), "title")
    if not title:
        return None

    faction_raw = json_data.get("faction") or ""
    type_raw = json_data.get("type") or ""
    rarity_raw = json_data.get("rarity") or ""
    set_raw = json_data.get("set") or ""
    description = extract_localized_field(json_data.get("text", {}), "description")

    card_info: dict[str, str] = {
        "CardId": card_id,
        "Nation": sanitize_text(translate_value("faction", str(faction_raw), translations)),
        "Name": sanitize_text(title),
        "Type": sanitize_text(translate_value("type", str(type_raw), translations)),
        "Rarity": sanitize_text(translate_value("rarity", str(rarity_raw), translations)),
        "Abilities": "",
        "Set": sanitize_text(translate_value("set", str(set_raw), translations)),
        "Quantity": "",
        "Credits": str(json_data.get("kredits", "")),
        "Attack": str(json_data.get("attack", "")),
        "Defense": str(json_data.get("defense", "")),
        "Description": sanitize_text(description),
    }

    return card_info


async def scrape_cards() -> list[dict[str, str]]:
    """Scrape cards from the Russian collection page.

    Returns:
        List of card dictionaries.
    """
    translations = await load_translations()
    api_data = await collect_api_data(COLLECTION_URL)
    return parse_api_data(api_data, translations)
