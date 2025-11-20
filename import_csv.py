import pandas as pd
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import uuid


DB_PATH = Path(__file__).parent / "db" / "food_cost_tracker.db"


def get_distributor_id(cursor, distributor_code):
    """Get distributor ID from code."""
    cursor.execute("SELECT id FROM distributors WHERE code = ?", (distributor_code,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Distributor '{distributor_code}' not found in database")
    return result[0]


def get_unit_id(cursor, unit_abbr):
    """Get unit ID from abbreviation."""
    cursor.execute("SELECT id FROM units WHERE abbreviation = ?", (unit_abbr,))
    result = cursor.fetchone()
    if result:
        return result[0]

    # If not found, try to match by name
    cursor.execute("SELECT id FROM units WHERE name LIKE ?", (f"%{unit_abbr}%",))
    result = cursor.fetchone()
    return result[0] if result else None


def import_csv(csv_file, distributor_code, effective_date=None):
    """
    Import cleaned CSV data into the database.

    Args:
        csv_file: Path to the cleaned CSV file
        distributor_code: Distributor code (sysco, vesta, etc.)
        effective_date: Price effective date (defaults to today)
    """

    if not Path(csv_file).exists():
        print(f"Error: File '{csv_file}' not found")
        return False

    if effective_date is None:
        effective_date = datetime.now().date()
    elif isinstance(effective_date, str):
        effective_date = datetime.strptime(effective_date, "%Y-%m-%d").date()

    print(f"\nImporting {csv_file} for distributor '{distributor_code}'...")
    print(f"Effective date: {effective_date}")

    # Read the CSV
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} rows from CSV")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return False

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Get distributor ID
        distributor_id = get_distributor_id(cursor, distributor_code)

        # Create import batch
        batch_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO import_batches (id, distributor_id, filename, import_date)
            VALUES (?, ?, ?, ?)
        """, (batch_id, distributor_id, Path(csv_file).name, datetime.now()))

        rows_imported = 0
        rows_failed = 0

        # Process each row
        for idx, row in df.iterrows():
            try:
                # Extract data from CSV row
                # name = Description from CSV (what the product actually is)
                # brand = Brand from CSV (manufacturer/brand name)
                product_name = str(row.get('Desc', '')) if pd.notna(row.get('Desc')) else ''
                product_name = product_name.strip()

                sku = str(row.get('SUPC', ''))
                brand = str(row.get('Brand', '')) if pd.notna(row.get('Brand')) else None
                pack = int(row.get('Pack', 0)) if pd.notna(row.get('Pack')) else None
                size = float(row.get('Size', 0)) if pd.notna(row.get('Size')) else None
                unit_abbr = str(row.get('Unit', '')) if pd.notna(row.get('Unit')) else None
                case_price = float(row.get('Case $', 0)) if pd.notna(row.get('Case $')) else None
                unit_price = float(row.get('Unit $', 0)) if pd.notna(row.get('Unit $')) else None

                # Get unit_id
                unit_id = get_unit_id(cursor, unit_abbr) if unit_abbr else None

                # Check if product already exists
                cursor.execute("""
                    SELECT p.id, dp.id
                    FROM products p
                    LEFT JOIN distributor_products dp ON dp.product_id = p.id AND dp.distributor_id = ?
                    WHERE p.name = ? AND p.brand = ? AND p.pack = ? AND p.size = ?
                """, (distributor_id, product_name, brand, pack, size))

                existing = cursor.fetchone()

                if existing and existing[0]:
                    # Product exists
                    product_id = existing[0]
                    distributor_product_id = existing[1]

                    if not distributor_product_id:
                        # Create distributor_product link
                        cursor.execute("""
                            INSERT INTO distributor_products (distributor_id, product_id, distributor_sku, distributor_name)
                            VALUES (?, ?, ?, ?)
                        """, (distributor_id, product_id, sku, product_name))
                        distributor_product_id = cursor.lastrowid
                else:
                    # Create new product
                    cursor.execute("""
                        INSERT INTO products (name, brand, pack, size, unit_id)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_name, brand, pack, size, unit_id))
                    product_id = cursor.lastrowid

                    # Create distributor_product link
                    cursor.execute("""
                        INSERT INTO distributor_products (distributor_id, product_id, distributor_sku, distributor_name)
                        VALUES (?, ?, ?, ?)
                    """, (distributor_id, product_id, sku, product_name))
                    distributor_product_id = cursor.lastrowid

                # Insert or update price
                if case_price is not None:
                    cursor.execute("""
                        INSERT INTO price_history (distributor_product_id, case_price, unit_price, effective_date, import_batch_id)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(distributor_product_id, effective_date)
                        DO UPDATE SET case_price = ?, unit_price = ?, import_batch_id = ?
                    """, (distributor_product_id, case_price, unit_price, effective_date, batch_id,
                          case_price, unit_price, batch_id))

                rows_imported += 1

                if (idx + 1) % 100 == 0:
                    print(f"  Processed {idx + 1} rows...")

            except Exception as e:
                print(f"  Error on row {idx + 1}: {e}")
                rows_failed += 1
                continue

        # Update batch statistics
        cursor.execute("""
            UPDATE import_batches
            SET rows_imported = ?, rows_failed = ?
            WHERE id = ?
        """, (rows_imported, rows_failed, batch_id))

        conn.commit()

        print(f"\n✓ Import complete!")
        print(f"  Successfully imported: {rows_imported} rows")
        print(f"  Failed: {rows_failed} rows")
        print(f"  Batch ID: {batch_id}")

        return True

    except Exception as e:
        print(f"\nError during import: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


def main():
    """Main function to handle command-line arguments."""

    if len(sys.argv) < 3:
        print("Usage: python import_csv.py <csv_file> <distributor_code> [effective_date]")
        print("\nDistributor codes: sysco, vesta, smseafood, shamrock, noblebread, sterling")
        print("Date format: YYYY-MM-DD (optional, defaults to today)")
        print("\nExample: python import_csv.py cleaned_sysco.csv sysco 2025-01-15")
        sys.exit(1)

    csv_file = sys.argv[1]
    distributor_code = sys.argv[2]
    effective_date = sys.argv[3] if len(sys.argv) > 3 else None

    success = import_csv(csv_file, distributor_code, effective_date)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
