#!/usr/bin/env python3
"""Standalone script to sync KARDS game rules to local markdown files.

Crawls kards.com for game rules and mechanics pages, extracts text content,
and saves topic-based markdown files for use by the LLM advisor.

Usage:
    python scripts/rules_sync.py [--output-dir rules/]

Requirements:
    pip install httpx beautifulsoup4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Known entry points for game rules
SEED_URLS = [
    "https://www.kards.com/rules",
    "https://www.kards.com/en/rules",
]

# Pattern to match internal rule-related links
RULES_LINK_PATTERN = re.compile(r"/(?:en/)?(?:rules|guide|mechanics|how-to-play)", re.IGNORECASE)

DEFAULT_OUTPUT_DIR = "rules"
METADATA_FILE = "metadata.json"
REQUEST_TIMEOUT = 30


def _fetch_page(client: httpx.Client, url: str) -> str | None:
    """Fetch page HTML, return None on error."""
    try:
        response = client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _compute_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _extract_text(html: str) -> str:
    """Extract main text content from HTML page."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Try to find main content area
    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
    if main is None:
        main = soup.body or soup

    # Extract text with structure preserved
    lines = []
    for element in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        text = element.get_text(strip=True)
        if not text:
            continue
        if element.name in ("h1", "h2"):
            lines.append(f"\n## {text}\n")
        elif element.name in ("h3", "h4"):
            lines.append(f"\n### {text}\n")
        elif element.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    return "\n".join(lines).strip()


def _url_to_topic(url: str) -> str:
    """Convert URL to a filesystem-safe topic name."""
    path = url.rstrip("/").split("/")[-1] or "index"
    # Remove language prefix if present
    if path in ("en", "ru"):
        path = "index"
    # Sanitize
    topic = re.sub(r"[^a-z0-9_-]", "_", path.lower())
    return topic


def _discover_links(html: str, base_url: str) -> list[str]:
    """Find internal rule-related links in the page."""
    soup = BeautifulSoup(html, "html.parser")
    discovered = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        if not href.startswith(base_url.rstrip("/").split("//")[0] + "//"):
            continue
        if RULES_LINK_PATTERN.search(href):
            discovered.add(href.split("#")[0].split("?")[0])

    return sorted(discovered)


def _load_metadata(output_dir: Path) -> dict:
    """Load existing metadata or return empty dict."""
    meta_path = output_dir / METADATA_FILE
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def _save_metadata(output_dir: Path, metadata: dict) -> None:
    """Save metadata to JSON file."""
    meta_path = output_dir / METADATA_FILE
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def sync_rules(output_dir: str = DEFAULT_OUTPUT_DIR) -> None:
    """Main sync function: crawl, extract, and save rules."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    metadata = _load_metadata(out_path)
    base_url = "https://www.kards.com"

    # Collect URLs to process
    urls_to_process = set(SEED_URLS)
    processed_urls: set[str] = set()

    client = httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; KARDSRulesSync/1.0)",
            "Accept": "text/html",
        }
    )

    updated = 0
    skipped = 0

    try:
        while urls_to_process:
            url = urls_to_process.pop()
            if url in processed_urls:
                continue
            processed_urls.add(url)

            logger.info("Processing: %s", url)
            html = _fetch_page(client, url)
            if html is None:
                continue

            # Discover more rule links
            new_links = _discover_links(html, base_url)
            for link in new_links:
                if link not in processed_urls:
                    urls_to_process.add(link)

            # Extract and check content
            content = _extract_text(html)
            if not content or len(content) < 50:
                logger.info("Skipping %s (insufficient content)", url)
                continue

            content_hash = _compute_hash(content)

            # Check if content changed
            if url in metadata and metadata[url].get("hash") == content_hash:
                logger.info("Unchanged: %s", url)
                skipped += 1
                continue

            # Save topic file
            topic = _url_to_topic(url)
            topic_file = out_path / f"{topic}.md"
            topic_file.write_text(content, encoding="utf-8")

            # Update metadata
            metadata[url] = {
                "hash": content_hash,
                "last_synced": datetime.now(UTC).isoformat(timespec="seconds"),
                "topic": topic,
                "file": f"{topic}.md",
            }
            updated += 1
            logger.info("Updated: %s -> %s.md", url, topic)

    finally:
        client.close()

    _save_metadata(out_path, metadata)
    logger.info("Rules sync complete: %d updated, %d unchanged", updated, skipped)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Sync KARDS game rules to local markdown files")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for rules files (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    try:
        sync_rules(output_dir=args.output_dir)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
