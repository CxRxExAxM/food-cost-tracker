"""EHC Module API Router

Environmental Health Compliance - Food Safety Audit Tracking.
Organization-scoped audit cycle management with section/subsection/point hierarchy.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import os
import uuid

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user, require_admin
from ..services.ehc_seeder import seed_full_ehc_cycle
from ..utils.email import (
    is_email_configured,
    get_email_status,
    send_test_email,
    send_form_qr_email
)

router = APIRouter(prefix="/ehc", tags=["ehc"])


# ============================================
# Pydantic Models
# ============================================

class CycleCreate(BaseModel):
    """Create a new audit cycle."""
    year: int
    target_date: Optional[str] = None  # YYYY-MM-DD


class CycleUpdate(BaseModel):
    """Update an audit cycle."""
    name: Optional[str] = None
    target_date: Optional[str] = None
    actual_date: Optional[str] = None
    status: Optional[str] = None
    total_score: Optional[float] = None
    notes: Optional[str] = None


class PointUpdate(BaseModel):
    """Update an audit point."""
    status: Optional[str] = None
    actual_score: Optional[float] = None
    flag_color: Optional[str] = None
    notes: Optional[str] = None
    internal_verified: Optional[bool] = None


class SubmissionUpdate(BaseModel):
    """Update a record submission."""
    status: Optional[str] = None
    is_physical: Optional[bool] = None
    notes: Optional[str] = None
    responsibility_code: Optional[str] = None
    period_label: Optional[str] = None
    outlet_name: Optional[str] = None


class SubmissionCreate(BaseModel):
    """Create a new submission."""
    record_id: int
    period_label: str
    outlet_name: Optional[str] = None
    status: Optional[str] = "pending"
    responsibility_code: Optional[str] = None


class OutletAssignment(BaseModel):
    """Add/update outlet assignment for a record."""
    outlet_name: str
    sub_type: Optional[str] = None
    notes: Optional[str] = None


class PointRecordLink(BaseModel):
    """Link a record to an audit point."""
    record_id: int
    is_primary: Optional[bool] = True
    notes: Optional[str] = None


class OutletCreate(BaseModel):
    """Create a new EHC outlet."""
    name: str
    full_name: Optional[str] = None
    outlet_type: Optional[str] = None
    leader_name: Optional[str] = None
    leader_email: Optional[str] = None
    sort_order: Optional[int] = 0


class OutletUpdate(BaseModel):
    """Update an EHC outlet."""
    name: Optional[str] = None
    full_name: Optional[str] = None
    outlet_type: Optional[str] = None
    leader_name: Optional[str] = None
    leader_email: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class OutletReorder(BaseModel):
    """Reorder outlets."""
    outlets: List[dict]  # [{"id": 1, "sort_order": 0}, ...]


class ResponsibilityCodeCreate(BaseModel):
    """Create a new responsibility code."""
    code: str
    role_name: Optional[str] = None
    scope: Optional[str] = None
    sort_order: Optional[int] = 0


class ResponsibilityCodeUpdate(BaseModel):
    """Update a responsibility code."""
    role_name: Optional[str] = None
    scope: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ContactCreate(BaseModel):
    """Create a new EHC contact."""
    name: str
    email: str
    title: Optional[str] = None


class ContactUpdate(BaseModel):
    """Update an EHC contact."""
    name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    is_active: Optional[bool] = None


class ContactOutletAssignment(BaseModel):
    """Set outlet assignments for a contact."""
    outlets: List[dict]  # [{"outlet_id": 1, "is_primary": true}, ...]


class SendFormLinksRequest(BaseModel):
    """Send QR emails for form links."""
    form_link_ids: List[int]
    include_qr: Optional[bool] = True
    custom_message: Optional[str] = None


# ============================================
# Helper Functions
# ============================================

def calculate_section_progress(cursor, section_id: int, cycle_id: int = None) -> dict:
    """Calculate completion stats for a section with three-level breakdown.

    Status is computed from linked records:
    - Points with records: verified if all submissions approved
    - Points without records: use manual status

    Three-level breakdown:
    - Pre-Work: Record-based points with all submissions approved
    - Internal Walk: Observational points with internal_verified = true
    - Audit Walk: Observational points with status = verified
    """
    # Get cycle_id if not provided
    if cycle_id is None:
        cursor.execute("""
            SELECT s.audit_cycle_id FROM ehc_section s WHERE s.id = %s
        """, (section_id,))
        row = cursor.fetchone()
        cycle_id = row['audit_cycle_id'] if row else None

    cursor.execute("""
        WITH point_status AS (
            SELECT
                ap.id,
                ap.max_score,
                COALESCE(ap.actual_score, 0) as actual_score,
                ap.status as manual_status,
                COALESCE(ap.internal_verified, false) as internal_verified,
                COALESCE(rec.record_count, 0) as record_count,
                COALESCE(rec.total_subs, 0) as total_subs,
                COALESCE(rec.approved_subs, 0) as approved_subs
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(DISTINCT prl.record_id) as record_count,
                    COUNT(rs.id) as total_subs,
                    SUM(CASE WHEN rs.status = 'approved' THEN 1 ELSE 0 END) as approved_subs
                FROM ehc_point_record_link prl
                LEFT JOIN ehc_record_submission rs ON rs.record_id = prl.record_id
                    AND rs.audit_cycle_id = %s
                WHERE prl.audit_point_id = ap.id
            ) rec ON true
            WHERE ss.section_id = %s
        )
        SELECT
            COUNT(*) as total_points,
            SUM(CASE
                WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1
                WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1
                ELSE 0
            END) as completed_points,
            SUM(max_score) as max_score,
            SUM(actual_score) as actual_score,
            -- Three-level breakdown
            SUM(CASE WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1 ELSE 0 END) as prework_ready,
            SUM(CASE WHEN record_count = 0 AND internal_verified THEN 1 ELSE 0 END) as internal_walk_ready,
            SUM(CASE WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1 ELSE 0 END) as audit_walk_ready
        FROM point_status
    """, (cycle_id, section_id))

    row = cursor.fetchone()
    total = row['total_points'] or 0
    completed = row['completed_points'] or 0
    prework = row['prework_ready'] or 0
    internal = row['internal_walk_ready'] or 0
    audit = row['audit_walk_ready'] or 0

    return {
        "total_points": total,
        "completed_points": completed,
        "completion_pct": round((completed / total * 100) if total > 0 else 0, 1),
        "max_score": float(row['max_score'] or 0),
        "actual_score": float(row['actual_score'] or 0),
        # Three-level breakdown (as percentages of total)
        "prework_pct": round((prework / total * 100) if total > 0 else 0, 1),
        "internal_pct": round((internal / total * 100) if total > 0 else 0, 1),
        "audit_pct": round((audit / total * 100) if total > 0 else 0, 1),
    }


def calculate_cycle_progress(cursor, cycle_id: int) -> dict:
    """Calculate overall completion stats for a cycle.

    Status is computed from linked records:
    - Points with records: verified if all submissions approved
    - Points without records: use manual status

    Three dashboard categories:
    - Pre-Work Ready: Record-based points with all submissions approved
    - Internal Walk: Observational points with internal_verified = true
    - Audit Walk: Observational points pending (not yet internally verified)
    """
    cursor.execute("""
        WITH point_status AS (
            SELECT
                ap.id,
                ap.max_score,
                COALESCE(ap.actual_score, 0) as actual_score,
                ap.status as manual_status,
                COALESCE(ap.internal_verified, false) as internal_verified,
                COALESCE(rec.record_count, 0) as record_count,
                COALESCE(rec.total_subs, 0) as total_subs,
                COALESCE(rec.approved_subs, 0) as approved_subs
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(DISTINCT prl.record_id) as record_count,
                    COUNT(rs.id) as total_subs,
                    SUM(CASE WHEN rs.status = 'approved' THEN 1 ELSE 0 END) as approved_subs
                FROM ehc_point_record_link prl
                LEFT JOIN ehc_record_submission rs ON rs.record_id = prl.record_id
                    AND rs.audit_cycle_id = %s
                WHERE prl.audit_point_id = ap.id
            ) rec ON true
            WHERE s.audit_cycle_id = %s
        )
        SELECT
            COUNT(*) as total_points,
            SUM(CASE
                WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1
                WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1
                ELSE 0
            END) as completed_points,
            SUM(CASE
                WHEN record_count > 0 AND (total_subs = 0 OR approved_subs = 0) THEN 1
                WHEN record_count = 0 AND manual_status = 'not_started' THEN 1
                ELSE 0
            END) as not_started,
            SUM(CASE
                WHEN record_count > 0 AND total_subs > 0 AND approved_subs > 0 AND approved_subs < total_subs THEN 1
                WHEN record_count = 0 AND manual_status = 'in_progress' THEN 1
                ELSE 0
            END) as in_progress,
            SUM(CASE WHEN manual_status = 'flagged' THEN 1 ELSE 0 END) as flagged,
            SUM(max_score) as max_score,
            SUM(actual_score) as actual_score,
            -- Pre-work points (have linked records)
            SUM(CASE WHEN record_count > 0 THEN 1 ELSE 0 END) as prework_total,
            SUM(CASE WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1 ELSE 0 END) as prework_completed,
            -- Observational points (no linked records) - split by internal verification
            SUM(CASE WHEN record_count = 0 THEN 1 ELSE 0 END) as obs_total,
            SUM(CASE WHEN record_count = 0 AND internal_verified THEN 1 ELSE 0 END) as internal_walk_completed,
            SUM(CASE WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1 ELSE 0 END) as audit_walk_completed
        FROM point_status
    """, (cycle_id, cycle_id))

    row = cursor.fetchone()
    total = row['total_points'] or 0
    completed = row['completed_points'] or 0
    prework_total = row['prework_total'] or 0
    prework_completed = row['prework_completed'] or 0
    obs_total = row['obs_total'] or 0
    internal_walk_completed = row['internal_walk_completed'] or 0
    audit_walk_completed = row['audit_walk_completed'] or 0

    return {
        "total_points": total,
        "completed_points": completed,
        "not_started": row['not_started'] or 0,
        "in_progress": row['in_progress'] or 0,
        "flagged": row['flagged'] or 0,
        "completion_pct": round((completed / total * 100) if total > 0 else 0, 1),
        "max_score": float(row['max_score'] or 0),
        "actual_score": float(row['actual_score'] or 0),
        # Three dashboard categories
        "prework": {
            "total": prework_total,
            "completed": prework_completed,
            "completion_pct": round((prework_completed / prework_total * 100) if prework_total > 0 else 0, 1),
        },
        "internal_walk": {
            "total": obs_total,
            "completed": internal_walk_completed,
            "completion_pct": round((internal_walk_completed / obs_total * 100) if obs_total > 0 else 0, 1),
        },
        "audit_walk": {
            "total": obs_total,
            "completed": audit_walk_completed,
            "completion_pct": round((audit_walk_completed / obs_total * 100) if obs_total > 0 else 0, 1),
        },
    }


def calculate_submission_stats(cursor, cycle_id: int) -> dict:
    """Calculate submission completion stats for a cycle."""
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
            SUM(CASE WHEN status = 'submitted' THEN 1 ELSE 0 END) as submitted,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status = 'not_applicable' THEN 1 ELSE 0 END) as not_applicable
        FROM ehc_record_submission
        WHERE audit_cycle_id = %s
    """, (cycle_id,))

    row = cursor.fetchone()
    total = row['total'] or 0
    approved = row['approved'] or 0

    return {
        "total": total,
        "approved": approved,
        "submitted": row['submitted'] or 0,
        "in_progress": row['in_progress'] or 0,
        "pending": row['pending'] or 0,
        "not_applicable": row['not_applicable'] or 0,
        "completion_pct": round((approved / total * 100) if total > 0 else 0, 1),
    }


