#!/usr/bin/env python3
"""
Test RAG retrieval functionality
"""

import asyncio
import logging
from retrieval_service import RetrievalService, RetrievalConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Test retrieval with various queries"""

    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    service = RetrievalService(db_config)

    test_queries = [
        "How do I configure Docker containers?",
        "Redis cache configuration",
        "PostgreSQL optimization settings",
        "FastAPI authentication",
        "React component lifecycle"
    ]

    for query in test_queries:
        logger.info(f"\n{'='*60}")
        logger.info(f"Query: {query}")
        logger.info('='*60)

        # Configure retrieval
        config = RetrievalConfig(
            top_k=5,
            use_reranking=False,  # MLX not running
            hybrid_alpha=0.3  # More weight on sparse search since no embeddings
        )

        # Perform retrieval
        result = await service.retrieve(query, config)

        logger.info(f"Retrieved {len(result['chunks'])} chunks")
        logger.info(f"Retrieval time: {result['retrieval_time_ms']}ms")

        # Show top result
        if result['chunks']:
            top_chunk = result['chunks'][0]
            logger.info(f"\nTop result:")
            logger.info(f"  Component: {top_chunk['component_name']}")
            logger.info(f"  Technology: {top_chunk.get('technology_name', 'N/A')}")
            logger.info(f"  Score: {top_chunk.get('score', 0):.3f}")
            logger.info(f"  Text preview: {top_chunk['chunk_text'][:200]}...")

    service.close()

if __name__ == "__main__":
    asyncio.run(main())