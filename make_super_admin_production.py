#!/usr/bin/env python3
"""
Make a user a super admin on the production database.
Usage: export DATABASE_URL="your_production_db_url" && python3 make_super_admin_production.py
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def make_super_admin(email):
    """Make a user a super admin."""
    db_url = os.environ.get('DATABASE_URL')

    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Usage: export DATABASE_URL='your_db_url' && python3 make_super_admin_production.py")
        sys.exit(1)

    # Parse DATABASE_URL
    result = urlparse(db_url)

    try:
        # Connect to database
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )

        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT id, email, username, is_super_admin FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            print(f"ERROR: User with email '{email}' not found")
            conn.close()
            sys.exit(1)

        user_id, user_email, username, current_super_admin = user

        if current_super_admin:
            print(f"User '{username}' ({user_email}) is already a super admin")
            conn.close()
            sys.exit(0)

        # Update user to super admin
        cursor.execute("""
            UPDATE users SET is_super_admin = 1
            WHERE email = %s
            RETURNING id, email, username
        """, (email,))

        updated_user = cursor.fetchone()
        conn.commit()

        print(f"✅ SUCCESS: User '{updated_user[2]}' ({updated_user[1]}) is now a super admin")
        print(f"   User ID: {updated_user[0]}")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    email = "mike.myers@fairmont.com"
    make_super_admin(email)
