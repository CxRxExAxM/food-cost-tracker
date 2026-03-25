"""
Unit normalization service for AI recipe parser.

Normalizes unit strings to standard abbreviations and looks up unit IDs.
Does NOT convert quantities - conversions happen at calculation time
using the base_conversions and product_conversions tables.
"""

from typing import Tuple, Optional


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
    Normalize unit string and look up unit ID.

    Does NOT convert quantities - keeps original values.
    Conversions happen at calculation time using base_conversions table.

    Args:
        quantity: Original quantity (returned unchanged)
        unit: Original unit string (normalized to standard abbreviation)
        conn: Database connection (to look up unit IDs)

    Returns:
        (quantity, normalized_unit, unit_id)

    Example:
        normalize_quantity(5, 'pound', conn)
        -> (5, 'LB', 3)  # Keeps 5 LB, looks up unit ID
    """
    # Normalize the unit string to standard abbreviation
    normalized_unit = normalize_unit_string(unit)

    # Look up unit ID from database
    unit_id = get_unit_id_by_abbreviation(normalized_unit, conn)

    # Return original quantity with normalized unit
    return (quantity, normalized_unit, unit_id)


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


