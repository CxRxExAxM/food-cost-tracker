#!/usr/bin/env python3
"""
Delete EHC submissions, form links, and responses for specific records.
Keeps the record definitions but clears all cycle data so you can start fresh.

Usage:
    1. Export your DATABASE_URL:
       export DATABASE_URL="postgresql://user:pass@host:port/db?sslmode=require"

    2. Run the script:
       python scripts/delete_ehc_responses.py

The script will show what will be deleted and ask for confirmation before proceeding.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Records to clean up - edit these as needed
RECORDS_TO_CLEAN = [
    5,
    9,
]

def get_connection():
    """Get database connection from DATABASE_URL env var."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("\nSet it with:")
        print('  export DATABASE_URL="postgresql://user:pass@host:port/db?sslmode=require"')
        sys.exit(1)

    # Show which database we're connecting to (hide password)
    import re
    safe_url = re.sub(r':([^:@]+)@', ':***@', db_url)
    print(f"\nConnecting to: {safe_url}")

    conn = psycopg2.connect(db_url)

    # Verify connection by checking database name
    cursor = conn.cursor()
    cursor.execute("SELECT current_database(), inet_server_addr()")
    db_name, server_addr = cursor.fetchone()
    print(f"Connected to database: {db_name} @ {server_addr}")
    cursor.close()

    return conn

def preview_deletions(cursor):
    """Show what will be deleted without actually deleting."""
    print("\n" + "="*60)
    print("PREVIEW: Data that will be deleted")
    print("="*60)

    totals = {'submissions': 0, 'form_links': 0, 'responses': 0}

    for record_id in RECORDS_TO_CLEAN:
        # Get record info
        cursor.execute("""
            SELECT id, name FROM ehc_record WHERE id = %s
        """, (record_id,))
        record = cursor.fetchone()

        if not record:
            print(f"\n[!] Record #{record_id} not found in database")
            continue

        # Count submissions, form links, and responses
        cursor.execute("""
            SELECT
                COUNT(DISTINCT rs.id) as submission_count,
                COUNT(DISTINCT fl.id) as form_link_count,
                COUNT(fr.id) as response_count
            FROM ehc_record_submission rs
            LEFT JOIN ehc_form_link fl ON fl.submission_id = rs.id
            LEFT JOIN ehc_form_response fr ON fr.form_link_id = fl.id
            WHERE rs.record_id = %s
        """, (record_id,))

        counts = cursor.fetchone()

        print(f"\n Record #{record_id}: {record['name']}")
        print(f"   └── Submissions: {counts['submission_count']}")
        print(f"       └── Form links: {counts['form_link_count']}")
        print(f"           └── Responses: {counts['response_count']}")

        totals['submissions'] += counts['submission_count']
        totals['form_links'] += counts['form_link_count']
        totals['responses'] += counts['response_count']

    print("\n" + "="*60)
    print("TOTALS TO DELETE:")
    print(f"  - {totals['responses']} responses")
    print(f"  - {totals['form_links']} form links (QR templates)")
    print(f"  - {totals['submissions']} submissions")
    print("\nKEEPING: Record definitions (headings)")
    print("="*60)

    return totals

def delete_all_for_records(cursor, conn):
    """Delete submissions, form links, and responses for specified records."""

    for record_id in RECORDS_TO_CLEAN:
        # Get submission IDs for this record
        cursor.execute("""
            SELECT id FROM ehc_record_submission WHERE record_id = %s
        """, (record_id,))
        submission_ids = [row['id'] for row in cursor.fetchall()]

        if not submission_ids:
            print(f"  Record #{record_id}: No submissions found")
            continue

        # Get form_link IDs
        cursor.execute("""
            SELECT id FROM ehc_form_link WHERE submission_id = ANY(%s)
        """, (submission_ids,))
        form_link_ids = [row['id'] for row in cursor.fetchall()]

        # 1. Delete responses first (references form_link)
        if form_link_ids:
            cursor.execute("""
                DELETE FROM ehc_form_response WHERE form_link_id = ANY(%s)
            """, (form_link_ids,))
            print(f"  Record #{record_id}: Deleted {cursor.rowcount} responses")

            # 2. Delete form links (references submission)
            cursor.execute("""
                DELETE FROM ehc_form_link WHERE id = ANY(%s)
            """, (form_link_ids,))
            print(f"  Record #{record_id}: Deleted {cursor.rowcount} form links")

        # 3. Delete submissions (references record)
        cursor.execute("""
            DELETE FROM ehc_record_submission WHERE id = ANY(%s)
        """, (submission_ids,))
        print(f"  Record #{record_id}: Deleted {cursor.rowcount} submissions")

    conn.commit()

def list_all_records(cursor):
    """List all records with their submission/response counts."""
    print("\n" + "="*70)
    print("ALL EHC RECORDS WITH DATA COUNTS")
    print("="*70)

    cursor.execute("""
        SELECT
            r.id,
            r.name,
            COUNT(DISTINCT rs.id) as submissions,
            COUNT(DISTINCT fl.id) as form_links,
            COUNT(fr.id) as responses
        FROM ehc_record r
        LEFT JOIN ehc_record_submission rs ON rs.record_id = r.id
        LEFT JOIN ehc_form_link fl ON fl.submission_id = rs.id
        LEFT JOIN ehc_form_response fr ON fr.form_link_id = fl.id
        GROUP BY r.id, r.name
        ORDER BY r.id
    """)

    records = cursor.fetchall()

    print(f"\n{'ID':<5} {'Record Name':<45} {'Subs':<6} {'Links':<6} {'Resp':<6}")
    print("-"*70)

    for r in records:
        has_data = "  <<<" if r['responses'] > 0 or r['form_links'] > 0 else ""
        print(f"{r['id']:<5} {r['name'][:44]:<45} {r['submissions']:<6} {r['form_links']:<6} {r['responses']:<6}{has_data}")

    print("-"*70)
    print("Records with data marked with <<<")
    print("Update RECORDS_TO_CLEAN in this script with the IDs you want to clear.\n")


def main():
    # Check for --list flag
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        list_all_records(cursor)
        cursor.close()
        conn.close()
        return

    print("\n" + "="*60)
    print("EHC Record Cleanup Script")
    print("="*60)
    print(f"\nTarget records: {RECORDS_TO_CLEAN}")
    print("This will DELETE: submissions, form links, and responses")
    print("This will KEEP: record definitions (headings)")

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Preview what will be deleted
        totals = preview_deletions(cursor)

        if totals['submissions'] == 0 and totals['form_links'] == 0 and totals['responses'] == 0:
            print("\nNothing to delete. These records are already clean.")
            return

        # Ask for confirmation
        print("\n[!] This action cannot be undone!")
        confirm = input("\nType 'DELETE' to confirm deletion: ")

        if confirm != 'DELETE':
            print("\nAborted. No changes made.")
            return

        # Perform deletion
        print("\nDeleting data...")
        delete_all_for_records(cursor, conn)

        print("\n SUCCESS!")
        print("Record definitions remain - you can now create fresh forms.")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()
