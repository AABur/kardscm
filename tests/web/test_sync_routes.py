"""End-to-end route tests for the kardscm webUI sync flow."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from kardscm.locales import LANGUAGE_EN
from kardscm.storage import (
    fetch_cards,
    get_connection,
    initialize_schema,
    upsert_cards,
)
from kardscm.web.app import create_app


@pytest.fixture()
def db_path(tmp_path, make_card) -> Path:
    """DB seeded with one card and the schema initialised."""
    path = tmp_path / "sync.db"
    with get_connection(path) as conn:
        initialize_schema(conn)
        upsert_cards(conn, [make_card(kredits=2)])
    return path


@pytest.fixture()
def client(db_path: Path, monkeypatch, tmp_path) -> TestClient:
    """TestClient bound to a temporary cwd so diff reports land inside tmp_path."""
    monkeypatch.chdir(tmp_path)
    app = create_app(db_path, lang_config=LANGUAGE_EN)
    return TestClient(app)


class TestSyncConfirmModal:
    def test_renders_confirm_modal(self, client: TestClient) -> None:
        r = client.get("/sync/modal")
        assert r.status_code == 200
        assert "modal-backdrop" in r.text
        assert LANGUAGE_EN.ui_strings["sync_confirm_title"] in r.text
        assert "/sync/start" in r.text


class TestSyncStart:
    @patch("kardscm.commands.sync.scrape_cards")
    def test_start_with_changes_renders_diff_modal(
        self, mock_scrape, client: TestClient, make_card
    ) -> None:
        mock_scrape.return_value = [make_card(kredits=5)]  # delta vs DB (kredits=2)
        r = client.post("/sync/start")
        assert r.status_code == 200
        assert "modal-backdrop" in r.text
        assert LANGUAGE_EN.ui_strings["sync_diff_title"] in r.text
        assert LANGUAGE_EN.ui_strings["sync_apply"] in r.text
        # Diff modal must reference an apply URL with a session id.
        assert "/sync/apply/" in r.text
        assert "/sync/cancel/" in r.text

    @patch("kardscm.commands.sync.scrape_cards")
    def test_start_with_no_changes_renders_empty_modal_and_updates_metadata(
        self, mock_scrape, client: TestClient, db_path: Path, make_card
    ) -> None:
        mock_scrape.return_value = [make_card(kredits=2)]  # equals DB state
        r = client.post("/sync/start")
        assert r.status_code == 200
        assert LANGUAGE_EN.ui_strings["sync_diff_empty"] in r.text
        # Empty diff must NOT expose apply/cancel URLs.
        assert "/sync/apply/" not in r.text
        with get_connection(db_path) as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key='last_sync'").fetchone()
        assert row is not None

    @patch("kardscm.commands.sync.scrape_cards")
    def test_start_on_contract_drift_renders_drift_modal(
        self, mock_scrape, client: TestClient, db_path: Path, make_card
    ) -> None:
        from kardscm.scraping import ApiContractDriftError
        from kardscm.scraping.baseline import DriftReport

        report = DriftReport()
        report.added_json_keys.append("newField")
        mock_scrape.side_effect = ApiContractDriftError(
            report,
            Path("sync-schema-diff-x.md"),
            Path("sync-schema-observed-x.json"),
        )
        r = client.post("/sync/start")
        assert r.status_code == 200
        # Drift modal points at the report and exposes no apply/cancel.
        assert "sync-schema-diff-x.md" in r.text
        assert "/sync/apply/" not in r.text
        # DB must remain untouched.
        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["kredits"] == 2


def _extract_sync_id(html: str) -> str:
    """Parse the sync_id out of an apply URL in the rendered diff modal."""
    marker = "/sync/apply/"
    idx = html.index(marker) + len(marker)
    # Stop at the first non-id character (quote, space, end-tag).
    end = idx
    while end < len(html) and html[end] not in ('"', "'", " ", "<", ">"):
        end += 1
    return html[idx:end]


class TestSyncApply:
    @patch("kardscm.commands.sync.scrape_cards")
    def test_apply_persists_and_redirects(
        self, mock_scrape, client: TestClient, db_path: Path, make_card, tmp_path
    ) -> None:
        mock_scrape.return_value = [make_card(kredits=5)]
        start = client.post("/sync/start")
        sync_id = _extract_sync_id(start.text)

        r = client.post(f"/sync/apply/{sync_id}")
        assert r.status_code == 200
        assert r.headers.get("HX-Redirect") == "/"

        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["kredits"] == 5
        assert not list(tmp_path.glob("sync-diff-*.md"))  # browser flow writes no files

        # Session must be evicted — second apply with same id is 404.
        again = client.post(f"/sync/apply/{sync_id}")
        assert again.status_code == 404

    def test_apply_unknown_id_returns_404(self, client: TestClient) -> None:
        r = client.post("/sync/apply/does-not-exist")
        assert r.status_code == 404


class TestSyncCancel:
    @patch("kardscm.commands.sync.scrape_cards")
    def test_cancel_clears_session(
        self, mock_scrape, client: TestClient, db_path: Path, make_card
    ) -> None:
        mock_scrape.return_value = [make_card(kredits=5)]
        start = client.post("/sync/start")
        sync_id = _extract_sync_id(start.text)

        r = client.post(f"/sync/cancel/{sync_id}")
        assert r.status_code == 200

        # Cancel must have evicted the cache.
        retry = client.post(f"/sync/apply/{sync_id}")
        assert retry.status_code == 404

        # DB must remain untouched.
        with get_connection(db_path) as conn:
            cards = fetch_cards(conn)
        assert cards[0]["kredits"] == 2


class TestSyncButtonRenders:
    def test_index_includes_sync_button(self, client: TestClient) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert LANGUAGE_EN.ui_strings["nav_sync"] in r.text
        assert "/sync/modal" in r.text


# Reference make_card fixture from project conftest; json import only needed if
# we ever build cards inline. Keep the import to mirror tests/test_commands.py
# style and to make ad-hoc additions easy.
_ = json
