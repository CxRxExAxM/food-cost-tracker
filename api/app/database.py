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

    # Create users table
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

    # Create distributors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distributors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default distributors if table is empty
    cursor.execute("SELECT COUNT(*) FROM distributors")
    if cursor.fetchone()[0] == 0:
        distributors = [
            ('Sysco', 'sysco'),
            ('Vesta', 'vesta'),
            ('SM Seafood', 'smseafood'),
            ('Shamrock', 'shamrock'),
            ('Noble Bread', 'noblebread'),
            ('Sterling', 'sterling'),
        ]
        cursor.executemany(
            "INSERT INTO distributors (name, code) VALUES (?, ?)",
            distributors
        )

    # Create units table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            abbreviation TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('weight', 'volume', 'count', 'length')),
            base_unit_id INTEGER,
            conversion_factor REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (base_unit_id) REFERENCES units(id)
        )
    """)

    # Seed default units if table is empty
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        units = [
            ('Pound', 'lb', 'weight', None, None),
            ('Ounce', 'oz', 'weight', 1, 0.0625),
            ('Kilogram', 'kg', 'weight', 1, 2.20462),
            ('Gram', 'g', 'weight', 1, 0.00220462),
            ('Gallon', 'gal', 'volume', None, None),
            ('Quart', 'qt', 'volume', 5, 0.25),
            ('Pint', 'pt', 'volume', 5, 0.125),
            ('Cup', 'cup', 'volume', 5, 0.0625),
            ('Fluid Ounce', 'fl oz', 'volume', 5, 0.0078125),
            ('Liter', 'L', 'volume', 5, 0.264172),
            ('Milliliter', 'mL', 'volume', 5, 0.000264172),
            ('Each', 'ea', 'count', None, None),
            ('Dozen', 'doz', 'count', 12, 12),
            ('Case', 'case', 'count', 12, None),
        ]
        cursor.executemany(
            "INSERT INTO units (name, abbreviation, type, base_unit_id, conversion_factor) VALUES (?, ?, ?, ?, ?)",
            units
        )

    # Create common_products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT,
            default_unit_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (default_unit_id) REFERENCES units(id)
        )
    """)

    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_id INTEGER NOT NULL,
            distributor_code TEXT,
            name TEXT NOT NULL,
            description TEXT,
            brand TEXT,
            pack_size TEXT,
            unit_id INTEGER,
            case_price REAL,
            unit_price REAL,
            price_per_unit REAL,
            common_product_id INTEGER,
            is_active INTEGER DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (distributor_id) REFERENCES distributors(id),
            FOREIGN KEY (unit_id) REFERENCES units(id),
            FOREIGN KEY (common_product_id) REFERENCES common_products(id)
        )
    """)

    # Create recipes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            yield_amount REAL,
            yield_unit_id INTEGER,
            prep_time_minutes INTEGER,
            cook_time_minutes INTEGER,
            instructions TEXT,
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (yield_unit_id) REFERENCES units(id)
        )
    """)

    # Create recipe_ingredients table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER NOT NULL,
            common_product_id INTEGER,
            product_id INTEGER,
            quantity REAL NOT NULL,
            unit_id INTEGER NOT NULL,
            preparation TEXT,
            notes TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (common_product_id) REFERENCES common_products(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (unit_id) REFERENCES units(id)
        )
    """)

    # Create import_batches table for tracking CSV imports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS import_batches (
            id TEXT PRIMARY KEY,
            distributor_id INTEGER REFERENCES distributors(id),
            filename TEXT NOT NULL,
            rows_imported INTEGER,
            rows_failed INTEGER,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
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
