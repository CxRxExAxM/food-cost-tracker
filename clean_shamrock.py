import pandas as pd
import sys
import re


# ========================================
# CONFIGURATION
# ========================================

# Header row (0-indexed) - Shamrock has 3 header rows before data header
HEADER_ROW = 3

# Columns to drop (by original name)
COLUMNS_TO_DROP = [
    'Unnamed: 0',  # Empty column
    'Unnamed: 1',  # Row number
    '#',           # Row number
    'Unnamed: 4',  # Empty
    'Unnamed: 5',  # Empty
    'LWP',         # Last Week Purchase - not needed
    'Avg',         # Average order quantity - not needed
]

# Column renames to standard format
COLUMN_RENAMES = {
    'Product #': 'SUPC',
    'Description': 'Desc',
    'Pack Size': 'Packaging',
    'Price': 'Case $',
}


def load_file(file_path, header_row=HEADER_ROW):
    """
    Load a CSV or Excel file into a pandas DataFrame.
    Automatically detects file type based on extension.
    """
    try:
        file_lower = file_path.lower()
        if file_lower.endswith('.csv'):
            df = pd.read_csv(file_path, header=header_row)
        elif file_lower.endswith('.xlsx'):
            df = pd.read_excel(file_path, header=header_row, engine='openpyxl')
        elif file_lower.endswith('.xls'):
            df = pd.read_excel(file_path, header=header_row, engine='xlrd')
        else:
            print(f"Error: Unsupported file format. Use .csv, .xlsx, or .xls")
            sys.exit(1)

        print(f"Successfully loaded {file_path}")
        print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)


