#!/usr/bin/env python3
"""
Script to completely reset PostgreSQL database - drops ALL tables.
Use this for a fresh start with the new schema.
"""
import psycopg2

# Your dev database connection string
DATABASE_URL = "postgresql://food_cost_dev_user:Xzx4zTBsKDw32GzVp5NFzEpF4bd09Req@dpg-d4l38ai4d50c73drl2ug-a.oregon-postgres.render.com/food_cost_dev"

def reset_database():
    """Drop all tables and reset the database to empty state."""
    try:
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        # Show current tables
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\nCurrent tables in database ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\nDatabase is already empty")
            cursor.close()
            conn.close()
            return

        print("\n⚠️  WARNING: This will DROP ALL TABLES!")
        print("Are you sure? (yes/no): ", end="")
        confirm = input().strip().lower()

        if confirm != "yes":
            print("❌ Aborted - no changes made")
            cursor.close()
            conn.close()
            return

        print("\nDropping all tables...")
        # Drop each table individually to handle dependencies
        cursor.execute("DROP SCHEMA public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        cursor.execute("GRANT ALL ON SCHEMA public TO food_cost_dev_user;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")

        print("✅ Successfully dropped all tables")

        # Verify it's empty
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"\n⚠️  Warning: {len(tables)} tables still exist:")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n✅ Database is now empty and ready for fresh migrations!")

        cursor.close()
        conn.close()

        print("\n📝 Next steps:")
        print("1. Go to Render dashboard")
        print("2. Trigger a manual deploy")
        print("3. Migrations will create all tables fresh")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you have psycopg2 installed: pip install psycopg2-binary")
        print("- Check if the database URL is correct")
        print("- Ensure you have network access to the database")

if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL Database Full Reset")
    print("=" * 60)
    reset_database()
