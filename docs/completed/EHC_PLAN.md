# EHC Module — Planning Document

> **Project:** RestauranTek  
> **Module:** EHC (Eating & Hygiene Compliance)  
> **Date:** March 26, 2026  
> **Property:** Fairmont Scottsdale Princess (fairmont-scp)  
> **Stack:** FastAPI + React, PostgreSQL (Render prod / Unraid dev), Alembic migrations

---

## 1. What This Module Does

The Fairmont Scottsdale Princess undergoes an annual EHC food safety audit — a scored 100-point walk-through of 125 questions across 6 sections, backed by 37 standard EHC records plus 10 SCP-specific records. Preparation spans months, involves multiple departments, and relies on both physical binders in each outlet and a centralized office file.

This module replaces the Notion databases and Word/Excel checklists currently tracking this work. It gives the team a single place to see what's done, what's missing, who owns it, and what still needs to be collected before audit day.

---

## 2. Document Analysis

### 2.1 The Audit Checklist (2025_Audit_Checklist.xlsx)

A 100-point scoring system. Structure:

- **6 Sections** — top-level categories (Purchasing/Storage, Food Handling, Bar & IRD, Good Hygiene, Support Docs, Special Circumstances)
- **26 Subsections** (A through Z) — functional groupings within each section
- **125 Questions** — the individual audit points the EHC auditor walks and scores

Each question carries:
- **Weighted score** — ranges from 0.25 to 2.5 points
- **NC Level (1–4)** — non-conformance severity if the point is failed
  - NC 1 (18 questions): Critical food safety risks — cross contamination, temperatures, sanitizer strength
  - NC 2 (40 questions): Operational compliance — gloves, hand wash, food covering, equipment condition
  - NC 3 (29 questions): Structural/documentation gaps — maintenance, floors, walls, SDS, signage
  - NC 4 (38 questions): Administrative records — completed forms, filed documents, certifications
- **Red/Orange flags** — escalation indicators (none triggered in 2025)
- **Actual score** vs **max score** — 2025 result: 100/100

### 2.2 The Records (EHC Records List + Outlet/Office Checklists)

The records are the *evidence* that backs the 125 audit points. They split into two physical locations:

**Outlet Books** — physical binders kept in each kitchen/bar area containing daily operational records:

| Record | Name | Outlets |
|--------|------|---------|
| 3 | Food Storage Temperature | Casual, Plaza, Pools, Toro, LaHa, BSAZ, Gold, Starbucks, Dish, MK, Pastry, GM |
| 4 | Cooking/Reheating Temperature | Casual, Toro, LaHa, BSAZ, Dish, MK, Starbucks, Pastry |
| 5 | Cooling of Food | Casual, Toro, LaHa, BSAZ, Dish, MK, GM, Pastry |
| 6 | Food Display Temperature | Casual, Dish, Gold |
| 7 | Thermometer Calibration | Casual, Plaza, Pools, Toro, LaHa, BSAZ, Gold, Starbucks, Dish, MK, Pastry, GM |
| 12 | Defrosting | Casual, MK, GM, Pastry, Dish, Toro, LaHa, BSAZ |
| 13 | Dishwasher/Glasswasher Temp | Dish: Casual, MK, Palomino, LaHa, Toro, BSAZ · Glass: Plaza, Pools, LaHa, Toro, BSAZ, Palomino, Gold |
| 17 | Cleaning Schedule | SOP Books: MK/GM/Pastry, Palomino, Casual, BSAZ, Toro, LaHa, Gold, Starbucks · Calendar |
| 20 | Kitchen Audit Checklist | MK, GM, Pastry, Dish, Casual, BSAZ, Toro, LaHa |
| 21 | Food Washing | GM |
| 24 | Allergen Matrix | Casual, BSAZ, Toro, LaHa, Gold, Starbucks |
| 27 | pH Testing | Toro |
| 28 | Thermometer Register | Casual, BSAZ, Toro, LaHa, Gold |
| 37 | Non Conformance | (all — as needed) |
| SCP 40 | Draft Line Cleaning | Plaza, Toro, Pools |
| SCP 47 | Food Sample Log (14 Day) | MK |

