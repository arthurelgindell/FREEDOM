# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Philosophy: FREEDOM Prime Directive

**FUNCTIONAL REALITY ONLY** - If it doesn't run, it doesn't exist.

Before declaring anything real, it must:
- EXECUTE: Run without fatal errors
- PROCESS: Accept and handle real input
- PRODUCE: Generate meaningful, usable output
- INTEGRATE: Connect and exchange with other systems
- DELIVER: Provide measurable value

## Essential Commands

### Development & Testing
```bash
# Start all services
make up
# or
docker-compose up --build

# Check service health
make health

# Run comprehensive verification (required before PRs)
make verify  # Runs health, smoke-test, integration-test, performance-test, metrics-check

# Run individual test suites
make smoke-test         # Basic functionality
make integration-test   # Service-to-service communication
make performance-test   # Performance benchmarks
pytest tests/unit/      # Unit tests
pytest tests/integration/  # Integration tests

# RAG system testing
cd services/rag_chunker
python3 test_e2e_rag.py  # End-to-end RAG tests
```

### Service Management
```bash
# Stop services
make down

# Clean everything (volumes too)
make clean

# View logs
make logs
# or
docker-compose logs -f [service-name]

# Access service shells
make shell-api  # API gateway shell
make shell-db   # PostgreSQL shell
```

### Local Development (without Docker)
```bash
# MLX server (port 8000)
source .venv/bin/activate
python -m mlx_vlm.server --model ./models/portalAI/UI-TARS-1.5-7B-mlx-bf16 --port 8000

# RAG API (port 5003)
cd services/rag_chunker
python3 rag_api.py

# LM Studio (port 1234) - fallback for MLX
# Start LM Studio GUI and load UI-TARS-1.5-7B model
```

## Architecture Overview

### Service Topology (Docker Compose)
- **API Gateway** (8080): Central orchestration, authentication, routing
- **PostgreSQL** (5432): Main database with pgvector extension
- **MLX Proxy** (8001): Proxy to host MLX server, with LM Studio fallback
- **Knowledge Base Service**: Internal vector storage and retrieval
- **TechKnowledge** (8002): Technical documentation API
- **Castle GUI** (3000): Next.js frontend
- **RAG System** (5003): Document chunking and retrieval
- **Router Service** (8003): Intelligent crawl task routing
- **Redis** (6379): Queue management and caching
- **Firecrawl** (8004): Web scraping service
- **Playwright Worker**: Browser automation for authenticated scraping

### Key Architectural Patterns
1. **Service Communication**: Internal Docker network (freedom_default)
2. **Authentication**: X-API-Key header validation at API Gateway
3. **Fallback Strategy**: MLX → LM Studio → Degraded mode
4. **Database Strategy**: Multiple PostgreSQL databases (freedom_kb, techknowledge)
5. **Embedding Pipeline**: LM Studio (local, fast) → OpenAI → Gemini → Fail

### RAG System Architecture
- **Database**: PostgreSQL `techknowledge` with pgvector
- **Embedding Model**: LM Studio nomic-embed-text (768-dim, 16.2x faster than OpenAI)
- **Search**: Hybrid (dense vectors + sparse keyword vectors)
- **Chunking**: 512-768 tokens with 64 token overlap
- **Caching**: Query result caching for performance

## Critical Service Dependencies

### Environment Variables Required
```bash
OPENAI_API_KEY      # For embeddings fallback (optional, system works without it)
FREEDOM_API_KEY     # API Gateway authentication (default: dev-key-change-in-production)
FIRECRAWL_API_KEY   # For Firecrawl service
```

### Host Services (must be running)
1. **MLX Server** (port 8000): Primary inference engine
2. **LM Studio** (port 1234): Fallback inference and embeddings
3. **PostgreSQL** databases must be initialized

## Testing Requirements

