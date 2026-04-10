#!/usr/bin/env python3
"""Seed the Kitchen Audit Checklist template for an organization.

This script creates the EHC Record 20 (Kitchen Audit Checklist) template
with all 58 Y/N questions. Run after migration 039.

Usage:
    python scripts/seed_kitchen_audit_template.py --org-id <organization_id>

    # Or using organization name (partial match, case-insensitive):
    python scripts/seed_kitchen_audit_template.py --org-name "fairmont"

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

# ============================================
# Kitchen Audit Checklist Questions (58 total)
# Record 20 in EHC Standards
# ============================================
# Note: Question 35 reworded so Y = good (was "Are there any obvious signs of pest activity?")

KITCHEN_AUDIT_ITEMS = [
    {"number": 1, "question": "Are all floors, walls and ceiling surfaces clean?", "response_type": "yes_no"},
    {"number": 2, "question": "Are food contact surfaces such as meat slicers, can openers, food mixers, hand whisks clean?", "response_type": "yes_no"},
    {"number": 3, "question": "Are door seals to all coolrooms, refrigeration units and freezer units clean?", "response_type": "yes_no"},
    {"number": 4, "question": "Is there a sanitiser solution available? Is it the correct strength?", "response_type": "yes_no"},
    {"number": 5, "question": "Are all chemicals correctly labelled?", "response_type": "yes_no"},
    {"number": 6, "question": "Are cleaning cloths in good condition and clean?", "response_type": "yes_no"},
    {"number": 7, "question": "Are all cleaning equipment stored correctly?", "response_type": "yes_no"},
    {"number": 8, "question": "Does the dishwasher achieve 55°C / 131°F for wash cycle and 82°C / 179.6°F for rinse cycle?", "response_type": "yes_no"},
    {"number": 9, "question": "Are staff wearing clean clothing?", "response_type": "yes_no"},
    {"number": 10, "question": "Are staff wearing protective head covering, including stewarding staff?", "response_type": "yes_no"},
    {"number": 11, "question": "Are staff wearing and using gloves correctly?", "response_type": "yes_no"},
    {"number": 12, "question": "Are there blue band aids available for use by staff in the kitchen?", "response_type": "yes_no"},
    {"number": 13, "question": "Have staff covered all cuts and wounds?", "response_type": "yes_no"},
    {"number": 14, "question": "Is there a wash hand basin in the kitchen?", "response_type": "yes_no"},
    {"number": 15, "question": "Does the wash hand basin have hot water to 38°C / 100.4°F within 30 seconds, soap and paper towels to dry hands?", "response_type": "yes_no"},
    {"number": 16, "question": "Are wash hand basins only being used for hand washing?", "response_type": "yes_no"},
    {"number": 17, "question": "Does the wash hand basin have direct access with nothing blocking regular use?", "response_type": "yes_no"},
    {"number": 18, "question": "Is there a waste bin for staff to use in the kitchen?", "response_type": "yes_no"},
    {"number": 19, "question": "Is there a lid for the bin when the kitchen is not in use?", "response_type": "yes_no"},
    {"number": 20, "question": "Are all coolrooms and refrigeration units operating at 5°C / 41°F or below?", "response_type": "yes_no"},
    {"number": 21, "question": "Are all freezer units operating at -18°C / 0°F or below?", "response_type": "yes_no"},
    {"number": 22, "question": "Are all foods covered?", "response_type": "yes_no"},
    {"number": 23, "question": "Are staff only using plastic, stainless steel or aluminium foil to cover foods?", "response_type": "yes_no"},
    {"number": 24, "question": "Are all foods labelled?", "response_type": "yes_no"},
    {"number": 25, "question": "Are all foods date coded?", "response_type": "yes_no"},
    {"number": 26, "question": "Are all foods stored within the area in date?", "response_type": "yes_no"},
    {"number": 27, "question": "Are all raw foods stored separate or below cooked foods or ready to eat foods?", "response_type": "yes_no"},
    {"number": 28, "question": "Are fruits and salad items being chlorinated at 100ppm (5 minute contact time) or if Acid wash is pH3 or below (1 minute contact time)?", "response_type": "yes_no"},
    {"number": 29, "question": "Are all ceilings, walls and floors in good structural condition with no holes, damage or disrepair?", "response_type": "yes_no"},
    {"number": 30, "question": "Are all the lights diffused (covered)?", "response_type": "yes_no"},
    {"number": 31, "question": "Is all food contact equipment in good condition?", "response_type": "yes_no"},
    {"number": 32, "question": "Are door seals to all coolrooms, refrigeration units and freezer units in good condition and not damaged?", "response_type": "yes_no"},
    {"number": 33, "question": "Have all wooden equipment been removed from the kitchen?", "response_type": "yes_no"},
    {"number": 34, "question": "Have all unnecessary glass been removed from the kitchen?", "response_type": "yes_no"},
    # Question 35 REWORDED: Original was "Are there any obvious signs of pest activity?" (Y=bad)
    # Now phrased so Y=good like all other questions
    {"number": 35, "question": "Is the area free from obvious signs of pest activity?", "response_type": "yes_no"},
    {"number": 36, "question": "Is there a designated cooling of food location?", "response_type": "yes_no"},
    {"number": 37, "question": "Are staff cooling foods correctly?", "response_type": "yes_no"},
    {"number": 38, "question": "Are colour coded boards being used?", "response_type": "yes_no"},
    {"number": 39, "question": "Are staff using the correct colours for the foods in relation to the colour coded boards?", "response_type": "yes_no"},
    {"number": 40, "question": "Is there a cutting board rack?", "response_type": "yes_no"},
    {"number": 41, "question": "Are there sterilising wipes for the cleaning of the thermometers used within the kitchen?", "response_type": "yes_no"},
    {"number": 42, "question": "Is there at least 1 operating probe thermometer for staff to use within the kitchen?", "response_type": "yes_no"},
    {"number": 43, "question": "Are there cooking/reheating temperature records?", "response_type": "yes_no"},
    {"number": 44, "question": "Are there cooling temperature records?", "response_type": "yes_no"},
    {"number": 45, "question": "Are there calibration records for the thermometers used within the kitchen?", "response_type": "yes_no"},
    {"number": 46, "question": "Are there temperature records for coolrooms, refrigeration units and freezer units?", "response_type": "yes_no"},
    {"number": 47, "question": "Is there a cleaning schedule for this area including every fixture and fitting?", "response_type": "yes_no"},
    {"number": 48, "question": "Do all records appear to be completed correctly - with black/blue pen, temperatures measured to the decimal point and not made up?", "response_type": "yes_no"},
    {"number": 49, "question": "Have the staff been trained in food safety within the last 12 months?", "response_type": "yes_no"},
    {"number": 50, "question": "Have all staff completed Record 11?", "response_type": "yes_no"},
    {"number": 51, "question": "Is the dishwasher / glass washer temperature record completed daily?", "response_type": "yes_no"},
    # Bar-specific questions (52-58) - shown to all outlets per Mike's confirmation
    {"number": 52, "question": "Has the bar got sterilising gel?", "response_type": "yes_no"},
    {"number": 53, "question": "Does the bar have a green cutting board for garnishes?", "response_type": "yes_no"},
    {"number": 54, "question": "Are raw eggs an ingredient for any cocktails?", "response_type": "yes_no"},
    {"number": 55, "question": "Is the milk and other dairy products being stored at the correct temperature?", "response_type": "yes_no"},
    {"number": 56, "question": "Are all bar snacks stored correctly with labelling & dating?", "response_type": "yes_no"},
    {"number": 57, "question": "Are straws individually wrapped or otherwise protected?", "response_type": "yes_no"},
    {"number": 58, "question": "Are glasses clean and polished?", "response_type": "yes_no"},
]

TEMPLATE_CONFIG = {
    "intro_text": "This checklist is developed to provide an internal audit tool for hygiene champions. Walk through each item and mark Y or N. Any 'N' answers require corrective action documentation.",
    "items": KITCHEN_AUDIT_ITEMS,
    "corrective_actions": True,
    "signature_required": True,
}


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


def find_organization(cursor, org_id=None, org_name=None):
    """Find organization by ID or name."""
    if org_id:
        cursor.execute("SELECT id, name FROM organizations WHERE id = %s", (org_id,))
    elif org_name:
        cursor.execute("SELECT id, name FROM organizations WHERE name ILIKE %s", (f"%{org_name}%",))
    else:
        print("ERROR: Must specify --org-id or --org-name")
        sys.exit(1)

    result = cursor.fetchone()
    if not result:
        print(f"ERROR: Organization not found")
        sys.exit(1)

    return result


def find_record_20(cursor, org_id):
    """Find EHC Record 20 (Kitchen Audit Checklist) for the organization."""
    cursor.execute("""
        SELECT id, name, record_number
        FROM ehc_record
        WHERE organization_id = %s AND record_number = '20'
    """, (org_id,))

    result = cursor.fetchone()
    if not result:
        print("WARNING: EHC Record 20 not found for this organization")
        print("         Template will be created without linking to a specific record")
        return None

    return result


def check_existing_template(cursor, org_id):
    """Check if a Kitchen Audit template already exists."""
    cursor.execute("""
        SELECT id, name
        FROM ehc_form_template
        WHERE organization_id = %s
          AND name = 'Kitchen Audit Checklist'
          AND is_active = true
    """, (org_id,))

    return cursor.fetchone()


def create_template(cursor, org_id, record_id=None):
    """Create the Kitchen Audit Checklist template."""
    cursor.execute("""
        INSERT INTO ehc_form_template (
            organization_id,
            name,
            form_type,
            ehc_record_id,
            config,
            is_active
        ) VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        org_id,
        'Kitchen Audit Checklist',
        'checklist_form',
        record_id,
        json.dumps(TEMPLATE_CONFIG),
        True
    ))

    return cursor.fetchone()['id']


