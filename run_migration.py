#!/usr/bin/env python3
"""
Run database migration 002: Add outlet_id to price_history
"""
import sys
import os

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from app.database import get_db

def run_migration():
    print("Starting migration 002: Add outlet_id to price_history...")

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Step 1: Add outlet_id column
            print("Step 1: Adding outlet_id column...")
            cursor.execute("ALTER TABLE price_history ADD COLUMN outlet_id INTEGER")
            print("✓ Column added")

            # Step 2: Populate from import_batches
            print("Step 2: Populating outlet_id from import_batches...")
            cursor.execute("""
                UPDATE price_history ph
                SET outlet_id = ib.outlet_id
                FROM import_batches ib
                WHERE ph.import_batch_id = ib.id
            """)
            updated_count = cursor.rowcount
            print(f"✓ Updated {updated_count} records")

            # Step 3: Set NOT NULL
            print("Step 3: Setting outlet_id to NOT NULL...")
            cursor.execute("ALTER TABLE price_history ALTER COLUMN outlet_id SET NOT NULL")
            print("✓ Column set to NOT NULL")

            # Step 4: Add foreign key
            print("Step 4: Adding foreign key constraint...")
            cursor.execute("""
                ALTER TABLE price_history
                ADD CONSTRAINT fk_price_history_outlet
                FOREIGN KEY (outlet_id) REFERENCES outlets(id) ON DELETE CASCADE
            """)
            print("✓ Foreign key added")

            # Step 5: Drop old unique constraint
            print("Step 5: Dropping old unique constraint...")
            cursor.execute("""
                ALTER TABLE price_history
                DROP CONSTRAINT IF EXISTS price_history_distributor_product_id_effective_date_key
            """)
            print("✓ Old constraint dropped")

            # Step 6: Add new unique constraint
            print("Step 6: Adding new unique constraint...")
            cursor.execute("""
                ALTER TABLE price_history
                ADD CONSTRAINT unique_price_per_outlet_product_date
                UNIQUE (distributor_product_id, outlet_id, effective_date)
            """)
            print("✓ New constraint added")

            # Step 7: Create index
            print("Step 7: Creating index on outlet_id...")
            cursor.execute("CREATE INDEX idx_price_history_outlet ON price_history(outlet_id)")
            print("✓ Index created")

            # Commit all changes
            conn.commit()
            print("\n✅ Migration completed successfully!")

        except Exception as e:
            conn.rollback()
            print(f"\n❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
