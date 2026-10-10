"""In-memory ChatGPT session tokens for teachers. Encrypted at rest in process memory.

Never written to SQL.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

from .crypto import decrypt_json, encrypt_json, token_scope


@dataclass
class ChatGptTokens:
    access_token: str
    refresh_token: str
    account_id: str
    expires_at: float  # unix seconds


@dataclass
class PendingDeviceLogin:
    user_id: str
    device_auth_id: str
    user_code: str
    interval_seconds: float
    created_at: float


@dataclass
class PendingBrowserLogin:
    user_id: str
    oauth_state: str
    code_verifier: str
    redirect_uri: str
    created_at: float


_LOCK = threading.Lock()
_TOKENS: dict[str, bytes] = {}
_PENDING: dict[str, PendingDeviceLogin] = {}
_BROWSER_PENDING: dict[str, PendingBrowserLogin] = {}


def clear_all_for_tests() -> None:
    with _LOCK:
        _TOKENS.clear()
        _PENDING.clear()
        _BROWSER_PENDING.clear()


def _serialize_tokens(tokens: ChatGptTokens) -> dict[str, object]:
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "account_id": tokens.account_id,
        "expires_at": tokens.expires_at,
    }


def _deserialize_tokens(payload: object) -> ChatGptTokens | None:
    if not isinstance(payload, dict):
        return None
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    account_id = payload.get("account_id")
    expires_at = payload.get("expires_at")
    if (
        not isinstance(access, str)
        or not isinstance(refresh, str)
        or not isinstance(account_id, str)
    ):
        return None
    try:
        expires = float(expires_at)
    except (TypeError, ValueError):
        return None
    return ChatGptTokens(
        access_token=access,
        refresh_token=refresh,
        account_id=account_id,
        expires_at=expires,
    )


def put_tokens(user_id: str, tokens: ChatGptTokens) -> None:
    blob = encrypt_json(token_scope(), _serialize_tokens(tokens), user_id=user_id)
    with _LOCK:
        _TOKENS[user_id] = blob


def get_tokens(user_id: str) -> ChatGptTokens | None:
    with _LOCK:
        blob = _TOKENS.get(user_id)
    if blob is None:
        return None
    payload = decrypt_json(token_scope(), blob, user_id=user_id)
    return _deserialize_tokens(payload)


def clear_tokens(user_id: str) -> None:
    with _LOCK:
        _TOKENS.pop(user_id, None)


def create_pending(login: PendingDeviceLogin) -> str:
    login_id = uuid.uuid4().hex
    with _LOCK:
        _PENDING[login_id] = login
    return login_id


def get_pending(login_id: str) -> PendingDeviceLogin | None:
    with _LOCK:
        return _PENDING.get(login_id)


def pop_pending(login_id: str) -> PendingDeviceLogin | None:
    with _LOCK:
        return _PENDING.pop(login_id, None)


def prune_stale_pending(*, max_age_seconds: float = 45 * 60) -> None:
    now = time.time()
    with _LOCK:
        dead = [key for key, value in _PENDING.items() if now - value.created_at > max_age_seconds]
        for key in dead:
            _PENDING.pop(key, None)
        dead_browser = [
            key
            for key, value in _BROWSER_PENDING.items()
            if now - value.created_at > max_age_seconds
        ]
        for key in dead_browser:
            _BROWSER_PENDING.pop(key, None)


def create_browser_pending(login: PendingBrowserLogin) -> str:
    login_id = uuid.uuid4().hex
    with _LOCK:
        _BROWSER_PENDING[login_id] = login
    return login_id


def get_browser_pending(login_id: str) -> PendingBrowserLogin | None:
    with _LOCK:
        return _BROWSER_PENDING.get(login_id)


def pop_browser_pending(login_id: str) -> PendingBrowserLogin | None:
    with _LOCK:
        return _BROWSER_PENDING.pop(login_id, None)
