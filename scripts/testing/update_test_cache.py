from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_PATH = REPO_ROOT / "artifacts" / "test_cache" / "source_test_results.json"
SCHEMA_VERSION = 1
MAX_CHANGED_FILES_IN_RUN = 100

TRACKED_SOURCE_DIRS = ("src", "tests", "scripts", "alembic")
TRACKED_CONFIG_FILES = (
    "pyproject.toml",
    "pytest.ini",
    "setup.cfg",
    "requirements.txt",
    "requirements-dev.txt",
    "uv.lock",
    "poetry.lock",
)
TRACKED_SUFFIXES = {".py"}
EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "artifacts",
    "audit_backups",
    "dist",
    "node_modules",
}
EXCLUDED_RELATIVE_PARTS = {
    ("tests", "scripts", "archive"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def repo_relative(path: Path, root: Path = REPO_ROOT) -> str:
    return path.relative_to(root).as_posix()


def is_excluded(path: Path, root: Path = REPO_ROOT) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        return True
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
        return True
    for excluded in EXCLUDED_RELATIVE_PARTS:
        if rel_parts[: len(excluded)] == excluded:
            return True
    return False


def iter_tracked_files(root: Path = REPO_ROOT) -> list[Path]:
    files: list[Path] = []
    for dirname in TRACKED_SOURCE_DIRS:
        directory = root / dirname
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in TRACKED_SUFFIXES and not is_excluded(path, root):
                files.append(path)
    for filename in TRACKED_CONFIG_FILES:
        path = root / filename
        if path.is_file() and not is_excluded(path, root):
            files.append(path)
    return sorted(set(files), key=lambda item: repo_relative(item, root))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_file_snapshot(root: Path = REPO_ROOT) -> dict[str, dict[str, Any]]:
    snapshot: dict[str, dict[str, Any]] = {}
    for path in iter_tracked_files(root):
        stat = path.stat()
        snapshot[repo_relative(path, root)] = {
            "sha256": sha256_file(path),
            "size_bytes": stat.st_size,
        }
    return snapshot


def dependency_snapshot(snapshot: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        path: data["sha256"]
        for path, data in snapshot.items()
        if path in TRACKED_CONFIG_FILES or path.startswith("alembic/")
    }


def command_key(command: list[str]) -> str:
    payload = json.dumps(command, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def command_to_text(command: list[str]) -> str:
    return " ".join(command)


def looks_like_pytest(command: list[str]) -> bool:
    lowered = [part.lower().replace("\\", "/") for part in command]
    if any(part == "pytest" or part.endswith("/pytest.exe") for part in lowered):
        return True
    return any(lowered[index : index + 2] == ["-m", "pytest"] for index in range(len(lowered) - 1))


def load_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "runs": [], "suites": {}, "files": {}}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Cache file is not a JSON object: {path}")
    data.setdefault("schema_version", SCHEMA_VERSION)
    data.setdefault("runs", [])
    data.setdefault("suites", {})
    data.setdefault("files", {})
    return data


def write_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temp_path.replace(path)


def run_git(args: list[str], root: Path = REPO_ROOT) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def git_state(root: Path = REPO_ROOT) -> dict[str, Any]:
    status = run_git(["status", "--porcelain", "--untracked-files=no"], root)
    return {
        "commit": run_git(["rev-parse", "HEAD"], root),
        "branch": run_git(["branch", "--show-current"], root),
        "tracked_dirty": bool(status),
    }


def comparison_baseline_for_suite(
    cache: dict[str, Any],
    suite_name: str,
) -> tuple[str | None, dict[str, str]]:
    suite = cache.get("suites", {}).get(suite_name, {})
    clean_hashes = suite.get("last_clean_file_hashes") or {}
    if clean_hashes:
        return suite_name, clean_hashes

    latest_name: str | None = None
    latest_finished_utc = ""
    latest_hashes: dict[str, str] = {}
    for candidate_name, candidate in cache.get("suites", {}).items():
        candidate_hashes = candidate.get("last_clean_file_hashes") or {}
        finished_utc = str((candidate.get("last_clean_run") or {}).get("finished_utc") or "")
        if candidate_hashes and finished_utc > latest_finished_utc:
            latest_name = candidate_name
            latest_finished_utc = finished_utc
            latest_hashes = candidate_hashes
    return latest_name, latest_hashes


def stale_files_for_suite(cache: dict[str, Any], suite_name: str, snapshot: dict[str, dict[str, Any]]) -> list[str]:
    _, clean_hashes = comparison_baseline_for_suite(cache, suite_name)
    stale: list[str] = []
    for path, current in snapshot.items():
        if clean_hashes.get(path) != current["sha256"]:
            stale.append(path)
    for path in clean_hashes:
        if path not in snapshot:
            stale.append(path)
    return sorted(set(stale))


def cache_has_clean_current_suite(
    cache: dict[str, Any],
    suite_name: str,
    command: list[str],
    snapshot: dict[str, dict[str, Any]],
) -> bool:
    suite = cache.get("suites", {}).get(suite_name, {})
    if suite.get("command_key") != command_key(command):
        return False
    if not suite.get("last_clean_run"):
        return False
    return not stale_files_for_suite(cache, suite_name, snapshot)


def update_cache_after_run(
    cache: dict[str, Any],
    *,
    root: Path,
    cache_path: Path,
    suite_name: str,
    command: list[str],
    snapshot: dict[str, dict[str, Any]],
    started_utc: str,
    finished_utc: str,
    duration_seconds: float,
    exit_code: int,
    stale_before_run: list[str],
) -> dict[str, Any]:
    result = "passed" if exit_code == 0 else "failed"
    run_record = {
        "id": hashlib.sha256(f"{started_utc}:{suite_name}:{command_to_text(command)}".encode("utf-8")).hexdigest()[:16],
        "suite": suite_name,
        "command": command,
        "command_text": command_to_text(command),
        "command_key": command_key(command),
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "duration_seconds": round(duration_seconds, 3),
        "exit_code": exit_code,
        "result": result,
        "git": git_state(root),
        "cache_path": repo_relative(cache_path, root) if cache_path.is_relative_to(root) else str(cache_path),
        "tracked_file_count": len(snapshot),
        "stale_file_count_before_run": len(stale_before_run),
        "stale_files_before_run": stale_before_run[:MAX_CHANGED_FILES_IN_RUN],
        "stale_files_truncated": len(stale_before_run) > MAX_CHANGED_FILES_IN_RUN,
    }

    cache["schema_version"] = SCHEMA_VERSION
    cache["updated_utc"] = finished_utc
    cache["tracked_source_dirs"] = list(TRACKED_SOURCE_DIRS)
    cache["tracked_config_files"] = list(TRACKED_CONFIG_FILES)
    cache["dependency_hashes"] = dependency_snapshot(snapshot)

    runs = cache.setdefault("runs", [])
    runs.append(run_record)
    cache["runs"] = runs[-50:]

    suites = cache.setdefault("suites", {})
    suite = suites.setdefault(suite_name, {})
    suite["command"] = command
    suite["command_text"] = command_to_text(command)
    suite["command_key"] = command_key(command)
    suite["last_run"] = run_record
    if exit_code == 0:
        suite["last_clean_run"] = run_record
        suite["last_clean_file_hashes"] = {
            path: data["sha256"]
            for path, data in snapshot.items()
        }
        suite["last_clean_dependency_hashes"] = dependency_snapshot(snapshot)

    files = cache.setdefault("files", {})
    for path, data in snapshot.items():
        file_entry = files.setdefault(path, {})
        file_entry["sha256"] = data["sha256"]
        file_entry["size_bytes"] = data["size_bytes"]
        file_entry["last_tested_utc"] = finished_utc
        file_entry["last_result"] = result
        file_entry["last_suite"] = suite_name
        file_entry["last_command_key"] = command_key(command)
        if exit_code == 0:
            file_entry["last_clean_utc"] = finished_utc
            file_entry["last_clean_sha256"] = data["sha256"]
            file_entry["last_clean_suite"] = suite_name
            file_entry["last_clean_command_key"] = command_key(command)

    return cache


def print_status(cache: dict[str, Any], suite_name: str, command: list[str] | None, snapshot: dict[str, dict[str, Any]]) -> None:
    baseline_name, _ = comparison_baseline_for_suite(cache, suite_name)
    if suite_name not in cache.get("suites", {}):
        print(f"No cached run exists for suite '{suite_name}'.")
        print(f"Tracked source/config files: {len(snapshot)}")
        stale = stale_files_for_suite(cache, suite_name, snapshot)
        print(f"Source snapshot baseline: {baseline_name or 'none'}")
        print(f"Files changed since source snapshot baseline: {len(stale)}")
        return
    stale = stale_files_for_suite(cache, suite_name, snapshot)
    suite = cache["suites"][suite_name]
    last_clean = suite.get("last_clean_run")
    print(f"Suite: {suite_name}")
    print(f"Tracked source/config files: {len(snapshot)}")
    print(f"Last run: {suite.get('last_run', {}).get('finished_utc', 'none')}")
    print(f"Last clean run: {last_clean.get('finished_utc') if last_clean else 'none'}")
    print(f"Source snapshot baseline: {baseline_name or 'none'}")
    if command:
        print(f"Command key: {command_key(command)}")
        print(f"Command matches last cached command: {suite.get('command_key') == command_key(command)}")
    print(f"Files changed since source snapshot baseline: {len(stale)}")
    for path in stale[:20]:
        print(f"  - {path}")
    if len(stale) > 20:
        print(f"  ... {len(stale) - 20} more")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a pytest command and update a source-aware local result cache. "
            "The cache is advisory and must not replace focused tests for security-sensitive work."
        )
    )
    parser.add_argument("--cache-path", default=str(DEFAULT_CACHE_PATH), help="JSON cache path.")
    parser.add_argument("--suite-name", default="default", help="Logical suite name for this command.")
    parser.add_argument("--status", action="store_true", help="Show cache status without running pytest.")
    parser.add_argument("--skip-if-clean", action="store_true", help="Skip pytest when the same command has a clean current cache.")
    parser.add_argument("--allow-non-pytest", action="store_true", help="Allow running a non-pytest command. Intended for maintenance only.")
    parser.add_argument("pytest_command", nargs=argparse.REMAINDER, help="Pytest command after --")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    command = list(args.pytest_command)
    if command and command[0] == "--":
        command = command[1:]

    root = REPO_ROOT
    cache_path = Path(args.cache_path)
    if not cache_path.is_absolute():
        cache_path = root / cache_path

    snapshot = build_file_snapshot(root)
    cache = load_cache(cache_path)

    if args.status:
        print_status(cache, args.suite_name, command or None, snapshot)
        return 0

    if not command:
        print("Missing pytest command. Example:", file=sys.stderr)
        print(
            "  C:/.venv/Scripts/python.exe scripts/testing/update_test_cache.py -- "
            "C:/.venv/Scripts/python.exe -m pytest tests/test_app.py -k \"api_key or mcp\" -q",
            file=sys.stderr,
        )
        return 2

    if not args.allow_non_pytest and not looks_like_pytest(command):
        print("Refusing to run a non-pytest command. Pass --allow-non-pytest only for maintenance.", file=sys.stderr)
        return 2

    baseline_name, _ = comparison_baseline_for_suite(cache, args.suite_name)
    stale_before_run = stale_files_for_suite(cache, args.suite_name, snapshot)
    if args.skip_if_clean and cache_has_clean_current_suite(cache, args.suite_name, command, snapshot):
        now = utc_now()
        cache["updated_utc"] = now
        cache.setdefault("suites", {}).setdefault(args.suite_name, {})["last_checked_utc"] = now
        write_cache(cache_path, cache)
        print(f"Skipped pytest: suite '{args.suite_name}' is clean for the current source hashes.")
        return 0

    print(f"Running pytest cache suite '{args.suite_name}': {command_to_text(command)}", flush=True)
    print(f"Tracked source/config files: {len(snapshot)}", flush=True)
    print(f"Source snapshot baseline: {baseline_name or 'none'}", flush=True)
    print(f"Files changed since source snapshot baseline: {len(stale_before_run)}", flush=True)
    started_utc = utc_now()
    started = time.perf_counter()
    result = subprocess.run(command, cwd=root, check=False)
    duration = time.perf_counter() - started
    finished_utc = utc_now()

    updated = update_cache_after_run(
        cache,
        root=root,
        cache_path=cache_path,
        suite_name=args.suite_name,
        command=command,
        snapshot=snapshot,
        started_utc=started_utc,
        finished_utc=finished_utc,
        duration_seconds=duration,
        exit_code=result.returncode,
        stale_before_run=stale_before_run,
    )
    write_cache(cache_path, updated)
    print(f"Updated cache: {cache_path}")
    print(f"Result: {'PASS' if result.returncode == 0 else 'FAIL'} ({result.returncode})")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
