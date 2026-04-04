# AI Invoice Parser Design

**Date:** March 26, 2026
**Status:** Planning
**Dependencies:** Ingredient Taxonomy (Phase 1)

---

## Overview

Replace vendor-specific Python cleaning scripts with an AI-powered universal invoice parser. Uses Claude for column detection and attribute extraction, with a learning loop that improves accuracy over time.

**Goals:**
- New vendor = zero code changes (just upload)
- Self-healing when vendor formats change
- Cross-vendor product deduplication via taxonomy
- Shared mappings enable network effect

---

## Architecture

### Current Flow (Per-Vendor Scripts)
```
Sysco CSV → VENDOR_CONFIGS["sysco"] → clean_dataframe() → products table
Vesta CSV → VENDOR_CONFIGS["vesta"] → parse_vesta_packaging() → products table
Shamrock CSV → VENDOR_CONFIGS["shamrock"] → parse_shamrock_packaging() → products table
```

### Future Flow (Universal AI Parser)
```
Any CSV → Column Detection (AI) → Attribute Extraction (AI) → Taxonomy Match → Review UI → products + variants
              │                          │                          │
              └──────────────────────────┴──────────────────────────┘
                                         │
                                   Learning Loop
                                   (instant match next time)
```

---

## Components

### 1. Column Detection Service

**Purpose:** Auto-detect CSV column purposes without vendor-specific config.

**Input:** First 10 rows of CSV as text
**Output:** Column mapping

```python
# api/app/services/invoice_column_detector.py

COLUMN_DETECTION_PROMPT = """Analyze this CSV and identify column purposes.

CSV Sample:
{csv_sample}

Identify which columns contain:
- sku: Product number/code (e.g., SUPC, Item #, Product Code)
- description: Product name/description
- brand: Brand name (may be in description)
- pack: Number of units per case (e.g., 24, 6, 1)
- size: Size of each unit (e.g., 5, 10, 4.5)
- unit: Unit of measure (e.g., LB, OZ, CT, GAL)
- packaging: Combined pack/size/unit field (e.g., "4/5 LB", "24/4OZ")
- case_price: Price per case
- unit_price: Price per unit
- category: Product category

Return JSON:
{
  "columns": {
    "sku": "column_name or null",
    "description": "column_name",
    "brand": "column_name or null",
    "pack": "column_name or null",
    "size": "column_name or null",
    "unit": "column_name or null",
    "packaging": "column_name or null",
    "case_price": "column_name or null",
    "unit_price": "column_name or null"
  },
  "skip_rows": number_of_header_rows_to_skip,
  "confidence": 0.0-1.0
}"""

async def detect_columns(csv_content: str) -> dict:
    """Detect CSV column purposes using Claude."""
    # Take first 10 rows for analysis
    lines = csv_content.split('\n')[:10]
    sample = '\n'.join(lines)

    response = await call_claude(
        COLUMN_DETECTION_PROMPT.format(csv_sample=sample),
        model="claude-sonnet"  # Use existing configured model
    )

    return parse_json_response(response)
```

### 2. Attribute Extraction Service

**Purpose:** Parse product descriptions into structured attributes.

**Input:** Product description string
**Output:** Structured attributes dict

```python
# api/app/services/invoice_attribute_extractor.py

ATTRIBUTE_EXTRACTION_PROMPT = """Parse this food product description into structured attributes.

Description: {description}
Brand (if known): {brand}
Packaging info (if available): {packaging}

Extract applicable attributes:
- base_ingredient: Core item name (e.g., "Chicken Breast", "Carrot", "Cheddar Cheese")
- variety: Color or type variant (e.g., "Red", "Rainbow", "Sharp")
- form: Size grade (e.g., "Baby", "Jumbo", "Florets")
- cut: Meat/fish cut (e.g., "Breast", "Thigh", "Fillet", "Loin")
- prep: Processing done (e.g., "Diced", "Sliced", "Boneless", "Peeled")
- cut_size: Specific dimensions (e.g., "1/4\"", "1/2\"", "3/8\"")
- skin: Skin status for proteins (e.g., "Skin On", "Skin Off")
- bone: Bone status (e.g., "Boneless", "Bone-In", "Frenched")
- grade: Quality grade (e.g., "Natural", "Choice", "Prime", "Grade A")
- state: Temperature state (e.g., "Fresh", "Frozen", "IQF")
- pack: Number per case (integer)
- size: Size value (number)
- unit: Unit of measure (e.g., "LB", "OZ", "CT")
- is_catch_weight: true if variable weight item

Return JSON with applicable fields only. Use null for unknown."""

async def extract_attributes(
    description: str,
    brand: str = None,
    packaging: str = None
) -> dict:
    """Extract structured attributes from product description."""

    response = await call_claude(
        ATTRIBUTE_EXTRACTION_PROMPT.format(
            description=description,
            brand=brand or "unknown",
            packaging=packaging or "none"
        ),
        model="claude-sonnet"
    )

    return parse_json_response(response)
```

