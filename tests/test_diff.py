"""Tests for the sync diff engine."""

from __future__ import annotations

import json

from kardscm.diff import (
    compute_diff,
    format_console_report,
    format_markdown_report,
    is_empty,
)
from kardscm.locales import LANGUAGE_EN, LANGUAGE_RU


def test_empty_when_old_equals_new(make_card):
    card = make_card()
    report = compute_diff([dict(card)], [card], locale_key="en-EN")
    assert is_empty(report)
    assert report == {
        "new": [],
        "changed": [],
        "reserved_in": [],
        "reserved_out": [],
        "removed": [],
    }


def test_numeric_field_changes_flagged(make_card):
    old = make_card(kredits=3, attack=4, defense=5, operationCost=2)
    new = make_card(kredits=4, attack=4, defense=2, operationCost=3)
    report = compute_diff([dict(old)], [new], locale_key="en-EN")

    assert len(report["changed"]) == 1
    fields = {c["field"]: c for c in report["changed"][0]["changes"]}
    assert fields["kredits"]["old"] == 3
    assert fields["kredits"]["new"] == 4
    assert fields["defense"]["old"] == 5
    assert fields["defense"]["new"] == 2
    assert fields["operationCost"]["old"] == 2
    assert fields["operationCost"]["new"] == 3
    assert "attack" not in fields


def test_attributes_compared_as_set(make_card):
    old = make_card(ability_blitz=1, ability_fury=1)
    new = make_card(ability_blitz=1, ability_fury=1)
    report = compute_diff([dict(old)], [new], locale_key="en-EN")
    assert is_empty(report)


def test_attributes_change_flagged(make_card):
    old = make_card(ability_mobilize=1, ability_heavyArmor2=1)
    new = make_card(ability_shock=1, ability_blitz=1, ability_heavyArmor2=1)
    report = compute_diff([dict(old)], [new], locale_key="en-EN")

    assert len(report["changed"]) == 1
    changes = report["changed"][0]["changes"]
    assert len(changes) == 1
    assert changes[0]["field"] == "attributes"
    assert sorted(changes[0]["old"]) == ["heavyArmor2", "mobilize"]
    assert sorted(changes[0]["new"]) == ["blitz", "heavyArmor2", "shock"]


def test_text_change_flagged_for_current_locale_only(make_card):
    old_text = json.dumps({"en-EN": "old text", "ru-RU": "старый текст"})
    new_text = json.dumps({"en-EN": "new text", "ru-RU": "старый текст"})
    old = make_card(text=old_text)
    new = make_card(text=new_text)

    en_report = compute_diff([dict(old)], [new], locale_key="en-EN")
    assert len(en_report["changed"]) == 1
    assert en_report["changed"][0]["changes"][0]["field"] == "text"
    assert en_report["changed"][0]["changes"][0]["old"] == "old text"
    assert en_report["changed"][0]["changes"][0]["new"] == "new text"

    ru_report = compute_diff([dict(old)], [new], locale_key="ru-RU")
    assert is_empty(ru_report)


def test_reserved_in_and_out_categorised(make_card):
    in_old = make_card(cardId="A", reserved=0)
    in_new = make_card(cardId="A", reserved=1)
    out_old = make_card(cardId="B", reserved=1)
    out_new = make_card(cardId="B", reserved=0)

    report = compute_diff(
        [dict(in_old), dict(out_old)],
        [in_new, out_new],
        locale_key="en-EN",
    )
    assert [c["cardId"] for c in report["reserved_in"]] == ["A"]
    assert [c["cardId"] for c in report["reserved_out"]] == ["B"]
    assert report["changed"] == []


def test_new_cards_bucket(make_card):
    old = make_card(cardId="A")
    new_a = make_card(cardId="A")
    new_b = make_card(cardId="B", title=json.dumps({"en-EN": "Bravo"}))

    report = compute_diff([dict(old)], [new_a, new_b], locale_key="en-EN")
    assert [c["cardId"] for c in report["new"]] == ["B"]
    assert report["removed"] == []
    assert report["changed"] == []


def test_removed_cards_bucket(make_card):
    old_a = make_card(cardId="A")
    old_b = make_card(cardId="B")
    new_a = make_card(cardId="A")

    report = compute_diff([dict(old_a), dict(old_b)], [new_a], locale_key="en-EN")
    assert [r["cardId"] for r in report["removed"]] == ["B"]
    assert report["new"] == []


def test_change_and_reserve_can_coexist(make_card):
    """A card both moving to reserve and getting nerfed should appear in
    both `reserved_in` and `changed`."""
    old = make_card(cardId="X", reserved=0, kredits=4)
    new = make_card(cardId="X", reserved=1, kredits=5)
    report = compute_diff([dict(old)], [new], locale_key="en-EN")

    assert [c["cardId"] for c in report["reserved_in"]] == ["X"]
    assert len(report["changed"]) == 1
    assert {c["field"] for c in report["changed"][0]["changes"]} == {"kredits"}


def test_silently_overwritten_fields_not_flagged(make_card):
    old = make_card(
        title=json.dumps({"en-EN": "Old name"}),
        imageUrl="old-url",
        rarity="Standard",
    )
    new = make_card(
        title=json.dumps({"en-EN": "New name"}),
        imageUrl="new-url",
        rarity="Elite",
    )
    report = compute_diff([dict(old)], [new], locale_key="en-EN")
    assert is_empty(report)


