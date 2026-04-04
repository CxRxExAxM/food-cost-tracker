# EHC Settings Tab — Build Spec

> **Project:** RestauranTek  
> **Feature:** EHC Settings Tab — Outlet Management & Module Configuration  
> **Date:** April 4, 2026  
> **Depends On:** EHC tab restructure (Phase 5 — complete), Forms tab (Phase 6 — complete)  
> **Current State:** Settings tab exists with cycle status management and NC level reference. "Coming Soon" placeholders for outlets, contacts, responsibility codes, scoring.

---

## 1. What We're Building

The Settings tab becomes the configuration backbone for the EHC module. The primary deliverable is **EHC Outlet Management** — a managed list of property areas (kitchens, restaurants, bars) with optional leader contact info. Secondary deliverables are making responsibility codes viewable/editable and cleaning up the cycle management UI.

### Architecture Decision: Decoupled Outlets

The `ehc_outlet` table is a **managed master list**, NOT a foreign key constraint on other tables. Existing tables (`ehc_record_outlet`, `ehc_form_link.config`, `ehc_record_submission.outlet_name`) continue using string outlet names. The outlet list serves as:

- A **suggestion source** for tag-pill selectors in form creation and record assignment
- A **reference directory** with leader names and emails for future distribution
- A **filter source** for consistent outlet dropdowns across the module

This means:
- No migration of existing string-based outlet references
- No FK constraints between `ehc_outlet` and other tables
- Outlet names in `ehc_outlet` should *match* the strings used elsewhere, but mismatches don't break anything
- A form link or record can reference an outlet not in the `ehc_outlet` table (manual override)

---

## 2. Data Model

### 2.1 New Table: `ehc_outlet`

```sql
CREATE TABLE ehc_outlet (
    id              SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(50) NOT NULL,        -- Short name used as tag/pill: "MK", "Toro", "LaHa"
    full_name       VARCHAR(255),                -- Display name: "Main Kitchen", "Toro Latin Restaurant & Rum Bar"
    outlet_type     VARCHAR(50),                 -- "Production Kitchen", "Restaurant", "Bar", "Lounge", "Support", "Franchise"
    leader_name     VARCHAR(255),                -- Optional: area leader / chef de cuisine
    leader_email    VARCHAR(255),                -- Optional: for future email distribution
    is_active       BOOLEAN DEFAULT true,
    sort_order      SMALLINT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE INDEX idx_ehc_outlet_org ON ehc_outlet(organization_id);
```

### 2.2 New Table: `ehc_responsibility_code`

```sql
CREATE TABLE ehc_responsibility_code (
    id              SERIAL PRIMARY KEY,
    organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    code            VARCHAR(10) NOT NULL,       -- "MM", "CF", "CM", etc.
    role_name       VARCHAR(255),               -- "Audit Prep Manager" — admin defines this
    scope           TEXT,                        -- "Coordination, swabbing" — admin defines this
    is_active       BOOLEAN DEFAULT true,
    sort_order      SMALLINT DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, code)
);

CREATE INDEX idx_ehc_resp_code_org ON ehc_responsibility_code(organization_id);
```

### 2.3 Seed Data — Responsibility Codes

Seed the code labels only. Role and scope start **blank** — the admin fills them in based on actual property assignments.

```python
SCP_RESPONSIBILITY_CODES = [
    ("MM",  None, None, 1),
    ("CF",  None, None, 2),
    ("CM",  None, None, 3),
    ("AM",  None, None, 4),
    ("ENG", None, None, 5),
    ("FF",  None, None, 6),
    ("EHC", None, None, 7),
]
# Columns: (code, role_name, scope, sort_order)
# role_name and scope are NULL — admin defines meanings via Settings UI
```

### 2.4 Seed Data — Outlets

Populate from existing `ehc_record_outlet` outlet names on first run. The 13 SCP areas:

```python
SCP_OUTLETS = [
    ("MK",        "Main Kitchen",                    "Production Kitchen", 1),
    ("GM",        "Garde Manger",                     "Production Kitchen", 2),
    ("Pastry",    "Pastry",                           "Production Kitchen", 3),
    ("Dish",      "Dishwashing / Stewarding",         "Support",           4),
    ("Casual",    "Casual Dining",                    "Restaurant",        5),
    ("Toro",      "Toro Latin Restaurant & Rum Bar",  "Restaurant",        6),
    ("LaHa",      "La Hacienda",                      "Restaurant",        7),
    ("BSAZ",      "Bourbon Steak Arizona",            "Restaurant",        8),
    ("Gold",      "Gold Lounge",                      "Lounge",            9),
    ("Plaza",     "Plaza Bar",                        "Bar",              10),
    ("Pools",     "Pool Service",                     "Bar",              11),
    ("Palomino",  "Palomino",                         "Lounge",           12),
    ("Starbucks", "Starbucks",                        "Franchise",        13),
]
# Columns: (name, full_name, outlet_type, sort_order)
# leader_name and leader_email start as NULL — filled in via Settings UI
```

