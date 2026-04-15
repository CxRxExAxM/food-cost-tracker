# Daily Monitoring Module — Planning Document

> **Project:** RestauranTek  
> **Feature:** Daily Monitoring Module (Daily Logs / Daily Operations)  
> **Date:** April 14, 2026  
> **Depends On:** EHC Outlet Settings (outlet configuration with equipment counts and capability toggles)  
> **Status:** Planning — architecture and phasing approved  

---

## 1. What We're Building

A daily equipment monitoring and food safety logging system that replaces the paper "Daily Worksheet" used by kitchen outlets. The module has two faces:

- **Kitchen-facing:** A QR-accessible daily workstation where staff log cooler temps, cooking/reheating temps, cooling records, and thawing records throughout their shifts.
- **Management-facing:** A monthly calendar view where the culinary manager reviews daily completion, spots gaps, and approves the month — which auto-generates EHC record submissions.

The module is built as a **generalized daily monitoring pattern** that starts with the kitchen daily worksheet but extends to dishwasher/glasswasher temp checks and future equipment monitoring (thermometer calibration, IoT sensor feeds, etc.).

### Key Concept: The Daily Workstation

The daily worksheet is NOT a form you submit. It's a **living document for the day** that multiple people contribute to across shifts. The AM cook logs cooler temps at 6am, comes back at 2pm to log a cooling record. The PM cook opens the same workstation and fills in PM temps and dinner cook temps. Everyone works on the same day's record.

The QR code is the entry point — scan it, pick your outlet, land on today's workstation. The QR is permanent (same link every day), not per-deployment like monthly checklists. The system auto-creates the day's record on first access.

---

## 2. Architecture Decisions

### 2.1 Separate Module, Connected to EHC

The daily monitoring module lives as its own nav item ("Daily Logs" or "Daily Operations") rather than inside the EHC module. Reasoning:

- **Different users:** Kitchen staff interact with daily logs; the culinary manager and Mike interact with EHC.
- **Different frequency:** Daily logs are touched multiple times per day; EHC is monthly/quarterly.
- **Different UI priorities:** Daily logs need mobile-first, fast data entry. EHC needs desktop-oriented compliance management.

The connection: every daily log entry flows into the corresponding EHC record submission for that outlet and month. Monthly approval in the daily logs module auto-creates/updates `ehc_record_submission` records.

### 2.2 QR Deployment: Universal with Outlet Selector

Same pattern as the monthly checklist: one universal QR → outlet selector → today's workstation. This lets Mike set it up once and distribute to all outlets without per-outlet QR management.

The QR URL is static: `/daily-log` (or similar). The outlet selector appears on first scan. Once selected, the outlet choice can be remembered via a cookie/localStorage for that device, so the walk-in iPad doesn't ask every time.

### 2.3 Auto-Save, Not Submit

Daily entries auto-save on each field change. No "submit" button for daily work. This eliminates the risk of lost data and matches how paper works — you write it down and walk away.

- **Same-day edits:** Free, no restrictions. Fat-fingered 395 instead of 39.5? Just fix it.
- **Next-day edits:** Allowed but flagged. System requires an edit reason ("PM forgot to log," "transcription error"). Creates an audit trail.
- **Post-approval edits:** Locked. Manager must un-approve the month to allow changes.

Every entry has a `recorded_at` timestamp (when the value was actually entered) separate from the `reading_date` and `shift` it applies to. This prevents backfilling — the auditor can see that all entries for April 3rd were logged on April 3rd, not April 7th.

### 2.4 Coolers/Freezers as Counts, Not Individual Equipment

Outlet settings store `cooler_count` and `freezer_count` as simple integers. The daily worksheet renders that many rows with sequential labels (1, 2, 3... FRZ1, FRZ2). No individual equipment registration for coolers/freezers at this stage.

**Upgrade path:** An optional `equipment` table can be added later to name individual units (e.g., "Walk-in 1 - Proteins"). Daily readings already store a `unit_number`, so historical data doesn't need migration — equipment metadata layers on top.

Dishwashers/glasswashers DO get individual registration (Phase 4) since there are fewer of them and each gets its own QR.

### 2.5 Corrective Actions Feed Record 37

