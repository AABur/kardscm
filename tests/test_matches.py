"""Tests for match tracking functionality."""

from __future__ import annotations

import sqlite3

import pytest

from kardscm.storage import (
    compute_deck_stats,
    delete_deck,
    fetch_matches_by_deck,
    insert_deck,
    insert_match,
)


@pytest.fixture()
def deck_id(db_connection) -> int:
    """Insert a test deck and return its ID."""
    did = insert_deck(
        db_connection,
        {
            "name": "Test Deck",
            "major_power": "soviet",
            "ally": "usa",
            "hq": "STALINGRAD",
            "deck_code": "%%TEST",
            "cards": [],
        },
    )
    db_connection.commit()
    return did


class TestInsertMatch:
    def test_insert_and_fetch(self, db_connection, deck_id):
        mid = insert_match(db_connection, deck_id, "win", "Germany", "Japan")
        db_connection.commit()

        assert mid is not None
        matches = fetch_matches_by_deck(db_connection, deck_id)
        assert len(matches) == 1
        assert matches[0]["result"] == "win"
        assert matches[0]["opponent_major"] == "Germany"
        assert matches[0]["opponent_ally"] == "Japan"

    def test_multiple_matches(self, db_connection, deck_id):
        insert_match(db_connection, deck_id, "win", "Germany", "Japan")
        insert_match(db_connection, deck_id, "loss", "USA", "Britain")
        db_connection.commit()

        matches = fetch_matches_by_deck(db_connection, deck_id)
        assert len(matches) == 2

    def test_fetch_empty(self, db_connection, deck_id):
        matches = fetch_matches_by_deck(db_connection, deck_id)
        assert matches == []


class TestComputeDeckStats:
    def test_with_matches(self, db_connection, deck_id):
        insert_match(db_connection, deck_id, "win", "Germany", "Japan")
        insert_match(db_connection, deck_id, "win", "Germany", "Japan")
        insert_match(db_connection, deck_id, "loss", "USA", "Britain")
        db_connection.commit()

        stats = compute_deck_stats(db_connection, deck_id)
        assert stats is not None
        assert stats["total"] == 3
        assert stats["wins"] == 2
        assert stats["losses"] == 1
        assert stats["winrate"] == 66.7

        assert ("Germany", "Japan") in stats["matchups"]
        assert stats["matchups"][("Germany", "Japan")]["wins"] == 2
        assert stats["matchups"][("Germany", "Japan")]["losses"] == 0

        assert ("USA", "Britain") in stats["matchups"]
        assert stats["matchups"][("USA", "Britain")]["wins"] == 0
        assert stats["matchups"][("USA", "Britain")]["losses"] == 1

    def test_empty_returns_none(self, db_connection, deck_id):
        stats = compute_deck_stats(db_connection, deck_id)
        assert stats is None


class TestMatchConstraints:
    def test_invalid_result_rejected(self, db_connection, deck_id):
        with pytest.raises(sqlite3.IntegrityError):
            insert_match(db_connection, deck_id, "draw", "Germany", "Japan")

    def test_cascade_on_deck_delete(self, db_connection, deck_id):
        insert_match(db_connection, deck_id, "win", "Germany", "Japan")
        insert_match(db_connection, deck_id, "loss", "USA", "Britain")
        db_connection.commit()

        delete_deck(db_connection, deck_id)
        db_connection.commit()

        matches = fetch_matches_by_deck(db_connection, deck_id)
        assert matches == []
