"""
Embedding utilities for semantic search on common_products.

Uses Voyage AI's voyage-3.5-lite model for generating embeddings
and pgvector for similarity search.
"""
import os
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import voyageai

logger = logging.getLogger(__name__)

# Initialize Voyage client (uses VOYAGE_API_KEY env var automatically)
_client: Optional[voyageai.Client] = None

# Embedding configuration
EMBEDDING_MODEL = "voyage-3.5-lite"  # Fast, cheap, good for short text
EMBEDDING_DIMENSIONS = 1024  # voyage-3.5-lite default


def get_voyage_client() -> voyageai.Client:
    """Get or create Voyage AI client instance."""
    global _client
    if _client is None:
        api_key = os.getenv("VOYAGE_API_KEY")
        if not api_key:
            raise ValueError("VOYAGE_API_KEY environment variable not set")
        _client = voyageai.Client(api_key=api_key)
    return _client


def generate_embedding(text: str, input_type: str = "document") -> List[float]:
    """
    Generate an embedding vector for the given text.

    Args:
        text: The text to embed (e.g., ingredient name)
        input_type: "document" for stored items, "query" for search queries

    Returns:
        List of floats representing the embedding vector
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate embedding for empty text")

    client = get_voyage_client()
    result = client.embed(
        texts=[text.strip()],
        model=EMBEDDING_MODEL,
        input_type=input_type
    )
    return result.embeddings[0]


def format_embedding_for_postgres(embedding: List[float]) -> str:
    """
    Format embedding list as a PostgreSQL vector literal.

    Args:
        embedding: List of floats

    Returns:
        String in format '[0.1,0.2,0.3,...]' suitable for pgvector
    """
    return "[" + ",".join(str(x) for x in embedding) + "]"


def embed_common_product(cursor, product_id: int, common_name: str) -> bool:
    """
    Generate and store embedding for a single common_product.

    Args:
        cursor: Database cursor
        product_id: ID of the common_product
        common_name: Name to embed

    Returns:
        True if successful, False otherwise
    """
    try:
        embedding = generate_embedding(common_name, input_type="document")
        embedding_str = format_embedding_for_postgres(embedding)

        cursor.execute(
            "UPDATE common_products SET embedding = %s WHERE id = %s",
            (embedding_str, product_id)
        )
        return True
    except Exception as e:
        logger.error(f"Failed to embed common_product {product_id}: {e}")
        return False


def embed_all_common_products(cursor, batch_size: int = 100, delay_seconds: float = 0.5) -> Tuple[int, int]:
    """
    Backfill embeddings for all common_products that don't have one.

    Args:
        cursor: Database cursor
        batch_size: Number of products to process before logging progress
        delay_seconds: Delay between API calls to avoid rate limiting

    Returns:
        Tuple of (successful_count, failed_count)
    """
    # Get all products without embeddings
    cursor.execute("""
        SELECT id, common_name
        FROM common_products
        WHERE embedding IS NULL AND is_active = 1
        ORDER BY id
    """)
    products = cursor.fetchall()

    success_count = 0
    fail_count = 0

    for product in products:
        if embed_common_product(cursor, product['id'], product['common_name']):
            success_count += 1
        else:
            fail_count += 1

        # Log progress
        total = success_count + fail_count
        if total % batch_size == 0:
            logger.info(f"Embedded {total}/{len(products)} products ({success_count} success, {fail_count} failed)")

        # Rate limiting delay
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return success_count, fail_count


def search_similar_products(
    cursor,
    query_text: str,
    organization_id: Optional[int] = None,
    limit: int = 5,
    threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Find common_products similar to the query text using semantic search.

    Args:
        cursor: Database cursor
        query_text: Text to search for (e.g., "heavy cream")
        organization_id: Optional org filter (for multi-tenant isolation)
        limit: Maximum number of results to return
        threshold: Minimum similarity score (0-1, higher is more similar)

    Returns:
        List of dicts with id, common_name, category, similarity_score
    """
    # Generate embedding for the query (use "query" input_type for search)
    query_embedding = generate_embedding(query_text, input_type="query")
    embedding_str = format_embedding_for_postgres(query_embedding)

    # Debug: log first few embedding values to verify consistency
    logger.info(f"[EMBED] query='{query_text}' first_5_values={query_embedding[:5]}")

    # pgvector uses cosine distance, so we convert to similarity (1 - distance)
    # Lower distance = more similar, so we order by distance ascending
    # Filter by organization_id for multi-tenant isolation
    if organization_id is not None:
        cursor.execute("""
            SELECT
                id,
                common_name,
                category,
                subcategory,
                preferred_unit_id,
                1 - (embedding <=> %s) as similarity_score
            FROM common_products
            WHERE embedding IS NOT NULL
              AND is_active = 1
              AND organization_id = %s
              AND 1 - (embedding <=> %s) > %s
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (embedding_str, organization_id, embedding_str, threshold, embedding_str, limit))
    else:
        cursor.execute("""
            SELECT
                id,
                common_name,
                category,
                subcategory,
                preferred_unit_id,
                1 - (embedding <=> %s) as similarity_score
            FROM common_products
            WHERE embedding IS NOT NULL
              AND is_active = 1
              AND 1 - (embedding <=> %s) > %s
            ORDER BY embedding <=> %s
            LIMIT %s
        """, (embedding_str, embedding_str, threshold, embedding_str, limit))

    results = cursor.fetchall()
    return [dict(row) for row in results]


def get_best_match(
    cursor,
    query_text: str,
    organization_id: Optional[int] = None,
    confidence_threshold: float = 0.7
) -> Optional[Dict[str, Any]]:
    """
    Get the single best matching common_product if confidence is high enough.

    Args:
        cursor: Database cursor
        query_text: Text to match
        organization_id: Optional org filter
        confidence_threshold: Minimum similarity to consider a match

    Returns:
        Best matching product dict or None if no confident match
    """
    results = search_similar_products(
        cursor,
        query_text,
        organization_id=organization_id,
        limit=1,
        threshold=confidence_threshold
    )
    return results[0] if results else None
