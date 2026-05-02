"""Type definitions for card data structures."""

from __future__ import annotations

from typing import Any, TypedDict


class CardDict(TypedDict):
    """Card data structure matching the DB schema (Stage 2+)."""

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
    operationCost: int | None
    reserved: int
    image: str
    can_create: str | None
    exile: str | None
    # Binary ability flags — 1 if the card has the ability, 0 otherwise.
    ability_alpine: int
    ability_ambush: int
    ability_blitz: int
    ability_bond: int
    ability_covert: int
    ability_fury: int
    ability_guard: int
    ability_heavyArmor1: int
    ability_heavyArmor2: int
    ability_heavyArmor3: int
    ability_intel1: int
    ability_intel2: int
    ability_intel3: int
    ability_mobilize: int
    ability_salvage: int
    ability_shock: int
    ability_smokescreen: int


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


class FieldChange(TypedDict):
    """One changed field for a card during sync diff."""

    field: str
    old: Any
    new: Any


class CardChange(TypedDict):
    """A card whose compared characteristics differ between DB and API.

    `card` carries the new (API) record so callers can render the current
    state. `changes` lists the per-field deltas.
    """

    card: CardDict
    changes: list[FieldChange]


class DiffReport(TypedDict):
    """Result of compute_diff over old DB rows and new API cards."""

    new: list[CardDict]
    changed: list[CardChange]
    reserved_in: list[CardDict]
    reserved_out: list[CardDict]
    removed: list[dict]
