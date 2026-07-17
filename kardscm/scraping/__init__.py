"""Scraping subpackage for KARDS card collection."""

from __future__ import annotations

import logging

from kardscm.models import CardDict
from kardscm.scraping.baseline import (
    ApiContractDriftError,
    build_snapshot,
    diff_snapshots,
    load_baseline,
    save_baseline,
)
from kardscm.scraping.fetcher import fetch_all_cards
from kardscm.scraping.normalizer import normalize_card
from kardscm.scraping.probe import build_static_probe

logger = logging.getLogger(__name__)


def _check_api_drift(raw_cards: list[dict]) -> None:
    """Compare observed snapshot vs committed baseline; halt on contract drift.

    On first run (no baseline file) — initialize the baseline silently and
    return. On any contract change, raise ApiContractDriftError carrying the
    drift and the observed snapshot, so the sync stops and the user decides.
    Benign content growth (new sets, more cards) is not a contract change and
    does not reach this raise.
    """
    observed = build_snapshot(raw_cards)
    baseline = load_baseline()
    if baseline is None:
        try:
            save_baseline(observed)
            logger.info("API baseline initialized from current sync (first run).")
        except OSError as exc:
            logger.warning(
                "Failed to write initial baseline (%s); drift detection disabled for this run.",
                exc,
            )
        return
    drift = diff_snapshots(baseline, observed)
    if not drift.has_changes():
        return
    logger.warning("API contract drift detected (%d items).", drift.count())
    raise ApiContractDriftError(drift, observed)


def scrape_cards(language: str = "en") -> list[CardDict]:
    """Scrape all cards via probe + GraphQL fetch + normalize.

    Args:
        language: GraphQL `$language` value (short code).

    Returns:
        List of normalized CardDict objects.

    Raises:
        ApiContractDriftError: The API shape diverged from the baseline.
    """
    logger.info("Starting card scrape (language=%s)...", language)
    probe = build_static_probe(language)
    raw_cards = fetch_all_cards(probe)

    _check_api_drift(raw_cards)

    cards: list[CardDict] = []
    for node in raw_cards:
        card = normalize_card(node)
        if card is not None:
            cards.append(card)

    logger.info("Scraped and normalized %d cards", len(cards))
    return cards


__all__ = ["ApiContractDriftError", "scrape_cards"]
