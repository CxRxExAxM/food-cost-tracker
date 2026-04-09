"""EHC Digital Forms API Router

Public tokenized form links for signature collection (staff declarations, team rosters).
No authentication required for public endpoints - token provides access control.
"""

from fastapi import APIRouter, HTTPException, Request, Query, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import secrets
import json
import os
import shutil

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user
from ..utils.qr_generator import generate_form_qr, generate_form_url, generate_qr_code_bytes
from ..services.pdf_generator import (
    generate_record_11_pdf,
    generate_record_35_pdf,
    generate_table_signoff_pdf,
    generate_flyer_pdf
)
from fastapi import Depends

# Base upload directory
UPLOAD_DIR = os.environ.get('UPLOAD_DIR', 'uploads')


router = APIRouter(prefix="/ehc", tags=["ehc-forms"])


# ============================================
# Pydantic Models
# ============================================

ALLOWED_FORM_TYPES = ['staff_declaration', 'team_roster', 'simple_signoff', 'table_signoff', 'checklist']


class FormLinkCreate(BaseModel):
    """Create a new form link for signature collection (tied to a submission)."""
    form_type: str  # 'staff_declaration', 'team_roster', 'simple_signoff'
    title: Optional[str] = None
    config: Dict[str, Any] = {}
    expected_responses: Optional[int] = None
    expires_at: Optional[str] = None  # ISO datetime string

    @field_validator('form_type')
    @classmethod
    def validate_form_type(cls, v):
        if v not in ALLOWED_FORM_TYPES:
            raise ValueError(f"form_type must be one of: {', '.join(ALLOWED_FORM_TYPES)}")
        return v


class StandaloneFormLinkCreate(BaseModel):
    """Create a standalone form link (not tied to a specific submission)."""
    form_type: str
    record_id: int  # Which record type this form is for
    title: Optional[str] = None
    config: Dict[str, Any] = {}
    expected_responses: Optional[int] = None
    expires_at: Optional[str] = None
    submission_id: Optional[int] = None  # Optional link to existing submission

    @field_validator('form_type')
    @classmethod
    def validate_form_type(cls, v):
        if v not in ALLOWED_FORM_TYPES:
            raise ValueError(f"form_type must be one of: {', '.join(ALLOWED_FORM_TYPES)}")
        return v


class FormLinkUpdate(BaseModel):
    """Update a form link."""
    title: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    expected_responses: Optional[int] = None
    expires_at: Optional[str] = None


class FormResponse(BaseModel):
    """Submit a form response with signature."""
    respondent_name: str
    respondent_role: Optional[str] = None
    respondent_dept: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    signature_data: str  # Base64 PNG

    @field_validator('respondent_name')
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        return v

    @field_validator('signature_data')
    @classmethod
    def validate_signature(cls, v):
        if not v:
            raise ValueError("Signature is required")
        # Basic validation - should start with data:image/png;base64, or be raw base64
        if v.startswith('data:image/'):
            # Extract just the base64 part
            if ';base64,' in v:
                v = v.split(';base64,')[1]
        # Check approximate size (50KB decoded = ~67KB base64)
        if len(v) > 70000:
            raise ValueError("Signature too large (max 50KB)")
        return v


# ============================================
# Public Endpoints (No Authentication)
# ============================================

