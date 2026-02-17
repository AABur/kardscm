"""Tests for kardscm.scraping.browser."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from kardscm.scraping.browser import close_browser, collect_api_data, load_all_cards

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(url: str, ok: bool = True, body: str | None = None):
    """Create a mock Playwright response."""
    resp = AsyncMock()
    resp.url = url
    resp.ok = ok
    if body is not None:
        resp.text.return_value = body
    else:
        resp.text.side_effect = Exception("no body")
    return resp


def _setup_collect_mocks(response):
    """Set up mocks for collect_api_data and return (pw_context, fake_load_page)."""
    captured: dict = {}

    page = AsyncMock()
    page.on = lambda event, cb: captured.update(callback=cb) if event == "response" else None

    browser = AsyncMock()
    browser.new_page.return_value = page

    pw_instance = AsyncMock()
    pw_instance.chromium.launch.return_value = browser

    pw_context = AsyncMock()
    pw_context.start.return_value = pw_instance

    async def fake_load_page(p, url):
        if "callback" in captured:
            await captured["callback"](response)

    return pw_context, fake_load_page


async def _run_collect(response) -> list:
    """Run collect_api_data with mocked Playwright, returning captured data."""
    pw_context, fake_load_page = _setup_collect_mocks(response)
    with (
        patch("kardscm.scraping.browser.async_playwright", return_value=pw_context),
        patch("kardscm.scraping.browser.load_page", side_effect=fake_load_page),
        patch("kardscm.scraping.browser.load_all_cards", new_callable=AsyncMock),
    ):
        return await collect_api_data("https://example.com/en/decks/collection")


# ---------------------------------------------------------------------------
# collect_api_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_collect_api_data_captures_graphql():
    """GraphQL responses with 'data' key are captured."""
    payload = json.dumps({"data": {"cards": []}})
    response = _make_response("https://example.com/graphql", body=payload)

    result = await _run_collect(response)

    assert len(result) == 1
    assert result[0]["data"] == {"cards": []}


@pytest.mark.asyncio()
async def test_collect_api_data_ignores_non_api():
    """URLs without 'graphql' or 'api' are not captured."""
    payload = json.dumps({"data": {"cards": []}})
    response = _make_response("https://example.com/static/style.css", body=payload)

    result = await _run_collect(response)

    assert result == []


@pytest.mark.asyncio()
async def test_collect_api_data_ignores_failed_responses():
    """Responses with ok=False are skipped."""
    payload = json.dumps({"data": {"cards": []}})
    response = _make_response("https://example.com/graphql", ok=False, body=payload)

    result = await _run_collect(response)

    assert result == []


@pytest.mark.asyncio()
async def test_collect_api_data_ignores_invalid_json():
    """Invalid JSON in response body is skipped."""
    response = _make_response("https://example.com/graphql", body="not json{")

    result = await _run_collect(response)

    assert result == []


@pytest.mark.asyncio()
async def test_collect_api_data_ignores_non_data_json():
    """JSON without 'data' or 'errors' keys is skipped."""
    payload = json.dumps({"status": "ok", "message": "hello"})
    response = _make_response("https://example.com/api/health", body=payload)

    result = await _run_collect(response)

    assert result == []


# ---------------------------------------------------------------------------
# close_browser
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_close_browser_all_none():
    """All params None -> no crash."""
    await close_browser(None, None, None)


@pytest.mark.asyncio()
async def test_close_browser_closes_all():
    """Calls close on page/browser and stop on playwright."""
    page = AsyncMock()
    browser = AsyncMock()
    pw = AsyncMock()

    await close_browser(pw, browser, page)

    page.close.assert_awaited_once()
    browser.close.assert_awaited_once()
    pw.stop.assert_awaited_once()


# ---------------------------------------------------------------------------
# load_all_cards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_load_all_cards_no_button():
    """No LOAD MORE button -> immediate exit, 0 clicks."""
    page = AsyncMock()
    page.query_selector_all.return_value = []

    await load_all_cards(page)

    page.query_selector_all.assert_awaited_once_with("button")


@pytest.mark.asyncio()
async def test_load_all_cards_clicks_button():
    """Button found, clicked, then disappears."""
    button = AsyncMock()
    button.inner_text.return_value = "LOAD MORE"

    page = AsyncMock()
    page.query_selector_all.side_effect = [[button], []]

    with patch("kardscm.scraping.browser.asyncio.sleep", new_callable=AsyncMock):
        await load_all_cards(page)

    button.click.assert_awaited_once()


@pytest.mark.asyncio()
async def test_load_all_cards_max_clicks():
    """Button never disappears -> stops at max_clicks=50."""
    button = AsyncMock()
    button.inner_text.return_value = "LOAD MORE"

    page = AsyncMock()
    page.query_selector_all.return_value = [button]

    with patch("kardscm.scraping.browser.asyncio.sleep", new_callable=AsyncMock):
        await load_all_cards(page)

    assert button.click.await_count == 50


@pytest.mark.asyncio()
async def test_load_all_cards_click_error():
    """Error during click -> break."""
    button = AsyncMock()
    button.inner_text.return_value = "LOAD MORE"
    button.scroll_into_view_if_needed.side_effect = Exception("element detached")

    page = AsyncMock()
    page.query_selector_all.return_value = [button]

    with patch("kardscm.scraping.browser.asyncio.sleep", new_callable=AsyncMock):
        await load_all_cards(page)

    button.click.assert_not_awaited()
