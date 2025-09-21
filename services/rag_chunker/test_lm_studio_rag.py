#!/usr/bin/env python3
"""
Test RAG system with LM Studio embeddings
Simpler, focused tests to verify functionality
"""

import asyncio
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from retrieval_service import RetrievalService, RetrievalConfig
from embedding_service import get_embedding_service
import os

def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)

async def test_rag_with_lm_studio():
    """Test RAG system with new LM Studio embeddings"""

    # Database config
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    print_section("FREEDOM RAG System - LM Studio Embedding Test")

    # 1. Check embedding status
    print("\n1. Embedding Status:")
    conn = psycopg2.connect(**db_config)
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(dense_vector) as with_embeddings,
                array_length(dense_vector, 1) as dimensions
            FROM document_chunks
            GROUP BY dimensions
        """)
        result = cursor.fetchone()
        print(f"   Total chunks: {result['total']}")
        print(f"   With embeddings: {result['with_embeddings']}")
        print(f"   Dimensions: {result['dimensions']}")

    # 2. Test embedding service
    print("\n2. Embedding Service Test:")
    service = get_embedding_service()
    test_text = "How to configure Redis cache?"

    start = time.time()
    embedding = service.get_embedding(test_text)
    latency = (time.time() - start) * 1000

    print(f"   Generated embedding: {len(embedding)} dimensions")
    print(f"   Latency: {latency:.1f}ms")
    print(f"   Using service: {'LM Studio' if service.lm_studio_available else 'Fallback'}")

    # 3. Test retrieval
    print("\n3. Retrieval Tests:")
    retrieval_service = RetrievalService(db_config, mlx_endpoint='http://localhost:8000')

    test_queries = [
        "How to configure Redis caching?",
        "Docker container networking setup",
        "PostgreSQL optimization settings",
        "FastAPI authentication implementation"
    ]

    for query in test_queries:
        print(f"\n   Query: '{query}'")

        # Perform retrieval
        config = RetrievalConfig(
            top_k=5,
            use_reranking=False,  # Skip MLX reranking for now
            cache_results=False
        )

        result = await retrieval_service.retrieve(query, config)

        print(f"   Retrieved chunks: {len(result['chunks'])}")
        print(f"   Retrieval time: {result['retrieval_time_ms']}ms")

        if result['chunks']:
            top_chunk = result['chunks'][0]
            print(f"   Top match: {top_chunk['component_name']} ({top_chunk['technology_name']})")
            print(f"   Score: {top_chunk.get('score', 0):.3f}")
            print(f"   Preview: {top_chunk['chunk_text'][:150]}...")

    # 4. Performance comparison
    print_section("Performance Metrics")

    # Run 10 queries to get average
    total_time = 0
    queries_run = 0

    for i in range(10):
        query = f"test query {i} configuration"
        result = await retrieval_service.retrieve(
            query,
            RetrievalConfig(top_k=5, use_reranking=False, cache_results=False)
        )
        total_time += result['retrieval_time_ms']
        queries_run += 1

    avg_time = total_time / queries_run
    print(f"Average retrieval time: {avg_time:.1f}ms")
    print(f"Throughput: {1000/avg_time:.1f} queries/sec")

    # Get service statistics
    stats = service.get_statistics()
    print(f"\nEmbedding Service Stats:")
    print(f"  LM Studio calls: {stats['lm_studio_calls']}")
    print(f"  OpenAI calls: {stats['openai_calls']}")
    print(f"  Gemini calls: {stats['gemini_calls']}")
    print(f"  Average latency: {stats['average_latency_ms']:.1f}ms")

    print_section("✅ TEST COMPLETE")

    retrieval_service.close()
    conn.close()

if __name__ == "__main__":
    # Source environment
    os.system('source ../../.env 2>/dev/null || true')

    # Run tests
    asyncio.run(test_rag_with_lm_studio())