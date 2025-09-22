#!/usr/bin/env python3
"""
Process all 702 specifications into RAG chunks with embeddings
Uses LM Studio for fast local embeddings (768 dimensions)
"""

import asyncio
import logging
import time
from typing import List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from chunking_service import ChunkingService
from embedding_service import get_embedding_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def process_and_embed_all():
    """Process all specifications and generate embeddings"""

    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'  # Using local user without password
    }

    # Initialize services
    chunking_service = ChunkingService(db_config, openai_api_key=None)
    embedding_service = get_embedding_service()

    # Check LM Studio availability
    if not embedding_service.lm_studio_available:
        logger.error("LM Studio is not available! Please ensure it's running with an embedding model.")
        return 0

    conn = psycopg2.connect(**db_config)

    try:
        logger.info("Starting to process all specifications...")

        # Get all specifications
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT
                    s.id, s.component_type, s.version,
                    s.component_name, s.specification, s.source_type,
                    t.name as technology_name
                FROM specifications s
                LEFT JOIN technologies t ON s.technology_id = t.id
                ORDER BY LENGTH(s.specification::text) DESC
            """)
            specifications = cursor.fetchall()

        logger.info(f"Found {len(specifications)} specifications to process")

        total_chunks = 0
        total_embeddings = 0
        start_time = time.time()

        for i, spec in enumerate(specifications):
            try:
                # Process specification into chunks
                chunks = chunking_service.process_specification(spec)

                if not chunks:
                    continue

                # Save chunks with embeddings
                with conn.cursor() as cursor:
                    for chunk in chunks:
                        # Generate embedding for chunk
                        try:
                            embedding = embedding_service.get_embedding(chunk['chunk_text'])

                            # Insert chunk with embedding
                            cursor.execute("""
                                INSERT INTO document_chunks (
                                    specification_id, chunk_index, chunk_text, chunk_tokens,
                                    prev_chunk_overlap, next_chunk_overlap,
                                    dense_vector, sparse_vector,
                                    technology_name, component_type, component_name,
                                    version, source_type
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (content_hash) DO NOTHING
                                RETURNING id
                            """, (
                                chunk['specification_id'],
                                chunk['chunk_index'],
                                chunk['chunk_text'],
                                chunk['chunk_tokens'],
                                chunk.get('prev_chunk_overlap'),
                                chunk.get('next_chunk_overlap'),
                                embedding,  # 768-dimensional vector from LM Studio
                                chunk['sparse_vector'],
                                chunk.get('technology_name'),
                                chunk['component_type'],
                                chunk['component_name'],
                                chunk['version'],
                                chunk['source_type']
                            ))

                            if cursor.fetchone():
                                total_chunks += 1
                                total_embeddings += 1

                        except Exception as e:
                            logger.error(f"Failed to generate embedding: {e}")
                            # Still save chunk without embedding
                            cursor.execute("""
                                INSERT INTO document_chunks (
                                    specification_id, chunk_index, chunk_text, chunk_tokens,
                                    prev_chunk_overlap, next_chunk_overlap,
                                    sparse_vector,
                                    technology_name, component_type, component_name,
                                    version, source_type
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (content_hash) DO NOTHING
                                RETURNING id
                            """, (
                                chunk['specification_id'],
                                chunk['chunk_index'],
                                chunk['chunk_text'],
                                chunk['chunk_tokens'],
                                chunk.get('prev_chunk_overlap'),
                                chunk.get('next_chunk_overlap'),
                                chunk['sparse_vector'],
                                chunk.get('technology_name'),
                                chunk['component_type'],
                                chunk['component_name'],
                                chunk['version'],
                                chunk['source_type']
                            ))

                            if cursor.fetchone():
                                total_chunks += 1

                conn.commit()

                # Progress report every 10 specifications
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = total_embeddings / elapsed if elapsed > 0 else 0
                    logger.info(f"Processed {i+1}/{len(specifications)} specs, "
                               f"created {total_chunks} chunks, "
                               f"{total_embeddings} embeddings "
                               f"({rate:.1f} embeddings/sec)")

            except Exception as e:
                logger.error(f"Failed to process specification {spec['component_name']}: {e}")
                conn.rollback()

        # Final statistics
        elapsed = time.time() - start_time

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT specification_id) as specs,
                    COUNT(*) as chunks,
                    COUNT(dense_vector) as embeddings,
                    AVG(chunk_tokens) as avg_tokens
                FROM document_chunks
            """)
            stats = cursor.fetchone()

        logger.info("="*60)
        logger.info("PROCESSING COMPLETE")
        logger.info("="*60)
        logger.info(f"Specifications processed: {stats[0]}")
        logger.info(f"Total chunks created: {stats[1]}")
        logger.info(f"Embeddings generated: {stats[2]}")
        logger.info(f"Average tokens per chunk: {stats[3]:.1f}" if stats[3] else "N/A")
        logger.info(f"Processing time: {elapsed:.1f} seconds")
        logger.info(f"Embedding rate: {total_embeddings/elapsed:.1f} embeddings/sec" if elapsed > 0 else "N/A")
        logger.info("="*60)

        return total_chunks

    finally:
        chunking_service.close()
        conn.close()

if __name__ == "__main__":
    asyncio.run(process_and_embed_all())