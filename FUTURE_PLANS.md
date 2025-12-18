# Future Plans: Scaling RestauranTek Platform

**Date:** December 17, 2024
**Status:** Planning Document
**Timeline:** Post-MVP (After Food Cost Tracking MVP Complete)

---

## Overview

This document outlines the technical strategy for scaling RestauranTek from a single-module application (Food Cost Tracking) to a multi-module platform (Food Cost + HACCP + future modules).

**Key Goals:**
1. Add new modules (HACCP, Inventory, Labor, etc.) without disrupting existing users
2. Maintain stability in production while developing experimental features
3. Enable per-organization feature access based on subscription tier
4. Keep codebase maintainable and modular

---

## Food Cost Tracker - Post-MVP Enhancements

Before starting new modules, complete these high-priority enhancements to the Food Cost Tracking module.

### AI Recipe Parser (High Priority)

**Goal:** Automate recipe ingredient entry by parsing Word/PDF documents using Claude API.

**MVP Scope - Ingredients Only:**
- Parse Word/PDF recipe files
- Extract: ingredient name, quantity, unit
- Match to common products in DB (show top 3 matches)
- Set yield % to 100% (user adjusts manually)
- User reviews/confirms before import
- Method steps parsing = future enhancement

**Technical Approach:**

1. **Backend Endpoint:** `POST /api/recipes/parse-file`
2. **File Processing:**
   - Use `python-docx` for Word files
   - Use `pypdf` for PDF text extraction
3. **AI Processing:**
   - Send extracted text to Claude API (Anthropic)
   - Claude returns structured JSON with ingredients
4. **Product Matching:**
   - Backend queries DB for matching common products
   - If uncertain, suggest top 3 product matches
5. **User Review:**
   - Frontend shows confirmation dialog
   - User selects correct matches or creates new products

**File Upload Flow:**
```
Upload Word/PDF → Extract text → Claude API parses →
Backend suggests matches → User reviews → Import ingredients
```

**Claude API Prompt Structure:**
```json
{
  "name": "recipe name",
  "yield": {"quantity": 2, "unit": "quart"},
  "servings": {"quantity": 8, "unit": "portions"},
  "ingredients": [
    {
      "name": "cucumber",
      "quantity": 10,
      "unit": "LB",
      "prep_note": "sliced"
    }
  ]
}
```

**AI Matching Logic:**
- If AI is uncertain, show top 3 product matches
- User selects correct match from dropdown
- If no match, user can search all products or create new
- Fuzzy matching algorithm for common product suggestions

**Cost Estimate:**
- ~$0.005-$0.02 per recipe parse (Claude API)
- Free tier: 10 parses/month (~$0.20/month max)
- Paid tier: Unlimited (even 100/month = ~$2)
- Very affordable for the value provided

**Dependencies:**
- Anthropic API key (console.anthropic.com)
- `python-docx` package
- `pypdf` package

**Testing Strategy:**
- Test with various recipe formats (formal recipes, notes, scanned PDFs)
- Verify product matching accuracy
- Handle edge cases (missing quantities, unusual units)
- User acceptance testing with real recipes

---

### Advanced Features (Phase 6)

**Recipe Features:**
- [ ] Recipe search (name, ingredients, allergens)
- [ ] Bulk operations (tag recipes, batch move)
- [ ] Recipe templates for common prep items
- [ ] Print/export recipe cards (PDF)
- [ ] Recipe history/versioning (track changes over time)
- [ ] Yield scaling (adjust quantities up/down)
- [ ] Shopping list generation from recipes
- [ ] Price trend charts per recipe (show cost over time)
- [ ] Batch cost comparison (compare multiple recipes)
- [ ] Unit conversions (automatic weight/volume conversion)

**Product Features:**
- [ ] Manual product entry form (instead of CSV only)
- [ ] Price history view per product (chart over time)
- [ ] Product merge/deduplication tool
- [ ] Bulk product editing (batch operations)
- [ ] Product categories and tagging
- [ ] Favorite/frequently used products

**Tech Debt & Improvements:**
- [ ] **Virtual Folders:** Move from localStorage to database table for multi-device sync
  - Currently: Virtual folders stored in browser localStorage (client-side only)
  - Future: Create `folders` table with columns: id, path, created_at
  - Benefits: Syncs across devices, survives cache clear, proper data persistence
