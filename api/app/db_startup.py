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
            # Find project root (where alembic.ini lives)
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent  # api/app/db_startup.py -> project root

            # Use python -m alembic instead of alembic command for better compatibility
            import sys
            result = subprocess.run(
                [sys.executable, '-m', 'alembic', 'upgrade', 'head'],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, 'DATABASE_URL': database_url}
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
