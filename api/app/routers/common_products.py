from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from ..database import get_db, dicts_from_rows, dict_from_row
from ..schemas import CommonProduct, CommonProductCreate, CommonProductUpdate
from ..auth import get_current_user

router = APIRouter(prefix="/common-products", tags=["common-products"])


@router.get("", response_model=list[CommonProduct])
def list_common_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List common products with optional filtering .

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **search**: Search in common product name
    - **category**: Filter by category
    """
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM common_products WHERE is_active = 1 AND organization_id = %s"
        params = [current_user["organization_id"]]

        if search:
            query += " AND common_name LIKE %s"
            params.append(f"%{search}%")

        if category:
            query += " AND category = %s"
            params.append(category)

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
            INSERT INTO common_products (common_name, category, subcategory, preferred_unit_id, notes, organization_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            common_product.common_name,
            common_product.category,
            common_product.subcategory,
            common_product.preferred_unit_id,
            common_product.notes,
            organization_id
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
