"""Sync and review workflow for the local rules knowledge base."""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import shutil
from collections import Counter, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

SEED_URLS = [
    "https://www.kards.com/rules",
    "https://www.kards.com/en/rules",
]
RULES_LINK_PATTERN = re.compile(r"/(?:en/)?(?:rules|guide|mechanics|how-to-play)", re.IGNORECASE)
DEFAULT_RULES_DIR = "rules"
DEFAULT_STAGING_DIR = ".rules_staging"
METADATA_FILE = "metadata.json"
SUMMARY_FILE = "summary.json"
REPORT_FILE = "report.md"
REQUEST_TIMEOUT = 30
MIN_CONTENT_CHARS = 50
SHORT_CONTENT_WARNING_CHARS = 250
MAX_CRAWL_PAGES = 100


@dataclass(frozen=True)
class RulesDocument:
    """Parsed rules page ready for local storage."""

    url: str
    topic: str
    content: str
    content_hash: str

    @property
    def filename(self) -> str:
        return f"{self.topic}.md"


@dataclass(frozen=True)
class RulesSyncResult:
    """Summary of a staged rules sync run."""

    added: int
    changed: int
    removed: int
    unchanged: int
    warnings: int
    staged_dir: Path
    report_path: Path


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _require_beautifulsoup() -> type:
    """Import BeautifulSoup lazily so unrelated CLI commands stay usable."""
    try:
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as e:
        raise SystemExit(
            "Missing dependency 'beautifulsoup4'. Run 'uv sync' to install project dependencies."
        ) from e
    return BeautifulSoup


def _fetch_page(client: httpx.Client, url: str) -> str | None:
    """Fetch page HTML, return None on HTTP error."""
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
    """Extract structured text content from an HTML page."""
    bs_class = _require_beautifulsoup()
    soup = bs_class(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.find("div", class_="content")
    if main is None:
        main = soup.body or soup

    lines: list[str] = []
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
    """Convert a full URL path into a unique filesystem-safe topic name."""
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "index"
    topic = re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")
    return topic or "index"


def _normalize_url(url: str) -> str:
    """Normalize URL for deterministic storage and comparisons."""
    parsed = urlparse(url)
    cleaned = parsed._replace(fragment="", query="")
    return cleaned.geturl().rstrip("/")


def _discover_links(html: str, base_url: str) -> list[str]:
    """Find rule-related links on the allowed domain only."""
    bs_class = _require_beautifulsoup()
    soup = bs_class(html, "html.parser")
    allowed_netloc = urlparse(base_url).netloc.lower()
    discovered: set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        candidate = _normalize_url(urljoin(base_url.rstrip("/") + "/", href))
        parsed = urlparse(candidate)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower() != allowed_netloc:
            continue
        if RULES_LINK_PATTERN.search(parsed.path):
            discovered.add(candidate)

    return sorted(discovered)


def _build_document(url: str, html: str) -> RulesDocument | None:
    """Build a rules document from fetched HTML."""
    content = _extract_text(html)
    if not content or len(content) < MIN_CONTENT_CHARS:
        logger.info("Skipping %s (insufficient content)", url)
        return None
    topic = _url_to_topic(url)
    return RulesDocument(
        url=url,
        topic=topic,
        content=content,
        content_hash=_compute_hash(content),
    )


def crawl_rules_documents(
    seed_urls: list[str] | None = None,
    base_url: str = "https://www.kards.com",
    max_pages: int = MAX_CRAWL_PAGES,
) -> list[RulesDocument]:
    """Crawl rule pages and return parsed documents."""
    urls_to_process = deque(_normalize_url(url) for url in (seed_urls or SEED_URLS))
    processed_urls: set[str] = set()
    documents: list[RulesDocument] = []

    with httpx.Client(
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; kardscm-rules-sync/1.0)",
            "Accept": "text/html",
        }
    ) as client:
        while urls_to_process:
            if len(processed_urls) >= max_pages:
                logger.warning("Reached crawl safety limit (%d pages).", max_pages)
                break
            url = urls_to_process.popleft()
            if url in processed_urls:
                continue
            processed_urls.add(url)

            logger.info("Processing: %s", url)
            html = _fetch_page(client, url)
            if html is None:
                continue

            for link in _discover_links(html, base_url):
                if link not in processed_urls:
                    urls_to_process.append(link)

            document = _build_document(url, html)
            if document is not None:
                documents.append(document)

    return sorted(documents, key=lambda document: document.topic)


