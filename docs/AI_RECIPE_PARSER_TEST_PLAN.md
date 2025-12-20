# AI Recipe Parser - Testing Plan

**Test Environment:** https://food-cost-tracker-dev.onrender.com

**Test Credentials:**
- Email: demo@test.com
- Password: demo1234

---

## Pre-Test Setup Checklist

- [ ] Render environment variable `ANTHROPIC_API_KEY` is set
- [ ] Database migration 005 has run successfully
- [ ] Dependencies installed (anthropic, python-docx, pypdf)
- [ ] Dev environment deployment is live

---

## Automated Playwright Test Workflow

### Test 1: Upload Modal Flow
**Purpose:** Verify upload modal opens and displays correctly

**Steps:**
1. Navigate to `/recipes` page
2. Verify "Upload Document" button (📤) is present
3. Click upload button
4. Verify upload modal opens
5. Verify drag-and-drop zone is visible
6. Verify usage stats display
7. Verify supported file formats are listed (.docx, .pdf, .xlsx)
8. Close modal

**Expected Results:**
- Upload button visible and clickable
- Modal renders with all elements
- Usage stats show tier and limits

---

### Test 2: File Upload - Word Document (.docx)
**Purpose:** Test complete flow with Word document

**Test File:** Sample recipe in .docx format

**Steps:**
1. Open upload modal
2. Select/upload .docx file
3. Verify file name and size display
4. Click "Parse Recipe" button
5. Verify processing state shows
6. Verify progress steps update
7. Wait for review modal to open

**Expected Results:**
- File uploads successfully
- Processing animation displays
- Progress steps animate through stages
- Review modal opens with parsed data

---

### Test 3: Review Parsed Recipe
**Purpose:** Verify review interface displays parsed ingredients correctly

**Steps:**
1. After successful parse, verify review modal opens
2. Check recipe name is populated
3. Check yield information is present
4. Verify ingredient list displays
5. Check each ingredient shows:
   - Parsed name
   - Quantity and unit
   - Product suggestions (if any)
   - Match confidence scores
6. Verify "needs review" indicators on unmatched ingredients

**Expected Results:**
- All parsed data displays correctly
- Ingredients show with quantities
- Product suggestions appear
- Confidence indicators visible

---

### Test 4: Product Matching
**Purpose:** Test ingredient-to-product matching UI

**Steps:**
1. In review modal, find ingredient with exact match
2. Verify it's auto-selected with green checkmark
3. Find ingredient needing review
4. Click product dropdown
5. Verify top 3 suggestions display
6. Verify confidence scores show
7. Select a product from dropdown
8. Verify selection updates

**Expected Results:**
- Exact matches auto-selected
- Dropdown shows suggestions
- Confidence scores visible
- Selection works correctly

---

### Test 5: Quick Create Product
**Purpose:** Test inline product creation during review

**Steps:**
1. In review modal, find ingredient with no matches
2. Click "Create New Product" option
3. Verify quick create form appears
4. Fill in:
   - Product name
   - Category (select from dropdown)
   - Subcategory (optional)
5. Click "Create & Select"
6. Verify product is created
7. Verify product is auto-selected for ingredient

**Expected Results:**
- Create form displays
- All fields functional
- Product creates successfully
- Auto-selects after creation

---

### Test 6: Create Recipe from Parse
**Purpose:** Complete end-to-end recipe creation flow

**Steps:**
1. In review modal, ensure all ingredients have products selected
2. Verify "Save as Draft" button is enabled
3. Edit recipe name if needed
4. Edit yield/category if needed
5. Click "Save as Draft"
6. Verify redirect to recipe editor
7. Verify recipe data is pre-filled
8. Verify all ingredients are present

**Expected Results:**
- Button enables when all matched
- Recipe creates successfully
- Redirects to editor
- All data preserved

---

### Test 7: Usage Limits - Free Tier
**Purpose:** Verify tier limits and credit protection

**Steps:**
1. Check usage stats in upload modal
2. Note current usage count
3. Upload and parse a recipe successfully
4. Check usage stats again
5. Verify count incremented
6. Verify credits_used: true in response

**Expected Results:**
- Usage count increments on success
- Stats display correctly
- Limit enforcement works

---

### Test 8: Failed Parse - Credit Protection
**Purpose:** Verify failed parses don't consume credits

**Steps:**
1. Upload invalid file (empty .txt renamed to .docx)
2. Attempt to parse
3. Verify error message displays
4. Check usage stats
5. Verify count DID NOT increment

**Expected Results:**
- Error displayed clearly
- Credits not consumed
- Usage count unchanged

---

### Test 9: Rate Limiting
**Purpose:** Verify rate limiting prevents abuse

**Test:** Upload 11 files rapidly

**Steps:**
1. Upload 10 files in quick succession
2. Attempt 11th upload
3. Verify rate limit error
4. Verify error message mentions hourly limit

**Expected Results:**
- First 10 succeed or fail gracefully
- 11th shows rate limit error
- Clear error messaging

---

### Test 10: File Validation
**Purpose:** Test file validation before AI call

