# Outlet Assignment Implementation Plan

**Date:** December 16, 2024
**Status:** Planning
**Target:** Phase 2 - Advanced Super Admin Features

## Overview

Implement outlet-level access control for non-admin users. Admins have full organization access, while Chefs and Viewers are restricted to outlets they're assigned to.

## User Experience Flow

### Current Behavior
- All users within an organization can see all outlets via the outlet dropdown
- OutletContext controls which outlet's data is displayed
- No permission-based restrictions

### New Behavior
- **Admins:** See all outlets (unchanged)
- **Chefs/Viewers:** Only see outlets they're assigned to in dropdown
- When user selects an outlet, all existing filtering works as-is
- Users with zero outlet assignments see no outlets → no data visible

## Architecture

### Database Schema

**New Table: `user_outlet_assignments`**
```sql
CREATE TABLE user_outlet_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outlet_id INTEGER NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, outlet_id)
);

CREATE INDEX idx_user_outlet_assignments_user_id ON user_outlet_assignments(user_id);
CREATE INDEX idx_user_outlet_assignments_outlet_id ON user_outlet_assignments(outlet_id);
```

**Relationship:** Many-to-many
- One user can be assigned to multiple outlets
- One outlet can have multiple users assigned

### Permission Logic

```
IF user.role == 'admin':
    accessible_outlets = ALL outlets in organization
ELSE:
    accessible_outlets = outlets from user_outlet_assignments WHERE user_id = current_user.id
```

## Implementation Steps

### 1. Database Migration

**File:** `api/migrations/add_user_outlet_assignments.sql`

- Create `user_outlet_assignments` table
- Add indexes for performance
- No data migration needed (start fresh)

### 2. Backend API Changes

#### 2.1 New Endpoints

**GET `/outlets`** - Modified
- If admin: return all org outlets (current behavior)
- If chef/viewer: return only assigned outlets
- Response includes outlet assignments for each outlet

**GET `/super-admin/organizations/{org_id}`** - Modified
- Include outlet assignments for each user in response
- Add `assigned_outlet_ids: List[int]` to UserResponse

**PATCH `/super-admin/users/{user_id}/outlets`** - New
- Update outlet assignments for a user
- Request body: `{"outlet_ids": [1, 2, 3]}`
- Replaces all assignments (delete old, insert new)

#### 2.2 Models

**New Pydantic Model:**
```python
class UserOutletAssignments(BaseModel):
    outlet_ids: List[int]
```

**Modified UserResponse:**
```python
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    assigned_outlet_ids: List[int]  # NEW
```

### 3. Frontend Changes

#### 3.1 OutletContext Modification

**File:** `frontend/src/contexts/OutletContext.jsx`

- Filter available outlets based on user role
- If non-admin and no assigned outlets: show empty state instead of selector
- Admins see all outlets (unchanged)

#### 3.2 Users Page

**File:** `frontend/src/pages/Users.jsx`

**Add "Outlets" column to table:**
- Display assigned outlets as badge chips
- Clicking badge could filter or highlight
- Show "All Outlets" badge for admins
- Show "No Outlets" warning for unassigned non-admins

**Modify Edit User Modal:**
- Add outlet assignment section with checkboxes
- Only show if organization has outlets
- Checkbox for each outlet
- Disabled/hidden for admin users (always have full access)

#### 3.3 Super Admin - Organization Detail

**File:** `frontend/src/pages/SuperAdmin/OrganizationDetail.jsx`

**Add "Outlets" column to users table:**
- Show outlet badges for each user
- "All" badge for admins
- "Manage Outlets" button opens modal

**New Modal: Manage User Outlets**
- Checkbox list of all organization outlets
- Save/Cancel actions
- Call PATCH endpoint to update

**Optional: User Creation Modal**
- Add outlet selection (checkboxes)
- Not required - can be set later
- If no outlets exist, hide section

### 4. Edge Cases

| Scenario | Behavior |
|----------|----------|
| User has no outlet assignments | Empty dropdown, helpful message "Contact admin for outlet access" |
| Outlet is deleted | Assignments auto-deleted via CASCADE |
| User promoted to admin | Outlet assignments ignored, sees all outlets |
| User demoted from admin | Falls back to assignments (may be none) |
| Organization has no outlets | All users see empty state (current behavior) |
| User switches between assigned outlets | Data updates via existing OutletContext logic |

## Testing Checklist

### Database
- [ ] Migration runs successfully
- [ ] Indexes created
- [ ] CASCADE delete works when outlet deleted
- [ ] UNIQUE constraint prevents duplicate assignments

### Backend
- [ ] Admin users get all outlets from GET /outlets
- [ ] Non-admin users get only assigned outlets
- [ ] Super admin can view user outlet assignments
- [ ] Super admin can update user outlet assignments
- [ ] Invalid outlet IDs rejected

### Frontend - OutletContext
- [ ] Admin sees all outlets in dropdown
- [ ] Chef with assignments sees only their outlets
- [ ] Chef with no assignments sees helpful empty state
- [ ] Switching outlets updates data correctly

### Frontend - Users Page
- [ ] Outlets column displays correctly
- [ ] Edit modal shows outlet checkboxes
- [ ] Saving outlet assignments works
- [ ] Admin users don't show outlet selector (or show "All")

### Frontend - Super Admin
- [ ] Organization detail shows user outlet assignments
- [ ] Can edit outlet assignments for users
- [ ] Can assign outlets during user creation (optional)

## Success Criteria

1. ✅ Admins maintain full organization access
2. ✅ Non-admins can only access assigned outlets
3. ✅ Users with no assignments cannot see any data
4. ✅ Super admins can manage outlet assignments
5. ✅ Org admins can manage outlet assignments for their users
6. ✅ Existing outlet filtering logic requires no changes
7. ✅ Performance remains acceptable (indexed queries)

## Future Enhancements

- Bulk assignment (assign multiple users to outlets)
- Default outlet assignment on user creation
- Outlet access request workflow
- Audit log for assignment changes
- Role-based outlet assignment templates

## Notes

- This feature is permission-scoping, not data-scoping
- Products and recipes remain organization-level entities
- All existing outlet-filtered queries work as-is
- The outlet dropdown becomes the access control point
