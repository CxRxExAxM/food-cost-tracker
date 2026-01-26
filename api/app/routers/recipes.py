from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Recipe, RecipeCreate, RecipeWithIngredients, RecipeWithCost
from ..auth import get_current_user, build_outlet_filter, check_outlet_access
from .banquet_menus import get_unit_conversion_factor
import json

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[Recipe])
def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    search: Optional[str] = None,
    category_path: Optional[str] = None,
    outlet_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List recipes with optional filtering.

    - **outlet_id**: Filter by specific outlet (must be one user has access to)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Build outlet filter
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        query = f"SELECT * FROM recipes WHERE is_active = 1 AND {outlet_filter}"
        params = outlet_params

        # If specific outlet requested, add additional filter
        if outlet_id is not None:
            query += " AND outlet_id = %s"
            params.append(outlet_id)

        if search:
            query += " AND name ILIKE %s"
            params.append(f"%{search}%")

        if category_path:
            query += " AND category_path LIKE %s"
            params.append(f"{category_path}%")

        query += " ORDER BY category_path, name LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cursor.execute(query, params)
        recipes = dicts_from_rows(cursor.fetchall())

        # Parse method JSON if present
        for recipe in recipes:
            if recipe.get('method'):
                recipe['method'] = json.loads(recipe['method'])

        return recipes


@router.get("/{recipe_id}", response_model=RecipeWithIngredients)
def get_recipe(recipe_id: int, current_user: dict = Depends(get_current_user)):
    """
    Get a single recipe with ingredients .
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get recipe - verify user has access
            outlet_filter, outlet_params = build_outlet_filter(current_user, "")
            query = f"SELECT * FROM recipes WHERE id = %s AND {outlet_filter}"
            params = [recipe_id] + outlet_params

            cursor.execute(query, params)
            recipe = dict_from_row(cursor.fetchone())

            if not recipe:
                raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

            # Parse method JSON
            if recipe.get('method'):
                recipe['method'] = json.loads(recipe['method'])

            # Get ingredients with display names (product, sub-recipe, or text-only)
            cursor.execute("""
                SELECT ri.*,
                       ri.ingredient_name,
                       cp.common_name,
                       u.abbreviation as unit_abbreviation,
                       r.name as sub_recipe_name
                FROM recipe_ingredients ri
                LEFT JOIN common_products cp ON cp.id = ri.common_product_id
                LEFT JOIN units u ON u.id = ri.unit_id
                LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
                WHERE ri.recipe_id = %s
                ORDER BY ri.id
            """, (recipe_id,))

            recipe['ingredients'] = dicts_from_rows(cursor.fetchall())

            return recipe
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] Get recipe {recipe_id} failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get recipe: {str(e)}")


@router.post("", response_model=Recipe, status_code=201)
def create_recipe(recipe: RecipeCreate, outlet_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    """
    Create a new recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        organization_id = current_user["organization_id"]

        # Determine outlet_id
        if not outlet_id:
            # No outlet specified - get first available outlet for user
            from ..auth import get_user_outlet_ids
            user_outlet_ids = get_user_outlet_ids(current_user["id"])

            if not user_outlet_ids:
                # Org-wide admin - use first outlet in organization
                cursor.execute("""
                    SELECT id FROM outlets
                    WHERE organization_id = %s AND is_active = 1
                    ORDER BY id LIMIT 1
                """, (organization_id,))
                outlet_row = cursor.fetchone()
                if not outlet_row:
                    raise HTTPException(status_code=400, detail="No active outlets found in organization")
                outlet_id = outlet_row["id"]
            else:
                # Use user's first assigned outlet
                outlet_id = user_outlet_ids[0]
        else:
            # Outlet specified - verify user has access
            if not check_outlet_access(current_user, outlet_id):
                raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        # Serialize method to JSON
        method_json = json.dumps([step.dict() for step in recipe.method]) if recipe.method else None

        cursor.execute("""
            INSERT INTO recipes (
                name, description, category, category_path,
                yield_amount, yield_unit_id, prep_time_minutes, cook_time_minutes,
                method, organization_id, outlet_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            recipe.name,
            recipe.description,
            recipe.category,
            recipe.category_path,
            recipe.yield_amount,
            recipe.yield_unit_id,
            recipe.prep_time_minutes,
            recipe.cook_time_minutes,
            method_json,
            organization_id,
            outlet_id
        ))

        recipe_id = cursor.fetchone()["id"]

        # Insert ingredients (TODO: implement in Phase 2)
        for ingredient in recipe.ingredients:
            cursor.execute("""
                INSERT INTO recipe_ingredients (
                    recipe_id, common_product_id, sub_recipe_id,
                    quantity, unit_id, yield_percentage, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                recipe_id,
                ingredient.common_product_id,
                ingredient.sub_recipe_id,
                ingredient.quantity,
                ingredient.unit_id,
                ingredient.yield_percentage,
                ingredient.notes
            ))

        conn.commit()

        # Fetch created recipe
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
        created_recipe = dict_from_row(cursor.fetchone())

        if created_recipe.get('method'):
            created_recipe['method'] = json.loads(created_recipe['method'])

        return created_recipe