When a reading exceeds its threshold, the system:
1. Flags the entry immediately in the UI (field turns red, status badge changes)
2. Expands an inline corrective action capture: what happened, what action was taken, ALICE ticket # (optional)
3. Tags the entry as a non-conformance

At month end, all tagged entries across all sections and outlets compile into a Record 37 (Non Conformance Record) summary with auto-populated fields:
- **Date** → from the reading's `reading_date`
- **Area** → from the outlet name
- **Non Conformance** → generated from reading context (e.g., "Cooler 3: 45.6°F, threshold 41°F")
- **Action Taken** → from the inline corrective action text

The `Date Completed` and `Sign` fields on Record 37 are filled by the manager during review, as the resolution may happen after the initial flag.

### 2.6 Signatures Are Per-Section, Per-Shift

Each section of the daily worksheet has its own signature capture, per shift. The AM person signs the cooler temp section after their readings. The PM person signs their own readings on the same section. This is cleaner than the paper version's ambiguous single signature line — the audit trail shows exactly who recorded what and when.

### 2.7 Minimum Entry Enforcement

The EHC standard requires specific minimums:
- **Record 3:** All coolers/freezers checked, AM and PM (2 readings per unit per day)
- **Record 4/6:** 3 cook or reheat temps per active meal period per service
- **Record 5:** No fixed minimum (log when you cool food)
- **Record 12:** No fixed minimum (log when you thaw food)

The completion status for each section is based on these minimums. "Complete" means the minimum has been met and signed. "Partial" means some entries exist but minimums aren't met. "Missing" means no entries for that section today.

---

## 3. Outlet Settings Expansion

The existing `ehc_outlet` table (or the planned outlet settings in the EHC Settings tab) needs these additional fields for daily monitoring:

### 3.1 Equipment Counts
```
cooler_count        INTEGER DEFAULT 0    -- Number of cooler/refrigeration units
freezer_count       INTEGER DEFAULT 0    -- Number of freezer units
```

### 3.2 Capability Toggles
```
has_cooking         BOOLEAN DEFAULT FALSE  -- Shows cook/reheat section (Rec 4/6)
has_cooling         BOOLEAN DEFAULT FALSE  -- Shows cooling section (Rec 5)
has_thawing         BOOLEAN DEFAULT FALSE  -- Shows thawing section (Rec 12)
has_hot_buffet      BOOLEAN DEFAULT FALSE  -- Adds hot buffet slots to cook/reheat
has_cold_buffet     BOOLEAN DEFAULT FALSE  -- Adds cold buffet slots to cook/reheat
```

### 3.3 Meal Period Configuration
```
serves_breakfast    BOOLEAN DEFAULT FALSE
serves_lunch        BOOLEAN DEFAULT FALSE
serves_dinner       BOOLEAN DEFAULT FALSE
readings_per_service INTEGER DEFAULT 3    -- Min cook/reheat entries per meal period
```

### 3.4 Threshold Configuration
```
cooler_max_f        DECIMAL DEFAULT 41.0   -- Max cooler temp (°F)
freezer_max_f       DECIMAL DEFAULT 0.0    -- Max freezer temp (°F)
cook_min_f          DECIMAL DEFAULT 165.0  -- Min final cook temp (°F) — always flags below, staff uses corrective action for exceptions
reheat_min_f        DECIMAL DEFAULT 165.0  -- Min reheat temp (°F)
hot_hold_min_f      DECIMAL DEFAULT 140.0  -- Min hot holding temp (°F)
cold_hold_max_f     DECIMAL DEFAULT 41.0   -- Max cold holding temp (°F)
```

### 3.5 Daily Monitoring Toggle
```
daily_monitoring_enabled  BOOLEAN DEFAULT FALSE  -- Master toggle for the whole feature
```

---

## 4. Data Model

### 4.1 Core Tables

**`daily_worksheet`** — One record per outlet per date. The "container" for the day.
```
id                  UUID PRIMARY KEY
organization_id     UUID NOT NULL FK → organizations
outlet_name         VARCHAR NOT NULL          -- String, matches ehc_outlet pattern
worksheet_date      DATE NOT NULL
status              VARCHAR DEFAULT 'open'    -- open | review | approved
approved_by         UUID FK → users
approved_at         TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()

UNIQUE(organization_id, outlet_name, worksheet_date)
```

