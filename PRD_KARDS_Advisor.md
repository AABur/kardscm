# Product Requirements Document

## Local LLM Advisor for KARDS

Version: 3.0  
Last updated: March 12, 2026

## 1. Product Goal

Build a local-first KARDS advisor that helps a player analyze an existing deck, understand how to pilot it better, and later evolve into a broader assistant for deck improvement and deckbuilding.

The core product value is not "general KARDS knowledge from an LLM". The value is a local agent grounded in:
- current game rules;
- current official card catalog;
- the player's actual collection;
- the player's own deck-level match results.

## 2. Product Positioning

This product is a personal deck copilot for one player, not a hosted platform, not an enterprise analytics tool, and not a generic chatbot.

The first release should optimize for:
- low operational overhead;
- deterministic local data handling;
- a CLI-only workflow;
- no GUI, TUI, or web application;
- minimal hallucination risk.

## 3. Problem Statement

Large language models have stale KARDS knowledge. Official game knowledge is fragmented across multiple pages on `kards.com`, not maintained in one machine-friendly source, and some relevant mechanics are introduced or clarified through set pages and patch notes.

At the same time:
- the official game does not provide a proper export of the player's full collection;
- the game only exports built decks;
- there is no safe, supported source of match history or per-turn data without intrusive methods;
- some card properties are only visible in the game client and are not exposed by the current catalog feed.

Because of this, a useful KARDS advisor must be built on top of a local data pipeline, not on model memory.

## 4. Target User

The target user is a single player who:
- is willing to maintain local data manually when needed;
- is comfortable with a CLI workflow;
- prefers practical recommendations over polished UI;
- accepts a pet-project workflow if it produces useful advice.

## 5. Product Principles

1. The LLM is not the source of truth.
2. Rules and card facts must come from local verified data.
3. The CLI must remain the only product interface.
4. Excel is the primary user-friendly editing surface for collection data and future manual annotations.
5. MVP should focus on one narrow, reliable use case before expanding.

## 6. Confirmed Data Sources

### 6.1 Current Card Catalog

Source of truth:
- current `kardscm` GraphQL/API sync pipeline.

Rationale:
- already implemented;
- sufficient for current official cards and card text;
- easier to maintain than manual catalog curation.

### 6.2 Player Collection

Confirmed practical workflow:
- `kardscm sync`
- `kardscm export -f xlsx`
- user edits Excel
- `kardscm update -i <file>`

Additional supported path:
- `kardscm deck add -u` can reconcile quantities from an imported deck.

Important constraint:
- there is no better official export path for the player's full collection.

### 6.3 Player Decks

Confirmed source:
- deck TXT export from the game client.

Important constraints:
- the game exports built decks only;
- the game does not support importing a deck file back into the client;
- external deck editing has little end-user value;
- the final user-facing output should therefore be text, not an external deck file workflow.

### 6.4 Match Results

Confirmed MVP source:
- manual player input only.

Fields confirmed for MVP:
- `win/loss`
- `opponent major`
- `opponent ally`

Out of scope for MVP:
- match date;
- opponent archetype;
- opponent card list;
- turn-by-turn data;
- automatic log extraction from the game client.

### 6.5 Rules and Mechanics Knowledge

Confirmed source:
- manual collection from `kards.com`.

Confirmed workflow:
- download relevant official pages once;
- store page source metadata such as `url`, `hash`, and update state;
- on future refresh, update only pages with changed content;
- normalize content into topic-specific Markdown files.

Confirmed organizational model:
- the knowledge base should be organized primarily by mechanics, abilities, deckbuilding rules, battlefield rules, and other functional topics;
- it should not be organized only by set, because sets matter less than the mechanics they introduce or modify.

### 6.6 Hidden or Visual Card Properties

Confirmed MVP decision:
- ignore them in MVP.

Confirmed next step after MVP:
- allow manual annotation through the same Excel-based workflow.

Important architectural consequence:
- any future manual card annotation must fit into the existing `sync -> export xlsx -> edit -> update` loop.

## 7. Language Strategy

Confirmed approach:
- internal canonical data should use the official English game language where practical;
- user communication should be available in the player's language when official localized data already exists;
- no separate machine translation layer should be introduced for core game knowledge.

## 8. MVP Scope

### 8.1 MVP Use Case

Analyze one existing deck and provide piloting advice.

### 8.2 MVP User Workflow

1. `rules sync`
2. `kardscm sync`
3. `kardscm export -f xlsx`
4. user edits Excel
5. `kardscm update -i <file>`
6. `kardscm deck add <deck.txt>`
7. user records match results with `kardscm match add`
8. user requests analysis with `kardscm deck analyze`

### 8.3 MVP Commands

- `rules sync`
- `kardscm sync`
- `kardscm export -f xlsx`
- `kardscm update -i <file>`
- `kardscm deck add <deck.txt>`
- `kardscm deck add <deck.txt> --replace`
- `kardscm match add`
- `kardscm deck analyze`

### 8.4 MVP Output

Primary output:
- text only.

Behavior:
- for deck analysis, the result is piloting advice;
- if no match statistics exist yet, the system still provides a base analysis and explicitly states that no statistics are available;
- if match statistics exist, they must be incorporated into the analysis;
- advice is general deck-level guidance, not matchup-specific guidance.

