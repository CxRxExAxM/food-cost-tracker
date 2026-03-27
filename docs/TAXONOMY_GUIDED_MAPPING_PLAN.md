# Taxonomy Guided Mapping Redesign

**Created:** March 26, 2026
**Status:** Planning
**Priority:** High - Foundation for product management UX

---

## Problem Statement

### Current Issues Discovered

1. **Hierarchy is cosmetic only** - The variant tree (`parent_variant_id`) provides visual organization but doesn't affect how Common Products are assigned to variants. Assignment is based on exact attribute matching from the parser, completely disconnected from the visual hierarchy.

2. **No guided onboarding** - Users can type any name for a Common Product, leading to:
   - Redundant/duplicate categories
   - Inconsistent naming conventions
   - Flat structures that should be hierarchical
   - Confusion about what goes where

3. **Retroactive organization is painful** - Trying to reorganize existing taxonomy data is extremely frustrating because:
   - Moving items doesn't change their attribute-based assignments
   - Editing names sometimes reorders things, sometimes doesn't
   - The system behavior feels inconsistent and unpredictable

4. **Variable depth requirements** - Different ingredients need different hierarchy depths:
   - Chicken, Breast, Airline, 8oz, Frenched = 5 levels
   - Onion, Yellow = 2 levels
   - Some items may need 0 variant levels

### User Quote
> "I've been working on Chicken now for 10 minutes... even adding variants and trying to change names to get things to order properly, sometimes they move by just clicking edit and save, sometimes what I think changing a name so it will slot in with other variants doesn't work. I'm kinda at a loss"

---

## Solution: Path-Based Autocomplete

### Core Concept

Replace the freeform "Create Common Product" text input with a **path-based autocomplete** that guides users through the hierarchy as they type.

Single input field, keyboard-driven, progressive disclosure.

### UX Flow

#### Step 1: Start Typing
```
┌─────────────────────────────────────────────────────────┐
│  Mapping: "Tyson Airline Breast 8oz Frenched IQF 40lb"  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────┐           │
│  │ chick█                                  │           │
│  ├─────────────────────────────────────────┤           │
│  │ 📁 Chicken (14 variants)            →   │           │
│  │ 📁 Chickpea (2 variants)            →   │           │
│  │ ─────────────────────────────────────── │           │
│  │ + Create "chick" as new base            │           │
│  └─────────────────────────────────────────┘           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Step 2: Select and Advance
User selects Chicken (click, Enter, comma, or space):
```
┌─────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────┐           │
│  │ Chicken, █                              │           │
│  ├─────────────────────────────────────────┤           │
│  │ 📁 Breast (5 variants)              →   │           │
│  │ 📁 Thigh (3 variants)               →   │           │
│  │ 📁 Ground (2 variants)              →   │           │
│  │ 📁 Wing                             →   │           │
│  │ 📁 Whole                            →   │           │
│  │ ─────────────────────────────────────── │           │
│  │ + Create new variant under Chicken      │           │
│  └─────────────────────────────────────────┘           │
│  Path: Chicken                                         │
└─────────────────────────────────────────────────────────┘
```

#### Step 3: Drill to Desired Depth
```
┌─────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────┐           │
│  │ Chicken, Breast, air█                   │           │
│  ├─────────────────────────────────────────┤           │
│  │ 📁 Airline (3 sizes)                →   │  ← variant with children
│  │ ─────────────────────────────────────── │
│  │ 📦 Airline 6oz Frenched         Select  │  ← existing CP (leaf)
│  │ 📦 Airline 8oz Frenched         Select  │
│  │ 📦 Airline 8oz Standard         Select  │
│  │ ─────────────────────────────────────── │
│  │ + Create "air" as variant               │
│  │ + Create "air" as common product        │  ← stop here, make CP
│  └─────────────────────────────────────────┘           │
│  Path: Chicken > Breast                                │
└─────────────────────────────────────────────────────────┘
```

### Visual Language

| Element | Meaning |
|---------|---------|
| 📁 with → | Variant - has children, can drill deeper |
| 📦 with Select | Common Product - leaf node, can map SKU to this |
| Comma/Space after selection | Advances to next level |
| Backspace at level start | Goes back up a level |
| Enter/Click on 📦 | Selects CP and completes mapping |

### Key Features

1. **No forced depth** - Select a CP at any level. No clicking through empty intermediate levels.

2. **Shows existing structure** - Users see what already exists before creating duplicates.

3. **Single input field** - Keyboard-driven, fast for power users, discoverable for new users.

4. **Create at any level**:
   - "Create as variant" → drills deeper, expects more levels
   - "Create as common product" → stops here, this is the leaf

5. **Flexible depth** - Same UI handles 2-level vegetables and 5-level chicken cuts.

---

## Technical Considerations

### Database Schema

Current schema already supports this:
- `base_ingredients` - Top level
- `ingredient_variants` - Unlimited nesting via `parent_variant_id`
- `common_products` - Leaf nodes (linked to a variant)
- `products` - SKUs (linked to a common product)

No schema changes required for the hierarchy itself.

### API Endpoints Needed

```
GET /taxonomy/search-path?query=chicken,breast,air&level=variant
Returns: variants and CPs matching "air" under Chicken > Breast

