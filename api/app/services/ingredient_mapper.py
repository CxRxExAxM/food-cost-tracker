"""
Ingredient mapping service for learning loop.

Records user corrections during recipe parsing and applies them to future parses.
Designed to work with current common_products table, future-proofed for
base_ingredients/ingredient_variants refactor (see Architecture Notes in Notion).

Three-tier data security model:
- Tenant-private: pricing, volumes (never shared)
- Anonymized shared: ingredient mappings (opt-in via is_shared)
- Fully public: taxonomy, unit normalizations
"""

from typing import Optional, Dict
from ..logger import get_logger

logger = get_logger(__name__)


def normalize_raw_name(text: str) -> str:
    """
    Normalize ingredient text for consistent lookup.

    Lowercase, strip whitespace, collapse multiple spaces.
    """
    return ' '.join(text.lower().strip().split())


def record_ingredient_mapping(
    organization_id: int,
    raw_name: str,
    common_product_id: int,
    user_id: int,
    conn,
    confidence_score: float = None,
    match_type: str = 'user_selected',
    is_shared: bool = False
) -> Optional[int]:
    """
    Record or update a user's ingredient mapping.

    Called when user manually selects a product during recipe review.
    Uses upsert to increment use_count if mapping already exists.

    Args:
        organization_id: Tenant ID
        raw_name: Original parsed ingredient text (e.g., "cilantro")
        common_product_id: Selected product ID
        user_id: Who made this selection
        conn: Database connection
        confidence_score: Optional confidence from the match
        match_type: How the mapping was created ('user_selected', 'accepted_suggestion', 'search')
        is_shared: Whether user opted in to share (default False)

    Returns:
        mapping_id or None if failed
    """
    if not raw_name or not common_product_id:
        return None

    normalized = normalize_raw_name(raw_name)

    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO ingredient_mappings (
                organization_id, raw_name, common_product_id,
                confidence_score, match_type, is_shared, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (organization_id, raw_name)
            DO UPDATE SET
                common_product_id = EXCLUDED.common_product_id,
                confidence_score = COALESCE(EXCLUDED.confidence_score, ingredient_mappings.confidence_score),
                match_type = EXCLUDED.match_type,
                use_count = ingredient_mappings.use_count + 1,
                updated_at = NOW()
            RETURNING id
        """, (
            organization_id, normalized, common_product_id,
            confidence_score, match_type, is_shared, user_id
        ))

        result = cursor.fetchone()
        mapping_id = result['id'] if result else None

        logger.debug(f"Recorded mapping: '{raw_name}' -> product {common_product_id} (org {organization_id})")

        return mapping_id

    except Exception as e:
        logger.error(f"Failed to record ingredient mapping: {e}")
        return None


def get_learned_mapping(
    organization_id: int,
    raw_name: str,
    conn
) -> Optional[Dict]:
    """
    Check if we have a learned mapping for this ingredient.

    Called during product matching to prioritize user corrections.

    Args:
        organization_id: Tenant ID
        raw_name: Parsed ingredient text to look up
        conn: Database connection

    Returns:
        Match dict with product info, or None if no mapping exists
    """
    if not raw_name:
        return None

    normalized = normalize_raw_name(raw_name)

    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                im.id as mapping_id,
                im.common_product_id,
                im.confidence_score as original_confidence,
                im.use_count,
                cp.common_name,
                cp.category,
                cp.subcategory
            FROM ingredient_mappings im
            JOIN common_products cp ON cp.id = im.common_product_id
            WHERE im.organization_id = %s
            AND LOWER(im.raw_name) = %s
            AND cp.is_active = 1
        """, (organization_id, normalized))

        result = cursor.fetchone()

        if result:
            # Higher confidence for frequently-used mappings
            # Base 0.95, up to 0.99 with repeated use
            confidence = min(0.99, 0.95 + (result['use_count'] * 0.01))

            return {
                'common_product_id': result['common_product_id'],
                'common_name': result['common_name'],
                'category': result['category'],
                'subcategory': result['subcategory'],
                'confidence': confidence,
                'exact_match': False,
                'match_type': 'learned',
                'use_count': result['use_count']
            }

        return None

    except Exception as e:
        logger.error(f"Failed to get learned mapping: {e}")
        return None


def get_shared_mapping(
    raw_name: str,
    conn,
    exclude_org_id: int = None
) -> Optional[Dict]:
    """
    Check cross-tenant shared mappings (future network effect).

    Only queries mappings where is_shared = TRUE.
    Used as fallback when organization has no mapping.

    Note: This feature requires user opt-in per the three-tier security model.
    Enterprise customers may be unable to opt in due to contract restrictions.

    Args:
        raw_name: Parsed ingredient text
        conn: Database connection
        exclude_org_id: Don't return mappings from this org (avoid self-match)

    Returns:
        Most-used shared mapping, or None
    """
    if not raw_name:
        return None

    normalized = normalize_raw_name(raw_name)

    cursor = conn.cursor()

    try:
        query = """
            SELECT
                im.common_product_id,
                cp.common_name,
                cp.category,
                SUM(im.use_count) as total_uses
            FROM ingredient_mappings im
            JOIN common_products cp ON cp.id = im.common_product_id
            WHERE LOWER(im.raw_name) = %s
            AND im.is_shared = TRUE
            AND cp.is_active = 1
        """
        params = [normalized]

        if exclude_org_id:
            query += " AND im.organization_id != %s"
            params.append(exclude_org_id)

        query += """
            GROUP BY im.common_product_id, cp.common_name, cp.category
            ORDER BY total_uses DESC
            LIMIT 1
        """

        cursor.execute(query, params)
        result = cursor.fetchone()

        # Require multiple confirmations for shared mappings
        if result and result['total_uses'] >= 3:
            return {
                'common_product_id': result['common_product_id'],
                'common_name': result['common_name'],
                'category': result['category'],
                'confidence': 0.85,  # Lower than org-specific learned
                'exact_match': False,
                'match_type': 'shared_learned',
                'network_uses': result['total_uses']
            }

        return None

    except Exception as e:
        logger.error(f"Failed to get shared mapping: {e}")
        return None


def delete_ingredient_mapping(
    organization_id: int,
    raw_name: str,
    conn
) -> bool:
    """
    Delete a learned mapping (if user wants to reset).

    Args:
        organization_id: Tenant ID
        raw_name: Ingredient text to unmmap
        conn: Database connection

    Returns:
        True if deleted, False otherwise
    """
    if not raw_name:
        return False

    normalized = normalize_raw_name(raw_name)

    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM ingredient_mappings
            WHERE organization_id = %s AND LOWER(raw_name) = %s
        """, (organization_id, normalized))

        return cursor.rowcount > 0

    except Exception as e:
        logger.error(f"Failed to delete ingredient mapping: {e}")
        return False
