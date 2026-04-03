# EHC Digital Forms — Planning Document

> **Project:** RestauranTek  
> **Feature:** EHC Digital Forms (Tokenized Public Signature Collection)  
> **Date:** April 2, 2026  
> **Property:** Fairmont Scottsdale Princess (fairmont-scp)  
> **Stack:** FastAPI + React, PostgreSQL (Render prod / Unraid dev), Alembic migrations  
> **Dependencies:** `qrcode`, `reportlab`, `Pillow` (Python); HTML5 Canvas signature pad (frontend)

---

## 1. What This Feature Does

Several EHC records require staff signatures — declarations, team rosters, training attendance, safety meeting sign-offs. Today these are printed, signed by hand, and filed physically. This feature replaces that workflow:

1. Admin generates a **tokenized public link** from any EHC record submission
2. Staff scan a **QR code** or tap a link — no login required
3. They see the form content, type their name, sign on their phone screen, and submit
4. Responses are tracked in real time (who's signed, who's missing)
5. A **PDF matching the original EHC template** is auto-generated and attached to the submission

This eliminates printing, chasing signatures, scanning, and manual filing. The auditor sees a familiar document format, but it was created digitally with timestamped signatures.

---

## 2. Form Types

The system supports multiple form patterns through a configurable `form_type` field. Initial implementation covers two types; the architecture supports future expansion.

### 2.1 `staff_declaration` (Record 11)

**Use case:** 50–100 staff must read and acknowledge a standard food safety declaration annually.

**Form behavior:**
- Displays the full 23-point declaration text (static content, stored in form config)
- Staff member enters their name, reads the declaration, signs on a signature pad
- Duplicate prevention: if a name closely matches an existing response, show confirmation ("You've already signed on [date]. Sign again?")
- Admin sees a live tracker: 67/95 complete, with a list of who's missing

**PDF output:** Summary format — header text + table of (Name, Date, Signature image) for all respondents. This is better evidence than 95 individual printed forms.

### 2.2 `team_roster` (Record 35)

**Use case:** 5–8 food safety team members sign a team record with pre-filled names, positions, and departments.

**Form behavior:**
- Admin pre-configures team members (name, position, department, date approved) when generating the link
- Form displays the full team table; each person finds their row and signs
- Optionally: a person can add themselves if they're not listed (admin approval required)
- Shows completion status inline (signed / awaiting)

**PDF output:** Matches the original Record 35 template — Fairmont header, standard intro text, table with Date Approved | Name | Position | Department | Signature columns. Signature images are placed into the signature column.

### 2.3 `simple_signoff` (General Purpose)

**Use case:** Any record where admin wants to upload an existing PDF document and collect a signature from each respondent.

**Form behavior:**
- Admin uploads a PDF document when creating the form link
- Staff view the embedded PDF, enter their name, and sign
- Collected signatures are tracked against the original PDF

**PDF output:** Original uploaded PDF with an appended signature page showing all collected signatures with timestamps.

### 2.4 `table_signoff` (Configurable Table Forms)

**Use case:** Custom table-based sign-off forms where admin defines columns dynamically — similar to Record 35 but without hardcoding each form structure.

**Form behavior:**
- Admin configures column definitions (name, type: text/date/signature)
- Admin optionally pre-fills rows (e.g., staff names, positions)
- Staff view the table, find their row (or add one), and sign
- Progress tracked by row completion

**Config structure:**
```json
{
  "columns": [
    { "key": "name", "label": "Name", "type": "text", "required": true },
    { "key": "position", "label": "Position", "type": "text" },
    { "key": "signature", "label": "Signature", "type": "signature", "required": true }
  ],
  "rows": [
    { "name": "John Smith", "position": "Line Cook" }
  ],
  "intro_text": "Please sign to confirm your attendance.",
  "property_name": "Fairmont Scottsdale Princess"
}
```

**PDF output:** Table matching the configured columns with signature images in the signature column.

### 2.5 Future: `checklist` (Record 20, etc.)

**Use case:** Multi-section checklists with checkboxes, text fields, and corrective action areas.

**Form behavior:** Dynamic form rendered from a `fields` config array. Each field has a type (checkbox, text, textarea, select, signature), label, and optional validation. Supports sections/headers for multi-page checklists.

