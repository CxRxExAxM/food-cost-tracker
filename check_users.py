#!/usr/bin/env python3
"""List all users in the database."""
import os
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("❌ DATABASE_URL not set")
    exit(1)

result = urlparse(db_url)
conn = psycopg2.connect(
    database=result.path[1:],
    user=result.username,
    password=result.password,
    host=result.hostname,
    port=result.port
)

cursor = conn.cursor()
cursor.execute("SELECT id, email, username, role, is_super_admin FROM users ORDER BY id")

print("\nUsers in database:")
print("-" * 80)
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Email: {row[1]}, Username: {row[2]}, Role: {row[3]}, Super Admin: {row[4]}")

conn.close()
