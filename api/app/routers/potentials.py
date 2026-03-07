"""Potentials Module API Router

F&B Planning Dashboard - Events, Forecast, and Group Room management.
Organization-scoped data with Excel file upload support.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import pandas as pd
import tempfile
import os

from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user, require_foh_or_admin

router = APIRouter(prefix="/potentials", tags=["potentials"])


# ============================================
# Pydantic Models
# ============================================

class EventCreate(BaseModel):
    """Create a new event."""
    date: str
    booking_name: str
    category: str
    event_name: Optional[str] = ""
    event_type: Optional[str] = ""
    venue: Optional[str] = ""
    time: Optional[str] = ""
    attendees: Optional[int] = 0
    gtd: Optional[int] = 0
    notes: Optional[str] = ""


class EventUpdate(BaseModel):
    """Update an existing event."""
    booking_name: Optional[str] = None
    event_name: Optional[str] = None
    venue: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[int] = None
    gtd: Optional[int] = None
    notes: Optional[str] = None
    category: Optional[str] = None


# ============================================
# Helper Functions
# ============================================

def categorize_event_type(ev_type: str) -> str:
    """Categorize event type into meal period or activity type."""
    if not ev_type:
        return "other"
    ev_type = str(ev_type).upper()

    # Breakfast events
    if ev_type in ["BKFB", "BKFT", "BKFC"]:
        return "breakfast"
    # Lunch events
    if ev_type in ["LNCB", "LNCH", "LNCX"]:
        return "lunch"
    # Dinner events
    if ev_type in ["DINB", "DINR"]:
        return "dinner"
    # Meetings
    if ev_type in ["MEET", "CBRK", "CBRH", "CBRM"]:
        return "meeting"
    # Receptions
    if ev_type in ["RECE", "RECH", "RECM"]:
        return "reception"
    # Buyouts
    if ev_type == "BOUT":
        return "buyout"

    return "other"


def build_daily_summary(cursor, org_id: int, start_date: str = None, end_date: str = None) -> list:
    """Build daily summary combining forecast and event data."""

    # Get forecast dates
    query = """
        SELECT DISTINCT date FROM potentials_forecast_metrics
        WHERE organization_id = %s
    """
    params = [org_id]
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    cursor.execute(query, params)
    forecast_dates = {str(row['date']) for row in cursor.fetchall()}

    # Get event dates
    query = """
        SELECT DISTINCT date FROM potentials_events
        WHERE organization_id = %s AND date IS NOT NULL
    """
    params = [org_id]
    if start_date:
        query += " AND date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND date <= %s"
        params.append(end_date)

    cursor.execute(query, params)
    event_dates = {str(row['date']) for row in cursor.fetchall()}

    all_dates = sorted(forecast_dates | event_dates)

    summary = []
    for date_str in all_dates:
        # Get forecast metrics for this date
        cursor.execute("""
            SELECT metric_name, value FROM potentials_forecast_metrics
            WHERE organization_id = %s AND date = %s
        """, (org_id, date_str))
        metrics = {row['metric_name']: float(row['value']) if row['value'] else 0
                   for row in cursor.fetchall()}

        # Get events for this date
        cursor.execute("""
            SELECT * FROM potentials_events
            WHERE organization_id = %s AND date = %s
        """, (org_id, date_str))
        day_events = dicts_from_rows(cursor.fetchall())

        # Count meal covers
        breakfast_covers = sum(e.get('attendees') or e.get('gtd') or 0
                              for e in day_events if e['category'] == 'breakfast')
        lunch_covers = sum(e.get('attendees') or e.get('gtd') or 0
                          for e in day_events if e['category'] == 'lunch')
        dinner_covers = sum(e.get('attendees') or e.get('gtd') or 0
                           for e in day_events if e['category'] == 'dinner')
        reception_covers = sum(e.get('attendees') or e.get('gtd') or 0
                              for e in day_events if e['category'] == 'reception')

        meeting_count = len([e for e in day_events if e['category'] == 'meeting'])
        groups_today = list(set(e['booking_name'] for e in day_events if e.get('booking_name')))

        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        has_forecast = bool(metrics)

        summary.append({
            "date": date_str,
            "day_of_week": date_obj.strftime("%A"),
            "day_short": date_obj.strftime("%a"),

            # Hotel metrics from forecast
            "forecasted_rooms": int(metrics.get("forecasted_occupied_rooms", 0)) or None,
            "occupancy_pct": round(metrics.get("forecasted_occupancy", 0) * 100, 1) if metrics.get("forecasted_occupancy") else None,
            "arrivals": int(metrics.get("arrivals_forecast", 0)) or None,
            "departures": int(metrics.get("departures_forecast", 0)) or None,
            "adr": round(metrics.get("adr", 0), 2) if metrics.get("adr") else None,
            "adults_children": int(metrics.get("adults_children_forecast", 0)) or None,
            "kids": int(metrics.get("children_otb", 0)) or 0,
            "has_forecast": has_forecast,

            # F&B metrics from events
            "catered_breakfast": breakfast_covers,
            "catered_lunch": lunch_covers,
            "catered_dinner": dinner_covers,
            "catered_reception": reception_covers,
            "total_catered_covers": breakfast_covers + lunch_covers + dinner_covers + reception_covers,

            # Activity counts
            "meeting_count": meeting_count,
            "event_count": len(day_events),
            "groups_in_house": len(groups_today),
            "group_names": groups_today[:5],
        })

    return summary


def build_groups_summary(cursor, org_id: int) -> list:
    """Build group-level summary across all dates."""
    cursor.execute("""
        SELECT * FROM potentials_events
        WHERE organization_id = %s
        ORDER BY date
    """, (org_id,))
    events = dicts_from_rows(cursor.fetchall())

    groups_dict = {}
    for event in events:
        group_name = event.get('booking_name')
        if not group_name:
            continue

        if group_name not in groups_dict:
            groups_dict[group_name] = {
                "name": group_name,
                "dates": set(),
                "total_events": 0,
                "total_attendees": 0,
                "meal_events": {"breakfast": 0, "lunch": 0, "dinner": 0, "reception": 0},
                "meeting_count": 0,
                "venues_used": set(),
            }

        g = groups_dict[group_name]
        if event.get('date'):
            g["dates"].add(str(event['date']))
        g["total_events"] += 1
        g["total_attendees"] += event.get('attendees') or 0

        category = event.get('category', '')
        if category in g["meal_events"]:
            g["meal_events"][category] += event.get('attendees') or 0
        if category == "meeting":
            g["meeting_count"] += 1
        if event.get('venue'):
            g["venues_used"].add(event['venue'])

    result = []
    for g in groups_dict.values():
        dates_list = sorted(list(g["dates"]))
        result.append({
            "name": g["name"],
            "start_date": dates_list[0] if dates_list else None,
            "end_date": dates_list[-1] if dates_list else None,
            "days_in_house": len(dates_list),
            "total_events": g["total_events"],
            "total_attendees": g["total_attendees"],
            "meal_events": g["meal_events"],
            "meeting_count": g["meeting_count"],
            "venues_used": list(g["venues_used"])[:5],
        })

    result.sort(key=lambda x: x["start_date"] or "9999")
    return result


# ============================================
# Daily Summary Endpoints
# ============================================

@router.get("/daily-summary")
def get_daily_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get daily summary data with optional date filtering."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        data = build_daily_summary(cursor, org_id, start_date, end_date)
        return {"data": data, "count": len(data)}


# ============================================
# Events Endpoints
# ============================================

@router.get("/events")
def get_events(
    date: Optional[str] = None,
    group: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get events with optional filtering."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, event_id, date, booking_name, event_name, event_type,
                   category, venue, time, attendees, gtd, notes
            FROM potentials_events
            WHERE organization_id = %s
        """
        params = [org_id]

        if date:
            query += " AND date = %s"
            params.append(date)
        if group:
            query += " AND LOWER(booking_name) LIKE %s"
            params.append(f"%{group.lower()}%")
        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY date, time"
        cursor.execute(query, params)

        data = dicts_from_rows(cursor.fetchall())
        # Convert date objects to strings
        for event in data:
            if event.get('date'):
                event['date'] = str(event['date'])

        return {"data": data, "count": len(data)}


