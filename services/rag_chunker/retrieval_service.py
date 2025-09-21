#!/usr/bin/env python3
"""
RAG Retrieval Service for FREEDOM Platform
Hybrid retrieval using dense + sparse vectors with MLX reranking
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import time

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import numpy as np
from openai import OpenAI
import requests
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RetrievalConfig:
    """Configuration for retrieval strategy"""
    top_k: int = 10                    # Number of chunks to retrieve
    rerank_top_k: int = 5              # Number of chunks after reranking
    hybrid_alpha: float = 0.7          # Balance between dense and sparse (0-1)
    similarity_threshold: float = 0.6   # Minimum similarity score
    use_reranking: bool = True         # Use MLX for reranking
    context_window: int = 4096         # Maximum context size in tokens
    cache_results: bool = True          # Cache frequently accessed queries

class RetrievalService:
    """Service for retrieving relevant chunks"""

    def __init__(self, db_config: Dict[str, Any],
                 openai_api_key: Optional[str] = None,
                 mlx_endpoint: str = "http://localhost:8000"):
        self.db_config = db_config
        self.mlx_endpoint = mlx_endpoint
        self.openai_client = None
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")

        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)

        # Database connection
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False

    async def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for search query"""
        if not self.openai_client:
            return None

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=query,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return None

    def extract_query_keywords(self, query: str) -> Dict[str, float]:
        """Extract keywords from query for sparse search"""
        import re

        # Tokenize and normalize
        words = re.findall(r'\b\w+\b', query.lower())

        # Calculate importance weights
        keyword_weights = {}
        total_words = len(words)

        for i, word in enumerate(words):
            # Give higher weight to words appearing early in query
            position_weight = 1.0 - (i / total_words) * 0.3

            # Boost technical terms
            if any(char.isdigit() for char in word):
                position_weight *= 1.2
            if word.isupper():
                position_weight *= 1.1

            keyword_weights[word] = keyword_weights.get(word, 0) + position_weight

        # Normalize weights
        max_weight = max(keyword_weights.values()) if keyword_weights else 1
        return {k: v/max_weight for k, v in keyword_weights.items()}

    async def dense_search(self, query_embedding: List[float],
                          top_k: int, filters: Dict = None) -> List[Dict]:
        """Perform dense vector similarity search"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Build filter clause
            filter_clause = ""
            filter_params = []

            if filters:
                conditions = []
                if 'technology' in filters:
                    conditions.append("technology_name = %s")
                    filter_params.append(filters['technology'])
                if 'component_type' in filters:
                    conditions.append("component_type = %s")
                    filter_params.append(filters['component_type'])
                if 'source_type' in filters:
                    conditions.append("source_type = %s")
                    filter_params.append(filters['source_type'])

                if conditions:
                    filter_clause = "WHERE " + " AND ".join(conditions)

            # Cosine similarity search
            query = f"""
                SELECT
                    id, chunk_text, chunk_index, specification_id,
                    technology_name, component_type, component_name,
                    version, source_type,
                    1 - (dense_vector <=> %s::vector) AS similarity
                FROM document_chunks
                {filter_clause}
                WHERE dense_vector IS NOT NULL
                ORDER BY dense_vector <=> %s::vector
                LIMIT %s
            """

            params = [query_embedding] + filter_params + [query_embedding, top_k]
            cursor.execute(query, params)

            return cursor.fetchall()

    async def sparse_search(self, keywords: Dict[str, float],
                           top_k: int, filters: Dict = None) -> List[Dict]:
        """Perform sparse keyword search using BM25"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Build filter clause
            filter_clause = ""
            filter_params = []

            if filters:
                conditions = []
                if 'technology' in filters:
                    conditions.append("technology_name = %s")
                    filter_params.append(filters['technology'])
                if 'component_type' in filters:
                    conditions.append("component_type = %s")
                    filter_params.append(filters['component_type'])

                if conditions:
                    filter_clause = "AND " + " AND ".join(conditions)

            # Full-text search with ranking
            # Handle single vs multiple keywords
            if len(keywords) == 1:
                search_terms = list(keywords.keys())[0]
            else:
                search_terms = ' | '.join(keywords.keys())

            query = f"""
                SELECT
                    id, chunk_text, chunk_index, specification_id,
                    technology_name, component_type, component_name,
                    version, source_type,
                    ts_rank_cd(
                        to_tsvector('english', LOWER(chunk_text)),
                        to_tsquery('english', %s)
                    ) AS similarity
                FROM document_chunks
                WHERE to_tsvector('english', LOWER(chunk_text)) @@ to_tsquery('english', %s)
                {filter_clause}
                ORDER BY similarity DESC
                LIMIT %s
            """

            params = [search_terms.lower(), search_terms.lower()] + filter_params + [top_k]
            cursor.execute(query, params)

            return cursor.fetchall()

    async def hybrid_search(self, query: str, config: RetrievalConfig,
                           filters: Dict = None) -> List[Dict]:
        """Perform hybrid search combining dense and sparse retrieval"""
        chunks_scores = {}

        # Generate query representations
        query_embedding = await self.generate_query_embedding(query)
        query_keywords = self.extract_query_keywords(query)

        # Perform dense search if embedding available
        if query_embedding:
            dense_results = await self.dense_search(
                query_embedding, config.top_k * 2, filters
            )

            for result in dense_results:
                chunk_id = result['id']
                dense_score = result['similarity']

                if chunk_id not in chunks_scores:
                    chunks_scores[chunk_id] = {
                        'chunk': result,
                        'dense_score': 0,
                        'sparse_score': 0
                    }

                chunks_scores[chunk_id]['dense_score'] = dense_score

        # Perform sparse search
        if query_keywords:
            sparse_results = await self.sparse_search(
                query_keywords, config.top_k * 2, filters
            )

            for result in sparse_results:
                chunk_id = result['id']
                sparse_score = result['similarity']

                if chunk_id not in chunks_scores:
                    chunks_scores[chunk_id] = {
                        'chunk': result,
                        'dense_score': 0,
                        'sparse_score': 0
                    }

                chunks_scores[chunk_id]['sparse_score'] = sparse_score
                chunks_scores[chunk_id]['chunk'] = result

        # Calculate hybrid scores
        for chunk_id, scores in chunks_scores.items():
            # Normalize scores to 0-1 range
            dense_norm = min(1.0, scores['dense_score'])
            sparse_norm = min(1.0, scores['sparse_score'] * 10)  # Scale sparse scores

            # Hybrid score calculation
            hybrid_score = (config.hybrid_alpha * dense_norm +
                          (1 - config.hybrid_alpha) * sparse_norm)

            scores['hybrid_score'] = hybrid_score

        # Sort by hybrid score
        sorted_chunks = sorted(
            chunks_scores.values(),
            key=lambda x: x['hybrid_score'],
            reverse=True
        )

        # Filter by threshold and return top-k
        filtered_chunks = [
            {**item['chunk'], 'score': item['hybrid_score']}
            for item in sorted_chunks
            if item['hybrid_score'] >= config.similarity_threshold
        ][:config.top_k]

        return filtered_chunks

    async def rerank_with_mlx(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """Rerank chunks using MLX cross-encoder model"""
        try:
            # Prepare reranking request
            rerank_data = {
                'query': query,
                'documents': [chunk['chunk_text'] for chunk in chunks],
                'model': 'cross-encoder'  # Use cross-encoder for reranking
            }

            # Call MLX reranking endpoint
            response = requests.post(
                f"{self.mlx_endpoint}/rerank",
                json=rerank_data,
                timeout=10
            )

            if response.status_code == 200:
                scores = response.json()['scores']

                # Update chunks with rerank scores
                for i, chunk in enumerate(chunks):
                    chunk['rerank_score'] = scores[i]

                # Sort by rerank score
                chunks.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)

                logger.info(f"Successfully reranked {len(chunks)} chunks")

            else:
                logger.warning(f"MLX reranking failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Error during reranking: {e}")

        return chunks

    def get_chunk_context(self, chunk_id: str) -> Dict:
        """Get surrounding context for a chunk"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get the chunk and its neighbors
            cursor.execute("""
                SELECT
                    c1.id, c1.chunk_text, c1.chunk_index,
                    c1.prev_chunk_overlap, c1.next_chunk_overlap,
                    c2.chunk_text as prev_chunk,
                    c3.chunk_text as next_chunk
                FROM document_chunks c1
                LEFT JOIN document_chunks c2 ON
                    c2.specification_id = c1.specification_id AND
                    c2.chunk_index = c1.chunk_index - 1
                LEFT JOIN document_chunks c3 ON
                    c3.specification_id = c1.specification_id AND
                    c3.chunk_index = c1.chunk_index + 1
                WHERE c1.id = %s
            """, (chunk_id,))

            return cursor.fetchone()

    def assemble_context(self, chunks: List[Dict],
                        config: RetrievalConfig) -> str:
        """Assemble retrieved chunks into coherent context"""
        context_parts = []
        total_tokens = 0

        # Group chunks by specification
        spec_chunks = {}
        for chunk in chunks:
            spec_id = chunk['specification_id']
            if spec_id not in spec_chunks:
                spec_chunks[spec_id] = []
            spec_chunks[spec_id].append(chunk)

        # Sort chunks within each specification by index
        for spec_id, spec_chunk_list in spec_chunks.items():
            spec_chunk_list.sort(key=lambda x: x['chunk_index'])

        # Assemble context with proper formatting
        for spec_id, spec_chunk_list in spec_chunks.items():
            if spec_chunk_list:
                first_chunk = spec_chunk_list[0]

                # Add specification header
                header = f"\n## {first_chunk['component_name']} ({first_chunk['technology_name']})\n"
                header += f"Type: {first_chunk['component_type']} | Version: {first_chunk['version']}\n\n"

                context_parts.append(header)
                total_tokens += len(self.tokenizer.encode(header))

                # Add chunks with deduplication of overlaps
                prev_text = ""
                for chunk in spec_chunk_list:
                    # Remove overlap with previous chunk
                    chunk_text = chunk['chunk_text']
                    if chunk.get('prev_chunk_overlap') and prev_text.endswith(chunk['prev_chunk_overlap']):
                        chunk_text = chunk_text[len(chunk['prev_chunk_overlap']):]

                    chunk_tokens = len(self.tokenizer.encode(chunk_text))

                    # Check if we exceed context window
                    if total_tokens + chunk_tokens > config.context_window:
                        break

                    context_parts.append(chunk_text)
                    total_tokens += chunk_tokens
                    prev_text = chunk_text

                context_parts.append("\n")

        return "".join(context_parts)

    async def retrieve(self, query: str,
                      config: Optional[RetrievalConfig] = None,
                      filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Main retrieval method with caching and logging"""
        if config is None:
            config = RetrievalConfig()

        start_time = time.time()

        # Check cache if enabled
        if config.cache_results:
            cache_key = hashlib.md5(f"{query}{filters}".encode()).hexdigest()

            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT context_chunks, embedding_vector
                    FROM rag_context_cache
                    WHERE query_hash = %s AND expires_at > NOW()
                """, (cache_key,))

                cached = cursor.fetchone()
                if cached:
                    logger.info(f"Cache hit for query: {query[:50]}...")

                    # Update cache statistics
                    cursor.execute("""
                        UPDATE rag_context_cache
                        SET hit_count = hit_count + 1,
                            last_accessed = NOW()
                        WHERE query_hash = %s
                    """, (cache_key,))
                    self.conn.commit()

                    return {
                        'context': cached['context_chunks'],
                        'chunks': [],
                        'cached': True,
                        'retrieval_time_ms': int((time.time() - start_time) * 1000)
                    }

        # Perform hybrid search
        chunks = await self.hybrid_search(query, config, filters)

        # Apply reranking if available and enabled
        if config.use_reranking and chunks:
            chunks = await self.rerank_with_mlx(query, chunks)
            chunks = chunks[:config.rerank_top_k]

        # Assemble context
        context = self.assemble_context(chunks, config)

        retrieval_time = int((time.time() - start_time) * 1000)

        # Log query for analytics
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO rag_query_logs (
                    query_text, retrieved_chunk_ids,
                    relevance_scores, retrieval_time_ms
                ) VALUES (%s, %s::uuid[], %s, %s)
            """, (
                query,
                [c['id'] for c in chunks],
                [c.get('score', 0) for c in chunks],
                retrieval_time
            ))

        # Cache result if enabled
        if config.cache_results and context:
            query_embedding = await self.generate_query_embedding(query)

            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO rag_context_cache (
                        query_hash, context_chunks, embedding_vector
                    ) VALUES (%s, %s, %s)
                    ON CONFLICT (query_hash) DO UPDATE
                    SET context_chunks = EXCLUDED.context_chunks,
                        embedding_vector = EXCLUDED.embedding_vector,
                        hit_count = 0,
                        last_accessed = NOW(),
                        expires_at = NOW() + INTERVAL '7 days'
                """, (cache_key, Json(context), query_embedding))

        self.conn.commit()

        return {
            'context': context,
            'chunks': chunks,
            'cached': False,
            'retrieval_time_ms': retrieval_time
        }

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


async def test_retrieval():
    """Test retrieval functionality"""
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    # Initialize service
    service = RetrievalService(db_config, os.getenv('OPENAI_API_KEY'))

    try:
        # Test queries
        test_queries = [
            "How do I configure Redis caching?",
            "What are the PostgreSQL optimization settings?",
            "Explain Docker container networking",
            "How to implement authentication in FastAPI?"
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print('='*60)

            result = await service.retrieve(query)

            print(f"Retrieved {len(result['chunks'])} chunks")
            print(f"Retrieval time: {result['retrieval_time_ms']}ms")
            print(f"Cached: {result['cached']}")
            print(f"\nContext preview (first 500 chars):")
            print(result['context'][:500] + "...")

    finally:
        service.close()


if __name__ == "__main__":
    asyncio.run(test_retrieval())