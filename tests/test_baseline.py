"""Tests for kardscm.scraping.baseline — API contract drift detection."""

from __future__ import annotations

import json

import pytest

from kardscm.scraping.baseline import (
    DriftReport,
    Snapshot,
    build_snapshot,
    diff_snapshots,
    format_drift_report_md,
    load_baseline,
    save_baseline,
)


def _node(
    *,
    card_id: str = "test_card",
    extra_node_keys: dict | None = None,
    json_overrides: dict | None = None,
) -> dict:
    """Build a raw API node with realistic shape; per-test overrides allowed."""
    base_json = {
        "title": {"en-EN": "Test"},
        "text": {"en-EN": "..."},
        "type": "infantry",
        "faction": "Soviet",
        "rarity": "Standard",
        "set": "Base",
        "kredits": 1,
        "attack": 1,
        "defense": 1,
        "attributes": ["blitz"],
    }
    if json_overrides:
        base_json.update(json_overrides)
    node: dict = {
        "cardId": card_id,
        "id": "abc",
        "importId": "1",
        "imageUrl": "x.png",
        "thumbUrl": "x_t.png",
        "reserved": False,
        "__typename": "Card",
        "json": base_json,
    }
    if extra_node_keys:
        node.update(extra_node_keys)
    return node


class TestBuildSnapshot:
    def test_captures_node_keys(self) -> None:
        snap = build_snapshot([_node()])
        assert "cardId" in snap["node_keys"]
        assert "json" in snap["node_keys"]
        assert "imageUrl" in snap["node_keys"]
        # Keys are sorted for stable diffs
        assert snap["node_keys"] == sorted(snap["node_keys"])

    def test_captures_json_keys_with_counts(self) -> None:
        # 3 cards: all have title/faction; only 2 have attack
        nodes = [
            _node(card_id="a"),
            _node(card_id="b"),
            _node(card_id="c", json_overrides={"attack": None}),
        ]
        # Remove attack from third card entirely
        del nodes[2]["json"]["attack"]
        snap = build_snapshot(nodes)
        assert snap["json_keys"]["title"] == 3
        assert snap["json_keys"]["faction"] == 3
        assert snap["json_keys"]["attack"] == 2

    def test_extracts_enum_values_sorted_unique(self) -> None:
        nodes = [
            _node(card_id="a", json_overrides={"faction": "Soviet"}),
            _node(card_id="b", json_overrides={"faction": "USA"}),
            _node(card_id="c", json_overrides={"faction": "Soviet"}),
        ]
        snap = build_snapshot(nodes)
        assert snap["enum_values"]["faction"] == ["Soviet", "USA"]

    def test_captures_attributes_from_array(self) -> None:
        nodes = [
            _node(card_id="a", json_overrides={"attributes": ["blitz", "guard"]}),
            _node(card_id="b", json_overrides={"attributes": ["guard", "ambush"]}),
            _node(card_id="c", json_overrides={"attributes": []}),
        ]
        snap = build_snapshot(nodes)
        assert snap["enum_values"]["attributes"] == ["ambush", "blitz", "guard"]

    def test_card_count_matches_input(self) -> None:
        snap = build_snapshot([_node(card_id=f"c{i}") for i in range(7)])
        assert snap["card_count"] == 7

    def test_empty_nodes_safe(self) -> None:
        snap = build_snapshot([])
        assert snap["card_count"] == 0
        assert snap["node_keys"] == []
        assert snap["json_keys"] == {}
        assert all(v == [] for v in snap["enum_values"].values())

    def test_omits_set_enum(self) -> None:
        # `set` (card expansion) is normal content, not a tracked contract enum.
        snap = build_snapshot([_node()])
        assert "set" not in snap["enum_values"]
        assert set(snap["enum_values"]) == {"faction", "type", "rarity", "attributes"}


def _baseline_snap(**overrides) -> Snapshot:
    snap = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
    snap.update(overrides)
    return snap


