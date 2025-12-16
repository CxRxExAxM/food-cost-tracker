# Resume Here - December 13, 2025

## Quick Context

**Current State (as of Dec 13 EOD):**
- ✅ Multi-tenancy COMPLETE (organizations + outlets)
- ✅ Phase 2 Core COMPLETE (outlet management UI)
- ✅ Per-outlet pricing COMPLETE (price_history.outlet_id)
- ✅ Organization overview card COMPLETE
- ✅ All features working on dev environment

**Branch:** `dev` (ready for final testing and production deployment)

---

## What We Accomplished Today (Dec 13)

### Critical Schema Change: Per-Outlet Pricing

**Problem Solved**: Multiple outlets uploading the same products caused conflicts
- Before: Last uploader "won", products disappeared from other outlets
- After: Each outlet maintains independent pricing

**Technical Implementation**:
1. Added `outlet_id` column to `price_history` table
2. Changed unique constraint from `(distributor_product_id, effective_date)` to `(distributor_product_id, outlet_id, effective_date)`
3. Updated all price queries to partition by outlet_id
4. Created migration scripts (migrate.py, fix_constraint.py)

**Migration**: `db/migrations/002_add_outlet_id_to_price_history.sql`

### Organization Overview Card

**Added**: Organization-level statistics card on Outlets page
- Total outlets, products, recipes, users, imports
- Distinctive gradient design
- Aggregate view across all outlets

**Endpoint**: `GET /outlets/organization/stats`

### Bug Fixes

1. ✅ CSV upload 500 error (variable shadowing)
2. ✅ Duplicate key constraint violations
3. ✅ Products disappearing between outlets
4. ✅ Outlet stats showing zeros (field name mismatch)
5. ✅ Dark mode text color issues in allergen modals

---

## Current System Architecture

### Data Hierarchy

```
Organization (Fairmont)
├── Outlets (Default, IAK, Test Kitchen)
│   ├── Price History (per-outlet, per-product, per-date)
│   ├── Recipes (outlet-scoped)
│   └── Users (assigned to outlets)
├── Products (organization-scoped, shared across outlets)
│   └── Common Product Mappings (organization-scoped, shared)
└── Distributors & Units (globally shared)
```

### Key Design Principles

1. **Products are Shared**: All outlets in an organization share the product catalog
2. **Pricing is Isolated**: Each outlet maintains independent price history
3. **Mappings are Reused**: Product-to-common_product mappings shared across outlets
4. **Filtering by Import**: Products shown based on which outlet has imported them

**Example**:
- Default Outlet uploads "Tomatoes" (SKU 7402) at $45.00
- IAK Outlet uploads "Tomatoes" (SKU 7402) at $50.00
- Result: Both outlets see their own prices, no conflicts

---

## Database Schema (Current)

### Multi-Tenancy Structure

```sql
organizations
├── id, name, slug
├── subscription_tier (free, basic, pro, enterprise)
└── max_users, max_recipes

outlets
├── id, organization_id (FK)
├── name, location, description
└── is_active

users
├── id, organization_id (FK)
├── email, username, hashed_password
└── role (admin, chef, viewer)

user_outlets (many-to-many)
├── user_id (FK)
└── outlet_id (FK)
```

### Product & Pricing Structure

```sql
products (organization-scoped, shared)
├── id, organization_id (FK)
├── outlet_id (historical: who created it first)
├── name, brand, pack, size
└── common_product_id (FK, nullable)

distributor_products (organization-scoped)
├── id, organization_id (FK)
├── product_id (FK), distributor_id (FK)
└── distributor_sku

price_history (outlet-scoped, isolated)
├── id, outlet_id (FK)                    ← NEW!
├── distributor_product_id (FK)
├── case_price, unit_price, effective_date
├── import_batch_id (FK)
└── UNIQUE (distributor_product_id, outlet_id, effective_date)

recipes (outlet-scoped)
├── id, organization_id (FK), outlet_id (FK)
├── name, category, description
└── yield_amount, yield_unit_id
```

---

## Frontend Structure

### Context & State Management

