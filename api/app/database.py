import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent.parent.parent / "db" / "food_cost_tracker.db"


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row):
    """Convert sqlite3.Row to dictionary."""
    return dict(row) if row else None


def dicts_from_rows(rows):
    """Convert list of sqlite3.Row to list of dictionaries."""
    return [dict(row) for row in rows]