### 3. Taxonomy Matcher

**Purpose:** Match extracted attributes to base_ingredients and variants.

```python
# api/app/services/invoice_taxonomy_matcher.py

def match_to_taxonomy(
    raw_description: str,
    attributes: dict,
    organization_id: int,
    conn
) -> dict:
    """Match parsed attributes to taxonomy, creating entries if needed."""

    # 1. Check learning loop first (instant match)
    learned = get_learned_invoice_mapping(organization_id, raw_description, conn)
    if learned:
        return {
            "match_type": "learned",
            "base_ingredient_id": learned["base_ingredient_id"],
            "variant_id": learned["variant_id"],
            "confidence": 0.98,
            "needs_review": False
        }

    # 2. Find base ingredient
    base_name = attributes.get("base_ingredient")
    base = find_base_ingredient(base_name, conn)

    if not base:
        # Search with fuzzy/semantic matching
        base_matches = search_base_ingredients(base_name, conn)
        if base_matches and base_matches[0]["confidence"] > 0.85:
            base = base_matches[0]
        else:
            # Will need to create - flag for review
            return {
                "match_type": "new_base",
                "suggested_base_name": base_name,
                "attributes": attributes,
                "confidence": 0.0,
                "needs_review": True
            }

    # 3. Find or suggest variant
    variant = find_variant_by_attributes(base["id"], attributes, conn)

    if variant:
        return {
            "match_type": "exact_variant",
            "base_ingredient_id": base["id"],
            "variant_id": variant["id"],
            "confidence": 0.95,
            "needs_review": False
        }

    # 4. Find similar variants for suggestions
    similar = find_similar_variants(base["id"], attributes, conn)

    return {
        "match_type": "new_variant",
        "base_ingredient_id": base["id"],
        "variant_id": None,
        "suggested_attributes": attributes,
        "similar_variants": similar[:3],
        "confidence": 0.7,
        "needs_review": True
    }
```

### 4. Learning Loop Integration

**Reuse existing ingredient_mappings table with extensions:**

```sql
-- Add invoice-specific fields to ingredient_mappings
ALTER TABLE ingredient_mappings
ADD COLUMN source_type VARCHAR(20) DEFAULT 'recipe',  -- 'recipe' or 'invoice'
ADD COLUMN vendor_code VARCHAR(20),                    -- distributor code
ADD COLUMN base_ingredient_id INTEGER REFERENCES base_ingredients(id),
ADD COLUMN variant_id INTEGER REFERENCES ingredient_variants(id);

-- Index for invoice lookups
CREATE INDEX idx_ingredient_mappings_invoice
ON ingredient_mappings(organization_id, vendor_code, LOWER(raw_name))
WHERE source_type = 'invoice';
```

```python
# api/app/services/invoice_learning.py

def record_invoice_mapping(
    organization_id: int,
    raw_description: str,
    vendor_code: str,
    base_ingredient_id: int,
    variant_id: int,
    user_id: int,
    conn,
    was_corrected: bool = False
):
    """Record user-confirmed invoice product mapping."""

    normalized = normalize_raw_name(raw_description)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO ingredient_mappings (
            organization_id, raw_name, base_ingredient_id, variant_id,
            source_type, vendor_code, match_type, created_by, use_count
        ) VALUES (%s, %s, %s, %s, 'invoice', %s, %s, %s, 1)
        ON CONFLICT (organization_id, raw_name)
        DO UPDATE SET
            base_ingredient_id = EXCLUDED.base_ingredient_id,
            variant_id = EXCLUDED.variant_id,
            use_count = ingredient_mappings.use_count + 1,
            updated_at = NOW()
    """, (
        organization_id, normalized, base_ingredient_id, variant_id,
        vendor_code, 'user_confirmed' if was_corrected else 'auto_matched',
        user_id
    ))
```

