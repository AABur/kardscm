"""Tests for SQLite storage helpers."""

from pathlib import Path

import pytest

from kardscm.storage import (
    fetch_all_decks,
    fetch_cards,
    fetch_deck_cards,
    find_card_id_by_nation_name,
    find_deck_by_name,
    get_connection,
    initialize_schema,
    insert_deck,
    insert_deck_cards,
    upsert_cards,
)


def test_initialize_schema_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()

    table_names = {row[0] for row in rows}
    assert "cards" in table_names
    assert "metadata" in table_names


def test_upsert_cards_inserts_and_updates(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)

        upsert_cards(
            conn,
            [
                {
                    "CardId": "card-1",
                    "Name": "Alpha",
                    "Nation": "USA",
                    "Type": "Infantry",
                    "Rarity": "Standard",
                    "Set": "Base",
                    "Credits": "2",
                    "Attack": "3",
                    "Defense": "2",
                    "Description": "First",
                }
            ],
        )

        upsert_cards(
            conn,
            [
                {
                    "CardId": "card-1",
                    "Name": "Alpha Prime",
                    "Nation": "USA",
                    "Type": "Infantry",
                    "Rarity": "Standard",
                    "Set": "Base",
                    "Credits": "3",
                    "Attack": "4",
                    "Defense": "2",
                    "Description": "Updated",
                }
            ],
        )

        cards = fetch_cards(conn)

    assert len(cards) == 1
    assert cards[0]["Name"] == "Alpha Prime"
    assert cards[0]["Credits"] == "3"
    assert cards[0]["Attack"] == "4"
    assert cards[0]["Description"] == "Updated"


def test_fetch_cards_returns_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        cards = fetch_cards(conn)

    assert cards == []


_SAMPLE_CARD = {
    "CardId": "card-soviet-1",
    "Name": "16-й СТРЕЛКОВЫЙ ПОЛК",
    "Nation": "Soviet",
    "Type": "Infantry",
    "Rarity": "Standard",
    "Set": "Base",
    "Credits": "1",
    "Attack": "1",
    "Defense": "2",
    "Description": "Test card",
}

_SAMPLE_DECK = {
    "name": "Test Deck",
    "major_power": "soviet",
    "ally": "usa",
    "hq": "СТАЛИНГРАД",
    "deck_code": "%%TEST",
    "cards": [{"nation": "soviet", "name": "16-й СТРЕЛКОВЫЙ ПОЛК", "quantity": 2, "cost": 1}],
}


def test_find_card_id_by_nation_name(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        card_id = find_card_id_by_nation_name(conn, "Soviet", "16-й СТРЕЛКОВЫЙ ПОЛК")
        assert card_id == "card-soviet-1"

        missing = find_card_id_by_nation_name(conn, "Soviet", "NONEXISTENT")
        assert missing is None


def test_insert_and_fetch_deck(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [_SAMPLE_CARD])

        deck_id = insert_deck(conn, _SAMPLE_DECK)
        insert_deck_cards(conn, deck_id, _SAMPLE_DECK["cards"], {"soviet": "Soviet"})
        conn.commit()

        decks = fetch_all_decks(conn)
        assert len(decks) == 1
        assert decks[0]["name"] == "Test Deck"
        assert decks[0]["major_power"] == "soviet"

        cards = fetch_deck_cards(conn, deck_id)
        assert len(cards) == 1
        assert cards[0]["name"] == "16-й СТРЕЛКОВЫЙ ПОЛК"
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
        assert found["major_power"] == "soviet"

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
            )
