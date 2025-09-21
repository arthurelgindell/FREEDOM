#!/usr/bin/env python3
"""
Migration script to regenerate all embeddings using LM Studio
Much faster (16x) and free compared to OpenAI
"""

import os
import sys
import time
import asyncio
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from embedding_service import get_embedding_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_embeddings(batch_size: int = 100, force_regenerate: bool = False):
    """
    Migrate all embeddings to use LM Studio

    Args:
        batch_size: Number of embeddings to process in batch
        force_regenerate: If True, regenerate even existing embeddings
    """

    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'techknowledge'),
        'user': os.getenv('DB_USER', 'arthurdell')
    }

    # Get embedding service
    embedding_service = get_embedding_service()

    # Test service first
    logger.info("Testing embedding service...")
    test_results = embedding_service.test_services()

    if not test_results.get('lm_studio', {}).get('success'):
        logger.error("❌ LM Studio is not available! Please ensure it's running.")
        return

    logger.info("✅ LM Studio is ready!")
    logger.info(f"   Model: {test_results['lm_studio']['model']}")
    logger.info(f"   Dimensions: {test_results['lm_studio']['dimensions']}")
    logger.info(f"   Latency: {test_results['lm_studio']['latency_ms']:.1f}ms")

    # Connect to database
    conn = psycopg2.connect(**db_config)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Count chunks
            if force_regenerate:
                cursor.execute("SELECT COUNT(*) FROM document_chunks")
                condition = ""
            else:
                cursor.execute("SELECT COUNT(*) FROM document_chunks WHERE dense_vector IS NULL")
                condition = "WHERE dense_vector IS NULL"

            total_chunks = cursor.fetchone()['count']

            if total_chunks == 0:
                logger.info("✅ All chunks already have embeddings!")
                return

            logger.info(f"Found {total_chunks} chunks to process")

            # Estimate time
            estimated_time = total_chunks / 76.6  # Based on benchmark: 76.6 embeddings/sec
            logger.info(f"Estimated time: {estimated_time:.1f} seconds ({estimated_time/60:.1f} minutes)")

            # Process in batches
            offset = 0
            processed = 0
            errors = 0
            start_time = time.time()

            while offset < total_chunks:
                # Get batch
                cursor.execute(f"""
                    SELECT id, chunk_text
                    FROM document_chunks
                    {condition}
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))

                chunks = cursor.fetchall()

                if not chunks:
                    break

                batch_start = time.time()
                batch_processed = 0

                for chunk in chunks:
                    try:
                        # Generate embedding
                        embedding = embedding_service.get_embedding(chunk['chunk_text'])

                        # Update database
                        cursor.execute("""
                            UPDATE document_chunks
                            SET dense_vector = %s
                            WHERE id = %s
                        """, (embedding, chunk['id']))

                        batch_processed += 1
                        processed += 1

                    except Exception as e:
                        logger.error(f"Error processing chunk {chunk['id']}: {e}")
                        errors += 1

                # Commit batch
                conn.commit()

                batch_time = time.time() - batch_start
                batch_rate = batch_processed / batch_time if batch_time > 0 else 0

                logger.info(
                    f"Batch {offset//batch_size + 1}: "
                    f"Processed {batch_processed}/{len(chunks)} chunks "
                    f"in {batch_time:.1f}s ({batch_rate:.1f} chunks/sec)"
                )

                # Update progress
                progress = (processed / total_chunks) * 100
                elapsed = time.time() - start_time

                if processed > 0:
                    rate = processed / elapsed
                    remaining = (total_chunks - processed) / rate

                    logger.info(
                        f"Progress: {processed}/{total_chunks} ({progress:.1f}%) "
                        f"| Rate: {rate:.1f} chunks/sec "
                        f"| ETA: {remaining/60:.1f} min"
                    )

                offset += batch_size

            # Final statistics
            total_time = time.time() - start_time
            final_rate = processed / total_time if total_time > 0 else 0

            logger.info("="*60)
            logger.info("MIGRATION COMPLETE")
            logger.info("="*60)
            logger.info(f"✅ Successfully processed: {processed} chunks")
            logger.info(f"❌ Errors: {errors}")
            logger.info(f"⏱️ Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
            logger.info(f"⚡ Average rate: {final_rate:.1f} chunks/second")

            # Get service statistics
            stats = embedding_service.get_statistics()
            logger.info(f"\nService Statistics:")
            logger.info(f"  LM Studio calls: {stats['lm_studio_calls']}")
            logger.info(f"  OpenAI calls: {stats['openai_calls']}")
            logger.info(f"  Gemini calls: {stats['gemini_calls']}")
            logger.info(f"  Average latency: {stats['average_latency_ms']:.1f}ms")
            logger.info(f"  Estimated cost saved: ${stats['estimated_cost_saved']:.2f}")

            # Rebuild index if needed
            if processed > 0:
                logger.info("\nRebuilding vector index...")
                cursor.execute("REINDEX INDEX IF EXISTS idx_chunks_dense_vector;")
                conn.commit()
                logger.info("✅ Index rebuilt")

    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate embeddings to LM Studio")
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of chunks to process in each batch (default: 100)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Regenerate all embeddings, even if they already exist'
    )

    args = parser.parse_args()

    logger.info("="*60)
    logger.info("LM STUDIO EMBEDDING MIGRATION")
    logger.info("="*60)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info(f"Force regenerate: {args.force}")
    logger.info("="*60)

    # Source environment
    os.system('source /Volumes/DATA/FREEDOM/.env')

    # Run migration
    asyncio.run(migrate_embeddings(
        batch_size=args.batch_size,
        force_regenerate=args.force
    ))