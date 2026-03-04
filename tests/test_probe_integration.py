"""Tests for kardscm.scraping.probe — run_probe with mocked Playwright."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from kardscm.scraping.probe import run_probe


def _make_playwright_mock(captured_body: dict | None = None):
    """Create a fully mocked Playwright stack."""
    mock_page = MagicMock()
    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page
    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context
    mock_chromium = MagicMock()
    mock_chromium.launch.return_value = mock_browser
    mock_pw = MagicMock()
    mock_pw.chromium = mock_chromium
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)

    if captured_body is not None:

        def fake_goto(url, **kwargs):
            pass

        def fake_on(event, callback):
            if event == "request":
                mock_request = MagicMock()
                mock_request.method = "POST"
                mock_request.post_data = json.dumps(captured_body)
                mock_request.url = "https://api.example.com/graphql"
                mock_request.headers = {
                    "content-type": "application/json",
                    "authorization": "Bearer test",
                    "user-agent": "TestBrowser",
                }
                callback(mock_request)

        mock_page.goto = fake_goto
        mock_page.on = fake_on
        mock_page.wait_for_timeout = MagicMock()
    else:
        mock_page.wait_for_timeout = MagicMock()

    return mock_pw


@patch("kardscm.scraping.probe.sync_playwright")
def test_run_probe_success(mock_sync_pw):
    body = {"operationName": "GetCards", "query": "...", "variables": {}}
    mock_pw = _make_playwright_mock(captured_body=body)
    mock_sync_pw.return_value = mock_pw

    result = run_probe("https://example.com/collection")
    assert result["url"] == "https://api.example.com/graphql"
    assert result["body"]["operationName"] == "GetCards"
    assert "content-type" in result["headers"]
    assert "user-agent" not in result["headers"]


@patch("kardscm.scraping.probe.sync_playwright")
def test_run_probe_timeout(mock_sync_pw):
    mock_pw = _make_playwright_mock(captured_body=None)
    mock_sync_pw.return_value = mock_pw

    with pytest.raises(RuntimeError, match="No GraphQL request detected"):
        run_probe("https://example.com/collection")
