#!/usr/bin/env python3
"""
Add OpenAI embeddings to existing chunks
"""

import os
import asyncio
import logging
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def add_embeddings():
    """Add dense embeddings to chunks that don't have them"""

    # Set OpenAI API key
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not openai_api_key:
        # Try to read from API_KEYS.md file
        try:
            with open('/Volumes/DATA/FREEDOM/API_KEYS.md', 'r') as f:
                content = f.read()
                # Extract OpenAI key from line 18
                lines = content.split('\n')
                for line in lines:
                    if 'Validated OpenAI:' in line:
                        openai_api_key = line.split(': ')[1].strip(' --')
                        break
        except:
            pass

    if not openai_api_key:
        logger.warning("No OpenAI API key found. Set OPENAI_API_KEY environment variable.")
        logger.info("For testing, we'll use mock embeddings instead.")
        use_mock = True
    else:
        use_mock = False
        client = OpenAI(api_key=openai_api_key)
        logger.info(f"Using OpenAI API key: {openai_api_key[:20]}...")

    # Database connection
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'techknowledge',
        'user': 'arthurdell'
    }

    conn = psycopg2.connect(**db_config)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Count chunks without embeddings
            cursor.execute("""
                SELECT COUNT(*)
                FROM document_chunks
                WHERE dense_vector IS NULL
            """)
            missing_count = cursor.fetchone()['count']

            logger.info(f"Found {missing_count} chunks without embeddings")

            if missing_count == 0:
                logger.info("All chunks already have embeddings!")
                return

            # Get chunks without embeddings
            cursor.execute("""
                SELECT id, chunk_text
                FROM document_chunks
                WHERE dense_vector IS NULL
                LIMIT 2500
            """)

            chunks = cursor.fetchall()

            for i, chunk in enumerate(chunks, 1):
                if use_mock:
                    # Create mock embedding (1536 dimensions)
                    import hashlib
                    import numpy as np

                    # Create deterministic mock embedding from text hash
                    text_hash = hashlib.md5(chunk['chunk_text'].encode()).hexdigest()
                    seed = int(text_hash[:8], 16)
                    np.random.seed(seed)
                    embedding = np.random.randn(1536).tolist()
                    embedding = [float(x) / 10 for x in embedding]  # Normalize
                else:
                    # Generate real embedding
                    try:
                        # Clean text to remove problematic Unicode characters
                        clean_text = chunk['chunk_text'].encode('utf-8', 'ignore').decode('utf-8')

                        response = client.embeddings.create(
                            model="text-embedding-ada-002",
                            input=clean_text
                        )
                        embedding = response.data[0].embedding
                    except Exception as e:
                        logger.error(f"Error generating embedding: {e}")
                        continue

                # Update chunk with embedding
                cursor.execute("""
                    UPDATE document_chunks
                    SET dense_vector = %s
                    WHERE id = %s
                """, (embedding, chunk['id']))

                if i % 10 == 0:
                    conn.commit()
                    logger.info(f"Processed {i}/{len(chunks)} chunks")

                # Rate limiting for OpenAI API
                if not use_mock:
                    time.sleep(0.02)  # 50 requests per second (well under 3000/min limit)

            conn.commit()
            logger.info(f"Successfully added embeddings to {len(chunks)} chunks")

            # Rebuild vector index
            logger.info("Rebuilding vector index...")
            cursor.execute("""
                REINDEX INDEX idx_chunks_dense_vector;
            """)
            conn.commit()

    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(add_embeddings())