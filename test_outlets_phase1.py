#!/usr/bin/env python3
"""
Phase 1 Multi-Outlet Backend Testing Script

Tests database migration and outlet functionality.
Run from project root: python test_outlets_phase1.py
"""

import os
import sys
from pathlib import Path

# Add api directory to path
sys.path.insert(0, str(Path(__file__).parent / "api"))

from app.database import get_db

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_section(title):
    print(f"\n{BLUE}{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}{RESET}\n")


# =============================================================================
# Test Suite 1: Database Migration Verification
# =============================================================================

def test_outlets_table():
    """Verify outlets table exists with correct structure."""
    print_section("TEST 1: Outlets Table Structure")

    with get_db() as conn:
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'outlets'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()

        if not columns:
            print_error("Outlets table does not exist!")
            return False

        print_info(f"Found {len(columns)} columns in outlets table:")

        expected_columns = {
            'id', 'organization_id', 'name', 'location', 'description',
            'is_active', 'created_at', 'updated_at'
        }

        actual_columns = {col['column_name'] for col in columns}

        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            print(f"  - {col['column_name']:20} {col['data_type']:20} {nullable}")

        if expected_columns.issubset(actual_columns):
            print_success("Outlets table has all required columns")
            return True
        else:
            missing = expected_columns - actual_columns
            print_error(f"Missing columns: {missing}")
            return False


def test_user_outlets_table():
    """Verify user_outlets junction table exists."""
    print_section("TEST 2: User-Outlets Junction Table")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'user_outlets'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()

        if not columns:
            print_error("user_outlets table does not exist!")
            return False

        print_info("user_outlets table structure:")
        for col in columns:
            print(f"  - {col['column_name']:20} {col['data_type']}")

        # Required columns (created_at is optional but acceptable)
        required = {'user_id', 'outlet_id'}
        actual = {col['column_name'] for col in columns}

        if required.issubset(actual):
            print_success("user_outlets table has all required columns")
            if 'created_at' in actual:
                print_info("  (Also has created_at timestamp - good for audit trail)")
            return True
        else:
            missing = required - actual
            print_error(f"Missing required columns: {missing}")
            return False


