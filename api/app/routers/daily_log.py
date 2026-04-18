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
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid
import secrets

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user
from ..utils.qr_generator import generate_daily_log_url, generate_daily_log_qr, generate_qr_code_bytes


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


class CookingRecordCreate(BaseModel):
    """Create a cooking/reheat/holding entry."""
    meal_period: str  # 'breakfast' | 'lunch' | 'dinner'
    entry_type: str  # 'cook' | 'reheat' | 'hot_hold' | 'cold_hold'
    item_name: Optional[str] = None
    temperature_f: Optional[Decimal] = None
    time_recorded: Optional[str] = None  # HH:MM format
    recorded_by: Optional[str] = None


class CookingRecordUpdate(BaseModel):
    """Update a cooking record."""
    item_name: Optional[str] = None
    temperature_f: Optional[Decimal] = None
    time_recorded: Optional[str] = None
    corrective_action: Optional[str] = None
    alice_ticket: Optional[str] = None
    recorded_by: Optional[str] = None


class CoolingRecordCreate(BaseModel):
    """Create a cooling log entry."""
    item_name: str
    start_time: Optional[str] = None  # HH:MM format
    method: Optional[str] = None  # 'ambient' | 'blast_chill' | 'ice_bath' | 'shallow_pan'
    recorded_by: Optional[str] = None


class CoolingRecordUpdate(BaseModel):
    """Update a cooling record."""
    item_name: Optional[str] = None
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None  # HH:MM format
    temp_2hr_f: Optional[Decimal] = None
    temp_6hr_f: Optional[Decimal] = None
    method: Optional[str] = None
    corrective_action: Optional[str] = None
    alice_ticket: Optional[str] = None
    recorded_by: Optional[str] = None


class ThawingRecordCreate(BaseModel):
    """Create a thawing log entry."""
    item_name: str
    start_time: Optional[str] = None  # HH:MM format
    method: Optional[str] = None  # 'walkin' | 'running_water' | 'microwave' | 'cooking'
    recorded_by: Optional[str] = None


class ThawingRecordUpdate(BaseModel):
    """Update a thawing record."""
    item_name: Optional[str] = None
    start_time: Optional[str] = None  # HH:MM format
    finish_date: Optional[date] = None
    finish_time: Optional[str] = None  # HH:MM format
    finish_temp_f: Optional[Decimal] = None
    method: Optional[str] = None
    corrective_action: Optional[str] = None
    alice_ticket: Optional[str] = None
    recorded_by: Optional[str] = None


class MealPeriodSignRequest(BaseModel):
    """Sign a meal period's cooking records."""
    meal_period: str  # 'breakfast' | 'lunch' | 'dinner'
    recorded_by: str
    signature_data: str


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
                   hot_hold_min_f, cold_hold_max_f,
                   daily_log_token
            FROM ehc_outlet
            WHERE organization_id = %s
              AND is_active = true
              AND daily_monitoring_enabled = true
            ORDER BY sort_order, name
        """, (org_id,))

        outlets = dicts_from_rows(cursor.fetchall())
        return {"data": outlets, "count": len(outlets)}


@router.post("/outlets/{outlet_name}/generate-token")
def generate_outlet_token(
    outlet_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate or regenerate the daily log access token for an outlet.
    Returns the token, QR code URL, and QR code image (base64).
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify outlet exists and belongs to org
        cursor.execute("""
            SELECT id, daily_monitoring_enabled
            FROM ehc_outlet
            WHERE organization_id = %s AND name = %s AND is_active = true
        """, (org_id, outlet_name))

        outlet = dict_from_row(cursor.fetchone())
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet not found")

        if not outlet["daily_monitoring_enabled"]:
            raise HTTPException(status_code=400, detail="Daily monitoring not enabled for this outlet")

        # Generate new token
        new_token = secrets.token_urlsafe(32)  # 43-char URL-safe token

        # Update outlet with new token
        cursor.execute("""
            UPDATE ehc_outlet
            SET daily_log_token = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING daily_log_token
        """, (new_token, outlet["id"]))

        conn.commit()

        # Generate QR code
        url = generate_daily_log_url(new_token)
        qr_base64 = generate_daily_log_qr(new_token)

        return {
            "outlet_name": outlet_name,
            "token": new_token,
            "url": url,
            "qr_code": qr_base64
        }


@router.get("/outlets/{outlet_name}/qr-code")
def get_outlet_qr_code(
    outlet_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the QR code image for an outlet's daily log.
    Returns PNG image directly.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT daily_log_token
            FROM ehc_outlet
            WHERE organization_id = %s AND name = %s
              AND is_active = true AND daily_monitoring_enabled = true
        """, (org_id, outlet_name))

        outlet = dict_from_row(cursor.fetchone())
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet not found")

        if not outlet["daily_log_token"]:
            raise HTTPException(status_code=400, detail="Token not generated. Call generate-token first.")

        url = generate_daily_log_url(outlet["daily_log_token"])
        qr_bytes = generate_qr_code_bytes(url, box_size=10)

        return Response(
            content=qr_bytes,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={outlet_name}-daily-log-qr.png"}
        )