```javascript
// AuthContext - User authentication
{
  user,              // Current user object
  organization_id,   // User's organization
  isAdmin(),         // Check admin role
  login(), logout()
}

// OutletContext - Outlet management
{
  outlets,           // All outlets in organization
  currentOutlet,     // Selected outlet (or "All Outlets")
  selectOutlet(),    // Change selected outlet
  createOutlet(),    // Create new outlet (admin)
  updateOutlet(),    // Update outlet (admin)
  deleteOutlet()     // Delete outlet (admin)
}
```

### Pages & Routes

```
/                    → Dashboard (products, recipes counts)
/products            → Products list (filtered by currentOutlet)
/recipes             → Recipes list (filtered by currentOutlet)
/outlets             → Outlets management (admin only)
/admin               → User management (admin only)
/uploads             → CSV upload (assigned to currentOutlet)
```

### Key Components

```
Navigation.jsx          - Header with OutletSelector
OutletSelector.jsx      - Dropdown to switch outlets
OutletCard.jsx          - Individual outlet display
OrgCard.jsx             - Organization overview stats
OutletBadge.jsx         - Shows outlet on product/recipe cards
CreateOutletModal.jsx   - Create new outlet form
EditOutletModal.jsx     - Edit outlet form
```

---

## API Endpoints (Complete List)

### Authentication
```
POST   /auth/setup              - Initial organization + admin setup
POST   /auth/login              - Login (returns JWT with org_id)
GET    /auth/me                 - Get current user info
GET    /auth/users              - List users in organization
POST   /auth/users              - Create user (admin)
PATCH  /auth/users/{id}         - Update user (admin)
DELETE /auth/users/{id}         - Delete user (admin)
```

### Outlets
```
GET    /outlets                     - List all outlets
GET    /outlets/{id}                - Get outlet details
GET    /outlets/{id}/stats          - Get outlet statistics
GET    /outlets/organization/stats  - Get organization statistics ← NEW!
POST   /outlets                     - Create outlet (admin)
PATCH  /outlets/{id}                - Update outlet (admin)
DELETE /outlets/{id}                - Delete outlet (admin)
GET    /outlets/{id}/users          - List users in outlet
POST   /outlets/{id}/users/{uid}    - Assign user to outlet
DELETE /outlets/{id}/users/{uid}    - Remove user from outlet
```

### Products
```
GET    /products                - List products (optional ?outlet_id filter)
GET    /products/{id}           - Get product details
POST   /products                - Create product
PATCH  /products/{id}           - Update product
DELETE /products/{id}           - Soft delete product
POST   /products/{id}/map       - Map to common product
DELETE /products/{id}/unmap     - Unmap from common product
```

### Recipes
```
GET    /recipes                 - List recipes (optional ?outlet_id filter)
GET    /recipes/{id}            - Get recipe details
POST   /recipes                 - Create recipe (?outlet_id param)
PATCH  /recipes/{id}            - Update recipe
DELETE /recipes/{id}            - Delete recipe
GET    /recipes/{id}/cost       - Calculate recipe cost
POST   /recipes/{id}/ingredients     - Add ingredient
PATCH  /recipes/{id}/ingredients/{iid} - Update ingredient
DELETE /recipes/{id}/ingredients/{iid} - Remove ingredient
```

### Common Products
```
GET    /common-products         - List common products
GET    /common-products/{id}    - Get common product
POST   /common-products         - Create common product
PATCH  /common-products/{id}    - Update common product
DELETE /common-products/{id}    - Soft delete common product
GET    /common-products/{id}/products - List mapped products
```

### Uploads
```
POST   /uploads/csv             - Upload CSV (?outlet_id param)
GET    /uploads/history         - List import batches
GET    /uploads/history/{id}    - Get import batch details
```

---

## Testing Checklist

### Multi-Outlet Pricing ✅
- [x] Create two outlets (Default, IAK)
- [x] Upload same product to both with different prices
- [x] Verify each outlet sees its own price
- [x] Verify products don't disappear
- [x] Switch outlets in selector
- [x] Verify product list filters correctly

### Organization Stats ✅
- [x] Organization card displays on Outlets page
- [x] Shows total outlets count
- [x] Shows total products count (org-wide)
- [x] Shows total recipes count (org-wide)
- [x] Shows total users count
- [x] Shows total imports count