- [ ] Add loading states for all async operations
- [ ] Implement proper error handling with user feedback
- [ ] Add data validation (client + server)
- [ ] Optimize tree rendering for large datasets
- [ ] Add keyboard shortcuts (save, cancel, etc.)
- [ ] Implement undo/redo for recipe editing
- [ ] Add autosave with drafts
- [ ] Improve mobile responsiveness
- [ ] Add comprehensive test coverage

**Prioritization:**
1. **Immediate (Week 1-2):** AI Recipe Parser
2. **High Priority:** Recipe scaling, shopping lists, price trend charts
3. **Medium Priority:** Recipe search, versioning, PDF export
4. **Polish:** Bulk operations, templates, unit conversions

---

## Branching Strategy Evolution

### Current State (Food Cost MVP)
```
main (production)
  └── dev (development)
      ├── feature/* (short-lived)
      └── fix/* (short-lived)
```

**Why This Works Now:**
- Single cohesive module
- Fast iteration needed
- Breaking changes acceptable during MVP
- Two branches keeps it simple

**Keep this until Food Cost MVP is complete.**

### Future State (Multi-Module Development)

When starting HACCP module development, implement the **Three-Branch System**:

```
main (production - food-cost-tracker.onrender.com)
  ├── staging (pre-production - food-cost-tracker-staging.onrender.com)
      ├── dev (development - food-cost-tracker-dev.onrender.com)
          ├── feature/temperature-monitoring
          ├── feature/haccp-checklist
          ├── feature/email-notifications
          ├── fix/food-cost-bug
          └── hotfix/critical-security-issue
```

#### Branch Purposes

**`main` - Production**
- Always stable and deployable
- Real customers use this
- Only merge from `staging` after thorough testing
- Manual deploys only (no auto-deploy)

**`staging` - Pre-Production Testing**
- Final testing before production release
- Exact replica of production environment
- Test all modules working together
- Integration testing happens here

**`dev` - Active Development**
- New features, experiments, rapid iteration
- HACCP module development happens here
- Food Cost bug fixes tested here
- Auto-deploys for fast feedback

#### Workflow Examples

**Adding a New HACCP Feature:**
```bash
# 1. Create feature branch from dev
git checkout dev
git pull origin dev
git checkout -b feature/temperature-monitoring

# 2. Develop and test locally
# ... make changes ...
git add .
git commit -m "feat: Add temperature monitoring UI"

# 3. Merge to dev for testing in dev environment
git checkout dev
git merge feature/temperature-monitoring
git push origin dev
# Auto-deploys to dev.onrender.com for testing

# 4. When stable, promote to staging
git checkout staging
git merge dev
git push origin staging
# Deploys to staging.onrender.com for final testing

# 5. After approval, promote to production
git checkout main
git merge staging
git push origin main
# Manual deploy to production
```

**Fixing a Food Cost Bug:**
```bash
# 1. Create fix branch from dev
git checkout -b fix/outlet-selector-crash dev

# 2. Fix the bug
# ... make changes ...
git commit -m "fix: Prevent crash when outlet has no products"

# 3. Merge to dev and test
git checkout dev
git merge fix/outlet-selector-crash
git push origin dev

# 4. If urgent, fast-track through staging to main
git checkout staging
git merge dev
git push origin staging

git checkout main
git merge staging
git push origin main
```

**Critical Production Hotfix:**
```bash
# 1. Branch from main (production)
git checkout main
git pull origin main
git checkout -b hotfix/payment-failure

# 2. Fix quickly
# ... emergency fix ...
git commit -m "hotfix: Fix payment processing error"

# 3. Deploy to main immediately
git checkout main
git merge hotfix/payment-failure
git push origin main
# Deploy to production NOW

# 4. Back-merge to staging and dev
git checkout staging
git merge main
git push origin staging

git checkout dev
git merge main
git push origin dev
```

#### Branch Protection Rules

Configure on GitHub:

**`main` (Production):**
- ✅ Require pull request reviews before merging
- ✅ Require status checks to pass (when CI/CD added)
- ✅ Prevent force pushes
- ✅ Prevent deletion
- ⚠️ Require approval from code owner (you)

**`staging` (Pre-Production):**
- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Prevent force pushes
- ✅ Prevent deletion

**`dev` (Development):**
- ⚠️ No restrictions - allow fast iteration
- ✅ Prevent deletion only