def test_outlet_id_columns():
    """Verify outlet_id added to products, recipes, etc."""
    print_section("TEST 3: outlet_id Column Migration")

    tables_to_check = ['products', 'recipes', 'distributor_products', 'import_batches']

    with get_db() as conn:
        cursor = conn.cursor()
        all_good = True

        for table in tables_to_check:
            cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = 'outlet_id';
            """)

            if cursor.fetchone():
                # Check how many records have outlet_id populated
                cursor.execute(f"""
                    SELECT COUNT(*) as total,
                           COUNT(outlet_id) as with_outlet
                    FROM {table};
                """)
                stats = cursor.fetchone()

                if stats['total'] > 0:
                    percentage = (stats['with_outlet'] / stats['total']) * 100
                    print_info(f"{table}: {stats['with_outlet']}/{stats['total']} records with outlet_id ({percentage:.1f}%)")

                    if stats['total'] > 0 and stats['with_outlet'] == 0:
                        print_warning(f"  WARNING: {table} has records but none have outlet_id!")
                        all_good = False
                else:
                    print_info(f"{table}: Table empty (OK for fresh install)")
            else:
                print_error(f"{table}: outlet_id column missing!")
                all_good = False

        if all_good:
            print_success("outlet_id columns exist and are populated")

        return all_good


def test_default_outlets():
    """Verify default outlets were created for existing organizations."""
    print_section("TEST 4: Default Outlet Creation")

    with get_db() as conn:
        cursor = conn.cursor()

        # Count organizations
        cursor.execute("SELECT COUNT(*) as count FROM organizations WHERE is_active = 1;")
        org_count = cursor.fetchone()['count']

        # Count default outlets
        cursor.execute("""
            SELECT o.id, o.name, org.name as organization_name, o.is_active
            FROM outlets o
            JOIN organizations org ON org.id = o.organization_id
            WHERE o.name = 'Default Outlet';
        """)

        default_outlets = cursor.fetchall()

        print_info(f"Found {org_count} active organizations")
        print_info(f"Found {len(default_outlets)} 'Default Outlet' entries")

        if default_outlets:
            for outlet in default_outlets:
                print(f"  - Outlet ID {outlet['id']}: {outlet['name']} ({outlet['organization_name']})")

        if len(default_outlets) >= org_count:
            print_success("Default outlets created successfully")
            return True
        elif org_count == 0:
            print_warning("No organizations exist - cannot test default outlet creation")
            return True
        else:
            print_error(f"Missing default outlets! Expected at least {org_count}, found {len(default_outlets)}")
            return False


# =============================================================================
# Test Suite 2: Outlet Data
# =============================================================================

def test_list_outlets():
    """Show all outlets in database."""
    print_section("TEST 5: List All Outlets")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.id, o.name, o.location, o.is_active,
                   org.name as organization_name
            FROM outlets o
            JOIN organizations org ON org.id = o.organization_id
            ORDER BY org.name, o.name;
        """)

        outlets = cursor.fetchall()

        if not outlets:
            print_warning("No outlets found in database")
            return False

        print_info(f"Found {len(outlets)} outlets:")
        print()
        print(f"{'ID':<5} {'Organization':<30} {'Outlet Name':<30} {'Location':<20} {'Active'}")
        print("-" * 100)

        for outlet in outlets:
            active = "Yes" if outlet['is_active'] else "No"
            location = outlet['location'] or "(none)"
            print(f"{outlet['id']:<5} {outlet['organization_name']:<30} {outlet['name']:<30} {location:<20} {active}")

        print_success(f"Listed {len(outlets)} outlets")
        return True


def test_user_outlet_assignments():
    """Show user-outlet assignments."""
    print_section("TEST 6: User-Outlet Assignments")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.id as user_id, u.email, u.role,
                   o.id as outlet_id, o.name as outlet_name,
                   org.name as organization_name
            FROM user_outlets uo
            JOIN users u ON u.id = uo.user_id
            JOIN outlets o ON o.id = uo.outlet_id
            JOIN organizations org ON org.id = u.organization_id
            ORDER BY org.name, u.email, o.name;
        """)

        assignments = cursor.fetchall()

        if not assignments:
            print_info("No user-outlet assignments found")
            print_info("(Users with no assignments = org-wide admins)")
            return True

        print_info(f"Found {len(assignments)} user-outlet assignments:")
        print()

        current_user = None
        for asn in assignments:
            if current_user != asn['email']:
                current_user = asn['email']
                print(f"\n{asn['email']} ({asn['role']}) - {asn['organization_name']}:")
            print(f"  → Outlet {asn['outlet_id']}: {asn['outlet_name']}")

        print()
        print_success("User-outlet assignments listed")
        return True


def test_org_wide_admins():
    """Identify users with no outlet assignments (org-wide admins)."""
    print_section("TEST 7: Org-Wide Admin Detection")

    with get_db() as conn:
        cursor = conn.cursor()

        # Find users with NO outlet assignments
        cursor.execute("""
            SELECT u.id, u.email, u.role, org.name as organization_name
            FROM users u
            JOIN organizations org ON org.id = u.organization_id
            LEFT JOIN user_outlets uo ON uo.user_id = u.id
            WHERE uo.user_id IS NULL AND u.is_active = 1
            ORDER BY org.name, u.email;
        """)

        admins = cursor.fetchall()

        if not admins:
            print_warning("No org-wide admins found (all users have outlet assignments)")
            print_info("This means no user can see ALL outlets in their organization")
            return True

        print_info(f"Found {len(admins)} org-wide admins (no outlet restrictions):")
        print()

        for admin in admins:
            print(f"  {admin['email']} ({admin['role']}) - {admin['organization_name']}")

        print()
        print_success("Org-wide admins identified")
        return True


# =============================================================================
# Test Suite 3: Products with Outlets
# =============================================================================

def test_products_with_outlets():
    """Verify products have outlet assignments."""
    print_section("TEST 8: Products with Outlet Assignments")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.id as outlet_id, o.name as outlet_name,
                   org.name as organization_name,
                   COUNT(p.id) as product_count
            FROM outlets o
            JOIN organizations org ON org.id = o.organization_id
            LEFT JOIN products p ON p.outlet_id = o.id AND p.is_active = 1
            GROUP BY o.id, o.name, org.name
            ORDER BY org.name, o.name;
        """)

        stats = cursor.fetchall()

        if not stats:
            print_warning("No outlet statistics available")
            return False

        print_info("Products per outlet:")
        print()
        print(f"{'Organization':<30} {'Outlet':<30} {'Products'}")
        print("-" * 70)

        for stat in stats:
            print(f"{stat['organization_name']:<30} {stat['outlet_name']:<30} {stat['product_count']}")

        total_products = sum(s['product_count'] for s in stats)
        print()
        print_success(f"Total: {total_products} products across {len(stats)} outlets")

        return True


