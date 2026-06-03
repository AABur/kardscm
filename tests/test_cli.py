"""Tests for kardscm.cli plumbing."""

from __future__ import annotations

import pytest

from kardscm.cli import _validate_extension


class TestValidateExtension:
    def test_correct_ext(self, tmp_path):
        _validate_extension(tmp_path / "cards.xlsx", ".xlsx")

    def test_wrong_ext(self, tmp_path):
        with pytest.raises(SystemExit, match="Expected .xlsx"):
            _validate_extension(tmp_path / "cards.csv", ".xlsx")

    def test_no_extension(self, tmp_path):
        with pytest.raises(SystemExit, match="no extension"):
            _validate_extension(tmp_path / "cards", ".xlsx")
