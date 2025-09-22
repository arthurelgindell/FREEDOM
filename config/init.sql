-- FREEDOM Knowledge Base Schema
-- Salvaged from proven techknowledge system

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Technologies registry
CREATE TABLE IF NOT EXISTS technologies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    official_url VARCHAR(500),
    github_repo VARCHAR(500),
    documentation_url VARCHAR(500),
    api_spec_url VARCHAR(500),
    release_feed_url VARCHAR(500),
    crawl_config JSONB,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Version tracking (3-version window)
CREATE TABLE IF NOT EXISTS versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id),
    version_current VARCHAR(50) NOT NULL,
    version_previous VARCHAR(50),
    version_legacy VARCHAR(50),
    current_released DATE,
    previous_released DATE,
    legacy_released DATE,
    current_eol DATE,
    update_frequency INTERVAL,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    next_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Technical specifications (core table)
CREATE TABLE IF NOT EXISTS specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id),
    version VARCHAR(50) NOT NULL,
    component_type VARCHAR(100) NOT NULL,
    component_name VARCHAR(255) NOT NULL,
    specification JSONB NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    source_checksum VARCHAR(64),
    confidence_score FLOAT DEFAULT 1.0,
    embedding vector(1536),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verification_status VARCHAR(20) DEFAULT 'unverified'
);

-- Crawl sources
CREATE TABLE IF NOT EXISTS crawl_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id),
    url VARCHAR(500) NOT NULL,
    url_pattern VARCHAR(500),
    crawl_frequency INTERVAL DEFAULT '7 days',
    last_crawled TIMESTAMP,
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    failure_count INTEGER DEFAULT 0,
    extracted_specs_count INTEGER DEFAULT 0,
    decontamination_stats JSONB,
    active BOOLEAN DEFAULT true
);

-- Usage tracking for aging
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    specification_id UUID REFERENCES specifications(id),
    accessed_by VARCHAR(100) NOT NULL,
    access_type VARCHAR(50) NOT NULL,
    access_context TEXT,
    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    was_useful BOOLEAN
);

-- Health check table
CREATE TABLE IF NOT EXISTS health_check (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_technologies_name ON technologies (name);
CREATE INDEX IF NOT EXISTS idx_technologies_category ON technologies (category);
CREATE INDEX IF NOT EXISTS idx_versions_technology ON versions (technology_id);
CREATE INDEX IF NOT EXISTS idx_specifications_technology ON specifications (technology_id);
CREATE INDEX IF NOT EXISTS idx_specifications_component ON specifications (component_type, component_name);
CREATE INDEX IF NOT EXISTS idx_specifications_embedding ON specifications
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_crawl_sources_technology ON crawl_sources (technology_id);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_spec ON usage_tracking (specification_id);

-- Insert initial data
INSERT INTO health_check (service, status) VALUES ('postgres', 'healthy');

-- Insert sample technology
INSERT INTO technologies (name, category, official_url, documentation_url)
VALUES
    ('kubernetes', 'orchestration', 'https://kubernetes.io', 'https://kubernetes.io/docs'),
    ('docker', 'containerization', 'https://docker.com', 'https://docs.docker.com'),
    ('postgresql', 'database', 'https://postgresql.org', 'https://www.postgresql.org/docs')
ON CONFLICT (name) DO NOTHING;

-- Create techknowledge database if it doesn't exist
-- This is for the TechKnowledge service
\c postgres
CREATE DATABASE techknowledge;
\c techknowledge

-- Apply same schema to techknowledge database
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Copy all table definitions (same as above)
CREATE TABLE IF NOT EXISTS technologies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    official_url VARCHAR(500),
    github_repo VARCHAR(500),
    documentation_url VARCHAR(500),
    api_spec_url VARCHAR(500),
    release_feed_url VARCHAR(500),
    crawl_config JSONB,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add other required tables for techknowledge
CREATE TABLE IF NOT EXISTS specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technology_id UUID REFERENCES technologies(id),
    version VARCHAR(50) NOT NULL,
    component_type VARCHAR(100) NOT NULL,
    component_name VARCHAR(255) NOT NULL,
    specification JSONB NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_type VARCHAR(100) NOT NULL,
    source_checksum VARCHAR(64),
    confidence_score FLOAT DEFAULT 1.0,
    embedding vector(1536),
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_verified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verification_status VARCHAR(20) DEFAULT 'unverified'
);

-- Switch back to freedom_kb
\c freedom_kb