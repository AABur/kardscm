"""Tests pinning expected values of language-agnostic constants."""

from __future__ import annotations

from kardscm.constants import GRAPHQL_VARIABLES


def test_graphql_variables_include_reserved_and_spawnables():
    """Sync must fetch reserved + spawnable cards so the diff engine can
    detect cards moving in/out of reserve and so spawned tokens land in
    the catalog. Exiles stay filtered out."""
    assert GRAPHQL_VARIABLES["showReserved"] is True
    assert GRAPHQL_VARIABLES["showSpawnables"] is True
    assert GRAPHQL_VARIABLES["showExiles"] is False
