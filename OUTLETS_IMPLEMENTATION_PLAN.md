# Multi-Outlet Support - Implementation Plan

**Date:** December 12, 2025
**Status:** Planning
**Priority:** HIGH - Core competitive differentiator

## Business Case

### The Problem
Multi-outlet organizations (hotels, restaurant groups, catering companies) currently face:
- **No outlet isolation** - Room Service chef sees/edits Main Dining recipes (chaos)
- **Massive product lists** - 5,000+ products from all outlets mixed together
- **No hierarchical access** - Can't give Executive Chef full visibility while restricting outlet chefs
- **Competitor weakness** - SaaS companies either force flat lists or require separate subscriptions per outlet

### The Solution
**Best of both worlds:**
- ✅ Outlet-specific products and recipes (isolation)
- ✅ Org-wide shared common product library (consistency)
- ✅ Hierarchical user access (corporate + outlet levels)
- ✅ Single subscription for entire organization
- ✅ Cross-outlet visibility for leadership
- ✅ Consolidated reporting and analytics

### Competitive Advantage
This is a **killer feature** for enterprise/hotel group sales that current SaaS platforms don't handle well.

---

## Architecture Design

### Data Model

```
Organization (e.g., Fairmont Hotel)
│
├── Common Products (ORG-WIDE, SHARED)
│   ├── "Red Onion"
│   ├── "Chicken Breast 6oz"
│   └── "Olive Oil, Extra Virgin"
│
├── Outlets (ORGANIZATION-SPECIFIC)
│   ├── Main Dining Room
│   │   ├── Products (outlet-specific, map to shared common products)
│   │   └── Recipes (outlet-specific, use shared common products)
│   ├── Banqueting
│   │   ├── Products
│   │   └── Recipes
│   ├── Room Service
│   │   ├── Products
│   │   └── Recipes
│   └── Pool Bar
│       ├── Products
│       └── Recipes
│
└── Users (with outlet access)
    ├── Executive Chef (access to ALL outlets)
    ├── F&B Director (access to ALL outlets)
    ├── Main Dining Chef (access to Main Dining only)
    ├── Banquet Chef (access to Banqueting only)
    └── Sous Chef (access to Main Dining AND Banqueting)
```

### Key Principles

1. **Outlets are optional** - Small orgs can skip outlets entirely
2. **Users can belong to multiple outlets** - Many-to-many relationship
3. **Products are outlet-specific** - Each outlet manages their own distributor imports
4. **Common products are org-wide** - Shared ingredient library across all outlets
5. **Recipes are outlet-specific** - But use shared common products
6. **Tier limits apply to organization** - Aggregate across all outlets

---

## Database Schema Changes

### New Tables

**outlets**
```sql
CREATE TABLE outlets (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),  -- Optional: "2nd Floor", "Building A"
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_outlets_organization FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX idx_outlets_organization ON outlets(organization_id);
```

**user_outlets** (many-to-many junction table)
```sql
CREATE TABLE user_outlets (
    user_id INTEGER NOT NULL REFERENCES users(id),
    outlet_id INTEGER NOT NULL REFERENCES outlets(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, outlet_id)
);

CREATE INDEX idx_user_outlets_user ON user_outlets(user_id);
CREATE INDEX idx_user_outlets_outlet ON user_outlets(outlet_id);
```

### Modified Tables

**Add outlet_id to existing tables:**
```sql
-- Products (outlet-specific)
ALTER TABLE products ADD COLUMN outlet_id INTEGER REFERENCES outlets(id);
CREATE INDEX idx_products_outlet ON products(outlet_id);

-- Recipes (outlet-specific)
ALTER TABLE recipes ADD COLUMN outlet_id INTEGER REFERENCES outlets(id);
CREATE INDEX idx_recipes_outlet ON recipes(outlet_id);

-- Distributor Products (outlet-specific)
ALTER TABLE distributor_products ADD COLUMN outlet_id INTEGER REFERENCES outlets(id);
CREATE INDEX idx_distributor_products_outlet ON distributor_products(outlet_id);

-- Import Batches (outlet-specific)
ALTER TABLE import_batches ADD COLUMN outlet_id INTEGER REFERENCES outlets(id);
CREATE INDEX idx_import_batches_outlet ON import_batches(outlet_id);

-- Common products remain ORG-WIDE (no outlet_id needed)
```

---

## Permission & Access Logic

### User Access Levels

