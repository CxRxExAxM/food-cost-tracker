# EHC Module Restructure Plan

**Created:** April 2, 2026
**Status:** Planning
**Related:** EHC_DIGITAL_FORMS_PLAN.md (Phase 3 complete)

---

## Overview

Restructure the EHC module from 3 tabs to 5 tabs, adding dedicated sections for Forms management and module Settings. This creates a scalable foundation for growing form-based workflows and centralizes configuration.

---

## Current Structure

```
EHC Module
├── Dashboard      (overview stats, readiness rings)
├── Audit Points   (144 points, status tracking)
└── Records        (evidence submissions, file uploads)
```

## Proposed Structure

```
EHC Module
├── Dashboard      (overview stats, readiness rings)
├── Audit Points   (144 points, status tracking)
├── Records        (evidence submissions, file uploads)
├── Forms          (NEW - digital signature collection hub)
└── Settings       (NEW - module configuration)
```

---

## Forms Section

### Purpose
Central management hub for all digital form links, response tracking, and future form creation tooling.

### Features

**Form Link Management**
- List all form links across all records and cycles
- Filter by: record type, cycle year, status (active/inactive), completion %
- Quick actions: copy URL, download QR, view responses, deactivate
- Bulk operations: export responses, deactivate multiple

**Response Tracking**
- View all responses for a form link
- See respondent name, outlet, signature, timestamp
- Delete/manage responses
- Export to CSV/PDF

**Completion Metrics**
- Progress bars per form link
- Completion % feeds into Records view
- Records completion feeds into Dashboard

**Future: Form Creation Tooling**
- Create custom form templates (beyond Record 11/35)
- Monthly outlet checks (see below)
- Checklist builders
- Question/acknowledgment editors

### Monthly Outlet Checks (Future Vision)

**Use Case:** Monthly food safety check assigned to each outlet leader

**Workflow Options:**

*Option A: Email-only (no login required)*
- Admin creates monthly check form
- Assigns to outlets with leader email addresses
- System auto-generates unique links per outlet
- Emails sent with personalized links
- Leaders complete on phone, no login needed
- Responses tracked by outlet

*Option B: Leader logins*
- Outlet leaders have user accounts
- Assigned to their outlet(s)
- See pending forms in their dashboard
- Email notifications as reminders
- Can view their submission history

**Decision Needed:** Option A is simpler to implement and matches current tokenized approach. Option B provides better accountability and history but requires user management.

**Recommendation:** Start with Option A (email + tokenized links), add Option B later if needed.

---

## Settings Section

### Purpose
Centralize EHC module configuration. Currently some settings are hardcoded or scattered.

### Features

**Outlet Management**
- CRUD for EHC outlets (may differ from main app outlets)
- Outlet name, leader name, leader email
- Active/inactive status
- Used in: form dropdowns, monthly check assignments, response filtering

**Audit Cycle Configuration**
- Create/edit audit cycles (year, audit date)
- Set cycle as active/archived
- Move cycle dropdown here from main UI

**Responsibility Codes**
- Currently hardcoded: MM, CF, CM, AM, ENG, FF, EHC
- Make editable: code, full name, assignee
- Used in: audit point assignments, filtering

**NC Level Definitions**
- Currently hardcoded: NC1-NC4 with colors
- Make editable: level, name, description, color
- Used in: audit point badges, priority sorting

**Notification Settings (Future)**
- Email notifications on form completion
- Daily/weekly digest options
- Webhook integrations

---

## Data Flow Architecture

```
Settings (outlets, codes, cycles)
    ↓ configures
Forms (digital signatures, monthly checks)
    ↓ completion feeds
Records (evidence tracking)
    ↓ status feeds
Audit Points (point-level status)
    ↓ aggregates to
Dashboard (overall readiness)
```

Each layer looks one level down, creating clean separation of concerns.

---

## Database Changes

### New Tables

