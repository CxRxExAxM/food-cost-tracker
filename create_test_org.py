#!/usr/bin/env python3
"""
Create a test organization and user for multi-tenancy testing.

Usage:
    export DATABASE_URL="postgresql://your-dev-database-url"
    python create_test_org.py
"""

import os
import sys
from passlib.context import CryptContext

# Check for DATABASE_URL
database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("ERROR: DATABASE_URL environment variable is not set!")
    print("\nSet it to your dev database URL:")
    print('export DATABASE_URL="postgresql://user:pass@host/database"')
    sys.exit(1)

import psycopg2

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_org():
    """Create a second test organization and admin user."""

    print("Creating test organization #2...\n")

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # Create second organization
        org_name = "Test Organization 2"
        org_slug = "test_org_2"

        cursor.execute("""
            INSERT INTO organizations (name, slug, subscription_tier, subscription_status)
            VALUES (%s, %s, 'free', 'active')
            RETURNING id
        """, (org_name, org_slug))

        org_id = cursor.fetchone()[0]
        print(f"✓ Created organization: '{org_name}' (ID: {org_id})")

        # Create admin user for this organization
        email = "test2@example.com"
        username = "testuser2"
        password = "password123"
        full_name = "Test User 2"

        hashed_password = pwd_context.hash(password)

        cursor.execute("""
            INSERT INTO users (email, username, hashed_password, full_name, role, organization_id)
            VALUES (%s, %s, %s, %s, 'admin', %s)
            RETURNING id
        """, (email, username, hashed_password, full_name, org_id))

        user_id = cursor.fetchone()[0]
        print(f"✓ Created admin user: '{username}' (ID: {user_id})")

        print("\n" + "=" * 60)
        print("SUCCESS! Test organization created.")
        print("=" * 60)
        print(f"\nOrganization ID: {org_id}")
        print(f"User ID: {user_id}")
        print(f"\nLogin credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print("\n" + "=" * 60)
        print("\nYou can now test multi-tenancy by:")
        print("1. Login as your original user (Organization 1)")
        print("2. Create some products/recipes")
        print("3. Logout and login as test2@example.com (Organization 2)")
        print("4. Verify you can't see Organization 1's data")
        print("=" * 60)

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_test_org()
