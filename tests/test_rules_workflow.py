"""Tests for the rules sync staging workflow."""

from __future__ import annotations

import json

import pytest

from kardscm.rules.workflow import (
    METADATA_FILE,
    REPORT_FILE,
    SUMMARY_FILE,
    RulesDocument,
    _build_summary,
    _diff_snippet,
    _validate_documents,
    accept_staged_rules,
    discard_staged_rules,
    sync_rules_to_staging,
)


def test_sync_rules_stages_report_and_summary(tmp_path, monkeypatch):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "rules.md").write_text("Old accepted rules", encoding="utf-8")
    (rules_dir / METADATA_FILE).write_text(
        json.dumps(
            {
                "https://www.kards.com/rules": {
                    "hash": "old-hash",
                    "last_synced": "2026-03-12T09:00:00",
                    "topic": "rules",
                    "file": "rules.md",
                }
            }
        ),
        encoding="utf-8",
    )

    def fake_crawl() -> list[RulesDocument]:
        return [
            RulesDocument(
                url="https://www.kards.com/rules",
                topic="rules",
                content="# Rules\n\nUpdated accepted rules body.",
                content_hash="new-hash",
            ),
            RulesDocument(
                url="https://www.kards.com/en/guide",
                topic="en_guide",
                content="# Guide\n\nA newly discovered rules guide page.",
                content_hash="guide-hash",
            ),
        ]

    monkeypatch.setattr("kardscm.rules.workflow.crawl_rules_documents", fake_crawl)

    result = sync_rules_to_staging(
        rules_dir=str(rules_dir),
        staging_dir=str(tmp_path / ".rules_staging"),
    )

    assert result.added == 1
    assert result.changed == 1
    assert result.removed == 0
    assert result.unchanged == 0
    assert (result.staged_dir / "rules.md").exists()
    assert (result.staged_dir / "en_guide.md").exists()
    assert (result.staged_dir / REPORT_FILE).exists()
    assert (result.staged_dir / SUMMARY_FILE).exists()

    summary = json.loads((result.staged_dir / SUMMARY_FILE).read_text(encoding="utf-8"))
    assert summary["counts"]["added"] == 1
    assert summary["counts"]["changed"] == 1
    assert summary["changed"][0]["url"] == "https://www.kards.com/rules"
    assert "```diff" in (result.staged_dir / REPORT_FILE).read_text(encoding="utf-8")


def test_accept_rules_replaces_active_corpus(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "rules.md").write_text("Old accepted rules", encoding="utf-8")
    (rules_dir / METADATA_FILE).write_text("{}", encoding="utf-8")

    staging_dir = tmp_path / ".rules_staging"
    staging_dir.mkdir()
    (staging_dir / "rules.md").write_text("New accepted rules", encoding="utf-8")
    (staging_dir / METADATA_FILE).write_text(
        json.dumps(
            {
                "https://www.kards.com/rules": {
                    "hash": "hash",
                    "last_synced": "2026-03-12T10:00:00",
                    "topic": "rules",
                    "file": "rules.md",
                }
            }
        ),
        encoding="utf-8",
    )
    (staging_dir / REPORT_FILE).write_text("report", encoding="utf-8")
    (staging_dir / SUMMARY_FILE).write_text("{}", encoding="utf-8")

    accept_staged_rules(rules_dir=str(rules_dir), staging_dir=str(staging_dir))

    assert not staging_dir.exists()
    assert (rules_dir / "rules.md").read_text(encoding="utf-8") == "New accepted rules"
    assert not (rules_dir / REPORT_FILE).exists()


def test_discard_rules_removes_staging(tmp_path):
    staging_dir = tmp_path / ".rules_staging"
    staging_dir.mkdir()
    (staging_dir / "report.md").write_text("report", encoding="utf-8")

    discard_staged_rules(staging_dir=str(staging_dir))

    assert not staging_dir.exists()


def test_discard_rules_requires_existing_stage(tmp_path):
    with pytest.raises(SystemExit, match="No staged rules found"):
        discard_staged_rules(staging_dir=str(tmp_path / ".rules_staging"))


def test_accept_rules_requires_existing_stage(tmp_path):
    with pytest.raises(SystemExit, match="No staged rules found"):
        accept_staged_rules(
            rules_dir=str(tmp_path / "rules"),
            staging_dir=str(tmp_path / ".rules_staging"),
        )


def test_validate_documents_rejects_duplicate_topics():
    documents = [
        RulesDocument("https://www.kards.com/rules", "rules", "Alpha", "hash-a"),
        RulesDocument("https://www.kards.com/en/rules", "rules", "Beta", "hash-b"),
    ]

    with pytest.raises(SystemExit, match="duplicate topic names"):
        _validate_documents(documents)


def test_validate_documents_warns_on_short_documents_and_duplicate_hashes():
    documents = [
        RulesDocument("https://www.kards.com/rules", "rules", "x" * 100, "same-hash"),
        RulesDocument("https://www.kards.com/en/guide", "en_guide", "y" * 120, "same-hash"),
    ]

    warnings = _validate_documents(documents)

    assert any("Short documents detected" in warning for warning in warnings)
    assert any("identical content" in warning for warning in warnings)


def test_diff_snippet_reports_changes():
    snippet = _diff_snippet("old line\nshared", "new line\nshared", limit=8)

    assert "--- accepted" in snippet
    assert "+++ candidate" in snippet
    assert "-old line" in snippet
    assert "+new line" in snippet


def test_build_summary_tracks_removed_urls():
    documents = [
        RulesDocument("https://www.kards.com/rules", "rules", "new text", "new-hash"),
    ]
    existing_metadata = {
        "https://www.kards.com/rules": {
            "hash": "old-hash",
            "topic": "rules",
            "file": "rules.md",
        },
        "https://www.kards.com/en/guide": {
            "hash": "guide-hash",
            "topic": "en_guide",
            "file": "en_guide.md",
        },
    }
    existing_content = {
        "https://www.kards.com/rules": "old text",
        "https://www.kards.com/en/guide": "guide text",
    }

    summary = _build_summary(documents, existing_metadata, existing_content, warnings=[])

    assert summary["counts"]["changed"] == 1
    assert summary["counts"]["removed"] == 1
    assert summary["removed"][0]["url"] == "https://www.kards.com/en/guide"
