#!/usr/bin/env python3
"""
Quick demo: Process and embed top 5 largest specifications
Demonstrates the complete RAG pipeline with LM Studio embeddings
"""

import sys
import logging
import time
import subprocess
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_in_docker(sql_command):
    """Execute SQL in Docker PostgreSQL"""
    result = subprocess.run(
        ['docker', 'exec', 'freedom-postgres-1', 'psql', '-U', 'freedom',
         '-d', 'techknowledge', '-t', '-A', '-c', sql_command],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error(f"SQL Error: {result.stderr}")
        return None
    return result.stdout.strip()

def main():
    logger.info("="*60)
    logger.info("RAG PIPELINE DEMO: Processing Top 5 Specifications")
    logger.info("="*60)

    # Get top 5 largest specifications
    sql_get_specs = """
        SELECT json_agg(row_to_json(s)) FROM (
            SELECT
                s.id, s.component_type, s.version,
                s.component_name, s.specification, s.source_type,
                t.name as technology_name,
                LENGTH(s.specification::text) as spec_length
            FROM specifications s
            LEFT JOIN technologies t ON s.technology_id = t.id
            WHERE LENGTH(s.specification::text) > 50000
            ORDER BY LENGTH(s.specification::text) DESC
            LIMIT 5
        ) s;
    """

    specs_json = run_in_docker(sql_get_specs)
    if not specs_json:
        logger.error("Failed to get specifications")
        return

    specs = json.loads(specs_json)
    logger.info(f"Found {len(specs)} large specifications to process")

    # Import services
    sys.path.insert(0, '/Volumes/DATA/FREEDOM/services/rag_chunker')
    from chunking_service import ChunkingService
    from embedding_service import get_embedding_service

    # Initialize services with local connection
    db_config = {'host': 'localhost', 'port': 5432, 'database': 'techknowledge', 'user': 'arthurdell'}
    chunking_service = ChunkingService(db_config, openai_api_key=None)
    embedding_service = get_embedding_service()

    if not embedding_service.lm_studio_available:
        logger.error("LM Studio is not available!")
        return

    total_chunks = 0
    total_embeddings = 0
    start_time = time.time()

    for i, spec in enumerate(specs, 1):
        logger.info(f"\n[{i}/{len(specs)}] Processing: {spec['component_name']} "
                   f"({spec['spec_length']:,} bytes)")

        try:
            # Create chunks
            chunks = chunking_service.process_specification(spec)
            logger.info(f"  Created {len(chunks)} chunks")

            # Process each chunk
            for j, chunk in enumerate(chunks):
                # Generate embedding
                embedding = embedding_service.get_embedding(chunk['chunk_text'])

                # Prepare SQL insert
                sql_insert = f"""
                    INSERT INTO document_chunks (
                        specification_id, chunk_index, chunk_text, chunk_tokens,
                        prev_chunk_overlap, next_chunk_overlap,
                        dense_vector, sparse_vector,
                        technology_name, component_type, component_name,
                        version, source_type
                    ) VALUES (
                        '{chunk['specification_id']}',
                        {chunk['chunk_index']},
                        '{chunk['chunk_text'].replace("'", "''")[:1000]}',
                        {chunk['chunk_tokens']},
                        {f"'{chunk.get('prev_chunk_overlap', '')[:100].replace("'", "''")}'" if chunk.get('prev_chunk_overlap') else 'NULL'},
                        {f"'{chunk.get('next_chunk_overlap', '')[:100].replace("'", "''")}'" if chunk.get('next_chunk_overlap') else 'NULL'},
                        '[{",".join(map(str, embedding))}]',
                        '{json.dumps(chunk['sparse_vector']).replace("'", "''")}',
                        '{spec.get('technology_name', 'Unknown').replace("'", "''")}',
                        '{chunk['component_type'].replace("'", "''")}',
                        '{chunk['component_name'].replace("'", "''")}',
                        '{chunk['version'].replace("'", "''")}',
                        '{chunk['source_type'].replace("'", "''")}'
                    )
                    ON CONFLICT (content_hash) DO NOTHING
                    RETURNING id;
                """

                result = run_in_docker(sql_insert)
                if result:
                    total_chunks += 1
                    total_embeddings += 1

                # Progress indicator
                if (j + 1) % 50 == 0:
                    logger.info(f"    Processed {j+1}/{len(chunks)} chunks...")

        except Exception as e:
            logger.error(f"  Error processing spec: {e}")

    # Final statistics
    elapsed = time.time() - start_time

    stats_sql = """
        SELECT
            COUNT(DISTINCT specification_id) as specs,
            COUNT(*) as chunks,
            COUNT(dense_vector) as embeddings
        FROM document_chunks;
    """

    stats = run_in_docker(stats_sql)
    if stats:
        specs_count, chunks_count, embeddings_count = stats.split('|')

        logger.info("\n" + "="*60)
        logger.info("DEMO COMPLETE")
        logger.info("="*60)
        logger.info(f"Specifications with chunks: {specs_count}")
        logger.info(f"Total chunks in database: {chunks_count}")
        logger.info(f"Total embeddings: {embeddings_count}")
        logger.info(f"Processing time: {elapsed:.1f} seconds")
        if total_embeddings > 0:
            logger.info(f"Embedding rate: {total_embeddings/elapsed:.1f} embeddings/sec")
        logger.info("="*60)

    chunking_service.close()

if __name__ == "__main__":
    main()