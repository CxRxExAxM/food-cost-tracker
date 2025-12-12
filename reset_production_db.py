#!/usr/bin/env python3
"""
Reset Production Database - Fresh Start

This script will:
1. Drop the entire public schema (all tables and data)
2. Recreate the public schema
3. Grant necessary permissions
4. Clear the alembic_version table

WARNING: This will DELETE ALL DATA in the database!

Usage:
    # Set the production DATABASE_URL
    export DATABASE_URL="postgresql://user:pass@host/database"

    # Run the script
    python reset_production_db.py
"""

import os
import sys
import psycopg2

def reset_database():
    """Reset the production database to a clean state."""

    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set!")
        print("\nPlease set it to your production database URL:")
        print('export DATABASE_URL="postgresql://user:pass@host/database"')
        sys.exit(1)

    # Safety check - ask for confirmation
    print("=" * 70)
    print("WARNING: This will DELETE ALL DATA in the production database!")
    print("=" * 70)
    print(f"\nDatabase: {database_url.split('@')[1] if '@' in database_url else 'unknown'}")
    print("\nThis will:")
    print("  1. Drop the entire public schema (all tables)")
    print("  2. Delete all data")
    print("  3. Recreate the schema")
    print("  4. Grant permissions")
    print("\n" + "=" * 70)

    confirm = input("\nType 'RESET PRODUCTION' to continue: ")

    if confirm != "RESET PRODUCTION":
        print("\nAborted. No changes made.")
        sys.exit(0)

    print("\nConnecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("\n[1/4] Dropping public schema...")
        cursor.execute("DROP SCHEMA IF EXISTS public CASCADE;")
        print("✓ Schema dropped")

        print("\n[2/4] Creating public schema...")
        cursor.execute("CREATE SCHEMA public;")
        print("✓ Schema created")

        print("\n[3/4] Granting permissions to postgres...")
        cursor.execute("GRANT ALL ON SCHEMA public TO postgres;")
        print("✓ Permissions granted")

        print("\n[4/4] Granting public access...")
        cursor.execute("GRANT ALL ON SCHEMA public TO public;")
        print("✓ Public access granted")

        # Verify schema is empty
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        table_count = cursor.fetchone()[0]

        print("\n" + "=" * 70)
        print("SUCCESS! Production database has been reset.")
        print("=" * 70)
        print(f"\nTables in public schema: {table_count} (should be 0)")
        print("\nNext steps:")
        print("  1. The next Render deployment will run migrations")
        print("  2. Visit https://food-cost-tracker.onrender.com")
        print("  3. Click 'Initial Setup' to create your admin user")
        print("\n" + "=" * 70)

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database()
