"""
FREEDOM Knowledge Base Embeddings Service
Handles vector generation for documents and queries
"""

import os
import asyncio
import structlog
from typing import List, Dict, Any
import openai
import json
import hashlib

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY')
        )
        self.model = "text-embedding-ada-002"
        self.max_tokens = 8000  # Conservative limit for OpenAI

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            # Truncate if too long
            if len(text) > self.max_tokens * 4:  # Rough token estimation
                text = text[:self.max_tokens * 4]

            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )

            embedding = response.data[0].embedding
            logger.info("embedding_generated",
                       text_length=len(text),
                       embedding_dimensions=len(embedding))

            return embedding

        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e), text_preview=text[:100])
            raise

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently"""
        try:
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
                           batch_size=len(batch),
                           total_processed=len(all_embeddings))

            return all_embeddings

        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e))
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