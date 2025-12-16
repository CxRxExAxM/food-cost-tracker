# Super Admin Panel - Implementation Plan

**Created**: December 16, 2024
**Status**: Planning Phase
**Goal**: Build platform owner dashboard for managing all organizations

---

## Overview

The Super Admin panel is a separate interface for platform owners (you) to manage all organizations, monitor system health, and provide support across the entire RestauranTek platform.

### Key Distinction
- **Organization Admin**: Manages users, outlets, and data within THEIR organization
- **Super Admin**: Manages ALL organizations across the platform (platform owner)

---

## Database Schema Changes

### Option 1: Add `is_super_admin` Flag to Users Table (RECOMMENDED)

**Pros**:
- Simple implementation
- Single authentication system
- Easy to assign/revoke
- Super admins can still belong to an organization for testing

**Cons**:
- Mixing super admin with regular users in same table

**Migration**:
```sql
-- Add is_super_admin column to users table
ALTER TABLE users ADD COLUMN is_super_admin INTEGER DEFAULT 0;

-- Create index for quick lookup
CREATE INDEX idx_users_super_admin ON users(is_super_admin);

-- Make your user a super admin
UPDATE users SET is_super_admin = 1 WHERE email = 'your-email@example.com';
```

### Option 2: Separate Super Admins Table

**Pros**:
- Complete separation of concerns
- Could have different auth system

**Cons**:
- More complex authentication
- Duplicate user management code
- Harder to maintain

**Decision**: Use Option 1 (flag on users table)

---

## Authentication & Authorization

### Access Control

```python
# api/app/auth.py - Add new dependency

def get_current_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Verify user is a super admin."""
    if not current_user.get('is_super_admin'):
        raise HTTPException(
            status_code=403,
            detail="Super admin access required"
        )
    return current_user
```

### Route Protection

All super admin routes will:
1. Require JWT authentication
2. Check `is_super_admin` flag
3. Return 403 Forbidden if not super admin

---

## API Endpoints

### Organization Management

```
GET    /api/super-admin/organizations
  - List all organizations with stats
  - Filters: tier, status, search
  - Pagination support
  - Returns: id, name, tier, status, users_count, outlets_count, created_at

POST   /api/super-admin/organizations
  - Create new organization
  - Body: name, slug, tier, max_users, max_recipes
  - Creates default outlet automatically

GET    /api/super-admin/organizations/{id}
  - Get detailed org info
  - Includes: outlets, users, statistics, recent activity

PATCH  /api/super-admin/organizations/{id}
  - Update organization details
  - Can change: name, tier, limits, status

DELETE /api/super-admin/organizations/{id}
  - Soft delete organization
  - Marks as inactive, doesn't actually delete data
```

### User Management (Cross-Organization)

```
GET    /api/super-admin/users
  - List all users across all organizations
  - Filters: organization_id, role, search
  - Returns: user info + organization name

GET    /api/super-admin/users/{id}
  - Get detailed user info
  - Shows: profile, organization, outlets, activity

PATCH  /api/super-admin/users/{id}
  - Update user (change org, role, activate/deactivate)

POST   /api/super-admin/users/{id}/impersonate
  - Generate impersonation token
  - Login as any user for support purposes
  - Token expires in 1 hour
```

### System Analytics

```
GET    /api/super-admin/stats/overview
  - Platform-wide statistics
  - Returns:
    - Total organizations
    - Total users
    - Total outlets
    - Organizations by tier
    - Active vs inactive orgs
    - Recent signups

GET    /api/super-admin/stats/usage
  - Usage metrics
  - Products created (by org, by tier)
  - Recipes created (by org, by tier)
  - CSV imports (by org, by month)
  - API usage

GET    /api/super-admin/activity
  - Recent platform activity
  - New organizations
  - New users
  - Large imports
  - Errors/issues
```

### Subscription Management

```
GET    /api/super-admin/subscriptions
  - List all subscriptions
  - Filter by tier, status

PATCH  /api/super-admin/organizations/{id}/subscription
  - Change subscription tier
  - Update limits (max_users, max_recipes)
  - Change status (active, suspended, inactive)
```

---

## Frontend Structure

### Route Structure

```
/super-admin
  ├── /dashboard          # Overview & stats
  ├── /organizations      # Org list
  ├── /organizations/:id  # Org detail
  ├── /users              # All users
  ├── /analytics          # Platform analytics
  └── /settings           # Super admin settings
```

### Components to Build

#### 1. SuperAdminGuard Component
```jsx
// Protect super admin routes
function SuperAdminRoute({ children }) {
  const { user } = useAuth();

  if (!user?.is_super_admin) {
    return <Navigate to="/" replace />;
  }

  return children;
}
```

#### 2. SuperAdminNav Component
```jsx
// Navigation bar for super admin section
- Link to main app (exit super admin)
- Dashboard, Orgs, Users, Analytics
- Different color scheme (e.g., red/purple vs blue/green)
```