Seed logic: check if `ehc_outlet` is empty for the org, if so insert the defaults. Don't re-seed if outlets already exist. Can be triggered by a management command or run on first Settings tab load.

---

## 3. API Endpoints

All under `/api/ehc/outlets`, authenticated, organization-scoped.

### 3.1 CRUD

```
GET    /api/ehc/outlets
```
List all outlets for the org. Returns array sorted by `sort_order`. Optional query param `?active_only=true` (default true).

Response:
```json
{
  "data": [
    {
      "id": 1,
      "name": "MK",
      "full_name": "Main Kitchen",
      "outlet_type": "Production Kitchen",
      "leader_name": null,
      "leader_email": null,
      "is_active": true,
      "sort_order": 1
    }
  ],
  "count": 13
}
```

```
POST   /api/ehc/outlets
```
Create a new outlet. Required: `name`. Optional: `full_name`, `outlet_type`, `leader_name`, `leader_email`, `sort_order`.

Validation: `name` must be unique within the org (case-insensitive).

```
PATCH  /api/ehc/outlets/{id}
```
Update outlet fields. Any field can be updated independently.

```
DELETE /api/ehc/outlets/{id}
```
Soft-delete: sets `is_active = false`. Does NOT cascade or affect any other tables (decoupled design). Outlet disappears from active dropdowns/pills but historical references remain valid.

### 3.2 Seed Endpoint

```
POST   /api/ehc/outlets/seed
```
Admin-only. Seeds default SCP outlets if none exist for the org. Returns count of outlets created. Idempotent — does nothing if outlets already exist.

### 3.3 Reorder Endpoint

```
PATCH  /api/ehc/outlets/reorder
```
Accepts array of `{ id, sort_order }` objects. Updates sort order for all provided outlets in a single transaction.

### 3.4 Responsibility Codes CRUD

```
GET    /api/ehc/responsibility-codes       List all codes for org (sorted by sort_order)
POST   /api/ehc/responsibility-codes       Create a new code (code required, role/scope optional)
PATCH  /api/ehc/responsibility-codes/{id}  Update role_name, scope, is_active
DELETE /api/ehc/responsibility-codes/{id}  Soft-delete (set is_active = false)
POST   /api/ehc/responsibility-codes/seed  Seed defaults if none exist (idempotent)
```

Validation: `code` must be unique within org (case-insensitive), max 10 characters, no spaces.

---

## 4. Settings Tab UI

### 4.1 Updated Layout