**Office Book** — centralized administrative file managed by specific roles:

| Record | Name | Responsibility | Notes |
|--------|------|---------------|-------|
| 1 | Checklist to Visit Suppliers | EHC | |
| 1a | Approved Supplier List | CM | |
| 2 | Food Delivery Record | CM | May, June, July (audit window) |
| 8 | Internal Food Safety Audit | MM/CF | Primary w/ DM signature + CA, Pre-inspection + CA |
| 9 | Food Poisoning Allegation | EHC | |
| 11 | Staff Food Safety Declaration | EHC | |
| 14 | Foreign Matter Record | — | As needed |
| 15 | Pesticide Usage Record | ENG | |
| 16 | Pesticide Approved List | ENG | |
| 18 | Food Poisoning/Foreign Object Letter | EHC | |
| 19 | Outdoor Catering Temp Record | EHC | |
| 23 | Training Records | AM | Attendance + discussion sheets |
| 25 | Ice Machine Cleaning | ENG | |
| 29 | Internal Swabbing | MM | Kitchen monthly, Room (IRD) bi-monthly |
| 30 | Guest-Supplied Food Indemnity | EHC | |
| 30b | Baby Milk Reheating Indemnity | EHC | |
| 32 | Maintenance Defect Record | MM/AM | Print Alice records (May–July) |
| 33 | Pest Sighting Record | MM/AM | Print Alice records (May–July) |
| 34 | Review Record | MM | Close out prior year in EHC Portal + EHC Worksheet |
| 35 | Food Safety Team Record | MM/CF | Summary sheet (MM) + leadership signatures (CF) |
| 36 | Food Donation Waiver | EHC | |
| SCP 38 | Notice Board Documents | AM | |
| SCP 39 | Dish Machine 3rd Party PM | FF | |
| SCP 41 | MSDS Link | FF | |
| SCP 42 | Pest Control License/Contract | ENG | |
| SCP 43 | Pest Control Insurance | ENG | |
| SCP 44 | Pest Control Bait Map | ENG | |
| SCP 45 | Water Testing Records | MM | Q1, Q2, Q3 |
| SCP 46 | Microbial Lab Test Results | MM | Q1, Q2, Q3 |

**Records removed from audit:** 10, 22, 26, 31

### 2.3 Responsibility Codes

| Code | Role | Scope |
|------|------|-------|
| MM | Mike / Audit Prep Manager | Overall coordination, verification records, swabbing, water testing, lab results |
| CF | Chef (Executive Chef) | Internal audits, food safety team, kitchen operations |
| CM | Commissary / Purchasing | Supplier lists, delivery records |
| AM | Area Manager / Assistant Manager | Training records, notice boards, maintenance/pest logs |
| ENG | Engineering | Pesticide records, pest control contracts, ice machines |
| FF | Facilities | Dish machine PMs, MSDS |
| EHC | External auditor (EHC) | Supplier visit checklists, declarations, indemnity forms |
| DM | Director / Division Manager | Signature authority on audits |

### 2.4 Outlet/Area Taxonomy

Based on all documents, these are the distinct areas at SCP:

| Abbreviation | Full Name | Type |
|-------------|-----------|------|
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

### 2.5 Period Patterns

| Frequency | Records |
|-----------|---------|
| Daily | 3, 4, 5, 6, 12, 13, 21 |
| Monthly | 7 (calibration), 20 (kitchen audit), 29 (kitchen swabs), 25 (ice machine) |
| Bi-monthly | 29 (room/IRD swabs) |
| Quarterly | SCP 45 (water testing), SCP 46 (lab results) |
| Annual / One-time | 1, 1a, 8, 11, 23, 34, 35, SCP 38–44 |
| As-needed | 2a, 9, 14, 18, 30, 30b, 32, 33, 36, 37 |
| Audit window (May–Jul) | 2 (delivery records), 32 (Alice prints), 33 (Alice prints) |