**`cooler_reading`** — Individual temperature readings for coolers/freezers (Record 3).
```
id                  UUID PRIMARY KEY
worksheet_id        UUID NOT NULL FK → daily_worksheet
unit_type           VARCHAR NOT NULL          -- 'cooler' | 'freezer'
unit_number         INTEGER NOT NULL          -- Sequential (1, 2, 3...)
shift               VARCHAR NOT NULL          -- 'am' | 'pm'
temperature_f       DECIMAL                   -- The reading (nullable = not yet recorded)
is_flagged          BOOLEAN DEFAULT FALSE     -- Auto-set when exceeds threshold
corrective_action   TEXT                      -- What happened / action taken
alice_ticket        VARCHAR                   -- Optional ALICE ticket reference
recorded_by         VARCHAR                   -- Staff initials or name
signature_data      TEXT                      -- Base64 signature image
recorded_at         TIMESTAMP                 -- When the value was actually entered
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()

UNIQUE(worksheet_id, unit_type, unit_number, shift)
```

**`cooking_record`** — Cook/reheat/holding entries (Records 4 & 6).
```
id                  UUID PRIMARY KEY
worksheet_id        UUID NOT NULL FK → daily_worksheet
meal_period         VARCHAR NOT NULL          -- 'breakfast' | 'lunch' | 'dinner'
entry_type          VARCHAR NOT NULL          -- 'cook' | 'reheat' | 'hot_hold' | 'cold_hold'
slot_number         INTEGER NOT NULL          -- Sequential within meal period
item_name           VARCHAR                   -- What was temped (user enters)
temperature_f       DECIMAL
time_recorded       TIME                      -- Time the temp was taken
is_flagged          BOOLEAN DEFAULT FALSE
corrective_action   TEXT
recorded_by         VARCHAR
signature_data      TEXT
recorded_at         TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()
```

**`cooling_record`** — Cooling log entries (Record 5).
```
id                  UUID PRIMARY KEY
worksheet_id        UUID NOT NULL FK → daily_worksheet
item_name           VARCHAR NOT NULL
start_time          TIMESTAMP                 -- When cooling began
end_time            TIMESTAMP                 -- When cooling completed
temp_2hr_f          DECIMAL                   -- Temp after 2 hours (must be ≤70°F)
temp_6hr_f          DECIMAL                   -- Temp after 6 hours (must be ≤41°F)
method              VARCHAR                   -- 'ambient' | 'blast_chill' | 'ice_bath' etc.
is_flagged          BOOLEAN DEFAULT FALSE
corrective_action   TEXT
recorded_by         VARCHAR
signature_data      TEXT
recorded_at         TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()
```

**`thawing_record`** — Thawing log entries (Record 12).
```
id                  UUID PRIMARY KEY
worksheet_id        UUID NOT NULL FK → daily_worksheet
item_name           VARCHAR NOT NULL
start_time          TIMESTAMP                 -- When thawing began
finish_date         DATE                      -- May be next day
finish_time         TIME
finish_temp_f       DECIMAL                   -- Final temp (must be ≤41°F)
method              VARCHAR                   -- 'walkin' | 'running_water' | 'microwave' etc.
is_flagged          BOOLEAN DEFAULT FALSE
corrective_action   TEXT
recorded_by         VARCHAR
signature_data      TEXT
recorded_at         TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()
```

**`daily_edit_log`** — Audit trail for any edits made after initial entry.
```
id                  UUID PRIMARY KEY
organization_id     UUID NOT NULL
table_name          VARCHAR NOT NULL          -- Which table was edited
record_id           UUID NOT NULL             -- PK of the edited record
field_name          VARCHAR NOT NULL          -- Which field changed
old_value           TEXT
new_value           TEXT
edit_reason         TEXT                      -- Required for next-day edits
edited_by           VARCHAR
edited_at           TIMESTAMP DEFAULT NOW()
```

### 4.2 Phase 4 Addition: Equipment Registration

