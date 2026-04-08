# Food Waste Tracking Module — Planning Document

> **Project:** RestauranTek  
> **Module:** Waste Tracking  
> **Date:** April 8, 2026  
> **Scope:** Property-level (no outlet breakdown)  
> **Users:** Admin only (single user)  
> **Stack:** FastAPI + React, PostgreSQL (Render prod / Unraid dev), Alembic migrations

---

## 1. Purpose

Track food waste diversion (compost + donation) against total covers to produce a **grams of waste per cover** KPI, measured monthly and compared against an editable year-end goal. QR codes allow kitchen staff to log compost and donation weights without needing a RestauranTek login.

**KPI Formula:**

```
Waste per Cover (g) = ((Compost lbs + Donation lbs) × 453.592) / (F&B Covers + Cafeteria Covers)
```

Where Cafeteria Covers is derived:

```
Cafeteria Covers = (FTE + Temp) × (Theoretic Capture % / 100)
```

---

## 2. Data Model

All tables use existing RestauranTek conventions: UUID primary keys, `organization_id` FK, `created_at`/`updated_at` timestamps. Prefix: `waste_`.

### 2.1 `waste_goals`

One row per year per org. Stores the editable target.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK → organizations | |
| year | INTEGER | e.g. 2026 |
| target_grams_per_cover | DECIMAL(10,2) | Editable at any time; recalc flows downstream |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Unique constraint:** `(organization_id, year)`

### 2.2 `waste_monthly_metrics`

One row per month per year. All manual inputs live here. Donation and compost fields auto-populate from QR weigh-ins but are fully editable (override pattern — same as BEO cover counts).

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK → organizations | |
| year | INTEGER | |
| month | INTEGER | 1–12 |
| fb_covers | INTEGER | Nullable — manual input, F&B guest covers |
| fte_count | INTEGER | Nullable — full-time employee count |
| temp_count | INTEGER | Nullable — temporary employee count |
| theoretic_capture_pct | DECIMAL(5,2) | Nullable — e.g. 75.00 for 75% |
| donation_lbs | DECIMAL(10,2) | Nullable — auto-aggregated from weigh-ins, editable |
| compost_lbs | DECIMAL(10,2) | Nullable — auto-aggregated from weigh-ins, editable |
| notes | TEXT | Optional month notes |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

**Unique constraint:** `(organization_id, year, month)`

**Calculated fields (not stored, computed at read time):**

- `cafe_covers` = `(fte_count + temp_count) × (theoretic_capture_pct / 100)` — rounded to integer
- `total_covers` = `fb_covers + cafe_covers`
- `total_diversion_lbs` = `donation_lbs + compost_lbs`
- `total_diversion_grams` = `total_diversion_lbs × 453.592`
- `grams_per_cover` = `total_diversion_grams / total_covers` (null if total_covers is 0)

### 2.3 `waste_weigh_ins`

Individual submissions from QR code forms. No auth required — validated by token.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK → organizations | |
| token_id | UUID FK → waste_qr_tokens | Which QR code was used |
| category | ENUM | `compost` or `donation` |
| weight_lbs | DECIMAL(10,2) | |
| recorded_date | DATE | User-selected date on the form |
| submitted_at | TIMESTAMP | Server timestamp of submission |
| created_at | TIMESTAMP | |

**No `updated_at`** — weigh-ins are append-only. Corrections happen by editing the monthly total.

### 2.4 `waste_qr_tokens`

Maps QR codes to their category and org. Tokens are UUIDs embedded in the QR URL. Separate table so tokens can be revoked/regenerated without losing weigh-in history.

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | Also the token value in the URL |
| organization_id | UUID FK → organizations | |
| category | ENUM | `compost` or `donation` |
| label | VARCHAR(255) | Display name, e.g. "Main Kitchen Compost" |
| is_active | BOOLEAN | Default true; false = QR link returns error |
| created_at | TIMESTAMP | |

---

## 3. QR Code Weigh-In Flow

### 3.1 Token Generation

Admin (you) generates QR codes from the waste dashboard. Each QR encodes a URL like:

```
https://restaurantek.com/waste/log/{token_uuid}
```

One QR per category minimum (one compost, one donation). You could generate multiples if different physical locations need their own codes — all aggregate to the same monthly totals.

### 3.2 Public Submission Form

The `/waste/log/{token_uuid}` route serves a minimal, no-auth page:

- Validates token exists and `is_active = true`
- Displays: category label (from token), weight input (lbs), date picker (defaults to today)
- Submit → creates `waste_weigh_in` row
- Success confirmation, form resets for next entry
- No login, no navigation, no access to anything else

### 3.3 Aggregation

When the waste dashboard loads monthly metrics, the API:

1. Sums `waste_weigh_ins` for that org/month/year grouped by category
2. If the monthly metric row's `donation_lbs` or `compost_lbs` is NULL → uses the aggregated sum
3. If the field has been manually edited (non-null) → uses the manual value
4. Dashboard shows both: the aggregated QR total and the effective value (which may differ if overridden)

**Implementation note:** This means the monthly row starts with NULL donation/compost. The first time you manually edit the field, it becomes the override. To revert to auto-aggregation, set it back to NULL (UI needs a "reset to auto" option on those fields).

---

## 4. UI Layout

Single page: **Waste Tracking** as a top-level nav item in RestauranTek.

### 4.1 Top Bar