def _load_metadata(directory: Path) -> dict[str, dict[str, str]]:
    """Load metadata from a rules directory."""
    meta_path = directory / METADATA_FILE
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _load_existing_content(directory: Path, metadata: dict[str, dict[str, str]]) -> dict[str, str]:
    """Load accepted rules content keyed by source URL."""
    content_by_url: dict[str, str] = {}
    for url, entry in metadata.items():
        filename = entry.get("file")
        if not filename:
            continue
        file_path = directory / filename
        if not file_path.exists():
            continue
        content_by_url[url] = file_path.read_text(encoding="utf-8")
    return content_by_url


def _validate_documents(documents: list[RulesDocument]) -> list[str]:
    """Return non-fatal validation warnings for manual review."""
    warnings: list[str] = []
    topics = [document.topic for document in documents]
    duplicate_topics = [topic for topic, count in Counter(topics).items() if count > 1]
    if duplicate_topics:
        joined = ", ".join(sorted(duplicate_topics))
        raise SystemExit(f"Rules sync produced duplicate topic names: {joined}")

    short_documents = [
        document.filename
        for document in documents
        if len(document.content) < SHORT_CONTENT_WARNING_CHARS
    ]
    if short_documents:
        joined = ", ".join(sorted(short_documents))
        warnings.append(f"Short documents detected: {joined}")

    duplicate_hashes = [
        digest
        for digest, count in Counter(document.content_hash for document in documents).items()
        if count > 1
    ]
    if duplicate_hashes:
        warnings.append(
            f"Documents with identical content detected: {len(duplicate_hashes)} duplicate hash group(s)"  # noqa: E501
        )

    return warnings


def _diff_snippet(old_text: str, new_text: str, limit: int = 12) -> str:
    """Return a short unified diff snippet for human review."""
    diff = list(
        difflib.unified_diff(
            old_text.splitlines(),
            new_text.splitlines(),
            fromfile="accepted",
            tofile="candidate",
            lineterm="",
            n=1,
        )
    )
    if not diff:
        return "No textual diff available."
    return "\n".join(diff[:limit])


def _build_summary(
    documents: list[RulesDocument],
    existing_metadata: dict[str, dict[str, str]],
    existing_content: dict[str, str],
    warnings: list[str],
) -> dict:
    """Build a review summary comparing candidate and accepted corpora."""
    new_by_url = {document.url: document for document in documents}
    old_urls = set(existing_metadata)
    new_urls = set(new_by_url)

    added_urls = sorted(new_urls - old_urls)
    removed_urls = sorted(old_urls - new_urls)
    unchanged_urls: list[str] = []
    changed_urls: list[str] = []
    for url in sorted(new_urls & old_urls):
        if existing_metadata[url].get("hash") == new_by_url[url].content_hash:
            unchanged_urls.append(url)
        else:
            changed_urls.append(url)

    return {
        "generated_at": _utc_timestamp(),
        "counts": {
            "candidate_documents": len(documents),
            "added": len(added_urls),
            "changed": len(changed_urls),
            "removed": len(removed_urls),
            "unchanged": len(unchanged_urls),
            "warnings": len(warnings),
        },
        "warnings": warnings,
        "added": [
            {
                "url": url,
                "topic": new_by_url[url].topic,
                "file": new_by_url[url].filename,
            }
            for url in added_urls
        ],
        "changed": [
            {
                "url": url,
                "topic": new_by_url[url].topic,
                "file": new_by_url[url].filename,
                "old_file": existing_metadata[url].get("file", ""),
                "diff_snippet": _diff_snippet(
                    existing_content.get(url, ""), new_by_url[url].content
                ),
            }
            for url in changed_urls
        ],
        "removed": [
            {
                "url": url,
                "topic": existing_metadata[url].get("topic", ""),
                "file": existing_metadata[url].get("file", ""),
            }
            for url in removed_urls
        ],
        "unchanged": [
            {
                "url": url,
                "topic": new_by_url[url].topic,
                "file": new_by_url[url].filename,
            }
            for url in unchanged_urls
        ],
    }


