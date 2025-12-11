import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Check if using PostgreSQL or SQLite
DATABASE_URL = os.getenv("DATABASE_URL")
USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith("postgresql")

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
else:
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
    # Note: Using UPPERCASE abbreviations for consistency with import normalization
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] == 0:
        units = [
            # Weight units
            ('Pound', 'LB', 'weight'),
            ('Ounce', 'OZ', 'weight'),
            ('Kilogram', 'KG', 'weight'),
            ('Gram', 'G', 'weight'),
            # Volume units
            ('Gallon', 'GAL', 'volume'),
            ('Quart', 'QT', 'volume'),
            ('Pint', 'PT', 'volume'),
            ('Cup', 'CUP', 'volume'),
            ('Fluid Ounce', 'FL OZ', 'volume'),
            ('Liter', 'L', 'volume'),
            ('Milliliter', 'ML', 'volume'),
            ('Tablespoon', 'TBSP', 'volume'),
            ('Teaspoon', 'TSP', 'volume'),
            # Count units
            ('Each', 'EA', 'count'),
            ('Count', 'CT', 'count'),
            ('Dozen', 'DOZ', 'count'),
            ('Case', 'CASE', 'count'),
            ('Box', 'BOX', 'count'),
            ('Bag', 'BAG', 'count'),
            ('Can', 'CAN', 'count'),
            ('Jar', 'JAR', 'count'),
            ('Pack', 'PACK', 'count'),
            ('Bunch', 'BUNCH', 'count'),
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

    # Run migrations for existing databases
    run_migrations()


def run_migrations():
    """Run database migrations to add missing columns/tables to existing databases."""
    print("[migrations] Checking for schema updates...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    migrations_run = 0

    # Helper to check if column exists
    def column_exists(table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    # Helper to add column if missing
    def add_column_if_missing(table, column, definition):
        nonlocal migrations_run
        if not column_exists(table, column):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            print(f"[migrations] Added {table}.{column}")
            migrations_run += 1

    # === RECIPES TABLE MIGRATIONS ===
    add_column_if_missing('recipes', 'method', 'TEXT')
    add_column_if_missing('recipes', 'category_path', 'TEXT')
    add_column_if_missing('recipes', 'servings', 'REAL')
    add_column_if_missing('recipes', 'serving_unit_id', 'INTEGER REFERENCES units(id)')

    # === RECIPE_INGREDIENTS TABLE MIGRATIONS ===
    add_column_if_missing('recipe_ingredients', 'sub_recipe_id', 'INTEGER REFERENCES recipes(id)')
    add_column_if_missing('recipe_ingredients', 'yield_percentage', 'REAL DEFAULT 100.00')

    # === UNITS TABLE - Add missing units ===
    # Check for missing uppercase units and add them
    required_units = [
        ('Pound', 'LB', 'weight'),
        ('Ounce', 'OZ', 'weight'),
        ('Kilogram', 'KG', 'weight'),
        ('Gram', 'G', 'weight'),
        ('Gallon', 'GAL', 'volume'),
        ('Quart', 'QT', 'volume'),
        ('Pint', 'PT', 'volume'),
        ('Cup', 'CUP', 'volume'),
        ('Fluid Ounce', 'FL OZ', 'volume'),
        ('Liter', 'L', 'volume'),
        ('Milliliter', 'ML', 'volume'),
        ('Tablespoon', 'TBSP', 'volume'),
        ('Teaspoon', 'TSP', 'volume'),
        ('Each', 'EA', 'count'),
        ('Count', 'CT', 'count'),
        ('Dozen', 'DOZ', 'count'),
        ('Case', 'CASE', 'count'),
        ('Box', 'BOX', 'count'),
        ('Bag', 'BAG', 'count'),
        ('Can', 'CAN', 'count'),
        ('Jar', 'JAR', 'count'),
        ('Pack', 'PACK', 'count'),
        ('Bunch', 'BUNCH', 'count'),
    ]

    for name, abbrev, unit_type in required_units:
        cursor.execute("SELECT id FROM units WHERE abbreviation = ?", (abbrev,))
        if not cursor.fetchone():
            try:
                cursor.execute(
                    "INSERT INTO units (name, abbreviation, unit_type) VALUES (?, ?, ?)",
                    (name, abbrev, unit_type)
                )
                print(f"[migrations] Added unit: {abbrev}")
                migrations_run += 1
            except sqlite3.IntegrityError:
                # Name might already exist with different abbreviation
                pass

    conn.commit()
    conn.close()

    if migrations_run > 0:
        print(f"[migrations] Completed {migrations_run} migration(s)")
    else:
        print("[migrations] Database schema is up to date")


class UniversalRow:
    """Row object that supports both tuple-style [0] and dict-style ['col'] access.

    This allows code to work with both SQLite (which returns sqlite3.Row objects)
    and PostgreSQL (which returns RealDictRow objects) transparently.
    """
    def __init__(self, data, use_postgres):
        if data is None:
            self._dict = None
            self._list = None
            self._original = None
        elif use_postgres:
            # RealDictCursor returns dict-like RealDictRow
            self._dict = dict(data)
            self._list = list(self._dict.values())
            self._original = None
        else:
            # sqlite3.Row already supports both access methods
            self._original = data
            self._dict = dict(data)
            self._list = None

    def __getitem__(self, key):
        if self._dict is None:
            raise TypeError("'NoneType' object is not subscriptable")

        if isinstance(key, int):
            # Integer indexing [0], [1], etc
            if self._list is not None:
                return self._list[key]
            else:
                # For SQLite, use original row which supports integer indexing
                return self._original[key]
        else:
            # String indexing ['column_name']
            return self._dict[key]

    def __iter__(self):
        """Make the row iterable, returning values in order."""
        if self._dict is None:
            return iter([])
        if self._list is not None:
            return iter(self._list)
        return iter(self._original)

    def __len__(self):
        """Return number of columns."""
        if self._dict is None:
            return 0
        return len(self._dict)

    def get(self, key, default=None):
        """Dict-style get method with default value."""
        if self._dict is None:
            return default
        return self._dict.get(key, default)

    def keys(self):
        """Return column names."""
        if self._dict is None:
            return []
        return self._dict.keys()

    def values(self):
        """Return column values."""
        if self._dict is None:
            return []
        return self._dict.values()

    def items(self):
        """Return (column, value) pairs."""
        if self._dict is None:
            return []
        return self._dict.items()


class DatabaseCursorWrapper:
    """Wrapper for database cursors that converts SQLite ? placeholders to PostgreSQL %s."""
    def __init__(self, cursor, use_postgres):
        self.cursor = cursor
        self.use_postgres = use_postgres
        self._last_insert_id = None

    def execute(self, query, params=None):
        """Execute query, converting placeholders if needed."""
        if self.use_postgres:
            if params:
                # Convert SQLite ? placeholders to PostgreSQL %s
                query = query.replace('?', '%s')
            # For INSERT statements, add RETURNING id to support lastrowid
            if query.strip().upper().startswith('INSERT'):
                if 'RETURNING' not in query.upper():
                    query = query.rstrip(';') + ' RETURNING id'
        result = self.cursor.execute(query, params)

        # Store the returned id for lastrowid property
        if self.use_postgres and query.strip().upper().startswith('INSERT'):
            try:
                returned_row = self.cursor.fetchone()
                if returned_row:
                    self._last_insert_id = returned_row.get('id') or returned_row[0]
                else:
                    self._last_insert_id = None
            except:
                self._last_insert_id = None

        return result

    def fetchone(self):
        """Fetch one row and wrap it in UniversalRow for consistent access."""
        result = self.cursor.fetchone()
        if result is None:
            return None
        return UniversalRow(result, self.use_postgres)

    def fetchall(self):
        """Fetch all rows and wrap them in UniversalRow for consistent access."""
        results = self.cursor.fetchall()
        return [UniversalRow(row, self.use_postgres) for row in results]

    def fetchmany(self, size=None):
        """Fetch many rows and wrap them in UniversalRow for consistent access."""
        results = self.cursor.fetchmany(size) if size else self.cursor.fetchmany()
        return [UniversalRow(row, self.use_postgres) for row in results]

    @property
    def lastrowid(self):
        if self.use_postgres:
            # Return the ID captured from RETURNING clause
            return self._last_insert_id
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


class DatabaseConnectionWrapper:
    """Wrapper for database connections that returns wrapped cursors."""
    def __init__(self, conn, use_postgres):
        self.conn = conn
        self.use_postgres = use_postgres

    def cursor(self):
        """Return wrapped cursor that handles placeholder conversion."""
        return DatabaseCursorWrapper(self.conn.cursor(), self.use_postgres)

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()

    def close(self):
        return self.conn.close()


@contextmanager
def get_db():
    """Context manager for database connections - supports PostgreSQL and SQLite."""
    if USE_POSTGRES:
        # PostgreSQL connection
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        try:
            yield DatabaseConnectionWrapper(conn, True)
        finally:
            conn.close()
    else:
        # SQLite connection
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        try:
            yield DatabaseConnectionWrapper(conn, False)
        finally:
            conn.close()


def dict_from_row(row):
    """Convert database row to dictionary - works with both PostgreSQL and SQLite."""
    if row is None:
        return None
    # Both psycopg2 RealDictCursor and sqlite3.Row can be converted with dict()
    return dict(row)


def dicts_from_rows(rows):
    """Convert list of database rows to list of dictionaries - works with both PostgreSQL and SQLite."""
    # Both psycopg2 RealDictCursor and sqlite3.Row can be converted with dict()
    return [dict(row) for row in rows]
