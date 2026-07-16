# KARDS Collection Manager

Local-first manager for a player's KARDS collection and saved decks:
syncs the official card set into a local database, tracks owned
quantities, and exports collection/deck data.

## Language

**Collection**:
The full set of KARDS cards together with the player's owned quantity per
card — a replica of the in-game collection, whose only added value is
richer filtering and management than the game offers. A card the player
owns zero copies of is still part of the Collection. There is no separate
word for the card set without quantities.
_Avoid_: Catalog

**Faction**:
The power a card belongs to (Soviet, USA, Britain, Germany, Japan, France,
Italy, Poland, Finland).
_Avoid_: Nation (appears only as a KARDS client TXT deck-file artifact)

**Deck**:
A saved deck brought in from a KARDS client TXT file. Because a deck comes
from the game client, it is evidence of ownership: the player owns at
least as many copies of each card as the deck uses. A Collection quantity
below a deck's count means the Collection is stale — never that the deck
is invalid. A deck using fewer copies than owned is normal.

**Quantity**:
The number of copies of a card the player owns. Managed by the player,
never touched by sync. Capped by rarity exactly as in the game
(Standard 4, Limited 3, Special 2, Elite 1) — a quantity above the cap is
a data error, not player freedom, and every write path enforces the cap.

**Baseline**:
The committed snapshot of the API contract shape that sync checks the
live response against. Drift is measured relative to the Baseline;
accepting drift promotes the observed shape to become the new Baseline.

**Spawnable**:
A card that cannot be obtained in packs or crafted — it only appears
in-game when another card creates it. Spawnable cards are part of the
Collection as reference material: the player looks up what a spawned card
does. They are hidden by default behind a view toggle; owning them is
meaningless but nothing enforces a zero quantity — the Collection mirrors
the game, it does not police it.

**Exile**:
A cross-faction link on a card: the card belongs to one faction but may be
played in decks of another faction (its exile faction), reflecting the
game's exile-forces mechanic. Deck import falls back to the exile link when
a card is not found under its own faction.

**Diff**:
The comparison of card content between the local database and a fresh API
pull: new cards, changed stats/text, reserve transitions, removed cards.
The player reviews and approves a Diff before it is applied.
_Avoid_: Drift (that word is for contract shape changes)

**Drift**:
A change in the *shape* of the API contract against the committed baseline:
a field added or removed, a new faction/type/rarity/ability value. Drift
halts sync until the player reviews and accepts the new baseline.
_Avoid_: Diff (that word is for card content changes)

**Reserved**:
A card state set by the game (not the player): the card has been moved to
the reserve pool. Cards transition into and out of reserve over time, so
sync reports these transitions as their own category rather than as a
generic field change.

**Ability**:
A named game mechanic a card has (guard, blitz, smokescreen, …). One concept
regardless of source: regular abilities come from the card JSON in the
GraphQL API; extra abilities are manually curated for mechanics the API does
not expose. The split may be revisited — the game recently introduced its own
categorization — but for now source is the only distinction.
_Avoid_: Attribute
