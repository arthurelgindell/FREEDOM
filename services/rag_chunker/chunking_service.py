#!/usr/bin/env python3
"""
RAG Chunking Service for FREEDOM Platform
Processes 702 specifications into optimized chunks for vector retrieval
"""

import os
import sys
import json
import hashlib
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import numpy as np
from openai import OpenAI
import tiktoken

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ChunkConfig:
    """Configuration for chunking strategy"""
    target_chunk_size: int = 512  # Target tokens per chunk
    max_chunk_size: int = 768      # Maximum tokens per chunk
    min_chunk_size: int = 128      # Minimum tokens per chunk
    overlap_size: int = 64         # Token overlap between chunks
    semantic_boundaries: bool = True  # Respect semantic boundaries
    preserve_structure: bool = True   # Preserve document structure

class ChunkingService:
    """Service for chunking and indexing specifications"""

    def __init__(self, db_config: Dict[str, Any], openai_api_key: Optional[str] = None):
        self.db_config = db_config
        self.openai_client = None
        self.tokenizer = tiktoken.encoding_for_model("text-embedding-ada-002")

        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)

        # Database connection
        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False

    def extract_spec_text(self, spec_json: Dict) -> str:
        """Extract text from specification JSON"""
        text_parts = []

        def extract_recursive(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Skip metadata fields
                    if key in ['_id', '_timestamp', '_source']:
                        continue

                    # Add key as section header
                    if prefix:
                        section = f"{prefix}.{key}"
                    else:
                        section = key

                    if isinstance(value, (str, int, float, bool)):
                        text_parts.append(f"{section}: {value}")
                    elif isinstance(value, list):
                        for i, item in enumerate(value):
                            if isinstance(item, str):
                                text_parts.append(f"{section}[{i}]: {item}")
                            else:
                                extract_recursive(item, f"{section}[{i}]")
                    else:
                        extract_recursive(value, section)

            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, str):
                        text_parts.append(f"{prefix}[{i}]: {item}")
                    else:
                        extract_recursive(item, f"{prefix}[{i}]")

            elif obj is not None:
                text_parts.append(f"{prefix}: {obj}")

        extract_recursive(spec_json)
        return "\n".join(text_parts)

    def find_semantic_boundaries(self, text: str) -> List[int]:
        """Find semantic boundaries in text for optimal chunk splitting"""
        boundaries = [0]

        # Pattern matching for semantic boundaries
        patterns = [
            r'\n\n+',                    # Multiple newlines
            r'\n(?=[A-Z][a-z]+:)',       # Section headers
            r'\n(?=\d+\.)',              # Numbered lists
            r'\n(?=[•\-\*])',            # Bullet points
            r'\.(?:\s+[A-Z])',           # Sentence boundaries
            r'\}\s*\{',                  # JSON object boundaries
            r'\]\s*\[',                  # Array boundaries
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                boundaries.append(match.start())

        # Sort and deduplicate
        boundaries = sorted(set(boundaries))
        boundaries.append(len(text))

        return boundaries

    def chunk_text(self, text: str, config: ChunkConfig) -> List[Dict[str, Any]]:
        """Chunk text into optimal segments with overlap"""
        chunks = []
        tokens = self.tokenizer.encode(text)

        if len(tokens) <= config.target_chunk_size:
            # Single chunk for small texts
            return [{
                'chunk_index': 0,
                'chunk_text': text,
                'chunk_tokens': len(tokens),
                'prev_chunk_overlap': None,
                'next_chunk_overlap': None
            }]

        # Find semantic boundaries
        if config.semantic_boundaries:
            boundaries = self.find_semantic_boundaries(text)
        else:
            boundaries = None

        current_pos = 0
        chunk_index = 0

        while current_pos < len(tokens):
            # Determine chunk size
            chunk_end = min(current_pos + config.target_chunk_size, len(tokens))

            # Adjust to semantic boundary if enabled
            if boundaries and config.semantic_boundaries:
                # Find nearest boundary
                token_to_char = len(self.tokenizer.decode(tokens[:chunk_end]))
                nearest_boundary = min(
                    boundaries,
                    key=lambda b: abs(b - token_to_char) if b >= current_pos else float('inf')
                )

                # Adjust chunk end to boundary
                adjusted_tokens = self.tokenizer.encode(text[:nearest_boundary])
                if config.min_chunk_size <= len(adjusted_tokens) - current_pos <= config.max_chunk_size:
                    chunk_end = len(adjusted_tokens)

            # Extract chunk with overlap
            chunk_tokens = tokens[current_pos:chunk_end]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            # Get overlap context
            prev_overlap = None
            next_overlap = None

            if chunk_index > 0 and config.overlap_size > 0:
                overlap_start = max(0, current_pos - config.overlap_size)
                prev_overlap = self.tokenizer.decode(tokens[overlap_start:current_pos])

            if chunk_end < len(tokens) and config.overlap_size > 0:
                overlap_end = min(len(tokens), chunk_end + config.overlap_size)
                next_overlap = self.tokenizer.decode(tokens[chunk_end:overlap_end])

            chunks.append({
                'chunk_index': chunk_index,
                'chunk_text': chunk_text,
                'chunk_tokens': len(chunk_tokens),
                'prev_chunk_overlap': prev_overlap,
                'next_chunk_overlap': next_overlap
            })

            # Move to next chunk with overlap
            current_pos = chunk_end - (config.overlap_size if chunk_end < len(tokens) else 0)
            chunk_index += 1

        return chunks

    def calculate_bm25_vector(self, text: str) -> Dict[str, float]:
        """Calculate sparse BM25 vector for text"""
        # Tokenize and normalize
        words = re.findall(r'\b\w+\b', text.lower())

        # Calculate term frequencies
        term_freq = {}
        for word in words:
            term_freq[word] = term_freq.get(word, 0) + 1

        # Normalize by document length
        doc_length = len(words)
        k1 = 1.2  # BM25 parameter
        b = 0.75  # BM25 parameter

        normalized_freq = {}
        for term, freq in term_freq.items():
            # Simplified BM25 scoring
            score = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * doc_length / 500))
            normalized_freq[term] = round(score, 4)

        return normalized_freq

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate dense embedding using OpenAI API"""
        if not self.openai_client:
            logger.warning("OpenAI client not initialized, skipping embedding generation")
            return None

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def process_specification(self, spec_row: Dict) -> List[Dict]:
        """Process a single specification into chunks"""
        logger.info(f"Processing specification: {spec_row['component_name']}")

        # Extract text from JSON specification
        spec_text = self.extract_spec_text(spec_row['specification'])

        # Add metadata to text
        metadata_text = f"""
