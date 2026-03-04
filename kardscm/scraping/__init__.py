"""Scraping subpackage for KARDS card collection."""

from __future__ import annotations

import logging

from kardscm.models import CardDict
from kardscm.scraping.fetcher import fetch_all_cards
from kardscm.scraping.normalizer import normalize_card
from kardscm.scraping.probe import build_static_probe

logger = logging.getLogger(__name__)


def scrape_cards() -> list[CardDict]:
    """Scrape all cards via probe + GraphQL fetch + normalize.

    Returns:
        List of normalized CardDict objects.
    """
    logger.info("Starting card scrape...")
    probe = build_static_probe()
    raw_cards = fetch_all_cards(probe)

    cards: list[CardDict] = []
    for node in raw_cards:
        card = normalize_card(node)
        if card is not None:
            cards.append(card)

    logger.info("Scraped and normalized %d cards", len(cards))
    return cards


__all__ = ["scrape_cards"]
