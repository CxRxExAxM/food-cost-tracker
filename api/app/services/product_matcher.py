"""
Product matching algorithm for AI recipe parser.

Matches parsed ingredient names to existing common products using
exact matching, fuzzy matching, and semantic similarity.
"""

from difflib import SequenceMatcher
from typing import List, Dict, Optional


def match_products(
    ingredient_name: str,
    organization_id: int,
    conn,
    max_results: int = 3
) -> List[Dict]:
    """
    Find matching common products using multi-strategy matching.

    Matching strategies (in order):
    1. Exact match (case-insensitive)
    2. Contains match (ingredient in product name or vice versa)
    3. Fuzzy match (similarity > 0.7)

    Args:
        ingredient_name: Parsed ingredient name from recipe
        organization_id: Organization ID to scope search
        conn: Database connection
        max_results: Maximum number of matches to return (default 3)

    Returns:
        List of matches sorted by confidence (0-1), max length 3

    Example:
        match_products("cucumber", 1, conn)
        -> [
            {
                'common_product_id': 123,
                'common_name': 'Cucumber',
                'category': 'Produce',
                'confidence': 1.0,
                'exact_match': True
            }
        ]
    """

    # Get all common products for organization
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, common_name, category, subcategory
        FROM common_products
        WHERE organization_id = %s AND is_active = 1
    """, (organization_id,))

    products = cursor.fetchall()

    if not products:
        return []

    matches = []
    ingredient_lower = ingredient_name.lower().strip()

    for product in products:
        product_name_lower = product['common_name'].lower().strip()

        # Strategy 1: Exact match (case-insensitive)
        if ingredient_lower == product_name_lower:
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'confidence': 1.0,
                'exact_match': True,
                'match_type': 'exact'
            })
            continue

        # Strategy 2: Contains match
        # Check if ingredient is in product name or vice versa
        if ingredient_lower in product_name_lower:
            confidence = len(ingredient_lower) / len(product_name_lower)
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'confidence': confidence,
                'exact_match': False,
                'match_type': 'contains_in_product'
            })
            continue

        if product_name_lower in ingredient_lower:
            confidence = len(product_name_lower) / len(ingredient_lower)
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'confidence': confidence,
                'exact_match': False,
                'match_type': 'product_in_ingredient'
            })
            continue

        # Strategy 3: Fuzzy match (similarity score)
        similarity = SequenceMatcher(None, ingredient_lower, product_name_lower).ratio()

        if similarity > 0.7:  # Only consider if reasonably similar
            matches.append({
                'common_product_id': product['id'],
                'common_name': product['common_name'],
                'category': product['category'],
                'subcategory': product['subcategory'],
                'confidence': similarity,
                'exact_match': False,
                'match_type': 'fuzzy'
            })

    # Sort by confidence (highest first), return top N
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    return matches[:max_results]


def get_best_match(
    ingredient_name: str,
    organization_id: int,
    conn
) -> Optional[Dict]:
    """
    Get single best match for ingredient.

    Only returns match if confidence >= 0.95 (very confident).
    Used for auto-selection in UI.

    Args:
        ingredient_name: Parsed ingredient name
        organization_id: Organization ID
        conn: Database connection

    Returns:
        Best match dict or None if not confident enough
    """

    matches = match_products(ingredient_name, organization_id, conn, max_results=1)

    if matches and matches[0]['confidence'] >= 0.95:
        return matches[0]

    return None


def search_products(
    search_term: str,
    organization_id: int,
    conn,
    limit: int = 20
) -> List[Dict]:
    """
    Search all common products for organization.

    Used in UI when user wants to search beyond top 3 suggestions.

    Args:
        search_term: User's search query
        organization_id: Organization ID
        conn: Database connection
        limit: Maximum results (default 20)

    Returns:
        List of matching products sorted by relevance
    """

    cursor = conn.cursor()

    # Use PostgreSQL's ILIKE for case-insensitive search
    cursor.execute("""
        SELECT
            id as common_product_id,
            common_name,
            category,
            subcategory
        FROM common_products
        WHERE organization_id = %s
        AND is_active = 1
        AND (
            common_name ILIKE %s
            OR category ILIKE %s
            OR subcategory ILIKE %s
        )
        ORDER BY
            CASE
                WHEN common_name ILIKE %s THEN 1  -- Exact match first
                WHEN common_name ILIKE %s THEN 2  -- Starts with
                ELSE 3  -- Contains
            END,
            common_name
        LIMIT %s
    """, (
        organization_id,
        f'%{search_term}%',
        f'%{search_term}%',
        f'%{search_term}%',
        search_term,
        f'{search_term}%',
        limit
    ))

    return cursor.fetchall()


def analyze_ingredient_name(ingredient_name: str) -> Dict:
    """
    Analyze ingredient name to extract potential modifiers.

    Helps improve matching by identifying prep notes, sizes, etc.

    Args:
        ingredient_name: Raw ingredient name

    Returns:
        Dict with cleaned name and potential prep notes

    Example:
        analyze_ingredient_name("cucumber, sliced")
        -> {
            'cleaned_name': 'cucumber',
            'prep_note': 'sliced',
            'modifiers': ['sliced']
        }
    """

    # Common prep terms that can be removed for better matching
    prep_terms = [
        'chopped', 'diced', 'sliced', 'minced', 'julienned',
        'peeled', 'seeded', 'crushed', 'grated', 'shredded',
        'fresh', 'frozen', 'dried', 'canned', 'whole',
        'halved', 'quartered', 'cubed', 'ground',
        'raw', 'cooked', 'blanched', 'toasted'
    ]

    cleaned_name = ingredient_name.lower().strip()
    found_modifiers = []

    # Extract prep notes (usually after comma or in parentheses)
    prep_note = None

    if ',' in cleaned_name:
        parts = cleaned_name.split(',')
        cleaned_name = parts[0].strip()
        prep_note = parts[1].strip()
        found_modifiers.append(prep_note)

    if '(' in cleaned_name and ')' in cleaned_name:
        start = cleaned_name.index('(')
        end = cleaned_name.index(')')
        prep_note = cleaned_name[start+1:end].strip()
        cleaned_name = cleaned_name[:start].strip()
        found_modifiers.append(prep_note)

    # Remove prep terms from name for better matching
    for term in prep_terms:
        if term in cleaned_name.split():
            found_modifiers.append(term)
            cleaned_name = cleaned_name.replace(term, '').strip()

    # Clean up double spaces
    cleaned_name = ' '.join(cleaned_name.split())

    return {
        'cleaned_name': cleaned_name,
        'prep_note': prep_note,
        'modifiers': found_modifiers,
        'original': ingredient_name
    }


def create_product_suggestion(
    ingredient_name: str,
    category_hint: Optional[str] = None
) -> Dict:
    """
    Create suggestion for new product creation.

    Analyzes ingredient name and suggests product attributes.

    Args:
        ingredient_name: Parsed ingredient name
        category_hint: Optional category hint from context

    Returns:
        Dict with suggested product attributes

    Example:
        create_product_suggestion("greek yogurt")
        -> {
            'common_name': 'Greek Yogurt',
            'suggested_category': 'Dairy',
            'suggested_subcategory': 'Yogurt'
        }
    """

    # Title case for product name
    cleaned = analyze_ingredient_name(ingredient_name)
    suggested_name = cleaned['cleaned_name'].title()

    # Category suggestions based on common ingredients
    category_keywords = {
        'Produce': ['lettuce', 'tomato', 'cucumber', 'onion', 'pepper', 'carrot',
                    'celery', 'spinach', 'kale', 'potato', 'garlic', 'herb'],
        'Dairy': ['milk', 'cream', 'cheese', 'yogurt', 'butter', 'sour cream'],
        'Meat': ['chicken', 'beef', 'pork', 'turkey', 'lamb', 'bacon', 'sausage'],
        'Seafood': ['fish', 'salmon', 'tuna', 'shrimp', 'cod', 'crab', 'lobster'],
        'Pantry': ['flour', 'sugar', 'salt', 'pepper', 'oil', 'vinegar', 'rice',
                   'pasta', 'sauce', 'spice', 'seasoning'],
        'Bakery': ['bread', 'bun', 'roll', 'tortilla', 'pita'],
    }

    suggested_category = category_hint or 'Pantry'  # Default
    name_lower = suggested_name.lower()

    for category, keywords in category_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            suggested_category = category
            break

    return {
        'common_name': suggested_name,
        'suggested_category': suggested_category,
        'suggested_subcategory': None,  # Let user fill in
        'prep_note': cleaned['prep_note'],
        'original_text': ingredient_name
    }
