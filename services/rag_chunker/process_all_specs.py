#!/usr/bin/env python3
"""
Process all 702 specifications into RAG chunks
"""

import asyncio
import logging
from chunking_service import ChunkingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Process all specifications"""

    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    # Initialize without OpenAI for now (will use sparse vectors only)
    service = ChunkingService(db_config, openai_api_key=None)

    try:
        logger.info("Starting to process all 702 specifications...")
        chunks_created = await service.process_all_specifications(batch_size=50)
        logger.info(f"Successfully created {chunks_created} chunks from 702 specifications")

        # Show statistics
        with service.conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT specification_id) as specs,
                    COUNT(*) as chunks,
                    AVG(chunk_tokens) as avg_tokens
                FROM document_chunks
            """)
            stats = cursor.fetchone()

            logger.info(f"Statistics:")
            logger.info(f"  Specifications processed: {stats[0]}")
            logger.info(f"  Total chunks created: {stats[1]}")
            logger.info(f"  Average tokens per chunk: {stats[2]:.1f}")

    finally:
        service.close()

if __name__ == "__main__":
    asyncio.run(main())