# Changelog

All notable changes to the Food Cost Tracker project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Excel-like inline editing for recipe ingredients table
- Autocomplete product search while typing ingredient names
- "Mapped?" column with ✓/× indicators for ingredient status
- Keyboard navigation (Tab, Enter, Escape, Arrow keys) for rapid data entry
- Auto-select text on focus for instant editing
- Debug endpoints for troubleshooting cost calculation issues
  - `/api/recipes/{recipe_id}/cost/debug` - Shows why costs aren't calculating
  - `/api/recipes/debug/common-product/{id}/products` - Shows product-outlet relationships

### Changed
- Removed "Text only" badge in favor of cleaner Mapped? column
- Ingredients now maintain insertion order (no longer reorder after edits)
- Recipe costs auto-update when ingredients are mapped to products
- Recipe `updated_at` timestamp updates when ingredients change

### Fixed
- Ingredients showing as "Unknown" after AI parser import (missing `ingredient_name` in INSERT)
- Ingredient list reordering after edit (added ORDER BY ri.id)
- Cost not updating when mapping ingredients to products (timestamp tracking)
- Duplicate field updates in ingredient PATCH endpoint

---

## [2024-12-18] - Recipe Editor Overhaul

### Added
- **Inline Editing System**
  - Click any cell to edit directly in table (no modal required)
  - Single-row edit mode with yellow highlight
  - Save/Cancel buttons for each row
  - Click-to-edit pattern matching Excel/Google Sheets

- **Autocomplete Product Mapping**
  - Type 2+ characters to see matching products
  - Arrow Up/Down to navigate suggestions
  - Enter to select highlighted product
  - Real-time filtering as you type
  - Green ✓ indicator when mapped to product
  - No separate "Map" button needed

- **Excel-like Keyboard Navigation**
  - **Tab**: Move to next field (ingredient → quantity → unit → yield%)
  - **Shift+Tab**: Move to previous field
  - **Enter**: Save current row and start editing next row
  - **Escape**: Cancel editing without saving
  - **Arrow Up/Down**: Navigate autocomplete dropdown
  - **Enter (in dropdown)**: Select highlighted suggestion
  - Auto-select text when focusing any field

- **Visual Improvements**
  - "Mapped?" column shows ✓ for mapped, × for unmapped ingredients
  - Removed cluttered "Text only" badge
  - Hover states on editable cells (pointer cursor)
  - Yellow background for row being edited
  - Cleaner, more intuitive interface

### Fixed
- **AI Parser Bug**: Fixed "Unknown" ingredients after import
  - Added `ingredient_name` to recipe_ingredients INSERT statement
  - Ingredients now display correctly with "Text only" status

- **Ingredient Ordering**: Fixed list reordering after edits
  - Added `ORDER BY ri.id` to maintain insertion order
  - Ingredients stay in original position when updated

- **Cost Calculation**: Fixed costs not updating when mapping products
  - Recipe `updated_at` timestamp updates on ingredient changes
  - RecipeCost component watches `updated_at` dependency
  - Costs recalculate automatically when ingredients mapped

- **Duplicate Field Error**: Fixed 500 error in ingredient PATCH
  - Prevented duplicate field assignments in UPDATE query
  - Auto-clear logic no longer conflicts with main field updates

### Technical Details

**Backend Changes** (`api/app/routers/recipes.py`):
- Added `common_product_id` and `ingredient_name` to allowed PATCH fields
- Implemented mutual exclusivity validation (can't set both at once)
- Auto-clear opposite field when mapping changes
- Update parent recipe timestamp on ingredient add/edit/delete
- Added ORDER BY ri.id to ingredient queries

**Frontend Changes** (`frontend/src/pages/Recipes.jsx`):
- Created `IngredientMappingCell` component with three states:
  - Autocomplete search active
  - Mapped to product (with remap/unmap buttons)
  - Text-only (with map button)
- Added state management: `editingIngredientId`, `editedValues`
- Implemented keyboard navigation handler with field awareness
- Added `onFocus={(e) => e.target.select()}` to all inputs
- Updated RecipeCost dependency to include `recipe.updated_at`

**Styling** (`frontend/src/pages/Recipes.css`):
- Added ~150 lines for inline editing interface
- Mapped indicator styles (.mapped-yes, .mapped-no)
- Inline edit input/select styles
- Product search dropdown with hover/selected states
- Row editing state (yellow highlight)

### Developer Experience
- Added comprehensive debug endpoints for cost troubleshooting
- Better error messages for product-outlet mismatches
- Clearer audit trail with recipe timestamp updates

---

## Previous Releases

See [docs/completed/](docs/completed/) for historical phase documentation.

---

**Last Updated:** December 18, 2024