---

## Module Architecture

### Frontend Structure

Organize code by module for clear separation:

```
frontend/src/
  ├── modules/
  │   ├── food-cost/              # Food Cost Tracking Module
  │   │   ├── pages/
  │   │   │   ├── Products.jsx
  │   │   │   ├── Recipes.jsx
  │   │   │   └── PriceHistory.jsx
  │   │   ├── components/
  │   │   │   ├── ProductForm.jsx
  │   │   │   ├── RecipeCalculator.jsx
  │   │   │   └── IngredientList.jsx
  │   │   └── hooks/
  │   │       ├── useProducts.js
  │   │       └── useRecipes.js
  │   │
  │   ├── haccp/                  # HACCP Module (Future)
  │   │   ├── pages/
  │   │   │   ├── TemperatureLog.jsx
  │   │   │   ├── HaccpChecklist.jsx
  │   │   │   └── CorrectiveActions.jsx
  │   │   ├── components/
  │   │   │   ├── TemperatureEntry.jsx
  │   │   │   ├── ChecklistItem.jsx
  │   │   │   └── AlertNotification.jsx
  │   │   └── hooks/
  │   │       ├── useTemperatureLogs.js
  │   │       └── useChecklists.js
  │   │
  │   ├── inventory/              # Inventory Module (Future)
  │   │   └── ...
  │   │
  │   └── labor/                  # Labor Management Module (Future)
  │       └── ...
  │
  ├── shared/                     # Shared Across All Modules
  │   ├── components/
  │   │   ├── Navigation.jsx
  │   │   ├── OutletSelector.jsx
  │   │   └── UserMenu.jsx
  │   ├── contexts/
  │   │   ├── AuthContext.jsx
  │   │   └── OutletContext.jsx
  │   ├── hooks/
  │   │   ├── useAuth.js
  │   │   └── usePermissions.js
  │   └── utils/
  │       ├── formatters.js
  │       └── validators.js
  │
  ├── pages/
  │   ├── Home.jsx                # Module selector / dashboard
  │   ├── Login.jsx
  │   └── Admin.jsx
  │
  └── App.jsx
```

**Benefits:**
- Clear ownership: "HACCP team works in `modules/haccp/`"
- No conflicts: Food Cost changes don't affect HACCP code
- Easier testing: Can test modules independently
- Code reuse: Shared components prevent duplication
- Future-proof: Easy to add more modules

### Backend Structure

```
api/app/
  ├── routers/
  │   ├── food_cost/              # Food Cost Endpoints
  │   │   ├── products.py
  │   │   ├── recipes.py
  │   │   └── price_history.py
  │   │
  │   ├── haccp/                  # HACCP Endpoints (Future)
  │   │   ├── temperature_logs.py
  │   │   ├── checklists.py
  │   │   └── corrective_actions.py
  │   │
  │   ├── shared/                 # Shared Endpoints
  │   │   ├── auth.py
  │   │   ├── users.py
  │   │   ├── outlets.py
  │   │   └── organizations.py
  │   │
  │   └── super_admin.py
  │
  ├── models/                     # Database models by module
  │   ├── food_cost.py
  │   ├── haccp.py
  │   └── shared.py
  │
  └── services/                   # Business logic by module
      ├── food_cost/
      ├── haccp/
      └── shared/
```

### Database Schema

Keep modules separate but share core infrastructure:

```sql
-- ============================================
-- SHARED TABLES (All Modules)
-- ============================================
users
organizations
organization_features       -- NEW: Feature flag system
outlets
audit_logs

-- ============================================
-- FOOD COST MODULE
-- ============================================
products
recipes
recipe_ingredients
distributors
price_history
outlet_stats

-- ============================================
-- HACCP MODULE (Future)
-- ============================================
temperature_logs
temperature_zones
haccp_checklists
checklist_items
checklist_completions
corrective_actions

-- ============================================
-- INVENTORY MODULE (Future)
-- ============================================
inventory_items
inventory_counts
inventory_adjustments
par_levels

-- ============================================
-- LABOR MODULE (Future)
-- ============================================
employees
schedules
time_punches
labor_costs
```

---

## Feature Flag System

**Problem:** You want to deploy HACCP code to production but only enable it for specific organizations (beta testers, paid tiers, etc.)

**Solution:** Feature flags at the organization level.

