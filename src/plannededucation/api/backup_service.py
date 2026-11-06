"""
Database Backup & Automated Maintenance Service
Supports SQLite and PostgreSQL backups, manual on-demand snapshots,
and automated midnight backups with 30-day retention policies.

F-033: Final backup artifacts are AES-GCM encrypted (PEBAK1 envelope).
Plaintext gzip dumps are never left as the durable artifact.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import hashlib
import logging
import os
import shutil
import sqlite3
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from . import database
from .deployment_config import load_deployment_config

logger = logging.getLogger("plannededucation.backup")

BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))

# PEBAK1 envelope: magic(6) + salt(16) + iv(12) + ciphertext(+GCM tag)
BACKUP_MAGIC = b"PEBAK1"
BACKUP_SALT_LENGTH = 16
BACKUP_IV_LENGTH = 12
BACKUP_KEY_LENGTH = 32
BACKUP_PBKDF2_ITERATIONS = 100_000

_EPHEMERAL_BACKUP_KEY: bytes | None = None

_ENCRYPTED_SUFFIXES = (".db.gz.enc", ".sql.gz.enc")
_LEGACY_PLAIN_SUFFIXES = (".db.gz", ".sql.gz", ".db", ".sql")


def _parse_master_key_material(raw: str) -> bytes:
    """Normalize urlsafe-b64 / hex / arbitrary secret into a 32-byte key."""
    raw = raw.strip()
    try:
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
        if len(decoded) >= 32:
            return decoded[:32]
    except Exception:
        pass
    try:
        decoded = bytes.fromhex(raw)
        if len(decoded) >= 32:
            return decoded[:32]
    except Exception:
        pass
    return hashlib.sha256(raw.encode("utf-8")).digest()


def get_backup_master_key(*, require: bool = True) -> bytes:
    """
    Load the backup AES-GCM master key.

    Preference order:
      1. BACKUP_MASTER_KEY — dedicated key (preferred)
      2. ARCHIVE_MASTER_KEY — documented fallback for test/dev only
      3. Ephemeral per-process key (test/dev only)

    Production/staging fail closed when no durable key is configured.
    """
    global _EPHEMERAL_BACKUP_KEY

    env = (os.getenv("PLANNED_EDUCATION_ENV") or os.getenv("ENVIRONMENT") or "").lower()
    backup_raw = (os.getenv("BACKUP_MASTER_KEY") or "").strip()
    if backup_raw:
        return _parse_master_key_material(backup_raw)

    archive_raw = (os.getenv("ARCHIVE_MASTER_KEY") or "").strip()
    if archive_raw and env not in {"production", "staging"}:
        logger.warning(
            "BACKUP_MASTER_KEY unset — using ARCHIVE_MASTER_KEY for backup AEAD "
            "(set a distinct BACKUP_MASTER_KEY in production)."
        )
        return _parse_master_key_material(archive_raw)

    if env in {"production", "staging"}:
        if require:
            raise RuntimeError(
                "BACKUP_MASTER_KEY must be set in production/staging for backup encryption."
            )
        raise RuntimeError("BACKUP_MASTER_KEY is not configured")

    if _EPHEMERAL_BACKUP_KEY is None:
        _EPHEMERAL_BACKUP_KEY = os.urandom(32)
        logger.warning(
            "BACKUP_MASTER_KEY not set — using ephemeral per-process backup key "
            "(encrypted backups will not decrypt after process restart)."
        )
    return _EPHEMERAL_BACKUP_KEY


def encrypt_backup_bytes(plaintext: bytes, key: bytes | None = None) -> bytes:
    """
    Encrypt plaintext with AES-GCM into a PEBAK1 single-file envelope.
    Layout: magic(6) + salt(16) + iv(12) + ciphertext(+tag).
    """
    if key is None:
        key = get_backup_master_key(require=True)

    salt = os.urandom(BACKUP_SALT_LENGTH)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=BACKUP_KEY_LENGTH,
        salt=salt,
        iterations=BACKUP_PBKDF2_ITERATIONS,
    )
    derived = kdf.derive(key)
    iv = os.urandom(BACKUP_IV_LENGTH)
    ciphertext = AESGCM(derived).encrypt(iv, plaintext, None)
    return BACKUP_MAGIC + salt + iv + ciphertext


def decrypt_backup_bytes(blob: bytes, key: bytes | None = None) -> bytes:
    """Decrypt a PEBAK1 envelope; raises on wrong key / tampered ciphertext."""
    if key is None:
        key = get_backup_master_key(require=True)

    if len(blob) < 6 + BACKUP_SALT_LENGTH + BACKUP_IV_LENGTH + 16:
        raise ValueError("Backup artifact too short for PEBAK1 envelope")
    if not blob.startswith(BACKUP_MAGIC):
        raise ValueError("Invalid backup magic; expected PEBAK1 encrypted artifact")

    salt = blob[6 : 6 + BACKUP_SALT_LENGTH]
    iv_start = 6 + BACKUP_SALT_LENGTH
    iv = blob[iv_start : iv_start + BACKUP_IV_LENGTH]
    ciphertext = blob[iv_start + BACKUP_IV_LENGTH :]

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=BACKUP_KEY_LENGTH,
        salt=salt,
        iterations=BACKUP_PBKDF2_ITERATIONS,
    )
    derived = kdf.derive(key)
    return AESGCM(derived).decrypt(iv, ciphertext, None)


def _approved_backup_root() -> Path:
    """Root under which backup_location must resolve (path containment)."""
    raw = (os.getenv("BACKUP_APPROVED_ROOT") or "").strip()
    if raw:
        return Path(raw).resolve()
    return Path.cwd().resolve()


def _load_backup_config() -> dict:
    """Load backup configuration from deployment config."""
    try:
        config = load_deployment_config()
        return {
            "backup_location": config.get("backup_location", "backups"),
            "backup_frequency_days": config.get("backup_frequency_days", 1),
            "backup_retention_days": config.get("backup_retention_days", 30),
            "backup_time": config.get("backup_time", "22:00"),
        }
    except Exception:
        return {
            "backup_location": "backups",
            "backup_frequency_days": 1,
            "backup_retention_days": 30,
            "backup_time": "22:00",
        }


def get_backup_dir() -> Path:
    """
    Ensure backup directory exists and return resolved path.

    Restricts backup_location under BACKUP_APPROVED_ROOT (default: cwd)
    so admin-configurable paths cannot escape an approved root.
    """
    cfg = _load_backup_config()
    location = Path(cfg["backup_location"])
    root = _approved_backup_root()
    if not location.is_absolute():
        bdir = (root / location).resolve()
    else:
        bdir = location.resolve()

    if not bdir.is_relative_to(root):
        raise RuntimeError(
            f"backup_location must resolve under approved root {root}; got {bdir}"
        )

    bdir.mkdir(parents=True, exist_ok=True)
    return bdir


def _gzip_compress_file(src_path: Path, dst_path: Path, compress_level: int = 9) -> None:
    """Compress a file with gzip at the given compression level (1-9)."""
    with open(src_path, "rb") as f_in, gzip.open(dst_path, "wb", compresslevel=compress_level) as f_out:
        f_out.write(f_in.read())


def _seal_gzip_artifact(plain_gz: Path) -> Path:
    """
    Encrypt a temporary .gz dump into a durable .gz.enc PEBAK1 file and
    remove the plaintext gzip so it is never left as the final artifact.
    """
    plaintext = plain_gz.read_bytes()
    sealed = encrypt_backup_bytes(plaintext)
    enc_path = Path(str(plain_gz) + ".enc")
    enc_path.write_bytes(sealed)
    # Best-effort wipe then unlink plaintext gzip
    try:
        with open(plain_gz, "wb") as fh:
            fh.write(b"\x00" * len(plaintext))
    except Exception:
        pass
    plain_gz.unlink(missing_ok=True)
    return enc_path


def decrypt_backup_file(path: Path, key: bytes | None = None) -> bytes:
    """
    Decrypt an encrypted backup artifact to its inner gzip (or raw) bytes.
    Legacy plaintext .gz/.db/.sql files are returned as-is for restore migration.
    """
    data = path.read_bytes()
    name = path.name
    if name.endswith(_ENCRYPTED_SUFFIXES) or data.startswith(BACKUP_MAGIC):
        return decrypt_backup_bytes(data, key=key)
    # Legacy unencrypted artifact (pre-F-033 residual)
    return data


def create_database_backup(is_auto: bool = False) -> dict:
    """
    Create a complete database backup snapshot.
    Supports SQLite atomic backup and PostgreSQL pg_dump.
    Final artifact is always AES-GCM encrypted (.db.gz.enc / .sql.gz.enc).
    Returns metadata dict on success.
    """
    # Fail closed early if production/staging lacks a key
    get_backup_master_key(require=True)

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
        plain_filename = f"{prefix}_{timestamp}.db.gz"
        plain_path = bdir / plain_filename
        tmp_path = bdir / f"{prefix}_{timestamp}.tmp.db"

        if src_path.exists():
            # Use atomic sqlite3 backup API to a temp file, then gzip compress
            src_conn = sqlite3.connect(str(src_path))
            tmp_conn = sqlite3.connect(str(tmp_path))
            try:
                src_conn.backup(tmp_conn)
            finally:
                tmp_conn.close()
                src_conn.close()
            _gzip_compress_file(tmp_path, plain_path, compress_level=9)
            tmp_path.unlink(missing_ok=True)
        else:
            # Memory or empty DB - create empty SQLite snapshot then compress
            tmp_conn = sqlite3.connect(str(tmp_path))
            try:
                tmp_conn.execute("VACUUM")
            finally:
                tmp_conn.close()
            _gzip_compress_file(tmp_path, plain_path, compress_level=9)
            tmp_path.unlink(missing_ok=True)

        enc_path = _seal_gzip_artifact(plain_path)
        backup_filename = enc_path.name
        file_size = enc_path.stat().st_size
    else:
        # PostgreSQL backup
        plain_filename = f"{prefix}_{timestamp}.sql.gz"
        plain_path = bdir / plain_filename

        pg_dump_cmd = shutil.which("pg_dump")
        if pg_dump_cmd:
            try:
                dump_proc = subprocess.Popen(
                    [pg_dump_cmd, db_url, "-F", "p"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, stderr = dump_proc.communicate()
                if dump_proc.returncode == 0:
                    with gzip.open(plain_path, "wb", compresslevel=9) as f_out:
                        f_out.write(stdout)
                else:
                    raise RuntimeError(
                        f"pg_dump error: {stderr.decode('utf-8', errors='ignore')}"
                    )
            except Exception as e:
                # F-033: never write DATABASE_URL/credentials into a fallback artifact.
                logger.error("pg_dump execution failed; refusing insecure fallback: %s", e)
                raise RuntimeError(
                    "PostgreSQL backup failed and insecure credential fallback is disabled"
                ) from e
        else:
            raise RuntimeError(
                "pg_dump is not installed; refusing to create a credential-bearing fallback backup"
            )

        enc_path = _seal_gzip_artifact(plain_path)
        backup_filename = enc_path.name
        file_size = enc_path.stat().st_size

    logger.info(
        "Database backup created: %s (%s bytes, is_auto=%s, aead=PEBAK1)",
        backup_filename,
        file_size,
        is_auto,
    )

    return {
        "filename": backup_filename,
        # Do not expose absolute server paths to API clients.
        "path": backup_filename,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "is_auto": is_auto,
        "encrypted": True,
        "encryption": "AES-GCM",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "success",
    }


def _is_backup_artifact(name: str) -> bool:
    """True if filename looks like a (encrypted or legacy) database backup."""
    lower = name.lower()
    if any(lower.endswith(sfx) for sfx in _ENCRYPTED_SUFFIXES):
        return True
    if any(lower.endswith(sfx) for sfx in _LEGACY_PLAIN_SUFFIXES):
        return True
    return False


def list_database_backups() -> list[dict]:
    """List all available database backups ordered newest first."""
    bdir = get_backup_dir()
    backups: list[dict] = []

    for f in bdir.iterdir():
        if f.is_file() and _is_backup_artifact(f.name):
            try:
                stat = f.stat()
                is_auto = f.name.startswith("backup_auto")
                encrypted = f.name.endswith(".enc")
                backups.append({
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    "is_auto": is_auto,
                    "encrypted": encrypted,
                })
            except Exception:
                continue

    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


def get_backup_file_path(filename: str) -> Path | None:
    """Retrieve verified, path-traversal protected backup file path."""
    clean_name = os.path.basename(filename)
    if not _is_backup_artifact(clean_name):
        return None
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


def clean_old_backups(retention_days: int | None = None) -> int:
    """Remove automated backups older than retention_days."""
    if retention_days is None:
        cfg = _load_backup_config()
        retention_days = cfg["backup_retention_days"]
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
    Background worker that runs at the configured time to create an automated database backup
    and prune snapshots older than the configured retention period.
    """
    logger.info("Autobackup scheduler initialized.")
    while True:
        try:
            cfg = _load_backup_config()
            frequency_days = cfg["backup_frequency_days"]
            backup_time_str = cfg["backup_time"]

            # Parse the configured backup time (HH:MM)
            hour, minute = map(int, backup_time_str.split(":"))

            now = datetime.now(UTC)
            # Next occurrence of the configured time today
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                # Already passed today, schedule for tomorrow
                next_run = next_run + timedelta(days=frequency_days)

            sleep_seconds = (next_run - now).total_seconds()

            if sleep_seconds > 0:
                logger.info(f"Next autobackup scheduled in {int(sleep_seconds)}s at {next_run.isoformat()}")
                await asyncio.sleep(sleep_seconds)

            # Perform automated backup
            result = create_database_backup(is_auto=True)
            purged = clean_old_backups()
            logger.info(f"Autobackup completed: {result['filename']}, purged {purged} expired backups.")

            # Sleep 60 seconds to prevent immediate double execution
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Midnight autobackup scheduler stopping.")
            break
        except Exception as e:
            logger.error(f"Error during midnight autobackup: {e}", exc_info=True)
            # Sleep 10 minutes on error before retry
            await asyncio.sleep(600)
