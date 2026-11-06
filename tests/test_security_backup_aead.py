"""F-033 residual: database backup artifacts must use AES-GCM (PEBAK1) AEAD."""

from __future__ import annotations

import gzip
import sqlite3
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from src.plannededucation.api import backup_service, database


BACKUP_KEY_HEX = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
WRONG_KEY_HEX = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


@pytest.fixture(autouse=True)
def _reset_ephemeral_key(monkeypatch):
    backup_service._EPHEMERAL_BACKUP_KEY = None
    monkeypatch.delenv("BACKUP_MASTER_KEY", raising=False)
    monkeypatch.delenv("ARCHIVE_MASTER_KEY", raising=False)
    monkeypatch.setenv("PLANNED_EDUCATION_ENV", "test")
    yield
    backup_service._EPHEMERAL_BACKUP_KEY = None


def test_encrypt_decrypt_round_trip(monkeypatch):
    monkeypatch.setenv("BACKUP_MASTER_KEY", BACKUP_KEY_HEX)
    key = backup_service.get_backup_master_key(require=True)
    plaintext = b"SQLite format 3\x00" + b"secret-row-data-pii"

    sealed = backup_service.encrypt_backup_bytes(plaintext, key=key)
    assert sealed.startswith(backup_service.BACKUP_MAGIC)
    assert plaintext not in sealed
    assert b"secret-row-data-pii" not in sealed

    restored = backup_service.decrypt_backup_bytes(sealed, key=key)
    assert restored == plaintext


def test_wrong_key_fails_authentication(monkeypatch):
    monkeypatch.setenv("BACKUP_MASTER_KEY", BACKUP_KEY_HEX)
    good = backup_service._parse_master_key_material(BACKUP_KEY_HEX)
    bad = backup_service._parse_master_key_material(WRONG_KEY_HEX)
    sealed = backup_service.encrypt_backup_bytes(b"gzip-payload", key=good)

    with pytest.raises(InvalidTag):
        backup_service.decrypt_backup_bytes(sealed, key=bad)


def test_production_missing_key_fail_closed(monkeypatch):
    monkeypatch.setenv("PLANNED_EDUCATION_ENV", "production")
    monkeypatch.delenv("BACKUP_MASTER_KEY", raising=False)
    monkeypatch.delenv("ARCHIVE_MASTER_KEY", raising=False)

    with pytest.raises(RuntimeError, match="BACKUP_MASTER_KEY"):
        backup_service.get_backup_master_key(require=True)


def test_create_backup_leaves_only_encrypted_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_MASTER_KEY", BACKUP_KEY_HEX)
    monkeypatch.setenv("BACKUP_APPROVED_ROOT", str(tmp_path))
    monkeypatch.setattr(
        backup_service,
        "_load_backup_config",
        lambda: {
            "backup_location": "backups",
            "backup_frequency_days": 1,
            "backup_retention_days": 30,
            "backup_time": "22:00",
        },
    )

    # Isolated SQLite DB with a recognizable credential-like marker
    db_path = tmp_path / "source.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("CREATE TABLE secrets (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute(
            "INSERT INTO secrets(value) VALUES (?)",
            ("postgresql://user:SuperSecretPass@db/prod",),
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(database, "is_sqlite", True)
    monkeypatch.setattr(database, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    result = backup_service.create_database_backup(is_auto=False)
    assert result["status"] == "success"
    assert result["encrypted"] is True
    assert result["filename"].endswith(".db.gz.enc")
    assert result["path"] == result["filename"]
    assert ":" not in result["path"] or not Path(result["path"]).is_absolute()

    bdir = backup_service.get_backup_dir()
    enc_path = bdir / result["filename"]
    assert enc_path.is_file()

    # No plaintext gzip left behind
    plain_candidates = list(bdir.glob("*.db.gz")) + list(bdir.glob("*.tmp.db"))
    assert plain_candidates == []

    raw = enc_path.read_bytes()
    assert raw.startswith(backup_service.BACKUP_MAGIC)
    assert b"SuperSecretPass" not in raw
    assert b"postgresql://" not in raw

    # Round-trip via decrypt helper → gzip → sqlite marker present only after decrypt
    inner_gz = backup_service.decrypt_backup_file(enc_path)
    assert b"SuperSecretPass" not in inner_gz  # still gzip-compressed
    decompressed = gzip.decompress(inner_gz)
    assert b"SuperSecretPass" in decompressed or b"secrets" in decompressed


def test_list_shows_encrypted_names(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_MASTER_KEY", BACKUP_KEY_HEX)
    monkeypatch.setenv("BACKUP_APPROVED_ROOT", str(tmp_path))
    monkeypatch.setattr(
        backup_service,
        "_load_backup_config",
        lambda: {
            "backup_location": "backups",
            "backup_frequency_days": 1,
            "backup_retention_days": 30,
            "backup_time": "22:00",
        },
    )

    bdir = backup_service.get_backup_dir()
    sealed = backup_service.encrypt_backup_bytes(b"fake-gz-bytes")
    (bdir / "backup_manual_20260101_000000.db.gz.enc").write_bytes(sealed)
    # Legacy plaintext should still be listed but flagged
    (bdir / "backup_auto_legacy.sql.gz").write_bytes(b"\x1f\x8blegacy")

    listed = backup_service.list_database_backups()
    names = {item["filename"] for item in listed}
    assert "backup_manual_20260101_000000.db.gz.enc" in names
    enc_entry = next(i for i in listed if i["filename"].endswith(".enc"))
    assert enc_entry["encrypted"] is True

    resolved = backup_service.get_backup_file_path(
        "backup_manual_20260101_000000.db.gz.enc"
    )
    assert resolved is not None
    assert resolved.name.endswith(".db.gz.enc")

    # Path traversal rejected
    assert backup_service.get_backup_file_path("../secrets.env") is None


def test_backup_location_must_stay_under_approved_root(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_MASTER_KEY", BACKUP_KEY_HEX)
    monkeypatch.setenv("BACKUP_APPROVED_ROOT", str(tmp_path / "allowed"))
    (tmp_path / "allowed").mkdir()
    monkeypatch.setattr(
        backup_service,
        "_load_backup_config",
        lambda: {
            "backup_location": str(tmp_path / "outside"),
            "backup_frequency_days": 1,
            "backup_retention_days": 30,
            "backup_time": "22:00",
        },
    )
    with pytest.raises(RuntimeError, match="approved root"):
        backup_service.get_backup_dir()
