#!/usr/bin/env python3
"""
Common Products Duplicate & Health Analysis

Analyzes the current state of common_products before deciding whether to do
a clean-slate archive (Step 5) or a targeted merge. Reports:

  1. Overall stats (total CPs, linked to taxonomy, orphans)
  2. Exact duplicates — same LOWER(common_name) within an org
  3. Taxonomy orphans — active CPs with no variant_id
  4. Usage breakdown — which CPs are actually referenced by products or recipes
  5. Base-ingredient clusters — functional duplicates with different names

Usage:
    DATABASE_URL="postgresql://..." python3 scripts/analyze_common_product_duplicates.py

Optional flags:
    --org-id 1       Limit to a specific organization_id
    --show-all       Show every CP in each group, not just the first few
"""

import os
import sys
import argparse
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
try:
    from taxonomy_parser import extract_base_and_attributes
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False


def get_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def section(title):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def sub(title):
    print()
    print(f"  --- {title} ---")


# ---------------------------------------------------------------------------
# 1. Overall stats
# ---------------------------------------------------------------------------

def overall_stats(cursor, org_filter):
    section("1. OVERALL COMMON PRODUCT STATS")

    where = f"WHERE organization_id = {org_filter}" if org_filter else ""
    cursor.execute(f"""
        SELECT
            o.name                                          AS org_name,
            COUNT(*)                                        AS total_active,
            COUNT(*) FILTER (WHERE cp.variant_id IS NOT NULL) AS linked_to_variant,
            COUNT(*) FILTER (WHERE cp.variant_id IS NULL)     AS orphans,
            COUNT(*) FILTER (WHERE cp.base_ingredient_id IS NOT NULL
                               AND cp.variant_id IS NULL)   AS base_only
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        {where}
          {"AND" if where else "WHERE"} cp.is_active = 1
        GROUP BY o.name
        ORDER BY o.name
    """)
    rows = cursor.fetchall()

    if not rows:
        print("  No active common_products found.")
        return

    for r in rows:
        print(f"\n  Org: {r['org_name']}")
        print(f"    Total active CPs   : {r['total_active']}")
        print(f"    Linked to variant  : {r['linked_to_variant']}")
        print(f"    Base-only (no var) : {r['base_only']}")
        print(f"    Full orphans       : {r['orphans'] - r['base_only']}  (no base, no variant)")

    # Usage counts
    cursor.execute(f"""
        SELECT
            o.name AS org_name,
            COUNT(DISTINCT cp.id) FILTER (
                WHERE EXISTS (SELECT 1 FROM products p
                              WHERE p.common_product_id = cp.id AND p.is_active = 1)
            ) AS cps_with_products,
            COUNT(DISTINCT cp.id) FILTER (
                WHERE EXISTS (SELECT 1 FROM recipe_ingredients ri
                              WHERE ri.common_product_id = cp.id)
            ) AS cps_with_recipes,
            COUNT(DISTINCT cp.id) FILTER (
                WHERE NOT EXISTS (SELECT 1 FROM products p
                                  WHERE p.common_product_id = cp.id AND p.is_active = 1)
                  AND NOT EXISTS (SELECT 1 FROM recipe_ingredients ri
                                  WHERE ri.common_product_id = cp.id)
            ) AS unused_cps
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        {where}
          {"AND" if where else "WHERE"} cp.is_active = 1
        GROUP BY o.name
        ORDER BY o.name
    """)
    usage_rows = cursor.fetchall()

    print()
    for r in usage_rows:
        print(f"  Org: {r['org_name']} — Usage:")
        print(f"    CPs referenced by vendor products : {r['cps_with_products']}")
        print(f"    CPs referenced by recipes         : {r['cps_with_recipes']}")
        print(f"    CPs with no references (unused)   : {r['unused_cps']}")


# ---------------------------------------------------------------------------
# 2. Exact duplicates
# ---------------------------------------------------------------------------

