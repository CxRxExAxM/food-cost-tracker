"""Banquet Menus API Router

CRUD operations for banquet menus, menu items, and prep items.
Supports linking prep items to products or recipes for cost calculation.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from ..database import get_db, dicts_from_rows, dict_from_row
from ..auth import get_current_user, build_outlet_filter, check_outlet_access

router = APIRouter(prefix="/banquet-menus", tags=["banquet-menus"])


# ============================================
# Helper Functions
# ============================================

def get_unit_id_from_abbreviation(cursor, abbr: str) -> int:
    """Look up unit ID from abbreviation."""
    if not abbr:
        return None
    cursor.execute("""
        SELECT id FROM units WHERE UPPER(abbreviation) = UPPER(%s) LIMIT 1
    """, (abbr.strip(),))
    result = cursor.fetchone()
    return result['id'] if result else None


def get_unit_conversion_factor(cursor, common_product_id: int, from_unit_id: int, to_unit_id: int, org_id: int) -> float:
    """
    Get conversion factor between two units for a common product.

    Returns the factor to multiply a quantity in from_unit to get to_unit.
    If no direct conversion exists, tries to find a path through standard conversions.

    Example: 1 EA ribeye = 6 OZ, and we need to convert to LB
    - Direct: EA -> LB might not exist
    - Path: EA -> OZ (factor 6) then OZ -> LB (factor 0.0625) = 0.375
    """
    if from_unit_id == to_unit_id:
        return 1.0

    if not from_unit_id or not to_unit_id or not common_product_id:
        return 1.0

    # Try direct conversion
    cursor.execute("""
        SELECT conversion_factor
        FROM product_conversions
        WHERE common_product_id = %s
          AND from_unit_id = %s
          AND to_unit_id = %s
          AND organization_id = %s
    """, (common_product_id, from_unit_id, to_unit_id, org_id))

    result = cursor.fetchone()
    if result:
        return float(result['conversion_factor'])

    # Try reverse conversion
    cursor.execute("""
        SELECT conversion_factor
        FROM product_conversions
        WHERE common_product_id = %s
          AND from_unit_id = %s
          AND to_unit_id = %s
          AND organization_id = %s
    """, (common_product_id, to_unit_id, from_unit_id, org_id))

    result = cursor.fetchone()
    if result:
        return 1.0 / float(result['conversion_factor'])

    # Try two-hop conversion through a common unit (typically OZ or LB)
    # Get all conversions FROM the from_unit
    cursor.execute("""
        SELECT to_unit_id, conversion_factor
        FROM product_conversions
        WHERE common_product_id = %s
          AND from_unit_id = %s
          AND organization_id = %s
    """, (common_product_id, from_unit_id, org_id))

    from_conversions = {row['to_unit_id']: row['conversion_factor'] for row in cursor.fetchall()}

    # Get all conversions TO the to_unit (we need from X to to_unit)
    cursor.execute("""
        SELECT from_unit_id, conversion_factor
        FROM product_conversions
        WHERE common_product_id = %s
          AND to_unit_id = %s
          AND organization_id = %s
    """, (common_product_id, to_unit_id, org_id))

    to_conversions = {row['from_unit_id']: row['conversion_factor'] for row in cursor.fetchall()}

    # Find intermediate unit that connects both
    for intermediate_unit, factor1 in from_conversions.items():
        if intermediate_unit in to_conversions:
            # from_unit -> intermediate -> to_unit
            factor2 = to_conversions[intermediate_unit]
            return float(factor1) * float(factor2)

    # Also check if we can go: from_unit -> intermediate, then intermediate -> to_unit (reverse)
    cursor.execute("""
        SELECT from_unit_id, conversion_factor
        FROM product_conversions
        WHERE common_product_id = %s
          AND to_unit_id = %s
          AND organization_id = %s
    """, (common_product_id, to_unit_id, org_id))

    # Try standard weight conversions if no product-specific conversion found
    # This handles OZ <-> LB conversions automatically
    cursor.execute("""
        SELECT u1.abbreviation as from_abbr, u2.abbreviation as to_abbr
        FROM units u1, units u2
        WHERE u1.id = %s AND u2.id = %s
    """, (from_unit_id, to_unit_id))

    units = cursor.fetchone()
    if units:
        from_abbr = units['from_abbr'].upper()
        to_abbr = units['to_abbr'].upper()

        # Standard weight conversions
        weight_to_oz = {'OZ': 1, 'LB': 16, 'G': 0.035274, 'KG': 35.274}

        if from_abbr in weight_to_oz and to_abbr in weight_to_oz:
            # Convert through ounces
            return weight_to_oz[from_abbr] / weight_to_oz[to_abbr]

    # No conversion found - return 1.0 (assumes same unit or incompatible)
    return 1.0


# ============================================
# Pydantic Models
# ============================================

class BanquetMenuCreate(BaseModel):
    """Create a new banquet menu."""
    meal_period: str
    service_type: str
    name: str
    price_per_person: Optional[float] = None
    min_guest_count: Optional[int] = None
    under_min_surcharge: Optional[float] = None
    target_food_cost_pct: Optional[float] = None
    outlet_id: int


class BanquetMenuUpdate(BaseModel):
    """Update an existing banquet menu."""
    meal_period: Optional[str] = None
    service_type: Optional[str] = None
    name: Optional[str] = None
    price_per_person: Optional[float] = None
    min_guest_count: Optional[int] = None
    under_min_surcharge: Optional[float] = None
    target_food_cost_pct: Optional[float] = None


class MenuItemCreate(BaseModel):
    """Create a new menu item."""
    name: str
    display_order: Optional[int] = 0
    is_enhancement: Optional[bool] = False
    additional_price: Optional[float] = None


class MenuItemUpdate(BaseModel):
    """Update an existing menu item."""
    name: Optional[str] = None
    display_order: Optional[int] = None
    is_enhancement: Optional[bool] = None
    additional_price: Optional[float] = None


class PrepItemCreate(BaseModel):
    """Create a new prep item."""
    name: str
    display_order: Optional[int] = 0
    amount_per_guest: Optional[float] = None
    amount_unit: Optional[str] = None  # Legacy field, prefer unit_id
    unit_id: Optional[int] = None
    amount_mode: Optional[str] = 'per_person'  # 'per_person', 'at_minimum', 'fixed'
    base_amount: Optional[float] = None  # For at_minimum/fixed modes
    vessel: Optional[str] = None  # Legacy text field
    vessel_id: Optional[int] = None  # FK to vessels table
    vessel_count: Optional[float] = None  # Number of vessels
    responsibility: Optional[str] = None
    product_id: Optional[int] = None
    recipe_id: Optional[int] = None
    common_product_id: Optional[int] = None


class PrepItemUpdate(BaseModel):
    """Update an existing prep item."""
    name: Optional[str] = None
    display_order: Optional[int] = None
    amount_per_guest: Optional[float] = None
    amount_unit: Optional[str] = None  # Legacy field, prefer unit_id
    unit_id: Optional[int] = None
    amount_mode: Optional[str] = None  # 'per_person', 'at_minimum', 'fixed'
    base_amount: Optional[float] = None  # For at_minimum/fixed modes
    vessel: Optional[str] = None  # Legacy text field
    vessel_id: Optional[int] = None  # FK to vessels table
    vessel_count: Optional[float] = None  # Number of vessels
    responsibility: Optional[str] = None
    product_id: Optional[int] = None
    recipe_id: Optional[int] = None
    common_product_id: Optional[int] = None


class ReorderItem(BaseModel):
    """Item for reordering."""
    id: int
    display_order: int


# ============================================
# Banquet Menu Endpoints
# ============================================

@router.get("")
def list_banquet_menus(
    outlet_id: Optional[int] = None,
    meal_period: Optional[str] = None,
    service_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List banquet menus with optional filtering.

    - **outlet_id**: Filter by specific outlet (required unless admin)
    - **meal_period**: Filter by meal period
    - **service_type**: Filter by service type
    """
    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        where_clauses = ["bm.is_active = 1", "bm.organization_id = %s"]
        params = [org_id]

        # Filter by outlet
        if outlet_id:
            if not check_outlet_access(current_user, outlet_id):
                raise HTTPException(status_code=403, detail="You don't have access to this outlet")
            where_clauses.append("bm.outlet_id = %s")
            params.append(outlet_id)
        else:
            # Apply user's outlet filter
            outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")
            where_clauses.append(outlet_filter)
            params.extend(outlet_params)

        if meal_period:
            where_clauses.append("bm.meal_period = %s")
            params.append(meal_period)

        if service_type:
            where_clauses.append("bm.service_type = %s")
            params.append(service_type)

        where_clause = " AND ".join(where_clauses)

        query = f"""
            SELECT
                bm.*,
                o.name as outlet_name,
                (SELECT COUNT(*) FROM banquet_menu_items WHERE banquet_menu_id = bm.id) as item_count
            FROM banquet_menus bm
            JOIN outlets o ON o.id = bm.outlet_id
            WHERE {where_clause}
            ORDER BY bm.meal_period, bm.service_type, bm.name
        """

        cursor.execute(query, params)
        menus = dicts_from_rows(cursor.fetchall())

        return {"menus": menus, "total": len(menus)}


