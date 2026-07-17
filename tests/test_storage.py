"""Tests for SQLite storage helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kardscm.storage import (
    delete_all_decks,
    delete_cards,
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


@pytest.fixture()
def storage_deck() -> dict:
    """Sample deck with one Soviet card for storage tests."""
    return {
        "name": "Test Deck",
        "major_power": "soviet",
        "ally": "usa",
        "hq": "STALINGRAD",
        "deck_code": "%%TEST",
        "cards": [{"nation": "soviet", "name": "16th Rifle Regiment", "quantity": 2, "cost": 1}],
    }


@pytest.fixture()
def exile_card(make_card) -> dict:
    """Sample exile card for storage tests."""
    return make_card(
        cardId="card-poland-1",
        faction="Poland",
        title=json.dumps({"en-EN": "IL-2M PL", "ru-RU": "Ил-2М PL"}),
        exile="Soviet",
    )


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


def test_upsert_cards_inserts_and_updates(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card()])
    upsert_cards(
        db_connection,
        [
            make_card(
                title=json.dumps({"en-EN": "Alpha Prime", "ru-RU": "Альфа Прайм"}),
                kredits=3,
                attack=4,
            )
        ],
    )

    cards = fetch_cards(db_connection)

    assert len(cards) == 1
    title = json.loads(cards[0]["title"])
    assert title["en-EN"] == "Alpha Prime"
    assert cards[0]["kredits"] == 3
    assert cards[0]["attack"] == 4


def test_upsert_preserves_quantity(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card()])
    db_connection.execute("UPDATE cards SET quantity = 5 WHERE cardId = 'card-1'")
    db_connection.commit()

    upsert_cards(db_connection, [make_card(kredits=99)])
    cards = fetch_cards(db_connection)

    assert cards[0]["quantity"] == 5
    assert cards[0]["kredits"] == 99


def test_fetch_cards_returns_empty(db_connection) -> None:
    cards = fetch_cards(db_connection)
    assert cards == []


def test_find_card_id(db_connection, sample_card) -> None:
    upsert_cards(db_connection, [sample_card])

    card_id = find_card_id(db_connection, "Soviet", "16th Rifle Regiment", "en-EN")
    assert card_id == "card-soviet-1"

    missing = find_card_id(db_connection, "Soviet", "NONEXISTENT", "en-EN")
    assert missing is None


def test_find_card_id_ru(db_connection, sample_card) -> None:
    upsert_cards(db_connection, [sample_card])

    card_id = find_card_id(db_connection, "Soviet", "16-й СТРЕЛКОВЫЙ ПОЛК", "ru-RU")
    assert card_id == "card-soviet-1"


def test_insert_and_fetch_deck(db_connection, sample_card, storage_deck) -> None:
    upsert_cards(db_connection, [sample_card])

    deck_id = insert_deck(db_connection, storage_deck)
    insert_deck_cards(
        db_connection,
        deck_id,
        storage_deck["cards"],
        "en-EN",
    )
    db_connection.commit()

    decks = fetch_all_decks(db_connection)
    assert len(decks) == 1
    assert decks[0]["name"] == "Test Deck"
    assert decks[0]["major_power"] == "soviet"

    cards = fetch_deck_cards(db_connection, deck_id)
    assert len(cards) == 1
    title = json.loads(cards[0]["title"])
    assert title["en-EN"] == "16th Rifle Regiment"
    assert cards[0]["deck_quantity"] == 2
    assert cards[0]["deck_cost"] == 1


def test_find_deck_by_name(db_connection, storage_deck) -> None:
    insert_deck(db_connection, storage_deck)
    db_connection.commit()

    found = find_deck_by_name(db_connection, "Test Deck")
    assert found is not None
    assert found["name"] == "Test Deck"

    not_found = find_deck_by_name(db_connection, "Nonexistent Deck")
    assert not_found is None


def test_deck_card_not_found(db_connection, storage_deck) -> None:
    deck_id = insert_deck(db_connection, storage_deck)
    with pytest.raises(ValueError, match="Card not found"):
        insert_deck_cards(
            db_connection,
            deck_id,
            [{"nation": "soviet", "name": "MISSING", "quantity": 1, "cost": 1}],
            "en-EN",
        )


def test_update_quantity(db_connection, sample_card) -> None:
    upsert_cards(db_connection, [sample_card])

    updated, not_found = update_quantity(
        db_connection,
        [
            ("Soviet", "16th Rifle Regiment", 5),
            ("USA", "NonExistent", 3),
        ],
        "en-EN",
    )

    assert updated == 1
    assert len(not_found) == 1
    assert "USA / NonExistent" in not_found


def test_update_quantity_skips_none_qty(db_connection, sample_card) -> None:
    upsert_cards(db_connection, [sample_card])

    updated, not_found = update_quantity(
        db_connection,
        [("Soviet", "16th Rifle Regiment", None)],
        "en-EN",
    )

    assert updated == 0
    assert not_found == []


def test_update_quantity_skips_empty(db_connection) -> None:
    updated, not_found = update_quantity(
        db_connection,
        [("", "Card", 1), ("USA", "", 1)],
        "en-EN",
    )

    assert updated == 0
    assert not_found == []


def test_fetch_all_decks_empty(db_connection) -> None:
    decks = fetch_all_decks(db_connection)
    assert decks == []


def test_fetch_all_decks_multiple(db_connection, storage_deck) -> None:
    insert_deck(db_connection, storage_deck)
    insert_deck(
        db_connection,
        {
            "name": "Deck B",
            "major_power": "usa",
            "ally": None,
            "hq": None,
            "deck_code": None,
            "cards": [],
        },
    )
    db_connection.commit()
    decks = fetch_all_decks(db_connection)

    assert len(decks) == 2
    assert decks[0]["name"] == "Test Deck"
    assert decks[1]["name"] == "Deck B"


def test_set_metadata(db_connection) -> None:
    set_metadata(db_connection, "test_key", "test_value")

    row = db_connection.execute(
        "SELECT value FROM metadata WHERE key = ?", ("test_key",)
    ).fetchone()
    assert row[0] == "test_value"

    set_metadata(db_connection, "test_key", "new_value")
    row = db_connection.execute(
        "SELECT value FROM metadata WHERE key = ?", ("test_key",)
    ).fetchone()
    assert row[0] == "new_value"


def test_get_connection_enables_foreign_keys(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    with get_connection(db_path) as conn:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk[0] == 1


# --- Tests for new exile/quantity functions ---


def test_find_card_id_by_exile_found(db_connection, exile_card) -> None:
    upsert_cards(db_connection, [exile_card])

    card_id = find_card_id_by_exile(db_connection, "Soviet", "IL-2M PL", "en-EN")
    assert card_id == "card-poland-1"


def test_find_card_id_by_exile_not_found(db_connection, exile_card) -> None:
    upsert_cards(db_connection, [exile_card])

    result = find_card_id_by_exile(db_connection, "USA", "IL-2M PL", "en-EN")
    assert result is None


def test_get_card_quantity_by_id_existing(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="q-card")])
    db_connection.execute("UPDATE cards SET quantity = 5 WHERE cardId = 'q-card'")
    db_connection.commit()

    qty = get_card_quantity_by_id(db_connection, "q-card")
    assert qty == 5


def test_get_card_quantity_by_id_missing(db_connection) -> None:
    qty = get_card_quantity_by_id(db_connection, "nonexistent")
    assert qty == 0


def test_update_card_quantity_by_id(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="upd-card")])

    update_card_quantity_by_id(db_connection, "upd-card", 3)
    db_connection.commit()

    qty = get_card_quantity_by_id(db_connection, "upd-card")
    assert qty == 3


def test_insert_deck_cards_with_exile_fallback(db_connection, exile_card, storage_deck) -> None:
    upsert_cards(db_connection, [exile_card])

    deck_id = insert_deck(db_connection, storage_deck)
    # Card is under Soviet nation in deck but has faction=Poland, exile=Soviet
    insert_deck_cards(
        db_connection,
        deck_id,
        [{"nation": "soviet", "name": "IL-2M PL", "quantity": 1, "cost": 2}],
        "en-EN",
        use_exile_fallback=True,
    )
    db_connection.commit()

    cards = fetch_deck_cards(db_connection, deck_id)
    assert len(cards) == 1


def test_insert_deck_cards_exile_fallback_disabled_raises(
    db_connection, exile_card, storage_deck
) -> None:
    upsert_cards(db_connection, [exile_card])

    deck_id = insert_deck(db_connection, storage_deck)
    with pytest.raises(ValueError, match="Card not found"):
        insert_deck_cards(
            db_connection,
            deck_id,
            [{"nation": "soviet", "name": "IL-2M PL", "quantity": 1, "cost": 2}],
            "en-EN",
            use_exile_fallback=False,
        )


def test_update_quantity_matches_nbsp_in_db(db_connection, make_card) -> None:
    nbsp_card = make_card(
        cardId="nbsp-card",
        faction="Britain",
        title=json.dumps({"en-EN": "GLADIATOR Mk I", "ru-RU": "GLADIATOR Mk I"}),
    )
    upsert_cards(db_connection, [nbsp_card])

    updated, not_found = update_quantity(
        db_connection,
        [("Britain", "GLADIATOR Mk I", 4)],
        "ru-RU",
    )

    assert updated == 1
    assert not_found == []
    qty = db_connection.execute("SELECT quantity FROM cards WHERE cardId = 'nbsp-card'").fetchone()[
        0
    ]
    assert qty == 4


def test_update_quantity_matches_double_space_in_db(db_connection, make_card) -> None:
    dbl_card = make_card(
        cardId="dbl-card",
        faction="USA",
        title=json.dumps({"en-EN": "USS FITCH", "ru-RU": "USS  ФИТЧ"}),
    )
    upsert_cards(db_connection, [dbl_card])

    updated, not_found = update_quantity(
        db_connection,
        [("USA", "USS ФИТЧ", 2)],
        "ru-RU",
    )

    assert updated == 1
    assert not_found == []


def test_find_card_id_matches_nbsp(db_connection, make_card) -> None:
    upsert_cards(
        db_connection,
        [
            make_card(
                cardId="nbsp-find",
                faction="Germany",
                title=json.dumps({"en-EN": "PANTHER G", "ru-RU": "PANTHER G"}),
            )
        ],
    )

    assert find_card_id(db_connection, "Germany", "PANTHER G", "ru-RU") == "nbsp-find"


def test_find_card_id_by_exile_matches_nbsp(db_connection, make_card) -> None:
    upsert_cards(
        db_connection,
        [
            make_card(
                cardId="exile-nbsp",
                faction="Poland",
                exile="Soviet",
                title=json.dumps({"en-EN": "IL-2M PL", "ru-RU": "ИЛ-2М PL"}),
            )
        ],
    )

    assert find_card_id_by_exile(db_connection, "Soviet", "ИЛ-2М PL", "ru-RU") == "exile-nbsp"


def test_delete_all_decks(db_connection, storage_deck) -> None:
    deck_a = {**storage_deck, "name": "Deck A"}
    deck_b = {**storage_deck, "name": "Deck B"}
    insert_deck(db_connection, deck_a)
    insert_deck(db_connection, deck_b)
    db_connection.commit()

    count = delete_all_decks(db_connection)
    db_connection.commit()

    assert count == 2
    assert fetch_all_decks(db_connection) == []


def test_delete_cards_removes_only_listed_ids(db_connection, make_card) -> None:
    upsert_cards(
        db_connection,
        [
            make_card(cardId="A"),
            make_card(cardId="B"),
            make_card(cardId="C"),
        ],
    )

    deleted = delete_cards(db_connection, ["B", "C"])

    assert deleted == 2
    remaining = {row["cardId"] for row in fetch_cards(db_connection)}
    assert remaining == {"A"}


def test_delete_cards_preserves_other_quantities(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="A"), make_card(cardId="B")])
    db_connection.execute("UPDATE cards SET quantity = 7 WHERE cardId = 'A'")
    db_connection.commit()

    delete_cards(db_connection, ["B"])

    rows = fetch_cards(db_connection)
    assert len(rows) == 1
    assert rows[0]["cardId"] == "A"
    assert rows[0]["quantity"] == 7


def test_delete_cards_empty_input_is_noop(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="A")])
    assert delete_cards(db_connection, []) == 0
    assert len(fetch_cards(db_connection)) == 1


# ---------------------------------------------------------------------------
# Rarity cap
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rarity", "requested", "expected"),
    [
        ("Standard", 9, 4),
        ("Limited", 9, 3),
        ("Special", 9, 2),
        ("Elite", 9, 1),
        ("Standard", 2, 2),
    ],
)
def test_update_card_quantity_by_id_caps_by_rarity(
    db_connection, make_card, rarity, requested, expected
) -> None:
    upsert_cards(db_connection, [make_card(cardId="A", rarity=rarity)])

    update_card_quantity_by_id(db_connection, "A", requested)

    assert get_card_quantity_by_id(db_connection, "A") == expected


def test_update_quantity_caps_by_rarity(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="A", rarity="Elite")])

    updated, not_found = update_quantity(db_connection, [("USA", "Alpha", 9)], "en-EN")

    assert (updated, not_found) == (1, [])
    assert get_card_quantity_by_id(db_connection, "A") == 1


def test_update_quantity_warns_when_capping(db_connection, make_card, caplog) -> None:
    upsert_cards(db_connection, [make_card(cardId="A", rarity="Elite")])

    with caplog.at_level("WARNING"):
        update_quantity(db_connection, [("USA", "Alpha", 9)], "en-EN")

    assert "9" in caplog.text and "1" in caplog.text


def test_update_card_quantity_by_id_warns_when_capping(db_connection, make_card, caplog) -> None:
    upsert_cards(db_connection, [make_card(cardId="A", rarity="Elite")])

    with caplog.at_level("WARNING"):
        update_card_quantity_by_id(db_connection, "A", 9)

    assert "9" in caplog.text and "1" in caplog.text


def test_unknown_rarity_falls_back_to_standard_cap(db_connection, make_card) -> None:
    upsert_cards(db_connection, [make_card(cardId="A", rarity="Mythic")])

    update_card_quantity_by_id(db_connection, "A", 9)

    assert get_card_quantity_by_id(db_connection, "A") == 4