def exact_duplicates(cursor, org_filter, show_all):
    section("2. EXACT DUPLICATES  (same LOWER(common_name) within org)")

    where = f"AND cp.organization_id = {org_filter}" if org_filter else ""
    cursor.execute(f"""
        SELECT
            o.name                              AS org_name,
            cp.organization_id,
            LOWER(cp.common_name)               AS norm_name,
            COUNT(*)                            AS count,
            ARRAY_AGG(cp.id ORDER BY cp.id)     AS ids,
            ARRAY_AGG(cp.common_name ORDER BY cp.id) AS names
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        WHERE cp.is_active = 1
          {where}
        GROUP BY o.name, cp.organization_id, LOWER(cp.common_name)
        HAVING COUNT(*) > 1
        ORDER BY o.name, COUNT(*) DESC
    """)
    dupes = cursor.fetchall()

    if not dupes:
        print("\n  No exact duplicates found. Clean on this metric.")
        return 0

    total = sum(d['count'] - 1 for d in dupes)
    print(f"\n  Found {len(dupes)} duplicate group(s) — {total} redundant CP(s) to merge/archive.\n")

    for d in dupes:
        print(f"  [{d['org_name']}]  \"{d['norm_name']}\"  ({d['count']} copies)")

        limit = len(d['ids']) if show_all else min(5, len(d['ids']))
        for i in range(limit):
            cp_id = d['ids'][i]
            cp_name = d['names'][i]

            cursor.execute("""
                SELECT
                    (SELECT COUNT(*) FROM products p
                     WHERE p.common_product_id = %s AND p.is_active = 1) AS product_refs,
                    (SELECT COUNT(*) FROM recipe_ingredients ri
                     WHERE ri.common_product_id = %s)                    AS recipe_refs,
                    (SELECT iv.display_name FROM ingredient_variants iv
                     WHERE iv.id = (SELECT variant_id FROM common_products
                                    WHERE id = %s)) AS variant_name
            """, (cp_id, cp_id, cp_id))
            usage = cursor.fetchone()

            variant_str = f"variant: {usage['variant_name']}" if usage['variant_name'] else "no variant"
            print(f"    id={cp_id}  \"{cp_name}\"  "
                  f"[{variant_str}]  "
                  f"products={usage['product_refs']}  recipes={usage['recipe_refs']}")

        if not show_all and len(d['ids']) > 5:
            print(f"    ... and {len(d['ids']) - 5} more")

    return len(dupes)


# ---------------------------------------------------------------------------
# 3. Taxonomy orphans
# ---------------------------------------------------------------------------

def taxonomy_orphans(cursor, org_filter, show_all):
    section("3. TAXONOMY ORPHANS  (active CPs with no variant_id)")

    where = f"AND cp.organization_id = {org_filter}" if org_filter else ""
    cursor.execute(f"""
        SELECT
            o.name           AS org_name,
            cp.id,
            cp.common_name,
            cp.base_ingredient_id,
            bi.name          AS base_name,
            (SELECT COUNT(*) FROM products p
             WHERE p.common_product_id = cp.id AND p.is_active = 1) AS product_refs,
            (SELECT COUNT(*) FROM recipe_ingredients ri
             WHERE ri.common_product_id = cp.id)                    AS recipe_refs
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        LEFT JOIN base_ingredients bi ON bi.id = cp.base_ingredient_id
        WHERE cp.is_active = 1
          AND cp.variant_id IS NULL
          {where}
        ORDER BY o.name, product_refs DESC, recipe_refs DESC, cp.common_name
    """)
    orphans = cursor.fetchall()

    if not orphans:
        print("\n  No orphans found — all active CPs are linked to a variant.")
        return 0

    by_org = defaultdict(list)
    for o in orphans:
        by_org[o['org_name']].append(o)

    for org_name, rows in by_org.items():
        in_use = [r for r in rows if r['product_refs'] > 0 or r['recipe_refs'] > 0]
        unused = [r for r in rows if r['product_refs'] == 0 and r['recipe_refs'] == 0]

        print(f"\n  [{org_name}]  {len(rows)} orphan(s)  "
              f"({len(in_use)} in-use, {len(unused)} unused)")

        display_rows = rows if show_all else rows[:20]
        for r in display_rows:
            base_str = r['base_name'] or "no base"
            flag = " *** IN USE" if r['product_refs'] > 0 or r['recipe_refs'] > 0 else ""
            print(f"    id={r['id']}  \"{r['common_name']}\"  "
                  f"[{base_str}]  "
                  f"products={r['product_refs']}  recipes={r['recipe_refs']}{flag}")

        if not show_all and len(rows) > 20:
            print(f"    ... and {len(rows) - 20} more (use --show-all to see all)")

    return len(orphans)


# ---------------------------------------------------------------------------
# 4. Base-ingredient clusters (functional duplicates)
# ---------------------------------------------------------------------------

