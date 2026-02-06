"""
Database query helper utilities.

Shared functions to reduce code duplication across routers.
"""
from typing import List, Dict, Any, Optional, Tuple


def build_dynamic_update(
    table: str,
    record_id: int,
    updates: Dict[str, Any],
    allowed_fields: List[str],
    id_column: str = "id"
) -> Tuple[Optional[str], Optional[List]]:
    """
    Build a dynamic UPDATE query safely.

    Only includes fields that are in the allowed_fields list.

    Args:
        table: Table name to update
        record_id: ID of the record to update
        updates: Dictionary of field names to new values
        allowed_fields: List of field names that are allowed to be updated
        id_column: Name of the ID column (default: "id")

    Returns:
        Tuple of (query_string, params_list) or (None, None) if no valid fields

    Example:
        query, params = build_dynamic_update(
            "recipes",
            recipe_id,
            {"name": "New Name", "category": "Desserts"},
            ["name", "category", "description"]
        )
        if query:
            cursor.execute(query, params)
    """
    update_fields = []
    params = []

    for field, value in updates.items():
        if field in allowed_fields:
            update_fields.append(f"{field} = %s")
            params.append(value)

    if not update_fields:
        return None, None

    params.append(record_id)
    query = f"UPDATE {table} SET {', '.join(update_fields)} WHERE {id_column} = %s"
    return query, params


def group_by_key(rows: List[Dict], key: str) -> Dict[Any, List[Dict]]:
    """
    Group a list of dictionaries by a key value.

    Useful for converting flat query results into nested structures
    without N+1 queries.

    Args:
        rows: List of dictionaries (e.g., from cursor.fetchall())
        key: Key name to group by

    Returns:
        Dictionary mapping key values to lists of matching rows

    Example:
        # Fetch all prep items for multiple menu items in one query
        cursor.execute("SELECT * FROM prep_items WHERE menu_item_id IN (...)")
        all_prep_items = cursor.fetchall()

        # Group by menu_item_id
        prep_by_item = group_by_key(all_prep_items, "menu_item_id")

        # Now assign to each menu item
        for item in menu_items:
            item["prep_items"] = prep_by_item.get(item["id"], [])
    """
    grouped = {}
    for row in rows:
        key_value = row.get(key)
        if key_value not in grouped:
            grouped[key_value] = []
        grouped[key_value].append(row)
    return grouped
