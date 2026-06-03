"""Business logic for CLI commands."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from openpyxl import load_workbook

from kardscm.commands.baseline import baseline_accept, baseline_init
from kardscm.commands.export import _read_xlsx_quantities, export_collection, update_collection
from kardscm.commands.sync import apply_sync_changes, fetch_and_compute_diff, sync_collection
from kardscm.commands.utils import (
    _emit_locale_warnings,
)
from kardscm.commands.validation import validate_file as validate_file
from kardscm.config import LanguageConfig, get_language_config
from kardscm.constants import DECK_NATION_TO_DB, DEFAULT_DB_PATH
from kardscm.export import (
    add_deck_sheet,
    export_deck_to_json,
)
from kardscm.importing import parse_deck_file
from kardscm.models import DeckCardEntry
from kardscm.storage import (
    delete_all_decks,
    delete_deck,
    fetch_all_decks,
    fetch_deck_cards,
    find_card_id,
    find_card_id_by_exile,
    find_deck_by_name,
    get_card_quantity_by_id,
    get_connection,
    initialize_schema,
    insert_deck,
    insert_deck_cards,
    update_card_quantity_by_id,
)

logger = logging.getLogger(__name__)


def import_deck(
    filename: str,
    db_path: str = DEFAULT_DB_PATH,
    *,
    lang: str | None = None,
) -> None:
    """Import a deck from TXT file into the database.

    Args:
        filename: Path to deck TXT file.
        db_path: SQLite database path.
        lang: Active language code (e.g. "en", "ru"). Defaults to English.
    """
    lang_config = get_language_config(lang)
    _emit_locale_warnings(lang_config)
    logger.info("Importing deck from file: %s", filename)

    try:
        deck = parse_deck_file(filename)
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(f"Failed to parse deck file: {e}") from e

    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)

        existing = find_deck_by_name(conn, deck["name"])
        if existing:
            raise SystemExit(f"Deck '{deck['name']}' already exists (id={existing['deck_id']})")

        not_found = []
        for card in deck["cards"]:
            faction = DECK_NATION_TO_DB.get(card["nation"], card["nation"])
            card_id = find_card_id(conn, faction, card["name"], lang_config.locale_key)
            if card_id is None:
                not_found.append(f"{faction} / {card['name']}")

        if not_found:
            lines = "\n".join(f"  - {entry}" for entry in not_found)
            raise SystemExit(f"Cards not found in collection:\n{lines}")

        deck_id = insert_deck(conn, deck)
        insert_deck_cards(
            conn,
            deck_id,
            deck["cards"],
            lang_config.locale_key,
        )
        conn.commit()

    logger.info("Deck '%s' imported (%d cards)", deck["name"], len(deck["cards"]))


def add_deck(
    filename: str,
    update: bool = False,
    replace: bool = False,
    db_path: str = DEFAULT_DB_PATH,
    *,
    lang: str | None = None,
) -> None:
    """Add a deck from TXT file with exile card support and quantity check.

    Raises RuntimeError (not SystemExit) so the CLI can collect errors
    across multiple files and report a batch summary.

    Args:
        filename: Path to deck TXT file.
        update: If True, update collection quantities to match deck.
        replace: If True, replace existing deck with same name.
        db_path: SQLite database path.
        lang: Active language code (e.g. "en", "ru"). Defaults to English.
    """
    lang_config = get_language_config(lang)
    _emit_locale_warnings(lang_config)
    logger.info("Adding deck from file: %s", filename)

    try:
        deck = parse_deck_file(filename)
    except (FileNotFoundError, ValueError) as e:
        raise RuntimeError(f"Failed to parse deck file: {e}") from e

    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)

        existing = find_deck_by_name(conn, deck["name"])
        if existing:
            if not replace:
                if existing.get("deck_code") != deck["deck_code"]:
                    raise RuntimeError(
                        f"Deck '{deck['name']}' exists with different code. Use --replace."
                    )
                raise RuntimeError(
                    f"Deck '{deck['name']}' already exists (id={existing['deck_id']})"
                )
            delete_deck(conn, existing["deck_id"])
            conn.commit()

        # Resolve card IDs with exile fallback
        not_found = []
        resolved: list[tuple[DeckCardEntry, str]] = []
        for card in deck["cards"]:
            faction = DECK_NATION_TO_DB.get(card["nation"], card["nation"])
            card_id = find_card_id(conn, faction, card["name"], lang_config.locale_key)
            if card_id is None:
                card_id = find_card_id_by_exile(conn, faction, card["name"], lang_config.locale_key)
            if card_id is None:
                not_found.append(f"{faction} / {card['name']}")
            else:
                resolved.append((card, card_id))

        if not_found:
            lines = "\n".join(f"  - {entry}" for entry in not_found)
            raise RuntimeError(f"Cards not found in collection:\n{lines}")

        # Quantity check
        mismatches: list[tuple[DeckCardEntry, str, int, int]] = []
        for card, card_id in resolved:
            faction = DECK_NATION_TO_DB.get(card["nation"], card["nation"])
            collection_qty = get_card_quantity_by_id(conn, card_id)
            if card["quantity"] != collection_qty:
                mismatches.append((card, card_id, card["quantity"], collection_qty))

        if mismatches and not update:
            lines = "\n".join(
                f"  - {DECK_NATION_TO_DB.get(c['nation'], c['nation'])} / {c['name']}:"
                f" deck={deck_qty}, collection={col_qty}"
                for c, _, deck_qty, col_qty in mismatches
            )
            raise RuntimeError(
                f"Card quantity mismatch:\n{lines}\n"
                "Re-run with --update (-u) to update collection quantities."
            )

        deck_id = insert_deck(conn, deck)
        insert_deck_cards(
            conn,
            deck_id,
            deck["cards"],
            lang_config.locale_key,
            use_exile_fallback=True,
        )
        conn.commit()

        if update and mismatches:
            for _, card_id, deck_qty, _ in mismatches:
                update_card_quantity_by_id(conn, card_id, deck_qty)
            conn.commit()

    logger.info("Deck '%s' added (%d cards)", deck["name"], len(deck["cards"]))


def _select_deck(conn: sqlite3.Connection) -> dict:
    """Interactively select a deck from the database.

    Args:
        conn: SQLite connection instance.

    Returns:
        Selected deck metadata dict.
    """
    decks = fetch_all_decks(conn)
    if not decks:
        raise SystemExit("No decks in database. Run 'kards deck import' first.")

    print("Available decks:")
    for i, deck in enumerate(decks, 1):
        print(f"  {i}. {deck['name']}")

    try:
        choice = int(input("Enter deck number: "))
    except (ValueError, EOFError) as e:
        raise SystemExit(f"Invalid input: expected a deck number (1-{len(decks)})") from e

    if choice < 1 or choice > len(decks):
        raise SystemExit(f"Invalid choice: {choice}. Enter a number from 1 to {len(decks)}")

    return decks[choice - 1]


def remove_deck(db_path: str = DEFAULT_DB_PATH) -> None:
    """Interactively select and delete a deck from the database.

    Enter 0 to delete all decks. Prompts for confirmation before deleting.
    Does not affect the cards table.

    Args:
        db_path: SQLite database path.
    """
    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)
        decks = fetch_all_decks(conn)
        if not decks:
            raise SystemExit("No decks in database. Run 'kards deck import' first.")

        print("Available decks:")
        print("  0. Delete ALL decks")
        for i, deck in enumerate(decks, 1):
            print(f"  {i}. {deck['name']}")

        try:
            choice = int(input("Enter deck number (0 to delete all): "))
        except (ValueError, EOFError) as e:
            raise SystemExit(f"Invalid input: expected a number (0-{len(decks)})") from e

        if choice < 0 or choice > len(decks):
            raise SystemExit(f"Invalid choice: {choice}. Enter a number from 0 to {len(decks)}")

        if choice == 0:
            print(f"\nAll {len(decks)} deck(s) will be deleted.")
            try:
                confirm = input("Confirm deletion? [y/N]: ").strip().lower()
            except EOFError:
                raise SystemExit("Aborted.")
            if confirm != "y":
                raise SystemExit("Aborted.")
            count = delete_all_decks(conn)
            conn.commit()

        else:
            deck = decks[choice - 1]
            print(f"\nDeck to delete: {deck['name']}")
            try:
                confirm = input("Confirm deletion? [y/N]: ").strip().lower()
            except EOFError:
                raise SystemExit("Aborted.")
            if confirm != "y":
                raise SystemExit("Aborted.")
            delete_deck(conn, deck["deck_id"])
            conn.commit()

    if choice == 0:
        logger.info("All decks deleted (%d).", count)
    else:
        logger.info("Deck '%s' deleted.", deck["name"])


def export_deck(
    fmt: str | None,
    filename: str,
    db_path: str = DEFAULT_DB_PATH,
    *,
    lang: str | None = None,
) -> None:
    """Export a deck to XLSX sheet or JSON file.

    Args:
        fmt: Export format ('json' or None for xlsx).
        filename: Output file path.
        db_path: SQLite database path.
        lang: Active language code (e.g. "en", "ru"). Defaults to English.
    """
    lang_config = get_language_config(lang)
    _emit_locale_warnings(lang_config)

    with get_connection(db_path) as conn:
        initialize_schema(conn, db_path)
        deck_meta = _select_deck(conn)
        deck_cards = fetch_deck_cards(conn, deck_meta["deck_id"])

    if not deck_cards:
        raise SystemExit("Deck has no cards")

    if fmt == "json":
        export_deck_to_json(deck_meta, deck_cards, filename, lang_config)
    else:
        wb = load_workbook(filename)
        add_deck_sheet(
            wb,
            deck_meta,
            deck_cards,
            lang_config.deck_headers,
            lang_config.deck_metadata_labels,
            lang_config.nation_display_names,
            lang_config,
        )
        wb.save(filename)

    logger.info("Deck exported: %s", filename)