### Before ANY PR
```bash
# All must pass with exit code 0
./scripts/maintenance/checks.sh     # Lint + type checks
pytest -q tests/unit && pytest -q tests/integration
./scripts/maintenance/smoke.sh       # End-to-end minimal path
python core/truth_engine/self_test.py --strict
```

### Performance Targets
- API Gateway: ~3-7ms health check response
- MLX Generation: 400+ tokens/sec
- RAG Query: ~226ms average response
- Embedding Generation: 28.9ms (LM Studio)

## Project Structure Patterns

### Service Structure
Each service in `services/` follows:
```
service_name/
├── Dockerfile          # Container definition
├── requirements.txt    # Python dependencies
├── main.py            # FastAPI application
├── README.md          # Service documentation
└── tests/             # Service-specific tests
```

### Documentation Convention
All docs in `documents/` must end with `_YYYY-MM-DD_HHMM.ext`

### Code Conventions
- ONE .py file per function/feature
- Docker heavily leveraged for functional value
- All services must have health endpoints
- Responses must follow OpenAI format where applicable

## Common Development Tasks

### Adding New Embeddings
```bash
cd services/rag_chunker
python3 add_embeddings.py  # Processes chunks without embeddings
```

### Verifying Crawl Stack
```bash
bash scripts/verify_crawl_stack.sh  # Tests router, firecrawl, playwright
```

### Database Operations
```bash
# Connect to main database
PGPASSWORD=freedom_dev psql -h localhost -U freedom -d freedom_kb

# Check techknowledge tables
PGPASSWORD=freedom_dev psql -h localhost -U freedom -d techknowledge -c "\dt"
```

## Verification Evidence
All verification must produce timestamped artifacts:
`documents/reports/EVIDENCE_<component>_<YYYY-MM-DD_HHMM>.json`

## MCP (Model Context Protocol) Servers

The FREEDOM platform includes 6 MCP servers for enhanced Claude integration:

### 1. RAG MCP Server (`rag`)
**Location**: `/Volumes/DATA/FREEDOM/mcp-servers/rag-mcp/`
**Purpose**: Semantic search across 2,425 technical documents
**Tools**:
- `rag_query`: Natural language semantic search with context building
- `rag_search`: Simple keyword search
- `rag_stats`: System statistics and health
- `rag_explore`: Browse by technology/component
- `rag_explain`: Get detailed concept explanations
- `rag_compare`: Compare features across technologies

**Performance**: 226ms avg response (cached), 16.2x faster embeddings via LM Studio

### 2. PostgreSQL MCP Servers
**postgres-freedom**: System database (freedom_kb)
**techknowledge**: Specifications database
**Features**: Connection pooling, transaction support, schema awareness

### 3. Docker MCP (`docker`)
**Purpose**: Container management and monitoring
**Features**: Health checks, log analysis, service restart

### 4. HTTP API MCP (`http-api`)
**Purpose**: REST API testing
**Features**: Pre-configured auth headers, performance testing

### 5. Redis MCP (`redis`)
**Location**: `/Volumes/DATA/FREEDOM/mcp-servers/redis-mcp/`
**Purpose**: Queue and cache management
**Tools**: get/set operations, queue status, pattern matching

### Setup for Claude Code
```bash
# MCP servers are already configured in project
claude mcp list  # View all 6 servers

# Start required services
docker-compose up -d postgres redis
cd services/rag_chunker && python3 rag_api.py
```

### Using MCP in Claude
- Natural language queries: "Search for cursor vim mode documentation"
- Direct tool calls: MCP servers provide specialized tools
- Persistent connections: 10x faster than one-off commands
- Cached operations: Intelligent result caching

## Important Notes
- NEVER claim something works without verification
- Always run `make verify` before claiming completion
- Use functional testing over unit testing when possible
- Follow "If it doesn't run, it doesn't exist" principle
- Prefer editing existing files over creating new ones
- Don't create documentation unless explicitly requested