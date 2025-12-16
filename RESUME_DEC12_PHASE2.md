# Resume Guide - Phase 2 Multi-Outlet UI
**Date**: December 12, 2024
**Session End**: Day 2 Complete
**Next Session**: Day 5 - Product/Recipe Integration

---

## 📍 Where We Are

### ✅ Completed Today (Days 1-2)

**Day 1: Outlet Context & Selector**
- Created outlet API service layer (`frontend/src/services/api/outlets.js`)
- Created OutletContext for global state management
- Created OutletSelector dropdown component
- Integrated into Navigation bar
- LocalStorage persistence working
- **Status**: ✅ Fully deployed and working

**Day 2: Outlet List Page**
- Created `/outlets` page with grid/list views
- Created OutletCard component with live stats
- Created Create/Edit outlet modals
- Added search/filter functionality
- Added admin-only "Outlets" nav link
- **Status**: ✅ Fully deployed and working

### 🎯 Current State

**What's Working:**
- Outlet selector in navigation (shows "Default Outlet" and "Test Kitchen")
- Can switch between outlets (selection persists in localStorage)
- Can view all outlets at `/outlets` page
- Can create new outlets (admin only)
- Can edit/delete outlets (admin only)
- Live statistics per outlet (products, recipes, users counts)

**What's NOT Working Yet:**
- Products page doesn't filter by selected outlet (shows all products)
- Recipes page doesn't filter by selected outlet (shows all recipes)
- No outlet badges on product/recipe cards
- No outlet field when creating products/recipes

**User Testing Discovered:**
- Created a recipe in Test Kitchen outlet
- Switched to Default Outlet
- Recipe still shows (expected - filtering not implemented yet)

---

## 🚀 What's Next: Day 5 (Tomorrow)

### Goal: Product/Recipe Integration

Make the outlet selector actually filter products and recipes!

### Tasks for Tomorrow

**1. Add OutletBadge Component** (~30 min)
```
Create: frontend/src/components/outlets/OutletBadge.jsx
Purpose: Show which outlet each item belongs to
Display: 🏢 Main Kitchen (badge on cards)
```

**2. Update Products Page** (~2 hours)
```
File: frontend/src/pages/Products.jsx
Changes:
- Import useOutlet hook
- Filter products by currentOutlet.id
- Add OutletBadge to product cards
- Show "All Outlets" when selected
```

**3. Update Recipes Page** (~2 hours)
```
File: frontend/src/pages/Recipes.jsx
Changes:
- Import useOutlet hook
- Filter recipes by currentOutlet.id
- Add OutletBadge to recipe cards
- Show "All Outlets" when selected
```

**4. Add Outlet Field to Product Form** (~1 hour)
```
File: (wherever product create form is)
Changes:
- Add outlet dropdown
- Default to currentOutlet
- Send outlet_id to API
```

**5. Add Outlet Field to Recipe Form** (~1 hour)
```
File: (wherever recipe create form is)
Changes:
- Add outlet dropdown
- Default to currentOutlet
- Send outlet_id to API (query param)
```

**Estimated Time**: 6-7 hours (1 full day)

---

## 📁 Key Files Reference

### Backend (Already Complete - Phase 1)

**API Endpoints:**
```
GET    /outlets                    - List all outlets
GET    /outlets/{id}               - Get outlet details
GET    /outlets/{id}/stats         - Get statistics
POST   /outlets                    - Create outlet (admin)
PATCH  /outlets/{id}               - Update outlet (admin)
DELETE /outlets/{id}               - Delete outlet (admin)

GET    /products?outlet_id={id}    - Products filtered by outlet
GET    /recipes?outlet_id={id}     - Recipes filtered by outlet
```

**Database:**
```
outlets table - has id, name, location, description
products.outlet_id - foreign key to outlets
recipes.outlet_id - foreign key to outlets
```

### Frontend (What We Built)

**Context & State:**
```javascript
// OutletContext provides:
{
  outlets,          // Array of all outlets
  currentOutlet,    // Currently selected outlet
  selectOutlet,     // Function to change outlet
  createOutlet,     // Create new outlet
  updateOutlet,     // Update outlet
  deleteOutlet,     // Delete outlet
  isOrgWideAdmin    // Check admin status
}

// Usage:
import { useOutlet } from '../contexts/OutletContext';
const { currentOutlet, outlets } = useOutlet();
```