### Implementation

#### 1. Create Database Table

```sql
CREATE TABLE organization_features (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    feature_name VARCHAR(50) NOT NULL,  -- 'food_cost', 'haccp', 'inventory', etc.
    enabled BOOLEAN DEFAULT FALSE,
    enabled_at TIMESTAMP,
    disabled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(organization_id, feature_name)
);

CREATE INDEX idx_org_features_org_id ON organization_features(organization_id);
CREATE INDEX idx_org_features_feature ON organization_features(feature_name);
```

#### 2. Backend Helper Function

```python
# api/app/features.py

def has_feature(organization_id: int, feature_name: str) -> bool:
    """
    Check if an organization has access to a specific feature.

    Args:
        organization_id: The organization's ID
        feature_name: Feature to check ('food_cost', 'haccp', 'inventory', etc.)

    Returns:
        True if enabled, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT enabled
            FROM organization_features
            WHERE organization_id = %s AND feature_name = %s
        """, (organization_id, feature_name))

        result = cursor.fetchone()
        return result["enabled"] if result else False


def enable_feature(organization_id: int, feature_name: str):
    """Enable a feature for an organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO organization_features (organization_id, feature_name, enabled, enabled_at)
            VALUES (%s, %s, TRUE, NOW())
            ON CONFLICT (organization_id, feature_name)
            DO UPDATE SET enabled = TRUE, enabled_at = NOW()
        """, (organization_id, feature_name))
        conn.commit()


def disable_feature(organization_id: int, feature_name: str):
    """Disable a feature for an organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE organization_features
            SET enabled = FALSE, disabled_at = NOW()
            WHERE organization_id = %s AND feature_name = %s
        """, (organization_id, feature_name))
        conn.commit()
```

#### 3. Use in API Endpoints

```python
# api/app/routers/haccp/temperature_logs.py

from fastapi import APIRouter, Depends, HTTPException
from ...features import has_feature
from ...auth import get_current_user

router = APIRouter(prefix="/haccp", tags=["haccp"])

@router.get("/temperature-logs")
def get_temperature_logs(current_user: dict = Depends(get_current_user)):
    # Check if organization has HACCP module enabled
    if not has_feature(current_user["organization_id"], "haccp"):
        raise HTTPException(
            status_code=403,
            detail="HACCP module not enabled for your organization. Please upgrade your subscription."
        )

    # Proceed with normal logic
    # ... fetch temperature logs ...
```

#### 4. Use in Frontend

```javascript
// frontend/src/contexts/FeaturesContext.jsx

import { createContext, useContext, useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import axios from '../lib/axios';

const FeaturesContext = createContext();

export function FeaturesProvider({ children }) {
  const { user } = useAuth();
  const [features, setFeatures] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      fetchFeatures();
    }
  }, [user]);

  const fetchFeatures = async () => {
    try {
      const response = await axios.get('/organizations/features');
      setFeatures(response.data);
    } catch (error) {
      console.error('Error fetching features:', error);
    } finally {
      setLoading(false);
    }
  };

  const hasFeature = (featureName) => {
    return features.some(f => f.feature_name === featureName && f.enabled);
  };

  return (
    <FeaturesContext.Provider value={{ features, hasFeature, loading }}>
      {children}
    </FeaturesContext.Provider>
  );
}

export const useFeatures = () => useContext(FeaturesContext);
```

```jsx
// frontend/src/components/Navigation.jsx

import { useFeatures } from '../contexts/FeaturesContext';

function Navigation() {
  const { hasFeature } = useFeatures();

  return (
    <nav>
      {/* Food Cost - Always visible */}
      <Link to="/products">Products</Link>
      <Link to="/recipes">Recipes</Link>

      {/* HACCP - Only if enabled */}
      {hasFeature('haccp') && (
        <>
          <Link to="/haccp/temperature-logs">Temperature Logs</Link>
          <Link to="/haccp/checklists">HACCP Checklists</Link>
        </>
      )}

      {/* Inventory - Only if enabled */}
      {hasFeature('inventory') && (
        <Link to="/inventory">Inventory</Link>
      )}
    </nav>
  );
}
```

#### 5. Subscription Tier Mapping

Automatically enable features based on subscription tier:

