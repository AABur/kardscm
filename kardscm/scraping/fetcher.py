"""GraphQL paginator using httpx."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from kardscm.models import ProbeData

logger = logging.getLogger(__name__)


def _find_edges_or_nodes(data: Any) -> list[Any] | None:
    """Recursively find the first 'edges' or 'nodes' key in the response."""
    if isinstance(data, dict):
        if "edges" in data:
            return list(data["edges"])
        if "nodes" in data:
            return list(data["nodes"])
        for value in data.values():
            result = _find_edges_or_nodes(value)
            if result is not None:
                return result
    if isinstance(data, list):
        for item in data:
            result = _find_edges_or_nodes(item)
            if result is not None:
                return result
    return None


def _find_page_info(data: Any) -> dict[str, Any] | None:
    """Recursively find the first 'pageInfo' in the response."""
    if isinstance(data, dict):
        if "pageInfo" in data:
            return dict(data["pageInfo"])
        for value in data.values():
            result = _find_page_info(value)
            if result is not None:
                return result
    if isinstance(data, list):
        for item in data:
            result = _find_page_info(item)
            if result is not None:
                return result
    return None


def _extract_card(item: dict[str, Any]) -> dict[str, Any]:
    """Extract card node from an edge, or return the item directly."""
    if "node" in item:
        return dict(item["node"])
    return item


def _detect_pagination(variables: dict, query: str = "") -> str:
    """Detect pagination type: 'cursor' or 'offset'."""
    if "after" in variables:
        return "cursor"
    if "offset" in variables:
        return "offset"
    if "$offset" in query or "offset:" in query:
        return "offset"
    if "$after" in query or "after:" in query:
        return "cursor"
    return "offset"


def fetch_all_cards(probe: ProbeData) -> list[dict]:
    """Fetch all cards via GraphQL pagination.

    Args:
        probe: Captured probe data with URL, headers, and body template.

    Returns:
        List of raw API card nodes.
    """
    url = probe["url"]
    headers = probe["headers"]
    body_template = probe["body"]
    variables = body_template.get("variables", {})

    query_text = body_template.get("query", "")
    pagination_type = _detect_pagination(variables, query_text)
    logger.info("Pagination type: %s", pagination_type)

    all_cards: list[dict] = []
    seen_ids: set[str] = set()

    cursor: str | None = None
    offset = 0
    limit = variables.get("first", variables.get("limit", variables.get("pageSize", 0)))
    if not limit:
        m = re.search(r"\bfirst:\s*(\d+)", query_text)
        limit = int(m.group(1)) if m else 50
    page = 0

    with httpx.Client(timeout=30.0) as client:
        while True:
            page += 1
            body = dict(body_template)
            vars_copy = dict(variables)

            if pagination_type == "cursor":
                if cursor is not None:
                    vars_copy["after"] = cursor
                elif "after" in vars_copy:
                    vars_copy.pop("after", None)
            else:
                vars_copy["offset"] = offset

            body["variables"] = vars_copy

            logger.info("Page %d (offset=%d)", page, offset)

            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                logger.error("GraphQL errors: %s", data["errors"])
                break

            edges = _find_edges_or_nodes(data.get("data", data))
            if not edges:
                logger.info("No data on page %d, stopping", page)
                break

            new_count = 0
            for item in edges:
                card = _extract_card(item)
                card_id = card.get("cardId") or card.get("id") or card.get("importId")
                if card_id and card_id in seen_ids:
                    continue
                if card_id:
                    seen_ids.add(card_id)
                all_cards.append(card)
                new_count += 1

            logger.info("Got %d new cards (total: %d)", new_count, len(all_cards))

            if new_count == 0:
                break

            if pagination_type == "cursor":
                page_info = _find_page_info(data.get("data", data))
                if not page_info:
                    break
                has_next = page_info.get("hasNextPage", False)
                cursor = page_info.get("endCursor")
                if not has_next or not cursor:
                    break
            else:
                if len(edges) < limit:
                    break
                offset += limit

    logger.info("Fetched %d total cards", len(all_cards))
    return all_cards
