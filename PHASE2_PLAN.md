# Phase 2: Outlet Management UI

**Status**: 🔄 **IN PROGRESS** (Days 1-2 Complete, Day 5 Next)
**Started**: December 12, 2024
**Progress**: 2/7 days (29%)
**Goal**: Build complete frontend interface for multi-outlet management

**Resume Guide**: See `RESUME_DEC12_PHASE2.md` for detailed next steps

---

## 🎯 Objectives

Enable users to:
1. View all outlets in their organization
2. Create, edit, and manage outlets (admin only)
3. Assign users to specific outlets (admin only)
4. Switch between outlets when creating products/recipes
5. See which outlet each product/recipe belongs to
6. View statistics per outlet

---

## 📋 Features to Build

### 1. Outlet List Page (`/outlets`)
**Priority**: HIGH
**Estimated**: 1 day

**What to Build**:
- Table/card view of all outlets
- "Create New Outlet" button (admin only)
- Edit/Delete actions (admin only)
- Quick stats per outlet (products count, recipes count, users count)
- Search/filter outlets
- Responsive design

**API Endpoints Used**:
- `GET /outlets` - List all outlets
- `GET /outlets/{id}/stats` - Get outlet statistics
- `POST /outlets` - Create outlet (admin)
- `DELETE /outlets/{id}` - Delete outlet (admin)

**Components to Create**:
- `OutletList.jsx` - Main page component
- `OutletCard.jsx` - Individual outlet display
- `CreateOutletModal.jsx` - Modal for creating new outlet

---

### 2. Outlet Detail Page (`/outlets/:id`)
**Priority**: HIGH
**Estimated**: 1 day

**What to Build**:
- Outlet information display
- Edit outlet details (admin only)
- Statistics dashboard (products, recipes, users, imports)
- List of users assigned to this outlet
- Quick view of recent products/recipes in this outlet
- Assign/remove users from outlet (admin only)

**API Endpoints Used**:
- `GET /outlets/{id}` - Get outlet details
- `PATCH /outlets/{id}` - Update outlet
- `GET /outlets/{id}/stats` - Statistics
- `GET /outlets/{id}/users` - Users in outlet
- `POST /outlets/{id}/users/{user_id}` - Assign user
- `DELETE /outlets/{id}/users/{user_id}` - Remove user

**Components to Create**:
- `OutletDetail.jsx` - Main detail page
- `OutletStats.jsx` - Statistics cards
- `OutletUsers.jsx` - User management section
- `EditOutletModal.jsx` - Edit outlet modal
- `AssignUserModal.jsx` - Assign user to outlet modal

---

### 3. Outlet Selector Component
**Priority**: CRITICAL
**Estimated**: 1 day

**What to Build**:
- Dropdown selector to choose current outlet
- Show current outlet in navbar/header
- Remember user's last selected outlet (localStorage)
- Filter products/recipes by selected outlet automatically
- Global context for current outlet

**Implementation**:
- Create `OutletContext.jsx` - React Context for outlet state
- Create `OutletSelector.jsx` - Dropdown component
- Add to Header/Navbar
- Persist selection in localStorage

**Used In**:
- Products page (filter by outlet)
- Recipes page (filter by outlet)
- Create product form (default outlet)
- Create recipe form (default outlet)
- Upload CSV form (assign to outlet)

---

### 4. Product/Recipe Forms - Add Outlet Field
**Priority**: HIGH
**Estimated**: 1 day

**What to Build**:
- Add "Outlet" dropdown to product create/edit forms
- Add "Outlet" dropdown to recipe create/edit forms
- Default to currently selected outlet
- Show outlet name on product/recipe cards
- Filter by outlet in lists

**Forms to Update**:
- `ProductForm.jsx` (or wherever product creation is)
- `RecipeForm.jsx` (or wherever recipe creation is)
- Product list/cards - show outlet badge
- Recipe list/cards - show outlet badge

**API Changes**:
- Send `outlet_id` in POST /products
- Send `outlet_id` in POST /recipes (as query param)
- Display `outlet_id` from API responses

---

