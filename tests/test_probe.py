"""Tests for kardscm.scraping.probe."""

from __future__ import annotations

from kardscm.scraping.probe import _filter_headers, _is_graphql_request


class MockRequest:
    def __init__(self, method: str = "POST", post_data: str | None = None, url: str = ""):
        self.method = method
        self.post_data = post_data
        self.url = url


class TestIsGraphqlRequest:
    def test_valid_graphql(self):
        req = MockRequest(method="POST", post_data='{"operationName":"GetCards"}')
        assert _is_graphql_request(req) is True

    def test_with_query(self):
        req = MockRequest(method="POST", post_data='{"query":"{ cards { id } }"}')
        assert _is_graphql_request(req) is True

    def test_get_request(self):
        req = MockRequest(method="GET", post_data='{"operationName":"X"}')
        assert _is_graphql_request(req) is False

    def test_no_post_data(self):
        req = MockRequest(method="POST", post_data=None)
        assert _is_graphql_request(req) is False

    def test_invalid_json(self):
        req = MockRequest(method="POST", post_data="not json")
        assert _is_graphql_request(req) is False

    def test_no_graphql_keys(self):
        req = MockRequest(method="POST", post_data='{"foo":"bar"}')
        assert _is_graphql_request(req) is False


class TestFilterHeaders:
    def test_keeps_relevant(self):
        headers = {
            "content-type": "application/json",
            "authorization": "Bearer token",
            "user-agent": "Mozilla",
            "cookie": "session=abc",
        }
        result = _filter_headers(headers)
        assert "content-type" in result
        assert "authorization" in result
        assert "user-agent" not in result
        assert "cookie" not in result

    def test_empty(self):
        assert _filter_headers({}) == {}
