"""Tests for kardscm.scraping.fetcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kardscm.scraping.fetcher import (
    _extract_card,
    _find_edges_or_nodes,
    _find_page_info,
    fetch_all_cards,
)


class TestFindEdgesOrNodes:
    def test_edges_at_top(self):
        data = {"edges": [1, 2, 3]}
        assert _find_edges_or_nodes(data) == [1, 2, 3]

    def test_nodes_at_top(self):
        data = {"nodes": [4, 5]}
        assert _find_edges_or_nodes(data) == [4, 5]

    def test_nested(self):
        data = {"data": {"cards": {"edges": [1]}}}
        assert _find_edges_or_nodes(data) == [1]

    def test_not_found(self):
        assert _find_edges_or_nodes({"foo": "bar"}) is None

    def test_in_list(self):
        data = [{"edges": [1]}]
        assert _find_edges_or_nodes(data) == [1]


class TestFindPageInfo:
    def test_found(self):
        data = {"data": {"cards": {"pageInfo": {"hasNextPage": True}}}}
        assert _find_page_info(data) == {"hasNextPage": True}

    def test_not_found(self):
        assert _find_page_info({"foo": "bar"}) is None


class TestExtractCard:
    def test_with_node(self):
        item = {"node": {"cardId": "1"}, "cursor": "abc"}
        assert _extract_card(item) == {"cardId": "1"}

    def test_without_node(self):
        item = {"cardId": "2"}
        assert _extract_card(item) == {"cardId": "2"}


class TestFetchAllCards:
    @pytest.fixture()
    def mock_httpx_client(self):
        with patch("kardscm.scraping.fetcher.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client
            yield mock_client

    @pytest.fixture()
    def default_probe(self):
        return {
            "url": "https://api.example.com/graphql",
            "headers": {},
            "body": {"variables": {"offset": 0, "first": 50}, "query": ""},
        }

    def _make_response(self, data):
        resp = MagicMock()
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        return resp

    def test_single_page(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response(
            {
                "data": {
                    "cards": {
                        "edges": [
                            {"node": {"cardId": "c1"}},
                            {"node": {"cardId": "c2"}},
                        ]
                    }
                }
            }
        )

        result = fetch_all_cards(default_probe)
        assert len(result) == 2
        assert result[0]["cardId"] == "c1"

    def test_deduplication(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response(
            {
                "data": {
                    "cards": {
                        "edges": [
                            {"node": {"cardId": "c1"}},
                            {"node": {"cardId": "c1"}},
                        ]
                    }
                }
            }
        )

        result = fetch_all_cards(default_probe)
        assert len(result) == 1

    def test_graphql_errors_stop(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response({"errors": [{"message": "fail"}]})

        result = fetch_all_cards(default_probe)
        assert result == []

    def test_empty_edges_stops(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response(
            {"data": {"cards": {"edges": []}}}
        )

        result = fetch_all_cards(default_probe)
        assert result == []

    def test_no_data_stops(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response({"data": {"something": "else"}})

        result = fetch_all_cards(default_probe)
        assert result == []

    def test_limit_from_query_text(self, mock_httpx_client):
        mock_httpx_client.post.return_value = self._make_response(
            {"data": {"cards": {"edges": [{"node": {"cardId": "c1"}}]}}}
        )

        probe = {
            "url": "https://api.example.com/graphql",
            "headers": {},
            "body": {"variables": {"offset": 0}, "query": "cards(first: 20)"},
        }

        result = fetch_all_cards(probe)
        assert len(result) == 1

    def test_nodes_instead_of_edges(self, mock_httpx_client, default_probe):
        mock_httpx_client.post.return_value = self._make_response(
            {"data": {"cards": {"nodes": [{"cardId": "c1"}, {"cardId": "c2"}]}}}
        )

        result = fetch_all_cards(default_probe)
        assert len(result) == 2
