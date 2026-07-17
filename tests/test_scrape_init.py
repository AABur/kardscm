"""Tests for kardscm.scraping.__init__ (scrape_cards orchestration + drift gate)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from kardscm.scraping import ApiContractDriftError, _check_api_drift, scrape_cards


@patch("kardscm.scraping._check_api_drift")
@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_success(mock_static_probe, mock_fetch, mock_normalize, _mock_drift):
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


@patch("kardscm.scraping._check_api_drift")
@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_skips_none(mock_static_probe, mock_fetch, mock_normalize, _mock_drift):
    mock_static_probe.return_value = {"url": "http://test", "headers": {}, "body": {}}
    mock_fetch.return_value = [{"cardId": "c1"}, {"bad": "data"}]
    mock_normalize.side_effect = [{"cardId": "c1"}, None]

    result = scrape_cards()
    assert len(result) == 1


@patch("kardscm.scraping._check_api_drift")
@patch("kardscm.scraping.normalize_card")
@patch("kardscm.scraping.fetch_all_cards")
@patch("kardscm.scraping.build_static_probe")
def test_scrape_cards_empty(mock_static_probe, mock_fetch, mock_normalize, _mock_drift):
    mock_static_probe.return_value = {"url": "http://test", "headers": {}, "body": {}}
    mock_fetch.return_value = []

    result = scrape_cards()
    assert result == []
    mock_normalize.assert_not_called()


def _raw_node(**json_overrides) -> dict:
    """Minimal raw API node (shape the drift snapshot consumes)."""
    base_json = {
        "title": {"en-EN": "T"},
        "type": "infantry",
        "faction": "Soviet",
        "rarity": "Standard",
        "set": "Base",
        "attributes": ["blitz"],
    }
    base_json.update(json_overrides)
    return {"cardId": "c", "json": base_json}


class TestApiDriftGate:
    def test_first_run_initializes_silently(self, tmp_path, monkeypatch):
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        monkeypatch.chdir(tmp_path)
        # No baseline yet → initialize from this sync, no raise.
        _check_api_drift([_raw_node()])
        assert (tmp_path / "baseline.json").exists()

    def test_no_drift_does_not_raise(self, tmp_path, monkeypatch):
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        monkeypatch.chdir(tmp_path)
        nodes = [_raw_node()]
        bm.save_baseline(bm.build_snapshot(nodes))
        _check_api_drift(nodes)  # identical observed → silent

    def test_benign_growth_does_not_raise(self, tmp_path, monkeypatch):
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        monkeypatch.chdir(tmp_path)
        bm.save_baseline(bm.build_snapshot([_raw_node()]))
        # More cards of the same shape = growth, not drift → silent.
        _check_api_drift([_raw_node(), _raw_node()])

    def test_contract_change_raises_carrying_the_observed_shape(self, tmp_path, monkeypatch):
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        monkeypatch.chdir(tmp_path)
        bm.save_baseline(bm.build_snapshot([_raw_node()]))
        # A new json key is a contract change → halt, carrying the snapshot.
        with pytest.raises(ApiContractDriftError) as exc_info:
            _check_api_drift([_raw_node(newField=1)])

        assert "newField" in exc_info.value.observed["json_keys"]
        assert exc_info.value.report.added_json_keys == ["newField"]

    def test_drift_writes_no_files(self, tmp_path, monkeypatch):
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        monkeypatch.chdir(tmp_path)
        bm.save_baseline(bm.build_snapshot([_raw_node()]))
        with pytest.raises(ApiContractDriftError):
            _check_api_drift([_raw_node(newField=1)])

        assert list(tmp_path.iterdir()) == [tmp_path / "baseline.json"]
