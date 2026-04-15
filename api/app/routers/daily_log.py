"""Daily Log Module API Router

Daily equipment monitoring and food safety logging system.
Replaces paper "Daily Worksheets" used by kitchen outlets.

Public endpoints for kitchen staff (QR access):
- Get/create daily worksheet
- Record cooler/freezer temperatures
- Sign shift readings

Authenticated endpoints for management:
- List outlets with monitoring enabled
- Review and approve worksheets
- View monthly calendar
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user


router = APIRouter(prefix="/daily-log", tags=["daily-log"])


# ============================================
# Pydantic Models
# ============================================

class CoolerReadingUpdate(BaseModel):
    """Update a single cooler/freezer reading."""
    temperature_f: Optional[Decimal] = None
    corrective_action: Optional[str] = None
    alice_ticket: Optional[str] = None
    recorded_by: Optional[str] = None


class CoolerSignRequest(BaseModel):
    """Sign a shift's cooler readings."""
    shift: str  # 'am' or 'pm'
    recorded_by: str
    signature_data: str  # base64 PNG


class WorksheetStatusUpdate(BaseModel):
    """Update worksheet status."""
    status: str  # 'open', 'review', 'approved'


# ============================================
# Public Endpoints (No Auth - QR Access)
# ============================================

@router.get("/outlets")
def list_monitoring_outlets(
    current_user: dict = Depends(get_current_user)
):
    """List outlets with daily monitoring enabled."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, name, full_name, outlet_type,
                   cooler_count, freezer_count,
                   has_cooking, has_cooling, has_thawing,
                   has_hot_buffet, has_cold_buffet,
                   serves_breakfast, serves_lunch, serves_dinner,
                   readings_per_service,
                   cooler_max_f, freezer_max_f, cook_min_f, reheat_min_f,
                   hot_hold_min_f, cold_hold_max_f
            FROM ehc_outlet
            WHERE organization_id = %s
              AND is_active = true
              AND daily_monitoring_enabled = true
            ORDER BY sort_order, name
        """, (org_id,))

        outlets = dicts_from_rows(cursor.fetchall())
        return {"data": outlets, "count": len(outlets)}


