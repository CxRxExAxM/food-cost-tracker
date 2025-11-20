import pandas as pd
import sys


# ========================================
# CONFIGURATION
# ========================================

# List columns to omit/drop from the dataset
COLUMNS_TO_OMIT = [
    'F',
    'Case Qty',
    'Split Qty',
    'Code',
    'Item Status',
    'Replaced Item',
    'Mfr #',
    'Split $',
    'Per Lb',
    'Market',
    'Splittable',
    'Splits',
    'Min Split',
    'Net Wt',
    'Lead Time',
    'Stock',
    'Substitute',
    'Agr',
    'Unnamed: 26',
    'Unnamed: 27'
]


def load_csv(file_path):
    """
    Load a CSV file into a pandas DataFrame.
    Sets row 1 (index 1) as the header, skipping the first row.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        pd.DataFrame: Loaded data
    """
    try:
        df = pd.read_csv(file_path, header=1)
        print(f"Successfully loaded {file_path}")
        print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)


def clean_unit_column(df):
    """
    Clean and normalize the 'Unit' column.
    - Convert '#' to 'LB'
    - Normalize all units to uppercase

    Args:
        df (pd.DataFrame): DataFrame with 'Unit' column

    Returns:
        pd.DataFrame: DataFrame with cleaned 'Unit' column
    """
    if 'Unit' not in df.columns:
        print("Warning: 'Unit' column not found in dataset")
        return df

    # Replace '#' with 'LB'
    df['Unit'] = df['Unit'].astype(str).str.replace('#', 'LB', regex=False)

    # Normalize to uppercase
    df['Unit'] = df['Unit'].str.upper()

    print(f"Cleaned 'Unit' column - normalized to uppercase")
    print(f"  Unique units: {df['Unit'].nunique()}")
    print(f"  Units: {df['Unit'].unique().tolist()}")

    return df


def clean_size_column(df):
    """
    Clean the 'Size' column by removing non-numeric characters and converting to float.

    Args:
        df (pd.DataFrame): DataFrame with 'Size' column

    Returns:
        pd.DataFrame: DataFrame with cleaned 'Size' column
    """
    if 'Size' not in df.columns:
        print("Warning: 'Size' column not found in dataset")
        return df

    # Remove all non-numeric characters except decimal point and negative sign
    df['Size'] = df['Size'].astype(str).str.replace(r'[^0-9.\-]', '', regex=True)

    # Convert to float, setting invalid values to NaN
    df['Size'] = pd.to_numeric(df['Size'], errors='coerce')

    print(f"Cleaned 'Size' column - converted to float")
    print(f"  Valid values: {df['Size'].notna().sum()}")
    print(f"  Invalid/NaN values: {df['Size'].isna().sum()}")

    return df


def calculate_unit_cost(df):
    """
    Calculate unit cost using the formula: Unit $ = Case $ / (Pack * Size)

    Args:
        df (pd.DataFrame): DataFrame with 'Case $', 'Pack', 'Size', and 'Unit' columns

    Returns:
        pd.DataFrame: DataFrame with new 'Unit $' column
    """
    required_cols = ['Case $', 'Pack', 'Size']
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print(f"Warning: Cannot calculate Unit $ - missing columns: {', '.join(missing_cols)}")
        return df

    # Ensure numeric types
    df['Case $'] = pd.to_numeric(df['Case $'], errors='coerce')
    df['Pack'] = pd.to_numeric(df['Pack'], errors='coerce')
    df['Size'] = pd.to_numeric(df['Size'], errors='coerce')

    # Calculate Unit $ = Case $ / (Pack * Size)
    df['Unit $'] = df['Case $'] / (df['Pack'] * df['Size'])

    # Round to 2 decimal places
    df['Unit $'] = df['Unit $'].round(2)

    # Count valid calculations
    valid_count = df['Unit $'].notna().sum()
    invalid_count = df['Unit $'].isna().sum()

    print(f"\nCalculated 'Unit $' column")
    print(f"  Valid calculations: {valid_count}")
    print(f"  Invalid/NaN values: {invalid_count}")

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
    print(df.head(rows))

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
        print("Usage: python clean_data.py <input_csv_file> [output_csv_file]")
        print("\nExample: python clean_data.py data.csv cleaned_data.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_sysco.csv"

    # Load the CSV
    df = load_csv(input_file)

    # Preview the data
    preview_dataframe(df)

    # ========================================
    # DATA CLEANING SECTION
    # Add your cleaning operations here
    # ========================================

    # Drop specified columns
    if COLUMNS_TO_OMIT:
        columns_found = [col for col in COLUMNS_TO_OMIT if col in df.columns]
        columns_not_found = [col for col in COLUMNS_TO_OMIT if col not in df.columns]

        if columns_found:
            df = df.drop(columns=columns_found)
            print(f"\nDropped {len(columns_found)} column(s): {', '.join(columns_found)}")

        if columns_not_found:
            print(f"\nWarning: {len(columns_not_found)} column(s) not found: {', '.join(columns_not_found)}")

    # Clean Unit column (normalize to uppercase, convert # to LB)
    df = clean_unit_column(df)

    # Clean Size column
    df = clean_size_column(df)

    # Calculate Unit $ column
    df = calculate_unit_cost(df)

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
