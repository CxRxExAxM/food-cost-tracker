# Banquet Menus Module Plan
**Date:** January 21, 2025
**Branch:** `dev` (will create `feature/banquet-menus`)
**Status:** Planning

---

## Overview

Add banquet menu management to the Food Cost module, allowing users to:
- View/manage menus organized by Meal Period → Service Type → Menu Name
- Track menu items and their prep items
- Link prep items to existing products or recipes for cost calculation
- See food cost metrics (target vs actual, variance, price vs cost)

---

## Data Model

### Hierarchy
```
Meal Period (Breakfast, Lunch, Dinner)
  └── Service Type (Buffet, Plated, Passed, etc.)
        └── Menu (Good Morning Starter, $80/person)
              └── Menu Item (Oatmeal, Omelets)
                    └── Prep Item (Brown Sugar → linked to Product)
```

### Schema

```sql
-- =============================================
-- Table 1: banquet_menus
-- The main menu container
-- =============================================
CREATE TABLE banquet_menus (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    outlet_id INTEGER NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,

    -- Hierarchy identifiers
    meal_period VARCHAR(50) NOT NULL,           -- 'Breakfast', 'Lunch', 'Dinner', etc.
    service_type VARCHAR(50) NOT NULL,          -- 'Buffet', 'Plated', 'Passed', etc.
    name VARCHAR(255) NOT NULL,                 -- 'Good Morning Starter'

    -- Pricing
    price_per_person DECIMAL(10,2),             -- $80.00

    -- Guest thresholds
    min_guest_count INTEGER,                    -- Minimum guests (e.g., 50)
    under_min_surcharge DECIMAL(10,2),          -- Per-person surcharge if under minimum

    -- Food cost targets
    target_food_cost_pct DECIMAL(5,2),          -- User-provided target (e.g., 28.00)

    -- Metadata
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Indexes
    CONSTRAINT unique_menu_per_outlet UNIQUE (outlet_id, meal_period, service_type, name)
);

CREATE INDEX idx_banquet_menus_org ON banquet_menus(organization_id);
CREATE INDEX idx_banquet_menus_outlet ON banquet_menus(outlet_id);
CREATE INDEX idx_banquet_menus_meal_period ON banquet_menus(meal_period);
CREATE INDEX idx_banquet_menus_service_type ON banquet_menus(service_type);

-- =============================================
-- Table 2: banquet_menu_items
-- Items within a menu (Oatmeal, Omelets, etc.)
-- =============================================
CREATE TABLE banquet_menu_items (
    id SERIAL PRIMARY KEY,
    banquet_menu_id INTEGER NOT NULL REFERENCES banquet_menus(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,                 -- 'Oatmeal', 'Farm Fresh Scrambled Eggs'
    display_order INTEGER DEFAULT 0,            -- For ordering in UI

    -- Enhancement/upsell pricing
    is_enhancement INTEGER DEFAULT 0,           -- 1 if this is an add-on
    additional_price DECIMAL(10,2),             -- Extra cost per person for enhancements

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_banquet_menu_items_menu ON banquet_menu_items(banquet_menu_id);

-- =============================================
-- Table 3: banquet_prep_items
-- Prep items within a menu item (ingredients/components)
-- =============================================
CREATE TABLE banquet_prep_items (
    id SERIAL PRIMARY KEY,
    banquet_menu_item_id INTEGER NOT NULL REFERENCES banquet_menu_items(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,                 -- 'Brown Sugar', 'Liquid Eggs'
    display_order INTEGER DEFAULT 0,

    -- Amount per guest
    amount_per_guest DECIMAL(10,4),             -- e.g., 0.25 (oz per guest)
    amount_unit VARCHAR(20),                    -- 'oz', 'each', 'cups' (freeform for now)

    -- Optional categorization (future lookup tables)
    vessel VARCHAR(100),                        -- 'Chafing Dish', 'Pitcher'
    responsibility VARCHAR(100),                -- 'Hot Line', 'Pantry', 'Pastry'

    -- Link to product OR recipe (one or the other, not both)
    product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure only one link type
    CONSTRAINT check_single_link CHECK (
        (product_id IS NULL AND recipe_id IS NULL) OR
        (product_id IS NOT NULL AND recipe_id IS NULL) OR
        (product_id IS NULL AND recipe_id IS NOT NULL)
    )
);

CREATE INDEX idx_banquet_prep_items_menu_item ON banquet_prep_items(banquet_menu_item_id);
CREATE INDEX idx_banquet_prep_items_product ON banquet_prep_items(product_id);
CREATE INDEX idx_banquet_prep_items_recipe ON banquet_prep_items(recipe_id);
```

---

## Cost Calculation Logic

### Per Prep Item
```
prep_item_cost = (linked_product_or_recipe_unit_cost) × (amount_per_guest) × (guest_count)
```

### Per Menu Item
```
menu_item_cost = SUM(prep_item_costs) + additional_price (if enhancement)
```

