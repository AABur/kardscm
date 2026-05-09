"""Playwright one-shot GraphQL interceptor."""

from __future__ import annotations

import json
import logging

from playwright.sync_api import Request, sync_playwright

from kardscm.constants import (
    GRAPHQL_HEADERS,
    GRAPHQL_QUERY,
    GRAPHQL_URL,
    GRAPHQL_VARIABLES,
)
from kardscm.models import ProbeData

logger = logging.getLogger(__name__)

KEEP_HEADERS = {
    "content-type",
    "accept",
    "accept-language",
    "apollographql-client-name",
    "apollographql-client-version",
    "x-apollo-operation-name",
    "x-apollo-operation-type",
    "authorization",
    "origin",
    "referer",
}


def _is_graphql_request(request: Request) -> bool:
    if request.method != "POST":
        return False
    body = request.post_data
    if not body:
        return False
    try:
        parsed = json.loads(body)
        return "operationName" in parsed or "query" in parsed
    except (json.JSONDecodeError, TypeError):
        return False


def _filter_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in KEEP_HEADERS}


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


def run_probe(url: str) -> ProbeData:
    """Open browser, intercept first GraphQL POST, return URL+headers+body.

    Args:
        url: Collection page URL to open.

    Returns:
        ProbeData with captured request details.

    Raises:
        RuntimeError: If no GraphQL request detected within timeout.
    """
    captured: dict | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        def on_request(request: Request) -> None:
            nonlocal captured
            if captured is not None:
                return
            if not _is_graphql_request(request):
                return
            try:
                body = json.loads(request.post_data or "{}")
            except json.JSONDecodeError:
                return
            operation = body.get("operationName", "<unknown>")
            logger.info("Intercepted GraphQL request: %s", operation)
            captured = {
                "url": request.url,
                "headers": _filter_headers(dict(request.headers)),
                "body": body,
            }

        page.on("request", on_request)
        logger.info("Opening %s ...", url)
        page.goto(url, wait_until="domcontentloaded")

        timeout_ms = 30_000
        waited = 0
        interval = 500
        while captured is None and waited < timeout_ms:
            page.wait_for_timeout(interval)
            waited += interval

        browser.close()

    if captured is None:
        msg = f"No GraphQL request detected within {timeout_ms // 1000}s"
        raise RuntimeError(msg)

    logger.info("Probe captured: %s", captured["url"])
    return ProbeData(
        url=captured["url"],
        headers=captured["headers"],
        body=captured["body"],
    )