Replace the "Coming Soon" section with real outlet management. Keep the existing cycle overview and NC reference sections.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Settings                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ ▼ Audit Cycle Overview          (EXISTING — keep as-is)            │
│   EHC 2026 • Preparing • July 20, 2026 (107 days)                 │
│   [Status management cards]                                         │
│                                                                     │
│ ▼ EHC Outlets                                           [+ Add]    │
│                                                                     │
│   Production Kitchen                                                │
│   ┌──────────┬─────────────────────────┬────────────┬─────────┐    │
│   │ MK       │ Main Kitchen            │ —          │ [Edit]  │    │
│   │ GM       │ Garde Manger            │ —          │ [Edit]  │    │
│   │ Pastry   │ Pastry                  │ —          │ [Edit]  │    │
│   └──────────┴─────────────────────────┴────────────┴─────────┘    │
│                                                                     │
│   Restaurant                                                        │
│   ┌──────────┬─────────────────────────┬────────────┬─────────┐    │
│   │ Casual   │ Casual Dining           │ —          │ [Edit]  │    │
│   │ Toro     │ Toro Latin Restaurant   │ —          │ [Edit]  │    │
│   │ LaHa     │ La Hacienda             │ John S.    │ [Edit]  │    │
│   │ BSAZ     │ Bourbon Steak Arizona   │ —          │ [Edit]  │    │
│   └──────────┴─────────────────────────┴────────────┴─────────┘    │
│                                                                     │
│   Bar                                                               │
│   ┌──────────┬─────────────────────────┬────────────┬─────────┐    │
│   │ Plaza    │ Plaza Bar               │ —          │ [Edit]  │    │
│   │ Pools    │ Pool Service            │ —          │ [Edit]  │    │
│   └──────────┴─────────────────────────┴────────────┴─────────┘    │
│                                                                     │
│   Lounge                                                            │
│   ┌──────────┬─────────────────────────┬────────────┬─────────┐    │
│   │ Gold     │ Gold Lounge             │ —          │ [Edit]  │    │
│   │ Palomino │ Palomino               │ —          │ [Edit]  │    │
│   └──────────┴─────────────────────────┴────────────┴─────────┘    │
│                                                                     │
│   Support / Other                                                   │
│   ┌──────────┬─────────────────────────┬────────────┬─────────┐    │
│   │ Dish     │ Dishwashing/Stewarding  │ —          │ [Edit]  │    │
│   │ Starbucks│ Starbucks               │ —          │ [Edit]  │    │
│   └──────────┴─────────────────────────┴────────────┴─────────┘    │
│                                                                     │
│ ▼ Responsibility Codes                                   [+ Add]    │
│                                                                     │
│   ┌──────┬──────────────────────────┬──────────────────────────┬───┐│
│   │ Code │ Role                     │ Scope                    │   ││
│   ├──────┼──────────────────────────┼──────────────────────────┼───┤│
│   │ MM   │ (editable)               │ (editable)               │ ✏ ││
│   │ CF   │ (editable)               │ (editable)               │ ✏ ││
│   │ CM   │ (editable)               │ (editable)               │ ✏ ││
│   │ AM   │ (editable)               │ (editable)               │ ✏ ││
│   │ ENG  │ (editable)               │ (editable)               │ ✏ ││
│   │ FF   │ (editable)               │ (editable)               │ ✏ ││
│   │ EHC  │ (editable)               │ (editable)               │ ✏ ││
│   └──────┴──────────────────────────┴──────────────────────────┴───┘│
│   You define what each code means. Used in audit point assignments  │
│   and record filtering.                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Outlet Table Design

**Grouped by `outlet_type`** — Production Kitchen, Restaurant, Bar, Lounge, Support/Other. Groups are collapsible. Within each group, outlets are sorted by `sort_order`.

**Columns:**
- **Name** — the short name / tag pill label (MK, Toro, etc.)
- **Full Name** — the long display name
- **Leader** — leader name (shows "—" if not set)
- **Actions** — [Edit] button

The leader email is NOT shown in the table (clutters the view) — it's visible in the edit modal.

### 4.3 Edit Modal / Inline Edit

Clicking [Edit] opens an inline editing row or a small modal:

```
┌─────────────────────────────────────────────────────────────┐
│ Edit Outlet                                          [Save] │
│                                                             │
│ Name (tag):     [MK          ]                              │
│ Full Name:      [Main Kitchen                          ]    │
│ Type:           [Production Kitchen ▼]                      │
│ Leader Name:    [                                      ]    │
│ Leader Email:   [                                      ]    │
│ Active:         [✓]                                         │
│                                                             │
│                              [Cancel] [Save] [Deactivate]   │
└─────────────────────────────────────────────────────────────┘
```

Type dropdown options: Production Kitchen, Restaurant, Bar, Lounge, Support, Franchise, Other.

### 4.4 Add Outlet

[+ Add] button at the section header opens the same form as edit, but empty. New outlets get `sort_order = max + 1` by default.

### 4.5 Responsibility Codes

Editable CRUD table. The current hardcoded codes (MM, CF, CM, etc.) are seeded as defaults with **blank role and scope fields** — the admin fills in the actual meanings. This is important because the assumptions baked into the EHC_PLAN.md about what each code means were inaccurate.

