from fastapi import APIRouter, HTTPException, Query, Depends, Request, Body
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import CommonProduct, CommonProductCreate, CommonProductUpdate, QuickCreateProductRequest, QuickCreateProductResponse, MergeCommonProductsRequest, MergeCommonProductsResponse
from ..auth import get_current_user
from ..audit import log_audit

router = APIRouter(prefix="/common-products", tags=["common-products"])


@router.get("/categories")
def get_categories(current_user: dict = Depends(get_current_user)):
    """Get distinct categories for common products."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT category
            FROM common_products
            WHERE is_active = 1
              AND organization_id = %s
              AND category IS NOT NULL
              AND category != ''
            ORDER BY category
        """, (current_user["organization_id"],))
        rows = cursor.fetchall()
        return [row["category"] for row in rows]


@router.get("")
def list_common_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    search: Optional[str] = None,
    category: Optional[str] = None,
    allergen: Optional[str] = None,
    include_linked_count: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """
    List common products with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search in common product name
    - **category**: Filter by category
    - **allergen**: Filter by allergen (e.g., 'allergen_gluten', 'allergen_dairy')
    - **include_linked_count**: Include count of linked products
    """
    with get_db() as conn:
        cursor = conn.cursor()

        if include_linked_count:
            query = """
                SELECT cp.*,
                       COALESCE(pc.linked_count, 0) as linked_products_count
                FROM common_products cp
                LEFT JOIN (
                    SELECT common_product_id, COUNT(*) as linked_count
                    FROM products
                    WHERE is_active = 1
                    GROUP BY common_product_id
                ) pc ON pc.common_product_id = cp.id
                WHERE cp.is_active = 1 AND cp.organization_id = %s
            """
        else:
            query = "SELECT * FROM common_products WHERE is_active = 1 AND organization_id = %s"
        params = [current_user["organization_id"]]

        if search:
            if include_linked_count:
                query += " AND cp.common_name ILIKE %s"
            else:
                query += " AND common_name ILIKE %s"
            params.append(f"%{search}%")

        if category:
            if include_linked_count:
                query += " AND cp.category = %s"
            else:
                query += " AND category = %s"
            params.append(category)

        if allergen:
            # Validate allergen field name to prevent SQL injection
            valid_allergens = [
                'allergen_vegan', 'allergen_vegetarian', 'allergen_gluten',
                'allergen_crustation', 'allergen_egg', 'allergen_mollusk',
                'allergen_fish', 'allergen_lupin', 'allergen_dairy',
                'allergen_tree_nuts', 'allergen_peanuts', 'allergen_sesame',
                'allergen_soy', 'allergen_sulphur_dioxide', 'allergen_mustard',
                'allergen_celery'
            ]
            if allergen in valid_allergens:
                if include_linked_count:
                    query += f" AND cp.{allergen} = 1"
                else:
                    query += f" AND {allergen} = 1"

        if include_linked_count:
            query += " ORDER BY cp.common_name LIMIT %s OFFSET %s"
        else:
            query += " ORDER BY common_name LIMIT %s OFFSET %s"
        params.extend([limit, skip])

        cursor.execute(query, params)
        common_products = dicts_from_rows(cursor.fetchall())

        return common_products


@router.get("/{common_product_id}", response_model=CommonProduct)
def get_common_product(common_product_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single common product by ID ."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM common_products WHERE id = %s AND organization_id = %s",
                      (common_product_id, current_user["organization_id"]))
        common_product = dict_from_row(cursor.fetchone())

        if not common_product:
            raise HTTPException(status_code=404, detail="Common product not found in your organization")

        return common_product