```python
# When creating or updating organization subscription

TIER_FEATURES = {
    "free": ["food_cost"],
    "basic": ["food_cost", "haccp"],
    "pro": ["food_cost", "haccp", "inventory"],
    "enterprise": ["food_cost", "haccp", "inventory", "labor", "analytics"]
}

def update_organization_subscription(org_id: int, new_tier: str):
    # Update subscription tier
    # ...

    # Update feature access based on tier
    enabled_features = TIER_FEATURES.get(new_tier, ["food_cost"])

    for feature in enabled_features:
        enable_feature(org_id, feature)

    # Optionally disable features not in new tier
    all_features = ["food_cost", "haccp", "inventory", "labor", "analytics"]
    for feature in all_features:
        if feature not in enabled_features:
            disable_feature(org_id, feature)
```

---

## Navigation & Module Selection

### Home Page as Module Selector

```jsx
// frontend/src/pages/Home.jsx

import { useFeatures } from '../contexts/FeaturesContext';

export default function Home() {
  const { hasFeature } = useFeatures();
  const { user } = useAuth();

  return (
    <div className="module-selector">
      <h1>Welcome to RestauranTek, {user.organization_name}</h1>
      <p>Select a module to get started:</p>

      <div className="module-grid">
        {/* Food Cost - Always available */}
        <ModuleCard
          title="Food Cost Tracker"
          icon="📊"
          description="Track ingredient prices, calculate recipe costs, and monitor margins"
          link="/products"
          enabled={true}
        />

        {/* HACCP - Conditional */}
        <ModuleCard
          title="HACCP Manager"
          icon="🌡️"
          description="Temperature monitoring, checklists, and compliance tracking"
          link="/haccp/temperature-logs"
          enabled={hasFeature('haccp')}
          upgradeMessage="Available on Basic plan and higher"
        />

        {/* Inventory - Conditional */}
        <ModuleCard
          title="Inventory Management"
          icon="📦"
          description="Track inventory levels, counts, and automated ordering"
          link="/inventory"
          enabled={hasFeature('inventory')}
          upgradeMessage="Available on Pro plan and higher"
        />

        {/* Labor - Conditional */}
        <ModuleCard
          title="Labor Management"
          icon="👥"
          description="Scheduling, time tracking, and labor cost optimization"
          link="/labor"
          enabled={hasFeature('labor')}
          upgradeMessage="Available on Enterprise plan"
        />
      </div>
    </div>
  );
}

function ModuleCard({ title, icon, description, link, enabled, upgradeMessage }) {
  if (!enabled) {
    return (
      <div className="module-card disabled">
        <div className="module-icon">{icon}</div>
        <h3>{title}</h3>
        <p>{description}</p>
        <div className="upgrade-prompt">
          🔒 {upgradeMessage}
          <button className="btn-upgrade">Upgrade Plan</button>
        </div>
      </div>
    );
  }

  return (
    <Link to={link} className="module-card">
      <div className="module-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{description}</p>
      <button className="btn-primary">Open Module →</button>
    </Link>
  );
}
```

---

## Migration Path: Food Cost MVP → Multi-Module Platform

### Phase 1: Complete Food Cost MVP (Current)
- ✅ Finish core features
- ✅ Bug fixes and polish
- ✅ Deploy to production
- ✅ Get initial customers

**Branch Strategy:** `main` + `dev` (keep it simple)

### Phase 2: Prepare for Multi-Module (Before HACCP Development)

**Week 1: Infrastructure Setup**
1. Create `staging` branch
2. Set up `food-cost-tracker-staging.onrender.com`
3. Configure branch protection rules on GitHub
4. Update deployment docs

**Week 2: Feature Flag System**
1. Create `organization_features` table migration
2. Implement backend feature flag helpers
3. Create `FeaturesContext` in frontend
4. Enable `food_cost` feature for all existing organizations

**Week 3: Module Restructuring**
1. Reorganize frontend code into `modules/food-cost/`
2. Move shared components to `shared/`
3. Test thoroughly - no functional changes, just reorganization
4. Update imports across codebase

**Week 4: Testing & Documentation**
1. Test three-branch workflow
2. Document new processes for team
3. Create HACCP module plan
4. Ready to start HACCP development

### Phase 3: HACCP Module Development

**Development Process:**
1. All HACCP work happens in `feature/haccp-*` branches off `dev`
2. HACCP code deploys to dev environment but feature-flagged off
3. Enable HACCP feature for test organization only
4. Iterate rapidly without affecting Food Cost users

