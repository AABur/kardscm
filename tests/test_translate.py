"""Tests for translate_card_for_export."""

from __future__ import annotations

import json

from kardscm.constants import KNOWN_ABILITIES
from kardscm.export import translate_card_for_export
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU


def _make_db_card(
    faction: str = "Soviet",
    title: dict | None = None,
    text: dict | None = None,
    type_: str = "infantry",
    rarity: str = "Standard",
    set_: str = "Base",
    kredits: int = 1,
    attack: int | None = 1,
    defense: int | None = 2,
    quantity: int = 0,
    **ability_overrides: int,
) -> dict:
    if title is None:
        title = {"en-EN": "Test Card", "ru-RU": "Тестовая карта"}
    if text is None:
        text = {"en-EN": "Description", "ru-RU": "Описание"}
    card: dict = {
        "faction": faction,
        "type": type_,
        "rarity": rarity,
        "set": set_,
        "title": json.dumps(title),
        "text": json.dumps(text),
        "kredits": kredits,
        "attack": attack,
        "defense": defense,
        "quantity": quantity,
    }
    for a in KNOWN_ABILITIES:
        card[f"ability_{a}"] = ability_overrides.get(f"ability_{a}", 0)
    return card


class TestTranslateCardEN:
    def test_basic_translation(self):
        card = _make_db_card()
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["faction"] == "Soviet Union"
        assert result["title"] == "Test Card"
        assert result["type"] == "Infantry"
        assert result["rarity"] == "Standard"
        assert result["set"] == "Base"
        assert result["text"] == "Description"

    def test_attributes(self):
        card = _make_db_card(ability_blitz=1, ability_guard=1)
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["attributes"] == "Blitz, Guard"

    def test_unknown_ability_not_in_output(self):
        card = _make_db_card(ability_blitz=1)
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["attributes"] == "Blitz"

    def test_nullable_fields(self):
        card = _make_db_card(attack=None, defense=None)
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["attack"] is None
        assert result["defense"] is None


class TestTranslateCardRU:
    def test_basic_translation(self):
        card = _make_db_card()
        result = translate_card_for_export(card, LANGUAGE_RU)
        assert result["faction"] == "Советский Союз"
        assert result["title"] == "Тестовая карта"
        assert result["type"] == "Пехота"
        assert result["rarity"] == "Стандартная"
        assert result["set"] == "Базовый"
        assert result["text"] == "Описание"

    def test_attributes_ru(self):
        card = _make_db_card(ability_guard=1)
        result = translate_card_for_export(card, LANGUAGE_RU)
        assert result["attributes"] == "Охрана"


class TestTranslateEdgeCases:
    def test_empty_title_json(self):
        card = _make_db_card()
        card["title"] = ""
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["title"] == ""

    def test_invalid_json_title(self):
        card = _make_db_card()
        card["title"] = "not json"
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["title"] == "not json"

    def test_missing_locale_falls_back_to_en(self):
        card = _make_db_card(title={"en-EN": "English Only"})
        result = translate_card_for_export(card, LANGUAGE_RU)
        assert result["title"] == "English Only"

    def test_empty_attributes(self):
        card = _make_db_card()
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["attributes"] == ""

    def test_quantity_preserved(self):
        card = _make_db_card(quantity=5)
        result = translate_card_for_export(card, LANGUAGE_EN)
        assert result["quantity"] == 5
