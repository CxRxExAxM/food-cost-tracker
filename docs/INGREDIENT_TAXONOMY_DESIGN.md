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
CREATE TABLE ingredient_variants (
    id SERIAL PRIMARY KEY,
    base_ingredient_id INTEGER NOT NULL REFERENCES base_ingredients(id),

    -- Structured attributes
    variety VARCHAR(50),                   -- "Orange", "Rainbow", "Roma"
    form VARCHAR(50),                      -- "Baby", "Jumbo", "Petite"
    prep VARCHAR(50),                      -- "Diced", "Peeled", "Sliced"
    cut_size VARCHAR(30),                  -- "1/2 inch", "1/4 inch"
    pack_size VARCHAR(30),                 -- "5 lb", "25 lb", "1 ct"

    -- Display name (computed or user-set)
    display_name VARCHAR(255) NOT NULL,    -- "Carrot, Orange, Jumbo, 25#"

    -- Override allergens if different from base
    allergen_override JSONB,               -- {"allergen_gluten": true}

    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Ensure unique combinations
    UNIQUE(base_ingredient_id, variety, form, prep, cut_size, pack_size)
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

### pack_size (packaging)
- 1 lb, 5 lb, 10 lb, 25 lb, 50 lb
- 1 ct, 6 ct, 12 ct, case

---

**Next Steps:**
1. Review this document
2. Confirm attribute set is complete
3. Begin Phase 1 migration development