def base_ingredient_clusters(cursor, org_filter, show_all):
    section("4. BASE-INGREDIENT CLUSTERS  (CPs that share the same detected base)")

    if not PARSER_AVAILABLE:
        print("\n  taxonomy_parser not importable — skipping cluster analysis.")
        return

    where = f"AND cp.organization_id = {org_filter}" if org_filter else ""
    cursor.execute(f"""
        SELECT
            o.name        AS org_name,
            cp.id,
            cp.common_name,
            cp.variant_id,
            cp.base_ingredient_id,
            bi.name       AS existing_base
        FROM common_products cp
        JOIN organizations o ON o.id = cp.organization_id
        LEFT JOIN base_ingredients bi ON bi.id = cp.base_ingredient_id
        WHERE cp.is_active = 1
          {where}
        ORDER BY o.name, cp.common_name
    """)
    all_cps = cursor.fetchall()

    # Group by (org, detected_base)
    clusters = defaultdict(list)
    for cp in all_cps:
        parsed = extract_base_and_attributes(cp['common_name'])
        detected_base = parsed.get('base_name', '').strip().lower() or '(undetected)'
        clusters[(cp['org_name'], detected_base)].append(cp)

    messy_clusters = {
        k: v for k, v in clusters.items() if len(v) > 1
    }

    if not messy_clusters:
        print("\n  No multi-CP base clusters found.")
        return

    # Sort by cluster size descending
    for (org_name, base), cps in sorted(
        messy_clusters.items(), key=lambda x: -len(x[1])
    ):
        # Only show clusters where there are CPs with different variant assignments
        # (same base + all same variant = fine, it's intentional depth)
        variant_ids = {cp['variant_id'] for cp in cps}

        print(f"\n  [{org_name}]  base=\"{base}\"  "
              f"{len(cps)} CP(s)  "
              f"{len(variant_ids)} distinct variant(s)")

        display = cps if show_all else cps[:8]
        for cp in display:
            variant_str = f"variant_id={cp['variant_id']}" if cp['variant_id'] else "no variant"
            print(f"    id={cp['id']}  \"{cp['common_name']}\"  [{variant_str}]")

        if not show_all and len(cps) > 8:
            print(f"    ... and {len(cps) - 8} more")


# ---------------------------------------------------------------------------
# 5. Multi-tenant safety check
# ---------------------------------------------------------------------------

def tenant_check(cursor):
    section("5. TENANT SAFETY CHECK")

    cursor.execute("""
        SELECT id, name, is_active
        FROM organizations
        ORDER BY id
    """)
    orgs = cursor.fetchall()

    print(f"\n  Total organizations in DB: {len(orgs)}")
    active = [o for o in orgs if o['is_active']]
    print(f"  Active organizations: {len(active)}")
    for o in orgs:
        status = "ACTIVE" if o['is_active'] else "inactive"
        print(f"    id={o['id']}  \"{o['name']}\"  [{status}]")

    if len(active) > 1:
        print()
        print("  *** WARNING: Multiple active organizations detected.")
        print("      Step 5 archive of ingredient_variants / base_ingredients is GLOBAL.")
        print("      Confirm with each org before running the global archive SQL.")
    else:
        print()
        print("  Single active org — global archive (Step 5) is safe to run.")

    return len(active)


# ---------------------------------------------------------------------------
# 6. Summary & recommendation
# ---------------------------------------------------------------------------

def recommendation(exact_dup_count, orphan_count, active_org_count):
    section("6. RECOMMENDATION")

    messy_total = exact_dup_count + orphan_count
    print(f"\n  Exact duplicate groups : {exact_dup_count}")
    print(f"  Orphaned CPs           : {orphan_count}")
    print(f"  Total messy CPs        : {messy_total}")
    print(f"  Active orgs            : {active_org_count}")
    print()

    if messy_total == 0:
        print("  Taxonomy is clean. No action required before Step 5.")
    elif messy_total < 30:
        print("  TARGETED MERGE recommended (messy count is small):")
        print("    Use MergeCommonProductsModal + reparse endpoint to fix")
        print("    individual items rather than a full clean-slate wipe.")
        print("    Estimated time: 30–60 min of guided cleanup.")
    else:
        print("  CLEAN SLATE recommended (messy count is large):")
        print("    Proceed with Step 5 archive + Step 6 guided remap.")
        print("    The guided flow (PathBasedProductMapper) makes Step 6 fast.")

    print()
    print("  Next steps:")
    print("    1. Review the orphan list above — any in-use orphans need")
    print("       manual re-linking before Step 5.")
    print("    2. Confirm active org count before running global archive SQL.")
    print("    3. Check TAXONOMY_GUIDED_MAPPING_PLAN_v2.md for Step 5 SQL.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze common_products for duplicates and orphans")
    parser.add_argument("--org-id", type=int, help="Limit analysis to a specific organization_id")
    parser.add_argument("--show-all", action="store_true", help="Show all items in each group")
    args = parser.parse_args()

    print()
    print("=" * 80)
    print("COMMON PRODUCTS — DUPLICATE & HEALTH ANALYSIS")
    print("=" * 80)
    if args.org_id:
        print(f"  Filtered to organization_id = {args.org_id}")

    conn = get_connection()
    cursor = conn.cursor()

    overall_stats(cursor, args.org_id)
    exact_count = exact_duplicates(cursor, args.org_id, args.show_all)
    orphan_count = taxonomy_orphans(cursor, args.org_id, args.show_all)
    base_ingredient_clusters(cursor, args.org_id, args.show_all)
    active_org_count = tenant_check(cursor)
    recommendation(exact_count, orphan_count, active_org_count)

    cursor.close()
    conn.close()
    print()


if __name__ == "__main__":
    main()
