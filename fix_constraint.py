#!/usr/bin/env python3
"""
Fix: Drop any remaining old unique constraints on price_history
"""
import os
import sys

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Error: DATABASE_URL not set")
    sys.exit(1)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ Error: psycopg2 not installed")
    sys.exit(1)

def fix_constraints():
    print("Fixing price_history constraints...")

    db_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    cursor = conn.cursor()

    try:
        # Find all unique constraints on price_history
        print("\nFinding existing constraints...")
        cursor.execute("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'price_history'::regclass
            AND contype = 'u'
        """)
        constraints = cursor.fetchall()

        print(f"Found {len(constraints)} unique constraints:")
        for c in constraints:
            print(f"  - {c['conname']}")

        # Drop old constraints that DON'T include outlet_id
        old_constraints = [
            'unique_price_per_date',
            'price_history_distributor_product_id_effective_date_key'
        ]

        for constraint_name in old_constraints:
            print(f"\nDropping {constraint_name}...")
            cursor.execute(f"""
                ALTER TABLE price_history
                DROP CONSTRAINT IF EXISTS {constraint_name}
            """)
            print(f"✓ Dropped {constraint_name}")

        # Ensure new constraint exists
        print("\nEnsuring new constraint exists...")
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
        print("✓ New constraint ensured")

        conn.commit()

        # Verify final state
        print("\nFinal constraints:")
        cursor.execute("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'price_history'::regclass
            AND contype = 'u'
        """)
        final_constraints = cursor.fetchall()
        for c in final_constraints:
            print(f"  ✓ {c['conname']}")

        print("\n" + "="*60)
        print("✅ Constraints fixed successfully!")
        print("="*60)
        print("\nYou can now upload to both outlets without conflicts.")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_constraints()
