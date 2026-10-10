"""Fernet helpers for ChatGPT gate secrets and history (at-rest encryption in memory)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

_SCOPE_TOKENS = "chatgpt:tokens"
_SCOPE_HISTORY = "chatgpt:history"

# Ephemeral fallback secret for local development / testing when env secret is not set
_EPHEMERAL_SECRET = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")


class ChatGptCryptoError(Exception):
    """Raised when ChatGPT secrets cannot be encrypted or decrypted safely."""


def _settings_secret() -> str:
    return (
        os.getenv("AI_KEY_MASTER_SECRET")
        or os.getenv("SECRET_KEY")
        or os.getenv("JWT_SECRET_KEY")
        or _EPHEMERAL_SECRET
    )


def fernet_for_scope(scope: str, *, user_id: str | None = None) -> Fernet:
    secret = _settings_secret()
    material = f"{secret}:{scope}"
    if user_id is not None:
        material = f"{material}:{user_id}"
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_bytes(
    scope: str,
    raw: bytes,
    *,
    user_id: str | None = None,
) -> bytes:
    fernet = fernet_for_scope(scope, user_id=user_id)
    return fernet.encrypt(raw)


def decrypt_bytes(scope: str, raw: bytes, *, user_id: str | None = None) -> bytes:
    fernet = fernet_for_scope(scope, user_id=user_id)
    try:
        return fernet.decrypt(raw)
    except InvalidToken as exc:
        raise ChatGptCryptoError("ChatGPT encrypted blob could not be decrypted.") from exc


def encrypt_json(
    scope: str,
    payload: Any,
    *,
    user_id: str | None = None,
) -> bytes:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return encrypt_bytes(scope, raw, user_id=user_id)


def decrypt_json(scope: str, raw: bytes, *, user_id: str | None = None) -> Any:
    decoded = decrypt_bytes(scope, raw, user_id=user_id)
    return json.loads(decoded.decode("utf-8"))


def token_scope() -> str:
    return _SCOPE_TOKENS


def history_scope() -> str:
    return _SCOPE_HISTORY
