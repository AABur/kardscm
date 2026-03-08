"""Tests for kardscm.scraping.probe."""

from __future__ import annotations

import pytest

from kardscm.scraping.probe import _filter_headers, _is_graphql_request


class MockRequest:
    def __init__(self, method: str = "POST", post_data: str | None = None, url: str = ""):
        self.method = method
        self.post_data = post_data
        self.url = url


@pytest.mark.parametrize(
    ("method", "post_data", "expected"),
    [
        ("POST", '{"operationName":"GetCards"}', True),
        ("POST", '{"query":"{ cards { id } }"}', True),
        ("GET", '{"operationName":"X"}', False),
        ("POST", None, False),
        ("POST", "not json", False),
        ("POST", '{"foo":"bar"}', False),
    ],
    ids=[
        "valid_graphql",
        "with_query",
        "get_request",
        "no_post_data",
        "invalid_json",
        "no_graphql_keys",
    ],
)
def test_is_graphql_request(method, post_data, expected):
    req = MockRequest(method=method, post_data=post_data)
    assert _is_graphql_request(req) is expected


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
