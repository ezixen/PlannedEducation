import os
import json
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from .database import engine, Base
from . import models, routes_auth, routes_exam, routes_chat, routes_anonymizer, routes_parent, routes_ocr


# ── Logging Configuration ────────────────────────────────────────────────────
# Structured JSON logging for security audit trail
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "security_event"):
            log_obj["security_event"] = record.security_event
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "ip"):
            log_obj["ip"] = record.ip
        return json.dumps(log_obj)

# Configure root logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plannededucation")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


# ── Rate Limiter (shared instance) ──────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
if os.getenv("PLANNED_EDUCATION_ENV") == "test":
    limiter.enabled = False

app = FastAPI(
    title="Planned Education API",
    description="Backend for the Planned Education platform.",
    version="1.0.0",
    lifespan=lifespan,
    # Disable automatic Swagger/Redoc in production
    docs_url="/docs" if os.getenv("PLANNED_EDUCATION_ENV") == "development" else None,
    redoc_url="/redoc" if os.getenv("PLANNED_EDUCATION_ENV") == "development" else None,
)

# ── State for rate limiter ───────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Security Headers Middleware ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # OWASP recommended security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"
        # Content Security Policy - restrictive by default
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com; "
            "frame-src https://accounts.google.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        if os.getenv("PLANNED_EDUCATION_ENV") != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ── Trusted Host Middleware (prevent Host header attacks) ────────────────────
# Only enable in production; tests use testclient which doesn't set proper Host header
if os.getenv("PLANNED_EDUCATION_ENV") == "production":
    allowed_hosts = [
        host.strip()
        for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
        if host.strip()
    ]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# ── CORS (explicit allow-list, never wildcard) ───────────────────────────────
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-SafeExamBrowser-RequestHash"],
    expose_headers=["X-Request-ID"],
    max_age=600,
)

# ── Request ID Middleware (for tracing) ──────────────────────────────────────
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", os.urandom(16).hex())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)

# ── Security Audit Logging Middleware ────────────────────────────────────────
class SecurityAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log security-relevant events
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log authentication attempts
        if request.url.path.startswith("/auth/"):
            logger.info(
                f"Auth endpoint accessed: {request.method} {request.url.path}",
                extra={
                    "security_event": "auth_endpoint_access",
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            )
        
        # Log exam access attempts
        if request.url.path.startswith("/exams/") and request.method in ("POST", "PUT", "DELETE"):
            logger.info(
                f"Exam mutation attempted: {request.method} {request.url.path}",
                extra={
                    "security_event": "exam_mutation_attempt",
                    "ip": client_ip,
                    "method": request.method,
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            )
        
        response = await call_next(request)
        
        # Log failed auth attempts
        if request.url.path.startswith("/auth/") and response.status_code >= 400:
            logger.warning(
                f"Auth failure: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "security_event": "auth_failure",
                    "ip": client_ip,
                    "status_code": response.status_code,
                    "request_id": getattr(request.state, "request_id", "unknown"),
                }
            )
        
        return response

app.add_middleware(SecurityAuditMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(routes_auth.router)
app.include_router(routes_exam.router)
app.include_router(routes_chat.router)
app.include_router(routes_anonymizer.router)
app.include_router(routes_parent.router)
app.include_router(routes_ocr.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Planned Education API"}


# ── Global Exception Handler (no stack traces in production) ─────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={
            "security_event": "unhandled_exception",
            "exception_type": type(exc).__name__,
            "request_id": request_id,
            "path": request.url.path,
        }
    )
    if os.getenv("PLANNED_EDUCATION_ENV") == "development":
        raise
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
