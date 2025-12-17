# Resume Here - December 12, 2025

## Quick Context

**Current State (as of Dec 11 EOD):**
- ✅ PostgreSQL migration COMPLETE and merged to main
- ✅ All core features working on both dev and production
- ✅ Clean, simplified codebase (39-line database.py)
- ✅ Single-tenant architecture (multi-tenancy removed)

**Branch:** `dev` (clean, ready for new features)

---

## Today's Goals

### 1. Multi-Tenancy Architecture
Add organization-based data isolation back, but properly designed this time.

**What to Add:**
- `organizations` table with tier system (free, basic, pro, enterprise)
- `organization_id` foreign keys on all user-scoped tables:
  - users
  - products
  - common_products
  - recipes
  - distributor_products
  - import_batches
- Organization-scoped queries (WHERE clauses)
- Tier-based limits (recipes, users, storage)

**What NOT to Add:**
- Don't touch distributors (shared)
- Don't touch units (shared)
- Don't overcomplicate with wrappers

**Approach:**
1. Create new Alembic migration for organizations table
2. Add organization_id columns with migrations
3. Update queries to filter by organization_id
4. Test with seed data (multiple orgs)

### 2. Admin Interface
Build organization management UI.

**Pages/Features:**
- Organization settings (name, tier, limits)
- User management (invite, roles, permissions)
- Usage stats (recipes count, users count)
- Tier limits display
- Billing/subscription hooks (future)

**Files to Create/Update:**
- `frontend/src/pages/Admin.jsx` (already exists, needs work)
- `api/app/routers/organizations.py` (already exists, needs update)
- New components for org management

---

## Key Documentation

### Read These First:
1. **POSTGRESQL_MIGRATION_DEC11.md** - What we accomplished yesterday
   - All the SQLite→PostgreSQL fixes
   - RealDictCursor patterns
   - cursor.lastrowid → RETURNING id
   - Boolean → integer conversions

2. **README.md** - Current project state
   - Tech stack
   - Database schema (current single-tenant)
   - How everything works

3. **TESTING_MULTI_TENANCY.md** - Previous multi-tenancy work
   - Has test scripts and examples
   - Shows what was attempted before

4. **PROJECT_CONTEXT.md** - Overall project vision

---

## Current Database Schema (Single-Tenant)

```sql
users
├── id, email, username, hashed_password
├── role (admin, chef, viewer)
└── No organization_id currently

products
├── id, name, brand, pack, size
├── unit_id, common_product_id
└── No organization_id currently

common_products
├── id, common_name, category
├── allergen_* fields (16 flags)
└── No organization_id currently

recipes
├── id, name, description, category
├── yield_amount, yield_unit_id
└── No organization_id currently
```

---

## What Needs to Change for Multi-Tenancy

### New Table: organizations
```sql
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    subscription_tier VARCHAR(20) DEFAULT 'free',  -- free, basic, pro, enterprise
    subscription_status VARCHAR(20) DEFAULT 'active',
    max_users INTEGER DEFAULT 2,
    max_recipes INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Add organization_id to:
```sql
ALTER TABLE users ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE products ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE common_products ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE recipes ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE distributor_products ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
ALTER TABLE import_batches ADD COLUMN organization_id INTEGER REFERENCES organizations(id);
```

### Update Queries:
```python
# Before (single-tenant):
cursor.execute("SELECT * FROM products WHERE is_active = 1")

# After (multi-tenant):
organization_id = current_user["organization_id"]
cursor.execute(
    "SELECT * FROM products WHERE is_active = 1 AND organization_id = %s",
    (organization_id,)
)
```

---

## Critical Patterns to Remember

### 1. Always Use Column Names with RealDictCursor
```python
# ✅ Correct:
result = cursor.fetchone()
id = result["id"]

# ❌ Wrong:
id = result[0]  # Will throw KeyError
```

### 2. Always Use RETURNING id for INSERTs
```python
# ✅ Correct:
cursor.execute("""
    INSERT INTO products (...) VALUES (%s)
    RETURNING id
""", (data,))
product_id = cursor.fetchone()["id"]

# ❌ Wrong:
product_id = cursor.lastrowid  # Returns 0 in PostgreSQL
```

### 3. Always Use Trailing Comma for Single-Item Tuples
```python
# ✅ Correct:
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

