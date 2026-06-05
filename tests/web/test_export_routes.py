"""End-to-end route tests for the kardscm webUI export flow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kardscm.locales import LANGUAGE_EN
from kardscm.storage import (
    get_connection,
    initialize_schema,
    upsert_cards,
)
from kardscm.web.app import create_app


@pytest.fixture()
def db_path(tmp_path, make_card) -> Path:
    """DB seeded with one card so export has something to write."""
    path = tmp_path / "export.db"
    with get_connection(path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [make_card()])
    return path


@pytest.fixture()
def client(db_path: Path, monkeypatch, tmp_path) -> TestClient:
    monkeypatch.chdir(tmp_path)
    app = create_app(db_path, lang_config=LANGUAGE_EN)
    return TestClient(app)


class TestExportModal:
    def test_renders_format_buttons(self, client: TestClient) -> None:
        r = client.get("/export/modal")
        assert r.status_code == 200
        assert "modal-backdrop" in r.text
        assert LANGUAGE_EN.ui_strings["export_modal_title"] in r.text
        for fmt in ("xlsx", "json"):
            assert f"/export/{fmt}" in r.text
        assert "/export/csv" not in r.text


class TestExportDownload:
    def test_xlsx_returns_attachment(self, client: TestClient) -> None:
        r = client.get("/export/xlsx")
        assert r.status_code == 200
        disp = r.headers.get("content-disposition", "")
        assert "attachment" in disp
        assert ".xlsx" in disp
        # XLSX is a ZIP archive — first bytes are the ZIP signature.
        assert r.content[:4] == b"PK\x03\x04"

    def test_csv_returns_400(self, client: TestClient) -> None:
        r = client.get("/export/csv")
        assert r.status_code == 400

    def test_json_returns_attachment(self, client: TestClient) -> None:
        r = client.get("/export/json")
        assert r.status_code == 200
        disp = r.headers.get("content-disposition", "")
        assert "attachment" in disp
        assert ".json" in disp
        body = json.loads(r.content)
        assert body["metadata"] == {"total_cards": len(body["cards"])}
        assert "language" not in body["metadata"]
        assert isinstance(body["cards"], list)
        card = body["cards"][0]
        assert isinstance(card["title"], dict)
        assert isinstance(card["attributes"], list)
        assert card["faction"] == "USA"

    def test_unknown_format_returns_400(self, client: TestClient) -> None:
        r = client.get("/export/pdf")
        assert r.status_code == 400


class TestExportButtonRenders:
    def test_index_includes_export_button(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert LANGUAGE_EN.ui_strings["nav_export"] in r.text
        assert "/export/modal" in r.text
