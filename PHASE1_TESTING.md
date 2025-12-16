# Phase 1 Multi-Outlet Backend Testing Plan

## Test Environment Setup

**Prerequisites:**
- Dev environment deployed with latest code
- Database migration 003_add_outlets_support.py applied
- At least one test organization in database
- API accessible at dev URL

---

## Test Suite 1: Database Migration Verification

### 1.1 Verify Outlets Table Created
```sql
-- Check outlets table exists and has correct structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'outlets'
ORDER BY ordinal_position;
```

**Expected:**
- id (integer, NOT NULL)
- organization_id (integer, NOT NULL)
- name (varchar, NOT NULL)
- location (varchar, NULLABLE)
- description (text, NULLABLE)
- is_active (integer, DEFAULT 1)
- created_at (timestamp)
- updated_at (timestamp)

### 1.2 Verify User-Outlets Junction Table
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'user_outlets'
ORDER BY ordinal_position;
```

**Expected:**
- user_id (integer, NOT NULL)
- outlet_id (integer, NOT NULL)
- Composite primary key (user_id, outlet_id)

### 1.3 Verify outlet_id Added to Tables
```sql
-- Check products table
SELECT COUNT(*) as total,
       COUNT(outlet_id) as with_outlet,
       COUNT(*) - COUNT(outlet_id) as without_outlet
FROM products;

-- Check recipes table
SELECT COUNT(*) as total,
       COUNT(outlet_id) as with_outlet
FROM recipes;

-- Check import_batches table
SELECT COUNT(*) as total,
       COUNT(outlet_id) as with_outlet
FROM import_batches;
```

**Expected:** All existing records should have outlet_id populated (migrated to "Default Outlet")

### 1.4 Verify Default Outlets Created
```sql
-- Check that each organization has a default outlet
SELECT o.id, o.name, org.name as organization_name, o.is_active
FROM outlets o
JOIN organizations org ON org.id = o.organization_id
WHERE o.name = 'Default Outlet';
```

**Expected:** One "Default Outlet" per organization

---

## Test Suite 2: Outlet CRUD Operations

### 2.1 List Outlets (GET /outlets)
```bash
curl -X GET "https://your-dev-url/outlets" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- 200 OK
- Returns array of outlets for user's organization
- Each outlet has: id, name, location, description, is_active, organization_id

### 2.2 Create Outlet (POST /outlets) - Admin Only
```bash
curl -X POST "https://your-dev-url/outlets" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Main Kitchen",
    "location": "Building A",
    "description": "Primary production kitchen"
  }'
```

**Expected:**
- 201 Created
- Returns created outlet with generated ID
- Verify in database

### 2.3 Get Outlet Details (GET /outlets/{id})
```bash
curl -X GET "https://your-dev-url/outlets/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- 200 OK
- Returns outlet details
- Only accessible if outlet belongs to user's organization

### 2.4 Update Outlet (PATCH /outlets/{id}) - Admin Only
```bash
curl -X PATCH "https://your-dev-url/outlets/1" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Building B - Updated"
  }'
```

**Expected:**
- 200 OK
- Returns updated outlet
- Verify location changed

### 2.5 Get Outlet Stats (GET /outlets/{id}/stats)
```bash
curl -X GET "https://your-dev-url/outlets/1/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- 200 OK
- Returns: products count, recipes count, users count, imports count

### 2.6 Access Control - Cross-Organization Denial
Create outlet in Org A, try to access from Org B user.

**Expected:** 404 or 403 error

---

## Test Suite 3: User-Outlet Assignment

### 3.1 Assign User to Outlet (POST /outlets/{id}/users/{user_id}) - Admin Only
```bash
curl -X POST "https://your-dev-url/outlets/1/users/2" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Expected:**
- 204 No Content
- Verify in database: `SELECT * FROM user_outlets WHERE user_id=2 AND outlet_id=1;`

### 3.2 List Users in Outlet (GET /outlets/{id}/users)
```bash
curl -X GET "https://your-dev-url/outlets/1/users" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- 200 OK
- Returns array of users assigned to outlet

