"""Call ChatGPT plan Responses API (chatgpt.com Codex backend) with teacher OAuth tokens."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx

from .oauth import ORIGINATOR, ChatGptOAuthError
from .token_store import ChatGptTokens

logger = logging.getLogger(__name__)

CODEX_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"
DEFAULT_MODEL = "gpt-5.4-mini"
USER_AGENT = "PlannedEducation/1.0 (ChatGPT gate; Codex responses)"


def _estimate_tokens(text: str) -> int:
    """Rough char heuristic — OpenAI does not expose a turn limit; we honor context_window."""
    return max(1, (len(text) + 3) // 4)


def _message_item(role: str, content: str) -> dict[str, Any]:
    part_type = "output_text" if role == "assistant" else "input_text"
    return {
        "type": "message",
        "role": role,
        "content": [{"type": part_type, "text": content}],
    }


def format_codex_input(
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
    context_window: int | None = None,
) -> list[dict[str, Any]]:
    """Build Codex `/responses` input items (not chat/completions shape).

    Includes prior messages up to the selected model's OpenAI context_window.
    """
    user_text = message.strip()
    if not user_text:
        raise ChatGptOAuthError("Message is empty.")

    prior: list[dict[str, Any]] = []
    for item in history or []:
        role = (item.get("role") or "").strip().lower()
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        prior.append(_message_item(role, content))

    current = _message_item("user", user_text)
    if context_window is None or context_window <= 0:
        return [*prior, current]

    # Leave headroom for the model reply within the published context window.
    if context_window < 2_048:
        reserve = max(32, context_window // 4)
    else:
        reserve = min(8_192, max(1_024, context_window // 8))
    budget = max(32, context_window - reserve)
    used = _estimate_tokens(user_text)
    kept: list[dict[str, Any]] = []
    for item in reversed(prior):
        text = ""
        content = item.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                text = str(first.get("text") or "")
        cost = _estimate_tokens(text)
        if used + cost > budget:
            break
        kept.append(item)
        used += cost
    kept.reverse()
    return [*kept, current]


def build_codex_payload(
    *,
    model: str,
    input_items: list[dict[str, Any]],
    instructions: str = "",
    reasoning_effort: str = "medium",
    verbosity: str = "medium",
) -> dict[str, Any]:
    return {
        "model": model,
        "instructions": instructions,
        "input": input_items,
        "stream": True,
        "store": False,
        "tools": [],
        "tool_choice": "none",
        "parallel_tool_calls": False,
        "reasoning": {"effort": reasoning_effort, "summary": "auto"},
        "text": {"verbosity": verbosity},
        "include": [],
    }


def upstream_error_message(status_code: int, body: str) -> str:
    detail: str | None = None
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        raw_detail = payload.get("detail")
        if isinstance(raw_detail, str) and raw_detail.strip():
            detail = raw_detail.strip()
        else:
            err = payload.get("error")
            if isinstance(err, dict):
                message = err.get("message")
                if isinstance(message, str) and message.strip():
                    detail = message.strip()
    if detail:
        if status_code in {401, 403}:
            return "ChatGPT session expired. Sign in again."
        if status_code == 429:
            return "ChatGPT rate limit reached on your plan. Wait and try again."
        return f"ChatGPT could not answer ({status_code}): {detail}"
    if status_code in {401, 403}:
        return "ChatGPT session expired. Sign in again."
    if status_code == 429:
        return "ChatGPT rate limit reached on your plan. Wait and try again."
    return "ChatGPT could not answer. Check your plan limits or sign in again."


def _extract_output_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    output = payload.get("output")
    if output is None:
        output = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") not in {None, "message"} and "content" not in item:
                continue
            content = item.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        chunks.append(text.strip())
            elif isinstance(content, str) and content.strip():
                chunks.append(content.strip())
    if chunks:
        return "\n".join(chunks)
    for key in ("output_text", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise ChatGptOAuthError("ChatGPT returned an empty reply.")


def _delta_from_event(event: dict[str, Any]) -> str | None:
    event_type = event.get("type")
    if event_type == "response.output_text.delta":
        delta = event.get("delta")
        if isinstance(delta, str) and delta:
            return delta
    if event_type == "response.output_text.done":
        text = event.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    item = event.get("item")
    if isinstance(item, dict):
        content = item.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            if parts:
                return "\n".join(parts)
    response = event.get("response")
    if isinstance(response, dict):
        try:
            return _extract_output_text(response)
        except ChatGptOAuthError:
            return None
    return None


def collect_text_from_sse(body: str) -> str:
    chunks: list[str] = []
    completed_text: str | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_type = event.get("type")
        if event_type == "response.failed" or event_type == "error":
            detail = event.get("error")
            if isinstance(detail, dict):
                message = detail.get("message")
                if isinstance(message, str) and message.strip():
                    raise ChatGptOAuthError(f"ChatGPT could not answer: {message.strip()}")
            raise ChatGptOAuthError("ChatGPT could not answer.")
        if event_type == "response.completed":
            response = event.get("response")
            if isinstance(response, dict):
                try:
                    completed_text = _extract_output_text(response)
                except ChatGptOAuthError:
                    completed_text = None
            continue
        delta = _delta_from_event(event)
        if isinstance(delta, str) and delta:
            if event_type == "response.output_text.done":
                chunks = [delta]
            else:
                chunks.append(delta)
    if completed_text and completed_text.strip():
        return completed_text.strip()
    text = "".join(chunks).strip()
    if text:
        return text
    raise ChatGptOAuthError("ChatGPT returned an empty reply.")


def looks_like_sse(body: str) -> bool:
    """Codex often leads with `event:` lines before the first `data:` frame."""
    head = body.lstrip()[:4_096]
    if head.startswith("data:") or head.startswith("event:"):
        return True
    return "\ndata:" in head or "\nevent:" in head


def _request_headers(tokens: ChatGptTokens) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {tokens.access_token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "ChatGPT-Account-ID": tokens.account_id,
        "OpenAI-Beta": "responses=v1",
        "originator": ORIGINATOR,
        "session_id": str(uuid.uuid4()),
        "User-Agent": USER_AGENT,
    }


def _is_unsupported_model_error(status_code: int, body: str) -> bool:
    if status_code != 400:
        return False
    lowered = body.lower()
    return "not supported when using codex" in lowered or "unsupported model" in lowered


async def _post_codex_once(
    http: httpx.AsyncClient,
    *,
    tokens: ChatGptTokens,
    model: str,
    input_items: list[dict[str, Any]],
    instructions: str = "",
    reasoning_effort: str,
    verbosity: str,
) -> str:
    payload = build_codex_payload(
        model=model,
        input_items=input_items,
        instructions=instructions,
        reasoning_effort=reasoning_effort,
        verbosity=verbosity,
    )
    async with http.stream(
        "POST",
        CODEX_RESPONSES_URL,
        headers=_request_headers(tokens),
        json=payload,
    ) as response:
        body = await response.aread()
        text_body = body.decode("utf-8", errors="replace")
        if response.status_code >= 400:
            logger.info(
                "ChatGPT responses upstream status=%s model=%s", response.status_code, model
            )
            message_text = upstream_error_message(response.status_code, text_body)
            if _is_unsupported_model_error(response.status_code, text_body):
                raise ChatGptOAuthError(message_text, status_code=400)
            status_code = 401 if response.status_code in {401, 403} else 502
            raise ChatGptOAuthError(message_text, status_code=status_code)
        content_type = (response.headers.get("content-type") or "").lower()
        if "text/event-stream" in content_type or looks_like_sse(text_body):
            return collect_text_from_sse(text_body)
        try:
            data = json.loads(text_body)
        except json.JSONDecodeError as exc:
            snippet = " ".join(text_body.split())[:180]
            logger.info(
                "ChatGPT non-JSON responses body model=%s content_type=%s snippet=%r",
                model,
                content_type,
                snippet,
            )
            raise ChatGptOAuthError(
                "ChatGPT returned an unexpected response. "
                "Try another model (for example GPT-5.4 Mini) or sign in again.",
            ) from exc
        if not isinstance(data, dict):
            raise ChatGptOAuthError(
                "ChatGPT returned an unexpected response. "
                "Try another model (for example GPT-5.4 Mini) or sign in again.",
            )
        return _extract_output_text(data)


async def create_response(
    tokens: ChatGptTokens,
    *,
    message: str,
    history: list[dict[str, str]] | None = None,
    instructions: str = "",
    model: str = DEFAULT_MODEL,
    model_candidates: list[str] | None = None,
    reasoning_effort: str = "medium",
    verbosity: str = "medium",
    context_window: int | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=120.0)
    input_items = format_codex_input(
        message=message,
        history=history,
        context_window=context_window,
    )
    candidates: list[str] = []
    for candidate in model_candidates or [model]:
        normalized = (candidate or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    if not candidates:
        candidates = [DEFAULT_MODEL]
    last_error: ChatGptOAuthError | None = None
    try:
        for index, candidate in enumerate(candidates):
            try:
                return await _post_codex_once(
                    http,
                    tokens=tokens,
                    model=candidate,
                    input_items=input_items,
                    instructions=instructions,
                    reasoning_effort=reasoning_effort,
                    verbosity=verbosity,
                )
            except ChatGptOAuthError as exc:
                last_error = exc
                if exc.status_code != 400 or index >= len(candidates) - 1:
                    raise
                if (
                    "not supported when using codex" not in str(exc).lower()
                    and "unsupported model" not in str(exc).lower()
                ):
                    raise
                logger.info("ChatGPT model %s unsupported; trying next Codex fallback", candidate)
        assert last_error is not None
        raise last_error
    finally:
        if owns:
            await http.aclose()