**1. Org-wide Admin (no outlet assignments)**
- User has NO entries in `user_outlets` table
- Sees ALL outlets in their organization
- Can switch between outlets or view "All Outlets"
- Full CRUD on all outlets

**2. Outlet-scoped User (assigned to specific outlets)**
- User has entries in `user_outlets` table
- Sees ONLY their assigned outlets
- Can switch between assigned outlets if multiple
- CRUD limited to their outlets

**3. Multi-outlet User (assigned to multiple outlets)**
- User assigned to 2+ outlets via `user_outlets`
- Can switch between assigned outlets
- Sees aggregated view of assigned outlets

### Query Filtering Logic

```python
def get_user_outlet_filter(current_user):
    """Generate SQL filter for outlet-scoped queries."""

    # Check if user has outlet assignments
    user_outlets = query("""
        SELECT outlet_id FROM user_outlets WHERE user_id = %s
    """, (current_user["id"],))

    if not user_outlets:
        # Org-wide admin - sees all outlets in org
        return f"organization_id = {current_user['organization_id']}", []
    else:
        # Outlet-scoped - sees only assigned outlets
        outlet_ids = [row["outlet_id"] for row in user_outlets]
        return f"organization_id = {current_user['organization_id']} AND outlet_id IN %s", [tuple(outlet_ids)]

# Usage in endpoints
@router.get("/products")
def list_products(current_user: dict = Depends(get_current_user)):
    where_clause, params = get_user_outlet_filter(current_user)
    query = f"SELECT * FROM products WHERE {where_clause}"
    # ...
```

---

## Recipe Costing with Outlets

### Pricing Resolution Logic

When calculating recipe cost, price comes from **outlet-specific products** that map to the common product:

```python
def get_price_for_ingredient(recipe_id, common_product_id):
    """Get price for common product in context of recipe's outlet."""

    # 1. Get recipe's outlet
    recipe = get_recipe(recipe_id)
    outlet_id = recipe["outlet_id"]

    # 2. Find products in this outlet mapped to this common product
    products = query("""
        SELECT p.*, ph.price, ph.effective_date
        FROM products p
        JOIN price_history ph ON p.id = ph.product_id
        WHERE p.outlet_id = %s
          AND p.common_product_id = %s
          AND p.is_active = 1
        ORDER BY ph.effective_date DESC
        LIMIT 1
    """, (outlet_id, common_product_id))

    if not products:
        return None  # No product mapped in this outlet

    return products[0]["price"]
```

### Edge Cases

**Multiple products map to same common product:**
- Use most recent price (latest effective_date)
- Future: Allow user to select "preferred distributor"

**No product mapped in outlet:**
- Recipe shows "Price unavailable - no product mapped"
- Prompts user to import/map product

**Cross-outlet recipe copying:**
- Recipe copied from Main Dining → Banqueting
- Automatically uses Banqueting's product pricing
- May show different total cost due to different distributor prices

---

## Implementation Phases

### Phase 1: Database & Backend Foundation
**Goal:** Add outlets infrastructure without breaking existing functionality

**Tasks:**
1. Create Alembic migration
   - Add `outlets` table
   - Add `user_outlets` junction table
   - Add `outlet_id` to products, recipes, distributor_products, import_batches
   - Create indexes

2. Data migration script
   - For existing orgs: create "Default Outlet"
   - Assign all existing products/recipes to default outlet
   - All existing users get access to default outlet

3. Update backend models & schemas
   - Add Outlet model (SQLAlchemy)
   - Add OutletCreate, OutletUpdate, OutletResponse schemas
   - Update existing schemas to include outlet_id

4. Create outlets router (`api/app/routers/outlets.py`)
   - `GET /outlets` - List outlets in user's org
   - `POST /outlets` - Create outlet (admin only)
   - `GET /outlets/{id}` - Get outlet details
   - `PATCH /outlets/{id}` - Update outlet (admin only)
   - `DELETE /outlets/{id}` - Soft delete outlet (admin only)
   - `GET /outlets/{id}/stats` - Usage stats for outlet

5. Update auth utilities
   - Add `get_user_outlets(user_id)` helper
   - Add `check_outlet_access(user, outlet_id)` helper
   - Add outlet filtering to `get_current_user`

6. Update all existing routers with outlet filtering
   - products.py - filter by user's outlets
   - recipes.py - filter by user's outlets
   - uploads.py - assign imports to outlet
   - common_products.py - NO filtering (org-wide)

