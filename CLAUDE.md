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

## Important Notes
- NEVER claim something works without verification
- Always run `make verify` before claiming completion
- Use functional testing over unit testing when possible
- Follow "If it doesn't run, it doesn't exist" principle
- Prefer editing existing files over creating new ones
- Don't create documentation unless explicitly requested