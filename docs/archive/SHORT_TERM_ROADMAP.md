# Short-Term Roadmap: Unified AI Parsing & Taxonomy

**Date:** March 26, 2026
**Status:** Active Development
**Goal:** Connected taxonomy and AI parsing for recipes and invoices, ready for UI review

---

## Executive Summary

Three interconnected systems working together:

```
                    ┌─────────────────────────────────────────┐
                    │         INGREDIENT TAXONOMY             │
                    │   base_ingredients → ingredient_variants │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
              ▼                       ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │  AI RECIPE      │     │  LEARNING       │     │  AI INVOICE     │
    │  PARSER         │     │  LOOP           │     │  PARSER         │
    │                 │     │                 │     │                 │
    │ PDFs/Images →   │────▶│ ingredient_     │◀────│ CSV/Excel →     │
    │ Structured      │     │ mappings        │     │ Structured      │
    │ Recipe          │     │                 │     │ Products        │
    └─────────────────┘     └─────────────────┘     └─────────────────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      │
                    ┌─────────────────┴───────────────────────┐
                    │         UNIFIED PRODUCT UI              │
                    │    Common Products → Nested View        │
                    └─────────────────────────────────────────┘
```

**Network Effect:** Each recipe parsed and each invoice imported improves matching accuracy for all future imports.

---

## Current State (March 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| AI Recipe Parser | ✅ Live | Method steps added, working in production |
| Learning Loop | ✅ Live | ingredient_mappings table, fuzzy matching |
| Ingredient Taxonomy | 📋 Designed | Schema ready, migration planned |
| AI Invoice Parser | 📋 Designed | Technical spec complete |
| Common Products UI | 🔄 Needs Update | Will reflect new taxonomy structure |

---

## Phase 1: Taxonomy Foundation (Week 1-2)

**Objective:** Create the attribute-based schema that both parsers will use.

### Tasks

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Create `base_ingredients` table | 🔴 High | 2h | None |
| Create `ingredient_variants` table | 🔴 High | 2h | base_ingredients |
| Add bridge columns to `common_products` | 🔴 High | 1h | ingredient_variants |
| Parse existing common_products names | 🟡 Medium | 4h | Bridge columns |
| Backfill base_ingredients | 🟡 Medium | 2h | Name parsing |
| Backfill ingredient_variants | 🟡 Medium | 4h | base_ingredients data |

### Database Schema

```sql
-- New tables (see INGREDIENT_TAXONOMY_DESIGN.md for full schema)
base_ingredients (id, name, category, subcategory, allergens...)
ingredient_variants (id, base_ingredient_id, variety, form, prep, cut_size, cut, bone, skin, grade, state...)

-- Bridge columns on existing table
common_products.base_ingredient_id → base_ingredients.id
common_products.variant_id → ingredient_variants.id
```

### Success Criteria
- [ ] All existing common_products have base_ingredient_id assigned
- [ ] 90%+ have variant_id assigned
- [ ] Existing recipes/products continue working (no breaking changes)

---

## Phase 2: AI Recipe Parser + Taxonomy (Week 2-3)

**Objective:** Connect recipe parsing to taxonomy for better ingredient matching.

### Already Complete
- ✅ Method step extraction from recipes
- ✅ Ingredient parsing with yield extraction
- ✅ Learning loop integration (ingredient_mappings)

### Remaining Tasks

| Task | Priority | Effort | Dependencies |
|------|----------|--------|--------------|
| Update matcher to prefer taxonomy matches | 🔴 High | 4h | Phase 1 complete |
| Add base_ingredient_id to ingredient_mappings | 🟡 Medium | 2h | Phase 1 complete |
| Add variant_id to ingredient_mappings | 🟡 Medium | 2h | Phase 1 complete |
| Test parsing with taxonomy fallback | 🟡 Medium | 2h | Matcher update |

### Flow After Enhancement

