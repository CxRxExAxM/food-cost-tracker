"""
PostgreSQL database connection and utilities.
"""
import os
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")


@contextmanager
def get_db():
    """
    Context manager for PostgreSQL database connections.
    Returns a connection with RealDictCursor that returns rows as dictionaries.
    """
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row):
    """Convert database row to dictionary."""
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    """Convert list of database rows to list of dictionaries."""
    return [dict(row) for row in rows]