For dishwashers/glasswashers (and eventually named coolers):
```
**`equipment`**
id                  UUID PRIMARY KEY
organization_id     UUID NOT NULL FK → organizations
outlet_name         VARCHAR NOT NULL
equipment_type      VARCHAR NOT NULL          -- 'dishwasher' | 'glasswasher' | 'cooler' | 'freezer'
name                VARCHAR NOT NULL          -- "Main Dish Pit" | "Bar Glasswasher"
location            VARCHAR                   -- Where in the outlet
thresholds          JSONB                     -- Type-specific thresholds
qr_code_id          VARCHAR                   -- For equipment-specific QR codes
is_active           BOOLEAN DEFAULT TRUE
created_at          TIMESTAMP DEFAULT NOW()

**`equipment_reading`**
id                  UUID PRIMARY KEY
equipment_id        UUID NOT NULL FK → equipment
reading_date        DATE NOT NULL
shift               VARCHAR
readings            JSONB NOT NULL            -- Type-specific: {wash_temp, rinse_temp, chemical_level}
is_flagged          BOOLEAN DEFAULT FALSE
corrective_action   TEXT
recorded_by         VARCHAR
recorded_at         TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
```

### 4.3 Record 37 Compilation View

Record 37 (Non Conformance Record) is a **database view**, not a separate table. It unions all flagged entries across all daily monitoring tables:

```sql
CREATE VIEW non_conformance_log AS
SELECT
    cr.recorded_at::date as date,
    dw.outlet_name as area,
    FORMAT('Cooler %s %s: %s°F (max %s°F)',
        cr.unit_type, cr.unit_number, cr.temperature_f, [threshold]) as non_conformance,
    cr.corrective_action as action_taken,
    NULL as date_completed,  -- Filled during manager review
    cr.recorded_by as sign
FROM cooler_reading cr
JOIN daily_worksheet dw ON cr.worksheet_id = dw.id
WHERE cr.is_flagged = TRUE

UNION ALL

-- Similar for cooking_record, cooling_record, thawing_record, equipment_reading
...
ORDER BY date DESC;
```

The actual Record 37 form in the EHC module can be pre-populated from this view, with the manager adding `date_completed` and final signature during monthly review.

---

## 5. API Routes

### 5.1 Daily Workstation
```
GET    /api/daily-log/:outlet/:date          -- Get or create worksheet for date
PATCH  /api/daily-log/:worksheet_id          -- Update worksheet status (review/approve)
```

### 5.2 Cooler Readings (Record 3)
```
GET    /api/daily-log/:worksheet_id/coolers              -- All readings for the day
PUT    /api/daily-log/:worksheet_id/coolers/:unit/:shift  -- Upsert a single reading
POST   /api/daily-log/:worksheet_id/coolers/sign          -- Sign a shift's readings
```

### 5.3 Cooking Records (Records 4 & 6)
```
GET    /api/daily-log/:worksheet_id/cooking               -- All entries for the day
POST   /api/daily-log/:worksheet_id/cooking                -- Add a new entry
PUT    /api/daily-log/:worksheet_id/cooking/:id            -- Update an entry
POST   /api/daily-log/:worksheet_id/cooking/sign           -- Sign a meal period
```

### 5.4 Cooling Records (Record 5)
```
GET    /api/daily-log/:worksheet_id/cooling
POST   /api/daily-log/:worksheet_id/cooling
PUT    /api/daily-log/:worksheet_id/cooling/:id
```

### 5.5 Thawing Records (Record 12)
```
GET    /api/daily-log/:worksheet_id/thawing
POST   /api/daily-log/:worksheet_id/thawing
PUT    /api/daily-log/:worksheet_id/thawing/:id
```

### 5.6 Monthly Review
```
GET    /api/daily-log/calendar/:outlet/:year/:month    -- Monthly calendar with status
GET    /api/daily-log/review/:outlet/:year/:month      -- Monthly summary for review
POST   /api/daily-log/approve/:outlet/:year/:month     -- Approve month → create EHC submissions
```

### 5.7 Non-Conformance (Record 37)
```
GET    /api/daily-log/non-conformance/:outlet/:year/:month  -- Compiled flagged entries
PUT    /api/daily-log/non-conformance/:id/resolve           -- Mark resolved with date
```

### 5.8 Edit History
```
GET    /api/daily-log/edits/:worksheet_id               -- Edit log for a specific day
```

---

## 6. Frontend Components

### 6.1 Daily Workstation (`DailyWorkstation.jsx`)
- Top bar: outlet name, date (with date picker for history), day completion status
- Tab bar: Cooler Temps | Cook/Reheat | Cooling | Thawing (only enabled tabs show)
- Each tab renders its section-specific component
- Mobile-first layout — this is primarily used on phones and tablets

