# Multi-Outlet Pricing Implementation - December 13, 2025

**Status:** ✅ **COMPLETE** - Full per-outlet pricing and organization overview

## Executive Summary

Successfully implemented per-outlet pricing to enable complete data isolation between outlets within the same organization. Previously, outlets shared product pricing organization-wide, causing conflicts when multiple outlets uploaded pricing for the same products. Now each outlet maintains independent pricing history.

**Key Achievement**: Outlets can now have different prices for the same product on the same date, enabling true multi-outlet operations where pricing varies by location.

---

## Problem Statement

### Original Issue
When multiple outlets uploaded CSV files with the same products:
- Last uploader "won" - their prices overwrote previous prices
- Products would disappear from other outlets' views
- Unique constraint violation: `(distributor_product_id, effective_date)` prevented concurrent uploads

### Example Scenario
1. Default Outlet uploads "Tomatoes" on Dec 13 → Price: $45.00
2. IAK Outlet uploads "Tomatoes" on Dec 13 → Price: $50.00
3. **Bug**: Default Outlet now sees $50.00 (IAK's price) or product disappears entirely

### Root Cause
Products are organization-scoped (shared across outlets) but pricing was also organization-scoped. This violated the principle that each outlet should manage its own pricing independently.

---

## Solution Architecture

### Design Philosophy

**Products**: Organization-level entities (shared)
- Common product catalog across all outlets
- Mapping to common_products is shared
- `product.outlet_id` is historical metadata (who created it first)

**Pricing**: Outlet-level entities (isolated)
- Each outlet maintains independent `price_history`
- Same product can have different prices per outlet
- Filtering based on which outlet has imported the product

### Benefits
1. **Data Isolation**: Outlets manage their own pricing
2. **Proactive Updates**: Active outlets can update frequently without affecting others
3. **Shared Mapping**: Product-to-common_product mappings are reused
4. **Scalability**: Supports unlimited outlets with independent operations

---

## Database Schema Changes

### Migration 002: Add outlet_id to price_history

**File**: `db/migrations/002_add_outlet_id_to_price_history.sql`

#### Step 1: Add outlet_id Column
```sql
ALTER TABLE price_history ADD COLUMN outlet_id INTEGER;
```

#### Step 2: Populate from import_batches
```sql
UPDATE price_history ph
SET outlet_id = ib.outlet_id
FROM import_batches ib
WHERE ph.import_batch_id = ib.id
AND ph.outlet_id IS NULL;
```

#### Step 3: Set NOT NULL Constraint
```sql
ALTER TABLE price_history ALTER COLUMN outlet_id SET NOT NULL;
```

#### Step 4: Add Foreign Key
```sql
ALTER TABLE price_history
ADD CONSTRAINT fk_price_history_outlet
FOREIGN KEY (outlet_id) REFERENCES outlets(id) ON DELETE CASCADE;
```

#### Step 5: Drop Old Unique Constraint
```sql
ALTER TABLE price_history
DROP CONSTRAINT IF EXISTS price_history_distributor_product_id_effective_date_key;
```

#### Step 6: Add New Unique Constraint
```sql
ALTER TABLE price_history
ADD CONSTRAINT unique_price_per_outlet_product_date
UNIQUE (distributor_product_id, outlet_id, effective_date);
```

**Key Change**: Unique constraint now includes `outlet_id`, allowing different outlets to have different prices for the same product on the same date.

#### Step 7: Create Index
```sql
CREATE INDEX idx_price_history_outlet ON price_history(outlet_id);
```

---

## Code Changes

### Backend Changes

#### 1. Products Router (`api/app/routers/products.py`)

**Key Changes**:
- Product filtering based on `price_history.outlet_id` instead of `product.outlet_id`
- Price joins partitioned by outlet_id

**Before** (organization-level products):
```python
cursor.execute("""
    SELECT * FROM products
    WHERE organization_id = %s
""", (org_id,))
```

**After** (outlet-filtered products):
```python
# Filter by which outlet has imported the product
if outlet_id is not None:
    where_clause += """ AND EXISTS (
        SELECT 1 FROM price_history ph_filter
        JOIN distributor_products dp_filter ON dp_filter.id = ph_filter.distributor_product_id
        WHERE dp_filter.product_id = p.id AND ph_filter.outlet_id = %s
    )"""
    params.append(outlet_id)
```

**Price Join with Outlet Partitioning**:
```python
# Get latest price per outlet
LEFT JOIN (
    SELECT distributor_product_id, outlet_id, case_price, unit_price, effective_date,
           ROW_NUMBER() OVER (
               PARTITION BY distributor_product_id, outlet_id
               ORDER BY effective_date DESC
           ) as rn
    FROM price_history
) ph ON ph.distributor_product_id = dp.id
    AND ph.rn = 1
    AND ph.outlet_id = %s
```

#### 2. Uploads Router (`api/app/routers/uploads.py`)

**Key Changes**:
- Include `outlet_id` in price_history INSERT/UPDATE queries
- Price lookups filtered by outlet_id

**Before** (global price lookup):
```python
cursor.execute("""
    SELECT id FROM price_history
    WHERE distributor_product_id = %s AND effective_date = %s
""", (distributor_product_id, eff_date))
```

**After** (outlet-scoped price lookup):
```python
cursor.execute("""
    SELECT id FROM price_history
    WHERE distributor_product_id = %s
      AND outlet_id = %s
      AND effective_date = %s
""", (distributor_product_id, outlet_id, eff_date))
```

**Price History INSERT** (line 505):
```python
cursor.execute("""
    INSERT INTO price_history
    (distributor_product_id, outlet_id, case_price, unit_price, effective_date, import_batch_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
""", (
    distributor_product_id,
    outlet_id,  # NEW: Outlet-scoped pricing
    case_price,
    unit_price,
    eff_date,
    import_batch_id
))
```

**Price History UPDATE** (line 518):
```python
cursor.execute("""
    UPDATE price_history
    SET case_price = %s, unit_price = %s
    WHERE distributor_product_id = %s
      AND outlet_id = %s          -- NEW: Outlet-scoped
      AND effective_date = %s
""", (case_price, unit_price, distributor_product_id, outlet_id, eff_date))
```

#### 3. Outlets Router (`api/app/routers/outlets.py`)

**Added Organization Stats Endpoint** (line 223):
```python
@router.get("/organization/stats")
def get_organization_stats(current_user: dict = Depends(get_current_user)):
    """Get aggregate statistics for the entire organization."""
    org_id = current_user["organization_id"]

    return {
        "organization_id": org_id,
        "organization_name": org["name"],
        "products_count": product_count,    # All products in org
        "recipes_count": recipe_count,      # All recipes in org
        "users_count": user_count,          # All users in org
        "outlets_count": outlet_count,      # All outlets in org
        "imports_count": import_count       # All imports in org
    }
```

**Updated Outlet Stats** (line 292):
- Changed product counting from `WHERE outlet_id = %s` to EXISTS subquery
- Fixed field names to match frontend expectations

```python
# Count products this outlet has imported
cursor.execute("""
    SELECT COUNT(DISTINCT p.id) as count
    FROM products p
    WHERE p.is_active = 1
    AND EXISTS (
        SELECT 1 FROM price_history ph
        JOIN distributor_products dp ON dp.id = ph.distributor_product_id
        WHERE dp.product_id = p.id AND ph.outlet_id = %s
    )
""", (outlet_id,))
```

### Frontend Changes

#### 1. Organization Card Component

**New Files**:
- `frontend/src/components/outlets/OrgCard.jsx`
- `frontend/src/components/outlets/OrgCard.css`

**Features**:
- Displays organization-wide statistics
- Distinctive gradient background to differentiate from outlet cards
- 5-column grid: Outlets, Products, Recipes, Users, Imports
- Responsive design (adapts to mobile)

**Styling Highlights**:
```css
.org-card {
  background: linear-gradient(135deg,
    rgba(16, 185, 129, 0.05) 0%,
    rgba(59, 130, 246, 0.05) 100%);
  border: 1px solid var(--border-strong, #4d4d4d);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}
```

#### 2. API Service Update

**File**: `frontend/src/services/api/outlets.js`

**Added Method**:
```javascript
getOrganizationStats: () => api.get('/outlets/organization/stats')
```

#### 3. Outlets Page Update

**File**: `frontend/src/pages/Outlets.jsx`

**Change**: Added OrgCard at top of page (line 62)
```javascript
{/* Organization Overview Card */}
<OrgCard />

{/* Search and View Controls */}
<div className="outlets-controls">
```

---

## Migration Scripts

### 1. Standalone Migration Script

**File**: `migrate.py`

**Purpose**: Run migration from developer's Mac without needing psql

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
python3 migrate.py
```

**Features**:
- Direct PostgreSQL connection via psycopg2
- Step-by-step migration with progress output
- Error handling and rollback
- Idempotent (safe to run multiple times)

### 2. Constraint Fix Script

**File**: `fix_constraint.py`

**Purpose**: Drop duplicate old constraints that prevented uploads

**What It Does**:
1. Lists all unique constraints on price_history
2. Drops old constraints:
   - `unique_price_per_date`
   - `price_history_distributor_product_id_effective_date_key`
3. Ensures new constraint exists:
   - `unique_price_per_outlet_product_date`

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
python3 fix_constraint.py
```

### 3. Remote Migration Shell Script

**File**: `run_migration_remote.sh`

**Purpose**: Helper script for running migration on remote database

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
./run_migration_remote.sh
```

---

## Testing & Verification

### Test Scenario 1: Independent Pricing ✅

**Setup**:
- Organization: Fairmont
- Outlets: Default, IAK

**Test Steps**:
1. Default Outlet uploads "Tomatoes" (SKU 7402) → $45.00
2. IAK Outlet uploads "Tomatoes" (SKU 7402) → $50.00

**Expected Results**:
- ✅ Default Outlet sees $45.00
- ✅ IAK Outlet sees $50.00
- ✅ Both uploads succeed without errors
- ✅ No products disappear

**Verification Query**:
```sql
SELECT
    p.name,
    o.name as outlet,
    ph.unit_price,
    ph.effective_date
FROM price_history ph
JOIN distributor_products dp ON dp.id = ph.distributor_product_id
JOIN products p ON p.id = dp.product_id
JOIN outlets o ON o.id = ph.outlet_id
WHERE p.name LIKE '%Tomato%'
ORDER BY o.name, ph.effective_date DESC;
```

### Test Scenario 2: Shared Product Mapping ✅

**Question**: "If Outlet 1 maps SKU 7402 to 'Tomatoes - Organic', does Outlet 4 need to remap it?"

**Answer**: NO! Product mappings are organization-level.

**Test Steps**:
1. Default Outlet uploads SKU 7402 (unmapped initially)
2. Default Outlet maps SKU 7402 → "Tomatoes - Organic"
3. IAK Outlet uploads same SKU 7402

**Expected Results**:
- ✅ IAK automatically gets the mapping
- ✅ No need to remap in IAK
- ✅ `product.common_product_id` is shared

### Test Scenario 3: Outlet Stats ✅

**Test**: Verify outlet cards show correct counts

**Expected**:
- Products count = products imported by this outlet
- Recipes count = recipes created in this outlet
- Users count = users assigned to this outlet
- Imports count = CSV uploads to this outlet

**Verification**:
```
GET /outlets/1/stats
Response:
{
  "outlet_id": 1,
  "outlet_name": "Default Outlet",
  "products_count": 15,
  "recipes_count": 3,
  "users_count": 2,
  "imports_count": 5
}
```

### Test Scenario 4: Organization Overview ✅

**Test**: Organization card displays aggregate stats

**Expected**:
- Total outlets: 2 (Default + IAK)
- Total products: All unique products across outlets
- Total recipes: All recipes across outlets
- Total users: All users in organization
- Total imports: All CSV uploads

**Verification**:
```
GET /outlets/organization/stats
Response:
{
  "organization_id": 1,
  "organization_name": "Fairmont",
  "outlets_count": 2,
  "products_count": 20,
  "recipes_count": 5,
  "users_count": 3,
  "imports_count": 7
}
```

---

## Errors Encountered & Fixed

### Error 1: CSV Upload 500 Error
**Error**: `UnboundLocalError: cannot access local variable 'get_db'`

**Cause**: Local imports inside function shadowing global imports (lines 398-399 in uploads.py)

**Fix**: Moved imports to top-level

**Commit**: `fix: Move get_user_outlet_ids import to top level to fix variable shadowing`

### Error 2: Duplicate Key Constraint
**Error**: `duplicate key value violates unique constraint "unique_price_per_date"`

**Cause**: Multiple old unique constraints existed on price_history table

**Fix**: Created `fix_constraint.py` script to drop all old constraints

**Migration**: Updated to use DO $ blocks for idempotent constraint creation

### Error 3: Products Disappearing
**Issue**: Products uploaded to Default disappeared when IAK uploaded same SKU

**Cause**: Single price record per product per date (organization-wide)

**Fix**: Added `outlet_id` to price_history unique constraint

### Error 4: Outlet Stats Showing Zeros
**Error**: Frontend cards showed 0 for all counts despite data existing

**Cause**: Field name mismatch - backend returned `products`, frontend expected `products_count`

**Fix**: Changed backend response to use `_count` suffix for all fields

**Commit**: `fix: Match outlet stats field names to frontend expectations`

---

## API Endpoints

### New Endpoint

```
GET /outlets/organization/stats
```
**Purpose**: Get organization-wide aggregate statistics
**Auth**: Required (JWT)
**Response**:
```json
{
  "organization_id": 1,
  "organization_name": "Fairmont",
  "products_count": 20,
  "recipes_count": 5,
  "users_count": 3,
  "outlets_count": 2,
  "imports_count": 7
}
```

### Modified Endpoints

**All product endpoints** now support outlet filtering:
- `GET /products?outlet_id=1` - Products imported by outlet 1
- `GET /products` (no param) - All products in organization

**Price history queries** now scoped by outlet:
- Prices partitioned by `(distributor_product_id, outlet_id)`
- Each outlet sees its own latest prices

---

## Deployment

### Git Commits (Chronological)

1. `fix: Add missing comma in get recipe SQL query and error logging`
2. `debug: Add error logging to common product update endpoint`
3. `fix: Convert boolean to integer for allergen fields in update`
4. `docs: Update documentation for PostgreSQL migration complete`
5. `docs: Add resume guide for Dec 12 multi-tenancy work`
6. `fix: Move get_user_outlet_ids import to top level`
7. `fix: Add outlet_id to price history queries in uploads`
8. `fix: Remove redundant outlet column from products table`
9. `fix: Match outlet stats field names to frontend expectations`
10. `feat: Add organization-level statistics card`

### Branch: `dev`

**Deployment**:
- Pushed to `origin/dev`
- Auto-deployed to Render (food-cost-tracker-dev.onrender.com)
- Migration runs automatically via Alembic

---

## Future Enhancements

### Phase 1: Recipe Costing Per Outlet
Currently recipes use organization-level product prices. Could enhance to use outlet-specific pricing for more accurate recipe costing per location.

### Phase 2: Historical Price Comparison
Add UI to compare prices across outlets:
- "Why is IAK paying more for tomatoes?"
- Price variance reports
- Outlet-to-outlet price comparisons

### Phase 3: Price Import Templates
Generate CSV templates pre-filled with products each outlet has used, making price updates easier.

### Phase 4: Bulk Price Updates
Allow admins to copy prices from one outlet to another:
- "Use Default's prices for IAK"
- Helpful for new outlet setup

---

## Lessons Learned

1. **Shared vs Scoped Data**
   - Products: Shared (organization-level)
   - Pricing: Scoped (outlet-level)
   - Clear separation prevents conflicts

2. **Historical Metadata**
   - `product.outlet_id` is "who created it first"
   - NOT "who can see it"
   - Filtering must use relationships (price_history.outlet_id)

3. **Unique Constraints Matter**
   - Must include all partitioning columns
   - `(distributor_product_id, outlet_id, effective_date)` allows per-outlet pricing

4. **Migration Scripts**
   - Standalone Python scripts > psql commands
   - Developers can run from Mac
   - Idempotent patterns (DO $ blocks, IF NOT EXISTS)

5. **Field Naming Conventions**
   - Backend and frontend must agree on field names
   - Use `_count` suffix for count fields consistently
   - Document expected response shapes

---

## Resources

- **Migration File**: `db/migrations/002_add_outlet_id_to_price_history.sql`
- **Migration Scripts**: `migrate.py`, `fix_constraint.py`, `run_migration_remote.sh`
- **Backend Files**: `api/app/routers/products.py`, `api/app/routers/uploads.py`, `api/app/routers/outlets.py`
- **Frontend Files**: `frontend/src/components/outlets/OrgCard.jsx`, `frontend/src/pages/Outlets.jsx`
- **Dev Environment**: https://food-cost-tracker-dev.onrender.com

---

**Status**: ✅ Complete and deployed to dev

Multi-outlet pricing is fully operational. Each outlet can now manage independent pricing without interfering with other outlets. Organization card provides helpful overview of entire organization's data. 🚀
