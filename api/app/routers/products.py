from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import Product, ProductWithPrice

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductWithPrice])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    distributor_id: Optional[int] = None,
    common_product_id: Optional[int] = None,
    unmapped_only: bool = False
):
    """
    List products with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search in product name or brand
    - **distributor_id**: Filter by distributor
    - **common_product_id**: Filter by common product mapping
    - **unmapped_only**: Show only products not mapped to common_products
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Build query
        query = """
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
            WHERE p.is_active = 1
        """

        params = []

        if search:
            query += " AND (p.name LIKE ? OR p.brand LIKE ?)"
            search_term = f"%{search}%"
            params.extend([search_term, search_term])

        if distributor_id:
            query += " AND dp.distributor_id = ?"
            params.append(distributor_id)

        if common_product_id is not None:
            query += " AND p.common_product_id = ?"
            params.append(common_product_id)

        if unmapped_only:
            query += " AND p.common_product_id IS NULL"

        query += " ORDER BY p.name LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        cursor.execute(query, params)
        products = dicts_from_rows(cursor.fetchall())

        return products


@router.get("/{product_id}", response_model=ProductWithPrice)
def get_product(product_id: int):
    """Get a single product by ID with latest price."""
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
            WHERE p.id = ?
        """, (product_id,))

        product = dict_from_row(cursor.fetchone())

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return product


@router.patch("/{product_id}/map")
def map_product_to_common(product_id: int, common_product_id: int):
    """Map a product to a common product."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        # Check if common product exists
        cursor.execute("SELECT id FROM common_products WHERE id = ?", (common_product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Common product not found")

        # Update mapping
        cursor.execute(
            "UPDATE products SET common_product_id = ? WHERE id = ?",
            (common_product_id, product_id)
        )
        conn.commit()

        return {"message": "Product mapped successfully", "product_id": product_id, "common_product_id": common_product_id}


@router.patch("/{product_id}/unmap")
def unmap_product(product_id: int):
    """Remove common product mapping from a product."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE products SET common_product_id = NULL WHERE id = ?",
            (product_id,)
        )
        conn.commit()

        return {"message": "Product unmapped successfully", "product_id": product_id}


@router.patch("/{product_id}")
def update_product(product_id: int, updates: dict):
    """Update product fields (name, brand, pack, size, unit_id, common_product_id)."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if product exists
        cursor.execute("SELECT id FROM products WHERE id = ?", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        # Build update query dynamically
        allowed_fields = ['name', 'brand', 'pack', 'size', 'unit_id', 'common_product_id']
        update_fields = []
        params = []

        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                params.append(value)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        params.append(product_id)
        query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"

        cursor.execute(query, params)
        conn.commit()

        return {"message": "Product updated successfully", "product_id": product_id}