@router.post("/events")
def create_event(event: EventCreate, current_user: dict = Depends(require_foh_or_admin)):
    """Create a new event. Requires admin or foh_manager role."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Generate new event_id (max + 1)
        cursor.execute("""
            SELECT COALESCE(MAX(event_id), 0) + 1 as new_id
            FROM potentials_events
            WHERE organization_id = %s
        """, (org_id,))
        new_event_id = cursor.fetchone()['new_id']

        cursor.execute("""
            INSERT INTO potentials_events (
                organization_id, event_id, date, booking_name, event_name,
                event_type, category, venue, time, attendees, gtd, notes, source_file
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            org_id, new_event_id, event.date, event.booking_name, event.event_name,
            event.event_type, event.category, event.venue, event.time,
            event.attendees, event.gtd, event.notes, 'manual_entry'
        ))

        db_id = cursor.fetchone()['id']
        conn.commit()

        return {"status": "ok", "id": db_id, "event_id": new_event_id, "message": "Event created"}


@router.put("/events/{event_id}")
def update_event(event_id: int, updates: EventUpdate, current_user: dict = Depends(require_foh_or_admin)):
    """Update an event. Requires admin or foh_manager role."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Check event exists and belongs to org
        cursor.execute("""
            SELECT id FROM potentials_events
            WHERE event_id = %s AND organization_id = %s
        """, (event_id, org_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Event not found")

        # Build update
        update_dict = updates.dict(exclude_unset=True)
        if not update_dict:
            return {"status": "ok", "message": "No fields to update"}

        update_fields = []
        params = []
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        params.extend([event_id, org_id])
        cursor.execute(f"""
            UPDATE potentials_events
            SET {', '.join(update_fields)}
            WHERE event_id = %s AND organization_id = %s
        """, params)

        conn.commit()
        return {"status": "ok", "event_id": event_id, "updated_fields": list(update_dict.keys())}


@router.delete("/events/{event_id}")
def delete_event(event_id: int, current_user: dict = Depends(require_foh_or_admin)):
    """Delete an event. Requires admin or foh_manager role."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM potentials_events
            WHERE event_id = %s AND organization_id = %s
        """, (event_id, org_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Event not found")

        conn.commit()
        return {"status": "ok", "event_id": event_id, "message": "Event deleted"}


# ============================================
# Groups Endpoints
# ============================================

@router.get("/groups")
def get_groups(current_user: dict = Depends(get_current_user)):
    """Get group-level summary data."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        data = build_groups_summary(cursor, org_id)
        return {"data": data, "count": len(data)}