**Not in initial build** — but the data model and form link infrastructure supports it. Adding a new form type means:
1. Add a new config schema
2. Add a React form renderer component
3. Add a PDF template

---

## 3. Data Model

Two new tables. Uses existing RestauranTek conventions: auto-increment integer PKs, `organization_id` scoping, `created_at`/`updated_at` timestamps. Prefix: `ehc_`.

### 3.1 `ehc_form_link`

One per generated form link. Tied to a specific record submission within an audit cycle.

```
id                  SERIAL PK
organization_id     INTEGER FK → organizations
audit_cycle_id      INTEGER FK → ehc_audit_cycle
submission_id       INTEGER FK → ehc_record_submission (nullable — can be linked after creation)
record_id           INTEGER FK → ehc_record
token               VARCHAR(64) UNIQUE NOT NULL    -- crypto-random, URL-safe
form_type           VARCHAR(50) NOT NULL           -- 'staff_declaration', 'team_roster', 'checklist'
title               VARCHAR(255)                   -- Display title: "Food Safety Declaration — EHC 2026"
config              JSONB NOT NULL                 -- Form-specific configuration (see §3.3)
is_active           BOOLEAN DEFAULT true           -- Can be deactivated to revoke access
expires_at          TIMESTAMP                      -- NULL = no expiry
expected_responses  INTEGER                        -- NULL or target count (e.g., 95 for Record 11)
created_by          INTEGER FK → users
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()
```

**Notes:**
- `token` is generated via `secrets.token_urlsafe(32)` — produces a 43-character URL-safe string
- `submission_id` is nullable so a link can be created before the submission exists, or linked to multiple submissions
- `record_id` is the master record reference (persists across cycles)
- `organization_id` is denormalized for query efficiency and tenant isolation

### 3.2 `ehc_form_response`

One per individual signature/submission against a form link.

```
id                  SERIAL PK
form_link_id        INTEGER FK → ehc_form_link
respondent_name     VARCHAR(255) NOT NULL
respondent_role     VARCHAR(100)           -- Position/title (optional)
respondent_dept     VARCHAR(100)           -- Department (optional)
response_data       JSONB                  -- Form-specific answers (acknowledgment, checklist fields, etc.)
signature_data      TEXT                   -- Base64 PNG from canvas signature pad
submitted_at        TIMESTAMP DEFAULT NOW()
ip_address          VARCHAR(45)            -- For audit trail (optional)
user_agent          VARCHAR(500)           -- Device info for audit trail (optional)
```

**Notes:**
- No FK to `users` — respondents are unauthenticated
- `signature_data` stores the full base64-encoded PNG. Typical phone signatures are 5–15KB encoded
- `response_data` holds form-type-specific fields (see §3.3)
- `ip_address` and `user_agent` provide a lightweight audit trail without requiring authentication

### 3.3 Config & Response Schemas

#### `staff_declaration` config:

```json
{
  "form_type": "staff_declaration",
  "document_ref": "record_11",
  "property_name": "Fairmont Scottsdale Princess",
  "cycle_year": 2026
}
```

The declaration content (intro text, 23 numbered items) is NOT stored in config. It lives as a **static document template** — see §6.3 for details. The `document_ref` field tells the form renderer which template to load. Config only holds form *behavior* settings (property, cycle year, expected count). Document *content* is a separate concern.

#### `staff_declaration` response_data:

```json
{
  "acknowledged": true,
  "scrolled_to_bottom": true
}
```

#### `team_roster` config:

```json
{
  "form_type": "team_roster",
  "team_members": [
    {
      "name": "John Smith",
      "position": "Executive Chef",
      "department": "Culinary",
      "date_approved": "2026-01-15"
    },
    {
      "name": "Jane Doe",
      "position": "F&B Operations Manager",
      "department": "F&B",
      "date_approved": "2026-01-15"
    }
  ],
  "allow_additions": false,
  "property_name": "Fairmont Scottsdale Princess",
  "cycle_year": 2026
}
```

#### `team_roster` response_data:

```json
{
  "team_member_index": 0,
  "date_approved": "2026-01-15"
}
```

