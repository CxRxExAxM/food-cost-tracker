"""Unit Conversion Utilities

Shared functions for unit conversions used by recipes and banquet menus.
"""


def get_base_conversion_factor(cursor, from_unit_id: int, to_unit_id: int, org_id: int, outlet_id: int = None) -> float:
    """
    Get base conversion factor from base_conversions table.

    Checks in priority order:
    1. Outlet-specific conversion (if outlet_id provided)
    2. Organization-wide conversion
    3. System default conversion (organization_id IS NULL)

    Returns None if no conversion found.
    """
    if from_unit_id == to_unit_id:
        return 1.0

    cursor.execute("""
        SELECT conversion_factor
        FROM base_conversions
        WHERE from_unit_id = %s
          AND to_unit_id = %s
          AND is_active = 1
          AND (organization_id IS NULL OR organization_id = %s)
          AND (outlet_id IS NULL OR outlet_id = %s)
        ORDER BY
            CASE WHEN outlet_id = %s THEN 0
                 WHEN organization_id = %s THEN 1
                 ELSE 2 END
        LIMIT 1
    """, (from_unit_id, to_unit_id, org_id, outlet_id or 0, outlet_id or 0, org_id))

    result = cursor.fetchone()
    if result:
        return float(result['conversion_factor'])

    return None


def get_unit_conversion_factor(cursor, common_product_id: int, from_unit_id: int, to_unit_id: int, org_id: int, outlet_id: int = None) -> float:
    """
    Get conversion factor between two units for a common product.

    Returns the factor to multiply a quantity in from_unit to get to_unit.

    Conversion priority:
    1. Direct product conversion (EA → LB for ribeye)
    2. Reverse product conversion (LB → EA inverted)
    3. Product conversion + base conversion chain (EA → OZ → LB)
    4. Base conversion from database (OZ → LB)
    5. Hardcoded fallback for common weight/volume conversions

    Example: 1 EA ribeye = 6 OZ, and we need to convert to LB
    - Product conversion: EA → OZ = 6
    - Base conversion: OZ → LB = 0.0625
    - Result: 6 × 0.0625 = 0.375
    """
    if from_unit_id == to_unit_id:
        return 1.0

    if not from_unit_id or not to_unit_id:
        return 1.0

    # ============================================
    # Step 1: Try direct product conversion
    # ============================================
    if common_product_id:
        cursor.execute("""
            SELECT conversion_factor
            FROM product_conversions
            WHERE common_product_id = %s
              AND from_unit_id = %s
              AND to_unit_id = %s
              AND organization_id = %s
        """, (common_product_id, from_unit_id, to_unit_id, org_id))

        result = cursor.fetchone()
        if result:
            return float(result['conversion_factor'])

        # ============================================
        # Step 2: Try reverse product conversion
        # ============================================
        cursor.execute("""
            SELECT conversion_factor
            FROM product_conversions
            WHERE common_product_id = %s
              AND from_unit_id = %s
              AND to_unit_id = %s
              AND organization_id = %s
        """, (common_product_id, to_unit_id, from_unit_id, org_id))

        result = cursor.fetchone()
        if result:
            return 1.0 / float(result['conversion_factor'])

        # ============================================
        # Step 3: Try chaining product conversion + base conversion
        # Example: EA → OZ (product) then OZ → LB (base)
        # ============================================
        cursor.execute("""
            SELECT to_unit_id, conversion_factor
            FROM product_conversions
            WHERE common_product_id = %s
              AND from_unit_id = %s
              AND organization_id = %s
        """, (common_product_id, from_unit_id, org_id))

        product_conversions = {row['to_unit_id']: float(row['conversion_factor']) for row in cursor.fetchall()}

        # For each intermediate unit from product conversions, try base conversion to target
        for intermediate_unit_id, product_factor in product_conversions.items():
            base_factor = get_base_conversion_factor(cursor, intermediate_unit_id, to_unit_id, org_id, outlet_id)
            if base_factor is not None:
                # Chain: from_unit → intermediate (product) → to_unit (base)
                return product_factor * base_factor

        # Also try reverse: base conversion first, then product conversion
        # Example: LB → OZ (base) then OZ → EA (reverse product)
        cursor.execute("""
            SELECT from_unit_id, conversion_factor
            FROM product_conversions
            WHERE common_product_id = %s
              AND to_unit_id = %s
              AND organization_id = %s
        """, (common_product_id, to_unit_id, org_id))

        reverse_product_conversions = {row['from_unit_id']: float(row['conversion_factor']) for row in cursor.fetchall()}

        for intermediate_unit_id, product_factor in reverse_product_conversions.items():
            base_factor = get_base_conversion_factor(cursor, from_unit_id, intermediate_unit_id, org_id, outlet_id)
            if base_factor is not None:
                # Chain: from_unit → intermediate (base) → to_unit (product)
                return base_factor * product_factor

    # ============================================
    # Step 4: Try base conversion from database
    # ============================================
    base_factor = get_base_conversion_factor(cursor, from_unit_id, to_unit_id, org_id, outlet_id)
    if base_factor is not None:
        return base_factor

    # ============================================
    # Step 5: Hardcoded fallback (in case base_conversions not populated)
    # ============================================
    cursor.execute("""
        SELECT u1.abbreviation as from_abbr, u2.abbreviation as to_abbr
        FROM units u1, units u2
        WHERE u1.id = %s AND u2.id = %s
    """, (from_unit_id, to_unit_id))

    units = cursor.fetchone()
    if units:
        from_abbr = units['from_abbr'].upper()
        to_abbr = units['to_abbr'].upper()

        # Standard weight conversions (all relative to OZ)
        weight_to_oz = {'OZ': 1, 'LB': 16, 'G': 0.035274, 'KG': 35.274}

        if from_abbr in weight_to_oz and to_abbr in weight_to_oz:
            return weight_to_oz[from_abbr] / weight_to_oz[to_abbr]

        # Standard volume conversions (all relative to FL OZ)
        volume_to_floz = {
            'FL OZ': 1,
            'CUP': 8,
            'PT': 16,
            'QT': 32,
            'GAL': 128,
            'ML': 0.033814,
            'L': 33.814,
            'TBSP': 0.5,
            'TSP': 0.166667
        }

        if from_abbr in volume_to_floz and to_abbr in volume_to_floz:
            return volume_to_floz[from_abbr] / volume_to_floz[to_abbr]

    # No conversion found - return 1.0 (assumes same unit or incompatible)
    return 1.0


def get_unit_id_from_abbreviation(cursor, abbr: str) -> int:
    """Look up unit ID from abbreviation."""
    if not abbr:
        return None
    cursor.execute("""
        SELECT id FROM units WHERE UPPER(abbreviation) = UPPER(%s) LIMIT 1
    """, (abbr.strip(),))
    result = cursor.fetchone()
    return result['id'] if result else None
