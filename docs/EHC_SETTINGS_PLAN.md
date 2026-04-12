# EHC Settings Tab — Planning Document

> **Project:** RestauranTek  
> **Module:** EHC → Settings Tab  
> **Date:** April 11, 2026  
> **Stack:** FastAPI + React + PostgreSQL, Alembic migrations  
> **Repo:** `github.com/CxRxExAxM/food-cost-tracker`  
> **Related:** `EHC_CHECKLIST_FORMS_PLAN.md` (template system depends on outlets defined here)

---

## 1. Problem

The EHC module currently uses freeform strings for outlet names (per Decision #1 in the original planning doc). Responsibility codes exist in the Notion planning doc but are acknowledged as incorrect. There's no way to:

- Manage which outlets participate in EHC
- Assign leaders/contacts to outlets
- Email QR codes or form links to the right people
- Configure outlet-level settings (book type, record requirements)

The Settings tab creates the foundation that the template deploy system, email distribution, and future outlet compliance dashboard all depend on.

---

## 2. What the Settings Tab Contains

Three sections, built in order:

### 2.1 EHC Outlets

The 13 (or however many) areas that participate in EHC at this property. Each outlet is a record in the database — not a freeform string.

**Per outlet:**
- Name (e.g., "Toro Latin Restaurant & Rum Bar")
- Abbreviation (e.g., "Toro") — used in UI, forms, and dropdowns
- Type: Production Kitchen / Restaurant / Bar / Lounge / Support / Franchise
- Book type: Outlet Book / Office Book / Both — determines which records apply
- Active flag — so outlets can be deactivated without deleting history
- Sort order — controls display ordering in lists and forms

**UI:** A simple editable table/list. Add outlet, edit inline, toggle active, drag to reorder. Nothing fancy.

**Relationship to RestauranTek outlets table:** These are EHC-specific outlet records, NOT the same as the platform-level `outlets` table (which is tied to food costing, user access, etc.). An optional `outlet_id` FK can link them later when ready to reconcile, but for now they're independent. This avoids coupling EHC outlet management to the broader platform outlet structure.

### 2.2 EHC Contacts

People involved in EHC at this property. Not RestauranTek users (yet) — just name/email/role records that the system can use for email distribution and display.

**Per contact:**
- Name
- Email
- Title/Role (freeform text, e.g., "Executive Sous Chef", "Hygiene Champion", "Area Manager")
- Assigned outlets (many-to-many — one person can be responsible for multiple outlets)
- Is primary (boolean per outlet assignment — the main person who gets the QR email)
- Active flag
- User ID (nullable FK to `users` table — populated later when/if they get accounts)

**UI:** Contact list with inline editing. Each contact shows their assigned outlets as pills/chips. Click a contact to edit details and outlet assignments. Add new contact button.

**The outlet assignment piece is key:** When you deploy checklist forms and select "Toro," the system looks up who the primary contact is for Toro and emails them the QR. No manual email entry at deploy time.

### 2.3 Email Configuration

Integration with Resend for transactional email. Minimal configuration needed in the UI — mostly backend setup.

**What the admin sees in Settings:**
- Verified sending domain status (restaurantek.io)
- "Send test email" button to verify configuration
- Default "from" name (e.g., "RestauranTek EHC")
- Optional reply-to address

**What happens behind the scenes:**
- `RESEND_API_KEY` env var on Render (same pattern as `ANTHROPIC_API_KEY`)
- `restaurantek.io` domain verified in Resend dashboard (DNS records)
- Email utility function used by the deploy endpoint and future notification features

---

## 3. Database Changes

### 3.1 New Table: `ehc_outlet`

```sql
CREATE TABLE ehc_outlet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,          -- "Toro Latin Restaurant & Rum Bar"
    abbreviation VARCHAR(50) NOT NULL,   -- "Toro"
    outlet_type VARCHAR(50),             -- 'production_kitchen', 'restaurant', 'bar', 'lounge', 'support', 'franchise'
    book_type VARCHAR(20) DEFAULT 'outlet',  -- 'outlet', 'office', 'both'
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    outlet_id UUID REFERENCES outlets(id),  -- nullable FK to platform outlets, for future reconciliation
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(organization_id, abbreviation)
);
```

### 3.2 New Table: `ehc_contact`

```sql
CREATE TABLE ehc_contact (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    title VARCHAR(255),                  -- "Executive Sous Chef"
    is_active BOOLEAN DEFAULT TRUE,
    user_id UUID REFERENCES users(id),   -- nullable, linked later
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 New Table: `ehc_contact_outlet`

Many-to-many between contacts and outlets:

```sql
CREATE TABLE ehc_contact_outlet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES ehc_contact(id) ON DELETE CASCADE,
    outlet_id UUID NOT NULL REFERENCES ehc_outlet(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,    -- primary contact for this outlet
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(contact_id, outlet_id)
);
```

### 3.4 New Table: `ehc_email_log`

Track sent emails for debugging and audit trail:

```sql
CREATE TABLE ehc_email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    contact_id UUID REFERENCES ehc_contact(id),
    email_to VARCHAR(255) NOT NULL,
    email_subject VARCHAR(500),
    email_type VARCHAR(50),              -- 'form_qr', 'reminder', 'notification'
    form_link_id UUID REFERENCES ehc_form_link(id),
    resend_id VARCHAR(100),              -- Resend's message ID for tracking
    status VARCHAR(20) DEFAULT 'sent',   -- 'sent', 'delivered', 'bounced', 'failed'
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. API Endpoints

### 4.1 Outlet Management

```
GET    /api/ehc/settings/outlets              -- List outlets for org
POST   /api/ehc/settings/outlets              -- Create outlet
PUT    /api/ehc/settings/outlets/{id}         -- Update outlet
DELETE /api/ehc/settings/outlets/{id}         -- Soft delete (set inactive)
PUT    /api/ehc/settings/outlets/reorder      -- Bulk update sort_order
```

### 4.2 Contact Management

```
GET    /api/ehc/settings/contacts             -- List contacts with outlet assignments
POST   /api/ehc/settings/contacts             -- Create contact
PUT    /api/ehc/settings/contacts/{id}        -- Update contact
DELETE /api/ehc/settings/contacts/{id}        -- Soft delete (set inactive)
POST   /api/ehc/settings/contacts/{id}/outlets -- Set outlet assignments (replace all)
```

**Contact list response includes nested outlet assignments:**
```json
{
  "id": "uuid",
  "name": "Juan Garcia",
  "email": "jgarcia@fairmont.com",
  "title": "Executive Sous Chef",
  "outlets": [
    {"outlet_id": "uuid", "abbreviation": "Toro", "is_primary": true},
    {"outlet_id": "uuid", "abbreviation": "LaHa", "is_primary": false}
  ]
}
```

### 4.3 Email

```
POST   /api/ehc/settings/email/test           -- Send test email to current user
POST   /api/ehc/email/send-form-links         -- Send QR/links to contacts for given form links
```

**Send form links request:**
```json
{
  "form_link_ids": ["uuid1", "uuid2", "uuid3"],
  "include_qr": true,
  "custom_message": "Please complete your April kitchen audit by April 30."
}
```

This endpoint:
1. For each form link, looks up the outlet → finds primary contact → gets email
2. Sends an email with the QR code inline, a direct link to the form, and any custom message
3. Logs each send in `ehc_email_log`
4. Returns success/failure per recipient

---

## 5. Email Implementation

### 5.1 Resend Setup

**Dependencies:**
```
pip install resend
```

**Environment variable:**
```
RESEND_API_KEY=re_xxxxxxxxxxxx
```

**Domain verification:**
- Add DNS records to restaurantek.io as instructed by Resend dashboard
- SPF, DKIM, and DMARC records for deliverability
- Once verified, emails send from `noreply@restaurantek.io`

### 5.2 Email Utility

**New file:** `api/app/utils/email.py`

```python
import resend
import os
from typing import Optional

resend.api_key = os.getenv("RESEND_API_KEY")

SENDER = "RestauranTek EHC <noreply@restaurantek.io>"

def send_form_qr_email(
    to_email: str,
    to_name: str,
    outlet_name: str,
    form_name: str,
    period_label: str,
    form_url: str,
    qr_image_base64: Optional[str] = None,
    custom_message: Optional[str] = None
) -> dict:
    """Send a form QR code email to a contact."""
    
    html = render_form_email_html(
        to_name=to_name,
        outlet_name=outlet_name,
        form_name=form_name,
        period_label=period_label,
        form_url=form_url,
        qr_image_base64=qr_image_base64,
        custom_message=custom_message
    )
    
    params = {
        "from": SENDER,
        "to": [to_email],
        "subject": f"EHC Form: {form_name} - {outlet_name} ({period_label})",
        "html": html,
    }
    
    response = resend.Emails.send(params)
    return response


def render_form_email_html(**kwargs) -> str:
    """Render the HTML email template for form distribution."""
    # Simple HTML template with inline styles (email-safe)
    # Includes: greeting, form name, outlet, period, QR code image,
    # direct link button, custom message if provided
    ...
```

### 5.3 Email Template

Clean, simple HTML email (inline CSS for email client compatibility):

- RestauranTek header/logo
- "Hi {name},"
- "Your {form_name} for {outlet_name} is ready for {period_label}."
- Custom message (if provided)
- QR code image (inline base64 or CID attachment)
- "Open Form" button linking directly to the form URL
- Footer with "Sent by RestauranTek EHC"

No fancy email template framework needed — a single HTML string with inline styles works fine for transactional email.

---

## 6. Frontend Components

### 6.1 Settings Tab

**New tab** in the EHC page, alongside Dashboard / Points / Records / Forms.

```
frontend/src/pages/EHC/tabs/Settings.jsx
```

Contains three sections, each collapsible or as sub-tabs:

**Outlets Section:**
- Table: Abbreviation | Name | Type | Book Type | Active | Actions
- "Add Outlet" button
- Inline editing (click to edit, blur to save — same pattern as other inline edits in EHC)
- Drag handle for reorder (or simple up/down arrows)

**Contacts Section:**
- Table: Name | Email | Title | Outlets | Actions
- Outlets column shows pill/chips with primary indicator
- "Add Contact" button opens a modal
- Contact modal: name, email, title fields + outlet assignment with checkboxes and primary toggle

**Email Section:**
- Status indicator: "Email configured" / "Email not configured" (checks if RESEND_API_KEY is set)
- "Send Test Email" button
- Last 10 sent emails from `ehc_email_log` (mini log view)

### 6.2 Integration with Template Deploy

The `CreateFromTemplateModal.jsx` (from checklist forms plan) needs to be updated:

**Current plan:** Admin types outlet names as freeform text in a pill selector.  
**Updated:** Admin selects from configured EHC outlets (loaded from `/api/ehc/settings/outlets`). Only active outlets appear.

**After deploy, add option:** "Email QR codes to contacts?" checkbox. If checked, triggers the email send endpoint for all created form links.

### 6.3 Forms Tab Email Button

Add a "Send QR" action button per form link in the Forms tab. Clicking it:
1. Looks up the primary contact for that form's outlet
2. Shows a confirmation: "Send to Juan Garcia (jgarcia@fairmont.com)?"
3. Sends and shows success/failure toast

Also add a bulk action: select multiple form links → "Email QR to all" → sends to each outlet's primary contact.

---

## 7. Seed Data

### 7.1 SCP Outlets

Seed the 13 known outlets for the fairmont-scp organization:

```python
SCP_OUTLETS = [
    {"abbreviation": "MK",          "name": "Main Kitchen",                    "outlet_type": "production_kitchen", "book_type": "outlet",  "sort_order": 1},
    {"abbreviation": "GM",          "name": "Garde Manger",                    "outlet_type": "production_kitchen", "book_type": "outlet",  "sort_order": 2},
    {"abbreviation": "Pastry",      "name": "Pastry",                          "outlet_type": "production_kitchen", "book_type": "outlet",  "sort_order": 3},
    {"abbreviation": "Dish",        "name": "The Dish (Employee Cafe)",        "outlet_type": "support",            "book_type": "outlet",  "sort_order": 4},
    {"abbreviation": "Receiving",   "name": "Receiving",                       "outlet_type": "support",            "book_type": "outlet",  "sort_order": 5},
    {"abbreviation": "Stewarding",  "name": "Stewarding",                      "outlet_type": "support",            "book_type": "outlet",  "sort_order": 6},
    {"abbreviation": "Casual",      "name": "Casual Dining",                   "outlet_type": "restaurant",         "book_type": "outlet",  "sort_order": 7},
    {"abbreviation": "Toro",        "name": "Toro Latin Restaurant & Rum Bar", "outlet_type": "restaurant",         "book_type": "outlet",  "sort_order": 8},
    {"abbreviation": "LaHa",        "name": "La Hacienda",                     "outlet_type": "restaurant",         "book_type": "outlet",  "sort_order": 9},
    {"abbreviation": "BSAZ",        "name": "Bourbon Steak Arizona",           "outlet_type": "restaurant",         "book_type": "outlet",  "sort_order": 10},
    {"abbreviation": "Gold",        "name": "Fairmont Gold Lounge",            "outlet_type": "lounge",             "book_type": "outlet",  "sort_order": 11},
    {"abbreviation": "Plaza",       "name": "Plaza Bar",                       "outlet_type": "bar",                "book_type": "outlet",  "sort_order": 12},
    {"abbreviation": "Pools",       "name": "Pool Service",                    "outlet_type": "bar",                "book_type": "outlet",  "sort_order": 13},
    {"abbreviation": "Palomino",    "name": "Palomino",                        "outlet_type": "lounge",             "book_type": "outlet",  "sort_order": 14},
    {"abbreviation": "Starbucks",   "name": "Starbucks",                       "outlet_type": "franchise",          "book_type": "outlet",  "sort_order": 15},
]
```

**Note:** Outlet count is 15 (not 13 from original planning doc). "Dish" is the employee cafe, and "Receiving" and "Stewarding" are separate areas. "Coffee Shop" from the thermometer register = Starbucks.

### 7.2 Contacts

NOT seeded — Mike adds contacts manually through the UI. Contact data (names, emails, titles) shouldn't be hardcoded in migrations.

---

## 8. Phased Build

### Phase 1: Outlets (Foundation)
- [ ] Alembic migration: `ehc_outlet` table
- [ ] Outlet CRUD endpoints
- [ ] Seed SCP outlets
- [ ] Settings tab shell with Outlets section UI
- [ ] Inline editing, add/delete, reorder

### Phase 2: Contacts
- [ ] Alembic migration: `ehc_contact` and `ehc_contact_outlet` tables
- [ ] Contact CRUD endpoints with outlet assignment
- [ ] Contacts section UI in Settings tab
- [ ] Contact modal with outlet assignment checkboxes + primary toggle

### Phase 3: Email (Resend)
- [ ] `pip install resend`, add to requirements.txt
- [ ] `api/app/utils/email.py` — send utility + HTML template
- [ ] Alembic migration: `ehc_email_log` table
- [ ] Email send endpoint
- [ ] Test email endpoint
- [ ] Email section in Settings tab (status + test button)
- [ ] Wire domain verification (DNS records for restaurantek.io)

### Phase 4: Integration
- [ ] Update `CreateFromTemplateModal` to use `ehc_outlet` records instead of freeform text
- [ ] Add "Email QR to contacts" option in deploy flow
- [ ] Add per-form "Send QR" button in Forms tab
- [ ] Bulk email action in Forms tab
- [ ] Email log mini-view in Settings

---

## 9. Design Decisions

1. **EHC outlets separate from platform outlets:** Avoids coupling EHC configuration to the broader platform outlet structure. Nullable `outlet_id` FK for future reconciliation. EHC may have areas (Receiving, Stewarding) that aren't traditional "outlets" in the food costing sense.

2. **Contacts are not users (yet):** Lightweight name/email/title records. Nullable `user_id` FK populated later when people get RestauranTek accounts. This means the chef scanning a QR doesn't need an account — they fill out the form anonymously with their signature.

3. **Resend for email:** Simple API, generous free tier (3,000/month), easy domain verification, no AWS/Microsoft dependency. Emails come from restaurantek.io which is portable across properties.

4. **Email log for auditability:** Every sent email is logged with recipient, form link, Resend message ID, and status. Important for "did Juan get the April QR?" conversations.

5. **Primary contact per outlet:** When deploying forms, the system auto-addresses emails to the primary contact. Non-primary contacts can still be CC'd or emailed manually. Keeps the default flow simple.

6. **No responsibility codes for now:** The existing codes (MM, CF, CM, etc.) are acknowledged as incorrect. The contact→outlet assignment replaces their function — you know who's responsible for Toro because they're assigned to Toro, not because they have a "CF" code.

---

## 10. Files to Create/Modify

### Backend (New)
- `alembic/versions/XXX_add_ehc_settings_tables.py` — outlets, contacts, contact_outlet, email_log
- `api/app/routers/ehc_settings.py` — outlet and contact CRUD endpoints
- `api/app/utils/email.py` — Resend integration + HTML template

### Backend (Modify)
- `api/app/main.py` — register ehc_settings router
- `requirements.txt` — add `resend`

### Frontend (New)
- `frontend/src/pages/EHC/tabs/Settings.jsx` — Settings tab component
- `frontend/src/pages/EHC/modals/ContactModal.jsx` — Contact add/edit modal

### Frontend (Modify)
- `frontend/src/pages/EHC/EHC.jsx` — Add Settings tab to tab navigation
- `frontend/src/pages/EHC/modals/CreateFromTemplateModal.jsx` — Use outlet records instead of freeform
- `frontend/src/pages/EHC/tabs/Forms.jsx` — Email action buttons

---

## 11. Open Questions — Resolved

1. **Receiving & Stewarding:** ✅ They are separate EHC outlets. "Dish" is the name of the employee cafe, not a catch-all for dishwashing/stewarding. Outlet list updated to 15 areas.

2. **Coffee Shop:** ✅ Same as Starbucks. Seed uses "Starbucks."

3. **Multiple contacts per outlet:** ✅ One primary contact per outlet. Secondary contacts are nice-to-have but not required for Phase 1. Schema supports multiple contacts per outlet with `is_primary` flag.

4. **Email reply-to:** ✅ No reply — emails sent from `noreply@restaurantek.io` with no reply-to header.

5. **Contact emails:** ✅ All Fairmont corporate email (@fairmont.com). Note: corporate email filters can be aggressive — may need to whitelist restaurantek.io sending domain with IT, or contacts may need to check spam initially until the domain builds reputation.
