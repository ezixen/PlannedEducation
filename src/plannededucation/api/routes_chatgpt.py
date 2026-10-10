"""ChatGPT gate for teachers: Sign in with ChatGPT (Device-Code / PKCE) + direct embedded chat."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..chatgpt import client as chatgpt_client
from ..chatgpt import models as chatgpt_models
from ..chatgpt import oauth as chatgpt_oauth
from ..chatgpt.history_store import (
    append_exchange,
    clear_history,
    get_history,
    replace_history,
)
from ..chatgpt.oauth import ChatGptOAuthError
from ..chatgpt.token_store import (
    PendingBrowserLogin,
    PendingDeviceLogin,
    clear_tokens,
    create_browser_pending,
    create_pending,
    get_pending,
    get_tokens,
    pop_browser_pending,
    pop_pending,
    prune_stale_pending,
    put_tokens,
)
from . import models
from .routes_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chatgpt", tags=["chatgpt"])


def require_teacher(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role not in {"teacher", "admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access the embedded ChatGPT workspace.",
        )
    return current_user


class ChatGptLoginStartResponse(BaseModel):
    login_id: str
    user_code: str
    verification_uri: str
    verification_uri_complete: str | None = None
    interval_seconds: float


class ChatGptBrowserLoginStartRequest(BaseModel):
    redirect_uri: str = Field(min_length=12, max_length=512)


class ChatGptBrowserLoginStartResponse(BaseModel):
    login_id: str
    auth_url: str
    state: str


class ChatGptBrowserLoginCompleteRequest(BaseModel):
    login_id: str = Field(min_length=8, max_length=64)
    code: str = Field(min_length=8, max_length=4096)
    state: str = Field(min_length=8, max_length=128)


class ChatGptLoginPollRequest(BaseModel):
    login_id: str = Field(min_length=8, max_length=64)


class ChatGptLoginPollResponse(BaseModel):
    status: str  # pending | complete | failed
    detail: str | None = None


class ChatGptSessionResponse(BaseModel):
    connected: bool
    account_id: str | None = None


class ChatGptChatMessage(BaseModel):
    role: str = Field(min_length=1, max_length=16)
    content: str = Field(min_length=1, max_length=20_000)


class ChatGptChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)
    history: list[ChatGptChatMessage] = Field(default_factory=list, max_length=100)
    instructions: str | None = Field(default=None, max_length=4_096)
    model: str | None = Field(default=None, max_length=64)
    reasoning_effort: str | None = Field(default=None, max_length=16)
    verbosity: str | None = Field(default=None, max_length=16)


class ChatGptModelOptionResponse(BaseModel):
    id: str
    label: str
    context_window: int | None = None
    reasoning_efforts: list[str] = Field(default_factory=list)
    default_reasoning_effort: str | None = None


class ChatGptOptionsResponse(BaseModel):
    models: list[ChatGptModelOptionResponse]
    default_model: str
    reasoning_efforts: list[str]
    verbosity_levels: list[str]
    default_reasoning_effort: str
    default_verbosity: str
    source: str


class ChatGptChatResponse(BaseModel):
    reply: str


class ChatGptHistoryResponse(BaseModel):
    messages: list[ChatGptChatMessage]


def _http_error(exc: ChatGptOAuthError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


async def fresh_teacher_tokens(user_id: str):
    tokens = get_tokens(user_id)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sign in with ChatGPT first. PlannedEducation does not supply ChatGPT for you.",
        )
    if tokens.expires_at > time.time() + 60:
        return tokens
    try:
        refreshed = await chatgpt_oauth.refresh_tokens(tokens.refresh_token)
    except ChatGptOAuthError as exc:
        clear_tokens(user_id)
        raise _http_error(exc) from exc
    put_tokens(user_id, refreshed)
    return refreshed


def _options_response(snapshot: chatgpt_models.ChatGptOptionsSnapshot) -> ChatGptOptionsResponse:
    return ChatGptOptionsResponse(
        models=[
            ChatGptModelOptionResponse(
                id=model.id,
                label=model.label,
                context_window=model.context_window,
                reasoning_efforts=list(model.reasoning_efforts),
                default_reasoning_effort=model.default_reasoning_effort,
            )
            for model in snapshot.models
        ],
        default_model=snapshot.default_model,
        reasoning_efforts=list(snapshot.reasoning_efforts),
        verbosity_levels=list(snapshot.verbosity_levels),
        default_reasoning_effort=snapshot.default_reasoning_effort,
        default_verbosity=snapshot.default_verbosity,
        source=snapshot.source,
    )


@router.get("/options", response_model=ChatGptOptionsResponse)
async def chatgpt_options(
    user: models.User = Depends(require_teacher),
    refresh: bool = Query(default=False),
) -> ChatGptOptionsResponse:
    tokens = get_tokens(user.id)
    if tokens is None:
        return _options_response(chatgpt_models.fallback_snapshot())
    snapshot = await chatgpt_models.get_chatgpt_options(
        user.id,
        tokens,
        force_refresh=refresh,
    )
    return _options_response(snapshot)


def _resolve_chat_history(user_id: str, body: ChatGptChatRequest) -> list[dict[str, str]]:
    stored = get_history(user_id)
    if stored:
        return stored
    if body.history:
        return replace_history(
            user_id,
            [{"role": item.role, "content": item.content} for item in body.history],
        )
    return []


@router.post("/login/start", response_model=ChatGptLoginStartResponse)
async def chatgpt_login_start(
    user: models.User = Depends(require_teacher),
) -> ChatGptLoginStartResponse:
    prune_stale_pending()
    try:
        started = await chatgpt_oauth.start_device_login()
    except ChatGptOAuthError as exc:
        raise _http_error(exc) from exc
    login_id = create_pending(
        PendingDeviceLogin(
            user_id=user.id,
            device_auth_id=started["device_auth_id"],
            user_code=started["user_code"],
            interval_seconds=float(started["interval_seconds"]),
            created_at=time.time(),
        )
    )
    return ChatGptLoginStartResponse(
        login_id=login_id,
        user_code=started["user_code"],
        verification_uri=started["verification_uri"],
        verification_uri_complete=started.get("verification_uri_complete"),
        interval_seconds=float(started["interval_seconds"]),
    )


@router.post("/login/browser/start", response_model=ChatGptBrowserLoginStartResponse)
async def chatgpt_browser_login_start(
    body: ChatGptBrowserLoginStartRequest,
    user: models.User = Depends(require_teacher),
) -> ChatGptBrowserLoginStartResponse:
    prune_stale_pending()
    redirect_uri = body.redirect_uri.strip()
    if not (
        redirect_uri.startswith("http://127.0.0.1")
        or redirect_uri.startswith("http://localhost")
        or redirect_uri.startswith("https://127.0.0.1")
        or redirect_uri.startswith("https://localhost")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Browser ChatGPT sign-in only works on localhost. "
                "On remote web hosting, use device-code sign-in."
            ),
        )
    pkce = chatgpt_oauth.generate_pkce()
    oauth_state = chatgpt_oauth.generate_oauth_state()
    login_id = create_browser_pending(
        PendingBrowserLogin(
            user_id=user.id,
            oauth_state=oauth_state,
            code_verifier=pkce["verifier"],
            redirect_uri=redirect_uri,
            created_at=time.time(),
        )
    )
    auth_url = chatgpt_oauth.build_browser_authorize_url(
        redirect_uri=redirect_uri,
        pkce=pkce,
        state=oauth_state,
    )
    return ChatGptBrowserLoginStartResponse(login_id=login_id, auth_url=auth_url, state=oauth_state)


@router.post("/login/browser/complete", status_code=status.HTTP_204_NO_CONTENT)
async def chatgpt_browser_login_complete(
    body: ChatGptBrowserLoginCompleteRequest,
    user: models.User = Depends(require_teacher),
) -> None:
    pending = pop_browser_pending(body.login_id)
    if pending is None or pending.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ChatGPT sign-in session not found."
        )
    if body.state != pending.oauth_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ChatGPT sign-in state mismatch."
        )
    try:
        tokens = await chatgpt_oauth.exchange_browser_code(
            authorization_code=body.code.strip(),
            redirect_uri=pending.redirect_uri,
            code_verifier=pending.code_verifier,
        )
    except ChatGptOAuthError as exc:
        raise _http_error(exc) from exc
    put_tokens(user.id, tokens)


@router.post("/login/poll", response_model=ChatGptLoginPollResponse)
async def chatgpt_login_poll(
    body: ChatGptLoginPollRequest,
    user: models.User = Depends(require_teacher),
) -> ChatGptLoginPollResponse:
    pending = get_pending(body.login_id)
    if pending is None or pending.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ChatGPT sign-in session not found."
        )
    try:
        authorized = await chatgpt_oauth.poll_device_authorization(
            device_auth_id=pending.device_auth_id,
            user_code=pending.user_code,
        )
    except ChatGptOAuthError as exc:
        pop_pending(body.login_id)
        return ChatGptLoginPollResponse(status="failed", detail=str(exc))
    if authorized is None:
        return ChatGptLoginPollResponse(status="pending")
    try:
        tokens = await chatgpt_oauth.exchange_device_code(
            authorization_code=authorized["authorization_code"],
            code_verifier=authorized["code_verifier"],
        )
    except ChatGptOAuthError as exc:
        pop_pending(body.login_id)
        return ChatGptLoginPollResponse(status="failed", detail=str(exc))
    pop_pending(body.login_id)
    put_tokens(user.id, tokens)
    return ChatGptLoginPollResponse(status="complete")


@router.get("/session", response_model=ChatGptSessionResponse)
async def chatgpt_session(
    user: models.User = Depends(require_teacher),
) -> ChatGptSessionResponse:
    tokens = get_tokens(user.id)
    if tokens is None:
        return ChatGptSessionResponse(connected=False)
    return ChatGptSessionResponse(connected=True, account_id=tokens.account_id)


@router.get("/history", response_model=ChatGptHistoryResponse)
async def chatgpt_get_history(
    user: models.User = Depends(require_teacher),
) -> ChatGptHistoryResponse:
    messages = get_history(user.id)
    return ChatGptHistoryResponse(
        messages=[
            ChatGptChatMessage(role=item["role"], content=item["content"]) for item in messages
        ]
    )


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
async def chatgpt_clear_history(
    user: models.User = Depends(require_teacher),
) -> None:
    clear_history(user.id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def chatgpt_logout(
    user: models.User = Depends(require_teacher),
) -> None:
    clear_tokens(user.id)
    clear_history(user.id)


@router.post("/chat", response_model=ChatGptChatResponse)
async def chatgpt_chat(
    body: ChatGptChatRequest,
    user: models.User = Depends(require_teacher),
) -> ChatGptChatResponse:
    tokens = await fresh_teacher_tokens(user.id)
    history = _resolve_chat_history(user.id, body)
    prior = [item for item in history if item["role"] in {"user", "assistant"}]
    snapshot = await chatgpt_models.get_chatgpt_options(user.id, tokens)
    selected_model = chatgpt_models.find_model(snapshot, body.model)
    reasoning_effort = chatgpt_models.normalize_reasoning_effort(
        body.reasoning_effort,
        model=selected_model,
    )
    verbosity = chatgpt_models.normalize_verbosity(body.verbosity)
    model_candidates = chatgpt_models.model_fallback_chain(snapshot, body.model)
    try:
        reply = await chatgpt_client.create_response(
            tokens,
            message=body.message,
            history=prior,
            instructions=(body.instructions or "").strip(),
            model=model_candidates[0],
            model_candidates=model_candidates,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            context_window=selected_model.context_window if selected_model else None,
        )
    except ChatGptOAuthError as exc:
        logger.info(
            "ChatGPT chat upstream failure for user_id=%s status=%s", user.id, exc.status_code
        )
        raise _http_error(exc) from exc
    append_exchange(user.id, user_message=body.message, assistant_message=reply)
    return ChatGptChatResponse(reply=reply)