**Columns:**
- **Code** — the short label (MM, CF, etc.). Editable on creation, immutable after (since it's referenced elsewhere as a string)
- **Role** — who this code represents (e.g., the actual person's title). Editable
- **Scope** — what they're responsible for. Editable
- **Actions** — [Edit] inline, [Delete] (soft-delete)

**Inline editing:** Click the edit icon on a row to make Role and Scope fields editable in-place. Save on blur or Enter. No modal needed — this is a simple table.

**Add new code:** [+ Add] at section header. Opens an inline new row at the bottom of the table with Code, Role, Scope fields.

### 4.6 NC Levels

**Removed from Settings.** NC levels (1–4) are defined by the audit company and don't change. They're not configuration — they're reference information. The existing NC level reference display should move to the Dashboard as a help tooltip or info panel, or stay as a reference in the Audit Points tab where it's contextually relevant. It does not belong in Settings because Settings implies configurability.

**Action for current Settings tab:** Remove the NC Level Reference section entirely. If users need to look up what NC1–NC4 mean, that context belongs next to where NC badges appear (Audit Points tab, Dashboard).

---

## 5. Outlet Tag Pills — Integration Points

Once `ehc_outlet` is populated, the outlet list becomes available as tag pills / selectable chips in other parts of the module. These integrations are NOT part of the Settings build but are enabled by it:

### 5.1 Form Creation (TableSignoffModal)

When creating a form link, an optional "Assign to Outlets" step shows outlet pills from `ehc_outlet`. Tapping a pill adds that outlet to the form's distribution list. This is how batch-generation would work for monthly checklists: select Record 20, select April 2026, tap the outlet pills for which kitchens need it, generate.

**Implementation:** The `TableSignoffModal` would call `GET /api/ehc/outlets` to populate the pill selector. Selected outlets get written into the form link config or used to batch-generate per-outlet links.

### 5.2 Record Outlet Assignment

The existing record outlet management (which outlets need which records) currently uses the `ehc_record_outlet` table with string names. A future enhancement: the "Add Outlet" action on a record could show pills from `ehc_outlet` instead of a freeform text input, ensuring consistency.

### 5.3 Response Filtering

Forms and Records tabs could filter by outlet using pills from `ehc_outlet` instead of deriving the list from existing data.

### 5.4 Monthly Checklist Distribution (Future)

When sending monthly checklist links to area leaders, the system reads `leader_email` from `ehc_outlet` to know where to send each outlet's link.

---

## 6. Build Plan

### Step 1: Database & API
1. Alembic migration: create `ehc_outlet` table
2. Seed script with SCP outlet defaults (run on first load or via `/seed` endpoint)
3. CRUD endpoints: GET, POST, PATCH, DELETE
4. Reorder endpoint for sort order management

### Step 2: Settings UI — Outlets Section
1. Replace "Coming Soon" outlets placeholder with real outlet table
2. Grouped-by-type layout with collapsible sections
3. Edit modal for individual outlets
4. Add outlet form
5. Deactivate (soft-delete) action
6. Load outlets on Settings tab mount, refetch after mutations

### Step 3: Settings UI — Responsibility Codes
1. Alembic migration: create `ehc_responsibility_code` table
2. Seed script with SCP code defaults (codes only, role/scope blank)
3. CRUD endpoints for responsibility codes
4. Inline-editable table in Settings tab
5. Add new code functionality
6. Deactivate (soft-delete) action

### Step 4: Remove NC Levels from Settings
1. Remove the NC Level Reference section from Settings.jsx
2. Optionally relocate NC reference as a tooltip/info panel in Audit Points tab or Dashboard
3. NC levels remain hardcoded — they're audit company constants, not configuration

### Step 5: Integration Prep (Optional, Not Blocking)
1. Export an `OutletPillSelector` component from the Settings/shared module
2. This component calls `GET /api/ehc/outlets`, renders selectable pills
3. Consumed by TableSignoffModal and Records tab in future phases

---

## 7. Decisions Log

1. **Decoupled outlets:** `ehc_outlet` is a managed suggestion list, not an FK constraint. No migration of existing string references. Outlet pills suggest from the list, but manual overrides are allowed.

2. **Grouped by type:** Outlets display grouped by `outlet_type` (Production Kitchen, Restaurant, Bar, etc.) for visual organization. This matches how the property actually thinks about its spaces.

3. **Leader info optional:** `leader_name` and `leader_email` are nullable. Not every outlet has a single identifiable leader, and the info isn't needed until email distribution is built.

4. **Soft delete:** Deactivating an outlet hides it from active selectors but preserves historical references. No cascading effects on other tables.

5. **Responsibility codes editable with blank defaults:** Codes are seeded as labels only (MM, CF, etc.) with role and scope left blank for the admin to define. The previous hardcoded assumptions about what each code meant were inaccurate. The admin knows their own org structure — let them fill it in.

6. **NC levels removed from Settings:** NC levels are audit company constants, not property configuration. Displaying them in Settings implies they're changeable when they're not. Reference info for NC1–NC4 belongs contextually near where NC badges appear (Audit Points, Dashboard), not in a configuration tab.

7. **Seed once, manage forever:** Default outlets and codes are seeded on first access. After that, all management is through the UI. Seed endpoints are idempotent — safe to call repeatedly.

8. **Tag pills are a separate integration:** The outlet list enables pill selectors across the module, but building the pill component and wiring it into form creation is a separate task. Settings just provides the data source.
