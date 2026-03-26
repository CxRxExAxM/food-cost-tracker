# Ingredient Taxonomy Design Review

**Date:** March 26, 2026
**Status:** Design Review
**Author:** Architecture Review Session

---

## Overview

This document captures the design for refactoring the ingredient data model from free-text naming to an attribute-based taxonomy. The goal is to enable:
- Consistent ingredient identification across vendors
- Attribute-based search and filtering
- Cost rollups at any attribute level
- Network effect through shared (anonymized) mappings

---

## Current State

### common_products Table
```sql
common_products
  - id
  - common_name        -- "Carrot, Jumbo, Peeled" (free text)
  - category           -- "Produce"
  - subcategory        -- "Vegetables"
  - preferred_unit_id
  - 16 allergen flags
  - notes, is_active, timestamps
```

### Problems with Current Approach
1. **Inconsistent naming:** "Carrot, Jumbo" vs "Jumbo Carrot" vs "Carrots - Jumbo"
2. **No attribute extraction:** Can't search "all peeled items" or "all 5lb packs"
3. **Scaling issues:** Multi-user = same ingredient, different records
4. **Cost rollup limitations:** Can't aggregate "all carrots" regardless of prep

### Tables Referencing common_products
- `products.common_product_id` - Distributor products
- `recipe_ingredients.common_product_id` - Recipe line items
- `ingredient_mappings.common_product_id` - Learning loop (new)

---

## Proposed Schema

### Phase 1: New Tables

```sql
-- Base ingredient concepts (tomato, chicken, carrot)
CREATE TABLE base_ingredients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,           -- "Carrot"
    category VARCHAR(50),                  -- "Produce"
    subcategory VARCHAR(50),               -- "Vegetables"
    default_unit_id INTEGER REFERENCES units(id),

    -- Allergen flags (inherited by variants)
    allergen_vegan BOOLEAN DEFAULT FALSE,
    allergen_vegetarian BOOLEAN DEFAULT FALSE,
    allergen_gluten BOOLEAN DEFAULT FALSE,
    allergen_crustation BOOLEAN DEFAULT FALSE,
    allergen_egg BOOLEAN DEFAULT FALSE,
    allergen_mollusk BOOLEAN DEFAULT FALSE,
    allergen_fish BOOLEAN DEFAULT FALSE,
    allergen_lupin BOOLEAN DEFAULT FALSE,
    allergen_dairy BOOLEAN DEFAULT FALSE,
    allergen_tree_nuts BOOLEAN DEFAULT FALSE,
    allergen_peanuts BOOLEAN DEFAULT FALSE,
    allergen_sesame BOOLEAN DEFAULT FALSE,
    allergen_soy BOOLEAN DEFAULT FALSE,
    allergen_sulphur_dioxide BOOLEAN DEFAULT FALSE,
    allergen_mustard BOOLEAN DEFAULT FALSE,
    allergen_celery BOOLEAN DEFAULT FALSE,

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(name)
);

-- Specific forms/variants (cherry tomato, diced carrot)
-- NOTE: pack_size intentionally NOT here - it's a product/SKU attribute, not ingredient
CREATE TABLE ingredient_variants (
    id SERIAL PRIMARY KEY,
    base_ingredient_id INTEGER NOT NULL REFERENCES base_ingredients(id),

    -- Structured attributes (ingredient characteristics)
    variety VARCHAR(50),                   -- "Orange", "Rainbow", "Roma"
    form VARCHAR(50),                      -- "Baby", "Jumbo", "Petite"
    prep VARCHAR(50),                      -- "Diced", "Peeled", "Sliced"
    cut_size VARCHAR(30),                  -- "1/2 inch", "1/4 inch"

    -- Protein-specific attributes
    cut VARCHAR(50),                       -- "Breast", "Thigh", "Loin"
    bone VARCHAR(30),                      -- "Boneless", "Bone-In"
    skin VARCHAR(30),                      -- "Skin On", "Skinless"
    grade VARCHAR(30),                     -- "Natural", "Choice", "Prime"
    state VARCHAR(30),                     -- "Fresh", "Frozen", "IQF"

    -- Display name (computed or user-set)
    display_name VARCHAR(255) NOT NULL,    -- "Carrot, Orange, Jumbo"

    -- Override allergens if different from base
    allergen_override JSONB,               -- {"allergen_gluten": true}

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique combinations (no pack_size = fewer duplicates)
    UNIQUE(base_ingredient_id, variety, form, prep, cut_size, cut, bone, skin, grade, state)
);

-- Indexes for attribute queries
CREATE INDEX idx_variants_base ON ingredient_variants(base_ingredient_id);
CREATE INDEX idx_variants_variety ON ingredient_variants(variety) WHERE variety IS NOT NULL;
CREATE INDEX idx_variants_form ON ingredient_variants(form) WHERE form IS NOT NULL;
CREATE INDEX idx_variants_prep ON ingredient_variants(prep) WHERE prep IS NOT NULL;
```

