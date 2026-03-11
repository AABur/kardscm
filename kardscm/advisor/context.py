"""Context assembly for LLM deck analysis prompts."""

from __future__ import annotations

import logging
from pathlib import Path

from kardscm.advisor.prompts import DEPTH_MODIFIERS, SYSTEM_PROMPT
from kardscm.config import LanguageConfig
from kardscm.export import translate_card_for_export
from kardscm.models import DeckStats

logger = logging.getLogger(__name__)


def _format_deck_meta(deck_meta: dict) -> str:
    """Format deck metadata section."""
    lines = [
        f"Name: {deck_meta.get('name', 'Unknown')}",
        f"Major Power: {deck_meta.get('major_power', 'Unknown')}",
    ]
    if deck_meta.get("ally"):
        lines.append(f"Ally: {deck_meta['ally']}")
    if deck_meta.get("hq"):
        lines.append(f"HQ: {deck_meta['hq']}")
    return "\n".join(lines)


def _format_card_list(deck_cards: list[dict], lang_config: LanguageConfig) -> str:
    """Format card list with localized data."""
    lines = []
    for card in deck_cards:
        translated = translate_card_for_export(card, lang_config)
        qty = card.get("deck_quantity", 1)
        cost = card.get("deck_cost", 0)
        name = translated.get("title", "Unknown")
        card_type = translated.get("type", "")
        faction = translated.get("faction", "")
        attack = card.get("attack", "")
        defense = card.get("defense", "")
        abilities = translated.get("attributes", "")
        text = translated.get("text", "")

        line = f"  {qty}x [{cost}K] {name} ({faction}, {card_type})"
        if attack or defense:
            line += f" [{attack}/{defense}]"
        if abilities:
            line += f" - {abilities}"
        if text:
            line += f" | {text}"
        lines.append(line)
    return "\n".join(lines)


def _format_stats(stats: DeckStats | None) -> str:
    """Format match statistics section."""
    if stats is None:
        return "No match statistics available."

    lines = [
        f"Total matches: {stats['total']}",
        f"Record: {stats['wins']}W / {stats['losses']}L ({stats['winrate']}%)",
        "",
        "Matchup breakdown:",
    ]
    for (major, ally), mu in stats["matchups"].items():
        total = mu["wins"] + mu["losses"]
        wr = round(mu["wins"] / total * 100, 1) if total > 0 else 0.0
        lines.append(f"  vs {major}/{ally}: {mu['wins']}W/{mu['losses']}L ({wr}%)")

    return "\n".join(lines)


def _load_rules(rules_dir: str) -> str:
    """Load rules markdown files if available."""
    rules_path = Path(rules_dir)
    if not rules_path.exists() or not rules_path.is_dir():
        return ""

    sections = []
    for md_file in sorted(rules_path.glob("*.md")):
        if md_file.name == "metadata.json":
            continue
        try:
            content = md_file.read_text(encoding="utf-8").strip()
            if content:
                sections.append(f"### {md_file.stem.replace('_', ' ').title()}\n{content}")
        except OSError:
            logger.warning("Failed to read rules file: %s", md_file)

    return "\n\n".join(sections)


def build_analysis_context(
    deck_meta: dict,
    deck_cards: list[dict],
    stats: DeckStats | None,
    depth: str,
    rules_dir: str = "rules/",
    lang_config: LanguageConfig | None = None,
) -> tuple[str, str]:
    """Assemble system and user prompts for deck analysis.

    Args:
        deck_meta: Deck metadata dict.
        deck_cards: List of deck card dicts with card info.
        stats: Aggregated deck stats or None.
        depth: Analysis depth (concise/standard/detailed).
        rules_dir: Path to rules markdown directory.
        lang_config: Language config for card translation.

    Returns:
        Tuple of (system_prompt, user_prompt).
    """
    from kardscm.config import get_language_config

    if lang_config is None:
        lang_config = get_language_config()

    sections = ["## Deck Information", _format_deck_meta(deck_meta)]

    sections.append("\n## Card List")
    sections.append(_format_card_list(deck_cards, lang_config))

    rules_text = _load_rules(rules_dir)
    if rules_text:
        sections.append("\n## Game Rules & Mechanics")
        sections.append(rules_text)

    sections.append("\n## Match Statistics")
    sections.append(_format_stats(stats))

    depth_instruction = DEPTH_MODIFIERS.get(depth, DEPTH_MODIFIERS["standard"])
    sections.append(f"\n## Analysis Instructions\n{depth_instruction}")

    user_prompt = "\n".join(sections)
    return SYSTEM_PROMPT, user_prompt
