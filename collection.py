#!/usr/bin/env python3
"""Collection CLI entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

from exporters import (
    RUSSIAN_HEADERS,
    SUPPORTED_EXPORT_FORMATS,
    export_to_csv,
    export_to_json,
    export_to_xlsx,
)
from scrape import LANGUAGE_CODE, LANGUAGE_NAME, scrape_cards
from storage import fetch_cards, get_connection, initialize_schema, set_metadata, upsert_cards

__version__ = "0.1"

DEFAULT_DB_PATH = "collection.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def sync_collection(db_path: str = DEFAULT_DB_PATH) -> None:
    """Synchronize local SQLite storage with the website.

    Args:
        db_path: SQLite database path.
    """
    logger.info("Starting sync from website...")
    cards = await scrape_cards()

    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, cards)
        set_metadata(conn, "last_sync", _utc_timestamp())

    logger.info("Sync completed. Stored %s cards.", len(cards))


def export_collection(
    export_format: str,
    filename: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Export cards from SQLite to the selected format.

    Args:
        export_format: Export format (csv, json, xlsx).
        filename: Output file path.
        db_path: SQLite database path.
    """
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        cards = fetch_cards(conn)

    if not cards:
        raise SystemExit("No cards in database. Run --sync first.")

    if export_format == "xlsx":
        export_to_xlsx(cards, filename, RUSSIAN_HEADERS)
    elif export_format == "csv":
        export_to_csv(cards, filename, RUSSIAN_HEADERS)
    elif export_format == "json":
        export_to_json(cards, filename, LANGUAGE_CODE, LANGUAGE_NAME)
    else:
        msg = f"Unsupported format: {export_format}"
        raise ValueError(msg)

    logger.info("Export completed: %s", filename)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Raw argument list.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Card collection scraper - sync and export",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--sync",
        action="store_true",
        help="Sync cards from the website into SQLite",
    )
    mode_group.add_argument(
        "--export",
        action="store_true",
        help="Export cards from SQLite",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=SUPPORTED_EXPORT_FORMATS,
        help="Export format (csv, json, xlsx)",
    )
    parser.add_argument(
        "--file",
        "-o",
        help="Output filename for export",
    )

    if not argv:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    """Validate CLI arguments and exit on error.

    Args:
        args: Parsed argument namespace.
    """
    if not args.sync and not args.export:
        msg = "Specify --sync or --export"
        raise SystemExit(msg)

    if args.export:
        if not args.format:
            msg = "--export requires --format"
            raise SystemExit(msg)
        if not args.file:
            msg = "--export requires --file"
            raise SystemExit(msg)


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


async def main() -> None:
    """Entry point for CLI."""
    args = parse_args(sys.argv[1:])
    validate_args(args)

    if args.sync:
        await sync_collection()
        sys.exit(0)

    if args.export:
        export_collection(args.format, args.file)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
