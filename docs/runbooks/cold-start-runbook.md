# FREEDOM Platform - Cold Start Runbook

## Overview
Complete setup procedures for establishing the FREEDOM platform from a clean environment. This runbook ensures any operator can deploy a fully functional system with zero hidden steps.

**Target Audience**: New operators, fresh deployments, disaster recovery
**Prerequisites**: macOS with Apple Silicon, Docker Desktop, Git
**Estimated Time**: 15-30 minutes

## Success Criteria
- ✅ All services running and healthy
- ✅ MLX model server operational at 40+ tokens/sec
- ✅ Knowledge base accessible and queryable
- ✅ Castle GUI responsive on http://localhost:3000
- ✅ End-to-end query workflow functional

---

## Phase 1: Environment Setup

### 1.1 System Requirements Verification
```bash
# Verify Apple Silicon Mac
uname -m
# Expected output: arm64

# Verify Docker Desktop running
docker --version
# Expected output: Docker version 24.x.x or higher

# Verify available disk space (minimum 20GB free)
df -h /
# Ensure >20GB available
```

### 1.2 Clone Repository
```bash
# Clone the FREEDOM platform
git clone <REPOSITORY_URL> /Volumes/DATA/FREEDOM
cd /Volumes/DATA/FREEDOM

# Verify repository structure
ls -la
# Expected: docker-compose.yml, Makefile, services/, models/, etc.
```

### 1.3 Environment Variables Setup
```bash
# Copy and configure environment variables
cp .env.example .env

# Edit environment variables (use your preferred editor)
nano .env
```

**Required Environment Variables:**
```bash
# API Keys (see API_KEYS.md for current keys)
OPENAI_API_KEY=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
FREEDOM_API_KEY=dev-key-change-in-production

# Database Configuration
POSTGRES_USER=freedom
POSTGRES_PASSWORD=freedom_dev
POSTGRES_DB=freedom_kb

# Service URLs (for local development)
KB_SERVICE_URL=http://kb-service:8000
MLX_SERVICE_URL=http://mlx-server:8000
```

**Verification Commands:**
```bash
# Check environment file exists and has required keys
grep -E "(OPENAI_API_KEY|FREEDOM_API_KEY)" .env
# Both keys should be present and non-empty
```

---

## Phase 2: MLX Model Setup

### 2.1 Verify MLX Model Availability
```bash
# Check UI-TARS model exists
ls -la models/portalAI/UI-TARS-1.5-7B-mlx-bf16/
# Expected: config.json, model files, tokenizer files

# Verify model integrity
du -sh models/portalAI/UI-TARS-1.5-7B-mlx-bf16/
# Expected: ~7-15GB total size
```

### 2.2 Test MLX Environment
```bash
# Activate Python environment
source .venv/bin/activate

# Test MLX import
python -c "import mlx.core as mx; print('MLX version:', mx.__version__)"
# Expected: MLX version: 0.x.x (no errors)

# Test MLX-VLM import
python -c "import mlx_vlm; print('MLX-VLM available')"
# Expected: MLX-VLM available
```

### 2.3 Alternative Model Download (if needed)
```bash
# If UI-TARS model is missing, download alternative
mkdir -p models/backup/
cd models/backup/

# Download lightweight alternative model
huggingface-cli download microsoft/Phi-3.5-mini-instruct \
  --local-dir ./phi-3.5-mini-instruct \
  --local-dir-use-symlinks False

# Update docker-compose.yml to point to backup model
sed -i '' 's|/app/models/portalAI/UI-TARS-1.5-7B-mlx-bf16|/app/models/backup/phi-3.5-mini-instruct|' docker-compose.yml
```

---

## Phase 3: Service Deployment

### 3.1 Database Initialization
```bash
# Start PostgreSQL first
docker-compose up -d postgres

# Wait for database to be ready
sleep 30

# Verify database health
docker-compose exec postgres pg_isready -U freedom -d freedom_kb
# Expected: freedom_kb:5432 - accepting connections
```

### 3.2 Build and Start All Services
```bash
# Build all services (initial build takes 5-10 minutes)
docker-compose build

# Start all services
docker-compose up -d

# Monitor startup logs
docker-compose logs -f
# Watch for "healthy" status on all services
```

### 3.3 Service Health Verification
```bash
# Use built-in health check
make health

# Manual health checks
curl -f http://localhost:8080/health
# Expected: {"status": "healthy", "services": {...}}

curl -f http://localhost:8000/docs > /dev/null && echo "✅ MLX service up"
# Expected: ✅ MLX service up

curl -f http://localhost:3000 > /dev/null && echo "✅ Castle GUI up"
# Expected: ✅ Castle GUI up
```

---

## Phase 4: Data Ingestion

### 4.1 Knowledge Base Initialization
```bash
# Check KB service is accepting connections
curl -X GET http://localhost:8000/health
# Expected: {"status": "healthy"}

# Initialize knowledge base schema
curl -X POST http://localhost:8000/admin/init-db
# Expected: {"message": "Database initialized successfully"}
```

### 4.2 Sample Data Ingestion
```bash
# Ingest sample documents
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "title": "FREEDOM Platform Test Document",
    "content": "This is a test document to verify the knowledge base ingestion workflow is functional.",
    "metadata": {"type": "test", "version": "1.0"}
  }'
# Expected: {"id": "...", "message": "Document ingested successfully"}
```