POST /taxonomy/create-in-path
Body: { path: ["Chicken", "Breast"], name: "Airline", type: "variant" | "common_product" }
Creates: new variant or CP at the specified path location
```

### Frontend Component

New component: `PathBasedProductMapper.jsx`
- Single controlled input
- Tracks current path as array: `["Chicken", "Breast"]`
- Debounced search as user types
- Keyboard navigation (arrow keys, enter, backspace)
- Visual path breadcrumb

### Integration Points

Replace current "Create Common Product" experience in:
- `UnmatchedProducts.jsx` - Primary mapping workflow
- `TaxonomyView.jsx` - Manual product reassignment
- Potentially recipe import flow

---

## Migration Strategy

### Recommended: Clean Slate

Given:
- Current data is already disorganized
- User is willing to remap
- Getting the foundation right matters for recipes/pricing

**Approach:**
1. Build the new guided mapping UI
2. Archive existing CP assignments
3. Re-import products
4. Remap using new guided flow

### Alternative: Reorganization Tool

Build a one-time "Reorganize" view that:
- Shows all CPs grouped by detected base ingredient
- Allows drag/drop to proper hierarchy positions
- More complex to build, less manual remapping

**Recommendation:** Start with clean slate. Don't invest in migration tooling for a one-time problem.

---

## Design Principles

1. **The Common Product is "the thing you compare across vendors"**
   - If comparing "8oz Frenched Airline Breast" between Sysco and US Foods, that's your CP
   - Variants above it are organizational

2. **Depth is user-driven, not system-mandated**
   - Simple items: 2 levels
   - Complex items: 5+ levels
   - Same UI handles both

3. **Show before create**
   - Always display existing options before offering to create new
   - Prevents duplicates organically

4. **Keyboard-first, mouse-friendly**
   - Power users can type full paths quickly
   - New users can click through and discover

---

## Open Questions

1. **Delimiter choice** - Comma seems natural. Consider: `>`, `/`, or smart detection?

2. **Attribute preservation** - When creating CPs through guided flow, do we still parse/store attributes? Or is the path sufficient?

3. **Existing auto-parser** - Keep it for suggestions? Disable entirely? Use for initial path suggestion?

4. **Fresh vs Frozen** - User noted this sometimes matters for price but isn't always a hierarchy level. Handle as:
   - Variant level (user choice)
   - CP name suffix
   - SKU metadata only

---

## Next Steps

1. [ ] User decision: Confirm clean slate approach
2. [ ] Design: Finalize delimiter and keyboard shortcuts
3. [ ] Backend: Build path search and create endpoints
4. [ ] Frontend: Build PathBasedProductMapper component
5. [ ] Integration: Replace current mapping UI
6. [ ] Migration: Archive old data, re-import, remap

---

## Session Context

**Date:** March 26, 2026

**Also completed this session:**
- Added product reassignment feature (individual SKUs can be moved between CPs)
- Fixed Dockerfile.render to include scripts/ folder
- Updated CLAUDE.md with no-assumptions rule and alembic location
- Diagnosed hierarchy-vs-assignment disconnect in current system

**Files modified:**
- `api/app/routers/taxonomy.py` - Added reassign endpoint
- `frontend/src/pages/Products/TaxonomyView.jsx` - Added reassign UI
- `frontend/src/pages/Products/TaxonomyView.css` - Reassign modal styles
- `Dockerfile.render` - Added COPY scripts/
- `CLAUDE.md` - Added verification rules

**Commits:**
- Work was in progress; verify commit status at session start
