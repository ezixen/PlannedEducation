"""ChatGPT account login via OpenAI device-code (Codex-compatible public client).

UI branding is ChatGPT. Tokens are never written to SQL.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from .token_store import ChatGptTokens

logger = logging.getLogger(__name__)

# Public Codex OAuth client (same as Codex CLI / IDE). Required for device-code ChatGPT plan access.
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
AUTH_BASE = "https://auth.openai.com"
AUTHORIZE_URL = f"{AUTH_BASE}/oauth/authorize"
DEVICE_USER_CODE_URL = f"{AUTH_BASE}/api/accounts/deviceauth/usercode"
DEVICE_TOKEN_URL = f"{AUTH_BASE}/api/accounts/deviceauth/token"
DEVICE_VERIFICATION_URI = f"{AUTH_BASE}/codex/device"
DEVICE_REDIRECT_URI = f"{AUTH_BASE}/deviceauth/callback"
TOKEN_URL = f"{AUTH_BASE}/oauth/token"
JWT_AUTH_CLAIM = "https://api.openai.com/auth"
ORIGINATOR = "plannededucation"
OAUTH_SCOPE = "openid profile email offline_access"


class ChatGptOAuthError(Exception):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


def _b64url_json(segment: str) -> dict[str, Any]:
    padded = segment + "=" * (-len(segment) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ChatGptOAuthError("Invalid token payload.")
    return payload


def account_id_from_access_token(access_token: str) -> str:
    parts = access_token.split(".")
    if len(parts) != 3:
        raise ChatGptOAuthError("ChatGPT access token is malformed.")
    claims = _b64url_json(parts[1])
    auth = claims.get(JWT_AUTH_CLAIM)
    if isinstance(auth, dict):
        account_id = auth.get("chatgpt_account_id")
        if isinstance(account_id, str) and account_id.strip():
            return account_id.strip()
    raise ChatGptOAuthError("ChatGPT account id missing from token.")


def generate_pkce() -> dict[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return {"verifier": verifier, "challenge": challenge}


def generate_oauth_state() -> str:
    return secrets.token_urlsafe(24)


def build_browser_authorize_url(*, redirect_uri: str, pkce: dict[str, str], state: str) -> str:
    """Standard PKCE authorize URL (browser redirect flow)."""
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": OAUTH_SCOPE,
        "code_challenge": pkce["challenge"],
        "code_challenge_method": "S256",
        "state": state,
        "id_token_add_organizations": "true",
        "originator": ORIGINATOR,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def _tokens_from_token_response(data: dict[str, Any]) -> ChatGptTokens:
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    expires_in = data.get("expires_in", 3600)
    if not isinstance(access, str) or not isinstance(refresh, str):
        raise ChatGptOAuthError("ChatGPT token response was incomplete.")
    try:
        expires_seconds = float(expires_in)
    except (TypeError, ValueError):
        expires_seconds = 3600.0
    return ChatGptTokens(
        access_token=access,
        refresh_token=refresh,
        account_id=account_id_from_access_token(access),
        expires_at=time.time() + max(60.0, expires_seconds),
    )


async def exchange_browser_code(
    *,
    authorization_code: str,
    redirect_uri: str,
    code_verifier: str,
    client: httpx.AsyncClient | None = None,
) -> ChatGptTokens:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        response = await http.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": authorization_code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            raise ChatGptOAuthError("Could not finish ChatGPT sign-in.")
        data = response.json()
        if not isinstance(data, dict):
            raise ChatGptOAuthError("ChatGPT token response was incomplete.")
        return _tokens_from_token_response(data)
    finally:
        if owns:
            await http.aclose()


async def start_device_login(client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        response = await http.post(DEVICE_USER_CODE_URL, json={"client_id": CLIENT_ID})
        if response.status_code >= 400:
            raise ChatGptOAuthError(
                "Could not start ChatGPT sign-in. Try again shortly.",
                status_code=502,
            )
        data = response.json()
        device_auth_id = data.get("device_auth_id")
        user_code = data.get("user_code")
        interval = data.get("interval", 5)
        if isinstance(interval, str):
            interval = float(interval.strip() or "5")
        if not isinstance(device_auth_id, str) or not isinstance(user_code, str):
            raise ChatGptOAuthError("ChatGPT sign-in response was incomplete.")
        verification_uri = data.get("verification_uri") or DEVICE_VERIFICATION_URI
        verification_uri_complete = data.get("verification_uri_complete")
        if not isinstance(verification_uri, str):
            verification_uri = DEVICE_VERIFICATION_URI
        return {
            "device_auth_id": device_auth_id,
            "user_code": user_code,
            "interval_seconds": float(interval),
            "verification_uri": verification_uri,
            "verification_uri_complete": verification_uri_complete
            if isinstance(verification_uri_complete, str)
            else None,
        }
    finally:
        if owns:
            await http.aclose()


async def poll_device_authorization(
    *,
    device_auth_id: str,
    user_code: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, str] | None:
    """Return authorization_code + code_verifier when complete; None while pending."""
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        response = await http.post(
            DEVICE_TOKEN_URL,
            json={"device_auth_id": device_auth_id, "user_code": user_code},
        )
        if response.status_code in {403, 404}:
            return None
        if response.status_code >= 400:
            try:
                body = response.json()
                err = body.get("error")
                code = err.get("code") if isinstance(err, dict) else err
                if code in {
                    "deviceauth_authorization_pending",
                    "slow_down",
                    "authorization_pending",
                }:
                    return None
            except Exception:  # noqa: BLE001
                pass
            raise ChatGptOAuthError("ChatGPT sign-in failed. Start again.")
        data = response.json()
        auth_code = data.get("authorization_code")
        verifier = data.get("code_verifier")
        if not isinstance(auth_code, str) or not isinstance(verifier, str):
            raise ChatGptOAuthError("ChatGPT sign-in response was incomplete.")
        return {"authorization_code": auth_code, "code_verifier": verifier}
    finally:
        if owns:
            await http.aclose()


async def exchange_device_code(
    *,
    authorization_code: str,
    code_verifier: str,
    client: httpx.AsyncClient | None = None,
) -> ChatGptTokens:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        response = await http.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": authorization_code,
                "code_verifier": code_verifier,
                "redirect_uri": DEVICE_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            raise ChatGptOAuthError("Could not finish ChatGPT sign-in.")
        data = response.json()
        if not isinstance(data, dict):
            raise ChatGptOAuthError("Could not finish ChatGPT sign-in.")
        return _tokens_from_token_response(data)
    finally:
        if owns:
            await http.aclose()


async def refresh_tokens(
    refresh_token: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> ChatGptTokens:
    owns = client is None
    http = client or httpx.AsyncClient(timeout=30.0)
    try:
        response = await http.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": CLIENT_ID,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 400:
            raise ChatGptOAuthError("ChatGPT session expired. Sign in again.", status_code=401)
        data = response.json()
        if not isinstance(data, dict):
            raise ChatGptOAuthError("ChatGPT refresh response was incomplete.")
        tokens = _tokens_from_token_response(
            {**data, "refresh_token": data.get("refresh_token") or refresh_token}
        )
        return tokens
    finally:
        if owns:
            await http.aclose()
