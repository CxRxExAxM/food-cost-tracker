# AI Recipe Parser - Design Document

**Feature:** Automate recipe ingredient entry by parsing Word/PDF/Excel documents using Claude API

**Status:** Design Phase

**Target Release:** Phase 5 (Post-MVP Enhancement)

---

## Table of Contents

1. [Database Schema](#database-schema)
2. [API Endpoints](#api-endpoints)
3. [UI/UX Flow](#uiux-flow)
4. [File Structure](#file-structure)
5. [Technical Implementation](#technical-implementation)
6. [Usage Limits & Tiers](#usage-limits--tiers)
7. [Error Handling](#error-handling)

---

## Database Schema

### New Table: `ai_parse_usage`

Track AI parsing usage for tier-based limits and audit trail.

**Important:** Only 'success' and 'partial' statuses count toward monthly limits. Failed parses don't consume credits.

```sql
CREATE TABLE ai_parse_usage (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    outlet_id INTEGER NOT NULL REFERENCES outlets(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL, -- 'docx', 'pdf', 'xlsx'
    parse_status VARCHAR(20) NOT NULL, -- 'success', 'partial', 'failed'
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    ingredients_count INTEGER, -- Number of ingredients parsed
    matched_count INTEGER, -- Number of ingredients auto-matched
    error_message TEXT, -- Error details if failed
    parse_time_ms INTEGER, -- Processing time
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT check_parse_status CHECK (parse_status IN ('success', 'partial', 'failed'))
);

-- Indexes for performance and rate limiting
CREATE INDEX idx_ai_parse_organization ON ai_parse_usage(organization_id);
CREATE INDEX idx_ai_parse_user ON ai_parse_usage(user_id);
CREATE INDEX idx_ai_parse_created ON ai_parse_usage(created_at);
CREATE INDEX idx_ai_parse_status ON ai_parse_usage(parse_status);
CREATE INDEX idx_ai_parse_recent_attempts ON ai_parse_usage(organization_id, created_at);
```

### Additions to `recipes` table

Add optional field to track AI-imported recipes:

```sql
ALTER TABLE recipes ADD COLUMN imported_from_ai BOOLEAN DEFAULT FALSE;
ALTER TABLE recipes ADD COLUMN import_filename VARCHAR(255);
```

---

## API Endpoints

### 1. POST `/api/recipes/parse-file`

**Purpose:** Parse uploaded document and extract recipe data with product matching

**Auth:** Required (Chef or Admin roles only)

**Request:**
```
Content-Type: multipart/form-data

Fields:
- file: File upload (.docx, .pdf, .xlsx)
- outlet_id: Integer (current outlet context)
```

**Response (Success 200):**
```json
{
  "parse_id": 123,
  "recipe_name": "Tzatziki Sauce",
  "yield": {
    "quantity": 2.0,
    "unit": "quart",
    "unit_id": 15
  },
  "ingredients": [
    {
      "parsed_name": "cucumber",
      "quantity": 10.0,
      "unit": "LB",
      "unit_id": 8,
      "normalized_quantity": 10.0,
      "normalized_unit": "LB",
      "normalized_unit_id": 8,
      "prep_note": "sliced",
      "suggested_products": [
        {
          "common_product_id": 123,
          "common_name": "Cucumber",
          "category": "Produce",
          "confidence": 0.95,
          "exact_match": true
        },
        {
          "common_product_id": 124,
          "common_name": "English Cucumber",
          "category": "Produce",
          "confidence": 0.85,
          "exact_match": false
        }
      ],
      "needs_review": false
    },
    {
      "parsed_name": "greek yogurt",
      "quantity": 2.5,
      "unit": "quart",
      "unit_id": 15,
      "normalized_quantity": 80.0,
      "normalized_unit": "OZ",
      "normalized_unit_id": 12,
      "prep_note": null,
      "suggested_products": [],
      "needs_review": true
    }
  ],
  "usage": {
    "used": 6,
    "limit": 10,
    "remaining": 4
  }
}
```

**Response (Error 429 - Limit Exceeded):**
```json
{
  "detail": "Monthly AI parse limit exceeded. Upgrade to Basic tier for more parses.",
  "usage": {
    "used": 10,
    "limit": 10,
    "tier": "free"
  }
}
```

**Response (Error 400 - Invalid File):**
```json
{
  "detail": "Invalid file format. Supported: .docx, .pdf, .xlsx"
}
```

### 2. POST `/api/recipes/create-from-parse`

**Purpose:** Create draft recipe from reviewed parse results

**Auth:** Required (Chef or Admin roles only)

**Request:**
```json
{
  "parse_id": 123,
  "name": "Tzatziki Sauce",
  "outlet_id": 1,
  "yield_quantity": 2.0,
  "yield_unit_id": 15,
  "description": "Traditional Greek yogurt cucumber sauce",
  "category": "Sauces",
  "ingredients": [
    {
      "common_product_id": 123,
      "quantity": 10.0,
      "unit_id": 8,
      "notes": "sliced"
    },
    {
      "common_product_id": 456,
      "quantity": 80.0,
      "unit_id": 12,
      "notes": null
    }
  ]
}
```

**Response (Success 201):**
```json
{
  "recipe_id": 789,
  "name": "Tzatziki Sauce",
  "status": "draft",
  "message": "Recipe created successfully. Opening editor..."
}
```

### 3. GET `/api/ai-parse/usage-stats`

**Purpose:** Get current month's usage statistics

**Auth:** Required

**Response:**
```json
{
  "organization_id": 1,
  "tier": "free",
  "current_month": "2024-12",
  "used": 6,
  "limit": 10,
  "remaining": 4,
  "history": [
    {
      "filename": "recipes.docx",
      "created_at": "2024-12-15T10:30:00Z",
      "status": "success",
      "ingredients_count": 8
    }
  ]
}
```

### 4. POST `/api/common-products/quick-create`

**Purpose:** Inline product creation during review flow

**Auth:** Required (Chef or Admin roles only)

**Request:**
```json
{
  "common_name": "Greek Yogurt",
  "category": "Dairy",
  "subcategory": "Yogurt",
  "organization_id": 1
}
```

**Response (Success 201):**
```json
{
  "common_product_id": 999,
  "common_name": "Greek Yogurt",
  "category": "Dairy",
  "message": "Product created successfully"
}
```

---

## UI/UX Flow

### 1. Entry Point - Recipe List Page

**Location:** `/recipes` page

**UI Addition:**
```
[Create Recipe] [Upload Document 📄]
```

- "Upload Document" button next to "Create Recipe"
- Only visible when outlet is selected
- Only enabled for Chef/Admin roles
- Disabled if monthly limit reached (shows tooltip with upgrade prompt)

### 2. Upload Modal

**Component:** `UploadRecipeModal.jsx`

**UI Elements:**
```
┌─────────────────────────────────────────┐
│  Upload Recipe Document                 │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │                                   │ │
│  │   📄 Drag & drop file here       │ │
│  │   or click to browse              │ │
│  │                                   │ │
│  │   Supported: .docx, .pdf, .xlsx   │ │
│  └───────────────────────────────────┘ │
│                                         │
│  Selected: recipes.docx (2.3 MB)       │
│                                         │
│  Usage: 6/10 parses this month         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━    │
│                                         │
│  [Cancel]          [Parse Recipe →]    │
└─────────────────────────────────────────┘
```

**States:**
- Empty: Drag/drop zone active
- File selected: Shows filename, size, parse button
- Processing: Shows spinner with progress messages
- Error: Shows error message with retry option

### 3. Processing State

**UI:**
```
┌─────────────────────────────────────────┐
│  Parsing Recipe...                      │
│                                         │
│  ⏳ Analyzing document...               │
│  ✓ Extracting ingredients...           │
│  → Matching products...                 │
│                                         │
│  This usually takes 10-15 seconds       │
└─────────────────────────────────────────┘
```

**Progress Steps:**
1. Uploading file
2. Analyzing document
3. Extracting ingredients
4. Matching products
5. Complete

### 4. Review Page

**Component:** `ReviewParsedRecipe.jsx`

**Full-screen modal interface:**

```
┌─────────────────────────────────────────────────────────────┐
│  Review Parsed Recipe                           [X Close]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Recipe Name: [Tzatziki Sauce                    ]         │
│  Yield: [2] [quart ▼]                                      │
│  Category: [Sauces             ]  (optional)               │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Ingredients (8)                                            │
│                                                             │
│  1. Cucumber - 10 LB (sliced)                              │
│     Product: [Cucumber ✓                      ▼]           │
│     ┌─────────────────────────────────────┐               │
│     │ ✓ Cucumber (Produce) - Exact match  │ ← Selected    │
│     │   English Cucumber (Produce)        │               │
│     │   Persian Cucumber (Produce)        │               │
│     │ + Create New Product                │               │
│     │ 🔍 Search all products...           │               │
│     └─────────────────────────────────────┘               │
│                                                             │
│  2. Greek Yogurt - 2.5 quart (80 OZ)          ⚠️           │
│     Product: [Search for product...        ▼]             │
│     No matches found - please select or create product    │
│     [+ Create "Greek Yogurt"]                             │
│                                                             │
│  3. Garlic - 2 OZ (minced)                                │
│     Product: [Garlic ✓                      ▼]            │
│                                                             │
│  ... (5 more ingredients)                                  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ⚠️ 2 ingredients need product selection                   │
│                                                             │
│  [Cancel]              [Save as Draft →]                   │
└─────────────────────────────────────────────────────────────┘
```

**Ingredient Row States:**

**Exact Match (Auto-selected):**
```
✓ Cucumber - 10 LB (sliced)
Product: [Cucumber ✓] ← Green checkmark, pre-selected
```

**Multiple Matches (Needs Selection):**
```
⚠️ Onion - 2 LB (diced)
Product: [Select product...  ▼] ← Yellow warning, dropdown shows top 3
```

**No Match (Needs Creation or Search):**
```
⚠️ Greek Yogurt - 2.5 quart (80 OZ)
Product: [Search or create...  ▼]
[+ Create "Greek Yogurt"] ← Quick create button
```

**Inline Product Creation:**

When user clicks "+ Create New Product", inline form appears:

```
┌─────────────────────────────────────┐
│  Create New Product                 │
│                                     │
│  Name: [Greek Yogurt           ]    │
│  Category: [Dairy        ▼]         │
│  Subcategory: [Yogurt    ▼]         │
│                                     │
│  [Cancel]  [Create & Select →]     │
└─────────────────────────────────────┘
```

After creation, product is auto-selected in dropdown.

### 5. Draft Recipe Editor

After clicking "Save as Draft", user is redirected to:

```
/recipes/789/edit
```

With pre-filled data from parse:
- Recipe name
- Yield
- Ingredients with quantities and products
- Category (if detected)

User can then:
- Add method/instructions
- Adjust quantities
- Add allergen notes
- Save as active recipe

---

## File Structure

### Frontend

```
frontend/src/
├── components/
│   └── RecipeImport/
│       ├── UploadRecipeModal.jsx         (Upload + processing UI)
│       ├── ReviewParsedRecipe.jsx        (Full review interface)
│       ├── IngredientMatchRow.jsx        (Single ingredient matching UI)
│       ├── ProductQuickCreate.jsx        (Inline product creation)
│       └── ParseUsageIndicator.jsx       (Usage stats display)
├── pages/
│   └── Recipes/
│       └── RecipeList.jsx                (Add upload button here)
├── services/
│   └── aiParseService.js                 (API calls for parsing)
└── styles/
    └── RecipeImport.css                  (Styling for import flow)
```

### Backend

```
api/app/
├── routers/
│   ├── ai_parse.py                       (NEW - AI parsing endpoints)
│   ├── recipes.py                        (Add create-from-parse endpoint)
│   └── common_products.py                (Add quick-create endpoint)
├── services/
│   ├── recipe_parser.py                  (NEW - Claude API integration)
│   ├── product_matcher.py                (NEW - Fuzzy matching logic)
│   ├── file_processor.py                 (NEW - Extract text from files)
│   └── unit_converter.py                 (NEW - Unit normalization)
├── schemas/
│   └── ai_parse.py                       (NEW - Pydantic models)
└── utils/
    └── tier_limits.py                    (NEW - Usage limit checking)
```

---

## Technical Implementation

### 1. File Processing

**Dependencies:**
```
python-docx==1.1.0      # Word documents
pypdf==4.0.0            # PDF parsing
openpyxl==3.1.2         # Excel files
```

**File Processor (`file_processor.py`):**

```python
async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text from uploaded document."""

    if file.filename.endswith('.docx'):
        return extract_from_docx(file)
    elif file.filename.endswith('.pdf'):
        return extract_from_pdf(file)
    elif file.filename.endswith('.xlsx'):
        return extract_from_excel(file)
    else:
        raise ValueError("Unsupported file format")
```

### 2. Claude API Integration

**Recipe Parser (`recipe_parser.py`):**

```python
import anthropic

async def parse_recipe_with_claude(text: str) -> dict:
    """
    Parse recipe text using Claude API.

    Returns structured recipe data.
    """

    client = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    prompt = f"""
    Parse the following recipe and extract structured data.

    Return ONLY valid JSON in this exact format:
    {{
      "name": "recipe name",
      "yield": {{"quantity": 2, "unit": "quart"}},
      "description": "brief description",
      "category": "category name",
      "ingredients": [
        {{
          "name": "cucumber",
          "quantity": 10,
          "unit": "LB",
          "prep_note": "sliced"
        }}
      ]
    }}

    Recipe text:
    {text}
    """

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return json.loads(message.content[0].text)
```

### 3. Product Matching Algorithm

**Product Matcher (`product_matcher.py`):**

```python
from difflib import SequenceMatcher

def match_products(
    ingredient_name: str,
    organization_id: int,
    conn
) -> list[dict]:
    """
    Find matching common products using fuzzy matching.

    Returns:
        List of matches sorted by confidence (0-1)
    """

    # Get all common products for organization
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, common_name, category, subcategory
        FROM common_products
        WHERE organization_id = %s AND is_active = 1
    """, (organization_id,))

    products = cursor.fetchall()

    matches = []
    ingredient_lower = ingredient_name.lower()

    for product in products:
        product_name_lower = product['common_name'].lower()

        # Exact match
        if ingredient_lower == product_name_lower:
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'confidence': 1.0,
                'exact_match': True
            })
            continue

        # Contains match
        if ingredient_lower in product_name_lower or product_name_lower in ingredient_lower:
            confidence = SequenceMatcher(None, ingredient_lower, product_name_lower).ratio()
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'confidence': confidence,
                'exact_match': False
            })
            continue

        # Fuzzy match (similarity > 0.7)
        similarity = SequenceMatcher(None, ingredient_lower, product_name_lower).ratio()
        if similarity > 0.7:
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'confidence': similarity,
                'exact_match': False
            })

    # Sort by confidence, return top 3
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    return matches[:3]
```

### 4. Unit Normalization

**Unit Converter (`unit_converter.py`):**

```python
# Conversion factors to base units
CONVERSIONS = {
    # Volume (to fluid ounces)
    'gallon': 128,
    'quart': 32,
    'pint': 16,
    'cup': 8,
    'fl oz': 1,

    # Weight (to ounces)
    'lb': 16,
    'oz': 1,

    # Count
    'each': 1,
}

def normalize_quantity(quantity: float, unit: str) -> tuple[float, str]:
    """
    Normalize quantity to preferred units.

    Returns: (normalized_quantity, normalized_unit)
    """

    unit_lower = unit.lower()

    # Volume normalization
    if unit_lower in ['gallon', 'quart', 'pint', 'cup']:
        fl_oz = quantity * CONVERSIONS[unit_lower]
        return (fl_oz, 'FL OZ')

    # Weight normalization
    if unit_lower == 'lb':
        oz = quantity * 16
        return (oz, 'OZ')

    # No conversion needed
    return (quantity, unit.upper())
```

---

## Usage Limits & Tiers

### Credit Protection

**Important:** Users only consume credits for successful parses. Failed parses don't count toward monthly limits.

**What Counts Toward Limit:**
- ✅ `success` - Recipe fully parsed with all data
- ✅ `partial` - Recipe parsed but some data missing (user still got value)

**What Doesn't Count:**
- ❌ `failed` - No recipe detected, API error, file corruption

**Rate Limiting:** To prevent abuse, all upload attempts (successful or not) are rate-limited to 10 per hour per organization.

### Tier Limits

| Tier       | Monthly Limit | Cost/Parse | Total Cost |
|------------|---------------|------------|------------|
| Free       | 10            | ~$0.02     | ~$0.20     |
| Basic      | 100           | ~$0.02     | ~$2.00     |
| Pro        | 100           | ~$0.02     | ~$2.00     |
| Enterprise | Unlimited     | ~$0.02     | Variable   |

*Note: Limits only count successful/partial parses, not failures.*

### Limit Checking

**Tier Limits Utility (`tier_limits.py`):**

```python
def get_monthly_parse_limit(tier: str) -> int | None:
    """Get parse limit for tier. None = unlimited."""
    limits = {
        'free': 10,
        'basic': 100,
        'pro': 100,
        'enterprise': None  # Unlimited
    }
    return limits.get(tier, 10)

def check_parse_limit(organization_id: int, conn) -> tuple[bool, dict]:
    """
    Check if organization can parse another recipe this month.

    Only counts 'success' and 'partial' status parses toward limit.
    Failed parses don't consume credits.

    Returns: (can_parse, usage_stats)
    """

    # Get organization tier
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subscription_tier
        FROM organizations
        WHERE id = %s
    """, (organization_id,))

    org = cursor.fetchone()
    tier = org['subscription_tier']
    limit = get_monthly_parse_limit(tier)

    # Count this month's usage (only successful/partial)
    cursor.execute("""
        SELECT COUNT(*) as used
        FROM ai_parse_usage
        WHERE organization_id = %s
        AND created_at >= date_trunc('month', CURRENT_DATE)
        AND parse_status IN ('success', 'partial')
    """, (organization_id,))

    usage = cursor.fetchone()['used']

    can_parse = (limit is None) or (usage < limit)

    return can_parse, {
        'tier': tier,
        'used': usage,
        'limit': limit or 'unlimited',
        'remaining': (limit - usage) if limit else 'unlimited'
    }

def check_rate_limit(organization_id: int, conn) -> bool:
    """
    Check if organization has exceeded hourly upload rate limit.

    Counts ALL attempts (success, partial, failed) to prevent abuse.
    Limit: 10 attempts per hour.

    Returns: True if within limit, False if exceeded
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) as attempts
        FROM ai_parse_usage
        WHERE organization_id = %s
        AND created_at > NOW() - INTERVAL '1 hour'
    """, (organization_id,))

    attempts = cursor.fetchone()['attempts']
    return attempts < 10
```

---

## Error Handling

### 1. File Upload Errors

**Error:** File too large (>10MB)
```json
{
  "detail": "File size exceeds 10MB limit",
  "max_size": "10MB"
}
```

**Error:** Invalid file format
```json
{
  "detail": "Unsupported file format. Supported: .docx, .pdf, .xlsx",
  "filename": "recipe.txt"
}
```

### 2. Parsing Errors

**Error:** Claude API failure
```json
{
  "detail": "AI parsing service unavailable. Please try again later.",
  "parse_id": 123,
  "status": "failed"
}
```

**Error:** No recipe detected
```json
{
  "detail": "Could not detect recipe structure in document. Please ensure document contains recipe name and ingredients.",
  "parse_id": 123
}
```

### 3. Limit Errors

**Error:** Monthly limit exceeded
```json
{
  "detail": "Monthly AI parse limit exceeded (10/10 used). Upgrade to Basic tier for 100 parses/month.",
  "usage": {
    "used": 10,
    "limit": 10,
    "tier": "free"
  },
  "upgrade_url": "/settings/subscription"
}
```

### 4. Permission Errors

**Error:** Viewer role attempting to parse
```json
{
  "detail": "Only Chef and Admin roles can upload recipes",
  "required_role": "chef"
}
```

### 5. Graceful Degradation

- If Claude API is down, show friendly error with manual entry option
- If product matching fails, allow manual search/creation
- If unit parsing fails, show original text for manual review
- All errors logged to ai_parse_usage table with error_message

---

## Success Metrics

### Track:
1. Parse success rate (target: >90%)
2. Auto-match rate (target: >70% of ingredients)
3. Time saved vs manual entry (estimate: 5-10 minutes/recipe)
4. User adoption (% of recipes created via AI vs manual)
5. Tier upgrade conversions from limit prompts

### Optimization:
- Improve prompt engineering based on failure patterns
- Expand product matching with ML embeddings (future)
- Add recipe format templates (future)
- Implement batch import (future)

---

**Next Steps:**
1. Create database migration for ai_parse_usage table
2. Implement backend file processing and Claude API integration
3. Build frontend upload and review components
4. Test with real recipe documents
5. Deploy to dev environment for user testing

---

**Last Updated:** December 17, 2024
