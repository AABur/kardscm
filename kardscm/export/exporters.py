"""Export helpers for card collections."""

from __future__ import annotations

import csv
import json
import logging

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook as WorkbookType

from kardscm.constants import DECK_COLUMN_WIDTHS, EXPORT_FIELD_NAMES
from kardscm.helpers import parse_int

logger = logging.getLogger(__name__)


def export_to_xlsx(
    cards: list[dict[str, str]],
    filename: str,
    headers: list[str],
    sheet_name: str = "Collection",
) -> None:
    """Export cards to Excel format with formatting.

    Args:
        cards: List of card dictionaries.
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

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    numeric_fields = {"Quantity", "Credits", "Attack", "Defense"}
    for card in cards:
        row = [
            parse_int(card.get(field, "")) if field in numeric_fields else card.get(field, "")
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
    cards: list[dict[str, str]],
    filename: str,
    headers: list[str],
) -> None:
    """Export cards to CSV format.

    Uses UTF-8 with BOM for Excel compatibility on Windows.

    Args:
        cards: List of card dictionaries.
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
    cards: list[dict[str, str]],
    filename: str,
    language: str,
    language_name: str,
) -> None:
    """Export cards to JSON format with metadata.

    Args:
        cards: List of card dictionaries.
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


def add_deck_sheet(
    wb: WorkbookType,
    deck_meta: dict,
    deck_cards: list[dict],
    deck_headers: list[str],
    metadata_labels: list[str],
    deck_nation_to_db: dict[str, str],
    nation_display_names: dict[str, str],
) -> None:
    """Add a deck sheet to an existing workbook.

    Args:
        wb: openpyxl Workbook instance.
        deck_meta: Deck metadata dict.
        deck_cards: List of card dicts with deck_quantity and deck_cost.
        deck_headers: Headers for deck card table.
        metadata_labels: Labels for deck metadata section.
        deck_nation_to_db: Mapping from deck nation keys to DB names.
        nation_display_names: Display names for nation sections.
    """
    sheet_name = deck_meta["name"][:31]  # Excel sheet name limit
    ws = wb.create_sheet(title=sheet_name)

    bold_font = Font(bold=True)

    major = deck_meta.get("major_power", "")
    ally = deck_meta.get("ally", "")
    meta_values = [
        deck_meta.get("name", ""),
        deck_nation_to_db.get(major, major),
        deck_nation_to_db.get(ally, ally),
        deck_meta.get("hq", ""),
        deck_meta.get("deck_code", ""),
    ]
    for row_idx, (label, value) in enumerate(zip(metadata_labels, meta_values), 1):
        ws.cell(row=row_idx, column=1, value=label).font = bold_font
        ws.cell(row=row_idx, column=2, value=value or "")

    header_row = 7
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for col_idx, header in enumerate(deck_headers, 1):
        cell = ws.cell(row=header_row, column=col_idx, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    current_row = header_row + 1
    cards_by_nation: dict[str, list[dict]] = {}
    for card in deck_cards:
        nation = card.get("nation", "")
        cards_by_nation.setdefault(nation, []).append(card)

    for nation, nation_cards in cards_by_nation.items():
        nation_lower = nation.lower()
        display_name = nation_display_names.get(nation_lower, nation)
        ws.cell(row=current_row, column=1, value=display_name).font = bold_font
        current_row += 1

        for card in nation_cards:
            ws.cell(row=current_row, column=1, value=card.get("name", ""))
            ws.cell(row=current_row, column=2, value=card.get("type", ""))
            ws.cell(row=current_row, column=3, value=card.get("deck_quantity"))
            ws.cell(row=current_row, column=4, value=card.get("deck_cost"))
            ws.cell(row=current_row, column=5, value=card.get("attack"))
            ws.cell(row=current_row, column=6, value=card.get("defense"))
            current_row += 1

    for col_idx, width in enumerate(DECK_COLUMN_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    logger.info("Deck sheet '%s' added (%d cards)", sheet_name, len(deck_cards))


def export_deck_to_json(
    deck_meta: dict,
    deck_cards: list[dict],
    filename: str,
) -> None:
    """Export a deck to JSON format.

    Args:
        deck_meta: Deck metadata dict.
        deck_cards: List of card dicts with deck_quantity and deck_cost.
        filename: Output file path.
    """
    output = {
        "deck": {
            "name": deck_meta.get("name", ""),
            "major_power": deck_meta.get("major_power", ""),
            "ally": deck_meta.get("ally"),
            "hq": deck_meta.get("hq"),
        },
        "cards": [
            {
                "nation": card.get("nation", ""),
                "name": card.get("name", ""),
                "type": card.get("type", ""),
                "rarity": card.get("rarity", ""),
                "set": card.get("set_name", ""),
                "credits": card.get("credits"),
                "attack": card.get("attack"),
                "defense": card.get("defense"),
                "description": card.get("description", ""),
                "deck_quantity": card.get("deck_quantity"),
                "deck_cost": card.get("deck_cost"),
            }
            for card in deck_cards
        ],
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info("Deck JSON exported: %s (%d cards)", filename, len(deck_cards))
