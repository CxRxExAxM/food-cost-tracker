"""
Waste Tracking API Router

Endpoints for food waste diversion tracking (compost + donation).
Supports QR-based weigh-in logging and monthly KPI reporting.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
import psycopg2.extras
from ..database import get_db
from ..auth import get_current_user

router = APIRouter(prefix="/waste", tags=["waste"])

# Constants
GRAMS_PER_LB = 453.592
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    return obj


def calculate_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate derived metrics for a monthly metrics row.
    Returns dict with calculated fields added.
    """
    result = dict(row)

    # Calculate cafe covers
    fte = row.get('fte_count') or 0
    temp = row.get('temp_count') or 0
    capture_pct = row.get('theoretic_capture_pct') or 0
    cafe_covers = round((fte + temp) * (float(capture_pct) / 100.0))
    result['cafe_covers'] = cafe_covers

    # Calculate total covers
    fb_covers = row.get('fb_covers') or 0
    total_covers = fb_covers + cafe_covers
    result['total_covers'] = total_covers

    # Calculate total diversion
    donation_lbs = float(row.get('donation_lbs') or 0)
    compost_lbs = float(row.get('compost_lbs') or 0)
    total_diversion_lbs = donation_lbs + compost_lbs
    total_diversion_grams = total_diversion_lbs * GRAMS_PER_LB
    result['total_diversion_lbs'] = total_diversion_lbs
    result['total_diversion_grams'] = round(total_diversion_grams, 2)

    # Calculate grams per cover
    if total_covers > 0:
        grams_per_cover = total_diversion_grams / total_covers
        result['grams_per_cover'] = round(grams_per_cover, 2)
    else:
        result['grams_per_cover'] = None

    return result


# ============================================================================
# GOALS ENDPOINTS
# ============================================================================