#### Future `checklist` config (for reference, not initial build):

```json
{
  "form_type": "checklist",
  "sections": [
    {
      "title": "Kitchen Audit Checklist",
      "fields": [
        { "id": "floors_clean", "type": "checkbox", "label": "Floors clean and in good condition" },
        { "id": "walls_clean", "type": "checkbox", "label": "Walls clean and in good condition" },
        { "id": "corrective_action", "type": "textarea", "label": "Corrective action required", "required_if": "any_unchecked" }
      ]
    }
  ]
}
```

---

## 4. API Routes

### 4.1 Public Endpoints (No Authentication)

These are accessed by staff scanning QR codes. No JWT required. Tenant isolation is enforced by the token itself — each token maps to a specific org/cycle/record.

```
GET  /api/ehc/forms/{token}
```
Returns form config, title, existing responses (names + signed status, NOT signature image data), and metadata. Used by the public form page to render the form.

**Response shape:**
```json
{
  "title": "Food Safety Declaration — EHC 2026",
  "form_type": "staff_declaration",
  "property_name": "Fairmont Scottsdale Princess",
  "config": { ... },
  "responses": [
    { "respondent_name": "John Smith", "submitted_at": "2026-03-15T10:30:00Z" }
  ],
  "total_responses": 45,
  "expected_responses": 95,
  "is_active": true,
  "expires_at": null
}
```

**Error cases:**
- Token not found → 404
- Token expired → 410 Gone with message "This form has expired"
- Token deactivated → 410 Gone with message "This form is no longer accepting responses"

```
POST /api/ehc/forms/{token}/respond
```
Submit a form response with signature.

**Request body:**
```json
{
  "respondent_name": "Maria Garcia",
  "respondent_role": "Line Cook",
  "respondent_dept": "Culinary",
  "response_data": { "acknowledged": true },
  "signature_data": "data:image/png;base64,iVBORw0KGgo..."
}
```

**Validation:**
- `respondent_name` required, min 2 characters
- `signature_data` required, must be valid base64 image, max 50KB decoded
- For `team_roster`: `response_data.team_member_index` must reference a valid team member
- Duplicate check: if name matches existing response (case-insensitive, trimmed), return 409 with the existing response date. Frontend shows "You already signed on [date]. Submit again?" confirmation, and can re-POST with `?force=true` to replace.

**Response:** 201 Created with the response object.

**Side effect:** After successful submission, check if the form link's expected_responses count is met. If so, auto-trigger PDF generation and attach to the linked submission (async/background if possible, sync is fine for MVP).

### 4.2 Authenticated Endpoints (Admin)

These require JWT authentication. Organization-scoped as per existing EHC patterns.

```
POST /api/ehc/submissions/{submission_id}/generate-form-link
```
Create a form link for a given submission. Admin provides form type and config.

**Request body:**
```json
{
  "form_type": "staff_declaration",
  "title": "Food Safety Declaration — EHC 2026",
  "config": { ... },
  "expected_responses": 95,
  "expires_at": null
}
```

**Response:** The created form link with token, plus a pre-generated QR code as base64 PNG.

```
GET /api/ehc/submissions/{submission_id}/form-links
```
List all form links for a submission (usually just one, but supports multiple).

```
GET /api/ehc/form-links/{link_id}/responses
```
Full response list including signature data (for admin review and PDF generation).

```
PATCH /api/ehc/form-links/{link_id}
```
Update form link: deactivate, change expiry, update config (e.g., add team members).

```
DELETE /api/ehc/form-links/{link_id}
```
Permanently delete a form link and all its responses. Use when a form was created in error or is no longer needed. For temporary suspension, use PATCH to set `is_active = false` instead.

```
DELETE /api/ehc/form-links/{link_id}/responses/{response_id}
```
Remove a response (e.g., staff member left the property, need to re-collect).

```
POST /api/ehc/form-links/{link_id}/generate-pdf
```
Generate the completed PDF and attach it to the linked submission. Returns the PDF file path. Also sets `submission.file_path` and `submission.original_filename`.

```
GET /api/ehc/form-links/{link_id}/qr
```
Returns the QR code image (PNG) for the form link URL. Useful for re-downloading without regenerating.

