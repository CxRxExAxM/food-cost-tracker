"""
Ingredient Taxonomy API endpoints.

Provides CRUD operations for:
- Base ingredients (core concepts like Carrot, Chicken, Tomato)
- Ingredient variants (specific forms like Diced Carrot, Chicken Breast Boneless)
- Variant merge functionality to consolidate duplicates
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
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

logger = get_logger(__name__)

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


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

        # Group variants by base ingredient
        variants_by_base = {}
        for v in variants:
            base_id = v["base_ingredient_id"]
            if base_id not in variants_by_base:
                variants_by_base[base_id] = []
            variants_by_base[base_id].append(v)

        # Attach variants to bases
        for base in bases:
            base["variants"] = variants_by_base.get(base["id"], [])

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

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify variant exists
        cursor.execute("SELECT id FROM ingredient_variants WHERE id = %s", (variant_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Variant not found")

        # Get common products with their linked vendor products
        cursor.execute("""
            SELECT
                cp.id,
                cp.common_name,
                cp.description,
                cp.standard_unit_id,
                u.name as unit_name,
                cp.created_at,
                cp.updated_at
            FROM common_products cp
            LEFT JOIN units u ON u.id = cp.standard_unit_id
            WHERE cp.variant_id = %s AND cp.is_active = 1
            ORDER BY cp.common_name
        """, (variant_id,))
        common_products = dicts_from_rows(cursor.fetchall())

        if not common_products:
            return []

        cp_ids = [cp["id"] for cp in common_products]

        # Get linked vendor products for these common products
        cursor.execute("""
            SELECT
                p.id,
                p.common_product_id,
                p.description,
                p.vendor_id,
                v.name as vendor_name,
                p.unit_id,
                u.name as unit_name,
                p.pack_size,
                p.price,
                p.vendor_code,
                p.is_active
            FROM products p
            JOIN vendors v ON v.id = p.vendor_id
            LEFT JOIN units u ON u.id = p.unit_id
            WHERE p.common_product_id = ANY(%s)
              AND p.organization_id = %s
              AND p.is_active = 1
            ORDER BY v.name, p.description
        """, (cp_ids, org_id))
        products = dicts_from_rows(cursor.fetchall())

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

        return common_products


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