**Invalid Files to Test:**
- [ ] File > 10MB
- [ ] Invalid extension (.txt, .jpg)
- [ ] Empty file
- [ ] Corrupted file

**Expected Results:**
- Each shows appropriate error
- No API call made
- Credits not consumed

---

### Test 11: Unit Normalization Display
**Purpose:** Verify unit conversion displays correctly

**Steps:**
1. Parse recipe with various units
2. In review modal, check ingredients
3. Verify both original and normalized units display
4. Examples to check:
   - 2 quarts → (64 FL OZ)
   - 5 lbs → (80 OZ)
   - 1 gallon → (128 FL OZ)

**Expected Results:**
- Original quantity/unit preserved
- Normalized unit shown in parentheses
- Conversions mathematically correct

---

### Test 12: Search All Products
**Purpose:** Test full product search when no suggestions

**Steps:**
1. Find ingredient with no suggestions
2. Click dropdown
3. Type in search field
4. Verify search results appear
5. Select product from search
6. Verify selection works

**Expected Results:**
- Search input functional
- Results filter as typed
- Selection works from search

---

### Test 13: Audit Logging
**Purpose:** Verify AI parse actions are logged

**Steps:**
1. Parse a recipe successfully
2. Navigate to Super Admin → Audit Logs
3. Filter by action type
4. Verify parse event is logged with:
   - Filename
   - Parse status
   - Ingredients count
   - User info

**Expected Results:**
- Parse events logged
- All metadata captured
- Searchable/filterable

---

### Test 14: Multi-File Type Support
**Purpose:** Test all supported file formats

**Files to Test:**
- [ ] .docx (Word document)
- [ ] .pdf (PDF document)
- [ ] .xlsx (Excel spreadsheet)

**Expected Results:**
- All formats parse successfully
- Text extracted correctly
- Recipe data structured properly

---

### Test 15: Error Recovery
**Purpose:** Test error handling and recovery

**Scenarios:**
1. Claude API timeout/error
2. Invalid recipe structure
3. Network interruption
4. No ingredients detected

**Expected Results:**
- Clear error messages
- No credits consumed on failure
- Can retry without issues
- No app crashes

---

## Manual Test Cases

### Manual Test 1: Complex Recipe Parsing
**File:** Multi-page recipe with 20+ ingredients

**Verify:**
- All ingredients extracted
- Quantities accurate
- Units normalized correctly
- Recipe name extracted
- Yield information correct

---

### Manual Test 2: Product Matching Accuracy
**Test:** Parse recipe with common ingredients

**Verify:**
- High confidence on exact matches
- Reasonable suggestions for fuzzy matches
- No false positives
- Confidence scores make sense

---

### Manual Test 3: Edge Cases
**Test various edge cases:**
- Recipe with no yield
- Recipe with fractional quantities (1/2, 1/4)
- Ingredients with special characters
- Very long ingredient names
- Ingredients with multiple prep notes

---

## Performance Testing

### Performance Test 1: Parse Speed
**Metrics to track:**
- Time from upload to review modal
- API response time
- UI responsiveness during processing

**Target:** < 15 seconds for typical recipe

---

### Performance Test 2: Large File Handling
**Test:** Upload 8-10MB file (near limit)

**Verify:**
- Uploads without timeout
- Processes successfully
- No memory issues

---

## Browser Compatibility Testing

**Browsers to test:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Features to verify on each:**
- File upload (drag-and-drop)
- Modal rendering
- Dropdown interactions
- Form submissions

---

## Accessibility Testing

**Verify:**
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Focus indicators visible
- [ ] Error messages announced
- [ ] Form labels present

---

## Security Testing

**Verify:**
- [ ] File type validation enforced
- [ ] Size limits enforced
- [ ] Only authenticated users can upload
- [ ] Only Chef/Admin roles can access
- [ ] Outlet scoping enforced
- [ ] Rate limiting works
- [ ] Usage limits enforced per organization

---

## Test Data Requirements

**Sample Files Needed:**
1. Valid recipe .docx (simple - 5-8 ingredients)
2. Valid recipe .pdf (medium - 10-15 ingredients)
3. Valid recipe .xlsx (spreadsheet format)
4. Complex recipe .docx (20+ ingredients)
5. Invalid file (corrupted)
6. Invalid file (wrong format)
7. Large file (near 10MB limit)

---

## Success Criteria

**Feature is considered successful if:**
- ✅ 90%+ of test cases pass
- ✅ All critical paths work (upload → parse → review → create)
- ✅ Credit protection works (failed parses don't consume)
- ✅ No data loss or corruption
- ✅ Error handling is clear and helpful
- ✅ Performance meets targets (<15s parse time)
- ✅ No security vulnerabilities
- ✅ Audit logging complete

---

## Known Limitations (Not Tested Yet)

- OCR for scanned PDFs (future phase)
- Batch import (future phase)
- Recipe method/steps extraction (future phase)
- Advanced allergen detection (future phase)

---

**Testing Execution Date:** _TBD after deployment_

**Tester:** Claude Code with Playwright MCP

**Environment:** Dev (food-cost-tracker-dev.onrender.com)
