# Start Here - December 17, 2024

## Quick Status

**Current Branch:** `dev`
**Last Deployed:** Password reset feature for user edit modal (commit a0307f8)
**Documentation:** Organized into docs/archive/ (commit f38f8df)

## What We Completed Yesterday (Dec 16)

### Phase 2 Super Admin Features - COMPLETE ✅
1. ✅ User creation for organizations
2. ✅ Organization detail page with full user/outlet visibility
3. ✅ User editing (full name, role, password reset)
4. ✅ User activate/deactivate functionality
5. ✅ All super admin features tested and working

**Status:** All Phase 2 features are complete, tested, and deployed to dev environment.

## Today's Focus: Outlet-Level User Access Control (Phase 3)

### The Goal
Implement permission-based outlet access for non-admin users:
- **Admins:** Full organization access (all outlets)
- **Chefs/Viewers:** Only see outlets they're assigned to
- **User with no assignments:** See no data (helpful empty state)

### Why This Matters
- Multi-location clients (hotels, franchises) need role-based outlet access
- Prevents cross-location data visibility issues
- Maintains existing outlet filtering - we're just controlling the dropdown

### The Approach
**Key Insight:** The outlet dropdown becomes the access control point. All existing data filtering works as-is because it's already scoped to the selected outlet via OutletContext.

**Permission Logic:**
```
IF user.role == 'admin':
    available_outlets = ALL org outlets
ELSE:
    available_outlets = user's assigned outlets from user_outlet_assignments table
```

### Detailed Implementation Plan

**See:** `OUTLET_ASSIGNMENT_PLAN.md` for comprehensive implementation details

**Quick Overview:**
1. Database migration - `user_outlet_assignments` table (many-to-many)
2. Backend API changes - modify `/outlets`, add assignment endpoints
3. Frontend OutletContext - filter outlets by permissions
4. Users page - add outlet assignment UI
5. Super Admin - manage outlet assignments

### Starting Point Recommendations

**Option 1: Database First (Recommended)**
Start with the migration to get the data structure in place:
1. Create migration file
2. Write SQL for `user_outlet_assignments` table
3. Run migration locally
4. Test with some manual INSERT statements

**Option 2: Full Stack Slice**
Implement end-to-end for viewing only:
1. Create migration
2. Add backend endpoint to get user outlet assignments
3. Filter OutletContext dropdown
4. Test that non-admins see limited outlets

**Option 3: Planning First**
Review the plan together and clarify any questions before starting implementation.

## Project Organization

### Active Documentation (Root)
- `README.md` - Main project documentation
- `PROJECT_CONTEXT.md` - Project background
- `DESIGN_SYSTEM.md` - UI/UX guidelines
- `PHASES.md` - High-level roadmap
- `OUTLET_ASSIGNMENT_PLAN.md` - Today's work plan (NEW)

### Archived Documentation
- `docs/archive/` - All phase completion docs, testing guides, migration notes

## Current Directory Structure

```
Clean_Invoices/
├── api/                           # Backend
│   ├── app/routers/
│   │   ├── super_admin.py        # Super admin endpoints (recently updated)
│   │   ├── auth.py               # User auth, will need updates
│   │   ├── outlets.py            # Will need permission filtering
│   │   └── ...
│   └── migrations/                # Will add user_outlet_assignments
├── frontend/src/
│   ├── pages/
│   │   ├── SuperAdmin/
│   │   │   ├── OrganizationDetail.jsx  # Recently updated
│   │   │   └── Organizations.jsx        # Recently updated
│   │   └── Users.jsx              # Will add outlet assignment UI
│   └── contexts/
│       └── OutletContext.jsx      # Will add permission filtering
├── docs/archive/                  # Historical documentation
├── OUTLET_ASSIGNMENT_PLAN.md      # Today's detailed plan
└── START_HERE_DEC17.md           # This file
```

## Key Files to Touch Today

### Backend
1. `api/migrations/` - New migration for user_outlet_assignments table
2. `api/app/routers/outlets.py` - Filter outlets by user permissions
3. `api/app/routers/super_admin.py` - Add outlet assignment management endpoints
4. `api/app/routers/auth.py` - Include assigned outlet IDs in user response

### Frontend
1. `frontend/src/contexts/OutletContext.jsx` - Filter dropdown by permissions
2. `frontend/src/pages/Users.jsx` - Add outlet assignment UI
3. `frontend/src/pages/SuperAdmin/OrganizationDetail.jsx` - Manage user outlet assignments

## Testing Strategy

### Manual Testing Checklist
- [ ] Create test user with admin role - verify sees all outlets
- [ ] Create test user with chef role, no assignments - verify sees no outlets
- [ ] Assign chef to specific outlet - verify sees only that outlet
- [ ] Assign chef to multiple outlets - verify sees all assigned outlets
- [ ] Switch between assigned outlets - verify data updates correctly
- [ ] Super admin can edit user outlet assignments
- [ ] Org admin can edit user outlet assignments (if we add this)

### Edge Cases to Consider
- User promoted from chef to admin - should see all outlets
- User demoted from admin to chef - falls back to assignments (may have none)
- Outlet deleted - assignments cascade delete automatically
- Organization with no outlets - all users see empty state

## Questions to Clarify (Optional)

1. Should org admins (non-super-admin) be able to manage outlet assignments for their users?
   - Likely YES - admins should manage their own team

2. Should we show outlet assignments during user creation or only after creation?
   - Plan suggests optional during creation, can be set later

3. What happens if a non-admin user currently logged in gets their outlet assignments changed?
   - Should they be logged out? Should we refresh their context?
   - Probably: next outlet dropdown interaction will reflect new permissions

## Git Workflow

```bash
# Current state
git status  # Should be clean on dev branch

# Start work
git checkout -b feature/outlet-user-assignments
# Make changes, commit frequently
# When ready to test:
git push origin feature/outlet-user-assignments
# Merge to dev for testing
# Merge to main when verified
```

## Environment Status

- **Dev:** https://food-cost-tracker-dev.onrender.com (up to date)
- **Production:** https://food-cost-tracker.onrender.com (pending dev → main merge)

## Notes from Yesterday's Session

- Documentation is now clean and organized
- Root directory went from 21 .md files to 5 (much cleaner!)
- All Phase 2 super admin features working perfectly
- Password reset functionality added to user edit modal
- Ready to start Phase 3 implementation

## Quick Win Suggestion

Start by creating the database migration and running it locally. This gives us the foundation and we can iterate on the UI/API from there. The migration is straightforward:

```sql
CREATE TABLE user_outlet_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outlet_id INTEGER NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, outlet_id)
);
```

---

**Let's build this! 🚀**
