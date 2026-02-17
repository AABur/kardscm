"""Tests for kardscm.scraping.scraper (parse_api_data, build_card)."""

from __future__ import annotations

from kardscm.config import LANGUAGE_EN, LANGUAGE_RU
from kardscm.scraping.scraper import build_card, parse_api_data


def _make_card_node(
    card_id: str = "card-1",
    title: dict | None = None,
    faction: str = "Soviet",
    card_type: str = "infantry",
    rarity: str = "Standard",
    card_set: str = "Base",
    attributes: list[str] | None = None,
    kredits: int = 2,
    attack: int = 3,
    defense: int = 2,
    text: dict | None = None,
) -> dict:
    """Helper to create a card node similar to API response."""
    if title is None:
        title = {"en": "Test Card", "ru": "Тестовая карта"}
    if text is None:
        text = {"en": "Description", "ru": "Описание"}
    if attributes is None:
        attributes = []
    return {
        "cardId": card_id,
        "json": {
            "title": title,
            "faction": faction,
            "type": card_type,
            "rarity": rarity,
            "set": card_set,
            "attributes": attributes,
            "kredits": kredits,
            "attack": attack,
            "defense": defense,
            "text": text,
        },
    }


def _make_api_response(*nodes: dict) -> dict:
    """Wrap card nodes into an API response structure."""
    edges = [{"node": node} for node in nodes]
    return {"data": {"cards": {"edges": edges}}}


class TestBuildCard:
    def test_basic(self):
        node = _make_card_node()
        card = build_card(node, "card-1", {}, LANGUAGE_EN)

        assert card is not None
        assert card["CardId"] == "card-1"
        assert card["Name"] == "Test Card"
        assert card["Credits"] == "2"
        assert card["Attack"] == "3"
        assert card["Defense"] == "2"

    def test_missing_title(self):
        node = _make_card_node(title={})
        card = build_card(node, "card-1", {}, LANGUAGE_EN)
        assert card is None

    def test_abilities_filtering(self):
        node = _make_card_node(attributes=["guard", "blitz", "BecomesVeteran:1"])
        card = build_card(node, "card-1", {}, LANGUAGE_EN)

        assert card is not None
        assert "Guard" in card["Abilities"]
        assert "Blitz" in card["Abilities"]
        assert "BecomesVeteran" not in card["Abilities"]

    def test_faction_fallback(self):
        node = _make_card_node(faction="Soviet")
        card = build_card(node, "card-1", {}, LANGUAGE_EN)

        assert card is not None
        assert card["Nation"] == "Soviet Union"

    def test_faction_translated(self):
        translations = {"iROGPL": "Советский Союз"}
        node = _make_card_node(faction="Soviet")
        card = build_card(node, "card-1", translations, LANGUAGE_RU)

        assert card is not None
        assert card["Nation"] == "Советский Союз"

    def test_russian_title(self):
        node = _make_card_node(title={"ru": "Тестовая карта", "en": "Test Card"})
        card = build_card(node, "card-1", {}, LANGUAGE_RU)

        assert card is not None
        assert card["Name"] == "Тестовая карта"

    def test_empty_optional_fields(self):
        node = _make_card_node(attack=None, defense=None, kredits=None)
        node["json"]["attack"] = None
        node["json"]["defense"] = None
        node["json"]["kredits"] = None
        card = build_card(node, "card-1", {}, LANGUAGE_EN)

        assert card is not None
        assert card["Attack"] == "None"
        assert card["Defense"] == "None"


class TestParseApiData:
    def test_deduplication(self):
        node = _make_card_node(card_id="card-dup")
        response = _make_api_response(node, node)
        cards = parse_api_data([response], {}, LANGUAGE_EN)

        assert len(cards) == 1

    def test_empty_list(self):
        cards = parse_api_data([], {}, LANGUAGE_EN)
        assert cards == []

    def test_malformed_response(self):
        good_response = _make_api_response(_make_card_node(card_id="good-1"))
        bad_response = {"data": "not_a_dict"}
        cards = parse_api_data([good_response, bad_response], {}, LANGUAGE_EN)

        assert len(cards) == 1
        assert cards[0]["CardId"] == "good-1"

    def test_multiple_responses(self):
        resp1 = _make_api_response(_make_card_node(card_id="c1"))
        resp2 = _make_api_response(_make_card_node(card_id="c2"))
        cards = parse_api_data([resp1, resp2], {}, LANGUAGE_EN)

        assert len(cards) == 2
        ids = {c["CardId"] for c in cards}
        assert ids == {"c1", "c2"}

    def test_skips_nodes_without_card_id(self):
        node = _make_card_node()
        node["cardId"] = ""
        response = _make_api_response(node)
        cards = parse_api_data([response], {}, LANGUAGE_EN)

        assert len(cards) == 0

    def test_response_with_no_edges(self):
        response = {"data": {"cards": {"edges": []}}}
        cards = parse_api_data([response], {}, LANGUAGE_EN)
        assert cards == []

    def test_exception_in_one_response_continues(self):
        good = _make_api_response(_make_card_node(card_id="ok"))
        bad = {"data": {"cards": {"edges": [{"node": None}]}}}
        cards = parse_api_data([bad, good], {}, LANGUAGE_EN)

        assert len(cards) == 1
