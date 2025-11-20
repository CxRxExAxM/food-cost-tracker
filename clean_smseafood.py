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


def load_csv(file_path):
    """
    Load a CSV file into a pandas DataFrame.

    Args:
        file_path (str): Path to the CSV file

    Returns:
        pd.DataFrame: Loaded data
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Successfully loaded {file_path}")
        print(f"Shape: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)


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
        print("Usage: python clean_smseafood.py <input_csv_file> [output_csv_file]")
        print("\nExample: python clean_smseafood.py smseafood_data.csv cleaned_smseafood.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "cleaned_smseafood.csv"

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