7. Testing
   - Create test org with multiple outlets
   - Verify data isolation
   - Test org-wide admin vs outlet-scoped users

**Deliverable:** Backend fully supports outlets, existing orgs continue working with "Default Outlet"

---

### Phase 2: Outlet Management UI
**Goal:** Allow admins to create/manage outlets and assign users

**Tasks:**
1. Create Outlets management page (`/outlets`)
   - List all outlets in organization
   - Create new outlet modal
   - Edit outlet details
   - Delete/deactivate outlets
   - Show stats per outlet (users, products, recipes)

2. Update Users management page
   - Multi-select outlet assignment
   - Show user's assigned outlets in table
   - "All Outlets" badge for org-wide admins
   - Bulk assign users to outlets

3. Navigation updates
   - Outlet selector dropdown (if user has multiple outlets)
   - "All Outlets" view option for org-wide admins
   - Current outlet indicator in header
   - Persist outlet selection in localStorage

4. Update existing pages with outlet context
   - Products page - show current outlet filter
   - Recipes page - show current outlet filter
   - Import page - select target outlet for import

5. Outlet switching UX
   - Smooth transition when switching outlets
   - Clear visual indication of current outlet
   - Reload data when outlet changes

**Deliverable:** Full UI for outlet management and switching

---

### Phase 3: Multi-Outlet Features
**Goal:** Advanced features leveraging outlet architecture

**Tasks:**
1. Cross-outlet recipe copying
   - "Copy to Outlet" button on recipe view
   - Select target outlet(s)
   - Warning if target outlet missing mapped products
   - Automatically use target outlet's pricing

2. Consolidated reporting
   - "All Outlets" aggregate view
   - Compare costs between outlets
   - Total product usage across outlets
   - Most expensive/cheapest outlets

3. Shared recipe library (corporate recipes)
   - Flag recipes as "Corporate Standard"
   - Corporate recipes visible to all outlets (read-only)
   - Outlets can copy to customize
   - Version tracking for corporate updates

4. Outlet analytics dashboard
   - Recipe count by outlet
   - Product count by outlet
   - Cost trends by outlet
   - User activity by outlet

5. Product availability warnings
   - When viewing recipe, show which outlets have products mapped
   - Alert when copying recipe to outlet without products
   - Suggest similar products from target outlet

**Deliverable:** Rich multi-outlet features for enterprise users

---

### Phase 4: Super Admin Panel
**Goal:** Platform owner can manage all organizations and outlets

**Tasks:**
1. Create super admin role
   - New `is_super_admin` flag on users table
   - OR special `organization_id = NULL` for platform owners
   - Bypass organization filtering for super admins

2. Super admin dashboard (`/super-admin`)
   - List all organizations
   - Org stats (outlets, users, products, recipes)
   - System-wide analytics
   - Search/filter organizations

3. Organization management
   - Create new organizations
   - Edit organization details
   - Update subscription tiers
   - Activate/deactivate organizations
   - View usage against tier limits

4. Outlet management (cross-org)
   - View all outlets across all orgs
   - Create outlets for any org
   - Deactivate problematic outlets

5. User management (cross-org)
   - View all users across all orgs
   - Impersonate user for support
   - Reset passwords
   - Assign super admin role

6. System monitoring
   - Total users, orgs, outlets
   - Growth metrics
   - Storage usage
   - API usage stats

**Deliverable:** Complete SaaS admin panel for platform management

---

## Migration Strategy for Existing Organizations

### Scenario: Existing org with data, adding outlets

**Step 1: Automatic migration on deployment**
```sql
-- For each existing organization
INSERT INTO outlets (organization_id, name, location, is_active)
VALUES (org.id, 'Default Outlet', NULL, 1);

-- Update all products to use default outlet
UPDATE products
SET outlet_id = (SELECT id FROM outlets WHERE organization_id = products.organization_id LIMIT 1)
WHERE outlet_id IS NULL;

-- Same for recipes, distributor_products, import_batches
```

**Step 2: User notification**
- Email admins: "Multi-outlet support is now available!"
- In-app banner: "Your data is in 'Default Outlet'. Create outlets to organize."
- Link to outlets setup guide

**Step 3: Admin creates outlets**
- Admin goes to /outlets
- Creates "Main Dining", "Banqueting", etc.
- Assigns users to outlets
- Optionally moves products/recipes to correct outlets

### Backward Compatibility

