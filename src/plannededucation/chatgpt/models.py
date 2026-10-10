"""Live Codex model discovery for ChatGPT-login."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

import httpx

from .client import DEFAULT_MODEL, USER_AGENT, upstream_error_message
from .oauth import ORIGINATOR, ChatGptOAuthError
from .token_store import ChatGptTokens

logger = logging.getLogger(__name__)

CODEX_MODELS_URL = "https://chatgpt.com/backend-api/codex/models"
CODEX_CLIENT_VERSION = "1.0.0"
CACHE_TTL_SECONDS = 300.0
PREFERRED_DEFAULT_MODEL = "codex-auto-review"

REASONING_EFFORTS = ("none", "low", "medium", "high")
VERBOSITY_LEVELS = ("low", "medium", "high")
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_VERBOSITY = "medium"

_LOCK = threading.Lock()
_CACHE: dict[str, tuple[float, ChatGptOptionsSnapshot]] = {}


@dataclass(frozen=True)
class CodexModelOption:
    id: str
    label: str
    context_window: int | None = None
    reasoning_efforts: tuple[str, ...] = ()
    default_reasoning_effort: str | None = None


@dataclass(frozen=True)
class ChatGptOptionsSnapshot:
    models: tuple[CodexModelOption, ...]
    default_model: str
    reasoning_efforts: tuple[str, ...] = REASONING_EFFORTS
    verbosity_levels: tuple[str, ...] = VERBOSITY_LEVELS
    default_reasoning_effort: str = DEFAULT_REASONING_EFFORT
    default_verbosity: str = DEFAULT_VERBOSITY
    source: str = "codex"


def clear_options_cache_for_tests() -> None:
    with _LOCK:
        _CACHE.clear()


def _non_empty_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    else:
        return None
    if number <= 0:
        return None
    return number


def _parse_reasoning_efforts(raw_levels: object, default_level: object) -> tuple[str, ...]:
    efforts: list[str] = []
    if isinstance(raw_levels, list):
        for item in raw_levels:
            if isinstance(item, dict):
                effort = _non_empty_str(item.get("effort"))
            else:
                effort = _non_empty_str(item)
            if effort and effort.lower() not in {entry.lower() for entry in efforts}:
                efforts.append(effort.lower())
    default_effort = _non_empty_str(default_level)
    if default_effort and default_effort.lower() not in {entry.lower() for entry in efforts}:
        efforts.insert(0, default_effort.lower())
    if not efforts:
        return REASONING_EFFORTS
    normalized = [effort for effort in REASONING_EFFORTS if effort in efforts]
    for effort in efforts:
        if effort not in normalized:
            normalized.append(effort)
    return tuple(normalized or REASONING_EFFORTS)


def _parse_model_entry(entry: object) -> tuple[CodexModelOption, float | int] | None:
    if not isinstance(entry, dict):
        return None
    slug = _non_empty_str(entry.get("slug")) or _non_empty_str(entry.get("id"))
    if not slug:
        return None
    supported_in_api = entry.get("supported_in_api")
    if supported_in_api is False:
        return None
    label = _non_empty_str(entry.get("display_name")) or slug
    context_window = _positive_int(entry.get("context_window"))
    default_reasoning = _non_empty_str(entry.get("default_reasoning_level"))
    reasoning_efforts = _parse_reasoning_efforts(
        entry.get("supported_reasoning_levels"),
        default_reasoning,
    )
    default_effort = default_reasoning.lower() if default_reasoning else None
    if default_effort and default_effort not in reasoning_efforts:
        default_effort = reasoning_efforts[0] if reasoning_efforts else DEFAULT_REASONING_EFFORT
    priority = entry.get("priority")
    sort_key: float | int = priority if isinstance(priority, (int, float)) else 10_000
    return (
        CodexModelOption(
            id=slug,
            label=label,
            context_window=context_window,
            reasoning_efforts=reasoning_efforts,
            default_reasoning_effort=default_effort,
        ),
        sort_key,
    )


def _normalize_models_payload(payload: object) -> list[CodexModelOption]:
    if not isinstance(payload, dict):
        return []
    entries = payload.get("models")
    if not isinstance(entries, list):
        entries = payload.get("data")
    if not isinstance(entries, list):
        return []
    parsed: list[tuple[CodexModelOption, float | int]] = []
    for entry in entries:
        item = _parse_model_entry(entry)
        if item is None:
            continue
        model, sort_key = item
        parsed.append((model, sort_key))
    parsed.sort(key=lambda pair: (pair[1], pair[0].id))
    return [model for model, _ in parsed]


def _is_preferred_default(model: CodexModelOption) -> bool:
    if model.id.strip().lower() == PREFERRED_DEFAULT_MODEL:
        return True
    blob = f"{model.id} {model.label}".lower()
    return "auto-review" in blob or "auto review" in blob


def _pick_default_model(models: list[CodexModelOption]) -> str:
    for model in models:
        if _is_preferred_default(model):
            return model.id
    return models[0].id


def fallback_snapshot() -> ChatGptOptionsSnapshot:
    return ChatGptOptionsSnapshot(
        models=(
            CodexModelOption(
                id=DEFAULT_MODEL,
                label="GPT-5.4 Mini",
                context_window=128000,
                reasoning_efforts=REASONING_EFFORTS,
                default_reasoning_effort=DEFAULT_REASONING_EFFORT,
            ),
            CodexModelOption(
                id="gpt-4o",
                label="GPT-4o",
                context_window=128000,
                reasoning_efforts=REASONING_EFFORTS,
                default_reasoning_effort=DEFAULT_REASONING_EFFORT,
            ),
        ),
        default_model=DEFAULT_MODEL,
        source="fallback",
    )


def _snapshot_from_models(models: list[CodexModelOption], *, source: str) -> ChatGptOptionsSnapshot:
    if not models:
        return fallback_snapshot()
    return ChatGptOptionsSnapshot(
        models=tuple(models),
        default_model=_pick_default_model(models),
        source=source,
    )


def _codex_headers(tokens: ChatGptTokens) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {tokens.access_token}",
        "Accept": "application/json",
        "ChatGPT-Account-ID": tokens.account_id,
        "OpenAI-Beta": "responses=v1",
        "originator": ORIGINATOR,
        "User-Agent": USER_AGENT,
    }


async def fetch_codex_models(
    tokens: ChatGptTokens,
    *,
    client: httpx.AsyncClient | None = None,
) -> ChatGptOptionsSnapshot:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    url = f"{CODEX_MODELS_URL}?client_version={CODEX_CLIENT_VERSION}"
    try:
        response = await http.get(url, headers=_codex_headers(tokens))
        body = response.text
        if response.status_code >= 400:
            logger.info("ChatGPT models upstream status=%s", response.status_code)
            message = upstream_error_message(response.status_code, body)
            status_code = 401 if response.status_code in {401, 403} else 502
            raise ChatGptOAuthError(message, status_code=status_code)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ChatGptOAuthError("ChatGPT returned an unexpected models response.") from exc
        models = _normalize_models_payload(payload)
        return _snapshot_from_models(models, source="codex")
    finally:
        if owns:
            await http.aclose()


def get_cached_options(user_id: str) -> ChatGptOptionsSnapshot | None:
    with _LOCK:
        cached = _CACHE.get(user_id)
    if cached is None:
        return None
    expires_at, snapshot = cached
    if time.time() >= expires_at:
        return None
    return snapshot


def store_cached_options(user_id: str, snapshot: ChatGptOptionsSnapshot) -> None:
    with _LOCK:
        _CACHE[user_id] = (time.time() + CACHE_TTL_SECONDS, snapshot)


async def get_chatgpt_options(
    user_id: str,
    tokens: ChatGptTokens,
    *,
    force_refresh: bool = False,
    client: httpx.AsyncClient | None = None,
) -> ChatGptOptionsSnapshot:
    if not force_refresh:
        cached = get_cached_options(user_id)
        if cached is not None:
            return cached
    try:
        snapshot = await fetch_codex_models(tokens, client=client)
    except ChatGptOAuthError:
        cached = get_cached_options(user_id)
        if cached is not None:
            return cached
        return fallback_snapshot()
    if not snapshot.models:
        snapshot = fallback_snapshot()
    store_cached_options(user_id, snapshot)
    return snapshot


def model_fallback_chain(snapshot: ChatGptOptionsSnapshot, requested: str | None) -> list[str]:
    primary = (requested or snapshot.default_model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    chain: list[str] = []
    for candidate in (
        primary,
        snapshot.default_model,
        PREFERRED_DEFAULT_MODEL,
        *(model.id for model in snapshot.models),
        DEFAULT_MODEL,
    ):
        if candidate and candidate not in chain:
            chain.append(candidate)
    return chain


def normalize_reasoning_effort(value: str | None, *, model: CodexModelOption | None = None) -> str:
    allowed = model.reasoning_efforts if model and model.reasoning_efforts else REASONING_EFFORTS
    requested = (value or "").strip().lower()
    if requested in allowed:
        return requested
    if model and model.default_reasoning_effort in allowed:
        return model.default_reasoning_effort
    if DEFAULT_REASONING_EFFORT in allowed:
        return DEFAULT_REASONING_EFFORT
    return allowed[0]


def normalize_verbosity(value: str | None) -> str:
    requested = (value or "").strip().lower()
    if requested in VERBOSITY_LEVELS:
        return requested
    return DEFAULT_VERBOSITY


def find_model(snapshot: ChatGptOptionsSnapshot, model_id: str | None) -> CodexModelOption | None:
    requested = (model_id or "").strip()
    if not requested:
        return snapshot.models[0] if snapshot.models else None
    for model in snapshot.models:
        if model.id == requested:
            return model
    return None
