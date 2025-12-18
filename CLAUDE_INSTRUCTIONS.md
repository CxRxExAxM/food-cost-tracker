# Instructions for Claude Code Sessions

**Purpose:** Guidelines to help Claude maintain project consistency across sessions.

---

## Documentation Structure

### Active Documentation (Root Directory)

**Keep only these 4 files in root:**

1. **README.md** - "Start here" guide
   - Current project status
   - Feature list with accurate completion status
   - Quick start guide
   - Links to other documentation

2. **FUTURE_PLANS.md** - Post-MVP roadmap
   - Multi-module architecture plans
   - Branching strategy (main/staging/dev)
   - Feature flag system design
   - HACCP module plans

3. **DESIGN_SYSTEM.md** - UI/UX guidelines
   - Color palette
   - Typography
   - Component patterns
   - Keep as reference, don't modify often

4. **DEVELOPMENT.md** - Developer guide
   - Local setup instructions
   - Git workflow
   - Deployment process
   - Testing guidelines

**Any other .md files in root = needs justification or archival**

### Documentation Archive (`docs/`)

```
docs/
├── archive/        # Historical planning documents
├── completed/      # Completed phase documentation
└── recipes/        # Recipe module specific docs
```

**Rules:**
- Outdated planning docs → `docs/archive/`
- Completed major phases → `docs/completed/`
- Module-specific implementation → `docs/<module>/`

---

## When Completing a Major Phase

1. **Create completion doc** in `docs/completed/`
   ```
   docs/completed/PHASE#_NAME.md
   ```

2. **Required sections:**
   - Completed date
   - Features implemented
   - Files modified (backend + frontend)
   - Database changes
   - Testing completed

3. **Update README.md:**
   - Move feature from "Upcoming" to "Completed"
   - Update current status section

4. **Update FUTURE_PLANS.md if needed:**
   - Remove completed items
   - Add new insights from implementation

---

## Git Workflow

### Branch Strategy (Current: Two-Branch)

```
main (production)
  └── dev (development)
      ├── feature/* (short-lived)
      └── fix/* (short-lived)
```

**Rules:**
- `main` = production (manual deploys only)
- `dev` = active development (auto-deploys to dev.onrender.com)
- All work happens in feature branches off `dev`
- Merge `dev` → `main` when ready for production

**Future (Three-Branch - When Starting HACCP):**
```
main (production)
  ├── staging (pre-production)
      └── dev (development)
```

See FUTURE_PLANS.md for when/how to implement.

### Commit Message Format

```
<type>: <description>

[optional body]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code restructuring (no functionality change)
- `test:` - Adding tests
- `chore:` - Maintenance (dependencies, etc.)

**Examples:**
```
feat: Add temperature monitoring UI for HACCP module
fix: Correct impersonation to use AuthContext.setToken
docs: Update README with Phase 4 completion status
```

---

## Code Organization

### Frontend Structure

**Current (Good - Don't Change Yet):**
```
frontend/src/
  ├── pages/           # Page components
  ├── components/      # Shared components
  ├── contexts/        # React contexts
  └── lib/             # Utilities
```

**Future (When Starting HACCP):**
```
frontend/src/
  ├── modules/
  │   ├── food-cost/   # Move Products, Recipes here
  │   └── haccp/       # New module
  ├── shared/          # Move Navigation, contexts here
  └── pages/
      ├── Home.jsx     # Module selector
      └── Login.jsx
```

**⚠️ Do NOT restructure until HACCP development starts!**

### Backend Structure

**Current (Good - Don't Change Yet):**
```
api/app/
  ├── routers/         # API endpoints
  ├── database.py
  ├── audit.py
  └── main.py
```

**Future (When Starting HACCP):**
```
api/app/
  ├── routers/
  │   ├── food_cost/   # Move products, recipes
  │   ├── haccp/       # New module
  │   └── shared/      # Auth, users, outlets
  └── ...
```

**⚠️ Do NOT restructure until HACCP development starts!**

---

## Database Migrations

### Creating Migrations

```bash
# Run from project root
alembic revision -m "description"
```

### Migration Naming

Format: `<sequential>_<description>.py`

Examples:
- `001_initial_schema.py`
- `002_add_missing_organization_columns.py`
- `5e7f498e6bd8_add_audit_logs_table.py`

### Running Migrations

**Local:**
```bash
alembic upgrade head
```

**Production (Render):**
- Runs automatically on deploy via Dockerfile.render
- Command: `alembic upgrade head && uvicorn ...`

### Migration Guidelines

1. **Always test locally first**
2. **Make migrations backward compatible when possible**
3. **Document schema changes in migration file docstring**
4. **Never edit merged migrations** - create new ones

---

## Common Patterns

### Feature Flags (Future)

When implementing organization features:

```python
# Backend
from api.app.features import has_feature

if not has_feature(org_id, "haccp"):
    raise HTTPException(403, "HACCP module not enabled")
```

```javascript
// Frontend
const { hasFeature } = useFeatures();

{hasFeature('haccp') && (
  <Link to="/haccp">HACCP Module</Link>
)}
```

**⚠️ Feature flag system doesn't exist yet!**
- Implement when starting HACCP module
- See FUTURE_PLANS.md for design

### Audit Logging

All critical actions should be logged:

```python
from api.app.audit import log_audit, AuditAction, EntityType

