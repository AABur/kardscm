"""Tests for collection CLI (Typer-based)."""

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from kardscm import __version__
from kardscm.cli import app


@pytest.fixture(scope="session")
def runner():
    return CliRunner()


def test_no_args_shows_help(runner) -> None:
    result = runner.invoke(app, [])
    assert "sync" in result.output
    assert "export" in result.output
    assert "update" in result.output
    assert "deck" in result.output


def test_version_flag(runner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_sync_command(runner) -> None:
    with patch("kardscm.cli.sync_collection") as mock_sync:
        result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    mock_sync.assert_called_once()


def test_export_requires_format(runner) -> None:
    result = runner.invoke(app, ["export", "--file", "out.json"])
    assert result.exit_code != 0


def test_export_requires_file(runner) -> None:
    result = runner.invoke(app, ["export", "--format", "json"])
    assert result.exit_code != 0


def test_export_rejects_invalid_format(runner) -> None:
    result = runner.invoke(app, ["export", "--format", "pdf", "--file", "out.pdf"])
    assert result.exit_code != 0
    assert "pdf" in result.output.lower()


def test_export_rejects_csv_format(runner) -> None:
    result = runner.invoke(app, ["export", "--format", "csv", "--file", "out.csv"])
    assert result.exit_code != 0
    assert "csv" in result.output.lower()


def test_export_valid(runner) -> None:
    with patch("kardscm.cli.export_collection") as mock_export:
        result = runner.invoke(app, ["export", "--format", "json", "--file", "out.json"])
    assert result.exit_code == 0
    args = mock_export.call_args[0]
    assert args[0] == "json"
    assert Path(args[1]).name == "out.json"


def test_update_requires_file(runner) -> None:
    result = runner.invoke(app, ["update"])
    assert result.exit_code != 0


def test_update_uses_input_flag(runner, tmp_path: Path) -> None:
    xlsx_file = tmp_path / "cards.xlsx"
    xlsx_file.write_bytes(b"")
    with patch("kardscm.cli.update_collection") as mock_update:
        result = runner.invoke(app, ["update", "-i", str(xlsx_file)])
    assert result.exit_code == 0
    mock_update.assert_called_once()


def test_deck_import_requires_file(runner) -> None:
    result = runner.invoke(app, ["deck", "import"])
    assert result.exit_code != 0


def test_deck_export_requires_file(runner) -> None:
    result = runner.invoke(app, ["deck", "export"])
    assert result.exit_code != 0


def test_deck_no_args_shows_help(runner) -> None:
    result = runner.invoke(app, ["deck"])
    assert "import" in result.output
    assert "export" in result.output


def test_deck_help_shows_description(runner) -> None:
    result = runner.invoke(app, ["deck", "--help"])
    assert "Import and export saved decks" in result.output


def test_lang_flag_forwarded_to_export(runner, tmp_path: Path) -> None:
    with patch("kardscm.cli.export_collection") as mock_export:
        result = runner.invoke(
            app,
            ["--lang", "ru", "export", "--format", "json", "--file", str(tmp_path / "out.json")],
        )
    assert result.exit_code == 0
    assert mock_export.call_args.kwargs.get("lang") == "ru"


def test_lang_flag_forwarded_to_sync(runner) -> None:
    with patch("kardscm.cli.sync_collection") as mock_sync:
        result = runner.invoke(app, ["--lang", "de", "sync"])
    assert result.exit_code == 0
    assert mock_sync.call_args.kwargs.get("lang") == "de"


def test_compound_lang_passed_verbatim(runner, tmp_path: Path) -> None:
    with patch("kardscm.cli.export_collection") as mock_export:
        result = runner.invoke(
            app,
            [
                "--lang",
                "zh-Hant",
                "export",
                "--format",
                "json",
                "--file",
                str(tmp_path / "out.json"),
            ],
        )
    assert result.exit_code == 0
    assert mock_export.call_args.kwargs.get("lang") == "zh-Hant"


def test_no_lang_flag_passes_none(runner, tmp_path: Path) -> None:
    with patch("kardscm.cli.export_collection") as mock_export:
        result = runner.invoke(
            app,
            ["export", "--format", "json", "--file", str(tmp_path / "out.json")],
        )
    assert result.exit_code == 0
    assert mock_export.call_args.kwargs.get("lang") is None
