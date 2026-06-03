"""SQLite storage helpers for card collections."""

from __future__ import annotations

from kardscm.storage.admin import (  # noqa: F401
    ADMIN_DB_COLUMNS,
    ADMIN_EDITABLE_SCALARS,
    update_card_admin,
)
from kardscm.storage.cards import (  # noqa: F401
    delete_cards,
    fetch_cards,
    find_card_id,
    find_card_id_by_exile,
    get_card_quantity_by_id,
    update_card_quantity_by_id,
    update_quantity,
    upsert_cards,
)
from kardscm.storage.decks import (  # noqa: F401
    delete_all_decks,
    delete_deck,
    fetch_all_decks,
    fetch_deck_cards,
    find_deck_by_name,
    insert_deck,
    insert_deck_cards,
)
from kardscm.storage.metadata import set_metadata  # noqa: F401
from kardscm.storage.schema import (  # noqa: F401
    SCHEMA_SQL,
    _ensure_extra_ability_columns,
    get_connection,
    initialize_schema,
)
from kardscm.storage.seed_extra_abilities import (  # noqa: F401
    _EXTRA_ABILITIES_TOML,
    _bootstrap_extra_abilities_if_stale,
    _load_extra_abilities_seed,
    apply_extra_abilities_seed,
)
