"""Scraping subpackage for KARDS card collection."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from kardscm.locales import LANGUAGE_EN
from kardscm.models import CardDict
from kardscm.scraping.baseline import (
    ApiContractDriftError,
    build_snapshot,
    diff_snapshots,
    format_drift_report_md,
    load_baseline,
    save_baseline,
    write_observed,
)
from kardscm.scraping.fetcher import fetch_all_cards
from kardscm.scraping.normalizer import normalize_card
from kardscm.scraping.probe import build_static_probe

if TYPE_CHECKING:
    from kardscm.locales import LanguageConfig

logger = logging.getLogger(__name__)


def _drift_report_paths() -> tuple[Path, Path]:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    cwd = Path.cwd()
    return cwd / f"sync-schema-diff-{ts}.md", cwd / f"sync-schema-observed-{ts}.json"


def _check_api_drift(raw_cards: list[dict], lang_config: LanguageConfig) -> None:
    """Compare observed snapshot vs committed baseline; halt on contract drift.

    On first run (no baseline file) — initialize the baseline silently and
    return. On any contract change, write the drift report + observed snapshot
    (a disk-write failure is logged, not fatal) and raise ApiContractDriftError
    so the sync stops and the user decides. Benign content growth (new sets,
    more cards) is not a contract change and does not reach this raise.
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
    report_path: Path | None
    observed_path: Path | None
    report_path, observed_path = _drift_report_paths()
    try:
        report_path.write_text(format_drift_report_md(drift, lang_config), encoding="utf-8")
        write_observed(observed, observed_path)
        logger.warning(
            "API contract drift detected (%d items). Report: %s | Observed: %s",
            drift.count(),
            report_path,
            observed_path,
        )
    except OSError as exc:
        logger.warning(
            "API contract drift detected (%d items) but report write failed (%s).",
            drift.count(),
            exc,
        )
        report_path = observed_path = None
    raise ApiContractDriftError(drift, report_path, observed_path)


def scrape_cards(language: str = "en", lang_config: LanguageConfig | None = None) -> list[CardDict]:
    """Scrape all cards via probe + GraphQL fetch + normalize.

    Args:
        language: GraphQL `$language` value (short code).
        lang_config: Optional LanguageConfig for the drift report. If None,
            falls back to English (drift detection is silent on missing locale).

    Returns:
        List of normalized CardDict objects.
    """
    logger.info("Starting card scrape (language=%s)...", language)
    probe = build_static_probe(language)
    raw_cards = fetch_all_cards(probe)

    if lang_config is None:
        lang_config = LANGUAGE_EN
    _check_api_drift(raw_cards, lang_config)

    cards: list[CardDict] = []
    for node in raw_cards:
        card = normalize_card(node)
        if card is not None:
            cards.append(card)

    logger.info("Scraped and normalized %d cards", len(cards))
    return cards


__all__ = ["ApiContractDriftError", "scrape_cards"]
