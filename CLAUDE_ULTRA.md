# CLAUDE_ULTRA.md - Optimized for Claude Code Ultra & Huge Projects

## 🚀 ULTRA-CRITICAL: START HERE EVERY SESSION

```bash
# INSTANT CONTEXT RECOVERY (5 seconds)
./freedom-recover  # Loads complete system state
cat SESSION_SUMMARY_*.md | tail -1  # Get latest work context

# IF RECOVERY FAILS:
docker ps --format "table {{.Names}}\t{{.Status}}"
make health || echo "DEGRADED MODE"
```

## ⚡ FREEDOM Prime Directive

**FUNCTIONAL REALITY ONLY** - If it doesn't run, it doesn't exist.

Quick Verification Chain:
```bash
timeout 5 make health && echo "✓ SYSTEM READY" || echo "✗ CHECK SERVICES"
```

## 🎯 ULTRA COMMANDS (One-Liners)

```bash
# SERVICE CONTROL
make up              # Start everything
make down            # Stop everything
make verify          # Full test suite (or skip if slow)
docker ps -q         # Quick status (returns IDs if running)

# INSTANT DEBUGGING
docker-compose logs --tail=20 api-gateway | grep ERROR
docker exec freedom-postgres-1 psql -U freedom -c "\dt" -d techknowledge

# CONTEXT PERSISTENCE
./freedom-save       # Save state before ending session
```

## 🏗️ Service Priority Matrix

### TIER 1: CRITICAL (Must Run)
- PostgreSQL (5432): `docker-compose up -d postgres`
- LM Studio (1234): Host service, check with `curl -s localhost:1234/v1/models`

### TIER 2: IMPORTANT (Graceful Degradation)
- RAG API (5003): `cd services/rag_chunker && python3 rag_api.py`
- Redis (6379): `docker-compose up -d redis`
- API Gateway (8080): `docker-compose up -d api-gateway`

### TIER 3: OPTIONAL
- All other services can fail without breaking core functionality

## 📊 Performance Baselines

| Component | Target | Command |
|-----------|--------|---------|
| Health Check | <5s | `time make health` |
| RAG Query | <250ms | `curl -s localhost:5003/health` |
| DB Query | <50ms | `docker exec freedom-postgres-1 psql -c "SELECT 1"` |

## 🔍 Smart Search Patterns

```bash
# CODEBASE NAVIGATION (for huge projects)
services/*/main.py       # All service entry points
**/*test*.py            # All tests
documents/*_2025*       # Recent docs only
*.{md,txt,json}         # Documentation files
```

## 🤖 MCP Servers (Enhanced Claude Integration)

```bash
# QUICK CHECK
claude mcp list | grep -E "rag|postgres|redis" || echo "CONFIGURE MCP"

# AUTO-START DEPENDENCIES
docker-compose up -d postgres redis && \
cd services/rag_chunker && python3 rag_api.py &
```

## ⚠️ FAILURE PROTOCOL

```bash
# INSTANT DIAGNOSIS
bash -c '
  echo "=== SERVICE STATUS ==="
  docker ps --format "table {{.Names}}\t{{.Status}}" | head -5
  echo "=== LAST ERRORS ==="
  docker-compose logs --tail=10 2>&1 | grep -E "ERROR|FAIL|error" || echo "No errors"
  echo "=== RECOVERY OPTIONS ==="
  echo "1. make clean && make up"
  echo "2. ./freedom-recover"
  echo "3. docker-compose restart [service]"
'
```

## 🏃 Quick Wins Database

```sql
-- Get all tech specs (instant)
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -t -c "
  SELECT COUNT(*) || ' specs across ' || COUNT(DISTINCT technology_id) || ' technologies'
  FROM specifications;
"

-- Search anything (pattern)
docker exec freedom-postgres-1 psql -U freedom -d techknowledge -c "
  SELECT t.name, s.component_name
  FROM specifications s
  JOIN technologies t ON s.technology_id = t.id
  WHERE specification::text ILIKE '%SEARCH_TERM%'
  LIMIT 5;
"
```

## 🛠️ Development Shortcuts

```bash
# ADD TO ~/.bashrc or ~/.zshrc:
alias fup='docker-compose up -d && make health'
alias fdown='docker-compose down'
alias flogs='docker-compose logs -f --tail=50'
alias ftest='make verify || echo "CHECK FAILURES"'
alias fdb='docker exec -it freedom-postgres-1 psql -U freedom -d techknowledge'
alias frag='cd /Volumes/DATA/FREEDOM/services/rag_chunker && python3'
```

## 📝 Critical Rules

1. **NEVER** claim success without: `make health` passing
2. **ALWAYS** run `./freedom-recover` on new sessions
3. **PREFER** `docker exec` over complex queries
4. **UPDATE** README.md after changes (or face chaos)
5. **USE** python3, never python

## 🚨 Emergency Recovery

```bash
# NUCLEAR OPTION (full reset)
docker-compose down -v && \
docker-compose up -d postgres && \
sleep 5 && \
./scripts/init_db.sh && \
docker-compose up -d

# QUICK FIX (most issues)
docker-compose restart && sleep 10 && make health
```

## 📊 What's Actually Running?

Current System (as of session):
- 702 specifications across 22 technologies
- 3 test RAG chunks (expandable to thousands)
- 6 MCP servers configured
- LM Studio: qwen3-next-80b (50-80 tok/s)
- Truth Engine: Session persistence active

## 💡 Ultra Tips

1. **Session Recovery**: Always start with `./freedom-recover`
2. **Parallel Commands**: Use `&&` for speed, `;` for safety
3. **Quick Validation**: `docker ps -q | wc -l` should return 5+
4. **MCP First**: Use MCP tools over bash when available (10x faster)
5. **Pattern Match**: Use glob patterns to reduce file reads

---
*Optimized for Claude Code Ultra - Maximum efficiency, minimum overhead*
*Last Updated: 2025-09-22 (Session persistence implemented)*