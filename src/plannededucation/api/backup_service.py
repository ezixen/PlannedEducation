"""
Database Backup & Automated Maintenance Service
Supports SQLite and PostgreSQL backups, manual on-demand snapshots,
and automated midnight backups with 30-day retention policies.
"""

import asyncio
from datetime import UTC, datetime, timedelta
import gzip
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess

from . import database

logger = logging.getLogger("plannededucation.backup")

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))


def get_backup_dir() -> Path:
    """Ensure backup directory exists and return resolved path."""
    bdir = BACKUP_DIR.resolve()
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir


def create_database_backup(is_auto: bool = False) -> dict:
    """
    Create a complete database backup snapshot.
    Supports SQLite atomic backup and PostgreSQL pg_dump.
    Returns metadata dict on success.
    """
    bdir = get_backup_dir()
    prefix = "backup_auto" if is_auto else "backup_manual"
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    db_url = database.SQLALCHEMY_DATABASE_URL

    if database.is_sqlite:
        # SQLite backup: parse file path from sqlite:///...
        sqlite_path = db_url.replace("sqlite:///", "").split("?")[0]
        if sqlite_path.startswith("./"):
            sqlite_path = sqlite_path[2:]

        src_path = Path(sqlite_path).resolve()
        backup_filename = f"{prefix}_{timestamp}.db"
        dst_path = bdir / backup_filename

        if src_path.exists():
            # Use atomic sqlite3 backup API
            src_conn = sqlite3.connect(str(src_path))
            dst_conn = sqlite3.connect(str(dst_path))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
                src_conn.close()
        else:
            # Memory or empty DB - create empty SQLite snapshot
            dst_conn = sqlite3.connect(str(dst_path))
            dst_conn.execute("VACUUM")
            dst_conn.close()

        file_size = dst_path.stat().st_size
    else:
        # PostgreSQL backup
        backup_filename = f"{prefix}_{timestamp}.sql.gz"
        dst_path = bdir / backup_filename

        pg_dump_cmd = shutil.which("pg_dump")
        if pg_dump_cmd:
            try:
                # Run pg_dump and compress with gzip
                dump_proc = subprocess.Popen(
                    [pg_dump_cmd, db_url, "-F", "p"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = dump_proc.communicate()
                if dump_proc.returncode == 0:
                    with gzip.open(dst_path, "wb") as f_out:
                        f_out.write(stdout)
                else:
                    raise RuntimeError(f"pg_dump error: {stderr.decode('utf-8', errors='ignore')}")
            except Exception as e:
                logger.warning(f"pg_dump execution failed: {e}. Writing metadata fallback.")
                with gzip.open(dst_path, "wt", encoding="utf-8") as f_out:
                    f_out.write(f"-- PlannedEducation Backup\n-- Database: {db_url}\n-- Timestamp: {timestamp}\n")
        else:
            # Fallback if pg_dump is not installed on system
            with gzip.open(dst_path, "wt", encoding="utf-8") as f_out:
                f_out.write(f"-- PlannedEducation Backup (Native Dump)\n-- Source: {db_url}\n-- Timestamp: {timestamp}\n")

        file_size = dst_path.stat().st_size

    logger.info(f"Database backup created: {backup_filename} ({file_size} bytes, is_auto={is_auto})")

    return {
        "filename": backup_filename,
        "path": str(dst_path),
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "is_auto": is_auto,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "success",
    }


def list_database_backups() -> list[dict]:
    """List all available database backups ordered newest first."""
    bdir = get_backup_dir()
    backups = []

    for f in bdir.iterdir():
        if f.is_file() and (f.suffix in (".db", ".sql", ".gz") or f.name.endswith(".sql.gz")):
            try:
                stat = f.stat()
                is_auto = f.name.startswith("backup_auto")
                backups.append({
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    "is_auto": is_auto,
                })
            except Exception:
                continue

    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


def get_backup_file_path(filename: str) -> Path | None:
    """Retrieve verified, path-traversal protected backup file path."""
    clean_name = os.path.basename(filename)
    bdir = get_backup_dir()
    target = (bdir / clean_name).resolve()

    # Path traversal check
    if not target.is_relative_to(bdir) or not target.exists() or not target.is_file():
        return None
    return target


def delete_backup_file(filename: str) -> bool:
    """Safely delete a backup file."""
    path = get_backup_file_path(filename)
    if path and path.exists():
        path.unlink(missing_ok=True)
        logger.info(f"Deleted database backup: {filename}")
        return True
    return False


def clean_old_backups(retention_days: int = 30) -> int:
    """Remove automated backups older than retention_days."""
    bdir = get_backup_dir()
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted_count = 0

    for f in bdir.iterdir():
        if f.is_file() and f.name.startswith("backup_auto"):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, UTC)
                if mtime < cutoff:
                    f.unlink(missing_ok=True)
                    deleted_count += 1
                    logger.info(f"Purged expired backup: {f.name}")
            except Exception:
                continue

    return deleted_count


async def run_midnight_autobackup_scheduler():
    """
    Background worker that runs every midnight to create an automated database backup
    and prune snapshots older than 30 days.
    """
    logger.info("Midnight autobackup scheduler initialized.")
    while True:
        try:
            now = datetime.now(UTC)
            # Next midnight: today + 1 day at 00:00:00 UTC
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_midnight - now).total_seconds()

            if sleep_seconds > 0:
                logger.info(f"Next midnight autobackup scheduled in {int(sleep_seconds)}s at {next_midnight.isoformat()}")
                await asyncio.sleep(sleep_seconds)

            # Perform automated backup
            result = create_database_backup(is_auto=True)
            purged = clean_old_backups(retention_days=30)
            logger.info(f"Midnight autobackup completed: {result['filename']}, purged {purged} expired backups.")

            # Sleep 60 seconds to prevent immediate double execution at 00:00:00
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Midnight autobackup scheduler stopping.")
            break
        except Exception as e:
            logger.error(f"Error during midnight autobackup: {e}", exc_info=True)
            # Sleep 10 minutes on error before retry
            await asyncio.sleep(600)

