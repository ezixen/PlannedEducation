"""
Outbound URL safety checks (SSRF / credential-exfil / DNS-rebinding prevention).

Used for teacher AI base URLs and admin package-source URLs.
Fail closed: any URL that cannot be proven safe is rejected.

DNS rebinding (F-022 residual):
- ``validate_outbound_url(..., return_ips=True)`` returns the public IPs seen at
  validation time.
- Outbound httpx clients MUST use ``create_outbound_async_client`` (or call
  ``assert_resolution_still_safe`` / pin via ``rewrite_url_to_pinned_ip``) so the
  connect-time resolution is re-checked against those IPs / public ranges.
- Always keep ``follow_redirects=False`` for teacher/admin-controlled URLs.
"""

from __future__ import annotations

import ipaddress
import os
import socket
from collections.abc import Iterable
from typing import Literal, overload
from urllib.parse import urlparse, urlunparse

import httpx

# Hostnames that are always treated as loopback / local (string form).
_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
        "instance-data",
    }
)

# Well-known cloud metadata / link-local targets.
_BLOCKED_LITERAL_HOSTS = frozenset(
    {
        "169.254.169.254",
        "169.254.170.2",
        "[fd00:ec2::254]",
        "fd00:ec2::254",
    }
)

# Credential-exfil / suspicious query keys often used to bounce secrets.
_EXFIL_QUERY_MARKERS = frozenset(
    {
        "api_key",
        "apikey",
        "access_key",
        "access_token",
        "auth_token",
        "authorization",
        "bearer",
        "client_secret",
        "id_token",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
        "x-api-key",
    }
)

# Hosts allowed for local-only providers (Ollama) when allow_loopback=True.
_LOCAL_OLLAMA_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF / allowlist validation."""


def _hostname_is_blocked_name(hostname: str) -> bool:
    host = hostname.strip(".").lower()
    if host in _BLOCKED_HOSTNAMES or host in _BLOCKED_LITERAL_HOSTS:
        return True
    return bool(host.endswith(".localhost") or host.endswith(".local"))


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    # Explicit cloud metadata ranges / documentation nets already covered by
    # is_private / is_link_local for 169.254/16 and 10/8, 172.16/12, 192.168/16.
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _normalize_ip_str(addr: str) -> str:
    return str(ipaddress.ip_address(addr.strip("[]")))


def resolve_public_ips(hostname: str, *, allow_loopback: bool = False) -> list[str]:
    """
    Resolve ``hostname`` and return public (or allowed loopback) IP strings.

    Raises UnsafeURLError if the name is blocked, unresolvable, or any address
    is non-public (unless ``allow_loopback`` permits loopback-only hosts).
    """
    host = (hostname or "").strip()
    if not host:
        raise UnsafeURLError("URL host is required")

    host_key = host.lower().strip("[]")

    if allow_loopback and host_key in {h.strip("[]") for h in _LOCAL_OLLAMA_HOSTS}:
        # Prefer concrete loopback addresses for pinning.
        if host_key in {"::1"}:
            return ["::1"]
        return ["127.0.0.1"]

    if _hostname_is_blocked_name(host) and not allow_loopback:
        raise UnsafeURLError("URL host is not allowed")

    try:
        literal = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        literal = None

    if literal is not None:
        if allow_loopback and literal.is_loopback:
            return [_normalize_ip_str(str(literal))]
        if _ip_is_blocked(literal):
            raise UnsafeURLError("URL resolves to a blocked address")
        return [_normalize_ip_str(str(literal))]

    if allow_loopback and host.lower() in {"localhost", "localhost.localdomain"}:
        return ["127.0.0.1"]

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError("URL host could not be resolved") from exc

    if not infos:
        raise UnsafeURLError("URL host could not be resolved")

    resolved: list[str] = []
    seen: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            addr = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        if allow_loopback and addr.is_loopback:
            key = _normalize_ip_str(str(addr))
            if key not in seen:
                seen.add(key)
                resolved.append(key)
            continue
        if _ip_is_blocked(addr):
            raise UnsafeURLError("URL resolves to a blocked address")
        key = _normalize_ip_str(str(addr))
        if key not in seen:
            seen.add(key)
            resolved.append(key)

    if not resolved:
        raise UnsafeURLError("URL host could not be resolved")
    return resolved


def _resolve_and_check_host(hostname: str, *, allow_loopback: bool) -> list[str]:
    """Resolve hostname and reject if any address is non-public (fail closed)."""
    return resolve_public_ips(hostname, allow_loopback=allow_loopback)


def assert_resolution_still_safe(
    hostname: str,
    *,
    allowed_ips: Iterable[str] | None = None,
    allow_loopback: bool = False,
) -> list[str]:
    """
    Re-resolve ``hostname`` immediately before connect.

    - Rejects if any resolved address is non-public (unless loopback allowed).
    - If ``allowed_ips`` was captured at validate time, rejects when none of the
      current addresses overlap (DNS rebinding to a different host/IP set).
    """
    current = resolve_public_ips(hostname, allow_loopback=allow_loopback)
    if allowed_ips is not None:
        allowed = {_normalize_ip_str(ip) for ip in allowed_ips}
        if not allowed:
            raise UnsafeURLError("No validated IP addresses available for pinning")
        if not any(ip in allowed for ip in current):
            raise UnsafeURLError("DNS rebinding detected: resolved IPs changed")
        # Prefer the intersection for pinning order.
        pinned = [ip for ip in current if ip in allowed]
        return pinned or current
    return current


def rewrite_url_to_pinned_ip(url: str, pinned_ip: str) -> tuple[str, str]:
    """
    Rewrite ``url`` so the netloc uses ``pinned_ip`` while returning the original
    hostname for the HTTP Host header.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL host is required")

    ip = ipaddress.ip_address(pinned_ip.strip("[]"))
    host_for_netloc = f"[{ip}]" if ip.version == 6 else str(ip)
    netloc = f"{host_for_netloc}:{parsed.port}" if parsed.port is not None else host_for_netloc

    pinned = urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
    return pinned, hostname


