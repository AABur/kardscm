#!/usr/bin/env python3
"""Compatibility wrapper for the built-in rules sync command.

Prefer `kardscm rules sync` for normal usage.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from kardscm.rules import sync_rules_to_staging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """CLI entry point for the compatibility wrapper."""
    parser = argparse.ArgumentParser(description="Stage a rules sync review report")
    parser.add_argument(
        "--rules-dir",
        default="rules",
        help="Accepted rules directory (default: rules)",
    )
    parser.add_argument(
        "--staging-dir",
        default=".rules_staging",
        help="Staging directory for candidate rules (default: .rules_staging)",
    )
    args = parser.parse_args()

    try:
        result = sync_rules_to_staging(
            rules_dir=str(Path(args.rules_dir)),
            staging_dir=str(Path(args.staging_dir)),
        )
        logger.info(
            "Rules staged: %d added, %d changed, %d removed, %d unchanged.",
            result.added,
            result.changed,
            result.removed,
            result.unchanged,
        )
        logger.info("Review report: %s", result.report_path)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    main()