### Per Menu
```
menu_cost = SUM(menu_item_costs)
menu_revenue = (price_per_person × guest_count) + surcharge_if_applicable
actual_fc_pct = (menu_cost / menu_revenue) × 100
variance = target_food_cost_pct - actual_fc_pct
```

### Surcharge Logic
```
if (guest_count < min_guest_count):
    surcharge = under_min_surcharge × guest_count
else:
    surcharge = 0
```

---

## API Endpoints

### Banquet Menus CRUD
```
GET    /api/banquet-menus                    # List menus (filtered by outlet)
GET    /api/banquet-menus/:id                # Get single menu with items & prep items
POST   /api/banquet-menus                    # Create menu
PUT    /api/banquet-menus/:id                # Update menu
DELETE /api/banquet-menus/:id                # Delete menu (cascades)

# Filtering parameters:
# - outlet_id (required unless viewing "all")
# - meal_period (optional)
# - service_type (optional)
```

### Menu Items
```
POST   /api/banquet-menus/:menuId/items      # Add menu item
PUT    /api/banquet-menu-items/:id           # Update menu item
DELETE /api/banquet-menu-items/:id           # Delete menu item
PATCH  /api/banquet-menu-items/reorder       # Reorder items (batch update)
```

### Prep Items
```
POST   /api/banquet-menu-items/:itemId/prep  # Add prep item
PUT    /api/banquet-prep-items/:id           # Update prep item (including linking)
DELETE /api/banquet-prep-items/:id           # Delete prep item
PATCH  /api/banquet-prep-items/reorder       # Reorder prep items
```

### Cost Calculation
```
GET    /api/banquet-menus/:id/cost?guests=50 # Calculate menu cost for guest count
```

### Dropdown Options
```
GET    /api/banquet-menus/meal-periods       # Distinct meal periods for outlet
GET    /api/banquet-menus/service-types      # Distinct service types for outlet (filtered by meal_period)
```

---

## Frontend Structure

### New Page: `/banquet-menus`

