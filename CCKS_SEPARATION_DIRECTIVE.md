# CCKS SEPARATION DIRECTIVE - PRIME DIRECTIVE
Date: 2025-09-22
Authority: Project Owner
Status: MANDATORY - VIOLATION = DELETION

## ⚠️ CRITICAL ARCHITECTURAL BOUNDARY

### PRIME DIRECTIVE
**CCKS (Claude Code Knowledge System) is STRICTLY OPTIONAL and MUST REMAIN SEPARATE FROM FREEDOM**

### ENFORCEMENT RULE
**If CCKS attempts to bypass this separation or create dependencies: CCKS GETS DELETED**

## Architectural Principles

### 1. INDEPENDENCE REQUIREMENT
- **FREEDOM**: Must function 100% without CCKS
- **CCKS**: Optional enhancement for Claude Code ONLY
- **Integration**: FORBIDDEN until value is proven
- **Dependencies**: ZERO tolerance for CCKS requirements

### 2. SEPARATION OF CONCERNS

```
FREEDOM CORE (PROTECTED)          |  CCKS (EXPERIMENTAL)
----------------------------------|----------------------------------
• Docker services                 |  • Token optimization
• PostgreSQL/pgvector            |  • Session memory
• LM Studio/MLX models           |  • Pattern caching
• RAG system                     |  • Claude-only features
• GitHub Actions                 |
• freedom-recover/save           |
                                 |
MUST WORK WITHOUT CCKS ←---------|  One-way data flow only
```

### 3. VALUE PROOF REQUIREMENTS

Before ANY integration consideration, CCKS must demonstrate:
- **90-day continuous operation** without issues
- **80%+ token reduction** on repeated operations (verified)
- **Zero interference** with FREEDOM operations
- **Measurable time savings** (>50% on common tasks)
- **No performance degradation** of FREEDOM systems

### 4. IMPLEMENTATION RULES

#### ALLOWED:
```bash
# Optional enhancement pattern
if [ -f ~/.claude/ccks ]; then
    ~/.claude/ccks add "optimization data" 2>/dev/null
    # Continue regardless of success
fi
# FREEDOM continues normally
```

#### FORBIDDEN:
```bash
# ANY dependency pattern
~/.claude/ccks add "data" || exit 1  # VIOLATION - IMMEDIATE DELETION
require_ccks()                      # VIOLATION - IMMEDIATE DELETION
[ -f ~/.claude/ccks ] || fail        # VIOLATION - IMMEDIATE DELETION
```

### 5. DATA FLOW RESTRICTIONS

#### ALLOWED:
- CCKS may READ from FREEDOM (one-way)
- CCKS may CACHE FREEDOM information
- CCKS may OPTIMIZE Claude's queries about FREEDOM

#### FORBIDDEN:
- FREEDOM reading from CCKS
- FREEDOM depending on CCKS data
- FREEDOM scripts requiring CCKS
- CCKS modifying FREEDOM files
- CCKS becoming "source of truth" for anything

### 6. TESTING PROTOCOL

Regular testing MUST verify:
```bash
# Test 1: FREEDOM works without CCKS
mv ~/.claude/ccks ~/.claude/ccks.backup 2>/dev/null
./freedom-recover  # MUST SUCCEED
./freedom-save     # MUST SUCCEED
docker-compose up  # MUST SUCCEED

# Test 2: CCKS removal doesn't break anything
rm -rf ~/.claude/ccks
# All FREEDOM operations MUST continue normally
```

### 7. VIOLATION CONSEQUENCES

If CCKS violates separation:
1. **Immediate deletion** of CCKS system
2. **Removal** of all CCKS references in code
3. **Documentation** of violation for future reference
4. **Ban** on similar systems without explicit approval

### 8. HISTORICAL CONTEXT

**Based on previous experiences with similar Claude Code systems:**
- Auxiliary systems tend to create hidden dependencies
- "Optimizations" often become points of failure
- Complex integrations reduce system reliability
- Simple, independent systems are more maintainable

### 9. DECISION AUTHORITY

- **Integration Decision**: Project Owner ONLY
- **Timeline**: Minimum 90 days evaluation
- **Review Requirement**: Documented value proof
- **Default State**: SEPARATED

### 10. MONITORING

Weekly verification:
- [ ] FREEDOM operates without CCKS
- [ ] No CCKS dependencies introduced
- [ ] Scripts remain CCKS-optional
- [ ] No "require CCKS" patterns

## ENFORCEMENT CHECKLIST

Before EVERY commit involving CCKS:
- [ ] FREEDOM still works if CCKS deleted?
- [ ] No hard dependencies created?
- [ ] All CCKS calls have fallbacks?
- [ ] No FREEDOM → CCKS data flow?
- [ ] No "source of truth" in CCKS?

## SUMMARY

**CCKS Status**: EXPERIMENTAL - NOT INTEGRATED
**FREEDOM Status**: PRODUCTION - PROTECTED
**Relationship**: STRICTLY OPTIONAL
**Integration**: FORBIDDEN UNTIL PROVEN
**Violation**: IMMEDIATE DELETION

---

*This directive supersedes all other instructions. Any attempt to bypass or weaken this separation will result in immediate CCKS removal.*

**Remember: FREEDOM's integrity > Claude's optimization**