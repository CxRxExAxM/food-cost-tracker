#!/usr/bin/env python3
"""
Script to reset Alembic migration history in PostgreSQL database.
Run this when you need to start fresh with migrations.
"""
import psycopg2

# Your dev database connection string
DATABASE_URL = "postgresql://food_cost_dev_user:Xzx4zTBsKDw32GzVp5NFzEpF4bd09Req@dpg-d4l38ai4d50c73drl2ug-a.oregon-postgres.render.com/food_cost_dev"

def reset_alembic():
    """Drop the alembic_version table to reset migration history."""
    try:
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Dropping alembic_version table...")
        cursor.execute("DROP TABLE IF EXISTS alembic_version CASCADE;")
        print("✅ Successfully dropped alembic_version table")

        # Check what tables exist
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\nExisting tables in database ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nNo tables in database (fresh start)")

        cursor.close()
        conn.close()

        print("\n✅ Database is ready for fresh migrations!")
        print("Now trigger a manual deploy in Render dashboard.")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you have psycopg2 installed: pip install psycopg2-binary")
        print("- Check if the database URL is correct")
        print("- Ensure you have network access to the database")

if __name__ == "__main__":
    print("=" * 60)
    print("Alembic Migration History Reset")
    print("=" * 60)
    reset_alembic()