### Phase 2: Migration Bridge

```sql
-- Add bridge columns to common_products (non-breaking)
ALTER TABLE common_products
ADD COLUMN base_ingredient_id INTEGER REFERENCES base_ingredients(id),
ADD COLUMN variant_id INTEGER REFERENCES ingredient_variants(id),
ADD COLUMN migrated_at TIMESTAMP;

-- Index for migration queries
CREATE INDEX idx_common_products_base ON common_products(base_ingredient_id);
```

### Phase 3: Update References (Optional)

Eventually, recipe_ingredients could reference variants directly:
```sql
-- Future: recipe_ingredients.variant_id instead of common_product_id
-- This is a larger migration - defer until taxonomy is stable
```

---

## Real Data Example

Current `common_products` rows for carrots:
```
Carrot, Dice, 1/2"        → base: Carrot, prep: Diced, cut_size: 1/2"
Carrot, Dice, 1/4"        → base: Carrot, prep: Diced, cut_size: 1/4"
Carrot, Orange, Jumbo     → base: Carrot, variety: Orange, form: Jumbo
Carrot, Rainbow           → base: Carrot, variety: Rainbow
Carrot, Baby, Rainbow     → base: Carrot, variety: Rainbow, form: Baby
Carrot, Baby, Peeled      → base: Carrot, form: Baby, prep: Peeled
```

After migration:
```
base_ingredients:
  id=1, name="Carrot", category="Produce"

ingredient_variants:
  id=1, base_id=1, prep="Diced", cut_size="1/2 inch", display_name="Carrot, Diced 1/2\""
  id=2, base_id=1, prep="Diced", cut_size="1/4 inch", display_name="Carrot, Diced 1/4\""
  id=3, base_id=1, variety="Orange", form="Jumbo", display_name="Carrot, Orange, Jumbo"
  ...
```

---

## Three-Tier Security Model

### Tier 1: Tenant-Private (Never Shared)
- Raw invoice data
- Pricing and volumes
- Vendor account numbers
- User information

### Tier 2: Anonymized Shared (Opt-In)
- Ingredient mappings (raw_name → base/variant)
- No pricing, no tenant ID in shared data
- Requires explicit opt-in consent
- Audit trail of consent decisions

### Tier 3: Fully Public (Always Available)
- Base taxonomy (base_ingredients table)
- Unit normalizations
- Standard attribute values

### Implementation in ingredient_mappings
```sql
-- Already exists, add taxonomy link
ALTER TABLE ingredient_mappings
ADD COLUMN base_ingredient_id INTEGER REFERENCES base_ingredients(id),
ADD COLUMN variant_id INTEGER REFERENCES ingredient_variants(id);

-- The existing is_shared flag handles tier 2 consent
```

---

## Migration Strategy

### Step 1: Schema Creation (Week 1)
- Create base_ingredients and ingredient_variants tables
- Add bridge columns to common_products
- No data changes yet

### Step 2: Data Analysis (Week 1-2)
- Export current common_products names
- Parse existing naming conventions (already follows "Base, Attr1, Attr2" pattern)
- Identify base ingredients and attributes
- Generate migration mapping

### Step 3: Backfill (Week 2)
- Create base_ingredients from unique base names
- Create ingredient_variants from parsed attributes
- Update common_products with base_ingredient_id and variant_id
- **Test on dev DB first before production**

### Step 4: API Updates (Week 3)
- Update product matcher to use taxonomy
- Update recipe costing to use base ingredient rollups
- Add attribute-based search endpoints

### Step 5: Frontend Updates (Week 4)
- Update product creation/editing forms
- Add attribute filters to product list
- Update recipe ingredient selector

---

## Decision Points for Review

### 1. Timing
**Question:** Should this happen before or after more AI Parser features?

**Recommendation:** Start Phase 1 (schema creation) now, defer Phase 2+ until parser is stable. The bridge column approach allows gradual migration.

### 2. Seed Data
**Question:** Bootstrap from USDA database or from existing user data?