- **Year selector** — dropdown, defaults to current year
- **Year-end goal** — inline editable field showing target grams/cover
- **YTD actual** — calculated grams/cover across all months with data
- **Variance** — actual vs goal, color-coded (green if under target, red if over)

### 4.2 Monthly Breakdown Table

12-row table (Jan–Dec), columns:

| Month | F&B Covers | FTE | Temp | Capture % | Cafe Covers | Donation (lbs) | Compost (lbs) | Total Diversion (g) | Grams/Cover | vs Goal |
|-------|-----------|-----|------|-----------|-------------|----------------|---------------|---------------------|-------------|---------|

- **F&B Covers, FTE, Temp, Capture %** — editable input fields inline
- **Cafe Covers** — calculated, displayed (not editable)
- **Donation, Compost** — shows effective value; editable; indicator if value differs from QR aggregate
- **Total Diversion, Grams/Cover, vs Goal** — calculated, displayed

Two interaction patterns to choose from (decide during build):

**Option A: Inline editable table** — click any input cell to edit, auto-saves on blur. Compact, fast for a single admin user. Risk: gets cramped on narrow screens with this many columns.

**Option B: Row click → modal** — table shows read-only calculated values, click a month row to open a modal with all input fields. Cleaner display, more room for field labels and the QR weigh-in log. Costs an extra click per edit.

**Recommendation:** Option B. The table has too many columns to inline-edit cleanly, and the modal gives you space to also show the QR weigh-in breakdown for that month (individual submissions with dates/weights) so you can reconcile before overriding.

### 4.3 Month Detail Modal

Opens when clicking a month row. Contains:

**Input Section:**
- F&B Covers
- FTE Count
- Temp Count
- Theoretic Capture %
- Cafeteria Covers (calculated, displayed)
- Donation lbs (with "auto: X lbs from N entries" subtext, reset-to-auto button)
- Compost lbs (same pattern)
- Notes

**QR Weigh-In Log Section:**
- Table of individual weigh-ins for this month, both categories
- Columns: Date, Category, Weight (lbs), Submitted At
- **Add entry button** — same fields as the QR form, lets admin add weigh-ins directly from dashboard without scanning
- No delete on individual weigh-ins (corrections go through the monthly override)

**Calculated Summary:**
- Total Covers
- Total Diversion (lbs and grams)
- Grams per Cover
- vs Goal (with color indicator)

### 4.4 QR Code Management

Section on the dashboard (below the table, or as a collapsible panel):

- List of active QR tokens with label and category
- Generate new QR button → creates token, displays QR code (use a client-side QR library, e.g. `qrcode.react`)
- Deactivate/reactivate toggle per token
- Copy URL button (for sharing without printing the QR)

---

## 5. API Routes

All under `/api/waste/` prefix.

### Goals
```
GET    /api/waste/goals?year=2026              Get goal for year (create default if missing)
PUT    /api/waste/goals                        Upsert goal for year
```

### Monthly Metrics
```
GET    /api/waste/metrics?year=2026            All 12 months with calculated fields
GET    /api/waste/metrics/{year}/{month}       Single month with QR weigh-in breakdown
PUT    /api/waste/metrics/{year}/{month}       Upsert monthly inputs
```

### QR Tokens
```
GET    /api/waste/tokens                       List all tokens for org
POST   /api/waste/tokens                       Create new token (category, label)
PATCH  /api/waste/tokens/{id}                  Update label or is_active
```

### Weigh-Ins (Public)
```
GET    /api/waste/log/{token}                  Validate token, return category/label (public)
POST   /api/waste/log/{token}                  Submit weigh-in (public, no auth)
```

### Weigh-Ins (Admin)
```
GET    /api/waste/weigh-ins?year=2026&month=4  List weigh-ins for month
POST   /api/waste/weigh-ins                    Admin-created weigh-in (same as QR but from dashboard)
```

### Dashboard Summary
```
GET    /api/waste/summary?year=2026            YTD aggregates, goal, variance
```

---

## 6. Build Phases

### Phase 1: Schema + Monthly Metrics CRUD
- Alembic migration for all 4 tables
- API routes for goals and monthly metrics
- Basic page with year selector, goal field, 12-month table (read-only initially)
- Month detail modal with input fields
- All calculations computed at read time

### Phase 2: QR Code System
- Token CRUD routes
- Public weigh-in form (standalone page, no nav/auth)
- QR generation on dashboard (qrcode.react)
- Aggregation logic: sum weigh-ins → populate monthly metrics
- Auto vs override display pattern on donation/compost fields

### Phase 3: Polish
- Add weigh-in from dashboard (admin entry in month modal)
- Reset-to-auto button on overridden fields
- Color-coded variance indicators
- YTD summary bar
- Print-friendly QR codes

---

## 7. Technical Notes

- **No outlet dimension.** All data is property-level. If outlet-level tracking is ever needed, add an optional `outlet_id` FK to `waste_monthly_metrics` and `waste_weigh_ins`. Not building for it now.
- **Grams conversion** is always `lbs × 453.592`, applied at read time, never stored.
- **QR tokens are org-scoped.** The public endpoint validates the token and writes the weigh-in against that org. No way to submit data to a different org via QR.
- **Monthly rows are created lazily.** The GET endpoint returns all 12 months; months without a row return calculated defaults (all nulls, zero totals). Rows are created on first PUT.
- **Year rollover:** No special handling. New year = new goal row + empty metrics. Previous year's data stays queryable via year param.