@router.post("", response_model=CommonProduct, status_code=201)
def create_common_product(common_product: CommonProductCreate, current_user: dict = Depends(get_current_user)):
    """Create a new common product ."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if common_name already exists in this organization
        organization_id = current_user["organization_id"]
        cursor.execute(
            "SELECT id FROM common_products WHERE common_name = %s AND organization_id = %s",
            (common_product.common_name, organization_id)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"Common product '{common_product.common_name}' already exists in your organization"
            )

        cursor.execute("""
            INSERT INTO common_products (
                common_name, category, subcategory, preferred_unit_id, notes, organization_id,
                allergen_vegan, allergen_vegetarian, allergen_gluten, allergen_crustation,
                allergen_egg, allergen_mollusk, allergen_fish, allergen_lupin, allergen_dairy,
                allergen_tree_nuts, allergen_peanuts, allergen_sesame, allergen_soy,
                allergen_sulphur_dioxide, allergen_mustard, allergen_celery
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            common_product.common_name,
            common_product.category,
            common_product.subcategory,
            common_product.preferred_unit_id,
            common_product.notes,
            organization_id,
            int(common_product.allergen_vegan),
            int(common_product.allergen_vegetarian),
            int(common_product.allergen_gluten),
            int(common_product.allergen_crustation),
            int(common_product.allergen_egg),
            int(common_product.allergen_mollusk),
            int(common_product.allergen_fish),
            int(common_product.allergen_lupin),
            int(common_product.allergen_dairy),
            int(common_product.allergen_tree_nuts),
            int(common_product.allergen_peanuts),
            int(common_product.allergen_sesame),
            int(common_product.allergen_soy),
            int(common_product.allergen_sulphur_dioxide),
            int(common_product.allergen_mustard),
            int(common_product.allergen_celery)
        ))

        result = dict_from_row(cursor.fetchone())
        conn.commit()

        return result


@router.patch("/{common_product_id}", response_model=CommonProduct)
def update_common_product(common_product_id: int, update: CommonProductUpdate, current_user: dict = Depends(get_current_user)):
    """Update a common product ."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check if exists and belongs to user's organization
            cursor.execute("SELECT id FROM common_products WHERE id = %s AND organization_id = %s",
                          (common_product_id, current_user["organization_id"]))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Common product not found in your organization")

            # Build update query dynamically
            update_fields = []
            params = []

            for field, value in update.model_dump(exclude_unset=True).items():
                update_fields.append(f"{field} = %s")
                # Convert boolean to integer for allergen fields (PostgreSQL uses integer for boolean)
                if field.startswith('allergen_') and isinstance(value, bool):
                    params.append(int(value))
                else:
                    params.append(value)

            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            params.append(common_product_id)
            query = f"UPDATE common_products SET {', '.join(update_fields)} WHERE id = %s"

            print(f"[DEBUG] Update query: {query}")
            print(f"[DEBUG] Params: {params}")
            cursor.execute(query, params)
            conn.commit()

            # Return updated common product
            cursor.execute("SELECT * FROM common_products WHERE id = %s", (common_product_id,))
            return dict_from_row(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[ERROR] Update common product failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.delete("/{common_product_id}")
def delete_common_product(common_product_id: int, current_user: dict = Depends(get_current_user)):
    """Soft delete a common product ."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE common_products SET is_active = 0 WHERE id = %s AND organization_id = %s",
            (common_product_id, current_user["organization_id"])
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Common product not found in your organization")

        conn.commit()

        return {"message": "Common product deleted successfully"}