class TestDiffSnapshots:
    def test_no_changes_returns_empty(self) -> None:
        baseline = _baseline_snap()
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        report = diff_snapshots(baseline, observed)
        assert not report.has_changes()
        assert report.count() == 0

    def test_new_node_key_warns(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id=f"c{i}", extra_node_keys={"newField": 1}) for i in range(10)]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert any("newField" in line for line in report.added_node_keys)

    def test_removed_node_key_errors(self) -> None:
        baseline = _baseline_snap()
        baseline["node_keys"] = sorted(baseline["node_keys"] + ["legacyField"])
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "legacyField" in report.removed_node_keys

    def test_new_enum_value_warns(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id="a", json_overrides={"faction": "Belgium"})] + [
            _node(card_id=f"c{i}") for i in range(10)
        ]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "Belgium" in report.added_enum_values["faction"]

    def test_removed_enum_value_warns(self) -> None:
        baseline = _baseline_snap()
        baseline["enum_values"]["faction"] = sorted(
            baseline["enum_values"]["faction"] + ["Atlantis"]
        )
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "Atlantis" in report.removed_enum_values["faction"]

    def test_card_count_growth_does_not_trigger(self) -> None:
        # Growth (new cards) is normal content evolution, never drift.
        baseline = _baseline_snap(card_count=100)
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(150)])
        report = diff_snapshots(baseline, observed)
        assert report.card_count_drop_pct is None
        assert not report.has_changes()

    def test_card_count_sharp_drop_triggers(self) -> None:
        # A large drop (-20%) suggests a partial/broken fetch → halt.
        baseline = _baseline_snap(card_count=100)
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(80)])
        report = diff_snapshots(baseline, observed)
        assert report.card_count_drop_pct is not None
        assert report.card_count_drop_pct >= 10
        assert report.has_changes()

    def test_card_count_small_drop_silent(self) -> None:
        # -5% is below the 10% drop threshold → no trigger.
        baseline = _baseline_snap(card_count=100)
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(95)])
        report = diff_snapshots(baseline, observed)
        assert report.card_count_drop_pct is None
        assert not report.has_changes()

    def test_new_set_value_does_not_trigger(self) -> None:
        # A new card set (expansion) is normal content, not contract drift.
        baseline = _baseline_snap()
        nodes = [_node(card_id=f"c{i}") for i in range(10)]
        nodes[0]["json"]["set"] = "NewExpansion"
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert not report.has_changes()

    def test_legacy_baseline_with_set_key_does_not_trigger(self) -> None:
        # A pre-existing baseline may still carry enum_values["set"]; the new
        # detector ignores untracked enum fields and must not flag them.
        baseline = _baseline_snap()
        baseline["enum_values"]["set"] = ["Base", "Retired"]
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        report = diff_snapshots(baseline, observed)
        assert not report.has_changes()

    def test_new_type_value_triggers(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id="a", json_overrides={"type": "warship"})] + [
            _node(card_id=f"c{i}") for i in range(9)
        ]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "warship" in report.added_enum_values["type"]

    def test_new_rarity_value_triggers(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id="a", json_overrides={"rarity": "Mythic"})] + [
            _node(card_id=f"c{i}") for i in range(9)
        ]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "Mythic" in report.added_enum_values["rarity"]

    def test_new_attribute_value_triggers(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id="a", json_overrides={"attributes": ["blitz", "newkeyword"]})] + [
            _node(card_id=f"c{i}") for i in range(9)
        ]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert report.has_changes()
        assert "newkeyword" in report.added_enum_values["attributes"]

    def test_new_json_key_warns(self) -> None:
        baseline = _baseline_snap()
        nodes = [_node(card_id=f"c{i}", json_overrides={"newCardField": 42}) for i in range(10)]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert "newCardField" in report.added_json_keys

    def test_removed_json_key_errors(self) -> None:
        baseline = _baseline_snap()
        baseline["json_keys"]["legacyCardField"] = 5
        observed = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        report = diff_snapshots(baseline, observed)
        assert "legacyCardField" in report.removed_json_keys


class TestFormatDriftReport:
    def test_includes_title_and_all_categories(self, monkeypatch) -> None:
        from kardscm.locales import LANGUAGE_EN

        baseline = _baseline_snap()
        baseline["node_keys"] = sorted(baseline["node_keys"] + ["legacyField"])
        baseline["enum_values"]["faction"] = sorted(
            baseline["enum_values"]["faction"] + ["Atlantis"]
        )
        nodes = [_node(card_id=f"c{i}", extra_node_keys={"newField": 1}) for i in range(10)]
        nodes[0]["json"]["faction"] = "Belgium"
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)

        md = format_drift_report_md(report, LANGUAGE_EN)
        assert "# " in md  # has title
        assert "newField" in md
        assert "legacyField" in md
        assert "Belgium" in md
        assert "Atlantis" in md


class TestPersistence:
    def test_load_baseline_returns_none_when_missing(self, tmp_path, monkeypatch) -> None:
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "missing.json")
        assert load_baseline() is None

    def test_save_then_load_roundtrip(self, tmp_path, monkeypatch) -> None:
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        snap = _baseline_snap()
        save_baseline(snap)
        loaded = load_baseline()
        assert loaded is not None
        assert loaded["card_count"] == snap["card_count"]
        assert loaded["node_keys"] == snap["node_keys"]
        assert loaded["json_keys"] == snap["json_keys"]
        assert loaded["enum_values"] == snap["enum_values"]


class TestDriftReportSemantics:
    def test_has_changes_true_when_added_node_key(self) -> None:
        report = DriftReport()
        report.added_node_keys.append("foo")
        assert report.has_changes()

    def test_has_changes_true_when_presence_dropped(self) -> None:
        report = DriftReport()
        report.presence_dropped_json_keys.append("attack: 100% -> 70%")
        assert report.has_changes()

    def test_has_changes_true_when_card_count_dropped(self) -> None:
        report = DriftReport()
        report.card_count_drop_pct = 15.0
        assert report.has_changes()

    def test_has_changes_false_when_empty(self) -> None:
        assert not DriftReport().has_changes()


