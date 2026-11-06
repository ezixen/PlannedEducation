"""
Archive Utilities for PlannedEducation
Handles compression, encryption, and archive management for exam submissions.
Uses zstd (best free compression) + AES-GCM encryption.
"""

import base64
import hashlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import zstandard as zstd

logger = logging.getLogger(__name__)

# ── Compression ──────────────────────────────────────────────────────────────

# Use zstandard (zstd) - best free compression algorithm
# Level 3 is a good balance of speed/compression for text data
# Level 19 is maximum compression (slower)
DEFAULT_COMPRESSION_LEVEL = 3
MAX_COMPRESSION_LEVEL = 19

def compress_data(data: bytes, level: int = DEFAULT_COMPRESSION_LEVEL) -> bytes:
    """Compress data using zstd."""
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data)

def decompress_data(data: bytes) -> bytes:
    """Decompress zstd data."""
    dctx = zstd.ZstdDecompressor()
    return dctx.decompress(data)

def compress_json(obj: dict, level: int = DEFAULT_COMPRESSION_LEVEL) -> bytes:
    """Compress a JSON object."""
    json_bytes = json.dumps(obj, separators=(',', ':'), sort_keys=True).encode('utf-8')
    return compress_data(json_bytes, level)

def decompress_to_json(data: bytes) -> dict:
    """Decompress to JSON object."""
    json_bytes = decompress_data(data)
    return json.loads(json_bytes.decode('utf-8'))

# ── Archive Path Structure ───────────────────────────────────────────────────

def build_archive_path(
    year: int,
    month: int,
    teacher_username: str,
    student_username: str,
    submission_id: str
) -> str:
    """
    Build archive path: year/month/teacher/student/submission_id.zst.enc
    Example: 2026/01/john_doe/jane_student/abc123.zst.enc
    """
    return f"{year:04d}/{month:02d}/{teacher_username}/{student_username}/{submission_id}.zst.enc"

def parse_archive_path(path: str) -> dict:
    """Parse archive path into components."""
    parts = path.strip('/').split('/')
    if len(parts) != 5:
        raise ValueError(f"Invalid archive path: {path}")
    return {
        'year': int(parts[0]),
        'month': int(parts[1]),
        'teacher_username': parts[2],
        'student_username': parts[3],
        'filename': parts[4],
    }

# ── Archive Encryption ───────────────────────────────────────────────────────

ARCHIVE_ENCRYPTION_ALGORITHM = "AES-GCM"
ARCHIVE_KEY_LENGTH = 256
ARCHIVE_IV_LENGTH = 12
ARCHIVE_SALT_LENGTH = 16

# Process-local fallback for development/test only (never for production/staging).
_EPHEMERAL_ARCHIVE_KEY: bytes | None = None


def get_archive_master_key(*, require: bool = True) -> bytes:
    """
    Load the archive AES master key.

    Preference order:
      1. ARCHIVE_MASTER_KEY — urlsafe-base64 32 bytes, or 64-char hex, or raw 32 bytes
      2. Dev/test ephemeral key (generated once per process)

    Production/staging fail closed when the env key is missing and require=True.
    """
    global _EPHEMERAL_ARCHIVE_KEY

    raw = (os.getenv("ARCHIVE_MASTER_KEY") or "").strip()
    env = (os.getenv("PLANNED_EDUCATION_ENV") or os.getenv("ENVIRONMENT") or "").lower()

    if raw:
        # Fernet-style urlsafe base64 (44 chars) → 32 bytes
        try:
            decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
            if len(decoded) >= 32:
                return decoded[:32]
        except Exception:
            pass
        # Hex (64 chars → 32 bytes)
        try:
            decoded = bytes.fromhex(raw)
            if len(decoded) >= 32:
                return decoded[:32]
        except Exception:
            pass
        # Derive a stable 32-byte key from an arbitrary secret string
        return hashlib.sha256(raw.encode("utf-8")).digest()

    if env in {"production", "staging"}:
        if require:
            raise RuntimeError(
                "ARCHIVE_MASTER_KEY must be set in production/staging for archive encryption."
            )
        raise RuntimeError("ARCHIVE_MASTER_KEY is not configured")

    if _EPHEMERAL_ARCHIVE_KEY is None:
        _EPHEMERAL_ARCHIVE_KEY = os.urandom(32)
        logger.warning(
            "ARCHIVE_MASTER_KEY not set — using ephemeral per-process archive key "
            "(archives will not survive process restart)."
        )
    return _EPHEMERAL_ARCHIVE_KEY