def create_outbound_async_client(
    *,
    validated_ips: list[str] | None = None,
    allow_loopback: bool = False,
    timeout: float = 15.0,
    **kwargs,
) -> httpx.AsyncClient:
    """
    Build an httpx AsyncClient that re-validates DNS before each request and
    connects only to a previously validated public IP (Host header preserved).

    Always disables redirects (SSRF redirect bypass).
    """
    kwargs.pop("follow_redirects", None)

    async def _pin_before_request(request: httpx.Request) -> None:
        host = request.url.host
        if not host:
            raise UnsafeURLError("URL host is required")
        # Skip re-pin if the URL already targets a literal IP we validated.
        try:
            literal = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            literal = None

        if literal is not None:
            if allow_loopback and literal.is_loopback:
                return
            if _ip_is_blocked(literal):
                raise UnsafeURLError("URL resolves to a blocked address")
            if validated_ips is not None:
                allowed = {_normalize_ip_str(ip) for ip in validated_ips}
                if _normalize_ip_str(str(literal)) not in allowed:
                    raise UnsafeURLError("DNS rebinding detected: resolved IPs changed")
            return

        pinned_ips = assert_resolution_still_safe(
            host,
            allowed_ips=validated_ips,
            allow_loopback=allow_loopback,
        )
        pin = pinned_ips[0]
        original_host = host
        # Mutate request URL to connect to the pinned IP; keep Host header.
        if "host" not in request.headers:
            port = request.url.port
            if port is not None:
                request.headers["Host"] = f"{original_host}:{port}"
            else:
                request.headers["Host"] = original_host
        # httpx URL host for IPv6 is unbracketed.
        request.url = request.url.copy_with(host=pin)

    hooks = kwargs.pop("event_hooks", None) or {}
    request_hooks = list(hooks.get("request") or [])
    request_hooks.insert(0, _pin_before_request)
    hooks = {**hooks, "request": request_hooks}

    return httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        event_hooks=hooks,
        **kwargs,
    )


