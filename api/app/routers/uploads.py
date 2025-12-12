"""
Upload router for handling vendor CSV file uploads.
Integrates vendor-specific cleaning and database import.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import pandas as pd
import io
import uuid
import re

from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/uploads", tags=["uploads"])


# Vendor-specific cleaning configurations
VENDOR_CONFIGS = {
    "sysco": {
        "header_row": 1,  # Skip first row, use row 1 as header
        "columns_to_drop": [
            'F', 'Case Qty', 'Split Qty', 'Code', 'Item Status',
            'Replaced Item', 'Mfr #', 'Split $', 'Per Lb', 'Market',
            'Splittable', 'Splits', 'Min Split', 'Net Wt', 'Lead Time',
            'Stock', 'Substitute', 'Agr', 'Unnamed: 26', 'Unnamed: 27'
        ],
        "unit_replacements": {"#": "LB"},
        "calculate_unit_price": True,
    },
    "vesta": {
        "header_row": 10,  # Vesta has 10 header rows before data
        "columns_to_drop": [],
        "unit_replacements": {
            'BK': 'PACK',
            'GL': 'GAL',
            'LT': 'L',
            'BU': 'BUNCH',
        },
        "calculate_unit_price": False,
        "parse_packaging": True,  # Vesta needs packaging column parsed
        "column_renames": {
            'Produce Description': 'Desc',
            'Prod Number': 'SUPC',
            'Price': 'Case $',
        },
    },
    "smseafood": {
        "header_row": 0,
        "columns_to_drop": [],
        "unit_replacements": {},
        "calculate_unit_price": False,
    },
    "shamrock": {
        "header_row": 3,
        "skip_first_data_row": True,  # First data row is actually column headers
        "columns_to_drop": ['Unnamed: 0', 'Unnamed: 1', '#', 'Unnamed: 4', 'Unnamed: 5', 'LWP', 'Avg'],
        "unit_replacements": {
            'CS': 'CASE',
            'LBA': 'LB',
            'PK': 'PACK',
        },
        "calculate_unit_price": False,
        "parse_shamrock_packaging": True,  # Parse Pack Size column
        "column_renames": {
            'Product #': 'SUPC',
            'Description': 'Desc',
            'Price': 'Case $',
        },
        "price_column_has_dollar": True,
    },
    "noblebread": {
        "header_row": 0,
        "columns_to_drop": [],
        "unit_replacements": {},
        "calculate_unit_price": False,
    },
    "sterling": {
        "header_row": 0,
        "columns_to_drop": [],
        "unit_replacements": {},
        "calculate_unit_price": False,
    },
}


class UploadResult(BaseModel):
    """Response model for upload results."""
    success: bool
    message: str
    batch_id: Optional[str] = None
    rows_imported: int = 0
    rows_failed: int = 0
    new_products: int = 0
    updated_prices: int = 0
    errors: list[str] = []


@router.get("/distributors")
def get_upload_distributors():
    """
    Get list of distributors for the upload form.
    Public endpoint - no auth required.
    """
    from ..database import dicts_from_rows
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code FROM distributors WHERE is_active = 1 ORDER BY name")
        distributors = dicts_from_rows(cursor.fetchall())
        return distributors


def parse_vesta_packaging(value):
    """
    Parse Vesta packaging value into pack, size, and unit.

    Examples:
        '4/5 LB' -> (4, 5.0, 'LB')
        '120/138 CT' -> (1, 129.0, 'CT')  # CT range, use midpoint
        '8/24 CT' -> (8, 24.0, 'CT')
        'LB' -> (1, None, 'LB')
    """
    if pd.isna(value) or str(value).strip() == '':
        return (None, None, None)

    value = str(value).strip()

    # Split by last space
    if ' ' in value:
        amount_part, unit = value.rsplit(' ', 1)
        unit = unit.upper()
    else:
        return (1, None, value.upper())

    # Parse amount_part
    if '/' in amount_part:
        parts = amount_part.split('/')
        try:
            first_num = float(parts[0])
            second_num = float(parts[1])

            # If unit is CT and first number > 20, treat as range
            is_range = (unit == 'CT' and first_num > 20)

            if is_range:
                pack = 1
                size = (first_num + second_num) / 2
            else:
                pack = int(first_num)
                size = second_num
        except ValueError:
            return (1, None, unit)
    else:
        try:
            pack = 1
            size = float(amount_part)
        except ValueError:
            return (1, None, unit)

    return (pack, size, unit)


def parse_shamrock_packaging(value):
    """
    Parse Shamrock Pack Size into Pack, Size, Unit, and is_catch_weight.

    Examples:
        '1/120/PK' -> (1, 120.0, 'PK', False)
        '1/10/LBAV' -> (1, 10.0, 'LB', True)
        '24/4OZ/AV' -> (24, 4.0, 'OZ', True)
        '8/9.4/LBAV' -> (8, 9.4, 'LB', True)

    Returns: (pack, size, unit, is_catch_weight)
    """
    if pd.isna(value) or str(value).strip() == '':
        return (None, None, None, False)

    value = str(value).strip().upper()
    is_catch_weight = 'AV' in value  # LBAV, OZ/AV indicate catch weight

    # Remove AV suffix for parsing
    value = value.replace('AV', '').replace('//', '/')

    # Split by /
    parts = value.split('/')

    if len(parts) >= 3:
        try:
            pack = int(parts[0])
        except ValueError:
            pack = 1

        size_part = parts[1]
        unit_part = parts[2] if len(parts) > 2 else ''

        size_match = re.match(r'([\d.]+)', size_part)
        if size_match:
            size = float(size_match.group(1))
            remaining = size_part[size_match.end():]
            if remaining:
                unit_part = remaining
        else:
            size = None

        unit = unit_part.strip()
        if unit == '' or unit == 'LB':
            unit = 'LB'

        return (pack, size, unit, is_catch_weight)

    elif len(parts) == 2:
        try:
            pack = int(parts[0])
            size_match = re.match(r'([\d.]+)', parts[1])
            if size_match:
                size = float(size_match.group(1))
                unit = parts[1][size_match.end():].strip() or 'EA'
            else:
                size = None
                unit = parts[1]
            return (pack, size, unit, is_catch_weight)
        except ValueError:
            return (1, None, value, is_catch_weight)

    return (1, None, value, is_catch_weight)


def clean_dataframe(df: pd.DataFrame, vendor_code: str) -> pd.DataFrame:
    """Apply vendor-specific cleaning to the dataframe."""
    config = VENDOR_CONFIGS.get(vendor_code, VENDOR_CONFIGS["vesta"])

    # For Shamrock, the first data row is actually column headers
    if config.get("skip_first_data_row"):
        # Set proper column names from first data row
        new_columns = df.iloc[0].tolist()
        for i, col in enumerate(new_columns):
            if pd.isna(col) or str(col).startswith('Unnamed'):
                new_columns[i] = f'Unnamed: {i}'
        df.columns = new_columns
        df = df.iloc[1:].reset_index(drop=True)

    # Remove empty rows
    df = df.dropna(how='all')

    # Drop rows without Description (for Shamrock)
    if 'Description' in df.columns:
        df = df.dropna(subset=['Description'])

    # Parse Vesta packaging column if needed
    if config.get("parse_packaging") and 'Packaging' in df.columns:
        # Drop rows without product description
        if 'Produce Description' in df.columns:
            df = df.dropna(subset=['Produce Description'])

        parsed = df['Packaging'].apply(parse_vesta_packaging)
        df['Pack'] = parsed.apply(lambda x: x[0])
        df['Size'] = parsed.apply(lambda x: x[1])
        df['Unit'] = parsed.apply(lambda x: x[2])
        df = df.drop(columns=['Packaging'])

        # Apply unit replacements for special cases (HG -> GAL with size adjustment)
        if 'Unit' in df.columns:
            # Handle HG (half-gallon) conversion
            hg_mask = df['Unit'] == 'HG'
            df.loc[hg_mask, 'Size'] = df.loc[hg_mask, 'Size'] * 0.5
            df.loc[hg_mask, 'Unit'] = 'GAL'

    # Parse Shamrock Pack Size column
    if config.get("parse_shamrock_packaging") and 'Pack Size' in df.columns:
        parsed = df['Pack Size'].apply(parse_shamrock_packaging)
        df['Pack'] = parsed.apply(lambda x: x[0])
        df['Size'] = parsed.apply(lambda x: x[1])
        df['Unit'] = parsed.apply(lambda x: x[2])
        df['is_catch_weight'] = parsed.apply(lambda x: x[3])
        df = df.drop(columns=['Pack Size'])

    # Rename columns if specified
    if config.get("column_renames"):
        df = df.rename(columns=config["column_renames"])

    # Drop specified columns
    columns_to_drop = [col for col in config["columns_to_drop"] if col in df.columns]
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)

    # Clean price column with $ signs
    if config.get("price_column_has_dollar") and 'Case $' in df.columns:
        df['Case $'] = df['Case $'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
        df['Case $'] = pd.to_numeric(df['Case $'], errors='coerce')

    # Clean Unit column
    if 'Unit' in df.columns:
        df['Unit'] = df['Unit'].astype(str)
        for old, new in config["unit_replacements"].items():
            df['Unit'] = df['Unit'].str.replace(old, new, regex=False)
        df['Unit'] = df['Unit'].str.upper()

    # Clean Size column - remove non-numeric characters (for non-Vesta/Shamrock vendors)
    if 'Size' in df.columns and not config.get("parse_packaging") and not config.get("parse_shamrock_packaging"):
        df['Size'] = df['Size'].astype(str).str.replace(r'[^0-9.\-]', '', regex=True)
        df['Size'] = pd.to_numeric(df['Size'], errors='coerce')

    # Calculate Unit $ if needed
    if config.get("calculate_unit_price"):
        required_cols = ['Case $', 'Pack', 'Size']
        if all(col in df.columns for col in required_cols):
            df['Case $'] = pd.to_numeric(df['Case $'], errors='coerce')
            df['Pack'] = pd.to_numeric(df['Pack'], errors='coerce')
            df['Size'] = pd.to_numeric(df['Size'], errors='coerce')
            df['Unit $'] = (df['Case $'] / (df['Pack'] * df['Size'])).round(2)

    return df


def get_distributor_id(cursor, distributor_code: str) -> int:
    """Get distributor ID from code."""
    cursor.execute("SELECT id FROM distributors WHERE code = %s", (distributor_code,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"Distributor '{distributor_code}' not found in database")
    # RealDictCursor returns dict, must use column name not index
    return result["id"]


def get_unit_id(cursor, unit_abbr: str) -> Optional[int]:
    """Get unit ID from abbreviation (case-insensitive)."""
    if not unit_abbr or unit_abbr == 'nan':
        return None

    cursor.execute("SELECT id FROM units WHERE LOWER(abbreviation) = LOWER(%s)", (unit_abbr,))
    result = cursor.fetchone()
    if result:
        return result["id"]  # Use column name instead of index

    cursor.execute("SELECT id FROM units WHERE LOWER(name) LIKE LOWER(%s)", (f"%{unit_abbr}%",))
    result = cursor.fetchone()
    return result["id"] if result else None  # Use column name instead of index


@router.get("/distributors")
def get_distributors():
    """Get list of available distributors for upload."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, code FROM distributors WHERE is_active = 1 ORDER BY name")
        rows = cursor.fetchall()
        return [{"id": row["id"], "name": row["name"], "code": row["code"]} for row in rows]