@router.get("/worksheet/{outlet_name}/{date_str}")
def get_or_create_worksheet(
    outlet_name: str,
    date_str: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get or create a daily worksheet for the given outlet and date.
    Also returns the outlet configuration and pre-populated reading slots.
    """
    org_id = current_user["organization_id"]

    # Parse date
    try:
        worksheet_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get outlet config
        cursor.execute("""
            SELECT id, name, full_name, outlet_type,
                   cooler_count, freezer_count,
                   has_cooking, has_cooling, has_thawing,
                   has_hot_buffet, has_cold_buffet,
                   serves_breakfast, serves_lunch, serves_dinner,
                   readings_per_service,
                   cooler_max_f, freezer_max_f, cook_min_f, reheat_min_f,
                   hot_hold_min_f, cold_hold_max_f,
                   daily_monitoring_enabled
            FROM ehc_outlet
            WHERE organization_id = %s
              AND name = %s
              AND is_active = true
        """, (org_id, outlet_name))

        outlet = dict_from_row(cursor.fetchone())
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet not found")

        if not outlet.get("daily_monitoring_enabled"):
            raise HTTPException(status_code=400, detail="Daily monitoring not enabled for this outlet")

        # Get or create worksheet
        cursor.execute("""
            SELECT id, outlet_name, worksheet_date, status,
                   approved_by, approved_at, created_at, updated_at
            FROM daily_worksheet
            WHERE organization_id = %s
              AND outlet_name = %s
              AND worksheet_date = %s
        """, (org_id, outlet_name, worksheet_date))

        worksheet = dict_from_row(cursor.fetchone())

        if not worksheet:
            # Create new worksheet
            cursor.execute("""
                INSERT INTO daily_worksheet (organization_id, outlet_name, worksheet_date)
                VALUES (%s, %s, %s)
                RETURNING id, outlet_name, worksheet_date, status,
                          approved_by, approved_at, created_at, updated_at
            """, (org_id, outlet_name, worksheet_date))

            worksheet = dict_from_row(cursor.fetchone())

            # Pre-create cooler reading slots based on outlet config
            _create_cooler_reading_slots(cursor, worksheet["id"], outlet)

            conn.commit()

        # Get all cooler readings for this worksheet
        cursor.execute("""
            SELECT id, unit_type, unit_number, shift,
                   temperature_f, is_flagged, corrective_action,
                   alice_ticket, recorded_by, signature_data, recorded_at,
                   created_at, updated_at
            FROM cooler_reading
            WHERE worksheet_id = %s
            ORDER BY unit_type, unit_number, shift
        """, (worksheet["id"],))

        readings = dicts_from_rows(cursor.fetchall())

        # Convert UUID to string for JSON serialization
        worksheet["id"] = str(worksheet["id"])
        for r in readings:
            r["id"] = str(r["id"])

        return {
            "worksheet": worksheet,
            "outlet": outlet,
            "cooler_readings": readings
        }


def _create_cooler_reading_slots(cursor, worksheet_id, outlet):
    """Pre-create empty reading slots for coolers and freezers."""
    slots = []

    # Create cooler slots
    for i in range(1, outlet.get("cooler_count", 0) + 1):
        for shift in ["am", "pm"]:
            slots.append((worksheet_id, "cooler", i, shift))

    # Create freezer slots
    for i in range(1, outlet.get("freezer_count", 0) + 1):
        for shift in ["am", "pm"]:
            slots.append((worksheet_id, "freezer", i, shift))

    if slots:
        # Batch insert
        values_template = ",".join(["(%s, %s, %s, %s)"] * len(slots))
        flat_values = [item for slot in slots for item in slot]

        cursor.execute(f"""
            INSERT INTO cooler_reading (worksheet_id, unit_type, unit_number, shift)
            VALUES {values_template}
            ON CONFLICT (worksheet_id, unit_type, unit_number, shift) DO NOTHING
        """, flat_values)


@router.put("/worksheet/{worksheet_id}/coolers/{unit_type}/{unit_number}/{shift}")
def update_cooler_reading(
    worksheet_id: str,
    unit_type: str,
    unit_number: int,
    shift: str,
    reading: CoolerReadingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a single cooler/freezer reading.
    Auto-saves on each field change. Auto-flags if temperature exceeds threshold.
    """
    org_id = current_user["organization_id"]

    # Validate inputs
    if unit_type not in ["cooler", "freezer"]:
        raise HTTPException(status_code=400, detail="unit_type must be 'cooler' or 'freezer'")
    if shift not in ["am", "pm"]:
        raise HTTPException(status_code=400, detail="shift must be 'am' or 'pm'")

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify worksheet ownership and get outlet config
        cursor.execute("""
            SELECT dw.id, dw.outlet_name, dw.status,
                   o.cooler_max_f, o.freezer_max_f
            FROM daily_worksheet dw
            JOIN ehc_outlet o ON o.organization_id = dw.organization_id
                              AND o.name = dw.outlet_name
            WHERE dw.id = %s AND dw.organization_id = %s
        """, (ws_uuid, org_id))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="Worksheet not found")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        # Get threshold for this unit type
        threshold = ws_data["cooler_max_f"] if unit_type == "cooler" else ws_data["freezer_max_f"]

        # Check if reading exceeds threshold (cooler/freezer max temps)
        is_flagged = False
        if reading.temperature_f is not None and threshold is not None:
            # Cooler/freezer readings flag if ABOVE max
            is_flagged = float(reading.temperature_f) > float(threshold)

        # Build update
        updates = ["updated_at = NOW()"]
        params = []

        if reading.temperature_f is not None:
            updates.append("temperature_f = %s")
            params.append(reading.temperature_f)
            updates.append("is_flagged = %s")
            params.append(is_flagged)
            updates.append("recorded_at = COALESCE(recorded_at, NOW())")

        if reading.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(reading.corrective_action)

        if reading.alice_ticket is not None:
            updates.append("alice_ticket = %s")
            params.append(reading.alice_ticket)

        if reading.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(reading.recorded_by)

        params.extend([ws_uuid, unit_type, unit_number, shift])

        cursor.execute(f"""
            UPDATE cooler_reading
            SET {", ".join(updates)}
            WHERE worksheet_id = %s
              AND unit_type = %s
              AND unit_number = %s
              AND shift = %s
            RETURNING id, unit_type, unit_number, shift,
                      temperature_f, is_flagged, corrective_action,
                      alice_ticket, recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        if not result:
            raise HTTPException(status_code=404, detail="Reading slot not found")

        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.post("/worksheet/{worksheet_id}/coolers/sign")
def sign_cooler_readings(
    worksheet_id: str,
    sign_request: CoolerSignRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Sign a shift's cooler readings.
    Applies signature to all readings for that shift.
    """
    org_id = current_user["organization_id"]

    if sign_request.shift not in ["am", "pm"]:
        raise HTTPException(status_code=400, detail="shift must be 'am' or 'pm'")

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify worksheet ownership
        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="Worksheet not found")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot sign approved worksheet")

        # Update all readings for this shift with signature
        cursor.execute("""
            UPDATE cooler_reading
            SET signature_data = %s,
                recorded_by = COALESCE(recorded_by, %s),
                updated_at = NOW()
            WHERE worksheet_id = %s AND shift = %s
            RETURNING id
        """, (sign_request.signature_data, sign_request.recorded_by, ws_uuid, sign_request.shift))

        updated_count = cursor.rowcount
        conn.commit()

        return {
            "status": "ok",
            "shift": sign_request.shift,
            "readings_signed": updated_count
        }


