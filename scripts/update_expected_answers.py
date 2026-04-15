#!/usr/bin/env python3
"""Update Kitchen Audit template with expected_answer values.

This script updates question 54 to have expected_answer: "N" since
"No raw eggs in cocktails" is the compliant response.

Updates both:
1. ehc_form_template.config (template definition)
2. ehc_form_link.config (deployed form instances)

Usage:
    python scripts/update_expected_answers.py --org-name "fairmont"
    python scripts/update_expected_answers.py --org-id 1
    python scripts/update_expected_answers.py --all

Requires DATABASE_URL environment variable.
"""
import os
import sys
import argparse
import json

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection from DATABASE_URL."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Handle Render's postgres:// vs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def update_item_expected_answer(items, question_number, expected_answer):
    """Update a specific question's expected_answer in items list."""
    updated = False
    for item in items:
        if item.get('number') == question_number:
            item['expected_answer'] = expected_answer
            updated = True
            break
    return updated


def update_templates(cursor, org_id=None, dry_run=False):
    """Update ehc_form_template configs."""
    if org_id:
        cursor.execute("""
            SELECT id, name, organization_id, config
            FROM ehc_form_template
            WHERE organization_id = %s
              AND form_type = 'checklist_form'
              AND is_active = true
        """, (org_id,))
    else:
        cursor.execute("""
            SELECT id, name, organization_id, config
            FROM ehc_form_template
            WHERE form_type = 'checklist_form'
              AND is_active = true
        """)

    templates = cursor.fetchall()
    updated_count = 0

    for tmpl in templates:
        config = tmpl['config']
        if not config:
            continue

        # Parse if string
        if isinstance(config, str):
            config = json.loads(config)

        items = config.get('items', [])
        if not items:
            continue

        # Update question 54 expected_answer
        modified = update_item_expected_answer(items, 54, 'N')

        if modified:
            if dry_run:
                print(f"  [DRY RUN] Would update template ID {tmpl['id']}: {tmpl['name']}")
            else:
                cursor.execute("""
                    UPDATE ehc_form_template
                    SET config = %s, updated_at = NOW()
                    WHERE id = %s
                """, (json.dumps(config), tmpl['id']))
                print(f"  ✓ Updated template ID {tmpl['id']}: {tmpl['name']}")
            updated_count += 1

    return updated_count


def update_form_links(cursor, org_id=None, dry_run=False):
    """Update ehc_form_link configs."""
    if org_id:
        cursor.execute("""
            SELECT fl.id, fl.outlet_name, fl.config, ft.name as template_name
            FROM ehc_form_link fl
            JOIN ehc_form_template ft ON fl.template_id = ft.id
            WHERE ft.organization_id = %s
              AND ft.form_type = 'checklist_form'
        """, (org_id,))
    else:
        cursor.execute("""
            SELECT fl.id, fl.outlet_name, fl.config, ft.name as template_name
            FROM ehc_form_link fl
            JOIN ehc_form_template ft ON fl.template_id = ft.id
            WHERE ft.form_type = 'checklist_form'
        """)

    form_links = cursor.fetchall()
    updated_count = 0

    for fl in form_links:
        config = fl['config']
        if not config:
            continue

        # Parse if string
        if isinstance(config, str):
            config = json.loads(config)

        items = config.get('items', [])
        if not items:
            continue

        # Update question 54 expected_answer
        modified = update_item_expected_answer(items, 54, 'N')

        if modified:
            outlet_display = fl['outlet_name'] or 'Unknown outlet'
            if dry_run:
                print(f"  [DRY RUN] Would update form link ID {fl['id']}: {outlet_display}")
            else:
                cursor.execute("""
                    UPDATE ehc_form_link
                    SET config = %s
                    WHERE id = %s
                """, (json.dumps(config), fl['id']))
                print(f"  ✓ Updated form link ID {fl['id']}: {outlet_display}")
            updated_count += 1

    return updated_count


def main():
    parser = argparse.ArgumentParser(description='Update Kitchen Audit expected_answer values')
    parser.add_argument('--org-id', type=int, help='Organization ID')
    parser.add_argument('--org-name', type=str, help='Organization name (partial match)')
    parser.add_argument('--all', action='store_true', help='Update all organizations')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    if not args.org_id and not args.org_name and not args.all:
        parser.print_help()
        sys.exit(1)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        org_id = None

        if args.org_id:
            cursor.execute("SELECT id, name FROM organizations WHERE id = %s", (args.org_id,))
            org = cursor.fetchone()
            if not org:
                print(f"ERROR: Organization ID {args.org_id} not found")
                sys.exit(1)
            org_id = org['id']
            print(f"Organization: {org['name']} (ID: {org_id})")

        elif args.org_name:
            cursor.execute("SELECT id, name FROM organizations WHERE name ILIKE %s", (f"%{args.org_name}%",))
            org = cursor.fetchone()
            if not org:
                print(f"ERROR: Organization matching '{args.org_name}' not found")
                sys.exit(1)
            org_id = org['id']
            print(f"Organization: {org['name']} (ID: {org_id})")

        else:
            print("Updating ALL organizations")

        print("\n--- Updating Templates ---")
        template_count = update_templates(cursor, org_id, args.dry_run)
        print(f"Templates updated: {template_count}")

        print("\n--- Updating Form Links ---")
        form_link_count = update_form_links(cursor, org_id, args.dry_run)
        print(f"Form links updated: {form_link_count}")

        if args.dry_run:
            print("\n[DRY RUN] No changes made")
        else:
            conn.commit()
            print(f"\n✓ Done! Updated {template_count} templates and {form_link_count} form links")
            print("\nChanges made:")
            print("  - Question 54 ('Are raw eggs an ingredient for any cocktails?')")
            print("    now has expected_answer: 'N'")
            print("    (Answering 'N' = compliant, 'Y' = non-compliant)")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