**API Service:**
```javascript
import { outletsAPI } from '../services/api/outlets';

outletsAPI.list()           // Get all outlets
outletsAPI.get(id)          // Get one outlet
outletsAPI.getStats(id)     // Get statistics
outletsAPI.create(data)     // Create
outletsAPI.update(id, data) // Update
outletsAPI.delete(id)       // Delete
```

**Components:**
```
frontend/src/
├── contexts/
│   └── OutletContext.jsx          (Global state)
├── services/api/
│   ├── client.js                  (Axios instance)
│   └── outlets.js                 (Outlet API calls)
├── components/
│   ├── Navigation.jsx             (Has OutletSelector)
│   └── outlets/
│       ├── OutletSelector.jsx     (Dropdown in nav)
│       ├── OutletCard.jsx         (Card display)
│       ├── CreateOutletModal.jsx  (Create form)
│       └── EditOutletModal.jsx    (Edit form)
└── pages/
    └── Outlets.jsx                (List page)
```

---

## 🐛 Known Issues

**None** - Everything deployed and working as expected!

**Previous Issues (Fixed):**
- ✅ Import path for AuthContext (fixed)
- ✅ API response structure (response.data vs response.data.outlets)

---

## 🔍 How to Test Current Functionality

### Test Outlet Selector
1. Go to https://food-cost-tracker-dev.onrender.com
2. Login as admin (mike.myers@fairmont.com)
3. Look at navigation bar - should see "🏢 Default Outlet"
4. Click dropdown - should see:
   - 🌐 All Outlets
   - 🏢 Default Outlet
   - 🏢 Test Kitchen
5. Select different outlet - selection should persist on refresh

### Test Outlets Page
1. Click "Outlets" in navigation (admin only)
2. Should see 2 outlets in grid view
3. Try grid/list toggle (top right)
4. Try search box
5. Click "+ Create Outlet"
6. Create a test outlet
7. Click "Edit" on any outlet
8. Click "Delete" → "Confirm Delete?"

### Test Current Limitation (What We'll Fix Tomorrow)
1. Go to Products or Recipes page
2. Change outlet in selector
3. Notice: Products/Recipes don't filter (shows all)
4. Create a new recipe
5. Notice: No outlet field in form
6. **This is what we'll fix in Day 5!**

---

## 💾 Git Status

**Branch**: `dev`
**Latest Commits**:
```
f1b6bbb - docs: Mark Phase 2 Day 2 as complete
8536990 - feat: Phase 2 Day 2 - Outlet List Page complete
fcb5b95 - fix: Correct outlets API response structure
9faf50f - fix: Correct import path for AuthContext
e7b1d5a - docs: Mark Phase 2 Day 1 as complete
6587c73 - feat: Phase 2 Day 1 - Outlet selector and context
```

**All Changes Committed**: ✅ Yes
**All Changes Pushed**: ✅ Yes
**Deployed to Dev**: ✅ Yes

---

## 📊 Progress Tracker

**Phase 2: Multi-Outlet UI**
- [x] Day 1: Setup & Outlet Context (Dec 12)
- [x] Day 2: Outlet List Page (Dec 12)
- [ ] Day 5: Product/Recipe Integration (NEXT - Dec 13)
- [ ] Day 6: Filtering & Polish (Dec 13)
- [ ] Day 7: Final Testing & Deploy
- [ ] Day 3: Outlet Detail Page (Optional - later)
- [ ] Day 4: User Assignment (Optional - later)

**Lines of Code So Far**: ~1,769 lines (Days 1-2)

---

## 🎯 Tomorrow's Game Plan

### Morning: Product/Recipe Integration (Day 5)

**Step 1: Create OutletBadge** (30 min)
- Small component to show outlet name on cards
- Design: `🏢 Main Kitchen` in a badge/chip

**Step 2: Update Products Page** (2 hours)
- Add filtering by currentOutlet
- Add OutletBadge to each product card
- Test filtering works

**Step 3: Update Recipes Page** (2 hours)
- Add filtering by currentOutlet
- Add OutletBadge to each recipe card
- Test filtering works

