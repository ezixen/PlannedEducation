import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .db_encryption import is_encryption_enabled  # noqa: E402

logger = logging.getLogger("plannededucation.db")

# ── Database Encryption Initialization ───────────────────────────────────────
# Initialize field-level encryption for sensitive columns.
# This must be imported before any model usage to register encrypt/decrypt
# event listeners on SQLAlchemy models.

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
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", _default_url)

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Example: postgresql+psycopg://user:pass@host:5432/dbname"
    )

is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine_kwargs: dict = {}
if is_sqlite:
    # SQLite: needed for multi-threaded FastAPI use in tests
    engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    # A normal ``sqlite:///`` URL uses the stdlib driver; passing a SQLCipher
    # key to it is unsupported and can silently create a plaintext database.
    # Production/staging deployments must use PostgreSQL or an explicitly
    # configured, verified SQLCipher dialect.
    if is_encryption_enabled() and os.getenv("PLANNED_EDUCATION_ENV", "").lower() in {
        "production",
        "staging",
    } and "pysqlcipher" not in SQLALCHEMY_DATABASE_URL:
        raise RuntimeError(
            "Encrypted production SQLite requires a verified SQLCipher dialect; "
            "use PostgreSQL or an explicit sqlite+pysqlcipher URL."
        )
else:
    # PostgreSQL: connection pool tuning for production
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True  # Detect stale connections
    # SSL mode for production
    if os.getenv("PLANNED_EDUCATION_ENV") != "development":
        engine_kwargs["connect_args"] = {"sslmode": "require"}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, connection_record):
        del connection_record
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=30000")
            if _is_test and ":memory:" not in SQLALCHEMY_DATABASE_URL:
                cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


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
