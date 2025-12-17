# Documentation & Directory Cleanup Plan

**Created:** December 17, 2024
**Status:** Proposed

---

## Problem Statement

Our documentation has grown organically during MVP development, resulting in:
- **8 markdown files** in root directory (some outdated)
- **Duplicate information** across multiple files
- **Outdated roadmaps** that don't reflect completed work (Phases 3 & 4)
- **No clear "start here"** for new developers or future you

---

## Current Documentation Audit

### Active & Accurate
| File | Size | Status | Action |
|------|------|--------|--------|
| `FUTURE_PLANS.md` | 23KB | ✅ Up to date | **KEEP** - Comprehensive future roadmap |
| `DESIGN_SYSTEM.md` | 19KB | ✅ Still relevant | **KEEP** - UI/UX guidelines |
| `PHASE4_COMPLETE.md` | 9.2KB | ✅ Accurate snapshot | **ARCHIVE** - Move to docs/completed/ |

### Outdated & Needs Update
| File | Size | Issues | Action |
|------|------|--------|--------|
| `README.md` | 18KB | Says "Phase 3 upcoming" but we completed Phases 3 & 4 | **UPDATE** - Make current |
| `PHASES.md` | 8.5KB | Recipe phases (0-5 complete), Phase 6 listed but not prioritized | **UPDATE** - Clarify status |
| `PROJECT_CONTEXT.md` | 7.3KB | Mentions SQLite→PostgreSQL as "upcoming" (done Nov 2024) | **ARCHIVE** - Superseded |
| `START_HERE_DEC17.md` | 7.2KB | Snapshot from Dec 17, says "Phase 3 next" (now complete) | **ARCHIVE** - Outdated |
| `OUTLET_ASSIGNMENT_PLAN.md` | 6.5KB | Phase 3 implementation plan (completed) | **ARCHIVE** - Historical reference |

---

## Proposed Documentation Structure

### Root Directory (Active Docs Only)

```
Clean_Invoices/
├── README.md                    # "Start here" - current state, quick setup
├── FUTURE_PLANS.md              # Post-MVP roadmap (multi-module, HACCP, etc.)
├── DESIGN_SYSTEM.md             # UI/UX guidelines
└── DEVELOPMENT.md               # NEW: Local setup, git workflow, deployment
```

**Total: 4 active files** (down from 8)

### Documentation Archive

```
Clean_Invoices/
└── docs/
    ├── completed/               # NEW: Completed phase documentation
    │   ├── PHASE1_OUTLETS.md
    │   ├── PHASE2_SUPER_ADMIN.md
    │   ├── PHASE3_OUTLET_ASSIGNMENTS.md
    │   └── PHASE4_SUPER_ADMIN_SUITE.md
    │
    ├── planning/                # NEW: Old planning docs (historical reference)
    │   ├── PROJECT_CONTEXT.md
    │   ├── OUTLET_ASSIGNMENT_PLAN.md
    │   └── START_HERE_DEC17.md
    │
    └── recipes/                 # Recipe module implementation (already exists)
        └── PHASES.md            # Move here - recipe-specific phases
```

---

## Consolidation Actions

### 1. Update README.md

**Current Issues:**
- Says "Upcoming Features: Phase 3" but we completed Phases 3 & 4
- Missing super admin features in feature list
- Missing audit logging

**New Structure:**
```markdown
# Food Cost Tracker

## Quick Links
- Production: https://food-cost-tracker.onrender.com
- Dev: https://food-cost-tracker-dev.onrender.com

## Current Status (December 2024)
- ✅ Food Cost Tracking MVP (Complete)
- ✅ Multi-Tenancy & Organizations (Complete)
- ✅ Multi-Outlet Support (Complete)
- ✅ Outlet-Level Access Control (Complete)
- ✅ Super Admin Management Suite (Complete)
- 📋 Next: AI Recipe Parser, Advanced Features

## Features
[Comprehensive feature list with accurate status]

## Tech Stack
- Backend: FastAPI + Python
- Frontend: React + Vite
- Database: PostgreSQL (Render)
- Hosting: Render

## Quick Start
[Local setup instructions]

## Documentation
- See FUTURE_PLANS.md for roadmap
- See DESIGN_SYSTEM.md for UI guidelines
- See docs/completed/ for phase documentation
```

### 2. Update FUTURE_PLANS.md

**Add Missing Content:**

From `PROJECT_CONTEXT.md`:
- AI Recipe Parser implementation details (technical approach, cost estimates)
- Claude API prompt structure
- File upload flow diagram

From `PHASES.md`:
- Phase 6 advanced features list
- Shopping list generation
- Recipe scaling
- Price trend charts
- Batch cost comparison

**New Section to Add:**
```markdown
## Food Cost Tracker - Advanced Features (Post-MVP)

### AI Recipe Parser (High Priority)
[Detailed implementation from PROJECT_CONTEXT.md]

### Phase 6 Features (Medium Priority)
[Features from PHASES.md Phase 6]
```

