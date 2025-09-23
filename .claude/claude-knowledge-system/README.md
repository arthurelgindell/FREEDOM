# Claude Code Knowledge System (CCKS)

## Overview
A GPU-accelerated, in-memory knowledge database exclusively for Claude Code that:
- Reduces API token consumption by 80%+
- Uses Apple M3 Ultra's unified memory for instant access
- Persists context across sessions
- Learns from every interaction

## Architecture

### Memory Allocation (Recommended)
- **Active Memory Pool**: 50GB (10% of total RAM)
- **GPU Vectors**: 20GB (Metal-optimized embeddings)
- **Context Cache**: 20GB (recent conversations & solutions)
- **Pattern Database**: 10GB (learned code patterns)

### Components

1. **Vector Engine** (Metal-accelerated)
   - 768-dim embeddings (compatible with nomic-embed-text)
   - Cosine similarity search in GPU
   - Sub-millisecond query times

2. **Context Cache**
   - Last 100 conversations
   - Solution patterns
   - Error resolutions
   - Command history

3. **Pattern Recognition**
   - Common fix sequences
   - Project-specific conventions
   - Frequently accessed files
   - Optimal tool chains

4. **Persistence Layer**
   - Auto-flush every 2 minutes (high velocity mode)
   - Session snapshots
   - Incremental backups
   - Fast recovery on startup

## Performance Targets

| Operation | Target | Method |
|-----------|--------|--------|
| Query Similar Context | <1ms | GPU vector search |
| Load Full Context | <100ms | Memory-mapped files |
| Save Checkpoint | <500ms | Async background flush (every 2 min) |
| Pattern Match | <5ms | In-memory B-tree |
| Token Reduction | 80%+ | Context reuse |

## API Token Optimization

### Before CCKS
- Every query: Full context upload (4000+ tokens)
- Repeated solutions: Re-explained (2000+ tokens)
- Pattern recognition: Manual (1000+ tokens)

### With CCKS
- Similar query detected: Reference ID only (50 tokens)
- Known solution: Delta update (200 tokens)
- Pattern matched: Template application (100 tokens)

## Storage Structure

```
~/.claude/claude-knowledge-system/
├── vectors/
│   ├── embeddings.metal     # GPU-optimized vectors
│   ├── index.faiss          # FAISS index for CPU fallback
│   └── metadata.json        # Vector metadata
├── context/
│   ├── sessions/            # Conversation history
│   ├── solutions/           # Proven fixes
│   └── patterns/            # Learned patterns
├── cache/
│   ├── recent.db           # SQLite for quick lookups
│   ├── commands.log        # Command history
│   └── errors.log          # Error patterns
└── config/
    ├── memory.conf         # Memory allocation
    ├── flush.conf          # Persistence intervals
    └── gpu.conf            # Metal optimization
```

## Benefits

1. **Instant Context Recovery**: No need to re-explain projects
2. **Smart Suggestions**: Based on similar past queries
3. **Error Memory**: Never repeat the same mistake
4. **Pattern Learning**: Adapts to your coding style
5. **Massive Token Savings**: 80%+ reduction in API usage