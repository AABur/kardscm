import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_file(path: str, expected_ext: str, must_exist: bool = False) -> Path:
    """Validate file extension and existence.

    Args:
        path: File path string.
        expected_ext: Expected extension (e.g. ".xlsx").
        must_exist: If True, file must exist on disk.

    Returns:
        Resolved Path object.

    Raises:
        SystemExit: If validation fails.
    """
    p = Path(path)
    if p.suffix != expected_ext:
        raise SystemExit(f"Expected {expected_ext} file, got: {p.suffix or '(no extension)'}")
    if must_exist and not p.exists():
        raise SystemExit(f"File not found: {path}")
    return p
