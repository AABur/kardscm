"""Business logic for CLI commands."""

from __future__ import annotations

from kardscm.commands.baseline import baseline_accept
from kardscm.commands.decks import add_deck, add_decks, export_deck, import_deck, remove_deck
from kardscm.commands.export import export_collection, update_collection
from kardscm.commands.sync import apply_sync_changes, fetch_and_compute_diff, sync_collection
from kardscm.commands.utils import _emit_locale_warnings

__all__ = [
    "baseline_accept",
    "add_deck",
    "add_decks",
    "export_deck",
    "import_deck",
    "remove_deck",
    "export_collection",
    "update_collection",
    "apply_sync_changes",
    "fetch_and_compute_diff",
    "sync_collection",
    "_emit_locale_warnings",
]
