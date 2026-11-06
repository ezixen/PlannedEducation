"""
Comprehensive Encryption Layer for PlannedEducation

Provides field-level encryption for sensitive database columns using Fernet (AES-128 CBC + HMAC).
Integrates with SQLAlchemy via event listeners for automatic encrypt/decrypt on model save/load.

Environment Variables:
    DB_ENCRYPTION_MASTER_KEY - Base64-encoded 32-byte master key for field encryption
    DATABASE_ENCRYPTION - Set to "true" (or 1/yes/on) to activate field-level encryption

Generate master key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("plannededucation.db.encryption")

# ── Master Key Configuration ─────────────────────────────────────────────────

_DB_ENCRYPTION_ENABLED = os.getenv("DATABASE_ENCRYPTION", "false").lower() in (
    "true", "1", "yes", "on"
)

_DB_ENCRYPTION_MASTER_KEY = os.getenv("DB_ENCRYPTION_MASTER_KEY", "")
_ENCRYPTION_ENVELOPE_PREFIX = "pe-db-v1$"
_DEPLOYMENT_ENV = os.getenv("PLANNED_EDUCATION_ENV", "production").lower()

if _DEPLOYMENT_ENV in {"production", "staging"} and not _DB_ENCRYPTION_ENABLED:
    raise RuntimeError(
        "DATABASE_ENCRYPTION=true is required in production/staging. "
        "Refusing to start with plaintext sensitive fields."
    )

_db_fernet: Fernet | None = None


def _init_db_fernet() -> None:
    """Initialize the database encryption Fernet instance."""
    global _db_fernet
    if not _DB_ENCRYPTION_ENABLED:
        logger.warning(
            "Database field-level encryption is DISABLED. "
            "Set DATABASE_ENCRYPTION=true to enable."
        )
        return

    if not _DB_ENCRYPTION_MASTER_KEY:
        raise RuntimeError(
            "DATABASE_ENCRYPTION=true but DB_ENCRYPTION_MASTER_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    try:
        _db_fernet = Fernet(_DB_ENCRYPTION_MASTER_KEY.encode())
        logger.info("Database field-level encryption initialized successfully")
    except Exception as e:
        raise RuntimeError(
            f"DB_ENCRYPTION_MASTER_KEY is invalid: {e}"
        ) from e


# Initialize on import
_init_db_fernet()


def is_encryption_enabled() -> bool:
    """Check if database field-level encryption is enabled."""
    return _db_fernet is not None


def encrypt_field(plaintext: str | None) -> str | None:
    """Encrypt a string value for database storage.

    Returns None if plaintext is None/empty. New values use a versioned
    envelope instead of guessing from a Fernet prefix.
    """
    if plaintext is None or plaintext == "":
        return plaintext
    if not _db_fernet:
        return plaintext
    if plaintext.startswith(_ENCRYPTION_ENVELOPE_PREFIX):
        return plaintext
    try:
        encrypted = _db_fernet.encrypt(plaintext.encode("utf-8"))
        return f"{_ENCRYPTION_ENVELOPE_PREFIX}{encrypted.decode('utf-8')}"
    except Exception as e:
        logger.error("Database field encryption failed: %s", type(e).__name__)
        raise


def decrypt_field(ciphertext: str | None) -> str | None:
    """Decrypt a string value from database storage.

    Legacy plaintext values are returned unchanged for the controlled
    re-encryption migration. Invalid ciphertext never falls back to plaintext.
    """
    if ciphertext is None or ciphertext == "":
        return ciphertext
    if not _db_fernet:
        if ciphertext.startswith(_ENCRYPTION_ENVELOPE_PREFIX) or ciphertext.startswith("gAAAA"):
            raise RuntimeError("Encrypted database field cannot be opened without the database key")
        return ciphertext

    token = None
    if ciphertext.startswith(_ENCRYPTION_ENVELOPE_PREFIX):
        token = ciphertext[len(_ENCRYPTION_ENVELOPE_PREFIX):]
    elif ciphertext.startswith("gAAAA"):
        # Compatibility for rows written before the versioned envelope. A
        # malformed legacy token is treated as corruption, never plaintext.
        token = ciphertext
    else:
        return ciphertext

    try:
        decrypted = _db_fernet.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        logger.error("Database field decryption failed: invalid ciphertext or key")
        raise RuntimeError("Encrypted database field failed authentication") from None
    except Exception as e:
        logger.error("Database field decryption failed: %s", type(e).__name__)
        raise


def encrypt_json(data: dict | None) -> str | None:
    """Encrypt a JSON-serializable dict for database storage."""
    if data is None:
        return None
    json_str = json.dumps(data, separators=(",", ":"), sort_keys=True)
    return encrypt_field(json_str)


def decrypt_json(ciphertext: str | None) -> dict | None:
    """Decrypt and parse a JSON string from database storage."""
    if ciphertext is None:
        return None
    json_str = decrypt_field(ciphertext)
    if json_str is None:
        return None
    return json.loads(json_str)


# ── SQLAlchemy Integration ───────────────────────────────────────────────────

def encrypt_model_instance(instance: Any) -> None:
    """Encrypt all encrypted fields on a model instance before save.

    Looks for __encrypted_fields__ attribute on the model class.
    """
    if not _db_fernet:
        return

    encrypted_fields = getattr(instance.__class__, "__encrypted_fields__", set())
    for field_name in encrypted_fields:
        value = getattr(instance, field_name, None)
        if value is not None:
            encrypted = encrypt_field(value)
            setattr(instance, field_name, encrypted)


def decrypt_model_instance(instance: Any) -> None:
    """Decrypt all encrypted fields on a model instance after load.

    Looks for __encrypted_fields__ attribute on the model class.
    Uses set_committed_value so decrypt does not mark the row dirty
    (setattr would re-trigger flush → encrypt → decrypt forever).
    """
    if not _db_fernet:
        return

    from sqlalchemy.orm.attributes import set_committed_value

    encrypted_fields = getattr(instance.__class__, "__encrypted_fields__", set())
    for field_name in encrypted_fields:
        value = getattr(instance, field_name, None)
        if value is not None:
            decrypted = decrypt_field(value)
            if decrypted != value:
                set_committed_value(instance, field_name, decrypted)


_SESSION_DECRYPT_HOOK_REGISTERED = False


def register_encrypted_model(model_class: Any, fields: list[str]) -> None:
    """Register a model class with its encrypted fields.

    Args:
        model_class: The SQLAlchemy model class
        fields: List of field names to encrypt/decrypt automatically
    """
    global _SESSION_DECRYPT_HOOK_REGISTERED
    model_class.__encrypted_fields__ = set(fields)

    # Register event listeners for automatic encrypt/decrypt
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    @event.listens_for(model_class, "before_insert")
    @event.listens_for(model_class, "before_update")
    def _encrypt_before_save(mapper, connection, target):
        encrypt_model_instance(target)

    @event.listens_for(model_class, "load")
    def _decrypt_after_load(target, context):
        decrypt_model_instance(target)

    @event.listens_for(model_class, "refresh")
    def _decrypt_after_refresh(target, context, attrs):
        decrypt_model_instance(target)

    # after_insert alone can be overwritten by INSERT result sync; also decrypt
    # after the flush fully finishes. Always use set_committed_value (in
    # decrypt_model_instance) so we never mark rows dirty / loop flushes.
    @event.listens_for(model_class, "after_insert")
    @event.listens_for(model_class, "after_update")
    def _decrypt_after_save(mapper, connection, target):
        decrypt_model_instance(target)

    if not _SESSION_DECRYPT_HOOK_REGISTERED:
        @event.listens_for(Session, "after_flush_postexec")
        def _decrypt_after_flush(session: Session, flush_context: Any) -> None:
            for obj in session.identity_map.values():
                if getattr(obj.__class__, "__encrypted_fields__", None):
                    decrypt_model_instance(obj)

        _SESSION_DECRYPT_HOOK_REGISTERED = True