---

## API Endpoints

### Parse Invoice File
```
POST /api/invoices/parse-file
```

**Request:** multipart/form-data
- file: CSV/Excel file
- outlet_id: Target outlet
- vendor_code: Optional (for learning loop context)

**Response:**
```json
{
  "parse_id": 123,
  "detected_columns": {
    "sku": "SUPC",
    "description": "Desc",
    "case_price": "Case $"
  },
  "products": [
    {
      "row_number": 1,
      "raw_description": "CHICKEN, BRST SGL SK ON TO NATRL",
      "sku": "3503261",
      "parsed_attributes": {
        "base_ingredient": "Chicken Breast",
        "cut": "Single",
        "skin": "Skin On",
        "bone": "Trim Off",
        "grade": "Natural"
      },
      "taxonomy_match": {
        "match_type": "exact_variant",
        "base_ingredient_id": 5,
        "variant_id": 12,
        "confidence": 0.95,
        "needs_review": false
      },
      "pack": 24,
      "size": 5.0,
      "unit": "OZ",
      "case_price": 90.20,
      "unit_price": 4.51
    }
  ],
  "summary": {
    "total_rows": 50,
    "auto_matched": 42,
    "needs_review": 8,
    "new_products": 3
  }
}
```

### Confirm and Import
```
POST /api/invoices/confirm-import
```

**Request:**
```json
{
  "parse_id": 123,
  "outlet_id": 1,
  "effective_date": "2026-03-26",
  "products": [
    {
      "row_number": 1,
      "sku": "3503261",
      "base_ingredient_id": 5,
      "variant_id": 12,
      "was_corrected": false
    },
    {
      "row_number": 8,
      "sku": "NEW123",
      "create_base": {
        "name": "Duck Leg",
        "category": "Poultry"
      },
      "create_variant": {
        "prep": "Confit",
        "state": "Frozen"
      },
      "was_corrected": true
    }
  ]
}
```

---

## Frontend Components

### InvoiceUploadModal.jsx
- Drag-drop file upload
- Optional vendor selection (for context)
- Progress indicators

### ReviewParsedInvoice.jsx
- Column mapping preview (editable if AI got it wrong)
- Product list with parsed attributes
- Inline editing for corrections
- "Did you mean?" suggestions
- Bulk actions (approve all confident matches)

### Common Product Management (Enhanced)
- Tree view grouped by base ingredient
- Attribute filters
- Create/edit variants inline
- See which invoices/recipes use each variant

---

## Cost Estimates

| Operation | Model | Cost per call | Calls per import |
|-----------|-------|---------------|------------------|
| Column detection | Sonnet | ~$0.01 | 1 |
| Attribute extraction | Sonnet | ~$0.02 | Per unique product |
| Total (50 products, first time) | — | ~$1.00 | — |
| Total (50 products, 80% learned) | — | ~$0.20 | — |

*Note: Using existing Sonnet configuration for simplicity. Can optimize to Haiku later if cost becomes a concern.*

---

## Migration from Current System

### Phase 1: Parallel Operation
- Keep existing VENDOR_CONFIGS and clean_dataframe()
- Add "Parse with AI" option to upload UI
- Collect data on AI accuracy vs script accuracy

### Phase 2: AI Primary, Scripts Fallback
- AI parsing becomes default
- Scripts run only if AI confidence < threshold
- Continue building learning loop data

### Phase 3: Scripts Deprecated
- Remove vendor-specific parsing code
- Keep only minimal column hints as optional config
- Scripts archived, not deleted (emergency fallback)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Auto-match rate (after 3 months) | > 90% |
| New vendor setup time | < 5 minutes |
| User corrections per import | < 5% of rows |
| Parse accuracy vs manual | > 98% |

---

## Open Questions

1. **Batch vs streaming:** Parse all products up front, or stream results as parsed?
2. **Confidence threshold:** What confidence level triggers auto-import vs review?
3. **Shared mappings:** Enable cross-tenant sharing for invoice mappings too?
4. **Price anomaly detection:** Flag unusual prices during parsing?

---

## Related Documents

- [Ingredient Taxonomy Design](./INGREDIENT_TAXONOMY_DESIGN.md)
- [AI Recipe Parser](./completed/AI_RECIPE_PARSER.md)
- [Learning Loop](./completed/LEARNING_LOOP.md)