@router.get("/group-rooms/{date}")
def get_group_rooms(date: str, current_user: dict = Depends(get_current_user)):
    """Get per-group room data for a specific date."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT block_code, block_name, rooms, arrivals, departures
            FROM potentials_group_rooms
            WHERE organization_id = %s AND date = %s
              AND (rooms > 0 OR arrivals > 0 OR departures > 0)
            ORDER BY block_name
        """, (org_id, date))

        data = dicts_from_rows(cursor.fetchall())
        return {"date": date, "data": data, "count": len(data)}


# ============================================
# Forecast Endpoints
# ============================================

@router.get("/forecast")
def get_forecast(current_user: dict = Depends(get_current_user)):
    """Get raw forecast metrics."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT date FROM potentials_forecast_metrics
            WHERE organization_id = %s
            ORDER BY date
        """, (org_id,))
        dates = [str(row['date']) for row in cursor.fetchall()]

        daily_metrics = {}
        for date_str in dates:
            cursor.execute("""
                SELECT metric_name, value FROM potentials_forecast_metrics
                WHERE organization_id = %s AND date = %s
            """, (org_id, date_str))
            daily_metrics[date_str] = {
                row['metric_name']: float(row['value']) if row['value'] else 0
                for row in cursor.fetchall()
            }

        return {"dates": dates, "daily_metrics": daily_metrics}


# ============================================
# Metrics Endpoint
# ============================================

