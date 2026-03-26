# Learning Loop - Completion Documentation

**Completed:** March 2026
**Status:** Production

---

## Overview

Records user ingredient→product corrections to improve future AI recipe parsing. Designed with three-tier security model for future network effect across tenants.

---

## Features Implemented

### Mapping Storage
- Records user's ingredient-to-product selections
- Tracks confidence score and match type
- Use count for repeated selections
- Opt-in sharing flag for network effect

### Match Types Recorded
- `user_selected` - User manually chose via search
- `accepted_suggestion` - User accepted AI suggestion
- `search` - User found via product search

### Priority in Matching
- Learned mappings checked FIRST (before all algorithmic matches)
- Confidence 0.95-0.99 based on use count
- Falls back to algorithmic if no learned match

### UI Integration
- "🧠 Remembered" badge on auto-matched items
- User can change learned matches
- Changes update existing mapping

---

## Files Modified

### Backend
- `api/app/services/ingredient_mapper.py` - Core service
  - `record_ingredient_mapping()` - Store user selection
  - `get_learned_mapping()` - Retrieve org-specific mapping
  - `get_shared_mapping()` - Future: cross-tenant lookup
- `api/app/services/product_matcher.py` - Strategy 0 integration
- `api/app/routers/ai_parse.py` - Recording on recipe create

### Frontend
- `frontend/src/components/RecipeImport/ReviewParsedRecipe.jsx`
  - Track selection_type in user selections
  - Pass learning fields on recipe creation
  - Display "🧠 Remembered" badge

### Database
- Migration `024_add_ingredient_mappings.py`

---

## Database Schema

```sql
CREATE TABLE ingredient_mappings (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL,    -- Tenant isolation
    raw_name VARCHAR(255) NOT NULL,       -- Normalized text ("cilantro")
    common_product_id INTEGER,            -- User's selection
    is_shared BOOLEAN DEFAULT FALSE,      -- Network effect opt-in
    confidence_score FLOAT,               -- Match quality
    match_type VARCHAR(20),               -- How selected
    use_count INTEGER DEFAULT 1,          -- Times applied
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    created_by INTEGER,                   -- User who made selection

    UNIQUE(organization_id, raw_name)
);

-- Fast lookup during parsing
CREATE INDEX idx_ingredient_mappings_lookup
ON ingredient_mappings(organization_id, LOWER(raw_name));

-- Future: query shared mappings
CREATE INDEX idx_ingredient_mappings_shared
ON ingredient_mappings(LOWER(raw_name))
WHERE is_shared = TRUE;
```

---

## Three-Tier Security Model

Designed to support future network effect:

1. **Tenant-private (never shared)**
   - Pricing, volumes, costs
   - User information

2. **Anonymized shared (opt-in)**
   - Ingredient mappings
   - `is_shared` flag per mapping
   - No pricing or user data exposed

3. **Fully public**
   - Base taxonomy
   - Unit normalizations
   - Standard ingredient names

---

## How It Works

### Recording
```python
# When user saves recipe with corrections
if ingredient.was_user_selected and ingredient.common_product_id:
    record_ingredient_mapping(
        organization_id=org_id,
        raw_name=ingredient.original_parsed_name,
        common_product_id=ingredient.common_product_id,
        user_id=user_id,
        match_type=ingredient.selection_type
    )
```

### Retrieval
```python
# In product_matcher.match_products()
learned = get_learned_mapping(org_id, ingredient_name, conn)
if learned:
    # Return learned match as highest priority
    return [learned] + other_matches[:2]
```

---

## Confidence Scoring

Learned matches get confidence based on use count:
- 1 use: 0.95
- 2-4 uses: 0.96
- 5-9 uses: 0.97
- 10-19 uses: 0.98
- 20+ uses: 0.99

Higher use count = higher confidence = more likely auto-select.

---

## Future Enhancements

- **Network Effect:** Query shared mappings when no org-specific match
- **Confidence Decay:** Reduce confidence for stale mappings
- **Bulk Export/Import:** Transfer mappings between orgs
- **Admin Override:** Super admin can edit shared mappings
