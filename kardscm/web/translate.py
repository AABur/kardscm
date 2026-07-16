"""Translation helpers for the webUI templates."""

from __future__ import annotations

from kardscm.config import LanguageConfig
from kardscm.export import translate_card_for_export


def to_view(card: dict, lang_config: LanguageConfig) -> dict:
    """Translate a raw DB card into a dict for Jinja templates.

    Reuses translate_card_for_export (which already provides all 12
    web-table fields, including extra_abilities and operationCost) and
    adds the web-only fields the templates need (cardId, image URLs,
    raw rarity).
    """
    base = translate_card_for_export(card, lang_config)
    base["cardId"] = card.get("cardId", "")
    base["imageUrl"] = card.get("imageUrl") or ""
    base["thumbUrl"] = card.get("thumbUrl") or ""
    base["rarity_raw"] = card.get("rarity", "")
    return base
