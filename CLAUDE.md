# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CCKS - OPTIONAL Claude Enhancement (NOT REQUIRED)

**SEPARATION DIRECTIVE: CCKS is OPTIONAL - FREEDOM must work 100% without it**
See: CCKS_SEPARATION_DIRECTIVE.md for mandatory separation rules

**IF AVAILABLE (check first):**
```bash
# OPTIONAL optimization - skip if not present
if [ -f ~/.claude/ccks ]; then
    ~/.claude/ccks stats > /dev/null 2>&1
    ~/.claude/ccks query "FREEDOM" > /dev/null 2>&1
fi
# Continue with FREEDOM regardless
```

**NEVER CREATE DEPENDENCIES ON CCKS**
- FREEDOM operates independently
- CCKS may be deleted at any time
- All operations must have non-CCKS paths

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
# LM Studio (port 1234) - PRIMARY inference engine
# Start LM Studio GUI and load qwen/qwen3-next-80b model
# Also provides embeddings via nomic-embed-text-v1.5

# RAG API (port 5003)
cd services/rag_chunker
python3 rag_api.py

# MLX server (port 8000) - NOT CURRENTLY USED
# Would run: python -m mlx_vlm.server --model [model] --port 8000
```

## Architecture Overview

### Service Topology (Docker Compose)
- **API Gateway** (8080): Central orchestration, authentication, routing
- **PostgreSQL** (5432): Main database with pgvector extension
- **MLX Proxy** (8001): Proxy to host MLX server, with LM Studio fallback
- **Knowledge Base Service** (8000): Vector storage and retrieval
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
3. **Inference Strategy**: LM Studio (primary) → Degraded mode (MLX not running)
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
1. **LM Studio** (port 1234): Primary inference (qwen3-next-80b) and embeddings
2. **PostgreSQL** databases must be initialized (freedom_kb, techknowledge)
3. **MLX Server** (port 8000): Currently not running (optional)

## Testing Requirements

### Before ANY PR
```bash
# Note: Some test scripts referenced don't exist
# ./scripts/maintenance/checks.sh - MISSING
# ./scripts/maintenance/smoke.sh - MISSING
pytest -q tests/unit && pytest -q tests/integration  # If tests exist
python3 core/truth_engine/self_test.py --strict  # Use python3
```

### Performance Targets
- API Gateway: ~3-7ms health check response
- LM Studio Generation: 50-80 tokens/sec (qwen3-next-80b)
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
# Query main database (freedom_kb)
docker exec freedom-postgres-1 psql -U freedom -d freedom_kb -c "SELECT * FROM technologies;"

# Query techknowledge database (702 specifications, 22 technologies)
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -c "SELECT * FROM specifications WHERE technology_id = (SELECT id FROM technologies WHERE name = 'anthropic');"

# Interactive database shell
docker exec -it freedom-postgres-1 psql -U freedom -d techknowledge

# List all tables
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -c "\dt"

# Search specifications by content
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -c "SELECT t.name, s.component_name FROM specifications s JOIN technologies t ON s.technology_id = t.id WHERE specification::text ILIKE '%search_term%';"

# Note: techknowledge service (port 8002) only provides /health endpoint - use direct database queries
```

## Verification Evidence
All verification must produce timestamped artifacts:
`documents/reports/EVIDENCE_<component>_<YYYY-MM-DD_HHMM>.json`

## MCP (Model Context Protocol) Servers

The FREEDOM platform includes 6 MCP servers for enhanced Claude integration:

### 1. RAG MCP Server (`rag`)
**Location**: `/Volumes/DATA/FREEDOM/mcp-servers/rag-mcp/`
**Purpose**: Semantic search across technical documents (currently 3 test chunks)
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

## Available AI Models

### Language Models (via LM Studio - Port 1234)
| Model | Parameters | Purpose | Memory |
|-------|------------|---------|--------|
| **qwen/qwen3-next-80b** | 80B | Primary inference, SOTA reasoning | ~40GB |
| **foundation-sec-8b** | 8B | Security analysis | 8GB |
| **qwen3-30b-a3b-instruct** | 30B | Fast alternative inference | 12.8GB |
| **nomic-embed-text-v1.5** | - | 768-dim embeddings | 2GB |

### Model Selection
- **General Tasks**: qwen3-next-80b (primary, 50-80 tokens/sec)
- **Security Analysis**: foundation-sec-8b for specialized security tasks
- **Fast Inference**: qwen3-30b for quicker responses with less memory
- **Embeddings**: nomic-embed-text-v1.5 (768-dim, 16.2x faster than OpenAI)

### Model Management
- Models are managed by LM Studio (not in repository)
- LM Studio handles model loading and switching
- Access via http://localhost:1234/v1/ endpoints

## Critical: README Synchronization

**ALWAYS UPDATE README.md AFTER ANY SUCCESSFUL IMPLEMENTATION**

Failure to update README causes:
- Reimplementation of existing features
- Destruction of working code
- Wasted development time

Before starting ANY work:
1. Check actual running services: `docker ps`, `make health`
2. Verify README matches reality
3. If mismatch found, UPDATE README FIRST

After completing work:
1. Update README with current state
2. Commit and push immediately
3. Never leave README outdated

See WORKFLOW_STANDARD.md for complete protocol.

## Important Notes
- NEVER claim something works without verification
- Always run `make verify` before claiming completion (if scripts exist)
- Use functional testing over unit testing when possible
- Follow "If it doesn't run, it doesn't exist" principle
- Prefer editing existing files over creating new ones
- Don't create documentation unless explicitly requested
- Use python3 instead of python for all commands