@router.post("/csv", response_model=UploadResult)
async def upload_csv(
    file: UploadFile = File(...),
    distributor_code: str = Form(...),
    effective_date: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and process a vendor CSV or Excel file.

    - Supports .csv, .xlsx, and .xls files
    - Applies vendor-specific cleaning rules
    - Imports products and prices into the database
    - Returns import statistics
    """
    # Validate file type
    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.csv') or filename_lower.endswith('.xlsx') or filename_lower.endswith('.xls')):
        raise HTTPException(status_code=400, detail="File must be CSV or Excel (.csv, .xlsx, .xls)")

    # Validate distributor code
    if distributor_code not in VENDOR_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown distributor code: {distributor_code}. Valid codes: {list(VENDOR_CONFIGS.keys())}"
        )

    # Parse effective date
    if effective_date:
        try:
            eff_date = datetime.strptime(effective_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        eff_date = date.today()

    # Read file content
    try:
        content = await file.read()
        config = VENDOR_CONFIGS[distributor_code]

        if filename_lower.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content), header=config["header_row"])
        elif filename_lower.endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(content), header=config["header_row"], engine='openpyxl')
        else:
            # .xls file (older Excel format)
            df = pd.read_excel(io.BytesIO(content), header=config["header_row"], engine='xlrd')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Apply cleaning
    df = clean_dataframe(df, distributor_code)

    # Import to database
    errors = []
    rows_imported = 0
    rows_failed = 0
    new_products = 0
    updated_prices = 0
    batch_id = str(uuid.uuid4())

    with get_db() as conn:
        cursor = conn.cursor()

        try:
            # Get distributor ID
            distributor_id = get_distributor_id(cursor, distributor_code)

            # Create import batch
            cursor.execute("""
                INSERT INTO import_batches (id, distributor_id, filename, import_date)
                VALUES (%s, %s, %s, %s)
            """, (batch_id, distributor_id, file.filename, datetime.now()))

            # Process each row
            for idx, row in df.iterrows():
                # Create savepoint for this row to isolate errors
                savepoint_name = f"row_{idx}"
                cursor.execute(f"SAVEPOINT {savepoint_name}")

                try:
                    # Extract data
                    product_name = str(row.get('Desc', '')).strip() if pd.notna(row.get('Desc')) else ''
                    if not product_name:
                        cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                        continue  # Skip rows without product name

                    sku = str(row.get('SUPC', '')) if pd.notna(row.get('SUPC')) else ''
                    brand = str(row.get('Brand', '')).strip() if pd.notna(row.get('Brand')) else None
                    pack = int(row.get('Pack', 0)) if pd.notna(row.get('Pack')) else None
                    size = float(row.get('Size', 0)) if pd.notna(row.get('Size')) else None
                    unit_abbr = str(row.get('Unit', '')) if pd.notna(row.get('Unit')) else None
                    case_price = float(row.get('Case $', 0)) if pd.notna(row.get('Case $')) else None
                    unit_price = float(row.get('Unit $', 0)) if pd.notna(row.get('Unit $')) else None
                    is_catch_weight = bool(row.get('is_catch_weight', False)) if 'is_catch_weight' in row else False

                    # For Shamrock catch weight items, the Price column is per-lb price
                    # So: Unit $ = Price, Case $ = Pack * Size (in lbs) * Price
                    if is_catch_weight and case_price:
                        unit_price = case_price  # Price column is per-lb
                        if pack and size:
                            # Convert size to lbs if unit is OZ
                            size_in_lbs = size / 16 if unit_abbr and unit_abbr.upper() == 'OZ' else size
                            case_price = round(pack * size_in_lbs * unit_price, 2)  # Calculate approx case cost
                    elif unit_price is None and case_price and pack and size:
                        # For non-catch-weight: calculate unit price from case price
                        unit_price = round(case_price / (pack * size), 2)

                    unit_id = get_unit_id(cursor, unit_abbr) if unit_abbr else None

                    # Check if product exists
                    cursor.execute("""
                        SELECT p.id as product_id, dp.id as distributor_product_id
                        FROM products p
                        LEFT JOIN distributor_products dp ON dp.product_id = p.id
                            AND dp.distributor_id = %s
                        WHERE p.name = %s AND (p.brand = %s OR (p.brand IS NULL AND %s IS NULL))
                              AND p.pack = %s AND p.size = %s
                    """, (distributor_id, product_name, brand, brand, pack, size))

                    existing = cursor.fetchone()

                    if existing and existing["product_id"]:
                        product_id = existing["product_id"]
                        distributor_product_id = existing["distributor_product_id"]

                        if not distributor_product_id:
                            cursor.execute("""
                                INSERT INTO distributor_products (distributor_id, product_id, distributor_sku, distributor_name)
                                VALUES (%s, %s, %s, %s)
                            """, (distributor_id, product_id, sku, product_name))
                            distributor_product_id = cursor.lastrowid
                    else:
                        # Create new product
                        cursor.execute("""
                            INSERT INTO products (name, brand, pack, size, unit_id, is_catch_weight)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (product_name, brand, pack, size, unit_id, int(is_catch_weight)))
                        product_id = cursor.lastrowid
                        new_products += 1

                        cursor.execute("""
                            INSERT INTO distributor_products (distributor_id, product_id, distributor_sku, distributor_name)
                            VALUES (%s, %s, %s, %s)
                        """, (distributor_id, product_id, sku, product_name))
                        distributor_product_id = cursor.lastrowid

                    # Insert/update price
                    if case_price is not None:
                        cursor.execute("""
                            SELECT id FROM price_history
                            WHERE distributor_product_id = %s AND effective_date = %s
                        """, (distributor_product_id, eff_date))

                        if cursor.fetchone():
                            cursor.execute("""
                                UPDATE price_history
                                SET case_price = %s, unit_price = %s, import_batch_id = %s
                                WHERE distributor_product_id = %s AND effective_date = %s
                            """, (case_price, unit_price, batch_id, distributor_product_id, eff_date))
                            updated_prices += 1
                        else:
                            cursor.execute("""
                                INSERT INTO price_history (distributor_product_id, case_price, unit_price, effective_date, import_batch_id)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (distributor_product_id, case_price, unit_price, eff_date, batch_id))

                    rows_imported += 1
                    # Release savepoint on success
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")

                except Exception as e:
                    # Rollback to savepoint to clear the error and continue processing
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                    rows_failed += 1
                    if len(errors) < 10:  # Limit error messages
                        errors.append(f"Row {idx + 1}: {str(e)}")

            # Update batch statistics
            cursor.execute("""
                UPDATE import_batches
                SET rows_imported = %s, rows_failed = %s
                WHERE id = %s
            """, (rows_imported, rows_failed, batch_id))

            conn.commit()

            return UploadResult(
                success=True,
                message=f"Successfully imported {rows_imported} products from {file.filename}",
                batch_id=batch_id,
                rows_imported=rows_imported,
                rows_failed=rows_failed,
                new_products=new_products,
                updated_prices=updated_prices,
                errors=errors
            )

        except Exception as e:
            conn.rollback()
            # Log the full error for debugging
            import traceback
            print(f"[ERROR] Upload failed: {str(e)}")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/history")
def get_upload_history(limit: int = 20):
    """Get recent upload history."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ib.id, d.name as distributor_name, ib.filename,
                   ib.import_date, ib.rows_imported, ib.rows_failed
            FROM import_batches ib
            JOIN distributors d ON d.id = ib.distributor_id
            ORDER BY ib.import_date DESC
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()
        return [{
            "id": row["id"],
            "distributor_name": row["distributor_name"],
            "filename": row["filename"],
            "import_date": row["import_date"],
            "rows_imported": row["rows_imported"],
            "rows_failed": row["rows_failed"]
        } for row in rows]