@router.patch("/worksheet/{worksheet_id}")
def update_worksheet_status(
    worksheet_id: str,
    update: WorksheetStatusUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update worksheet status (for manager review/approval)."""
    org_id = current_user["organization_id"]
    user_id = current_user["id"]

    if update.status not in ["open", "review", "approved"]:
        raise HTTPException(status_code=400, detail="status must be 'open', 'review', or 'approved'")

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify worksheet ownership
        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="Worksheet not found")

        # Build update
        updates = ["status = %s", "updated_at = NOW()"]
        params = [update.status]

        if update.status == "approved":
            updates.append("approved_by = %s")
            updates.append("approved_at = NOW()")
            params.append(user_id)
        elif update.status == "open":
            # Unapproving - clear approval fields
            updates.append("approved_by = NULL")
            updates.append("approved_at = NULL")

        params.append(ws_uuid)
        params.append(org_id)

        cursor.execute(f"""
            UPDATE daily_worksheet
            SET {", ".join(updates)}
            WHERE id = %s AND organization_id = %s
            RETURNING id, outlet_name, worksheet_date, status,
                      approved_by, approved_at, created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.get("/calendar/{outlet_name}/{year}/{month}")
def get_monthly_calendar(
    outlet_name: str,
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get monthly calendar view with worksheet status for each day.
    Returns status and completion info for each day.
    """
    org_id = current_user["organization_id"]

    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get all worksheets for this outlet/month
        cursor.execute("""
            SELECT dw.id, dw.worksheet_date, dw.status,
                   dw.approved_by, dw.approved_at,
                   COUNT(cr.id) as total_readings,
                   COUNT(cr.temperature_f) as completed_readings,
                   SUM(CASE WHEN cr.is_flagged THEN 1 ELSE 0 END) as flagged_count,
                   COUNT(DISTINCT CASE WHEN cr.signature_data IS NOT NULL THEN cr.shift END) as signed_shifts
            FROM daily_worksheet dw
            LEFT JOIN cooler_reading cr ON cr.worksheet_id = dw.id
            WHERE dw.organization_id = %s
              AND dw.outlet_name = %s
              AND EXTRACT(YEAR FROM dw.worksheet_date) = %s
              AND EXTRACT(MONTH FROM dw.worksheet_date) = %s
            GROUP BY dw.id
            ORDER BY dw.worksheet_date
        """, (org_id, outlet_name, year, month))

        worksheets = dicts_from_rows(cursor.fetchall())

        # Convert to dict by date for easy lookup
        calendar_data = {}
        for ws in worksheets:
            date_key = ws["worksheet_date"].isoformat()
            ws["id"] = str(ws["id"])
            calendar_data[date_key] = ws

        return {
            "outlet_name": outlet_name,
            "year": year,
            "month": month,
            "days": calendar_data
        }