# ============================================
# Audit Cycle Endpoints
# ============================================

@router.get("/cycles")
def get_cycles(current_user: dict = Depends(get_current_user)):
    """Get all audit cycles for the organization."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, year, target_date, actual_date, status,
                   total_score, passing_threshold, notes, created_at
            FROM ehc_audit_cycle
            WHERE organization_id = %s
            ORDER BY year DESC
        """, (org_id,))

        cycles = dicts_from_rows(cursor.fetchall())

        # Add progress stats for each cycle
        for cycle in cycles:
            cycle['progress'] = calculate_cycle_progress(cursor, cycle['id'])
            if cycle.get('target_date'):
                cycle['target_date'] = str(cycle['target_date'])
            if cycle.get('actual_date'):
                cycle['actual_date'] = str(cycle['actual_date'])

        return {"data": cycles, "count": len(cycles)}


@router.post("/cycles")
def create_cycle(
    cycle: CycleCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new audit cycle and seed all data. Requires admin."""
    org_id = current_user["organization_id"]

    target_date = None
    if cycle.target_date:
        target_date = datetime.strptime(cycle.target_date, "%Y-%m-%d").date()

    with get_db() as conn:
        # Check if cycle already exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE organization_id = %s AND year = %s
        """, (org_id, cycle.year))

        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Audit cycle for {cycle.year} already exists"
            )

        # Seed the full cycle
        summary = seed_full_ehc_cycle(conn, org_id, cycle.year, target_date)

        return {
            "status": "ok",
            "message": f"Audit cycle {cycle.year} created",
            "summary": summary
        }