**Testing Process:**
1. Test in `dev` with HACCP enabled for test org
2. Promote to `staging` for final integration testing
3. Deploy to `main` but keep feature disabled for most orgs
4. Enable for beta testers, gather feedback
5. Enable for all Basic+ tier organizations when ready

### Phase 4: Future Modules

Repeat the process for Inventory, Labor, etc.

Each new module:
- Develops in feature branches off `dev`
- Gets feature-flagged
- Tests in isolation
- Promotes through staging → main
- Enables gradually for users

---

## Benefits of This Approach

### 1. **Safe Experimentation**
- Develop HACCP module without breaking Food Cost
- Can deploy incomplete features hidden behind flags
- Beta test with select customers before full rollout

### 2. **Independent Release Cycles**
- Fix Food Cost bugs and deploy immediately
- HACCP features can be in development for months
- Don't need to wait for one module to release another

### 3. **Better Code Organization**
- Clear module boundaries
- Easier to onboard new developers ("work on HACCP module")
- Reduced merge conflicts

### 4. **Flexible Monetization**
- Different subscription tiers get different modules
- Can enable features for specific customers
- Easy to run promotions (enable feature temporarily)

### 5. **Scalable Architecture**
- Adding new modules follows established pattern
- Database stays organized
- Frontend and backend both modular

---

## Technology Additions to Consider

### 1. **Lazy Loading Modules (Frontend Performance)**

```javascript
// App.jsx - Load modules on demand

const FoodCostModule = lazy(() => import('./modules/food-cost'));
const HaccpModule = lazy(() => import('./modules/haccp'));
const InventoryModule = lazy(() => import('./modules/inventory'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/products/*" element={<FoodCostModule />} />
        <Route path="/haccp/*" element={<HaccpModule />} />
        <Route path="/inventory/*" element={<InventoryModule />} />
      </Routes>
    </Suspense>
  );
}
```

**Benefits:**
- Initial page load only downloads Food Cost code
- HACCP code loads only when user navigates to HACCP
- Faster app for users who only use one module

### 2. **CI/CD Pipeline**

When you're ready:
- GitHub Actions for automated testing
- Run tests on every pull request
- Auto-deploy `dev` branch to dev.onrender.com
- Require tests to pass before merging to `staging`

### 3. **Monitoring & Analytics**

Track module usage:
- Which modules are most used?
- Where do users get stuck?
- Which features drive upgrades?

Tools to consider:
- Sentry (error tracking)
- PostHog or Mixpanel (product analytics)
- LogRocket (session replay)

---

## Action Items

### Immediate (During Food Cost MVP)
- [ ] Nothing - focus on MVP
- [ ] Keep using `main` + `dev` branches

### When Ready to Start HACCP (Post-MVP)
- [ ] Create `staging` branch and Render environment
- [ ] Implement `organization_features` table
- [ ] Build feature flag system (backend + frontend)
- [ ] Reorganize code into modular structure
- [ ] Document three-branch workflow
- [ ] Test complete workflow before HACCP development

### During HACCP Development
- [ ] All HACCP features developed in `dev`
- [ ] Feature-flag HACCP features off by default
- [ ] Enable for test organization only
- [ ] Thoroughly test in `staging` before `main`
- [ ] Gradual rollout via feature flags

---

## Questions to Consider

1. **Module Pricing:** Will each module be a separate add-on, or bundled in tiers?
2. **Data Isolation:** Should HACCP data be in separate database schemas for security?
3. **Mobile Apps:** Will modules have mobile apps? (HACCP temperature logging on tablets?)
4. **API Access:** Will external systems need API access to modules?
5. **White Labeling:** Will customers want to white-label individual modules?

---

## Conclusion

This approach gives you:
- ✅ Safe way to develop new modules without disrupting existing users
- ✅ Flexible feature rollout with feature flags
- ✅ Organized codebase that scales to many modules
- ✅ Clear branching strategy for team collaboration
- ✅ Foundation for multi-module SaaS platform

**Start Simple. Scale When Needed.**

Keep using `main` + `dev` until Food Cost MVP is complete. When you start HACCP, implement the three-branch system and feature flags. This document will guide that transition.

---

**Document Version:** 1.0
**Last Updated:** December 17, 2024
**Next Review:** When Food Cost MVP nears completion
