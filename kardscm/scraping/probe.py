"""Static GraphQL probe builder."""

from __future__ import annotations

from kardscm.constants import (
    GRAPHQL_HEADERS,
    GRAPHQL_QUERY,
    GRAPHQL_URL,
    GRAPHQL_VARIABLES,
)
from kardscm.models import ProbeData


def build_static_probe(language: str = "en") -> ProbeData:
    """Build ProbeData from hardcoded constants (no browser needed).

    Args:
        language: GraphQL `$language` parameter (short code, e.g. "en", "ru").

    Returns:
        ProbeData with known API endpoint, headers, and query template.
    """
    variables = dict(GRAPHQL_VARIABLES)
    variables["language"] = language
    return ProbeData(
        url=GRAPHQL_URL,
        headers=dict(GRAPHQL_HEADERS),
        body={
            "operationName": "getCards",
            "variables": variables,
            "query": GRAPHQL_QUERY,
        },
    )
