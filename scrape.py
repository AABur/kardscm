"""Scraping and translation helpers for card collections."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx
from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kards.com"
COLLECTION_URL = f"{BASE_URL}/ru/decks/collection"

LANGUAGE_CODE = "ru"
LANGUAGE_NAME = "Russian"

RU_KEYS = ("ru", "ru-RU")
EN_KEYS = ("en", "en-EN")

RU_LANG_INDEX = 9

KNOWN_MAPPINGS: dict[str, dict[str, str]] = {
    "type": {
        "infantry": "llkqn9",
        "tank": "QIFcAI",
        "armor": "QIFcAI",
        "artillery": "ziY9j1",
        "fighter": "al73ht",
        "air": "al73ht",
        "order": "UYUgdb",
        "countermeasure": "qM208o",
    },
    "faction": {
        "Soviet": "iROGPL",
        "USA": "Mqy/Zy",
        "Japan": "A1ET6E",
        "Germany": "XTtR6a",
        "Britain": "OICU0U",
        "France": "+gY+iO",
        "Italy": "MFljzs",
        "Poland": "sfwBnA",
    },
    "rarity": {
        "Standard": "TJBHlP",
        "Limited": "HhURN3",
        "Special": "qBFI6F",
        "Elite": "JEzmqf",
    },
    "set": {
        "Base": "Nzwli2",
        "Allegiance": "bPobF4",
        "TheatersOfWar": "MPVNE8",
        "Breakthrough": "paHq3y",
        "WorldAtWar": "tkXxPO",
        "CovertOps": "/Adfjf",
        "BloodAndIron": "vhFlLC",
        "Legions": "a6nh/L",
        "NavalWarfare": "6bDKSi",
        "Homefront": "5rE6vr",
        "WinterWar": "wDZgXG",
    },
}

ESCAPE_RE = re.compile(r"\\(x[0-9A-Fa-f]{2}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|r|n|t|\\|\"|')")


def decode_escapes(text: str) -> str:
    """Decode common escape sequences without altering other characters.

    Args:
        text: Text possibly containing escape sequences.

    Returns:
        Text with escape sequences decoded.
    """
    if not text:
        return text

    def replace_match(match: re.Match[str]) -> str:
        token = match.group(1)
        if token == "r":
            return "\r"
        if token == "n":
            return "\n"
        if token == "t":
            return "\t"
        if token == "\\":
            return "\\"
        if token == '"':
            return '"'
        if token == "'":
            return "'"
        if token.startswith("x"):
            return chr(int(token[1:], 16))
        if token.startswith("u"):
            return chr(int(token[1:], 16))
        if token.startswith("U"):
            return chr(int(token[1:], 16))
        return match.group(0)

    return ESCAPE_RE.sub(replace_match, text)


def strip_quotes(text: str) -> str:
    """Remove surrounding quotes from text.

    Args:
        text: Text possibly wrapped in quotes.

    Returns:
        Text with surrounding quotes removed.
    """
    if not text:
        return text
    quote_pairs = [("«", "»"), ('"', '"'), ("'", "'")]
    for open_q, close_q in quote_pairs:
        if text.startswith(open_q) and text.endswith(close_q):
            text = text[len(open_q) : -len(close_q)]
    return text


def sanitize_text(text: str) -> str:
    """Sanitize text by removing quotes, newlines, and decoding escapes.

    Args:
        text: Text to sanitize.

    Returns:
        Sanitized text with quotes removed, newlines replaced with spaces,
        escape sequences decoded, and duplicate spaces removed.
    """
    if not text:
        return text
    text = decode_escapes(text)
    text = strip_quotes(text)
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = " ".join(text.split())
    return text


def extract_localized_field(
    field_data: dict[str, str] | str,
    field_name: str = "",
) -> str:
    """Extract localized field value with fallback logic.

    Priority: Russian -> English -> empty string.

    Args:
        field_data: Dictionary with language codes as keys or string value.
        field_name: Field name for debug logging.

    Returns:
        Localized string value or empty string if not found.
    """
    if not isinstance(field_data, dict):
        return str(field_data) if field_data else ""

    for key in RU_KEYS:
        if key in field_data:
            return field_data[key]

    for key in EN_KEYS:
        if key in field_data:
            logger.debug("%s not available in Russian, using English fallback", field_name)
            return field_data[key]

    return ""


def translate_value(
    category: str,
    value: str,
    translations: dict[str, str],
) -> str:
    """Translate a value using loaded translations.

    Args:
        category: Category name (type, faction, rarity, set).
        value: Original value from API.
        translations: Translation dictionary.

    Returns:
        Translated value or original if not found.
    """
    if not value:
        return ""

    normalized = value.strip()
    category_map = KNOWN_MAPPINGS.get(category, {})
    trans_id = category_map.get(normalized)

    if not trans_id:
        for key, tid in category_map.items():
            if key.lower() == normalized.lower():
                trans_id = tid
                break

    if trans_id and trans_id in translations:
        translated = decode_escapes(translations[trans_id])
        return strip_quotes(translated)

    return normalized


async def load_translations() -> dict[str, str]:
    """Load translations for Russian from website JS files.

    Returns:
        Translation dictionary for Russian.
    """
    logger.info("Loading translations for Russian...")
    translations: dict[str, str] = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(COLLECTION_URL)
            html = response.text

            js_urls = re.findall(r'/_next/static/chunks/[^"\']+\.js', html)
            translation_content = ""
            for js_url in js_urls:
                if "2840-" in js_url:
                    js_response = await client.get(f"{BASE_URL}{js_url}")
                    translation_content = js_response.text
                    break

            if translation_content:
                translations = _parse_translations(translation_content)
                logger.info("Loaded %s translation keys", len(translations))
            else:
                logger.warning("Translation JS file not found, using fallback")

    except Exception as exc:
        logger.warning("Failed to load translations dynamically: %s", exc)
        logger.info("Using fallback translations")

    return translations


def _parse_translations(js_content: str) -> dict[str, str]:
    """Parse translations from JS content.

    Args:
        js_content: JavaScript file content.

    Returns:
        Mapping from translation ID to Russian text.
    """
    translations: dict[str, str] = {}

    all_ids: set[str] = set()
    for category_mappings in KNOWN_MAPPINGS.values():
        all_ids.update(category_mappings.values())

    for trans_id in all_ids:
        pattern = re.compile(rf'"{re.escape(trans_id)}":"([^"]*)"')
        matches = pattern.findall(js_content)

        if matches and RU_LANG_INDEX < len(matches):
            translations[trans_id] = matches[RU_LANG_INDEX]
        elif matches:
            translations[trans_id] = matches[-1]

    return translations


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


def parse_api_data(
    api_data: list[dict[str, Any]],
    translations: dict[str, str],
) -> list[dict[str, str]]:
    """Parse API data to extract cards.

    Args:
        api_data: Collected API responses.
        translations: Translation dictionary.

    Returns:
        List of card dictionaries.
    """
    logger.info("Parsing %s API responses...", len(api_data))
    cards: list[dict[str, str]] = []
    card_ids: set[str] = set()

    for api_response in api_data:
        try:
            data = api_response.get("data")
            if not isinstance(data, dict):
                continue

            for value in data.values():
                if isinstance(value, dict) and "edges" in value:
                    edges = value.get("edges", [])
                    for edge in edges:
                        node = edge.get("node")
                        if not isinstance(node, dict):
                            continue
                        card_id = node.get("cardId", "")
                        if not card_id or card_id in card_ids:
                            continue
                        card_info = build_card(node, card_id, translations)
                        if card_info:
                            cards.append(card_info)
                            card_ids.add(card_id)
        except Exception as exc:
            logger.warning("Error parsing response: %s", exc)

    logger.info("Total cards extracted: %s", len(cards))
    return cards


def build_card(
    card_node: dict[str, Any],
    card_id: str,
    translations: dict[str, str],
) -> dict[str, str] | None:
    """Build a card dictionary from API node data.

    Args:
        card_node: Card node data from API.
        card_id: Card identifier from API.
        translations: Translation dictionary.

    Returns:
        Card dictionary or None if required fields are missing.
    """
    json_data = card_node.get("json", {})

    title = extract_localized_field(json_data.get("title", {}), "title")
    if not title:
        return None

    faction_raw = json_data.get("faction") or ""
    type_raw = json_data.get("type") or ""
    rarity_raw = json_data.get("rarity") or ""
    set_raw = json_data.get("set") or ""
    description = extract_localized_field(json_data.get("text", {}), "description")

    card_info: dict[str, str] = {
        "CardId": card_id,
        "Nation": sanitize_text(translate_value("faction", str(faction_raw), translations)),
        "Name": sanitize_text(title),
        "Type": sanitize_text(translate_value("type", str(type_raw), translations)),
        "Rarity": sanitize_text(translate_value("rarity", str(rarity_raw), translations)),
        "Abilities": "",
        "Set": sanitize_text(translate_value("set", str(set_raw), translations)),
        "Quantity": "",
        "Credits": str(json_data.get("kredits", "")),
        "Attack": str(json_data.get("attack", "")),
        "Defense": str(json_data.get("defense", "")),
        "Description": sanitize_text(description),
    }

    return card_info


async def scrape_cards() -> list[dict[str, str]]:
    """Scrape cards from the Russian collection page.

    Returns:
        List of card dictionaries.
    """
    translations = await load_translations()
    api_data = await collect_api_data(COLLECTION_URL)
    return parse_api_data(api_data, translations)