#### 3. OrganizationList Component
```jsx
// Table/grid of all organizations
- Search by name
- Filter by tier, status
- Sort by created date, name
- Actions: View, Edit, Suspend
- Shows: name, tier, outlets count, users count, status
```

#### 4. OrganizationDetail Component
```jsx
// Detailed org view
- Organization info (editable)
- Subscription tier with upgrade/downgrade
- Usage statistics vs limits
- Outlets list
- Users list with roles
- Recent activity
- Quick actions: Suspend, Delete, Impersonate Admin
```

#### 5. PlatformStatsCard Component
```jsx
// Dashboard overview cards
- Total Orgs (with breakdown by tier)
- Total Users
- Total Outlets
- This Month Growth
- Active vs Inactive Orgs
```

#### 6. TierBadge Component
```jsx
// Visual tier indicator
- Free: Gray
- Basic: Blue
- Pro: Purple
- Enterprise: Gold
```

#### 7. ImpersonateUserModal Component
```jsx
// User impersonation for support
- Select user from dropdown
- Show warning: "You will be logged in as [user]"
- Confirm button
- Creates impersonation token
- Logs you in as that user in new tab
```

---

## UI/UX Design

### Color Scheme
Use distinct colors to differentiate super admin from regular app:

**Regular App**: Blue/Green tones
**Super Admin**: Red/Purple tones

```css
:root {
  /* Super Admin Theme */
  --super-admin-primary: #9333ea;     /* Purple */
  --super-admin-secondary: #dc2626;   /* Red */
  --super-admin-accent: #f59e0b;      /* Amber */
  --super-admin-bg: #1a1a2e;          /* Dark purple-ish */
}
```

