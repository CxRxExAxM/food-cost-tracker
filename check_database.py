#!/usr/bin/env python3
"""
Check if seed data exists in the database.
"""
import psycopg2

DATABASE_URL = "postgresql://food_cost_dev_user:Xzx4zTBsKDw32GzVp5NFzEpF4bd09Req@dpg-d4l38ai4d50c73drl2ug-a.oregon-postgres.render.com/food_cost_dev"

def check_database():
    """Check database contents."""
    try:
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check distributors
        cursor.execute("SELECT COUNT(*) FROM distributors")
        dist_count = cursor.fetchone()[0]
        print(f"\n📦 Distributors: {dist_count}")

        cursor.execute("SELECT id, name, code FROM distributors ORDER BY name")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]} ({row[2]})")

        # Check units
        cursor.execute("SELECT COUNT(*) FROM units")
        unit_count = cursor.fetchone()[0]
        print(f"\n📏 Units: {unit_count}")

        cursor.execute("SELECT id, abbreviation, unit_type FROM units ORDER BY abbreviation LIMIT 10")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]} ({row[2]})")
        print(f"   ... and {unit_count - 10} more")

        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"\n👤 Users: {user_count}")

        cursor.execute("SELECT id, email, username, role FROM users")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]} ({row[2]}) - {row[3]}")

        # Check other tables
        cursor.execute("SELECT COUNT(*) FROM products")
        print(f"\n🏷️  Products: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM common_products")
        print(f"🥫 Common Products: {cursor.fetchone()[0]}")

        cursor.execute("SELECT COUNT(*) FROM recipes")
        print(f"📝 Recipes: {cursor.fetchone()[0]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("Database Contents Check")
    print("=" * 60)
    check_database()
