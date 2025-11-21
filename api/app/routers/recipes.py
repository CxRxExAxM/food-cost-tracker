from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Recipe, RecipeCreate, RecipeWithIngredients, RecipeWithCost
import json

router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("", response_model=list[Recipe])
def list_recipes(
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    search: Optional[str] = None,
    category_path: Optional[str] = None
):
    """
    List recipes with optional filtering.

    TODO Phase 1: Implement basic listing
    TODO Phase 2: Add category_path filtering for tree structure
    TODO Phase 3: Add search across name, ingredients
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM recipes WHERE is_active = 1"
        params = []

        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")

        if category_path:
            query += " AND category_path LIKE ?"
            params.append(f"{category_path}%")

        query += " ORDER BY category_path, name LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        cursor.execute(query, params)
        recipes = dicts_from_rows(cursor.fetchall())

        # Parse method JSON if present
        for recipe in recipes:
            if recipe.get('method'):
                recipe['method'] = json.loads(recipe['method'])

        return recipes


@router.get("/{recipe_id}", response_model=RecipeWithIngredients)
def get_recipe(recipe_id: int):
    """
    Get a single recipe with ingredients.

    TODO Phase 1: Basic recipe retrieval
    TODO Phase 2: Include ingredients with details
    TODO Phase 3: Include sub-recipe expansion
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get recipe
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
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
            WHERE ri.recipe_id = ?
        """, (recipe_id,))

        recipe['ingredients'] = dicts_from_rows(cursor.fetchall())

        return recipe


@router.post("", response_model=Recipe, status_code=201)
def create_recipe(recipe: RecipeCreate):
    """
    Create a new recipe.

    TODO Phase 1: Implement basic creation
    TODO Phase 2: Handle ingredients creation
    TODO Phase 3: Validate sub-recipe references
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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

        recipe_id = cursor.lastrowid

        # Insert ingredients (TODO: implement in Phase 2)
        for ingredient in recipe.ingredients:
            cursor.execute("""
                INSERT INTO recipe_ingredients (
                    recipe_id, common_product_id, sub_recipe_id,
                    quantity, unit_id, yield_percentage, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
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
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        created_recipe = dict_from_row(cursor.fetchone())

        if created_recipe.get('method'):
            created_recipe['method'] = json.loads(created_recipe['method'])

        return created_recipe


@router.patch("/{recipe_id}", response_model=Recipe)
def update_recipe(recipe_id: int, updates: dict):
    """
    Update a recipe.

    TODO Phase 1: Implement basic updates
    TODO Phase 2: Handle ingredient updates
    TODO Phase 3: Validate changes
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if recipe exists
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
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
                update_fields.append(f"{field} = ?")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(recipe_id)
        query = f"UPDATE recipes SET {', '.join(update_fields)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()

        # Fetch updated recipe
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        updated_recipe = dict_from_row(cursor.fetchone())

        if updated_recipe.get('method'):
            updated_recipe['method'] = json.loads(updated_recipe['method'])

        return updated_recipe


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int):
    """
    Delete a recipe (soft delete).

    TODO Phase 1: Implement soft delete
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("UPDATE recipes SET is_active = 0 WHERE id = ?", (recipe_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Recipe not found")

        conn.commit()

        return {"message": "Recipe deleted successfully", "recipe_id": recipe_id}


@router.get("/{recipe_id}/cost", response_model=RecipeWithCost)
def calculate_recipe_cost(recipe_id: int):
    """
    Calculate total cost of a recipe with breakdown.

    TODO Phase 3: Implement cost calculation
    - Get latest prices for all ingredients
    - Handle sub-recipes recursively
    - Calculate cost per serving
    - Return breakdown by ingredient
    """
    # Placeholder - will implement in Phase 3
    raise HTTPException(status_code=501, detail="Cost calculation not yet implemented")


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
        cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            recipe_id,
            common_product_id,
            sub_recipe_id,
            ingredient.get('quantity'),
            ingredient.get('unit_id'),
            ingredient.get('yield_percentage', 100),
            ingredient.get('notes')
        ))

        ingredient_id = cursor.lastrowid
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
            WHERE ri.id = ?
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
            WHERE id = ? AND recipe_id = ?
        """, (ingredient_id, recipe_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Ingredient not found")

        # Build update query
        allowed_fields = ['quantity', 'unit_id', 'yield_percentage', 'notes']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(ingredient_id)
        query = f"UPDATE recipe_ingredients SET {', '.join(update_fields)} WHERE id = ?"

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
            WHERE ri.id = ?
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
            WHERE id = ? AND recipe_id = ?
        """, (ingredient_id, recipe_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ingredient not found")

        conn.commit()

        return {"message": "Ingredient removed successfully", "ingredient_id": ingredient_id}
