# EHC Module — Forms & Restructure Plan (Combined)

> **Project:** RestauranTek  
> **Module:** EHC Digital Forms, UI Restructure, Settings  
> **Date:** April 2, 2026  
> **Property:** Fairmont Scottsdale Princess (fairmont-scp)  
> **Stack:** FastAPI + React, PostgreSQL (Render prod / Unraid dev), Alembic migrations  
> **Status:** Phase 1–3 of Digital Forms complete (Record 11 QR→sign→track working end-to-end)

---

## 1. What This Plan Covers

This is a combined plan for three interconnected features:

1. **Digital Forms expansion** — extending beyond Record 11 to cover team rosters (Record 35), monthly checklists (Record 20), training attendance (Record 23), and other form-eligible records
2. **UI restructure** — adding Forms and Settings tabs to the EHC module (3 tabs → 5 tabs)
3. **Settings infrastructure** — outlet management, responsibility codes, and module configuration

These are unified because they share data models, inform each other's UX, and should be built in a coordinated sequence.

### Architecture Decision: Hybrid Model

**Forms tab = admin workbench** (creation, distribution, campaign management)  
**Records tab = operational source of truth** (completion tracking, approval, dashboard cascade)

The Forms tab is where Mike (admin) creates form links, batch-generates QR codes, configures team rosters, pastes training agendas, and monitors response campaigns. The culinary manager and area leaders never need to touch it — they stay in Records, where form-linked submissions show an indicator that digital collection is active and eventually receive an auto-attached PDF.

No redundant tracking. Each tab has one job:
- **Forms:** "I need to create, distribute, or manage a form collection campaign"
- **Records:** "I need to check what's complete, approve submissions, see what's missing"
- **Settings:** "I need to update outlet info, leader contacts, or module config"

---

## 2. Current State (What's Already Built)

### Working (Phase 1–3 of original Digital Forms plan)
- `ehc_form_link` and `ehc_form_response` tables in PostgreSQL
- Public endpoints: `GET /api/ehc/forms/{token}`, `POST /api/ehc/forms/{token}/respond`
- Admin endpoints: create form link, list form links, list responses
- Token generation, validation, duplicate detection
- QR code generation
- Public form UI at `/form/:token` (outside auth wrapper)
- Signature pad component (HTML5 Canvas, mobile-first)
- `staff_declaration` form renderer with scroll-to-sign (Record 11)
- Success/error/expired states
- Form link management in existing EHC UI

### Not Yet Built
- Record 35 (team_roster) form type
- Record 20/23 and other form types
- PDF generation (ReportLab)
- Flyer PDF with QR
- Forms tab (dedicated management hub)
- Settings tab
- `ehc_outlet` table
- Batch form link generation
- Records tab integration (form link indicators)

---

## 3. Tab Structure

```
EHC Module
├── Dashboard       (unchanged — overview stats, readiness rings, section progress)
├── Audit Points    (unchanged — 125 points, status tracking, Auto/Obs split)
├── Records         (enhanced — form link indicators on submissions)
├── Forms           (NEW — admin workbench for digital form management)
└── Settings        (NEW — outlet config, responsibility codes, module settings)
```

### Data Flow

```
Settings (outlets, leader contacts, responsibility codes)
    ↓ configures
Forms (create links, distribute QR, track responses)
    ↓ generates PDFs, attaches to
Records (evidence submissions, approval workflow)
    ↓ status feeds
Audit Points (point-level completion)
    ↓ aggregates to
Dashboard (overall readiness %)
```

---

## 4. Form Types

### 4.1 `staff_declaration` (Record 11) — WORKING

Mass sign-off against a static document. 50–100 staff read the 23-point declaration, scroll to bottom, acknowledge, sign.

- Document content: static template file (`templates/record_11.js`), not config JSON
- Config: `{ document_ref, property_name, cycle_year }`
- Scroll-to-sign gate: signature section disabled until user scrolls through full document
- Response data: `{ acknowledged: true, scrolled_to_bottom: true }`
- PDF output: summary table format (Name | Date | Signature for all respondents)

### 4.2 `team_roster` (Record 35) — NEXT TO BUILD

Small team signature roster (5–8 people). Admin pre-configures team members with name, position, department, date approved.