### 3. Create DEVELOPMENT.md (New)

**Purpose:** Developer setup and workflow guide

**Contents:**
```markdown
# Development Guide

## Local Setup
1. Clone repository
2. Backend setup (venv, requirements)
3. Frontend setup (npm install)
4. Database setup (PostgreSQL local or Render)
5. Environment variables

## Git Workflow
- main (production)
- dev (development)
- feature/* branches

## Running Locally
- Backend: uvicorn api.app.main:app --reload
- Frontend: npm run dev
- Database: alembic upgrade head

## Deployment
- Dev: Auto-deploy from dev branch
- Production: Manual deploy from main branch
- Migrations run automatically on deploy

## Testing
- Manual testing checklist
- Key user flows to verify
```

### 4. Organize Completed Phase Docs

**Create:** `docs/completed/`

**Move & Rename:**
- `PHASE4_COMPLETE.md` → `docs/completed/PHASE4_SUPER_ADMIN_SUITE.md`

**Create New (from git history/memory):**
- `docs/completed/PHASE1_OUTLETS.md` - Multi-outlet backend implementation
- `docs/completed/PHASE2_SUPER_ADMIN.md` - Super admin dashboard
- `docs/completed/PHASE3_OUTLET_ASSIGNMENTS.md` - User outlet access control

**Format:**
```markdown
# Phase N: [Name]

**Completed:** [Date]
**Branch:** dev
**Commits:** [Key commits]

## Features Implemented
- Feature 1
- Feature 2

## Files Modified
- Backend: [files]
- Frontend: [files]

## Database Changes
- Migrations: [migration files]

## Testing Completed
- [Test checklist]
```

### 5. Archive Old Planning Docs

**Create:** `docs/planning/` (or `docs/archive/`)

**Move:**
- `PROJECT_CONTEXT.md` → `docs/planning/PROJECT_CONTEXT_NOV2024.md`
- `OUTLET_ASSIGNMENT_PLAN.md` → `docs/planning/OUTLET_ASSIGNMENT_PLAN.md`
- `START_HERE_DEC17.md` → `docs/planning/START_HERE_DEC17.md`

**Add README:**
```markdown
# Planning Archive

Historical planning documents. These were accurate when written but have been superseded by current documentation.

Refer to root README.md and FUTURE_PLANS.md for current information.
```

### 6. Move Recipe Phases Doc

**Move:**
- `PHASES.md` → `docs/recipes/RECIPE_PHASES.md`

**Why:**
- It's specific to recipe module implementation
- Phase 6 content should be consolidated into FUTURE_PLANS.md
- Keeps root directory focused on current/future, not implementation details

---

## Directory Structure Recommendations

### Current Frontend Structure (Already Good!)

Your frontend is already well-organized:

```
frontend/src/
  ├── pages/
  │   ├── Home.jsx
  │   ├── Login.jsx
  │   ├── Products.jsx          # Food Cost
  │   ├── Recipes.jsx           # Food Cost
  │   ├── Users.jsx             # Shared
  │   ├── Admin.jsx             # Shared
  │   ├── Outlets.jsx           # Shared
  │   └── SuperAdmin/           # Module-like already!
  │       ├── Dashboard.jsx
  │       ├── Organizations.jsx
  │       ├── OrganizationDetail.jsx
  │       └── AuditLogs.jsx
  ├── components/
  │   ├── Navigation.jsx
  │   ├── ImpersonationBanner.jsx
  │   └── outlets/              # Sub-organized
  │       └── OutletSelector.jsx
  ├── contexts/
  │   ├── AuthContext.jsx
  │   └── OutletContext.jsx
  └── lib/
      └── axios.js
```

**Recommendation:** Don't restructure yet. Wait until you start HACCP module development (per FUTURE_PLANS.md), then implement the modular structure:

```
frontend/src/
  ├── modules/
  │   ├── food-cost/            # Move Products, Recipes here
  │   └── haccp/                # New module
  ├── shared/                   # Move Navigation, contexts here
  └── pages/
      ├── Home.jsx              # Module selector
      └── Login.jsx
```

### Current Backend Structure (Also Good!)

```
api/app/
  ├── routers/
  │   ├── auth.py
  │   ├── users.py
  │   ├── outlets.py
  │   ├── products.py
  │   ├── recipes.py
  │   ├── super_admin.py        # Already modular!
  │   └── uploads.py
  ├── database.py
  ├── audit.py
  └── main.py
```

**Recommendation:** Also wait to restructure. When adding HACCP:

```
api/app/
  ├── routers/
  │   ├── food_cost/            # Move products, recipes
  │   ├── haccp/                # New module
  │   └── shared/               # Auth, users, outlets
  └── ...
```

### Suggested Cleanup (Minor)

**Create:**
```
Clean_Invoices/
├── .github/                   # If using GitHub Actions
├── scripts/                   # Utility scripts
│   └── vendor_cleaning/       # Move clean_*.py scripts here
└── docs/                      # Documentation organization
    ├── completed/
    ├── planning/
    └── recipes/
```