# ❌ Wrong:
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id))  # Passes int, not tuple
```

### 4. Convert Booleans to Integers for PostgreSQL
```python
# ✅ Correct:
cursor.execute("INSERT INTO products (is_catch_weight) VALUES (%s)", (int(is_catch_weight),))

# ❌ Wrong:
cursor.execute("INSERT INTO products (is_catch_weight) VALUES (%s)", (is_catch_weight,))
# Error: column is type integer but expression is type boolean
```

---

## Git Workflow for Today

```bash
# Already on dev branch
git status  # Should be clean

# Create feature branch
git checkout -b feature/multi-tenancy-admin

# Make changes, commit frequently
git add .
git commit -m "feat: Add organizations table and migrations"

# Push to dev for testing
git push origin feature/multi-tenancy-admin

# Or work directly on dev if preferred
```

---

## Testing Plan

### 1. Database Migration Testing
```bash
# Create migration
venv/bin/alembic revision --autogenerate -m "Add multi-tenancy support"

# Review generated migration carefully
# Edit if needed (ensure column names match)

# Test upgrade
venv/bin/alembic upgrade head

# Test rollback
venv/bin/alembic downgrade -1
venv/bin/alembic upgrade head
```

### 2. Seed Test Data
Create multiple organizations with different users:
```python
# Org 1: Free tier (2 users, 5 recipes)
# Org 2: Pro tier (10 users, unlimited recipes)
# Test data isolation between orgs
```

### 3. API Testing
Use `/docs` endpoint to test:
- User can only see their org's data
- Admin can manage org settings
- Tier limits are enforced

### 4. Frontend Testing
- Login as different org users
- Verify data isolation
- Test admin interface

---

## Files to Focus On

### Backend:
- `alembic/versions/002_add_multi_tenancy.py` (create new)
- `api/app/models.py` (add Organization model)
- `api/app/schemas.py` (add organization schemas)
- `api/app/routers/organizations.py` (update/complete)
- `api/app/routers/auth.py` (add organization_id to tokens)
- `api/app/routers/products.py` (add org filters)
- `api/app/routers/common_products.py` (add org filters)
- `api/app/routers/recipes.py` (add org filters)
- `api/app/routers/uploads.py` (add org scoping)

### Frontend:
- `frontend/src/pages/Admin.jsx` (organization management)
- `frontend/src/context/AuthContext.jsx` (add organization to user state)
- Add organization selector if needed

---

## Quick Reference Commands

```bash
# Start backend
cd api && ../venv/bin/uvicorn app.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Create migration
venv/bin/alembic revision --autogenerate -m "Description"

# Run migrations
venv/bin/alembic upgrade head

# Check current migration
venv/bin/alembic current

# View git changes
git status
git diff

# Test on dev environment (push to dev branch)
git push origin dev
# Watch https://food-cost-tracker-dev.onrender.com
```

---

## Potential Gotchas

1. **Don't forget organization_id in WHERE clauses**
   - Every query needs org scoping
   - Easy to miss in complex joins

2. **Shared vs Scoped Tables**
   - distributors: SHARED (no org_id)
   - units: SHARED (no org_id)
   - products, recipes, users: SCOPED (needs org_id)

3. **UNIQUE Constraints**
   - May need to add organization_id to UNIQUE indexes
   - Example: (organization_id, distributor_id, distributor_sku) UNIQUE

4. **JWT Token Changes**
   - Must include organization_id in JWT payload
   - Update TokenData schema
   - Update create_access_token calls

5. **Initial Setup Flow**
   - /auth/setup creates first org AND first admin user
   - Need both for initial login

---

## Success Criteria for Today

- [ ] Organizations table created with migration
- [ ] All tables have organization_id foreign keys
- [ ] Auth system includes organization_id in JWT
- [ ] All queries filter by organization_id
- [ ] Admin interface shows org settings
- [ ] Can create multiple orgs and verify data isolation
- [ ] Tier limits enforced (at least basic validation)
- [ ] All tests pass on dev environment

---

## When You're Done

1. Test thoroughly on dev environment
2. Document any new patterns/gotchas
3. Push to dev, verify deployment
4. Tomorrow: Merge to main if all working

---

**You're all set! The codebase is clean, documented, and ready for multi-tenancy. Good luck! 🚀**