@router.get("/calendar/{outlet_name}/{year}/{month}")
def get_monthly_calendar(
    outlet_name: str,
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get monthly calendar data for an outlet showing completion status per day.

    Returns each day's status:
    - worksheet_id: ID if exists
    - has_cooler_data: bool
    - am_signed: bool (for cooler temps)
    - pm_signed: bool (for cooler temps)
    - cooking_signed: dict of meal periods signed
    - has_flags: any readings flagged
    - completion_status: 'complete', 'partial', 'empty', 'flagged'
    """
    import calendar
    from datetime import date as date_type

    org_id = current_user["organization_id"]

    # Validate month/year
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Invalid month")
    if year < 2020 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get outlet config
        cursor.execute("""
            SELECT id, name, full_name, outlet_type,
                   cooler_count, freezer_count,
                   has_cooking, serves_breakfast, serves_lunch, serves_dinner
            FROM ehc_outlet
            WHERE organization_id = %s AND name = %s
              AND is_active = true AND daily_monitoring_enabled = true
        """, (org_id, outlet_name))

        outlet = dict_from_row(cursor.fetchone())
        if not outlet:
            raise HTTPException(status_code=404, detail="Outlet not found")

        # Calculate date range for month
        _, last_day = calendar.monthrange(year, month)
        start_date = date_type(year, month, 1)
        end_date = date_type(year, month, last_day)

        # Determine what signatures are required for this outlet
        has_coolers = (outlet["cooler_count"] or 0) > 0 or (outlet["freezer_count"] or 0) > 0
        has_cooking = outlet["has_cooking"]
        active_meals = []
        if outlet["serves_breakfast"]:
            active_meals.append("breakfast")
        if outlet["serves_lunch"]:
            active_meals.append("lunch")
        if outlet["serves_dinner"]:
            active_meals.append("dinner")

        # Get all worksheets for the month
        cursor.execute("""
            SELECT id, worksheet_date, status
            FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s
              AND worksheet_date >= %s AND worksheet_date <= %s
        """, (org_id, outlet_name, start_date, end_date))

        worksheets = {row["worksheet_date"]: row for row in dicts_from_rows(cursor.fetchall())}

        # Get cooler reading signatures for the month
        cooler_sigs = {}
        if has_coolers and worksheets:
            worksheet_ids = [w["id"] for w in worksheets.values()]
            cursor.execute("""
                SELECT cr.worksheet_id, cr.shift,
                       bool_or(cr.signature_data IS NOT NULL) as is_signed,
                       bool_or(cr.is_flagged) as has_flags
                FROM cooler_reading cr
                WHERE cr.worksheet_id = ANY(%s)
                GROUP BY cr.worksheet_id, cr.shift
            """, (worksheet_ids,))

            for row in dicts_from_rows(cursor.fetchall()):
                ws_id = row["worksheet_id"]
                if ws_id not in cooler_sigs:
                    cooler_sigs[ws_id] = {"am": False, "pm": False, "flags": False}
                cooler_sigs[ws_id][row["shift"]] = row["is_signed"]
                if row["has_flags"]:
                    cooler_sigs[ws_id]["flags"] = True

        # Get cooking record signatures for the month
        cooking_sigs = {}
        if has_cooking and worksheets:
            worksheet_ids = [w["id"] for w in worksheets.values()]
            cursor.execute("""
                SELECT cr.worksheet_id, cr.meal_period,
                       bool_or(cr.signature_data IS NOT NULL) as is_signed,
                       bool_or(cr.is_flagged) as has_flags
                FROM cooking_record cr
                WHERE cr.worksheet_id = ANY(%s)
                GROUP BY cr.worksheet_id, cr.meal_period
            """, (worksheet_ids,))

            for row in dicts_from_rows(cursor.fetchall()):
                ws_id = row["worksheet_id"]
                if ws_id not in cooking_sigs:
                    cooking_sigs[ws_id] = {m: False for m in active_meals}
                    cooking_sigs[ws_id]["flags"] = False
                if row["meal_period"] in active_meals:
                    cooking_sigs[ws_id][row["meal_period"]] = row["is_signed"]
                if row["has_flags"]:
                    cooking_sigs[ws_id]["flags"] = True

        # Build day-by-day status
        days = []
        today = date_type.today()

        for day in range(1, last_day + 1):
            current_date = date_type(year, month, day)
            worksheet = worksheets.get(current_date)

            day_data = {
                "date": current_date.isoformat(),
                "day": day,
                "weekday": current_date.strftime("%a"),
                "is_future": current_date > today,
                "is_today": current_date == today,
                "worksheet_id": worksheet["id"] if worksheet else None,
                "status": "empty"
            }

            if current_date > today:
                day_data["status"] = "future"
            elif worksheet:
                ws_id = worksheet["id"]
                has_flags = False
                sigs_required = 0
                sigs_present = 0

                # Check cooler signatures
                if has_coolers:
                    sigs_required += 2  # AM + PM
                    cs = cooler_sigs.get(ws_id, {})
                    if cs.get("am"):
                        sigs_present += 1
                    if cs.get("pm"):
                        sigs_present += 1
                    if cs.get("flags"):
                        has_flags = True

                # Check cooking signatures
                if has_cooking:
                    sigs_required += len(active_meals)
                    ck = cooking_sigs.get(ws_id, {})
                    for meal in active_meals:
                        if ck.get(meal):
                            sigs_present += 1
                    if ck.get("flags"):
                        has_flags = True

                # Determine status
                if sigs_required == 0:
                    day_data["status"] = "empty"
                elif sigs_present == sigs_required:
                    day_data["status"] = "flagged" if has_flags else "complete"
                elif sigs_present > 0:
                    day_data["status"] = "partial"
                else:
                    day_data["status"] = "empty"

                day_data["sigs_present"] = sigs_present
                day_data["sigs_required"] = sigs_required
                day_data["has_flags"] = has_flags

            days.append(day_data)

        # Calculate summary stats
        complete_days = sum(1 for d in days if d["status"] == "complete")
        partial_days = sum(1 for d in days if d["status"] == "partial")
        flagged_days = sum(1 for d in days if d["status"] == "flagged")
        empty_days = sum(1 for d in days if d["status"] == "empty")
        past_days = sum(1 for d in days if not d.get("is_future", True))

        return {
            "outlet": {
                "id": outlet["id"],
                "name": outlet["name"],
                "full_name": outlet["full_name"],
                "has_coolers": has_coolers,
                "has_cooking": has_cooking,
                "active_meals": active_meals
            },
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "days": days,
            "summary": {
                "complete": complete_days,
                "partial": partial_days,
                "flagged": flagged_days,
                "empty": empty_days,
                "past_days": past_days,
                "completion_rate": round((complete_days + flagged_days) / past_days * 100, 1) if past_days > 0 else 0
            }
        }


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

        cooler_readings = dicts_from_rows(cursor.fetchall())

        # Get cooking records (table may not exist if migration 044 hasn't run)
        cooking_records = []
        try:
            cursor.execute("""
                SELECT id, meal_period, entry_type, slot_number,
                       item_name, temperature_f, time_recorded,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM cooking_record
                WHERE worksheet_id = %s
                ORDER BY meal_period, entry_type, slot_number
            """, (worksheet["id"],))
            cooking_records = dicts_from_rows(cursor.fetchall())
        except Exception as e:
            print(f"Warning: Could not fetch cooking_records: {e}")
            conn.rollback()

        # Get cooling records
        cooling_records = []
        try:
            cursor.execute("""
                SELECT id, item_name, start_time, end_time,
                       temp_2hr_f, temp_6hr_f, method,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM cooling_record
                WHERE worksheet_id = %s
                ORDER BY created_at
            """, (worksheet["id"],))
            cooling_records = dicts_from_rows(cursor.fetchall())
        except Exception as e:
            print(f"Warning: Could not fetch cooling_records: {e}")
            conn.rollback()

        # Get thawing records
        thawing_records = []
        try:
            cursor.execute("""
                SELECT id, item_name, start_time,
                       finish_date, finish_time, finish_temp_f, method,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM thawing_record
                WHERE worksheet_id = %s
                ORDER BY created_at
            """, (worksheet["id"],))
            thawing_records = dicts_from_rows(cursor.fetchall())
        except Exception as e:
            print(f"Warning: Could not fetch thawing_records: {e}")
            conn.rollback()

        # Convert UUID to string for JSON serialization
        worksheet["id"] = str(worksheet["id"])
        for r in cooler_readings:
            r["id"] = str(r["id"])
        for r in cooking_records:
            r["id"] = str(r["id"])
        for r in cooling_records:
            r["id"] = str(r["id"])
        for r in thawing_records:
            r["id"] = str(r["id"])

        return {
            "worksheet": worksheet,
            "outlet": outlet,
            "cooler_readings": cooler_readings,
            "cooking_records": cooking_records,
            "cooling_records": cooling_records,
            "thawing_records": thawing_records
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


# ============================================
# Cooking Records (Records 4 & 6)
# ============================================

@router.get("/worksheet/{worksheet_id}/cooking")
def list_cooking_records(
    worksheet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all cooking/reheat/holding entries for a worksheet."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify worksheet ownership
        cursor.execute("""
            SELECT id FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Worksheet not found")

        cursor.execute("""
            SELECT id, meal_period, entry_type, slot_number,
                   item_name, temperature_f, time_recorded,
                   is_flagged, corrective_action, alice_ticket,
                   recorded_by, signature_data, recorded_at,
                   created_at, updated_at
            FROM cooking_record
            WHERE worksheet_id = %s
            ORDER BY meal_period, entry_type, slot_number
        """, (ws_uuid,))

        records = dicts_from_rows(cursor.fetchall())
        for r in records:
            r["id"] = str(r["id"])

        return {"data": records, "count": len(records)}


@router.post("/worksheet/{worksheet_id}/cooking")
def create_cooking_record(
    worksheet_id: str,
    record: CookingRecordCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new cooking/reheat/holding entry."""
    org_id = current_user["organization_id"]

    if record.meal_period not in ["breakfast", "lunch", "dinner"]:
        raise HTTPException(status_code=400, detail="meal_period must be 'breakfast', 'lunch', or 'dinner'")
    if record.entry_type not in ["cook", "reheat", "hot_hold", "cold_hold"]:
        raise HTTPException(status_code=400, detail="entry_type must be 'cook', 'reheat', 'hot_hold', or 'cold_hold'")

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Verify worksheet ownership and get thresholds
            cursor.execute("""
                SELECT dw.id, dw.status,
                       o.cook_min_f, o.reheat_min_f, o.hot_hold_min_f, o.cold_hold_max_f
                FROM daily_worksheet dw
                JOIN ehc_outlet o ON o.organization_id = dw.organization_id
                                  AND o.name = dw.outlet_name
                WHERE dw.id = %s AND dw.organization_id = %s
            """, (ws_uuid, org_id))

            ws_data = dict_from_row(cursor.fetchone())
            if not ws_data:
                raise HTTPException(status_code=404, detail="Worksheet not found")

            if ws_data["status"] == "approved":
                raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

            # Get next slot number
            cursor.execute("""
                SELECT COALESCE(MAX(slot_number), 0) + 1 AS next_slot
                FROM cooking_record
                WHERE worksheet_id = %s AND meal_period = %s AND entry_type = %s
            """, (ws_uuid, record.meal_period, record.entry_type))
            slot_number = cursor.fetchone()["next_slot"]

            # Check flagging based on entry type
            is_flagged = False
            if record.temperature_f is not None:
                temp = float(record.temperature_f)
                if record.entry_type == "cook" and ws_data["cook_min_f"]:
                    is_flagged = temp < float(ws_data["cook_min_f"])
                elif record.entry_type == "reheat" and ws_data["reheat_min_f"]:
                    is_flagged = temp < float(ws_data["reheat_min_f"])
                elif record.entry_type == "hot_hold" and ws_data["hot_hold_min_f"]:
                    is_flagged = temp < float(ws_data["hot_hold_min_f"])
                elif record.entry_type == "cold_hold" and ws_data["cold_hold_max_f"]:
                    is_flagged = temp > float(ws_data["cold_hold_max_f"])

            # Parse time if provided
            time_val = None
            if record.time_recorded:
                try:
                    time_val = datetime.strptime(record.time_recorded, "%H:%M").time()
                except ValueError:
                    raise HTTPException(status_code=400, detail="time_recorded must be HH:MM format")

            cursor.execute("""
                INSERT INTO cooking_record (
                    worksheet_id, meal_period, entry_type, slot_number,
                    item_name, temperature_f, time_recorded, is_flagged,
                    recorded_by, recorded_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, meal_period, entry_type, slot_number,
                          item_name, temperature_f, time_recorded,
                          is_flagged, corrective_action, alice_ticket,
                          recorded_by, signature_data, recorded_at,
                          created_at, updated_at
            """, (ws_uuid, record.meal_period, record.entry_type, slot_number,
                  record.item_name, record.temperature_f, time_val, is_flagged,
                  record.recorded_by))

            result = dict_from_row(cursor.fetchone())
            conn.commit()

            result["id"] = str(result["id"])
            return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in create_cooking_record: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}. If table doesn't exist, migration 044 may not have run."
        )


@router.put("/worksheet/{worksheet_id}/cooking/{record_id}")
def update_cooking_record(
    worksheet_id: str,
    record_id: str,
    record: CookingRecordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a cooking record."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership and get thresholds
        cursor.execute("""
            SELECT dw.status, cr.entry_type,
                   o.cook_min_f, o.reheat_min_f, o.hot_hold_min_f, o.cold_hold_max_f
            FROM daily_worksheet dw
            JOIN cooking_record cr ON cr.worksheet_id = dw.id
            JOIN ehc_outlet o ON o.organization_id = dw.organization_id
                              AND o.name = dw.outlet_name
            WHERE dw.id = %s AND dw.organization_id = %s AND cr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="Record not found")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        # Build update
        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.temperature_f is not None:
            updates.append("temperature_f = %s")
            params.append(record.temperature_f)

            # Check flagging
            temp = float(record.temperature_f)
            entry_type = ws_data["entry_type"]
            is_flagged = False
            if entry_type == "cook" and ws_data["cook_min_f"]:
                is_flagged = temp < float(ws_data["cook_min_f"])
            elif entry_type == "reheat" and ws_data["reheat_min_f"]:
                is_flagged = temp < float(ws_data["reheat_min_f"])
            elif entry_type == "hot_hold" and ws_data["hot_hold_min_f"]:
                is_flagged = temp < float(ws_data["hot_hold_min_f"])
            elif entry_type == "cold_hold" and ws_data["cold_hold_max_f"]:
                is_flagged = temp > float(ws_data["cold_hold_max_f"])

            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.time_recorded is not None:
            try:
                time_val = datetime.strptime(record.time_recorded, "%H:%M").time()
                updates.append("time_recorded = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="time_recorded must be HH:MM format")

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.alice_ticket is not None:
            updates.append("alice_ticket = %s")
            params.append(record.alice_ticket)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE cooking_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, meal_period, entry_type, slot_number,
                      item_name, temperature_f, time_recorded,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/worksheet/{worksheet_id}/cooking/{record_id}")
def delete_cooking_record(
    worksheet_id: str,
    record_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a cooking record."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooking_record cr ON cr.worksheet_id = dw.id
            WHERE dw.id = %s AND dw.organization_id = %s AND cr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM cooking_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}


@router.post("/worksheet/{worksheet_id}/cooking/sign")
def sign_cooking_records(
    worksheet_id: str,
    sign_request: MealPeriodSignRequest,
    current_user: dict = Depends(get_current_user)
):
    """Sign a meal period's cooking records."""
    org_id = current_user["organization_id"]

    if sign_request.meal_period not in ["breakfast", "lunch", "dinner"]:
        raise HTTPException(status_code=400, detail="meal_period must be 'breakfast', 'lunch', or 'dinner'")

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Worksheet not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot sign approved worksheet")

        cursor.execute("""
            UPDATE cooking_record
            SET signature_data = %s,
                recorded_by = COALESCE(recorded_by, %s),
                updated_at = NOW()
            WHERE worksheet_id = %s AND meal_period = %s
            RETURNING id
        """, (sign_request.signature_data, sign_request.recorded_by, ws_uuid, sign_request.meal_period))

        updated_count = cursor.rowcount
        conn.commit()

        return {
            "status": "ok",
            "meal_period": sign_request.meal_period,
            "records_signed": updated_count
        }


# ============================================
# Cooling Records (Record 5)
# ============================================

@router.get("/worksheet/{worksheet_id}/cooling")
def list_cooling_records(
    worksheet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all cooling log entries for a worksheet."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Worksheet not found")

        cursor.execute("""
            SELECT id, item_name, start_time, end_time,
                   temp_2hr_f, temp_6hr_f, method,
                   is_flagged, corrective_action, alice_ticket,
                   recorded_by, signature_data, recorded_at,
                   created_at, updated_at
            FROM cooling_record
            WHERE worksheet_id = %s
            ORDER BY created_at
        """, (ws_uuid,))

        records = dicts_from_rows(cursor.fetchall())
        for r in records:
            r["id"] = str(r["id"])

        return {"data": records, "count": len(records)}


@router.post("/worksheet/{worksheet_id}/cooling")
def create_cooling_record(
    worksheet_id: str,
    record: CoolingRecordCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new cooling log entry."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status FROM daily_worksheet
                WHERE id = %s AND organization_id = %s
            """, (ws_uuid, org_id))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Worksheet not found")

            if row["status"] == "approved":
                raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

            # Parse start_time if provided - combine with today's date for timestamp column
            start_time_val = None
            if record.start_time:
                try:
                    time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                    start_time_val = datetime.combine(date.today(), time_parsed)
                except ValueError:
                    raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

            cursor.execute("""
                INSERT INTO cooling_record (
                    worksheet_id, item_name, method, recorded_by,
                    start_time, recorded_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id, item_name, start_time, end_time,
                          temp_2hr_f, temp_6hr_f, method,
                          is_flagged, corrective_action, alice_ticket,
                          recorded_by, signature_data, recorded_at,
                          created_at, updated_at
            """, (ws_uuid, record.item_name, record.method, record.recorded_by, start_time_val))

            result = dict_from_row(cursor.fetchone())
            conn.commit()

            result["id"] = str(result["id"])
            return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in create_cooling_record: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}. If table doesn't exist, migration 044 may not have run."
        )


@router.put("/worksheet/{worksheet_id}/cooling/{record_id}")
def update_cooling_record(
    worksheet_id: str,
    record_id: str,
    record: CoolingRecordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a cooling record. Auto-flags if temps exceed thresholds."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooling_record cr ON cr.worksheet_id = dw.id
            WHERE dw.id = %s AND dw.organization_id = %s AND cr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        # Build update
        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.start_time is not None:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("start_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        if record.end_time is not None:
            try:
                time_parsed = datetime.strptime(record.end_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("end_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="end_time must be HH:MM format")

        # Check flagging for temp thresholds
        # 2hr must be <= 70F, 6hr must be <= 41F
        is_flagged = False
        if record.temp_2hr_f is not None:
            updates.append("temp_2hr_f = %s")
            params.append(record.temp_2hr_f)
            if float(record.temp_2hr_f) > 70.0:
                is_flagged = True

        if record.temp_6hr_f is not None:
            updates.append("temp_6hr_f = %s")
            params.append(record.temp_6hr_f)
            if float(record.temp_6hr_f) > 41.0:
                is_flagged = True

        if record.temp_2hr_f is not None or record.temp_6hr_f is not None:
            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.method is not None:
            updates.append("method = %s")
            params.append(record.method)

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.alice_ticket is not None:
            updates.append("alice_ticket = %s")
            params.append(record.alice_ticket)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE cooling_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, item_name, start_time, end_time,
                      temp_2hr_f, temp_6hr_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/worksheet/{worksheet_id}/cooling/{record_id}")
def delete_cooling_record(
    worksheet_id: str,
    record_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a cooling record."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooling_record cr ON cr.worksheet_id = dw.id
            WHERE dw.id = %s AND dw.organization_id = %s AND cr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM cooling_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}


# ============================================
# Thawing Records (Record 12)
# ============================================

@router.get("/worksheet/{worksheet_id}/thawing")
def list_thawing_records(
    worksheet_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all thawing log entries for a worksheet."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM daily_worksheet
            WHERE id = %s AND organization_id = %s
        """, (ws_uuid, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Worksheet not found")

        cursor.execute("""
            SELECT id, item_name, start_time,
                   finish_date, finish_time, finish_temp_f, method,
                   is_flagged, corrective_action, alice_ticket,
                   recorded_by, signature_data, recorded_at,
                   created_at, updated_at
            FROM thawing_record
            WHERE worksheet_id = %s
            ORDER BY created_at
        """, (ws_uuid,))

        records = dicts_from_rows(cursor.fetchall())
        for r in records:
            r["id"] = str(r["id"])

        return {"data": records, "count": len(records)}


@router.post("/worksheet/{worksheet_id}/thawing")
def create_thawing_record(
    worksheet_id: str,
    record: ThawingRecordCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new thawing log entry."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid worksheet ID")

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status FROM daily_worksheet
                WHERE id = %s AND organization_id = %s
            """, (ws_uuid, org_id))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Worksheet not found")

            if row["status"] == "approved":
                raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

            # Parse start_time if provided - combine with today's date for timestamp column
            start_time_val = None
            if record.start_time:
                try:
                    time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                    start_time_val = datetime.combine(date.today(), time_parsed)
                except ValueError:
                    raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

            cursor.execute("""
                INSERT INTO thawing_record (
                    worksheet_id, item_name, method, recorded_by,
                    start_time, recorded_at
                ) VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id, item_name, start_time,
                          finish_date, finish_time, finish_temp_f, method,
                          is_flagged, corrective_action, alice_ticket,
                          recorded_by, signature_data, recorded_at,
                          created_at, updated_at
            """, (ws_uuid, record.item_name, record.method, record.recorded_by, start_time_val))

            result = dict_from_row(cursor.fetchone())
            conn.commit()

            result["id"] = str(result["id"])
            return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in create_thawing_record: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}. If table doesn't exist, migration 044 may not have run."
        )


@router.put("/worksheet/{worksheet_id}/thawing/{record_id}")
def update_thawing_record(
    worksheet_id: str,
    record_id: str,
    record: ThawingRecordUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a thawing record. Auto-flags if finish temp > 41F."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN thawing_record tr ON tr.worksheet_id = dw.id
            WHERE dw.id = %s AND dw.organization_id = %s AND tr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        # Build update
        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.start_time is not None:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("start_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        if record.finish_date is not None:
            updates.append("finish_date = %s")
            params.append(record.finish_date)

        if record.finish_time is not None:
            try:
                time_val = datetime.strptime(record.finish_time, "%H:%M").time()
                updates.append("finish_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="finish_time must be HH:MM format")

        if record.finish_temp_f is not None:
            updates.append("finish_temp_f = %s")
            params.append(record.finish_temp_f)
            # Flag if > 41F
            is_flagged = float(record.finish_temp_f) > 41.0
            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.method is not None:
            updates.append("method = %s")
            params.append(record.method)

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.alice_ticket is not None:
            updates.append("alice_ticket = %s")
            params.append(record.alice_ticket)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE thawing_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, item_name, start_time,
                      finish_date, finish_time, finish_temp_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/worksheet/{worksheet_id}/thawing/{record_id}")
def delete_thawing_record(
    worksheet_id: str,
    record_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a thawing record."""
    org_id = current_user["organization_id"]

    try:
        ws_uuid = uuid.UUID(worksheet_id)
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN thawing_record tr ON tr.worksheet_id = dw.id
            WHERE dw.id = %s AND dw.organization_id = %s AND tr.id = %s
        """, (ws_uuid, org_id, rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM thawing_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}


# ============================================
# PUBLIC ENDPOINTS (Token-based, No Auth)
# ============================================
# These endpoints allow kitchen staff to access daily logs
# via QR code without logging in. Access controlled by token.

def _get_outlet_by_token(cursor, token: str):
    """Look up outlet by daily_log_token. Returns outlet dict or None."""
    cursor.execute("""
        SELECT id, organization_id, name, full_name, outlet_type,
               cooler_count, freezer_count,
               has_cooking, has_cooling, has_thawing,
               has_hot_buffet, has_cold_buffet,
               serves_breakfast, serves_lunch, serves_dinner,
               readings_per_service,
               cooler_max_f, freezer_max_f, cook_min_f, reheat_min_f,
               hot_hold_min_f, cold_hold_max_f,
               daily_monitoring_enabled
        FROM ehc_outlet
        WHERE daily_log_token = %s
          AND is_active = true
          AND daily_monitoring_enabled = true
    """, (token,))
    return dict_from_row(cursor.fetchone())


@router.get("/public/{token}")
def get_public_worksheet_today(token: str):
    """
    Get today's worksheet for public access. No authentication required.
    Creates worksheet if it doesn't exist.
    """
    today = date.today()
    return get_public_worksheet(token, today.isoformat())


@router.get("/public/{token}/{date_str}")
def get_public_worksheet(token: str, date_str: str):
    """
    Get or create a daily worksheet for public access.
    No authentication required - uses token for access control.
    """
    # Parse date
    try:
        worksheet_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get outlet by token
        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        org_id = outlet["organization_id"]
        outlet_name = outlet["name"]

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

            # Pre-create cooler reading slots
            _create_cooler_reading_slots(cursor, worksheet["id"], outlet)

            conn.commit()

        # Get all records
        cursor.execute("""
            SELECT id, unit_type, unit_number, shift,
                   temperature_f, is_flagged, corrective_action,
                   alice_ticket, recorded_by, signature_data, recorded_at,
                   created_at, updated_at
            FROM cooler_reading
            WHERE worksheet_id = %s
            ORDER BY unit_type, unit_number, shift
        """, (worksheet["id"],))
        cooler_readings = dicts_from_rows(cursor.fetchall())

        # Get cooking records (handle missing table gracefully)
        cooking_records = []
        try:
            cursor.execute("""
                SELECT id, meal_period, entry_type, slot_number,
                       item_name, temperature_f, time_recorded,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM cooking_record
                WHERE worksheet_id = %s
                ORDER BY meal_period, entry_type, slot_number
            """, (worksheet["id"],))
            cooking_records = dicts_from_rows(cursor.fetchall())
        except Exception:
            conn.rollback()

        # Get cooling records
        cooling_records = []
        try:
            cursor.execute("""
                SELECT id, item_name, start_time, end_time,
                       temp_2hr_f, temp_6hr_f, method,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM cooling_record
                WHERE worksheet_id = %s
                ORDER BY created_at
            """, (worksheet["id"],))
            cooling_records = dicts_from_rows(cursor.fetchall())
        except Exception:
            conn.rollback()

        # Get thawing records
        thawing_records = []
        try:
            cursor.execute("""
                SELECT id, item_name, start_time,
                       finish_date, finish_time, finish_temp_f, method,
                       is_flagged, corrective_action, alice_ticket,
                       recorded_by, signature_data, recorded_at,
                       created_at, updated_at
                FROM thawing_record
                WHERE worksheet_id = %s
                ORDER BY created_at
            """, (worksheet["id"],))
            thawing_records = dicts_from_rows(cursor.fetchall())
        except Exception:
            conn.rollback()

        # Convert UUIDs to strings
        worksheet["id"] = str(worksheet["id"])
        for r in cooler_readings:
            r["id"] = str(r["id"])
        for r in cooking_records:
            r["id"] = str(r["id"])
        for r in cooling_records:
            r["id"] = str(r["id"])
        for r in thawing_records:
            r["id"] = str(r["id"])

        return {
            "worksheet": worksheet,
            "outlet": outlet,
            "cooler_readings": cooler_readings,
            "cooking_records": cooking_records,
            "cooling_records": cooling_records,
            "thawing_records": thawing_records
        }


@router.put("/public/{token}/coolers/{unit_type}/{unit_number}/{shift}")
def update_public_cooler_reading(
    token: str,
    unit_type: str,
    unit_number: int,
    shift: str,
    reading: CoolerReadingUpdate
):
    """Update a cooler reading via public token access."""
    if unit_type not in ["cooler", "freezer"]:
        raise HTTPException(status_code=400, detail="unit_type must be 'cooler' or 'freezer'")
    if shift not in ["am", "pm"]:
        raise HTTPException(status_code=400, detail="shift must be 'am' or 'pm'")

    with get_db() as conn:
        cursor = conn.cursor()

        # Get outlet by token
        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        org_id = outlet["organization_id"]
        outlet_name = outlet["name"]
        today = date.today()

        # Get today's worksheet
        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (org_id, outlet_name, today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        ws_uuid = ws_data["id"]

        # Get threshold
        threshold = outlet["cooler_max_f"] if unit_type == "cooler" else outlet["freezer_max_f"]

        # Check flagging
        is_flagged = False
        if reading.temperature_f is not None and threshold is not None:
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


@router.post("/public/{token}/coolers/sign")
def sign_public_cooler_readings(token: str, sign_request: CoolerSignRequest):
    """Sign a shift's cooler readings via public token access."""
    if sign_request.shift not in ["am", "pm"]:
        raise HTTPException(status_code=400, detail="shift must be 'am' or 'pm'")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        org_id = outlet["organization_id"]
        outlet_name = outlet["name"]
        today = date.today()

        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (org_id, outlet_name, today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot sign approved worksheet")

        cursor.execute("""
            UPDATE cooler_reading
            SET signature_data = %s,
                recorded_by = COALESCE(recorded_by, %s),
                updated_at = NOW()
            WHERE worksheet_id = %s AND shift = %s
            RETURNING id
        """, (sign_request.signature_data, sign_request.recorded_by, ws_data["id"], sign_request.shift))

        updated_count = cursor.rowcount
        conn.commit()

        return {
            "status": "ok",
            "shift": sign_request.shift,
            "readings_signed": updated_count
        }


@router.post("/public/{token}/cooking")
def create_public_cooking_record(token: str, record: CookingRecordCreate):
    """Create a cooking record via public token access."""
    if record.meal_period not in ["breakfast", "lunch", "dinner"]:
        raise HTTPException(status_code=400, detail="meal_period must be 'breakfast', 'lunch', or 'dinner'")
    if record.entry_type not in ["cook", "reheat", "hot_hold", "cold_hold"]:
        raise HTTPException(status_code=400, detail="entry_type must be 'cook', 'reheat', 'hot_hold', or 'cold_hold'")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        org_id = outlet["organization_id"]
        outlet_name = outlet["name"]
        today = date.today()

        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (org_id, outlet_name, today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

        ws_uuid = ws_data["id"]

        # Get next slot number
        cursor.execute("""
            SELECT COALESCE(MAX(slot_number), 0) + 1 AS next_slot
            FROM cooking_record
            WHERE worksheet_id = %s AND meal_period = %s AND entry_type = %s
        """, (ws_uuid, record.meal_period, record.entry_type))
        slot_number = cursor.fetchone()["next_slot"]

        # Check flagging
        is_flagged = False
        if record.temperature_f is not None:
            temp = float(record.temperature_f)
            if record.entry_type == "cook" and outlet["cook_min_f"]:
                is_flagged = temp < float(outlet["cook_min_f"])
            elif record.entry_type == "reheat" and outlet["reheat_min_f"]:
                is_flagged = temp < float(outlet["reheat_min_f"])
            elif record.entry_type == "hot_hold" and outlet["hot_hold_min_f"]:
                is_flagged = temp < float(outlet["hot_hold_min_f"])
            elif record.entry_type == "cold_hold" and outlet["cold_hold_max_f"]:
                is_flagged = temp > float(outlet["cold_hold_max_f"])

        time_val = None
        if record.time_recorded:
            try:
                time_val = datetime.strptime(record.time_recorded, "%H:%M").time()
            except ValueError:
                raise HTTPException(status_code=400, detail="time_recorded must be HH:MM format")

        cursor.execute("""
            INSERT INTO cooking_record (
                worksheet_id, meal_period, entry_type, slot_number,
                item_name, temperature_f, time_recorded, is_flagged,
                recorded_by, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id, meal_period, entry_type, slot_number,
                      item_name, temperature_f, time_recorded,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, (ws_uuid, record.meal_period, record.entry_type, slot_number,
              record.item_name, record.temperature_f, time_val, is_flagged,
              record.recorded_by))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.put("/public/{token}/cooking/{record_id}")
def update_public_cooking_record(token: str, record_id: str, record: CookingRecordUpdate):
    """Update a cooking record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        org_id = outlet["organization_id"]
        outlet_name = outlet["name"]

        # Verify record belongs to this outlet
        cursor.execute("""
            SELECT dw.status, cr.entry_type
            FROM daily_worksheet dw
            JOIN cooking_record cr ON cr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND cr.id = %s
        """, (org_id, outlet_name, rec_uuid))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="Record not found")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        # Build update
        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.temperature_f is not None:
            updates.append("temperature_f = %s")
            params.append(record.temperature_f)

            temp = float(record.temperature_f)
            entry_type = ws_data["entry_type"]
            is_flagged = False
            if entry_type == "cook" and outlet["cook_min_f"]:
                is_flagged = temp < float(outlet["cook_min_f"])
            elif entry_type == "reheat" and outlet["reheat_min_f"]:
                is_flagged = temp < float(outlet["reheat_min_f"])
            elif entry_type == "hot_hold" and outlet["hot_hold_min_f"]:
                is_flagged = temp < float(outlet["hot_hold_min_f"])
            elif entry_type == "cold_hold" and outlet["cold_hold_max_f"]:
                is_flagged = temp > float(outlet["cold_hold_max_f"])

            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.time_recorded is not None:
            try:
                time_val = datetime.strptime(record.time_recorded, "%H:%M").time()
                updates.append("time_recorded = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="time_recorded must be HH:MM format")

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE cooking_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, meal_period, entry_type, slot_number,
                      item_name, temperature_f, time_recorded,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/public/{token}/cooking/{record_id}")
def delete_public_cooking_record(token: str, record_id: str):
    """Delete a cooking record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooking_record cr ON cr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND cr.id = %s
        """, (outlet["organization_id"], outlet["name"], rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM cooking_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}


@router.post("/public/{token}/cooking/sign")
def sign_public_cooking_records(token: str, sign_request: MealPeriodSignRequest):
    """Sign a meal period's cooking records via public token access."""
    if sign_request.meal_period not in ["breakfast", "lunch", "dinner"]:
        raise HTTPException(status_code=400, detail="meal_period must be 'breakfast', 'lunch', or 'dinner'")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        today = date.today()

        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (outlet["organization_id"], outlet["name"], today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot sign approved worksheet")

        cursor.execute("""
            UPDATE cooking_record
            SET signature_data = %s,
                recorded_by = COALESCE(recorded_by, %s),
                updated_at = NOW()
            WHERE worksheet_id = %s AND meal_period = %s
            RETURNING id
        """, (sign_request.signature_data, sign_request.recorded_by, ws_data["id"], sign_request.meal_period))

        updated_count = cursor.rowcount
        conn.commit()

        return {
            "status": "ok",
            "meal_period": sign_request.meal_period,
            "records_signed": updated_count
        }


@router.post("/public/{token}/cooling")
def create_public_cooling_record(token: str, record: CoolingRecordCreate):
    """Create a cooling record via public token access."""
    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        today = date.today()

        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (outlet["organization_id"], outlet["name"], today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

        # Combine time with today's date for timestamp column
        start_time_val = None
        if record.start_time:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                start_time_val = datetime.combine(date.today(), time_parsed)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        cursor.execute("""
            INSERT INTO cooling_record (
                worksheet_id, item_name, method, recorded_by,
                start_time, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id, item_name, start_time, end_time,
                      temp_2hr_f, temp_6hr_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, (ws_data["id"], record.item_name, record.method, record.recorded_by, start_time_val))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.put("/public/{token}/cooling/{record_id}")
def update_public_cooling_record(token: str, record_id: str, record: CoolingRecordUpdate):
    """Update a cooling record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooling_record cr ON cr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND cr.id = %s
        """, (outlet["organization_id"], outlet["name"], rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.start_time is not None:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("start_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        if record.end_time is not None:
            try:
                time_parsed = datetime.strptime(record.end_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("end_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="end_time must be HH:MM format")

        is_flagged = False
        if record.temp_2hr_f is not None:
            updates.append("temp_2hr_f = %s")
            params.append(record.temp_2hr_f)
            if float(record.temp_2hr_f) > 70.0:
                is_flagged = True

        if record.temp_6hr_f is not None:
            updates.append("temp_6hr_f = %s")
            params.append(record.temp_6hr_f)
            if float(record.temp_6hr_f) > 41.0:
                is_flagged = True

        if record.temp_2hr_f is not None or record.temp_6hr_f is not None:
            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.method is not None:
            updates.append("method = %s")
            params.append(record.method)

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE cooling_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, item_name, start_time, end_time,
                      temp_2hr_f, temp_6hr_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/public/{token}/cooling/{record_id}")
def delete_public_cooling_record(token: str, record_id: str):
    """Delete a cooling record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN cooling_record cr ON cr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND cr.id = %s
        """, (outlet["organization_id"], outlet["name"], rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM cooling_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}


@router.post("/public/{token}/thawing")
def create_public_thawing_record(token: str, record: ThawingRecordCreate):
    """Create a thawing record via public token access."""
    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        today = date.today()

        cursor.execute("""
            SELECT id, status FROM daily_worksheet
            WHERE organization_id = %s AND outlet_name = %s AND worksheet_date = %s
        """, (outlet["organization_id"], outlet["name"], today))

        ws_data = dict_from_row(cursor.fetchone())
        if not ws_data:
            raise HTTPException(status_code=404, detail="No worksheet for today")

        if ws_data["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot add to approved worksheet")

        # Combine time with today's date for timestamp column
        start_time_val = None
        if record.start_time:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                start_time_val = datetime.combine(date.today(), time_parsed)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        cursor.execute("""
            INSERT INTO thawing_record (
                worksheet_id, item_name, method, recorded_by,
                start_time, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id, item_name, start_time,
                      finish_date, finish_time, finish_temp_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, (ws_data["id"], record.item_name, record.method, record.recorded_by, start_time_val))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.put("/public/{token}/thawing/{record_id}")
def update_public_thawing_record(token: str, record_id: str, record: ThawingRecordUpdate):
    """Update a thawing record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN thawing_record tr ON tr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND tr.id = %s
        """, (outlet["organization_id"], outlet["name"], rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot edit approved worksheet")

        updates = ["updated_at = NOW()"]
        params = []

        if record.item_name is not None:
            updates.append("item_name = %s")
            params.append(record.item_name)

        if record.start_time is not None:
            try:
                time_parsed = datetime.strptime(record.start_time, "%H:%M").time()
                time_val = datetime.combine(date.today(), time_parsed)
                updates.append("start_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="start_time must be HH:MM format")

        if record.finish_date is not None:
            updates.append("finish_date = %s")
            params.append(record.finish_date)

        if record.finish_time is not None:
            try:
                time_val = datetime.strptime(record.finish_time, "%H:%M").time()
                updates.append("finish_time = %s")
                params.append(time_val)
            except ValueError:
                raise HTTPException(status_code=400, detail="finish_time must be HH:MM format")

        if record.finish_temp_f is not None:
            updates.append("finish_temp_f = %s")
            params.append(record.finish_temp_f)
            is_flagged = float(record.finish_temp_f) > 41.0
            updates.append("is_flagged = %s")
            params.append(is_flagged)

        if record.method is not None:
            updates.append("method = %s")
            params.append(record.method)

        if record.corrective_action is not None:
            updates.append("corrective_action = %s")
            params.append(record.corrective_action)

        if record.recorded_by is not None:
            updates.append("recorded_by = %s")
            params.append(record.recorded_by)

        params.append(rec_uuid)

        cursor.execute(f"""
            UPDATE thawing_record
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, item_name, start_time,
                      finish_date, finish_time, finish_temp_f, method,
                      is_flagged, corrective_action, alice_ticket,
                      recorded_by, signature_data, recorded_at,
                      created_at, updated_at
        """, params)

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        result["id"] = str(result["id"])
        return result


@router.delete("/public/{token}/thawing/{record_id}")
def delete_public_thawing_record(token: str, record_id: str):
    """Delete a thawing record via public token access."""
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid record ID")

    with get_db() as conn:
        cursor = conn.cursor()

        outlet = _get_outlet_by_token(cursor, token)
        if not outlet:
            raise HTTPException(status_code=404, detail="Invalid or inactive token")

        cursor.execute("""
            SELECT dw.status
            FROM daily_worksheet dw
            JOIN thawing_record tr ON tr.worksheet_id = dw.id
            WHERE dw.organization_id = %s AND dw.outlet_name = %s AND tr.id = %s
        """, (outlet["organization_id"], outlet["name"], rec_uuid))

        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        if row["status"] == "approved":
            raise HTTPException(status_code=400, detail="Cannot delete from approved worksheet")

        cursor.execute("DELETE FROM thawing_record WHERE id = %s", (rec_uuid,))
        conn.commit()

        return {"status": "ok", "deleted": record_id}
