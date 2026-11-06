"""
Lightweight additive schema upgrades for SQLite / PostgreSQL.

SQLAlchemy ``create_all`` creates missing *tables* but never adds new *columns*
to existing tables. Installers and upgrades therefore call ``ensure_schema()``
after ``create_all`` so older databases pick up aide / messaging columns.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger("plannededucation.db.schema")

# Additive-only column upgrades. Never rename/drop here.
_USER_COLUMN_UPGRADES: list[tuple[str, str]] = [
    ("is_teacher_aide", "BOOLEAN NOT NULL DEFAULT 0"),
    ("aide_approved_by", "VARCHAR(36)"),
    ("aide_approved_at", "TIMESTAMP"),
    ("allow_student_dms", "BOOLEAN NOT NULL DEFAULT 0"),
    ("is_visible_in_teacher_dm", "BOOLEAN NOT NULL DEFAULT 1"),
]


def _existing_columns(engine: Engine, table: str) -> set[str]:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return set()
    return {col["name"] for col in insp.get_columns(table)}


def ensure_schema(engine: Engine) -> None:
    """Add any missing columns required by the current models (idempotent)."""
    dialect = engine.dialect.name
    existing = _existing_columns(engine, "users")
    if not existing:
        # Table not created yet — create_all will handle a fresh schema.
        return

    added: list[str] = []
    with engine.begin() as conn:
        for col_name, col_ddl in _USER_COLUMN_UPGRADES:
            if col_name in existing:
                continue
            # SQLite and PostgreSQL both accept ADD COLUMN for these types.
            sql = f"ALTER TABLE users ADD COLUMN {col_name} {col_ddl}"
            try:
                conn.execute(text(sql))
                added.append(col_name)
            except Exception as exc:  # noqa: BLE001 — log and continue; next boot retries
                logger.warning(
                    "Could not add users.%s (%s dialect): %s",
                    col_name,
                    dialect,
                    exc,
                )

    if added:
        logger.info("Schema ensure added users columns: %s", ", ".join(added))
    else:
        logger.debug("Schema ensure: users table already up to date")
