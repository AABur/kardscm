"""Collection export helpers (XLSX, CSV, JSON) for card collections."""

from __future__ import annotations

import csv
import json
import logging

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from kardscm.config import LanguageConfig
from kardscm.constants import EXPORT_FIELD_NAMES, KNOWN_ABILITIES
from kardscm.export.styles import HEADER_ALIGNMENT, HEADER_FILL, HEADER_FONT
from kardscm.helpers import extract_locale, sanitize_text

logger = logging.getLogger(__name__)


def translate_card_for_export(card: dict, lang_config: LanguageConfig) -> dict:
    """Translate a raw DB card dict to a localized export dict.

    Extracts localized title and text via locale_key, translates
    faction/type/rarity/set via static mappings, formats attributes.

    Args:
        card: Raw card dict from database.
        lang_config: Language configuration.

    Returns:
        Dict with export field names as keys.
    """
    locale_key = lang_config.locale_key

    title_raw = card.get("title", "")
    title = extract_locale(title_raw, locale_key, default=str(title_raw), en_fallback=True)

    text_raw = card.get("text", "")
    text = extract_locale(text_raw, locale_key, en_fallback=True)

    # Translate faction
    faction_api = card.get("faction", "")
    faction = lang_config.faction_names.get(faction_api, faction_api)

    # Translate type
    type_api = card.get("type", "")
    type_name = lang_config.type_names.get(type_api, type_api)

    # Translate rarity
    rarity_api = card.get("rarity", "")
    rarity = lang_config.rarity_names.get(rarity_api, rarity_api)

    # Translate set
    set_api = card.get("set", "")
    set_name = lang_config.set_names.get(set_api, set_api)

    # Format abilities from binary columns
    abilities = ", ".join(
        lang_config.ability_names.get(a, a) for a in KNOWN_ABILITIES if card.get(f"ability_{a}", 0)
    )

    return {
        "faction": sanitize_text(faction),
        "title": sanitize_text(title),
        "type": sanitize_text(type_name),
        "rarity": sanitize_text(rarity),
        "attributes": abilities,
        "set": sanitize_text(set_name),
        "quantity": card.get("quantity", 0),
        "kredits": card.get("kredits", 0),
        "attack": card.get("attack"),
        "defense": card.get("defense"),
        "text": sanitize_text(str(text)) if text else "",
    }


def export_to_xlsx(
    cards: list[dict],
    filename: str,
    headers: list[str],
    sheet_name: str = "Collection",
) -> None:
    """Export cards to Excel format with formatting.

    Args:
        cards: List of card dictionaries (already translated for export).
        filename: Output filename.
        headers: Display headers for columns.
        sheet_name: Name of the worksheet.
    """
    logger.info("Exporting %s cards to Excel: %s", len(cards), filename)

    wb = Workbook()
    ws = wb.active
    if not ws:
        msg = "Failed to create worksheet"
        raise RuntimeError(msg)
    ws.title = sheet_name

    header_row = list(headers)
    ws.append(header_row)

    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGNMENT

    numeric_fields = {"quantity", "kredits", "attack", "defense"}
    for card in cards:
        row = [
            card.get(field) if field in numeric_fields else card.get(field, "")
            for field in EXPORT_FIELD_NAMES
        ]
        ws.append(row)

    column_widths = [15, 35, 18, 15, 12, 20, 10, 10, 8, 8, 60]
    for i, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(header_row))}{len(cards) + 1}"

    wb.save(filename)
    logger.info("Excel file created: %s (%s cards)", filename, len(cards))


def export_to_csv(
    cards: list[dict],
    filename: str,
    headers: list[str],
) -> None:
    """Export cards to CSV format.

    Uses UTF-8 with BOM for Excel compatibility on Windows.

    Args:
        cards: List of card dictionaries (already translated for export).
        filename: Output filename.
        headers: Display headers for columns.
    """
    logger.info("Exporting %s cards to CSV: %s", len(cards), filename)

    header_row = list(headers)

    with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header_row)

        for card in cards:
            row = [card.get(field, "") for field in EXPORT_FIELD_NAMES]
            writer.writerow(row)

    logger.info("CSV file created: %s (%s cards)", filename, len(cards))


def export_to_json(
    cards: list[dict],
    filename: str,
    language: str,
    language_name: str,
) -> None:
    """Export cards to JSON format with metadata.

    Args:
        cards: List of card dictionaries (already translated for export).
        filename: Output filename.
        language: Language code for metadata.
        language_name: Language name for metadata.
    """
    logger.info("Exporting %s cards to JSON: %s", len(cards), filename)

    output_data = {
        "metadata": {
            "language": language,
            "language_name": language_name,
            "total_cards": len(cards),
        },
        "cards": cards,
    }

    with open(filename, "w", encoding="utf-8") as jsonfile:
        json.dump(output_data, jsonfile, ensure_ascii=False, indent=2)

    logger.info("JSON file created: %s (%s cards)", filename, len(cards))