@router.get("/{common_product_id}/products")
def get_common_product_products(common_product_id: int, current_user: dict = Depends(get_current_user)):
    """Get all distributor products mapped to this common product ."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if common product exists and belongs to user's organization
        cursor.execute("SELECT id FROM common_products WHERE id = %s AND organization_id = %s",
                      (common_product_id, current_user["organization_id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Common product not found in your organization")

        cursor.execute("""
            SELECT
                p.*,
                d.name as distributor_name,
                dp.distributor_sku,
                ph.case_price,
                ph.unit_price,
                ph.effective_date,
                u.abbreviation as unit_abbreviation
            FROM products p
            JOIN distributor_products dp ON dp.product_id = p.id
            JOIN distributors d ON d.id = dp.distributor_id
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN (
                SELECT distributor_product_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
            WHERE p.common_product_id = %s AND p.organization_id = %s
            ORDER BY ph.unit_price ASC
        """, (common_product_id, current_user["organization_id"]))

        products = dicts_from_rows(cursor.fetchall())

        return products


@router.get("/{common_product_id}/mapped-products")
def get_mapped_products(
    common_product_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all products mapped to this common product, grouped by outlet.
    Respects user outlet access for multi-tenancy.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify common product exists and user has access
        cursor.execute("""
            SELECT * FROM common_products
            WHERE id = %s AND organization_id = %s
        """, (common_product_id, current_user['organization_id']))

        common_product = dict_from_row(cursor.fetchone())
        if not common_product:
            raise HTTPException(status_code=404, detail="Common product not found")

        # Build outlet filter based on user role and outlet assignments
        outlet_filter = ""
        outlet_params = []

        # If user is not admin, filter by assigned outlets
        if current_user.get('role') != 'admin':
            cursor.execute("""
                SELECT outlet_id FROM user_outlets WHERE user_id = %s
            """, (current_user['id'],))
            user_outlets = [row['outlet_id'] for row in cursor.fetchall()]

            if user_outlets:
                placeholders = ', '.join(['%s'] * len(user_outlets))
                outlet_filter = f"AND p.outlet_id IN ({placeholders})"
                outlet_params = user_outlets
            else:
                # User has no outlet access - return empty
                return {
                    "common_product": common_product,
                    "products_by_outlet": {},
                    "total_count": 0
                }

        # Get all mapped products with latest prices
        query = f"""
            SELECT
                p.*,
                o.name as outlet_name,
                d.name as distributor_name,
                u.abbreviation as unit_abbreviation,
                ph.case_price,
                ph.unit_price,
                ph.effective_date
            FROM products p
            JOIN outlets o ON o.id = p.outlet_id
            LEFT JOIN distributor_products dp ON dp.product_id = p.id
            LEFT JOIN distributors d ON d.id = dp.distributor_id
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN (
                SELECT distributor_product_id, outlet_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id, outlet_id
                                          ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
            WHERE p.common_product_id = %s
              AND p.organization_id = %s
              {outlet_filter}
            ORDER BY o.name, p.name
        """

        params = [common_product_id, current_user['organization_id']] + outlet_params
        cursor.execute(query, params)
        products = dicts_from_rows(cursor.fetchall())

        # Group by outlet
        products_by_outlet = {}
        for product in products:
            outlet_name = product['outlet_name']
            if outlet_name not in products_by_outlet:
                products_by_outlet[outlet_name] = []
            products_by_outlet[outlet_name].append(product)

        return {
            "common_product": common_product,
            "products_by_outlet": products_by_outlet,
            "total_count": len(products)
        }


# ============================================
# Unit Conversions Endpoints
# ============================================

@router.get("/{common_product_id}/conversions")
def get_conversions(
    common_product_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Get all unit conversions for a common product."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify access
        cursor.execute("""
            SELECT id FROM common_products
            WHERE id = %s AND organization_id = %s
        """, (common_product_id, current_user['organization_id']))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Common product not found")

        # Get conversions with unit names
        cursor.execute("""
            SELECT
                pc.*,
                u1.abbreviation as from_unit_name,
                u2.abbreviation as to_unit_name
            FROM product_conversions pc
            JOIN units u1 ON u1.id = pc.from_unit_id
            JOIN units u2 ON u2.id = pc.to_unit_id
            WHERE pc.common_product_id = %s
            ORDER BY u1.abbreviation, u2.abbreviation
        """, (common_product_id,))

        return dicts_from_rows(cursor.fetchall())


@router.post("/{common_product_id}/conversions")
def create_conversion(
    common_product_id: int,
    from_unit_id: int = Body(...),
    to_unit_id: int = Body(...),
    conversion_factor: float = Body(...),
    notes: str = Body(None),
    create_reverse: bool = Body(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a unit conversion for a common product.

    Example: 1 ea Banana = 5 oz
    - from_unit_id: ea (each)
    - to_unit_id: oz (ounce)
    - conversion_factor: 5.0
    - create_reverse: True (also creates oz → ea with factor 1/5)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Validate
        if from_unit_id == to_unit_id:
            raise HTTPException(status_code=400, detail="Cannot convert unit to itself")
        if conversion_factor <= 0:
            raise HTTPException(status_code=400, detail="Conversion factor must be positive")

        # Verify access
        cursor.execute("""
            SELECT id FROM common_products
            WHERE id = %s AND organization_id = %s
        """, (common_product_id, current_user['organization_id']))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Common product not found")

        # Create forward conversion
        try:
            cursor.execute("""
                INSERT INTO product_conversions
                (common_product_id, from_unit_id, to_unit_id, conversion_factor, notes, organization_id, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                common_product_id, from_unit_id, to_unit_id, conversion_factor,
                notes, current_user['organization_id'], current_user['id']
            ))

            forward_id = dict_from_row(cursor.fetchone())['id']
        except Exception as e:
            if 'uq_product_conversion' in str(e):
                raise HTTPException(status_code=400, detail="This conversion already exists")
            raise

        # Create reverse conversion if requested
        reverse_id = None
        if create_reverse:
            try:
                cursor.execute("""
                    INSERT INTO product_conversions
                    (common_product_id, from_unit_id, to_unit_id, conversion_factor, notes, organization_id, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    common_product_id, to_unit_id, from_unit_id, 1.0 / conversion_factor,
                    f"Reverse of: {notes}" if notes else None,
                    current_user['organization_id'], current_user['id']
                ))
                reverse_id = dict_from_row(cursor.fetchone())['id']
            except Exception as e:
                # If reverse fails, still commit the forward
                pass

        conn.commit()

        return {
            "forward_conversion_id": forward_id,
            "reverse_conversion_id": reverse_id,
            "message": f"Conversion created{' (with reverse)' if create_reverse else ''}"
        }


@router.patch("/{common_product_id}/conversions/{conversion_id}")
def update_conversion(
    common_product_id: int,
    conversion_id: int,
    conversion_factor: float = Body(None),
    notes: str = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Update conversion factor or notes."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify access
        cursor.execute("""
            SELECT id FROM product_conversions
            WHERE id = %s AND common_product_id = %s AND organization_id = %s
        """, (conversion_id, common_product_id, current_user['organization_id']))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Conversion not found")

        # Build update
        updates = []
        params = []

        if conversion_factor is not None:
            if conversion_factor <= 0:
                raise HTTPException(status_code=400, detail="Factor must be positive")
            updates.append("conversion_factor = %s")
            params.append(conversion_factor)

        if notes is not None:
            updates.append("notes = %s")
            params.append(notes)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(conversion_id)

        cursor.execute(f"""
            UPDATE product_conversions
            SET {', '.join(updates)}
            WHERE id = %s
        """, params)

        conn.commit()

        return {"message": "Conversion updated"}


@router.delete("/{common_product_id}/conversions/{conversion_id}")
def delete_conversion(
    common_product_id: int,
    conversion_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a unit conversion."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM product_conversions
            WHERE id = %s AND common_product_id = %s AND organization_id = %s
        """, (conversion_id, common_product_id, current_user['organization_id']))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conversion not found")

        conn.commit()

        return {"message": "Conversion deleted"}


@router.post("/{common_product_id}/convert")
def convert_quantity(
    common_product_id: int,
    quantity: float = Body(...),
    from_unit_id: int = Body(...),
    to_unit_id: int = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Utility endpoint to convert a quantity between units.
    Returns converted quantity or error if conversion not defined.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Find conversion
        cursor.execute("""
            SELECT conversion_factor
            FROM product_conversions
            WHERE common_product_id = %s
              AND from_unit_id = %s
              AND to_unit_id = %s
              AND organization_id = %s
        """, (common_product_id, from_unit_id, to_unit_id, current_user['organization_id']))

        conversion = dict_from_row(cursor.fetchone())

        if not conversion:
            raise HTTPException(
                status_code=404,
                detail=f"No conversion defined from unit {from_unit_id} to {to_unit_id}"
            )

        converted_quantity = quantity * conversion['conversion_factor']

        return {
            "original_quantity": quantity,
            "original_unit_id": from_unit_id,
            "converted_quantity": round(converted_quantity, 4),
            "converted_unit_id": to_unit_id,
            "conversion_factor": conversion['conversion_factor']
        }


@router.post("/merge", response_model=MergeCommonProductsResponse)
def merge_common_products(
    request: MergeCommonProductsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Merge multiple common products into one target.

    - Remaps all products from source common products to target
    - Remaps recipe ingredients from sources to target
    - Merges allergens using OR logic (if any source has allergen, target gets it)
    - Soft-deletes source common products
    """
    if current_user['role'] not in ['chef', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Only Chef and Admin roles can merge products"
        )

    if request.target_id in request.source_ids:
        raise HTTPException(
            status_code=400,
            detail="Target cannot be in source list"
        )

    if len(request.source_ids) < 1:
        raise HTTPException(
            status_code=400,
            detail="At least one source product is required"
        )

    with get_db() as conn:
        cursor = conn.cursor()
        organization_id = current_user["organization_id"]

        # Verify target exists and belongs to organization
        cursor.execute("""
            SELECT * FROM common_products
            WHERE id = %s AND organization_id = %s AND is_active = 1
        """, (request.target_id, organization_id))
        target = dict_from_row(cursor.fetchone())
        if not target:
            raise HTTPException(status_code=404, detail="Target product not found")

        # Verify all sources exist and belong to organization
        placeholders = ', '.join(['%s'] * len(request.source_ids))
        cursor.execute(f"""
            SELECT * FROM common_products
            WHERE id IN ({placeholders})
              AND organization_id = %s
              AND is_active = 1
        """, (*request.source_ids, organization_id))
        sources = dicts_from_rows(cursor.fetchall())

        if len(sources) != len(request.source_ids):
            raise HTTPException(status_code=404, detail="One or more source products not found")

        # Count products that will be remapped
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM products
            WHERE common_product_id IN ({placeholders})
              AND organization_id = %s
        """, (*request.source_ids, organization_id))
        products_remapped = dict_from_row(cursor.fetchone())['count']

        # Count recipe ingredients that will be remapped
        cursor.execute(f"""
            SELECT COUNT(*) as count FROM recipe_ingredients
            WHERE common_product_id IN ({placeholders})
        """, request.source_ids)
        ingredients_remapped = dict_from_row(cursor.fetchone())['count']

        # Remap products from sources to target
        cursor.execute(f"""
            UPDATE products
            SET common_product_id = %s
            WHERE common_product_id IN ({placeholders})
              AND organization_id = %s
        """, (request.target_id, *request.source_ids, organization_id))

        # Remap recipe ingredients from sources to target
        cursor.execute(f"""
            UPDATE recipe_ingredients
            SET common_product_id = %s
            WHERE common_product_id IN ({placeholders})
        """, (request.target_id, *request.source_ids))

        # Merge allergens using OR logic
        allergen_fields = [
            'allergen_vegan', 'allergen_vegetarian', 'allergen_gluten',
            'allergen_crustation', 'allergen_egg', 'allergen_mollusk',
            'allergen_fish', 'allergen_lupin', 'allergen_dairy',
            'allergen_tree_nuts', 'allergen_peanuts', 'allergen_sesame',
            'allergen_soy', 'allergen_sulphur_dioxide', 'allergen_mustard',
            'allergen_celery'
        ]

        merged_allergens = {}
        for field in allergen_fields:
            # Target starts with its own value, OR with all sources
            value = target.get(field, 0)
            for source in sources:
                value = value or source.get(field, 0)
            merged_allergens[field] = 1 if value else 0

        # Update target with merged allergens
        update_parts = [f"{field} = %s" for field in allergen_fields]
        cursor.execute(f"""
            UPDATE common_products
            SET {', '.join(update_parts)}
            WHERE id = %s
        """, (*merged_allergens.values(), request.target_id))

        # Soft-delete source common products
        cursor.execute(f"""
            UPDATE common_products
            SET is_active = 0
            WHERE id IN ({placeholders})
        """, request.source_ids)

        conn.commit()

        # Get updated target
        cursor.execute("SELECT * FROM common_products WHERE id = %s", (request.target_id,))
        updated_target = dict_from_row(cursor.fetchone())

        return MergeCommonProductsResponse(
            target_id=request.target_id,
            sources_merged=len(request.source_ids),
            products_remapped=products_remapped,
            ingredients_remapped=ingredients_remapped,
            merged_allergens=[k for k, v in merged_allergens.items() if v],
            message=f"Successfully merged {len(request.source_ids)} products into '{updated_target['common_name']}'"
        )


@router.post("/quick-create", response_model=QuickCreateProductResponse, status_code=201)
def quick_create_common_product(
    product: QuickCreateProductRequest,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Quick create common product during AI recipe parsing flow.

    Simplified version of create endpoint with minimal required fields.
    Used when user needs to create a product inline during review.

    Required permissions: Chef or Admin role
    """

    print(f"[QUICK-CREATE] Starting product creation: {product.common_name}")
    print(f"[QUICK-CREATE] User: {current_user.get('id')}, Org: {current_user.get('organization_id')}")

    try:
        # Check permissions
        if current_user['role'] not in ['chef', 'admin']:
            raise HTTPException(
                status_code=403,
                detail="Only Chef and Admin roles can create products"
            )

        organization_id = current_user["organization_id"]

        with get_db() as conn:
            cursor = conn.cursor()

            print(f"[QUICK-CREATE] Checking for duplicates...")
            # Check if common_name already exists in this organization
            cursor.execute(
                "SELECT id FROM common_products WHERE common_name = %s AND organization_id = %s",
                (product.common_name, organization_id)
            )
            existing = cursor.fetchone()
            if existing:
                print(f"[QUICK-CREATE] Duplicate found: {existing['id']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Product '{product.common_name}' already exists in your organization"
                )

            print(f"[QUICK-CREATE] Inserting into database...")
            # Create with minimal fields (allergens default to 0)
            cursor.execute("""
                INSERT INTO common_products (
                    common_name, category, subcategory, organization_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, common_name, category
            """, (
                product.common_name,
                product.category,
                product.subcategory,
                organization_id
            ))

            result = cursor.fetchone()
            print(f"[QUICK-CREATE] Product created with ID: {result['id']}")
            conn.commit()
            print(f"[QUICK-CREATE] Committed to database")

            # Log audit event
            print(f"[QUICK-CREATE] Logging audit event...")
            try:
                log_audit(
                    user_id=current_user['id'],  # Database column is 'id', not 'user_id'
                    organization_id=organization_id,
                    action='common_product_created',
                    entity_type='common_product',
                    entity_id=result['id'],
                    changes={
                        'common_name': product.common_name,
                        'category': product.category,
                        'created_via': 'ai_recipe_parser'
                    },
                    ip_address=request.client.host if request else None
                )
                print(f"[QUICK-CREATE] Audit logged successfully")
            except Exception as audit_error:
                print(f"[QUICK-CREATE ERROR] Audit logging failed: {type(audit_error).__name__}: {str(audit_error)}")
                import traceback
                traceback.print_exc()
                # Continue despite audit failure
                print(f"[QUICK-CREATE] Continuing despite audit failure...")

            print(f"[QUICK-CREATE] Creating response...")
            response = QuickCreateProductResponse(
                common_product_id=result['id'],
                common_name=result['common_name'],
                category=result['category'],
                message=f"Product '{product.common_name}' created successfully"
            )
            print(f"[QUICK-CREATE] Success! Returning response")
            return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"[QUICK-CREATE ERROR] Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating product: {str(e)}"
        )
