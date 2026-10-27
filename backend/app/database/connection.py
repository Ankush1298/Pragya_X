"""
Database Connection and Initialization Layer
PostgreSQL connection pool for local development and managed Supabase deployments.
Owned by: Nagin (Supabase Database Architecture) & Arsh (Backend)
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)
logging.getLogger("psycopg.pool").setLevel(logging.CRITICAL)

# psycopg 3 imports
try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool, PoolTimeout as psycopg_pool_timeout

    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    dict_row = None
    ConnectionPool = None


class DatabaseConnectionError(Exception):
    """Raised when database connection fails without leaking secrets."""


_pool: Any | None = None
_transaction_connection = ContextVar("transaction_connection", default=None)


class PostgresCursorWrapper:
    """Cursor wrapper that translates '?' placeholders to '%s' for psycopg 3."""

    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, query: str, params=None):
        if params is not None:
            translated_query = query.replace("?", "%s") if isinstance(query, str) and "?" in query else query
            return self._cur.execute(translated_query, params)
        return self._cur.execute(query)

    def executemany(self, query: str, params_seq):
        translated_query = query.replace("?", "%s") if isinstance(query, str) and "?" in query else query
        return self._cur.executemany(translated_query, params_seq)

    @staticmethod
    def _normalize_row(row):
        if not row or not isinstance(row, dict):
            return row
        return {
            k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()
        }

    def fetchone(self):
        row = self._cur.fetchone()
        return self._normalize_row(row)

    def fetchall(self):
        rows = self._cur.fetchall()
        if not rows:
            return rows
        return [self._normalize_row(r) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __getattr__(self, name):
        return getattr(self._cur, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._cur.__exit__(exc_type, exc_val, exc_tb)


class PostgresConnectionWrapper:
    """Connection wrapper that returns PostgresCursorWrapper cursors."""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self, *args, **kwargs):
        cur = self._conn.cursor(*args, **kwargs)
        return PostgresCursorWrapper(cur)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._conn.rollback()
        else:
            self._conn.commit()
        return False


def get_db_pool() -> Any:
    """Returns or initializes the psycopg 3 connection pool."""
    global _pool
    if not PSYCOPG_AVAILABLE:
        raise DatabaseConnectionError(
            "psycopg and psycopg_pool must be installed for PostgreSQL support."
        )

    if _pool is not None and not _pool.closed:
        return _pool

    database_url = settings.DATABASE_URL
    if not database_url:
        raise DatabaseConnectionError("DATABASE_URL is not set.")

    # Enforce SSL for PostgreSQL connection unless sslmode is explicitly defined
    conn_kwargs = {"row_factory": dict_row, "autocommit": False}
    if "sslmode=" not in database_url.lower():
        conn_kwargs["sslmode"] = "require"

    try:
        _pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=10,
            timeout=10.0,
            max_idle=300.0,
            kwargs=conn_kwargs,
            open=True,
        )
        return _pool
    except Exception:
        sanitized = settings.sanitized_database_url
        raise DatabaseConnectionError(
            f"Failed to initialize PostgreSQL connection pool to {sanitized}: connection error."
        ) from None


def close_db_pool() -> None:
    """Gracefully closes the PostgreSQL connection pool."""
    global _pool
    if _pool is not None:
        try:
            _pool.close()
        except Exception:
            pass
        finally:
            _pool = None


@contextmanager
def get_db():
    """Acquire a PostgreSQL connection; errors roll back the entire transaction."""
    current = _transaction_connection.get()
    if current is not None:
        yield current
        return
    pool = get_db_pool()
    try:
        with pool.connection() as conn:
            yield PostgresConnectionWrapper(conn)
    except psycopg_pool_timeout as exc:
        raise DatabaseConnectionError("PostgreSQL connection unavailable") from None


def ping_db() -> dict[str, Any]:
    """Read-only readiness check; never exposes a connection string."""
    try:
        with get_db() as conn:
            conn.cursor().execute("SELECT 1")
        return {"status": "healthy", "engine": "PostgreSQL", "connected": True}
    except Exception:
        return {"status": "unhealthy", "engine": "PostgreSQL", "connected": False,
                "error": "PostgreSQL connection unavailable; check private DATABASE_URL configuration."}


def verify_authorization() -> dict[str, Any]:
    """Verifies the active database role and RLS bypass permissions for PostgreSQL."""
    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute("""
                    SELECT current_user AS role_name,
                           rolsuper AS is_superuser,
                           rolbypassrls AS bypasses_rls
                    FROM pg_roles
                    WHERE rolname = current_user;
                """)
            row = cur.fetchone()
            if row:
                return {
                    "engine": "postgresql",
                    "current_user": row.get("role_name"),
                    "is_superuser": bool(row.get("is_superuser")),
                    "bypasses_rls": bool(row.get("bypasses_rls")),
                    "authorized": True,
                }
            return {
                "engine": "postgresql",
                "current_user": "unknown",
                "authorized": False,
                "error": "Could not inspect role in pg_roles",
            }
    except Exception as exc:
        return {
            "engine": "postgresql",
            "authorized": False,
            "error": f"Authorization verification query failed: {type(exc).__name__}",
        }




def init_db():
    """Check connectivity and migration history without mutating the database."""
    if not settings.DATABASE_URL:
        raise DatabaseConnectionError("DATABASE_URL is required. Configure a PostgreSQL database and run migrations.")
    if not ping_db()["connected"]:
        raise DatabaseConnectionError("PostgreSQL startup verification failed.")
    from .migrate import pending_migrations
    if pending_migrations(settings.DATABASE_URL):
        raise DatabaseConnectionError("Database migrations are pending. Run python -m backend.app.database.migrate.")


def atomic_write(fn):
    """One transaction across nested repositories, serialized across backend workers.

    The shared advisory lock deliberately favors correctness for the demo workload.
    Replace with consistently ordered aggregate row locks before scaling writes.
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if _transaction_connection.get() is not None:
            return fn(*args, **kwargs)
        with get_db() as conn:
            conn.cursor().execute("SELECT pg_advisory_xact_lock(724130612)")
            token = _transaction_connection.set(conn)
            try:
                return fn(*args, **kwargs)
            finally:
                _transaction_connection.reset(token)
    return wrapped