**Recommendation:** Start with existing common_products data. The naming convention already implies structure. USDA can be added later as validation/enhancement.

### 3. Attribute Set
**Question:** What attributes are actually needed?

**Current proposal based on real data:**
- `variety` - Color/type variant (Orange, Rainbow, Roma)
- `form` - Size/shape (Baby, Jumbo, Petite)
- `prep` - Processing (Diced, Sliced, Peeled, IQF)
- `cut_size` - Specific dimensions (1/2", 1/4")
- `pack_size` - Packaging (5 lb, 25 lb, case)

**Open question:** Do we need `brand` as an attribute?

### 4. Learning Loop Integration
**Question:** How do learned mappings interact with taxonomy?

**Proposal:**
- Continue storing raw_name → common_product_id mapping
- Add base_ingredient_id and variant_id to mappings
- When user selects a match, we can infer taxonomy from the common_product

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Test on dev DB, maintain rollback path |
| Breaking existing recipes | High | Bridge columns, no immediate reference changes |
| Attribute set insufficient | Medium | Make attributes nullable, add as needed |
| Performance regression | Medium | Index attribute columns, test query plans |
| User confusion | Low | Gradual rollout, maintain familiar UI |

---

## Variant Management & Merge Strategy

### The Proliferation Problem

Without controls, we could end up with the same fragmentation we're trying to solve:

```
❌ Bad: 15 "basically the same" variants
─────────────────────────────────────
Carrot, Orange, Jumbo, 25#
Carrot, Orange, Jumbo, 50#
Carrot, Orange, Large
Carrot, Jumbo
Carrot, Orange Jumbo
...still have to pick "which carrot?"
```

### Design Decision: Separate Pack Size from Variant

**Key insight:** `pack_size` is a *purchasing attribute*, not an *ingredient attribute*.

A recipe calls for "jumbo orange carrots" - it doesn't care if they came in a 25# or 50# bag.

```sql
-- REVISED: Remove pack_size from ingredient_variants
-- pack_size stays on products table (vendor SKU level)

ingredient_variants:
  - variety, form, prep, cut_size  -- Ingredient characteristics
  - cut, bone, skin, grade, state  -- Protein characteristics
  -- NO pack_size here

products:
  - variant_id                      -- Links to ingredient
  - pack, size, unit                -- Packaging info (already exists)
```

This reduces variant count significantly:
```
✅ Good: Variants describe the ingredient, not the package
──────────────────────────────────────────────────────────
Carrot (base)
  ├─ Orange, Jumbo           ← One variant
  │    └─ Sysco 25# bag      ← Product with pack info
  │    └─ Sysco 50# bag      ← Product with pack info
  │    └─ Vesta 10# bag      ← Product with pack info
  ├─ Diced, 1/2"             ← Another variant
  └─ Baby, Peeled            ← Another variant
```

### Variant Merge Feature

Even with good design, duplicates will happen. Users need the ability to merge:

**UI Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│ Carrot Variants                                    [Merge]  │
├─────────────────────────────────────────────────────────────┤
│ ☑ Orange, Jumbo                    [5 products, 3 recipes]  │
│ ☑ Jumbo Orange                     [2 products, 1 recipe]   │
│ ☐ Diced, 1/2"                      [3 products, 2 recipes]  │
└─────────────────────────────────────────────────────────────┘
                          ↓ Click Merge
┌─────────────────────────────────────────────────────────────┐
│ Merge 2 variants into:                                      │
│                                                             │
│ Keep: ◉ Orange, Jumbo (more usage)                         │
│       ○ Jumbo Orange                                        │
│                                                             │
│ This will update:                                           │
│   • 2 products → point to "Orange, Jumbo"                  │
│   • 1 recipe → use "Orange, Jumbo"                         │
│   • Delete "Jumbo Orange" variant                          │
│                                                             │
│                              [Cancel]  [Merge Variants]     │
└─────────────────────────────────────────────────────────────┘
```

**Backend Merge Operation:**
```python
def merge_variants(keep_id: int, merge_ids: List[int], conn):
    """Merge multiple variants into one."""

    # 1. Update all products pointing to merged variants
    cursor.execute("""
        UPDATE products
        SET variant_id = %s
        WHERE variant_id = ANY(%s)
    """, (keep_id, merge_ids))

    # 2. Update all recipe_ingredients (if applicable)
    cursor.execute("""
        UPDATE recipe_ingredients
        SET variant_id = %s
        WHERE variant_id = ANY(%s)
    """, (keep_id, merge_ids))

    # 3. Update ingredient_mappings to prevent future duplicates
    cursor.execute("""
        UPDATE ingredient_mappings
        SET variant_id = %s
        WHERE variant_id = ANY(%s)
    """, (keep_id, merge_ids))

    # 4. Delete merged variants
    cursor.execute("""
        DELETE FROM ingredient_variants
        WHERE id = ANY(%s)
    """, (merge_ids,))

    # 5. Log merge for audit
    log_variant_merge(keep_id, merge_ids, conn)
