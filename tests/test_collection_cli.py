"""Tests for collection CLI argument parsing."""

import argparse

import pytest

from kards.cli import parse_args, validate_args


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults = {
        "sync": False,
        "export": False,
        "update": False,
        "import_deck": False,
        "export_deck": False,
        "format": None,
        "file": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_parse_args_sync() -> None:
    args = parse_args(["--sync"])
    assert args.sync is True
    assert args.export is False


def test_parse_args_export() -> None:
    args = parse_args(["--export", "--format", "csv", "--file", "out.csv"])
    assert args.export is True
    assert args.format == "csv"
    assert args.file == "out.csv"


def test_parse_args_import_deck() -> None:
    args = parse_args(["--import-deck", "--file", "deck.txt"])
    assert args.import_deck is True
    assert args.file == "deck.txt"


def test_parse_args_export_deck() -> None:
    args = parse_args(["--export-deck", "--file", "cards.xlsx"])
    assert args.export_deck is True
    assert args.file == "cards.xlsx"


def test_validate_args_requires_mode() -> None:
    with pytest.raises(SystemExit):
        validate_args(_ns())


def test_validate_args_export_requires_format() -> None:
    with pytest.raises(SystemExit):
        validate_args(_ns(export=True, file="out.csv"))


def test_validate_args_export_requires_file() -> None:
    with pytest.raises(SystemExit):
        validate_args(_ns(export=True, format="csv"))


def test_validate_args_export_ok() -> None:
    validate_args(_ns(export=True, format="csv", file="out.csv"))


def test_validate_args_import_deck_requires_file() -> None:
    with pytest.raises(SystemExit):
        validate_args(_ns(import_deck=True))


def test_validate_args_export_deck_requires_file() -> None:
    with pytest.raises(SystemExit):
        validate_args(_ns(export_deck=True))


def test_parse_args_rejects_invalid_format() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--export", "--format", "pdf", "--file", "out.pdf"])
