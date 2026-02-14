"""Tests for collection export behavior."""

from pathlib import Path

import pytest

from kards.cli import export_collection


def test_export_requires_data(tmp_path: Path) -> None:
    db_path = tmp_path / "collection.db"
    output_path = tmp_path / "out.csv"

    with pytest.raises(SystemExit, match="Run --sync first"):
        export_collection("csv", str(output_path), db_path=str(db_path))
