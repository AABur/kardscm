# MVP Technical Specification

## Local LLM Advisor for KARDS

Version: 1.0  
Last updated: March 12, 2026

## 1. Scope

This specification covers the first deliverable only:
- local rules synchronization;
- collection synchronization through existing `kardscm` flows;
- deck ingestion through `kardscm deck add`;
- manual match entry;
- one-deck-at-a-time piloting analysis grounded in local data.

It does not cover:
- new deck generation;
- replacement-card suggestions;
- mission-oriented recommendations;
- gameplay video analysis;
- hidden card property annotation.

## 2. System Boundaries

### 2.1 Canonical Data

Canonical data must remain outside the LLM and must be stored locally.

Canonical layers:
- official card catalog from GraphQL sync;
- player collection and quantities;
- imported deck lists and deck codes;
- raw match records;
- local rules knowledge base in Markdown.

### 2.2 LLM Role

The LLM consumes prepared context and generates:
- piloting advice;
- confidence-aware explanation;
- statistics-aware observations when match data exists.

The LLM must not:
- invent cards or rules;
- infer unsupported hidden properties as facts;
- act as the deck legality engine.

## 3. User Workflow

### 3.1 Rules

1. User runs `rules sync`.
2. System downloads or refreshes official rule source pages.
3. System stores source metadata and normalized Markdown files.

### 3.2 Collection

1. User runs `kardscm sync`.
2. User runs `kardscm export -f xlsx`.
3. User edits the Excel file.
4. User runs `kardscm update -i <file>`.

### 3.3 Decks

1. User exports a deck TXT from the game.
2. User runs `kardscm deck add <deck.txt>`.
3. If the name already exists and the deck code differs, the system requires `--replace`.

### 3.4 Match Entry

1. User runs `kardscm match add`.
2. System shows available decks.
3. User selects one deck.
4. User enters multiple matches in a loop.
5. System stores raw match rows only.

### 3.5 Analysis

1. User runs `kardscm deck analyze`.
2. System shows available decks.
3. User selects one deck.
4. System builds grounded analysis context.
5. LLM returns piloting advice in text form.

## 4. CLI Contract

### 4.1 Rules Commands

`rules sync`

Responsibilities:
- fetch official source pages configured for the rules knowledge base;
- compare content hashes;
- refresh only changed pages;
- regenerate normalized topic Markdown files.

### 4.2 Existing Collection Commands

Reuse existing commands:
- `kardscm sync`
- `kardscm export -f xlsx`
- `kardscm update -i <file>`

### 4.3 Deck Commands

`kardscm deck add <deck.txt>`

Behavior:
- parse deck file;
- check whether a deck with the same name already exists;
- compare `deck_code` if the name already exists;
- add, reject, or require `--replace`.

`kardscm deck add <deck.txt> --replace`

Behavior:
- delete old deck with the same name;
- delete all statistics associated with that deck;
- add the new deck.

### 4.4 Match Commands

`kardscm match add`

Interactive flow:
- list decks;
- choose one deck;
- repeat:
  - ask for `win/loss`;
  - ask for `opponent major`;
  - ask for `opponent ally`;
  - save row;
- stop on explicit user exit.

### 4.5 Analysis Commands

`kardscm deck analyze`

Interactive flow:
- list decks;
- choose one deck;
- compute deck-specific statistics;
- gather relevant rules and mechanics context;
- build LLM prompt context;
- print piloting advice.

## 5. Data Model

### 5.1 Existing Tables Reused

Reuse existing tables:
- `cards`
- `decks`
- `deck_cards`
- `metadata`

### 5.2 New Tables

#### `matches`

Purpose:
- store raw deck-specific match records.