@router.patch("/{recipe_id}", response_model=Recipe)
def update_recipe(recipe_id: int, updates: dict, current_user: dict = Depends(get_current_user)):
    """
    Update a recipe .

    TODO Phase 1: Implement basic updates
    TODO Phase 2: Handle ingredient updates
    TODO Phase 3: Validate changes
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if recipe exists and user has access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        check_query = f"SELECT id FROM recipes WHERE id = %s AND {outlet_filter}"
        check_params = [recipe_id] + outlet_params
        cursor.execute(check_query, check_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        # Build update query
        allowed_fields = [
            'name', 'description', 'category', 'category_path',
            'yield_amount', 'yield_unit_id', 'servings', 'serving_unit_id',
            'prep_time_minutes', 'cook_time_minutes', 'method', 'notes'
        ]

        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                # Serialize method if present
                if field == 'method' and value:
                    value = json.dumps(value)
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.extend([recipe_id])
        query = f"UPDATE recipes SET {', '.join(update_fields)} WHERE id = %s"

        cursor.execute(query, params)
        conn.commit()

        # Fetch updated recipe
        cursor.execute("SELECT * FROM recipes WHERE id = %s", (recipe_id,))
        updated_recipe = dict_from_row(cursor.fetchone())

        if updated_recipe.get('method'):
            updated_recipe['method'] = json.loads(updated_recipe['method'])

        return updated_recipe


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, current_user: dict = Depends(get_current_user)):
    """
    Delete a recipe (soft delete, ).

    TODO Phase 1: Implement soft delete
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Build outlet filter
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        query = f"UPDATE recipes SET is_active = 0 WHERE id = %s AND {outlet_filter}"
        params = [recipe_id] + outlet_params

        cursor.execute(query, params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        conn.commit()

        return {"message": "Recipe deleted successfully", "recipe_id": recipe_id}


@router.get("/debug/common-product/{common_product_id}/products")
def debug_common_product_products(common_product_id: int, current_user: dict = Depends(get_current_user)):
    """
    Show ALL products mapped to a common product, across all outlets.
    Helps diagnose outlet assignment issues.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get common product info
        cursor.execute("SELECT * FROM common_products WHERE id = %s", (common_product_id,))
        common_product = dict_from_row(cursor.fetchone())

        if not common_product:
            raise HTTPException(status_code=404, detail="Common product not found")

        # Get ALL products for this common product (any outlet)
        cursor.execute("""
            SELECT
                p.id as product_id,
                p.name as product_name,
                p.outlet_id,
                o.name as outlet_name,
                p.common_product_id,
                d.name as distributor_name,
                ph.unit_price,
                ph.effective_date
            FROM products p
            JOIN outlets o ON o.id = p.outlet_id
            JOIN distributor_products dp ON dp.product_id = p.id
            JOIN distributors d ON d.id = dp.distributor_id
            LEFT JOIN (
                SELECT distributor_product_id, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
            WHERE p.common_product_id = %s
            ORDER BY p.outlet_id, ph.unit_price ASC NULLS LAST
        """, (common_product_id,))

        products = dicts_from_rows(cursor.fetchall())

        return {
            "common_product_id": common_product_id,
            "common_product_name": common_product['common_name'],
            "total_products_found": len(products),
            "products_by_outlet": products
        }


@router.get("/{recipe_id}/cost/debug")
def debug_recipe_cost(recipe_id: int, current_user: dict = Depends(get_current_user)):
    """
    Debug endpoint to see why costs aren't calculating.
    Shows what products/prices exist for each ingredient.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get recipe
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        query = f"SELECT * FROM recipes WHERE id = %s AND {outlet_filter}"
        params = [recipe_id] + outlet_params
        cursor.execute(query, params)
        recipe = dict_from_row(cursor.fetchone())

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Get ingredients
        cursor.execute("""
            SELECT ri.*,
                   cp.common_name
            FROM recipe_ingredients ri
            LEFT JOIN common_products cp ON cp.id = ri.common_product_id
            WHERE ri.recipe_id = %s
            ORDER BY ri.id
        """, (recipe_id,))

        ingredients = dicts_from_rows(cursor.fetchall())
        debug_info = []

        for ing in ingredients:
            ing_debug = {
                "ingredient_id": ing['id'],
                "name": ing.get('common_name') or ing.get('ingredient_name'),
                "common_product_id": ing.get('common_product_id'),
                "quantity": ing['quantity'],
                "products_found": []
            }

            if ing.get('common_product_id'):
                # Check what products exist for this outlet + common product
                cursor.execute("""
                    SELECT
                        p.id as product_id,
                        p.name as product_name,
                        p.outlet_id,
                        d.name as distributor_name,
                        ph.unit_price,
                        ph.effective_date
                    FROM products p
                    JOIN distributor_products dp ON dp.product_id = p.id
                    JOIN distributors d ON d.id = dp.distributor_id
                    LEFT JOIN (
                        SELECT distributor_product_id, unit_price, effective_date,
                               ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                        FROM price_history
                    ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
                    WHERE p.common_product_id = %s AND p.outlet_id = %s
                    ORDER BY ph.unit_price ASC NULLS LAST
                """, (ing['common_product_id'], recipe['outlet_id']))

                products = dicts_from_rows(cursor.fetchall())
                ing_debug["products_found"] = products
                ing_debug["has_price"] = any(p.get('unit_price') is not None for p in products)

            debug_info.append(ing_debug)

        return {
            "recipe_id": recipe_id,
            "recipe_name": recipe['name'],
            "outlet_id": recipe['outlet_id'],
            "ingredients": debug_info
        }


@router.get("/{recipe_id}/cost", response_model=RecipeWithCost)
def calculate_recipe_cost(recipe_id: int, current_user: dict = Depends(get_current_user)):
    """
    Calculate total cost of a recipe with breakdown .

    Returns:
    - Total cost of all ingredients
    - Cost per serving (if yield_amount is set)
    - Breakdown by ingredient with prices and percentages
    - Flags for missing price data
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get recipe with yield and serving unit info - verify outlet access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "r")
        query = f"""
            SELECT r.*,
                   yu.abbreviation as yield_unit_abbreviation,
                   su.abbreviation as serving_unit_abbreviation
            FROM recipes r
            LEFT JOIN units yu ON yu.id = r.yield_unit_id
            LEFT JOIN units su ON su.id = r.serving_unit_id
            WHERE r.id = %s AND {outlet_filter}
        """
        params = [recipe_id] + outlet_params
        cursor.execute(query, params)
        recipe = dict_from_row(cursor.fetchone())

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        # Parse method JSON
        if recipe.get('method'):
            recipe['method'] = json.loads(recipe['method'])

        # Calculate costs recursively - use recipe's outlet_id for product filtering
        ingredients_with_costs, total_cost = _calculate_ingredient_costs(
            cursor, recipe_id, recipe['outlet_id'], visited=set(),
            org_id=current_user["organization_id"]
        )

        # Calculate cost per serving (use servings field, fallback to yield_amount for backwards compat)
        cost_per_serving = None
        servings = recipe.get('servings') or recipe.get('yield_amount')
        if servings and servings > 0:
            cost_per_serving = total_cost / servings

        # Add percentage of total to each ingredient
        for ing in ingredients_with_costs:
            if total_cost > 0 and ing.get('cost') is not None:
                ing['cost_percentage'] = round((ing['cost'] / total_cost) * 100, 1)
            else:
                ing['cost_percentage'] = None

        # Calculate allergens from all ingredients
        allergen_summary = _calculate_recipe_allergens(cursor, recipe_id, visited=set())

        return {
            **recipe,
            "total_cost": round(total_cost, 2),
            "cost_per_serving": round(cost_per_serving, 2) if cost_per_serving else None,
            "ingredients": ingredients_with_costs,
            "allergens": allergen_summary
        }


def _calculate_ingredient_costs(cursor, recipe_id: int, outlet_id: int, visited: set, org_id: int = None) -> tuple[list[dict], float]:
    """
    Recursively calculate costs for all ingredients in a recipe.

    Args:
        cursor: Database cursor
        recipe_id: Recipe ID to calculate
        outlet_id: Outlet ID to filter products (for outlet-specific pricing)
        visited: Set of recipe IDs already visited (prevents infinite recursion)
        org_id: Organization ID for conversion lookups (will be looked up from outlet if not provided)

    Returns:
        Tuple of (ingredients_with_costs, total_cost)
    """
    # Get org_id from outlet if not provided
    if org_id is None and outlet_id:
        cursor.execute("SELECT organization_id FROM outlets WHERE id = %s", (outlet_id,))
        outlet_row = cursor.fetchone()
        if outlet_row:
            org_id = outlet_row['organization_id']
    # Prevent infinite recursion from circular sub-recipe references
    if recipe_id in visited:
        return [], 0.0
    visited.add(recipe_id)

    # Get all ingredients for this recipe
    cursor.execute("""
        SELECT ri.*,
               ri.ingredient_name,
               cp.common_name,
               u.abbreviation as unit_abbreviation,
               r.name as sub_recipe_name,
               r.yield_amount as sub_recipe_yield,
               r.outlet_id as sub_recipe_outlet_id
        FROM recipe_ingredients ri
        LEFT JOIN common_products cp ON cp.id = ri.common_product_id
        LEFT JOIN units u ON u.id = ri.unit_id
        LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
        WHERE ri.recipe_id = %s
        ORDER BY ri.id
    """, (recipe_id,))

    ingredients = dicts_from_rows(cursor.fetchall())
    ingredients_with_costs = []
    total_cost = 0.0

    for ing in ingredients:
        ing_cost = None
        unit_price = None
        has_price = False
        price_source = None

        if ing.get('common_product_id'):
            # Get lowest unit price for this common product from same outlet
            cursor.execute("""
                SELECT
                    ph.unit_price,
                    p.unit_id as product_unit_id,
                    d.name as distributor_name,
                    p.name as product_name,
                    p.pack,
                    p.size,
                    u.abbreviation as product_unit
                FROM products p
                JOIN distributor_products dp ON dp.product_id = p.id
                JOIN distributors d ON d.id = dp.distributor_id
                LEFT JOIN units u ON u.id = p.unit_id
                LEFT JOIN (
                    SELECT distributor_product_id, unit_price,
                           ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                    FROM price_history
                ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
                WHERE p.common_product_id = %s AND p.outlet_id = %s AND ph.unit_price IS NOT NULL
                ORDER BY ph.unit_price ASC
                LIMIT 1
            """, (ing['common_product_id'], outlet_id))

            price_row = dict_from_row(cursor.fetchone())

            if price_row and price_row.get('unit_price'):
                unit_price = price_row['unit_price']
                product_unit_id = price_row['product_unit_id']
                ingredient_unit_id = ing['unit_id']
                yield_pct = ing.get('yield_percentage', 100) or 100

                # Check if units match
                if product_unit_id == ingredient_unit_id:
                    # Direct calculation - units match
                    ing_cost = ing['quantity'] * unit_price * (100 / yield_pct)
                    has_price = True
                    price_source = f"{price_row['distributor_name']}: {price_row['product_name']}"
                    total_cost += ing_cost

                else:
                    # Units don't match - use shared conversion logic
                    # This checks: product conversions, chained conversions, and base conversions
                    conversion_factor = get_unit_conversion_factor(
                        cursor,
                        ing['common_product_id'],
                        ingredient_unit_id,
                        product_unit_id,
                        org_id,
                        outlet_id
                    )

                    if conversion_factor != 1.0 or ingredient_unit_id == product_unit_id:
                        # Conversion found or units actually match
                        converted_quantity = ing['quantity'] * conversion_factor
                        ing_cost = converted_quantity * unit_price * (100 / yield_pct)
                        has_price = True
                        if conversion_factor != 1.0:
                            price_source = f"{price_row['distributor_name']}: {price_row['product_name']} (converted {ing.get('unit_abbreviation')} → {price_row.get('product_unit')})"
                        else:
                            price_source = f"{price_row['distributor_name']}: {price_row['product_name']}"
                        total_cost += ing_cost
                    else:
                        # No conversion available - log warning and use direct calc (may be inaccurate)
                        print(f"[WARN] No conversion from unit {ingredient_unit_id} ({ing.get('unit_abbreviation')}) to {product_unit_id} ({price_row.get('product_unit')}) for common_product {ing['common_product_id']}")
                        ing_cost = ing['quantity'] * unit_price * (100 / yield_pct)
                        has_price = True
                        price_source = f"{price_row['distributor_name']}: {price_row['product_name']} (unit mismatch: {ing.get('unit_abbreviation')} vs {price_row.get('product_unit')})"
                        total_cost += ing_cost

        elif ing.get('sub_recipe_id'):
            # Recursively calculate sub-recipe cost - use sub-recipe's outlet_id
            sub_outlet_id = ing.get('sub_recipe_outlet_id', outlet_id)  # Fallback to parent if missing
            _, sub_recipe_total = _calculate_ingredient_costs(
                cursor, ing['sub_recipe_id'], sub_outlet_id, visited.copy(), org_id
            )

            if sub_recipe_total > 0:
                has_price = True
                price_source = f"Sub-recipe: {ing.get('sub_recipe_name', 'Unknown')}"

                # If sub-recipe has yield, calculate cost per unit of yield
                sub_yield = ing.get('sub_recipe_yield')
                if sub_yield and sub_yield > 0:
                    # Cost per unit of sub-recipe yield * quantity needed
                    cost_per_yield_unit = sub_recipe_total / sub_yield
                    ing_cost = cost_per_yield_unit * ing['quantity']
                else:
                    # Use full sub-recipe cost * quantity (assume quantity=1 means full recipe)
                    ing_cost = sub_recipe_total * ing['quantity']

                total_cost += ing_cost

        elif ing.get('ingredient_name') and not ing.get('common_product_id') and not ing.get('sub_recipe_id'):
            # Text-only ingredient - no cost available
            has_price = False
            price_source = "Not mapped to product"

        ingredients_with_costs.append({
            **ing,
            'unit_price': round(unit_price, 4) if unit_price else None,
            'cost': round(ing_cost, 2) if ing_cost else None,
            'has_price': has_price,
            'price_source': price_source
        })

    return ingredients_with_costs, total_cost


# Allergen field names
ALLERGEN_FIELDS = [
    'allergen_gluten', 'allergen_dairy', 'allergen_egg', 'allergen_fish',
    'allergen_crustation', 'allergen_mollusk', 'allergen_tree_nuts', 'allergen_peanuts',
    'allergen_soy', 'allergen_sesame', 'allergen_mustard', 'allergen_celery',
    'allergen_lupin', 'allergen_sulphur_dioxide', 'allergen_vegan', 'allergen_vegetarian'
]


def _calculate_recipe_allergens(cursor, recipe_id: int, visited: set) -> dict:
    """
    Calculate allergens for a recipe from all its ingredients.

    Returns a dict with:
    - contains: list of allergens present in any ingredient
    - vegan: True if all ingredients are vegan-flagged
    - vegetarian: True if all ingredients are vegetarian-flagged
    - by_ingredient: list of which ingredients have which allergens
    """
    if recipe_id in visited:
        return {"contains": [], "vegan": False, "vegetarian": False, "by_ingredient": []}
    visited.add(recipe_id)

    # Get all ingredients with their common product allergens
    cursor.execute("""
        SELECT ri.id, ri.common_product_id, ri.sub_recipe_id, ri.ingredient_name,
               cp.common_name,
               cp.allergen_gluten, cp.allergen_dairy, cp.allergen_egg, cp.allergen_fish,
               cp.allergen_crustation, cp.allergen_mollusk, cp.allergen_tree_nuts,
               cp.allergen_peanuts, cp.allergen_soy, cp.allergen_sesame,
               cp.allergen_mustard, cp.allergen_celery, cp.allergen_lupin,
               cp.allergen_sulphur_dioxide, cp.allergen_vegan, cp.allergen_vegetarian,
               r.name as sub_recipe_name
        FROM recipe_ingredients ri
        LEFT JOIN common_products cp ON cp.id = ri.common_product_id
        LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
        WHERE ri.recipe_id = %s
    """, (recipe_id,))

    ingredients = dicts_from_rows(cursor.fetchall())

    # Track allergens across all ingredients
    all_allergens = set()
    all_vegan = True
    all_vegetarian = True
    by_ingredient = []
    has_ingredients = False

    for ing in ingredients:
        has_ingredients = True
        ing_allergens = []
        ing_vegan = False
        ing_vegetarian = False

        if ing.get('common_product_id'):
            # Check allergens from common product
            for field in ALLERGEN_FIELDS:
                if field in ['allergen_vegan', 'allergen_vegetarian']:
                    continue  # Handle dietary flags separately
                if ing.get(field):
                    allergen_name = field.replace('allergen_', '').replace('_', ' ').title()
                    ing_allergens.append(allergen_name)
                    all_allergens.add(allergen_name)

            ing_vegan = bool(ing.get('allergen_vegan'))
            ing_vegetarian = bool(ing.get('allergen_vegetarian'))

            if not ing_vegan:
                all_vegan = False
            if not ing_vegetarian:
                all_vegetarian = False

            by_ingredient.append({
                "ingredient_id": ing['id'],
                "name": ing['common_name'],
                "allergens": ing_allergens,
                "vegan": ing_vegan,
                "vegetarian": ing_vegetarian
            })

        elif ing.get('sub_recipe_id'):
            # Recursively get allergens from sub-recipe
            sub_allergens = _calculate_recipe_allergens(cursor, ing['sub_recipe_id'], visited.copy())

            all_allergens.update(sub_allergens.get('contains', []))
            if not sub_allergens.get('vegan', False):
                all_vegan = False
            if not sub_allergens.get('vegetarian', False):
                all_vegetarian = False

            by_ingredient.append({
                "ingredient_id": ing['id'],
                "name": ing['sub_recipe_name'],
                "is_sub_recipe": True,
                "allergens": sub_allergens.get('contains', []),
                "vegan": sub_allergens.get('vegan', False),
                "vegetarian": sub_allergens.get('vegetarian', False)
            })

    # If no ingredients, dietary status is unknown
    if not has_ingredients:
        all_vegan = False
        all_vegetarian = False

    return {
        "contains": sorted(list(all_allergens)),
        "vegan": all_vegan,
        "vegetarian": all_vegetarian,
        "by_ingredient": by_ingredient
    }


@router.post("/{recipe_id}/duplicate", response_model=Recipe)
def duplicate_recipe(recipe_id: int, new_name: Optional[str] = None):
    """
    Duplicate a recipe with all ingredients.

    TODO Phase 2: Implement recipe duplication
    """
    # Placeholder - will implement in Phase 2
    raise HTTPException(status_code=501, detail="Recipe duplication not yet implemented")


# Recipe Ingredients endpoints
@router.post("/{recipe_id}/ingredients")
def add_ingredient(recipe_id: int, ingredient: dict, current_user: dict = Depends(get_current_user)):
    """
    Add an ingredient to a recipe.

    Must have either common_product_id OR sub_recipe_id (not both).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify recipe exists and user has access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        check_query = f"SELECT id FROM recipes WHERE id = %s AND {outlet_filter}"
        check_params = [recipe_id] + outlet_params
        cursor.execute(check_query, check_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        # Validate: must have one of common_product_id, sub_recipe_id, or ingredient_name
        common_product_id = ingredient.get('common_product_id')
        sub_recipe_id = ingredient.get('sub_recipe_id')
        ingredient_name = ingredient.get('ingredient_name')

        # Cannot have both product and sub-recipe
        if common_product_id and sub_recipe_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot specify both common_product_id and sub_recipe_id"
            )

        # Must have at least ONE identifier
        if not common_product_id and not sub_recipe_id and not ingredient_name:
            raise HTTPException(
                status_code=400,
                detail="Must specify either common_product_id, sub_recipe_id, or ingredient_name"
            )

        # Insert ingredient
        cursor.execute("""
            INSERT INTO recipe_ingredients (
                recipe_id, common_product_id, sub_recipe_id, ingredient_name,
                quantity, unit_id, yield_percentage, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            recipe_id,
            common_product_id,
            sub_recipe_id,
            ingredient_name,
            ingredient.get('quantity'),
            ingredient.get('unit_id'),
            ingredient.get('yield_percentage', 100),
            ingredient.get('notes')
        ))

        ingredient_id = cursor.fetchone()["id"]

        # Update parent recipe's updated_at to trigger cost recalculation
        cursor.execute("""
            UPDATE recipes
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (recipe_id,))

        conn.commit()

        # Return the created ingredient with details
        cursor.execute("""
            SELECT ri.*,
                   ri.ingredient_name,
                   cp.common_name,
                   u.abbreviation as unit_abbreviation,
                   r.name as sub_recipe_name
            FROM recipe_ingredients ri
            LEFT JOIN common_products cp ON cp.id = ri.common_product_id
            LEFT JOIN units u ON u.id = ri.unit_id
            LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
            WHERE ri.id = %s
        """, (ingredient_id,))

        return dict_from_row(cursor.fetchone())


@router.patch("/{recipe_id}/ingredients/{ingredient_id}")
def update_ingredient(recipe_id: int, ingredient_id: int, updates: dict, current_user: dict = Depends(get_current_user)):
    """
    Update an ingredient in a recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify recipe exists and user has access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        check_query = f"SELECT id FROM recipes WHERE id = %s AND {outlet_filter}"
        check_params = [recipe_id] + outlet_params
        cursor.execute(check_query, check_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        # Verify ingredient exists and belongs to recipe
        cursor.execute("""
            SELECT id FROM recipe_ingredients
            WHERE id = %s AND recipe_id = %s
        """, (ingredient_id, recipe_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Ingredient not found")

        # Build update query
        allowed_fields = ['quantity', 'unit_id', 'yield_percentage', 'notes', 'common_product_id', 'ingredient_name']
        update_fields = []
        params = []

        # Validate mutual exclusivity of product mapping and text name
        if 'common_product_id' in updates and 'ingredient_name' in updates:
            if updates.get('common_product_id') and updates.get('ingredient_name'):
                raise HTTPException(
                    status_code=400,
                    detail="Cannot specify both common_product_id and ingredient_name"
                )

        # Determine which fields to auto-clear (to avoid duplicate field errors)
        auto_clear_ingredient_name = 'common_product_id' in updates and updates.get('common_product_id') is not None
        auto_clear_common_product_id = 'ingredient_name' in updates and updates.get('ingredient_name') is not None

        for field, value in updates.items():
            if field in allowed_fields:
                # Skip if we're going to auto-clear this field
                if field == 'ingredient_name' and auto_clear_ingredient_name:
                    continue
                if field == 'common_product_id' and auto_clear_common_product_id:
                    continue
                update_fields.append(f"{field} = %s")
                params.append(value)

        # Auto-clear opposite field when mapping changes
        if auto_clear_ingredient_name:
            # When mapping to product, clear text name
            update_fields.append("ingredient_name = NULL")
        if auto_clear_common_product_id:
            # When setting text name, clear product mapping
            update_fields.append("common_product_id = NULL")

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(ingredient_id)
        query = f"UPDATE recipe_ingredients SET {', '.join(update_fields)} WHERE id = %s"

        cursor.execute(query, params)

        # Update parent recipe's updated_at to trigger cost recalculation
        cursor.execute("""
            UPDATE recipes
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (recipe_id,))

        conn.commit()

        # Return updated ingredient with details
        cursor.execute("""
            SELECT ri.*,
                   cp.common_name,
                   u.abbreviation as unit_abbreviation,
                   r.name as sub_recipe_name
            FROM recipe_ingredients ri
            LEFT JOIN common_products cp ON cp.id = ri.common_product_id
            LEFT JOIN units u ON u.id = ri.unit_id
            LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
            WHERE ri.id = %s
        """, (ingredient_id,))

        return dict_from_row(cursor.fetchone())


@router.delete("/{recipe_id}/ingredients/{ingredient_id}")
def remove_ingredient(recipe_id: int, ingredient_id: int, current_user: dict = Depends(get_current_user)):
    """
    Remove an ingredient from a recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify recipe exists and user has access
        outlet_filter, outlet_params = build_outlet_filter(current_user, "")
        check_query = f"SELECT id FROM recipes WHERE id = %s AND {outlet_filter}"
        check_params = [recipe_id] + outlet_params
        cursor.execute(check_query, check_params)

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found or you don't have access to it")

        cursor.execute("""
            DELETE FROM recipe_ingredients
            WHERE id = %s AND recipe_id = %s
        """, (ingredient_id, recipe_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        # Update parent recipe's updated_at to trigger cost recalculation
        cursor.execute("""
            UPDATE recipes
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (recipe_id,))

        conn.commit()

        return {"message": "Ingredient removed successfully", "ingredient_id": ingredient_id}