```
GET /api/ehc/form-links/{link_id}/flyer
```
Returns a printable PDF flyer containing: QR code, form title, brief instructions ("Scan with your phone camera to complete this form"), cycle year, and property name. Ready to print and post.

---

## 5. QR Code & Link Distribution

### 5.1 URL Structure

Form links follow the pattern:

```
https://{frontend_domain}/form/{token}
```

Examples:
- Dev: `http://localhost:5173/form/abc123def456`
- Prod: `https://restaurantek.example.com/form/abc123def456`

The frontend domain is configured via an environment variable `FRONTEND_URL` (already implied by the CORS config). The QR code encodes this full URL.

### 5.2 QR Code Generation

Backend generates QR codes using the `qrcode` Python library:

```python
import qrcode
from io import BytesIO
import base64

def generate_qr_code(url: str) -> str:
    """Generate QR code as base64 PNG string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()
```

QR is generated on form link creation and can be regenerated on demand via the `/qr` endpoint. Not stored in the database — generated from the token + frontend URL each time.

### 5.3 Distribution Methods

| Method | Best For | How |
|--------|----------|-----|
| **QR flyer posted in kitchen** | Record 11 (mass signatures) | Download flyer PDF from RestauranTek, print, post in break room / kitchen office |
| **QR projected at team meeting** | Record 11 (batch collection) | Display QR on screen, staff scan during pre-shift or safety meeting |
| **Direct link via text/chat** | Record 35 (small team) | Copy link from share modal, paste in WhatsApp/Teams/SMS |
| **Email with link** | Office-based staff | Copy link, include in email body |
| **QR on notice board** | Record 11, ongoing | Permanent posting for staff who weren't at the meeting |

### 5.4 Share Modal UI

When admin clicks "Generate Form Link" on a submission, the modal shows:

1. **Link URL** — full URL with a copy-to-clipboard button
2. **QR Code** — displayed inline, with a download button (PNG)
3. **Download Flyer** — button to download a printable PDF with QR + instructions
4. **Settings** — expiry date picker, expected response count, active/inactive toggle
5. **Live status** — "12 of 95 responses collected" with a progress bar

For `team_roster` type, the modal also includes the team member configuration table (add/remove/edit members before generating).

---

## 6. Frontend: Public Form Page

### 6.1 Route

```
/form/:token
```

This route does NOT require authentication. It lives outside the app's auth wrapper. The component fetches form data from `GET /api/ehc/forms/{token}` and renders based on `form_type`.

### 6.2 UX Flow — Staff Declaration (Record 11)

Standard e-signature scroll-to-sign pattern (DocuSign, HelloSign, etc.):

1. **Landing:** Fairmont-branded header, form title ("Food Safety Declaration — EHC 2026"), property name
2. **Document body:** The full Record 11 content rendered as formatted HTML — intro paragraphs followed by all 23 numbered points. This is the actual document they're signing. Styled to feel like a formal document (clean serif or sans-serif font, proper spacing, numbered list)
3. **Scroll gate:** The sign-off section (step 4–6) is **disabled/greyed out until the user scrolls to the bottom** of the declaration text. A subtle prompt at the bottom of the document area: "↓ Scroll to read the full declaration before signing." Once they've scrolled through, the sign-off section activates. This is standard practice for e-signed documents and provides evidence of acknowledgment
4. **Acknowledgment checkbox:** "I have read and understand the above food safety standards" — appears below the document, enabled only after scroll completion
5. **Name field:** Text input for full name
6. **Signature pad:** HTML5 canvas area (sized for thumb signing on mobile). Clear button to retry
7. **Submit button:** Disabled until all three conditions met: scrolled to bottom + checkbox checked + name entered + signature drawn
8. **Success screen:** "Thank you, [name]. Your declaration has been recorded." with a timestamp
9. **Already signed:** If name matches existing response (checked after name field blur), show inline message: "A response for [name] was already submitted on [date]. Submitting again will replace it." No blocking modal — just inform and allow

**Mobile-first:** Full-width layout, large touch targets, signature pad minimum 300×150px responsive. No horizontal scrolling. Document text is the primary content — no competing UI elements above the fold.

### 6.3 Static Document Templates

