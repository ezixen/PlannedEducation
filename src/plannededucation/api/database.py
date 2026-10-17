import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE_URL must always be set explicitly. No implicit defaults — fail loudly.
# For tests, use SQLite in-memory. For development, use PostgreSQL.
# Check for test environment FIRST, before any other logic
_is_test = os.getenv("PLANNED_EDUCATION_ENV") == "test" or os.getenv("DATABASE_URL", "").startswith("sqlite")

if os.getenv("PLANNED_EDUCATION_ENV") == "test":
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test_plannededucation.db")
elif os.getenv("DATABASE_URL", "").startswith("sqlite"):
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
else:
    _default_url = "postgresql+psycopg://postgres:postgres@localhost:5433/plannededucation" \
        if os.getenv("PLANNED_EDUCATION_ENV") == "development" else ""
    SQLALCHEMY_DATABASE_URL: str = os.getenv("DATABASE_URL", _default_url)

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Example: postgresql+psycopg://user:pass@host:5432/dbname"
    )

is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine_kwargs: dict = {}
if is_sqlite:
    # SQLite: needed for multi-threaded FastAPI use in tests
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: connection pool tuning for production
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True  # Detect stale connections
    # SSL mode for production
    if os.getenv("PLANNED_EDUCATION_ENV") != "development":
        engine_kwargs["connect_args"] = {"sslmode": "require"}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Database Security Event Listeners ────────────────────────────────────────
# Log all DDL changes for audit trail
@event.listens_for(engine, "before_execute")
def log_ddl(conn, clauseelement, multiparams, params, execution_options):
    if hasattr(clauseelement, "__visit_name__") and clauseelement.__visit_name__ in (
        "create_table", "drop_table", "alter_table", "create_index", "drop_index"
    ):
        import logging
        logger = logging.getLogger("plannededucation.db")
        op = clauseelement.__visit_name__
        log_fn = (
            logger.debug
            if (_is_test or op in ("create_table", "create_index"))
            else logger.warning
        )
        log_fn(
            f"DDL operation: {op}",
            extra={
                "security_event": "ddl_operation",
                "operation": op,
                "sql": str(clauseelement),
            }
        )
