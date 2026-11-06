"""Versioned, additive schema assurance for SQLite and PostgreSQL.

``create_all`` only creates missing tables; it does not upgrade existing
tables. This module provides a small transactional migration ledger for the
security-critical additive changes currently needed by the application. Any
remaining model/schema drift fails startup instead of being logged and ignored.
Destructive changes and data backfills must be introduced as explicit,
reviewed migrations rather than inferred from ORM metadata.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.schema import MetaData

logger = logging.getLogger("plannededucation.db.schema")

_MIGRATION_TABLE = "schema_migrations"

_USER_COLUMN_UPGRADES: list[tuple[str, str]] = [
    ("is_teacher_aide", "BOOLEAN NOT NULL DEFAULT 0"),
    ("aide_approved_by", "VARCHAR(36)"),
    ("aide_approved_at", "TIMESTAMP"),
    ("allow_student_dms", "BOOLEAN NOT NULL DEFAULT 0"),
    ("is_visible_in_teacher_dm", "BOOLEAN NOT NULL DEFAULT 1"),
    ("is_superadmin", "BOOLEAN NOT NULL DEFAULT 0"),
]


def _existing_columns(connection: Connection, table: str) -> set[str]:
    inspector = inspect(connection)
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _add_columns(
    connection: Connection,
    table: str,
    upgrades: list[tuple[str, str]],
) -> list[str]:
    """Add known columns and raise on any unexpected DDL failure."""
    existing = _existing_columns(connection, table)
    if not existing:
        return []

    added: list[str] = []
    for column_name, column_ddl in upgrades:
        if column_name in existing:
            continue
        connection.execute(
            text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_ddl}")
        )
        added.append(column_name)
        existing.add(column_name)
    return added


def _migration_users(connection: Connection) -> None:
    added = _add_columns(connection, "users", _USER_COLUMN_UPGRADES)
    if "is_superadmin" in added:
        connection.execute(
            text(
                "UPDATE users SET is_superadmin = 1 "
                "WHERE is_admin = 1 AND (is_superadmin = 0 OR is_superadmin IS NULL)"
            )
        )
        logger.info("Schema migration mapped existing administrators to superadmins")


def _migration_exam_and_notification_security(connection: Connection) -> None:
    _add_columns(
        connection,
        "exam_submissions",
        [("deadline_at", "TIMESTAMP")],
    )
    _add_columns(
        connection,
        "answers",
        [
            ("generated_question_text", "TEXT"),
            ("generated_options_json", "TEXT"),
        ],
    )
    _add_columns(
        connection,
        "in_app_notifications",
        [("action_consumed_at", "TIMESTAMP")],
    )


def _migration_reset_security_columns(connection: Connection) -> None:
    # These columns existed in some historical schemas under different
    # versions. Additive assurance keeps upgrades explicit without dropping
    # legacy columns or copying unencrypted secrets automatically.
    added = _add_columns(
        connection,
        "users",
        [
            ("password_reset_otp", "VARCHAR(128)"),
            ("password_reset_otp_expires", "TIMESTAMP"),
            ("recovery_codes", "TEXT"),
            ("reset_token", "VARCHAR(256)"),
            ("force_password_reset", "BOOLEAN NOT NULL DEFAULT 0"),
            ("reset_by_teacher_id", "VARCHAR(36)"),
            ("reset_by_parent_id", "VARCHAR(36)"),
            ("reset_by_admin_id", "VARCHAR(36)"),
            ("reset_expires", "TIMESTAMP"),
            ("ai_api_key_encrypted", "TEXT"),
            ("ai_model_name", "VARCHAR(128)"),
            ("ai_base_url", "VARCHAR(512)"),
        ],
    )
    # Older deployments used ``ai_api_key``. Copy it only through the current
    # Fernet service, then clear the legacy plaintext column. If the dedicated
    # AI key is unavailable, abort the migration rather than preserving secret
    # material or pretending the transform succeeded.
    existing = _existing_columns(connection, "users")
    if "ai_api_key" in existing and "ai_api_key_encrypted" in added:
        from . import crypto

        rows = connection.execute(
            text("SELECT id, ai_api_key FROM users WHERE ai_api_key IS NOT NULL")
        ).fetchall()
        for user_id, legacy_key in rows:
            encrypted_key = crypto.encrypt_api_key(str(legacy_key))
            if not encrypted_key:
                raise RuntimeError(
                    "Legacy ai_api_key values require AI_KEY_MASTER_SECRET for migration"
                )
            connection.execute(
                text(
                    "UPDATE users SET ai_api_key_encrypted = :encrypted_key "
                    "WHERE id = :user_id"
                ),
                {"encrypted_key": encrypted_key, "user_id": user_id},
            )
        if rows:
            connection.execute(text("UPDATE users SET ai_api_key = NULL"))
            logger.info("Migrated legacy AI keys into encrypted storage")


def _migration_refresh_sessions(connection: Connection) -> None:
    """F-049: per-device refresh sessions with rotation families."""
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS refresh_sessions ("
            "id VARCHAR(36) NOT NULL PRIMARY KEY, "
            "user_id VARCHAR(36) NOT NULL, "
            "token_hash VARCHAR(256) NOT NULL, "
            "family_id VARCHAR(36) NOT NULL, "
            "device_label VARCHAR(128), "
            "created_at TIMESTAMP NOT NULL, "
            "expires_at TIMESTAMP NOT NULL, "
            "revoked_at TIMESTAMP, "
            "replaced_by VARCHAR(36), "
            "FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE"
            ")"
        )
    )
    # Indexes are additive and idempotent across SQLite/PostgreSQL.
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_refresh_sessions_user_id "
        "ON refresh_sessions (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_sessions_token_hash "
        "ON refresh_sessions (token_hash)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_sessions_family_id "
        "ON refresh_sessions (family_id)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_sessions_token_hash_user_id "
        "ON refresh_sessions (token_hash, user_id)",
        "CREATE INDEX IF NOT EXISTS ix_refresh_sessions_id "
        "ON refresh_sessions (id)",
    ):
        connection.execute(text(statement))


def _migration_sealed_sync_submissions(connection: Connection) -> None:
    """F-048: sealed offline sync store for three-way submission copies."""
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS sealed_sync_submissions ("
            "id VARCHAR(36) NOT NULL PRIMARY KEY, "
            "exam_id VARCHAR(36) NOT NULL, "
            "student_id VARCHAR(36) NOT NULL, "
            "content_hash VARCHAR(128) NOT NULL, "
            "sync_hash VARCHAR(128) NOT NULL, "
            "payload_json TEXT NOT NULL, "
            "payload_bytes INTEGER NOT NULL, "
            "created_at TIMESTAMP NOT NULL, "
            "updated_at TIMESTAMP NOT NULL, "
            "FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE, "
            "FOREIGN KEY(student_id) REFERENCES users (id) ON DELETE CASCADE"
            ")"
        )
    )
    for statement in (
        "CREATE INDEX IF NOT EXISTS ix_sealed_sync_submissions_exam_id "
        "ON sealed_sync_submissions (exam_id)",
        "CREATE INDEX IF NOT EXISTS ix_sealed_sync_submissions_student_id "
        "ON sealed_sync_submissions (student_id)",
        "CREATE INDEX IF NOT EXISTS ix_sealed_sync_submissions_id "
        "ON sealed_sync_submissions (id)",
    ):
        connection.execute(text(statement))


def _migration_home_exam_flag(connection: Connection) -> None:
    """Optional home-exam proctoring per exam (classroom default OFF)."""
    _add_columns(
        connection,
        "exams",
        [("home_exam_enabled", "BOOLEAN NOT NULL DEFAULT 0")],
    )


Migration = tuple[int, str, Callable[[Connection], None]]
_MIGRATIONS: tuple[Migration, ...] = (
    (1, "users-admin-and-messaging-columns", _migration_users),
    (2, "exam-deadlines-answer-fields-and-notification-actions", _migration_exam_and_notification_security),
    (3, "password-reset-security-columns", _migration_reset_security_columns),
    (4, "refresh-sessions-per-device", _migration_refresh_sessions),
    (5, "sealed-sync-submissions", _migration_sealed_sync_submissions),
    (6, "home-exam-enabled-column", _migration_home_exam_flag),
)


def _ensure_migration_table(connection: Connection) -> None:
    # Table name is a module constant (not user input); keep SQL literal for Bandit B608.
    assert _MIGRATION_TABLE == "schema_migrations"
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "name VARCHAR(128) NOT NULL, "
            "applied_at TIMESTAMP NOT NULL)"
        )
    )


def _applied_versions(connection: Connection) -> set[int]:
    assert _MIGRATION_TABLE == "schema_migrations"
    return {
        int(row[0])
        for row in connection.execute(
            text("SELECT version FROM schema_migrations")
        ).fetchall()
    }


def _validate_model_schema(engine: Engine, metadata: MetaData) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing: list[str] = []
    for table_name, table in metadata.tables.items():
        if table_name not in tables:
            missing.append(f"{table_name} (table)")
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name not in actual_columns:
                missing.append(f"{table_name}.{column.name}")
    if missing:
        raise RuntimeError(
            "Database schema is missing required migrated objects: "
            + ", ".join(sorted(missing))
        )


def ensure_schema(engine: Engine, metadata: MetaData | None = None) -> None:
    """Apply pending migrations transactionally and fail closed on drift."""
    if metadata is None:
        # Delayed import avoids a database/models import cycle for callers that
        # use this helper from installer scripts.
        from .database import Base

        metadata = Base.metadata

    with engine.begin() as connection:
        _ensure_migration_table(connection)
        applied = _applied_versions(connection)
        for version, name, migration in _MIGRATIONS:
            if version in applied:
                continue
            migration(connection)
            connection.execute(
                text(
                    "INSERT INTO schema_migrations "
                    "(version, name, applied_at) VALUES (:version, :name, CURRENT_TIMESTAMP)"
                ),
                {"version": version, "name": name},
            )
            logger.info("Applied schema migration %s: %s", version, name)

    _validate_model_schema(engine, metadata)
