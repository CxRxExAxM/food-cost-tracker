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
from ..utils.conversions import get_unit_conversion_factor, get_base_conversion_factor, get_unit_id_from_abbreviation

router = APIRouter(prefix="/banquet-menus", tags=["banquet-menus"])


def _get_calculate_ingredient_costs():
    """Lazy import to avoid circular dependency."""
    from .recipes import _calculate_ingredient_costs
    return _calculate_ingredient_costs


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
    menu_type: Optional[str] = 'banquet'  # 'banquet' or 'restaurant'


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
    choice_count: Optional[int] = None  # For "Choose X" items


class MenuItemUpdate(BaseModel):
    """Update an existing menu item."""
    name: Optional[str] = None
    display_order: Optional[int] = None
    is_enhancement: Optional[bool] = None
    additional_price: Optional[float] = None
    choice_count: Optional[int] = None  # For "Choose X" items


class BanquetMenuImportItem(BaseModel):
    """Single row for bulk import."""
    meal_period: str
    service_type: str
    menu_name: str
    menu_item: str
    prep_item: Optional[str] = None
    choice_count: Optional[int] = None


class BanquetMenuImportRequest(BaseModel):
    """Bulk import request for banquet menus."""
    outlet_id: int
    items: List[BanquetMenuImportItem]


class PrepItemCreate(BaseModel):
    """Create a new prep item."""
    name: str
    display_order: Optional[int] = 0
    amount_per_guest: Optional[float] = None
    amount_unit: Optional[str] = None  # Legacy field, prefer unit_id
    unit_id: Optional[int] = None
    amount_mode: Optional[str] = 'per_person'  # Legacy: 'per_person', 'at_minimum', 'fixed'
    base_amount: Optional[float] = None  # Legacy: for at_minimum/fixed modes
    guests_per_amount: Optional[int] = 1  # New: 1 = per person, 10 = per 10 guests
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
    amount_mode: Optional[str] = None  # Legacy: 'per_person', 'at_minimum', 'fixed'
    base_amount: Optional[float] = None  # Legacy: for at_minimum/fixed modes
    guests_per_amount: Optional[int] = None  # New: 1 = per person, 10 = per 10 guests
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
    menu_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List banquet menus with optional filtering.

    - **outlet_id**: Filter by specific outlet (required unless admin)
    - **meal_period**: Filter by meal period
    - **service_type**: Filter by service type
    - **menu_type**: Filter by menu type ('banquet' or 'restaurant')
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

        if menu_type:
            where_clauses.append("bm.menu_type = %s")
            params.append(menu_type)

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
    menu_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get distinct meal periods for an outlet, optionally filtered by menu type."""
    if not check_outlet_access(current_user, outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT DISTINCT meal_period
            FROM banquet_menus
            WHERE outlet_id = %s AND is_active = 1
        """
        params = [outlet_id]

        if menu_type:
            query += " AND menu_type = %s"
            params.append(menu_type)

        query += " ORDER BY meal_period"

        cursor.execute(query, params)

        periods = [row["meal_period"] for row in cursor.fetchall()]
        return {"meal_periods": periods}