async def encrypt_archive_data(data: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt archive data with AES-GCM.
    Returns: (ciphertext, iv, salt)
    """
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    # Derive key from master key + salt
    salt = os.urandom(ARCHIVE_SALT_LENGTH)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=ARCHIVE_KEY_LENGTH // 8,
        salt=salt,
        iterations=100000,
    )
    derived_key = kdf.derive(key)

    # Encrypt
    aesgcm = AESGCM(derived_key)
    iv = os.urandom(ARCHIVE_IV_LENGTH)
    ciphertext = aesgcm.encrypt(iv, data, None)

    return ciphertext, iv, salt

async def decrypt_archive_data(ciphertext: bytes, iv: bytes, salt: bytes, key: bytes) -> bytes:
    """Decrypt archive data."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=ARCHIVE_KEY_LENGTH // 8,
        salt=salt,
        iterations=100000,
    )
    derived_key = kdf.derive(key)

    aesgcm = AESGCM(derived_key)
    return aesgcm.decrypt(iv, ciphertext, None)

# ── Archive Manager ──────────────────────────────────────────────────────────

class ArchiveManager:
    """Manages archiving of sealed exam submissions."""

    def __init__(self, storage_root: str = "/var/lib/plannededucation/archive"):
        self.storage_root = Path(storage_root)
        try:
            self.storage_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.storage_root = Path(tempfile.gettempdir()) / "plannededucation_archive"
            self.storage_root.mkdir(parents=True, exist_ok=True)

    def get_archive_file_path(self, archive_path: str) -> Path:
        """Get full filesystem path for archive."""
        return self.storage_root / archive_path

    async def archive_submission(
        self,
        sealed_submission: dict,
        teacher_username: str,
        student_username: str,
        compression_level: int = DEFAULT_COMPRESSION_LEVEL,
        master_key: bytes | None = None,
        *,
        require_encryption: bool = True,
    ) -> dict:
        """
        Archive a sealed submission (zstd + AES-GCM).

        F-024: encryption is required by default. When require_encryption is True
        and no master_key is passed, the archive master key is loaded (fail closed
        in production/staging). Returns metadata including the ciphertext hex
        for DB persistence (compressed_data must never store only a hash).
        """
        # Build archive path
        now = datetime.now(UTC)
        year = now.year
        month = now.month

        archive_rel_path = build_archive_path(
            year, month,
            teacher_username, student_username,
            sealed_submission['submissionId']
        )

        # Ensure directory exists
        full_path = self.get_archive_file_path(archive_rel_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize and compress
        json_bytes = json.dumps(
            sealed_submission, separators=(',', ':'), sort_keys=True
        ).encode('utf-8')
        original_size = len(json_bytes)
        compressed = compress_data(json_bytes, compression_level)

        if master_key is None and require_encryption:
            master_key = get_archive_master_key(require=True)

        if master_key:
            encrypted, iv, salt = await encrypt_archive_data(compressed, master_key)
            final_data = encrypted
            encryption_iv = iv.hex()
            encryption_salt = salt.hex()
            encryption_algorithm = ARCHIVE_ENCRYPTION_ALGORITHM
        else:
            # Explicit opt-out only (tests); never claim encryption.
            final_data = compressed
            encryption_iv = ""
            encryption_salt = ""
            encryption_algorithm = "none"

        # Persist ciphertext (hex) to disk
        ciphertext_hex = final_data.hex()
        full_path.write_text(ciphertext_hex)

        content_hash = hashlib.sha256(json_bytes).hexdigest()
        archive_hash = hashlib.sha256(final_data).hexdigest()

        return {
            'archive_path': archive_rel_path,
            'original_size': original_size,
            'compressed_size': len(final_data),
            'compression_ratio': original_size / len(final_data) if len(final_data) > 0 else 0,
            'compression_algorithm': f'zstd-{compression_level}',
            'encryption_algorithm': encryption_algorithm,
            'encryption_iv': encryption_iv,
            'encryption_salt': encryption_salt,
            'content_hash': content_hash,
            'archive_hash': archive_hash,
            # Actual ciphertext for DB compressed_data column (not the hash).
            'compressed_data': ciphertext_hex,
            'archived_at': now.isoformat(),
        }

    async def restore_submission(
        self,
        archive_path: str,
        master_key: bytes | None = None,
        *,
        encryption_algorithm: str | None = None,
        encryption_iv: str | None = None,
        encryption_salt: str | None = None,
        compressed_data_hex: str | None = None,
    ) -> dict:
        """Restore a submission from archive file and/or DB ciphertext."""
        final_data: bytes | None = None

        if compressed_data_hex:
            final_data = bytes.fromhex(compressed_data_hex)
        else:
            full_path = self.get_archive_file_path(archive_path)
            if not full_path.exists():
                raise FileNotFoundError(f"Archive not found: {archive_path}")
            final_data = bytes.fromhex(full_path.read_text())

        algo = (encryption_algorithm or "").strip() or (
            ARCHIVE_ENCRYPTION_ALGORITHM if master_key else "none"
        )

        if algo == ARCHIVE_ENCRYPTION_ALGORITHM:
            if master_key is None:
                master_key = get_archive_master_key(require=True)
            if not encryption_iv or not encryption_salt:
                raise ValueError("Missing encryption_iv/encryption_salt for AES-GCM archive")
            final_data = await decrypt_archive_data(
                final_data,
                bytes.fromhex(encryption_iv),
                bytes.fromhex(encryption_salt),
                master_key,
            )
        elif algo not in {"", "none"}:
            raise ValueError(f"Unsupported archive encryption algorithm: {algo}")

        json_bytes = decompress_data(final_data)
        return json.loads(json_bytes.decode('utf-8'))

    def verify_archive_integrity(self, archive_path: str, expected_hash: str) -> bool:
        """Verify archive file integrity."""
        full_path = self.get_archive_file_path(archive_path)
        if not full_path.exists():
            return False

        final_data_b64 = full_path.read_text()
        final_data = bytes.fromhex(final_data_b64)

        import hashlib
        actual_hash = hashlib.sha256(final_data).hexdigest()
        return actual_hash == expected_hash

    def list_archives(
        self,
        year: int = None,
        month: int = None,
        teacher_username: str = None,
        student_username: str = None
    ) -> list[dict]:
        """List archives with optional filters."""
        results = []

        for year_dir in sorted(self.storage_root.iterdir()):
            if not year_dir.is_dir():
                continue
            if year and int(year_dir.name) != year:
                continue

            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                if month and int(month_dir.name) != month:
                    continue

                for teacher_dir in sorted(month_dir.iterdir()):
                    if not teacher_dir.is_dir():
                        continue
                    if teacher_username and teacher_dir.name != teacher_username:
                        continue

                    for student_dir in sorted(teacher_dir.iterdir()):
                        if not student_dir.is_dir():
                            continue
                        if student_username and student_dir.name != student_username:
                            continue

                        for file in sorted(student_dir.iterdir()):
                            if file.suffix == '.enc':
                                stat = file.stat()
                                mod_iso = datetime.fromtimestamp(stat.st_mtime, UTC).isoformat()
                                results.append({
                                    'path': str(file.relative_to(self.storage_root)),
                                    'year': int(year_dir.name),
                                    'month': int(month_dir.name),
                                    'teacher': teacher_dir.name,
                                    'student': student_dir.name,
                                    'filename': file.name,
                                    'size': stat.st_size,
                                    'modified': mod_iso,
                                })

        return results

    def get_storage_stats(self) -> dict:
        """Get archive storage statistics."""
        total_files = 0
        total_size = 0
        by_year = {}

        for year_dir in sorted(self.storage_root.iterdir()):
            if not year_dir.is_dir():
                continue
            year = int(year_dir.name)
            year_size = 0
            year_files = 0

            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for teacher_dir in month_dir.iterdir():
                    if not teacher_dir.is_dir():
                        continue
                    for student_dir in teacher_dir.iterdir():
                        if not student_dir.is_dir():
                            continue
                        for file in student_dir.iterdir():
                            if file.suffix == '.enc':
                                total_files += 1
                                total_size += file.stat().st_size
                                year_files += 1
                                year_size += file.stat().st_size

            by_year[year] = {'files': year_files, 'size': year_size}

        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'by_year': by_year,
        }


