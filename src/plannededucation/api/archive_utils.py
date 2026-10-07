"""
Archive Utilities for PlannedEducation
Handles compression, encryption, and archive management for exam submissions.
Uses zstd (best free compression) + AES-GCM encryption.
"""

import json
import lzma
import os
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import zstandard as zstd

from . import crypto

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

async def encrypt_archive_data(data: bytes, key: bytes) -> tuple[bytes, bytes, bytes]:
    """
    Encrypt archive data with AES-GCM.
    Returns: (ciphertext, iv, salt)
    """
    import hashlib
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
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
    import hashlib
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
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
        master_key: bytes = None
    ) -> dict:
        """
        Archive a sealed submission.
        Returns archive metadata.
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
        json_bytes = json.dumps(sealed_submission, separators=(',', ':'), sort_keys=True).encode('utf-8')
        original_size = len(json_bytes)
        compressed = compress_data(json_bytes, compression_level)
        compressed_size = len(compressed)
        
        # Encrypt if master key provided
        if master_key:
            encrypted, iv, salt = await encrypt_archive_data(compressed, master_key)
            final_data = encrypted
            encryption_iv = iv.hex()
            encryption_salt = salt.hex()
        else:
            final_data = compressed
            encryption_iv = ""
            encryption_salt = ""
        
        # Write to file
        final_data_b64 = final_data.hex()  # Store as hex for simplicity
        full_path.write_text(final_data_b64)
        
        # Compute hashes
        import hashlib
        content_hash = hashlib.sha256(json_bytes).hexdigest()
        archive_hash = hashlib.sha256(final_data).hexdigest()
        
        return {
            'archive_path': archive_rel_path,
            'original_size': original_size,
            'compressed_size': len(final_data),
            'compression_ratio': original_size / len(final_data) if len(final_data) > 0 else 0,
            'compression_algorithm': f'zstd-{compression_level}',
            'encryption_algorithm': 'AES-GCM' if master_key else 'none',
            'encryption_iv': encryption_iv,
            'encryption_salt': encryption_salt,
            'content_hash': content_hash,
            'archive_hash': archive_hash,
            'archived_at': now.isoformat(),
        }
    
    async def restore_submission(
        self,
        archive_path: str,
        master_key: bytes = None
    ) -> dict:
        """Restore a submission from archive."""
        full_path = self.get_archive_file_path(archive_path)
        if not full_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")
        
        # Read file
        final_data_b64 = full_path.read_text()
        final_data = bytes.fromhex(final_data_b64)
        
        # Decrypt if needed
        if master_key:
            # Parse path to get IV and salt from metadata (would need to be stored)
            # For now, assume metadata is stored separately
            pass
        
        # Decompress
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
                                results.append({
                                    'path': str(file.relative_to(self.storage_root)),
                                    'year': int(year_dir.name),
                                    'month': int(month_dir.name),
                                    'teacher': teacher_dir.name,
                                    'student': student_dir.name,
                                    'filename': file.name,
                                    'size': file.stat().st_size,
                                    'modified': datetime.fromtimestamp(file.stat().st_mtime, UTC).isoformat(),
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