- Config includes `team_members` array with pre-filled details
- Each person opens the same link, finds their row, signs inline
- PDF output: matches original Record 35 template (Date Approved | Name | Position | Department | Signature)

### 4.3 `training_attendance` (Record 23) — FUTURE

Per-session training attendance with dynamic agenda content.

- Admin types/pastes agenda text into config when creating the form link
- Sets session date, topic title, expected attendees (optional count)
- Form displays agenda as scrollable document content (same scroll-to-sign pattern as Record 11, but content comes from config, not static template)
- Staff sign to confirm attendance
- Session history visible in Forms tab: each session shows agenda summary, date, attendance count
- PDF output: attendance summary with agenda header

### 4.4 `checklist` (Record 20, 7, 25, SCP 40) — FUTURE

Monthly area checklists filled by outlet leaders.

- Config includes `sections` array with field definitions (checkbox, text, textarea, select)
- Fields support corrective action areas (textarea shown conditionally when a check fails)
- One form link per outlet per period (see §5.2)
- Area leader scans their kitchen's specific QR, fills checklist
- PDF output: completed checklist matching the record format

### 4.5 Form Types NOT in Scope

These records are better handled by other mechanisms:

| Record | Why Not a Form |
|--------|---------------|
| 3/4/5/6/12/27/37 (Daily walkthrough) | Thousands of data points — this is the HACCP/digital capture module, not forms |
| 13 (Dishwasher log) | Running daily log, same as above |
| 24 (Allergen matrix) | Depends on recipe/menu module completion |
| 32, 33 (Maintenance/pest) | Alice export — potential Actabl API integration |
| 29 (Internal swabbing) | Mike fills this himself, simple submission |

---

## 5. Key Design Decisions

### 5.1 Form Link ↔ Record Submission Relationship

Each form link ties to a specific record submission in the Records tab. When the form collection completes:

1. PDF auto-generates from responses
2. PDF attaches to the submission (`file_path`, `original_filename`)
3. Submission status advances to `submitted`
4. Admin still manually approves (reviews PDF, verifies quality)
5. Approval triggers existing cascade: submission → audit point → section → dashboard

This preserves the existing approval workflow. No auto-approval.

### 5.2 Recurring Checklists: One Link Per Outlet Per Period

For monthly records (Record 20, 7, etc.), each outlet gets its own form link per period. Batch generation: "Create April 2026 walkthrough links" produces one link per assigned outlet.

**Why per-outlet links (not a shared link with outlet selector):**
- Maps 1:1 to existing submission structure (each outlet-month is already a separate submission row)
- No room for leader to pick wrong outlet
- Each outlet can have a standing QR posted in the kitchen (future optimization)
- Form already knows the context — no selection step for the leader

**Batch generation workflow:**
1. Admin goes to Forms tab → "Create Monthly Checklist Links"
2. Selects record type (e.g., Record 20), month, and year
3. System reads outlet assignments from `ehc_record_outlet` (or `ehc_outlet` once built)
4. Generates one form link per outlet, tied to corresponding submission
5. Admin downloads QR codes (batch ZIP or individual) or copies links for distribution

### 5.3 Static Templates vs Config Content

Two patterns for form document content:

**Static template** (Record 11): Content that doesn't change between sessions. Lives as a versioned file in both frontend and backend. Config references it by `document_ref`.

**Config content** (Record 23 training): Content that changes per session (agenda text). Stored in `ehc_form_link.config` JSON. Form renderer falls back to config content when no static template reference exists.

Checklist field definitions (Record 20) are a third pattern — structural config that defines the form shape, not document content. Also stored in config JSON.

### 5.4 Records Tab Enhancement (Bridge Between Tabs)

The Records tab gets a lightweight enhancement — NOT a parallel tracking system:

- Submissions with an active form link show a small **QR icon** or **response badge** (e.g., "45/95") in the row
- Clicking the indicator opens a **quick popover** with: response count, completion %, link to Forms tab for full management
- When a form link's PDF is auto-attached, the file column updates and the submission can be approved normally
- No form creation, distribution, or response management in Records — that all lives in Forms

This means the culinary manager sees "Record 11: 45/95 responses" directly in her Records view without needing to know the Forms tab exists. When it hits 95/95 and the PDF appears, she approves it just like any other submission.