@router.get("/goals")
async def get_goal(
    year: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get waste goal for specified year.
    Creates default goal (0 grams/cover) if none exists.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Try to fetch existing goal
            cur.execute("""
                SELECT id, organization_id, year, target_grams_per_cover,
                       created_at, updated_at
                FROM waste_goals
                WHERE organization_id = %s AND year = %s
            """, (org_id, year))

            goal = cur.fetchone()

            if not goal:
                # Create default goal
                cur.execute("""
                    INSERT INTO waste_goals (organization_id, year, target_grams_per_cover)
                    VALUES (%s, %s, 0)
                    RETURNING id, organization_id, year, target_grams_per_cover,
                              created_at, updated_at
                """, (org_id, year))
                goal = cur.fetchone()
                conn.commit()

            return convert_decimals(dict(goal))


@router.put("/goals")
async def upsert_goal(
    year: int,
    target_grams_per_cover: float,
    current_user: dict = Depends(get_current_user)
):
    """
    Create or update waste goal for specified year.
    """
    org_id = current_user["organization_id"]

    # Validate target
    if target_grams_per_cover < 0:
        raise HTTPException(400, "Target grams per cover must be non-negative")

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO waste_goals (organization_id, year, target_grams_per_cover)
                VALUES (%s, %s, %s)
                ON CONFLICT (organization_id, year)
                DO UPDATE SET
                    target_grams_per_cover = EXCLUDED.target_grams_per_cover,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, organization_id, year, target_grams_per_cover,
                          created_at, updated_at
            """, (org_id, year, target_grams_per_cover))

            goal = cur.fetchone()
            conn.commit()

            return convert_decimals(dict(goal))


# ============================================================================
# MONTHLY METRICS ENDPOINTS
# ============================================================================

@router.get("/metrics")
async def get_all_metrics(
    year: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all 12 months of metrics for specified year.
    Returns empty defaults for months without data.
    Includes calculated fields and QR aggregates.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch existing monthly metrics
            cur.execute("""
                SELECT id, organization_id, year, month,
                       fb_covers, fte_count, temp_count, theoretic_capture_pct,
                       donation_lbs, compost_lbs, notes,
                       created_at, updated_at
                FROM waste_monthly_metrics
                WHERE organization_id = %s AND year = %s
                ORDER BY month
            """, (org_id, year))

            existing = {row['month']: dict(row) for row in cur.fetchall()}

            # Fetch QR aggregates for the year
            cur.execute("""
                SELECT
                    EXTRACT(MONTH FROM recorded_date)::int as month,
                    category,
                    SUM(weight_lbs) as total_lbs
                FROM waste_weigh_ins
                WHERE organization_id = %s
                  AND EXTRACT(YEAR FROM recorded_date) = %s
                GROUP BY EXTRACT(MONTH FROM recorded_date), category
            """, (org_id, year))

            qr_aggregates = {}
            for row in cur.fetchall():
                month = row['month']
                category = row['category']
                if month not in qr_aggregates:
                    qr_aggregates[month] = {}
                qr_aggregates[month][category] = float(row['total_lbs'])

            # Build response for all 12 months
            result = []
            for month_num in range(1, 13):
                if month_num in existing:
                    # Existing metric row
                    metric = existing[month_num]

                    # Get QR aggregates for this month
                    month_qr = qr_aggregates.get(month_num, {})
                    metric['qr_donation_lbs'] = month_qr.get('donation', 0)
                    metric['qr_compost_lbs'] = month_qr.get('compost', 0)

                    # Use override if set, otherwise use QR aggregate
                    if metric['donation_lbs'] is None:
                        metric['donation_lbs'] = metric['qr_donation_lbs']
                    if metric['compost_lbs'] is None:
                        metric['compost_lbs'] = metric['qr_compost_lbs']

                    # Calculate derived metrics
                    metric = calculate_metrics(metric)
                else:
                    # No data for this month - return defaults
                    month_qr = qr_aggregates.get(month_num, {})
                    metric = {
                        'id': None,
                        'organization_id': org_id,
                        'year': year,
                        'month': month_num,
                        'fb_covers': None,
                        'fte_count': None,
                        'temp_count': None,
                        'theoretic_capture_pct': None,
                        'donation_lbs': month_qr.get('donation', 0),
                        'compost_lbs': month_qr.get('compost', 0),
                        'qr_donation_lbs': month_qr.get('donation', 0),
                        'qr_compost_lbs': month_qr.get('compost', 0),
                        'notes': None,
                        'created_at': None,
                        'updated_at': None,
                        'cafe_covers': 0,
                        'total_covers': 0,
                        'total_diversion_lbs': 0,
                        'total_diversion_grams': 0,
                        'grams_per_cover': None
                    }

                metric['month_name'] = MONTHS[month_num - 1]
                result.append(metric)

            return convert_decimals(result)


@router.get("/metrics/{year}/{month}")
async def get_month_metrics(
    year: int,
    month: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed metrics for a specific month including weigh-in breakdown.
    """
    org_id = current_user["organization_id"]

    # Validate month
    if month < 1 or month > 12:
        raise HTTPException(400, "Month must be between 1 and 12")

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch monthly metric
            cur.execute("""
                SELECT id, organization_id, year, month,
                       fb_covers, fte_count, temp_count, theoretic_capture_pct,
                       donation_lbs, compost_lbs, notes,
                       created_at, updated_at
                FROM waste_monthly_metrics
                WHERE organization_id = %s AND year = %s AND month = %s
            """, (org_id, year, month))

            metric = cur.fetchone()

            # Fetch QR aggregate for this month
            cur.execute("""
                SELECT
                    category,
                    SUM(weight_lbs) as total_lbs
                FROM waste_weigh_ins
                WHERE organization_id = %s
                  AND EXTRACT(YEAR FROM recorded_date) = %s
                  AND EXTRACT(MONTH FROM recorded_date) = %s
                GROUP BY category
            """, (org_id, year, month))

            qr_aggregates = {row['category']: float(row['total_lbs']) for row in cur.fetchall()}

            # Fetch individual weigh-ins
            cur.execute("""
                SELECT wi.id, wi.category, wi.weight_lbs, wi.recorded_date,
                       wi.submitted_at, wt.label as token_label
                FROM waste_weigh_ins wi
                JOIN waste_qr_tokens wt ON wi.token_id = wt.id
                WHERE wi.organization_id = %s
                  AND EXTRACT(YEAR FROM wi.recorded_date) = %s
                  AND EXTRACT(MONTH FROM wi.recorded_date) = %s
                ORDER BY wi.recorded_date DESC, wi.submitted_at DESC
            """, (org_id, year, month))

            weigh_ins = [dict(row) for row in cur.fetchall()]

            # Build response
            if metric:
                result = dict(metric)
                result['qr_donation_lbs'] = qr_aggregates.get('donation', 0)
                result['qr_compost_lbs'] = qr_aggregates.get('compost', 0)

                # Use override if set, otherwise use QR aggregate
                if result['donation_lbs'] is None:
                    result['donation_lbs'] = result['qr_donation_lbs']
                if result['compost_lbs'] is None:
                    result['compost_lbs'] = result['qr_compost_lbs']

                result = calculate_metrics(result)
            else:
                # No metric row exists yet
                result = {
                    'id': None,
                    'organization_id': org_id,
                    'year': year,
                    'month': month,
                    'fb_covers': None,
                    'fte_count': None,
                    'temp_count': None,
                    'theoretic_capture_pct': None,
                    'donation_lbs': qr_aggregates.get('donation', 0),
                    'compost_lbs': qr_aggregates.get('compost', 0),
                    'qr_donation_lbs': qr_aggregates.get('donation', 0),
                    'qr_compost_lbs': qr_aggregates.get('compost', 0),
                    'notes': None,
                    'created_at': None,
                    'updated_at': None,
                    'cafe_covers': 0,
                    'total_covers': 0,
                    'total_diversion_lbs': 0,
                    'total_diversion_grams': 0,
                    'grams_per_cover': None
                }

            result['month_name'] = MONTHS[month - 1]
            result['weigh_ins'] = weigh_ins

            return convert_decimals(result)


@router.put("/metrics/{year}/{month}")
async def upsert_month_metrics(
    year: int,
    month: int,
    fb_covers: Optional[int] = None,
    fte_count: Optional[int] = None,
    temp_count: Optional[int] = None,
    theoretic_capture_pct: Optional[float] = None,
    donation_lbs: Optional[float] = None,
    compost_lbs: Optional[float] = None,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Create or update monthly metrics.
    """
    org_id = current_user["organization_id"]

    # Validate month
    if month < 1 or month > 12:
        raise HTTPException(400, "Month must be between 1 and 12")

    # Validate inputs
    if theoretic_capture_pct is not None and (theoretic_capture_pct < 0 or theoretic_capture_pct > 100):
        raise HTTPException(400, "Theoretic capture percentage must be between 0 and 100")

    if fb_covers is not None and fb_covers < 0:
        raise HTTPException(400, "F&B covers must be non-negative")

    if fte_count is not None and fte_count < 0:
        raise HTTPException(400, "FTE count must be non-negative")

    if temp_count is not None and temp_count < 0:
        raise HTTPException(400, "Temp count must be non-negative")

    if donation_lbs is not None and donation_lbs < 0:
        raise HTTPException(400, "Donation weight must be non-negative")

    if compost_lbs is not None and compost_lbs < 0:
        raise HTTPException(400, "Compost weight must be non-negative")

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO waste_monthly_metrics
                    (organization_id, year, month, fb_covers, fte_count, temp_count,
                     theoretic_capture_pct, donation_lbs, compost_lbs, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (organization_id, year, month)
                DO UPDATE SET
                    fb_covers = EXCLUDED.fb_covers,
                    fte_count = EXCLUDED.fte_count,
                    temp_count = EXCLUDED.temp_count,
                    theoretic_capture_pct = EXCLUDED.theoretic_capture_pct,
                    donation_lbs = EXCLUDED.donation_lbs,
                    compost_lbs = EXCLUDED.compost_lbs,
                    notes = EXCLUDED.notes,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, organization_id, year, month,
                          fb_covers, fte_count, temp_count, theoretic_capture_pct,
                          donation_lbs, compost_lbs, notes,
                          created_at, updated_at
            """, (org_id, year, month, fb_covers, fte_count, temp_count,
                  theoretic_capture_pct, donation_lbs, compost_lbs, notes))

            metric = dict(cur.fetchone())
            conn.commit()

            # Calculate derived metrics
            metric = calculate_metrics(metric)
            metric['month_name'] = MONTHS[month - 1]

            return convert_decimals(metric)


# ============================================================================
# DASHBOARD SUMMARY
# ============================================================================

@router.get("/summary")
async def get_summary(
    year: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get YTD summary including goal, actual, and variance.
    """
    org_id = current_user["organization_id"]

    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Fetch goal
            cur.execute("""
                SELECT target_grams_per_cover
                FROM waste_goals
                WHERE organization_id = %s AND year = %s
            """, (org_id, year))

            goal_row = cur.fetchone()
            target = float(goal_row['target_grams_per_cover']) if goal_row else 0

            # Fetch all months with data
            cur.execute("""
                SELECT month, fb_covers, fte_count, temp_count,
                       theoretic_capture_pct, donation_lbs, compost_lbs
                FROM waste_monthly_metrics
                WHERE organization_id = %s AND year = %s
            """, (org_id, year))

            metrics = [dict(row) for row in cur.fetchall()]

            # Calculate YTD actual (only include months with covers data)
            total_diversion_grams = 0
            total_covers = 0

            for metric in metrics:
                # Calculate for this month
                calc = calculate_metrics(metric)

                # Only include if there's covers data
                if calc['total_covers'] > 0:
                    total_diversion_grams += calc['total_diversion_grams']
                    total_covers += calc['total_covers']

            # Calculate YTD grams per cover
            ytd_actual = round(total_diversion_grams / total_covers, 2) if total_covers > 0 else 0

            # Calculate variance
            variance = ytd_actual - target
            variance_pct = (variance / target * 100) if target > 0 else 0

            return convert_decimals({
                'year': year,
                'target_grams_per_cover': target,
                'ytd_actual_grams_per_cover': ytd_actual,
                'variance': round(variance, 2),
                'variance_pct': round(variance_pct, 2),
                'total_diversion_grams': round(total_diversion_grams, 2),
                'total_covers': total_covers
            })
