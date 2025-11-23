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
    print(f"[init_db] Initializing database at: {DB_PATH}")

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
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL,
            contact_info TEXT,
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
            name TEXT UNIQUE NOT NULL,
            abbreviation TEXT UNIQUE NOT NULL,
            unit_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed default units if table is empty
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        units = [
            ('Pound', 'lb', 'weight'),
            ('Ounce', 'oz', 'weight'),
            ('Kilogram', 'kg', 'weight'),
            ('Gram', 'g', 'weight'),
            ('Gallon', 'gal', 'volume'),
            ('Quart', 'qt', 'volume'),
            ('Pint', 'pt', 'volume'),
            ('Cup', 'cup', 'volume'),
            ('Fluid Ounce', 'fl oz', 'volume'),
            ('Liter', 'L', 'volume'),
            ('Milliliter', 'mL', 'volume'),
            ('Each', 'ea', 'count'),
            ('Dozen', 'doz', 'count'),
            ('Case', 'case', 'count'),
        ]
        cursor.executemany(
            "INSERT INTO units (name, abbreviation, unit_type) VALUES (?, ?, ?)",
            units
        )

    # Create common_products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS common_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            common_name TEXT UNIQUE NOT NULL,
            category TEXT,
            subcategory TEXT,
            preferred_unit_id INTEGER REFERENCES units(id),
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            allergen_vegan INTEGER DEFAULT 0,
            allergen_vegetarian INTEGER DEFAULT 0,
            allergen_gluten INTEGER DEFAULT 0,
            allergen_crustation INTEGER DEFAULT 0,
            allergen_egg INTEGER DEFAULT 0,
            allergen_mollusk INTEGER DEFAULT 0,
            allergen_fish INTEGER DEFAULT 0,
            allergen_lupin INTEGER DEFAULT 0,
            allergen_dairy INTEGER DEFAULT 0,
            allergen_tree_nuts INTEGER DEFAULT 0,
            allergen_peanuts INTEGER DEFAULT 0,
            allergen_sesame INTEGER DEFAULT 0,
            allergen_soy INTEGER DEFAULT 0,
            allergen_sulphur_dioxide INTEGER DEFAULT 0,
            allergen_mustard INTEGER DEFAULT 0,
            allergen_celery INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            brand TEXT,
            category TEXT,
            pack INTEGER,
            size REAL,
            unit_id INTEGER REFERENCES units(id),
            common_product_id INTEGER REFERENCES common_products(id),
            is_catch_weight INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create distributor_products junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS distributor_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_id INTEGER REFERENCES distributors(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            distributor_sku TEXT NOT NULL,
            distributor_name TEXT,
            is_available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(distributor_id, distributor_sku)
        )
    """)

    # Create price_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_product_id INTEGER REFERENCES distributor_products(id) ON DELETE CASCADE,
            case_price REAL NOT NULL,
            unit_price REAL,
            effective_date DATE NOT NULL,
            import_batch_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(distributor_product_id, effective_date)
        )
    """)

    # Create import_batches table
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

    # Create recipes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            category_path TEXT,
            yield_amount REAL,
            yield_unit_id INTEGER REFERENCES units(id),
            servings REAL,
            serving_unit_id INTEGER REFERENCES units(id),
            prep_time_minutes INTEGER,
            cook_time_minutes INTEGER,
            method TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create recipe_ingredients table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            common_product_id INTEGER REFERENCES common_products(id),
            sub_recipe_id INTEGER REFERENCES recipes(id),
            quantity REAL NOT NULL,
            unit_id INTEGER REFERENCES units(id),
            yield_percentage REAL DEFAULT 100.00,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_common_product ON products(common_product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_common_products_name ON common_products(common_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_distributor_products_distributor ON distributor_products(distributor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_distributor_products_product ON distributor_products(product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_distributor_products_sku ON distributor_products(distributor_sku)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_dist_prod ON price_history(distributor_product_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_history_date ON price_history(effective_date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_common_product ON recipe_ingredients(common_product_id)")

    conn.commit()

    # Verify tables were created
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"[init_db] Tables created: {tables}")

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
