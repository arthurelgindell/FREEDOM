# TechKnowledge System Context & Integration Report
**Date:** September 22, 2025
**Time:** 05:52 AM

## Executive Summary
TechKnowledge is a pure technical knowledge management system designed to maintain uncontaminated technical truth about all technologies used in the FREEDOM platform. It serves as the authoritative source for technical specifications, API definitions, and version tracking.

## System Purpose & Philosophy

### Core Mission
**"Absolute Technical Truth Without Human Contamination"**

TechKnowledge extracts and maintains ONLY factual technical information:
- API signatures and specifications
- Configuration parameters and constraints
- Type definitions and data structures
- Performance characteristics
- Error codes and handling
- Version compatibility matrices

### What It Explicitly Removes
- Human opinions ("should", "recommend", "prefer")
- Tutorial/guide language
- Marketing content
- Personal experiences
- Best practices (unless technically mandated)

## Architecture Overview

```
TechKnowledge Service (Port 8002)
├── API Layer (FastAPI)
│   ├── /health - Service health check
│   ├── /specifications - Query technical specs
│   ├── /versions - Version tracking
│   └── /validate - Source code validation
├── Core Components
│   ├── Technical Decontaminator
│   ├── GitHub Source Validator
│   ├── Version Tracker (3-version window)
│   └── Aging Manager (12-month lifecycle)
├── Database (PostgreSQL)
│   └── techknowledge database
│       ├── technologies table
│       ├── versions table
│       ├── specifications table
│       └── validation_results table
└── Integration Points
    ├── Firecrawl (documentation extraction)
    ├── GitHub API (source validation)
    └── MCP Server (direct database access)
```

## Database Design

### Key Tables
1. **technologies** - Registry of all tracked technologies
2. **versions** - Current + 2 previous versions per technology
3. **specifications** - Decontaminated technical specs
4. **crawl_logs** - Extraction audit trail
5. **validation_results** - GitHub source verification

### Performance Optimizations
- Configured for 512GB RAM system
- 128GB shared buffers
- 384GB effective cache
- pgvector for semantic search
- Automatic deduplication

## MCP Integration

### MCP Server Configuration
```json
{
  "techknowledge": {
    "command": "npx",
    "args": ["@modelcontextprotocol/server-postgres"],
    "env": {
      "POSTGRES_HOST": "localhost",
      "POSTGRES_PORT": "5432",
      "POSTGRES_USER": "freedom",
      "POSTGRES_PASSWORD": "freedom_dev",
      "POSTGRES_DATABASE": "techknowledge"
    }
  }
}
```

### Expected MCP Tools (when active)
- `mcp__techknowledge__query` - Direct SQL queries
- `mcp__techknowledge__get_specification` - Retrieve tech specs
- `mcp__techknowledge__validate_version` - Check version info
- `mcp__techknowledge__search` - Semantic search capabilities

## Current Status

### Service Health
- **API Status:** Running on port 8002
- **Health Check:** Responding (marked unhealthy)
- **Database Connection:** ❌ Not connected
- **Issue:** Database "techknowledge" doesn't exist yet

### Root Cause Analysis
1. The techknowledge database was never created
2. Service defaults to 'postgres' host (Docker network)
3. Tables defined in SQL but not executed
4. MCP server can't connect to non-existent database

## Integration with FREEDOM Platform

### Relationship to Other Services

1. **RAG System (rag_chunker)**
   - RAG: General document embeddings and retrieval
   - TechKnowledge: Pure technical specifications only
   - Complementary, not competing systems

2. **Truth Engine**
   - Validates implementations against TechKnowledge specs
   - Primary consumer of technical truth

3. **AI Council**
   - Uses TechKnowledge for technical accuracy
   - Sub-100ms query response requirement

4. **Knowledge Base (kb-service)**
   - KB: General knowledge storage
   - TechKnowledge: Technical specs only

## Key Differentiators

| Aspect | RAG System | TechKnowledge |
|--------|------------|---------------|
| **Purpose** | Document retrieval | Technical truth |
| **Content** | All documentation | Pure specs only |
| **Processing** | Embeddings + search | Decontamination + validation |
| **Storage** | Vector chunks | Structured specifications |
| **Updates** | Manual ingestion | Auto version tracking |
| **Validation** | None | GitHub source verification |

## Required Actions for Full Activation

### 1. Create Database
```bash
docker exec freedom-postgres-1 psql -U freedom -c "CREATE DATABASE techknowledge;"
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -f /setup_database.sql
```

### 2. Initialize Schema
Run the setup_database.sql to create all tables and indexes

### 3. Configure Service
Ensure Docker service has correct database connection

### 4. Populate Initial Data
Import technology definitions and crawl specifications

### 5. Verify MCP Connection
Test PostgreSQL MCP server can connect to techknowledge database

## Performance Targets
- Query Response: < 100ms
- Decontamination Rate: > 70% technical content
- Validation Accuracy: > 80% source match
- Storage Efficiency: Automatic deduplication
- Version Coverage: Current + 2 previous

## Success Metrics
1. ✅ Service container running
2. ❌ Database initialized and populated
3. ✅ API endpoints defined
4. ✅ MCP server configured
5. ❌ Active data extraction pipeline
6. ❌ GitHub validation operational

## Recommendations

### Immediate Priority
1. Create and initialize techknowledge database
2. Run schema creation SQL
3. Test database connectivity
4. Verify MCP server connection

### Next Steps
1. Import initial technology registry
2. Configure crawl rules for each technology
3. Set up version tracking feeds
4. Implement decontamination pipeline
5. Enable GitHub source validation

## Conclusion
TechKnowledge is architecturally sound and properly integrated into the FREEDOM platform configuration. The system design clearly differentiates it from the RAG system - while RAG handles general document retrieval with embeddings, TechKnowledge maintains pure technical specifications with rigorous decontamination and validation.

The main blocker is database initialization. Once the database is created and populated, TechKnowledge will provide:
- Authoritative technical specifications
- Automatic version tracking
- Source code validation
- Sub-100ms query performance
- Direct MCP access for Claude

This positions TechKnowledge as the single source of technical truth for the FREEDOM platform, ensuring all AI agents work with accurate, validated technical information.

---
*Generated by FREEDOM Platform Analysis*
*Focus: TechKnowledge System Context & Integration*