Proposed fields:
- `match_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `deck_id INTEGER NOT NULL`
- `result TEXT NOT NULL`
- `opponent_major TEXT NOT NULL`
- `opponent_ally TEXT NOT NULL`

Constraints:
- `result` limited to `win` or `loss`
- foreign key to `decks(deck_id)` with cascade delete

No date field is required in MVP.

### 5.3 No Aggregate Tables in MVP

Do not store:
- winrate aggregates;
- matchup summary tables;
- player-wide statistics tables.

Compute aggregates on demand from `matches`.

## 6. Deck Identity Rules

### 6.1 Player-Facing Identity

Player-facing identity is the deck name.

### 6.2 Technical Equality

Technical equality for the current deck version is based on:
- same deck name;
- same `deck_code`.

### 6.3 Replace Semantics

If:
- deck name matches;
- deck code differs;

Then:
- plain `deck add` must refuse the operation and instruct the user to use `--replace`;
- `--replace` deletes the prior deck row and its match rows, then inserts the new deck.

## 7. Rules Knowledge Base

### 7.1 Source Storage

Store downloaded source page metadata:
- source URL;
- content hash;
- last synced marker.

### 7.2 Normalized Output

Generate topic-oriented Markdown files, for example:
- `deck_building_rules.md`
- `battlefield_rules.md`
- `card_abilities.md`
- `mechanic_intel.md`
- `mechanic_navy.md`
- `mechanic_resistance.md`

### 7.3 Current-State Only

The normalized rules layer should represent current game state only.
Historical evolution is intentionally excluded from MVP.

## 8. Analysis Input Assembly

For `deck analyze`, the application must build a compact grounded context containing:
- selected deck metadata;
- selected deck card list with quantities and available structured card fields;
- official card text for cards in that deck;
- relevant mechanics/rules Markdown excerpts;
- deck-specific computed statistics from raw matches.

If no matches exist:
- include an explicit marker that no match statistics are available.

## 9. Analysis Output Contract

The output must be:
- text only;
- focused on piloting advice;
- general to the deck, not matchup-specific;
- aware of deck-specific statistics when available.

The output should not include:
- replacement-card proposals in MVP;
- generated new decklists in MVP;
- unsupported claims about hidden card properties.

## 10. Grounding Rules for the LLM Layer

### 10.1 Required Guardrails

The prompt construction layer must clearly state:
- only use supplied card facts and rules;
- do not invent cards or properties;
- if a fact is unknown, say it is unknown;
- distinguish rules-derived conclusions from statistics-derived conclusions.

### 10.2 Recommended Context Segments

Recommended prompt structure:
- system constraints
- current deck summary
- card facts
- current rules/mechanics excerpts
- computed statistics
- requested explanation depth

## 11. Explanation Depth

MVP should support configurable explanation depth in analysis output.

At minimum, support a simple user preference such as:
- concise
- standard
- detailed

The exact config surface may be deferred, but the analysis layer should be designed for it now.

## 12. Error Handling

### 12.1 `deck add`

Cases:
- no such file;
- invalid deck TXT;
- duplicate same-name same-code deck;
- same-name different-code deck without `--replace`.

### 12.2 `match add`

Cases:
- no decks available;
- invalid deck selection;
- invalid `win/loss` input;
- invalid nation input if validation is enforced.

### 12.3 `deck analyze`

Cases:
- no decks available;
- selected deck has no cards;
- no rules knowledge base available;
- no match statistics available.

The last case is not fatal and should still produce a base analysis.

## 13. Validation Rules

### 13.1 Match Input

All fields are mandatory:
- `result`
- `opponent major`
- `opponent ally`

### 13.2 Nation Inputs

Prefer validation against known KARDS nations already used in the project configuration layer.

## 14. Implementation Notes

### 14.1 Reuse Existing Interaction Style

The repository already uses interactive deck selection patterns. Reuse that interaction model for:
- `match add`
- `deck analyze`

### 14.2 Keep MVP Small

Do not introduce:
- provider-specific orchestration complexity beyond config-driven selection;
- new UI surfaces;
- speculative data pipelines not needed for MVP.

### 14.3 Preserve Excel as the Only Manual Editing Surface

Any future annotation path should extend the Excel pipeline rather than bypass it.

## 15. Test Requirements

### 15.1 Command Tests

Add tests for:
- `deck add` duplicate name/same code;
- `deck add` duplicate name/different code;
- `deck add --replace` deletes prior deck and stats;
- `match add` multi-entry flow;
- `deck analyze` with no matches;
- `deck analyze` with deck-specific matches.

### 15.2 Storage Tests

Add tests for:
- `matches` table creation;
- cascade delete of match rows when a deck is replaced or deleted;
- computed winrate and match counts from raw rows.

### 15.3 Analysis Assembly Tests

Add tests for:
- no-statistics marker in assembled context;
- inclusion of rules/mechanics excerpts;
- exclusion of unsupported hidden-property claims from the context layer.

## 16. Deferred Technical Hooks

Do not implement these now, but avoid blocking them later:
- Excel columns for hidden/manual card tags;
- archival instead of destructive deck replacement;
- player-wide statistics across decks;
- matchup-aware advice;
- card replacement recommendations;
- gameplay video ingestion;
- nation-pair effectiveness analysis.
