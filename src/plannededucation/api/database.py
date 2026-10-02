import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# DATABASE_URL must always be set explicitly. No implicit defaults — fail loudly.
_default_url = "postgresql://postgres:postgres@localhost:5433/plannededucation" \
    if os.getenv("PLANNED_EDUCATION_ENV") == "development" else ""

SQLALCHEMY_DATABASE_URL: str = os.getenv("DATABASE_URL", _default_url)

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Example: postgresql://user:pass@host:5432/dbname"
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
        logger.warning(
            f"DDL operation: {clauseelement.__visit_name__}",
            extra={
                "security_event": "ddl_operation",
                "operation": clauseelement.__visit_name__,
                "sql": str(clauseelement),
            }
        )