### 4.3 Ingestion Verification
```bash
# Verify document count
curl -X GET http://localhost:8000/documents/count
# Expected: {"total_documents": 1} or higher

# Test search functionality
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test document", "limit": 5}'
# Expected: Array of search results including test document
```

---

## Phase 5: End-to-End Testing

### 5.1 MLX Model Performance Test
```bash
# Test MLX inference performance
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello, please respond briefly."}],
    "max_tokens": 50,
    "temperature": 0.7
  }'
# Expected: Response with generated text and performance metrics
```

### 5.2 Complete Query Workflow
```bash
# Test full RAG pipeline through API Gateway
curl -X POST http://localhost:8080/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "query": "What is the FREEDOM platform?",
    "use_rag": true,
    "max_tokens": 100
  }'
# Expected: Contextual response using RAG
```

### 5.3 GUI Functionality Test
```bash
# Open Castle GUI in browser
open http://localhost:3000

# GUI should display:
# - Chat interface
# - Model selection dropdown
# - Settings panel
# - No error messages
```

---

## Phase 6: Performance Validation

### 6.1 Run Comprehensive Tests
```bash
# Execute all verification tests
make verify

# Expected output:
# 🧪 Running FREEDOM Platform Smoke Tests... ✅
# 🔗 Running FREEDOM Platform Integration Tests... ✅
# ⚡ Running FREEDOM Platform Performance Benchmarks... ✅
# 📊 Verifying Prometheus Metrics Endpoints... ✅
# 🎯 FREEDOM Platform Verification Complete
```

### 6.2 Performance Benchmarks
```bash
# Check MLX inference speed
python -c "
import time
import requests
start = time.time()
response = requests.post('http://localhost:8001/v1/chat/completions',
  json={'messages': [{'role': 'user', 'content': 'Count to 10'}], 'max_tokens': 50})
end = time.time()
print(f'Response time: {end-start:.2f}s')
print(f'Tokens/sec estimate: {50/(end-start):.1f}')
"
# Expected: >30 tokens/sec on Apple Silicon
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Docker Build Fails
**Symptoms**: Build errors during `docker-compose build`
**Solutions**:
```bash
# Clear Docker cache
docker system prune -f
docker builder prune -f

# Rebuild without cache
docker-compose build --no-cache

# Check available disk space
df -h /
```

#### Issue: MLX Service Won't Start
**Symptoms**: MLX health check fails
**Solutions**:
```bash
# Check model path exists
ls -la models/portalAI/UI-TARS-1.5-7B-mlx-bf16/

# Check MLX installation in container
docker-compose exec mlx-server python -c "import mlx.core; print('MLX OK')"

# Check container logs
docker-compose logs mlx-server

# Restart with clean state
docker-compose restart mlx-server
```

#### Issue: Database Connection Failed
**Symptoms**: KB service can't connect to postgres
**Solutions**:
```bash
# Check postgres is running
docker-compose ps postgres

# Verify postgres health
docker-compose exec postgres pg_isready -U freedom -d freedom_kb

# Check environment variables
docker-compose exec kb-service env | grep POSTGRES

# Reset database
docker-compose down -v
docker-compose up -d postgres
sleep 30
docker-compose up -d kb-service
```

#### Issue: Port Conflicts
**Symptoms**: "Port already in use" errors
**Solutions**:
```bash
# Check what's using ports
lsof -i :3000
lsof -i :8080
lsof -i :8000
lsof -i :5432

# Stop conflicting services or modify docker-compose.yml ports
# Example: Change "3000:3000" to "3001:3000"
```

#### Issue: Out of Memory
**Symptoms**: Services crash with OOM errors
**Solutions**:
```bash
# Check available memory
free -h

# Reduce MLX model size or use quantized model
# Edit docker-compose.yml MODEL_PATH to point to smaller model

# Increase Docker Desktop memory allocation
# Docker Desktop > Settings > Resources > Memory (recommend 8GB+)
```

### Performance Optimization

#### Slow Model Loading
```bash
# Pre-warm model cache
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}'

# Monitor model loading time
docker-compose logs mlx-server | grep -i "model loaded"
```

#### Database Query Optimization
```bash
# Check database performance
docker-compose exec postgres psql -U freedom -d freedom_kb -c "
  SELECT schemaname,tablename,attname,n_distinct,correlation
  FROM pg_stats WHERE tablename = 'documents';
"

# Rebuild indexes if needed
docker-compose exec postgres psql -U freedom -d freedom_kb -c "REINDEX DATABASE freedom_kb;"
```

---

## Success Validation Checklist

Before declaring cold start successful, verify:

- [ ] All 5 services show "healthy" status
- [ ] MLX model responds within 3 seconds
- [ ] Database accepts connections and queries
- [ ] Castle GUI loads without errors
- [ ] Sample document ingestion succeeds
- [ ] End-to-end query returns relevant results
- [ ] Performance tests pass with acceptable metrics
- [ ] No error messages in service logs

## Next Steps

After successful cold start:
1. Review [Operations Manual](operations-manual.md) for daily procedures
2. Configure production API keys if not already done
3. Set up monitoring and alerting (see Operations Manual)
4. Review [MLX Models Management](mlx-models-management.md) for optimization

---

**Document Version**: 1.0
**Last Updated**: 2025-09-19
**Tested On**: Apple Silicon macOS, Docker Desktop 4.x
**Average Completion Time**: 20 minutes