#!/usr/bin/env python3
"""
Make a user a super admin.
Connects using DATABASE_URL environment variable.

Usage:
  export DATABASE_URL="your-database-url"
  python make_super_admin.py mike.myers@fairmont.com
"""
import sys
import os
import psycopg2
from urllib.parse import urlparse

def make_super_admin(email: str):
    """Update user to be a super admin."""

    # Get DATABASE_URL from environment
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable not set")
        print("Usage: export DATABASE_URL='your-database-url'")
        return False

    # Parse DATABASE_URL
    result = urlparse(db_url)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port

    try:
        # Connect to database
        print(f"Connecting to database at {hostname}...")
        conn = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute(
            "SELECT id, email, username, is_super_admin FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        if not user:
            print(f"❌ User not found with email: {email}")
            conn.close()
            return False

        user_id, user_email, username, current_super_admin = user

        if current_super_admin:
            print(f"✅ User {email} is already a super admin!")
            conn.close()
            return True

        # Update user to super admin
        cursor.execute(
            """
            UPDATE users
            SET is_super_admin = 1
            WHERE email = %s
            RETURNING id, email, username
            """,
            (email,)
        )

        updated_user = cursor.fetchone()
        conn.commit()

        print(f"✅ Successfully made {email} a super admin!")
        print(f"   User ID: {updated_user[0]}")
        print(f"   Username: {updated_user[2]}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_super_admin.py <email>")
        print("Example: python make_super_admin.py mike.myers@fairmont.com")
        sys.exit(1)

    email = sys.argv[1]
    success = make_super_admin(email)

    sys.exit(0 if success else 1)