```

### Duplicate Prevention

**At Creation Time:**
```python
def suggest_existing_variants(base_id: int, attributes: dict, conn) -> List[dict]:
    """Before creating a variant, show potential matches."""

    similar = find_similar_variants(base_id, attributes, conn)

    if similar:
        return {
            "action": "confirm",
            "message": f"Found {len(similar)} similar variants",
            "similar": similar,
            "suggested_match": similar[0] if similar[0]["confidence"] > 0.8 else None
        }

    return {"action": "create", "message": "No similar variants found"}
```

**UI Warning:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️  Similar variant exists                                  │
│                                                             │
│ You're creating: "Carrot, Jumbo, Orange"                    │
│                                                             │
│ Did you mean one of these?                                  │
│   • Carrot, Orange, Jumbo (92% match) [Use This]           │
│   • Carrot, Orange, Large (78% match) [Use This]           │
│                                                             │
│                    [Create Anyway]  [Cancel]                │
└─────────────────────────────────────────────────────────────┘
```

### Attribute Normalization

Enforce consistent attribute values to reduce drift:

```python
# Standard allowed values (expandable by admin)
ATTRIBUTE_VALUES = {
    "form": ["Baby", "Petite", "Medium", "Large", "Jumbo", "Colossal"],
    "prep": ["Whole", "Diced", "Sliced", "Julienne", "Peeled", "Shredded", "IQF"],
    "variety": None,  # Free text - too many valid values
    "cut_size": ["1/4\"", "3/8\"", "1/2\"", "3/4\"", "1\""],
}

def normalize_attribute(attr_name: str, value: str) -> str:
    """Normalize to standard value if possible."""
    allowed = ATTRIBUTE_VALUES.get(attr_name)
    if allowed is None:
        return value.strip().title()

    # Fuzzy match to allowed values
    match = find_closest_match(value, allowed)
    return match if match else value
```

---

## Implementation Checklist

### Phase 1: Preparation
- [ ] Create Alembic migration for base_ingredients table
- [ ] Create Alembic migration for ingredient_variants table
- [ ] Add bridge columns to common_products
- [ ] Write data analysis script to parse existing names
- [ ] Generate base ingredient list from common_products

### Phase 2: Migration
- [ ] Backfill base_ingredients from analysis
- [ ] Backfill ingredient_variants from analysis
- [ ] Update common_products with taxonomy links
- [ ] Test all existing functionality unchanged

### Phase 3: Features
- [ ] Update product_matcher.py to use taxonomy
- [ ] Add attribute-based search endpoint
- [ ] Update cost rollup queries
- [ ] Update recipe ingredient selector UI

---

## Appendix: Attribute Value Standards

### variety (colors, types)
- Orange, Yellow, White, Red, Rainbow
- Roma, Cherry, Grape, Beefsteak (tomatoes)
- Russet, Yukon, Red, Fingerling (potatoes)

### form (size grades)
- Baby, Petite, Medium, Large, Jumbo, Colossal

### prep (processing)
- Whole, Diced, Sliced, Julienne, Peeled
- IQF (frozen), Fresh, Canned, Dried

### cut_size (specific dimensions)
- 1/4", 1/2", 3/4", 1"
- Small dice, Medium dice, Large dice, Brunoise

### cut (protein cuts)
- Breast, Thigh, Leg, Wing (poultry)
- Loin, Rib, Shoulder, Belly (pork)
- Chuck, Rib, Loin, Round (beef)

### bone / skin (protein modifiers)
- Boneless, Bone-In, Frenched
- Skin On, Skinless

### grade (quality grades)
- Natural, Organic, Choice, Prime, Select
- Grade A, Grade B

### state (temperature/processing state)
- Fresh, Frozen, IQF (Individually Quick Frozen)
- Canned, Dried, Smoked

*Note: `pack_size` (5 lb, 25 lb, etc.) stays on the `products` table as a purchasing attribute, not an ingredient characteristic.*

---

**Next Steps:**
1. Review this document
2. Confirm attribute set is complete
3. Begin Phase 1 migration development
