import pandas as pd
import sys


# ========================================
# CONFIGURATION
# ========================================

# List columns to omit/drop from the dataset
COLUMNS_TO_OMIT = [
    # Add column names here, e.g.:
    # 'Unwanted Column 1',
    # 'Unwanted Column 2',
]


def load_file(file_path, header_row=0):
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
    return load_file(file_path, header_row=0)


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
        print("Usage: python clean_sterling.py <input_file> [output_csv_file]")
        print("\nSupported formats: .csv, .xlsx, .xls")
        print("Example: python clean_sterling.py sterling_data.xlsx cleaned_sterling.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_sterling.csv"

    # Load the file (CSV or Excel)
    df = load_file(input_file, header_row=0)

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

    # Uncomment to export:
    # export_csv(df, output_file)


if __name__ == "__main__":
    main()