@router.get("/service-types")
def get_service_types(
    outlet_id: int,
    meal_period: Optional[str] = None,
    menu_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get distinct service types for an outlet, optionally filtered by meal period and menu type."""
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

        if menu_type:
            query += " AND menu_type = %s"
            params.append(menu_type)

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
    guests: Optional[int] = Query(None, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """Calculate menu cost for a given number of guests.

    For restaurant menus, guests is always 1 (single portion).
    For banquet menus, guests defaults to 50 if not specified.
    """
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

        # For restaurant menus, always use guests=1
        is_restaurant = menu.get('menu_type') == 'restaurant'
        if is_restaurant:
            guests = 1
        elif guests is None:
            guests = 50  # Default for banquet

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
                    -- Check if product is catch weight (pricing is per LB)
                    (
                        SELECT p.is_catch_weight
                        FROM products p
                        WHERE p.id = bp.product_id
                    ) as product_is_catch_weight,
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
                    ) as common_product_pricing_unit_id,
                    -- Check if any linked common product has catch weight products
                    (
                        SELECT MAX(p2.is_catch_weight)
                        FROM products p2
                        WHERE p2.common_product_id = bp.common_product_id
                    ) as common_product_is_catch_weight
                FROM banquet_prep_items bp
                LEFT JOIN vessels v ON v.id = bp.vessel_id
                WHERE bp.banquet_menu_item_id = %s
            """, (item["id"],))

            prep_items = dicts_from_rows(cursor.fetchall())
            org_id = current_user["organization_id"]

            # Get LB unit ID for catch weight products (they're always priced per LB)
            cursor.execute("SELECT id FROM units WHERE UPPER(abbreviation) = 'LB' LIMIT 1")
            lb_unit_result = cursor.fetchone()
            lb_unit_id = lb_unit_result['id'] if lb_unit_result else None

            for prep in prep_items:
                unit_cost = Decimal("0")
                pricing_unit_id = None
                linked_common_product_id = None
                is_catch_weight = False

                if prep.get("product_unit_cost"):
                    unit_cost = Decimal(str(prep["product_unit_cost"]))
                    pricing_unit_id = prep.get("product_pricing_unit_id")
                    is_catch_weight = bool(prep.get("product_is_catch_weight"))
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
                    is_catch_weight = bool(prep.get("common_product_is_catch_weight"))
                elif prep.get("recipe_id"):
                    # Calculate recipe cost and get cost per yield unit
                    cursor.execute("""
                        SELECT r.id, r.yield_amount, r.yield_unit_id, r.outlet_id
                        FROM recipes r
                        WHERE r.id = %s
                    """, (prep["recipe_id"],))
                    recipe_info = dict_from_row(cursor.fetchone())

                    if recipe_info:
                        recipe_outlet_id = recipe_info.get("outlet_id") or menu.get("outlet_id")
                        # Calculate total recipe cost using shared function (lazy import to avoid circular dep)
                        calculate_costs = _get_calculate_ingredient_costs()
                        _, recipe_total_cost = calculate_costs(
                            cursor, prep["recipe_id"], recipe_outlet_id, visited=set(), org_id=org_id
                        )

                        recipe_yield = recipe_info.get("yield_amount")
                        recipe_yield_unit_id = recipe_info.get("yield_unit_id")

                        if recipe_total_cost > 0 and recipe_yield and recipe_yield > 0:
                            # Cost per yield unit (e.g., cost per gallon)
                            unit_cost = Decimal(str(recipe_total_cost)) / Decimal(str(recipe_yield))
                            pricing_unit_id = recipe_yield_unit_id

                # For catch weight products, pricing is always per LB regardless of display unit
                if is_catch_weight and lb_unit_id:
                    pricing_unit_id = lb_unit_id

                # Get prep item's unit - prefer unit_id, fallback to looking up from amount_unit text
                prep_unit_id = prep.get("unit_id")
                if not prep_unit_id and prep.get("amount_unit"):
                    prep_unit_id = get_unit_id_from_abbreviation(cursor, prep["amount_unit"])

                # Apply unit conversion if prep item unit differs from pricing unit
                if prep_unit_id and pricing_unit_id and prep_unit_id != pricing_unit_id:
                    # Convert: we have price per pricing_unit, we want price per prep_unit
                    # e.g., price is $22.4/LB, prep is 6 OZ, conversion OZ->LB = 0.0625
                    # so cost per OZ = $22.4 * 0.0625 = $1.40
                    # total for 6 OZ = $1.40 * 6 = $8.40
                    conversion_factor = get_unit_conversion_factor(
                        cursor, linked_common_product_id, prep_unit_id, pricing_unit_id, org_id,
                        outlet_id=menu.get("outlet_id")
                    )
                    unit_cost = unit_cost * Decimal(str(conversion_factor))

                # Calculate amount - supports both old (amount_mode) and new (guests_per_amount) formats
                calculated_amount = Decimal("0")
                amount_mode = prep.get("amount_mode") or "per_person"
                guests_per_amount = prep.get("guests_per_amount") or 1

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
                    # Check for new guests_per_amount field first
                    if prep.get("guests_per_amount") is not None:
                        # New calculation: amount * (guests / guests_per_amount)
                        amount_per_guest = Decimal(str(prep.get("amount_per_guest") or 0))
                        gpa = Decimal(str(guests_per_amount))
                        if gpa > 0:
                            calculated_amount = amount_per_guest * (guests / gpa)
                        else:
                            calculated_amount = amount_per_guest * guests
                    else:
                        # Legacy calculation using amount_mode
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
                    "guests_per_amount": int(guests_per_amount),
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
        # Surcharge only applies to banquet menus
        if not is_restaurant and guests < min_guests and surcharge_per_person > 0:
            surcharge = surcharge_per_person * guests

        revenue = (price_per_person * guests) + surcharge
        cost_per_guest = total_cost / guests if guests > 0 else Decimal("0")

        actual_fc_pct = (total_cost / revenue * 100) if revenue > 0 else Decimal("0")
        target_fc_pct = Decimal(str(menu.get("target_food_cost_pct") or 0))
        variance = target_fc_pct - actual_fc_pct if target_fc_pct > 0 else Decimal("0")

        return {
            "menu_id": menu_id,
            "menu_type": menu.get("menu_type", "banquet"),
            "guests": guests,
            "price_per_person": float(price_per_person),
            "min_guest_count": min_guests if not is_restaurant else None,
            "surcharge_per_person": float(surcharge_per_person) if not is_restaurant else None,
            "surcharge_total": float(surcharge) if not is_restaurant else None,
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
                    price_per_person, min_guest_count, under_min_surcharge, target_food_cost_pct,
                    menu_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                org_id, menu.outlet_id, menu.meal_period, menu.service_type, menu.name,
                menu.price_per_person, menu.min_guest_count, menu.under_min_surcharge,
                menu.target_food_cost_pct, menu.menu_type or 'banquet'
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

        # Get minimum display_order to insert at top
        cursor.execute("""
            SELECT COALESCE(MIN(display_order), 0) - 1 as new_order
            FROM banquet_menu_items WHERE banquet_menu_id = %s
        """, (menu_id,))
        new_order = cursor.fetchone()["new_order"]

        cursor.execute("""
            INSERT INTO banquet_menu_items (
                banquet_menu_id, name, display_order, is_enhancement, additional_price, choice_count
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            menu_id, item.name, new_order,
            int(item.is_enhancement), item.additional_price, item.choice_count
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

        # Get minimum display_order to insert at top
        cursor.execute("""
            SELECT COALESCE(MIN(display_order), 0) - 1 as new_order
            FROM banquet_prep_items WHERE banquet_menu_item_id = %s
        """, (item_id,))
        new_order = cursor.fetchone()["new_order"]

        # Use old columns (amount_mode) which always exist
        # The cost calculation will use guests_per_amount if available, otherwise derive from amount_mode
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
            item_id, prep.name, new_order, prep.amount_per_guest, prep.amount_unit,
            prep.unit_id, prep.amount_mode or 'per_person', prep.base_amount,
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

        # Check if guests_per_amount column exists (migration 014)
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'banquet_prep_items' AND column_name = 'guests_per_amount'
        """)
        has_guests_per_amount = cursor.fetchone() is not None

        # Remove guests_per_amount from update if column doesn't exist
        if not has_guests_per_amount and "guests_per_amount" in update_dict:
            del update_dict["guests_per_amount"]

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


# ============================================
# Bulk Import Endpoint
# ============================================

@router.post("/import")
def import_banquet_menus(
    request: BanquetMenuImportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk import banquet menus from CSV-like data.

    Handles deduplication at each level:
    - Menu: unique by (outlet_id, meal_period, service_type, name)
    - Menu Item: unique by (menu_id, name)
    - Prep Item: unique by (menu_item_id, name)

    Returns summary of what was created vs skipped.
    """
    if not check_outlet_access(current_user, request.outlet_id):
        raise HTTPException(status_code=403, detail="You don't have access to this outlet")

    org_id = current_user["organization_id"]

    # Track what we created vs skipped
    stats = {
        "menus_created": 0,
        "menus_skipped": 0,
        "items_created": 0,
        "items_skipped": 0,
        "prep_items_created": 0,
        "prep_items_skipped": 0,
        "errors": []
    }

    # Cache for lookups (avoid repeated DB queries)
    menu_cache = {}  # (meal_period, service_type, name) -> menu_id
    item_cache = {}  # (menu_id, item_name) -> item_id

    with get_db() as conn:
        cursor = conn.cursor()

        # Pre-load existing menus for this outlet
        cursor.execute("""
            SELECT id, meal_period, service_type, name
            FROM banquet_menus
            WHERE outlet_id = %s AND organization_id = %s AND is_active = 1
        """, (request.outlet_id, org_id))

        for row in cursor.fetchall():
            key = (row["meal_period"], row["service_type"], row["name"])
            menu_cache[key] = row["id"]

        # Process each import item
        for idx, item in enumerate(request.items):
            try:
                # 1. Get or create menu
                menu_key = (item.meal_period, item.service_type, item.menu_name)

                if menu_key in menu_cache:
                    menu_id = menu_cache[menu_key]
                    # Only count as skipped the first time we see this menu
                    if menu_key not in getattr(import_banquet_menus, '_seen_menus', set()):
                        stats["menus_skipped"] += 1
                        if not hasattr(import_banquet_menus, '_seen_menus'):
                            import_banquet_menus._seen_menus = set()
                        import_banquet_menus._seen_menus.add(menu_key)
                else:
                    # Create new menu
                    cursor.execute("""
                        INSERT INTO banquet_menus (
                            organization_id, outlet_id, meal_period, service_type, name
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (org_id, request.outlet_id, item.meal_period, item.service_type, item.menu_name))

                    menu_id = cursor.fetchone()["id"]
                    menu_cache[menu_key] = menu_id
                    stats["menus_created"] += 1

                # 2. Get or create menu item
                item_key = (menu_id, item.menu_item)

                if item_key in item_cache:
                    item_id = item_cache[item_key]
                    stats["items_skipped"] += 1
                else:
                    # Check if item exists in DB (in case cache was pre-populated only with menus)
                    cursor.execute("""
                        SELECT id FROM banquet_menu_items
                        WHERE banquet_menu_id = %s AND name = %s
                    """, (menu_id, item.menu_item))

                    existing_item = cursor.fetchone()
                    if existing_item:
                        item_id = existing_item["id"]
                        item_cache[item_key] = item_id
                        stats["items_skipped"] += 1
                    else:
                        # Get next display order (at bottom for imports)
                        cursor.execute("""
                            SELECT COALESCE(MAX(display_order), 0) + 1 as next_order
                            FROM banquet_menu_items WHERE banquet_menu_id = %s
                        """, (menu_id,))
                        next_order = cursor.fetchone()["next_order"]

                        # Create new menu item
                        cursor.execute("""
                            INSERT INTO banquet_menu_items (
                                banquet_menu_id, name, display_order, choice_count
                            )
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                        """, (menu_id, item.menu_item, next_order, item.choice_count))

                        item_id = cursor.fetchone()["id"]
                        item_cache[item_key] = item_id
                        stats["items_created"] += 1

                # 3. Create prep item if provided
                if item.prep_item and item.prep_item.strip():
                    prep_name = item.prep_item.strip()

                    # Check if prep item exists
                    cursor.execute("""
                        SELECT id FROM banquet_prep_items
                        WHERE banquet_menu_item_id = %s AND name = %s
                    """, (item_id, prep_name))

                    if cursor.fetchone():
                        stats["prep_items_skipped"] += 1
                    else:
                        # Get next display order
                        cursor.execute("""
                            SELECT COALESCE(MAX(display_order), 0) + 1 as next_order
                            FROM banquet_prep_items WHERE banquet_menu_item_id = %s
                        """, (item_id,))
                        next_order = cursor.fetchone()["next_order"]

                        # Create prep item
                        cursor.execute("""
                            INSERT INTO banquet_prep_items (
                                banquet_menu_item_id, name, display_order
                            )
                            VALUES (%s, %s, %s)
                        """, (item_id, prep_name, next_order))

                        stats["prep_items_created"] += 1

            except Exception as e:
                stats["errors"].append(f"Row {idx + 1}: {str(e)}")

        conn.commit()

        # Clean up the seen_menus tracker
        if hasattr(import_banquet_menus, '_seen_menus'):
            del import_banquet_menus._seen_menus

    return {
        "message": "Import completed",
        "stats": stats
    }
