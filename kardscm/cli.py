#!/usr/bin/env python3
"""Collection CLI entrypoint (Typer-based)."""

from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from kardscm import __version__
from kardscm.commands import (
    export_collection,
    export_deck,
    import_deck,
    sync_collection,
    update_collection,
    validate_file,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = typer.Typer(
    help="KARDS card collection manager",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
deck_app = typer.Typer(
    help="Import and export saved decks",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
app.add_typer(deck_app, name="deck")


class ExportFormat(StrEnum):
    xlsx = "xlsx"
    csv = "csv"
    json = "json"


class DeckExportFormat(StrEnum):
    xlsx = "xlsx"
    json = "json"


def _version_callback(value: bool) -> None:
    if value:
        print(f"kards {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """KARDS card collection manager."""


@app.command(
    epilog="Examples:\n\n* `kards sync`",
)
def sync() -> None:
    """Sync card collection from the website.

    Intercepts GraphQL API, fetches all cards via direct HTTP,
    and stores them in the local SQLite database.
    """
    sync_collection()


@app.command(
    epilog="Examples:\n\n"
    "* `kards export -f xlsx -o cards.xlsx`\n\n"
    "* `kards export -f csv -o cards.csv`\n\n"
    "* `kards export -f json -o cards.json`",
)
def export(
    fmt: Annotated[
        ExportFormat,
        typer.Option("--format", "-f", help="Output file format"),
    ],
    file: Annotated[
        Path,
        typer.Option("--file", "-o", help="Output file path", resolve_path=True),
    ],
) -> None:
    """Export card collection to a file.

    Reads cards from the local database and writes them to the
    specified format. Run **sync** first to populate the database.
    """
    validate_file(str(file), f".{fmt.value}")
    export_collection(fmt.value, str(file))


@app.command(
    epilog="Examples:\n\n* `kards update -i cards.xlsx`",
)
def update(
    file: Annotated[
        Path,
        typer.Option(
            "--file",
            "-i",
            help="XLSX file with card quantities",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
) -> None:
    """Update card quantities from an XLSX file.

    Reads the **Quantity** column from the spreadsheet and
    updates matching cards in the local database.
    Column names depend on the language setting in config.ini.
    """
    validate_file(str(file), ".xlsx", must_exist=True)
    update_collection(str(file))


@deck_app.command(
    "import",
    epilog="Examples:\n\n* `kards deck import -i deck.txt`",
)
def deck_import(
    file: Annotated[
        Path,
        typer.Option(
            "--file",
            "-i",
            help="Deck TXT file to import",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
) -> None:
    """Import a deck from a TXT file.

    Parses the deck file and saves it to the local database.
    Cards in the file must already exist in the collection.
    """
    validate_file(str(file), ".txt", must_exist=True)
    import_deck(str(file))


@deck_app.command(
    "export",
    epilog="Examples:\n\n"
    "* `kards deck export -f xlsx -o cards.xlsx`\n\n"
    "* `kards deck export -f json -o deck.json`",
)
def deck_export_cmd(
    fmt: Annotated[
        DeckExportFormat,
        typer.Option("--format", "-f", help="Output file format"),
    ],
    file: Annotated[
        Path,
        typer.Option("--file", "-o", help="Output file path", resolve_path=True),
    ],
) -> None:
    """Export a saved deck to XLSX or JSON.

    Select a deck interactively and write it to the specified
    format. Run **deck import** first to add decks.
    """
    validate_file(str(file), f".{fmt.value}")
    export_deck(fmt.value, str(file))


def run() -> None:
    """Console script entry point."""
    app()