@router.get("/forms/{token}")
def get_public_form(token: str):
    """Get form data for public access. No authentication required.

    Returns form config, title, and list of respondents (names only, no signatures).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Look up form link by token
        cursor.execute("""
            SELECT
                fl.id, fl.organization_id, fl.audit_cycle_id, fl.submission_id,
                fl.record_id, fl.form_type, fl.title, fl.config,
                fl.is_active, fl.expires_at, fl.expected_responses,
                fl.created_at,
                c.year as cycle_year,
                r.record_number, r.name as record_name
            FROM ehc_form_link fl
            JOIN ehc_audit_cycle c ON c.id = fl.audit_cycle_id
            JOIN ehc_record r ON r.id = fl.record_id
            WHERE fl.token = %s
        """, (token,))

        form_link = dict_from_row(cursor.fetchone())

        if not form_link:
            raise HTTPException(status_code=404, detail="Form not found")

        # Check if expired
        if form_link.get('expires_at'):
            expires = form_link['expires_at']
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if expires < datetime.now(expires.tzinfo) if expires.tzinfo else datetime.now():
                raise HTTPException(status_code=410, detail="This form has expired")

        # Check if deactivated
        if not form_link.get('is_active'):
            raise HTTPException(status_code=410, detail="This form is no longer accepting responses")

        # Get existing responses (names and dates only, no signature data)
        cursor.execute("""
            SELECT respondent_name, respondent_role, respondent_dept, submitted_at
            FROM ehc_form_response
            WHERE form_link_id = %s
            ORDER BY submitted_at DESC
        """, (form_link['id'],))

        responses = dicts_from_rows(cursor.fetchall())

        # Format response data
        for resp in responses:
            if resp.get('submitted_at'):
                resp['submitted_at'] = resp['submitted_at'].isoformat()

        # Parse config if it's a string (stored via json.dumps)
        config = form_link.get('config') or {}
        if isinstance(config, str):
            config = json.loads(config)

        return {
            "title": form_link.get('title') or f"{form_link['record_name']} - EHC {form_link['cycle_year']}",
            "form_type": form_link['form_type'],
            "record_number": form_link['record_number'],
            "record_name": form_link['record_name'],
            "cycle_year": form_link['cycle_year'],
            "config": config,
            "responses": responses,
            "total_responses": len(responses),
            "expected_responses": form_link.get('expected_responses'),
            "is_active": form_link.get('is_active', True),
            "expires_at": form_link['expires_at'].isoformat() if form_link.get('expires_at') else None,
        }


@router.get("/forms/{token}/document")
def get_public_form_document(token: str):
    """Get the attached PDF document for a form. No authentication required.

    Uses token for access control instead of authentication.
    Returns 404 if no document is attached to this form.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Look up form link and get document path from config
        cursor.execute("""
            SELECT
                fl.id, fl.organization_id, fl.config, fl.is_active,
                o.id as org_id
            FROM ehc_form_link fl
            JOIN organizations o ON o.id = fl.organization_id
            WHERE fl.token = %s
        """, (token,))

        form_link = dict_from_row(cursor.fetchone())

        if not form_link:
            raise HTTPException(status_code=404, detail="Form not found")

        # Parse config to get document path
        config = form_link.get('config') or {}
        if isinstance(config, str):
            config = json.loads(config)

        document_path = config.get('document_path')

        if not document_path:
            raise HTTPException(status_code=404, detail="No document attached to this form")

        # Verify file exists
        if not os.path.exists(document_path):
            raise HTTPException(status_code=404, detail="Document file not found")

        # Extract filename from path
        filename = os.path.basename(document_path)

        return FileResponse(
            document_path,
            media_type="application/pdf",
            filename=filename
        )


