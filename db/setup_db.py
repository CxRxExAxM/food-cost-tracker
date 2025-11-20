import sqlite3
from pathlib import Path

# Database file location
DB_PATH = Path(__file__).parent / "food_cost_tracker.db"


def create_database():
    """Create SQLite database and initialize schema."""

    # Remove existing database if it exists
    if DB_PATH.exists():
        response = input(f"Database already exists at {DB_PATH}. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Database setup cancelled.")
            return
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Creating database schema...")

    # Distributors table
    cursor.execute("""
        CREATE TABLE distributors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL,
            contact_info TEXT, -- JSON as text
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Units of measure
    cursor.execute("""
        CREATE TABLE units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            abbreviation TEXT UNIQUE NOT NULL,
            unit_type TEXT NOT NULL, -- 'weight', 'volume', 'count'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Common Products (user-defined normalized ingredients)
    cursor.execute("""
        CREATE TABLE common_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            common_name TEXT UNIQUE NOT NULL,
            category TEXT,
            subcategory TEXT,
            preferred_unit_id INTEGER REFERENCES units(id),
            notes TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Products catalog (distributor-specific)
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            brand TEXT,
            category TEXT,
            pack INTEGER, -- Number of units per case
            size REAL, -- Size of individual unit
            unit_id INTEGER REFERENCES units(id),
            common_product_id INTEGER REFERENCES common_products(id), -- Link to common product
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Distributor products (junction table with distributor-specific info)
    cursor.execute("""
        CREATE TABLE distributor_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_id INTEGER REFERENCES distributors(id) ON DELETE CASCADE,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            distributor_sku TEXT NOT NULL, -- Distributor's item code/SUPC
            distributor_name TEXT, -- How distributor names this product
            is_available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(distributor_id, distributor_sku)
        )
    """)

    # Price history
    cursor.execute("""
        CREATE TABLE price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distributor_product_id INTEGER REFERENCES distributor_products(id) ON DELETE CASCADE,
            case_price REAL NOT NULL,
            unit_price REAL, -- Calculated: case_price / (pack * size)
            effective_date DATE NOT NULL,
            import_batch_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(distributor_product_id, effective_date)
        )
    """)

    # Import batches (track CSV imports)
    cursor.execute("""
        CREATE TABLE import_batches (
            id TEXT PRIMARY KEY, -- UUID as text
            distributor_id INTEGER REFERENCES distributors(id),
            filename TEXT NOT NULL,
            rows_imported INTEGER,
            rows_failed INTEGER,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)

    # Recipes
    cursor.execute("""
        CREATE TABLE recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            yield_amount REAL, -- How many portions/servings
            yield_unit_id INTEGER REFERENCES units(id),
            prep_time_minutes INTEGER,
            cook_time_minutes INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Recipe ingredients
    cursor.execute("""
        CREATE TABLE recipe_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
            common_product_id INTEGER REFERENCES common_products(id), -- References common products, not distributor-specific
            quantity REAL NOT NULL,
            unit_id INTEGER REFERENCES units(id),
            yield_percentage REAL DEFAULT 100.00, -- Account for waste/trim
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("Creating indexes...")

    # Indexes for performance
    cursor.execute("CREATE INDEX idx_products_common_product ON products(common_product_id)")
    cursor.execute("CREATE INDEX idx_common_products_name ON common_products(common_name)")
    cursor.execute("CREATE INDEX idx_distributor_products_distributor ON distributor_products(distributor_id)")
    cursor.execute("CREATE INDEX idx_distributor_products_product ON distributor_products(product_id)")
    cursor.execute("CREATE INDEX idx_distributor_products_sku ON distributor_products(distributor_sku)")
    cursor.execute("CREATE INDEX idx_price_history_dist_prod ON price_history(distributor_product_id)")
    cursor.execute("CREATE INDEX idx_price_history_date ON price_history(effective_date DESC)")
    cursor.execute("CREATE INDEX idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id)")
    cursor.execute("CREATE INDEX idx_recipe_ingredients_common_product ON recipe_ingredients(common_product_id)")

    # Triggers for updated_at
    for table in ['distributors', 'common_products', 'products', 'distributor_products', 'recipes', 'recipe_ingredients']:
        cursor.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            AFTER UPDATE ON {table}
            FOR EACH ROW
            BEGIN
                UPDATE {table} SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

    print("Seeding initial data...")

    # Insert distributors
    distributors = [
        ('Sysco', 'sysco'),
        ('Vesta', 'vesta'),
        ('SM Seafood', 'smseafood'),
        ('Shamrock', 'shamrock'),
        ('Noble Bread', 'noblebread'),
        ('Sterling', 'sterling')
    ]
    cursor.executemany("INSERT INTO distributors (name, code) VALUES (?, ?)", distributors)

    # Insert common units
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
        ('Tablespoon', 'tbsp', 'volume'),
        ('Teaspoon', 'tsp', 'volume'),
        ('Each', 'ea', 'count'),
        ('Dozen', 'doz', 'count'),
        ('Case', 'case', 'count'),
        ('Box', 'box', 'count'),
        ('Bag', 'bag', 'count'),
        ('Can', 'can', 'count'),
        ('Jar', 'jar', 'count')
    ]
    cursor.executemany("INSERT INTO units (name, abbreviation, unit_type) VALUES (?, ?, ?)", units)

    conn.commit()
    conn.close()

    print(f"\n✓ Database created successfully at: {DB_PATH}")
    print(f"✓ Tables created: 10")
    print(f"✓ Distributors seeded: {len(distributors)}")
    print(f"✓ Units seeded: {len(units)}")
    print("\nDatabase structure:")
    print("  - common_products: User-defined normalized ingredients")
    print("  - products: Distributor-specific products (linked to common_products)")
    print("  - recipe_ingredients: References common_products for flexibility")
    print("\nYou can now start importing your cleaned CSV data!")


if __name__ == "__main__":
    create_database()
