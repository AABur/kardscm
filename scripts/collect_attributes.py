"""Collect all unique card attributes from kards.com API.

Loads all cards via Playwright, extracts unique attribute values,
prints a summary report and saves to attributes_report.json.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from kardscm.config import get_language_config
from kardscm.scraping.browser import collect_api_data

OUTPUT_FILE = Path(__file__).parent / "attributes_report.json"


def extract_attributes(api_data: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Extract attributes from API responses.

    Returns:
        Mapping of attribute value to list of card titles that have it.
    """
    attr_cards: dict[str, list[str]] = defaultdict(list)
    card_ids: set[str] = set()

    for api_response in api_data:
        data = api_response.get("data")
        if not isinstance(data, dict):
            continue

        for value in data.values():
            if not isinstance(value, dict) or "edges" not in value:
                continue

            for edge in value.get("edges", []):
                node = edge.get("node")
                if not isinstance(node, dict):
                    continue

                card_id = node.get("cardId", "")
                if not card_id or card_id in card_ids:
                    continue
                card_ids.add(card_id)

                json_data = node.get("json", {})
                title_data = json_data.get("title", {})
                title = title_data.get("en", "") or next(
                    (v for v in title_data.values() if isinstance(v, str) and v), card_id
                )
                attributes = json_data.get("attributes", [])

                for attr in attributes:
                    attr_cards[attr].append(title)

    return dict(attr_cards)


async def main() -> None:
    lang_config = get_language_config()
    url = lang_config.collection_url
    print(f"Language: {lang_config.name} ({lang_config.code})")
    print(f"URL: {url}")
    print()

    print("Loading all cards (this may take a few minutes)...")
    api_data = await collect_api_data(url)
    print(f"API responses collected: {len(api_data)}")
    print()

    attr_cards = extract_attributes(api_data)

    if not attr_cards:
        print("No attributes found.")
        return

    # Sort by count descending
    sorted_attrs = sorted(attr_cards.items(), key=lambda x: len(x[1]), reverse=True)

    total_cards_with_attrs = len({card for cards in attr_cards.values() for card in cards})
    print(f"Unique attributes: {len(sorted_attrs)}")
    print(f"Cards with at least one attribute: {total_cards_with_attrs}")
    print()
    print("--- Attributes Report ---")
    print()

    for attr, cards in sorted_attrs:
        examples = ", ".join(cards[:3])
        suffix = f", ... (+{len(cards) - 3})" if len(cards) > 3 else ""
        print(f"  {attr}")
        print(f"    Count: {len(cards)} | Examples: {examples}{suffix}")
        print()

    # Save report
    report = {
        "total_unique_attributes": len(sorted_attrs),
        "total_cards_with_attributes": total_cards_with_attrs,
        "attributes": [
            {
                "name": attr,
                "count": len(cards),
                "examples": cards[:3],
            }
            for attr, cards in sorted_attrs
        ],
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Report saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
