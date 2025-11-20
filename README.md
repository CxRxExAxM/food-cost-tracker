# Food Cost Tracker

A system for managing food costs, tracking prices from multiple distributors, and calculating recipe costs.

## Quick Start

### 1. Set Up the Database

```bash
# Activate virtual environment
source venv/bin/activate

# Create the SQLite database
python db/setup_db.py
```

This will create `db/food_cost_tracker.db` with all necessary tables and seed data.

### 2. Clean and Import Distributor Data

```bash
# Activate virtual environment
source venv/bin/activate

# Clean distributor CSV (creates cleaned_sysco.csv)
python clean_sysco.py sysco.csv

# Import cleaned data into database
python import_csv.py cleaned_sysco.csv sysco

# For other distributors:
# python clean_vesta.py vesta_data.csv && python import_csv.py cleaned_vesta.csv vesta
# python clean_smseafood.py smseafood_data.csv && python import_csv.py cleaned_smseafood.csv smseafood
# python clean_shamrock.py shamrock_data.csv && python import_csv.py cleaned_shamrock.csv shamrock
# python clean_noblebread.py noblebread_data.csv && python import_csv.py cleaned_noblebread.csv noblebread
# python clean_sterling.py sterling_data.csv && python import_csv.py cleaned_sterling.csv sterling
```

## Database Schema

### Core Tables

- **distributors**: Food distributors (Sysco, Vesta, etc.)
- **units**: Units of measure (lb, oz, gal, etc.)
- **common_products**: User-defined normalized ingredients ("Red Onion", "Chicken Breast")
- **products**: Distributor-specific products (linked to common_products)
- **distributor_products**: Junction table linking products to distributors with SKUs
- **price_history**: Time-series price tracking
- **import_batches**: Track CSV import operations
- **recipes**: Recipe definitions
- **recipe_ingredients**: Recipe components (references common_products)

## Tech Stack

- **Database**: SQLite 3
- **Data Processing**: Python 3 + Pandas
- **Backend** (planned): FastAPI
- **Frontend** (planned): React

## Development

View database:
```bash
sqlite3 db/food_cost_tracker.db
```

Reset database (deletes all data):
```bash
python db/setup_db.py
```

Backup database:
```bash
cp db/food_cost_tracker.db db/food_cost_tracker_backup_$(date +%Y%m%d).db
```
