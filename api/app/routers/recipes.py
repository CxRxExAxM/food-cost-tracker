from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Recipe, RecipeCreate, RecipeWithIngredients, RecipeWithCost
from ..auth import get_current_user
import json

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[Recipe])
def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    search: Optional[str] = None,
    category_path: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List recipes with optional filtering .
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM recipes WHERE is_active = 1"
        params = []

        if search:
            query += " AND name LIKE %s"
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
    with get_db() as conn:
        cursor = conn.cursor()

        # Get recipe - verify it belongs to user's organization
        cursor.execute(
            "SELECT * FROM recipes WHERE id = %s",
            (recipe_id)
        )
        recipe = dict_from_row(cursor.fetchone())

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Parse method JSON
        if recipe.get('method'):
            recipe['method'] = json.loads(recipe['method'])

        # Get ingredients (TODO: expand with product/sub-recipe details)
        cursor.execute("""
            SELECT ri.*,
                   cp.common_name,
                   u.abbreviation as unit_abbreviation,
                   r.name as sub_recipe_name
            FROM recipe_ingredients ri
            LEFT JOIN common_products cp ON cp.id = ri.common_product_id
            LEFT JOIN units u ON u.id = ri.unit_id
            LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
            WHERE ri.recipe_id = %s
        """, (recipe_id,))

        recipe['ingredients'] = dicts_from_rows(cursor.fetchall())

        return recipe


@router.post("", response_model=Recipe, status_code=201)
def create_recipe(recipe: RecipeCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Serialize method to JSON
        method_json = json.dumps([step.dict() for step in recipe.method]) if recipe.method else None

        cursor.execute("""
            INSERT INTO recipes (
                name, description, category, category_path,
                yield_amount, yield_unit_id, prep_time_minutes, cook_time_minutes,
                method
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            method_json
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

        # Check if recipe exists and belongs to user's organization
        cursor.execute("SELECT id FROM recipes WHERE id = %s", (recipe_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Build update query
        allowed_fields = [
            'name', 'description', 'category', 'category_path',
            'yield_amount', 'yield_unit_id', 'prep_time_minutes',
            'cook_time_minutes', 'method', 'notes'
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

        cursor.execute("UPDATE recipes SET is_active = 0 WHERE id = %s", (recipe_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe not found")

        conn.commit()

        return {"message": "Recipe deleted successfully", "recipe_id": recipe_id}


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

        # Get recipe with yield and serving unit info
        cursor.execute("""
            SELECT r.*,
                   yu.abbreviation as yield_unit_abbreviation,
                   su.abbreviation as serving_unit_abbreviation
            FROM recipes r
            LEFT JOIN units yu ON yu.id = r.yield_unit_id
            LEFT JOIN units su ON su.id = r.serving_unit_id
            WHERE r.id = %s
        """, (recipe_id,))
        recipe = dict_from_row(cursor.fetchone())

        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Parse method JSON
        if recipe.get('method'):
            recipe['method'] = json.loads(recipe['method'])

        # Calculate costs recursively
        ingredients_with_costs, total_cost = _calculate_ingredient_costs(
            cursor, recipe_id, visited=set()
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


def _calculate_ingredient_costs(cursor, recipe_id: int, visited: set) -> tuple[list[dict], float]:
    """
    Recursively calculate costs for all ingredients in a recipe.

    Args:
        cursor: Database cursor
        recipe_id: Recipe ID to calculate
        visited: Set of recipe IDs already visited (prevents infinite recursion)

    Returns:
        Tuple of (ingredients_with_costs, total_cost)
    """
    # Prevent infinite recursion from circular sub-recipe references
    if recipe_id in visited:
        return [], 0.0
    visited.add(recipe_id)

    # Get all ingredients for this recipe
    cursor.execute("""
        SELECT ri.*,
               cp.common_name,
               u.abbreviation as unit_abbreviation,
               r.name as sub_recipe_name,
               r.yield_amount as sub_recipe_yield
        FROM recipe_ingredients ri
        LEFT JOIN common_products cp ON cp.id = ri.common_product_id
        LEFT JOIN units u ON u.id = ri.unit_id
        LEFT JOIN recipes r ON r.id = ri.sub_recipe_id
        WHERE ri.recipe_id = %s
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
            # Get lowest unit price for this common product
            cursor.execute("""
                SELECT
                    ph.unit_price,
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
                WHERE p.common_product_id = %s AND ph.unit_price IS NOT NULL
                ORDER BY ph.unit_price ASC
                LIMIT 1
            """, (ing['common_product_id'],))

            price_row = dict_from_row(cursor.fetchone())

            if price_row and price_row.get('unit_price'):
                unit_price = price_row['unit_price']
                has_price = True
                price_source = f"{price_row['distributor_name']}: {price_row['product_name']}"

                # Calculate ingredient cost: quantity * unit_price * (yield_percentage / 100)
                yield_pct = ing.get('yield_percentage', 100) or 100
                ing_cost = ing['quantity'] * unit_price * (100 / yield_pct)
                total_cost += ing_cost

        elif ing.get('sub_recipe_id'):
            # Recursively calculate sub-recipe cost
            _, sub_recipe_total = _calculate_ingredient_costs(
                cursor, ing['sub_recipe_id'], visited.copy()
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
        SELECT ri.id, ri.common_product_id, ri.sub_recipe_id,
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
def add_ingredient(recipe_id: int, ingredient: dict):
    """
    Add an ingredient to a recipe.

    Must have either common_product_id OR sub_recipe_id (not both).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify recipe exists
        cursor.execute("SELECT id FROM recipes WHERE id = %s", (recipe_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Validate: must have exactly one of common_product_id or sub_recipe_id
        common_product_id = ingredient.get('common_product_id')
        sub_recipe_id = ingredient.get('sub_recipe_id')

        if not common_product_id and not sub_recipe_id:
            raise HTTPException(status_code=400, detail="Must specify either common_product_id or sub_recipe_id")

        if common_product_id and sub_recipe_id:
            raise HTTPException(status_code=400, detail="Cannot specify both common_product_id and sub_recipe_id")

        # Insert ingredient
        cursor.execute("""
            INSERT INTO recipe_ingredients (
                recipe_id, common_product_id, sub_recipe_id,
                quantity, unit_id, yield_percentage, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            recipe_id,
            common_product_id,
            sub_recipe_id,
            ingredient.get('quantity'),
            ingredient.get('unit_id'),
            ingredient.get('yield_percentage', 100),
            ingredient.get('notes')
        ))

        ingredient_id = cursor.fetchone()["id"]
        conn.commit()

        # Return the created ingredient with details
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


@router.patch("/{recipe_id}/ingredients/{ingredient_id}")
def update_ingredient(recipe_id: int, ingredient_id: int, updates: dict):
    """
    Update an ingredient in a recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify ingredient exists and belongs to recipe
        cursor.execute("""
            SELECT id FROM recipe_ingredients
            WHERE id = %s AND recipe_id = %s
        """, (ingredient_id, recipe_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Ingredient not found")

        # Build update query
        allowed_fields = ['quantity', 'unit_id', 'yield_percentage', 'notes']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(ingredient_id)
        query = f"UPDATE recipe_ingredients SET {', '.join(update_fields)} WHERE id = %s"

        cursor.execute(query, params)
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
def remove_ingredient(recipe_id: int, ingredient_id: int):
    """
    Remove an ingredient from a recipe.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM recipe_ingredients
            WHERE id = %s AND recipe_id = %s
        """, (ingredient_id, recipe_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        conn.commit()

        return {"message": "Ingredient removed successfully", "ingredient_id": ingredient_id}