**No major refactoring needed** - your structure is already clean!

---

## Implementation Steps

### Phase 1: Documentation Consolidation (30 minutes)

```bash
# 1. Create directories
mkdir -p docs/completed
mkdir -p docs/planning
mkdir -p docs/recipes

# 2. Move files
git mv PROJECT_CONTEXT.md docs/planning/PROJECT_CONTEXT_NOV2024.md
git mv OUTLET_ASSIGNMENT_PLAN.md docs/planning/
git mv START_HERE_DEC17.md docs/planning/
git mv PHASE4_COMPLETE.md docs/completed/PHASE4_SUPER_ADMIN_SUITE.md
git mv PHASES.md docs/recipes/RECIPE_PHASES.md

# 3. Create archive README
cat > docs/planning/README.md << 'EOF'
# Planning Archive

Historical planning documents from MVP development.
Accurate when written but superseded by current documentation.

Refer to root README.md and FUTURE_PLANS.md for current information.
EOF

# 4. Commit
git add -A
git commit -m "docs: Reorganize documentation structure

- Move outdated planning docs to docs/planning/
- Move completed phase docs to docs/completed/
- Move recipe-specific phases to docs/recipes/
- Prepare for README and FUTURE_PLANS updates"
```

### Phase 2: Update Active Docs (60 minutes)

1. **Update README.md**
   - Accurate current status (Phases 1-4 complete)
   - Clean feature list
   - Quick start guide
   - Links to other docs

2. **Update FUTURE_PLANS.md**
   - Add AI Recipe Parser details from PROJECT_CONTEXT.md
   - Add Phase 6 advanced features from PHASES.md
   - Consolidate all future roadmap info

3. **Create DEVELOPMENT.md**
   - Local setup instructions
   - Git workflow
   - Deployment process
   - Testing guide

### Phase 3: Create Completed Phase Docs (Optional - 30 minutes)

Create documentation for Phases 1-3 by reviewing git history:

- `docs/completed/PHASE1_OUTLETS.md`
- `docs/completed/PHASE2_SUPER_ADMIN.md`
- `docs/completed/PHASE3_OUTLET_ASSIGNMENTS.md`

---

## Before & After

### Before (Current)

```
Clean_Invoices/
├── DESIGN_SYSTEM.md           ✅ Keep
├── FUTURE_PLANS.md            ✅ Keep (update)
├── OUTLET_ASSIGNMENT_PLAN.md  ❌ Outdated planning
├── PHASE4_COMPLETE.md         ⚠️  Archive
├── PHASES.md                  ⚠️  Recipe-specific
├── PROJECT_CONTEXT.md         ❌ Outdated (SQLite migration, etc.)
├── README.md                  ⚠️  Needs update
└── START_HERE_DEC17.md        ❌ Snapshot from Dec 17
```

**8 files in root, 3 need action, 3 outdated**

### After (Proposed)

```
Clean_Invoices/
├── README.md                  ✅ Updated - "Start here"
├── FUTURE_PLANS.md            ✅ Updated - Comprehensive roadmap
├── DESIGN_SYSTEM.md           ✅ Keep as-is
├── DEVELOPMENT.md             ✨ New - Developer guide
└── docs/
    ├── completed/             ✨ Phase completion docs
    ├── planning/              ✨ Historical planning docs
    └── recipes/               ✨ Recipe module details
```

**4 active files in root, organized archive**

---

## Benefits

1. **Clear Entry Point** - README.md is accurate and welcoming
2. **Reduced Cognitive Load** - 4 active docs vs 8
3. **Historical Context Preserved** - Completed and planning docs archived
4. **Future-Ready** - FUTURE_PLANS.md has comprehensive roadmap
5. **Developer-Friendly** - DEVELOPMENT.md for setup/workflow
6. **Easier Maintenance** - Less duplication, clear ownership

---

## Recommendation

**Do This Now (Before starting any new features):**
- Phase 1: Reorganize docs (30 min) ✅
- Phase 2: Update README & FUTURE_PLANS (60 min) ✅

**Do Later (Optional):**
- Phase 3: Create completed phase docs ⏰
- Directory restructuring when starting HACCP module ⏰

**Total Time:** ~90 minutes to have clean, accurate documentation

---

## Questions for You

1. **Archive location name:** Prefer `docs/planning/` or `docs/archive/` for old planning docs?

2. **Completed phases:** Want me to create Phase 1-3 completion docs from git history, or skip for now?

3. **README length:** Prefer comprehensive (current 18KB) or concise with links to other docs?

4. **DEVELOPMENT.md:** Should this include deployment instructions or keep those in README?

5. **Recipe phases:** Keep as separate doc in `docs/recipes/` or consolidate Phase 6 features into FUTURE_PLANS.md?

---

**Ready to execute this plan when you are!**
