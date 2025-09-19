# FREEDOM Knowledge Base Service

Production-ready knowledge base service with vector search capabilities, salvaged and enhanced from the proven techknowledge system.

## Features

- **Async PostgreSQL** with pgvector for vector similarity search
- **FastAPI** endpoints for ingestion and querying
- **OpenAI embeddings** for semantic search
- **Docker containerization** with health checks
- **Performance monitoring** targeting <800ms p99 at 10 RPS
- **Bulletproof operation** with comprehensive smoke tests

## Quick Start

1. **Set environment variables:**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export POSTGRES_PASSWORD="your-password"
   ```

2. **Run the service:**
   ```bash
   cd /Volumes/DATA/FREEDOM/services/kb
   ./run.sh
   ```

3. **Verify operation:**
   - Service: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## API Endpoints

### POST /ingest
Ingest technical specifications with automatic embedding generation.

```json
{
  "technology_name": "kubernetes",
  "version": "1.28",
  "component_type": "api",
  "component_name": "Pod",
  "specification": { "apiVersion": "v1", ... },
  "source_url": "https://kubernetes.io/docs/...",
  "confidence_score": 0.95
}
```

### POST /query
Query the knowledge base using semantic vector search.

```json
{
  "query": "How to create a Pod in Kubernetes?",
  "limit": 10,
  "similarity_threshold": 0.7,
  "technology_filter": "kubernetes"
}
```

### GET /health
Comprehensive health check including database and pgvector status.

### GET /stats
Service statistics and performance metrics.

## Architecture

- **Database Layer**: Async PostgreSQL with pgvector extension
- **Embedding Service**: OpenAI text-embedding-ada-002 model
- **API Layer**: FastAPI with structured logging
- **Container**: Docker with health checks and security

## Performance

- Target: <800ms p99 response time at 10 RPS
- Connection pooling: 5-25 connections
- Timeout: 30s command timeout
- Health checks every 30s

## Verification

The service includes comprehensive smoke tests that verify:
- Health check functionality
- Specification ingestion with embeddings
- Vector similarity search
- Performance baseline (10 concurrent queries)
- Statistics endpoint

Run tests manually:
```bash
python test_smoke.py
```

## Development

### Local Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### Docker Development
```bash
docker-compose up --build
```

## Database Schema

Uses the enhanced PostgreSQL schema from `/Volumes/DATA/FREEDOM/config/init.sql` with:
- Technologies registry
- Specifications with vector embeddings
- Usage tracking for analytics
- Health monitoring tables

## Security

- Non-root container user
- Input validation with Pydantic
- SQL injection protection with parameterized queries
- CORS middleware configured
- Environment-based configuration