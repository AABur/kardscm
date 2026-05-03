"""Tests for kardscm.scraping.normalizer."""

from __future__ import annotations

import json

from kardscm.scraping.normalizer import normalize_card


def _make_node(
    card_id: str = "test-1",
    faction: str = "Soviet",
    title: dict | None = None,
    text: dict | None = None,
    type_: str = "infantry",
    rarity: str = "Standard",
    set_: str = "Base",
    kredits: int = 1,
    attack: int | None = 1,
    defense: int | None = 2,
    attributes: list | None = None,
) -> dict:
    if title is None:
        title = {"en-EN": "Test Card", "ru-RU": "Тестовая карта"}
    if text is None:
        text = {"en-EN": "Description", "ru-RU": "Описание"}
    return {
        "cardId": card_id,
        "imageUrl": "https://example.com/img.png",
        "thumbUrl": "https://example.com/thumb.png",
        "json": {
            "id": card_id,
            "import_id": f"imp-{card_id}",
            "faction": faction,
            "type": type_,
            "rarity": rarity,
            "set": set_,
            "title": title,
            "text": text,
            "kredits": kredits,
            "attack": attack,
            "defense": defense,
            "attributes": attributes or [],
            "operationCost": None,
            "reserved": 0,
            "image": "img.png",
            "can_create": None,
            "exile": None,
        },
    }


def test_normalize_basic():
    node = _make_node()
    result = normalize_card(node)
    assert result is not None
    assert result["cardId"] == "test-1"
    assert result["faction"] == "Soviet"
    assert result["type"] == "infantry"
    assert result["kredits"] == 1
    title = json.loads(result["title"])
    assert title["en-EN"] == "Test Card"


def test_normalize_with_attributes():
    node = _make_node(attributes=["blitz", "guard"])
    result = normalize_card(node)
    assert result is not None
    assert result["ability_blitz"] == 1
    assert result["ability_guard"] == 1
    assert result["ability_alpine"] == 0


def test_normalize_no_card_id():
    node = _make_node()
    del node["cardId"]
    assert normalize_card(node) is None


def test_normalize_no_title():
    node = _make_node(title={})
    # Empty title dict is falsy for .get("title") check
    node["json"]["title"] = None
    assert normalize_card(node) is None


def test_normalize_no_faction():
    node = _make_node(faction="")
    assert normalize_card(node) is None


def test_normalize_nullable_attack_defense():
    node = _make_node(attack=None, defense=None)
    result = normalize_card(node)
    assert result is not None
    assert result["attack"] is None
    assert result["defense"] is None


def test_normalize_can_create():
    node = _make_node()
    node["json"]["can_create"] = ["card-2", "card-3"]
    result = normalize_card(node)
    assert result is not None
    can_create = json.loads(result["can_create"])
    assert can_create == ["card-2", "card-3"]


def test_normalize_no_json():
    node = {"cardId": "test-1"}
    assert normalize_card(node) is None