Declaration content is stored as **static React components or JSON template files**, not in the form link config. This keeps document content separate from form behavior config and provides a single source of truth.

**File structure:**

```
frontend/src/pages/EHC/forms/
├── FormPage.jsx                    # Route component, fetches token, renders form type
├── StaffDeclarationForm.jsx        # Record 11 form with scroll-to-sign
├── TeamRosterForm.jsx              # Record 35 form with team table
├── SignaturePad.jsx                # Reusable canvas signature component
├── templates/
│   ├── record_11.js                # Declaration content (intro text + 23 items)
│   └── record_35.js                # Team record header text
└── FormSuccess.jsx                 # Shared success state component
```

**Example template file (`templates/record_11.js`):**

```javascript
export const RECORD_11 = {
  title: "Record 11: Initial Staff Food Safety Information Declaration",
  version: "Fairmont Safe Food and Hygiene Standards Manual — Version 3",
  date: "Document Dated — May 2024",
  intro: [
    "The hotel is committed to ensuring that the foods that are purchased, accepted, stored, prepared and served are safe & wholesome.",
    "To support the development & implementation of the hotel's food safety system based on HACCP principles and as a follow up to the initial food safety training that the hotel carried out, the Executive Chef is to provide a reminder sheet for all staff.",
    "If there is anything explained to you that you do not understand, please ask. Our system in food safety will only work if we have the commitment from ALL of our staff."
  ],
  items: [
    "Limit the amount of jewellery to be worn during the preparation of food.",
    "Ensure that you are wearing suitable protective head covering when preparing foods.",
    "Ensure that your clothing and footwear are clean daily.",
    // ... all 23 items
  ]
};
```

**Why this approach:**
- Document content updates are a code change (version-controlled, reviewable), not a database edit
- The same template is used by both the form renderer AND the PDF generator (backend has a parallel Python version or reads from a shared JSON file)
- If Fairmont updates the manual (e.g., Version 4), you update one template file
- No risk of config JSON corruption breaking the document display

**Backend parallel:** For PDF generation, the same content lives as a Python dict or JSON file in `api/app/services/ehc_templates/`. Both frontend and backend reference the same document version.

### 6.4 UX Flow — Team Roster (Record 35)

1. **Landing:** Fairmont-branded header, form title, standard intro text ("The following is an up to date list of the hotel's food safety team...")
2. **Team table:** Each row shows name, position, department, date approved. Signed members show a green checkmark and signed date. Unsigned members show a "Sign" button
3. **Sign flow:** Tapping "Sign" on your row expands a signature pad section below that row (inline, not modal — keeps context visible)
4. **Signature pad:** Same reusable component as Record 11 — canvas with clear button
5. **Submit:** Captures signature for that specific team member, row updates immediately
6. **Completion:** When all team members have signed, a "All signatures collected" banner appears

### 6.5 Signature Pad Implementation

Use HTML5 Canvas with touch event handling. No external library needed — the implementation is straightforward:

```jsx
// Core signature pad logic (simplified)
const canvas = useRef(null);
const [isDrawing, setIsDrawing] = useState(false);

const getPos = (e) => {
  const rect = canvas.current.getBoundingClientRect();
  const touch = e.touches ? e.touches[0] : e;
  return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
};

// Touch/mouse event handlers for drawing
// Export: canvas.current.toDataURL('image/png')
```

Key considerations:
- Prevent page scroll while signing (touch-action: none on canvas)
- White background for clean PNG export
- Line width 2–3px for natural feel
- Clear button resets canvas
- Minimum stroke length validation (prevent accidental taps from counting as signatures)

### 6.6 Branding

The public form page should feel official but lightweight:
- Fairmont logo at top (loaded from a static asset or config)
- Clean white/light background (not the dark RestauranTek admin theme)
- Property name and cycle year displayed
- Minimal footer: "Powered by RestauranTek" (small, unobtrusive)

The form page should NOT look like the RestauranTek admin UI. It's a public-facing form that kitchen staff see on their phones — it needs to feel like a quick, trustworthy task, not a software product.

---

## 7. PDF Generation

### 7.1 Technology

ReportLab (Python). Already referenced in the project's broader tooling context. Generates PDFs programmatically with precise layout control.