Technology: {spec_row.get('technology_name', 'Unknown')}
Component Type: {spec_row['component_type']}
Component Name: {spec_row['component_name']}
Version: {spec_row['version']}
Source: {spec_row['source_type']}

{spec_text}
"""

        # Configure chunking strategy based on content type
        config = ChunkConfig()
        if spec_row['component_type'] == 'API':
            config.target_chunk_size = 768  # Larger chunks for APIs
        elif spec_row['component_type'] == 'Configuration':
            config.target_chunk_size = 512  # Medium chunks for configs

        # Create chunks
        chunks = self.chunk_text(metadata_text, config)

        # Enhance chunks with metadata
        for chunk in chunks:
            chunk['specification_id'] = spec_row['id']
            chunk['technology_name'] = spec_row.get('technology_name')
            chunk['component_type'] = spec_row['component_type']
            chunk['component_name'] = spec_row['component_name']
            chunk['version'] = spec_row['version']
            chunk['source_type'] = spec_row['source_type']

            # Calculate sparse vector
            chunk['sparse_vector'] = self.calculate_bm25_vector(chunk['chunk_text'])

        return chunks

    async def index_chunks(self, chunks: List[Dict]) -> int:
        """Index chunks into the database with embeddings"""
        indexed_count = 0

        for chunk in chunks:
            try:
                # Generate embedding if OpenAI is available
                if self.openai_client:
                    embedding = await self.generate_embedding(chunk['chunk_text'])
                else:
                    embedding = None

                # Insert chunk into database
                with self.conn.cursor() as cursor:
                    insert_query = """
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
                        RETURNING id;
                    """

                    cursor.execute(insert_query, (
                        chunk['specification_id'],
                        chunk['chunk_index'],
                        chunk['chunk_text'],
                        chunk['chunk_tokens'],
                        chunk.get('prev_chunk_overlap'),
                        chunk.get('next_chunk_overlap'),
                        embedding,
                        Json(chunk['sparse_vector']),
                        chunk.get('technology_name'),
                        chunk['component_type'],
                        chunk['component_name'],
                        chunk['version'],
                        chunk['source_type']
                    ))

                    if cursor.fetchone():
                        indexed_count += 1

                self.conn.commit()

            except Exception as e:
                logger.error(f"Error indexing chunk: {e}")
                self.conn.rollback()

        return indexed_count

    async def process_all_specifications(self, batch_size: int = 10):
        """Process all specifications in batches"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all specifications with technology info
            cursor.execute("""
                SELECT
                    s.id, s.technology_id, s.version, s.component_type,
                    s.component_name, s.specification, s.source_type,
                    t.name as technology_name
                FROM specifications s
                LEFT JOIN technologies t ON s.technology_id = t.id
                ORDER BY s.extracted_at DESC
            """)

            specs = cursor.fetchall()
            total_specs = len(specs)

            logger.info(f"Found {total_specs} specifications to process")

            total_chunks_created = 0

            # Process in batches
            for i in range(0, total_specs, batch_size):
                batch = specs[i:i + batch_size]
                batch_chunks = []

                for spec in batch:
                    chunks = self.process_specification(spec)
                    batch_chunks.extend(chunks)

                # Index chunks
                indexed = await self.index_chunks(batch_chunks)
                total_chunks_created += indexed

                logger.info(f"Processed {i + len(batch)}/{total_specs} specifications, "
                           f"created {indexed} chunks")

            logger.info(f"Completed: {total_chunks_created} chunks created from {total_specs} specifications")

            return total_chunks_created

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


async def main():
    """Main entry point"""
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    # OpenAI API key (optional - will work without it using sparse vectors only)
    openai_api_key = os.getenv('OPENAI_API_KEY')

    # Initialize service
    service = ChunkingService(db_config, openai_api_key)

    try:
        # Apply schema
        logger.info("Creating vector storage schema...")
        with open('/Volumes/DATA/FREEDOM/services/rag_chunker/create_vector_schema.sql', 'r') as f:
            schema_sql = f.read()

        with service.conn.cursor() as cursor:
            cursor.execute(schema_sql)
            service.conn.commit()

        logger.info("Schema created successfully")

        # Process all specifications
        logger.info("Starting specification chunking and indexing...")
        chunks_created = await service.process_all_specifications()

        logger.info(f"Successfully created {chunks_created} chunks")

    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise

    finally:
        service.close()


if __name__ == "__main__":
    asyncio.run(main())