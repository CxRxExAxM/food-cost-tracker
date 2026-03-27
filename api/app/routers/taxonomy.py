"""
Ingredient Taxonomy API endpoints.

Provides CRUD operations for:
- Base ingredients (core concepts like Carrot, Chicken, Tomato)
- Ingredient variants (specific forms like Diced Carrot, Chicken Breast Boneless)
- Variant merge functionality to consolidate duplicates
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
import re
import sys
import os

from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import (
    BaseIngredient, BaseIngredientCreate, BaseIngredientUpdate,
    IngredientVariant, IngredientVariantCreate, IngredientVariantUpdate,
    BaseIngredientWithVariants, VariantMergeRequest, VariantMergeResponse
)
from ..auth import get_current_user
from ..audit import log_audit
from ..config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT_LARGE
from ..logger import get_logger

# Add scripts directory to path for parser import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))
try:
    from taxonomy_parser import extract_base_and_attributes, build_display_name
except ImportError:
    # Fallback: define minimal parser inline if import fails
    def extract_base_and_attributes(common_name: str, category: str = None) -> dict:
        """Minimal fallback parser."""
        result = {
            "base_name": None, "variety": None, "form": None, "prep": None,
            "cut_size": None, "cut": None, "bone": None, "skin": None,
            "grade": None, "state": None,
        }
        if "," in common_name:
            parts = common_name.split(",", 1)
            result["base_name"] = parts[0].strip().title()
        else:
            result["base_name"] = common_name.strip().title()
        return result

    def build_display_name(base_name: str, attrs: dict) -> str:
        parts = [base_name]
        for key in ["variety", "form", "cut", "bone", "skin", "prep", "cut_size", "grade", "state"]:
            if attrs.get(key):
                parts.append(attrs[key])
        return ", ".join(parts)

logger = get_logger(__name__)

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


# =============================================================================
# Request/Response Models for Common Product Updates
# =============================================================================

class CommonProductUpdateRequest(BaseModel):
    common_name: str


class CommonProductReparseResponse(BaseModel):
    id: int
    common_name: str
    variant_id: Optional[int]
    variant_display_name: Optional[str]
    detected_attributes: dict
    moved: bool
    message: str


# =============================================================================
# Base Ingredients
# =============================================================================

@router.get("/base-ingredients", response_model=List[BaseIngredient])
def list_base_ingredients(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT_LARGE),
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List base ingredients with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM base_ingredients WHERE is_active = 1"
        params = []

        if search:
            query += " AND LOWER(name) LIKE LOWER(%s)"
            params.append(f"%{search}%")

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY name LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cursor.execute(query, params)
        return dicts_from_rows(cursor.fetchall())


@router.get("/base-ingredients/categories")
def get_base_ingredient_categories(current_user: dict = Depends(get_current_user)):
    """Get distinct categories for base ingredients."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT category
            FROM base_ingredients
            WHERE is_active = 1 AND category IS NOT NULL
            ORDER BY category
        """)
        return [row["category"] for row in cursor.fetchall()]


@router.get("/base-ingredients/with-variants")
def list_base_ingredients_with_variants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    category: Optional[str] = None,
    include_counts: bool = Query(True, description="Include recipe/product counts"),
    current_user: dict = Depends(get_current_user)
):
    """List base ingredients with their variants (tree view) including usage counts."""
    org_id = current_user["organization_id"]

    with get_db() as conn:
        cursor = conn.cursor()

        # First get base ingredients
        query = "SELECT * FROM base_ingredients WHERE is_active = 1"
        params = []

        if search:
            # Search in both base name and variant display names
            query += """ AND (LOWER(name) LIKE LOWER(%s)
                OR id IN (SELECT base_ingredient_id FROM ingredient_variants
                          WHERE LOWER(display_name) LIKE LOWER(%s) AND is_active = 1))"""
            params.extend([f"%{search}%", f"%{search}%"])

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY name LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cursor.execute(query, params)
        bases = dicts_from_rows(cursor.fetchall())

        if not bases:
            return []

        # Get variants for these base ingredients with counts
        base_ids = [b["id"] for b in bases]

        if include_counts:
            # Get variants with linked common_products count and recipe usage
            cursor.execute("""
                SELECT
                    v.*,
                    COALESCE(cp_counts.common_product_count, 0) as common_product_count,
                    COALESCE(cp_counts.linked_product_count, 0) as linked_product_count,
                    COALESCE(recipe_counts.recipe_count, 0) as recipe_count
                FROM ingredient_variants v
                LEFT JOIN (
                    SELECT
                        variant_id,
                        COUNT(*) as common_product_count,
                        SUM(COALESCE(linked_count, 0)) as linked_product_count
                    FROM common_products cp
                    LEFT JOIN (
                        SELECT common_product_id, COUNT(*) as linked_count
                        FROM products
                        WHERE organization_id = %s AND is_active = 1
                        GROUP BY common_product_id
                    ) p ON p.common_product_id = cp.id
                    WHERE cp.variant_id IS NOT NULL AND cp.is_active = 1
                    GROUP BY variant_id
                ) cp_counts ON cp_counts.variant_id = v.id
                LEFT JOIN (
                    SELECT
                        cp.variant_id,
                        COUNT(DISTINCT ri.recipe_id) as recipe_count
                    FROM recipe_ingredients ri
                    JOIN common_products cp ON cp.id = ri.common_product_id
                    JOIN recipes r ON r.id = ri.recipe_id
                    WHERE cp.variant_id IS NOT NULL
                      AND r.organization_id = %s
                      AND r.is_active = 1
                    GROUP BY cp.variant_id
                ) recipe_counts ON recipe_counts.variant_id = v.id
                WHERE v.base_ingredient_id = ANY(%s) AND v.is_active = 1
                ORDER BY v.display_name
            """, (org_id, org_id, base_ids))
        else:
            cursor.execute("""
                SELECT * FROM ingredient_variants
                WHERE base_ingredient_id = ANY(%s) AND is_active = 1
                ORDER BY display_name
            """, (base_ids,))

        variants = dicts_from_rows(cursor.fetchall())

        # Build hierarchical tree structure for variants
        def build_variant_tree(variants_list):
            """Build a tree of variants where children are nested under parents."""
            # Index variants by id for quick lookup
            variants_by_id = {v["id"]: v for v in variants_list}

            # Initialize children arrays
            for v in variants_list:
                v["children"] = []

            # Build tree - attach children to parents
            root_variants = []
            for v in variants_list:
                parent_id = v.get("parent_variant_id")
                if parent_id and parent_id in variants_by_id:
                    variants_by_id[parent_id]["children"].append(v)
                else:
                    root_variants.append(v)

            return root_variants

        # Group variants by base ingredient first
        variants_by_base = {}
        for v in variants:
            base_id = v["base_ingredient_id"]
            if base_id not in variants_by_base:
                variants_by_base[base_id] = []
            variants_by_base[base_id].append(v)

        # Build tree for each base's variants and attach
        for base in bases:
            base_variants = variants_by_base.get(base["id"], [])
            base["variants"] = build_variant_tree(base_variants)

        return bases


@router.get("/base-ingredients/{base_id}", response_model=BaseIngredient)
def get_base_ingredient(base_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single base ingredient by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM base_ingredients WHERE id = %s", (base_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Base ingredient not found")
        return dict_from_row(row)


@router.post("/base-ingredients", response_model=BaseIngredient, status_code=201)
def create_base_ingredient(
    data: BaseIngredientCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new base ingredient."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check for duplicate name
        cursor.execute(
            "SELECT id FROM base_ingredients WHERE LOWER(name) = LOWER(%s)",
            (data.name,)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Base ingredient with this name already exists")

        cursor.execute("""
            INSERT INTO base_ingredients (
                name, category, subcategory, default_unit_id,
                allergen_vegan, allergen_vegetarian, allergen_gluten,
                allergen_crustation, allergen_egg, allergen_mollusk,
                allergen_fish, allergen_lupin, allergen_dairy,
                allergen_tree_nuts, allergen_peanuts, allergen_sesame,
                allergen_soy, allergen_sulphur_dioxide, allergen_mustard,
                allergen_celery
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            data.name, data.category, data.subcategory, data.default_unit_id,
            int(data.allergen_vegan), int(data.allergen_vegetarian), int(data.allergen_gluten),
            int(data.allergen_crustation), int(data.allergen_egg), int(data.allergen_mollusk),
            int(data.allergen_fish), int(data.allergen_lupin), int(data.allergen_dairy),
            int(data.allergen_tree_nuts), int(data.allergen_peanuts), int(data.allergen_sesame),
            int(data.allergen_soy), int(data.allergen_sulphur_dioxide), int(data.allergen_mustard),
            int(data.allergen_celery)
        ))
        row = cursor.fetchone()
        conn.commit()

        log_audit(cursor, "base_ingredient_created", "base_ingredient", row["id"],
                  current_user["id"], current_user["organization_id"],
                  {"name": data.name})
        conn.commit()

        logger.info(f"Created base ingredient: {data.name} (id={row['id']})")
        return dict_from_row(row)


