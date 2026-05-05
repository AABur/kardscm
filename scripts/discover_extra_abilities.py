"""Discover cardIds matching a GraphQL search term.

Dev-only helper for populating ``kardscm/data/extra_abilities.toml``.
Hits the live KARDS GraphQL API with ``q=<search_term>`` and prints
matching cards (cardId + EN title) for inclusion in the seed file.

Usage:
    uv run python scripts/discover_extra_abilities.py <search_term> [language]

Examples:
    uv run python scripts/discover_extra_abilities.py pincer
    uv run python scripts/discover_extra_abilities.py pincer en
    uv run python scripts/discover_extra_abilities.py клещи ru
"""

from __future__ import annotations

import logging
import sys

from kardscm.scraping.fetcher import fetch_all_cards
from kardscm.scraping.probe import build_static_probe

logging.basicConfig(level=logging.WARNING, format="%(message)s")


def main() -> int:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(__doc__)
        return 2

    search_term = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) == 3 else "en"

    probe = build_static_probe(language=language)
    probe["body"]["variables"]["q"] = search_term

    cards = fetch_all_cards(probe)
    print(f"# {len(cards)} cards matching q={search_term!r} (language={language!r})")
    for card in cards:
        card_id = card.get("cardId", "?")
        json_data = card.get("json") or {}
        title = json_data.get("title") or {}
        title_en = title.get("en-EN") if isinstance(title, dict) else str(title)
        print(f'  "{card_id}",  # {title_en}')
    return 0


if __name__ == "__main__":
    sys.exit(main())
