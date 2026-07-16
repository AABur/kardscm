"""Sync commands — fetch, diff, and apply collection updates."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from kardscm.commands.utils import (
    _emit_locale_warnings,
    _safe_timestamp,
    _utc_timestamp,
)
from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import DEFAULT_DB_PATH
from kardscm.diff import (
    compute_diff,
    format_console_report,
    format_markdown_report,
    is_empty,
)
from kardscm.models import CardDict, DiffReport
from kardscm.scraping import ApiContractDriftError, scrape_cards
from kardscm.storage import (
    apply_extra_abilities_seed,
    delete_cards,
    fetch_cards,
    get_connection,
    initialize_schema,
    set_metadata,
    upsert_cards,
)

logger = logging.getLogger(__name__)


_APPROVAL_CATEGORIES = (
    ("new", "Apply"),
    ("changed", "Apply"),
    ("reserved_in", "Apply"),
    ("reserved_out", "Apply"),
    ("removed", "Delete"),
)


def _approve_all_categories(report: DiffReport, lang_config: LanguageConfig) -> bool:
    """Prompt y/N for each non-empty category. Any 'no' returns False."""
    headers = lang_config.diff_headers
    for key, verb in _APPROVAL_CATEGORIES:
        items = report[key]  # type: ignore[literal-required]
        if not items:
            continue
        label = headers.get(key, key)
        if not typer.confirm(f"{verb} {len(items)} '{label}'?", default=True):
            return False
    return True


def _write_diff_report(
    path: Path,
    report: DiffReport,
    lang_config: LanguageConfig,
    timestamp: str,
) -> None:
    content = format_markdown_report(report, lang_config, timestamp)
    path.write_text(content, encoding="utf-8")


def fetch_and_compute_diff(
    db_path: str,
    lang_config: LanguageConfig,
) -> tuple[DiffReport, list[CardDict], str]:
    """Fetch fresh cards from the website and compute the DB diff.

    Pure read path: no DB writes, no console echo, no markdown report.
    Web flows call this to drive the preview modal; the CLI orchestrator
    composes it with `apply_sync_changes`.

    Args:
        db_path: SQLite database path.
        lang_config: Active language configuration.

    Returns:
        Tuple of (DiffReport, fetched cards, filesystem-safe UTC timestamp).
        The timestamp is generated once here so every report path the
        caller writes shares the same identifier.
    """
    new_cards = scrape_cards(language=lang_config.code, lang_config=lang_config)
    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)
        old_cards = fetch_cards(conn)
        report = compute_diff(old_cards, new_cards, lang_config.locale_key)
    return report, new_cards, _safe_timestamp()


def apply_sync_changes(
    db_path: str,
    new_cards: list[CardDict],
    report: DiffReport,
    lang_config: LanguageConfig,
    timestamp: str,
    diff_report_path: Path | None = None,
) -> Path | None:
    """Persist the sync result to the DB and update metadata.

    Args:
        db_path: SQLite database path.
        new_cards: Cards returned by `fetch_and_compute_diff`.
        report: Diff report bucketed by category.
        lang_config: Active language configuration.
        timestamp: Filesystem-safe UTC timestamp from `fetch_and_compute_diff`.
        diff_report_path: Where to write the markdown report. No report is
            written when None — the user has already reviewed the diff on
            screen, so a file is only produced on explicit request.

    Returns:
        Path to the markdown report when one was requested and written,
        otherwise None.
    """
    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)
        if is_empty(report):
            set_metadata(conn, "last_sync", _utc_timestamp())
            set_metadata(conn, "language", lang_config.code)
            return None

        upsert_cards(conn, new_cards)
        if report["removed"]:
            delete_cards(conn, [r["cardId"] for r in report["removed"]])
        apply_extra_abilities_seed(conn)
        set_metadata(conn, "last_sync", _utc_timestamp())
        set_metadata(conn, "language", lang_config.code)

    if diff_report_path is None:
        return None
    _write_diff_report(diff_report_path, report, lang_config, timestamp)
    return diff_report_path


def sync_collection(
    db_path: str = DEFAULT_DB_PATH,
    *,
    lang: str | None = None,
    diff_only: bool = False,
    yes: bool = False,
    diff_report_path: Path | None = None,
) -> None:
    """Synchronize local SQLite storage with the website.

    Computes a diff between the current DB state and the fresh API pull,
    prints it, and asks the user to bulk-approve each non-empty category.
    Any rejection aborts the sync — the DB is left untouched.

    Args:
        db_path: SQLite database path.
        lang: Active language code (e.g. "en", "ru"). Defaults to English.
        diff_only: If True, print the diff and return without prompting
            or modifying the DB. Useful for previews and CI.
        yes: If True, auto-approve every category without prompting.
        diff_report_path: Write a Markdown report to this path. Nothing is
            written when None; the diff is shown on screen either way.
    """
    lang_config = get_language_config(lang)
    _emit_locale_warnings(lang_config)
    logger.info("Starting sync from website (language: %s)...", lang_config.name)

    try:
        report, new_cards, timestamp = fetch_and_compute_diff(db_path, lang_config)
    except ApiContractDriftError as exc:
        location = exc.report_path or "the current directory"
        raise SystemExit(
            f"API contract drift detected ({exc.report.count()} change(s)). "
            "Sync halted to avoid silently corrupting data.\n"
            f"Review {location}, then run `kardscm baseline accept` to adopt the new "
            "shape (or fix normalization), and re-run the sync."
        ) from exc

    if is_empty(report):
        apply_sync_changes(db_path, new_cards, report, lang_config, timestamp)
        logger.info("No changes. %s cards in collection.", len(new_cards))
        return

    typer.echo(format_console_report(report, lang_config))

    if diff_only:
        if diff_report_path is not None:
            _write_diff_report(diff_report_path, report, lang_config, timestamp)
            logger.info("Diff report written to %s.", diff_report_path)
        logger.info("No DB changes.")
        return

    if not yes and not _approve_all_categories(report, lang_config):
        logger.info("Sync aborted by user. No DB changes.")
        return

    written = apply_sync_changes(
        db_path, new_cards, report, lang_config, timestamp, diff_report_path
    )
    logger.info("Sync completed. Stored %s cards. Report: %s", len(new_cards), written)