@router.patch("/base-ingredients/{base_id}", response_model=BaseIngredient)
def update_base_ingredient(
    base_id: int,
    data: BaseIngredientUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a base ingredient."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check exists
        cursor.execute("SELECT * FROM base_ingredients WHERE id = %s", (base_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Base ingredient not found")

        # Build update query dynamically
        updates = []
        params = []
        for field, value in data.model_dump(exclude_unset=True).items():
            if field.startswith("allergen_") and value is not None:
                value = int(value)
            elif field == "is_active" and value is not None:
                value = int(value)
            updates.append(f"{field} = %s")
            params.append(value)

        if not updates:
            return dict_from_row(existing)

        params.append(base_id)
        cursor.execute(
            f"UPDATE base_ingredients SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s RETURNING *",
            params
        )
        row = cursor.fetchone()
        conn.commit()

        log_audit(cursor, "base_ingredient_updated", "base_ingredient", base_id,
                  current_user["id"], current_user["organization_id"],
                  data.model_dump(exclude_unset=True))
        conn.commit()

        return dict_from_row(row)


# =============================================================================
# Ingredient Variants
# =============================================================================

@router.get("/variants", response_model=List[IngredientVariant])
def list_variants(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT_LARGE),
    base_ingredient_id: Optional[int] = None,
    search: Optional[str] = None,
    variety: Optional[str] = None,
    form: Optional[str] = None,
    prep: Optional[str] = None,
    state: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List ingredient variants with optional attribute filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM ingredient_variants WHERE is_active = 1"
        params = []

        if base_ingredient_id:
            query += " AND base_ingredient_id = %s"
            params.append(base_ingredient_id)

        if search:
            query += " AND LOWER(display_name) LIKE LOWER(%s)"
            params.append(f"%{search}%")

        if variety:
            query += " AND variety = %s"
            params.append(variety)

        if form:
            query += " AND form = %s"
            params.append(form)

        if prep:
            query += " AND prep = %s"
            params.append(prep)

        if state:
            query += " AND state = %s"
            params.append(state)

        query += " ORDER BY display_name LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cursor.execute(query, params)
        return dicts_from_rows(cursor.fetchall())


@router.get("/variants/attribute-values")
def get_variant_attribute_values(current_user: dict = Depends(get_current_user)):
    """Get distinct values for each variant attribute (for filter dropdowns)."""
    with get_db() as conn:
        cursor = conn.cursor()

        attributes = {}
        for attr in ["variety", "form", "prep", "cut_size", "cut", "bone", "skin", "grade", "state"]:
            cursor.execute(f"""
                SELECT DISTINCT {attr}
                FROM ingredient_variants
                WHERE is_active = 1 AND {attr} IS NOT NULL
                ORDER BY {attr}
            """)
            attributes[attr] = [row[attr] for row in cursor.fetchall()]

        return attributes


@router.get("/variants/{variant_id}/common-products")
def get_variant_common_products(
    variant_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get common products linked to a variant, along with their vendor SKUs.
    Returns the third level of the taxonomy tree: Common Products → Linked SKUs.
    """
    org_id = current_user["organization_id"]

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Verify variant exists
            logger.info(f"[common-products] Fetching for variant_id={variant_id}, org_id={org_id}")
            cursor.execute("SELECT id FROM ingredient_variants WHERE id = %s", (variant_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Variant not found")

            # Get common products with their linked vendor products
            logger.info(f"[common-products] Fetching common_products for variant_id={variant_id}")
            cursor.execute("""
                SELECT
                    cp.id,
                    cp.common_name,
                    cp.notes,
                    cp.category,
                    cp.preferred_unit_id,
                    u.name as unit_name,
                    cp.created_at,
                    cp.updated_at
                FROM common_products cp
                LEFT JOIN units u ON u.id = cp.preferred_unit_id
                WHERE cp.variant_id = %s AND cp.is_active = 1
                ORDER BY cp.common_name
            """, (variant_id,))
            common_products = dicts_from_rows(cursor.fetchall())
            logger.info(f"[common-products] Found {len(common_products)} common products")

            if not common_products:
                return []

            cp_ids = [cp["id"] for cp in common_products]
            logger.info(f"[common-products] Looking up linked products for cp_ids={cp_ids}")

            # Get linked vendor products for these common products
            # Schema: products -> distributor_products (has org_id) -> distributors + price_history
            cursor.execute("""
                SELECT
                    p.id,
                    p.common_product_id,
                    p.name as product_name,
                    p.description,
                    p.pack,
                    p.size,
                    p.unit_id,
                    u.name as unit_name,
                    dp.id as distributor_product_id,
                    dp.distributor_sku,
                    d.id as distributor_id,
                    d.name as distributor_name,
                    ph.unit_price as latest_price
                FROM products p
                JOIN distributor_products dp ON dp.product_id = p.id
                JOIN distributors d ON d.id = dp.distributor_id
                LEFT JOIN units u ON u.id = p.unit_id
                LEFT JOIN LATERAL (
                    SELECT unit_price
                    FROM price_history
                    WHERE distributor_product_id = dp.id
                    ORDER BY effective_date DESC
                    LIMIT 1
                ) ph ON true
                WHERE p.common_product_id = ANY(%s)
                  AND dp.organization_id = %s
                  AND p.is_active = 1
                  AND COALESCE(dp.is_available, 1) = 1
                ORDER BY d.name, p.name
            """, (cp_ids, org_id))
            products = dicts_from_rows(cursor.fetchall())
            logger.info(f"[common-products] Found {len(products)} linked products")

            # Group products by common_product_id
            products_by_cp = {}
            for p in products:
                cp_id = p["common_product_id"]
                if cp_id not in products_by_cp:
                    products_by_cp[cp_id] = []
                products_by_cp[cp_id].append(p)

            # Attach linked products to common products
            for cp in common_products:
                cp["linked_products"] = products_by_cp.get(cp["id"], [])
                cp["linked_count"] = len(cp["linked_products"])

            logger.info(f"[common-products] Successfully returning {len(common_products)} common products")
            return common_products

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[common-products] Error fetching common products for variant_id={variant_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching common products: {str(e)}")


@router.get("/variants/{variant_id}/similar")
def find_similar_variants(
    variant_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Find variants similar to the given variant (for duplicate detection)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get the target variant
        cursor.execute("SELECT * FROM ingredient_variants WHERE id = %s", (variant_id,))
        target = cursor.fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Variant not found")

        # Find similar variants (same base, matching attributes)
        cursor.execute("""
            SELECT v.*, bi.name as base_name,
                   (CASE WHEN v.variety = %s THEN 1 ELSE 0 END +
                    CASE WHEN v.form = %s THEN 1 ELSE 0 END +
                    CASE WHEN v.prep = %s THEN 1 ELSE 0 END +
                    CASE WHEN v.state = %s THEN 1 ELSE 0 END) as match_score
            FROM ingredient_variants v
            JOIN base_ingredients bi ON v.base_ingredient_id = bi.id
            WHERE v.base_ingredient_id = %s
              AND v.id != %s
              AND v.is_active = 1
            ORDER BY match_score DESC
            LIMIT 10
        """, (
            target["variety"], target["form"], target["prep"], target["state"],
            target["base_ingredient_id"], variant_id
        ))

        return dicts_from_rows(cursor.fetchall())


# NOTE: This route must come AFTER more specific routes like /common-products and /similar
# because FastAPI matches routes in order and {variant_id} would match "common-products" as a string
@router.get("/variants/{variant_id}", response_model=IngredientVariant)
def get_variant(variant_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single variant by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ingredient_variants WHERE id = %s", (variant_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Variant not found")
        return dict_from_row(row)


@router.post("/variants", response_model=IngredientVariant, status_code=201)
def create_variant(
    data: IngredientVariantCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new ingredient variant."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check base ingredient exists
        cursor.execute("SELECT id FROM base_ingredients WHERE id = %s", (data.base_ingredient_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Base ingredient not found")

        cursor.execute("""
            INSERT INTO ingredient_variants (
                base_ingredient_id, display_name,
                variety, form, prep, cut_size,
                cut, bone, skin, grade, state
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            data.base_ingredient_id, data.display_name,
            data.variety, data.form, data.prep, data.cut_size,
            data.cut, data.bone, data.skin, data.grade, data.state
        ))
        row = cursor.fetchone()
        conn.commit()

        log_audit(cursor, "variant_created", "ingredient_variant", row["id"],
                  current_user["id"], current_user["organization_id"],
                  {"display_name": data.display_name, "base_ingredient_id": data.base_ingredient_id})
        conn.commit()

        logger.info(f"Created variant: {data.display_name} (id={row['id']})")
        return dict_from_row(row)


@router.patch("/variants/{variant_id}", response_model=IngredientVariant)
def update_variant(
    variant_id: int,
    data: IngredientVariantUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an ingredient variant."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check exists
        cursor.execute("SELECT * FROM ingredient_variants WHERE id = %s", (variant_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Variant not found")

        # Build update query dynamically
        updates = []
        params = []
        for field, value in data.model_dump(exclude_unset=True).items():
            if field == "is_active" and value is not None:
                value = int(value)
            updates.append(f"{field} = %s")
            params.append(value)

        if not updates:
            return dict_from_row(existing)

        params.append(variant_id)
        cursor.execute(
            f"UPDATE ingredient_variants SET {', '.join(updates)}, updated_at = NOW() WHERE id = %s RETURNING *",
            params
        )
        row = cursor.fetchone()
        conn.commit()

        log_audit(cursor, "variant_updated", "ingredient_variant", variant_id,
                  current_user["id"], current_user["organization_id"],
                  data.model_dump(exclude_unset=True))
        conn.commit()

        return dict_from_row(row)


# =============================================================================
# Variant Hierarchy Management
# =============================================================================

class VariantMoveRequest(BaseModel):
    parent_variant_id: Optional[int] = None  # None = move to root level


@router.patch("/variants/{variant_id}/move")
def move_variant(
    variant_id: int,
    data: VariantMoveRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Move a variant to a new parent (or to root level).

    This updates the parent_variant_id and recalculates depth.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get the variant
        cursor.execute("SELECT * FROM ingredient_variants WHERE id = %s", (variant_id,))
        variant = cursor.fetchone()
        if not variant:
            raise HTTPException(status_code=404, detail="Variant not found")

        new_parent_id = data.parent_variant_id
        new_depth = 0

        if new_parent_id:
            # Verify parent exists and is from the same base ingredient
            cursor.execute(
                "SELECT id, base_ingredient_id, depth FROM ingredient_variants WHERE id = %s",
                (new_parent_id,)
            )
            parent = cursor.fetchone()
            if not parent:
                raise HTTPException(status_code=400, detail="Parent variant not found")
            if parent["base_ingredient_id"] != variant["base_ingredient_id"]:
                raise HTTPException(status_code=400, detail="Cannot move to variant from different base ingredient")

            # Prevent circular reference
            if new_parent_id == variant_id:
                raise HTTPException(status_code=400, detail="Variant cannot be its own parent")

            # Check for circular reference in ancestors
            ancestor_id = new_parent_id
            while ancestor_id:
                if ancestor_id == variant_id:
                    raise HTTPException(status_code=400, detail="Circular reference detected")
                cursor.execute(
                    "SELECT parent_variant_id FROM ingredient_variants WHERE id = %s",
                    (ancestor_id,)
                )
                row = cursor.fetchone()
                ancestor_id = row["parent_variant_id"] if row else None

            new_depth = (parent["depth"] or 0) + 1

        # Update the variant
        cursor.execute("""
            UPDATE ingredient_variants
            SET parent_variant_id = %s, depth = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (new_parent_id, new_depth, variant_id))
        updated = cursor.fetchone()

        # Update depths of all descendants
        def update_descendant_depths(parent_id, parent_depth):
            cursor.execute(
                "SELECT id FROM ingredient_variants WHERE parent_variant_id = %s",
                (parent_id,)
            )
            children = cursor.fetchall()
            for child in children:
                child_depth = parent_depth + 1
                cursor.execute(
                    "UPDATE ingredient_variants SET depth = %s WHERE id = %s",
                    (child_depth, child["id"])
                )
                update_descendant_depths(child["id"], child_depth)

        update_descendant_depths(variant_id, new_depth)

        conn.commit()

        log_audit(cursor, "variant_moved", "ingredient_variant", variant_id,
                  current_user["id"], current_user["organization_id"],
                  {"old_parent_id": variant["parent_variant_id"], "new_parent_id": new_parent_id})
        conn.commit()

        return {
            "id": variant_id,
            "parent_variant_id": new_parent_id,
            "depth": new_depth,
            "message": f"Moved to {'root level' if not new_parent_id else f'under variant {new_parent_id}'}"
        }


# =============================================================================
# Common Product Re-parsing
# =============================================================================

@router.patch("/common-products/{cp_id}/reparse", response_model=CommonProductReparseResponse)
def update_and_reparse_common_product(
    cp_id: int,
    data: CommonProductUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a common product's name and re-parse to assign to correct variant.

    This will:
    1. Parse the new name to extract attributes
    2. Find or create a matching variant
    3. Update the common product's name and variant_id
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Get current common product
            cursor.execute("""
                SELECT cp.*, bi.id as current_base_id, bi.name as current_base_name
                FROM common_products cp
                LEFT JOIN ingredient_variants iv ON iv.id = cp.variant_id
                LEFT JOIN base_ingredients bi ON bi.id = iv.base_ingredient_id
                WHERE cp.id = %s
            """, (cp_id,))
            cp = cursor.fetchone()
            if not cp:
                raise HTTPException(status_code=404, detail="Common product not found")

            old_variant_id = cp["variant_id"]

            # Parse the new name
            attrs = extract_base_and_attributes(data.common_name)
            base_name = attrs.pop("base_name")

            logger.info(f"[reparse] Parsing '{data.common_name}' -> base={base_name}, attrs={attrs}")

            # Find or create the base ingredient
            cursor.execute(
                "SELECT id FROM base_ingredients WHERE LOWER(name) = LOWER(%s) AND is_active = 1",
                (base_name,)
            )
            base_row = cursor.fetchone()

            if base_row:
                base_id = base_row["id"]
            else:
                # Create new base ingredient
                cursor.execute("""
                    INSERT INTO base_ingredients (name, is_active)
                    VALUES (%s, 1)
                    RETURNING id
                """, (base_name,))
                base_id = cursor.fetchone()["id"]
                logger.info(f"[reparse] Created new base ingredient: {base_name} (id={base_id})")

            # Build variant display name and find/create matching variant
            display_name = build_display_name(base_name, attrs)

            # Look for existing variant with matching attributes
            attr_conditions = []
            attr_params = [base_id]
            for attr_name in ["variety", "form", "prep", "cut_size", "cut", "bone", "skin", "grade", "state"]:
                val = attrs.get(attr_name)
                if val:
                    attr_conditions.append(f"{attr_name} = %s")
                    attr_params.append(val)
                else:
                    attr_conditions.append(f"{attr_name} IS NULL")

            variant_query = f"""
                SELECT id, display_name FROM ingredient_variants
                WHERE base_ingredient_id = %s AND is_active = 1
                AND {' AND '.join(attr_conditions)}
            """
            cursor.execute(variant_query, attr_params)
            variant_row = cursor.fetchone()

            if variant_row:
                variant_id = variant_row["id"]
                variant_display = variant_row["display_name"]
                logger.info(f"[reparse] Found existing variant: {variant_display} (id={variant_id})")
            else:
                # Create new variant
                cursor.execute("""
                    INSERT INTO ingredient_variants (
                        base_ingredient_id, display_name,
                        variety, form, prep, cut_size, cut, bone, skin, grade, state, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    RETURNING id
                """, (
                    base_id, display_name,
                    attrs.get("variety"), attrs.get("form"), attrs.get("prep"), attrs.get("cut_size"),
                    attrs.get("cut"), attrs.get("bone"), attrs.get("skin"), attrs.get("grade"), attrs.get("state")
                ))
                variant_id = cursor.fetchone()["id"]
                variant_display = display_name
                logger.info(f"[reparse] Created new variant: {display_name} (id={variant_id})")

            # Update the common product
            cursor.execute("""
                UPDATE common_products
                SET common_name = %s, variant_id = %s, base_ingredient_id = %s, updated_at = NOW()
                WHERE id = %s
            """, (data.common_name, variant_id, base_id, cp_id))
            conn.commit()

            moved = old_variant_id != variant_id

            log_audit(cursor, "common_product_reparsed", "common_product", cp_id,
                      current_user["id"], current_user["organization_id"],
                      {"old_variant_id": old_variant_id, "new_variant_id": variant_id, "new_name": data.common_name})
            conn.commit()

            return CommonProductReparseResponse(
                id=cp_id,
                common_name=data.common_name,
                variant_id=variant_id,
                variant_display_name=variant_display,
                detected_attributes=attrs,
                moved=moved,
                message=f"Moved to '{variant_display}'" if moved else "Name updated, variant unchanged"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"[reparse] Error reparsing common product {cp_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reparsing: {str(e)}")


@router.get("/common-products/{cp_id}/detected-attributes")
def get_detected_attributes(
    cp_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the detected attributes for a common product (for tooltip display).
    Shows what the parser extracts from the current name.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cp.common_name, cp.variant_id, iv.display_name as variant_display_name,
                   iv.variety, iv.form, iv.prep, iv.cut_size, iv.cut, iv.bone, iv.skin, iv.grade, iv.state
            FROM common_products cp
            LEFT JOIN ingredient_variants iv ON iv.id = cp.variant_id
            WHERE cp.id = %s
        """, (cp_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Common product not found")

        # Parse the current name to show detected attributes
        detected = extract_base_and_attributes(row["common_name"])

        # Get current variant attributes
        variant_attrs = {
            "variety": row["variety"],
            "form": row["form"],
            "prep": row["prep"],
            "cut_size": row["cut_size"],
            "cut": row["cut"],
            "bone": row["bone"],
            "skin": row["skin"],
            "grade": row["grade"],
            "state": row["state"],
        }

        # Find mismatches (detected but not in variant)
        unassigned = {}
        for key, val in detected.items():
            if key != "base_name" and val and not variant_attrs.get(key):
                unassigned[key] = val

        return {
            "common_name": row["common_name"],
            "variant_display_name": row["variant_display_name"],
            "detected_base": detected.get("base_name"),
            "detected_attributes": {k: v for k, v in detected.items() if k != "base_name" and v},
            "variant_attributes": {k: v for k, v in variant_attrs.items() if v},
            "unassigned_attributes": unassigned
        }


# =============================================================================
# Variant Merge
# =============================================================================

@router.post("/variants/merge", response_model=VariantMergeResponse)
def merge_variants(
    data: VariantMergeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Merge multiple variants into one.

    All products and mappings pointing to the merged variants will be updated
    to point to the kept variant. The merged variants will be soft-deleted.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Validate keep_variant_id exists
        cursor.execute("SELECT * FROM ingredient_variants WHERE id = %s", (data.keep_variant_id,))
        keep_variant = cursor.fetchone()
        if not keep_variant:
            raise HTTPException(status_code=404, detail="Keep variant not found")

        # Validate merge_variant_ids exist and are different base ingredients check
        cursor.execute("""
            SELECT id, base_ingredient_id FROM ingredient_variants
            WHERE id = ANY(%s)
        """, (data.merge_variant_ids,))
        merge_variants = cursor.fetchall()

        if len(merge_variants) != len(data.merge_variant_ids):
            raise HTTPException(status_code=400, detail="One or more merge variants not found")

        # Verify all variants are from the same base ingredient
        base_ids = set(v["base_ingredient_id"] for v in merge_variants)
        base_ids.add(keep_variant["base_ingredient_id"])
        if len(base_ids) > 1:
            raise HTTPException(status_code=400, detail="Cannot merge variants from different base ingredients")

        # Update products to point to keep_variant_id
        cursor.execute("""
            UPDATE products
            SET variant_id = %s
            WHERE variant_id = ANY(%s)
        """, (data.keep_variant_id, data.merge_variant_ids))
        products_updated = cursor.rowcount

        # Update common_products to point to keep_variant_id
        cursor.execute("""
            UPDATE common_products
            SET variant_id = %s
            WHERE variant_id = ANY(%s)
        """, (data.keep_variant_id, data.merge_variant_ids))

        # Update ingredient_mappings to point to keep_variant_id
        cursor.execute("""
            UPDATE ingredient_mappings
            SET variant_id = %s
            WHERE variant_id = ANY(%s)
        """, (data.keep_variant_id, data.merge_variant_ids))
        mappings_updated = cursor.rowcount

        # Soft-delete merged variants
        cursor.execute("""
            UPDATE ingredient_variants
            SET is_active = 0, updated_at = NOW()
            WHERE id = ANY(%s)
        """, (data.merge_variant_ids,))
        merged_count = cursor.rowcount

        conn.commit()

        # Audit log
        log_audit(cursor, "variants_merged", "ingredient_variant", data.keep_variant_id,
                  current_user["id"], current_user["organization_id"],
                  {
                      "merged_variant_ids": data.merge_variant_ids,
                      "products_updated": products_updated,
                      "mappings_updated": mappings_updated
                  })
        conn.commit()

        logger.info(f"Merged {merged_count} variants into {data.keep_variant_id}, "
                    f"updated {products_updated} products, {mappings_updated} mappings")

        return VariantMergeResponse(
            success=True,
            kept_variant_id=data.keep_variant_id,
            merged_count=merged_count,
            products_updated=products_updated,
            mappings_updated=mappings_updated
        )
