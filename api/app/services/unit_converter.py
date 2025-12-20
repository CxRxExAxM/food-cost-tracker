"""
Unit conversion and normalization service for AI recipe parser.

Normalizes ingredient quantities to preferred units while preserving original values.
"""

from typing import Tuple, Optional


# Conversion factors to base units
VOLUME_CONVERSIONS = {
    # To fluid ounces (FL OZ)
    'gallon': 128,
    'gal': 128,
    'quart': 32,
    'qt': 32,
    'pint': 16,
    'pt': 16,
    'cup': 8,
    'c': 8,
    'fluid ounce': 1,
    'fl oz': 1,
    'fl. oz': 1,
    'tablespoon': 0.5,
    'tbsp': 0.5,
    'teaspoon': 0.166667,
    'tsp': 0.166667,
}

WEIGHT_CONVERSIONS = {
    # To ounces (OZ)
    'pound': 16,
    'lb': 16,
    'lbs': 16,
    'ounce': 1,
    'oz': 1,
    'kilogram': 35.274,
    'kg': 35.274,
    'gram': 0.035274,
    'g': 0.035274,
}

# Unit type mapping
UNIT_TYPES = {
    'volume': list(VOLUME_CONVERSIONS.keys()),
    'weight': list(WEIGHT_CONVERSIONS.keys()),
    'count': ['each', 'ea', 'piece', 'pc', 'item', 'unit', 'whole']
}


def get_unit_type(unit: str) -> Optional[str]:
    """
    Determine if unit is volume, weight, or count.

    Args:
        unit: Unit string (e.g., 'lb', 'cup', 'each')

    Returns:
        'volume', 'weight', 'count', or None if unknown
    """
    unit_lower = unit.lower().strip()

    for unit_type, units in UNIT_TYPES.items():
        if unit_lower in units:
            return unit_type

    return None


def normalize_unit_string(unit: str) -> str:
    """
    Normalize unit string to standard abbreviation.

    Args:
        unit: Raw unit string from parsing

    Returns:
        Normalized unit abbreviation
    """
    unit_lower = unit.lower().strip()

    # Volume units
    if unit_lower in ['gallon', 'gal']:
        return 'GAL'
    elif unit_lower in ['quart', 'qt']:
        return 'QT'
    elif unit_lower in ['pint', 'pt']:
        return 'PT'
    elif unit_lower in ['cup', 'c']:
        return 'CUP'
    elif unit_lower in ['fluid ounce', 'fl oz', 'fl. oz']:
        return 'FL OZ'
    elif unit_lower in ['tablespoon', 'tbsp']:
        return 'TBSP'
    elif unit_lower in ['teaspoon', 'tsp']:
        return 'TSP'

    # Weight units
    elif unit_lower in ['pound', 'lb', 'lbs']:
        return 'LB'
    elif unit_lower in ['ounce', 'oz']:
        return 'OZ'
    elif unit_lower in ['kilogram', 'kg']:
        return 'KG'
    elif unit_lower in ['gram', 'g']:
        return 'G'

    # Count units
    elif unit_lower in ['each', 'ea', 'piece', 'pc', 'item', 'unit', 'whole']:
        return 'EA'

    # Return as-is if unknown (let user review)
    return unit.upper()


