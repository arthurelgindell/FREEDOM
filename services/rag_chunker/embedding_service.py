#!/usr/bin/env python3
"""
FREEDOM Platform Embedding Service
Primary: LM Studio (local, fast, free)
Fallback: OpenAI API (if LM Studio unavailable)
No mock embeddings - fails honestly if no service available
"""

import os
import time
import logging
import requests
from typing import List, Optional, Tuple, Dict
from openai import OpenAI
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Production embedding service with local-first architecture.
    Prioritizes LM Studio for privacy, speed, and cost.
    """

    def __init__(self):
        # LM Studio configuration (PRIMARY)
        self.lm_studio_url = os.getenv('LM_STUDIO_ENDPOINT', 'http://localhost:1234/v1')
        self.lm_studio_model = os.getenv('LM_STUDIO_EMBED_MODEL', 'text-embedding-nomic-embed-text-v1.5')
        self.lm_studio_available = self._check_lm_studio()

        # OpenAI configuration (FALLBACK 1)
        openai_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=openai_key) if openai_key else None
        self.openai_model = 'text-embedding-ada-002'

        # Gemini configuration (FALLBACK 2)
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.gemini_model = 'models/text-embedding-004'
        self.gemini_url = 'https://generativelanguage.googleapis.com/v1beta'

        # Statistics
        self.stats = {
            'lm_studio_calls': 0,
            'lm_studio_errors': 0,
            'openai_calls': 0,
            'openai_errors': 0,
            'gemini_calls': 0,
            'gemini_errors': 0,
            'total_latency_ms': 0,
            'embeddings_generated': 0
        }

        # Log configuration
        self._log_configuration()

    def _check_lm_studio(self) -> bool:
        """Check if LM Studio is available and has embedding model"""
        try:
            response = requests.get(f"{self.lm_studio_url}/models", timeout=2)
            if response.status_code == 200:
                models = response.json().get('data', [])
                for model in models:
                    if 'embed' in model.get('id', '').lower():
                        logger.info(f"✅ LM Studio embedding model found: {model['id']}")
                        return True
            logger.warning("⚠️ LM Studio available but no embedding model loaded")
            return False
        except Exception as e:
            logger.warning(f"⚠️ LM Studio not available: {e}")
            return False

    def _log_configuration(self):
        """Log the current embedding service configuration"""
        logger.info("="*60)
        logger.info("EMBEDDING SERVICE CONFIGURATION")
        logger.info("="*60)

        if self.lm_studio_available:
            logger.info(f"✅ PRIMARY: LM Studio at {self.lm_studio_url}")
            logger.info(f"   Model: {self.lm_studio_model}")
            logger.info(f"   Status: AVAILABLE (local, fast, free)")
        else:
            logger.info(f"❌ PRIMARY: LM Studio UNAVAILABLE")

        if self.openai_client:
            logger.info(f"✅ FALLBACK 1: OpenAI API")
            logger.info(f"   Model: {self.openai_model}")
            logger.info(f"   Status: CONFIGURED (network, slower, paid)")
        else:
            logger.info(f"❌ FALLBACK 1: OpenAI API NOT CONFIGURED")

        if self.gemini_api_key:
            logger.info(f"✅ FALLBACK 2: Gemini API")
            logger.info(f"   Model: {self.gemini_model}")
            logger.info(f"   Status: CONFIGURED (network, free tier available)")
        else:
            logger.info(f"❌ FALLBACK 2: Gemini API NOT CONFIGURED")

        if not self.lm_studio_available and not self.openai_client and not self.gemini_api_key:
            logger.error("⚠️ WARNING: No embedding service available!")

        logger.info("="*60)

    def get_embedding(self, text: str, force_openai: bool = False) -> List[float]:
        """
        Get embedding for text with automatic service selection.

        Args:
            text: Text to embed
            force_openai: Force use of OpenAI (for testing/comparison)

        Returns:
            Embedding vector

        Raises:
            Exception: If no embedding service is available
        """
        start_time = time.perf_counter()

        # Try LM Studio first (unless forced to use OpenAI)
        if self.lm_studio_available and not force_openai:
            try:
                embedding = self._get_lm_studio_embedding(text)
                latency_ms = (time.perf_counter() - start_time) * 1000

                self.stats['lm_studio_calls'] += 1
                self.stats['embeddings_generated'] += 1
                self.stats['total_latency_ms'] += latency_ms

                logger.debug(f"LM Studio embedding generated in {latency_ms:.1f}ms")
                return embedding

            except Exception as e:
                logger.warning(f"LM Studio embedding failed: {e}")
                self.stats['lm_studio_errors'] += 1
                # Fall through to OpenAI

        # Try OpenAI as fallback
        if self.openai_client:
            try:
                embedding = self._get_openai_embedding(text)
                latency_ms = (time.perf_counter() - start_time) * 1000

                self.stats['openai_calls'] += 1
                self.stats['embeddings_generated'] += 1
                self.stats['total_latency_ms'] += latency_ms

                logger.debug(f"OpenAI embedding generated in {latency_ms:.1f}ms")
                return embedding

            except Exception as e:
                logger.error(f"OpenAI embedding failed: {e}")
                self.stats['openai_errors'] += 1
                # Fall through to Gemini

        # Try Gemini as final fallback
        if self.gemini_api_key:
            try:
                embedding = self._get_gemini_embedding(text)
                latency_ms = (time.perf_counter() - start_time) * 1000

                self.stats['gemini_calls'] += 1
                self.stats['embeddings_generated'] += 1
                self.stats['total_latency_ms'] += latency_ms

                logger.debug(f"Gemini embedding generated in {latency_ms:.1f}ms")
                return embedding

            except Exception as e:
                logger.error(f"Gemini embedding failed: {e}")
                self.stats['gemini_errors'] += 1
                raise

        # No service available - fail honestly
        raise Exception(
            "No embedding service available. "
            "Please ensure LM Studio is running with an embedding model, "
            "or configure OPENAI_API_KEY environment variable."
        )

    def _get_lm_studio_embedding(self, text: str) -> List[float]:
        """Get embedding from LM Studio"""
        response = requests.post(
            f"{self.lm_studio_url}/embeddings",
            json={
                "input": text,
                "model": self.lm_studio_model
            },
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"LM Studio returned status {response.status_code}: {response.text}")

        data = response.json()
        return data['data'][0]['embedding']

    def _get_openai_embedding(self, text: str) -> List[float]:
        """Get embedding from OpenAI API"""
        response = self.openai_client.embeddings.create(
            model=self.openai_model,
            input=text
        )
        return response.data[0].embedding

    def _get_gemini_embedding(self, text: str) -> List[float]:
        """Get embedding from Gemini API"""
        import requests

        url = f"{self.gemini_url}/{self.gemini_model}:embedContent"
        params = {'key': self.gemini_api_key}

        payload = {
            "model": self.gemini_model,
            "content": {
                "parts": [{"text": text}]
            },
            "taskType": "RETRIEVAL_DOCUMENT",
            "title": "Document"
        }

        response = requests.post(url, params=params, json=payload, timeout=30)

        if response.status_code != 200:
            raise Exception(f"Gemini returned status {response.status_code}: {response.text}")

        data = response.json()
        return data['embedding']['values']

    def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts efficiently.
        LM Studio can handle batch processing locally without rate limits.
        """
        embeddings = []

        for i, text in enumerate(texts):
            if i % 10 == 0 and i > 0:
                logger.info(f"Processed {i}/{len(texts)} embeddings")

            embedding = self.get_embedding(text)
            embeddings.append(embedding)

            # Only sleep for OpenAI to respect rate limits
            if self.stats['openai_calls'] > self.stats['lm_studio_calls']:
                time.sleep(0.02)  # 50 requests/sec max for OpenAI

        return embeddings

    def get_statistics(self) -> Dict:
        """Get service usage statistics"""
        total_calls = self.stats['lm_studio_calls'] + self.stats['openai_calls']
        avg_latency = (self.stats['total_latency_ms'] / total_calls) if total_calls > 0 else 0

        return {
            'total_embeddings': self.stats['embeddings_generated'],
            'lm_studio_calls': self.stats['lm_studio_calls'],
            'lm_studio_errors': self.stats['lm_studio_errors'],
            'lm_studio_success_rate': (
                (self.stats['lm_studio_calls'] - self.stats['lm_studio_errors']) /
                self.stats['lm_studio_calls'] * 100
            ) if self.stats['lm_studio_calls'] > 0 else 0,
            'openai_calls': self.stats['openai_calls'],
            'openai_errors': self.stats['openai_errors'],
            'gemini_calls': self.stats['gemini_calls'],
            'gemini_errors': self.stats['gemini_errors'],
            'average_latency_ms': avg_latency,
            'primary_service': 'lm_studio' if self.lm_studio_available else 'openai',
            'estimated_cost_saved': self.stats['lm_studio_calls'] * 0.0001  # Rough estimate
        }

    def test_services(self) -> Dict:
        """Test both embedding services and compare"""
        test_text = "Test embedding for FREEDOM platform RAG system"
        results = {}

        # Test LM Studio
        if self.lm_studio_available:
            try:
                start = time.perf_counter()
                lm_embedding = self._get_lm_studio_embedding(test_text)
                lm_latency = (time.perf_counter() - start) * 1000

                results['lm_studio'] = {
                    'success': True,
                    'latency_ms': lm_latency,
                    'dimensions': len(lm_embedding),
                    'model': self.lm_studio_model
                }
            except Exception as e:
                results['lm_studio'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            results['lm_studio'] = {'success': False, 'error': 'Not available'}

        # Test OpenAI
        if self.openai_client:
            try:
                start = time.perf_counter()
                openai_embedding = self._get_openai_embedding(test_text)
                openai_latency = (time.perf_counter() - start) * 1000

                results['openai'] = {
                    'success': True,
                    'latency_ms': openai_latency,
                    'dimensions': len(openai_embedding),
                    'model': self.openai_model
                }
            except Exception as e:
                results['openai'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            results['openai'] = {'success': False, 'error': 'Not configured'}

        # Test Gemini
        if self.gemini_api_key:
            try:
                start = time.perf_counter()
                gemini_embedding = self._get_gemini_embedding(test_text)
                gemini_latency = (time.perf_counter() - start) * 1000

                results['gemini'] = {
                    'success': True,
                    'latency_ms': gemini_latency,
                    'dimensions': len(gemini_embedding),
                    'model': self.gemini_model
                }
            except Exception as e:
                results['gemini'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            results['gemini'] = {'success': False, 'error': 'Not configured'}

        return results


# Singleton instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


if __name__ == "__main__":
    # Test the service
    logging.basicConfig(level=logging.INFO)

    service = get_embedding_service()

    # Test both services
    print("\nTesting embedding services...")
    test_results = service.test_services()

    for service_name, result in test_results.items():
        print(f"\n{service_name}:")
        if result['success']:
            print(f"  ✅ Success")
            print(f"  Latency: {result['latency_ms']:.1f}ms")
            print(f"  Dimensions: {result['dimensions']}")
            print(f"  Model: {result.get('model', 'N/A')}")
        else:
            print(f"  ❌ Failed: {result['error']}")

    # Test actual embedding
    print("\nGenerating test embedding...")
    try:
        embedding = service.get_embedding("FREEDOM platform RAG system test")
        print(f"✅ Embedding generated: {len(embedding)} dimensions")
        print(f"   First 5 values: {embedding[:5]}")

        # Show statistics
        stats = service.get_statistics()
        print(f"\nStatistics:")
        print(f"  Primary service: {stats['primary_service']}")
        print(f"  Total embeddings: {stats['total_embeddings']}")
        print(f"  Average latency: {stats['average_latency_ms']:.1f}ms")
    except Exception as e:
        print(f"❌ Error: {e}")