### 6.2 Cooler Temp Section (`CoolerTempSection.jsx`)
- Grid layout: Unit # | AM | PM | Status
- Rows dynamically rendered from outlet's cooler_count + freezer_count
- Inline numeric input for temperatures
- Auto-threshold check on blur → flag if out of range
- Expandable corrective action row when flagged
- Per-shift signature at bottom

### 6.3 Cook/Reheat Section (`CookReheatSection.jsx`)
- Grouped by meal period (only active periods shown)
- Each slot: Item Name (text input) | Cook/Reheat toggle | Time | Temp | Status
- Minimum entries indicator ("2 of 3 required entries logged")
- Buffet holding entries at bottom (if enabled): item name + temp
- Per-meal-period signature

### 6.4 Cooling Section (`CoolingSection.jsx`)
- Add-entry pattern (no fixed rows — add as needed)
- Each entry: Item | Start Time | End Time | 2hr Temp | 6hr Temp | Method | Status
- Method dropdown: ambient, blast chill, ice bath
- Auto-flag if 2hr temp > 70°F or 6hr temp > 41°F

### 6.5 Thawing Section (`ThawingSection.jsx`)
- Add-entry pattern
- Each entry: Item | Start Time | Finish Date | Finish Time | Finish Temp | Method | Status
- Method dropdown: walk-in, running water, microwave
- Auto-flag if finish temp > 41°F

### 6.6 Monthly Calendar View (`MonthlyCalendar.jsx`)
- Calendar grid with color-coded day status (green/yellow/red/gray)
- Click any day → detail view (read-only if approved)
- Month-level stats: X complete, Y partial, Z missed
- "Review & Approve" action for the month
- Non-conformance summary panel

### 6.7 Outlet Selector (`OutletSelector.jsx`)
- Reuses existing outlet selector pattern from monthly checklist
- Remembers last selection per device

---

## 7. Threshold Reference

From the Fairmont Safe Food and Hygiene Standards Manual v3:

| Check | Threshold | Direction |
|-------|-----------|-----------|
| Cooler/refrigeration | ≤ 41°F (5°C) | Flag if above |
| Freezer | ≤ 0°F (-18°C) | Flag if above |
| Final cook temp | ≥ 165°F (74°C) | Flag if below (exceptions for rare meat, fish) |
| Reheat temp | ≥ 165°F (74°C) | Flag if below |
| Hot holding | ≥ 140°F (60°C) | Flag if below |
| Cold holding | ≤ 41°F (5°C) | Flag if above |
| Cooling — 2hr check | ≤ 70°F (21°C) | Flag if above |
| Cooling — 6hr check | ≤ 41°F (5°C) | Flag if above |
| Blast chill | ≤ 41°F within 2hr | Flag if above |
| Thawing finish temp | ≤ 41°F (5°C) | Flag if above |

These are stored as outlet-level settings with defaults, allowing property-level override if needed.

---

## 8. Build Phases

### Phase 1: Outlet Settings Expansion
**Scope:** Add equipment counts, capability toggles, and meal period config to the EHC outlet settings.  
**Tables:** ALTER `ehc_outlet` (or create new config table)  
**UI:** Settings tab additions — numeric inputs for cooler/freezer count, toggle switches for capabilities, checkboxes for meal periods  
**Depends on:** EHC Settings tab (in progress)

### Phase 2: Cooler/Freezer Temperature Monitoring (Record 3)
**Scope:** The simplest, most universal section. Every outlet has coolers. This phase validates the entire pipeline end-to-end.  
**Tables:** `daily_worksheet`, `cooler_reading`, `daily_edit_log`  
**UI:** QR entry → outlet selector → Cooler Temp Section with AM/PM readings, threshold flagging, corrective action capture, shift signature  
**API:** Workstation GET/create, cooler reading CRUD, signing  
**EHC connection:** Not wired yet — just data capture and storage  
**Deliverable:** Kitchen staff can scan QR, log cooler temps, see out-of-range flags, sign their shift

