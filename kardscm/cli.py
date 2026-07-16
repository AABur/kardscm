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
    add_decks,
    baseline_accept,
    export_collection,
    export_deck,
    remove_deck,
    sync_collection,
    update_collection,
)
from kardscm.web.app import run as run_web

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

baseline_app = typer.Typer(
    help="Manage the API contract baseline used for drift detection",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
app.add_typer(baseline_app, name="baseline")


class ExportFormat(StrEnum):
    xlsx = "xlsx"
    json = "json"


class DeckExportFormat(StrEnum):
    xlsx = "xlsx"
    json = "json"


def _version_callback(value: bool) -> None:
    if value:
        print(f"kards {__version__}")
        raise typer.Exit()


def _lang(ctx: typer.Context) -> str | None:
    """Return the global --lang value from the Typer context, if any."""
    return (ctx.obj or {}).get("lang") if ctx.obj else None


def _validate_extension(path: Path, expected_ext: str) -> None:
    if path.suffix != expected_ext:
        raise SystemExit(f"Expected {expected_ext} file, got: {path.suffix or '(no extension)'}")


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
    lang: Annotated[
        str | None,
        typer.Option(
            "--lang",
            "-l",
            help=(
                "UI language code (en, ru, de, fr, it, es, pt, pl, ja, ko, zh, "
                "zh-Hant). Default: en."
            ),
        ),
    ] = None,
) -> None:
    """KARDS card collection manager."""
    ctx.obj = {"lang": lang}


@app.command(
    epilog="Examples:\n\n"
    "* `kards sync`\n\n"
    "* `kards sync --diff-only`\n\n"
    "* `kards sync --yes --diff-report ./diffs/today.md`",
)
def sync(
    ctx: typer.Context,
    diff_only: Annotated[
        bool,
        typer.Option(
            "--diff-only",
            help="Print the diff; do not modify the DB.",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Auto-approve every diff category without prompting.",
        ),
    ] = False,
    diff_report: Annotated[
        Path | None,
        typer.Option(
            "--diff-report",
            help="Also write the diff as Markdown to this path.",
            resolve_path=True,
        ),
    ] = None,
) -> None:
    """Sync card collection from the website.

    Fetches all cards via GraphQL, computes a diff against the local DB,
    and prompts approval per non-empty category (new cards / changed
    characteristics / reserve transitions / removed cards). Any
    rejection aborts the sync; the DB is left untouched. The diff is
    shown on screen; pass --diff-report to also save it as Markdown.
    """
    sync_collection(
        lang=_lang(ctx),
        diff_only=diff_only,
        yes=yes,
        diff_report_path=diff_report,
    )


@app.command(
    epilog="Examples:\n\n"
    "* `kards export -f xlsx -o cards.xlsx`\n\n"
    "* `kards export -f json -o cards.json`",
)
def export(
    ctx: typer.Context,
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
    _validate_extension(file, f".{fmt.value}")
    export_collection(fmt.value, str(file), lang=_lang(ctx))


@app.command(
    epilog="Examples:\n\n* `kards update -i cards.xlsx`",
)
def update(
    ctx: typer.Context,
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
    Column names follow the active **--lang** locale.
    """
    _validate_extension(file, ".xlsx")
    update_collection(str(file), lang=_lang(ctx))


@deck_app.command(
    "add",
    epilog="Examples:\n\n"
    "* `kards deck add deck.txt`\n\n"
    "* `kards deck add *.txt -u`\n\n"
    "* `kards deck add deck.txt -r`",
)
def deck_add(
    ctx: typer.Context,
    files: Annotated[
        list[Path],
        typer.Argument(
            help="Deck TXT file(s) to add",
            exists=True,
            readable=True,
            resolve_path=True,
        ),
    ],
    update: Annotated[
        bool,
        typer.Option("--update", "-u", help="Raise collection quantities to the deck's counts"),
    ] = False,
    replace: Annotated[
        bool,
        typer.Option("--replace", "-r", help="Replace existing deck with same name"),
    ] = False,
) -> None:
    """Add deck(s) from TXT file(s), with exile card support.

    Looks up cards by faction first, then falls back to the exile field.
    Fails when a deck needs more copies than the collection records;
    use --update to raise them.
    Use --replace to overwrite an existing deck with the same name.
    On error, continues with remaining files and prints a summary at the end.
    """
    add_decks([str(f) for f in files], update=update, replace=replace, lang=_lang(ctx))


@deck_app.command(
    "delete",
    epilog="Examples:\n\n* `kards deck delete`",
)
def deck_delete() -> None:
    """Delete a saved deck from the database.

    Lists available decks, prompts for selection and confirmation.
    Only removes records from decks and deck_cards tables.
    """
    remove_deck()


@deck_app.command(
    "export",
    epilog="Examples:\n\n"
    "* `kards deck export -f xlsx -o cards.xlsx`\n\n"
    "* `kards deck export -f json -o deck.json`",
)
def deck_export_cmd(
    ctx: typer.Context,
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
    _validate_extension(file, f".{fmt.value}")
    export_deck(fmt.value, str(file), lang=_lang(ctx))


@app.command(
    epilog="Examples:\n\n"
    "* `kards web`\n\n"
    "* `kards web --port 9000 --no-browser`\n\n"
    "* `kards --lang ru web`\n\n"
    "* `kards --lang ru web --admin`",
)
def web(
    ctx: typer.Context,
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="HTTP port (default 8765)"),
    ] = 8765,
    no_browser: Annotated[
        bool,
        typer.Option("--no-browser", help="Do not auto-open the browser"),
    ] = False,
    host: Annotated[
        str,
        typer.Option("--host", help="Bind host (default 127.0.0.1)"),
    ] = "127.0.0.1",
    admin: Annotated[
        bool,
        typer.Option(
            "--admin",
            "-A",
            help="Enable admin editing of all card fields. Backs up the DB and shows a red banner.",
        ),
    ] = False,
) -> None:
    """Start the local webUI for browsing and editing the collection.

    Without --admin, only the user mode is available: the in-page Edit
    toggle exposes per-card quantity editing. With --admin, every editable
    column becomes available via a modal form, and the database is backed
    up to a timestamped sibling file before the server starts.
    """
    run_web(
        port=port,
        open_browser=not no_browser,
        host=host,
        lang=_lang(ctx),
        admin=admin,
    )


@baseline_app.command("accept")
def baseline_accept_cmd() -> None:
    """Promote the latest `sync-schema-observed-*.json` to baseline.

    After reviewing a `sync-schema-diff-*.md` report and updating any
    constants/translations, run this to acknowledge the new API shape.
    """
    baseline_accept()


def run() -> None:
    """Console script entry point."""
    app()