def _render_report(summary: dict) -> str:
    """Render a human-readable markdown review report."""
    counts = summary["counts"]
    lines = [
        "# Rules Sync Review",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "## Summary",
        f"- Candidate documents: {counts['candidate_documents']}",
        f"- Added: {counts['added']}",
        f"- Changed: {counts['changed']}",
        f"- Removed: {counts['removed']}",
        f"- Unchanged: {counts['unchanged']}",
        f"- Validation warnings: {counts['warnings']}",
        "",
        "Review this report against kards.com, then run `kardscm rules accept` to replace the active corpus.",  # noqa: E501
    ]

    if summary["warnings"]:
        lines.extend(["", "## Validation Warnings"])
        lines.extend(f"- {warning}" for warning in summary["warnings"])

    def append_section(title: str, items: list[dict], include_diff: bool = False) -> None:
        if not items:
            return
        lines.extend(["", f"## {title}"])
        for item in items:
            lines.append(f"- {item['topic']} ({item['file']})")
            lines.append(f"  Source: {item['url']}")
            if include_diff:
                lines.append("")
                lines.append("```diff")
                lines.append(item["diff_snippet"])
                lines.append("```")

    append_section("Added", summary["added"])
    append_section("Changed", summary["changed"], include_diff=True)
    append_section("Removed", summary["removed"])

    return "\n".join(lines) + "\n"


def _write_candidate_corpus(
    staging_dir: Path, documents: list[RulesDocument]
) -> dict[str, dict[str, str]]:
    """Write candidate markdown files and return metadata."""
    metadata: dict[str, dict[str, str]] = {}
    for document in documents:
        (staging_dir / document.filename).write_text(document.content, encoding="utf-8")
        metadata[document.url] = {
            "hash": document.content_hash,
            "last_synced": _utc_timestamp(),
            "topic": document.topic,
            "file": document.filename,
        }
    (staging_dir / METADATA_FILE).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata


def sync_rules_to_staging(
    rules_dir: str = DEFAULT_RULES_DIR,
    staging_dir: str = DEFAULT_STAGING_DIR,
) -> RulesSyncResult:
    """Fetch rules pages, validate them, and stage a reviewable candidate corpus."""
    accepted_dir = Path(rules_dir)
    staged_dir = Path(staging_dir)

    documents = crawl_rules_documents()
    if not documents:
        raise SystemExit("Rules sync found no valid rule pages.")

    warnings = _validate_documents(documents)
    existing_metadata = _load_metadata(accepted_dir)
    existing_content = _load_existing_content(accepted_dir, existing_metadata)
    summary = _build_summary(documents, existing_metadata, existing_content, warnings)

    if staged_dir.exists():
        shutil.rmtree(staged_dir)
    staged_dir.mkdir(parents=True, exist_ok=True)

    _write_candidate_corpus(staged_dir, documents)
    report = _render_report(summary)
    (staged_dir / SUMMARY_FILE).write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path = staged_dir / REPORT_FILE
    report_path.write_text(report, encoding="utf-8")

    return RulesSyncResult(
        added=summary["counts"]["added"],
        changed=summary["counts"]["changed"],
        removed=summary["counts"]["removed"],
        unchanged=summary["counts"]["unchanged"],
        warnings=summary["counts"]["warnings"],
        staged_dir=staged_dir,
        report_path=report_path,
    )


def accept_staged_rules(
    rules_dir: str = DEFAULT_RULES_DIR,
    staging_dir: str = DEFAULT_STAGING_DIR,
) -> None:
    """Replace the accepted rules corpus with the reviewed staged corpus."""
    accepted_dir = Path(rules_dir)
    staged_dir = Path(staging_dir)
    metadata_path = staged_dir / METADATA_FILE
    corpus_files = sorted(
        md_file for md_file in staged_dir.glob("*.md") if md_file.name != REPORT_FILE
    )

    if not staged_dir.exists():
        raise SystemExit("No staged rules found. Run 'kardscm rules sync' first.")
    if not metadata_path.exists() or not corpus_files:
        raise SystemExit("Staged rules are incomplete. Run 'kardscm rules sync' again.")

    tmp_dir = accepted_dir.parent / f".{accepted_dir.name}_tmp"
    if tmp_dir.exists():
        logger.warning("Removing stale temporary accept directory: %s", tmp_dir)
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    for md_file in corpus_files:
        shutil.copy2(md_file, tmp_dir / md_file.name)
    shutil.copy2(metadata_path, tmp_dir / METADATA_FILE)

    if accepted_dir.exists():
        shutil.rmtree(accepted_dir)
    tmp_dir.replace(accepted_dir)
    shutil.rmtree(staged_dir)


def discard_staged_rules(staging_dir: str = DEFAULT_STAGING_DIR) -> None:
    """Delete the currently staged candidate corpus."""
    staged_dir_path = Path(staging_dir)
    if not staged_dir_path.exists():
        raise SystemExit("No staged rules found.")
    shutil.rmtree(staged_dir_path)