def _has_credential_exfil_patterns(parsed) -> bool:
    if parsed.username is not None or parsed.password is not None:
        return True
    # userinfo without netloc edge cases
    if "@" in (parsed.netloc or ""):
        return True
    query = (parsed.query or "").lower()
    if not query:
        return False
    for marker in _EXFIL_QUERY_MARKERS:
        if f"{marker}=" in query or query.startswith(f"{marker}=") or f"&{marker}=" in query:
            return True
    return False


@overload
def validate_outbound_url(
    url: str | None,
    *,
    allow_loopback: bool = False,
    allowed_schemes: tuple[str, ...] = ("https",),
    resolve_dns: bool = True,
    return_ips: Literal[True],
) -> tuple[str, list[str]]: ...


@overload
def validate_outbound_url(
    url: str | None,
    *,
    allow_loopback: bool = False,
    allowed_schemes: tuple[str, ...] = ("https",),
    resolve_dns: bool = True,
    return_ips: Literal[False] = False,
) -> str: ...


def validate_outbound_url(
    url: str | None,
    *,
    allow_loopback: bool = False,
    allowed_schemes: tuple[str, ...] = ("https",),
    resolve_dns: bool = True,
    return_ips: bool = False,
) -> str | tuple[str, list[str]]:
    """
    Validate an outbound URL for SSRF safety.

    Returns the stripped URL on success; raises UnsafeURLError otherwise.
    When ``return_ips=True``, returns ``(url, validated_ip_addresses)`` for
    connect-time pinning / rebind checks.
    """
    if url is None:
        raise UnsafeURLError("URL is required")

    cleaned = str(url).strip()
    if not cleaned:
        raise UnsafeURLError("URL is required")

    if any(ch.isspace() for ch in cleaned):
        raise UnsafeURLError("URL must not contain whitespace")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in allowed_schemes:
        raise UnsafeURLError(f"URL scheme '{scheme or 'none'}' is not allowed")

    if scheme in {"file", "unix", "socket", "gopher", "dict", "ftp", "ftps", "ldap", "ldaps"}:
        raise UnsafeURLError("URL scheme is not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL host is required")

    if parsed.port == 0:
        raise UnsafeURLError("URL port is not allowed")

    if _has_credential_exfil_patterns(parsed):
        raise UnsafeURLError("URL contains credential or secret-exfiltration patterns")

    validated_ips: list[str] = []
    if resolve_dns:
        validated_ips = _resolve_and_check_host(hostname, allow_loopback=allow_loopback)
    else:
        # Literal / name checks only (used in unit tests that mock DNS).
        try:
            literal = ipaddress.ip_address(hostname.strip("[]"))
        except ValueError:
            if _hostname_is_blocked_name(hostname) and not allow_loopback:
                raise UnsafeURLError("URL host is not allowed") from None
            if allow_loopback and hostname.lower() in {"localhost", "localhost.localdomain"}:
                validated_ips = ["127.0.0.1"]
                return (cleaned, validated_ips) if return_ips else cleaned
        else:
            if allow_loopback and literal.is_loopback:
                validated_ips = [_normalize_ip_str(str(literal))]
                return (cleaned, validated_ips) if return_ips else cleaned
            if _ip_is_blocked(literal):
                raise UnsafeURLError("URL resolves to a blocked address")
            validated_ips = [_normalize_ip_str(str(literal))]

    if return_ips:
        return cleaned, validated_ips
    return cleaned


@overload
def validate_ai_base_url(
    url: str | None,
    *,
    provider: str | None = None,
    return_ips: Literal[True],
) -> tuple[str, list[str]] | None: ...


@overload
def validate_ai_base_url(
    url: str | None,
    *,
    provider: str | None = None,
    return_ips: Literal[False] = False,
) -> str | None: ...


