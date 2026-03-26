#!/usr/bin/env python3
"""
Taxonomy Migration Script - Phase 2

Parses existing common_products names and creates:
1. base_ingredients - core ingredient concepts
2. ingredient_variants - specific forms with attributes
3. Updates common_products with bridge columns

Naming patterns detected:
- Vesta (Produce): "CARROT-DICE 3/8"" → Base: Carrot, Prep: Diced, Cut Size: 3/8"
- Shamrock (Protein): "CHICKEN, BRST SGL SK ON NATRL" → Base: Chicken, Cut: Breast, etc.

Run with: python scripts/migrate_taxonomy.py [--dry-run]
"""
import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app.database import get_db
from scripts.taxonomy_parser import (
    extract_base_and_attributes,
    build_display_name,
    determine_category_subcategory
)


def migrate_taxonomy(dry_run: bool = False, verbose: bool = False):
    """
    Main migration function.

    Steps:
    1. Read all common_products
    2. Parse names into base + attributes
    3. Create unique base_ingredients
    4. Create ingredient_variants
    5. Update common_products with bridge columns
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}Starting taxonomy migration...")

    with get_db() as conn:
        cursor = conn.cursor()

        # Step 1: Read all common_products
        cursor.execute("""
            SELECT id, common_name, category, subcategory
            FROM common_products
            WHERE is_active = 1 AND base_ingredient_id IS NULL
            ORDER BY common_name
        """)
        products = cursor.fetchall()

        print(f"Found {len(products)} common_products to migrate")

        if not products:
            print("No products to migrate (all may already be migrated)")
            return

        # Step 2: Parse and collect unique bases
        base_ingredients = {}  # name -> {category, subcategory, products: [...]}
        parsed_products = []

        for prod in products:
            parsed = extract_base_and_attributes(prod["common_name"], prod["category"])
            base_name = parsed["base_name"]

            if not base_name:
                print(f"  WARNING: Could not parse base from: {prod['common_name']}")
                continue

            # Collect base ingredient info
            if base_name not in base_ingredients:
                cat, subcat = determine_category_subcategory(base_name)
                base_ingredients[base_name] = {
                    "category": cat or prod["category"],
                    "subcategory": subcat or prod["subcategory"],
                    "products": []
                }

            # Build display name
            display_name = build_display_name(base_name, parsed)

            parsed_products.append({
                "common_product_id": prod["id"],
                "common_name": prod["common_name"],
                "base_name": base_name,
                "parsed": parsed,
                "display_name": display_name,
            })

            base_ingredients[base_name]["products"].append(parsed_products[-1])

            if verbose:
                print(f"  {prod['common_name']}")
                print(f"    → Base: {base_name}, Display: {display_name}")
                print(f"    → Attrs: {parsed}")

        print(f"\nIdentified {len(base_ingredients)} unique base ingredients")

        # Step 3: Create base_ingredients
        base_id_map = {}  # name -> id

        for base_name, info in sorted(base_ingredients.items()):
            if dry_run:
                print(f"  [DRY RUN] Would create base: {base_name} ({info['category']}/{info['subcategory']})")
                base_id_map[base_name] = -1  # Placeholder
            else:
                # Check if already exists
                cursor.execute(
                    "SELECT id FROM base_ingredients WHERE LOWER(name) = LOWER(%s)",
                    (base_name,)
                )
                existing = cursor.fetchone()

                if existing:
                    base_id_map[base_name] = existing["id"]
                    if verbose:
                        print(f"  Base exists: {base_name} (id={existing['id']})")
                else:
                    cursor.execute("""
                        INSERT INTO base_ingredients (name, category, subcategory)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (base_name, info["category"], info["subcategory"]))
                    new_id = cursor.fetchone()["id"]
                    base_id_map[base_name] = new_id
                    print(f"  Created base: {base_name} (id={new_id})")

        # Step 4: Create ingredient_variants and update common_products
        variants_created = 0
        products_updated = 0

        for parsed_prod in parsed_products:
            base_name = parsed_prod["base_name"]
            base_id = base_id_map.get(base_name)

            if not base_id:
                continue

            attrs = parsed_prod["parsed"]
            display_name = parsed_prod["display_name"]

            if dry_run:
                print(f"  [DRY RUN] Would create variant: {display_name}")
            else:
                # Check if variant exists
                cursor.execute("""
                    SELECT id FROM ingredient_variants
                    WHERE base_ingredient_id = %s
                      AND COALESCE(variety, '') = COALESCE(%s, '')
                      AND COALESCE(form, '') = COALESCE(%s, '')
                      AND COALESCE(prep, '') = COALESCE(%s, '')
                      AND COALESCE(cut_size, '') = COALESCE(%s, '')
                      AND COALESCE(cut, '') = COALESCE(%s, '')
                      AND COALESCE(bone, '') = COALESCE(%s, '')
                      AND COALESCE(skin, '') = COALESCE(%s, '')
                      AND COALESCE(grade, '') = COALESCE(%s, '')
                      AND COALESCE(state, '') = COALESCE(%s, '')
                """, (
                    base_id,
                    attrs["variety"], attrs["form"], attrs["prep"], attrs["cut_size"],
                    attrs["cut"], attrs["bone"], attrs["skin"], attrs["grade"], attrs["state"]
                ))
                existing_variant = cursor.fetchone()

                if existing_variant:
                    variant_id = existing_variant["id"]
                else:
                    cursor.execute("""
                        INSERT INTO ingredient_variants (
                            base_ingredient_id, display_name,
                            variety, form, prep, cut_size,
                            cut, bone, skin, grade, state
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        base_id, display_name,
                        attrs["variety"], attrs["form"], attrs["prep"], attrs["cut_size"],
                        attrs["cut"], attrs["bone"], attrs["skin"], attrs["grade"], attrs["state"]
                    ))
                    variant_id = cursor.fetchone()["id"]
                    variants_created += 1
                    if verbose:
                        print(f"  Created variant: {display_name} (id={variant_id})")

                # Update common_product with bridge columns
                cursor.execute("""
                    UPDATE common_products
                    SET base_ingredient_id = %s, variant_id = %s, migrated_at = %s
                    WHERE id = %s
                """, (base_id, variant_id, datetime.now(), parsed_prod["common_product_id"]))
                products_updated += 1

        if not dry_run:
            conn.commit()
            print(f"\n✅ Migration complete:")
            print(f"   - Base ingredients created: {len([b for b in base_id_map.values() if b > 0])}")
            print(f"   - Variants created: {variants_created}")
            print(f"   - Common products updated: {products_updated}")
        else:
            print(f"\n[DRY RUN] Would create:")
            print(f"   - Base ingredients: {len(base_ingredients)}")
            print(f"   - Variants: {len(parsed_products)}")
            print(f"   - Common products to update: {len(parsed_products)}")


def main():
    parser = argparse.ArgumentParser(description="Migrate common_products to taxonomy")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    migrate_taxonomy(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
