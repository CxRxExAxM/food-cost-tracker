#!/usr/bin/env python3
"""
Run database migration 002: Add outlet_id to price_history
Standalone version - works with DATABASE_URL env var
"""
import os
import sys

# Check for DATABASE_URL
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL environment variable not set")
    print("")
    print("Please set it first:")
    print('  export DATABASE_URL="postgres://user:pass@host/dbname"')
    print("")
    print("Get it from: Render Dashboard -> Your Database -> Connect -> External Connection")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ Error: psycopg2 not installed")
    print("")
    print("Install it with:")
    print("  pip3 install psycopg2-binary")
    sys.exit(1)

def run_migration():
    print("Starting migration 002: Add outlet_id to price_history...")
    print(f"Connecting to database...")

    # Convert Render's postgres:// to postgresql:// if needed
    db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    cursor = conn.cursor()

    try:
        # Step 1: Add outlet_id column
        print("\nStep 1: Adding outlet_id column...")
        cursor.execute("ALTER TABLE price_history ADD COLUMN IF NOT EXISTS outlet_id INTEGER")
        print("✓ Column added")

        # Step 2: Populate from import_batches
        print("\nStep 2: Populating outlet_id from import_batches...")
        cursor.execute("""
            UPDATE price_history ph
            SET outlet_id = ib.outlet_id
            FROM import_batches ib
            WHERE ph.import_batch_id = ib.id
            AND ph.outlet_id IS NULL
        """)
        updated_count = cursor.rowcount
        print(f"✓ Updated {updated_count} records")

        # Step 3: Set NOT NULL
        print("\nStep 3: Setting outlet_id to NOT NULL...")
        cursor.execute("ALTER TABLE price_history ALTER COLUMN outlet_id SET NOT NULL")
        print("✓ Column set to NOT NULL")

        # Step 4: Add foreign key
        print("\nStep 4: Adding foreign key constraint...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_price_history_outlet'
                ) THEN
                    ALTER TABLE price_history
                    ADD CONSTRAINT fk_price_history_outlet
                    FOREIGN KEY (outlet_id) REFERENCES outlets(id) ON DELETE CASCADE;
                END IF;
            END $$;
        """)
        print("✓ Foreign key added")

        # Step 5: Drop old unique constraint
        print("\nStep 5: Dropping old unique constraint...")
        cursor.execute("""
            ALTER TABLE price_history
            DROP CONSTRAINT IF EXISTS price_history_distributor_product_id_effective_date_key
        """)
        print("✓ Old constraint dropped")

        # Step 6: Add new unique constraint
        print("\nStep 6: Adding new unique constraint...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'unique_price_per_outlet_product_date'
                ) THEN
                    ALTER TABLE price_history
                    ADD CONSTRAINT unique_price_per_outlet_product_date
                    UNIQUE (distributor_product_id, outlet_id, effective_date);
                END IF;
            END $$;
        """)
        print("✓ New constraint added")

        # Step 7: Create index
        print("\nStep 7: Creating index on outlet_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_outlet
            ON price_history(outlet_id)
        """)
        print("✓ Index created")

        # Commit all changes
        conn.commit()
        print("\n" + "="*60)
        print("✅ Migration completed successfully!")
        print("="*60)
        print("\nYou can now test multi-outlet uploads.")
        print("Each outlet will maintain independent pricing!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
