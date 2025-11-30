# Multi-Tenancy Testing Guide

This guide explains how to test the multi-tenancy implementation locally.

## Overview

The multi-tenancy implementation ensures that:
- Each organization's data is completely isolated
- Users can only access data from their own organization
- JWT tokens include organization_id to enforce access control
- All API routes filter queries by organization_id

## Prerequisites

1. **Backend API running:**
   ```bash
   venv/bin/uvicorn api.app.main:app --port 8000 --host 127.0.0.1 --reload
   ```

2. **Frontend running (optional):**
   ```bash
   cd frontend && npm run dev
   ```

3. **Required tools:**
   - `curl` - for API testing
   - `jq` - for JSON parsing (install with: `brew install jq`)

## Quick Start - Automated Testing

### Run the full test suite:
```bash
./test_multi_tenancy.sh
```

This automated script will:
1. Create two separate organizations (Org A and Org B)
2. Create test data for each organization
3. Verify data isolation (Org A cannot see Org B's data)
4. Test direct access prevention (accessing by ID)
5. Test common products isolation
6. Provide a pass/fail summary

## Manual Testing Scenarios

### Scenario 1: Create Two Organizations

#### Terminal 1: Organization A
```bash
# 1. Create first admin (this creates Organization 1)
curl -X POST http://127.0.0.1:8000/auth/setup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@org-a.com",
    "username": "admin_a",
    "password": "testpass123",
    "full_name": "Org A Admin"
  }'

# Save the access_token from response
export ORG_A_TOKEN="<paste_token_here>"

# 2. Verify your organization
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $ORG_A_TOKEN" | jq
```

#### Terminal 2: Organization B
```bash
# Note: Second org needs to be created manually in database for now
# Future: Will have organization signup endpoint

# 1. Create Org B in database
sqlite3 food_cost.db <<EOF
INSERT INTO organizations (id, name, slug, subscription_tier, subscription_status, max_recipes, max_distributors, max_ai_parses_per_month, ai_parses_used_this_month)
VALUES (2, 'Organization B', 'org-b', 'free', 'active', 5, 1, 10, 0);

INSERT INTO users (organization_id, email, username, hashed_password, full_name, role, is_active)
SELECT 2, 'admin@org-b.com', 'admin_b',
       (SELECT hashed_password FROM users LIMIT 1),
       'Org B Admin', 'admin', 1;
EOF

# 2. Login as Org B admin
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@org-b.com",
    "password": "testpass123"
  }'

# Save the access_token
export ORG_B_TOKEN="<paste_token_here>"

# 3. Verify your organization
curl -X GET http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer $ORG_B_TOKEN" | jq
```

### Scenario 2: Test Recipe Isolation

#### Create Recipe in Org A:
```bash
curl -X POST http://127.0.0.1:8000/recipes \
  -H "Authorization: Bearer $ORG_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Secret Org A Recipe",
    "description": "Only Org A should see this",
    "category": "Entrees",
    "category_path": "Entrees",
    "yield_amount": 4,
    "method": [],
    "ingredients": []
  }' | jq
```

#### Create Recipe in Org B:
```bash
curl -X POST http://127.0.0.1:8000/recipes \
  -H "Authorization: Bearer $ORG_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Secret Org B Recipe",
    "description": "Only Org B should see this",
    "category": "Desserts",
    "category_path": "Desserts",
    "yield_amount": 8,
    "method": [],
    "ingredients": []
  }' | jq
```

#### Verify Isolation:
```bash
# Org A lists recipes (should only see Org A's recipe)
curl -X GET http://127.0.0.1:8000/recipes \
  -H "Authorization: Bearer $ORG_A_TOKEN" | jq '[.[].name]'

# Org B lists recipes (should only see Org B's recipe)
curl -X GET http://127.0.0.1:8000/recipes \
  -H "Authorization: Bearer $ORG_B_TOKEN" | jq '[.[].name]'
```

### Scenario 3: Test Direct Access Prevention

```bash
# Get a recipe ID from Org B
ORG_B_RECIPE_ID=$(curl -s -X GET http://127.0.0.1:8000/recipes \
  -H "Authorization: Bearer $ORG_B_TOKEN" | jq -r '.[0].id')

echo "Org B Recipe ID: $ORG_B_RECIPE_ID"

# Try to access it from Org A (should return 404)
curl -v -X GET http://127.0.0.1:8000/recipes/$ORG_B_RECIPE_ID \
  -H "Authorization: Bearer $ORG_A_TOKEN"

# Expected: HTTP 404 Not Found (recipe doesn't exist for Org A)
```

### Scenario 4: Test Common Products Isolation

```bash
# Org A creates a common product
curl -X POST http://127.0.0.1:8000/common-products \
  -H "Authorization: Bearer $ORG_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "Org A Chicken Breast",
    "category": "Proteins",
    "subcategory": "Poultry"
  }' | jq

# Org B creates a common product with same name (should work - different org)
curl -X POST http://127.0.0.1:8000/common-products \
  -H "Authorization: Bearer $ORG_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "common_name": "Org A Chicken Breast",
    "category": "Proteins",
    "subcategory": "Poultry"
  }' | jq

# List common products for Org A (should only see Org A's)
curl -X GET http://127.0.0.1:8000/common-products \
  -H "Authorization: Bearer $ORG_A_TOKEN" | jq '[.[].common_name]'

# List common products for Org B (should only see Org B's)
curl -X GET http://127.0.0.1:8000/common-products \
  -H "Authorization: Bearer $ORG_B_TOKEN" | jq '[.[].common_name]'
```

### Scenario 5: Test Products Isolation

```bash
# Org A creates a product
curl -X POST http://127.0.0.1:8000/products \
  -H "Authorization: Bearer $ORG_A_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Org A Premium Beef",
    "brand": "Premium Meats",
    "pack": 10,
    "size": 16,
    "unit_id": 2
  }' | jq

# Org B creates a product
curl -X POST http://127.0.0.1:8000/products \
  -H "Authorization: Bearer $ORG_B_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Org B Premium Beef",
    "brand": "Premium Meats",
    "pack": 10,
    "size": 16,
    "unit_id": 2
  }' | jq

# Verify products are isolated
curl -X GET http://127.0.0.1:8000/products \
  -H "Authorization: Bearer $ORG_A_TOKEN" | jq '.products | [.[].name]'

curl -X GET http://127.0.0.1:8000/products \
  -H "Authorization: Bearer $ORG_B_TOKEN" | jq '.products | [.[].name]'
```

## Frontend Testing (Manual)

### Browser Test 1: Two Organizations Side by Side
1. **Browser 1 (Chrome):** Login as Org A admin
   - Open http://localhost:5173
   - Login with `admin@org-a.com` / `testpass123`
   - Create a recipe
   - Note the recipes you can see

2. **Browser 2 (Firefox/Safari):** Login as Org B admin
   - Open http://localhost:5173
   - Login with `admin@org-b.com` / `testpass123`
   - Create a recipe
   - Verify you CANNOT see Org A's recipes

### Browser Test 2: User Management
1. Login as Org A admin
2. Go to Users page
3. Create a new user (chef or viewer role)
4. Verify the new user:
   - Can login
   - Belongs to Org A (same organization_id)
   - Can only see Org A's data

## Expected Results

### ✅ What Should Work:
- Each organization can create users, recipes, products, and common products
- Users can only see data from their own organization
- Direct access to another organization's resources returns 404
- Same product/recipe names can exist in different organizations
- JWT tokens correctly include organization_id

### ❌ What Should Fail (Security Tests):
- Org A accessing Org B's recipe by ID → 404 Not Found
- Org A listing recipes → should NOT include Org B's recipes
- Manipulating JWT token to change organization_id → 401 Unauthorized
- Accessing API without auth token → 401 Unauthorized

## Database Inspection

To verify data isolation at the database level:

```bash
# Check organizations
sqlite3 food_cost.db "SELECT id, name, slug FROM organizations;"

# Check users per organization
sqlite3 food_cost.db "SELECT id, username, email, organization_id FROM users ORDER BY organization_id;"

# Check recipes per organization
sqlite3 food_cost.db "SELECT id, name, organization_id FROM recipes ORDER BY organization_id;"

# Check common products per organization
sqlite3 food_cost.db "SELECT id, common_name, organization_id FROM common_products ORDER BY organization_id;"
```

## Troubleshooting

### Issue: "Setup already completed" error
**Solution:** Database already has users. Either:
1. Use existing admin credentials to login
2. Delete `food_cost.db` to start fresh
3. Create second org manually using SQL

### Issue: JWT token not working
**Solution:**
1. Check token hasn't expired (24 hour lifetime)
2. Verify token format: `Authorization: Bearer <token>`
3. Check server logs for auth errors

### Issue: Can see other organization's data
**Solution:** This is a security bug!
1. Check API route has `current_user: dict = Depends(get_current_user)`
2. Verify SQL query filters by `organization_id`
3. Check JWT token includes correct `organization_id`

### Issue: Cannot create second organization
**Solution:**
1. Initial setup endpoint only creates first org
2. Use SQL to manually create second org for testing
3. Future enhancement: Add organization signup endpoint

## Current Limitations

1. **Organization Creation:** Only one organization can be created via `/auth/setup`. Additional organizations must be created manually in the database for testing.

2. **Units & Distributors:** These may be global (shared across all organizations) or organization-scoped depending on requirements. Currently need to verify.

3. **Uploads Router:** Not yet updated with organization filtering (on the todo list).

## Next Steps

After verifying multi-tenancy works:
1. Deploy to dev environment
2. Test with production PostgreSQL database
3. Build organization signup UI
4. Implement tier limits enforcement
5. Create enhanced admin panel

## Support

If tests fail or you encounter issues:
1. Check API server logs for errors
2. Verify database schema with Alembic migrations
3. Inspect JWT tokens at https://jwt.io
4. Review the API route implementations in `api/app/routers/`
