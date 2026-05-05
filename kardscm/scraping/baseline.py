"""API contract baseline + drift detection.

Captures the observed shape of GraphQL responses (keys, enum values, card
count) and compares against a committed baseline to surface API changes
that would otherwise be silently dropped during normalization.

GraphQL introspection on api.kards.com is disabled, so the snapshot is
purely data-driven — derived from the raw card nodes returned by
``fetch_all_cards``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, cast

if TYPE_CHECKING:
    from kardscm.locales import LanguageConfig

# Enum-like fields whose distinct values we track for drift detection.
_TRACKED_ENUM_FIELDS: tuple[str, ...] = ("faction", "type", "rarity", "set")
# Threshold for INFO-level card-count delta.
_CARD_COUNT_DELTA_PCT_THRESHOLD = 5.0

BASELINE_PATH: Path = Path(__file__).parent.parent / "data" / "api_baseline.json"


class Snapshot(TypedDict):
    """Observed shape of a GraphQL `cards` response."""

    captured_at: str
    card_count: int
    node_keys: list[str]
    json_keys: dict[str, int]
    enum_values: dict[str, list[str]]


@dataclass
class DriftReport:
    """Categorised differences between baseline and observed snapshot."""

    added_node_keys: list[str] = field(default_factory=list)
    removed_node_keys: list[str] = field(default_factory=list)
    added_json_keys: list[str] = field(default_factory=list)
    removed_json_keys: list[str] = field(default_factory=list)
    added_enum_values: dict[str, list[str]] = field(default_factory=dict)
    removed_enum_values: dict[str, list[str]] = field(default_factory=dict)
    card_count_baseline: int = 0
    card_count_observed: int = 0
    card_count_delta_pct: float | None = None

    def has_changes(self) -> bool:
        return bool(
            self.added_node_keys
            or self.removed_node_keys
            or self.added_json_keys
            or self.removed_json_keys
            or any(self.added_enum_values.values())
            or any(self.removed_enum_values.values())
            or self.card_count_delta_pct is not None
        )

    def count(self) -> int:
        return (
            len(self.added_node_keys)
            + len(self.removed_node_keys)
            + len(self.added_json_keys)
            + len(self.removed_json_keys)
            + sum(len(v) for v in self.added_enum_values.values())
            + sum(len(v) for v in self.removed_enum_values.values())
            + (1 if self.card_count_delta_pct is not None else 0)
        )


def build_snapshot(raw_nodes: list[dict]) -> Snapshot:
    """Derive a Snapshot from raw API card nodes (the result of fetch_all_cards)."""
    node_key_set: set[str] = set()
    json_key_counts: dict[str, int] = {}
    enum_sets: dict[str, set[str]] = {field: set() for field in _TRACKED_ENUM_FIELDS}
    enum_sets["attributes"] = set()

    for node in raw_nodes:
        node_key_set.update(node.keys())
        node_json = node.get("json")
        if not isinstance(node_json, dict):
            continue
        for key in node_json:
            json_key_counts[key] = json_key_counts.get(key, 0) + 1
        for field_name in _TRACKED_ENUM_FIELDS:
            value = node_json.get(field_name)
            if isinstance(value, str) and value:
                enum_sets[field_name].add(value)
        attrs = node_json.get("attributes")
        if isinstance(attrs, list):
            for a in attrs:
                if isinstance(a, str) and a:
                    enum_sets["attributes"].add(a)

    return {
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "card_count": len(raw_nodes),
        "node_keys": sorted(node_key_set),
        "json_keys": dict(sorted(json_key_counts.items())),
        "enum_values": {k: sorted(v) for k, v in enum_sets.items()},
    }


def diff_snapshots(baseline: Snapshot, observed: Snapshot) -> DriftReport:
    """Categorise differences between two snapshots."""
    report = DriftReport(
        card_count_baseline=baseline.get("card_count", 0),
        card_count_observed=observed.get("card_count", 0),
    )

    base_node = set(baseline.get("node_keys", []))
    obs_node = set(observed.get("node_keys", []))
    report.added_node_keys = sorted(obs_node - base_node)
    report.removed_node_keys = sorted(base_node - obs_node)

    base_json = set(baseline.get("json_keys", {}).keys())
    obs_json = set(observed.get("json_keys", {}).keys())
    report.added_json_keys = sorted(obs_json - base_json)
    report.removed_json_keys = sorted(base_json - obs_json)

    base_enums = baseline.get("enum_values", {})
    obs_enums = observed.get("enum_values", {})
    all_enum_fields = set(base_enums) | set(obs_enums)
    for field_name in sorted(all_enum_fields):
        base_vals = set(base_enums.get(field_name, []))
        obs_vals = set(obs_enums.get(field_name, []))
        added = sorted(obs_vals - base_vals)
        removed = sorted(base_vals - obs_vals)
        if added:
            report.added_enum_values[field_name] = added
        if removed:
            report.removed_enum_values[field_name] = removed

    if report.card_count_baseline > 0:
        delta_pct = (
            abs(report.card_count_observed - report.card_count_baseline)
            / report.card_count_baseline
            * 100.0
        )
        if delta_pct >= _CARD_COUNT_DELTA_PCT_THRESHOLD:
            report.card_count_delta_pct = round(delta_pct, 2)

    return report


def format_drift_report_md(report: DriftReport, lang_config: LanguageConfig) -> str:
    """Render a DriftReport as a human-readable markdown document.

    `lang_config` is used for section headings via `ui_strings`. EN
    fallback is handled by the locale loader.
    """
    ui = lang_config.ui_strings
    title = ui.get("schema_drift_title", "API contract drift")
    section_node = ui.get("schema_drift_section_node_keys", "Top-level node keys")
    section_json = ui.get("schema_drift_section_json_keys", "Card JSON keys")
    section_enum = ui.get("schema_drift_section_enum_values", "Enum values")
    section_count = ui.get("schema_drift_section_card_count", "Card count")
    label_added = ui.get("schema_drift_added", "Added")
    label_removed = ui.get("schema_drift_removed", "Removed")

    lines: list[str] = [f"# {title}", ""]
    lines.append(f"_{report.card_count_baseline} → {report.card_count_observed} cards_")
    lines.append("")

    if report.added_node_keys or report.removed_node_keys:
        lines.append(f"## {section_node}")
        for k in report.added_node_keys:
            lines.append(f"- **{label_added}:** `{k}`")
        for k in report.removed_node_keys:
            lines.append(f"- **{label_removed}:** `{k}`")
        lines.append("")

    if report.added_json_keys or report.removed_json_keys:
        lines.append(f"## {section_json}")
        for k in report.added_json_keys:
            lines.append(f"- **{label_added}:** `{k}`")
        for k in report.removed_json_keys:
            lines.append(f"- **{label_removed}:** `{k}`")
        lines.append("")

    if report.added_enum_values or report.removed_enum_values:
        lines.append(f"## {section_enum}")
        for field_name in sorted(set(report.added_enum_values) | set(report.removed_enum_values)):
            added = report.added_enum_values.get(field_name, [])
            removed = report.removed_enum_values.get(field_name, [])
            lines.append(f"### `{field_name}`")
            for v in added:
                lines.append(f"- **{label_added}:** `{v}`")
            for v in removed:
                lines.append(f"- **{label_removed}:** `{v}`")
            lines.append("")

    if report.card_count_delta_pct is not None:
        lines.append(f"## {section_count}")
        lines.append(
            f"- {report.card_count_baseline} → {report.card_count_observed} "
            f"(Δ {report.card_count_delta_pct}%)"
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def load_baseline() -> Snapshot | None:
    """Read the committed baseline; return None if it doesn't exist."""
    if not BASELINE_PATH.exists():
        return None
    return cast(Snapshot, json.loads(BASELINE_PATH.read_text(encoding="utf-8")))


def save_baseline(snapshot: Snapshot) -> None:
    """Write/overwrite the committed baseline JSON."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_observed(snapshot: Snapshot, path: Path) -> None:
    """Write a per-sync observed snapshot (for later promotion to baseline)."""
    path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
