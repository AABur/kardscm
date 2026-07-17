"""Shared utility functions for command orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

import typer

from kardscm.config import LanguageConfig


def _utc_timestamp() -> str:
    return datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds")


def _safe_timestamp() -> str:
    """Filesystem-safe UTC timestamp (no colons)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def _emit_locale_warnings(cfg: LanguageConfig) -> None:
    if not cfg.fallback_warnings:
        return
    keys = cfg.fallback_warnings
    summary = ", ".join(keys[:5])
    suffix = f", … and {len(keys) - 5} more" if len(keys) > 5 else ""
    typer.echo(
        f"Locale '{cfg.code}': {len(keys)} key(s) fell back to English ({summary}{suffix}).",
        err=True,
    )