@router.post("/forms/{token}/respond")
def submit_form_response(
    token: str,
    response: FormResponse,
    request: Request,
    force: bool = Query(False, description="Force submission even if duplicate name exists")
):
    """Submit a form response with signature. No authentication required.

    Duplicate detection: If a response with the same name exists, returns 409
    unless force=true is passed.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Look up form link
        cursor.execute("""
            SELECT id, is_active, expires_at, expected_responses, form_type
            FROM ehc_form_link
            WHERE token = %s
        """, (token,))

        form_link = dict_from_row(cursor.fetchone())

        if not form_link:
            raise HTTPException(status_code=404, detail="Form not found")

        # Check if expired
        if form_link.get('expires_at'):
            expires = form_link['expires_at']
            if isinstance(expires, str):
                expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if expires < datetime.now(expires.tzinfo) if expires.tzinfo else datetime.now():
                raise HTTPException(status_code=410, detail="This form has expired")

        # Check if deactivated
        if not form_link.get('is_active'):
            raise HTTPException(status_code=410, detail="This form is no longer accepting responses")

        form_link_id = form_link['id']

        # Check for duplicate name (case-insensitive)
        cursor.execute("""
            SELECT id, submitted_at
            FROM ehc_form_response
            WHERE form_link_id = %s AND LOWER(TRIM(respondent_name)) = LOWER(TRIM(%s))
        """, (form_link_id, response.respondent_name))

        existing = dict_from_row(cursor.fetchone())

        if existing and not force:
            # Return 409 with info about existing response
            submitted_at = existing['submitted_at']
            if isinstance(submitted_at, datetime):
                submitted_at = submitted_at.isoformat()
            raise HTTPException(
                status_code=409,
                detail={
                    "message": f"A response for '{response.respondent_name}' was already submitted",
                    "existing_submitted_at": submitted_at,
                    "existing_response_id": existing['id']
                }
            )

        if existing and force:
            # Delete existing response before inserting new one
            cursor.execute("""
                DELETE FROM ehc_form_response WHERE id = %s
            """, (existing['id'],))

        # Check flood prevention (2x expected_responses)
        if form_link.get('expected_responses'):
            cursor.execute("""
                SELECT COUNT(*) as count FROM ehc_form_response WHERE form_link_id = %s
            """, (form_link_id,))
            current_count = cursor.fetchone()['count']
            max_allowed = form_link['expected_responses'] * 2
            if current_count >= max_allowed:
                raise HTTPException(
                    status_code=400,
                    detail="This form has reached its maximum number of responses"
                )

        # Get client info for audit trail
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get('user-agent', '')[:500]

        # Insert response
        response_data_json = json.dumps(response.response_data) if response.response_data else None

        cursor.execute("""
            INSERT INTO ehc_form_response (
                form_link_id, respondent_name, respondent_role, respondent_dept,
                response_data, signature_data, ip_address, user_agent
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, submitted_at
        """, (
            form_link_id,
            response.respondent_name.strip(),
            response.respondent_role,
            response.respondent_dept,
            response_data_json,
            response.signature_data,
            ip_address,
            user_agent
        ))

        result = cursor.fetchone()

        # Check if all expected signatures are collected - if so, update submission status
        if form_link.get('expected_responses'):
            cursor.execute("""
                SELECT COUNT(*) as count FROM ehc_form_response WHERE form_link_id = %s
            """, (form_link_id,))
            new_count = cursor.fetchone()['count']

            if new_count >= form_link['expected_responses']:
                # All signatures collected - update linked submission to pending_approval
                cursor.execute("""
                    UPDATE ehc_record_submission
                    SET status = 'pending_approval', updated_at = NOW()
                    WHERE id = (
                        SELECT submission_id FROM ehc_form_link WHERE id = %s
                    )
                    AND status = 'collecting'
                """, (form_link_id,))

        conn.commit()

        return {
            "status": "ok",
            "response_id": result['id'],
            "submitted_at": result['submitted_at'].isoformat(),
            "message": f"Thank you, {response.respondent_name}. Your response has been recorded."
        }


# ============================================
# Authenticated Admin Endpoints
# ============================================

@router.post("/submissions/{submission_id}/generate-form-link")
def create_form_link(
    submission_id: int,
    data: FormLinkCreate,
    current_user: dict = Depends(get_current_user)
):
    """Generate a form link for a submission. Returns link with QR code."""
    org_id = current_user["organization_id"]
    user_id = current_user["id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify submission ownership and get related info
        cursor.execute("""
            SELECT
                rs.id, rs.audit_cycle_id, rs.record_id,
                c.year as cycle_year,
                r.record_number, r.name as record_name
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            JOIN ehc_record r ON r.id = rs.record_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        submission = dict_from_row(cursor.fetchone())
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Check for existing active link with same form_type
        cursor.execute("""
            SELECT id, token, title, form_type, expected_responses, expires_at, created_at
            FROM ehc_form_link
            WHERE submission_id = %s AND form_type = %s AND is_active = true
            ORDER BY created_at DESC
            LIMIT 1
        """, (submission_id, data.form_type))

        existing = dict_from_row(cursor.fetchone())
        if existing:
            # Return existing link instead of creating new one
            form_url = generate_form_url(existing['token'])
            qr_code = generate_form_qr(existing['token'])
            return {
                "status": "ok",
                "reused": True,
                "form_link_id": existing['id'],
                "token": existing['token'],
                "url": form_url,
                "qr_code": qr_code,
                "title": existing['title'],
                "form_type": existing['form_type'],
                "expected_responses": existing['expected_responses'],
                "expires_at": existing['expires_at'].isoformat() if existing['expires_at'] else None,
                "created_at": existing['created_at'].isoformat()
            }

        # Generate unique token for new link
        token = secrets.token_urlsafe(32)

        # Build config with defaults
        config = data.config or {}
        config['property_name'] = config.get('property_name', 'Property')
        config['cycle_year'] = submission['cycle_year']
        config['form_type'] = data.form_type

        # Parse expires_at if provided
        expires_at = None
        if data.expires_at:
            try:
                expires_at = datetime.fromisoformat(data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expires_at format. Use ISO format.")

        # Default title if not provided
        title = data.title or f"{submission['record_name']} - EHC {submission['cycle_year']}"

        # Insert form link
        cursor.execute("""
            INSERT INTO ehc_form_link (
                organization_id, audit_cycle_id, submission_id, record_id,
                token, form_type, title, config,
                expected_responses, expires_at, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            org_id,
            submission['audit_cycle_id'],
            submission_id,
            submission['record_id'],
            token,
            data.form_type,
            title,
            json.dumps(config),
            data.expected_responses,
            expires_at,
            user_id
        ))

        result = cursor.fetchone()
        conn.commit()

        # Generate QR code
        form_url = generate_form_url(token)
        qr_code = generate_form_qr(token)

        return {
            "status": "ok",
            "form_link_id": result['id'],
            "token": token,
            "url": form_url,
            "qr_code": qr_code,  # Base64 PNG
            "title": title,
            "form_type": data.form_type,
            "expected_responses": data.expected_responses,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": result['created_at'].isoformat()
        }


@router.get("/submissions/{submission_id}/form-links")
def get_submission_form_links(
    submission_id: int,
    current_user: dict = Depends(get_current_user)
):
    """List all form links for a submission."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify submission ownership
        cursor.execute("""
            SELECT rs.id
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get form links with response counts
        cursor.execute("""
            SELECT
                fl.id, fl.token, fl.form_type, fl.title, fl.config,
                fl.is_active, fl.expires_at, fl.expected_responses,
                fl.created_at, fl.updated_at,
                COUNT(fr.id) as response_count
            FROM ehc_form_link fl
            LEFT JOIN ehc_form_response fr ON fr.form_link_id = fl.id
            WHERE fl.submission_id = %s
            GROUP BY fl.id
            ORDER BY fl.created_at DESC
        """, (submission_id,))

        links = dicts_from_rows(cursor.fetchall())

        # Add URLs to each link
        for link in links:
            link['url'] = generate_form_url(link['token'])
            if link.get('expires_at'):
                link['expires_at'] = link['expires_at'].isoformat()
            if link.get('created_at'):
                link['created_at'] = link['created_at'].isoformat()
            if link.get('updated_at'):
                link['updated_at'] = link['updated_at'].isoformat()

        return {"data": links, "count": len(links)}


@router.get("/cycles/{cycle_id}/form-links")
def get_cycle_form_links(
    cycle_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get all form links for a cycle - for the Forms admin workbench."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify cycle ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Get all form links with response counts and record info
        cursor.execute("""
            SELECT
                fl.id, fl.token, fl.form_type, fl.title, fl.config,
                fl.is_active, fl.expires_at, fl.expected_responses,
                fl.submission_id, fl.record_id,
                fl.created_at, fl.updated_at,
                r.record_number, r.name as record_name,
                COUNT(fr.id) as response_count
            FROM ehc_form_link fl
            JOIN ehc_record r ON r.id = fl.record_id
            LEFT JOIN ehc_form_response fr ON fr.form_link_id = fl.id
            WHERE fl.audit_cycle_id = %s AND fl.organization_id = %s
            GROUP BY fl.id, r.id
            ORDER BY r.record_number, fl.created_at DESC
        """, (cycle_id, org_id))

        links = dicts_from_rows(cursor.fetchall())

        # Add URLs and format dates
        for link in links:
            link['url'] = generate_form_url(link['token'])
            if link.get('expires_at'):
                link['expires_at'] = link['expires_at'].isoformat()
            if link.get('created_at'):
                link['created_at'] = link['created_at'].isoformat()
            if link.get('updated_at'):
                link['updated_at'] = link['updated_at'].isoformat()
            # Parse config
            if link.get('config') and isinstance(link['config'], str):
                link['config'] = json.loads(link['config'])

        return {"data": links, "count": len(links)}


@router.post("/cycles/{cycle_id}/form-links")
def create_standalone_form_link(
    cycle_id: int,
    data: StandaloneFormLinkCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a standalone form link from the Forms tab.

    Unlike the submission-based endpoint, this creates forms directly
    without requiring an existing submission. Great for:
    - Simple sign-off forms with uploaded PDFs
    - Staff declarations before submissions exist
    - Forms that span multiple records
    """
    org_id = current_user["organization_id"]
    user_id = current_user["id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify cycle ownership and get year
        cursor.execute("""
            SELECT id, year FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        cycle = dict_from_row(cursor.fetchone())
        if not cycle:
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Verify record exists
        cursor.execute("""
            SELECT id, record_number, name FROM ehc_record WHERE id = %s
        """, (data.record_id,))

        record = dict_from_row(cursor.fetchone())
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Auto-create a submission for this form link
        # Status: 'collecting' (form-linked, awaiting signatures)
        cursor.execute("""
            INSERT INTO ehc_record_submission (
                audit_cycle_id, record_id, period_label, status
            )
            VALUES (%s, %s, %s, 'collecting')
            RETURNING id
        """, (
            cycle_id,
            data.record_id,
            f"EHC {cycle['year']}"  # Default period label
        ))
        submission_id = cursor.fetchone()['id']

        # Generate unique token
        token = secrets.token_urlsafe(32)

        # Build config with defaults
        config = data.config or {}
        config['property_name'] = config.get('property_name', 'Property')
        config['cycle_year'] = cycle['year']
        config['form_type'] = data.form_type

        # Parse expires_at if provided
        expires_at = None
        if data.expires_at:
            try:
                expires_at = datetime.fromisoformat(data.expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expires_at format")

        # Default title if not provided
        title = data.title or f"{record['name']} - EHC {cycle['year']}"

        # Insert form link
        cursor.execute("""
            INSERT INTO ehc_form_link (
                organization_id, audit_cycle_id, submission_id, record_id,
                token, form_type, title, config,
                expected_responses, expires_at, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        """, (
            org_id,
            cycle_id,
            submission_id,
            data.record_id,
            token,
            data.form_type,
            title,
            json.dumps(config),
            data.expected_responses,
            expires_at,
            user_id
        ))

        result = cursor.fetchone()
        conn.commit()

        # Generate QR code
        form_url = generate_form_url(token)
        qr_code = generate_form_qr(token)

        return {
            "status": "ok",
            "form_link_id": result['id'],
            "token": token,
            "url": form_url,
            "qr_code": qr_code,
            "title": title,
            "form_type": data.form_type,
            "record_number": record['record_number'],
            "record_name": record['name'],
            "expected_responses": data.expected_responses,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": result['created_at'].isoformat()
        }


@router.get("/cycles/{cycle_id}/records")
def get_cycle_records(
    cycle_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get all records for form creation dropdown."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify cycle ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Get all records for this organization
        cursor.execute("""
            SELECT id, record_number, name, description, location_type, record_type
            FROM ehc_record
            WHERE organization_id = %s
            ORDER BY
                CASE WHEN record_number ~ '^[0-9]+$' THEN CAST(record_number AS INTEGER) ELSE 999 END,
                record_number
        """, (org_id,))

        records = dicts_from_rows(cursor.fetchall())
        return {"data": records, "count": len(records)}


@router.post("/form-links/upload-document")
async def upload_form_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a PDF document for simple sign-off forms.

    Returns a document path to include in form link config.
    Documents are stored in uploads/ehc/{org_id}/documents/
    """
    org_id = current_user["organization_id"]

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Create directory if needed
    doc_dir = os.path.join(UPLOAD_DIR, 'ehc', str(org_id), 'documents')
    os.makedirs(doc_dir, exist_ok=True)

    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_name = f"{secrets.token_urlsafe(16)}{file_ext}"
    file_path = os.path.join(doc_dir, unique_name)

    # Save file
    with open(file_path, 'wb') as f:
        f.write(contents)

    return {
        "status": "ok",
        "document_path": file_path,
        "document_name": file.filename,
        "file_size": len(contents)
    }


@router.get("/form-links/document/{org_id}/{filename}")
def get_form_document(
    org_id: int,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Download a form document (for admin preview)."""
    # Verify user belongs to this org
    if current_user["organization_id"] != org_id:
        raise HTTPException(status_code=403, detail="Access denied")

    file_path = os.path.join(UPLOAD_DIR, 'ehc', str(org_id), 'documents', filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/form-links/{link_id}")
def get_form_link(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a form link with full details."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                fl.id, fl.token, fl.form_type, fl.title, fl.config,
                fl.is_active, fl.expires_at, fl.expected_responses,
                fl.submission_id, fl.record_id, fl.audit_cycle_id,
                fl.created_at, fl.updated_at,
                r.record_number, r.name as record_name,
                c.year as cycle_year
            FROM ehc_form_link fl
            JOIN ehc_record r ON r.id = fl.record_id
            JOIN ehc_audit_cycle c ON c.id = fl.audit_cycle_id
            WHERE fl.id = %s AND fl.organization_id = %s
        """, (link_id, org_id))

        link = dict_from_row(cursor.fetchone())
        if not link:
            raise HTTPException(status_code=404, detail="Form link not found")

        # Get response count
        cursor.execute("""
            SELECT COUNT(*) as count FROM ehc_form_response WHERE form_link_id = %s
        """, (link_id,))
        link['response_count'] = cursor.fetchone()['count']

        # Add URL
        link['url'] = generate_form_url(link['token'])

        # Format dates
        if link.get('expires_at'):
            link['expires_at'] = link['expires_at'].isoformat()
        if link.get('created_at'):
            link['created_at'] = link['created_at'].isoformat()
        if link.get('updated_at'):
            link['updated_at'] = link['updated_at'].isoformat()

        return link


@router.get("/form-links/{link_id}/responses")
def get_form_link_responses(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get all responses for a form link, including signature data."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_form_link WHERE id = %s AND organization_id = %s
        """, (link_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Form link not found")

        cursor.execute("""
            SELECT
                id, respondent_name, respondent_role, respondent_dept,
                response_data, signature_data, submitted_at,
                ip_address, user_agent
            FROM ehc_form_response
            WHERE form_link_id = %s
            ORDER BY submitted_at DESC
        """, (link_id,))

        responses = dicts_from_rows(cursor.fetchall())

        for resp in responses:
            if resp.get('submitted_at'):
                resp['submitted_at'] = resp['submitted_at'].isoformat()

        return {"data": responses, "count": len(responses)}


@router.patch("/form-links/{link_id}")
def update_form_link(
    link_id: int,
    updates: FormLinkUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a form link (deactivate, change expiry, update config)."""
    import json
    from psycopg2.extras import Json

    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_form_link WHERE id = %s AND organization_id = %s
        """, (link_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Form link not found")

        # Build update
        update_dict = updates.model_dump(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        # Handle expires_at conversion
        if 'expires_at' in update_dict and update_dict['expires_at']:
            try:
                update_dict['expires_at'] = datetime.fromisoformat(
                    update_dict['expires_at'].replace('Z', '+00:00')
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expires_at format")

        update_fields = []
        params = []
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            # Wrap dict/list values with Json for proper PostgreSQL JSON serialization
            if isinstance(value, (dict, list)):
                params.append(Json(value))
            else:
                params.append(value)

        update_fields.append("updated_at = NOW()")
        params.append(link_id)

        cursor.execute(f"""
            UPDATE ehc_form_link
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "link_id": link_id, "updated_fields": list(update_dict.keys())}


@router.delete("/form-links/{link_id}")
def delete_form_link(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a form link and all its responses.

    This is a destructive action - all response data will be permanently deleted.
    Consider deactivating instead if you want to preserve response history.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership and get info for response
        cursor.execute("""
            SELECT fl.id, fl.title, fl.form_type, COUNT(fr.id) as response_count
            FROM ehc_form_link fl
            LEFT JOIN ehc_form_response fr ON fr.form_link_id = fl.id
            WHERE fl.id = %s AND fl.organization_id = %s
            GROUP BY fl.id
        """, (link_id, org_id))

        form_link = dict_from_row(cursor.fetchone())
        if not form_link:
            raise HTTPException(status_code=404, detail="Form link not found")

        # Delete responses first (cascade should handle this, but be explicit)
        cursor.execute("""
            DELETE FROM ehc_form_response WHERE form_link_id = %s
        """, (link_id,))

        # Delete form link
        cursor.execute("""
            DELETE FROM ehc_form_link WHERE id = %s
        """, (link_id,))

        conn.commit()

        return {
            "status": "ok",
            "deleted_link_id": link_id,
            "deleted_title": form_link['title'],
            "deleted_responses": form_link['response_count']
        }


@router.delete("/form-links/{link_id}/responses/{response_id}")
def delete_form_response(
    link_id: int,
    response_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a form response (e.g., staff member left)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_form_link WHERE id = %s AND organization_id = %s
        """, (link_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Form link not found")

        # Delete response
        cursor.execute("""
            DELETE FROM ehc_form_response
            WHERE id = %s AND form_link_id = %s
            RETURNING respondent_name
        """, (response_id, link_id))

        deleted = cursor.fetchone()
        if not deleted:
            raise HTTPException(status_code=404, detail="Response not found")

        conn.commit()
        return {
            "status": "ok",
            "deleted_response_id": response_id,
            "deleted_name": deleted['respondent_name']
        }


@router.get("/form-links/{link_id}/qr")
def get_form_link_qr(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get QR code image (PNG) for a form link."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT token FROM ehc_form_link WHERE id = %s AND organization_id = %s
        """, (link_id, org_id))

        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Form link not found")

        # Generate QR code as PNG bytes
        url = generate_form_url(result['token'])
        qr_bytes = generate_qr_code_bytes(url)

        return Response(
            content=qr_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=qr_form_{link_id}.png"}
        )


# ============================================
# PDF Generation Endpoints
# ============================================

@router.post("/form-links/{link_id}/generate-pdf")
def generate_form_pdf(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Generate PDF for completed form responses.

    Returns PDF file for download.
    Supports: staff_declaration (Record 11), team_roster (Record 35)
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Get form link with config
        cursor.execute("""
            SELECT
                fl.id, fl.form_type, fl.title, fl.config, fl.expected_responses,
                c.year as cycle_year
            FROM ehc_form_link fl
            JOIN ehc_audit_cycle c ON c.id = fl.audit_cycle_id
            WHERE fl.id = %s AND fl.organization_id = %s
        """, (link_id, org_id))

        form_link = dict_from_row(cursor.fetchone())
        if not form_link:
            raise HTTPException(status_code=404, detail="Form link not found")

        # Parse config
        config = form_link.get('config') or {}
        if isinstance(config, str):
            config = json.loads(config)

        property_name = config.get('property_name', 'Property')
        cycle_year = form_link.get('cycle_year', datetime.now().year)
        form_type = form_link.get('form_type')
        title = form_link.get('title', f"Record - EHC {cycle_year}")

        # Get all responses with signature data
        cursor.execute("""
            SELECT
                id, respondent_name, respondent_role, respondent_dept,
                response_data, signature_data, submitted_at
            FROM ehc_form_response
            WHERE form_link_id = %s
            ORDER BY submitted_at ASC
        """, (link_id,))

        responses = dicts_from_rows(cursor.fetchall())

        # Parse response_data JSON
        for resp in responses:
            if resp.get('response_data') and isinstance(resp['response_data'], str):
                resp['response_data'] = json.loads(resp['response_data'])
            if resp.get('submitted_at'):
                resp['submitted_at'] = resp['submitted_at'].isoformat()

        # Generate PDF based on form type
        if form_type == 'staff_declaration':
            pdf_bytes = generate_record_11_pdf(
                title=title,
                property_name=property_name,
                cycle_year=cycle_year,
                responses=responses,
                expected_count=form_link.get('expected_responses')
            )
            filename = f"Record_11_Staff_Declaration_{cycle_year}.pdf"

        elif form_type == 'team_roster':
            team_members = config.get('team_members', [])
            pdf_bytes = generate_record_35_pdf(
                title=title,
                property_name=property_name,
                cycle_year=cycle_year,
                team_members=team_members,
                responses=responses
            )
            filename = f"Record_35_Food_Safety_Team_{cycle_year}.pdf"

        elif form_type == 'table_signoff':
            columns = config.get('columns', [])
            rows = config.get('rows', [])
            intro_text = config.get('intro_text', '')
            pdf_bytes = generate_table_signoff_pdf(
                title=title,
                property_name=property_name,
                cycle_year=cycle_year,
                columns=columns,
                rows=rows,
                responses=responses,
                intro_text=intro_text
            )
            # Create safe filename from title
            safe_title = "".join(c for c in title if c.isalnum() or c in ' -_')[:50]
            filename = f"{safe_title}_{cycle_year}.pdf"

        else:
            raise HTTPException(
                status_code=400,
                detail=f"PDF generation not supported for form type: {form_type}"
            )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )


@router.get("/form-links/{link_id}/flyer")
def get_form_flyer(
    link_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Generate printable flyer PDF with QR code for posting.

    Returns PDF with large QR code and instructions.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Get form link details
        cursor.execute("""
            SELECT
                fl.id, fl.token, fl.form_type, fl.title, fl.config,
                c.year as cycle_year
            FROM ehc_form_link fl
            JOIN ehc_audit_cycle c ON c.id = fl.audit_cycle_id
            WHERE fl.id = %s AND fl.organization_id = %s
        """, (link_id, org_id))

        form_link = dict_from_row(cursor.fetchone())
        if not form_link:
            raise HTTPException(status_code=404, detail="Form link not found")

        # Parse config
        config = form_link.get('config') or {}
        if isinstance(config, str):
            config = json.loads(config)

        property_name = config.get('property_name', 'Property')
        cycle_year = form_link.get('cycle_year', datetime.now().year)
        form_type = form_link.get('form_type', 'staff_declaration')
        title = form_link.get('title', f"EHC Form {cycle_year}")

        # Generate QR code
        qr_code_base64 = generate_form_qr(form_link['token'])

        # Generate flyer PDF
        pdf_bytes = generate_flyer_pdf(
            title=title,
            property_name=property_name,
            cycle_year=cycle_year,
            qr_code_base64=qr_code_base64,
            form_type=form_type
        )

        filename = f"QR_Flyer_{form_type}_{cycle_year}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
