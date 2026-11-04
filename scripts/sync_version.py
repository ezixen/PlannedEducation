"""
Synchronize the project version from VERSION to derived files.

Run this after editing VERSION to propagate the version number to
all derived files (e.g. package.json).

Usage:
    python scripts/sync_version.py
"""

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_VERSION_FILE = _ROOT / "VERSION"
_PACKAGE_JSON = _ROOT / "web" / "apps" / "portal" / "package.json"


def main() -> None:
    version = _VERSION_FILE.read_text(encoding="utf-8").strip()

    # Sync package.json
    pkg_path = _PACKAGE_JSON
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg["version"] = version
    pkg_path.write_text(json.dumps(pkg, indent=2) + "\n", encoding="utf-8")

    print(f"Synced version {version} to {pkg_path}")


if __name__ == "__main__":
    main()
