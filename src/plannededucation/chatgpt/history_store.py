"""Encrypted in-memory ChatGPT chat history per teacher. Never stored in SQL."""

from __future__ import annotations

import threading

from .crypto import decrypt_json, encrypt_json, history_scope

_MAX_MESSAGES = 100
_MAX_CONTENT_LEN = 10_000
_LOCK = threading.Lock()
_STORE: dict[str, bytes] = {}


def clear_all_for_tests() -> None:
    with _LOCK:
        _STORE.clear()


def clear_history(user_id: str) -> None:
    with _LOCK:
        _STORE.pop(user_id, None)


def _normalize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in messages[-_MAX_MESSAGES:]:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        if len(content) > _MAX_CONTENT_LEN:
            content = content[:_MAX_CONTENT_LEN]
        normalized.append({"role": role, "content": content})
    return normalized


def get_history(user_id: str) -> list[dict[str, str]]:
    with _LOCK:
        blob = _STORE.get(user_id)
    if not blob:
        return []
    payload = decrypt_json(history_scope(), blob, user_id=user_id)
    if not isinstance(payload, list):
        return []
    return _normalize_messages([item for item in payload if isinstance(item, dict)])


def replace_history(user_id: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized = _normalize_messages(messages)
    blob = encrypt_json(history_scope(), normalized, user_id=user_id)
    with _LOCK:
        _STORE[user_id] = blob
    return normalized


def append_exchange(
    user_id: str, *, user_message: str, assistant_message: str
) -> list[dict[str, str]]:
    history = get_history(user_id)
    user_text = user_message.strip()
    assistant_text = assistant_message.strip()
    if not user_text or not assistant_text:
        return history
    history.extend(
        [
            {"role": "user", "content": user_text[:_MAX_CONTENT_LEN]},
            {"role": "assistant", "content": assistant_text[:_MAX_CONTENT_LEN]},
        ]
    )
    return replace_history(user_id, history)