- ✅ Existing orgs continue working with "Default Outlet"
- ✅ API queries with `outlet_id = NULL` fallback to first/default outlet
- ✅ Users with no outlet assignments see all outlets (org-wide admin)
- ✅ No breaking changes to existing workflows

---

## API Endpoint Changes

### New Endpoints

```
# Outlets
GET    /outlets                    # List outlets in user's org
POST   /outlets                    # Create outlet (admin)
GET    /outlets/{id}               # Get outlet details
PATCH  /outlets/{id}               # Update outlet (admin)
DELETE /outlets/{id}               # Delete outlet (admin)
GET    /outlets/{id}/stats         # Outlet usage stats

# User-Outlet Assignment
POST   /users/{id}/outlets         # Assign user to outlets (admin)
GET    /users/{id}/outlets         # Get user's outlets
DELETE /users/{id}/outlets/{outlet_id}  # Remove outlet access
```

### Modified Endpoints

All existing endpoints gain optional `?outlet_id=X` query param:

```
GET /products?outlet_id=5          # Filter to specific outlet
GET /recipes?outlet_id=5           # Filter to specific outlet
GET /products                      # Returns all outlets user has access to
```

---

## UI/UX Mockups

### Navigation with Outlet Selector

```
┌─────────────────────────────────────────────────────┐
│ RestauranTek                    [Main Dining ▼]  👤│
├─────────────────────────────────────────────────────┤
│  Home  Products  Recipes  Users  Outlets  Admin    │
└─────────────────────────────────────────────────────┘

Outlet Dropdown:
┌──────────────────────┐
│ ✓ Main Dining        │
│   Banqueting         │
│   Room Service       │
│   Pool Bar           │
├──────────────────────┤
│ 📊 All Outlets       │ (org-wide admins only)
└──────────────────────┘
```

### Outlets Management Page

