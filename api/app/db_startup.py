"""
Database startup utilities.
Handles both SQLite and PostgreSQL initialization.
"""
import os
import subprocess
from pathlib import Path


def run_migrations():
    """Run Alembic migrations if using PostgreSQL."""
    database_url = os.getenv('DATABASE_URL')

    if database_url and database_url.startswith('postgresql'):
        print("[db_startup] PostgreSQL detected - running migrations...")
        try:
            # Run alembic upgrade head
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'],
                capture_output=True,
                text=True,
                check=True
            )
            print("[db_startup] Migrations completed successfully")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"[db_startup] Migration failed: {e}")
            if e.stderr:
                print(e.stderr)
            raise
    else:
        print("[db_startup] SQLite detected - using init_db()")
        from api.app.database import init_db
        init_db()


def initialize_database():
    """Initialize database on application startup."""
    print("[db_startup] Initializing database...")
    run_migrations()
    print("[db_startup] Database initialization complete")
