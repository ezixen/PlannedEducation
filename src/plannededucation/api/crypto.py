import os
import base64
from cryptography.fernet import Fernet, InvalidToken


# ── AI Key Encryption ────────────────────────────────────────────────────────
# The master key is a URL-safe base64-encoded 32-byte key, stored in environment.
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_AI_KEY_MASTER = os.getenv("AI_KEY_MASTER_SECRET", "")
_fernet: Fernet | None = None

if _AI_KEY_MASTER:
    try:
        _fernet = Fernet(_AI_KEY_MASTER.encode())
    except Exception:
        raise RuntimeError(
            "AI_KEY_MASTER_SECRET is set but is not a valid Fernet key. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
elif os.getenv("PLANNED_EDUCATION_ENV") == "development":
    # In dev, generate a per-process ephemeral key (no persistence needed)
    _fernet = Fernet(Fernet.generate_key())
# In production without AI_KEY_MASTER_SECRET, AI key storage is disabled (fernet=None)


def encrypt_api_key(plain: str) -> str | None:
    """Encrypt a user-provided API key before storing in the database."""
    if not _fernet or not plain:
        return None
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_api_key(encrypted: str | None) -> str | None:
    """Decrypt a stored API key for use in an outbound API call."""
    if not _fernet or not encrypted:
        return None
    try:
        return _fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None  # Key was rotated or data is corrupt

