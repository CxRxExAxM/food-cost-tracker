from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Product, ProductWithPrice
from ..auth import get_current_user, build_outlet_filter, build_product_filter, check_outlet_access
from ..config import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from ..logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreate(BaseModel):
    """Create a new product (organization-wide)."""
    name: str
    brand: Optional[str] = None
    pack: Optional[int] = None
    size: Optional[float] = None
    unit_id: Optional[int] = None
    is_catch_weight: bool = False
    distributor_id: Optional[int] = None
    distributor_sku: Optional[str] = None
    case_price: Optional[float] = None
    outlet_id: Optional[int] = None  # Only used for price_history (not for product itself)


@router.post("")
def create_product(product: ProductCreate, current_user: dict = Depends(get_current_user)):
    """Create a new product (organization-wide) with optional distributor link and price."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            organization_id = current_user["organization_id"]

            # Determine outlet_id for price_history only
            outlet_id = product.outlet_id
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

            # Insert the product with organization_id only (products are org-wide)
            cursor.execute("""
                INSERT INTO products (name, brand, pack, size, unit_id, is_catch_weight, organization_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (product.name, product.brand, product.pack, product.size,
                  product.unit_id, int(product.is_catch_weight), organization_id))

            product_id = cursor.fetchone()["id"]

            # If distributor specified, create distributor_product link (org-wide)
            if product.distributor_id:
                cursor.execute("""
                    INSERT INTO distributor_products (distributor_id, product_id, distributor_sku, distributor_name, organization_id)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (product.distributor_id, product_id, product.distributor_sku or '', product.name, organization_id))

                distributor_product_id = cursor.fetchone()["id"]

                # If price specified, add to price_history (outlet-specific)
                if product.case_price is not None:
                    unit_price = None
                    if product.pack and product.size:
                        unit_price = round(product.case_price / (product.pack * product.size), 2)

                    cursor.execute("""
                        INSERT INTO price_history (distributor_product_id, case_price, unit_price, effective_date, outlet_id)
                        VALUES (%s, %s, %s, CURRENT_DATE, %s)
                    """, (distributor_product_id, product.case_price, unit_price, outlet_id))

            conn.commit()

            return {"message": "Product created successfully", "product_id": product_id}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f" Create product failed: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")


class ProductListResponse(BaseModel):
    """Response model for product list with pagination info."""
    products: list[ProductWithPrice]
    total: int


@router.get("", response_model=ProductListResponse)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    search: Optional[str] = None,
    distributor_id: Optional[int] = None,
    common_product_id: Optional[int] = None,
    unmapped_only: bool = False,
    mapped_only: bool = False,
    outlet_id: Optional[int] = None,
    sort_by: str = Query("name", description="Column to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    List products with optional filtering and sorting.

    Products are organization-wide. All users in an organization see all products.
    The outlet_id parameter is used only to filter which outlet's prices to display.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search in product name or brand
    - **distributor_id**: Filter by distributor
    - **common_product_id**: Filter by common product mapping
    - **unmapped_only**: Show only products not mapped to common_products
    - **mapped_only**: Show only products mapped to common_products
    - **outlet_id**: Filter prices by specific outlet (products are org-wide)
    - **sort_by**: Column to sort by (name, brand, distributor_name, pack, size, case_price, unit_price)
    - **sort_dir**: Sort direction (asc or desc)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Base WHERE clause - products are org-wide, all users see all products
        org_id = current_user["organization_id"]
        where_clause = f"WHERE p.is_active = 1 AND p.organization_id = %s"
        params = [org_id]

        # Validate outlet_id for price filtering if specified
        if outlet_id is not None:
            if not check_outlet_access(current_user, outlet_id):
                raise HTTPException(status_code=403, detail="You don't have access to this outlet")

        if search:
            where_clause += " AND (p.name ILIKE %s OR p.brand ILIKE %s OR cp.common_name ILIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term, search_term])

        if distributor_id:
            where_clause += " AND dp.distributor_id = %s"
            params.append(distributor_id)

        if common_product_id is not None:
            where_clause += " AND p.common_product_id = %s"
            params.append(common_product_id)

        if unmapped_only:
            where_clause += " AND p.common_product_id IS NULL"

        if mapped_only:
            where_clause += " AND p.common_product_id IS NOT NULL"

        # Count total matching products
        count_query = f"""
            SELECT COUNT(DISTINCT p.id) as count
            FROM products p
            LEFT JOIN distributor_products dp ON dp.product_id = p.id
            LEFT JOIN common_products cp ON cp.id = p.common_product_id
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()["count"]

        # Map sort columns to actual SQL columns
        sort_column_map = {
            'name': 'p.name',
            'brand': 'p.brand',
            'distributor_name': 'd.name',
            'pack': 'p.pack',
            'size': 'p.size',
            'unit': 'u.abbreviation',
            'case_price': 'ph.case_price',
            'unit_price': 'ph.unit_price',
            'common_product_name': 'cp.common_name'
        }
        sort_col = sort_column_map.get(sort_by, 'p.name')
        sort_direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

        # Build price_history subquery and join condition
        # When outlet specified: get latest price for that outlet
        # When no outlet (All): get latest price from any outlet
        if outlet_id is not None:
            ph_subquery = """
                SELECT distributor_product_id, outlet_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id, outlet_id ORDER BY effective_date DESC) as rn
                FROM price_history
            """
            ph_join_condition = f"ph.distributor_product_id = dp.id AND ph.rn = 1 AND ph.outlet_id = {outlet_id}"
        else:
            # No outlet filter - get latest price across all outlets
            ph_subquery = """
                SELECT distributor_product_id, outlet_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            """
            ph_join_condition = "ph.distributor_product_id = dp.id AND ph.rn = 1"

        # Build main query
        query = f"""
            SELECT
                p.*,
                d.name as distributor_name,
                dp.distributor_sku,
                ph.case_price,
                ph.unit_price,
                ph.effective_date,
                u.abbreviation as unit_abbreviation,
                cp.common_name as common_product_name
            FROM products p
            LEFT JOIN distributor_products dp ON dp.product_id = p.id
            LEFT JOIN distributors d ON d.id = dp.distributor_id
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN common_products cp ON cp.id = p.common_product_id
            LEFT JOIN ({ph_subquery}) ph ON {ph_join_condition}
            {where_clause}
            ORDER BY {sort_col} {sort_direction} NULLS LAST
            LIMIT %s OFFSET %s
        """
        params.extend([limit, skip])

        cursor.execute(query, params)
        products = dicts_from_rows(cursor.fetchall())

        return {"products": products, "total": total}


@router.get("/{product_id}", response_model=ProductWithPrice)
def get_product(product_id: int, current_user: dict = Depends(get_current_user)):
    """Get a single product by ID with latest price."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build product filter (org-wide, no outlet filter)
        product_filter, product_params = build_product_filter(current_user, "p")

        # Get latest price across all outlets for this product
        query = f"""
            SELECT
                p.*,
                d.name as distributor_name,
                dp.distributor_sku,
                ph.case_price,
                ph.unit_price,
                ph.effective_date,
                u.abbreviation as unit_abbreviation,
                cp.common_name as common_product_name
            FROM products p
            LEFT JOIN distributor_products dp ON dp.product_id = p.id
            LEFT JOIN distributors d ON d.id = dp.distributor_id
            LEFT JOIN units u ON u.id = p.unit_id
            LEFT JOIN common_products cp ON cp.id = p.common_product_id
            LEFT JOIN (
                SELECT distributor_product_id, outlet_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
            WHERE p.id = %s AND {product_filter}
        """

        params = [product_id] + product_params
        cursor.execute(query, params)

        product = dict_from_row(cursor.fetchone())

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return product


@router.patch("/{product_id}/map")
def map_product_to_common(product_id: int, common_product_id: int, current_user: dict = Depends(get_current_user)):
    """Map a product to a common product."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists in user's organization (products are org-wide)
        product_filter, product_params = build_product_filter(current_user, "")
        query = f"SELECT id FROM products WHERE id = %s AND {product_filter}"
        params = [product_id] + product_params
        cursor.execute(query, params)

        product = dict_from_row(cursor.fetchone())
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Check if common product exists and belongs to user's organization
        cursor.execute("SELECT id FROM common_products WHERE id = %s AND organization_id = %s",
                      (common_product_id, current_user["organization_id"]))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Common product not found")

        # Update mapping
        cursor.execute(
            "UPDATE products SET common_product_id = %s WHERE id = %s",
            (common_product_id, product_id)
        )
        conn.commit()

        return {"message": "Product mapped successfully", "product_id": product_id, "common_product_id": common_product_id}


@router.patch("/{product_id}/unmap")
def unmap_product(product_id: int, current_user: dict = Depends(get_current_user)):
    """Remove common product mapping from a product."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Build product filter (org-wide)
        product_filter, product_params = build_product_filter(current_user, "")
        query = f"UPDATE products SET common_product_id = NULL WHERE id = %s AND {product_filter}"
        params = [product_id] + product_params

        cursor.execute(query, params)

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")

        conn.commit()

        return {"message": "Product unmapped successfully", "product_id": product_id}


@router.patch("/{product_id}")
def update_product(product_id: int, updates: dict, current_user: dict = Depends(get_current_user)):
    """Update product fields and/or prices."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists in user's organization (products are org-wide)
        product_filter, product_params = build_product_filter(current_user, "")
        check_query = f"SELECT id, pack, size FROM products WHERE id = %s AND {product_filter}"
        check_params = [product_id] + product_params
        cursor.execute(check_query, check_params)

        product = dict_from_row(cursor.fetchone())
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        current_pack = product["pack"]
        current_size = product["size"]

        # Separate price fields from product fields
        price_fields = ['case_price', 'unit_price']
        case_price_update = updates.pop('case_price', None)
        unit_price_update = updates.pop('unit_price', None)

        # Build update query dynamically for product fields
        allowed_fields = ['name', 'brand', 'pack', 'size', 'unit_id', 'common_product_id', 'is_catch_weight']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                # Convert boolean to int for is_catch_weight (stored as INTEGER in DB)
                if field == 'is_catch_weight':
                    params.append(int(value) if value is not None else 0)
                else:
                    params.append(value)

        # Update product fields if any
        if update_fields:
            params.append(product_id)
            params.extend(product_params)
            query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s AND {product_filter}"
            cursor.execute(query, params)

        # Recalculate unit_price in price_history if pack or size changed
        if 'pack' in updates or 'size' in updates:
            new_pack = updates.get('pack', current_pack)
            new_size = updates.get('size', current_size)

            if new_pack and new_size:
                # Update unit_price for all price_history records for this product
                # Cast to numeric for ROUND to work with precision argument
                cursor.execute("""
                    UPDATE price_history
                    SET unit_price = ROUND((case_price / (%s * %s))::numeric, 2)
                    WHERE distributor_product_id IN (
                        SELECT id FROM distributor_products WHERE product_id = %s
                    )
                    AND case_price IS NOT NULL
                """, (new_pack, new_size, product_id))

        # Handle price updates (case_price and/or unit_price)
        if case_price_update is not None or unit_price_update is not None:
            # Get the latest price_history record for this product
            cursor.execute("""
                SELECT ph.id, ph.case_price, ph.unit_price, dp.id as distributor_product_id
                FROM price_history ph
                JOIN distributor_products dp ON dp.id = ph.distributor_product_id
                WHERE dp.product_id = %s
                ORDER BY ph.effective_date DESC, ph.id DESC
                LIMIT 1
            """, (product_id,))

            price_record = dict_from_row(cursor.fetchone())

            if price_record:
                # Update existing price_history record
                new_case_price = float(case_price_update) if case_price_update is not None else price_record['case_price']
                new_unit_price = float(unit_price_update) if unit_price_update is not None else price_record['unit_price']

                # If only case_price changed, recalculate unit_price
                if case_price_update is not None and unit_price_update is None:
                    if current_pack and current_size:
                        new_unit_price = round(new_case_price / (current_pack * current_size), 2)

                cursor.execute("""
                    UPDATE price_history
                    SET case_price = %s, unit_price = %s
                    WHERE id = %s
                """, (new_case_price, new_unit_price, price_record['id']))

        # Ensure we have at least one update
        if not update_fields and case_price_update is None and unit_price_update is None:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        conn.commit()

        return {"message": "Product updated successfully", "product_id": product_id}


@router.delete("/{product_id}")
def delete_product(product_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a product and all its related data (distributor_products, price_history)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists in user's organization (products are org-wide)
        product_filter, product_params = build_product_filter(current_user, "")
        check_query = f"SELECT id, name FROM products WHERE id = %s AND {product_filter}"
        check_params = [product_id] + product_params
        cursor.execute(check_query, check_params)

        product = dict_from_row(cursor.fetchone())
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        # Delete the product (CASCADE will handle related records)
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")

        conn.commit()

        return {"message": f"Product '{product['name']}' deleted successfully", "product_id": product_id}
