#!/usr/bin/env python3
"""
Script to make a user a super admin
Usage: python make_super_admin.py <email>
"""
import os
import sys
from sqlalchemy import create_engine, text

def make_super_admin(email):
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # Update user to be super admin (is_super_admin is integer: 1 = true, 0 = false)
        result = conn.execute(
            text("UPDATE users SET is_super_admin = 1 WHERE email = :email"),
            {"email": email}
        )
        conn.commit()
        
        if result.rowcount == 0:
            print(f"ERROR: No user found with email: {email}")
            sys.exit(1)
        
        # Verify the change
        user = conn.execute(
            text("""
                SELECT id, email, full_name, role, is_super_admin, organization_id
                FROM users
                WHERE email = :email
            """),
            {"email": email}
        ).fetchone()
        
        print(f"\n✓ Successfully updated user to super admin:\n")
        print(f"  ID: {user[0]}")
        print(f"  Email: {user[1]}")
        print(f"  Name: {user[2]}")
        print(f"  Role: {user[3]}")
        print(f"  Super Admin: {bool(user[4])}")
        print(f"  Organization ID: {user[5]}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python make_super_admin.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    make_super_admin(email)