---

## 3. Data Model

All tables use existing RestauranTek conventions: UUID PKs, `organization_id` FK, `created_at`/`updated_at` timestamps. Prefix: `ehc_`.

### 3.1 `ehc_audit_cycle`

One per audit year per organization. The top-level container.

```
id                  UUID PK
organization_id     UUID FK → organizations
name                VARCHAR(100)        "EHC 2026"
year                SMALLINT            2026
target_date         DATE                Scheduled audit date
actual_date         DATE                NULL until audit happens
status              VARCHAR(20)         preparing | in_progress | completed | archived
total_score         DECIMAL(5,2)        NULL until scored (out of 100)
passing_threshold   DECIMAL(5,2)        Default 80.0
notes               TEXT
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### 3.2 `ehc_section`

The 6 sections. Static template seeded once per cycle.

```
id                  UUID PK
audit_cycle_id      UUID FK → ehc_audit_cycle
ref_number          SMALLINT            1–6
name                VARCHAR(255)        "Purchasing, Receival & Food Storage"
sort_order          SMALLINT
max_score           DECIMAL(5,2)        Sum of child subsection max scores
created_at          TIMESTAMP
```

### 3.3 `ehc_subsection`

The 26 subsections (A–Z). Each belongs to a section.

```
id                  UUID PK
section_id          UUID FK → ehc_section
ref_code            VARCHAR(5)          "A", "B", ... "Z"
name                VARCHAR(255)        "Purchasing - Approved Suppliers"
sort_order          SMALLINT
max_score           DECIMAL(5,2)        Sum of child audit point max scores
created_at          TIMESTAMP
```

### 3.4 `ehc_audit_point`

The 125 individual questions. The core tracking unit during audit prep.

```
id                  UUID PK
subsection_id       UUID FK → ehc_subsection
ref_code            VARCHAR(10)         "A1", "B2", "M11"
question_text       TEXT                Full question from the checklist
nc_level            SMALLINT            1–4
max_score           DECIMAL(5,2)        Weighted point value (0.25–2.5)
actual_score        DECIMAL(5,2)        NULL until scored
status              VARCHAR(20)         not_started | in_progress | evidence_collected | verified | flagged
flag_color          VARCHAR(10)         NULL, "red", "orange"
responsible_area    VARCHAR(100)        Primary outlet/area responsible
notes               TEXT                Auditor comments, prep notes
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### 3.5 `ehc_record`

The master list of records (37 EHC + 10 SCP). Persists across audit years — this is the reference table.

```
id                  UUID PK
organization_id     UUID FK → organizations
record_number       VARCHAR(10)         "3", "1a", "SCP 40"
name                VARCHAR(255)        "Food Storage Temperature Record"
record_type         VARCHAR(20)         daily | monthly | bi_monthly | quarterly | annual | one_time | audit_window | as_needed
location_type       VARCHAR(20)         outlet_book | office_book
responsibility_code VARCHAR(10)         Freeform label: "MM", "CF", "CM", "AM", "ENG", "FF", "EHC" (no FK to users)
is_physical_only    BOOLEAN             Default true for outlet books
is_removed          BOOLEAN             True for records 10, 22, 26, 31
description         TEXT                What this record is, from the standards manual
notes               TEXT                Prep notes (e.g. "Print Alice Records May–July")
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### 3.6 `ehc_record_outlet`

Which outlets need which outlet-book records. This is the pre-seeded assignment matrix from the Outlet Books checklist.

```
id                  UUID PK
record_id           UUID FK → ehc_record
outlet_name         VARCHAR(100)        "Toro", "MK", "Casual", etc.
sub_type            VARCHAR(50)         NULL, "Dish", "Glass" (for Record 13 split)
notes               TEXT                "Garnish/KegRoom/NA Bev" etc.
created_at          TIMESTAMP
```

### 3.7 `ehc_record_submission`

A specific instance of a record for a given period within an audit cycle. This is the workhorse — where users mark things complete, upload files, or check off physical records.

```
id                  UUID PK
audit_cycle_id      UUID FK → ehc_audit_cycle
record_id           UUID FK → ehc_record
outlet_name         VARCHAR(100)        NULL for office book records
period_label        VARCHAR(50)         "January 2026", "Q1", "May–July", "Annual", "As Needed"
period_start        DATE                NULL for as-needed
period_end          DATE                NULL for as-needed
status              VARCHAR(20)         pending | in_progress | submitted | approved | not_applicable
is_physical         BOOLEAN             Checked off as physically present
file_path           VARCHAR(500)        NULL or path to uploaded file
submitted_by        UUID FK → users     NULL until submitted
approved_by         UUID FK → users     NULL until approved
notes               TEXT
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### 3.8 `ehc_point_record_link`

