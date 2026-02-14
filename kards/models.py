"""Type definitions for card data structures."""

from __future__ import annotations

from typing import TypedDict


class DeckCardEntry(TypedDict):
    """Single card entry in a deck."""

    nation: str
    name: str
    quantity: int
    cost: int


class ParsedDeck(TypedDict):
    """Parsed deck structure from TXT file."""

    name: str
    major_power: str
    ally: str | None
    hq: str | None
    deck_code: str | None
    cards: list[DeckCardEntry]