def parse_pack_size(value):
    """
    Parse Shamrock Pack Size into Pack, Size, and Unit.

    Examples:
        '1/120/PK' -> (1, 120.0, 'PK')
        '1/10/LBAV' -> (1, 10.0, 'LB', is_catch_weight=True)
        '24/4OZ/AV' -> (24, 4.0, 'OZ', is_catch_weight=True)
        '8/9.4/LBAV' -> (8, 9.4, 'LB', is_catch_weight=True)
        '2/8/LBAV' -> (2, 8.0, 'LB', is_catch_weight=True)

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
        # Format: pack/size/unit (e.g., 1/120/PK, 24/4OZ)
        try:
            pack = int(parts[0])
        except ValueError:
            pack = 1

        # Size might have unit attached (e.g., 4OZ)
        size_part = parts[1]
        unit_part = parts[2] if len(parts) > 2 else ''

        # Extract numeric size
        size_match = re.match(r'([\d.]+)', size_part)
        if size_match:
            size = float(size_match.group(1))
            # Check if unit is in size part
            remaining = size_part[size_match.end():]
            if remaining:
                unit_part = remaining
        else:
            size = None

        # Clean unit
        unit = unit_part.strip()
        if unit == 'LB' or unit == '':
            unit = 'LB'

        return (pack, size, unit, is_catch_weight)

    elif len(parts) == 2:
        # Format: pack/size or size/unit
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


def clean_price(value):
    """Remove $ and convert to float."""
    if pd.isna(value):
        return None
    value = str(value).replace('$', '').replace(',', '').strip()
    try:
        return float(value)
    except ValueError:
        return None


def preview_dataframe(df, rows=10):
    """Display a preview of the DataFrame."""
    print("\n" + "="*80)
    print("DATA PREVIEW")
    print("="*80)
    print(f"\nFirst {rows} rows:")
    print(df.head(rows).to_string())

    print("\n" + "-"*80)
    print("COLUMN INFO")
    print("-"*80)
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nDtypes:\n{df.dtypes}")


def export_csv(df, output_path):
    """Export DataFrame to CSV file."""
    try:
        df.to_csv(output_path, index=False)
        print(f"\nSuccessfully exported to {output_path}")
    except Exception as e:
        print(f"Error exporting file: {e}")


def main():
    """Main function to orchestrate data cleaning workflow."""

    if len(sys.argv) < 2:
        print("Usage: python clean_shamrock.py <input_file> [output_csv_file]")
        print("\nSupported formats: .csv, .xlsx, .xls")
        print("Example: python clean_shamrock.py shamrock.xls cleaned_shamrock.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_shamrock.csv"

    # Load the file
    df = load_file(input_file, header_row=HEADER_ROW)

    # The first row after header is actually the column names row
    # Set proper column names from first data row
    new_columns = df.iloc[0].tolist()
    # Fill in unnamed columns
    for i, col in enumerate(new_columns):
        if pd.isna(col) or str(col).startswith('Unnamed'):
            new_columns[i] = f'Unnamed: {i}'
    df.columns = new_columns

    # Drop the header row that's now in data
    df = df.iloc[1:].reset_index(drop=True)

    # Preview raw data
    print("\n--- RAW DATA ---")
    preview_dataframe(df)

    # ========================================
    # DATA CLEANING
    # ========================================

    # Drop empty rows
    df = df.dropna(how='all')

    # Drop rows without Description
    if 'Description' in df.columns:
        df = df.dropna(subset=['Description'])

    # Drop unwanted columns
    columns_to_drop = [col for col in COLUMNS_TO_DROP if col in df.columns]
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop)
        print(f"\nDropped columns: {columns_to_drop}")

    # Rename columns to standard format
    df = df.rename(columns=COLUMN_RENAMES)

    # Parse Pack Size into Pack, Size, Unit, is_catch_weight
    if 'Packaging' in df.columns:
        parsed = df['Packaging'].apply(parse_pack_size)
        df['Pack'] = parsed.apply(lambda x: x[0])
        df['Size'] = parsed.apply(lambda x: x[1])
        df['Unit'] = parsed.apply(lambda x: x[2])
        df['is_catch_weight'] = parsed.apply(lambda x: x[3])
        df = df.drop(columns=['Packaging'])

    # Clean Price column
    if 'Case $' in df.columns:
        df['Case $'] = df['Case $'].apply(clean_price)

    # For Shamrock catch weight items, the Price column is actually per-lb price
    # So we need to: Unit $ = Price, Case $ = Pack * Size * Price
    if all(col in df.columns for col in ['Case $', 'Pack', 'Size']):
        def calc_prices(row):
            price_value = row['Case $']
            if pd.isna(price_value):
                return (None, None)

            if row.get('is_catch_weight', False):
                # For catch weight: Price column is per-lb price
                unit_price = price_value
                # Calculate approximate case cost (convert OZ to LB if needed)
                if row['Pack'] and row['Size']:
                    size_in_lbs = row['Size'] / 16 if row.get('Unit') == 'OZ' else row['Size']
                    case_price = round(row['Pack'] * size_in_lbs * price_value, 2)
                else:
                    case_price = None
                return (case_price, unit_price)
            else:
                # For non-catch-weight: Price column is case price
                case_price = price_value
                if row['Pack'] and row['Size']:
                    unit_price = round(case_price / (row['Pack'] * row['Size']), 2)
                else:
                    unit_price = None
                return (case_price, unit_price)

        prices = df.apply(calc_prices, axis=1)
        df['Case $'] = prices.apply(lambda x: x[0])
        df['Unit $'] = prices.apply(lambda x: x[1])

    # Normalize units
    if 'Unit' in df.columns:
        unit_map = {
            'CS': 'CASE',
            'LB': 'LB',
            'LBA': 'LB',  # LBA is LB Average
            'OZ': 'OZ',
            'PK': 'PACK',
            'EA': 'EA',
        }
        df['Unit'] = df['Unit'].map(lambda x: unit_map.get(str(x).upper(), str(x).upper()) if pd.notna(x) else None)

    # Reorder columns to standard format
    standard_cols = ['SUPC', 'Desc', 'Brand', 'Pack', 'Size', 'Unit', 'Case $', 'Unit $', 'is_catch_weight']
    existing_cols = [col for col in standard_cols if col in df.columns]
    other_cols = [col for col in df.columns if col not in standard_cols]
    df = df[existing_cols + other_cols]

    print("\n" + "="*80)
    print("CLEANED DATA")
    print("="*80)
    print(f"Final shape: {df.shape[0]} rows, {df.shape[1]} columns")

    preview_dataframe(df, rows=15)

    # Show catch weight items
    if 'is_catch_weight' in df.columns:
        cw_count = df['is_catch_weight'].sum()
        print(f"\nCatch weight items: {cw_count}")

    # Show unique units
    if 'Unit' in df.columns:
        print(f"\nUnique units: {df['Unit'].unique().tolist()}")

    # Export
    export_csv(df, output_file)


if __name__ == "__main__":
    main()
