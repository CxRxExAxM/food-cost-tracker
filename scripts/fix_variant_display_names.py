#!/usr/bin/env python3
"""
Fix variant display_names that were incorrectly created with the base ingredient
name as a prefix (e.g., "Cheese, American, SLI" under Cheese → "American, SLI").

Safe to run multiple times (idempotent). Prints a preview before applying.

Usage:
    python3 scripts/fix_variant_display_names.py           # dry run
    python3 scripts/fix_variant_display_names.py --apply   # apply changes
"""
import sys
import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required")
    sys.exit(1)

apply = "--apply" in sys.argv

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Find variants whose display_name starts with their base ingredient name + ", "
cur.execute("""
    SELECT
        iv.id,
        iv.display_name AS old_name,
        bi.name AS base_name,
        TRIM(SUBSTRING(iv.display_name FROM LENGTH(bi.name) + 3)) AS new_name
    FROM ingredient_variants iv
    JOIN base_ingredients bi ON bi.id = iv.base_ingredient_id
    WHERE iv.display_name ILIKE bi.name || ', %'
      AND iv.is_active = 1
    ORDER BY bi.name, iv.display_name
""")
rows = cur.fetchall()

if not rows:
    print("No variants found with redundant base name prefix. Nothing to do.")
    conn.close()
    sys.exit(0)

print(f"Found {len(rows)} variants with redundant base name prefix:\n")
for r in rows:
    print(f"  [{r['id']:4d}] {r['old_name']!r}")
    print(f"         → {r['new_name']!r}")
    print()

if not apply:
    print(f"DRY RUN — {len(rows)} variants would be renamed.")
    print("Run with --apply to apply changes.")
    conn.close()
    sys.exit(0)

# Apply the renames
ids = [r['id'] for r in rows]
cur.execute("""
    UPDATE ingredient_variants iv
    SET display_name = TRIM(SUBSTRING(iv.display_name FROM LENGTH(bi.name) + 3)),
        updated_at = NOW()
    FROM base_ingredients bi
    WHERE iv.base_ingredient_id = bi.id
      AND iv.id = ANY(%s)
""", (ids,))

updated = cur.rowcount
conn.commit()
print(f"Applied: renamed {updated} variants.")
conn.close()
