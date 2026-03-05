"""Tests for SQLite storage helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kardscm.storage import (
    fetch_all_decks,
    fetch_cards,
    fetch_deck_cards,
    find_card_id,
    find_card_id_by_exile,
    find_deck_by_name,
    get_card_quantity_by_id,
    get_connection,
    initialize_schema,
    insert_deck,
    insert_deck_cards,
    set_metadata,
    update_card_quantity_by_id,
    update_quantity,
    upsert_cards,
)


def _make_card(**overrides) -> dict:
    """Create a sample CardDict with defaults."""
    card = {
        "cardId": "card-1",
        "importId": "imp-1",
        "imageUrl": "",
        "thumbUrl": "",
        "faction": "USA",
        "type": "infantry",
        "rarity": "Standard",
        "set": "Base",
        "title": json.dumps({"en-EN": "Alpha", "ru-RU": "Альфа"}),
        "text": json.dumps({"en-EN": "Test", "ru-RU": "Тест"}),
        "kredits": 2,
        "attack": 3,
        "defense": 2,
        "attributes": json.dumps(["guard"]),
        "operationCost": None,
        "reserved": 0,
        "image": "",
        "can_create": None,
        "exile": None,
    }
    card.update(overrides)
    return card


def test_initialize_schema_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    table_names = {row[0] for row in rows}
    assert "cards" in table_names
    assert "metadata" in table_names


def test_old_schema_detected(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        conn.execute("CREATE TABLE cards (nation TEXT, name TEXT)")
        with pytest.raises(SystemExit, match="Old database schema"):
            initialize_schema(conn)


def test_upsert_cards_inserts_and_updates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)

        upsert_cards(conn, [_make_card()])

        upsert_cards(
            conn,
            [
                _make_card(
                    title=json.dumps({"en-EN": "Alpha Prime", "ru-RU": "Альфа Прайм"}),
                    kredits=3,
                    attack=4,
                )
            ],
        )

        cards = fetch_cards(conn)

    assert len(cards) == 1
    title = json.loads(cards[0]["title"])
    assert title["en-EN"] == "Alpha Prime"
    assert cards[0]["kredits"] == 3
    assert cards[0]["attack"] == 4


def test_upsert_preserves_quantity(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_make_card()])
        conn.execute("UPDATE cards SET quantity = 5 WHERE cardId = 'card-1'")
        conn.commit()

        upsert_cards(conn, [_make_card(kredits=99)])
        cards = fetch_cards(conn)

    assert cards[0]["quantity"] == 5
    assert cards[0]["kredits"] == 99


def test_fetch_cards_returns_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        cards = fetch_cards(conn)
    assert cards == []


_SAMPLE_CARD = _make_card(
    cardId="card-soviet-1",
    faction="Soviet",
    type="infantry",
    rarity="Standard",
    set="Base",
    title=json.dumps({"en-EN": "16th Rifle Regiment", "ru-RU": "16-й СТРЕЛКОВЫЙ ПОЛК"}),
    text=json.dumps({"en-EN": "Test card"}),
    kredits=1,
    attack=1,
    defense=2,
)

_SAMPLE_DECK = {
    "name": "Test Deck",
    "major_power": "soviet",
    "ally": "usa",
    "hq": "STALINGRAD",
    "deck_code": "%%TEST",
    "cards": [{"nation": "soviet", "name": "16th Rifle Regiment", "quantity": 2, "cost": 1}],
}


def test_find_card_id(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        card_id = find_card_id(conn, "Soviet", "16th Rifle Regiment", "en-EN")
        assert card_id == "card-soviet-1"

        missing = find_card_id(conn, "Soviet", "NONEXISTENT", "en-EN")
        assert missing is None


def test_find_card_id_ru(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        card_id = find_card_id(conn, "Soviet", "16-й СТРЕЛКОВЫЙ ПОЛК", "ru-RU")
        assert card_id == "card-soviet-1"


def test_insert_and_fetch_deck(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        deck_id = insert_deck(conn, _SAMPLE_DECK)
        insert_deck_cards(
            conn,
            deck_id,
            _SAMPLE_DECK["cards"],
            {"soviet": "Soviet"},
            "en-EN",
        )
        conn.commit()

        decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "Test Deck"
        assert decks[0]["major_power"] == "soviet"

        cards = fetch_deck_cards(conn, deck_id)
        assert len(cards) == 1
        title = json.loads(cards[0]["title"])
        assert title["en-EN"] == "16th Rifle Regiment"
        assert cards[0]["deck_quantity"] == 2
        assert cards[0]["deck_cost"] == 1


def test_find_deck_by_name(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        insert_deck(conn, _SAMPLE_DECK)
        conn.commit()

        found = find_deck_by_name(conn, "Test Deck")
        assert found is not None
        assert found["name"] == "Test Deck"

        not_found = find_deck_by_name(conn, "Nonexistent Deck")
        assert not_found is None


def test_deck_card_not_found(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)

        deck_id = insert_deck(conn, _SAMPLE_DECK)
        with pytest.raises(ValueError, match="Card not found"):
            insert_deck_cards(
                conn,
                deck_id,
                [{"nation": "soviet", "name": "MISSING", "quantity": 1, "cost": 1}],
                {"soviet": "Soviet"},
                "en-EN",
            )


def test_update_quantity(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        updated, not_found = update_quantity(
            conn,
            [
                ("Soviet", "16th Rifle Regiment", 5),
                ("USA", "NonExistent", 3),
            ],
            "en-EN",
        )

    assert updated == 1
    assert len(not_found) == 1
    assert "USA / NonExistent" in not_found


def test_update_quantity_skips_none_qty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        updated, not_found = update_quantity(
            conn,
            [("Soviet", "16th Rifle Regiment", None)],
            "en-EN",
        )

    assert updated == 0
    assert not_found == []


def test_update_quantity_skips_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)

        updated, not_found = update_quantity(
            conn,
            [("", "Card", 1), ("USA", "", 1)],
            "en-EN",
        )

    assert updated == 0
    assert not_found == []


def test_fetch_all_decks_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        decks = fetch_all_decks(conn)
    assert decks == []


def test_fetch_all_decks_multiple(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        insert_deck(conn, _SAMPLE_DECK)
        insert_deck(
            conn,
            {
                "name": "Deck B",
                "major_power": "usa",
                "ally": None,
                "hq": None,
                "deck_code": None,
                "cards": [],
            },
        )
        conn.commit()
        decks = fetch_all_decks(conn)

    assert len(decks) == 2
    assert decks[0]["name"] == "Test Deck"
    assert decks[1]["name"] == "Deck B"


def test_set_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        set_metadata(conn, "test_key", "test_value")

        row = conn.execute("SELECT value FROM metadata WHERE key = ?", ("test_key",)).fetchone()
        assert row[0] == "test_value"

        set_metadata(conn, "test_key", "new_value")
        row = conn.execute("SELECT value FROM metadata WHERE key = ?", ("test_key",)).fetchone()
        assert row[0] == "new_value"


def test_get_connection_enables_foreign_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk[0] == 1


# --- Tests for new exile/quantity functions ---

_EXILE_CARD = _make_card(
    cardId="card-poland-1",
    faction="Poland",
    title=json.dumps({"en-EN": "IL-2M PL", "ru-RU": "Ил-2М PL"}),
    exile="Soviet",
)


def test_find_card_id_by_exile_found(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_EXILE_CARD])

        card_id = find_card_id_by_exile(conn, "Soviet", "IL-2M PL", "en-EN")
        assert card_id == "card-poland-1"


def test_find_card_id_by_exile_not_found(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_EXILE_CARD])

        result = find_card_id_by_exile(conn, "USA", "IL-2M PL", "en-EN")
        assert result is None


def test_get_card_quantity_by_id_existing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_make_card(cardId="q-card", quantity=5)])
        conn.execute("UPDATE cards SET quantity = 5 WHERE cardId = 'q-card'")
        conn.commit()

        qty = get_card_quantity_by_id(conn, "q-card")
        assert qty == 5


def test_get_card_quantity_by_id_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)

        qty = get_card_quantity_by_id(conn, "nonexistent")
        assert qty == 0


def test_update_card_quantity_by_id(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_make_card(cardId="upd-card")])

        update_card_quantity_by_id(conn, "upd-card", 7)
        conn.commit()

        qty = get_card_quantity_by_id(conn, "upd-card")
        assert qty == 7


def test_insert_deck_cards_with_exile_fallback(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_EXILE_CARD])

        deck_id = insert_deck(conn, _SAMPLE_DECK)
        # Card is under Soviet nation in deck but has faction=Poland, exile=Soviet
        insert_deck_cards(
            conn,
            deck_id,
            [{"nation": "soviet", "name": "IL-2M PL", "quantity": 1, "cost": 2}],
            {"soviet": "Soviet"},
            "en-EN",
            use_exile_fallback=True,
        )
        conn.commit()

        cards = fetch_deck_cards(conn, deck_id)
        assert len(cards) == 1


def test_insert_deck_cards_exile_fallback_disabled_raises(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_EXILE_CARD])

        deck_id = insert_deck(conn, _SAMPLE_DECK)
        with pytest.raises(ValueError, match="Card not found"):
            insert_deck_cards(
                conn,
                deck_id,
                [{"nation": "soviet", "name": "IL-2M PL", "quantity": 1, "cost": 2}],
                {"soviet": "Soviet"},
                "en-EN",
                use_exile_fallback=False,
            )
