# FREEDOM Session Management System

## Overview
Complete session persistence solution for Claude Code that prevents work loss and enables seamless recovery after session termination.

## Components

### 1. GitHub Actions Workflow
**File:** `.github/workflows/claude-session-persistence.yml`
- Runs on every push to capture state
- Creates recovery artifacts
- Uses macOS runners for compatibility
- Stores 30-day artifact history

### 2. Local Recovery Script
**Command:** `./freedom-recover`
- Downloads latest GitHub artifacts
- Checks all service states
- Queries knowledge database
- Generates recovery summary
- Provides quick action commands

### 3. Session Save Script
**Command:** `./freedom-save`
- Creates checkpoint before ending session
- Optional WIP commit creation
- Updates knowledge database
- Pushes to GitHub (optional)
- Generates recovery hints

### 4. Knowledge Database
**Location:** `claude-knowledge-system/`
- DuckDB-powered conversation storage
- Searchable history
- Topic extraction
- Context memory

## Workflow

### Starting a New Session
```bash
# 1. Run recovery to get context
./freedom-recover

# 2. Review the generated summary
cat .freedom/sessions/recovery-*.md

# 3. Start required services
make up
cd services/rag_chunker && python3 rag_api.py

# 4. Continue work
git checkout <your-branch>
```

### During Work
- Changes are tracked automatically
- GitHub Actions captures state on push
- Knowledge DB can be queried anytime:
  ```bash
  python3 claude-knowledge-system/claude_knowledge_db.py search "topic"
  ```

### Ending a Session
```bash
# 1. Save session state
./freedom-save

# 2. Follow prompts to:
#    - Create WIP commit
#    - Update knowledge DB
#    - Push to GitHub

# 3. Session checkpoint created at:
#    .freedom/sessions/checkpoint-*.md
```

### After Session Termination
When Claude session ends (thread limit, crash, etc.):

1. **Next session:** Run `./freedom-recover`
2. **Check checkpoint:** Review last saved state
3. **Download artifacts:** GitHub Actions preserves everything
4. **Resume work:** All context restored

## Quick Reference

### Essential Commands
```bash
# Save current session
./freedom-save

# Recover previous session
./freedom-recover

# Search knowledge base
cd claude-knowledge-system
python3 claude_knowledge_db.py search "RAG optimization"

# Check service health
make health

# View recent commits
git log --oneline -20

# Download GitHub artifacts
gh run download <run-id>
```

### File Locations
- **Session checkpoints:** `.freedom/sessions/checkpoint-*.md`
- **Recovery summaries:** `.freedom/sessions/recovery-*.md`
- **GitHub artifacts:** Downloaded via `gh run download`
- **Knowledge DB:** `claude-knowledge-system/claude_knowledge.db`
- **Recovery hints:** `.freedom/sessions/RECOVERY_HINTS.md`

## Benefits

1. **Zero Lost Work**
   - Every change tracked
   - Automatic GitHub backups
   - Local checkpoints

2. **Fast Recovery**
   - < 30 seconds to restore context
   - All services checked
   - Recent work summarized

3. **Knowledge Accumulation**
   - DuckDB stores all conversations
   - Searchable history
   - Pattern recognition

4. **Seamless Workflow**
   - Simple commands
   - Automated processes
   - Clear recovery path

## Troubleshooting

### GitHub CLI Not Authenticated
```bash
# Install GitHub CLI
brew install gh

# Authenticate
gh auth login
```

### Knowledge DB Empty
```bash
# Initialize database
cd claude-knowledge-system
python3 claude_knowledge_db.py stats

# Ingest conversations
python3 claude_knowledge_db.py ingest
```

### Services Not Starting
```bash
# Check Docker
docker info

# Start all services
make up

# Check individual service
docker logs <service-name>
```

### Recovery Script Fails
```bash
# Check permissions
chmod +x freedom-recover freedom-save

# Run with debug
bash -x ./freedom-recover
```

## Architecture

```
┌─────────────────────────┐
│   GitHub Actions        │
│   (Cloud Persistence)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Local Recovery        │
│   (freedom-recover)     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Knowledge Database    │
│   (DuckDB + Search)     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   Session Checkpoints   │
│   (.freedom/sessions/)  │
└─────────────────────────┘
```

## Next Steps

1. **Test the system:**
   ```bash
   ./freedom-save  # Save current state
   ./freedom-recover  # Test recovery
   ```

2. **Push to GitHub** to activate workflow:
   ```bash
   git add -A
   git commit -m "Add session management system"
   git push
   ```

3. **Monitor GitHub Actions:**
   - Visit: https://github.com/arthurelgindell/FREEDOM/actions
   - Check workflow runs
   - Download artifacts

## Summary

This system ensures that no work is ever lost due to Claude session termination. Every piece of code, every decision, and every test result is captured and can be instantly recovered in the next session.