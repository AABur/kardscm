"""Tests for SQLite storage helpers."""

from pathlib import Path

from kards.storage import fetch_cards, get_connection, initialize_schema, upsert_cards


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