def test_recipes_with_outlets():
    """Verify recipes have outlet assignments."""
    print_section("TEST 9: Recipes with Outlet Assignments")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.id as outlet_id, o.name as outlet_name,
                   org.name as organization_name,
                   COUNT(r.id) as recipe_count
            FROM outlets o
            JOIN organizations org ON org.id = o.organization_id
            LEFT JOIN recipes r ON r.outlet_id = o.id AND r.is_active = 1
            GROUP BY o.id, o.name, org.name
            ORDER BY org.name, o.name;
        """)

        stats = cursor.fetchall()

        if not stats:
            print_warning("No outlet statistics available")
            return False

        print_info("Recipes per outlet:")
        print()
        print(f"{'Organization':<30} {'Outlet':<30} {'Recipes'}")
        print("-" * 70)

        for stat in stats:
            print(f"{stat['organization_name']:<30} {stat['outlet_name']:<30} {stat['recipe_count']}")

        total_recipes = sum(s['recipe_count'] for s in stats)
        print()
        print_success(f"Total: {total_recipes} recipes across {len(stats)} outlets")

        return True


# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all tests."""
    print(f"\n{BLUE}╔═══════════════════════════════════════════════════════════╗")
    print(f"║                                                           ║")
    print(f"║   Phase 1 Multi-Outlet Backend - Database Tests          ║")
    print(f"║                                                           ║")
    print(f"╚═══════════════════════════════════════════════════════════╝{RESET}\n")

    # Check DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print_error("DATABASE_URL environment variable not set!")
        print_info("Set it in your .env file or export it:")
        print_info("  export DATABASE_URL='postgresql://user:pass@host:port/dbname'")
        return 1

    tests = [
        ("Outlets Table Structure", test_outlets_table),
        ("User-Outlets Junction Table", test_user_outlets_table),
        ("outlet_id Column Migration", test_outlet_id_columns),
        ("Default Outlet Creation", test_default_outlets),
        ("List All Outlets", test_list_outlets),
        ("User-Outlet Assignments", test_user_outlet_assignments),
        ("Org-Wide Admin Detection", test_org_wide_admins),
        ("Products with Outlets", test_products_with_outlets),
        ("Recipes with Outlets", test_recipes_with_outlets),
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")

    print()
    print(f"Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}, {len(results)} total")
    print()

    if failed == 0:
        print_success("All database tests passed! ✨")
        print_info("\nNext steps:")
        print_info("  1. Test API endpoints with actual HTTP requests")
        print_info("  2. Test outlet-specific pricing in recipe costing")
        print_info("  3. Test CSV uploads with outlet assignment")
        print_info("  4. Test access control and data isolation")
        return 0
    else:
        print_error(f"{failed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
