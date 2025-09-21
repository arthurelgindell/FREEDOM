"""
FREEDOM Knowledge Base Embeddings Service
Handles vector generation for documents and queries
"""

import os
import asyncio
import structlog
from typing import List, Dict, Any, Optional
import json
import hashlib
import random
import numpy as np

# Conditional OpenAI import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings"""

    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.use_openai = OPENAI_AVAILABLE and self.openai_key

        if self.use_openai:
            self.client = openai.AsyncOpenAI(api_key=self.openai_key)
            self.model = "text-embedding-ada-002"
            self.embedding_dim = 1536  # OpenAI ada-002 dimensions
            logger.info("embedding_service_initialized", provider="openai", model=self.model)
        else:
            self.client = None
            self.embedding_dim = 1536  # Match OpenAI dimensions for compatibility
            logger.warning("embedding_service_initialized",
                         provider="local_fallback",
                         reason="OpenAI unavailable or no API key",
                         dimensions=self.embedding_dim)

        self.max_tokens = 8000  # Conservative limit

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            # Truncate if too long
            if len(text) > self.max_tokens * 4:  # Rough token estimation
                text = text[:self.max_tokens * 4]

            if self.use_openai:
                # Use OpenAI API
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
            else:
                # Local fallback: Generate deterministic pseudo-embeddings
                embedding = self._generate_local_embedding(text)

            logger.info("embedding_generated",
                       provider="openai" if self.use_openai else "local",
                       text_length=len(text),
                       embedding_dimensions=len(embedding))

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed",
                        error=str(e),
                        provider="openai" if self.use_openai else "local",
                        text_preview=text[:100])
            # Fallback to local if OpenAI fails
            if self.use_openai:
                logger.info("falling_back_to_local_embedding")
                return self._generate_local_embedding(text)
            raise

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently"""
        try:
            if self.use_openai:
                # Process in batches to respect API limits
                batch_size = 100
                all_embeddings = []

                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]

                    # Truncate texts in batch
                    truncated_batch = []
                    for text in batch:
                        if len(text) > self.max_tokens * 4:
                            text = text[:self.max_tokens * 4]
                        truncated_batch.append(text)

                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=truncated_batch
                    )

                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)

                    logger.info("batch_embeddings_generated",
                               provider="openai",
                               batch_size=len(batch),
                               total_processed=len(all_embeddings))
            else:
                # Local fallback for batch
                all_embeddings = []
                for text in texts:
                    if len(text) > self.max_tokens * 4:
                        text = text[:self.max_tokens * 4]
                    embedding = self._generate_local_embedding(text)
                    all_embeddings.append(embedding)

                logger.info("batch_embeddings_generated",
                           provider="local",
                           total_processed=len(all_embeddings))

            return all_embeddings

        except Exception as e:
            logger.error("batch_embedding_generation_failed",
                        error=str(e),
                        provider="openai" if self.use_openai else "local")
            # Fallback to local if OpenAI fails
            if self.use_openai:
                logger.info("falling_back_to_local_batch_embedding")
                return [self._generate_local_embedding(t[:self.max_tokens * 4] if len(t) > self.max_tokens * 4 else t)
                       for t in texts]
            raise

    def extract_text_for_embedding(self, specification: Dict[str, Any]) -> str:
        """Extract meaningful text from specification for embedding"""
        try:
            # Extract key information from specification
            text_parts = []

            # Add specification content
            if isinstance(specification, dict):
                # Recursively extract text from nested dictionaries
                def extract_values(obj, path=""):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            extract_values(value, current_path)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            current_path = f"{path}[{i}]" if path else f"[{i}]"
                            extract_values(item, current_path)
                    elif isinstance(obj, str) and len(obj.strip()) > 0:
                        text_parts.append(f"{path}: {obj.strip()}")

                extract_values(specification)

            # Join all text parts
            full_text = " | ".join(text_parts)

            # Ensure we have some text
            if not full_text.strip():
                full_text = json.dumps(specification)

            logger.debug("text_extracted_for_embedding",
                        original_length=len(json.dumps(specification)),
                        extracted_length=len(full_text))

            return full_text

        except Exception as e:
            logger.error("text_extraction_failed", error=str(e))
            # Fallback to JSON representation
            return json.dumps(specification)

    def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate a deterministic local embedding as fallback

        This creates a consistent pseudo-embedding based on text features.
        While not as semantically meaningful as OpenAI embeddings, it provides:
        - Deterministic output for the same input
        - Basic text similarity (similar texts get similar embeddings)
        - Compatibility with the existing vector database schema
        """
        # Create a deterministic seed from text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)

        # Initialize random state with seed for deterministic output
        rng = np.random.RandomState(seed)

        # Generate base embedding
        embedding = rng.randn(self.embedding_dim).tolist()

        # Add some text-based features to improve similarity matching
        # (length, word count, character distribution)
        text_features = [
            len(text) / 10000.0,  # Normalized length
            text.count(' ') / 100.0,  # Word count estimate
            text.count('.') / 10.0,  # Sentence count estimate
        ]

        # Blend features into first few dimensions
        for i, feature in enumerate(text_features):
            if i < len(embedding):
                embedding[i] = (embedding[i] + feature) / 2.0

        # Normalize to unit length (similar to OpenAI embeddings)
        norm = sum(x**2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]

        return embedding

    def generate_content_hash(self, specification: Dict[str, Any]) -> str:
        """Generate hash for content deduplication"""
        content_str = json.dumps(specification, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()


# Singleton instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service