async def reencrypt_legacy_plaintext_row(
    compressed_data_hex: str,
    *,
    master_key: bytes | None = None,
) -> dict:
    """
    F-024 residual: re-encrypt a legacy archive row that used encryption_algorithm=none.

    `compressed_data_hex` is expected to be hex of raw zstd ciphertext (plaintext at rest).
    Returns fields suitable for updating ArchivedSubmission.
    """
    if master_key is None:
        master_key = get_archive_master_key(require=True)

    try:
        plaintext_compressed = bytes.fromhex(compressed_data_hex)
    except ValueError as exc:
        raise ValueError("Legacy archive compressed_data is not valid hex") from exc

    encrypted, iv, salt = await encrypt_archive_data(plaintext_compressed, master_key)
    ciphertext_hex = encrypted.hex()
    return {
        "compressed_data": ciphertext_hex,
        "compressed_size": len(encrypted),
        "encryption_algorithm": ARCHIVE_ENCRYPTION_ALGORITHM,
        "encryption_iv": iv.hex(),
        "encryption_salt": salt.hex(),
        "archive_hash": hashlib.sha256(encrypted).hexdigest(),
        "key_id": "ARCHIVE_MASTER_KEY",
    }


async def migrate_legacy_plaintext_archives(db_session, *, limit: int = 100) -> dict:
    """
    Find ArchivedSubmission rows with encryption_algorithm='none' and re-encrypt them.

    Operator-driven (admin endpoint / ops script). Fail closed if ARCHIVE_MASTER_KEY
    cannot be loaded in production/staging.
    """
    from . import models  # local import avoids circular import at module load

    master_key = get_archive_master_key(require=True)
    rows = (
        db_session.query(models.ArchivedSubmission)
        .filter(models.ArchivedSubmission.encryption_algorithm == "none")
        .limit(max(1, min(limit, 1000)))
        .all()
    )
    migrated = 0
    failed: list[str] = []
    for row in rows:
        try:
            updated = await reencrypt_legacy_plaintext_row(
                row.compressed_data,
                master_key=master_key,
            )
            # Also rewrite on-disk copy when present.
            try:
                mgr = ArchiveManager()
                disk_path = mgr.get_archive_file_path(row.archive_path)
                if disk_path.exists():
                    disk_path.write_text(updated["compressed_data"])
            except OSError as disk_exc:
                logger.warning(
                    "Legacy archive disk rewrite failed for %s: %s",
                    row.id,
                    disk_exc,
                )
            row.compressed_data = updated["compressed_data"]
            row.compressed_size = updated["compressed_size"]
            row.encryption_algorithm = updated["encryption_algorithm"]
            row.encryption_iv = updated["encryption_iv"]
            row.encryption_salt = updated["encryption_salt"]
            row.archive_hash = updated["archive_hash"]
            row.key_id = updated["key_id"]
            migrated += 1
        except Exception as exc:  # noqa: BLE001 — collect per-row failures for ops
            failed.append(f"{row.id}:{type(exc).__name__}")
            logger.error("Legacy archive migrate failed for %s: %s", row.id, exc)

    if migrated:
        db_session.commit()
    return {
        "scanned": len(rows),
        "migrated": migrated,
        "failed": failed,
        "remaining_hint": "Re-run until scanned=0 or migrated=0 with empty failed.",
    }