### 3.3 Remove User from Outlet (DELETE /outlets/{id}/users/{user_id})
```bash
curl -X DELETE "https://your-dev-url/outlets/1/users/2" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

**Expected:**
- 204 No Content
- Verify removed from database

### 3.4 Test Org-Wide Admin Access
User with NO user_outlets entries should see ALL outlets in their organization.

```sql
-- Remove all outlet assignments for test admin user
DELETE FROM user_outlets WHERE user_id = {admin_user_id};
```

Then list products/recipes - should see ALL outlets.

---

## Test Suite 4: Products with Outlet Filtering

### 4.1 Create Product with Outlet Assignment
```bash
curl -X POST "https://your-dev-url/products" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Organic Tomatoes",
    "brand": "Fresh Farms",
    "pack": 25,
    "size": 1.0,
    "unit_id": 1,
    "outlet_id": 1
  }'
```

**Expected:**
- 201 Created
- Product assigned to outlet_id = 1
- Verify: `SELECT * FROM products WHERE name='Organic Tomatoes';`

### 4.2 Create Product Without Outlet (Auto-Assignment)
```bash
curl -X POST "https://your-dev-url/products" \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "pack": 12,
    "size": 16.0
  }'
```

**Expected:**
- Product auto-assigned to user's first outlet
- Check response: `"outlet_id": {some_id}`

### 4.3 List Products - Outlet Filtering
Setup:
- Create 2 outlets
- Create Product A in Outlet 1
- Create Product B in Outlet 2
- Assign User X to Outlet 1 only

Test:
```bash
curl -X GET "https://your-dev-url/products" \
  -H "Authorization: Bearer USER_X_TOKEN"
```

**Expected:**
- User X only sees Product A (Outlet 1)
- User X does NOT see Product B (Outlet 2)

### 4.4 Test Cross-Outlet Access Denial
Try to access product from different outlet:
```bash
curl -X GET "https://your-dev-url/products/{product_in_other_outlet_id}" \
  -H "Authorization: Bearer USER_TOKEN"
```

**Expected:** 404 "Product not found or you don't have access to it"

### 4.5 Test Org-Wide Admin Sees All Products
Org-wide admin (no user_outlets entries) should see products from all outlets.

---

## Test Suite 5: Recipes with Outlet Filtering

### 5.1 Create Recipe with Outlet Assignment
```bash
curl -X POST "https://your-dev-url/recipes" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Tomato Sauce",
    "category": "Sauces",
    "outlet_id": 1,
    "ingredients": []
  }'
```

**Expected:**
- 201 Created
- Recipe assigned to outlet_id = 1
- Verify in database

### 5.2 List Recipes - Outlet Filtering
Setup similar to products test:
- Recipe A in Outlet 1
- Recipe B in Outlet 2
- User only assigned to Outlet 1

**Expected:** User only sees Recipe A

### 5.3 Test Recipe Access Control
Try to access recipe from unauthorized outlet.

**Expected:** 404 error

---

## Test Suite 6: Recipe Costing with Outlet-Specific Prices

### CRITICAL TEST - This is the killer feature!

Setup:
1. Create 2 outlets: "Main Kitchen" and "Banquet Kitchen"
2. Create common product: "Butter"
3. Create Product mapping in Main Kitchen:
   - Sysco Butter: $2.50/lb
4. Create Product mapping in Banquet Kitchen:
   - Different supplier Butter: $3.00/lb
5. Create identical recipe "Butter Sauce" in both outlets using common product "Butter"

### 6.1 Test Main Kitchen Recipe Cost
```bash
curl -X GET "https://your-dev-url/recipes/{main_kitchen_recipe_id}/cost" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- Uses Sysco Butter price ($2.50/lb)
- Total cost calculated with $2.50 rate

### 6.2 Test Banquet Kitchen Recipe Cost
```bash
curl -X GET "https://your-dev-url/recipes/{banquet_kitchen_recipe_id}/cost" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected:**
- Uses other supplier price ($3.00/lb)
- Total cost calculated with $3.00 rate

### 6.3 Verify SQL Query in Logs
Check that recipe costing query includes:
```sql
WHERE p.common_product_id = %s AND p.outlet_id = %s
```

**This ensures outlet-specific pricing!**

---

## Test Suite 7: CSV Upload with Outlet Assignment

### 7.1 Upload CSV with Outlet Specified
```bash
curl -X POST "https://your-dev-url/uploads/csv" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@sysco_price_list.csv" \
  -F "distributor_code=sysco" \
  -F "outlet_id=1"
```

**Expected:**
- All products created/updated in outlet_id = 1
- Verify: `SELECT outlet_id FROM products WHERE name IN (...imported products...);`

### 7.2 Upload CSV Without Outlet (Auto-Assignment)
```bash
curl -X POST "https://your-dev-url/uploads/csv" \
  -H "Authorization: Bearer USER_TOKEN" \
  -F "file=@vesta_price_list.csv" \
  -F "distributor_code=vesta"
