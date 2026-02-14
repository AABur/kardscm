"""Browser automation for collecting card data."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)


async def collect_api_data(url: str) -> list[dict[str, Any]]:
    """Collect API responses from the collection page.

    Args:
        url: Collection page URL.

    Returns:
        List of JSON responses from the API.
    """
    api_data: list[dict[str, Any]] = []
    playwright = await async_playwright().start()
    browser: Browser | None = None
    page: Page | None = None

    async def on_response(response: Any) -> None:
        response_url = response.url
        if ("graphql" in response_url.lower() or "api" in response_url.lower()) and response.ok:
            try:
                text = await response.text()
                if text:
                    try:
                        data = json.loads(text)
                        if "data" in data or "errors" in data:
                            api_data.append(data)
                            logger.info("API data received: %s bytes", len(text))
                    except json.JSONDecodeError:
                        pass
            except Exception as exc:
                logger.debug("Error reading response: %s", exc)

    try:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("response", on_response)

        await load_page(page, url)
        await load_all_cards(page)
        return api_data
    finally:
        await close_browser(playwright, browser, page)


async def close_browser(playwright: Any, browser: Browser | None, page: Page | None) -> None:
    """Close browser resources."""
    if page:
        await page.close()
    if browser:
        await browser.close()
    if playwright:
        await playwright.stop()


async def load_page(page: Page, url: str) -> None:
    """Load the collection page.

    Args:
        page: Playwright page instance.
        url: URL to load.
    """
    logger.info("Loading page %s...", url)
    await page.goto(url, wait_until="networkidle", timeout=60000)
    logger.info("Page loaded")
    await page.wait_for_timeout(2000)


async def load_all_cards(page: Page) -> None:
    """Load all cards by clicking the 'LOAD MORE' button."""
    logger.info("Loading all cards by clicking 'LOAD MORE'...")

    load_more_clicks = 0
    max_clicks = 50

    while load_more_clicks < max_clicks:
        buttons = await page.query_selector_all("button")

        load_more_button = None
        for button in buttons:
            try:
                text = await button.inner_text()
                if "LOAD MORE" in text.upper():
                    load_more_button = button
                    break
            except Exception:
                pass

        if not load_more_button:
            logger.info("'LOAD MORE' button not found. All cards loaded.")
            break

        try:
            await load_more_button.scroll_into_view_if_needed()
            await asyncio.sleep(0.3)
            await load_more_button.click()
            load_more_clicks += 1
            logger.info("Click on 'LOAD MORE' %s/%s", load_more_clicks, max_clicks)
            await asyncio.sleep(2)
        except Exception as exc:
            logger.warning("Error clicking LOAD MORE: %s", exc)
            break

    logger.info("Loading completed after %s clicks", load_more_clicks)
