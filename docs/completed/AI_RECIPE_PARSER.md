# AI Recipe Parser - Completion Documentation

**Completed:** February 2026
**Status:** Production

---

## Overview

Automated recipe ingredient extraction using Claude API. Parses Word, PDF, and Excel documents to extract ingredients, quantities, and units with intelligent product matching.

---

## Features Implemented

### Document Parsing
- Word (.docx) - python-docx
- PDF - pypdf
- Excel (.xlsx) - openpyxl
- Claude API for structured extraction

### Multi-Strategy Product Matching
Priority order:
1. **Learned** (0.90+) - User's previous selections via learning loop
2. **Exact** (1.0) - Case-insensitive name match
3. **Base match** (0.85+) - Core ingredient word matching
4. **Contains** (0.95+) - Partial name matching
5. **Fuzzy** (0.95+) - String similarity (SequenceMatcher)
6. **Semantic** (0.70+) - pgvector embedding similarity

### Auto-Match Thresholds
- `learned` ≥ 0.90 → auto-select
- `base_match` ≥ 0.85 → auto-select
- `semantic` ≥ 0.70 → auto-select
- Others ≥ 0.95 → auto-select

### User Review Interface
- Review extracted ingredients before import
- "Did you mean?" suggestions for unmatched items
- Product search for manual selection
- "🧠 Remembered" badge for learned matches

### Learning Loop
- Records user corrections
- Applies to future parses (highest priority)
- Use count tracking for confidence boost
- See: `docs/completed/LEARNING_LOOP.md`

### Usage Limits
- Free tier: 10 parses/month
- Basic+: 100 parses/month
- Rate limit: 10 uploads/hour per org
- Only successful/partial parses count

---

## Files Modified

### Backend
- `api/app/routers/ai_parse.py` - Main endpoints
- `api/app/services/recipe_parser.py` - Claude API integration
- `api/app/services/product_matcher.py` - Multi-strategy matching
- `api/app/services/file_processor.py` - Text extraction
- `api/app/services/ingredient_mapper.py` - Learning loop
- `api/app/utils/embeddings.py` - Semantic search

### Frontend
- `frontend/src/components/RecipeImport/UploadRecipeModal.jsx` - Upload flow
- `frontend/src/components/RecipeImport/ReviewParsedRecipe.jsx` - Review interface
- `frontend/src/services/aiParseService.js` - API client

### Database
- Migration `023_add_pgvector_embeddings.py` - Vector search
- Migration `024_add_ingredient_mappings.py` - Learning loop
- Table `ai_parse_history` - Parse tracking

---

## API Endpoints

```
POST /api/ai-parse/parse-file    - Parse uploaded document
GET  /api/ai-parse/usage         - Get usage statistics
POST /api/ai-parse/create-recipe - Create recipe from parse
GET  /api/ai-parse/search-products - Product search
```

---

## Environment Variables

- `ANTHROPIC_API_KEY` - Required for Claude API
- `VOYAGE_API_KEY` - Optional, enables semantic search

---

## Cost Estimates

- Claude API: ~$0.005-$0.02 per recipe parse
- Voyage AI: ~$0.001 per embedding query
- Very affordable for value provided

---

## Future Enhancements (Planned)

- Method step parsing (cooking instructions)
- Better unit handling (fractions, recipe-specific)
- Bulk recipe import
