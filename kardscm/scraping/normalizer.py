"""Transform raw API card nodes to CardDict format."""

from __future__ import annotations

import json
import logging
from typing import Any

from kardscm.models import CardDict

logger = logging.getLogger(__name__)


def normalize_card(node: dict[str, Any]) -> CardDict | None:
    """Transform a raw API node into a CardDict.

    Extracts top-level fields and nested json fields.
    Serializes title, text, attributes, and can_create to JSON strings.

    Args:
        node: Raw API card node.

    Returns:
        CardDict or None if required fields are missing.
    """
    card_id = node.get("cardId")
    if not card_id:
        return None

    json_data = node.get("json", {})
    if not isinstance(json_data, dict):
        return None

    title = json_data.get("title")
    if not title:
        return None

    faction = json_data.get("faction", "")
    if not faction:
        return None

    title_str = json.dumps(title, ensure_ascii=False) if isinstance(title, dict) else str(title)

    text = json_data.get("text")
    text_str = (
        json.dumps(text, ensure_ascii=False)
        if isinstance(text, dict)
        else (str(text) if text else "")
    )

    attributes = json_data.get("attributes", [])
    attributes_str = json.dumps(attributes, ensure_ascii=False) if attributes else None

    can_create = json_data.get("can_create")
    can_create_str = json.dumps(can_create, ensure_ascii=False) if can_create else None

    return CardDict(
        cardId=card_id,
        importId=str(json_data.get("import_id", json_data.get("id", ""))),
        imageUrl=node.get("imageUrl", ""),
        thumbUrl=node.get("thumbUrl", ""),
        faction=str(faction),
        type=str(json_data.get("type", "")),
        rarity=str(json_data.get("rarity", "")),
        set=str(json_data.get("set", "")),
        title=title_str,
        text=text_str,
        kredits=int(json_data.get("kredits", 0)),
        attack=json_data.get("attack"),
        defense=json_data.get("defense"),
        attributes=attributes_str or "[]",
        operationCost=json_data.get("operationCost"),
        reserved=int(json_data.get("reserved", 0)),
        image=str(json_data.get("image", node.get("image", ""))),
        can_create=can_create_str,
        exile=json_data.get("exile"),
    )