### Phase 3: Remaining Daily Worksheet Sections
**Scope:** Add cook/reheat, cooling, and thawing sections. Add monthly calendar and manager review.  
**Tables:** `cooking_record`, `cooling_record`, `thawing_record`  
**UI:** Full tabbed workstation with all sections, monthly calendar view, manager review/approve workflow  
**API:** CRUD for all record types, monthly calendar, approval  
**EHC connection:** Monthly approval creates `ehc_record_submission` entries for Records 3, 4, 5, 6, 12

### Phase 4: Dishwasher/Glasswasher Monitoring
**Scope:** Equipment registration with individual QR codes. Proves the monitoring pattern is extensible.  
**Tables:** `equipment`, `equipment_reading`  
**UI:** Equipment management in outlet settings, single-section monitoring form per machine, equipment-specific QR generation  
**EHC connection:** Feeds Record 13 (dishwasher temp records)

### Phase 5: Record 37 Auto-Compilation + Analytics
**Scope:** Wire up the non-conformance log and build the reporting layer.  
**Tables:** `non_conformance_log` view  
**UI:** Record 37 pre-populated form in EHC, non-conformance trends dashboard, temperature analytics (per-unit trends, outlier detection)  
**EHC connection:** Full pipeline — daily entries → monthly approval → EHC submissions + Record 37

---

## 9. EHC Record Mapping

| Daily Worksheet Section | EHC Record | Frequency | Notes |
|------------------------|------------|-----------|-------|
| Cooler/freezer temps | Record 3: Food Holding Temperature | Daily (AM + PM) | One per outlet per month |
| Cook/reheat temps | Record 4: Cooking Temperature | Per service | Grouped with Record 6 |
| Hot/cold holding | Record 6: Display Food Temperature | Per service | Grouped with Record 4 |
| Cooling log | Record 5: Cooling of Food Record | As needed | Event-driven entries |
| Thawing log | Record 12: Thawing Record | As needed | Event-driven entries |
| Dishwasher temps | Record 13: Dishwasher Temperature | Daily | Phase 4 |
| Flagged entries | Record 37: Non Conformance Record | Rolling | Auto-compiled view |

---

## 10. Decisions Made

1. **Shift definition:** AM/PM is sufficient. PM shift covers lunch temps as well — the PM person knows to include lunch readings.

2. **Cook temp exceptions:** The system flags ALL cook temps below 165°F — no special handling for rare meat/fish. If staff temp a protein cooked to a lower spec, the system flags it and they explain in the corrective action/non-conformance note. Expectation is staff will learn to only log items expected to hit 165°F. This keeps the logic simple and the audit trail clean.

3. **Blast chill tracking:** No additional handling needed. The existing cooling section with the method dropdown (ambient vs blast chill) is sufficient. Blast chill entries just have a shorter expected timeline.

4. **Photo capture:** Future enhancement. Not in scope for this build. Schema should include an optional `attachments` JSONB field on corrective action entries to support this later.

5. **Offline support:** Future enhancement. Add to long-term roadmap. Would require service workers + IndexedDB + conflict resolution — significant lift. Worth revisiting once the module is in daily use and we know whether WiFi coverage in walk-in areas is actually a problem.

6. **Integration with ALICE:** Future enhancement. Continue capturing ALICE ticket numbers as manual text entry for now. Auto-ticket creation depends on pending API access (`developer@aliceapp.com`) and may require Accor corporate IT approval.

7. **Thermometer calibration (Record 21):** Monthly, not daily. Not part of the daily workstation. Could be handled as a monthly checklist form via the existing EHC Forms system, or added as a separate monthly task in a future phase.

---

## 11. Navigation & Naming

Proposed nav structure:

```
RestauranTek
├── Dashboard
├── Food Cost
├── Daily Logs          ← NEW (this module)
│   ├── Today           ← Default: outlet selector → workstation
│   ├── Calendar        ← Monthly view per outlet
│   └── Review          ← Manager approval workflow
├── EHC
│   ├── Dashboard
│   ├── Audit Points
│   ├── Records         ← Auto-populated by Daily Logs approval
│   ├── Forms           ← Monthly checklists, declarations, etc.
│   └── Settings        ← Outlet config lives here
├── Food Waste          ← Planned module
└── Settings
```

The outlet configuration (cooler counts, capabilities, meal periods) lives in EHC Settings because it's part of outlet management. The Daily Logs module reads that configuration but doesn't own it.