```

**Expected:**
- Products auto-assigned to user's first outlet
- Check import_batch: `SELECT outlet_id FROM import_batches WHERE id = {batch_id};`

### 7.3 Test Cross-Outlet Product Conflict
Setup:
- Upload "Organic Carrots" to Outlet 1
- Upload "Organic Carrots" (different price) to Outlet 2

**Expected:**
- Two separate product records created (different outlets)
- No conflict/overwrite

---

## Test Suite 8: Data Isolation Verification

### 8.1 Complete Isolation Test

**Setup:**
```sql
-- Create test scenario
-- Organization: "Hotel XYZ"
-- Outlet 1: "Main Kitchen"
-- Outlet 2: "Banquet Kitchen"
-- User A: Assigned to Main Kitchen only
-- User B: Assigned to Banquet Kitchen only
-- Admin C: No outlet assignments (org-wide)

-- Products:
-- Product 1: "Test Tomatoes" in Main Kitchen
-- Product 2: "Test Onions" in Banquet Kitchen

-- Recipes:
-- Recipe 1: "Test Pasta" in Main Kitchen
-- Recipe 2: "Test Steak" in Banquet Kitchen
```

**Test Matrix:**

| User    | GET /products | Should See        |
|---------|---------------|-------------------|
| User A  | GET /products | Product 1 only    |
| User B  | GET /products | Product 2 only    |
| Admin C | GET /products | Products 1 & 2    |

| User    | GET /recipes  | Should See        |
|---------|---------------|-------------------|
| User A  | GET /recipes  | Recipe 1 only     |
| User B  | GET /recipes  | Recipe 2 only     |
| Admin C | GET /recipes  | Recipes 1 & 2     |

| User    | Access Product 2 (Outlet 2) | Expected |
|---------|----------------------------|----------|
| User A  | GET /products/2            | 404      |
| User B  | GET /products/2            | 200 OK   |
| Admin C | GET /products/2            | 200 OK   |

---

## Test Suite 9: Edge Cases & Error Handling

### 9.1 Test User with Multiple Outlet Access
Assign user to both Outlet 1 and Outlet 2.

**Expected:** User sees products/recipes from BOTH outlets

### 9.2 Test Creating Product in Unauthorized Outlet
```bash
curl -X POST "https://your-dev-url/products" \
  -H "Authorization: Bearer USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test",
    "outlet_id": 999
  }'
```

**Expected:** 403 "You don't have access to this outlet"

### 9.3 Test Organization with No Outlets
Create new organization, check if error handling works.

**Expected:** Graceful error message

### 9.4 Test Deleting Outlet with Products
Try to delete outlet that has products.

**Expected:** 400 "Cannot delete outlet with X products and Y recipes"

### 9.5 Test Deactivating Outlet
Update outlet `is_active = 0`.

**Expected:** Outlet hidden from lists but data preserved

---

## Test Suite 10: Performance & Query Optimization

### 10.1 Check Query Plans
```sql
EXPLAIN ANALYZE
SELECT * FROM products p
WHERE p.organization_id = 1 AND p.outlet_id IN (1, 2);
```

**Verify:** Uses indexes efficiently

### 10.2 Test with Large Dataset
- Create 1000+ products across 5 outlets
- Time list products endpoint
- Should complete in < 500ms

---

## Summary Checklist

- [ ] Database migration applied successfully
- [ ] Default outlets created for existing organizations
- [ ] Outlet CRUD operations work correctly
- [ ] User-outlet assignments function properly
- [ ] Org-wide admins see all outlets
- [ ] Outlet-scoped users see only assigned outlets
- [ ] Products properly filtered by outlet access
- [ ] Recipes properly filtered by outlet access
- [ ] **Recipe costing uses outlet-specific product prices** ⭐
- [ ] CSV uploads assign to correct outlet
- [ ] Data isolation prevents cross-outlet access
- [ ] Error handling works for unauthorized access
- [ ] Multi-outlet users see aggregated data
- [ ] No performance degradation with filtering

---

## Next Steps After Testing

Once all tests pass:
1. Document any bugs found and fix them
2. Update API documentation with outlet_id parameters
3. Create test dataset for demo purposes
4. Proceed to Phase 2: Outlet Management UI
