"""Type definitions for card data structures."""

from __future__ import annotations

from typing import TypedDict


class CardDict(TypedDict, total=False):
    """Card dictionary structure."""

    CardId: str
    Name: str
    Nation: str
    Type: str
    Rarity: str
    Abilities: str
    Set: str
    Quantity: str
    Credits: str
    Attack: str
    Defense: str
    Description: str


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
