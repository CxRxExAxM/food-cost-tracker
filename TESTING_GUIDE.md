# Phase 1 Testing Guide

## Option 1: Test Against Your Dev Database on Render (Recommended)

### Step 1: Get your Render PostgreSQL connection string

1. Go to your Render dashboard: https://dashboard.render.com
2. Find your PostgreSQL database
3. Click on it and copy the "External Database URL" (starts with `postgresql://`)

### Step 2: Set the DATABASE_URL environment variable

```bash
# Export your database connection string
export DATABASE_URL='postgresql://user:password@host:5432/database_name'
```

### Step 3: Install Python dependencies (if not already installed)

```bash
cd /Users/mike/Documents/DevProjects/Clean_Invoices
pip install psycopg2-binary python-dotenv
```

### Step 4: Run the database tests

```bash
python test_outlets_phase1.py
```

This will:
- ✓ Verify migration ran successfully
- ✓ Check outlets table structure
- ✓ Verify default outlets were created
- ✓ Show user-outlet assignments
- ✓ Display products/recipes per outlet
- ✓ Identify org-wide admins

---

## Option 2: Test with Local PostgreSQL Database

If you want to test locally:

### Step 1: Install PostgreSQL

```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql
```

### Step 2: Create test database

```bash
createdb food_cost_tracker_test
```

### Step 3: Set DATABASE_URL

```bash
export DATABASE_URL='postgresql://localhost/food_cost_tracker_test'
```

### Step 4: Run migrations

```bash
cd /Users/mike/Documents/DevProjects/Clean_Invoices
alembic upgrade head
```

### Step 5: Run the tests

```bash
python test_outlets_phase1.py
```

---

## What the Tests Verify

### ✅ Database Structure
- `outlets` table exists with all required columns
- `user_outlets` junction table for many-to-many relationships
- `outlet_id` column added to products, recipes, distributor_products, import_batches

### ✅ Data Migration
- Default outlets created for existing organizations
- All existing products/recipes assigned to default outlet
- Foreign key constraints in place

### ✅ Data Distribution
- Shows how many products per outlet
- Shows how many recipes per outlet
- Lists all user-outlet assignments
- Identifies org-wide admins (users with no outlet restrictions)

---

## Next: API Testing

After database tests pass, we'll test the actual API endpoints:

1. **Outlet CRUD** - Create, read, update outlets
2. **User Assignment** - Assign users to outlets
3. **Product Filtering** - Verify users only see their outlet's products
4. **Recipe Filtering** - Verify users only see their outlet's recipes
5. **Recipe Costing** - CRITICAL: Verify outlet-specific pricing works
6. **CSV Upload** - Test outlet assignment during import
7. **Access Control** - Test cross-outlet access denial

---

## Troubleshooting

### "DATABASE_URL environment variable not set"
Make sure you've exported DATABASE_URL in your current terminal session.

### "connection refused"
Your PostgreSQL server might not be running. Check with:
```bash
brew services list  # macOS
```

### "database does not exist"
Create the database first:
```bash
createdb your_database_name
```

### "migration failed"
Check alembic version table:
```bash
psql $DATABASE_URL -c "SELECT * FROM alembic_version;"
```

If stuck, reset and re-run:
```bash
alembic downgrade base
alembic upgrade head
```