@router.get("/metrics")
def get_summary_metrics(current_user: dict = Depends(get_current_user)):
    """Get high-level summary metrics for dashboard header."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        daily_summary = build_daily_summary(cursor, org_id)

        if not daily_summary:
            return {"error": "No data loaded"}

        total_days = len(daily_summary)
        avg_occupancy = sum(d["occupancy_pct"] or 0 for d in daily_summary) / total_days if total_days else 0
        total_catered_covers = sum(d["total_catered_covers"] for d in daily_summary)
        total_events = sum(d["event_count"] for d in daily_summary)

        groups_data = build_groups_summary(cursor, org_id)

        peak_day = max(daily_summary, key=lambda x: x["total_catered_covers"]) if daily_summary else None

        return {
            "total_days": total_days,
            "date_range": {
                "start": daily_summary[0]["date"] if daily_summary else None,
                "end": daily_summary[-1]["date"] if daily_summary else None,
            },
            "avg_occupancy_pct": round(avg_occupancy, 1),
            "total_catered_covers": total_catered_covers,
            "total_events": total_events,
            "total_groups": len(groups_data),
            "peak_day": {
                "date": peak_day["date"] if peak_day else None,
                "covers": peak_day["total_catered_covers"] if peak_day else 0,
                "day_of_week": peak_day["day_of_week"] if peak_day else None,
            } if peak_day else None,
        }


# ============================================
# Upload Endpoints
# ============================================

@router.post("/upload/hitlist")
async def upload_hitlist(file: UploadFile = File(...), current_user: dict = Depends(require_foh_or_admin)):
    """Upload a hitlist Excel file. Requires admin or foh_manager role."""
    org_id = current_user["organization_id"]

    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx)")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = pd.read_excel(tmp_path)
        df = df.copy()
        df.loc[:, "event_date"] = pd.to_datetime(df["DATE_SORT_COLUMN"])

        fb_categories = {"breakfast", "lunch", "dinner", "reception"}

        with get_db() as conn:
            cursor = conn.cursor()

            added = 0
            skipped = 0
            now = datetime.now().isoformat()

            for _, row in df.iterrows():
                # Skip cancelled events
                if row.get("DISTRO?") == "CXLD" or row.get("EV_STATUS") == "CAN":
                    continue

                event_id = row.get("EVENT_ID")
                if pd.isna(event_id):
                    continue

                category = categorize_event_type(row.get("EV_TYPE"))

                # Skip non-F&B events
                if category not in fb_categories:
                    continue

                # Check if event exists
                cursor.execute("""
                    SELECT 1 FROM potentials_events
                    WHERE event_id = %s AND organization_id = %s
                """, (int(event_id), org_id))

                if cursor.fetchone():
                    skipped += 1
                    continue

                # Insert new event
                event_date = row["event_date"].strftime("%Y-%m-%d") if pd.notna(row["event_date"]) else None
                cursor.execute("""
                    INSERT INTO potentials_events (
                        organization_id, event_id, date, booking_name, event_name,
                        event_type, category, venue, time, attendees, gtd, source_file, imported_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    org_id,
                    int(event_id),
                    event_date,
                    str(row["BOOKING_NAME"]) if pd.notna(row.get("BOOKING_NAME")) else "Unknown",
                    str(row["EV_NAME"]) if pd.notna(row.get("EV_NAME")) else "",
                    str(row["EV_TYPE"]) if pd.notna(row.get("EV_TYPE")) else "",
                    category,
                    str(row["FUNC_SPACE"]) if pd.notna(row.get("FUNC_SPACE")) else "",
                    str(row["TIME"]) if pd.notna(row.get("TIME")) else "",
                    int(row["ATTENDEES"]) if pd.notna(row.get("ATTENDEES")) else 0,
                    int(row["GTD"]) if pd.notna(row.get("GTD")) else 0,
                    file.filename,
                    now
                ))
                added += 1

            # Log the import
            cursor.execute("""
                INSERT INTO potentials_import_log (organization_id, filename, file_type, records_added, records_updated)
                VALUES (%s, %s, %s, %s, %s)
            """, (org_id, file.filename, "hitlist", added, 0))

            conn.commit()

            return {
                "status": "ok",
                "filename": file.filename,
                "events_added": added,
                "events_skipped": skipped
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import file: {str(e)}")
    finally:
        os.unlink(tmp_path)


@router.post("/upload/forecast")
async def upload_forecast(file: UploadFile = File(...), current_user: dict = Depends(require_foh_or_admin)):
    """Upload a forecast Excel file. Requires admin or foh_manager role."""
    org_id = current_user["organization_id"]

    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="File must be an Excel file (.xlsx)")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = pd.read_excel(tmp_path, sheet_name="21-day forecast", header=None)

        # Extract dates from row 1
        dates = []
        for col in range(1, 23):
            val = df.iloc[1, col]
            if pd.notna(val) and isinstance(val, datetime):
                dates.append(val)

        # Row mapping for metrics
        row_mapping = {
            2: "out_of_order_rooms",
            4: "arrivals_otb",
            5: "transient_arrivals_otb",
            6: "departures_otb",
            8: "arrivals_forecast",
            9: "departures_forecast",
            10: "occupied_rooms_otb",
            11: "occupancy_pct_otb",
            12: "adr",
            15: "forecasted_occupied_rooms",
            16: "forecasted_occupancy",
            17: "adults_children_otb",
            18: "adults_children_forecast",
            19: "children_otb",
        }

        with get_db() as conn:
            cursor = conn.cursor()

            added = 0
            updated = 0
            now = datetime.now().isoformat()

            for i, date_val in enumerate(dates):
                col_idx = i + 1
                date_str = date_val.strftime("%Y-%m-%d")

                for row_idx, metric_name in row_mapping.items():
                    val = df.iloc[row_idx, col_idx]
                    if pd.notna(val) and not isinstance(val, str):
                        value = float(val)

                        # Check if exists
                        cursor.execute("""
                            SELECT value FROM potentials_forecast_metrics
                            WHERE organization_id = %s AND date = %s AND metric_name = %s
                        """, (org_id, date_str, metric_name))
                        existing = cursor.fetchone()

                        if existing is None:
                            cursor.execute("""
                                INSERT INTO potentials_forecast_metrics
                                (organization_id, date, metric_name, value, source_file)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (org_id, date_str, metric_name, value, file.filename))
                            added += 1
                        elif abs(float(existing['value'] or 0) - value) > 0.001:
                            cursor.execute("""
                                UPDATE potentials_forecast_metrics
                                SET value = %s, updated_at = NOW(), source_file = %s
                                WHERE organization_id = %s AND date = %s AND metric_name = %s
                            """, (value, file.filename, org_id, date_str, metric_name))
                            updated += 1

            # Import group rooms
            groups_imported = import_group_rooms_from_df(cursor, df, dates, org_id, file.filename)

            # Log the import
            cursor.execute("""
                INSERT INTO potentials_import_log (organization_id, filename, file_type, records_added, records_updated)
                VALUES (%s, %s, %s, %s, %s)
            """, (org_id, file.filename, "forecast", added, updated))

            conn.commit()

            return {
                "status": "ok",
                "filename": file.filename,
                "metrics_added": added,
                "metrics_updated": updated,
                "groups_imported": groups_imported
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import file: {str(e)}")
    finally:
        os.unlink(tmp_path)


def import_group_rooms_from_df(cursor, df, dates, org_id: int, filename: str) -> int:
    """Import per-group daily room data from 21-day forecast sheet."""
    # Find GROUP ROOMS IN HOUSE header
    header_row = None
    for i in range(len(df)):
        if df.iloc[i, 0] == "GROUP ROOMS IN HOUSE":
            header_row = i
            break

    if header_row is None:
        return 0

    groups_processed = 0
    records_added = 0

    # Get previous day for historical lookup
    if dates:
        first_date = dates[0]
        prev_date = (first_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        prev_date = None

    # Process each group row
    for row_idx in range(header_row + 2, len(df)):
        group_name = df.iloc[row_idx, 0]

        if pd.isna(group_name) or str(group_name).strip() == "":
            break

        group_name = str(group_name).strip()
        groups_processed += 1

        # Get historical rooms
        historical_prev_rooms = 0
        if prev_date:
            cursor.execute("""
                SELECT rooms FROM potentials_group_rooms
                WHERE organization_id = %s AND block_name = %s AND date = %s
            """, (org_id, group_name, prev_date))
            hist_row = cursor.fetchone()
            if hist_row:
                historical_prev_rooms = hist_row['rooms'] or 0

        # Get daily rooms
        daily_rooms = []
        for col in range(1, len(dates) + 1):
            val = df.iloc[row_idx, col]
            rooms = int(val) if pd.notna(val) and not isinstance(val, str) else 0
            daily_rooms.append(rooms)

        # Calculate arrivals/departures
        for day_idx, rooms in enumerate(daily_rooms):
            date_val = dates[day_idx]
            date_str = date_val.strftime("%Y-%m-%d")

            if day_idx == 0:
                prev_rooms = historical_prev_rooms
            else:
                prev_rooms = daily_rooms[day_idx - 1]

            arrivals = max(0, rooms - prev_rooms)
            departures = max(0, prev_rooms - rooms)

            if rooms > 0 or arrivals > 0 or departures > 0:
                # Upsert
                cursor.execute("""
                    INSERT INTO potentials_group_rooms
                    (organization_id, block_code, block_name, date, rooms, arrivals, departures, source_file)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (organization_id, block_code, date)
                    DO UPDATE SET rooms = EXCLUDED.rooms, arrivals = EXCLUDED.arrivals,
                                  departures = EXCLUDED.departures, source_file = EXCLUDED.source_file,
                                  updated_at = NOW()
                """, (org_id, group_name, group_name, date_str, rooms, arrivals, departures, filename))
                records_added += 1

    return groups_processed


# ============================================
# Status & Refresh Endpoints
# ============================================

@router.get("/status")
def get_status(current_user: dict = Depends(get_current_user)):
    """Get import status and last update times."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Last hitlist import
        cursor.execute("""
            SELECT filename, imported_at, records_added
            FROM potentials_import_log
            WHERE organization_id = %s AND file_type = 'hitlist'
            ORDER BY imported_at DESC
            LIMIT 1
        """, (org_id,))
        last_hitlist = dict_from_row(cursor.fetchone())

        # Last forecast import
        cursor.execute("""
            SELECT filename, imported_at, records_added, records_updated
            FROM potentials_import_log
            WHERE organization_id = %s AND file_type = 'forecast'
            ORDER BY imported_at DESC
            LIMIT 1
        """, (org_id,))
        last_forecast = dict_from_row(cursor.fetchone())

        # Total counts
        cursor.execute("""
            SELECT COUNT(*) as count FROM potentials_events
            WHERE organization_id = %s
        """, (org_id,))
        event_count = cursor.fetchone()['count']

        cursor.execute("""
            SELECT COUNT(DISTINCT date) as count FROM potentials_forecast_metrics
            WHERE organization_id = %s
        """, (org_id,))
        forecast_days = cursor.fetchone()['count']

        # Imported files list
        cursor.execute("""
            SELECT DISTINCT filename, file_type, MAX(imported_at) as imported_at
            FROM potentials_import_log
            WHERE organization_id = %s
            GROUP BY filename, file_type
            ORDER BY imported_at DESC
        """, (org_id,))
        imported_files = dicts_from_rows(cursor.fetchall())

        return {
            "last_hitlist_import": {
                "filename": last_hitlist.get("filename") if last_hitlist else None,
                "imported_at": str(last_hitlist.get("imported_at")) if last_hitlist and last_hitlist.get("imported_at") else None,
                "records_added": last_hitlist.get("records_added", 0) if last_hitlist else 0,
            } if last_hitlist else None,
            "last_forecast_import": {
                "filename": last_forecast.get("filename") if last_forecast else None,
                "imported_at": str(last_forecast.get("imported_at")) if last_forecast and last_forecast.get("imported_at") else None,
                "records_added": last_forecast.get("records_added", 0) if last_forecast else 0,
                "records_updated": last_forecast.get("records_updated", 0) if last_forecast else 0,
            } if last_forecast else None,
            "totals": {
                "events": event_count,
                "forecast_days": forecast_days,
            },
            "imported_files": imported_files,
        }


@router.post("/refresh")
def refresh_data(current_user: dict = Depends(get_current_user)):
    """Refresh data summary (no file scanning in multi-tenant)."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) as count FROM potentials_events WHERE organization_id = %s", (org_id,))
        events = cursor.fetchone()['count']

        daily_summary = build_daily_summary(cursor, org_id)
        groups_data = build_groups_summary(cursor, org_id)

        return {
            "status": "ok",
            "totals": {
                "events": events,
                "days": len(daily_summary),
                "groups": len(groups_data),
            }
        }