Many-to-many: which record submissions satisfy which audit points.

```
id                  UUID PK
audit_point_id      UUID FK → ehc_audit_point
record_id           UUID FK → ehc_record
is_primary          BOOLEAN             True if this record is the main evidence for the point
notes               TEXT
created_at          TIMESTAMP
```

This is a link between audit_point and record (not submission) — it defines the *relationship* between "what the auditor asks" and "what evidence answers it." The UI uses this to compute completion: if all linked records have approved submissions for the relevant periods, the audit point can be marked as evidence_collected.

---

## 4. Record ↔ Audit Point Mapping

This is the pre-seeded link table. Based on matching each audit question to the EHC record(s) it references:

| Audit Points | Primary Record(s) | Relationship |
|-------------|-------------------|--------------|
| A1, A2 | 1, 1a | Approved suppliers |
| B1 | 2 | Food delivery/receival |
| B2 | 2a | Rejection record |
| C1, C2, C3, C8, C9, C10 | 3 | Food storage temps |
| C4, C5, C6, C7 | — | Observational (no specific record) |
| D1 | 12 | Defrosting record |
| D2, D3 | — | Observational |
| E1, E2 | — | Observational |
| F1 | 4 | Cooking/reheating temps |
| F2 | — | Menu statement (observational) |
| G1 | 5 | Cooling record |
| G2 | — | Equipment check |
| H1 | — | Observational |
| I1, I3 | 6 | Food display temps |
| I2, I4, I5 | — | Observational |
| J1, J2 | 28 | Thermometer register |
| J3 | 7 | Calibration record |
| J4 | — | Observational (wipes) |
| K1–K12 | 13, SCP 40 | Bar records (dishwasher/glasswasher temps, draft lines) |
| K3, K4 | 25 | Ice machine cleaning |
| L1 | — | Observational (IRD covering) |
| M1–M8 | 17 | Cleaning schedules |
| M9, M10 | 13 | Dishwasher temps |
| M11 | 17 | Cleaning schedules |
| M12 | SCP 41 | MSDS/SDS |
| N1–N4, N6, N7 | — | Observational (maintenance condition) |
| N5 | 32 | Maintenance defect record |
| O1–O14 | — | Observational (food handler behavior) |
| P1 | 33 | Pest sighting record |
| P2, P3 | — | Observational |
| P4, P5 | SCP 42, SCP 43 | Pest control contract/insurance |
| P6 | SCP 44 | Bait map |
| P7 | 16 | Pesticide approved list |
| P8 | 15 | Pesticide usage record |
| Q1, Q2 | — | Observational (waste) |
| R1 | 23 | Training records |
| R2 | — | Training materials (observational) |
| R3 | 23 | Hygiene champion certification |
| S1 | SCP 45 | Water testing |
| T1 | 9, 18 | Food poisoning records |
| T2 | 8 | Internal audit record |
| T3 | SCP 46 | Microbial lab testing |
| T4 | 29 | Swabbing record |
| T5 | 27 | pH testing |
| T6 | SCP 47 | Food sample log |
| T7, T8 | 37 | Non-conformance / corrective actions |
| U1 | — | Observational (room glass sanitation) |
| U2 | 29 | Swabbing (guest rooms) |
| V1 | — | Observational (raw eggs) |
| W1–W5 | 24 | Allergen matrix |
| X1–X4 | 21 | Food washing record |
| Y1, Y2 | — | Observational (glass/wood policy) |
| Z1–Z5 | SCP 38 | Notice board docs, signage |
| Z6 | 34 | Review record (HACCP program) |
| Z7 | — | Observational (doggy bags) |
| Z8 | — | Health dept license (observational) |
| Z9 | 35 | Food safety team record |
| Z10 | — | General (any other comment) |