```
┌─────────────────────────────────────────────────────────────────┐
│  Navigation                                                      │
├─────────────────────────────────────────────────────────────────┤
│  BANQUET MENUS                                     [+ New Menu] │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐│
│  │ Meal Period │ │ Service Type│ │ Menu Name                   ││
│  │ [Breakfast▼]│ │ [Buffet   ▼]│ │ [Good Morning Starter     ▼]││
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│  DASHBOARD                                              [Edit ⚙]│
│  ┌────────────┬────────────┬────────────┬────────────┐          │
│  │ Menu Price │ Menu Cost  │ Target FC  │ Actual FC  │          │
│  │ $80.00/pp  │ $24.50/pp  │ 28.0%      │ 30.6%      │          │
│  └────────────┴────────────┴────────────┴────────────┘          │
│                                                                  │
│  ┌────────────┬────────────┬────────────┐                       │
│  │ Guests     │ Min Guests │ Variance   │                       │
│  │ [50    ]   │ 50         │ -2.6% ▼    │                       │
│  └────────────┴────────────┴────────────┘                       │
│  Surcharge: $0.00 (at/above minimum)                            │
├─────────────────────────────────────────────────────────────────┤
│  MENU ITEMS                                       [+ Add Item]  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ▼ Oatmeal                                      $0.45/guest  ││
│  │   ┌──────────────┬─────────┬────────────────┬─────────────┐ ││
│  │   │ Prep Item    │ Amount  │ Linked To      │ Cost/Guest  │ ││
│  │   ├──────────────┼─────────┼────────────────┼─────────────┤ ││
│  │   │ Dried Fruit  │ 0.5 oz  │ Dried Fruit Mix│ $0.25       │ ││
│  │   │ Brown Sugar  │ 0.25 oz │ [+ Link]       │ --          │ ││
│  │   │ Cinnamon     │ pinch   │ [+ Link]       │ --          │ ││
│  │   └──────────────┴─────────┴────────────────┴─────────────┘ ││
│  │   [+ Add Prep Item]                                         ││
│  │                                                              ││
│  │ ▶ Farm Fresh Scrambled Eggs                    $0.82/guest  ││
│  │ ▶ Omelets                                      $1.20/guest  ││
│  │ ▶ Applewood Smoked Bacon                       $0.95/guest  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

```
frontend/src/pages/BanquetMenus/
├── BanquetMenus.jsx          # Main page component
├── BanquetMenus.css          # Styles
├── components/
│   ├── MenuDashboard.jsx     # Stats cards + guest input + edit modal
│   ├── MenuItemList.jsx      # Expandable accordion of menu items
│   ├── MenuItemRow.jsx       # Single menu item (expandable)
│   ├── PrepItemTable.jsx     # Table of prep items within menu item
│   ├── PrepItemRow.jsx       # Single prep item row with linking
│   ├── LinkProductModal.jsx  # Modal to search/link product or recipe
│   ├── NewMenuModal.jsx      # Modal to create new menu
│   └── EditMenuModal.jsx     # Modal to edit menu settings (dashboard edit)
```

### State Management

```javascript
// BanquetMenusContext.jsx (or local state)
{
  // Dropdown selections
  selectedMealPeriod: 'Breakfast',
  selectedServiceType: 'Buffet',
  selectedMenuId: 123,

  // Current menu data
  currentMenu: {
    id: 123,
    meal_period: 'Breakfast',
    service_type: 'Buffet',
    name: 'Good Morning Starter',
    price_per_person: 80.00,
    min_guest_count: 50,
    under_min_surcharge: 10.00,
    target_food_cost_pct: 28.00,
    menu_items: [
      {
        id: 1,
        name: 'Oatmeal',
        display_order: 0,
        is_enhancement: false,
        additional_price: null,
        prep_items: [
          {
            id: 1,
            name: 'Dried Fruit',
            amount_per_guest: 0.5,
            amount_unit: 'oz',
            product_id: 456,
            product_name: 'Dried Fruit Mix',
            unit_cost: 0.50  // from linked product
          }
        ]
      }
    ]
  },

  // User input
  guestCount: 50,

  // Calculated values
  calculatedCost: {
    menu_cost_per_guest: 24.50,
    total_menu_cost: 1225.00,
    menu_revenue: 4000.00,
    actual_fc_pct: 30.6,
    variance: -2.6,
    surcharge: 0
  },

  // Dropdown options
  mealPeriods: ['Breakfast', 'Lunch', 'Dinner'],
  serviceTypes: ['Buffet', 'Plated', 'Passed'],
  menus: [{id: 1, name: 'Good Morning Starter'}, ...]
}
```

---

## Implementation Phases

### Phase 1: Database & Models
- [ ] Create migration file `008_add_banquet_menus.py`
- [ ] Add 3 tables with indexes and constraints
- [ ] Test migration up/down locally

### Phase 2: Backend API
- [ ] Create `api/app/routers/banquet_menus.py`
- [ ] Implement CRUD for menus, menu items, prep items
- [ ] Implement cost calculation endpoint
- [ ] Implement dropdown options endpoints
- [ ] Add to main.py router registration

### Phase 3: Frontend Page
- [ ] Create `BanquetMenus.jsx` with cascading dropdowns
- [ ] Build dashboard component with editable metrics
- [ ] Build accordion menu item list
- [ ] Build prep item table with linking functionality
- [ ] Create link product/recipe modal
- [ ] Add route to App.jsx
- [ ] Add navigation link

### Phase 4: Polish
- [ ] Add validation and error handling
- [ ] Inline editing for prep item amounts
- [ ] Drag-drop reordering (optional)
- [ ] Loading states
- [ ] Empty states

---

## Files to Create/Modify

### New Files
```
alembic/versions/008_add_banquet_menus.py
api/app/routers/banquet_menus.py
frontend/src/pages/BanquetMenus/BanquetMenus.jsx
frontend/src/pages/BanquetMenus/BanquetMenus.css
frontend/src/pages/BanquetMenus/components/MenuDashboard.jsx
frontend/src/pages/BanquetMenus/components/MenuItemList.jsx
frontend/src/pages/BanquetMenus/components/PrepItemTable.jsx
frontend/src/pages/BanquetMenus/components/LinkProductModal.jsx
frontend/src/pages/BanquetMenus/components/NewMenuModal.jsx
```

### Modified Files
```
api/app/main.py                    # Add router
frontend/src/App.jsx               # Add route
frontend/src/components/Navigation.jsx  # Add nav link
```

---

## Open Questions / Future Considerations

1. **Lookup tables**: Should meal_period, service_type, vessel, responsibility be lookup tables now, or freeform for MVP?
   - **Decision**: Freeform for MVP, can add lookups later

2. **Copy/duplicate menu**: Should users be able to duplicate a menu to create variations?
   - **Future feature**

3. **Menu versioning**: Track changes over time?
   - **Not needed for MVP**

4. **Bulk import**: User mentioned import is for dev, not users
   - **Skip for now**, can add later if needed

5. **Print/export**: PDF menu costing sheet?
   - **Future feature**

6. **Prep amount logic**: May need iteration once we see it in practice
   - Current approach: `amount_per_guest` × `guest_count`
   - May need adjustments for buffet minimums, batch sizing, etc.

---

## Design Decisions (Confirmed)

1. **New Menu modal**: Dropdowns for meal period/service type are selectable (not pre-populated from current view)
2. **Cascading dropdowns**: Filter progressively (selecting Breakfast shows only Breakfast service types)
3. **Prep amounts**: Start simple, iterate based on real-world testing

---

## Success Criteria

- [ ] User can select Meal Period → Service Type → Menu via dropdowns
- [ ] Dashboard shows price, cost, target FC, actual FC, variance
- [ ] User can input guest count and see costs recalculate
- [ ] Menu items display in expandable accordion
- [ ] Prep items show in table within each menu item
- [ ] User can link prep items to products or recipes
- [ ] Costs calculate correctly from linked items
- [ ] All CRUD operations work (create, edit, delete)
- [ ] Multi-tenant: menus are outlet-specific

---

**Ready for implementation approval.**
