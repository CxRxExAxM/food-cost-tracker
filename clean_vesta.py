import pandas as pd
import sys

# Show all rows/columns in print output (for debugging)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)


# ========================================
# CONFIGURATION
# ========================================

# List columns to omit/drop from the dataset
COLUMNS_TO_OMIT = [
    # Add column names here, e.g.:
    # 'Unwanted Column 1',
    # 'Unwanted Column 2',
]

# Unit normalization mapping
# Maps Vesta units to database-compatible abbreviations (uppercase)
UNIT_MAP = {
    'BK': 'PACK',      # Basket -> Pack
    'KG': 'KG',        # Kilogram
    'GL': 'GAL',       # Gallon
    'LT': 'L',         # Liter
    'BU': 'BUNCH',     # Bunch
    'CASE': 'CASE',    # Case
    'EA': 'EA',        # Each
    'PACK': 'PACK',    # Pack
}


def load_file(file_path, header_row=10):
    """
    Load a CSV or Excel file into a pandas DataFrame.
    Automatically detects file type based on extension.

    Args:
        file_path (str): Path to the CSV or Excel file
        header_row (int): Row to use as header (default 0)

    Returns:
        pd.DataFrame: Loaded data
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


# Backwards compatibility alias
def load_csv(file_path):
    """Deprecated: Use load_file() instead."""
    return load_file(file_path, header_row=10)


def parse_packaging_value(value):
    """
    Parse a single packaging value into pack, size, and unit.

    Logic:
    - Split by last space to get amount_part and unit
    - If no space, entire value is unit (pack=1, size=None)
    - For amount_part containing '/':
      - If first number > 50: treat as range, use midpoint for size, pack=1
      - If first number <= 50: treat as pack/size

    Examples:
        '4/5 LB' -> (4, 5.0, 'LB')
        '120/138 CT' -> (1, 129.0, 'CT')  # midpoint
        '8/24 CT' -> (8, 24.0, 'CT')
        'LB' -> (1, None, 'LB')

    Args:
        value: The packaging string to parse

    Returns:
        tuple: (pack, size, unit)
    """
    if pd.isna(value) or str(value).strip() == '':
        return (None, None, None)

    value = str(value).strip()

    # Split by last space
    if ' ' in value:
        # rsplit with maxsplit=1 splits from the right
        amount_part, unit = value.rsplit(' ', 1)
        unit = unit.upper()
    else:
        # No space - entire value is unit
        return (1, None, value.upper())

    # Parse amount_part
    if '/' in amount_part:
        parts = amount_part.split('/')
        try:
            first_num = float(parts[0])
            second_num = float(parts[1])

            # Determine if this is a range or pack/size
            # If unit is CT and first number > 20, treat as range (e.g., 56/72 CT, 120/138 CT)
            # Otherwise treat as pack/size (e.g., 4/5 LB, 8/24 CT)
            is_range = (unit == 'CT' and first_num > 20)

            if is_range:
                # Treat as range, use midpoint
                pack = 1
                size = (first_num + second_num) / 2
            else:
                # Treat as pack/size
                pack = int(first_num)
                size = second_num
        except ValueError:
            # Can't parse numbers, return as-is
            return (1, None, unit)
    else:
        # No slash, try to parse as single number (size)
        try:
            pack = 1
            size = float(amount_part)
        except ValueError:
            return (1, None, unit)

    return (pack, size, unit)


def normalize_unit(unit, size):
    """
    Normalize unit to database-compatible abbreviation.
    Also handles unit conversions that affect size (e.g., HG -> gal with size * 0.5).

    Args:
        unit (str): The unit abbreviation
        size (float): The size value

    Returns:
        tuple: (normalized_unit, adjusted_size)
    """
    if unit is None:
        return (None, size)

    # Special case: HG (Half-Gallon) -> convert to GAL with size adjustment
    if unit == 'HG':
        new_size = size * 0.5 if size is not None else 0.5
        return ('GAL', new_size)

    # Check mapping table
    if unit in UNIT_MAP:
        return (UNIT_MAP[unit], size)

    # Return as-is (will be matched case-insensitively by the import)
    return (unit, size)


def clean_packaging_column(df, packaging_col='Pack'):
    """
    Clean and split the packaging column into Pack, Size, and Unit columns.

    Args:
        df (pd.DataFrame): DataFrame with packaging column
        packaging_col (str): Name of the packaging column

    Returns:
        pd.DataFrame: DataFrame with new Pack, Size, Unit columns
    """
    if packaging_col not in df.columns:
        print(f"Warning: '{packaging_col}' column not found in dataset")
        return df

    # Parse each packaging value
    parsed = df[packaging_col].apply(parse_packaging_value)

    # Apply unit normalization (may adjust size for conversions like HG -> gal)
    def apply_normalization(row):
        pack, size, unit = row
        normalized_unit, adjusted_size = normalize_unit(unit, size)
        return (pack, adjusted_size, normalized_unit)

    parsed = parsed.apply(apply_normalization)

    # Create new columns
    df['Pack'] = parsed.apply(lambda x: x[0])
    df['Size'] = parsed.apply(lambda x: x[1])
    df['Unit'] = parsed.apply(lambda x: x[2])

    # Drop the original packaging column if it's different from 'Pack'
    if packaging_col != 'Pack':
        df = df.drop(columns=[packaging_col])

    # Report results
    print(f"\nParsed '{packaging_col}' column into Pack, Size, Unit")
    print(f"  Valid Pack values: {df['Pack'].notna().sum()}")
    print(f"  Valid Size values: {df['Size'].notna().sum()}")
    print(f"  Unique Units: {df['Unit'].dropna().unique().tolist()}")

    return df


def preview_dataframe(df, rows=10):
    """
    Display a preview of the DataFrame.

    Args:
        df (pd.DataFrame): DataFrame to preview
        rows (int): Number of rows to display
    """
    print("\n" + "="*80)
    print("DATA PREVIEW")
    print("="*80)
    print(f"\nFirst {rows} rows:")
    #print(df.head(rows))
    print(df)

    print("\n" + "-"*80)
    print("COLUMN INFO")
    print("-"*80)
    print(df.info())

    print("\n" + "-"*80)
    print("BASIC STATISTICS")
    print("-"*80)
    print(df.describe())


def export_csv(df, output_path):
    """
    Export DataFrame to CSV file.

    Args:
        df (pd.DataFrame): DataFrame to export
        output_path (str): Path for the output file
    """
    try:
        df.to_csv(output_path, index=False)
        print(f"\nSuccessfully exported to {output_path}")
    except Exception as e:
        print(f"Error exporting file: {e}")


def main():
    """Main function to orchestrate data cleaning workflow."""

    # Check if file path is provided
    if len(sys.argv) < 2:
        print("Usage: python clean_vesta.py <input_file> [output_csv_file]")
        print("\nSupported formats: .csv, .xlsx, .xls")
        print("Example: python clean_vesta.py vesta_data.xlsx cleaned_vesta.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_vesta.csv"

    # Load the file (CSV or Excel)
    df = load_file(input_file, header_row=10)

    # Preview the data
    preview_dataframe(df)

    # ========================================
    # DATA CLEANING SECTION
    # ========================================

    # Remove empty/NaN rows
    initial_rows = len(df)
    df = df.dropna(how='all')  # Drop rows where all values are NaN
    df = df.dropna(subset=['Produce Description'])  # Drop rows with no product name
    dropped_rows = initial_rows - len(df)
    if dropped_rows > 0:
        print(f"\nDropped {dropped_rows} empty/invalid rows")

    # Clean packaging column - splits into Pack, Size, Unit
    df = clean_packaging_column(df, packaging_col='Packaging')

    # Rename columns to match database import format (Sysco standard)
    column_renames = {
        'Produce Description': 'Desc',
        'Prod Number': 'SUPC',
        'Price': 'Case $',
    }
    df = df.rename(columns=column_renames)
    print(f"\nRenamed columns: {column_renames}")

    # Convert SUPC to int
    if 'SUPC' in df.columns:
        df['SUPC'] = pd.to_numeric(df['SUPC'], errors='coerce').astype('Int64')

    # Drop specified columns
    if COLUMNS_TO_OMIT:
        columns_found = [col for col in COLUMNS_TO_OMIT if col in df.columns]
        columns_not_found = [col for col in COLUMNS_TO_OMIT if col not in df.columns]

        if columns_found:
            df = df.drop(columns=columns_found)
            print(f"\nDropped {len(columns_found)} column(s): {', '.join(columns_found)}")

        if columns_not_found:
            print(f"\nWarning: {len(columns_not_found)} column(s) not found: {', '.join(columns_not_found)}")

    # Example cleaning operations (uncomment to use):
    # df = df.dropna()  # Remove rows with missing values
    # df = df.drop_duplicates()  # Remove duplicate rows
    # df.columns = df.columns.str.strip()  # Remove whitespace from column names

    print("\n" + "="*80)
    print("CLEANED DATA")
    print("="*80)
    print(f"Final shape: {df.shape[0]} rows, {df.shape[1]} columns")

    # Show preview of cleaned data
    preview_dataframe(df)

    # Export cleaned data
    export_csv(df, output_file)


if __name__ == "__main__":
    main()
