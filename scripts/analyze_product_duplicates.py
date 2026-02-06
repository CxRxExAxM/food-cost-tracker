#!/usr/bin/env python3
"""
Product Duplicates Analysis Script

Analyzes duplicate products across outlets before org-wide migration.
Finds products with same name/brand/pack/size/unit across different outlets
and reports which products will be merged.

Usage:
    DATABASE_URL="postgresql://..." python3 scripts/analyze_product_duplicates.py
"""

import os
import sys
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    """Get database connection from DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def analyze_duplicates():
    """Find and report duplicate products across outlets."""
    print("=" * 80)
    print("PRODUCT DUPLICATES ANALYSIS")
    print("=" * 80)
    print()

    conn = get_connection()
    cursor = conn.cursor()

    # Find duplicate products grouped by (name, brand, pack, size, unit_id, organization_id)
    cursor.execute("""
        SELECT
            p.organization_id,
            o.name as org_name,
            p.name as product_name,
            p.brand,
            p.pack,
            p.size,
            p.unit_id,
            u.abbreviation as unit_abbr,
            COUNT(*) as duplicate_count,
            ARRAY_AGG(p.id ORDER BY p.id) as product_ids,
            ARRAY_AGG(DISTINCT out.name) as outlet_names
        FROM products p
        JOIN organizations o ON o.id = p.organization_id
        LEFT JOIN units u ON u.id = p.unit_id
        LEFT JOIN outlets out ON out.id = p.outlet_id
        WHERE p.is_active = 1
        GROUP BY
            p.organization_id, o.name,
            p.name, p.brand, p.pack, p.size, p.unit_id, u.abbreviation
        HAVING COUNT(*) > 1
        ORDER BY o.name, COUNT(*) DESC, p.name
    """)

    duplicates = cursor.fetchall()

    if not duplicates:
        print("No duplicate products found across outlets!")
        print()
        print("All products are unique within their organizations.")
        cursor.close()
        conn.close()
        return

    # Group by organization
    by_org = defaultdict(list)
    for dup in duplicates:
        by_org[dup['org_name']].append(dup)

    total_duplicates = 0
    total_affected_products = 0
    total_to_merge = 0

    for org_name, org_dups in by_org.items():
        print(f"\n{'=' * 80}")
        print(f"Organization: {org_name}")
        print(f"{'=' * 80}")

        for dup in org_dups:
            total_duplicates += 1
            total_affected_products += dup['duplicate_count']
            total_to_merge += dup['duplicate_count'] - 1  # Keep one, merge rest

            size_str = f"{dup['size']}" if dup['size'] else "N/A"
            unit_str = dup['unit_abbr'] or "N/A"
            brand_str = dup['brand'] or "(no brand)"

            print(f"\n  {dup['product_name']}")
            print(f"     Brand: {brand_str}")
            print(f"     Pack: {dup['pack'] or 'N/A'} x Size: {size_str} {unit_str}")
            print(f"     Found in {dup['duplicate_count']} outlets: {', '.join(dup['outlet_names'])}")
            print(f"     Product IDs: {dup['product_ids']}")
            print(f"     -> Will KEEP ID: {dup['product_ids'][0]}, MERGE: {dup['product_ids'][1:]}")

            # Show affected distributor_products
            cursor.execute("""
                SELECT dp.id, dp.product_id, dp.distributor_sku, d.name as distributor_name
                FROM distributor_products dp
                JOIN distributors d ON d.id = dp.distributor_id
                WHERE dp.product_id = ANY(%s)
                ORDER BY dp.product_id
            """, (dup['product_ids'],))
            dist_prods = cursor.fetchall()

            if dist_prods:
                print(f"     Distributor Products to update:")
                for dp in dist_prods:
                    keep_or_merge = "KEEP" if dp['product_id'] == dup['product_ids'][0] else "REMAP"
                    print(f"       - [{keep_or_merge}] {dp['distributor_name']} SKU: {dp['distributor_sku']} (dp.id={dp['id']})")

            # Show affected price_history counts
            cursor.execute("""
                SELECT
                    dp.product_id,
                    out.name as outlet_name,
                    COUNT(*) as price_count
                FROM price_history ph
                JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                LEFT JOIN outlets out ON out.id = ph.outlet_id
                WHERE dp.product_id = ANY(%s)
                GROUP BY dp.product_id, out.name
                ORDER BY dp.product_id
            """, (dup['product_ids'],))
            price_counts = cursor.fetchall()

            if price_counts:
                print(f"     Price History records:")
                for pc in price_counts:
                    outlet_str = pc['outlet_name'] or "Unknown Outlet"
                    print(f"       - Product {pc['product_id']}, {outlet_str}: {pc['price_count']} prices")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Total duplicate product groups: {total_duplicates}")
    print(f"  Total products affected: {total_affected_products}")
    print(f"  Products to merge (soft-delete): {total_to_merge}")
    print(f"  Products to keep: {total_duplicates}")
    print()
    print("MIGRATION PLAN:")
    print("  1. For each duplicate group, the LOWEST ID product will be kept")
    print("  2. All distributor_products pointing to merged products will be remapped")
    print("  3. Merged products will be soft-deleted (is_active = 0)")
    print("  4. Price history remains on distributor_products (outlet-specific)")
    print()
    print("Run 'alembic upgrade head' to apply migration 019_products_org_wide")
    print()

    cursor.close()
    conn.close()


def show_org_product_stats():
    """Show current product statistics by organization and outlet."""
    print("\n" + "=" * 80)
    print("CURRENT PRODUCT STATISTICS")
    print("=" * 80)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            o.name as org_name,
            out.name as outlet_name,
            COUNT(p.id) as product_count
        FROM products p
        JOIN organizations o ON o.id = p.organization_id
        LEFT JOIN outlets out ON out.id = p.outlet_id
        WHERE p.is_active = 1
        GROUP BY o.name, out.name
        ORDER BY o.name, out.name
    """)

    stats = cursor.fetchall()
    current_org = None

    for row in stats:
        if row['org_name'] != current_org:
            if current_org:
                print()
            current_org = row['org_name']
            print(f"\n{row['org_name']}:")

        outlet_name = row['outlet_name'] or "(no outlet)"
        print(f"  {outlet_name}: {row['product_count']} products")

    print()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("PHASE 7: ORG-WIDE PRODUCTS MIGRATION ANALYSIS")
    print("=" * 80)
    print()
    print("This script analyzes your database for duplicate products")
    print("that exist across multiple outlets within the same organization.")
    print()
    print("These duplicates will be merged during migration 019.")
    print()

    show_org_product_stats()
    analyze_duplicates()
