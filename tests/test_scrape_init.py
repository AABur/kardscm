"""Tests for kardscm.scraping.__init__ (scrape_cards orchestration)."""

from __future__ import annotations

from unittest.mock import patch

from kardscm.scraping import scrape_cards


@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_success(mock_static_probe, mock_fetch, mock_normalize):
    mock_static_probe.return_value = {"url": "http://test", "headers": {}, "body": {}}
    mock_fetch.return_value = [{"cardId": "c1"}, {"cardId": "c2"}]
    mock_normalize.side_effect = [
        {"cardId": "c1", "faction": "USA"},
        {"cardId": "c2", "faction": "Soviet"},
    ]

    result = scrape_cards()
    assert len(result) == 2
    mock_static_probe.assert_called_once()
    mock_fetch.assert_called_once()


@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_skips_none(mock_static_probe, mock_fetch, mock_normalize):
    mock_static_probe.return_value = {"url": "http://test", "headers": {}, "body": {}}
    mock_fetch.return_value = [{"cardId": "c1"}, {"bad": "data"}]
    mock_normalize.side_effect = [{"cardId": "c1"}, None]

    result = scrape_cards()
    assert len(result) == 1


@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_empty(mock_static_probe, mock_fetch, mock_normalize):
    mock_static_probe.return_value = {"url": "http://test", "headers": {}, "body": {}}
    mock_fetch.return_value = []

    result = scrape_cards()
    assert result == []
    mock_normalize.assert_not_called()
