"""Admin editing helpers for card storage."""

from __future__ import annotations

import json
import sqlite3

from kardscm.constants import KNOWN_ABILITIES, KNOWN_EXTRA_ABILITIES

ADMIN_EDITABLE_SCALARS: tuple[str, ...] = (
    "faction",
    "type",
    "rarity",
    "set",
    "kredits",
    "attack",
    "defense",
    "operationCost",
    "reserved",
)

# DB columns the admin UI can write directly. Title/text are NOT in this
# set — they are stored as locale-keyed JSON and merged in a separate
# branch in update_card_admin.
ADMIN_DB_COLUMNS: frozenset[str] = (
    frozenset(ADMIN_EDITABLE_SCALARS)
    | {f"ability_{a}" for a in KNOWN_ABILITIES}
    | {f"extra_ability_{a}" for a in KNOWN_EXTRA_ABILITIES}
)


def update_card_admin(
    conn: sqlite3.Connection,
    card_id: str,
    fields: dict,
    locale_key: str,
) -> None:
    """Apply admin edits to a single card. Caller must commit.

    Whitelists column names, merges localized title/text into existing JSON,
    rejects unknown fields, and emits a single parametrised UPDATE.

    Args:
        conn: SQLite connection instance.
        card_id: cardId of the row to update.
        fields: Mapping of column name to new value. Recognised keys:
            ADMIN_EDITABLE_SCALARS, ability_*, extra_ability_*, title, text.
            title/text values must be plain strings (the active locale text);
            they are merged into the existing JSON under locale_key.
        locale_key: JSON key for title/text merge (e.g. "en-EN").

    Raises:
        KeyError: If card_id does not exist.
        ValueError: If fields contains an unsupported key.
    """
    row = conn.execute("SELECT title, text FROM cards WHERE cardId = ?", (card_id,)).fetchone()
    if row is None:
        raise KeyError(f"card not found: {card_id}")

    set_clauses: list[str] = []
    params: list[object] = []

    for key, value in fields.items():
        if key in ADMIN_DB_COLUMNS:
            set_clauses.append(f'"{key}" = ?')
            params.append(value)
        elif key == "title":
            existing = json.loads(row[0]) if row[0] else {}
            existing[locale_key] = value
            set_clauses.append('"title" = ?')
            params.append(json.dumps(existing, ensure_ascii=False))
        elif key == "text":
            existing = json.loads(row[1]) if row[1] else {}
            existing[locale_key] = value
            set_clauses.append('"text" = ?')
            params.append(json.dumps(existing, ensure_ascii=False))
        else:
            raise ValueError(f"unsupported admin field: {key}")

    if not set_clauses:
        return

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(card_id)
    sql = f"UPDATE cards SET {', '.join(set_clauses)} WHERE cardId = ?"
    conn.execute(sql, params)
