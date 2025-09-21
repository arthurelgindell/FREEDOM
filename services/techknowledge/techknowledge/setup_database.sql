-- TechKnowledge Database Setup
-- Pure technical knowledge system for FREEDOM

-- Create dedicated database
CREATE DATABASE techknowledge;

-- Connect to techknowledge database
\c techknowledge;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Performance optimization for 512GB RAM system
ALTER SYSTEM SET shared_buffers = '128GB';
ALTER SYSTEM SET effective_cache_size = '384GB';
ALTER SYSTEM SET work_mem = '2GB';
ALTER SYSTEM SET maintenance_work_mem = '16GB';
ALTER SYSTEM SET max_parallel_workers = 32;
ALTER SYSTEM SET max_parallel_workers_per_gather = 16;

-- Main technology registry
CREATE TABLE technologies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL, -- 'language', 'framework', 'database', 'tool', 'protocol'
    official_url TEXT NOT NULL,
    github_repo TEXT,
    documentation_url TEXT,
    api_spec_url TEXT, -- OpenAPI/Swagger if available
    release_feed_url TEXT, -- RSS/Atom for version tracking
    crawl_config JSONB, -- Specific extraction rules for this tech
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Version tracking with 3-version window
CREATE TABLE versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id) ON DELETE CASCADE,
    version_current TEXT NOT NULL,
    version_previous TEXT,
    version_legacy TEXT,
    current_released DATE,
    previous_released DATE,
    legacy_released DATE,
    current_eol DATE, -- End of life date if known
    update_frequency INTERVAL, -- Detected release pattern
    last_checked TIMESTAMP DEFAULT NOW(),
    next_check TIMESTAMP DEFAULT NOW() + INTERVAL '1 day',
    UNIQUE(technology_id, version_current)
);

-- Pure technical specifications
CREATE TABLE specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    component_type TEXT NOT NULL, -- 'api', 'config', 'types', 'limits', 'protocols'
    component_name TEXT NOT NULL,
    specification JSONB NOT NULL, -- The pure technical data
    source_url TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('official_docs', 'github_source', 'api_spec', 'rfc')),
    source_checksum TEXT, -- Detect changes
    confidence_score FLOAT DEFAULT 1.0, -- 1.0 for official, lower for inferred
    extracted_at TIMESTAMP DEFAULT NOW(),
    last_verified TIMESTAMP DEFAULT NOW(),
    verification_status TEXT DEFAULT 'unverified' -- 'verified', 'failed', 'outdated'
);

-- Crawl history and source tracking
CREATE TABLE crawl_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    url_pattern TEXT, -- For matching documentation pages
    crawl_frequency INTERVAL DEFAULT '7 days',
    last_crawled TIMESTAMP,
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    extracted_specs_count INTEGER DEFAULT 0,
    decontamination_stats JSONB, -- Stats on filtered content
    active BOOLEAN DEFAULT true,
    UNIQUE(technology_id, url)
);

-- GitHub source validation
CREATE TABLE github_validations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID REFERENCES specifications(id) ON DELETE CASCADE,
    github_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    validation_type TEXT, -- 'source_match', 'implementation_example', 'config_default'
    matches BOOLEAN,
    discrepancies JSONB, -- Detailed diff if not matching
    validated_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking for aging/refresh
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID REFERENCES specifications(id) ON DELETE CASCADE,
    accessed_by TEXT NOT NULL, -- Agent or system name
    access_type TEXT, -- 'query', 'reference', 'implementation'
    access_context TEXT, -- What task/conversation triggered this
    accessed_at TIMESTAMP DEFAULT NOW(),
    was_useful BOOLEAN -- Feedback from Truth Engine
);

-- Decontamination audit trail
CREATE TABLE decontamination_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    crawl_source_id UUID REFERENCES crawl_sources(id) ON DELETE CASCADE,
    original_size INTEGER,
    cleaned_size INTEGER,
    removed_patterns JSONB, -- What was filtered out
    extracted_technical JSONB, -- What was kept
    contamination_score FLOAT, -- Percentage of content removed
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for Performance
-- Fast lookups
CREATE INDEX idx_tech_name ON technologies(name);
CREATE INDEX idx_specs_verification ON specifications(verification_status, last_verified);
CREATE INDEX idx_versions_next_check ON versions(next_check) WHERE next_check <= NOW();
CREATE INDEX idx_usage_aging ON usage_tracking(accessed_at) WHERE accessed_at < NOW() - INTERVAL '12 months';

-- Composite indexes for common queries
CREATE INDEX idx_tech_version_component ON specifications(technology_id, version, component_type);
CREATE INDEX idx_specification_gin USING gin (specification);
CREATE INDEX idx_component_name ON specifications(component_name);

-- Full text search on specifications
CREATE INDEX idx_spec_text_search ON specifications 
USING gin (to_tsvector('english', specification::text));

-- Usage tracking indexes
CREATE INDEX idx_accessed_at ON usage_tracking(accessed_at);
CREATE INDEX idx_specification_usage ON usage_tracking(specification_id, accessed_at);

-- Create update trigger for technologies table
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_technologies_modtime 
BEFORE UPDATE ON technologies 
FOR EACH ROW 
EXECUTE FUNCTION update_modified_column();
