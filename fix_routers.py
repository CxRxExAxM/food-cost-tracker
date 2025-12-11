#!/usr/bin/env python3
"""
Script to remove organization_id references from all router files.
"""
import re
from pathlib import Path

def fix_sql_queries(content):
    """Remove organization_id from SQL queries and convert to PostgreSQL syntax."""

    # Convert SQLite placeholders to PostgreSQL
    # This is a simple replacement - be careful with strings containing ?
    content = re.sub(r'\?', '%s', content)

    # Remove "AND organization_id = ?" patterns (now %s)
    content = re.sub(r'\s+AND organization_id = %s', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\s+WHERE organization_id = %s AND', ' WHERE', content, flags=re.IGNORECASE)
    content = re.sub(r'\s+WHERE organization_id = %s', '', content, flags=re.IGNORECASE)

    # Remove organization_id from INSERT column lists
    content = re.sub(r'organization_id,\s*', '', content)
    content = re.sub(r',\s*organization_id', '', content)

    # Remove current_user["organization_id"] from params
    content = re.sub(r'current_user\["organization_id"\],\s*', '', content)
    content = re.sub(r',\s*current_user\["organization_id"\]', '', content)
    content = re.sub(r'current_user\["organization_id"\]', '', content)

    # Update docstrings
    content = re.sub(r'\(organization-scoped\)', '', content)
    content = re.sub(r'organization-scoped\.?\s*', '', content, flags=re.IGNORECASE)
    content = re.sub(r'in current user\'s organization', '', content, flags=re.IGNORECASE)
    content = re.sub(r'current organization', 'database', content, flags=re.IGNORECASE)

    return content

def fix_router_file(filepath):
    """Fix a single router file."""
    print(f"Processing {filepath.name}...")

    content = filepath.read_text()
    original_content = content

    # Apply fixes
    content = fix_sql_queries(content)

    # Write back if changed
    if content != original_content:
        filepath.write_text(content)
        print(f"  ✅ Updated {filepath.name}")
        return True
    else:
        print(f"  ⏭️  No changes needed for {filepath.name}")
        return False

def main():
    """Fix all router files."""
    routers_dir = Path("api/app/routers")

    files_to_fix = [
        "common_products.py",
        "products.py",
        "recipes.py",
        "uploads.py"
    ]

    print("=" * 60)
    print("Fixing Router Files - Removing organization_id")
    print("=" * 60)

    fixed_count = 0
    for filename in files_to_fix:
        filepath = routers_dir / filename
        if filepath.exists():
            if fix_router_file(filepath):
                fixed_count += 1
        else:
            print(f"  ⚠️  {filename} not found")

    print("\n" + "=" * 60)
    print(f"✅ Fixed {fixed_count} router files")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the changes: git diff")
    print("2. Test locally if possible")
    print("3. Commit and push: git add -A && git commit -m 'fix: Remove organization_id from routers'")
    print("4. Deploy to Render")

if __name__ == "__main__":
    main()