### 5. User Management - Outlet Assignment
**Priority**: MEDIUM
**Estimated**: 1 day

**What to Build**:
- View which outlets a user has access to
- Assign user to multiple outlets (admin only)
- Remove user from outlets (admin only)
- Show org-wide admin status (user with no outlet restrictions)
- User detail page with outlet assignments

**Where to Build**:
- Update existing user management page
- Add "Outlet Assignments" section
- Show badges for assigned outlets
- Assign/remove buttons (admin only)

**API Endpoints Used**:
- `POST /outlets/{outlet_id}/users/{user_id}`
- `DELETE /outlets/{outlet_id}/users/{user_id}`
- `GET /outlets/{outlet_id}/users`

---

### 6. Visual Improvements
**Priority**: MEDIUM
**Estimated**: 1-2 days

**What to Build**:
- Outlet badge component (color-coded)
- Outlet icons/avatars
- Statistics cards with charts
- Empty states ("No outlets yet")
- Loading states
- Error states
- Success/error toast notifications
- Consistent styling with existing app

---

## 🎨 UI/UX Design

### Design System
- **Colors**: Use existing color scheme
- **Components**: Match existing component library
- **Layout**: Consistent with current pages
- **Responsiveness**: Mobile-first design

### Key Components

#### Outlet Card
```
┌─────────────────────────────────────┐
│ 🏢 Main Kitchen                     │
│ Building A - 1st Floor              │
│                                     │
│ Products: 65  Recipes: 12  Users: 3 │
│                                     │
│ [View Details] [Edit] [Delete]     │
└─────────────────────────────────────┘
```

#### Outlet Selector (in Header)
```
┌─────────────────────┐
│ 🏢 Main Kitchen  ▼  │
├─────────────────────┤
│ Main Kitchen        │
│ Banquet Kitchen     │
│ Pastry Shop         │
│ All Outlets (Admin) │
└─────────────────────┘
```

#### Outlet Badge (on Products/Recipes)
```
Product Card:
┌─────────────────────────────────┐
│ Organic Tomatoes                │
│ 🏢 Main Kitchen    Pack: 25/1lb │
│ $45.00                          │
└─────────────────────────────────┘
```

---

## 🗂️ File Structure

```
frontend/src/
├── components/
│   ├── outlets/
│   │   ├── OutletList.jsx          (NEW)
│   │   ├── OutletCard.jsx          (NEW)
│   │   ├── OutletDetail.jsx        (NEW)
│   │   ├── OutletStats.jsx         (NEW)
│   │   ├── OutletSelector.jsx      (NEW)
│   │   ├── OutletBadge.jsx         (NEW)
│   │   ├── CreateOutletModal.jsx   (NEW)
│   │   ├── EditOutletModal.jsx     (NEW)
│   │   └── AssignUserModal.jsx     (NEW)
│   └── ... (existing components)
├── contexts/
│   ├── OutletContext.jsx           (NEW)
│   └── ... (existing contexts)
├── services/
│   ├── api/
│   │   ├── outlets.js              (NEW)
│   │   └── ... (existing API services)
└── pages/
    ├── OutletsPage.jsx             (NEW)
    ├── OutletDetailPage.jsx        (NEW)
    └── ... (existing pages)
```

---

## 🔌 API Integration

### New API Service (`frontend/src/services/api/outlets.js`)

```javascript
import api from './client';

export const outletsAPI = {
  // List outlets
  list: () => api.get('/outlets'),

  // Get outlet details
  get: (outletId) => api.get(`/outlets/${outletId}`),

  // Get outlet statistics
  getStats: (outletId) => api.get(`/outlets/${outletId}/stats`),

  // Create outlet
  create: (data) => api.post('/outlets', data),

  // Update outlet
  update: (outletId, data) => api.patch(`/outlets/${outletId}`, data),

  // Delete outlet
  delete: (outletId) => api.delete(`/outlets/${outletId}`),

  // Get users in outlet
  getUsers: (outletId) => api.get(`/outlets/${outletId}/users`),

  // Assign user to outlet
  assignUser: (outletId, userId) =>
    api.post(`/outlets/${outletId}/users/${userId}`),

  // Remove user from outlet
  removeUser: (outletId, userId) =>
    api.delete(`/outlets/${outletId}/users/${userId}`)
};
```

