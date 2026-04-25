"""Compute and render the diff between the DB cards and a fresh API pull.

This module is pure logic — no IO, no DB, no prompts. It is consumed by
`kardscm.commands.sync_collection` to render the four-section diff that
the user approves before any DB writes happen.

Compared fields per `cardId`:
- `kredits`, `attack`, `defense`, `operationCost`: numeric equality
- `attributes`: JSON array compared as a set (order-independent)
- `text`: extract value at `LanguageConfig.locale_key`, compare strings
- `reserved`: routed into `reserved_in` / `reserved_out` categories,
  not the generic `changed` list

Other fields are upserted silently and never surfaced.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from kardscm.config import LanguageConfig
from kardscm.models import (
    CardChange,
    CardDict,
    DiffReport,
    FieldChange,
)

NUMERIC_FIELDS = ("kredits", "attack", "defense", "operationCost")


def compute_diff(
    old_cards: Iterable[dict],
    new_cards: Iterable[CardDict],
    locale_key: str,
) -> DiffReport:
    """Compare DB rows against fresh API cards and bucket the differences.

    Args:
        old_cards: Rows from `fetch_cards(conn)` — raw DB dicts.
        new_cards: CardDict items from `scrape_cards()`.
        locale_key: Active locale, e.g. "en-EN" or "ru-RU".

    Returns:
        DiffReport with five lists: new, changed, reserved_in, reserved_out,
        removed. Each list is empty if the corresponding category is empty.
    """
    old_by_id = {row["cardId"]: row for row in old_cards if row.get("cardId")}
    new_by_id = {card["cardId"]: card for card in new_cards if card.get("cardId")}

    report: DiffReport = {
        "new": [],
        "changed": [],
        "reserved_in": [],
        "reserved_out": [],
        "removed": [],
    }

    for card_id, new_card in new_by_id.items():
        old_row = old_by_id.get(card_id)
        if old_row is None:
            report["new"].append(new_card)
            continue

        old_reserved = int(old_row.get("reserved") or 0)
        new_reserved = int(new_card.get("reserved") or 0)
        if old_reserved != new_reserved:
            if new_reserved and not old_reserved:
                report["reserved_in"].append(new_card)
            elif old_reserved and not new_reserved:
                report["reserved_out"].append(new_card)

        changes = _card_changes(old_row, new_card, locale_key)
        if changes:
            report["changed"].append({"card": new_card, "changes": changes})

    for card_id, old_row in old_by_id.items():
        if card_id not in new_by_id:
            report["removed"].append(old_row)

    return report


def is_empty(report: DiffReport) -> bool:
    """True when every category in the report is empty."""
    return not (
        report["new"]
        or report["changed"]
        or report["reserved_in"]
        or report["reserved_out"]
        or report["removed"]
    )


def _card_changes(old: dict, new: CardDict, locale_key: str) -> list[FieldChange]:
    """Compute per-field changes between an old DB row and a new API card."""
    changes: list[FieldChange] = []

    for field in NUMERIC_FIELDS:
        old_val = old.get(field)
        new_val = new.get(field)
        if old_val != new_val:
            changes.append({"field": field, "old": old_val, "new": new_val})

    old_attrs = _attributes_set(old.get("attributes"))
    new_attrs = _attributes_set(new.get("attributes"))
    if old_attrs != new_attrs:
        changes.append(
            {
                "field": "attributes",
                "old": sorted(old_attrs),
                "new": sorted(new_attrs),
            }
        )

    old_text = _text_for_locale(old.get("text"), locale_key)
    new_text = _text_for_locale(new.get("text"), locale_key)
    if old_text != new_text:
        changes.append({"field": "text", "old": old_text, "new": new_text})

    return changes


def _parse_json(value: object) -> object:
    """Parse a JSON string defensively. Returns None on any failure."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def _attributes_set(value: object) -> frozenset[str]:
    parsed = _parse_json(value)
    if not isinstance(parsed, list):
        return frozenset()
    return frozenset(str(item) for item in parsed)


def _text_for_locale(value: object, locale_key: str) -> str:
    parsed = _parse_json(value)
    if isinstance(parsed, dict):
        return str(parsed.get(locale_key, "") or "")
    return ""


def _faction_label(faction: str, lang_config: LanguageConfig) -> str:
    return lang_config.faction_names.get(faction, faction)


def _title_for_locale(value: object, locale_key: str) -> str:
    """Best-effort localized title for display. Falls back to en-EN, then raw."""
    parsed = _parse_json(value)
    if isinstance(parsed, dict):
        return str(parsed.get(locale_key) or parsed.get("en-EN") or "")
    return str(value or "")


def _group_by_faction(cards: list[CardDict] | list[dict]) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for card in cards:
        faction = card.get("faction", "") or ""
        grouped.setdefault(faction, []).append(card)
    return grouped


def _format_value(field: str, value: object, lang_config: LanguageConfig) -> str:
    """Render an old/new value for display in console + Markdown reports."""
    if field == "attributes":
        if isinstance(value, list):
            translated = [lang_config.ability_names.get(str(v), str(v)) for v in value]
            return "[" + ", ".join(translated) + "]"
        return str(value)
    if value is None:
        return "—"
    return str(value)


