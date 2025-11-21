# Recipe Module Implementation Phases

## ✅ Phase 0: Foundation (COMPLETE)
- [x] Database schema updates (allergens, method, category_path, sub_recipes)
- [x] Pydantic schemas updated
- [x] API router skeleton created
- [x] Frontend page skeleton created
- [x] CSS styling complete

## ✅ Phase 1: Basic CRUD & Editing (COMPLETE)
**Goal**: Create, view, edit, and delete recipes with basic functionality

### Backend
- [x] Implement full recipe CRUD operations
- [x] Add validation for required fields
- [x] Handle method JSON serialization properly
- [x] Add category_path search/filter

### Frontend
- [x] Make recipe metadata editable (name, path, yield, description)
- [x] Implement create new recipe form/modal
- [x] Add edit mode for recipe details
- [x] Implement save/cancel with dirty state tracking
- [x] Add delete confirmation dialog
- [x] Handle unsaved changes warning

### Components Built
- [x] RecipeCreateModal
- [x] Editable header fields (name, category_path)
- [x] Editable metadata fields (yield, description)
- [x] Save/Cancel buttons with dirty state

---

## ✅ Phase 2: Ingredients & Method (COMPLETE)
**Goal**: Full ingredient management and method step editing

### Backend
- [x] Implement add/remove ingredient endpoints
- [x] Add ingredient validation (either common_product_id OR sub_recipe_id)
- [x] Handle sub-recipe references
- [x] Return ingredient details with prices
- [x] PATCH endpoint for updating ingredients

### Frontend
- [x] Build ingredient autocomplete (common products)
- [x] Add ingredient inline editing
- [x] Implement remove ingredient
- [x] Build method step editor (numbered textboxes)
- [x] Add/remove/reorder steps
- [ ] Sub-recipe display logic (name, expand, jump) - Deferred to Phase 3

### Components Built
- [x] IngredientAutocomplete (inline)
- [x] MethodStepEditor (inline editable)
- [ ] SubRecipeExpander - Deferred to Phase 3

---

## ✅ Phase 3: Tree Explorer & Organization (COMPLETE)
**Goal**: VS Code-style folder tree for recipe organization

### Backend
- [x] Build tree structure from category_path (client-side)
- [x] Implement move recipe (change category_path via PATCH)
- [x] Add folder operations (create, rename, delete via recipe updates)

### Frontend
- [x] Build collapsible tree component
- [x] Implement folder expand/collapse
- [x] Add drag-and-drop for moving recipes
- [x] Context menu (right-click) for tree items
- [ ] Recipe duplication - Deferred to Phase 6

### Components Built
- [x] RecipeTree (inline in Recipes.jsx)
- [x] TreeNode component (folders + recipes)
- [x] ContextMenu component
- [x] Drag-and-drop with visual feedback

---

## Phase 4: Cost Calculations
**Goal**: Real-time recipe cost analysis

### Backend
- [ ] Implement `/recipes/{id}/cost` endpoint
- [ ] Calculate ingredient costs from latest prices
- [ ] Handle sub-recipe cost recursion
- [ ] Calculate cost per serving
- [ ] Return cost breakdown by ingredient
- [ ] Handle missing price data gracefully

### Frontend
- [ ] Display total cost
- [ ] Display cost per serving
- [ ] Show cost breakdown table
- [ ] Highlight ingredients with no price data
- [ ] Add cost percentage by ingredient
- [ ] Make cost panel collapsible

### Components to Build
- [ ] CostBreakdownTable
- [ ] PriceWarning component

---

## Phase 5: Allergen Management
**Goal**: Allergen tracking from common products to recipes

### Backend
- [ ] Update common_products PATCH to handle allergens
- [ ] Calculate recipe allergens from ingredients
- [ ] Return allergen summary with recipe

### Frontend (Products Page)
- [ ] Build allergen modal for common products
- [ ] Add allergen checkboxes (16 total)
- [ ] Show allergen indicators on product badges

### Frontend (Recipes Page)
- [ ] Display recipe allergen summary
- [ ] Show allergen warnings
- [ ] Allergen icons/badges

### Components to Build
- [ ] AllergenModal
- [ ] AllergenBadges
- [ ] AllergenSummary

---

## Phase 6: Advanced Features
**Goal**: Polish and advanced functionality

- [ ] Recipe search (name, ingredients, allergens)
- [ ] Bulk operations (tag recipes, batch move)
- [ ] Recipe templates
- [ ] Print/export recipe
- [ ] Recipe history/versioning
- [ ] Yield scaling (adjust quantities)
- [ ] Shopping list generation
- [ ] Price trend charts per recipe
- [ ] Batch cost comparison
- [ ] Unit conversions

---

## Tech Debt & Improvements
- [ ] **Virtual Folders**: Move from localStorage to database table for multi-device sync
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

---

## Current Status

**Phase 0**: ✅ COMPLETE
**Phase 1**: ✅ COMPLETE
**Phase 2**: ✅ COMPLETE
**Phase 3**: ✅ COMPLETE
**Next Steps**: Ready for Phase 4 - Cost Calculations

---

## Notes

- Each phase should be fully tested before moving to the next
- UI/UX should be iterated based on user feedback
- Performance optimizations should be considered for large datasets
- All features should work without sub-recipes first, then add sub-recipe support