---

## 6. Forms Tab — UI Design

### 6.1 Layout: Grouped by Record Type

The Forms tab organizes form links by their parent record, matching the mental model from the Records tab. Each record type is an expandable card showing aggregate stats, with individual form links nested inside.

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Forms                                                    [+ New Form]  │
├─────────────────────────────────────────────────────────────────────────┤
│ Filter: [All Records ▼] [EHC 2026 ▼] [Active ▼]                       │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📋 Record 11 — Staff Food Safety Declaration                       │ │
│ │ staff_declaration • EHC 2026 • 1 active link                       │ │
│ │                                                                     │ │
│ │  ┌───────────────────────────────────────────────────────────────┐  │ │
│ │  │ Food Safety Declaration 2026         67/95 (71%) ██████░░░░  │  │ │
│ │  │ Created Mar 15 • Active • Expires: None                      │  │ │
│ │  │ [Copy Link] [QR ↓] [Flyer ↓] [Responses] [Deactivate]      │  │ │
│ │  └───────────────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📋 Record 35 — Food Safety Team Record                             │ │
│ │ team_roster • EHC 2026 • 1 active link                             │ │
│ │                                                                     │ │
│ │  ┌───────────────────────────────────────────────────────────────┐  │ │
│ │  │ Food Safety Team 2026                5/5 (100%) ██████████   │  │ │
│ │  │ Created Mar 20 • Complete • PDF Generated                    │  │ │
│ │  │ [Copy Link] [QR ↓] [Responses] [View PDF]                   │  │ │
│ │  └───────────────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📋 Record 23 — Training Records                                    │ │
│ │ training_attendance • EHC 2026 • 3 sessions                        │ │
│ │                                                                     │ │
│ │  ┌───────────────────────────────────────────────────────────────┐  │ │
│ │  │ March Safety Meeting — Knife Safety    28/32 (88%) ████████░ │  │ │
│ │  │ Session: Mar 10, 2026 • Active                               │  │ │
│ │  │ [Copy Link] [QR ↓] [Responses] [Deactivate]                 │  │ │
│ │  ├───────────────────────────────────────────────────────────────┤  │ │
│ │  │ February Safety Meeting — Fire Ext.    32/32 (100%) █████████│  │ │
│ │  │ Session: Feb 12, 2026 • Complete • PDF Generated             │  │ │
│ │  │ [Responses] [View PDF]                                       │  │ │
│ │  ├───────────────────────────────────────────────────────────────┤  │ │
│ │  │ January Safety Meeting — HACCP Basics  30/32 (94%) █████████░│  │ │
│ │  │ Session: Jan 8, 2026 • Complete • PDF Generated              │  │ │
│ │  │ [Responses] [View PDF]                                       │  │ │
│ │  └───────────────────────────────────────────────────────────────┘  │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ 📋 Record 20 — Kitchen Audit Checklist                  ▶ expand   │ │
│ │ checklist • EHC 2026 • April: 2/8 outlets complete                 │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Record 20 Expanded — Month × Outlet Grid

When a recurring checklist record is expanded, it shows a month-by-outlet grid:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 📋 Record 20 — Kitchen Audit Checklist                             │
│ checklist • EHC 2026 • 8 outlets assigned                          │
│                                                          [+ Month] │
│                                                                     │
│ April 2026                                          2/8 complete    │
│ ┌──────────────┬────────────┬──────────────────────────────────────┐│
│ │ MK           │ ██████████ │ Complete 04/02  [QR] [Responses]    ││
│ │ Casual       │ ██████████ │ Complete 04/01  [QR] [Responses]    ││
│ │ Toro         │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ │ LaHa         │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ │ BSAZ         │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ │ Dish         │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ │ GM           │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ │ Pastry       │ ░░░░░░░░░░ │ Not started     [QR] [Copy Link]   ││
│ └──────────────┴────────────┴──────────────────────────────────────┘│
│                                                                     │
│ ▶ March 2026                                        8/8 complete   │
│ ▶ February 2026                                     8/8 complete   │
│ ▶ January 2026                                      8/8 complete   │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 "New Form" Creation Flow

The [+ New Form] button opens a creation wizard:

**Step 1: Select form type**
- Staff Declaration (Record 11)
- Team Roster (Record 35)
- Training Attendance (Record 23)
- Monthly Checklist (Record 20, 7, 25, SCP 40)

**Step 2: Configure (varies by type)**

*Staff Declaration:*
- Select audit cycle
- Set expected response count
- Optional: expiry date
- Document template auto-selected

*Team Roster:*
- Select audit cycle
- Add team members (name, position, department, date approved)
- Table editor with add/remove rows

*Training Attendance:*
- Session title (e.g., "Knife Safety Refresher")
- Session date
- Agenda text area (paste/type the agenda content)
- Expected attendance count (optional)

*Monthly Checklist:*
- Select record type (Record 20, 7, etc.)
- Select month/year
- Outlets auto-populated from `ehc_outlet` (or `ehc_record_outlet`)
- Batch generates one link per outlet
- Option to download all QR codes as ZIP

**Step 3: Review & Generate**
- Preview the form link details
- Generate token(s)
- Show QR code(s) and copy link(s)
- Option to download flyer PDF

### 6.4 Response Viewer

Clicking "Responses" on any form link opens an inline expandable panel (not a full page navigation):

```
┌─────────────────────────────────────────────────────────────────────┐
│ Responses — Food Safety Declaration 2026           67/95 collected  │
├─────────────────────────────────────────────────────────────────────┤
│ Search: [________________]                    [Export CSV] [Gen PDF]│
│                                                                     │
│ ┌──────────────────────┬─────────────┬─────────────────────────────┐│
│ │ Name                 │ Date        │ Status                      ││
│ ├──────────────────────┼─────────────┼─────────────────────────────┤│
│ │ Maria Garcia         │ 03/15 10:30 │ ✓ Signed                   ││
│ │ John Smith           │ 03/15 10:32 │ ✓ Signed                   ││
│ │ ... (65 more)        │             │                             ││
│ └──────────────────────┴─────────────┴─────────────────────────────┘│
│                                                                     │
│ Missing (28):                                                       │
│ Names not yet signed would appear here if a roster is configured   │
│ Otherwise shows count only                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Settings Tab — UI Design

### 7.1 Layout

Settings is a simple vertical layout with collapsible sections:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Settings                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ▼ EHC Outlets                                           [+ Add]    │
│ ┌──────────────┬────────────────┬──────────────────┬──────────────┐│
│ │ Outlet       │ Leader         │ Email            │ Actions      ││
│ ├──────────────┼────────────────┼──────────────────┼──────────────┤│
│ │ MK           │ John Smith     │ john@hotel.com   │ [Edit] [×]   ││
│ │ Casual       │ Jane Doe       │ jane@hotel.com   │ [Edit] [×]   ││
│ │ Toro         │ Bob Wilson     │ bob@hotel.com    │ [Edit] [×]   ││
│ │ LaHa         │ —              │ —                │ [Edit] [×]   ││
│ │ BSAZ         │ —              │ —                │ [Edit] [×]   ││
│ │ Dish         │ —              │ —                │ [Edit] [×]   ││
│ │ GM           │ —              │ —                │ [Edit] [×]   ││
│ │ Pastry       │ —              │ —                │ [Edit] [×]   ││
│ │ Gold         │ —              │ —                │ [Edit] [×]   ││
│ │ Plaza        │ —              │ —                │ [Edit] [×]   ││
│ │ Pools        │ —              │ —                │ [Edit] [×]   ││
│ │ Starbucks    │ —              │ —                │ [Edit] [×]   ││
│ └──────────────┴────────────────┴──────────────────┴──────────────┘│
│                                                                     │
│ ▼ Audit Cycles                                                      │
│   Active: EHC 2026 • Audit Date: July 20, 2026                    │
│   Status: Preparing (109 days)                                      │
│   [Edit Cycle] [+ New Cycle] [Archive]                              │
│                                                                     │
│ ▶ Responsibility Codes                                              │
│   MM, CF, CM, AM, ENG, FF, EHC (7 codes)                           │
│                                                                     │
│ ▶ NC Level Definitions                                              │
│   NC1 (Critical), NC2 (Operational), NC3 (Structural),             │
│   NC4 (Administrative)                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 EHC Outlets

The `ehc_outlet` table is separate from main app outlets for flexibility — EHC tracks areas like "Dish" and "GM" that aren't revenue outlets. Initial data is seeded from the existing `ehc_record_outlet` outlet names.

Leader name and email are optional — they're needed for future email distribution of monthly checklists but not required immediately. The outlet list is used in:
- Forms tab: outlet dropdowns when batch-generating checklist links
- Records tab: outlet filtering (replaces current hardcoded outlet names)
- Settings: CRUD management

---

## 8. Database Changes

### 8.1 New Table: `ehc_outlet`

```sql
CREATE TABLE ehc_outlet (
    id              SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id),
    name            VARCHAR(100) NOT NULL,
    full_name       VARCHAR(255),          -- "Main Kitchen" vs display "MK"
    outlet_type     VARCHAR(50),           -- "Production Kitchen", "Restaurant", "Bar", "Support"
    leader_name     VARCHAR(255),
    leader_email    VARCHAR(255),
    is_active       BOOLEAN DEFAULT true,
    sort_order      SMALLINT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, name)
);
```

Seed from existing outlet names in `ehc_record_outlet` table. The 13 EHC areas from the plan doc:

| name | full_name | type |
|------|-----------|------|
| MK | Main Kitchen | Production Kitchen |
| GM | Garde Manger | Production Kitchen |
| Pastry | Pastry | Production Kitchen |
| Dish | Dishwashing / Stewarding | Support |
| Casual | Casual Dining | Restaurant |
| Toro | Toro Latin Restaurant & Rum Bar | Restaurant |
| LaHa | La Hacienda | Restaurant |
| BSAZ | Bourbon Steak Arizona | Restaurant |
| Gold | Gold Lounge | Lounge |
| Plaza | Plaza Bar | Bar |
| Pools | Pool Service | Bar / Outdoor |
| Palomino | Palomino | Lounge |
| Starbucks | Starbucks | Franchise Outlet |

### 8.2 Existing Table Updates

```sql
-- Add outlet FK to form links (for per-outlet checklist links)
ALTER TABLE ehc_form_link ADD COLUMN outlet_id INTEGER REFERENCES ehc_outlet(id);