**Step 4: Add Outlet to Forms** (2 hours)
- Product create/edit form - add outlet dropdown
- Recipe create/edit form - add outlet dropdown
- Default to currentOutlet
- Test creation with outlet assignment

### Afternoon: Filtering & Polish (Day 6)

**Already Done:**
- ✅ Outlet selector in header (Day 1)

**Todo:**
- Loading/error states
- Empty states ("No products in this outlet")
- Mobile responsive testing
- Cross-browser testing

**Estimated**: 3-4 hours

### End of Day: Testing & Deploy

- Test all functionality
- Verify outlet filtering works
- Test switching outlets updates products/recipes
- Commit and deploy

---

## 📝 Code Patterns to Follow

### Adding Outlet Filter to Pages

```javascript
import { useOutlet } from '../contexts/OutletContext';

function ProductsPage() {
  const { currentOutlet } = useOutlet();
  const [products, setProducts] = useState([]);

  useEffect(() => {
    fetchProducts();
  }, [currentOutlet]); // Re-fetch when outlet changes

  const fetchProducts = async () => {
    let url = '/products';

    // Filter by outlet if specific outlet selected
    if (currentOutlet && currentOutlet.id !== 'all') {
      url += `?outlet_id=${currentOutlet.id}`;
    }

    const response = await axios.get(url);
    setProducts(response.data.products);
  };

  // ... render products with OutletBadge
}
```

### Adding OutletBadge to Cards

```javascript
import OutletBadge from '../components/outlets/OutletBadge';

function ProductCard({ product }) {
  return (
    <div className="product-card">
      <h3>{product.name}</h3>
      <OutletBadge outletId={product.outlet_id} />
      {/* ... rest of card */}
    </div>
  );
}
```

### Adding Outlet Field to Forms

```javascript
import { useOutlet } from '../contexts/OutletContext';

function ProductForm() {
  const { outlets, currentOutlet } = useOutlet();
  const [formData, setFormData] = useState({
    name: '',
    outlet_id: currentOutlet?.id || outlets[0]?.id
  });

  return (
    <form>
      {/* ... other fields */}

      <label>Outlet</label>
      <select
        value={formData.outlet_id}
        onChange={(e) => setFormData({...formData, outlet_id: e.target.value})}
      >
        {outlets.map(outlet => (
          <option key={outlet.id} value={outlet.id}>
            {outlet.name}
          </option>
        ))}
      </select>
    </form>
  );
}
```

---

## 🎓 Quick Refresher: Tech Stack

**Frontend:**
- React 18 with hooks
- React Router v6
- Context API for state
- Axios for API calls
- Custom CSS (dark theme)

**Backend:**
- FastAPI (already complete)
- PostgreSQL database
- JWT authentication

**Key Patterns:**
- Context Providers for global state
- Custom hooks (useOutlet, useAuth)
- Protected routes
- API service layer

---

## 📞 Questions to Consider Tomorrow

1. **Where are the Products and Recipes pages?**
   - Need to find the actual files to update
   - Look in `frontend/src/pages/`

2. **What do product/recipe cards look like?**
   - Need to see current structure to add badges

3. **Where are the create forms?**
   - Could be modals or separate pages
   - Need to find and add outlet dropdown

4. **Does the backend API support filtering?**
   - ✅ Yes! Backend accepts `?outlet_id=X` query param
   - Already implemented in Phase 1

---

## ✅ Success Criteria for Tomorrow

By end of tomorrow, you should be able to:

1. **Switch outlets** - Select "Test Kitchen" in dropdown
2. **See filtered recipes** - Only see recipes created in Test Kitchen
3. **Switch to Default Outlet** - See only Default Outlet recipes
4. **See outlet badges** - Each product/recipe shows which outlet it belongs to
5. **Create with outlet** - New products/recipes have outlet dropdown
6. **Select "All Outlets"** - See all products/recipes (admin only)

**This is the killer feature!** Each outlet has its own product catalog and pricing.

---

## 🎊 What We Accomplished Today

- Built outlet selector with persistence
- Built complete outlet management page
- Created 9 new components
- Wrote ~1,769 lines of production code
- Zero compilation errors
- Fully deployed to dev environment
- Everything working perfectly

**Great work today!** Ready to finish the core functionality tomorrow! 🚀

---

**End of Session - December 12, 2024**
**Resume from: Day 5 - Product/Recipe Integration**
