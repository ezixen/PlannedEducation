"""
Centralized version management.

The VERSION file at the repository root is the single source of truth
for the project version number. All other files reference this file
indirectly through this module.

To bump the version, edit only VERSION and re-run the sync script
(or commit VERSION and let CI sync derived files).
"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_VERSION_FILE = _ROOT / "VERSION"


def get_version() -> str:
    """Read the project version from the VERSION file."""
    return _VERSION_FILE.read_text(encoding="utf-8").strip()


__version__ = get_version()