### Outlet Stats ✅
- [x] Each outlet card shows correct counts
- [x] Products count = products imported by outlet
- [x] Recipes count = recipes created in outlet
- [x] Users count = users assigned to outlet

### Product Filtering ✅
- [x] Select "All Outlets" → see all products
- [x] Select specific outlet → see only imported products
- [x] Create product → assigned to current outlet
- [x] Upload CSV → products assigned to selected outlet

### Recipe Filtering ✅
- [x] Select "All Outlets" → see all recipes
- [x] Select specific outlet → see only outlet recipes
- [x] Create recipe → assigned to current outlet

---

## Migration Scripts Reference

### migrate.py
**Purpose**: Standalone migration script for adding outlet_id to price_history

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
python3 migrate.py
```

**What it does**:
1. Adds outlet_id column
2. Populates from import_batches
3. Sets NOT NULL constraint
4. Adds foreign key
5. Updates unique constraint
6. Creates index

### fix_constraint.py
**Purpose**: Drop old duplicate constraints that prevent uploads

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
python3 fix_constraint.py
```

**What it does**:
1. Lists all constraints on price_history
2. Drops old constraints
3. Ensures new constraint exists

### run_migration_remote.sh
**Purpose**: Helper script to run migration on remote database

**Usage**:
```bash
export DATABASE_URL="postgres://user:pass@host/dbname"
./run_migration_remote.sh
```

---

## Critical Code Patterns

### 1. Product Filtering by Outlet

```python
# In products.py - Filter products by outlet import history
if outlet_id is not None:
    where_clause += """ AND EXISTS (
        SELECT 1 FROM price_history ph_filter
        JOIN distributor_products dp_filter ON dp_filter.id = ph_filter.distributor_product_id
        WHERE dp_filter.product_id = p.id AND ph_filter.outlet_id = %s
    )"""
```

### 2. Price Join with Outlet Partitioning

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

### 3. Price History Insert with Outlet

```python
# In uploads.py - Create price with outlet_id
cursor.execute("""
    INSERT INTO price_history
    (distributor_product_id, outlet_id, case_price, unit_price, effective_date, import_batch_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id
""", (distributor_product_id, outlet_id, case_price, unit_price, eff_date, import_batch_id))
```

---

## Known Limitations & Future Work

### Current Limitations
1. **Recipe Costing**: Uses organization-level product prices, not outlet-specific
2. **User Assignment UI**: Can assign users via API but no UI yet
3. **Outlet Detail Page**: No detailed outlet page (optional feature)

### Future Enhancements (Phase 3)

**High Priority**:
- [ ] Recipe costing per outlet (use outlet-specific prices)
- [ ] Bulk price import templates (pre-filled with outlet products)
- [ ] Price comparison across outlets

**Medium Priority**:
- [ ] Outlet detail page with detailed stats
- [ ] User assignment UI (assign users to outlets)
- [ ] Historical price trends per outlet

**Low Priority**:
- [ ] Copy prices from one outlet to another
- [ ] Outlet-to-outlet price variance reports
- [ ] Export outlet-specific data

---

## Git Workflow

### Current Branch Status

```bash
Branch: dev
Status: Clean, all changes committed and pushed
Latest Commit: feat: Add organization-level statistics card (ede014a)
```

### Recent Commits (Chronological)

```
77e532b - docs: Add resume guide for Dec 12 multi-tenancy work
f538765 - docs: Update documentation for PostgreSQL migration complete
30b5810 - fix: Add missing comma in get recipe SQL query and error logging
9240467 - fix: Convert boolean to integer for allergen fields in update
78fbe28 - debug: Add error logging to common product update endpoint
b889ff0 - fix: Match outlet stats field names to frontend expectations
ede014a - feat: Add organization-level statistics card
```

### Deployment Status

- ✅ Dev: https://food-cost-tracker-dev.onrender.com (deployed)
- ⚠️ Prod: https://food-cost-tracker.onrender.com (needs merge from dev)

---

## Next Steps

### Option 1: Production Deployment (Recommended)

**Why**: Core functionality is complete and working on dev

