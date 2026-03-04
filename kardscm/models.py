"""Type definitions for card data structures."""

from __future__ import annotations

from typing import TypedDict


class CardDict(TypedDict):
    """Card data structure matching the new DB schema."""

    cardId: str
    importId: str
    imageUrl: str
    thumbUrl: str
    faction: str
    type: str
    rarity: str
    set: str
    title: str
    text: str
    kredits: int
    attack: int | None
    defense: int | None
    attributes: str
    operationCost: int | None
    reserved: int
    image: str
    can_create: str | None
    exile: str | None


class ProbeData(TypedDict):
    """Data captured from Playwright GraphQL intercept."""

    url: str
    headers: dict[str, str]
    body: dict


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