### 8.5 MVP LLM Scope

The LLM is responsible for:
- producing grounded deck piloting advice;
- using deck composition, card text, card properties, rules knowledge, and deck-specific statistics;
- adapting explanation depth based on player preference.

The LLM is not responsible for:
- inventing cards, mechanics, or rules;
- acting as the canonical rules engine;
- generating new decks in MVP;
- proposing replacement cards in MVP.

## 9. Deck Lifecycle Rules

Confirmed MVP behavior for `deck add`:
- use deck name for player-facing identity;
- use `deck_code` as the technical representation of the current deck list;
- if deck name is new, add the deck;
- if deck name matches and `deck_code` matches, report that the deck already exists;
- if deck name matches but `deck_code` differs, require `--replace`.

Confirmed MVP behavior for `--replace`:
- delete the old deck;
- add the new deck;
- delete all accumulated statistics for the replaced deck.

Reasoning:
- for MVP, once the deck list changes, previous results are treated as no longer valid for that deck.

## 10. Match Data Rules

Confirmed MVP behavior for `match add`:
- player selects the deck interactively from a list;
- the command supports entering multiple match results in one session;
- each match requires:
  - `win/loss`
  - `opponent major`
  - `opponent ally`
- match aggregates are computed on demand from raw records.

Confirmed MVP analytical scope:
- analysis uses statistics for the selected deck only;
- cross-deck player-wide matchup statistics are not part of MVP.

## 11. Knowledge Base Requirements

The local rules knowledge base must support:
- deckbuilding rules;
- battlefield rules;
- card ability definitions;
- mechanics introduced or modified by expansions or patches;
- synergy descriptions relevant to actual card play.

Confirmed MVP representation:
- Markdown files.

Confirmed time model:
- only current state matters;
- historical mechanics evolution is not kept as a first-class requirement in MVP.

## 12. Non-Functional Requirements

- local-first operation after synchronization;
- CLI-only workflow;
- low maintenance burden suitable for a personal project;
- ability to switch LLM provider through configuration;
- minimal hallucination risk through strict grounding;
- explicit separation between canonical data and model-generated advice.

## 13. LLM Provider Requirements

Confirmed MVP provider model:
- configuration-based provider selection.

Confirmed MVP provider list:
- OpenAI
- Anthropic
- Google

## 14. Risks and Design Concerns

### 14.1 Rules Drift

Risk:
- manual rules sync can become stale.

Mitigation:
- keep downloaded source pages with hash tracking;
- keep normalized mechanic-level Markdown files;
- expose a dedicated `rules sync` command.

### 14.2 Hidden Card Properties

Risk:
- some useful properties are not available from the catalog feed.

Mitigation:
- ignore in MVP;
- extend the Excel editing flow later to support manual annotation.

### 14.3 Replaced Deck Statistics

Risk:
- deleting statistics on `--replace` is simple but loses potentially useful historical learning.

MVP decision:
- accept deletion for simplicity.

Future concern to preserve:
- consider archival or versioned snapshots later without changing the user-facing deck-name workflow.

### 14.4 Hallucinations

Risk:
- LLM may invent cards, card abilities, or game rules.

Mitigation:
- never let the model operate without grounded local context;
- keep verified rules and card data outside the LLM;
- treat the LLM as an interpretation layer, not a rules authority.

### 14.5 Excel Pipeline Expansion

Risk:
- the current Excel pipeline is quantity-oriented;
- future manual annotation may require additional editable columns and validation.

Future concern to preserve:
- design collection export/update so it can later carry hidden abilities and manual card tags without breaking the user workflow.

## 15. Deferred Scope

The following items were explicitly discussed and postponed.

### 15.1 Post-MVP

- replacement-card recommendations for existing decks;
- deeper deck analysis beyond piloting advice;
- manual annotation of hidden or visual-only card properties through Excel;
- richer rules/mechanics normalization beyond simple Markdown storage;
- configurable explanation depth for different player experience levels;
- use of mechanics-focused knowledge files assembled from multiple official pages.

### 15.2 Post-MVP+

- automatic or assisted match understanding from video or screencast analysis;
- using VLM/LLM analysis of recorded matches to recover move sequences and richer signals;
- player-wide statistics across all decks;
- matchup-aware advice based on broader accumulated data;
- support for suggestions influenced by current metagame patterns.

### 15.3 Post-Post-MVP

- analysis of the effectiveness of specific `major + ally` nation pairings in the current metagame;
- analysis of the effectiveness of those nation pairings specifically in the hands of this player;
- more strategic personalization beyond deck-level advice.

## 16. Explicit Non-Goals for MVP

- no GUI;
- no TUI;
- no web app;
- no fully automatic rules ingestion;
- no full deck generation;
- no mission deckbuilder;
- no turn-by-turn gameplay reconstruction;
- no historical mechanics archive;
- no enterprise-grade automation.

## 17. MVP Success Criteria

MVP is successful when:
- the player can keep rules, collection, and decks updated locally with the agreed CLI workflow;
- the player can batch-enter match results for a selected deck;
- the player can run analysis for one deck at a time;
- the system always produces grounded piloting advice;
- the system explicitly reports when no statistics are available;
- the analysis uses deck-specific statistics when they do exist;
- no GUI or extra application layer is required.
