-- RAG Vector Storage Schema for FREEDOM Platform
-- Leverages existing pgvector extension for hybrid search

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

    -- Vector embeddings
    dense_vector vector(1536),  -- OpenAI ada-002 embeddings
    sparse_vector JSONB,        -- BM25 term frequencies

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
CREATE INDEX IF NOT EXISTS idx_chunks_dense_vector ON document_chunks
    USING ivfflat (dense_vector vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_spec_id ON document_chunks(specification_id);
CREATE INDEX IF NOT EXISTS idx_chunks_technology ON document_chunks(technology_name);
CREATE INDEX IF NOT EXISTS idx_chunks_component ON document_chunks(component_type, component_name);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON document_chunks(content_hash);

-- GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_chunks_text_search ON document_chunks
    USING gin(to_tsvector('english', chunk_text));

-- Index for sparse vector JSONB
CREATE INDEX IF NOT EXISTS idx_chunks_sparse ON document_chunks USING gin(sparse_vector);

-- Query logs for improving retrieval
CREATE TABLE IF NOT EXISTS rag_query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_text TEXT NOT NULL,
    query_embedding vector(1536),

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
    embedding_vector vector(1536),

    -- Cache management
    hit_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days',

    created_at TIMESTAMP DEFAULT NOW()
);

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