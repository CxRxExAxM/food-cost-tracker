#!/usr/bin/env python3
"""Seed EHC outlets for an organization.

This script creates the standard EHC outlet records for a property.
By default, seeds the 15 SCP (Scottsdale) outlets.

Usage:
    python scripts/seed_ehc_outlets.py --org-id <organization_id>

    # Or using organization name (partial match, case-insensitive):
    python scripts/seed_ehc_outlets.py --org-name "fairmont"

    # List existing outlets without seeding:
    python scripts/seed_ehc_outlets.py --org-name "fairmont" --list-only

Requires DATABASE_URL environment variable.
"""
import os
import sys
import argparse

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================
# SCP Outlets (15 total)
# Scottsdale / Fairmont Scottsdale Princess
# ============================================

SCP_OUTLETS = [
    {"name": "MK",         "full_name": "Main Kitchen",                     "outlet_type": "Production Kitchen", "sort_order": 1},
    {"name": "GM",         "full_name": "Garde Manger",                     "outlet_type": "Production Kitchen", "sort_order": 2},
    {"name": "Pastry",     "full_name": "Pastry",                           "outlet_type": "Production Kitchen", "sort_order": 3},
    {"name": "Dish",       "full_name": "The Dish (Employee Cafe)",         "outlet_type": "Support",            "sort_order": 4},
    {"name": "Receiving",  "full_name": "Receiving",                        "outlet_type": "Support",            "sort_order": 5},
    {"name": "Stewarding", "full_name": "Stewarding",                       "outlet_type": "Support",            "sort_order": 6},
    {"name": "Casual",     "full_name": "Casual Dining",                    "outlet_type": "Restaurant",         "sort_order": 7},
    {"name": "Toro",       "full_name": "Toro Latin Restaurant & Rum Bar",  "outlet_type": "Restaurant",         "sort_order": 8},
    {"name": "LaHa",       "full_name": "La Hacienda",                      "outlet_type": "Restaurant",         "sort_order": 9},
    {"name": "BSAZ",       "full_name": "Bourbon Steak Arizona",            "outlet_type": "Restaurant",         "sort_order": 10},
    {"name": "Gold",       "full_name": "Fairmont Gold Lounge",             "outlet_type": "Lounge",             "sort_order": 11},
    {"name": "Plaza",      "full_name": "Plaza Bar",                        "outlet_type": "Bar",                "sort_order": 12},
    {"name": "Pools",      "full_name": "Pool Service",                     "outlet_type": "Bar",                "sort_order": 13},
    {"name": "Palomino",   "full_name": "Palomino",                         "outlet_type": "Lounge",             "sort_order": 14},
    {"name": "Starbucks",  "full_name": "Starbucks",                        "outlet_type": "Franchise",          "sort_order": 15},
]


def get_db_connection():
    """Get database connection from DATABASE_URL."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    return psycopg2.connect(database_url)


def find_organization(cursor, org_id=None, org_name=None):
    """Find organization by ID or name."""
    if org_id:
        cursor.execute("SELECT id, name FROM organizations WHERE id = %s", (org_id,))
    elif org_name:
        cursor.execute(
            "SELECT id, name FROM organizations WHERE LOWER(name) LIKE %s",
            (f"%{org_name.lower()}%",)
        )
    else:
        raise ValueError("Either --org-id or --org-name is required")

    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Organization not found: {org_id or org_name}")

    return row['id'], row['name']


def list_outlets(cursor, org_id):
    """List existing outlets for an organization."""
    cursor.execute("""
        SELECT name, full_name, outlet_type, is_active, sort_order
        FROM ehc_outlet
        WHERE organization_id = %s
        ORDER BY sort_order, name
    """, (org_id,))

    outlets = cursor.fetchall()
    if not outlets:
        print("No outlets found.")
        return

    print(f"\n{'Name':<12} {'Full Name':<40} {'Type':<20} {'Active':<8}")
    print("-" * 85)
    for o in outlets:
        active = "Yes" if o['is_active'] else "No"
        print(f"{o['name']:<12} {(o['full_name'] or '-'):<40} {(o['outlet_type'] or '-'):<20} {active:<8}")


def seed_outlets(cursor, org_id, outlets=None):
    """Seed outlets for an organization."""
    if outlets is None:
        outlets = SCP_OUTLETS

    created = 0
    skipped = 0

    for outlet in outlets:
        # Check if outlet already exists
        cursor.execute("""
            SELECT id FROM ehc_outlet
            WHERE organization_id = %s AND name = %s
        """, (org_id, outlet['name']))

        if cursor.fetchone():
            print(f"  Skipping {outlet['name']} (already exists)")
            skipped += 1
            continue

        # Insert outlet
        cursor.execute("""
            INSERT INTO ehc_outlet (organization_id, name, full_name, outlet_type, sort_order)
            VALUES (%s, %s, %s, %s, %s)
        """, (org_id, outlet['name'], outlet['full_name'], outlet['outlet_type'], outlet['sort_order']))

        print(f"  Created {outlet['name']}: {outlet['full_name']}")
        created += 1

    return created, skipped


def main():
    parser = argparse.ArgumentParser(description='Seed EHC outlets for an organization')
    parser.add_argument('--org-id', type=int, help='Organization ID')
    parser.add_argument('--org-name', type=str, help='Organization name (partial match)')
    parser.add_argument('--list-only', action='store_true', help='List existing outlets without seeding')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be created without making changes')

    args = parser.parse_args()

    if not args.org_id and not args.org_name:
        parser.error("Either --org-id or --org-name is required")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Find organization
        org_id, org_name = find_organization(cursor, args.org_id, args.org_name)
        print(f"\nOrganization: {org_name} (ID: {org_id})")

        if args.list_only:
            list_outlets(cursor, org_id)
            return

        if args.dry_run:
            print("\n[DRY RUN] Would create these outlets:")
            for outlet in SCP_OUTLETS:
                cursor.execute("""
                    SELECT id FROM ehc_outlet
                    WHERE organization_id = %s AND name = %s
                """, (org_id, outlet['name']))
                exists = cursor.fetchone()
                status = "SKIP (exists)" if exists else "CREATE"
                print(f"  [{status}] {outlet['name']}: {outlet['full_name']}")
            return

        print(f"\nSeeding {len(SCP_OUTLETS)} outlets...")
        created, skipped = seed_outlets(cursor, org_id)

        conn.commit()
        print(f"\nDone! Created: {created}, Skipped: {skipped}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cursor' in dir():
            cursor.close()
        if 'conn' in dir():
            conn.close()


if __name__ == '__main__':
    main()
