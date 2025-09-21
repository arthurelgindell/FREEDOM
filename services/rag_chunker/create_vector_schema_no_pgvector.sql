-- RAG Vector Storage Schema for FREEDOM Platform
-- Modified version that works without pgvector extension
-- Uses JSONB to store embeddings

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create chunks table for storing document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID REFERENCES specifications(id) ON DELETE CASCADE,

    -- Chunk metadata
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_tokens INTEGER,

    -- Overlap context
    prev_chunk_overlap TEXT,
    next_chunk_overlap TEXT,

    -- Vector embeddings stored as JSONB
    dense_vector JSONB,  -- OpenAI ada-002 embeddings (1536 dimensions)
    sparse_vector JSONB, -- BM25 term frequencies

    -- Metadata for filtering
    technology_name TEXT,
    component_type TEXT,
    component_name TEXT,
    version TEXT,
    source_type TEXT,

    -- Content hash for deduplication
    content_hash TEXT GENERATED ALWAYS AS (md5(chunk_text)) STORED,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,

    -- Search metadata
    relevance_score FLOAT DEFAULT 0.0,
    semantic_tags TEXT[]
);

-- Indexes for efficient retrieval
CREATE INDEX IF NOT EXISTS idx_chunks_spec_id ON document_chunks(specification_id);
CREATE INDEX IF NOT EXISTS idx_chunks_technology ON document_chunks(technology_name);
CREATE INDEX IF NOT EXISTS idx_chunks_component ON document_chunks(component_type, component_name);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON document_chunks(content_hash);

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_chunks_text_search ON document_chunks
    USING gin(to_tsvector('english', chunk_text));

-- Index for sparse vector JSONB
CREATE INDEX IF NOT EXISTS idx_chunks_sparse ON document_chunks USING gin(sparse_vector);

-- Index for dense vector JSONB
CREATE INDEX IF NOT EXISTS idx_chunks_dense ON document_chunks USING gin(dense_vector);

-- Query logs for improving retrieval
CREATE TABLE IF NOT EXISTS rag_query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_embedding JSONB,

    -- Retrieved chunks
    retrieved_chunk_ids UUID[],
    relevance_scores FLOAT[],

    -- User feedback
    selected_chunk_id UUID,
    feedback_score FLOAT,

    -- Performance metrics
    retrieval_time_ms INTEGER,
    generation_time_ms INTEGER,
    total_tokens INTEGER,

    -- Context
    session_id UUID,
    user_context JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Chunk relationships for context graphs
CREATE TABLE IF NOT EXISTS chunk_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    target_chunk_id UUID REFERENCES document_chunks(id) ON DELETE CASCADE,
    relationship_type TEXT, -- 'sequential', 'reference', 'similar', 'contradicts'
    confidence FLOAT DEFAULT 1.0,
    metadata JSONB,

    UNIQUE(source_chunk_id, target_chunk_id, relationship_type)
);

-- Cache for frequently accessed contexts
CREATE TABLE IF NOT EXISTS rag_context_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_hash TEXT UNIQUE NOT NULL,
    context_chunks JSONB NOT NULL,
    embedding_vector JSONB,

    -- Cache management
    hit_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days',

    created_at TIMESTAMP DEFAULT NOW()
);

-- Function to calculate cosine similarity between JSONB vectors
CREATE OR REPLACE FUNCTION cosine_similarity(vec1 JSONB, vec2 JSONB)
RETURNS FLOAT AS $$
DECLARE
    dot_product FLOAT := 0;
    norm1 FLOAT := 0;
    norm2 FLOAT := 0;
    key TEXT;
    val1 FLOAT;
    val2 FLOAT;
BEGIN
    -- Check if vectors are arrays
    IF jsonb_typeof(vec1) = 'array' AND jsonb_typeof(vec2) = 'array' THEN
        -- Handle array format
        FOR i IN 0..jsonb_array_length(vec1)-1 LOOP
            val1 := (vec1->>i)::FLOAT;
            val2 := (vec2->>i)::FLOAT;
            dot_product := dot_product + (val1 * val2);
            norm1 := norm1 + (val1 * val1);
            norm2 := norm2 + (val2 * val2);
        END LOOP;
    ELSE
        -- Handle object format (sparse vectors)
        FOR key IN SELECT jsonb_object_keys(vec1) LOOP
            val1 := (vec1->>key)::FLOAT;
            val2 := COALESCE((vec2->>key)::FLOAT, 0);
            dot_product := dot_product + (val1 * val2);
            norm1 := norm1 + (val1 * val1);
        END LOOP;

        FOR key IN SELECT jsonb_object_keys(vec2) LOOP
            val2 := (vec2->>key)::FLOAT;
            norm2 := norm2 + (val2 * val2);
        END LOOP;
    END IF;

    IF norm1 = 0 OR norm2 = 0 THEN
        RETURN 0;
    END IF;

    RETURN dot_product / (sqrt(norm1) * sqrt(norm2));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to calculate hybrid search score
CREATE OR REPLACE FUNCTION hybrid_search_score(
    dense_similarity FLOAT,
    sparse_similarity FLOAT,
    alpha FLOAT DEFAULT 0.7
) RETURNS FLOAT AS $$
BEGIN
    -- Alpha controls the balance: 1.0 = pure dense, 0.0 = pure sparse
    RETURN (alpha * dense_similarity) + ((1 - alpha) * sparse_similarity);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to update access statistics
CREATE OR REPLACE FUNCTION update_chunk_access() RETURNS TRIGGER AS $$
BEGIN
    NEW.last_accessed = NOW();
    NEW.access_count = OLD.access_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updating access stats
DROP TRIGGER IF EXISTS update_chunk_access_trigger ON document_chunks;
CREATE TRIGGER update_chunk_access_trigger
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    WHEN (OLD.last_accessed IS DISTINCT FROM NEW.last_accessed)
    EXECUTE FUNCTION update_chunk_access();