def main():
    parser = argparse.ArgumentParser(description='Seed Kitchen Audit Checklist template')
    parser.add_argument('--org-id', type=int, help='Organization ID')
    parser.add_argument('--org-name', type=str, help='Organization name (partial match)')
    parser.add_argument('--force', action='store_true', help='Overwrite existing template')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')

    args = parser.parse_args()

    if not args.org_id and not args.org_name:
        parser.print_help()
        sys.exit(1)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Find organization
        org = find_organization(cursor, args.org_id, args.org_name)
        print(f"Organization: {org['name']} (ID: {org['id']})")

        # Check for existing template
        existing = check_existing_template(cursor, org['id'])
        if existing:
            if args.force:
                print(f"Existing template found (ID: {existing['id']}) - will deactivate")
                if not args.dry_run:
                    cursor.execute("""
                        UPDATE ehc_form_template
                        SET is_active = false, updated_at = NOW()
                        WHERE id = %s
                    """, (existing['id'],))
            else:
                print(f"ERROR: Template already exists (ID: {existing['id']})")
                print("       Use --force to deactivate existing and create new")
                sys.exit(1)

        # Find Record 20
        record = find_record_20(cursor, org['id'])
        if record:
            print(f"Linking to: {record['name']} (Record {record['record_number']}, ID: {record['id']})")

        # Create template
        print(f"\nTemplate config:")
        print(f"  - Name: Kitchen Audit Checklist")
        print(f"  - Form type: checklist_form")
        print(f"  - Questions: {len(KITCHEN_AUDIT_ITEMS)}")
        print(f"  - Corrective actions: enabled")
        print(f"  - Signature required: yes")

        if args.dry_run:
            print("\n[DRY RUN] Would create template - no changes made")
        else:
            template_id = create_template(
                cursor,
                org['id'],
                record['id'] if record else None
            )
            conn.commit()
            print(f"\n✓ Template created successfully (ID: {template_id})")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
