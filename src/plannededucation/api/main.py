import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager

from .database import engine, Base
from . import models, routes_auth, routes_exam, routes_chat, routes_anonymizer, routes_parent


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
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if os.getenv("PLANNED_EDUCATION_ENV") != "development":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

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
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(routes_auth.router)
app.include_router(routes_exam.router)
app.include_router(routes_chat.router)
app.include_router(routes_anonymizer.router)
app.include_router(routes_parent.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Planned Education API"}