@router.get("/cycles/{cycle_id}")
def get_cycle(cycle_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single audit cycle with full stats."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, year, target_date, actual_date, status,
                   total_score, passing_threshold, notes, created_at, updated_at
            FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        cycle = dict_from_row(cursor.fetchone())

        if not cycle:
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Add detailed stats
        cycle['progress'] = calculate_cycle_progress(cursor, cycle_id)
        cycle['submissions'] = calculate_submission_stats(cursor, cycle_id)

        # Days until target
        if cycle.get('target_date'):
            target = cycle['target_date']
            if isinstance(target, str):
                target = datetime.strptime(target, "%Y-%m-%d").date()
            days_until = (target - date.today()).days
            cycle['days_until_audit'] = days_until
            cycle['target_date'] = str(cycle['target_date'])

        if cycle.get('actual_date'):
            cycle['actual_date'] = str(cycle['actual_date'])

        return cycle


@router.patch("/cycles/{cycle_id}")
def update_cycle(
    cycle_id: int,
    updates: CycleUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update an audit cycle. Requires admin."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Build update
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        update_fields = []
        params = []
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        update_fields.append("updated_at = NOW()")
        params.extend([cycle_id, org_id])

        cursor.execute(f"""
            UPDATE ehc_audit_cycle
            SET {', '.join(update_fields)}
            WHERE id = %s AND organization_id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "cycle_id": cycle_id, "updated_fields": list(update_dict.keys())}


@router.get("/cycles/{cycle_id}/dashboard")
def get_cycle_dashboard(cycle_id: int, current_user: dict = Depends(get_current_user)):
    """Get dashboard data for a cycle: sections with progress, NC breakdown."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id, name, year, target_date, status
            FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        cycle = dict_from_row(cursor.fetchone())
        if not cycle:
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Get sections with progress
        cursor.execute("""
            SELECT id, ref_number, name, sort_order
            FROM ehc_section
            WHERE audit_cycle_id = %s
            ORDER BY sort_order
        """, (cycle_id,))

        sections = []
        for row in cursor.fetchall():
            section = dict_from_row(row)
            section['progress'] = calculate_section_progress(cursor, section['id'], cycle_id)
            sections.append(section)

        # NC Level breakdown - compute status from linked records with three-level breakdown
        # Points with records: verified if all submissions approved
        # Points without records: use manual status
        cursor.execute("""
            WITH point_status AS (
                SELECT
                    ap.id,
                    ap.nc_level,
                    ap.status as manual_status,
                    COALESCE(ap.internal_verified, false) as internal_verified,
                    COALESCE(rec.record_count, 0) as record_count,
                    COALESCE(rec.total_subs, 0) as total_subs,
                    COALESCE(rec.approved_subs, 0) as approved_subs
                FROM ehc_audit_point ap
                JOIN ehc_subsection ss ON ss.id = ap.subsection_id
                JOIN ehc_section s ON s.id = ss.section_id
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(DISTINCT prl.record_id) as record_count,
                        COUNT(rs.id) as total_subs,
                        SUM(CASE WHEN rs.status = 'approved' THEN 1 ELSE 0 END) as approved_subs
                    FROM ehc_point_record_link prl
                    LEFT JOIN ehc_record_submission rs ON rs.record_id = prl.record_id
                        AND rs.audit_cycle_id = %s
                    WHERE prl.audit_point_id = ap.id
                ) rec ON true
                WHERE s.audit_cycle_id = %s
            )
            SELECT
                nc_level,
                COUNT(*) as total,
                SUM(CASE
                    WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1
                    WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1
                    ELSE 0
                END) as completed,
                -- Three-level breakdown
                SUM(CASE WHEN record_count > 0 AND total_subs > 0 AND approved_subs = total_subs THEN 1 ELSE 0 END) as prework_ready,
                SUM(CASE WHEN record_count = 0 AND internal_verified THEN 1 ELSE 0 END) as internal_walk_ready,
                SUM(CASE WHEN record_count = 0 AND manual_status IN ('evidence_collected', 'verified') THEN 1 ELSE 0 END) as audit_walk_ready
            FROM point_status
            GROUP BY nc_level
            ORDER BY nc_level
        """, (cycle_id, cycle_id))

        nc_breakdown = []
        for row in cursor.fetchall():
            total = row['total'] or 0
            nc_breakdown.append({
                "nc_level": row['nc_level'],
                "total": total,
                "completed": row['completed'],
                "completion_pct": round((row['completed'] / total * 100) if total > 0 else 0, 1),
                # Three-level breakdown (as percentages of total)
                "prework_pct": round((row['prework_ready'] / total * 100) if total > 0 else 0, 1),
                "internal_pct": round((row['internal_walk_ready'] / total * 100) if total > 0 else 0, 1),
                "audit_pct": round((row['audit_walk_ready'] / total * 100) if total > 0 else 0, 1),
            })

        # Days until audit
        days_until = None
        if cycle.get('target_date'):
            target = cycle['target_date']
            if isinstance(target, str):
                target = datetime.strptime(target, "%Y-%m-%d").date()
            days_until = (target - date.today()).days
            cycle['target_date'] = str(cycle['target_date'])

        return {
            "cycle": cycle,
            "days_until_audit": days_until,
            "overall_progress": calculate_cycle_progress(cursor, cycle_id),
            "submission_stats": calculate_submission_stats(cursor, cycle_id),
            "sections": sections,
            "nc_breakdown": nc_breakdown,
        }


# ============================================
# Sections & Subsections Endpoints
# ============================================

@router.get("/cycles/{cycle_id}/sections")
def get_sections(cycle_id: int, current_user: dict = Depends(get_current_user)):
    """Get all sections with nested subsections for a cycle."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Get sections
        cursor.execute("""
            SELECT id, ref_number, name, sort_order, max_score
            FROM ehc_section
            WHERE audit_cycle_id = %s
            ORDER BY sort_order
        """, (cycle_id,))

        sections = []
        for section_row in cursor.fetchall():
            section = dict_from_row(section_row)
            section['progress'] = calculate_section_progress(cursor, section['id'], cycle_id)

            # Get subsections for this section
            cursor.execute("""
                SELECT ss.id, ss.ref_code, ss.name, ss.sort_order, ss.max_score,
                       COUNT(ap.id) as point_count,
                       SUM(CASE WHEN ap.status IN ('evidence_collected', 'verified') THEN 1 ELSE 0 END) as completed_count
                FROM ehc_subsection ss
                LEFT JOIN ehc_audit_point ap ON ap.subsection_id = ss.id
                WHERE ss.section_id = %s
                GROUP BY ss.id, ss.ref_code, ss.name, ss.sort_order, ss.max_score
                ORDER BY ss.sort_order
            """, (section['id'],))

            subsections = []
            for ss_row in cursor.fetchall():
                ss = dict_from_row(ss_row)
                total = ss['point_count'] or 0
                completed = ss['completed_count'] or 0
                ss['completion_pct'] = round((completed / total * 100) if total > 0 else 0, 1)
                subsections.append(ss)

            section['subsections'] = subsections
            sections.append(section)

        return {"data": sections, "count": len(sections)}


# ============================================
# Audit Points Endpoints
# ============================================

@router.get("/cycles/{cycle_id}/points")
def get_points(
    cycle_id: int,
    section: Optional[int] = None,
    subsection: Optional[str] = None,
    nc_level: Optional[int] = None,
    status: Optional[str] = None,
    area: Optional[str] = None,
    has_records: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get audit points with filtering."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Build query with computed status from linked records
        # Points with records: status derived from record completion
        # Points without records (observational): use manual status
        query = """
            SELECT
                ap.id, ap.ref_code, ap.question_text, ap.nc_level, ap.max_score,
                ap.actual_score, ap.status as manual_status, ap.flag_color, ap.responsible_area, ap.notes,
                COALESCE(ap.internal_verified, false) as internal_verified,
                ss.ref_code as subsection_code, ss.name as subsection_name,
                s.ref_number as section_number, s.name as section_name,
                COALESCE(rec_stats.record_count, 0) as linked_record_count,
                COALESCE(rec_stats.total_submissions, 0) as total_submissions,
                COALESCE(rec_stats.approved_submissions, 0) as approved_submissions,
                rec_stats.linked_record_names
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            LEFT JOIN LATERAL (
                SELECT
                    COUNT(DISTINCT prl.record_id) as record_count,
                    COUNT(rs.id) as total_submissions,
                    SUM(CASE WHEN rs.status = 'approved' THEN 1 ELSE 0 END) as approved_submissions,
                    STRING_AGG(DISTINCT r.record_number || ': ' || r.name, ', ' ORDER BY r.record_number || ': ' || r.name) as linked_record_names
                FROM ehc_point_record_link prl
                JOIN ehc_record r ON r.id = prl.record_id
                LEFT JOIN ehc_record_submission rs ON rs.record_id = r.id AND rs.audit_cycle_id = %s
                WHERE prl.audit_point_id = ap.id
            ) rec_stats ON true
            WHERE s.audit_cycle_id = %s
        """
        params = [cycle_id, cycle_id]  # First for LATERAL, second for WHERE

        if section:
            query += " AND s.ref_number = %s"
            params.append(section)

        if subsection:
            query += " AND ss.ref_code = %s"
            params.append(subsection)

        if nc_level:
            query += " AND ap.nc_level = %s"
            params.append(nc_level)

        if area:
            query += " AND LOWER(ap.responsible_area) LIKE %s"
            params.append(f"%{area.lower()}%")

        query += " ORDER BY s.sort_order, ss.sort_order, ap.ref_code"

        cursor.execute(query, params)
        points = dicts_from_rows(cursor.fetchall())

        # Compute status from linked records
        for point in points:
            if point['linked_record_count'] > 0:
                # Has records: derive status from submissions
                total = point['total_submissions']
                approved = point['approved_submissions']
                if total > 0 and approved == total:
                    point['status'] = 'verified'
                    point['computed_status'] = True
                elif approved > 0:
                    point['status'] = 'in_progress'
                    point['computed_status'] = True
                else:
                    point['status'] = 'not_started'
                    point['computed_status'] = True
            else:
                # No records (observational): use manual status
                point['status'] = point['manual_status']
                point['computed_status'] = False

        # Filter by status (after computing)
        if status:
            points = [p for p in points if p['status'] == status]

        # Optionally filter by has_records
        if has_records is not None:
            points = [p for p in points if (p['linked_record_count'] > 0) == has_records]

        return {"data": points, "count": len(points)}


@router.get("/points/{point_id}")
def get_point(point_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single audit point with linked records."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Get point with ownership check
        cursor.execute("""
            SELECT
                ap.id, ap.ref_code, ap.question_text, ap.nc_level, ap.max_score,
                ap.actual_score, ap.status, ap.flag_color, ap.responsible_area, ap.notes,
                ap.created_at, ap.updated_at,
                ss.ref_code as subsection_code, ss.name as subsection_name,
                s.ref_number as section_number, s.name as section_name,
                c.id as cycle_id, c.year
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            JOIN ehc_audit_cycle c ON c.id = s.audit_cycle_id
            WHERE ap.id = %s AND c.organization_id = %s
        """, (point_id, org_id))

        point = dict_from_row(cursor.fetchone())

        if not point:
            raise HTTPException(status_code=404, detail="Audit point not found")

        # Get linked records with their submission status
        cursor.execute("""
            SELECT
                r.id as record_id, r.record_number, r.name as record_name,
                r.record_type, r.location_type,
                prl.is_primary,
                COUNT(rs.id) as submission_count,
                SUM(CASE WHEN rs.status = 'approved' THEN 1 ELSE 0 END) as approved_count
            FROM ehc_point_record_link prl
            JOIN ehc_record r ON r.id = prl.record_id
            LEFT JOIN ehc_record_submission rs ON rs.record_id = r.id
                AND rs.audit_cycle_id = %s
            WHERE prl.audit_point_id = %s
            GROUP BY r.id, r.record_number, r.name, r.record_type, r.location_type, prl.is_primary
            ORDER BY prl.is_primary DESC, r.record_number
        """, (point['cycle_id'], point_id))

        point['linked_records'] = dicts_from_rows(cursor.fetchall())

        return point


@router.patch("/points/{point_id}")
def update_point(
    point_id: int,
    updates: PointUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an audit point."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT ap.id
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            JOIN ehc_audit_cycle c ON c.id = s.audit_cycle_id
            WHERE ap.id = %s AND c.organization_id = %s
        """, (point_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Audit point not found")

        # Build update
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        update_fields = []
        params = []
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        update_fields.append("updated_at = NOW()")
        params.append(point_id)

        cursor.execute(f"""
            UPDATE ehc_audit_point
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "point_id": point_id, "updated_fields": list(update_dict.keys())}


@router.post("/points/{point_id}/link-record")
def link_record_to_point(
    point_id: int,
    link: PointRecordLink,
    current_user: dict = Depends(get_current_user)
):
    """Link a record to an audit point. Creates a point-record relationship."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify point ownership
        cursor.execute("""
            SELECT ap.id
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            JOIN ehc_audit_cycle c ON c.id = s.audit_cycle_id
            WHERE ap.id = %s AND c.organization_id = %s
        """, (point_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Audit point not found")

        # Verify record ownership
        cursor.execute("""
            SELECT id, record_number, name
            FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (link.record_id, org_id))

        record = dict_from_row(cursor.fetchone())
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if link already exists
        cursor.execute("""
            SELECT id FROM ehc_point_record_link
            WHERE audit_point_id = %s AND record_id = %s
        """, (point_id, link.record_id))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Record already linked to this point")

        # Create the link
        cursor.execute("""
            INSERT INTO ehc_point_record_link (audit_point_id, record_id, is_primary, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (point_id, link.record_id, link.is_primary, link.notes))

        link_id = cursor.fetchone()['id']
        conn.commit()

        return {
            "status": "ok",
            "link_id": link_id,
            "message": f"Record {record['record_number']}: {record['name']} linked to point"
        }


@router.delete("/points/{point_id}/link-record/{record_id}")
def unlink_record_from_point(
    point_id: int,
    record_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove a record link from an audit point."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify point ownership
        cursor.execute("""
            SELECT ap.id
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            JOIN ehc_audit_cycle c ON c.id = s.audit_cycle_id
            WHERE ap.id = %s AND c.organization_id = %s
        """, (point_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Audit point not found")

        # Delete the link
        cursor.execute("""
            DELETE FROM ehc_point_record_link
            WHERE audit_point_id = %s AND record_id = %s
            RETURNING id
        """, (point_id, record_id))

        deleted = cursor.fetchone()
        if not deleted:
            raise HTTPException(status_code=404, detail="Link not found")

        conn.commit()
        return {"status": "ok", "message": "Record unlinked from point"}


# ============================================
# Records Endpoints
# ============================================

@router.get("/records")
def get_records(
    location_type: Optional[str] = None,
    responsibility: Optional[str] = None,
    record_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get master record list for the organization."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT r.id, r.record_number, r.name, r.record_type, r.location_type,
                   r.responsibility_code, r.is_physical_only, r.is_removed, r.notes,
                   (SELECT COUNT(*) FROM ehc_record_outlet WHERE record_id = r.id) as outlet_count
            FROM ehc_record r
            WHERE r.organization_id = %s AND r.is_removed = false
        """
        params = [org_id]

        if location_type:
            query += " AND r.location_type = %s"
            params.append(location_type)

        if responsibility:
            query += " AND r.responsibility_code = %s"
            params.append(responsibility)

        if record_type:
            query += " AND r.record_type = %s"
            params.append(record_type)

        query += " ORDER BY r.record_number"

        cursor.execute(query, params)
        records = dicts_from_rows(cursor.fetchall())

        return {"data": records, "count": len(records)}


@router.get("/records/{record_id}")
def get_record(record_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single record with outlet mappings."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, record_number, name, record_type, location_type,
                   responsibility_code, is_physical_only, description, notes
            FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (record_id, org_id))

        record = dict_from_row(cursor.fetchone())

        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Get outlet mappings
        cursor.execute("""
            SELECT outlet_name, sub_type, notes
            FROM ehc_record_outlet
            WHERE record_id = %s
            ORDER BY outlet_name
        """, (record_id,))

        record['outlets'] = dicts_from_rows(cursor.fetchall())

        return record


class RecordUpdate(BaseModel):
    """Update a record."""
    name: Optional[str] = None
    notes: Optional[str] = None
    responsibility_code: Optional[str] = None
    record_type: Optional[str] = None  # daily, monthly, quarterly, annual, as_needed
    location_type: Optional[str] = None  # outlet_book, office_book
    description: Optional[str] = None
    is_physical_only: Optional[bool] = None


@router.patch("/records/{record_id}")
def update_record(
    record_id: int,
    updates: RecordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a record's metadata."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (record_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Record not found")

        # Build update
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        update_fields = []
        params = []
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        update_fields.append("updated_at = NOW()")
        params.append(record_id)

        cursor.execute(f"""
            UPDATE ehc_record
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "record_id": record_id, "updated_fields": list(update_dict.keys())}


@router.get("/records/{record_id}/outlets")
def get_record_outlets(record_id: int, current_user: dict = Depends(get_current_user)):
    """Get outlet assignments for a record."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (record_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute("""
            SELECT id, outlet_name, sub_type, notes
            FROM ehc_record_outlet
            WHERE record_id = %s
            ORDER BY outlet_name
        """, (record_id,))

        return {"data": dicts_from_rows(cursor.fetchall())}


@router.post("/records/{record_id}/outlets")
def add_record_outlet(
    record_id: int,
    outlet: OutletAssignment,
    current_user: dict = Depends(get_current_user)
):
    """Add an outlet assignment to a record."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (record_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Record not found")

        # Check if already exists
        cursor.execute("""
            SELECT id FROM ehc_record_outlet
            WHERE record_id = %s AND outlet_name = %s
        """, (record_id, outlet.outlet_name))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Outlet already assigned to this record")

        cursor.execute("""
            INSERT INTO ehc_record_outlet (record_id, outlet_name, sub_type, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (record_id, outlet.outlet_name, outlet.sub_type, outlet.notes))

        result = cursor.fetchone()
        conn.commit()

        return {"status": "ok", "outlet_id": result['id'], "outlet_name": outlet.outlet_name}


@router.delete("/records/{record_id}/outlets/{outlet_name}")
def remove_record_outlet(
    record_id: int,
    outlet_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove an outlet assignment from a record."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (record_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Record not found")

        cursor.execute("""
            DELETE FROM ehc_record_outlet
            WHERE record_id = %s AND outlet_name = %s
        """, (record_id, outlet_name))

        conn.commit()
        return {"status": "ok", "removed_outlet": outlet_name}


# ============================================
# Submissions Endpoints
# ============================================

@router.get("/cycles/{cycle_id}/submissions")
def get_submissions(
    cycle_id: int,
    record_id: Optional[int] = None,
    outlet: Optional[str] = None,
    status: Optional[str] = None,
    period: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get record submissions for a cycle with filtering."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        query = """
            SELECT
                rs.id, rs.record_id, rs.outlet_name, rs.period_label,
                rs.period_start, rs.period_end, rs.status, rs.is_physical,
                rs.file_path, rs.original_filename, rs.notes, rs.submitted_at, rs.approved_at,
                rs.responsibility_code,
                r.record_number, r.name as record_name, r.location_type,
                -- Form link info (if this submission is linked to a form)
                fl.id as form_link_id,
                fl.token as form_token,
                fl.title as form_title,
                fl.expected_responses as form_expected,
                fl.is_active as form_is_active,
                COALESCE(resp_count.response_count, 0) as form_responses
            FROM ehc_record_submission rs
            JOIN ehc_record r ON r.id = rs.record_id
            LEFT JOIN ehc_form_link fl ON fl.submission_id = rs.id AND fl.is_active = true
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as response_count
                FROM ehc_form_response fr
                WHERE fr.form_link_id = fl.id
            ) resp_count ON true
            WHERE rs.audit_cycle_id = %s
        """
        params = [cycle_id]

        if record_id:
            query += " AND rs.record_id = %s"
            params.append(record_id)

        if outlet:
            query += " AND rs.outlet_name = %s"
            params.append(outlet)

        if status:
            query += " AND rs.status = %s"
            params.append(status)

        if period:
            query += " AND rs.period_label LIKE %s"
            params.append(f"%{period}%")

        query += " ORDER BY r.record_number, rs.outlet_name, rs.period_start"

        cursor.execute(query, params)
        submissions = dicts_from_rows(cursor.fetchall())

        # Convert dates to strings and build form_link object
        for sub in submissions:
            if sub.get('period_start'):
                sub['period_start'] = str(sub['period_start'])
            if sub.get('period_end'):
                sub['period_end'] = str(sub['period_end'])

            # Nest form link info if present
            if sub.get('form_link_id'):
                sub['form_link'] = {
                    'id': sub.pop('form_link_id'),
                    'token': sub.pop('form_token'),
                    'title': sub.pop('form_title'),
                    'expected_responses': sub.pop('form_expected'),
                    'response_count': sub.pop('form_responses'),
                    'is_active': sub.pop('form_is_active'),
                }
            else:
                # Remove the null fields
                sub.pop('form_link_id', None)
                sub.pop('form_token', None)
                sub.pop('form_title', None)
                sub.pop('form_expected', None)
                sub.pop('form_responses', None)
                sub.pop('form_is_active', None)

        return {"data": submissions, "count": len(submissions)}


@router.post("/cycles/{cycle_id}/submissions")
def create_submission(
    cycle_id: int,
    submission: SubmissionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new submission for a record."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify cycle ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Verify record ownership
        cursor.execute("""
            SELECT id FROM ehc_record
            WHERE id = %s AND organization_id = %s
        """, (submission.record_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Record not found")

        # Create submission
        cursor.execute("""
            INSERT INTO ehc_record_submission (
                audit_cycle_id, record_id, outlet_name, period_label,
                status, responsibility_code
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            cycle_id, submission.record_id, submission.outlet_name,
            submission.period_label, submission.status or 'pending',
            submission.responsibility_code
        ))

        result = cursor.fetchone()
        conn.commit()

        return {
            "status": "ok",
            "submission_id": result['id'],
            "message": f"Submission created for {submission.period_label}"
        }


@router.patch("/submissions/{submission_id}")
def update_submission(
    submission_id: int,
    updates: SubmissionUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a record submission."""
    org_id = current_user["organization_id"]
    user_id = current_user["id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT rs.id, rs.status
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Build update
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        update_fields = []
        params = []

        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        # Track status transitions
        new_status = update_dict.get('status')
        if new_status == 'submitted' and existing['status'] != 'submitted':
            update_fields.append("submitted_by = %s")
            update_fields.append("submitted_at = NOW()")
            params.extend([user_id])
        elif new_status == 'approved' and existing['status'] != 'approved':
            update_fields.append("approved_by = %s")
            update_fields.append("approved_at = NOW()")
            params.extend([user_id])

        update_fields.append("updated_at = NOW()")
        params.append(submission_id)

        cursor.execute(f"""
            UPDATE ehc_record_submission
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "submission_id": submission_id, "updated_fields": list(update_dict.keys())}


@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a submission (for cleaning up duplicates)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT rs.id
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Submission not found")

        cursor.execute("DELETE FROM ehc_record_submission WHERE id = %s", (submission_id,))
        conn.commit()

        return {"status": "ok", "deleted_id": submission_id}


@router.post("/submissions/{submission_id}/upload")
async def upload_submission_file(
    submission_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a file for a submission."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership and get cycle info
        cursor.execute("""
            SELECT rs.id, c.year, r.record_number
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            JOIN ehc_record r ON r.id = rs.record_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        submission = cursor.fetchone()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Create upload directory
        upload_dir = f"uploads/ehc/{org_id}/{submission['year']}/{submission['record_number']}"
        os.makedirs(upload_dir, exist_ok=True)

        # Generate unique filename
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{submission_id}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = f"{upload_dir}/{unique_name}"

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Update submission with file path and original filename
        cursor.execute("""
            UPDATE ehc_record_submission
            SET file_path = %s, original_filename = %s, updated_at = NOW()
            WHERE id = %s
        """, (file_path, file.filename, submission_id))

        conn.commit()

        return {
            "status": "ok",
            "submission_id": submission_id,
            "file_path": file_path,
            "original_filename": file.filename
        }


@router.get("/submissions/{submission_id}/download")
async def download_submission_file(
    submission_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Download the file attached to a submission."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership and get file info
        cursor.execute("""
            SELECT rs.file_path, rs.original_filename
            FROM ehc_record_submission rs
            JOIN ehc_audit_cycle c ON c.id = rs.audit_cycle_id
            WHERE rs.id = %s AND c.organization_id = %s
        """, (submission_id, org_id))

        submission = cursor.fetchone()
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        if not submission['file_path']:
            raise HTTPException(status_code=404, detail="No file attached to this submission")

        if not os.path.exists(submission['file_path']):
            raise HTTPException(status_code=404, detail="File not found on server")

        # Return file with original filename
        return FileResponse(
            path=submission['file_path'],
            filename=submission['original_filename'] or os.path.basename(submission['file_path']),
            media_type='application/octet-stream'
        )


# ============================================
# Summary / Stats Endpoints
# ============================================

@router.get("/cycles/{cycle_id}/missing")
def get_missing_items(
    cycle_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get 'what's missing' summary - incomplete points and pending submissions."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_audit_cycle
            WHERE id = %s AND organization_id = %s
        """, (cycle_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Cycle not found")

        # Get incomplete audit points (not verified/evidence_collected)
        cursor.execute("""
            SELECT
                ap.id, ap.ref_code, ap.question_text, ap.nc_level,
                ap.status, ap.responsible_area,
                ss.ref_code as subsection_code,
                s.name as section_name
            FROM ehc_audit_point ap
            JOIN ehc_subsection ss ON ss.id = ap.subsection_id
            JOIN ehc_section s ON s.id = ss.section_id
            WHERE s.audit_cycle_id = %s
            AND ap.status NOT IN ('evidence_collected', 'verified')
            ORDER BY ap.nc_level, s.sort_order, ss.sort_order
        """, (cycle_id,))

        incomplete_points = dicts_from_rows(cursor.fetchall())

        # Get pending submissions
        cursor.execute("""
            SELECT
                rs.id, rs.period_label, rs.outlet_name, rs.status,
                r.record_number, r.name as record_name, r.location_type
            FROM ehc_record_submission rs
            JOIN ehc_record r ON r.id = rs.record_id
            WHERE rs.audit_cycle_id = %s
            AND rs.status IN ('pending', 'in_progress')
            ORDER BY r.record_number, rs.outlet_name
        """, (cycle_id,))

        pending_submissions = dicts_from_rows(cursor.fetchall())

        # Group by responsible area / location
        points_by_area = {}
        for point in incomplete_points:
            area = point.get('responsible_area') or 'Unassigned'
            if area not in points_by_area:
                points_by_area[area] = []
            points_by_area[area].append(point)

        submissions_by_location = {
            "outlet_book": [],
            "office_book": []
        }
        for sub in pending_submissions:
            loc = sub.get('location_type', 'office_book')
            submissions_by_location[loc].append(sub)

        return {
            "incomplete_points": {
                "total": len(incomplete_points),
                "by_area": points_by_area,
                "critical_nc1": [p for p in incomplete_points if p['nc_level'] == 1],
            },
            "pending_submissions": {
                "total": len(pending_submissions),
                "by_location": submissions_by_location,
            }
        }


# ============================================
# EHC Settings - Outlets Endpoints
# ============================================

@router.get("/outlets")
def get_outlets(
    active_only: bool = Query(default=True),
    current_user: dict = Depends(get_current_user)
):
    """Get all outlets for the organization."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, name, full_name, outlet_type, leader_name, leader_email,
                   is_active, sort_order, created_at, updated_at
            FROM ehc_outlet
            WHERE organization_id = %s
        """
        params = [org_id]

        if active_only:
            query += " AND is_active = true"

        query += " ORDER BY sort_order, name"

        cursor.execute(query, params)
        outlets = dicts_from_rows(cursor)

        return {"data": outlets, "count": len(outlets)}


@router.post("/outlets")
def create_outlet(
    outlet: OutletCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new outlet."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if name already exists (case-insensitive)
        cursor.execute("""
            SELECT id FROM ehc_outlet
            WHERE organization_id = %s AND LOWER(name) = LOWER(%s)
        """, (org_id, outlet.name))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Outlet name already exists")

        cursor.execute("""
            INSERT INTO ehc_outlet
                (organization_id, name, full_name, outlet_type, leader_name,
                 leader_email, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, full_name, outlet_type, leader_name, leader_email,
                      is_active, sort_order, created_at, updated_at
        """, (
            org_id, outlet.name, outlet.full_name, outlet.outlet_type,
            outlet.leader_name, outlet.leader_email, outlet.sort_order
        ))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        return result


@router.patch("/outlets/{outlet_id}")
def update_outlet(
    outlet_id: int,
    outlet: OutletUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an outlet."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_outlet
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Outlet not found")

        # Check if name conflict (if changing name)
        if outlet.name:
            cursor.execute("""
                SELECT id FROM ehc_outlet
                WHERE organization_id = %s AND LOWER(name) = LOWER(%s) AND id != %s
            """, (org_id, outlet.name, outlet_id))

            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Outlet name already exists")

        # Build update query
        updates = []
        params = []

        if outlet.name is not None:
            updates.append("name = %s")
            params.append(outlet.name)
        if outlet.full_name is not None:
            updates.append("full_name = %s")
            params.append(outlet.full_name)
        if outlet.outlet_type is not None:
            updates.append("outlet_type = %s")
            params.append(outlet.outlet_type)
        if outlet.leader_name is not None:
            updates.append("leader_name = %s")
            params.append(outlet.leader_name)
        if outlet.leader_email is not None:
            updates.append("leader_email = %s")
            params.append(outlet.leader_email)
        if outlet.is_active is not None:
            updates.append("is_active = %s")
            params.append(outlet.is_active)
        if outlet.sort_order is not None:
            updates.append("sort_order = %s")
            params.append(outlet.sort_order)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.extend([outlet_id, org_id])

        cursor.execute(f"""
            UPDATE ehc_outlet
            SET {", ".join(updates)}
            WHERE id = %s AND organization_id = %s
            RETURNING id, name, full_name, outlet_type, leader_name, leader_email,
                      is_active, sort_order, created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        return result


@router.delete("/outlets/{outlet_id}")
def delete_outlet(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Soft-delete an outlet (set is_active = false)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_outlet
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Outlet not found")

        cursor.execute("""
            UPDATE ehc_outlet
            SET is_active = false, updated_at = NOW()
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        conn.commit()

        return {"status": "ok", "outlet_id": outlet_id}


@router.patch("/outlets/reorder")
def reorder_outlets(
    data: OutletReorder,
    current_user: dict = Depends(get_current_user)
):
    """Bulk update sort order for outlets."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        for item in data.outlets:
            outlet_id = item.get("id")
            sort_order = item.get("sort_order")

            if outlet_id is None or sort_order is None:
                continue

            # Verify ownership and update
            cursor.execute("""
                UPDATE ehc_outlet
                SET sort_order = %s, updated_at = NOW()
                WHERE id = %s AND organization_id = %s
            """, (sort_order, outlet_id, org_id))

        conn.commit()

        return {"status": "ok", "updated": len(data.outlets)}


# ============================================
# EHC Settings - Responsibility Codes Endpoints
# ============================================

@router.get("/responsibility-codes")
def get_responsibility_codes(
    active_only: bool = Query(default=True),
    current_user: dict = Depends(get_current_user)
):
    """Get all responsibility codes for the organization."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, code, role_name, scope, is_active, sort_order,
                   created_at, updated_at
            FROM ehc_responsibility_code
            WHERE organization_id = %s
        """
        params = [org_id]

        if active_only:
            query += " AND is_active = true"

        query += " ORDER BY sort_order, code"

        cursor.execute(query, params)
        codes = dicts_from_rows(cursor)

        return {"data": codes, "count": len(codes)}


@router.post("/responsibility-codes")
def create_responsibility_code(
    code_data: ResponsibilityCodeCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new responsibility code."""
    org_id = current_user["organization_id"]

    # Validate code format
    if not code_data.code or len(code_data.code) > 10 or ' ' in code_data.code:
        raise HTTPException(
            status_code=400,
            detail="Code must be 1-10 characters with no spaces"
        )

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if code already exists (case-insensitive)
        cursor.execute("""
            SELECT id FROM ehc_responsibility_code
            WHERE organization_id = %s AND LOWER(code) = LOWER(%s)
        """, (org_id, code_data.code))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Responsibility code already exists")

        cursor.execute("""
            INSERT INTO ehc_responsibility_code
                (organization_id, code, role_name, scope, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, code, role_name, scope, is_active, sort_order,
                      created_at, updated_at
        """, (
            org_id, code_data.code.upper(), code_data.role_name,
            code_data.scope, code_data.sort_order
        ))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        return result


@router.patch("/responsibility-codes/{code_id}")
def update_responsibility_code(
    code_id: int,
    code_data: ResponsibilityCodeUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a responsibility code."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_responsibility_code
            WHERE id = %s AND organization_id = %s
        """, (code_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Responsibility code not found")

        # Build update query
        updates = []
        params = []

        if code_data.role_name is not None:
            updates.append("role_name = %s")
            params.append(code_data.role_name)
        if code_data.scope is not None:
            updates.append("scope = %s")
            params.append(code_data.scope)
        if code_data.is_active is not None:
            updates.append("is_active = %s")
            params.append(code_data.is_active)
        if code_data.sort_order is not None:
            updates.append("sort_order = %s")
            params.append(code_data.sort_order)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.extend([code_id, org_id])

        cursor.execute(f"""
            UPDATE ehc_responsibility_code
            SET {", ".join(updates)}
            WHERE id = %s AND organization_id = %s
            RETURNING id, code, role_name, scope, is_active, sort_order,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        return result


@router.delete("/responsibility-codes/{code_id}")
def delete_responsibility_code(
    code_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Soft-delete a responsibility code (set is_active = false)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_responsibility_code
            WHERE id = %s AND organization_id = %s
        """, (code_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Responsibility code not found")

        cursor.execute("""
            UPDATE ehc_responsibility_code
            SET is_active = false, updated_at = NOW()
            WHERE id = %s AND organization_id = %s
        """, (code_id, org_id))

        conn.commit()

        return {"status": "ok", "code_id": code_id}


# ============================================
# EHC Settings - Contacts Endpoints
# ============================================

@router.get("/contacts")
def get_contacts(
    active_only: bool = Query(default=True),
    current_user: dict = Depends(get_current_user)
):
    """Get all contacts for the organization with their outlet assignments."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT c.id, c.name, c.email, c.title, c.is_active, c.user_id,
                   c.created_at, c.updated_at
            FROM ehc_contact c
            WHERE c.organization_id = %s
        """
        params = [org_id]

        if active_only:
            query += " AND c.is_active = true"

        query += " ORDER BY c.name"

        cursor.execute(query, params)
        contacts = dicts_from_rows(cursor)

        # Get outlet assignments for each contact
        for contact in contacts:
            cursor.execute("""
                SELECT co.outlet_id, o.name as outlet_name, o.full_name, co.is_primary
                FROM ehc_contact_outlet co
                JOIN ehc_outlet o ON o.id = co.outlet_id
                WHERE co.contact_id = %s AND o.is_active = true
                ORDER BY o.sort_order, o.name
            """, (contact['id'],))
            contact['outlets'] = dicts_from_rows(cursor)

        return {"data": contacts, "count": len(contacts)}


@router.get("/contacts/{contact_id}")
def get_contact(
    contact_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get a single contact with outlet assignments."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, email, title, is_active, user_id, created_at, updated_at
            FROM ehc_contact
            WHERE id = %s AND organization_id = %s
        """, (contact_id, org_id))

        contact = dict_from_row(cursor.fetchone())
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # Get outlet assignments
        cursor.execute("""
            SELECT co.outlet_id, o.name as outlet_name, o.full_name, co.is_primary
            FROM ehc_contact_outlet co
            JOIN ehc_outlet o ON o.id = co.outlet_id
            WHERE co.contact_id = %s
            ORDER BY o.sort_order, o.name
        """, (contact_id,))
        contact['outlets'] = dicts_from_rows(cursor)

        return contact


@router.post("/contacts")
def create_contact(
    contact: ContactCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new contact."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if email already exists
        cursor.execute("""
            SELECT id FROM ehc_contact
            WHERE organization_id = %s AND LOWER(email) = LOWER(%s)
        """, (org_id, contact.email))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Contact with this email already exists")

        cursor.execute("""
            INSERT INTO ehc_contact (organization_id, name, email, title)
            VALUES (%s, %s, %s, %s)
            RETURNING id, name, email, title, is_active, user_id, created_at, updated_at
        """, (org_id, contact.name, contact.email, contact.title))

        result = dict_from_row(cursor.fetchone())
        result['outlets'] = []  # New contact has no outlets
        conn.commit()

        return result


@router.patch("/contacts/{contact_id}")
def update_contact(
    contact_id: int,
    contact: ContactUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a contact."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_contact
            WHERE id = %s AND organization_id = %s
        """, (contact_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Contact not found")

        # Check email conflict if changing email
        if contact.email:
            cursor.execute("""
                SELECT id FROM ehc_contact
                WHERE organization_id = %s AND LOWER(email) = LOWER(%s) AND id != %s
            """, (org_id, contact.email, contact_id))

            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Contact with this email already exists")

        # Build update query
        updates = []
        params = []

        if contact.name is not None:
            updates.append("name = %s")
            params.append(contact.name)
        if contact.email is not None:
            updates.append("email = %s")
            params.append(contact.email)
        if contact.title is not None:
            updates.append("title = %s")
            params.append(contact.title)
        if contact.is_active is not None:
            updates.append("is_active = %s")
            params.append(contact.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = NOW()")
        params.extend([contact_id, org_id])

        cursor.execute(f"""
            UPDATE ehc_contact
            SET {", ".join(updates)}
            WHERE id = %s AND organization_id = %s
            RETURNING id, name, email, title, is_active, user_id, created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())

        # Get outlet assignments
        cursor.execute("""
            SELECT co.outlet_id, o.name as outlet_name, o.full_name, co.is_primary
            FROM ehc_contact_outlet co
            JOIN ehc_outlet o ON o.id = co.outlet_id
            WHERE co.contact_id = %s
            ORDER BY o.sort_order, o.name
        """, (contact_id,))
        result['outlets'] = dicts_from_rows(cursor)

        conn.commit()

        return result


@router.delete("/contacts/{contact_id}")
def delete_contact(
    contact_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Soft-delete a contact (set is_active = false)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT id FROM ehc_contact
            WHERE id = %s AND organization_id = %s
        """, (contact_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Contact not found")

        cursor.execute("""
            UPDATE ehc_contact
            SET is_active = false, updated_at = NOW()
            WHERE id = %s AND organization_id = %s
        """, (contact_id, org_id))

        conn.commit()

        return {"status": "ok", "contact_id": contact_id}


@router.post("/contacts/{contact_id}/outlets")
def set_contact_outlets(
    contact_id: int,
    assignment: ContactOutletAssignment,
    current_user: dict = Depends(get_current_user)
):
    """Set outlet assignments for a contact (replaces all existing assignments)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify contact ownership
        cursor.execute("""
            SELECT id FROM ehc_contact
            WHERE id = %s AND organization_id = %s
        """, (contact_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Contact not found")

        # Verify all outlets belong to this org
        outlet_ids = [o.get('outlet_id') for o in assignment.outlets if o.get('outlet_id')]
        if outlet_ids:
            cursor.execute("""
                SELECT id FROM ehc_outlet
                WHERE id = ANY(%s) AND organization_id = %s
            """, (outlet_ids, org_id))
            valid_outlets = {row['id'] for row in dicts_from_rows(cursor)}
            invalid_ids = set(outlet_ids) - valid_outlets
            if invalid_ids:
                raise HTTPException(status_code=400, detail=f"Invalid outlet IDs: {invalid_ids}")

        # Clear existing assignments
        cursor.execute("""
            DELETE FROM ehc_contact_outlet WHERE contact_id = %s
        """, (contact_id,))

        # Insert new assignments
        for outlet_data in assignment.outlets:
            outlet_id = outlet_data.get('outlet_id')
            is_primary = outlet_data.get('is_primary', False)

            if outlet_id:
                # If setting as primary, clear other primary assignments for this outlet
                if is_primary:
                    cursor.execute("""
                        UPDATE ehc_contact_outlet
                        SET is_primary = false
                        WHERE outlet_id = %s AND contact_id != %s
                    """, (outlet_id, contact_id))

                cursor.execute("""
                    INSERT INTO ehc_contact_outlet (contact_id, outlet_id, is_primary)
                    VALUES (%s, %s, %s)
                """, (contact_id, outlet_id, is_primary))

        conn.commit()

        # Return updated contact with outlets
        cursor.execute("""
            SELECT id, name, email, title, is_active, user_id, created_at, updated_at
            FROM ehc_contact
            WHERE id = %s
        """, (contact_id,))
        result = dict_from_row(cursor.fetchone())

        cursor.execute("""
            SELECT co.outlet_id, o.name as outlet_name, o.full_name, co.is_primary
            FROM ehc_contact_outlet co
            JOIN ehc_outlet o ON o.id = co.outlet_id
            WHERE co.contact_id = %s
            ORDER BY o.sort_order, o.name
        """, (contact_id,))
        result['outlets'] = dicts_from_rows(cursor)

        return result


@router.get("/outlets/{outlet_id}/contacts")
def get_outlet_contacts(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get all contacts assigned to an outlet."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify outlet ownership
        cursor.execute("""
            SELECT id FROM ehc_outlet
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Outlet not found")

        cursor.execute("""
            SELECT c.id, c.name, c.email, c.title, co.is_primary
            FROM ehc_contact c
            JOIN ehc_contact_outlet co ON co.contact_id = c.id
            WHERE co.outlet_id = %s AND c.is_active = true
            ORDER BY co.is_primary DESC, c.name
        """, (outlet_id,))

        contacts = dicts_from_rows(cursor)

        return {"data": contacts, "count": len(contacts)}


@router.get("/outlets/{outlet_id}/primary-contact")
def get_outlet_primary_contact(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get the primary contact for an outlet (for email distribution)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify outlet ownership
        cursor.execute("""
            SELECT id, name FROM ehc_outlet
            WHERE id = %s AND organization_id = %s
        """, (outlet_id, org_id))

        outlet = dict_from_row(cursor.fetchone())
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet not found")

        cursor.execute("""
            SELECT c.id, c.name, c.email, c.title
            FROM ehc_contact c
            JOIN ehc_contact_outlet co ON co.contact_id = c.id
            WHERE co.outlet_id = %s AND co.is_primary = true AND c.is_active = true
            LIMIT 1
        """, (outlet_id,))

        contact = dict_from_row(cursor.fetchone())

        return {
            "outlet_id": outlet_id,
            "outlet_name": outlet['name'],
            "primary_contact": contact
        }


# ============================================
# EHC Settings - Email Endpoints
# ============================================

@router.get("/email/status")
def get_email_configuration_status(
    current_user: dict = Depends(get_current_user)
):
    """Get email configuration status."""
    return get_email_status()


@router.post("/email/test")
def send_email_test(
    current_user: dict = Depends(get_current_user)
):
    """Send a test email to the current user."""
    org_id = current_user["organization_id"]
    user_email = current_user.get("email")
    user_name = current_user.get("name", "User")

    if not user_email:
        raise HTTPException(status_code=400, detail="Current user has no email address")

    if not is_email_configured():
        raise HTTPException(status_code=503, detail="Email is not configured. Set RESEND_API_KEY.")

    # Send test email
    result = send_test_email(to_email=user_email, to_name=user_name)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {result['error']}")

    # Log the email
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ehc_email_log
                (organization_id, email_to, email_to_name, email_subject, email_type,
                 resend_id, status, sent_by_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            org_id, user_email, user_name, "RestauranTek EHC - Test Email",
            "test", result["resend_id"], "sent", current_user["id"]
        ))
        log_id = cursor.fetchone()['id']
        conn.commit()

    return {
        "success": True,
        "message": f"Test email sent to {user_email}",
        "resend_id": result["resend_id"],
        "log_id": log_id
    }


@router.post("/email/send-form-links")
def send_form_link_emails(
    request: SendFormLinksRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send QR code emails for form links to their assigned outlets' primary contacts."""
    org_id = current_user["organization_id"]

    if not is_email_configured():
        raise HTTPException(status_code=503, detail="Email is not configured. Set RESEND_API_KEY.")

    if not request.form_link_ids:
        raise HTTPException(status_code=400, detail="No form link IDs provided")

    results = []
    with get_db() as conn:
        cursor = conn.cursor()

        for form_link_id in request.form_link_ids:
            # Get form link details
            cursor.execute("""
                SELECT fl.id, fl.token, fl.outlet_name, fl.period_label,
                       fl.config, t.name as template_name
                FROM ehc_form_link fl
                LEFT JOIN ehc_form_template t ON t.id = fl.template_id
                WHERE fl.id = %s AND fl.organization_id = %s
            """, (form_link_id, org_id))

            form_link = dict_from_row(cursor.fetchone())
            if not form_link:
                results.append({
                    "form_link_id": form_link_id,
                    "success": False,
                    "error": "Form link not found"
                })
                continue

            # Find the outlet and its primary contact
            cursor.execute("""
                SELECT o.id as outlet_id, o.name, c.id as contact_id, c.name as contact_name, c.email
                FROM ehc_outlet o
                JOIN ehc_contact_outlet co ON co.outlet_id = o.id AND co.is_primary = true
                JOIN ehc_contact c ON c.id = co.contact_id AND c.is_active = true
                WHERE o.organization_id = %s AND o.name = %s AND o.is_active = true
            """, (org_id, form_link['outlet_name']))

            contact_row = dict_from_row(cursor.fetchone())
            if not contact_row:
                results.append({
                    "form_link_id": form_link_id,
                    "outlet_name": form_link['outlet_name'],
                    "success": False,
                    "error": f"No primary contact found for outlet '{form_link['outlet_name']}'"
                })
                continue

            # Build form URL
            # Use production URL if available, otherwise dev
            base_url = os.getenv("FRONTEND_URL", "https://www.restaurantek.io")
            form_url = f"{base_url}/ehc/form/{form_link['token']}"

            # Get QR code if requested
            qr_base64 = None
            if request.include_qr:
                cursor.execute("""
                    SELECT qr_code FROM ehc_form_link WHERE id = %s
                """, (form_link_id,))
                qr_row = cursor.fetchone()
                if qr_row and qr_row['qr_code']:
                    qr_base64 = qr_row['qr_code']

            # Send the email
            form_name = form_link.get('template_name') or "EHC Form"
            email_result = send_form_qr_email(
                to_email=contact_row['email'],
                to_name=contact_row['contact_name'],
                outlet_name=form_link['outlet_name'],
                form_name=form_name,
                period_label=form_link['period_label'] or "",
                form_url=form_url,
                qr_image_base64=qr_base64,
                custom_message=request.custom_message
            )

            # Log the email
            status = "sent" if email_result["success"] else "failed"
            cursor.execute("""
                INSERT INTO ehc_email_log
                    (organization_id, contact_id, email_to, email_to_name, email_subject,
                     email_type, form_link_id, outlet_id, resend_id, status, error_message,
                     sent_by_user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                org_id, contact_row['contact_id'], contact_row['email'],
                contact_row['contact_name'],
                f"EHC Form: {form_name} - {form_link['outlet_name']} ({form_link['period_label']})",
                "form_qr", form_link_id, contact_row['outlet_id'],
                email_result.get("resend_id"), status, email_result.get("error"),
                current_user["id"]
            ))

            results.append({
                "form_link_id": form_link_id,
                "outlet_name": form_link['outlet_name'],
                "contact_name": contact_row['contact_name'],
                "contact_email": contact_row['email'],
                "success": email_result["success"],
                "error": email_result.get("error"),
                "resend_id": email_result.get("resend_id")
            })

        conn.commit()

    # Summary
    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful

    return {
        "results": results,
        "summary": {
            "total": len(results),
            "successful": successful,
            "failed": failed
        }
    }


@router.get("/email/log")
def get_email_log(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    email_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get recent email log entries."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT el.id, el.email_to, el.email_to_name, el.email_subject,
                   el.email_type, el.status, el.error_message, el.sent_at,
                   el.resend_id, o.name as outlet_name, c.name as contact_name,
                   u.name as sent_by_name
            FROM ehc_email_log el
            LEFT JOIN ehc_outlet o ON o.id = el.outlet_id
            LEFT JOIN ehc_contact c ON c.id = el.contact_id
            LEFT JOIN users u ON u.id = el.sent_by_user_id
            WHERE el.organization_id = %s
        """
        params = [org_id]

        if email_type:
            query += " AND el.email_type = %s"
            params.append(email_type)

        query += " ORDER BY el.sent_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        logs = dicts_from_rows(cursor)

        # Get total count
        count_query = """
            SELECT COUNT(*) as total FROM ehc_email_log WHERE organization_id = %s
        """
        count_params = [org_id]
        if email_type:
            count_query += " AND email_type = %s"
            count_params.append(email_type)

        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']

        return {
            "data": logs,
            "count": len(logs),
            "total": total
        }