-- Add outlet FK to form responses (for filtering/reporting)
ALTER TABLE ehc_form_response ADD COLUMN outlet_id INTEGER REFERENCES ehc_outlet(id);
```

### 8.3 No Changes Needed

- `ehc_form_link` and `ehc_form_response` already exist and work (Phase 1–3 complete)
- Records tab tables unchanged — form integration is purely display-layer
- Responsibility codes and NC levels stay hardcoded for now (editable is a "nice to have")

---

## 9. API Changes

### 9.1 New Endpoints

**EHC Outlets (Settings):**
```
GET    /api/ehc/outlets                    List outlets for org
POST   /api/ehc/outlets                    Create outlet
PATCH  /api/ehc/outlets/{id}               Update outlet (leader, email, etc.)
DELETE /api/ehc/outlets/{id}               Soft-delete outlet
```

**Form Link Enhancements:**
```
POST   /api/ehc/form-links/batch           Batch-create links for a record×period×outlets
GET    /api/ehc/form-links/{id}/flyer      Download printable flyer PDF with QR
POST   /api/ehc/form-links/{id}/generate-pdf   Generate completed form PDF
GET    /api/ehc/form-links/by-record/{record_id}   List all form links for a record (grouped view)
```

### 9.2 Enhanced Existing Endpoints

```
GET /api/ehc/cycles/{id}/submissions
```
Add `has_form_link` and `form_response_count` / `form_expected_count` to submission response objects. This powers the Records tab form link indicator without requiring a separate API call.

---

## 10. Frontend Changes

### 10.1 File Structure

```
frontend/src/pages/EHC/
├── EHC.jsx                          # Main container with 5-tab navigation
├── EHC.css                          # Existing styles
├── tabs/
│   ├── Dashboard.jsx                # Extracted from EHC.jsx
│   ├── AuditPoints.jsx              # Extracted from EHC.jsx  
│   ├── Records.jsx                  # Extracted from EHC.jsx + form link indicators
│   ├── Forms.jsx                    # NEW — form management hub
│   └── Settings.jsx                 # NEW — outlet config, module settings
├── forms/
│   ├── FormPage.jsx                 # Public route /form/:token (existing, outside auth)
│   ├── StaffDeclarationForm.jsx     # Record 11 renderer (existing)
│   ├── TeamRosterForm.jsx           # Record 35 renderer (NEW)
│   ├── TrainingAttendanceForm.jsx   # Record 23 renderer (FUTURE)
│   ├── ChecklistForm.jsx            # Record 20 etc. renderer (FUTURE)
│   ├── SignaturePad.jsx             # Shared component (existing)
│   ├── FormSuccess.jsx              # Shared success state (existing)
│   └── templates/
│       ├── record_11.js             # Static declaration content
│       └── record_35.js             # Static team record header
├── components/
│   ├── FormLinkCard.jsx             # Reusable card for form link display
│   ├── ResponseViewer.jsx           # Inline expandable response list
│   ├── CreateFormModal.jsx          # Multi-step form creation wizard
│   ├── QRShareModal.jsx             # Copy link / download QR / download flyer
│   └── OutletManager.jsx            # CRUD table for Settings tab
```

### 10.2 Component Extraction Priority

The current EHC.jsx is 2,000 lines. Before adding Forms and Settings tabs, extract the existing three tabs into separate components. This is a refactor sprint — no functionality changes:

1. Extract Dashboard rendering logic → `tabs/Dashboard.jsx`
2. Extract Audit Points table + filters → `tabs/AuditPoints.jsx`
3. Extract Records list + submission management → `tabs/Records.jsx`
4. EHC.jsx becomes a thin shell: tab navigation + shared state (active cycle, org)

This makes adding the two new tabs trivial and prevents EHC.jsx from becoming unmanageable.

---

## 11. PDF Generation

### 11.1 Technology

ReportLab (Python). Backend service that generates PDFs matching original EHC template formats.

### 11.2 Templates

**Record 11 (Staff Declaration Summary):**
- Fairmont header + Record 11 title
- Summary text: "The following staff members have read and acknowledged..."
- Table: Name | Date | Signature (image) — auto-paginates
- Footer: total count, generation timestamp, manual version reference

**Record 35 (Food Safety Team Record):**
- Matches original template exactly: Fairmont header, intro text
- Table: Date Approved | Name | Position | Department | Signature (image)
- 5 columns, ~8 rows

**Record 23 (Training Attendance):**
- Header with session title, date, topic
- Agenda text reproduced
- Attendance table: Name | Signature | Timestamp

**Flyer PDF (universal):**
- Fairmont logo, form title, large QR code (~250×250px)
- Brief instruction text: "Scan with your phone camera to complete this form"
- Property name, cycle year
- Ready to print and post

### 11.3 PDF Attachment Flow

1. PDF saved to `uploads/ehc/{org_id}/{year}/forms/record_{number}_{token_prefix}.pdf`
2. `ehc_record_submission.file_path` and `original_filename` updated
3. Submission status advances to `submitted`
4. Admin manually approves (reviews PDF quality)
5. Existing cascade fires: approved → audit point evidence_collected → dashboard

---

## 12. Phased Build Plan

### Phase 4: PDF Generation + Record 35
*Extends existing Phase 1–3 foundation*

1. Install ReportLab, Pillow dependencies
2. PDF generation service: Record 11 summary template
3. PDF generation service: Record 35 template-match layout
4. Flyer PDF template with QR code
5. API endpoints: `/generate-pdf`, `/flyer`
6. Auto-attach PDF to submission on completion
7. `team_roster` form type: backend config schema, public form renderer
8. Team member management UI in form creation flow
9. Test Record 35 end-to-end: create link → share → sign → PDF → attach

### Phase 5: Component Extraction
*Prerequisite for new tabs*

1. Extract Dashboard → `tabs/Dashboard.jsx`
2. Extract Audit Points → `tabs/AuditPoints.jsx`
3. Extract Records → `tabs/Records.jsx`
4. EHC.jsx becomes tab shell with navigation
5. Verify no regressions — all existing functionality works
6. Add empty Forms and Settings tab placeholders

### Phase 6: Forms Tab
*The admin workbench*

1. `Forms.jsx` — grouped-by-record layout
2. `FormLinkCard.jsx` — reusable card component with progress bar and actions
3. `ResponseViewer.jsx` — inline expandable response list with search
4. `CreateFormModal.jsx` — multi-step wizard (select type → configure → generate)
5. `QRShareModal.jsx` — copy link, download QR, download flyer
6. Move existing form link management from Records to Forms tab
7. API: `GET /form-links/by-record/{record_id}` for grouped view
8. Wire up response viewer with export CSV functionality

### Phase 7: Settings Tab + Outlets

1. Alembic migration: `ehc_outlet` table
2. Seed outlets from existing `ehc_record_outlet` data
3. API: CRUD endpoints for `/ehc/outlets`
4. `Settings.jsx` with outlet manager section
5. `OutletManager.jsx` — CRUD table with inline editing
6. Audit cycle management section (move from main UI)
7. Responsibility codes display (read-only initially, editable later)

### Phase 8: Records Tab Integration

1. Enhance submission API response with `has_form_link`, `form_response_count`, `form_expected_count`
2. Form link indicator on submission rows (QR icon + response badge)
3. Quick popover on click: response count, completion %, link to Forms tab
4. Auto-update submission display when PDF is attached

### Phase 9: Training Attendance (Record 23)

1. `training_attendance` form type: backend config schema with agenda text
2. `TrainingAttendanceForm.jsx` — public form with dynamic agenda content + scroll-to-sign
3. PDF template for attendance summary with agenda
4. Session history view in Forms tab (grouped under Record 23)
5. Test end-to-end: create session → paste agenda → generate QR → collect signatures → PDF

### Phase 10: Monthly Checklists (Record 20 etc.)

1. `checklist` form type: config schema with sections and field definitions
2. Define Record 20 checklist structure (fields, sections, corrective action areas)
3. `ChecklistForm.jsx` — public form renderer for dynamic checklist fields
4. Batch form link generation: API endpoint + UI in create wizard
5. Month × outlet grid view in Forms tab
6. PDF template for completed checklist
7. `ehc_form_link.outlet_id` FK wired up
8. Test end-to-end with Record 20: batch generate → distribute → area leaders complete → PDF → approve

### Future (Not Phased Yet)

- Email distribution for monthly checklist links (requires email service integration)
- Standing per-outlet QR codes (auto-detect current period)
- Rate limiting on public endpoints
- Editable responsibility codes and NC levels in Settings
- Form template builder for custom forms
- Batch QR download as ZIP
- Year-over-year: clone form link configs from prior cycle

---

## 13. Decisions Log

1. **Hybrid model:** Forms tab = admin workbench for creation/distribution/management. Records tab = operational source of truth for completion/approval. No redundant tracking.

2. **Grouped by record type:** Forms tab organizes links under their parent record, with record-level aggregate stats and drill-down to individual links. Scales naturally as form types and recurring links multiply.

3. **One link per outlet per period:** Recurring checklists generate a separate form link per outlet. Maps 1:1 to existing submission structure, eliminates outlet selection errors, enables future standing QR codes.

4. **Static templates vs config content:** Record 11 uses static versioned template files. Record 23 uses config-stored agenda text. Checklist fields use config-stored structure. Each pattern exists for a reason — content stability vs. per-session variability vs. structural definition.

5. **Component extraction before new tabs:** EHC.jsx split into tab components before adding Forms/Settings. Prevents the file from growing to 4,000+ lines and makes the new tabs a clean addition.

6. **EHC outlets separate from main outlets:** `ehc_outlet` table with leader name/email, separate from main app outlets. EHC cares about areas (Dish, GM) that aren't revenue outlets. Leader contact info is EHC-specific.

7. **Admin approval preserved:** Form completion → PDF generation → submission status = "submitted" → admin reviews and explicitly approves. No auto-approval, matching existing workflow.

8. **Training agenda in config, not template:** Record 23 agenda changes per session, so it's stored in form link config when creating the link. Form renderer checks for static template reference first, falls back to config content.

9. **Responsibility codes and NC levels stay hardcoded initially:** Editable config is a nice-to-have. Current values work and rarely change. Settings tab shows them for reference but doesn't need CRUD on day one.

10. **Daily logs are NOT forms:** Records 3/4/5/6/12/13/21/27/37 are high-frequency data capture — the HACCP/digital capture module, not the forms system. Different UX, different architecture, different build timeline.