**Steps**:
1. Final testing on dev environment (30 min)
   - Test multi-outlet CSV uploads
   - Test outlet switching and filtering
   - Test organization stats card
   - Test recipe creation with outlets

2. Merge dev → main (5 min)
   ```bash
   git checkout main
   git pull origin main
   git merge dev
   git push origin main
   ```

3. Verify production deployment (15 min)
   - Migration runs automatically
   - Test basic flows
   - Verify data isolation

4. Update documentation (15 min)
   - Mark Phase 2 as deployed to production
   - Create production testing guide

**Total Time**: ~1 hour

---

### Option 2: Add Optional Features (Phase 3)

**Why**: If you want outlet detail page and user assignment UI

**Features to Build**:
1. Outlet Detail Page (2-3 hours)
   - Detailed statistics
   - Recent products/recipes
   - Activity timeline

2. User Assignment UI (2-3 hours)
   - Assign users to outlets interface
   - Show user's assigned outlets
   - Bulk assignment

**Total Time**: 4-6 hours

---

### Option 3: Recipe Costing Enhancement

**Why**: Make recipe costs outlet-specific

**Changes Needed**:
1. Update recipe costing to use outlet_id (1-2 hours)
2. Add outlet selector to recipe costing page (30 min)
3. Display price source (which outlet) on recipe cards (30 min)

**Total Time**: 2-3 hours

---

## Documentation Files

**Phase 2 Documentation**:
- `MULTI_OUTLET_PRICING_DEC13.md` - Complete guide to per-outlet pricing
- `PHASE2_PLAN.md` - Phase 2 implementation plan (updated)
- `START_HERE_DEC13.md` - This file

**Multi-Tenancy Documentation**:
- `MULTI_TENANCY_DEC12.md` - Organization-based multi-tenancy
- `START_HERE_DEC12.md` - Previous resume guide

**Migration Documentation**:
- `POSTGRESQL_MIGRATION_DEC11.md` - SQLite → PostgreSQL migration
- `db/migrations/002_add_outlet_id_to_price_history.sql` - Schema migration

**Project Overview**:
- `README.md` - Main project documentation
- `PROJECT_CONTEXT.md` - Overall project vision
- `TESTING_GUIDE.md` - Testing procedures

---

## Quick Reference Commands

### Backend
```bash
# Start backend
cd api && ../venv/bin/uvicorn app.main:app --reload --port 8000

# Run migrations locally
venv/bin/alembic upgrade head

# Check current migration
venv/bin/alembic current

# Create new migration
venv/bin/alembic revision --autogenerate -m "Description"
```

### Frontend
```bash
# Start frontend
cd frontend && npm run dev

# Build for production
npm run build
```

### Git
```bash
# Check status
git status

# View changes
git diff

# Push to dev (auto-deploys)
git push origin dev

# Merge to main (production)
git checkout main
git merge dev
git push origin main
```

### Database Migration (Remote)
```bash
# Get DATABASE_URL from Render dashboard
export DATABASE_URL="postgres://user:pass@host/dbname"

# Run migration
python3 migrate.py

# Fix constraints if needed
python3 fix_constraint.py
```

---

## Success Metrics

### Phase 2 Complete ✅

- [x] Multiple outlets can operate independently
- [x] Each outlet maintains its own pricing
- [x] Product filtering works correctly
- [x] Organization overview provides aggregate view
- [x] Mobile responsive design
- [x] Error handling and edge cases covered
- [x] All features working on dev

### Production Ready ⚠️

- [x] All code committed and pushed
- [x] Database migrations tested
- [x] Multi-outlet pricing verified
- [ ] Final end-to-end testing on dev
- [ ] Merge to main
- [ ] Production deployment
- [ ] Production smoke testing

---

## Recommended Path Forward

**Today (Dec 13 EOD)**:
1. ✅ Document completion (this file)
2. ✅ Update all relevant documentation
3. ✅ Commit documentation updates

**Tomorrow (Dec 14)**:
1. Final testing on dev (30 min)
2. Merge to main (5 min)
3. Verify production deployment (15 min)
4. Create Phase 3 plan (optional features)

---

**You're in great shape! Phase 2 core functionality is complete and working perfectly on dev. Ready for production when you are! 🚀**