class TestPresenceDropDetection:
    def test_key_drops_from_full_to_partial(self) -> None:
        # baseline: attack on all 10 cards. observed: attack on only 5.
        baseline = build_snapshot([_node(card_id=f"c{i}") for i in range(10)])
        # Build observed where half of cards lack `attack` in their json
        nodes = [_node(card_id=f"c{i}") for i in range(10)]
        for n in nodes[:5]:
            del n["json"]["attack"]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert any("attack" in s for s in report.presence_dropped_json_keys)

    def test_no_drop_when_ratio_below_threshold(self) -> None:
        # 100% baseline → 99% observed (1 missing of 100). Below 5pp threshold.
        baseline = build_snapshot([_node(card_id=f"c{i}") for i in range(100)])
        nodes = [_node(card_id=f"c{i}") for i in range(100)]
        del nodes[0]["json"]["attack"]
        observed = build_snapshot(nodes)
        report = diff_snapshots(baseline, observed)
        assert not any("attack" in s for s in report.presence_dropped_json_keys)


class TestBaselineCommands:
    """`baseline accept` promotes the snapshot the last halted sync stashed."""

    @staticmethod
    def _stash(db_path, payload) -> None:
        from kardscm.commands.sync import OBSERVED_SNAPSHOT_KEY
        from kardscm.storage import get_connection, initialize_schema, set_metadata

        with get_connection(db_path) as conn:
            initialize_schema(conn, db_path)
            set_metadata(conn, OBSERVED_SNAPSHOT_KEY, payload)

    @staticmethod
    def _valid_snapshot() -> dict:
        return {
            "card_count": 10,
            "node_keys": ["cardId"],
            "json_keys": {"title": 10},
            "enum_values": {"faction": ["Soviet"]},
        }

    def test_accept_without_stashed_snapshot_exits(self, tmp_path) -> None:
        from kardscm.commands import baseline_accept

        with pytest.raises(SystemExit, match="No drifted API shape"):
            baseline_accept(db_path=str(tmp_path / "t.db"))

    def test_accept_malformed_json_exits(self, tmp_path) -> None:
        from kardscm.commands import baseline_accept

        db_path = str(tmp_path / "t.db")
        self._stash(db_path, "{not json")
        with pytest.raises(SystemExit, match="not valid JSON"):
            baseline_accept(db_path=db_path)

    def test_accept_non_dict_root_exits(self, tmp_path) -> None:
        from kardscm.commands import baseline_accept

        db_path = str(tmp_path / "t.db")
        self._stash(db_path, "[]")
        with pytest.raises(SystemExit, match="not an object"):
            baseline_accept(db_path=db_path)

    def test_accept_missing_required_keys_exits(self, tmp_path) -> None:
        from kardscm.commands import baseline_accept

        db_path = str(tmp_path / "t.db")
        self._stash(db_path, json.dumps({"card_count": 10, "node_keys": []}))
        with pytest.raises(SystemExit, match="missing required keys"):
            baseline_accept(db_path=db_path)

    def test_accept_wrong_type_for_card_count_exits(self, tmp_path) -> None:
        from kardscm.commands import baseline_accept

        db_path = str(tmp_path / "t.db")
        self._stash(db_path, json.dumps({**self._valid_snapshot(), "card_count": "ten"}))
        with pytest.raises(SystemExit, match="card_count must be an int"):
            baseline_accept(db_path=db_path)

    def test_accept_promotes_the_reviewed_snapshot(self, tmp_path, monkeypatch) -> None:
        from kardscm.commands import baseline_accept
        from kardscm.scraping import baseline as bm

        baseline_path = tmp_path / "baseline.json"
        monkeypatch.setattr(bm, "BASELINE_PATH", baseline_path)

        db_path = str(tmp_path / "t.db")
        self._stash(db_path, json.dumps({**self._valid_snapshot(), "card_count": 999}))

        baseline_accept(db_path=db_path)

        assert json.loads(baseline_path.read_text())["card_count"] == 999

    def test_accept_clears_the_snapshot_so_it_is_not_reused(self, tmp_path, monkeypatch) -> None:
        from kardscm.commands import baseline_accept
        from kardscm.scraping import baseline as bm

        monkeypatch.setattr(bm, "BASELINE_PATH", tmp_path / "baseline.json")
        db_path = str(tmp_path / "t.db")
        self._stash(db_path, json.dumps(self._valid_snapshot()))

        baseline_accept(db_path=db_path)

        with pytest.raises(SystemExit, match="No drifted API shape"):
            baseline_accept(db_path=db_path)
