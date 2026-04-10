# EHC Checklist Forms & Template System — Planning Document

> **Project:** RestauranTek  
> **Module:** EHC → Digital Forms (extension)  
> **Date:** April 9, 2026  
> **Stack:** FastAPI + React + PostgreSQL (Render prod / Unraid dev), Alembic migrations  
> **Repo:** `github.com/CxRxExAxM/food-cost-tracker`

---

## 1. Problem

The EHC module currently supports `table_signoff` forms — a pattern where all outlets appear as rows on a single sheet, each person fills in a few fields and signs. This works for simple records like the Thermometer Register (Record 13/DB ID 5).

Record 20 (Kitchen Audit Checklist, DB ID 9) is a 58-question Y/N walk-through with a corrective actions section and signature. It cannot fit the `table_signoff` pattern because:

- Each outlet needs to answer 58 questions (not fill in one row)
- "N" answers require corrective action documentation (what, when, who)
- Each outlet's completed checklist is a standalone document for audit evidence
- It runs monthly — each month needs its own set of forms per outlet

This is also the first record that would benefit from a **form template system** — a reusable definition that can stamp out per-outlet form instances. The Forms Brain Dump in Notion identifies several other records that will need similar treatment (Record 8 Internal Audit, Record 23 Training Records, SCP 40 Draft Line Cleaning).

---

## 2. Solution: `checklist_form` Type + Template System

### 2.1 New Form Type: `checklist_form`

A form where the user answers a list of questions (Y/N, or future: multi-choice, numeric), documents corrective actions for failed items, and signs.

**User flow (chef scanning QR at an outlet):**
1. Scan QR code → opens public form page (token-based, no auth — same as `table_signoff`)
2. Form renders: outlet name at top, 58 Y/N questions in a scrollable list
3. User taps Y or N for each question
4. Any "N" answer expands an inline corrective action block:
   - Action required (text)
   - When by (date)
   - Who by (text)
5. Scroll-to-sign at bottom
6. Submit → response saved, linked submission auto-updates to completed

**Key difference from `table_signoff`:** Each form instance IS one outlet's checklist. There is no outlet selector — the QR code is outlet-specific.

### 2.2 Template System

Templates are reusable form definitions stored in the database. An admin creates a form "from template" rather than configuring from scratch.

**Template definition stores:**
- Template name (e.g., "Kitchen Audit Checklist")
- Form type (`checklist_form`)
- Linked EHC record (DB ID 9 / Record 20)
- Checklist items: ordered list of questions with response type
- Intro text (instructions shown at top)
- Whether corrective actions section is included
- Signature requirement

**"Create from Template" flow:**
1. Admin clicks "Create from Template" button (next to existing "Create New Form")
2. Modal shows available templates (initially just one: Kitchen Audit Checklist)
3. Admin selects template
4. Admin picks which outlets get forms (pill/chip selector from configured EHC outlets)
5. Admin sets the period label (e.g., "April 2026")
6. System generates one `ehc_form_link` per selected outlet, each with:
   - Its own token and QR code
   - The checklist items copied from the template config
   - Pre-linked to the correct EHC record submission for that outlet/period
7. Forms appear in the Forms tab, grouped by template + period

---

## 3. Database Changes

### 3.1 New Table: `ehc_form_template`

Stores reusable form definitions. Initially seeded with Record 20's 58 questions.

