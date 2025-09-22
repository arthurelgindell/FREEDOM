# Knowledge System Optimization Plan
**Date:** September 22, 2025
**Goal:** Highly efficient technical knowledge system that prevents missed steps

## Executive Summary
Create two complementary systems: TechKnowledge for pure technical reference and RAG for context-aware Q&A. They work together to ensure complete, accurate technical guidance.

## Current State Issues
1. **RAG System:** Has embedding dimension mismatch (768 vs 1536)
2. **TechKnowledge:** Database not initialized, service unhealthy
3. **Integration:** No unified access point
4. **Result:** Documentation gaps cause missed implementation steps

## Proposed Architecture

### System 1: TechKnowledge (Reference Library)
**Purpose:** Authoritative technical specifications for ALL technologies

**What It Stores:**
- API specifications
- Configuration parameters
- Type definitions
- Version matrices
- Performance characteristics
- Error codes

**Key Features:**
- Decontamination (removes opinions/tutorials)
- Version tracking (current + 2 previous)
- GitHub validation
- Sub-100ms query performance

**Example Entry:**
```json
{
  "tech": "Redis",
  "version": "7.2",
  "spec": "CONFIG SET maxmemory",
  "params": {
    "type": "bytes",
    "default": 0,
    "description": "Maximum memory Redis can use"
  }
}
```

### System 2: RAG (Q&A Engine)
**Purpose:** Answer "How do I..." questions with full project context

**What It Provides:**
- Context-aware answers
- Project-specific guidance
- Implementation steps
- Best practices (when technically mandated)

**Key Features:**
- LM Studio embeddings (16.2x faster)
- Hybrid search (dense + sparse)
- FREEDOM project awareness
- Reranking with MLX

**Example Query:**
```
Q: "How do I set up Redis caching for FREEDOM?"
A: [Combines Redis specs from TechKnowledge + FREEDOM architecture + implementation steps]
```

## Integration Strategy

### 1. Unified Access Layer
```python
@app.post("/knowledge/query")
async def unified_query(query: str, filters: Dict):
    # Classify query intent
    if is_specification_query(query):
        return techknowledge.get_spec(query)
    elif is_implementation_query(query):
        context = techknowledge.get_relevant_specs(query)
        return rag.answer_with_context(query, context)
    else:
        # Complex query - use both
        specs = techknowledge.get_specs(query)
        docs = rag.search(query)
        return combine_results(specs, docs)
```

### 2. Metadata Tagging
```sql
-- Single enhanced schema
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY,
    content TEXT,
    embedding vector(768),  -- LM Studio standard
    metadata JSONB,  -- {
                    --   "source": "techknowledge|rag",
                    --   "type": "spec|guide|example",
                    --   "technology": "PostgreSQL",
                    --   "version": "15.3",
                    --   "validated": true,
                    --   "decontaminated": true
                    -- }
    created_at TIMESTAMP
);
```

### 3. Smart Routing
```python
class KnowledgeRouter:
    def route(self, query):
        # Keywords that indicate specification queries
        spec_keywords = ["parameters", "config", "API", "type", "definition"]

        # Keywords that indicate how-to queries
        howto_keywords = ["how", "implement", "setup", "configure", "integrate"]

        if any(kw in query for kw in spec_keywords):
            return "techknowledge"
        elif any(kw in query for kw in howto_keywords):
            return "rag"
        else:
            return "both"
```

## Implementation Steps

### Phase 1: Fix Current Issues (Day 1)
1. ✅ RAG embedding dimension fix:
   - Re-embed with consistent 768-dim vectors
   - Or switch to 1536-dim model
2. ✅ Initialize TechKnowledge database
3. ✅ Test both systems independently

### Phase 2: Enhance Systems (Day 2-3)
1. ✅ Add metadata tagging to RAG
2. ✅ Implement TechKnowledge decontaminator
3. ✅ Create ingestion classifier

### Phase 3: Integration (Day 4-5)
1. ✅ Build unified API endpoint
2. ✅ Implement query router
3. ✅ Create context augmentation

### Phase 4: Testing (Day 6-7)
1. ✅ Test specification queries
2. ✅ Test implementation queries
3. ✅ Test complex combined queries
4. ✅ Verify no steps missed

## Success Metrics

### Functional Excellence
- **Query Response:** < 500ms for 95% of queries
- **Accuracy:** 100% correct technical specifications
- **Completeness:** Zero missed implementation steps
- **Coverage:** All FREEDOM technologies documented

### Simplicity
- **Single endpoint:** `/knowledge/query`
- **Unified search:** One query, complete answer
- **Clear separation:** Specs vs guides
- **No redundancy:** Each fact stored once

## Example Use Cases

### Case 1: Setting Up PostgreSQL
```
Query: "Configure PostgreSQL for FREEDOM production"

TechKnowledge provides:
- shared_buffers parameter specs
- max_connections limits
- pgvector requirements

RAG provides:
- FREEDOM-specific settings
- Docker configuration
- Integration with services

Combined Result:
Complete setup guide with exact parameters
```

### Case 2: Debugging Redis
```
Query: "Redis connection refused error"

TechKnowledge provides:
- Error code definitions
- Configuration parameters
- Network requirements

RAG provides:
- FREEDOM Redis setup
- Common issues
- Troubleshooting steps

Combined Result:
Precise diagnosis and solution
```

## Risk Mitigation

1. **Embedding Mismatch:** Standardize on 768-dim (LM Studio)
2. **Database Issues:** Use single PostgreSQL instance
3. **Performance:** Cache frequent queries
4. **Accuracy:** Validate against source code
5. **Maintenance:** Automated ingestion pipeline

## Conclusion

This plan delivers:
- ✅ **Simplicity:** Two clear systems, one access point
- ✅ **Efficiency:** LM Studio for speed, PostgreSQL for storage
- ✅ **Completeness:** No missed steps, full coverage
- ✅ **Value:** Both systems are high-value and used

The key insight: TechKnowledge and RAG aren't competing - they're complementary. TechKnowledge provides the "what", RAG provides the "how", and together they ensure nothing gets missed.

---
*Next Step: Exit planning mode and begin implementation*