```
┌─────────────────────────────────────────────────────┐
│ Outlets                           [+ Create Outlet] │
├─────────────────────────────────────────────────────┤
│                                                      │
│  📍 Main Dining Room              [Edit] [Delete]   │
│     2nd Floor, Main Building                        │
│     👥 5 users  |  📦 1,234 products  |  📖 89 recipes│
│                                                      │
│  📍 Banqueting                    [Edit] [Delete]   │
│     Conference Level                                │
│     👥 3 users  |  📦 456 products  |  📖 34 recipes │
│                                                      │
│  📍 Room Service                  [Edit] [Delete]   │
│     Kitchen Level B1                                │
│     👥 2 users  |  📦 234 products  |  📖 12 recipes │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### User Outlet Assignment

```
┌─────────────────────────────────────────────────────┐
│ Edit User: John Smith (Sous Chef)                  │
├─────────────────────────────────────────────────────┤
│  Email: john@fairmont.com                           │
│  Role:  Chef                                        │
│                                                      │
│  Outlet Access:                                     │
│  ☑ Main Dining Room                                 │
│  ☑ Banqueting                                       │
│  ☐ Room Service                                     │
│  ☐ Pool Bar                                         │
│                                                      │
│  ☐ Grant access to all outlets (Org Admin)         │
│                                                      │
│                           [Cancel]  [Save Changes]  │
└─────────────────────────────────────────────────────┘
```

---

## Testing Plan

### Unit Tests
- Outlet filtering logic
- User outlet access checks
- Price resolution for multi-outlet recipes
- Migration script (create default outlet)

### Integration Tests
- Create org → create outlets → assign users
- Import products to specific outlet
- Calculate recipe cost using outlet-specific pricing
- Cross-outlet recipe copying

### User Acceptance Testing
1. **Single outlet org** - Works like before (default outlet)
2. **Multi-outlet org** - Data properly isolated
3. **Org-wide admin** - Can see/manage all outlets
4. **Outlet-scoped user** - Can only see assigned outlet
5. **Multi-outlet user** - Can switch between assigned outlets

### Edge Cases
- Delete outlet with products/recipes → soft delete, warning
- Remove all user's outlet assignments → becomes org admin
- Copy recipe to outlet without mapped products → warning
- User tries to access outlet they're not assigned to → 403 error

---

## Success Metrics

### Phase 1 (Backend Foundation)
- ✅ Zero data loss during migration
- ✅ All existing orgs have "Default Outlet"
- ✅ API tests pass for outlet filtering
- ✅ No performance regression

### Phase 2 (Outlet Management UI)
- ✅ Admins can create outlets in < 30 seconds
- ✅ Users can switch outlets in < 2 clicks
- ✅ Clear visual indication of current outlet
- ✅ No UX confusion reported

### Phase 3 (Multi-Outlet Features)
- ✅ Recipe copying works 100% of time
- ✅ Consolidated reporting shows accurate data
- ✅ Org-wide admins save time with "All Outlets" view

### Phase 4 (Super Admin)
- ✅ Platform owner can manage all orgs efficiently
- ✅ Support tickets resolved faster with impersonation
- ✅ Tier upgrades/downgrades work correctly

---

## Risks & Mitigation

### Risk 1: Data Migration Complexity
**Risk:** Existing data might not migrate cleanly to outlets
**Mitigation:**
- Create "Default Outlet" for all existing orgs
- Extensive testing on dev environment first
- Backup before production migration

### Risk 2: Performance with Large Outlet Counts
**Risk:** Orgs with 50+ outlets might have slow queries
**Mitigation:**
- Proper indexing on outlet_id columns
- Pagination on outlet lists
- Caching for outlet metadata

### Risk 3: User Confusion
**Risk:** Users don't understand outlet concept
**Mitigation:**
- Clear onboarding tooltips
- Documentation and video guides
- In-app help text

### Risk 4: Complex Permission Logic
**Risk:** Bugs in outlet access control
**Mitigation:**
- Comprehensive test coverage
- Audit logging for outlet access
- Gradual rollout (beta flag for early adopters)

---

## Timeline Estimate

**Phase 1: Backend Foundation**
- Database migrations: 2 days
- Backend logic & routers: 3 days
- Testing & debugging: 2 days
- **Total: ~1 week**

**Phase 2: Outlet Management UI**
- Outlets CRUD pages: 2 days
- User assignment UI: 2 days
- Navigation & switching: 2 days
- Testing & polish: 1 day
- **Total: ~1 week**

**Phase 3: Multi-Outlet Features**
- Recipe copying: 1 day
- Reporting: 2 days
- Shared library: 2 days
- Testing: 1 day
- **Total: ~1 week**

**Phase 4: Super Admin Panel**
- Backend super admin logic: 2 days
- Super admin UI: 3 days
- Testing & security: 2 days
- **Total: ~1 week**

**Overall: ~4 weeks for full implementation**

---

## Open Questions

1. **Outlet deletion behavior:**
   - Hard delete or soft delete?
   - What happens to products/recipes in deleted outlet?
   - Move to another outlet or mark inactive?

2. **Shared vs outlet-specific common products:**
   - Are common products ALWAYS org-wide?
   - Or could outlets have outlet-specific common products too?
   - Current plan: Always org-wide (simpler)

3. **Outlet-level permissions:**
   - Just read/write, or more granular (view recipes, edit products)?
   - Current plan: Simple read/write based on outlet assignment

4. **Inter-outlet transfers:**
   - Can users move products/recipes between outlets?
   - Requires admin approval?
   - Current plan: Phase 3 feature

5. **Default outlet behavior:**
   - If user has no outlet assignments, are they org admin?
   - Or should we require explicit "all outlets" flag?
   - Current plan: No assignments = org admin

---

## Documentation & Training

### Developer Docs
- Database schema updates
- API endpoint changes
- Permission logic examples
- Migration guide

### User Docs
- "What are outlets?"
- "Creating and managing outlets"
- "Assigning users to outlets"
- "Working with multi-outlet organizations"

### Video Tutorials
- Admin: Setting up outlets
- Chef: Switching between outlets
- Corporate: Using "All Outlets" view
- Recipe copying across outlets

---

## Post-Launch Monitoring

### Metrics to Track
- Outlets created per organization
- User outlet assignments
- Recipe copies between outlets
- Performance of outlet-filtered queries
- Support tickets related to outlets

### Feedback Collection
- In-app survey for outlet users
- Admin feedback on management UI
- Performance complaints
- Feature requests

---

## Future Enhancements (Beyond Phase 4)

- **Outlet groups/regions** - Group outlets by geography or brand
- **Cross-outlet inventory** - Transfer stock between outlets
- **Outlet-level reporting** - P&L per outlet
- **Franchise mode** - Franchisees as separate sub-orgs
- **Menu sync** - Push corporate menu to all outlets
- **Outlet-specific branding** - Different logos/colors per outlet

---

**Next Steps:**
1. Review and approve this plan
2. Create Phase 1 implementation tasks
3. Set up dev environment for testing
4. Begin database migration development