### Layout
```
┌─────────────────────────────────────────────────────────┐
│  [🔧 SUPER ADMIN]  Dashboard  Orgs  Users  Analytics   │
│  Exit Super Admin ↗                             [You ▼] │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Platform Overview                                      │
│  ┌─────────────┬─────────────┬─────────────┬──────────┐│
│  │ 127 Orgs    │ 2,453 Users │ 384 Outlets │ +12 This ││
│  │ +5 this mo. │ +89 this mo.│ +23 this mo.│ Month    ││
│  └─────────────┴─────────────┴─────────────┴──────────┘│
│                                                         │
│  Recent Organizations                                   │
│  ┌────────────────────────────────────────────────────┐│
│  │ Fairmont Hotels    [PRO]   12 outlets   45 users  ││
│  │ Hilton Group       [ENT]   28 outlets  156 users  ││
│  │ Local Bistro       [FREE]   1 outlet     2 users  ││
│  └────────────────────────────────────────────────────┘│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Mobile Responsive
- Cards stack vertically
- Tables convert to cards
- Actions in dropdown menus

---

## Security Considerations

### 1. Super Admin Access Logging
Log all super admin actions:
```sql
CREATE TABLE super_admin_logs (
  id SERIAL PRIMARY KEY,
  super_admin_id INTEGER REFERENCES users(id),
  action VARCHAR(50),  -- 'view_org', 'edit_org', 'impersonate_user', etc.
  target_type VARCHAR(50),  -- 'organization', 'user', etc.
  target_id INTEGER,
  details JSONB,
  ip_address VARCHAR(45),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Rate Limiting
- Stricter rate limits on super admin endpoints
- Prevent abuse even if credentials compromised

### 3. Two-Factor Authentication (Future)
- Require 2FA for super admin accounts
- Phase 2 enhancement

### 4. IP Whitelist (Optional)
- Only allow super admin access from specific IPs
- Add to environment config

---

## Implementation Phases

### Phase 1: Core Functionality (Week 1)
**Backend**:
- [ ] Add `is_super_admin` column to users table
- [ ] Create super admin auth dependency
- [ ] Build organizations CRUD endpoints
- [ ] Build platform stats endpoint
- [ ] Create super admin audit logging

**Frontend**:
- [ ] Create `/super-admin` route structure
- [ ] Build SuperAdminGuard component
- [ ] Create SuperAdminNav
- [ ] Build OrganizationList page
- [ ] Build Dashboard with stats

### Phase 2: Organization Management (Week 2)
**Backend**:
- [ ] Organization detail endpoint with full stats
- [ ] Subscription tier update endpoint
- [ ] Organization suspend/activate endpoint
- [ ] User search across organizations

**Frontend**:
- [ ] OrganizationDetail page
- [ ] Subscription tier editor
- [ ] Usage statistics visualization
- [ ] Organization suspend/delete flows

### Phase 3: User Management & Support (Week 3)
**Backend**:
- [ ] Cross-organization user list
- [ ] User impersonation token generation
- [ ] Activity logs endpoint

**Frontend**:
- [ ] All Users list page
- [ ] User impersonation modal
- [ ] Activity feed component

### Phase 4: Analytics & Polish (Week 4)
**Backend**:
- [ ] Usage analytics endpoints
- [ ] Growth metrics
- [ ] Export capabilities (CSV)

**Frontend**:
- [ ] Analytics dashboard with charts
- [ ] Search improvements
- [ ] Mobile responsive polish
- [ ] Dark mode support

---

## Data Visualization

### Charts Needed

1. **Organizations Growth Chart**
   - Line chart: Orgs created over time
   - Breakdown by tier

2. **User Growth Chart**
   - Line chart: Users added over time
   - Breakdown by organization tier

3. **Tier Distribution**
   - Pie chart: % of orgs in each tier
   - Shows: Free, Basic, Pro, Enterprise

4. **Usage Metrics**
   - Bar chart: Products/Recipes per tier
   - Shows average usage by tier

### Library Recommendation
- **Chart.js** or **Recharts** for visualizations
- Lightweight and React-friendly

---

## Environment Variables

Add to `.env` and Render config:

```bash
# Super Admin Settings
SUPER_ADMIN_EMAIL=your-email@example.com  # Auto-promote on first login
ENABLE_SUPER_ADMIN=true                   # Feature flag
SUPER_ADMIN_IP_WHITELIST=                 # Optional: comma-separated IPs
```

---

## Testing Strategy

### Manual Testing Checklist
- [ ] Create organization as super admin
- [ ] Edit organization details
- [ ] Change subscription tier
- [ ] Suspend/activate organization
- [ ] View all users across organizations
- [ ] Impersonate a user
- [ ] View platform statistics
- [ ] Verify non-super-admin cannot access

### Security Testing
- [ ] Attempt super admin access without flag
- [ ] Verify audit logs capture all actions
- [ ] Test impersonation token expiration
- [ ] Verify organization data isolation still works

---

## Future Enhancements

### Phase 5+
- [ ] Billing integration (Stripe)
- [ ] Automated tier enforcement (block actions when over limit)
- [ ] Email notifications (new org signup, usage alerts)
- [ ] Support ticket system
- [ ] Feature flags per organization
- [ ] A/B testing framework
- [ ] System health monitoring
- [ ] Automated backups management
- [ ] Multi-region support
- [ ] API key management for integrations

---

## Files to Create/Modify

### Backend
**New Files**:
- `alembic/versions/004_add_super_admin_support.py` - Migration
- `alembic/versions/005_add_super_admin_audit_log.py` - Migration
- `api/app/routers/super_admin.py` - All super admin endpoints

**Modified Files**:
- `api/app/auth.py` - Add `get_current_super_admin` dependency
- `api/app/main.py` - Include super admin router
- `api/app/schemas.py` - Add super admin response schemas

### Frontend
**New Files**:
- `frontend/src/pages/SuperAdmin/Dashboard.jsx`
- `frontend/src/pages/SuperAdmin/OrganizationList.jsx`
- `frontend/src/pages/SuperAdmin/OrganizationDetail.jsx`
- `frontend/src/pages/SuperAdmin/UserList.jsx`
- `frontend/src/pages/SuperAdmin/Analytics.jsx`
- `frontend/src/components/superadmin/SuperAdminNav.jsx`
- `frontend/src/components/superadmin/OrganizationCard.jsx`
- `frontend/src/components/superadmin/TierBadge.jsx`
- `frontend/src/components/superadmin/StatsCard.jsx`
- `frontend/src/components/superadmin/ImpersonateModal.jsx`
- `frontend/src/services/api/superadmin.js`
- `frontend/src/pages/SuperAdmin/SuperAdmin.css`

**Modified Files**:
- `frontend/src/App.jsx` - Add super admin routes
- `frontend/src/components/Navigation.jsx` - Add super admin link (if is_super_admin)
- `frontend/src/context/AuthContext.jsx` - Include is_super_admin in user object

---

## Success Criteria

Phase 1 Complete When:
- [x] Super admin can view all organizations
- [x] Super admin can create new organization
- [x] Super admin can view platform statistics
- [x] Platform stats show accurate counts
- [x] Non-super-admin users cannot access
- [x] Distinct UI differentiates super admin from regular app

---

## Questions to Answer

1. **Single vs Multi Super Admins?**
   - Start with single (you)
   - Easy to add more later with flag

2. **Soft vs Hard Delete Organizations?**
   - Soft delete (mark inactive)
   - Preserve data for recovery

3. **Impersonation Session Handling?**
   - Separate tab/window
   - Clear visual indicator "Viewing as [User]"
   - Easy exit back to super admin

4. **Tier Enforcement?**
   - Phase 1: Manual (you upgrade/downgrade)
   - Phase 2: Automated enforcement
   - Phase 3: Self-service with Stripe

---

**Next Steps**: Review plan, then start Phase 1 implementation with database migration.
