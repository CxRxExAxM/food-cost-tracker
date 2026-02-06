"""
PostgreSQL database connection with connection pooling.
"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

# Database connection from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Connection pool settings from centralized config
from .config import DB_MIN_CONNECTIONS, DB_MAX_CONNECTIONS

# Initialize the connection pool
_pool = None


def get_pool():
    """Get or create the connection pool (lazy initialization)."""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=DB_MIN_CONNECTIONS,
            maxconn=DB_MAX_CONNECTIONS,
            dsn=DATABASE_URL
        )
    return _pool


@contextmanager
def get_db():
    """
    Context manager for PostgreSQL database connections.
    Gets a connection from the pool and returns it when done.
    Returns a connection with RealDictCursor that returns rows as dictionaries.
    """
    pool = get_pool()
    conn = pool.getconn()

    # Set the cursor factory for this connection
    conn.cursor_factory = RealDictCursor

    try:
        yield conn
    except Exception:
        # Rollback on any error to reset connection state
        conn.rollback()
        raise
    finally:
        # Return connection to pool (don't close it)
        pool.putconn(conn)


def dict_from_row(row):
    """Convert database row to dictionary."""
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    """Convert list of database rows to list of dictionaries."""
    return [dict(row) for row in rows]