---

## 🚦 Implementation Order (REVISED)

**Original Plan**: Days 1→2→3→4→5→6→7
**Revised Plan**: Days 1→2→5→6→7→3→4

**Reasoning**: Days 5-6 are the core value (filtering), so prioritize them.
Days 3-4 (detail page & user assignment) are nice-to-have, can be done later.

---

## 🚦 Implementation Order

### Day 1: Setup & Outlet Context ✅ COMPLETE
- [x] Phase 1 Backend Complete
- [x] Create Phase 2 plan
- [x] Create outlet API service
- [x] Create OutletContext
- [x] Create basic OutletSelector component
- [x] Add to Header/Navbar

### Day 2: Outlet List Page ✅ COMPLETE
- [x] Create OutletList page
- [x] Create OutletCard component
- [x] Implement list/grid view
- [x] Add search/filter
- [x] Create CreateOutletModal
- [x] Test create outlet flow

### Day 3: Outlet Detail Page
- [ ] Create OutletDetail page
- [ ] Create OutletStats component
- [ ] Display outlet information
- [ ] Create EditOutletModal
- [ ] Test edit/delete flows

### Day 4: User Assignment
- [ ] Create OutletUsers component
- [ ] Create AssignUserModal
- [ ] Implement assign user flow
- [ ] Implement remove user flow
- [ ] Show org-wide admin status

### Day 5: Product/Recipe Integration
- [ ] Add outlet field to ProductForm
- [ ] Add outlet field to RecipeForm
- [ ] Add OutletBadge to product cards
- [ ] Add OutletBadge to recipe cards
- [ ] Update upload CSV form

### Day 6: Polish & Testing
- [ ] Add outlet selector to header
- [ ] Filter products by selected outlet
- [ ] Filter recipes by selected outlet
- [ ] Add loading/error states
- [ ] Add empty states
- [ ] Mobile responsive testing

### Day 7: Final Testing & Deploy
- [ ] End-to-end testing
- [ ] Cross-browser testing
- [ ] Fix any bugs
- [ ] Deploy to dev
- [ ] Deploy to production

---

## 🧪 Testing Plan

### Manual Testing Checklist
- [ ] Create new outlet
- [ ] Edit outlet details
- [ ] Delete outlet (should prevent if has data)
- [ ] Assign user to outlet
- [ ] Remove user from outlet
- [ ] Switch outlets using selector
- [ ] Create product in specific outlet
- [ ] Create recipe in specific outlet
- [ ] Filter products by outlet
- [ ] Filter recipes by outlet
- [ ] Upload CSV to specific outlet
- [ ] Org-wide admin sees all outlets
- [ ] Outlet-scoped user sees only assigned outlets

### Edge Cases
- [ ] User with no outlet assignments (org-wide admin)
- [ ] User with multiple outlet assignments
- [ ] Outlet with no products/recipes
- [ ] Outlet with products/recipes (prevent deletion)
- [ ] Creating product without outlet selection
- [ ] Switching outlets while creating product

---

## 🎯 Success Criteria

Phase 2 is complete when:
- [ ] Outlet list page functional
- [ ] Outlet detail page functional
- [ ] Outlet selector working in header
- [ ] Users can create/edit/delete outlets
- [ ] Users can assign other users to outlets
- [ ] Product creation includes outlet selection
- [ ] Recipe creation includes outlet selection
- [ ] Products show which outlet they belong to
- [ ] Recipes show which outlet they belong to
- [ ] Filtering by outlet works
- [ ] All tests passing
- [ ] Mobile responsive
- [ ] Deployed to dev and production

---

## 📝 Notes

### Current Frontend Stack
- React 18
- React Router v6
- Axios for API calls
- Context API for state
- Custom CSS (check existing styling)

### Questions to Answer
1. What does the current frontend structure look like?
2. Where are products/recipes forms located?
3. What's the current routing setup?
4. What's the existing component library/design system?
5. Where is the Header/Navbar component?

---

Let's get started! 🚀
