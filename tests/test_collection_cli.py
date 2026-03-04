"""Tests for collection CLI (Typer-based)."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from kardscm.cli import app

runner = CliRunner()


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "sync" in result.output
    assert "export" in result.output
    assert "update" in result.output
    assert "deck" in result.output


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.2.0" in result.output


def test_sync_command() -> None:
    with patch("kardscm.cli.sync_collection") as mock_sync:
        result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    mock_sync.assert_called_once()


def test_export_requires_format() -> None:
    result = runner.invoke(app, ["export", "--file", "out.csv"])
    assert result.exit_code != 0


def test_export_requires_file() -> None:
    result = runner.invoke(app, ["export", "--format", "csv"])
    assert result.exit_code != 0


def test_export_rejects_invalid_format() -> None:
    result = runner.invoke(app, ["export", "--format", "pdf", "--file", "out.pdf"])
    assert result.exit_code != 0
    assert "pdf" in result.output.lower()


def test_export_valid() -> None:
    with patch("kardscm.cli.export_collection") as mock_export:
        result = runner.invoke(app, ["export", "--format", "csv", "--file", "out.csv"])
    assert result.exit_code == 0
    args = mock_export.call_args[0]
    assert args[0] == "csv"
    assert Path(args[1]).name == "out.csv"


def test_update_requires_file() -> None:
    result = runner.invoke(app, ["update"])
    assert result.exit_code != 0


def test_update_uses_input_flag(tmp_path: Path) -> None:
    xlsx_file = tmp_path / "cards.xlsx"
    xlsx_file.write_bytes(b"")
    with patch("kardscm.cli.update_collection") as mock_update:
        result = runner.invoke(app, ["update", "-i", str(xlsx_file)])
    assert result.exit_code == 0
    mock_update.assert_called_once()


def test_deck_import_requires_file() -> None:
    result = runner.invoke(app, ["deck", "import"])
    assert result.exit_code != 0


def test_deck_export_requires_file() -> None:
    result = runner.invoke(app, ["deck", "export"])
    assert result.exit_code != 0


def test_deck_no_args_shows_help() -> None:
    result = runner.invoke(app, ["deck"])
    assert "import" in result.output
    assert "export" in result.output


def test_deck_help_shows_description() -> None:
    result = runner.invoke(app, ["deck", "--help"])
    assert "Import and export saved decks" in result.output
