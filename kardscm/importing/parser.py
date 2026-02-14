"""Deck file parser for KARDS TXT export format."""

from __future__ import annotations

import re

from kardscm.constants import DECK_CARD_PATTERN, DECK_METADATA_KEYS
from kardscm.models import DeckCardEntry, ParsedDeck

_CARD_RE = re.compile(DECK_CARD_PATTERN)


def parse_deck_file(file_path: str) -> ParsedDeck:
    """Parse a deck TXT file into a ParsedDeck structure.

    Args:
        file_path: Path to the deck TXT file.

    Returns:
        Parsed deck data.

    Raises:
        ValueError: If required fields (name, major_power) are missing.
    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    name: str | None = None
    metadata: dict[str, str | None] = {"major_power": None, "ally": None, "hq": None}
    cards: list[DeckCardEntry] = []
    deck_code: str | None = None
    current_nation: str | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("%%"):
            deck_code = stripped
            continue

        meta_key = _parse_metadata_line(stripped)
        if meta_key is not None:
            key, value = meta_key
            metadata[key] = value
            continue

        nation = _parse_nation_header(stripped)
        if nation is not None:
            current_nation = nation
            continue

        card_match = _CARD_RE.match(stripped)
        if card_match and current_nation:
            cards.append(
                DeckCardEntry(
                    nation=current_nation,
                    name=card_match.group(3),
                    quantity=int(card_match.group(1)),
                    cost=int(card_match.group(2)),
                )
            )
            continue

        if name is None:
            name = stripped

    if not name:
        msg = "Deck name is missing"
        raise ValueError(msg)
    if not metadata["major_power"]:
        msg = "Major power is missing"
        raise ValueError(msg)

    return ParsedDeck(
        name=name,
        major_power=metadata["major_power"],
        ally=metadata["ally"],
        hq=metadata["hq"],
        deck_code=deck_code,
        cards=cards,
    )


def _parse_metadata_line(line: str) -> tuple[str, str] | None:
    """Try to parse a metadata line like 'Major power: soviet'."""
    for label, key in DECK_METADATA_KEYS.items():
        if line.startswith(f"{label}:"):
            value = line[len(label) + 1 :].strip()
            return key, value
    return None


def _parse_nation_header(line: str) -> str | None:
    """Try to parse a nation section header like 'soviet:'."""
    if line.endswith(":") and " " not in line:
        return line[:-1]
    return None
