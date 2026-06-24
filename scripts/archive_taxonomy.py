#!/usr/bin/env python3
"""
Taxonomy Archive Script (Step 5)

Soft-archives all active taxonomy data (base_ingredients, ingredient_variants,
common_products) before a clean-slate rebuild. Creates backup tables first so
the archive is fully reversible.

Modes:
    --dry-run    (default) Show counts of what would be archived, no changes
    --apply      Create backups and archive (sets is_active = 0)
    --rollback   Restore from backup tables (sets is_active = 1)
    --status     Show current active counts + whether backup tables exist

Usage:
    source venv/bin/activate
    DATABASE_URL="postgresql://..." python3 scripts/archive_taxonomy.py --dry-run
    DATABASE_URL="postgresql://..." python3 scripts/archive_taxonomy.py --apply
    DATABASE_URL="postgresql://..." python3 scripts/archive_taxonomy.py --rollback
"""

import os
import sys
import argparse

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def backup_tables_exist(cursor):
    cursor.execute("""
        SELECT COUNT(*) AS n FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN (
            'base_ingredients_backup',
            'ingredient_variants_backup',
            'common_products_backup',
            'ingredient_mappings_backup',
            'product_cp_links_backup'
          )
    """)
    return cursor.fetchone()['n'] == 5


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def cmd_status(cursor):
    section("TAXONOMY STATUS")

    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM base_ingredients WHERE is_active = 1)       AS active_bases,
            (SELECT COUNT(*) FROM base_ingredients WHERE is_active = 0)       AS archived_bases,
            (SELECT COUNT(*) FROM ingredient_variants WHERE is_active = 1)    AS active_variants,
            (SELECT COUNT(*) FROM ingredient_variants WHERE is_active = 0)    AS archived_variants,
            (SELECT COUNT(*) FROM common_products WHERE is_active = 1)        AS active_cps,
            (SELECT COUNT(*) FROM common_products WHERE is_active = 0)        AS archived_cps
    """)
    r = cursor.fetchone()

    print(f"\n  base_ingredients    : {r['active_bases']} active  /  {r['archived_bases']} archived")
    print(f"  ingredient_variants : {r['active_variants']} active  /  {r['archived_variants']} archived")
    print(f"  common_products     : {r['active_cps']} active  /  {r['archived_cps']} archived")

    has_backups = backup_tables_exist(cursor)
    print(f"\n  Backup tables exist : {'YES' if has_backups else 'NO'}")

    if has_backups:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM base_ingredients_backup)       AS b_bases,
                (SELECT COUNT(*) FROM ingredient_variants_backup)    AS b_variants,
                (SELECT COUNT(*) FROM common_products_backup)        AS b_cps,
                (SELECT COUNT(*) FROM ingredient_mappings_backup)    AS b_mappings,
                (SELECT COUNT(*) FROM product_cp_links_backup)       AS b_links
        """)
        b = cursor.fetchone()
        print(f"    base_ingredients_backup    : {b['b_bases']} rows")
        print(f"    ingredient_variants_backup : {b['b_variants']} rows")
        print(f"    common_products_backup     : {b['b_cps']} rows")
        print(f"    ingredient_mappings_backup : {b['b_mappings']} rows")
        print(f"    product_cp_links_backup    : {b['b_links']} rows")


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def cmd_dry_run(cursor):
    section("DRY RUN — What would be archived")

    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_active = 1) AS active
        FROM base_ingredients
    """)
    bases = cursor.fetchone()['active']

    cursor.execute("""
        SELECT COUNT(*) FILTER (WHERE is_active = 1) AS active
        FROM ingredient_variants
    """)
    variants = cursor.fetchone()['active']

    cursor.execute("""
        SELECT
            o.name,
            COUNT(*) FILTER (WHERE cp.is_active = 1) AS active
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        GROUP BY o.name
        ORDER BY o.name
    """)
    cp_rows = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS active
        FROM ingredient_mappings
    """)
    mappings = cursor.fetchone()['active']

    print(f"\n  Would archive:")
    print(f"    base_ingredients       : {bases} rows  (global)")
    print(f"    ingredient_variants    : {variants} rows  (global)")
    for row in cp_rows:
        print(f"    common_products        : {row['active']} rows  [{row['name']}]")
    print(f"    ingredient_mappings    : {mappings} rows  (all orgs — learned mappings reset)")

    print(f"\n  Would CREATE backup tables:")
    print(f"    base_ingredients_backup")
    print(f"    ingredient_variants_backup")
    print(f"    common_products_backup")
    print(f"    ingredient_mappings_backup")

    print(f"\n  NOT touched:")
    print(f"    products               (vendor SKUs — common_product_id goes stale but rows stay)")
    print(f"    recipe_ingredients     (common_product_id goes stale but rows stay)")
    print(f"    distributor_products   (untouched)")
    print(f"    price_history          (untouched)")
    print(f"    recipes / banquet_menus (untouched)")

    print(f"\n  Run with --apply to execute.")


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def cmd_apply(conn, cursor):
    section("APPLYING ARCHIVE")

    if backup_tables_exist(cursor):
        print("\n  Backup tables already exist.")
        print("  If you want to re-archive, drop them first or run --rollback first.")
        print("  Aborting to avoid overwriting your rollback path.")
        sys.exit(1)

    print("\n  Step 1: Creating backup tables...")

    cursor.execute("""
        CREATE TABLE base_ingredients_backup AS
        SELECT * FROM base_ingredients
    """)
    cursor.execute("SELECT COUNT(*) AS n FROM base_ingredients_backup")
    n = cursor.fetchone()['n']
    print(f"    base_ingredients_backup       : {n} rows")

    cursor.execute("""
        CREATE TABLE ingredient_variants_backup AS
        SELECT * FROM ingredient_variants
    """)
    cursor.execute("SELECT COUNT(*) AS n FROM ingredient_variants_backup")
    n = cursor.fetchone()['n']
    print(f"    ingredient_variants_backup    : {n} rows")

    cursor.execute("""
        CREATE TABLE common_products_backup AS
        SELECT * FROM common_products
    """)
    cursor.execute("SELECT COUNT(*) AS n FROM common_products_backup")
    n = cursor.fetchone()['n']
    print(f"    common_products_backup        : {n} rows")

    cursor.execute("""
        CREATE TABLE ingredient_mappings_backup AS
        SELECT * FROM ingredient_mappings
    """)
    cursor.execute("SELECT COUNT(*) AS n FROM ingredient_mappings_backup")
    n = cursor.fetchone()['n']
    print(f"    ingredient_mappings_backup    : {n} rows")

    # Snapshot product→CP links so rollback can restore them exactly
    cursor.execute("""
        CREATE TABLE product_cp_links_backup AS
        SELECT id, common_product_id FROM products
        WHERE common_product_id IS NOT NULL
    """)
    cursor.execute("SELECT COUNT(*) AS n FROM product_cp_links_backup")
    n = cursor.fetchone()['n']
    print(f"    product_cp_links_backup       : {n} rows")

    print("\n  Step 2: Archiving live data...")

    cursor.execute("UPDATE base_ingredients SET is_active = 0 WHERE is_active = 1")
    print(f"    base_ingredients archived     : {cursor.rowcount} rows")

    cursor.execute("UPDATE ingredient_variants SET is_active = 0 WHERE is_active = 1")
    print(f"    ingredient_variants archived  : {cursor.rowcount} rows")

    cursor.execute("UPDATE common_products SET is_active = 0 WHERE is_active = 1")
    print(f"    common_products archived      : {cursor.rowcount} rows")

    # Ingredient mappings point at now-archived common_product_ids.
    # Delete rather than soft-archive — they'll be re-learned as users remap.
    cursor.execute("DELETE FROM ingredient_mappings")
    print(f"    ingredient_mappings cleared   : {cursor.rowcount} rows")

    # Null out FK columns so the app doesn't surface stale links in the UI
    cursor.execute("UPDATE products SET common_product_id = NULL WHERE common_product_id IS NOT NULL")
    print(f"    products.common_product_id    : {cursor.rowcount} NULLed (stale links removed)")

    conn.commit()

    print("\n  Done. Taxonomy is now blank.")
    print("  Backup tables are in place — run --rollback to undo.")
    print("\n  Next: rebuild the taxonomy via PathBasedProductMapper (Step 6).")


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def cmd_rollback(conn, cursor):
    section("ROLLING BACK")

    if not backup_tables_exist(cursor):
        print("\n  No backup tables found. Nothing to roll back.")
        sys.exit(1)

    print("\n  Step 1: Restoring base_ingredients...")
    cursor.execute("""
        UPDATE base_ingredients bi
        SET is_active = bak.is_active
        FROM base_ingredients_backup bak
        WHERE bi.id = bak.id
    """)
    print(f"    Restored {cursor.rowcount} rows")

    print("\n  Step 2: Restoring ingredient_variants...")
    cursor.execute("""
        UPDATE ingredient_variants iv
        SET is_active = bak.is_active
        FROM ingredient_variants_backup bak
        WHERE iv.id = bak.id
    """)
    print(f"    Restored {cursor.rowcount} rows")

    print("\n  Step 3: Restoring common_products...")
    cursor.execute("""
        UPDATE common_products cp
        SET is_active = bak.is_active
        FROM common_products_backup bak
        WHERE cp.id = bak.id
    """)
    print(f"    Restored {cursor.rowcount} rows")

    print("\n  Step 4: Restoring ingredient_mappings...")
    cursor.execute("""
        INSERT INTO ingredient_mappings
        SELECT * FROM ingredient_mappings_backup
        ON CONFLICT (id) DO NOTHING
    """)
    print(f"    Restored {cursor.rowcount} rows")

    print("\n  Step 5: Restoring products.common_product_id...")
    cursor.execute("""
        UPDATE products p
        SET common_product_id = bak.common_product_id
        FROM product_cp_links_backup bak
        WHERE p.id = bak.id
    """)
    print(f"    Restored {cursor.rowcount} product→CP links")

    conn.commit()

    print("\n  Step 6: Dropping backup tables...")
    for table in [
        'base_ingredients_backup',
        'ingredient_variants_backup',
        'common_products_backup',
        'ingredient_mappings_backup',
        'product_cp_links_backup',
    ]:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"    Dropped {table}")

    conn.commit()
    print("\n  Rollback complete. Taxonomy restored to pre-archive state.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Archive taxonomy data before clean-slate rebuild")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True,
                       help="Show what would be archived (default)")
    group.add_argument("--apply", action="store_true",
                       help="Create backups and archive")
    group.add_argument("--rollback", action="store_true",
                       help="Restore from backup tables")
    group.add_argument("--status", action="store_true",
                       help="Show current counts and backup state")
    args = parser.parse_args()

    conn = get_connection()
    cursor = conn.cursor()

    if args.status:
        cmd_status(cursor)
    elif args.apply:
        print("\n  *** ARCHIVE MODE — this will soft-delete all active taxonomy data ***")
        confirm = input("  Type 'yes' to continue: ").strip().lower()
        if confirm != 'yes':
            print("  Aborted.")
            sys.exit(0)
        cmd_apply(conn, cursor)
    elif args.rollback:
        print("\n  *** ROLLBACK MODE — this will restore from backup tables ***")
        confirm = input("  Type 'yes' to continue: ").strip().lower()
        if confirm != 'yes':
            print("  Aborted.")
            sys.exit(0)
        cmd_rollback(conn, cursor)
    else:
        cmd_dry_run(cursor)

    cursor.close()
    conn.close()
    print()


if __name__ == "__main__":
    main()