**Key insight:** Roughly 40% of audit points are purely observational — the auditor sees it during the walk, there's no backing record. The module should handle these as standalone status items that get marked during or after the walk, separate from the record-evidence flow.

---

## 5. Seeding Logic

### 5.1 Audit Cycle Setup

When a new audit cycle is created:

1. Copy all 6 sections, 26 subsections, and 125 audit points from the template (or the prior year's cycle)
2. Copy the record→audit_point link mappings
3. Generate `ehc_record_submission` rows based on `ehc_record.record_type`:
   - **daily** records: One submission per month (Jan–audit month). Each represents a monthly batch of physical daily logs. Completion = checkbox confirming the batch was turned in.
   - **monthly** records: One submission per month in the cycle year (Jan–audit month)
   - **quarterly** records: Q1, Q2, Q3 submissions
   - **annual/one_time** records: Single submission
   - **audit_window** records: Submissions for the audit window months only (e.g., May, June, July)
   - **as_needed** records: Single placeholder submission (users can add more)
4. For outlet-book records, generate submissions per outlet from `ehc_record_outlet`

### 5.2 Editable After Seeding

All seeded data is editable. Users can:
- Add/remove submission periods
- Change responsibility assignments
- Add custom records (the SCP records are already an example of property-specific additions)
- Override the record→audit_point links
- Mark submissions as not_applicable

---

## 6. Completion Flow

The completion status cascades upward:

```
ehc_record_submission (approved)
    ↓ via ehc_point_record_link
ehc_audit_point (evidence_collected when all linked submissions approved)
    ↓
ehc_subsection (% complete based on child point statuses)
    ↓
ehc_section (% complete based on child subsections)
    ↓
ehc_audit_cycle (overall readiness %)
```

For **observational points** (no linked records): status is set directly on the audit point — either during prep (verified by internal audit) or during the actual audit walk.

For **points with linked records**: status auto-advances to `evidence_collected` when all linked record submissions reach `approved` status. Can still be manually overridden.

---

## 7. File Uploads

Some records are always physical (outlet books). Some can have digital uploads (office book records like Alice exports, lab results, training attendance sheets).

- `ehc_record_submission.is_physical` — checkbox for "I have the physical copy in the binder"
- `ehc_record_submission.file_path` — optional digital upload (PDF, image, docx)
- Storage: local filesystem on Unraid for dev, S3-compatible for production (or Render disk)
- File types to accept: PDF, JPEG, PNG, DOCX, XLSX

A submission can be both physical AND have an upload (e.g., scanned copy of a physical record).

---

## 8. UI Priorities

### 8.1 Dashboard (Primary View)

The audit cycle dashboard. Shows:
- Overall readiness percentage
- Section-by-section progress bars
- Countdown to audit date
- Filtered views: by NC level, by status, by responsible area
- Quick-action: "What's still missing?" filtered to incomplete items

### 8.2 Audit Points View

Table/list of all 125 points, filterable by:
- Section / Subsection
- NC Level (1–4)
- Status (not_started → verified)
- Responsible area
- Has linked records vs observational-only

Each point expands to show linked record submissions and their status.

### 8.3 Records View

All records with their submission status, filterable by:
- Location type (outlet book / office book)
- Responsibility code
- Outlet
- Frequency (daily, monthly, etc.)
- Status

Bulk actions: mark multiple submissions as physical-confirmed, upload files against a record.

### 8.4 Record Submission Detail

Individual submission page:
- Status workflow (pending → in_progress → submitted → approved)
- Physical checkbox
- File upload zone
- Notes field
- Shows which audit points this satisfies

---

## 9. API Routes

All under `/api/ehc/` prefix. Standard REST patterns matching existing RestauranTek conventions.

### Audit Cycles
```
GET    /api/ehc/cycles                         List cycles for org
POST   /api/ehc/cycles                         Create new cycle (triggers seeding)
GET    /api/ehc/cycles/{id}                     Get cycle with summary stats
PATCH  /api/ehc/cycles/{id}                     Update cycle metadata
GET    /api/ehc/cycles/{id}/dashboard           Aggregated completion stats
```

### Sections & Subsections
```
GET    /api/ehc/cycles/{id}/sections            All sections with subsections nested
GET    /api/ehc/sections/{id}                   Single section with points
```

### Audit Points
```
GET    /api/ehc/cycles/{id}/points              Filterable list (query params: section, nc_level, status, area)
GET    /api/ehc/points/{id}                     Single point with linked records
PATCH  /api/ehc/points/{id}                     Update status, score, notes
```

### Records
```
GET    /api/ehc/records                         Master record list for org
POST   /api/ehc/records                         Add custom record
PATCH  /api/ehc/records/{id}                    Update record metadata
```

### Submissions
```
GET    /api/ehc/cycles/{id}/submissions         Filterable list
POST   /api/ehc/submissions                     Create new submission
PATCH  /api/ehc/submissions/{id}                Update status, physical flag, notes
POST   /api/ehc/submissions/{id}/upload         File upload
DELETE /api/ehc/submissions/{id}/upload         Remove uploaded file
```

### Seeding / Admin
```
POST   /api/ehc/cycles/{id}/seed                Re-seed submissions for a cycle
GET    /api/ehc/point-record-links/{cycle_id}   View mappings
PATCH  /api/ehc/point-record-links/{id}         Edit a mapping
```

---

## 10. Phased Build Plan

### Phase 1: Data Foundation
- Alembic migrations for all `ehc_` tables
- Seed script: 125 audit points, 47 records, outlet assignments, point↔record links
- Basic CRUD endpoints for cycles, points, records, submissions
- No UI yet — verify data model with API calls

### Phase 2: Dashboard & Points View
- Audit cycle dashboard with progress stats
- Audit points table with filtering
- Point detail view showing linked record status
- Section/subsection drill-down

### Phase 3: Records & Submissions
- Records list view with outlet breakdown
- Submission status workflow
- Physical record checkbox
- File upload (local storage first, S3 later)
- Bulk status updates

### Phase 4: Completion Cascade
- Auto-status computation (submissions → points → subsections → sections → cycle)
- "What's missing?" smart filter
- Pre-audit readiness report

### Phase 5: Year-over-Year
- Clone cycle from prior year
- Score comparison view
- Carry forward notes and corrective actions

---

## 11. Decisions Log

1. **Outlet mapping:** The 13 EHC areas do not currently match RestauranTek outlet names. Reconciliation needed but not blocking — use plain string names in `ehc_record_outlet` for now, add FK to `outlets` table later once names are aligned.

2. **Responsibility codes:** Stay as freeform labels (MM, CF, CM, etc.) — no user assignment or notification system needed now. Can wire to `users` table in a future phase.

3. **Alice/Actabl integration:** Future goal to pull Records 32 (Maintenance Defect) and 33 (Pest Sighting) digitally via Actabl API. Not required for initial build — print-and-file workflow is acceptable. Endpoint research exists somewhere in notes.

4. **Daily record granularity:** Monthly rollup. Physical daily records (temp logs, etc.) are turned in as a monthly batch. Each `ehc_record_submission` for a daily-type record represents one month, with a simple checkbox for completion. No per-day row generation.

5. **Audit walk mode:** Not needed. The EHC auditor conducts the walk and exports results via their own system (Excel). Scoring is imported after the fact, not done live in RestauranTek.

6. **EHC Portal:** Handled separately outside RestauranTek. No integration needed.