```
Recipe PDF → AI Extract → Match Ingredient → Check taxonomy first
                              │                      │
                              │              ┌───────┴───────┐
                              │              │ Found in      │
                              │              │ taxonomy?     │
                              │              └───────┬───────┘
                              │                 Yes ↙   ↘ No
                              │                 │         │
                              │     ┌───────────┘         └──────────┐
                              ▼     ▼                                ▼
                         Use taxonomy match              Fall back to learning loop
                         (highest confidence)            (ingredient_mappings)
```

---

## Phase 3: AI Invoice Parser (Week 3-4)

**Objective:** Replace vendor-specific scripts with universal AI parsing.

### New Components

| Component | File | Purpose |
|-----------|------|---------|
| Column Detector | `api/app/services/invoice_column_detector.py` | Auto-detect CSV column purposes |
| Attribute Extractor | `api/app/services/invoice_attribute_extractor.py` | Parse product descriptions |
| Taxonomy Matcher | `api/app/services/invoice_taxonomy_matcher.py` | Match to base/variant |
| Invoice Learning | `api/app/services/invoice_learning.py` | Record confirmed mappings |

### API Endpoints

```
POST /api/invoices/parse-file
  - Input: CSV/Excel file
  - Output: Detected columns, parsed products with taxonomy matches

POST /api/invoices/confirm-import
  - Input: User-confirmed product mappings
  - Output: Created products, updated learning loop
```

### Migration from Current System

1. **Phase 3a:** Add "Parse with AI" option alongside existing scripts
2. **Phase 3b:** AI becomes default, scripts as fallback
3. **Phase 3c:** Deprecate vendor-specific code

### Vendor Scripts to Replace

| Vendor | Current Config | AI Replacement |
|--------|----------------|----------------|
| Sysco | `VENDOR_CONFIGS["sysco"]` | Column detection |
| Vesta | `parse_vesta_packaging()` | Attribute extraction |
| Shamrock | `parse_shamrock_packaging()` | Attribute extraction |
| SM Seafood | `VENDOR_CONFIGS["smseafood"]` | Column detection |
| Noble Bread | `VENDOR_CONFIGS["noblebread"]` | Column detection |
| Sterling | `VENDOR_CONFIGS["sterling"]` | Column detection |

---

## Phase 4: Common Products UI (Week 4-5)

**Objective:** Update UI to reflect taxonomy structure.

### Current UI
- Flat list of common_products
- Text-based search only
- No attribute filtering

### Proposed UI Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| Nested tree view | 🔴 High | Group by base_ingredient → variants |
| Attribute filters | 🔴 High | Filter by variety, form, prep, etc. |
| Quick variant creation | 🟡 Medium | "Create variant" from base ingredient |
| Usage indicators | 🟡 Medium | Show which recipes/products use each |
| Bulk operations | 🟢 Low | Mass update attributes |

### Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│ Common Products                    [+ New Base Ingredient]  │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Variety ▼] [Form ▼] [Prep ▼] [Category ▼]        │
├─────────────────────────────────────────────────────────────┤
│ ▼ Carrot (12 variants)                                      │
│   ├─ Orange, Jumbo                    [Recipes: 3] [Edit]   │
│   ├─ Diced 1/2"                       [Recipes: 5] [Edit]   │
│   ├─ Baby, Peeled                     [Recipes: 2] [Edit]   │
│   └─ [+ Add Variant]                                        │
│                                                             │
│ ▼ Chicken Breast (8 variants)                               │
│   ├─ Boneless, Skinless, Natural      [Recipes: 7] [Edit]   │
│   ├─ Bone-In, Skin On                 [Recipes: 1] [Edit]   │
│   └─ [+ Add Variant]                                        │
│                                                             │
│ ▶ Tomato (6 variants)                                       │
│ ▶ Onion (4 variants)                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Connected Learning System

### How It All Works Together

