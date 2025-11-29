"""
Database startup utilities.
Handles both SQLite and PostgreSQL initialization.
"""
import os
import sys
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

            # Change to project root for alembic
            original_cwd = Path.cwd()
            os.chdir(project_root)

            # Import and run alembic directly
            from alembic.config import Config
            from alembic import command

            # Use absolute path to alembic.ini
            alembic_ini_path = project_root / "alembic.ini"
            alembic_cfg = Config(str(alembic_ini_path))
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)

            print(f"[db_startup] Running migrations from {project_root}")
            command.upgrade(alembic_cfg, "head")
            print("[db_startup] Migrations completed successfully")

            # Change back to original directory
            os.chdir(original_cwd)

        except Exception as e:
            print(f"[db_startup] Migration failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
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
