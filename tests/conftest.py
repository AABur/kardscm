"""Shared test fixtures."""

from __future__ import annotations

import sqlite3

import pytest

from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
from kardscm.storage import get_connection, initialize_schema


@pytest.fixture()
def lang_config_ru():
    """Russian language configuration."""
    return LANGUAGE_RU


@pytest.fixture()
def lang_config_en():
    """English language configuration."""
    return LANGUAGE_EN


@pytest.fixture()
def sample_card() -> dict[str, str]:
    """Sample card dictionary for reuse across tests."""
    return {
        "CardId": "card-soviet-1",
        "Name": "16-й СТРЕЛКОВЫЙ ПОЛК",
        "Nation": "Советский Союз",
        "Type": "Пехота",
        "Rarity": "Стандартная",
        "Abilities": "Охрана",
        "Set": "Базовый",
        "Quantity": "2",
        "Credits": "1",
        "Attack": "1",
        "Defense": "2",
        "Description": "Тестовая карта",
    }


@pytest.fixture()
def sample_card_en() -> dict[str, str]:
    """Sample English card dictionary."""
    return {
        "CardId": "card-usa-1",
        "Name": "M4 Sherman",
        "Nation": "USA",
        "Type": "Tank",
        "Rarity": "Standard",
        "Abilities": "Blitz",
        "Set": "Base",
        "Quantity": "1",
        "Credits": "4",
        "Attack": "3",
        "Defense": "4",
        "Description": "Test tank card",
    }


@pytest.fixture()
def db_connection(tmp_path) -> sqlite3.Connection:
    """SQLite in-memory-like connection with initialized schema."""
    db_path = tmp_path / "test.db"
    conn = get_connection(db_path)
    initialize_schema(conn)
    yield conn
    conn.close()


@pytest.fixture()
def sample_deck() -> dict:
    """Sample ParsedDeck for reuse across tests."""
    return {
        "name": "Test Deck",
        "major_power": "soviet",
        "ally": "usa",
        "hq": "СТАЛИНГРАД",
        "deck_code": "%%TEST",
        "cards": [
            {"nation": "soviet", "name": "16-й СТРЕЛКОВЫЙ ПОЛК", "quantity": 2, "cost": 1},
            {"nation": "usa", "name": "M4 Sherman", "quantity": 1, "cost": 4},
        ],
    }
