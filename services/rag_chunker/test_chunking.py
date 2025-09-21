#!/usr/bin/env python3
"""
Test script for RAG chunking service
Tests chunking and indexing of 702 specifications
"""

import os
import sys
import asyncio
import logging
from chunking_service import ChunkingService, ChunkConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_chunking():
    """Test chunking functionality on a subset of specifications"""

    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    # Initialize service (no OpenAI key for now, just testing structure)
    service = ChunkingService(db_config, openai_api_key=None)

    try:
        # Get a sample of specifications
        with service.conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    s.id, s.technology_id, s.version, s.component_type,
                    s.component_name, s.specification, s.source_type,
                    t.name as technology_name
                FROM specifications s
                LEFT JOIN technologies t ON s.technology_id = t.id
                ORDER BY s.extracted_at DESC
                LIMIT 5
            """)

            specs = cursor.fetchall()

            logger.info(f"Testing with {len(specs)} specifications")

            for spec in specs:
                logger.info(f"\nProcessing: {spec[4]} ({spec[3]})")

                # Convert tuple to dict for processing
                spec_dict = {
                    'id': spec[0],
                    'technology_id': spec[1],
                    'version': spec[2],
                    'component_type': spec[3],
                    'component_name': spec[4],
                    'specification': spec[5],
                    'source_type': spec[6],
                    'technology_name': spec[7]
                }

                # Process specification
                chunks = service.process_specification(spec_dict)

                logger.info(f"  Created {len(chunks)} chunks")

                # Index chunks (without embeddings for now)
                indexed = await service.index_chunks(chunks)
                logger.info(f"  Indexed {indexed} chunks successfully")

        # Check total chunks created
        with service.conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            total = cursor.fetchone()[0]
            logger.info(f"\nTotal chunks in database: {total}")

            # Show sample chunk
            cursor.execute("""
                SELECT chunk_text, chunk_tokens, component_name
                FROM document_chunks
                LIMIT 1
            """)
            sample = cursor.fetchone()
            if sample:
                logger.info(f"\nSample chunk:")
                logger.info(f"  Component: {sample[2]}")
                logger.info(f"  Tokens: {sample[1]}")
                logger.info(f"  Text preview: {sample[0][:200]}...")

    except Exception as e:
        logger.error(f"Error during testing: {e}")
        raise

    finally:
        service.close()

if __name__ == "__main__":
    asyncio.run(test_chunking())