# Changelog

All notable changes to the Food Cost Tracker project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

*No unreleased changes*

---

## [2026-06-28] - Recipe Import, Search Performance & Vendor Creation

### Added

**Vendor Creation**
- `POST /api/distributors` endpoint to create vendors (external or internal/housemade) without waiting for an invoice import
- "+ Add new vendor" option in the Products add-row distributor dropdown, with auto-select after creation
- Seeded a global "Internal / Housemade" vendor (migration 047) so in-house items can carry a price (pricing is keyed on distributor_products)

**Recipe Parser - Legacy .doc Support**
- Added `.doc` (legacy binary Word) extraction via `antiword` (system package, added to both Dockerfiles)
- Feeds the same Claude extraction pipeline as `.docx`; frontend upload now accepts `.doc`

### Changed

**Search Performance**
- Debounced the all-products search (300ms) and moved search-independent reference data (common products, distributors, units) to a mount-only load — typing "chicken" went from ~28 requests to ~1
- Applied the same 300ms debounce to the super-admin organization search

**Infrastructure**
- Upgraded the Render PostgreSQL instance from Basic-256mb (0.1 CPU) to Basic-1gb (0.5 CPU) — resolved query latency variance traced to CPU starvation, not missing indexes

### Fixed

**Recipe Parser - Saving**
- Parsed recipes with unquantified ingredients (e.g. "salt to taste") no longer 422 on save; `quantity`/`unit_id` are now optional, with null quantity coerced to 0 for completion in the editor
- Validation errors (HTTP 422) no longer crash the review UI with React error #31 — the error detail is rendered as a readable message
- Viewing a recipe with a unit-less ingredient no longer 500s; the recipe read model now allows null `unit_id` (was a regression from allowing such ingredients to save)

---

## [2025-01-30] - Banquet Menus & Quality of Life Updates

### Added

**Banquet Menu System**
- Complete banquet menu management for event catering
- Menu structure: Meal Period → Service Type → Menu Name → Menu Items → Prep Items
- CSV import for bulk menu data with duplicate detection
- PDF export for banquet prep lists
- Drag-and-drop reordering for menu items and prep items
- Guest count scaling for prep quantities
- Vessel capacity management for prep planning
- Common product linking for prep items with cost calculation

**User Management**
- Last login tracking for all users
- Display last login in admin user list (relative time with full timestamp on hover)
- Display last login in super admin organization detail

**Products Page Improvements**
- Pagination with page selector (first/prev/page numbers/next/last)
- Mapping filter dropdown (All Products / Mapped Only / Unmapped Only)
- Distributor dropdown filter
- Shows "Showing X-Y of Z" for current page range

**Recipe Improvements**
- Auto-convert ingredient quantity when unit changes
- `GET /recipes/convert-unit` endpoint for unit conversions
- Uses product-specific conversions when available (e.g., 1 EA chicken = 6 OZ)
- Falls back to standard weight/volume conversions

### Fixed
- Common products search now case-insensitive
- Banquet prep item linking to common products

---

## [2024-12-18] - Recipe Editor Overhaul

### Added
- Excel-like inline editing for recipe ingredients table
- Autocomplete product search while typing ingredient names
- "Mapped?" column with ✓/× indicators for ingredient status
- Keyboard navigation (Tab, Enter, Escape, Arrow keys) for rapid data entry
- Auto-select text on focus for instant editing
- Debug endpoints for troubleshooting cost calculation issues

### Changed
- Removed "Text only" badge in favor of cleaner Mapped? column
- Ingredients now maintain insertion order (no longer reorder after edits)
- Recipe costs auto-update when ingredients are mapped to products

### Fixed
- Ingredients showing as "Unknown" after AI parser import
- Ingredient list reordering after edit
- Cost not updating when mapping ingredients to products
- Duplicate field updates in ingredient PATCH endpoint

### Technical Details
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

**Last Updated:** January 30, 2025