def validate_ai_base_url(
    url: str | None,
    *,
    provider: str | None = None,
    return_ips: bool = False,
) -> str | None | tuple[str, list[str]]:
    """
    Validate a teacher-configured AI base URL.

    - Empty / None → None (use provider default).
    - Ollama may use http://127.0.0.1 or http://localhost.
    - All other providers require https to a public host.
    Custom endpoints that fail validation raise UnsafeURLError (fail closed).
    """
    if url is None:
        return None
    cleaned = str(url).strip()
    if not cleaned:
        return None

    provider_l = (provider or "").lower()
    if provider_l == "ollama":
        if return_ips:
            return validate_outbound_url(
                cleaned,
                allow_loopback=True,
                allowed_schemes=("http", "https"),
                return_ips=True,
            )
        return validate_outbound_url(
            cleaned,
            allow_loopback=True,
            allowed_schemes=("http", "https"),
            return_ips=False,
        )

    # Non-ollama custom endpoints: HTTPS only, no private/loopback.
    if return_ips:
        return validate_outbound_url(
            cleaned,
            allow_loopback=False,
            allowed_schemes=("https",),
            return_ips=True,
        )
    return validate_outbound_url(
        cleaned,
        allow_loopback=False,
        allowed_schemes=("https",),
        return_ips=False,
    )


@overload
def validate_package_source_url(
    url: str | None,
    *,
    return_ips: Literal[True],
) -> tuple[str, list[str]]: ...


@overload
def validate_package_source_url(
    url: str | None,
    *,
    return_ips: Literal[False] = False,
) -> str: ...


def validate_package_source_url(
    url: str | None,
    *,
    return_ips: bool = False,
) -> str | tuple[str, list[str]]:
    """Validate admin package-source URLs (HTTPS public hosts only)."""
    if return_ips:
        return validate_outbound_url(
            url,
            allow_loopback=False,
            allowed_schemes=("https",),
            return_ips=True,
        )
    return validate_outbound_url(
        url,
        allow_loopback=False,
        allowed_schemes=("https",),
        return_ips=False,
    )


def _teacher_sync_allowlist() -> set[str]:
    """Comma-separated hosts from TEACHER_SYNC_URL_ALLOWLIST (case-insensitive)."""
    raw = os.getenv("TEACHER_SYNC_URL_ALLOWLIST", "") or ""
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _ip_is_private_or_loopback(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True for RFC1918 / ULA / loopback — allowed for classroom teacher sync."""
    return bool(ip.is_private or ip.is_loopback)


def validate_teacher_sync_url(url: str | None, *, resolve_dns: bool = True) -> str:
    """
    Validate a teacher-device LAN sync URL (F-048).

    Opposite of AI SSRF policy: only http(s) to private/LAN/loopback addresses,
    OR hostnames explicitly listed in TEACHER_SYNC_URL_ALLOWLIST.
    Public internet hosts are rejected (fail closed).
    """
    if url is None:
        raise UnsafeURLError("Teacher sync URL is required")

    cleaned = str(url).strip().rstrip("/")
    if not cleaned:
        raise UnsafeURLError("Teacher sync URL is required")

    if any(ch.isspace() for ch in cleaned):
        raise UnsafeURLError("Teacher sync URL must not contain whitespace")

    parsed = urlparse(cleaned)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise UnsafeURLError(f"URL scheme '{scheme or 'none'}' is not allowed")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL host is required")

    if parsed.port == 0:
        raise UnsafeURLError("URL port is not allowed")

    if _has_credential_exfil_patterns(parsed):
        raise UnsafeURLError("URL contains credential or secret-exfiltration patterns")

    host_l = hostname.strip("[]").lower()
    allowlist = _teacher_sync_allowlist()
    if host_l in allowlist:
        return cleaned

    try:
        literal = ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        literal = None

    if literal is not None:
        if _ip_is_private_or_loopback(literal):
            return cleaned
        raise UnsafeURLError("Teacher sync URL must target a private/LAN address")

    if host_l in {"localhost", "localhost.localdomain"} or host_l.endswith(".localhost"):
        return cleaned

    if host_l.endswith(".local"):
        return cleaned

    if not resolve_dns:
        raise UnsafeURLError("Teacher sync hostname is not allowlisted")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError("Teacher sync host could not be resolved") from exc

    if not infos:
        raise UnsafeURLError("Teacher sync host could not be resolved")

    saw_addr = False
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            addr = ipaddress.ip_address(sockaddr[0])
        except ValueError:
            continue
        saw_addr = True
        if not _ip_is_private_or_loopback(addr):
            raise UnsafeURLError("Teacher sync URL resolves to a public address")

    if not saw_addr:
        raise UnsafeURLError("Teacher sync host could not be resolved")

    return cleaned