log_audit(
    action=AuditAction.SUBSCRIPTION_UPDATED,
    user_id=current_user["id"],
    organization_id=org_id,
    entity_type=EntityType.ORGANIZATION,
    entity_id=org_id,
    changes={"tier": {"from": "free", "to": "basic"}},
    ip_address=request.client.host if request else None
)
```

**Critical actions to log:**
- Subscription changes
- User role changes
- Impersonation start/end
- Organization settings changes
- Outlet assignments

---

## Testing Guidelines

### Manual Testing Checklist

Before marking a phase complete:

1. **Happy path** - Primary user flow works
2. **Edge cases** - Empty states, no data scenarios
3. **Permissions** - Admin vs non-admin access
4. **Multi-tenant** - Test with 2+ organizations
5. **Error handling** - Invalid inputs, network failures

### Key User Flows

Test these regularly:

1. **Organization Admin:**
   - Create outlet
   - Create user
   - Assign user to outlet
   - Upload price list
   - Create recipe

2. **Super Admin:**
   - Create organization
   - Update subscription
   - Impersonate organization
   - View audit logs

3. **Non-Admin User:**
   - Login
   - See only assigned outlets
   - Access restrictions work

---

## Documentation Maintenance

### When to Update README.md

- ✅ Phase completed
- ✅ New major feature deployed
- ✅ Tech stack changes
- ✅ Deployment URLs change
- ❌ Small bug fixes
- ❌ Minor tweaks

### When to Update FUTURE_PLANS.md

- ✅ New module planned
- ✅ Architecture decisions made
- ✅ Roadmap changes
- ❌ Individual feature ideas (use GitHub Issues)
- ❌ Bug tracking

### When to Create Completion Doc

**Create `docs/completed/PHASE#_NAME.md` when:**
- Major feature set complete (3+ related features)
- Database schema changes
- New module/section added
- Significant architectural change

**Don't create for:**
- Bug fixes
- Minor feature additions
- UI tweaks
- Refactoring

---

## Common Mistakes to Avoid

### ❌ Don't Do This:

1. **Create new .md files in root** without archiving old ones
2. **Restructure code** before HACCP development starts
3. **Force push to main or dev branches**
4. **Implement features without testing multi-tenancy**
5. **Skip audit logging for critical actions**
6. **Modify completed migrations**
7. **Use `localStorage` directly** (use AuthContext.setToken)
8. **Add emojis to code** unless explicitly requested

### ✅ Do This Instead:

1. **Update existing docs** or archive outdated ones
2. **Wait for modular restructure** per FUTURE_PLANS.md
3. **Use normal git workflow** (commits, PRs)
4. **Test with multiple orgs/outlets**
5. **Log all subscription, user, impersonation changes**
6. **Create new migrations** for schema changes
7. **Use React contexts and hooks** for state management
8. **Keep code professional** and clean

---

## Quick Reference

### Important Files

**Configuration:**
- `api/app/database.py` - Database connection
- `api/app/main.py` - FastAPI app setup
- `frontend/src/lib/axios.js` - API client
- `alembic.ini` - Migration config
- `Dockerfile.render` - Deployment config

**Core Contexts:**
- `AuthContext` - User authentication, token management
- `OutletContext` - Current outlet selection

**Key Utilities:**
- `api/app/audit.py` - Audit logging helpers
- `api/app/auth.py` - JWT token handling

### Environment Variables

**Backend:**
- `DATABASE_URL` - PostgreSQL connection
- `JWT_SECRET_KEY` - Token signing (auto-generated on Render)
- `PYTHON_ENV` - "production" on Render

**Frontend:**
- `VITE_API_URL` - Backend URL (empty = relative paths)

### Deployment URLs

- **Production:** https://food-cost-tracker.onrender.com
- **Dev:** https://food-cost-tracker-dev.onrender.com

---

## Questions to Ask User

Before making significant changes, confirm:

1. **Major restructure?** "This would reorganize the codebase significantly. Should we wait until HACCP development per FUTURE_PLANS.md?"

2. **New documentation?** "Should I create a new .md file or add to existing documentation?"

3. **Breaking changes?** "This change affects existing functionality. Should we implement with feature flags?"

4. **Branching strategy?** "Ready to implement three-branch workflow (main/staging/dev) or stay with two-branch?"

---

## Session Handoff

At the end of each session, provide:

1. **Summary of work completed**
2. **Files modified** (with line references if significant)
3. **Commits made** (with commit hashes)
4. **Next recommended steps**
5. **Any blockers or questions**

**Format:**
```
## Session Summary

**Work Completed:**
- Fixed impersonation banner (Navigation.jsx:60-77 removed)
- Updated audit logging (audit.py:61 - use bool() not int)

**Commits:**
- 8752bbd - fix: Remove duplicate impersonation banner
- 66e4922 - fix: Use boolean type for audit logs

**Next Steps:**
1. Wait for Render deploy
2. Test impersonation workflow
3. Verify audit logs populating

**Status:** ✅ Ready for testing
```

---

## Project Philosophy

### Keep It Simple
- Two branches until HACCP development
- Minimal .md files in root
- Don't over-engineer for future needs

### Multi-Tenant First
- Every feature must work with multiple organizations
- Test with 2+ orgs and outlets
- Data isolation is critical

### Document Major Changes Only
- Completion docs for phases, not individual features
- README stays current, not exhaustive
- FUTURE_PLANS.md for strategic decisions

### Professional Code
- No emojis in code
- Clear variable names
- Comments explain "why" not "what"
- Follow existing patterns

---

**Last Updated:** December 17, 2024
**Next Review:** When starting HACCP module development
