#!/usr/bin/env python3
"""
One-time import script for banquet menus from CSV.
Imports to SCP organization, Banquets outlet.

Usage:
    DATABASE_URL="postgresql://..." python3 scripts/import_banquet_menus.py
"""

import csv
import os
import sys
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor

# CSV file path
CSV_PATH = os.path.expanduser("~/Documents/DevProjects/BqtMenuCost/menuimport_complete.csv")

# Target organization and outlet names
TARGET_ORG = "SCP"
TARGET_OUTLET = "Banquets"


def get_connection():
    """Get database connection from DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def parse_price(price_str):
    """Parse price string like '$80.00' to Decimal."""
    if not price_str:
        return None
    clean = price_str.strip().replace("$", "").replace(",", "")
    try:
        return Decimal(clean)
    except:
        return None


def main():
    print(f"Importing banquet menus from: {CSV_PATH}")
    print(f"Target: {TARGET_ORG} / {TARGET_OUTLET}")
    print("-" * 50)

    conn = get_connection()
    cursor = conn.cursor()

    # Look up organization
    cursor.execute("SELECT id FROM organizations WHERE name = %s", (TARGET_ORG,))
    org_row = cursor.fetchone()
    if not org_row:
        print(f"ERROR: Organization '{TARGET_ORG}' not found")
        sys.exit(1)
    org_id = org_row["id"]
    print(f"Found organization: {TARGET_ORG} (id={org_id})")

    # Look up outlet
    cursor.execute(
        "SELECT id FROM outlets WHERE organization_id = %s AND name = %s",
        (org_id, TARGET_OUTLET)
    )
    outlet_row = cursor.fetchone()
    if not outlet_row:
        print(f"ERROR: Outlet '{TARGET_OUTLET}' not found in organization")
        sys.exit(1)
    outlet_id = outlet_row["id"]
    print(f"Found outlet: {TARGET_OUTLET} (id={outlet_id})")

    # Read CSV
    with open(CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Read {len(rows)} rows from CSV")

    # Group data by menu -> menu item -> prep items
    menus = {}  # key: (meal_period, service_type, menu_name)

    for row in rows:
        meal_period = row["Meal Period"].strip()
        service_type = row["Service Type"].strip()
        menu_name = row["Menu Name"].strip()
        price_str = row["Menu Price Per Person"].strip()
        menu_item_name = row["Menu Item"].strip()
        prep_item_name = row.get("Prep Item", "").strip()

        menu_key = (meal_period, service_type, menu_name)

        if menu_key not in menus:
            menus[menu_key] = {
                "meal_period": meal_period,
                "service_type": service_type,
                "name": menu_name,
                "price_per_person": parse_price(price_str),
                "menu_items": {}
            }

        menu = menus[menu_key]

        if menu_item_name not in menu["menu_items"]:
            menu["menu_items"][menu_item_name] = {
                "name": menu_item_name,
                "prep_items": []
            }

        menu_item = menu["menu_items"][menu_item_name]

        # Add prep item if present
        if prep_item_name:
            # Avoid duplicates
            if prep_item_name not in [p["name"] for p in menu_item["prep_items"]]:
                menu_item["prep_items"].append({
                    "name": prep_item_name,
                    "vessel": row.get("Prep Item Vessel", "").strip() or None,
                    "responsibility": row.get("Prep Item Responsibility", "").strip() or None
                })

    print(f"Parsed {len(menus)} menus")

    # Insert data
    menus_created = 0
    items_created = 0
    prep_items_created = 0

    for menu_key, menu_data in menus.items():
        # Check if menu already exists
        cursor.execute("""
            SELECT id FROM banquet_menus
            WHERE outlet_id = %s AND meal_period = %s AND service_type = %s AND name = %s
        """, (outlet_id, menu_data["meal_period"], menu_data["service_type"], menu_data["name"]))

        existing = cursor.fetchone()
        if existing:
            print(f"  Menu already exists: {menu_data['name']} - skipping")
            continue

        # Insert menu
        cursor.execute("""
            INSERT INTO banquet_menus (
                organization_id, outlet_id, meal_period, service_type, name, price_per_person
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            org_id, outlet_id,
            menu_data["meal_period"],
            menu_data["service_type"],
            menu_data["name"],
            menu_data["price_per_person"]
        ))
        menu_id = cursor.fetchone()["id"]
        menus_created += 1
        print(f"  Created menu: {menu_data['name']} (id={menu_id})")

        # Insert menu items
        display_order = 0
        for item_name, item_data in menu_data["menu_items"].items():
            cursor.execute("""
                INSERT INTO banquet_menu_items (
                    banquet_menu_id, name, display_order
                ) VALUES (%s, %s, %s)
                RETURNING id
            """, (menu_id, item_data["name"], display_order))
            item_id = cursor.fetchone()["id"]
            items_created += 1
            display_order += 1

            # Insert prep items
            prep_order = 0
            for prep_data in item_data["prep_items"]:
                cursor.execute("""
                    INSERT INTO banquet_prep_items (
                        banquet_menu_item_id, name, display_order, vessel, responsibility
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    item_id,
                    prep_data["name"],
                    prep_order,
                    prep_data["vessel"],
                    prep_data["responsibility"]
                ))
                prep_items_created += 1
                prep_order += 1

    conn.commit()
    conn.close()

    print("-" * 50)
    print(f"Import complete!")
    print(f"  Menus created: {menus_created}")
    print(f"  Menu items created: {items_created}")
    print(f"  Prep items created: {prep_items_created}")


if __name__ == "__main__":
    main()
