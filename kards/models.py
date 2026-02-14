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
