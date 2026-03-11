"""Tests for kardscm.advisor — context assembly and LLM dispatch."""

from __future__ import annotations

import json

import pytest

from kardscm.advisor.context import build_analysis_context
from kardscm.advisor.llm import get_llm_response
from kardscm.config import LANGUAGE_EN, AdvisorConfig
from kardscm.models import DeckStats, MatchupStats


@pytest.fixture()
def deck_meta() -> dict:
    return {
        "name": "Test Deck",
        "major_power": "soviet",
        "ally": "usa",
        "hq": "STALINGRAD",
    }


@pytest.fixture()
def deck_cards() -> list[dict]:
    return [
        {
            "faction": "Soviet",
            "title": json.dumps({"en-EN": "16th Rifle Regiment"}),
            "type": "infantry",
            "rarity": "Standard",
            "set": "Base",
            "kredits": 1,
            "attack": 1,
            "defense": 2,
            "text": json.dumps({"en-EN": "A basic unit"}),
            "attributes": json.dumps(["guard"]),
            "deck_quantity": 2,
            "deck_cost": 1,
        },
    ]


@pytest.fixture()
def sample_stats() -> DeckStats:
    return DeckStats(
        total=3,
        wins=2,
        losses=1,
        winrate=66.7,
        matchups={
            ("Germany", "Japan"): MatchupStats(wins=2, losses=0),
            ("USA", "Britain"): MatchupStats(wins=0, losses=1),
        },
    )


class TestBuildContext:
    def test_with_stats(self, deck_meta, deck_cards, sample_stats, tmp_path):
        system, user = build_analysis_context(
            deck_meta, deck_cards, sample_stats, "standard",
            rules_dir=str(tmp_path / "no_rules"),
            lang_config=LANGUAGE_EN,
        )
        assert "KARDS" in system
        assert "Test Deck" in user
        assert "16th Rifle Regiment" in user
        assert "66.7%" in user
        assert "Germany/Japan" in user

    def test_no_stats(self, deck_meta, deck_cards, tmp_path):
        system, user = build_analysis_context(
            deck_meta, deck_cards, None, "standard",
            rules_dir=str(tmp_path / "no_rules"),
            lang_config=LANGUAGE_EN,
        )
        assert "No match statistics available" in user

    def test_no_rules_dir(self, deck_meta, deck_cards, tmp_path):
        system, user = build_analysis_context(
            deck_meta, deck_cards, None, "standard",
            rules_dir=str(tmp_path / "nonexistent"),
            lang_config=LANGUAGE_EN,
        )
        assert "Game Rules" not in user

    def test_with_rules(self, deck_meta, deck_cards, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "deck_building.md").write_text("Max 40 cards per deck.", encoding="utf-8")

        system, user = build_analysis_context(
            deck_meta, deck_cards, None, "standard",
            rules_dir=str(rules_dir),
            lang_config=LANGUAGE_EN,
        )
        assert "Game Rules" in user
        assert "Max 40 cards" in user

    def test_depth_concise(self, deck_meta, deck_cards, tmp_path):
        _, user = build_analysis_context(
            deck_meta, deck_cards, None, "concise",
            rules_dir=str(tmp_path / "no_rules"),
            lang_config=LANGUAGE_EN,
        )
        assert "3-5 bullet points" in user

    def test_depth_detailed(self, deck_meta, deck_cards, tmp_path):
        _, user = build_analysis_context(
            deck_meta, deck_cards, None, "detailed",
            rules_dir=str(tmp_path / "no_rules"),
            lang_config=LANGUAGE_EN,
        )
        assert "comprehensive" in user

    def test_depth_default_fallback(self, deck_meta, deck_cards, tmp_path):
        _, user = build_analysis_context(
            deck_meta, deck_cards, None, "unknown_depth",
            rules_dir=str(tmp_path / "no_rules"),
            lang_config=LANGUAGE_EN,
        )
        assert "structured analysis" in user


class TestGetLlmResponse:
    def test_unsupported_provider(self):
        config = AdvisorConfig(provider="unsupported")
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            get_llm_response("sys", "user", config)