@router.get("/meal-periods")
def get_meal_periods(
    outlet_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get distinct meal periods for an outlet."""
    if not check_outlet_access(current_user, outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT meal_period
            FROM banquet_menus
            WHERE outlet_id = %s AND is_active = 1
            ORDER BY meal_period
        """, (outlet_id,))

        periods = [row["meal_period"] for row in cursor.fetchall()]
        return {"meal_periods": periods}


@router.get("/service-types")
def get_service_types(
    outlet_id: int,
    meal_period: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get distinct service types for an outlet, optionally filtered by meal period."""
    if not check_outlet_access(current_user, outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT service_type
            FROM banquet_menus
            WHERE outlet_id = %s AND is_active = 1
        """
        params = [outlet_id]

        if meal_period:
            query += " AND meal_period = %s"
            params.append(meal_period)

        query += " ORDER BY service_type"

        cursor.execute(query, params)
        types = [row["service_type"] for row in cursor.fetchall()]
        return {"service_types": types}


@router.get("/{menu_id}")
def get_banquet_menu(menu_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single banquet menu with all items and prep items."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get menu with outlet filter
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bm.*, o.name as outlet_name
            FROM banquet_menus bm
            JOIN outlets o ON o.id = bm.outlet_id
            WHERE bm.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [menu_id] + outlet_params)

        menu = dict_from_row(cursor.fetchone())
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found or you don't have access")

        # Get menu items
        cursor.execute("""
            SELECT * FROM banquet_menu_items
            WHERE banquet_menu_id = %s
            ORDER BY display_order, name
        """, (menu_id,))
        menu_items = dicts_from_rows(cursor.fetchall())

        # Get prep items for each menu item with linked product/recipe/common_product info
        for item in menu_items:
            cursor.execute("""
                SELECT
                    bp.*,
                    p.name as product_name,
                    p.unit_id as product_unit_id,
                    pu.abbreviation as product_unit_abbr,
                    r.name as recipe_name,
                    cp.common_name as common_product_name,
                    cp.category as common_product_category,
                    -- Unit info for the prep item
                    bu.abbreviation as unit_abbr,
                    bu.name as unit_name,
                    -- Vessel info
                    v.name as vessel_name,
                    v.default_capacity as vessel_default_capacity,
                    vu.abbreviation as vessel_unit_abbr,
                    -- Get product-specific vessel capacity if exists
                    (
                        SELECT vpc.capacity
                        FROM vessel_product_capacities vpc
                        WHERE vpc.vessel_id = bp.vessel_id
                          AND vpc.common_product_id = bp.common_product_id
                    ) as vessel_product_capacity,
                    -- Get latest unit price for the product
                    (
                        SELECT ph.unit_price
                        FROM price_history ph
                        JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                        WHERE dp.product_id = bp.product_id
                        ORDER BY ph.effective_date DESC
                        LIMIT 1
                    ) as product_unit_cost,
                    -- Get average unit cost for common product (from all linked products)
                    (
                        SELECT AVG(ph2.unit_price)
                        FROM price_history ph2
                        JOIN distributor_products dp2 ON dp2.id = ph2.distributor_product_id
                        JOIN products p2 ON p2.id = dp2.product_id
                        WHERE p2.common_product_id = bp.common_product_id
                        AND ph2.effective_date = (
                            SELECT MAX(ph3.effective_date)
                            FROM price_history ph3
                            WHERE ph3.distributor_product_id = dp2.id
                        )
                    ) as common_product_unit_cost
                FROM banquet_prep_items bp
                LEFT JOIN products p ON p.id = bp.product_id
                LEFT JOIN units pu ON pu.id = p.unit_id
                LEFT JOIN units bu ON bu.id = bp.unit_id
                LEFT JOIN recipes r ON r.id = bp.recipe_id
                LEFT JOIN common_products cp ON cp.id = bp.common_product_id
                LEFT JOIN vessels v ON v.id = bp.vessel_id
                LEFT JOIN units vu ON vu.id = v.default_unit_id
                WHERE bp.banquet_menu_item_id = %s
                ORDER BY bp.display_order, bp.name
            """, (item["id"],))
            item["prep_items"] = dicts_from_rows(cursor.fetchall())

        menu["menu_items"] = menu_items
        return menu


@router.get("/{menu_id}/cost")
def calculate_menu_cost(
    menu_id: int,
    guests: int = Query(50, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """Calculate menu cost for a given number of guests."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get menu with outlet filter
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bm.*
            FROM banquet_menus bm
            WHERE bm.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [menu_id] + outlet_params)

        menu = dict_from_row(cursor.fetchone())
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found or you don't have access")

        # Calculate costs
        total_cost = Decimal("0")
        item_costs = []

        cursor.execute("""
            SELECT * FROM banquet_menu_items
            WHERE banquet_menu_id = %s
        """, (menu_id,))
        menu_items = dicts_from_rows(cursor.fetchall())

        for item in menu_items:
            item_cost = Decimal("0")
            prep_costs = []

            cursor.execute("""
                SELECT
                    bp.*,
                    v.default_capacity as vessel_default_capacity,
                    (
                        SELECT vpc.capacity
                        FROM vessel_product_capacities vpc
                        WHERE vpc.vessel_id = bp.vessel_id
                          AND vpc.common_product_id = bp.common_product_id
                    ) as vessel_product_capacity,
                    -- Get product unit cost and the product's unit_id
                    (
                        SELECT ph.unit_price
                        FROM price_history ph
                        JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                        WHERE dp.product_id = bp.product_id
                        ORDER BY ph.effective_date DESC
                        LIMIT 1
                    ) as product_unit_cost,
                    (
                        SELECT p.unit_id
                        FROM products p
                        WHERE p.id = bp.product_id
                    ) as product_pricing_unit_id,
                    -- Get common product average unit cost and typical pricing unit
                    (
                        SELECT AVG(ph2.unit_price)
                        FROM price_history ph2
                        JOIN distributor_products dp2 ON dp2.id = ph2.distributor_product_id
                        JOIN products p2 ON p2.id = dp2.product_id
                        WHERE p2.common_product_id = bp.common_product_id
                        AND ph2.effective_date = (
                            SELECT MAX(ph3.effective_date)
                            FROM price_history ph3
                            WHERE ph3.distributor_product_id = dp2.id
                        )
                    ) as common_product_unit_cost,
                    -- Get the most common pricing unit for this common product
                    (
                        SELECT p2.unit_id
                        FROM products p2
                        WHERE p2.common_product_id = bp.common_product_id
                        GROUP BY p2.unit_id
                        ORDER BY COUNT(*) DESC
                        LIMIT 1
                    ) as common_product_pricing_unit_id
                FROM banquet_prep_items bp
                LEFT JOIN vessels v ON v.id = bp.vessel_id
                WHERE bp.banquet_menu_item_id = %s
            """, (item["id"],))

            prep_items = dicts_from_rows(cursor.fetchall())
            org_id = current_user["organization_id"]

            for prep in prep_items:
                unit_cost = Decimal("0")
                pricing_unit_id = None
                linked_common_product_id = None

                if prep.get("product_unit_cost"):
                    unit_cost = Decimal(str(prep["product_unit_cost"]))
                    pricing_unit_id = prep.get("product_pricing_unit_id")
                    # For direct product links, get the common_product_id from the product
                    if prep.get("product_id"):
                        cursor.execute("SELECT common_product_id FROM products WHERE id = %s", (prep["product_id"],))
                        prod_result = cursor.fetchone()
                        if prod_result:
                            linked_common_product_id = prod_result.get("common_product_id")
                elif prep.get("common_product_unit_cost"):
                    unit_cost = Decimal(str(prep["common_product_unit_cost"]))
                    pricing_unit_id = prep.get("common_product_pricing_unit_id")
                    linked_common_product_id = prep.get("common_product_id")
                # TODO: Add recipe cost calculation when recipes are linked

                # Get prep item's unit - prefer unit_id, fallback to looking up from amount_unit text
                prep_unit_id = prep.get("unit_id")
                if not prep_unit_id and prep.get("amount_unit"):
                    prep_unit_id = get_unit_id_from_abbreviation(cursor, prep["amount_unit"])

                # Debug: log unit conversion info with abbreviations
                prep_unit_abbr = None
                pricing_unit_abbr = None
                if prep_unit_id:
                    cursor.execute("SELECT abbreviation FROM units WHERE id = %s", (prep_unit_id,))
                    r = cursor.fetchone()
                    prep_unit_abbr = r['abbreviation'] if r else None
                if pricing_unit_id:
                    cursor.execute("SELECT abbreviation FROM units WHERE id = %s", (pricing_unit_id,))
                    r = cursor.fetchone()
                    pricing_unit_abbr = r['abbreviation'] if r else None
                print(f"[COST DEBUG] Prep '{prep.get('name')}': prep_unit={prep_unit_abbr}(id={prep_unit_id}), pricing_unit={pricing_unit_abbr}(id={pricing_unit_id}), common_prod_id={linked_common_product_id}, unit_cost_before={unit_cost}")

                # Apply unit conversion if prep item unit differs from pricing unit
                if prep_unit_id and pricing_unit_id and prep_unit_id != pricing_unit_id:
                    # Convert: we have price per pricing_unit, we want price per prep_unit
                    # e.g., price is $22.4/LB, prep is 6 OZ, conversion OZ->LB = 0.0625
                    # so cost per OZ = $22.4 * 0.0625 = $1.40
                    # total for 6 OZ = $1.40 * 6 = $8.40
                    conversion_factor = get_unit_conversion_factor(
                        cursor, linked_common_product_id, prep_unit_id, pricing_unit_id, org_id
                    )
                    print(f"[COST DEBUG] Conversion factor: {conversion_factor}, unit_cost_after={unit_cost * Decimal(str(conversion_factor))}")
                    unit_cost = unit_cost * Decimal(str(conversion_factor))
                elif prep_unit_id and pricing_unit_id:
                    print(f"[COST DEBUG] No conversion needed (same unit)")
                else:
                    print(f"[COST DEBUG] Missing unit IDs - no conversion applied")

                # Calculate amount based on amount_mode and vessel
                amount_mode = prep.get("amount_mode") or "per_person"
                calculated_amount = Decimal("0")

                # Check if using vessel-based calculation
                if prep.get("vessel_id") and prep.get("vessel_count"):
                    vessel_count = Decimal(str(prep["vessel_count"]))
                    # Use product-specific capacity if available, otherwise vessel default
                    if prep.get("vessel_product_capacity"):
                        capacity = Decimal(str(prep["vessel_product_capacity"]))
                    elif prep.get("vessel_default_capacity"):
                        capacity = Decimal(str(prep["vessel_default_capacity"]))
                    else:
                        capacity = Decimal("0")
                    calculated_amount = vessel_count * capacity
                else:
                    # Standard amount modes
                    if amount_mode == "per_person":
                        amount_per_guest = Decimal(str(prep.get("amount_per_guest") or 0))
                        calculated_amount = amount_per_guest * guests
                    elif amount_mode in ("at_minimum", "fixed"):
                        calculated_amount = Decimal(str(prep.get("base_amount") or 0))

                prep_total = unit_cost * calculated_amount

                prep_costs.append({
                    "prep_item_id": prep["id"],
                    "name": prep["name"],
                    "unit_cost": float(unit_cost),
                    "unit_id": prep.get("unit_id"),
                    "pricing_unit_id": pricing_unit_id,
                    "amount_mode": amount_mode,
                    "amount_per_guest": float(prep.get("amount_per_guest") or 0),
                    "base_amount": float(prep.get("base_amount") or 0),
                    "vessel_id": prep.get("vessel_id"),
                    "vessel_count": float(prep.get("vessel_count") or 0),
                    "calculated_amount": float(calculated_amount),
                    "total_cost": float(prep_total),
                    "linked": bool(prep.get("product_id") or prep.get("recipe_id") or prep.get("common_product_id"))
                })

                item_cost += prep_total

            # Add enhancement price if applicable
            if item.get("is_enhancement") and item.get("additional_price"):
                item_cost += Decimal(str(item["additional_price"])) * guests

            item_costs.append({
                "menu_item_id": item["id"],
                "name": item["name"],
                "is_enhancement": bool(item.get("is_enhancement")),
                "cost_per_guest": float(item_cost / guests) if guests > 0 else 0,
                "total_cost": float(item_cost),
                "prep_costs": prep_costs
            })

            total_cost += item_cost

        # Calculate revenue and metrics
        price_per_person = Decimal(str(menu.get("price_per_person") or 0))
        min_guests = menu.get("min_guest_count") or 0
        surcharge_per_person = Decimal(str(menu.get("under_min_surcharge") or 0))

        surcharge = Decimal("0")
        if guests < min_guests and surcharge_per_person > 0:
            surcharge = surcharge_per_person * guests

        revenue = (price_per_person * guests) + surcharge
        cost_per_guest = total_cost / guests if guests > 0 else Decimal("0")

        actual_fc_pct = (total_cost / revenue * 100) if revenue > 0 else Decimal("0")
        target_fc_pct = Decimal(str(menu.get("target_food_cost_pct") or 0))
        variance = target_fc_pct - actual_fc_pct if target_fc_pct > 0 else Decimal("0")

        return {
            "menu_id": menu_id,
            "guests": guests,
            "price_per_person": float(price_per_person),
            "min_guest_count": min_guests,
            "surcharge_per_person": float(surcharge_per_person),
            "surcharge_total": float(surcharge),
            "menu_cost_per_guest": float(cost_per_guest),
            "total_menu_cost": float(total_cost),
            "total_revenue": float(revenue),
            "target_food_cost_pct": float(target_fc_pct),
            "actual_food_cost_pct": float(actual_fc_pct),
            "variance_pct": float(variance),
            "item_costs": item_costs
        }


@router.post("")
def create_banquet_menu(menu: BanquetMenuCreate, current_user: dict = Depends(get_current_user)):
    """Create a new banquet menu."""
    if not check_outlet_access(current_user, menu.outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    with get_db() as conn:
        cursor = conn.cursor()
        org_id = current_user["organization_id"]

        try:
            cursor.execute("""
                INSERT INTO banquet_menus (
                    organization_id, outlet_id, meal_period, service_type, name,
                    price_per_person, min_guest_count, under_min_surcharge, target_food_cost_pct
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                org_id, menu.outlet_id, menu.meal_period, menu.service_type, menu.name,
                menu.price_per_person, menu.min_guest_count, menu.under_min_surcharge,
                menu.target_food_cost_pct
            ))

            menu_id = cursor.fetchone()["id"]
            conn.commit()

            return {"message": "Menu created successfully", "menu_id": menu_id}

        except Exception as e:
            if "unique_menu_per_outlet" in str(e):
                raise HTTPException(
                    status_code=400,
                    detail="A menu with this name already exists for this meal period and service type"
                )
            raise


@router.put("/{menu_id}")
def update_banquet_menu(menu_id: int, updates: BanquetMenuUpdate, current_user: dict = Depends(get_current_user)):
    """Update an existing banquet menu."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")

        cursor.execute(f"""
            SELECT id FROM banquet_menus
            WHERE id = %s AND is_active = 1 AND {outlet_filter}
        """, [menu_id] + outlet_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Menu not found or you don't have access")

        # Build update query
        update_fields = []
        params = []

        update_dict = updates.dict(exclude_unset=True)
        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(menu_id)

        cursor.execute(f"""
            UPDATE banquet_menus
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"message": "Menu updated successfully", "menu_id": menu_id}


@router.delete("/{menu_id}")
def delete_banquet_menu(menu_id: int, current_user: dict = Depends(get_current_user)):
    """Delete (soft) a banquet menu."""
    with get_db() as conn:
        cursor = conn.cursor()

        outlet_filter, outlet_params = build_outlet_filter(current_user, "")

        cursor.execute(f"""
            UPDATE banquet_menus
            SET is_active = 0, updated_at = NOW()
            WHERE id = %s AND {outlet_filter}
        """, [menu_id] + outlet_params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Menu not found or you don't have access")

        conn.commit()
        return {"message": "Menu deleted successfully", "menu_id": menu_id}


# ============================================
# Menu Item Endpoints
# ============================================

@router.post("/{menu_id}/items")
def create_menu_item(menu_id: int, item: MenuItemCreate, current_user: dict = Depends(get_current_user)):
    """Add a menu item to a banquet menu."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check menu access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT id FROM banquet_menus bm
            WHERE id = %s AND is_active = 1 AND {outlet_filter}
        """, [menu_id] + outlet_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Menu not found or you don't have access")

        cursor.execute("""
            INSERT INTO banquet_menu_items (
                banquet_menu_id, name, display_order, is_enhancement, additional_price
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            menu_id, item.name, item.display_order,
            int(item.is_enhancement), item.additional_price
        ))

        item_id = cursor.fetchone()["id"]
        conn.commit()

        return {"message": "Menu item created successfully", "item_id": item_id}


@router.put("/items/{item_id}")
def update_menu_item(item_id: int, updates: MenuItemUpdate, current_user: dict = Depends(get_current_user)):
    """Update a menu item."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check access via menu
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bmi.id FROM banquet_menu_items bmi
            JOIN banquet_menus bm ON bm.id = bmi.banquet_menu_id
            WHERE bmi.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [item_id] + outlet_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Menu item not found or you don't have access")

        # Build update query
        update_fields = []
        params = []

        update_dict = updates.dict(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "is_enhancement":
                value = int(value)
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(item_id)

        cursor.execute(f"""
            UPDATE banquet_menu_items
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"message": "Menu item updated successfully", "item_id": item_id}


@router.delete("/items/{item_id}")
def delete_menu_item(item_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a menu item (and its prep items via cascade)."""
    with get_db() as conn:
        cursor = conn.cursor()

        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            DELETE FROM banquet_menu_items
            WHERE id = %s AND banquet_menu_id IN (
                SELECT id FROM banquet_menus bm
                WHERE bm.is_active = 1 AND {outlet_filter}
            )
        """, [item_id] + outlet_params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Menu item not found or you don't have access")

        conn.commit()
        return {"message": "Menu item deleted successfully", "item_id": item_id}


@router.patch("/items/reorder")
def reorder_menu_items(items: List[ReorderItem], current_user: dict = Depends(get_current_user)):
    """Reorder menu items."""
    with get_db() as conn:
        cursor = conn.cursor()

        for item in items:
            cursor.execute("""
                UPDATE banquet_menu_items
                SET display_order = %s, updated_at = NOW()
                WHERE id = %s
            """, (item.display_order, item.id))

        conn.commit()
        return {"message": "Items reordered successfully"}


# ============================================
# Prep Item Endpoints
# ============================================

@router.post("/items/{item_id}/prep")
def create_prep_item(item_id: int, prep: PrepItemCreate, current_user: dict = Depends(get_current_user)):
    """Add a prep item to a menu item."""
    # Validate that at most one of product_id, recipe_id, or common_product_id is set
    link_count = sum(1 for x in [prep.product_id, prep.recipe_id, prep.common_product_id] if x)
    if link_count > 1:
        raise HTTPException(status_code=400, detail="Cannot link to multiple sources - choose product, recipe, or common product")

    with get_db() as conn:
        cursor = conn.cursor()

        # Check menu item access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bmi.id FROM banquet_menu_items bmi
            JOIN banquet_menus bm ON bm.id = bmi.banquet_menu_id
            WHERE bmi.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [item_id] + outlet_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Menu item not found or you don't have access")

        cursor.execute("""
            INSERT INTO banquet_prep_items (
                banquet_menu_item_id, name, display_order, amount_per_guest, amount_unit,
                unit_id, amount_mode, base_amount,
                vessel, vessel_id, vessel_count,
                responsibility, product_id, recipe_id, common_product_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            item_id, prep.name, prep.display_order, prep.amount_per_guest, prep.amount_unit,
            prep.unit_id, prep.amount_mode, prep.base_amount,
            prep.vessel, prep.vessel_id, prep.vessel_count,
            prep.responsibility, prep.product_id, prep.recipe_id, prep.common_product_id
        ))

        prep_id = cursor.fetchone()["id"]
        conn.commit()

        return {"message": "Prep item created successfully", "prep_item_id": prep_id}


@router.put("/prep/{prep_id}")
def update_prep_item(prep_id: int, updates: PrepItemUpdate, current_user: dict = Depends(get_current_user)):
    """Update a prep item."""
    update_dict = updates.dict(exclude_unset=True)

    # Count how many link fields are being set to non-null values
    link_fields = ["product_id", "recipe_id", "common_product_id"]
    links_being_set = sum(1 for f in link_fields if f in update_dict and update_dict[f])
    if links_being_set > 1:
        raise HTTPException(status_code=400, detail="Cannot link to multiple sources - choose product, recipe, or common product")

    with get_db() as conn:
        cursor = conn.cursor()

        # Check access via menu
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bp.id, bp.product_id, bp.recipe_id, bp.common_product_id FROM banquet_prep_items bp
            JOIN banquet_menu_items bmi ON bmi.id = bp.banquet_menu_item_id
            JOIN banquet_menus bm ON bm.id = bmi.banquet_menu_id
            WHERE bp.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [prep_id] + outlet_params)

        existing = dict_from_row(cursor.fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="Prep item not found or you don't have access")

        # Handle clearing links: when setting one link, clear the others
        if "product_id" in update_dict and update_dict["product_id"]:
            update_dict["recipe_id"] = None
            update_dict["common_product_id"] = None
        elif "recipe_id" in update_dict and update_dict["recipe_id"]:
            update_dict["product_id"] = None
            update_dict["common_product_id"] = None
        elif "common_product_id" in update_dict and update_dict["common_product_id"]:
            update_dict["product_id"] = None
            update_dict["recipe_id"] = None

        # Build update query
        update_fields = []
        params = []

        for field, value in update_dict.items():
            update_fields.append(f"{field} = %s")
            params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_fields.append("updated_at = NOW()")
        params.append(prep_id)

        cursor.execute(f"""
            UPDATE banquet_prep_items
            SET {', '.join(update_fields)}
            WHERE id = %s
        """, params)

        conn.commit()
        return {"message": "Prep item updated successfully", "prep_item_id": prep_id}


@router.delete("/prep/{prep_id}")
def delete_prep_item(prep_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a prep item."""
    with get_db() as conn:
        cursor = conn.cursor()

        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            DELETE FROM banquet_prep_items
            WHERE id = %s AND banquet_menu_item_id IN (
                SELECT bmi.id FROM banquet_menu_items bmi
                JOIN banquet_menus bm ON bm.id = bmi.banquet_menu_id
                WHERE bm.is_active = 1 AND {outlet_filter}
            )
        """, [prep_id] + outlet_params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Prep item not found or you don't have access")

        conn.commit()
        return {"message": "Prep item deleted successfully", "prep_item_id": prep_id}


@router.patch("/prep/reorder")
def reorder_prep_items(items: List[ReorderItem], current_user: dict = Depends(get_current_user)):
    """Reorder prep items."""
    with get_db() as conn:
        cursor = conn.cursor()

        for item in items:
            cursor.execute("""
                UPDATE banquet_prep_items
                SET display_order = %s, updated_at = NOW()
                WHERE id = %s
            """, (item.display_order, item.id))

        conn.commit()
        return {"message": "Prep items reordered successfully"}
