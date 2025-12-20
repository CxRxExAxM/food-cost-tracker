"""
Database startup utilities - PostgreSQL with Alembic migrations.
"""
import os
from pathlib import Path


def initialize_database():
    """Run Alembic migrations on application startup."""
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    print("[db_startup] PostgreSQL detected - running migrations...")

    try:
        # Find project root (where alembic directory lives)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # api/app/db_startup.py -> project root

        # Import and run alembic directly
        from alembic.config import Config
        from alembic import command

        # Create config programmatically (more robust than parsing ini file in Docker)
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Set the alembic directory as the base for version locations
        alembic_cfg.config_file_name = str(project_root / "alembic.ini")

        print(f"[db_startup] Running migrations from {project_root / 'alembic'}")
        command.upgrade(alembic_cfg, "head")
        print("[db_startup] Migrations completed successfully")

    except Exception as e:
        print(f"[db_startup] Migration failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
