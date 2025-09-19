# Claude Code Knowledge System - Portable Installation

This package contains a complete Claude Code knowledge system that provides conversation continuity across sessions through a DuckDB-powered knowledge base.

## What's Included

- `claude_knowledge_db.py` - Core knowledge base management script
- `CLAUDE.md` - Persistent context instructions for Claude Code
- `claude_knowledge.db` - Pre-populated knowledge database (67 conversations, 3,266 messages)
- `README.md` - This installation guide

## Quick Installation

1. **Copy files to new system**:
   ```bash
   # Copy entire folder to your new system's home directory
   cp -r claude-knowledge-system ~/
   cd ~/claude-knowledge-system
   ```

2. **Install CLAUDE.md**:
   ```bash
   # Copy to any working directory where you'll use Claude Code
   cp CLAUDE.md ~/
   # OR to a specific project directory
   cp CLAUDE.md /path/to/your/project/
   ```

3. **Test the system**:
   ```bash
   python3 claude_knowledge_db.py stats
   ```

4. **Start Claude Code** in the directory with CLAUDE.md:
   ```bash
   claude
   ```

## System Requirements

- Python 3.7+
- DuckDB (auto-installed via pip if needed)
- Claude Code CLI

## How It Works

### Automatic Session Initialization
When Claude Code starts in a directory with `CLAUDE.md`, it automatically:
1. Loads the knowledge base status
2. Checks for relevant previous conversations
3. Provides context continuity without overwhelming output

### Knowledge Base Features
- **67 conversation sessions** with full searchable content
- **Topic extraction** and cross-referencing
- **Context memory** for recurring themes
- **Version control** - tracks evolution of understanding
- **Search capabilities** across all previous work

### Commands

```bash
# View database statistics
python3 claude_knowledge_db.py stats

# Search previous conversations
python3 claude_knowledge_db.py search "your search term"

# Get context for specific topics
python3 claude_knowledge_db.py context "topic name"

# Import new conversations (on original system)
python3 claude_knowledge_db.py ingest

# Update CLAUDE.md with latest context
python3 claude_knowledge_db.py generate-md >> CLAUDE.md
```

## Key Benefits

### 🔄 Session Continuity
- No more repeating setup explanations
- Builds on previous decisions and implementations
- Maintains context across Claude Code sessions

### 🧠 Intelligent Memory
- Remembers project architectures and decisions
- Tracks what tools and approaches work
- Avoids redundant discovery processes

### 📚 Knowledge Evolution
- Version-controlled understanding (doesn't just overwrite)
- Shows progression of problem-solving approaches
- Preserves valuable context from "failed" experiments

### 🚀 Productivity Gains
- Immediate context on session start
- No re-explaining established patterns
- Focus on current work, not historical context

## Established Context (from source system)

### Current Projects
- **Claudia GUI**: Desktop wrapper for Claude Code (Tauri + React + Rust)
- **DuckDB Knowledge System**: This system (67 sessions, 3,266 messages)
- **MCP Server Setup**: Claude Code as MCP server for external access

### Configuration
- **Model**: Opus 4.1 (claude-opus-4-1-20250805)
- **Platform**: macOS (adaptable to other systems)
- **Integration**: Works with both terminal Claude Code and Claudia GUI

### Known Solutions
- **Session fragmentation**: Solved with this knowledge system
- **Context loss**: Eliminated through CLAUDE.md + DuckDB integration
- **Redundant summaries**: Configured to avoid repetitive startup content

## Customization

### For New Systems
1. Update paths in `claude_knowledge_db.py` if needed
2. Modify `CLAUDE.md` to reflect new system configuration
3. Run `ingest` to import new conversations as they occur

### Adding to Existing Projects
- Copy `CLAUDE.md` to project root
- Keep `claude_knowledge_db.py` and database in accessible location
- Reference via relative paths if needed

## Troubleshooting

### Database Issues
```bash
# Check database integrity
python3 claude_knowledge_db.py stats

# Backup before changes
cp claude_knowledge.db claude_knowledge.db.backup
```

### Missing Dependencies
```bash
# Install DuckDB if needed
pip install duckdb
```

### Path Issues
- Ensure `claude_knowledge_db.py` is executable
- Update database path in script if moved
- Check CLAUDE.md references correct paths

## Migration Notes

This knowledge base contains context from:
- macOS system (adaptable)
- Homebrew package management (adjust for your package manager)
- Specific project architectures (reference for similar setups)

The knowledge is broadly applicable but may reference system-specific details that should be adapted for your environment.

## Success Metrics

After installation, you should see:
- Claude Code auto-loads without repetitive setup questions
- References to previous conversations when relevant
- Faster problem-solving through accumulated knowledge
- Reduced redundant discovery of tools and approaches

---

*This system transforms Claude Code from session-isolated tool to persistent knowledge-building partner.*