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
    amount_unit: Optional[str] = None
    vessel: Optional[str] = None
    responsibility: Optional[str] = None
    product_id: Optional[int] = None
    recipe_id: Optional[int] = None


class PrepItemUpdate(BaseModel):
    """Update an existing prep item."""
    name: Optional[str] = None
    display_order: Optional[int] = None
    amount_per_guest: Optional[float] = None
    amount_unit: Optional[str] = None
    vessel: Optional[str] = None
    responsibility: Optional[str] = None
    product_id: Optional[int] = None
    recipe_id: Optional[int] = None


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

        # Get prep items for each menu item with linked product/recipe info
        for item in menu_items:
            cursor.execute("""
                SELECT
                    bp.*,
                    p.name as product_name,
                    p.unit_id as product_unit_id,
                    u.abbreviation as product_unit_abbr,
                    r.name as recipe_name,
                    -- Get latest unit price for the product
                    (
                        SELECT ph.unit_price
                        FROM price_history ph
                        JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                        WHERE dp.product_id = bp.product_id
                        ORDER BY ph.effective_date DESC
                        LIMIT 1
                    ) as product_unit_cost,
                    -- Get recipe cost per serving
                    r.cost_per_serving as recipe_unit_cost
                FROM banquet_prep_items bp
                LEFT JOIN products p ON p.id = bp.product_id
                LEFT JOIN units u ON u.id = p.unit_id
                LEFT JOIN recipes r ON r.id = bp.recipe_id
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
                    (
                        SELECT ph.unit_price
                        FROM price_history ph
                        JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                        WHERE dp.product_id = bp.product_id
                        ORDER BY ph.effective_date DESC
                        LIMIT 1
                    ) as product_unit_cost,
                    r.cost_per_serving as recipe_unit_cost
                FROM banquet_prep_items bp
                LEFT JOIN recipes r ON r.id = bp.recipe_id
                WHERE bp.banquet_menu_item_id = %s
            """, (item["id"],))

            prep_items = dicts_from_rows(cursor.fetchall())

            for prep in prep_items:
                unit_cost = Decimal("0")
                if prep.get("product_unit_cost"):
                    unit_cost = Decimal(str(prep["product_unit_cost"]))
                elif prep.get("recipe_unit_cost"):
                    unit_cost = Decimal(str(prep["recipe_unit_cost"]))

                amount = Decimal(str(prep.get("amount_per_guest") or 0))
                prep_total = unit_cost * amount * guests

                prep_costs.append({
                    "prep_item_id": prep["id"],
                    "name": prep["name"],
                    "unit_cost": float(unit_cost),
                    "amount_per_guest": float(amount),
                    "total_cost": float(prep_total),
                    "linked": bool(prep.get("product_id") or prep.get("recipe_id"))
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
    # Validate that only one of product_id or recipe_id is set
    if prep.product_id and prep.recipe_id:
        raise HTTPException(status_code=400, detail="Cannot link to both product and recipe")

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
                vessel, responsibility, product_id, recipe_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            item_id, prep.name, prep.display_order, prep.amount_per_guest, prep.amount_unit,
            prep.vessel, prep.responsibility, prep.product_id, prep.recipe_id
        ))

        prep_id = cursor.fetchone()["id"]
        conn.commit()

        return {"message": "Prep item created successfully", "prep_item_id": prep_id}


@router.put("/prep/{prep_id}")
def update_prep_item(prep_id: int, updates: PrepItemUpdate, current_user: dict = Depends(get_current_user)):
    """Update a prep item."""
    # Validate that only one of product_id or recipe_id is set if both are in updates
    update_dict = updates.dict(exclude_unset=True)
    if "product_id" in update_dict and "recipe_id" in update_dict:
        if update_dict["product_id"] and update_dict["recipe_id"]:
            raise HTTPException(status_code=400, detail="Cannot link to both product and recipe")

    with get_db() as conn:
        cursor = conn.cursor()

        # Check access via menu
        outlet_filter, outlet_params = build_outlet_filter(current_user, "bm")

        cursor.execute(f"""
            SELECT bp.id, bp.product_id, bp.recipe_id FROM banquet_prep_items bp
            JOIN banquet_menu_items bmi ON bmi.id = bp.banquet_menu_item_id
            JOIN banquet_menus bm ON bm.id = bmi.banquet_menu_id
            WHERE bp.id = %s AND bm.is_active = 1 AND {outlet_filter}
        """, [prep_id] + outlet_params)

        existing = dict_from_row(cursor.fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="Prep item not found or you don't have access")

        # Handle clearing links: if setting product_id, clear recipe_id and vice versa
        if "product_id" in update_dict and update_dict["product_id"]:
            update_dict["recipe_id"] = None
        elif "recipe_id" in update_dict and update_dict["recipe_id"]:
            update_dict["product_id"] = None

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