```sql
CREATE TABLE ehc_form_template (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,           -- "Kitchen Audit Checklist"
    form_type VARCHAR(50) NOT NULL,       -- 'checklist_form'
    ehc_record_id UUID REFERENCES ehc_record(id),  -- links to Record 20 (DB ID 9)
    config JSONB NOT NULL,                -- checklist items, settings (see below)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**`config` JSON structure:**

```json
{
  "intro_text": "This checklist is developed to provide an internal audit tool for hygiene champions. Walk through each item and mark Y or N.",
  "items": [
    {
      "number": 1,
      "question": "Are all floors, walls and ceiling surfaces clean?",
      "response_type": "yes_no"
    },
    {
      "number": 2,
      "question": "Are food contact surfaces such as meat slicers, can openers, food mixers, hand whisks clean?",
      "response_type": "yes_no"
    }
    // ... all 58 questions
  ],
  "corrective_actions": true,
  "signature_required": true
}
```

### 3.2 Extend `ehc_form_link`

Add columns to support the new form type and template linkage:

```sql
ALTER TABLE ehc_form_link ADD COLUMN form_type VARCHAR(50) DEFAULT 'table_signoff';
ALTER TABLE ehc_form_link ADD COLUMN template_id UUID REFERENCES ehc_form_template(id);
ALTER TABLE ehc_form_link ADD COLUMN outlet_name VARCHAR(255);
ALTER TABLE ehc_form_link ADD COLUMN period_label VARCHAR(100);  -- "April 2026"
```

**Why `outlet_name` as a string:** Matches the existing freeform outlet approach used elsewhere in EHC (per the planning doc decision). Can add FK to outlets table later.

**Existing `config` column** on `ehc_form_link` will store the checklist items for this specific instance (copied from template at creation time, so template changes don't retroactively alter existing forms).

### 3.3 Extend `ehc_form_response`

The existing `response_data` JSONB column already supports arbitrary data. For `checklist_form`, the response data structure will be:

```json
{
  "answers": {
    "1": { "answer": "Y" },
    "2": { "answer": "N", "action": "Deep clean slicers", "when_by": "2026-04-15", "who_by": "Juan" },
    "3": { "answer": "Y" }
    // ... all 58
  },
  "completed_at": "2026-04-10T14:30:00Z",
  "outlet_name": "Toro"
}
```

No schema change needed — `response_data` is already JSONB.

### 3.4 Add `ref_code` to `ehc_record`

Resolve the DB ID vs EHC record number mismatch:

```sql
ALTER TABLE ehc_record ADD COLUMN ref_code VARCHAR(20);
```

Then populate: DB ID 1 → ref_code "3" (Food Storage Temp), DB ID 9 → ref_code "20" (Kitchen Audit), etc. This is a data migration based on the mapping from the uploaded screenshot.

---

## 4. API Endpoints

### 4.1 Template Endpoints (Admin, authenticated)

```
GET    /api/ehc/templates                    -- List templates for org
POST   /api/ehc/templates                    -- Create template
GET    /api/ehc/templates/{id}               -- Get template detail
PUT    /api/ehc/templates/{id}               -- Update template
DELETE /api/ehc/templates/{id}               -- Soft delete template
```

### 4.2 "Create from Template" Endpoint (Admin)

```
POST   /api/ehc/templates/{id}/deploy
```

**Request body:**
```json
{
  "outlets": ["Main Kitchen", "Toro", "La Hacienda", "Bourbon Steak"],
  "period_label": "April 2026",
  "record_id": "uuid-of-record-20"
}
```

**What it does:**
1. For each outlet in the list:
   - Creates an `ehc_form_link` with `form_type='checklist_form'`, config copied from template
   - Generates token and QR code (existing `qr_generator.py`)
   - Sets `outlet_name` and `period_label`
   - If `record_id` provided, creates or links to the corresponding `ehc_record_submission` for that outlet/period
2. Returns the list of created form links

### 4.3 Public Checklist Form Endpoints (No auth, token-based)

```
GET    /api/ehc/forms/{token}                -- Existing endpoint, extended
POST   /api/ehc/forms/{token}/respond        -- Existing endpoint, extended
```

The existing public endpoints already handle token lookup and response submission. They need to be extended to:
- Return `form_type` so the frontend knows which component to render
- Accept the checklist response data structure
- Validate that all questions are answered before accepting submission

### 4.4 PDF Export

```
GET    /api/ehc/forms/{token}/export-pdf     -- Generate completed checklist PDF
```

Generates a formatted PDF of the completed checklist showing all 58 questions, answers, corrective actions, and signature. Simple formatted output (not overlaid on the Fairmont template — that's a future enhancement).

---

## 5. Frontend Components

### 5.1 Public Form Page

**Existing:** `frontend/src/pages/EHC/forms/TableSignoffForm.jsx`

**New:** `frontend/src/pages/EHC/forms/ChecklistForm.jsx`

The public form page (`/forms/{token}`) already exists and loads form data by token. It currently renders `TableSignoffForm` for `table_signoff` type. Add a router:

```jsx
// In the public form page component
if (formData.form_type === 'checklist_form') {
  return <ChecklistForm data={formData} token={token} />;
}
return <TableSignoffForm data={formData} token={token} />;
```

**ChecklistForm.jsx responsibilities:**
- Display outlet name and period at top
- Render intro text
- Render 58 questions as a scrollable list with Y/N toggle buttons
- Expand corrective action fields inline when "N" is tapped
- Progress indicator (e.g., "32/58 answered")
- Scroll-to-sign gate at bottom (reuse existing signature canvas component)
- Submit handler that posts response data

**Mobile-first design:** This will primarily be used on a phone/tablet while walking a kitchen. Large tap targets for Y/N, clear visual distinction between answered and unanswered, sticky progress bar.

### 5.2 Template Selection Modal

**New:** `frontend/src/pages/EHC/modals/CreateFromTemplateModal.jsx`

Triggered by "Create from Template" button in Forms tab.

**Steps:**
1. Select template (list of available templates — initially just one)
2. Select outlets (pill/chip selector — type to search, click to add)
3. Set period label (text input, e.g., "April 2026")
4. Review and confirm
5. System creates forms, shows success with QR codes

### 5.3 Forms Tab Updates

**Existing:** `frontend/src/pages/EHC/tabs/Forms.jsx`

Add:
- "Create from Template" button next to "Create New Form"
- Grouping/filtering by template + period (so all "Kitchen Audit - April 2026" forms are visually grouped)
- Status badges showing per-outlet completion
- Bulk QR flyer generation for a group of forms

### 5.4 Template Management (Settings Tab — Future)

Template CRUD UI will live in the Settings tab when that's built. For Phase 1, the Kitchen Audit template is seeded via migration and not editable from the UI.

---

## 6. Seed Data

### 6.1 Record 20 Template

Create an Alembic migration or seed script that:

1. Adds `ref_code` column to `ehc_record` and populates the mapping
2. Creates the `ehc_form_template` table
3. Seeds the Kitchen Audit Checklist template with all 58 questions:

```python
KITCHEN_AUDIT_ITEMS = [
    {"number": 1, "question": "Are all floors, walls and ceiling surfaces clean?", "response_type": "yes_no"},
    {"number": 2, "question": "Are food contact surfaces such as meat slicers, can openers, food mixers, hand whisks clean?", "response_type": "yes_no"},
    {"number": 3, "question": "Are door seals to all coolrooms, refrigeration units and freezer units clean?", "response_type": "yes_no"},
    {"number": 4, "question": "Is there a sanitiser solution available? Is it the correct strength?", "response_type": "yes_no"},
    {"number": 5, "question": "Are all chemicals correctly labelled?", "response_type": "yes_no"},
    {"number": 6, "question": "Are cleaning cloths in good condition and clean?", "response_type": "yes_no"},
    {"number": 7, "question": "Are all cleaning equipment stored correctly?", "response_type": "yes_no"},
    {"number": 8, "question": "Does the dishwasher achieve 55°C / 131°F for wash cycle and 82°C / 179.6°F for rinse cycle?", "response_type": "yes_no"},
    {"number": 9, "question": "Are staff wearing clean clothing?", "response_type": "yes_no"},
    {"number": 10, "question": "Are staff wearing protective head covering, including stewarding staff?", "response_type": "yes_no"},
    {"number": 11, "question": "Are staff wearing and using gloves correctly?", "response_type": "yes_no"},
    {"number": 12, "question": "Are there blue band aids available for use by staff in the kitchen?", "response_type": "yes_no"},
    {"number": 13, "question": "Have staff covered all cuts and wounds?", "response_type": "yes_no"},
    {"number": 14, "question": "Is there a wash hand basin in the kitchen?", "response_type": "yes_no"},
    {"number": 15, "question": "Does the wash hand basin have hot water to 38°C / 100.4°F within 30 seconds, soap and paper towels to dry hands?", "response_type": "yes_no"},
    {"number": 16, "question": "Are wash hand basins only being used for hand washing?", "response_type": "yes_no"},
    {"number": 17, "question": "Does the wash hand basin have direct access with nothing blocking regular use?", "response_type": "yes_no"},
    {"number": 18, "question": "Is there a waste bin for staff to use in the kitchen?", "response_type": "yes_no"},
    {"number": 19, "question": "Is there a lid for the bin when the kitchen is not in use?", "response_type": "yes_no"},
    {"number": 20, "question": "Are all coolrooms and refrigeration units operating at 5°C / 41°F or below?", "response_type": "yes_no"},
    {"number": 21, "question": "Are all freezer units operating at -18°C / 0°F or below?", "response_type": "yes_no"},
    {"number": 22, "question": "Are all foods covered?", "response_type": "yes_no"},
    {"number": 23, "question": "Are staff only using plastic, stainless steel or aluminium foil to cover foods?", "response_type": "yes_no"},
    {"number": 24, "question": "Are all foods labelled?", "response_type": "yes_no"},
    {"number": 25, "question": "Are all foods date coded?", "response_type": "yes_no"},
    {"number": 26, "question": "Are all foods stored within the area in date?", "response_type": "yes_no"},
    {"number": 27, "question": "Are all raw foods stored separate or below cooked foods or ready to eat foods?", "response_type": "yes_no"},
    {"number": 28, "question": "Are fruits and salad items being chlorinated at 100ppm (5 minute contact time) or if Acid wash is pH3 or below (1 minute contact time)?", "response_type": "yes_no"},
    {"number": 29, "question": "Are all ceilings, walls and floors in good structural condition with no holes, damage or disrepair?", "response_type": "yes_no"},
    {"number": 30, "question": "Are all the lights diffused (covered)?", "response_type": "yes_no"},
    {"number": 31, "question": "Is all food contact equipment in good condition?", "response_type": "yes_no"},
    {"number": 32, "question": "Are door seals to all coolrooms, refrigeration units and freezer units in good condition and not damaged?", "response_type": "yes_no"},
    {"number": 33, "question": "Have all wooden equipment been removed from the kitchen?", "response_type": "yes_no"},
    {"number": 34, "question": "Have all unnecessary glass been removed from the kitchen?", "response_type": "yes_no"},
    {"number": 35, "question": "Are there any obvious signs of pest activity?", "response_type": "yes_no"},
    {"number": 36, "question": "Is there a designated cooling of food location?", "response_type": "yes_no"},
    {"number": 37, "question": "Are staff cooling foods correctly?", "response_type": "yes_no"},
    {"number": 38, "question": "Are colour coded boards being used?", "response_type": "yes_no"},
    {"number": 39, "question": "Are staff using the correct colours for the foods in relation to the colour coded boards?", "response_type": "yes_no"},
    {"number": 40, "question": "Is there a cutting board rack?", "response_type": "yes_no"},
    {"number": 41, "question": "Are there sterilising wipes for the cleaning of the thermometers used within the kitchen?", "response_type": "yes_no"},
    {"number": 42, "question": "Is there at least 1 operating probe thermometer for staff to use within the kitchen?", "response_type": "yes_no"},
    {"number": 43, "question": "Are there cooking/reheating temperature records?", "response_type": "yes_no"},
    {"number": 44, "question": "Are there cooling temperature records?", "response_type": "yes_no"},
    {"number": 45, "question": "Are there calibration records for the thermometers used within the kitchen?", "response_type": "yes_no"},
    {"number": 46, "question": "Are there temperature records for coolrooms, refrigeration units and freezer units?", "response_type": "yes_no"},
    {"number": 47, "question": "Is there a cleaning schedule for this area including every fixture and fitting?", "response_type": "yes_no"},
    {"number": 48, "question": "Do all records appear to be completed correctly - with black/blue pen, temperatures measured to the decimal point and not made up?", "response_type": "yes_no"},
    {"number": 49, "question": "Have the staff been trained in food safety within the last 12 months?", "response_type": "yes_no"},
    {"number": 50, "question": "Have all staff completed Record 11?", "response_type": "yes_no"},
    {"number": 51, "question": "Is the dishwasher / glass washer temperature record completed daily?", "response_type": "yes_no"},
    {"number": 52, "question": "Has the bar got sterilising gel?", "response_type": "yes_no"},
    {"number": 53, "question": "Does the bar have a green cutting board for garnishes?", "response_type": "yes_no"},
    {"number": 54, "question": "Are raw eggs an ingredient for any cocktails?", "response_type": "yes_no"},
    {"number": 55, "question": "Is the milk and other dairy products being stored at the correct temperature?", "response_type": "yes_no"},
    {"number": 56, "question": "Are all bar snacks stored correctly with labelling & dating?", "response_type": "yes_no"},
    {"number": 57, "question": "Are straws individually wrapped or otherwise protected?", "response_type": "yes_no"},
    {"number": 58, "question": "Are glasses clean and polished?", "response_type": "yes_no"},
]
```

### 6.2 ref_code Mapping

Based on the uploaded screenshot (DB ID → EHC Record Number):

```python
REF_CODE_MAP = {
    1: "3",      # Food Storage Temperature
    2: "4",      # Cooking/Reheating Temperature
    3: "5",      # Cooling of Food
    4: "6",      # Food Display Temperature
    5: "7",      # Thermometer Calibration
    6: "12",     # Defrosting Record
    7: "13",     # Dishwasher/Glasswasher Temperature
    8: "17",     # Cleaning Schedule
    9: "20",     # Kitchen Audit Checklist  <-- THIS RECORD
    10: "21",    # Food Washing Record
    11: "24",    # Allergen Matrix
    12: "27",    # pH Testing Record
    13: "28",    # Thermometer Register
    14: "14",    # Non Conformance Record
    15: "SCP40", # Draft Line Cleaning
    16: "37",    # Food Sample Log (14 Day)
    17: "1",     # Checklist to Visit Suppliers
    18: "1a",    # Approved Supplier List
    19: "2",     # Food Delivery Record
    20: "8",     # Internal Food Safety Audit
    21: "9",     # Food Poisoning Allegation
    22: "11",    # Staff Food Safety Declaration
    23: "14",    # Foreign Matter Record  (NOTE: check if duplicate with ID 14)
    24: "15",    # Pesticide Usage Record
    25: "16",    # Pesticide Approved List
    26: "18",    # Food Poisoning/Foreign Object Letter
    27: "19",    # Outdoor Catering Temperature Record
    28: "23",    # Training Records
    29: "25",    # Ice Machine Cleaning
    30: "29",    # Internal Swabbing Record
    31: "30",    # Guest-Supplied Food Indemnity
    32: "30b",   # Baby Milk Reheating Indemnity
    33: "32",    # Maintenance Defect Record
    34: "33",    # Pest Sighting Record
    35: "34",    # Review Record
    36: "35",    # Food Safety Team Record
    37: "36",    # Food Donation Waiver
    38: "SCP38", # Notice Board Documents
    39: "SCP39", # Dish Machine 3rd Party PM
    40: "SCP41", # MSDS/SDS Link
    41: "SCP42", # Pest Control License/Contract
    42: "SCP43", # Pest Control Insurance
    43: "SCP44", # Pest Control Bait Map
    44: "SCP45", # Water Testing Records
    45: "SCP46", # Microbial Lab Test Results
}
```

**NOTE:** Mike should verify this mapping — the DB IDs were renumbered sequentially and some records were removed from the original EHC numbering (10, 22, 26, 31). Cross-reference with the EHC Standards Manual for accuracy.

---

## 7. Phased Build

### Phase 1: Foundation (Backend)
- [ ] Alembic migration: `ehc_form_template` table
- [ ] Alembic migration: Add `form_type`, `template_id`, `outlet_name`, `period_label` to `ehc_form_link`
- [ ] Alembic migration: Add `ref_code` to `ehc_record`, populate mapping
- [ ] Template CRUD endpoints
- [ ] Seed Kitchen Audit Checklist template for fairmont-scp org
- [ ] Deploy endpoint (`POST /api/ehc/templates/{id}/deploy`)
- [ ] Extend public form GET to return `form_type`
- [ ] Extend public form POST to accept checklist response data
- [ ] Checklist response validation (all questions answered)

### Phase 2: Public Checklist Form (Frontend)
- [ ] `ChecklistForm.jsx` — mobile-first Y/N checklist UI
- [ ] Inline corrective action expansion on "N" answer
- [ ] Progress indicator
- [ ] Reuse existing scroll-to-sign and signature canvas
- [ ] Form type router on public form page
- [ ] Test on phone/tablet for kitchen walkability

### Phase 3: Admin UI (Frontend)
- [ ] "Create from Template" button in Forms tab
- [ ] `CreateFromTemplateModal.jsx` — template select, outlet picker, period label
- [ ] Forms tab grouping by template + period
- [ ] Per-outlet completion badges
- [ ] Response viewer for checklist forms (similar to existing ResponseTrackerModal but showing Q&A + actions)

### Phase 4: PDF Export
- [ ] PDF generation endpoint for completed checklists
- [ ] Clean formatted output: header, questions with Y/N, corrective actions table, signature
- [ ] Download button in response viewer

### Phase 5: Template Management UI (Later — with Settings Tab)
- [ ] Template list view
- [ ] Template editor (add/edit/reorder questions)
- [ ] "Save as Template" from existing form

---

## 8. Design Decisions

1. **One QR per outlet (Option B):** Each outlet gets its own form instance with unique QR. No outlet selector on the form. Chef scans → immediately in their checklist. Scales to future templates.

2. **Config copied at creation, not referenced:** When forms are created from a template, the checklist items are copied into the form's config. This means template updates don't retroactively change existing forms. Same pattern as `table_signoff` where config is self-contained.

3. **Template in DB, not JSON file:** Stored in `ehc_form_template` table so it's org-scoped, editable via future UI, and follows existing multi-tenant patterns. Seeded via migration for Phase 1.

4. **No outlet list pre-loading:** Admin manually selects which outlets get forms each month via the deploy modal. No automatic "generate for all outlets" — keeps it flexible for months where not all outlets need auditing.

5. **`ref_code` as separate column:** Human-facing EHC record numbers (1, 1a, 20, SCP38, etc.) stored in `ref_code` column on `ehc_record`, separate from the UUID primary key. Resolves the DB ID confusion in CLI workflows.

6. **Corrective actions inline, not separate:** Actions are stored inside the response JSON, not as separate records. Keeps the data self-contained per checklist submission. If cross-checklist action tracking is needed later, a separate `ehc_corrective_action` table can be added.

7. **PDF export is simple format first:** Plain formatted PDF with questions, answers, and actions. Overlaying on the original Fairmont Record 20 template is deferred — it requires precise coordinate mapping and is a separate effort.

---

## 9. Files to Create/Modify

### Backend (New)
- `alembic/versions/XXX_add_form_templates.py` — migration
- `api/app/routers/ehc_templates.py` — template CRUD + deploy endpoint (or extend `ehc_forms.py`)

### Backend (Modify)
- `api/app/routers/ehc_forms.py` — extend public endpoints for checklist_form type
- `api/app/routers/ehc.py` — add ref_code to record serialization

### Frontend (New)
- `frontend/src/pages/EHC/forms/ChecklistForm.jsx` — public checklist form
- `frontend/src/pages/EHC/modals/CreateFromTemplateModal.jsx` — template deploy modal

### Frontend (Modify)
- `frontend/src/pages/EHC/forms/` — form type router (render ChecklistForm vs TableSignoffForm)
- `frontend/src/pages/EHC/tabs/Forms.jsx` — "Create from Template" button, grouping, completion badges

---

## 10. Open Questions

1. **ref_code mapping accuracy:** The mapping in Section 6.2 was derived from the screenshot. Mike should verify each row matches the correct EHC standard record number.

2. **Question 35 polarity:** "Are there any obvious signs of pest activity?" — a "Y" here is bad, unlike every other question where "Y" is good. Should this be flagged differently in the UI, or is the chef expected to understand?

3. **Corrective action follow-up:** Currently actions are captured but not tracked to completion. Is a simple "completed on" date field sufficient, or does this need to link to ALICE work orders eventually?

4. **Bar questions visibility:** Questions 52-58 are bar-specific. Decision was to show all 58 to everyone. Confirmed by Mike.

5. **Monthly cadence:** Mike creates forms per month manually (duplicate/create from template). No automated scheduling needed for Phase 1.
