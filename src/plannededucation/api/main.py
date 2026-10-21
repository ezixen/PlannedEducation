import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

# ── OpenTelemetry Observability ──────────────────────────────────────────────
from opentelemetry import metrics, trace
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, start_http_server
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from . import (
    routes_admin,
    routes_ai,
    routes_alerts,
    routes_anonymizer,
    routes_archive,
    routes_auth,
    routes_chat,
    routes_chatgpt,
    routes_exam,
    routes_notifications,
    routes_ocr,
    routes_packages,
    routes_parent,
    routes_proctoring,
    routes_stt,
)
from .database import Base, engine


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
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Configure root & application loggers with separated info and error log files
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plannededucation")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.propagate = False  # avoid duplicate plain-text lines from the root logger

if os.getenv("PLANNED_EDUCATION_ENV") != "test":
    try:
        log_dir = os.getenv("PLANNED_EDUCATION_LOG_DIR", os.path.join(os.getcwd(), "logs"))
        os.makedirs(log_dir, exist_ok=True)
        info_file_handler = logging.FileHandler(os.path.join(log_dir, "backend.log"), encoding="utf-8")
        info_file_handler.setLevel(logging.INFO)
        info_file_handler.setFormatter(JSONFormatter())

        err_file_handler = logging.FileHandler(os.path.join(log_dir, "backend_error.log"), encoding="utf-8")
        err_file_handler.setLevel(logging.WARNING)
        err_file_handler.setFormatter(JSONFormatter())

        logger.addHandler(info_file_handler)
        logger.addHandler(err_file_handler)
        logging.getLogger("uvicorn.error").addHandler(err_file_handler)
        logging.getLogger("uvicorn.access").addHandler(info_file_handler)
    except OSError:
        pass

logger.setLevel(logging.INFO)


# ── Prometheus Metrics ───────────────────────────────────────────────────────
# Custom metrics for SLO tracking (guarded against duplicate registration in test/reload environments)

try:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
    )
    ACTIVE_USERS = Gauge(
        "active_users",
        "Number of active users",
    )
    EXAM_SUBMISSIONS = Counter(
        "exam_submissions_total",
        "Total exam submissions",
        ["status"],
    )
    AI_GRADING_REQUESTS = Counter(
        "ai_grading_requests_total",
        "Total AI grading requests",
        ["provider", "status"],
    )
except Exception:
    REQUEST_COUNT = REGISTRY._names_to_collectors.get("http_requests_total")
    REQUEST_LATENCY = REGISTRY._names_to_collectors.get("http_request_duration_seconds")
    ACTIVE_USERS = REGISTRY._names_to_collectors.get("active_users")
    EXAM_SUBMISSIONS = REGISTRY._names_to_collectors.get("exam_submissions_total")
    AI_GRADING_REQUESTS = REGISTRY._names_to_collectors.get("ai_grading_requests_total")

# Start Prometheus metrics server on port 9090 (skip in test mode or if port is busy)
if os.getenv("PLANNED_EDUCATION_ENV") != "test":
    try:
        start_http_server(9090)
    except OSError:
        logger.warning("Prometheus metrics port 9090 already in use; skipping start_http_server.")

# Configure OpenTelemetry
resource = Resource.create({"service.name": "plannededucation-api"})
trace_provider = TracerProvider(resource=resource)
if os.getenv("OTEL_CONSOLE_EXPORT", "").lower() == "true":
    trace_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(trace_provider)

metric_reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# Get tracer and meter
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Custom metrics instruments
request_counter = meter.create_counter(
    "http_requests_total",
    description="Total HTTP requests",
)
request_latency = meter.create_histogram(
    "http_request_duration_seconds",
    description="HTTP request latency in seconds",
    unit="s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize OpenTelemetry instrumentation (skip_dep_check=True supports SQLAlchemy 2.1+)
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:
        logger.warning(f"FastAPI OpenTelemetry instrumentation skipped: {exc}")
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine, skip_dep_check=True)
    except Exception as exc:
        logger.warning(f"SQLAlchemy OpenTelemetry instrumentation skipped: {exc}")
    try:
        RequestsInstrumentor().instrument(skip_dep_check=True)
    except Exception as exc:
        logger.warning(f"Requests OpenTelemetry instrumentation skipped: {exc}")

    Base.metadata.create_all(bind=engine)

    # Start background midnight autobackup task (when not in test mode)
    backup_task = None
    if os.getenv("PLANNED_EDUCATION_ENV") != "test":
        from . import backup_service
        backup_task = asyncio.create_task(backup_service.run_midnight_autobackup_scheduler())

    yield

    if backup_task:
        backup_task.cancel()
        with suppress(asyncio.CancelledError):
            await backup_task


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
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        # Content Security Policy - restrictive by default
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://accounts.google.com https://apis.google.com; "
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
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
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
_raw_cors = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175",
)
if os.getenv("PLANNED_EDUCATION_ENV") == "development":
    _raw_cors += ",http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"

# If config/deployment.json exists, ensure its cors_origins are also merged
try:
    _dep_json = os.path.join(os.getcwd(), "config", "deployment.json")
    if os.path.isfile(_dep_json):
        with open(_dep_json, encoding="utf-8") as _f:
            _ddata = json.load(_f)
            if isinstance(_ddata, dict) and _ddata.get("cors_origins"):
                _raw_cors += f",{_ddata['cors_origins']}"
except Exception:
    pass

cors_origins = [
    origin.strip()
    for origin in _raw_cors.split(",")
    if origin.strip()
]
# Ensure both localhost and 127.0.0.1 equivalents are accepted
expanded_origins = set(cors_origins)
for origin in list(expanded_origins):
    if "localhost" in origin:
        expanded_origins.add(origin.replace("localhost", "127.0.0.1"))
    elif "127.0.0.1" in origin:
        expanded_origins.add(origin.replace("127.0.0.1", "localhost"))
cors_origins = list(expanded_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-SafeExamBrowser-RequestHash",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Request-ID",
    ],
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

# ── Metrics Middleware (Prometheus + OpenTelemetry) ──────────────────────────
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path

        response = await call_next(request)

        duration = time.time() - start_time
        status_code = response.status_code

        # Prometheus metrics
        REQUEST_COUNT.labels(method=method, endpoint=path, status_code=status_code).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(duration)

        # OpenTelemetry metrics
        request_counter.add(
            1, {"method": method, "endpoint": path, "status_code": str(status_code)}
        )
        request_latency.record(duration, {"method": request.method, "endpoint": path})

        return response

app.add_middleware(MetricsMiddleware)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(routes_auth.router)
app.include_router(routes_exam.router)
app.include_router(routes_chat.router)
app.include_router(routes_anonymizer.router)
app.include_router(routes_parent.router)
app.include_router(routes_ocr.router)
app.include_router(routes_stt.router)
app.include_router(routes_proctoring.router)
app.include_router(routes_packages.router)
app.include_router(routes_ai.router)
app.include_router(routes_chatgpt.router)
app.include_router(routes_archive.router)
app.include_router(routes_admin.router)
app.include_router(routes_alerts.router)
app.include_router(routes_notifications.router)


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
