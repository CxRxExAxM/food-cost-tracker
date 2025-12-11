#!/usr/bin/env python3
"""
Script to completely reset PostgreSQL database - drops ALL tables.
No confirmation prompt - runs immediately.
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

        print("\n🗑️  Dropping all tables...")
        # Drop and recreate schema to remove all objects
        cursor.execute("DROP SCHEMA public CASCADE;")
        cursor.execute("CREATE SCHEMA public;")
        cursor.execute("GRANT ALL ON SCHEMA public TO food_cost_dev_user;")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")

        print("✅ Successfully dropped all tables and objects")

        # Verify it's empty
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables_after = cursor.fetchall()

        if not tables_after:
            print("✅ Database is now completely empty!")
        else:
            print(f"\n⚠️  Warning: {len(tables_after)} tables still exist:")
            for table in tables_after:
                print(f"  - {table[0]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("✅ DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\n📝 Next steps:")
        print("1. Go to Render dashboard: https://dashboard.render.com")
        print("2. Find your 'food-cost-tracker-dev' web service")
        print("3. Click 'Manual Deploy' → Deploy latest commit")
        print("4. Watch logs - Alembic will create all tables fresh")
        print("5. Once deployed, visit the site and use /auth/setup to create first user")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("PostgreSQL Database Full Reset (DEV)")
    print("=" * 60)
    reset_database()