```
┌─────────────────────────────────────────────────────────────────────┐
│                         IMPORT SOURCES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Recipe PDF                          Invoice CSV                     │
│       │                                   │                          │
│       ▼                                   ▼                          │
│  ┌─────────────┐                   ┌─────────────┐                  │
│  │ AI Recipe   │                   │ AI Invoice  │                  │
│  │ Parser      │                   │ Parser      │                  │
│  └──────┬──────┘                   └──────┬──────┘                  │
│         │                                  │                         │
│         │  "2 lbs chicken                  │  "CHICKEN, BRST SGL    │
│         │   breast, diced"                 │   SK ON TO NATRL"      │
│         │                                  │                         │
│         └──────────────┬───────────────────┘                        │
│                        ▼                                             │
│              ┌─────────────────────┐                                │
│              │  TAXONOMY MATCHER   │                                │
│              │                     │                                │
│              │  1. Check learned   │                                │
│              │  2. Search taxonomy │                                │
│              │  3. Fuzzy match     │                                │
│              └──────────┬──────────┘                                │
│                         │                                            │
│         ┌───────────────┼───────────────┐                           │
│         ▼               ▼               ▼                           │
│    ┌─────────┐    ┌─────────┐    ┌─────────┐                       │
│    │ Instant │    │ High    │    │ Needs   │                       │
│    │ Match   │    │ Conf.   │    │ Review  │                       │
│    │ (98%+)  │    │ (85%+)  │    │ (<85%)  │                       │
│    └────┬────┘    └────┬────┘    └────┬────┘                       │
│         │              │              │                             │
│         └──────────────┼──────────────┘                             │
│                        ▼                                             │
│              ┌─────────────────────┐                                │
│              │  LEARNING LOOP      │                                │
│              │                     │                                │
│              │  User confirms →    │                                │
│              │  ingredient_mappings│                                │
│              │  updated            │                                │
│              └──────────┬──────────┘                                │
│                         │                                            │
│                         ▼                                             │
│              Next import = instant match                             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Shared Mapping Benefits

| Scenario | Before | After |
|----------|--------|-------|
| New Sysco product | Manual lookup | Instant if seen in any invoice |
| Recipe says "chicken breast" | Fuzzy match | Exact taxonomy match |
| Vesta format changes | Update Python script | AI adapts automatically |
| New vendor onboard | Write new config | Just upload CSV |

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| 1 | Taxonomy Schema | Tables created, bridge columns added |
| 2 | Data Migration | Existing products linked to taxonomy |
| 3 | AI Invoice Parser | Core parsing services implemented |
| 4 | Invoice UI | Upload + review flow for AI-parsed invoices |
| 5 | Common Products UI | Tree view, attribute filters |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Recipe ingredient match rate | > 85% auto | Matches without user intervention |
| Invoice product match rate | > 80% auto (month 1) | Matches without review |
| New vendor setup time | < 5 minutes | Time from CSV upload to import |
| User corrections per import | < 5% of rows | Manual fixes needed |
| Common products with taxonomy | 100% | base_ingredient_id populated |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Taxonomy migration breaks recipes | Bridge columns, no FK changes yet |
| AI parsing less accurate than scripts | Run parallel, compare results |
| User confusion with new structure | Gradual UI rollout, maintain familiar patterns |
| Performance with large taxonomies | Proper indexing, caching common lookups |

---

## Related Documents

- [Ingredient Taxonomy Design](./INGREDIENT_TAXONOMY_DESIGN.md) - Full schema and migration details
- [AI Invoice Parser Design](./AI_INVOICE_PARSER_DESIGN.md) - Technical spec for invoice parsing
- [AI Recipe Parser](./completed/AI_RECIPE_PARSER.md) - Current implementation details
- [Learning Loop](./completed/LEARNING_LOOP.md) - Mapping system architecture

---

**Ready for Review:** This roadmap is ready for product/technical review before implementation begins.
