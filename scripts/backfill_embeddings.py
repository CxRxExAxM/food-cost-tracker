#!/usr/bin/env python3
"""
Backfill embeddings for all common_products.

Run from project root:
    python scripts/backfill_embeddings.py

Options:
    --delay SECONDS  Delay between API calls (default: 0.5)
    --batch SIZE     Log progress every N products (default: 50)

Requires:
    - VOYAGE_API_KEY environment variable
    - DATABASE_URL environment variable (or local SQLite fallback)
"""
import os
import sys
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.app.database import get_db
from api.app.utils.embeddings import embed_all_common_products
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Backfill embeddings for common_products')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between API calls in seconds (default: 0.5)')
    parser.add_argument('--batch', type=int, default=50, help='Log progress every N products (default: 50)')
    args = parser.parse_args()

    # Check for API key
    if not os.getenv("VOYAGE_API_KEY"):
        logger.error("VOYAGE_API_KEY environment variable not set")
        sys.exit(1)

    logger.info("Starting embedding backfill for common_products...")
    logger.info(f"Rate limit delay: {args.delay}s between calls")

    with get_db() as conn:
        cursor = conn.cursor()

        # Check how many need embedding
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(embedding) as with_embedding
            FROM common_products
            WHERE is_active = 1
        """)
        stats = cursor.fetchone()
        total = stats['total']
        existing = stats['with_embedding']
        remaining = total - existing

        logger.info(f"Found {total} active common_products")
        logger.info(f"  - Already embedded: {existing}")
        logger.info(f"  - Need embedding: {remaining}")

        if remaining == 0:
            logger.info("All products already have embeddings. Nothing to do.")
            return

        # Estimate time
        est_minutes = (remaining * args.delay) / 60
        logger.info(f"Estimated time: ~{est_minutes:.1f} minutes at {args.delay}s delay")
        logger.info("Starting backfill...")

        # Run backfill
        success, failed = embed_all_common_products(
            cursor,
            batch_size=args.batch,
            delay_seconds=args.delay
        )
        conn.commit()

        logger.info(f"Backfill complete!")
        logger.info(f"  - Succeeded: {success}")
        logger.info(f"  - Failed: {failed}")


if __name__ == "__main__":
    main()