### 7.2 Record 11 — Staff Declaration Summary PDF

**Layout:**

```
┌────────────────────────────────────────────────────┐
│            [Fairmont Logo]                         │
│                                                    │
│  Record 11: Initial Staff Food Safety              │
│  Information Declaration                           │
│                                                    │
│  Fairmont Scottsdale Princess — EHC 2026           │
│                                                    │
│  The following staff members have read and          │
│  acknowledged the food safety information           │
│  declaration for the current audit cycle.           │
│                                                    │
│  ┌──────────────────┬────────────┬─────────────┐   │
│  │ Name             │ Date       │ Signature   │   │
│  ├──────────────────┼────────────┼─────────────┤   │
│  │ Maria Garcia     │ 03/15/2026 │ [sig img]   │   │
│  │ John Smith       │ 03/15/2026 │ [sig img]   │   │
│  │ ...              │ ...        │ ...         │   │
│  └──────────────────┴────────────┴─────────────┘   │
│                                                    │
│  Total: 95 of 95 staff acknowledged                │
│  Generated: 04/02/2026 14:30 MST                   │
│                                                    │
│  ─────────────────────────────────────────────     │
│  Fairmont Safe Food and Hygiene Standards Manual   │
│  Version 3 — Document Dated May 2024     Page X    │
└────────────────────────────────────────────────────┘
```

**Notes:**
- Signature images rendered at approximately 100×40px in the table cells
- Table auto-paginates if more than ~25 rows per page
- Footer matches the original document footer format
- Page numbering: "Page X of Y"

### 7.3 Record 35 — Food Safety Team Record PDF

**Layout matches the original template exactly:**

```
┌────────────────────────────────────────────────────┐
│            [Fairmont Logo]                         │
│                                                    │
│  Record 35: Food Safety Team Record                │
│                                                    │
│  The following is an up to date list of the        │
│  hotel's food safety team. A copy of this record   │
│  will be made available on the hotel's food        │
│  safety noticeboard.                               │
│                                                    │
│  ┌──────────┬───────────┬──────────┬──────────┬────────────┐
│  │ Date     │ Name      │ Position │ Dept     │ Signature  │
│  │ approved │           │          │          │            │
│  ├──────────┼───────────┼──────────┼──────────┼────────────┤
│  │ 01/15/26 │ John Smith│ Exec Chef│ Culinary │ [sig img]  │
│  │ 01/15/26 │ Jane Doe  │ F&B Ops  │ F&B      │ [sig img]  │
│  │ ...      │ ...       │ ...      │ ...      │ ...        │
│  └──────────┴───────────┴──────────┴──────────┴────────────┘
│                                                    │
│  ─────────────────────────────────────────────     │
│  Fairmont Safe Food and Hygiene Standards Manual   │
│  Version 3 — Document Dated May 2024     Page 50   │
└────────────────────────────────────────────────────┘
```

**Notes:**
- 5 columns matching the original template
- Unsigned rows show empty signature cell (or "Awaiting signature" in grey if desired)
- Generated PDF replaces the need to ever print, sign, and scan the original

### 7.4 PDF Attachment Flow

When PDF is generated (manually via admin button or auto-triggered on completion):

1. PDF is saved to `uploads/ehc/{org_id}/{year}/forms/record_{record_number}_{token_prefix}.pdf`
2. `ehc_record_submission.file_path` is updated to point to the generated PDF
3. `ehc_record_submission.original_filename` is set to a readable name: `Record_35_Food_Safety_Team_2026.pdf`
4. Submission status can optionally auto-advance to `submitted` if all expected responses are collected

This integrates with the existing file upload/download system — the generated PDF appears in the same place as any manually uploaded file.

### 7.5 Flyer PDF

Simple single-page PDF for printing and posting:

```
┌────────────────────────────────────────────────────┐
│            [Fairmont Logo]                         │
│                                                    │
│        FOOD SAFETY DECLARATION                     │
│              EHC 2026                              │
│                                                    │
│  ┌────────────────────────────────────┐            │
│  │                                    │            │
│  │         [QR CODE - large]          │            │
│  │           ~250×250px               │            │
│  │                                    │            │
│  └────────────────────────────────────┘            │
│                                                    │
│     Scan with your phone camera                    │
│     to complete your annual food                   │
│     safety declaration.                            │
│                                                    │
│     Takes less than 2 minutes.                     │
│                                                    │
│  ─────────────────────────────────────────────     │
│  Fairmont Scottsdale Princess                      │
└────────────────────────────────────────────────────┘
```