def normalize_quantity(
    quantity: float,
    unit: str,
    conn
) -> Tuple[float, str, Optional[int]]:
    """
    Normalize quantity to preferred units.

    Conversion logic:
    - Volume: Convert large volumes (gal, qt, pt, cup) to FL OZ
    - Weight: Convert pounds to ounces
    - Count: No conversion
    - Small units (tbsp, tsp): Keep as-is for readability

    Args:
        quantity: Original quantity
        unit: Original unit string
        conn: Database connection (to look up unit IDs)

    Returns:
        (normalized_quantity, normalized_unit, unit_id)

    Example:
        normalize_quantity(2.5, 'quart', conn)
        -> (80.0, 'FL OZ', 12)  # 2.5 quarts = 80 fl oz
    """

    unit_lower = unit.lower().strip()
    unit_type = get_unit_type(unit_lower)

    # Volume normalization
    if unit_type == 'volume':
        # Convert large volumes to fluid ounces
        if unit_lower in ['gallon', 'gal', 'quart', 'qt', 'pint', 'pt', 'cup', 'c']:
            fl_oz = quantity * VOLUME_CONVERSIONS[unit_lower]
            unit_id = get_unit_id_by_abbreviation('FL OZ', conn)
            return (fl_oz, 'FL OZ', unit_id)

        # Keep tablespoons and teaspoons as-is (more readable)
        elif unit_lower in ['tablespoon', 'tbsp']:
            unit_id = get_unit_id_by_abbreviation('TBSP', conn)
            return (quantity, 'TBSP', unit_id)
        elif unit_lower in ['teaspoon', 'tsp']:
            unit_id = get_unit_id_by_abbreviation('TSP', conn)
            return (quantity, 'TSP', unit_id)

        # Already in fluid ounces
        else:
            unit_id = get_unit_id_by_abbreviation('FL OZ', conn)
            return (quantity, 'FL OZ', unit_id)

    # Weight normalization
    elif unit_type == 'weight':
        # Convert pounds to ounces
        if unit_lower in ['pound', 'lb', 'lbs']:
            oz = quantity * 16
            unit_id = get_unit_id_by_abbreviation('OZ', conn)
            return (oz, 'OZ', unit_id)

        # Convert kilograms to ounces
        elif unit_lower in ['kilogram', 'kg']:
            oz = quantity * 35.274
            unit_id = get_unit_id_by_abbreviation('OZ', conn)
            return (oz, 'OZ', unit_id)

        # Convert grams to ounces if large quantity
        elif unit_lower in ['gram', 'g']:
            if quantity >= 100:  # 100g+ -> convert to oz
                oz = quantity * 0.035274
                unit_id = get_unit_id_by_abbreviation('OZ', conn)
                return (oz, 'OZ', unit_id)
            else:  # Keep small amounts in grams
                unit_id = get_unit_id_by_abbreviation('G', conn)
                return (quantity, 'G', unit_id)

        # Already in ounces
        else:
            unit_id = get_unit_id_by_abbreviation('OZ', conn)
            return (quantity, 'OZ', unit_id)

    # Count - no conversion
    elif unit_type == 'count':
        unit_id = get_unit_id_by_abbreviation('EA', conn)
        return (quantity, 'EA', unit_id)

    # Unknown unit - return as-is with normalized string
    else:
        normalized = normalize_unit_string(unit)
        unit_id = get_unit_id_by_abbreviation(normalized, conn)
        return (quantity, normalized, unit_id)


def get_unit_id_by_abbreviation(abbreviation: str, conn) -> Optional[int]:
    """
    Look up unit ID by abbreviation from database.

    Args:
        abbreviation: Unit abbreviation (e.g., 'OZ', 'LB', 'EA')
        conn: Database connection

    Returns:
        Unit ID or None if not found
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM units
        WHERE UPPER(abbreviation) = UPPER(%s)
        LIMIT 1
    """, (abbreviation,))

    result = cursor.fetchone()
    return result['id'] if result else None


def format_quantity_for_display(
    original_quantity: float,
    original_unit: str,
    normalized_quantity: float,
    normalized_unit: str
) -> dict:
    """
    Format quantity for UI display with both original and normalized values.

    Args:
        original_quantity: Original parsed quantity
        original_unit: Original parsed unit
        normalized_quantity: Normalized quantity
        normalized_unit: Normalized unit

    Returns:
        Dict with display strings

    Example:
        {
            'original': '2.5 quart',
            'normalized': '80 FL OZ',
            'display': '2.5 quart (80 FL OZ)'
        }
    """

    # Round quantities for display
    orig_qty = round(original_quantity, 2) if original_quantity % 1 else int(original_quantity)
    norm_qty = round(normalized_quantity, 2) if normalized_quantity % 1 else int(normalized_quantity)

    original_str = f"{orig_qty} {original_unit}"
    normalized_str = f"{norm_qty} {normalized_unit}"

    # If same, show only once
    if original_unit.upper() == normalized_unit.upper() and abs(original_quantity - normalized_quantity) < 0.01:
        display_str = original_str
    else:
        display_str = f"{original_str} ({normalized_str})"

    return {
        'original': original_str,
        'normalized': normalized_str,
        'display': display_str,
        'original_quantity': original_quantity,
        'original_unit': original_unit,
        'normalized_quantity': normalized_quantity,
        'normalized_unit': normalized_unit
    }
