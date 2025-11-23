import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Use DATABASE_PATH env var if set (for Render), otherwise use local db folder
_default_db_path = Path(__file__).parent.parent.parent / "db" / "food_cost_tracker.db"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(_default_db_path)))


def init_db():
    """Initialize database with required tables if they don't exist."""
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL DEFAULT 'viewer' CHECK(role IN ('admin', 'chef', 'viewer')),
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


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