---

## 8. Security Considerations

### 8.1 Token Security

- Tokens are 43-character cryptographically random strings (256 bits of entropy via `secrets.token_urlsafe(32)`)
- Tokens are not JWTs — they are opaque lookup keys. No data is encoded in the token itself
- Rate limiting on public endpoints: 30 requests per minute per IP on `GET /forms/{token}`, 10 per minute on `POST /forms/{token}/respond`
- Tokens can be deactivated instantly by setting `is_active = false`
- Optional expiry date for time-limited collection periods

### 8.2 Data Protection

- Signature data is stored as base64 in the database, not as files on disk
- Public `GET /forms/{token}` returns respondent names and submission dates but NOT signature image data
- Signature images are only accessible via authenticated admin endpoints
- No PII beyond name and signature is collected (no email, phone, employee ID)
- IP address and user agent are stored for audit trail but not displayed to other respondents

### 8.3 Abuse Prevention

- Form responses require a minimum name length (2 characters)
- Signature validation: minimum stroke length to prevent empty/accidental submissions
- Duplicate name detection with force-override option (prevents accidental double-submissions without blocking legitimate corrections)
- Max response limit: if `expected_responses` is set, reject submissions beyond 2× that count (prevents flooding)
- CORS: public form endpoints should allow `*` origins (staff phones won't be on the same domain)

---

## 9. Integration with Existing EHC Module

### 9.1 Submission Detail Enhancement

The existing submission detail view (expanded row in Records tab) adds:

- **"Generate Form Link" button** — appears for records flagged as form-eligible (see §9.2)
- **Form link status indicator** — shows "Form link active: 67/95 responses" or "No form link" 
- **"View Responses" button** — opens a modal/drawer with the full response list
- **"Generate PDF" button** — creates and attaches the completed PDF
- **"Download Flyer" button** — when a form link is active

### 9.2 Form-Eligible Records

Not every record type benefits from digital forms. The initial form-eligible records:

| Record | Name | Form Type | Expected Responses |
|--------|------|-----------|-------------------|
| 11 | Staff Food Safety Declaration | `staff_declaration` | ~50–100 (configurable) |
| 35 | Food Safety Team Record | `team_roster` | ~5–8 (from config) |
| 23 | Training Records | `staff_declaration` (variant) | Varies per session |
| 30 | Guest-Supplied Food Indemnity | Future: `simple_form` | As needed |
| 30b | Baby Milk Reheating Indemnity | Future: `simple_form` | As needed |

The `ehc_record` table does NOT need a new column for this. Form eligibility is determined by the presence of an `ehc_form_link` for that record's submission — any record can have a form link generated. The UI can suggest form types based on `record_number` but doesn't enforce it.

### 9.3 Auto-Completion Cascade

When all expected responses are collected for a form link:

1. PDF is auto-generated and attached to the submission
2. Submission `is_physical` remains false (it's digital-native)
3. Submission status advances to `submitted`
4. Admin still needs to manually approve (review the PDF, verify it looks correct)
5. Approval triggers the existing cascade: submission approved → audit point evidence_collected → section progress updates → dashboard updates

This preserves the existing approval workflow — no auto-approval. The admin retains control.

---

## 10. Environment & Configuration

### 10.1 New Environment Variables

```
FRONTEND_URL=https://restaurantek.example.com    # Used for QR code URL generation
FORM_LINK_DEFAULT_EXPIRY_DAYS=365                # Default expiry (NULL = no expiry)
FORM_RATE_LIMIT_PER_MINUTE=30                    # Public endpoint rate limit (if implemented)
```

### 10.2 New Python Dependencies

```
qrcode[pil]>=7.4       # QR code generation (uses Pillow for image output)
reportlab>=4.0          # PDF generation
Pillow>=10.0            # Image handling (QR codes, signature image processing)
```

These should be added to `requirements.txt`. All are pure Python, no system-level dependencies.

### 10.3 File Storage

Generated PDFs follow existing upload conventions:
```
uploads/ehc/{org_id}/{year}/forms/record_{record_number}_{token_prefix}.pdf
```

QR codes and flyers are generated on-the-fly, not stored on disk.

---

## 11. Phased Build Plan

### Phase 1: Data Foundation + Public API
- Alembic migration for `ehc_form_link` and `ehc_form_response` tables
- Public endpoints: `GET /forms/{token}` and `POST /forms/{token}/respond`
- Admin endpoints: create form link, list form links, list responses
- QR code generation utility function
- Token generation and validation logic
- Duplicate response detection
- **Test with curl/Postman before any UI**

### Phase 2: Public Form UI
- Static document template files (Record 11 content as `templates/record_11.js`, Record 35 header as `templates/record_35.js`)
- New React route `/form/:token` (outside auth wrapper)
- Signature pad component (HTML5 Canvas, mobile-first)
- `staff_declaration` form renderer with scroll-to-sign gate (Record 11)
- `team_roster` form renderer with inline signing (Record 35)
- Success/error/expired states
- Mobile responsive layout with clean branding (light theme, not admin dark theme)

### Phase 3: Admin UI Integration
- Share modal on submission detail (generate link, copy URL, download QR)
- Response tracker view (who's signed, who's missing)
- Form link management (deactivate, update config)
- Link status indicator on submission rows in Records view

### Phase 4: PDF Generation
- ReportLab templates for Record 11 (summary format) and Record 35 (matching original)
- Flyer PDF with QR code for posting
- Auto-attach PDF to submission on completion
- Manual "Generate PDF" button for partial completion

### Phase 5: Polish & Expansion
- Rate limiting on public endpoints
- Email/notification when all responses collected (if notification system exists)
- Additional form types (checklist for Record 20, etc.)
- Year-over-year: clone form link configs from prior cycle
- Bulk form link generation (create links for all form-eligible records in a cycle at once)

---

## 12. Decisions Log

1. **Opaque tokens over JWTs:** Form links use random tokens, not JWTs. Simpler, revocable, no payload to tamper with. The token is just a database lookup key.

2. **No authentication for respondents:** The target users are kitchen staff on their personal phones. Requiring login would kill adoption. The token itself provides access control — you can only submit if you have the link.

3. **Signatures as base64 in database, not files:** Simplifies storage, backup, and PDF generation. Signature PNGs are tiny (5–15KB). At 100 responses, that's ~1.5MB total — trivial for PostgreSQL JSONB or TEXT columns.

4. **Summary PDF for Record 11, template-match PDF for Record 35:** Different approaches for different needs. Record 11 as individual forms would be 100 pages of near-identical documents. A summary table is better evidence and easier for the auditor to review. Record 35 is a small team roster where matching the original template format matters.

5. **Duplicate detection by name, not device/IP:** Staff may sign from different devices or share a phone. Name-based detection with override option is the right tradeoff between preventing accidents and not blocking legitimate use.

6. **Admin approval still required:** Auto-generated PDFs don't auto-approve submissions. The admin reviews the generated document and explicitly approves. This matches the existing EHC workflow where someone verifies records before marking them complete.

7. **Form eligibility not enforced in schema:** Any record can have a form link. The UI suggests appropriate form types, but doesn't prevent an admin from generating a link for any record. This keeps the system flexible for unanticipated use cases.

8. **Flyer PDF as a convenience feature:** Could be skipped in MVP, but the effort is minimal (one ReportLab template) and the practical value is high — a printed QR flyer in the kitchen is the most reliable distribution method for hourly staff.

9. **Document content as static templates, not config JSON:** The Record 11 declaration text (intro + 23 items) lives as a static template file in both frontend and backend, not in the `ehc_form_link.config` field. Config describes form *behavior* (property name, cycle year, expected count). Document *content* is a versioned asset that changes only when Fairmont updates the manual. This follows the standard e-signature pattern: the document is a fixed artifact that gets signed, not a dynamic form. The scroll-to-sign UX reinforces this — the signer reads the actual document content, scrolls to the bottom to prove they've seen it all, then signs.