def format_console_report(report: DiffReport, lang_config: LanguageConfig) -> str:
    """Render a human-readable report for terminal output. Empty sections skipped."""
    locale_key = lang_config.locale_key
    headers = lang_config.diff_headers
    out: list[str] = []

    def emit_card_list(cards: list[CardDict] | list[dict]) -> None:
        for faction, items in sorted(_group_by_faction(cards).items()):
            out.append(f"  {_faction_label(faction, lang_config)}:")
            for card in sorted(items, key=lambda c: _title_for_locale(c.get("title"), locale_key)):
                out.append(f"    - {_title_for_locale(card.get('title'), locale_key)}")

    if report["new"]:
        out.append(f"=== {headers.get('new', 'New cards')} ===")
        emit_card_list(report["new"])
        out.append("")

    if report["changed"]:
        out.append(f"=== {headers.get('changed', 'Changed characteristics')} ===")
        grouped: dict[str, list[CardChange]] = {}
        for change in report["changed"]:
            faction = change["card"].get("faction", "") or ""
            grouped.setdefault(faction, []).append(change)
        for faction, items in sorted(grouped.items()):
            out.append(f"  {_faction_label(faction, lang_config)}:")
            for change in sorted(
                items,
                key=lambda c: _title_for_locale(c["card"].get("title"), locale_key),
            ):
                out.append(f"    - {_title_for_locale(change['card'].get('title'), locale_key)}")
                for field_change in change["changes"]:
                    field = field_change["field"]
                    old_val = _format_value(field, field_change["old"], lang_config)
                    new_val = _format_value(field, field_change["new"], lang_config)
                    if field == "text":
                        out.append("        text:")
                        out.append(f"          old: {old_val}")
                        out.append(f"          new: {new_val}")
                    else:
                        out.append(f"        {field}: {old_val} → {new_val}")
        out.append("")

    if report["reserved_in"]:
        out.append(f"=== {headers.get('reserved_in', 'Moved to reserve')} ===")
        emit_card_list(report["reserved_in"])
        out.append("")

    if report["reserved_out"]:
        out.append(f"=== {headers.get('reserved_out', 'Returned from reserve')} ===")
        emit_card_list(report["reserved_out"])
        out.append("")

    if report["removed"]:
        out.append(f"=== {headers.get('removed', 'Removed cards')} ===")
        emit_card_list(report["removed"])
        out.append("")

    return "\n".join(out).rstrip() + "\n" if out else ""


def format_markdown_report(
    report: DiffReport,
    lang_config: LanguageConfig,
    timestamp: str,
) -> str:
    """Render the full diff report as Markdown for `--diff-report` output."""
    locale_key = lang_config.locale_key
    headers = lang_config.diff_headers
    out: list[str] = [f"# {headers.get('title', 'Sync diff')} — {timestamp}", ""]

    def emit_card_list(cards: list[CardDict] | list[dict]) -> None:
        for faction, items in sorted(_group_by_faction(cards).items()):
            out.append(f"### {_faction_label(faction, lang_config)}")
            out.append("")
            for card in sorted(items, key=lambda c: _title_for_locale(c.get("title"), locale_key)):
                out.append(f"- {_title_for_locale(card.get('title'), locale_key)}")
            out.append("")

    if report["new"]:
        out.append(f"## {headers.get('new', 'New cards')}")
        out.append("")
        emit_card_list(report["new"])

    if report["changed"]:
        out.append(f"## {headers.get('changed', 'Changed characteristics')}")
        out.append("")
        grouped: dict[str, list[CardChange]] = {}
        for change in report["changed"]:
            faction = change["card"].get("faction", "") or ""
            grouped.setdefault(faction, []).append(change)
        for faction, items in sorted(grouped.items()):
            out.append(f"### {_faction_label(faction, lang_config)}")
            out.append("")
            for change in sorted(
                items,
                key=lambda c: _title_for_locale(c["card"].get("title"), locale_key),
            ):
                title = _title_for_locale(change["card"].get("title"), locale_key)
                out.append(f"- **{title}**")
                for field_change in change["changes"]:
                    field = field_change["field"]
                    old_val = _format_value(field, field_change["old"], lang_config)
                    new_val = _format_value(field, field_change["new"], lang_config)
                    if field == "text":
                        out.append("  - text:")
                        out.append(f"    - old: `{old_val}`")
                        out.append(f"    - new: `{new_val}`")
                    else:
                        out.append(f"  - {field}: `{old_val}` → `{new_val}`")
            out.append("")

    if report["reserved_in"]:
        out.append(f"## {headers.get('reserved_in', 'Moved to reserve')}")
        out.append("")
        emit_card_list(report["reserved_in"])

    if report["reserved_out"]:
        out.append(f"## {headers.get('reserved_out', 'Returned from reserve')}")
        out.append("")
        emit_card_list(report["reserved_out"])

    if report["removed"]:
        out.append(f"## {headers.get('removed', 'Removed cards')}")
        out.append("")
        emit_card_list(report["removed"])

    return "\n".join(out).rstrip() + "\n"
