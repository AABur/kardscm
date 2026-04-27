"""Translation helpers for the webUI templates."""

from __future__ import annotations

from kardscm.config import LanguageConfig
from kardscm.export.exporters import translate_card_for_export


def to_view(card: dict, lang_config: LanguageConfig) -> dict:
    """Translate a raw DB card into a dict for Jinja templates.

    Reuses translate_card_for_export and adds the fields the webUI needs
    that are not part of the xlsx export (cardId, image URLs, operationCost).
    """
    base = translate_card_for_export(card, lang_config)
    base["cardId"] = card.get("cardId", "")
    base["operationCost"] = card.get("operationCost")
    base["imageUrl"] = card.get("imageUrl") or ""
    base["thumbUrl"] = card.get("thumbUrl") or ""
    return base
