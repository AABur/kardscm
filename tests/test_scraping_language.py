"""Tests that the GraphQL `$language` value flows from CLI down to the probe."""

from __future__ import annotations

from unittest.mock import patch

from kardscm.scraping import scrape_cards
from kardscm.scraping.probe import build_static_probe


def test_build_static_probe_default_is_english():
    probe = build_static_probe()
    assert probe["body"]["variables"]["language"] == "en"


def test_build_static_probe_injects_given_language():
    probe = build_static_probe("ru")
    assert probe["body"]["variables"]["language"] == "ru"


def test_build_static_probe_supports_compound_codes():
    probe = build_static_probe("zh-Hant")
    assert probe["body"]["variables"]["language"] == "zh-Hant"


@patch("kardscm.scraping.normalize_card", return_value=None)
@patch("kardscm.scraping.fetch_all_cards", return_value=[])
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_forwards_language(mock_probe, mock_fetch, _normalize):
    mock_probe.return_value = {"url": "u", "headers": {}, "body": {}}
    scrape_cards("ja")
    mock_probe.assert_called_once_with("ja")
