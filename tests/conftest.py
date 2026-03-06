"""Shared test fixtures."""

from __future__ import annotations

import json
import sqlite3

import pytest

from kardscm.models import CardDict
from kardscm.storage import get_connection, initialize_schema


@pytest.fixture()
def sample_card() -> CardDict:
    """Sample CardDict for reuse across tests."""
    return CardDict(
        cardId="card-soviet-1",
        importId="imp-1",
        imageUrl="https://example.com/img.png",
        thumbUrl="https://example.com/thumb.png",
        faction="Soviet",
        type="infantry",
        rarity="Standard",
        set="Base",
        title=json.dumps({"en-EN": "16th Rifle Regiment", "ru-RU": "16-й СТРЕЛКОВЫЙ ПОЛК"}),
        text=json.dumps({"en-EN": "Test card", "ru-RU": "Тестовая карта"}),
        kredits=1,
        attack=1,
        defense=2,
        attributes=json.dumps(["guard"]),
        operationCost=None,
        reserved=0,
        image="img.png",
        can_create=None,
        exile=None,
    )


@pytest.fixture()
def db_connection(tmp_path) -> sqlite3.Connection:
    """SQLite connection with initialized schema."""
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    initialize_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def make_card():
    """Factory fixture for creating test card dicts with defaults."""
    def _factory(**overrides):
        base = {
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
            "attributes": json.dumps([]),
            "operationCost": None,
            "reserved": 0,
            "image": "",
            "can_create": None,
            "exile": None,
        }
        base.update(overrides)
        return base
    return _factory


@pytest.fixture()
def sample_deck() -> dict:
    """Sample ParsedDeck for reuse across tests."""
    return {
        "name": "Test Deck",
        "major_power": "soviet",
        "ally": "usa",
        "hq": "STALINGRAD",
        "deck_code": "%%TEST",
        "cards": [
            {"nation": "soviet", "name": "16th Rifle Regiment", "quantity": 2, "cost": 1},
            {"nation": "usa", "name": "M4 Sherman", "quantity": 1, "cost": 4},
        ],
    }
