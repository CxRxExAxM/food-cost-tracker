from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Product, ProductWithPrice
from ..auth import get_current_user

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreate(BaseModel):
    """Create a new product."""
    name: str
    brand: Optional[str] = None
    pack: Optional[int] = None
    size: Optional[float] = None
    unit_id: Optional[int] = None
    is_catch_weight: bool = False
    distributor_id: Optional[int] = None
    case_price: Optional[float] = None


@router.post("")
def create_product(product: ProductCreate, current_user: dict = Depends(get_current_user)):
    """Create a new product with optional distributor link and price ."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Insert the product
        cursor.execute("""
            INSERT INTO products (name, brand, pack, size, unit_id, is_catch_weight)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (product.name, product.brand, product.pack, product.size,
              product.unit_id, product.is_catch_weight))

        product_id = cursor.lastrowid

        # If distributor specified, create distributor_product link
        if product.distributor_id:
            cursor.execute("""
                INSERT INTO distributor_products (distributor_id, product_id, distributor_name)
                VALUES (%s, %s, %s)
            """, (product.distributor_id, product_id, product.name))

            distributor_product_id = cursor.lastrowid

            # If price specified, add to price_history
            if product.case_price is not None:
                unit_price = None
                if product.pack and product.size:
                    unit_price = round(product.case_price / (product.pack * product.size), 2)

                cursor.execute("""
                    INSERT INTO price_history (distributor_product_id, case_price, unit_price, effective_date)
                    VALUES (%s, %s, %s, date('now'))
                """, (distributor_product_id, product.case_price, unit_price))

        conn.commit()

        return {"message": "Product created successfully", "product_id": product_id}


class ProductListResponse(BaseModel):
    """Response model for product list with pagination info."""
    products: list[ProductWithPrice]
    total: int


@router.get("", response_model=ProductListResponse)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    distributor_id: Optional[int] = None,
    common_product_id: Optional[int] = None,
    unmapped_only: bool = False,
    sort_by: str = Query("name", description="Column to sort by"),
    sort_dir: str = Query("asc", description="Sort direction: asc or desc"),
    current_user: dict = Depends(get_current_user)
):
    """
    List products with optional filtering and sorting .

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search in product name or brand
    - **distributor_id**: Filter by distributor
    - **common_product_id**: Filter by common product mapping
    - **unmapped_only**: Show only products not mapped to common_products
    - **sort_by**: Column to sort by (name, brand, distributor_name, pack, size, case_price, unit_price)
    - **sort_dir**: Sort direction (asc or desc)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Base WHERE clause - filter by organization
        where_clause = "WHERE p.is_active = 1 AND p.organization_id = %s"
        params = []

        if search:
            where_clause += " AND (p.name LIKE %s OR p.brand LIKE %s)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        if distributor_id:
            where_clause += " AND dp.distributor_id = %s"
            params.append(distributor_id)

        if common_product_id is not None:
            where_clause += " AND p.common_product_id = %s"
            params.append(common_product_id)

        if unmapped_only:
            where_clause += " AND p.common_product_id IS NULL"

        # Count total matching products
        count_query = f"""
            SELECT COUNT(DISTINCT p.id)
            FROM products p
            LEFT JOIN distributor_products dp ON dp.product_id = p.id
            {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

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
            LEFT JOIN (
                SELECT distributor_product_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
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
    """Get a single product by ID with latest price ."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
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
                SELECT distributor_product_id, case_price, unit_price, effective_date,
                       ROW_NUMBER() OVER (PARTITION BY distributor_product_id ORDER BY effective_date DESC) as rn
                FROM price_history
            ) ph ON ph.distributor_product_id = dp.id AND ph.rn = 1
            WHERE p.id = %s AND p.organization_id = %s
        """, (product_id))

        product = dict_from_row(cursor.fetchone())

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return product


@router.patch("/{product_id}/map")
def map_product_to_common(product_id: int, common_product_id: int, current_user: dict = Depends(get_current_user)):
    """Map a product to a common product ."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists and belongs to user's organization
        cursor.execute("SELECT id FROM products WHERE id = %s", (product_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        # Check if common product exists and belongs to user's organization
        cursor.execute("SELECT id FROM common_products WHERE id = %s", (common_product_id))
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
    """Remove common product mapping from a product ."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE products SET common_product_id = NULL WHERE id = %s",
            (product_id)
        )

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Product not found")

        conn.commit()

        return {"message": "Product unmapped successfully", "product_id": product_id}


@router.patch("/{product_id}")
def update_product(product_id: int, updates: dict, current_user: dict = Depends(get_current_user)):
    """Update product fields ."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists and get current values
        cursor.execute("SELECT id, pack, size FROM products WHERE id = %s", (product_id))
        product = cursor.fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        current_pack = product[1]
        current_size = product[2]

        # Build update query dynamically
        allowed_fields = ['name', 'brand', 'pack', 'size', 'unit_id', 'common_product_id', 'is_catch_weight']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = %s")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.extend([product_id])
        query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = %s"

        cursor.execute(query, params)

        # Recalculate unit_price in price_history if pack or size changed
        if 'pack' in updates or 'size' in updates:
            new_pack = updates.get('pack', current_pack)
            new_size = updates.get('size', current_size)

            if new_pack and new_size:
                # Update unit_price for all price_history records for this product
                cursor.execute("""
                    UPDATE price_history
                    SET unit_price = ROUND(case_price / (%s * %s), 2)
                    WHERE distributor_product_id IN (
                        SELECT id FROM distributor_products WHERE product_id = %s
                    )
                    AND case_price IS NOT NULL
                """, (new_pack, new_size, product_id))

        conn.commit()

        return {"message": "Product updated successfully", "product_id": product_id}