```sql
-- EHC Outlets (separate from main outlets for flexibility)
ehc_outlet
  - id
  - organization_id
  - name
  - leader_name
  - leader_email
  - is_active
  - created_at, updated_at

-- Outlet assignments for monthly checks (future)
ehc_outlet_form_assignment
  - id
  - outlet_id
  - form_link_id
  - assigned_at
  - due_date
  - completed_at
```

### Existing Table Updates

```sql
-- ehc_form_link: add outlet assignment
ALTER TABLE ehc_form_link ADD COLUMN outlet_id INTEGER REFERENCES ehc_outlet(id);

-- ehc_form_response: link to outlet (already has respondent_dept)
-- May want to add outlet_id FK for better querying
```

---

## UI Components

### Forms Tab

```
┌─────────────────────────────────────────────────────────┐
│ Forms                                        [+ New Form]│
├─────────────────────────────────────────────────────────┤
│ Filter: [All Records ▼] [All Cycles ▼] [Active ▼]       │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Record 11 - Staff Declaration          45/95 (47%)  │ │
│ │ EHC 2026 • Active • Created Mar 15                  │ │
│ │ [Copy] [QR] [Responses] [Deactivate]               │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Record 35 - Team Roster                 8/12 (67%)  │ │
│ │ EHC 2026 • Active • Created Mar 20                  │ │
│ │ [Copy] [QR] [Responses] [Deactivate]               │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Settings Tab

```
┌─────────────────────────────────────────────────────────┐
│ Settings                                                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Outlets                                      [+ Add]     │
│ ┌──────────────────┬────────────────┬─────────────────┐ │
│ │ La Hacienda      │ John Smith     │ john@hotel.com  │ │
│ │ Bourbon Steak    │ Jane Doe       │ jane@hotel.com  │ │
│ │ Banquets         │ Bob Wilson     │ bob@hotel.com   │ │
│ └──────────────────┴────────────────┴─────────────────┘ │
│                                                          │
│ Audit Cycle                                              │
│ Current: 2026 • Audit Date: June 15, 2026               │
│ [Edit Cycle] [Create New Cycle]                         │
│                                                          │
│ Responsibility Codes                         [Edit]      │
│ MM, CF, CM, AM, ENG, FF, EHC                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase A: UI Restructure
1. Add Forms and Settings tabs to EHC.jsx
2. Move existing form link functionality to Forms tab
3. Create empty Settings tab with placeholder sections
4. Update tab navigation

### Phase B: Forms Tab Build-out
1. List all form links with filtering
2. Response viewer (move from modal to inline/page)
3. Bulk actions (export, deactivate)
4. Completion metrics display

### Phase C: Settings - Outlets
1. Create ehc_outlet table and migration
2. CRUD API endpoints
3. Settings UI for outlet management
4. Update form dropdown to use ehc_outlet

### Phase D: Settings - Configuration
1. Move audit cycle management to Settings
2. Editable responsibility codes (optional - may keep hardcoded)
3. NC level customization (optional)

### Phase E: Monthly Outlet Checks (Future)
1. Form template for monthly checks
2. Outlet assignment workflow
3. Email distribution system
4. Due date tracking and reminders

---

## Open Questions

1. **Separate outlets or reuse main app outlets?**
   - Recommendation: Separate ehc_outlet table for flexibility
   - EHC outlets may differ from recipe/inventory outlets

2. **Leader login vs email-only?**
   - Start with email-only (tokenized links)
   - Add leader accounts later if accountability needed

3. **Responsibility codes editable?**
   - Low priority - current hardcoded list works
   - Could defer to "nice to have"

4. **Form template builder?**
   - Complex feature, defer to later phase
   - Current Record 11/35 templates handle main use cases

---

## Success Metrics

- All form links manageable from one place
- Outlet dropdown populated from database (not hardcoded)
- Clear completion flow: Forms → Records → Dashboard
- Settings changes don't require code deploys

---

## Next Steps

1. Review and approve this plan
2. Start Phase A: UI Restructure
3. Iterate based on usage feedback
