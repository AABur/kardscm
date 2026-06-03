"""Business logic for CLI commands."""

from __future__ import annotations

from kardscm.commands.baseline import baseline_accept, baseline_init
from kardscm.commands.utils import _emit_locale_warnings
from kardscm.commands.decks import (
    _select_deck,
    add_deck,
    export_deck,
    import_deck,
    remove_deck,
)
from kardscm.commands.export import _read_xlsx_quantities, export_collection, update_collection
from kardscm.commands.sync import apply_sync_changes, fetch_and_compute_diff, sync_collection
from kardscm.commands.validation import validate_file as validate_file
