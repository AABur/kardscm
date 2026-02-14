"""Tests for collection CLI argument parsing."""

import argparse

import pytest

from kards.cli import parse_args, validate_args


def test_parse_args_sync() -> None:
    args = parse_args(["--sync"])
    assert args.sync is True
    assert args.export is False


def test_parse_args_export() -> None:
    args = parse_args(["--export", "--format", "csv", "--file", "out.csv"])
    assert args.export is True
    assert args.format == "csv"
    assert args.file == "out.csv"


def test_validate_args_requires_mode() -> None:
    args = argparse.Namespace(sync=False, export=False, update=False, format=None, file=None)
    with pytest.raises(SystemExit):
        validate_args(args)


def test_validate_args_export_requires_format() -> None:
    args = argparse.Namespace(sync=False, export=True, update=False, format=None, file="out.csv")
    with pytest.raises(SystemExit):
        validate_args(args)


def test_validate_args_export_requires_file() -> None:
    args = argparse.Namespace(sync=False, export=True, update=False, format="csv", file=None)
    with pytest.raises(SystemExit):
        validate_args(args)


def test_validate_args_export_ok() -> None:
    args = argparse.Namespace(sync=False, export=True, update=False, format="csv", file="out.csv")
    validate_args(args)


def test_parse_args_rejects_invalid_format() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--export", "--format", "pdf", "--file", "out.pdf"])
