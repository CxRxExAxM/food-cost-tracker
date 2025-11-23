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

## ✅ Phase 4: Cost Calculations (COMPLETE)
**Goal**: Real-time recipe cost analysis

### Backend
- [x] Implement `/recipes/{id}/cost` endpoint
- [x] Calculate ingredient costs from latest prices
- [x] Handle sub-recipe cost recursion
- [x] Calculate cost per serving
- [x] Return cost breakdown by ingredient
- [x] Handle missing price data gracefully

### Frontend
- [x] Display total cost
- [x] Display cost per serving
- [x] Show cost breakdown table
- [x] Highlight ingredients with no price data
- [x] Add cost percentage by ingredient
- [x] Make cost panel collapsible

### Components Built
- [x] RecipeCost component (with collapsible panel)
- [x] CostBreakdownTable (inline in RecipeCost)
- [x] PriceWarning (inline in RecipeCost)

---

## ✅ Phase 5: Allergen Management (COMPLETE)
**Goal**: Allergen tracking from common products to recipes

### Backend
- [x] Update common_products PATCH to handle allergens (already worked)
- [x] Calculate recipe allergens from ingredients
- [x] Return allergen summary with recipe cost endpoint

### Frontend (Products Page)
- [x] Build allergen modal for common products
- [x] Add allergen checkboxes (16 total)
- [x] Show allergen indicators on product badges

### Frontend (Recipes Page)
- [x] Display recipe allergen summary
- [x] Show dietary flags (Vegan/Vegetarian)
- [x] Allergen icons/badges

### Components Built
- [x] AllergenModal (in Products.jsx)
- [x] Allergen badges on common product display
- [x] Allergen summary in RecipeCost component

---

## Phase 6: Advanced Features
**Goal**: Polish and advanced functionality

### Recipes
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

### Products
- [x] CSV upload UI for vendor price lists (with vendor-specific cleaning)
- [ ] Manual product entry form
- [ ] Price history view per product
- [ ] Product merge/deduplication tool
- [ ] Bulk product editing

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
**Phase 4**: ✅ COMPLETE
**Phase 5**: ✅ COMPLETE
**Next Steps**: Ready for Phase 6 - Advanced Features

---

## Vendor Import Workflow

### Overview
The system supports importing price lists from multiple vendors. Each vendor has unique file formats that require specific cleaning operations. The goal is to make imports seamless for users - they simply select the vendor and upload the raw file.

### Supported Vendors
| Vendor | File Format | Header Row | Special Handling |
|--------|-------------|------------|------------------|
| Sysco | CSV/Excel | Row 1 | Unit `#` → `LB`, calculates Unit $ |
| Vesta | Excel (.xls) | Row 10 | Parses `Packaging` column into Pack/Size/Unit |
| SM Seafood | CSV/Excel | Row 0 | TBD |
| Shamrock | CSV/Excel | Row 0 | TBD |
| Noble Bread | CSV/Excel | Row 0 | TBD |
| Sterling | CSV/Excel | Row 0 | TBD |

### Import Flow
1. **User uploads raw vendor file** via Products page
2. **Select vendor** from dropdown (determines cleaning rules)
3. **Backend applies vendor-specific cleaning**:
   - Reads file with correct header row
   - Drops unnecessary columns
   - Parses/normalizes packaging info into `Pack`, `Size`, `Unit`
   - Renames columns to standard format (`Desc`, `SUPC`, `Case $`, etc.)
   - Applies unit normalizations (e.g., `BK` → `PACK`, `HG` → `GAL`)
4. **Data imports to database**:
   - Creates new products if not found
   - Updates prices if product exists
   - Links products to distributor

### Standard Column Format (Post-Cleaning)
All vendor files are normalized to these columns before database import:
- `Desc` - Product description/name
- `SUPC` - Vendor SKU/product number
- `Brand` - Brand name (optional)
- `Pack` - Number of units per case
- `Size` - Size of each unit
- `Unit` - Unit of measure (LB, OZ, CT, EA, GAL, etc.)
- `Case $` - Price per case
- `Unit $` - Price per unit (calculated if not provided)

### Unit Normalization
All units are normalized to UPPERCASE and mapped to database entries:
- `#` → `LB`
- `BK` (Basket) → `PACK`
- `BU` (Bunch) → `BUNCH`
- `HG` (Half-Gallon) → `GAL` (with size × 0.5)
- `GL` → `GAL`
- `LT` → `L`

### CLI Scripts
Each vendor also has a standalone CLI cleaning script for manual processing:
- `clean_sysco.py`
- `clean_vesta.py`
- `clean_smseafood.py`
- `clean_shamrock.py`
- `clean_noblebread.py`
- `clean_sterling.py`

Usage: `venv/bin/python3 clean_<vendor>.py <input_file> [output_csv]`

### Adding New Vendors
1. Add vendor config to `api/app/routers/uploads.py` → `VENDOR_CONFIGS`
2. Add vendor to `distributors` table in database
3. Create CLI script `clean_<vendor>.py` (optional, for manual use)
4. Document header row, column mappings, and special handling

---

## Notes

- Each phase should be fully tested before moving to the next
- UI/UX should be iterated based on user feedback
- Performance optimizations should be considered for large datasets
- All features should work without sub-recipes first, then add sub-recipe support