def test_format_console_report_skips_empty_sections(make_card):
    new_card = make_card(cardId="B", title=json.dumps({"en-EN": "Bravo"}))
    report = compute_diff([], [new_card], locale_key="en-EN")
    out = format_console_report(report, LANGUAGE_EN)
    assert "New cards" in out
    assert "Bravo" in out
    assert "Changed characteristics" not in out
    assert "Removed cards" not in out


def test_format_console_report_uses_localized_headers(make_card):
    new_card = make_card(cardId="B", title=json.dumps({"ru-RU": "Браво"}))
    report = compute_diff([], [new_card], locale_key="ru-RU")
    out = format_console_report(report, LANGUAGE_RU)
    assert "Новые карты" in out
    assert "Браво" in out


def test_format_markdown_report_includes_timestamp_and_diff(make_card):
    old = make_card(cardId="X", kredits=3)
    new = make_card(cardId="X", kredits=4, title=json.dumps({"en-EN": "Xenon"}))
    report = compute_diff([dict(old)], [new], locale_key="en-EN")

    md = format_markdown_report(report, LANGUAGE_EN, "2026-04-25T14-32-11Z")
    assert "# Sync diff — 2026-04-25T14-32-11Z" in md
    assert "## Changed characteristics" in md
    assert "**Xenon**" in md
    assert "kredits: `3` → `4`" in md


def test_format_console_report_renders_text_change(make_card):
    old_text = json.dumps({"en-EN": "OLD"})
    new_text = json.dumps({"en-EN": "NEW"})
    old = make_card(cardId="X", text=old_text)
    new = make_card(cardId="X", text=new_text, title=json.dumps({"en-EN": "Xenon"}))

    report = compute_diff([dict(old)], [new], locale_key="en-EN")
    out = format_console_report(report, LANGUAGE_EN)
    assert "old: OLD" in out
    assert "new: NEW" in out


def test_format_console_report_renders_all_sections(make_card):
    new_card = make_card(cardId="A", title=json.dumps({"en-EN": "Alpha"}))
    changed_old = make_card(cardId="C", kredits=2)
    changed_new = make_card(cardId="C", kredits=3, title=json.dumps({"en-EN": "Charlie"}))
    moved_in_old = make_card(cardId="I", reserved=0)
    moved_in_new = make_card(cardId="I", reserved=1, title=json.dumps({"en-EN": "India"}))
    moved_out_old = make_card(cardId="O", reserved=1)
    moved_out_new = make_card(cardId="O", reserved=0, title=json.dumps({"en-EN": "Oscar"}))
    removed_old = make_card(cardId="X", title=json.dumps({"en-EN": "Xray"}))

    report = compute_diff(
        [dict(changed_old), dict(moved_in_old), dict(moved_out_old), dict(removed_old)],
        [new_card, changed_new, moved_in_new, moved_out_new],
        locale_key="en-EN",
    )
    out = format_console_report(report, LANGUAGE_EN)

    assert "New cards" in out
    assert "Alpha" in out
    assert "Changed characteristics" in out
    assert "kredits: 2 → 3" in out
    assert "Moved to reserve" in out
    assert "India" in out
    assert "Returned from reserve" in out
    assert "Oscar" in out
    assert "Removed cards" in out
    assert "Xray" in out


def test_format_markdown_report_renders_all_sections(make_card):
    new_card = make_card(cardId="A", title=json.dumps({"en-EN": "Alpha"}))
    moved_in_old = make_card(cardId="I", reserved=0)
    moved_in_new = make_card(cardId="I", reserved=1, title=json.dumps({"en-EN": "India"}))
    moved_out_old = make_card(cardId="O", reserved=1)
    moved_out_new = make_card(cardId="O", reserved=0, title=json.dumps({"en-EN": "Oscar"}))
    removed_old = make_card(cardId="X", title=json.dumps({"en-EN": "Xray"}))

    report = compute_diff(
        [dict(moved_in_old), dict(moved_out_old), dict(removed_old)],
        [new_card, moved_in_new, moved_out_new],
        locale_key="en-EN",
    )
    md = format_markdown_report(report, LANGUAGE_EN, "T")

    assert "## New cards" in md
    assert "## Moved to reserve" in md
    assert "## Returned from reserve" in md
    assert "## Removed cards" in md
    assert "- Alpha" in md
    assert "- India" in md
    assert "- Oscar" in md
    assert "- Xray" in md


def test_format_value_attributes_translated_when_known(make_card):
    """Known ability codes get translated via LanguageConfig.ability_names."""
    old = make_card(cardId="X")
    new = make_card(cardId="X", ability_blitz=1, title=json.dumps({"en-EN": "Xenon"}))
    report = compute_diff([dict(old)], [new], locale_key="en-EN")
    out = format_console_report(report, LANGUAGE_EN)
    assert "Blitz" in out


def test_compute_diff_detects_text_change(make_card):
    """Verify text-change detection still works after attributes refactor."""
    old = make_card(text='{"en-EN": "old"}')
    new = make_card(ability_blitz=1, text='{"en-EN": "new"}')

    report = compute_diff([dict(old)], [new], locale_key="en-EN")
    fields = {c["field"] for c in report["changed"][0]["changes"]}
    assert "attributes" in fields
    assert "text" in fields
