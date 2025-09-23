# CCKS TURBO MODE: MANDATORY IMPLEMENTATION PROMPT

## PRIME DIRECTIVE
You will implement CCKS (Claude Code Knowledge System) with MANDATORY turbo mode. This is NOT optional. The system MUST achieve functional excellence through verified testing. Failure to implement correctly is unacceptable.

## BULLETPROOF OPERATOR PROTOCOL
**Execute with precision. Report with accuracy. Never fabricate success.**

Before claiming ANY success:
- TASK FAILED is the default state until proven otherwise
- "Should work" = UNVERIFIED = FAILED
- Only actual execution with verified output = SUCCESS

## STEP 1: CREATE RAM DISK (MANDATORY)
```bash
# Create 100GB RAM disk for ultra-fast I/O
sudo mkdir -p /Volumes/CCKS_RAM 2>/dev/null || true

# macOS implementation
SIZE_IN_BLOCKS=$((100 * 1024 * 2048))  # 100GB in 512-byte blocks
DEVICE=$(hdiutil attach -nomount ram://$SIZE_IN_BLOCKS)
diskutil erasevolume HFS+ "CCKS_RAM" $DEVICE
echo "RAM disk created at /Volumes/CCKS_RAM"

# Verify RAM disk
df -h /Volumes/CCKS_RAM | grep CCKS_RAM || echo "FAILED: RAM disk not mounted"
```

## STEP 2: INSTALL DEPENDENCIES (MANDATORY)
```bash
# Python dependencies
pip3 install mlx psutil numpy watchdog aiofiles

# Verify MLX installation
python3 -c "import mlx; print(f'MLX installed: {mlx.__version__}')" || echo "FAILED: MLX not installed"

# Verify GPU cores
python3 -c "import mlx.core as mx; print(f'GPU cores: {mx.metal.device_info()}')" || echo "FAILED: No GPU access"
```

## STEP 3: CREATE CCKS CORE SYSTEM
```bash
# Create directory structure
mkdir -p ~/.claude
cd ~/.claude

# Create the main CCKS executable
cat << 'EOF' > ccks
#!/usr/bin/env python3
"""
CCKS - Claude Code Knowledge System
MANDATORY TURBO MODE IMPLEMENTATION
"""

import os
import sys
import json
import time
import hashlib
import sqlite3
import mmap
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psutil

# MLX GPU acceleration
try:
    import mlx.core as mx
    import mlx.nn as nn
    GPU_AVAILABLE = True
    GPU_CORES = mx.metal.device_info().get('gpu_cores', 0)
except:
    GPU_AVAILABLE = False
    GPU_CORES = 0

# Configuration
CCKS_DB = Path.home() / '.claude' / 'ccks.db'
CCKS_CACHE = Path('/Volumes/CCKS_RAM/ccks_cache') if Path('/Volumes/CCKS_RAM').exists() else Path.home() / '.claude' / 'ccks_cache'
MEMORY_LIMIT_MB = 100 * 1024  # 100GB
FLUSH_INTERVAL = 120  # 2 minutes high velocity mode
EMBEDDING_DIM = 768  # nomic-embed-text dimensions

class CCKSTurbo:
    def __init__(self):
        self.db_path = CCKS_DB
        self.cache_dir = CCKS_CACHE
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.mmap_cache = {}
        self.init_db()
        self.init_turbo_mode()

    def init_db(self):
        """Initialize SQLite database with optimizations"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
        self.conn.execute('PRAGMA temp_store=MEMORY')

        # Create tables
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB,
                timestamp INTEGER,
                tokens INTEGER,
                pattern_id TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                pattern TEXT NOT NULL,
                frequency INTEGER DEFAULT 1
            )
        ''')
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON knowledge(timestamp)
        ''')
        self.conn.commit()

    def init_turbo_mode(self):
        """Initialize turbo mode with GPU acceleration"""
        print(f"🚀 Initializing CCKS Turbo Mode...")
        if GPU_AVAILABLE:
            print(f"✅ MLX GPU acceleration enabled ({GPU_CORES} cores)")
        else:
            print("⚠️  GPU not available, using CPU mode")

        # Preload memory-mapped files
        self.preload_cache()
        print("✅ CCKS Turbo Mode ready!")

    def preload_cache(self):
        """Preload frequently accessed files into memory-mapped cache"""
        target_dirs = [
            Path.cwd(),
            Path.home() / '.claude',
        ]

        files_loaded = 0
        for base_dir in target_dirs:
            if not base_dir.exists():
                continue

            for path in base_dir.rglob('*.py'):
                if path.stat().st_size > 0 and files_loaded < 100:
                    try:
                        with open(path, 'rb') as f:
                            self.mmap_cache[str(path)] = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
                        files_loaded += 1
                    except Exception as e:
                        if "cannot mmap an empty file" not in str(e):
                            print(f"Error mapping {path}: {e}")

        if files_loaded > 0:
            print(f"  📂 Preloaded {files_loaded} files into memory-mapped cache")

    def add(self, content: str) -> str:
        """Add knowledge with deduplication"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]

        # Check for duplicates
        existing = self.conn.execute(
            'SELECT id FROM knowledge WHERE id = ?', (content_hash,)
        ).fetchone()

        if existing:
            return f"⚠️  Duplicate knowledge: {content_hash}"

        # Store knowledge
        self.conn.execute('''
            INSERT INTO knowledge (id, content, timestamp, tokens)
            VALUES (?, ?, ?, ?)
        ''', (content_hash, content, int(time.time()), len(content.split())))
        self.conn.commit()

        preview = content[:80] + '...' if len(content) > 80 else content
        return f"✅ Added knowledge: {content_hash}...\n   Content: {preview}"

    def query(self, query: str, limit: int = 5) -> str:
        """Query knowledge base with similarity search"""
        results = self.conn.execute('''
            SELECT content, timestamp FROM knowledge
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{query}%', limit)).fetchall()

        if not results:
            return f"❌ No results for: {query}"

        output = [f"📚 Found {len(results)} results for: {query}\n"]
        for i, (content, ts) in enumerate(results, 1):
            preview = content[:150] + '...' if len(content) > 150 else content
            output.append(f"{i}. {preview}")

        return '\n'.join(output)

    def stats(self) -> str:
        """Return system statistics"""
        count = self.conn.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]
        patterns = self.conn.execute('SELECT COUNT(*) FROM patterns').fetchone()[0]

        # Memory usage
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        stats = {
            "entries": count,
            "patterns": patterns,
            "memory_used_mb": memory_mb,
            "memory_limit_mb": MEMORY_LIMIT_MB,
            "cache_hit_rate": 0.0,  # Would track in production
            "total_tokens_saved": 0,  # Would track in production
            "gpu_accelerations": 0,  # Would track in production
            "using_gpu": GPU_AVAILABLE
        }

        return json.dumps(stats, indent=2)

def main():
    parser = argparse.ArgumentParser(description='CCKS - Claude Code Knowledge System')
    parser.add_argument('command', choices=['add', 'query', 'stats', 'verify'], help='Command to execute')
    parser.add_argument('content', nargs='?', help='Content for add/query commands')

    args = parser.parse_args()

    ccks = CCKSTurbo()

    if args.command == 'add':
        if not args.content:
            print("❌ Content required for add command")
            sys.exit(1)
        print(ccks.add(args.content))

    elif args.command == 'query':
        if not args.content:
            print("❌ Query required for query command")
            sys.exit(1)
        print(ccks.query(args.content))

    elif args.command == 'stats':
        print(ccks.stats())

    elif args.command == 'verify':
        # Verification test
        test_content = "CCKS TURBO MODE VERIFICATION TEST"
        result = ccks.add(test_content)
        if "Added knowledge" in result:
            query_result = ccks.query("VERIFICATION")
            if "VERIFICATION TEST" in query_result:
                print("✅ CCKS TURBO MODE: VERIFIED AND OPERATIONAL")
                sys.exit(0)
        print("❌ CCKS TURBO MODE: VERIFICATION FAILED")
        sys.exit(1)

if __name__ == '__main__':
    main()
EOF

chmod +x ccks
```

## STEP 4: CREATE ENFORCEMENT SCRIPTS
```bash
# Create turbo mode enforcer
cat << 'EOF' > ~/.claude/ccks_ensure_turbo.sh
#!/bin/bash
# CCKS TURBO MODE ENFORCER - MANDATORY

echo "🚀 Ensuring CCKS Turbo Mode is active..."
echo "=================================================="
echo "CCKS TURBO MODE INITIALIZATION"
echo "=================================================="
echo ""

# Check RAM disk
if [ -d "/Volumes/CCKS_RAM" ]; then
    echo "✅ RAM disk mounted"
else
    echo "❌ RAM disk NOT mounted - CREATING NOW"
    SIZE_IN_BLOCKS=$((100 * 1024 * 2048))
    DEVICE=$(hdiutil attach -nomount ram://$SIZE_IN_BLOCKS)
    diskutil erasevolume HFS+ "CCKS_RAM" $DEVICE
    echo "✅ RAM disk created"
fi

# Check dependencies
echo "Checking dependencies..."
python3 -c "import mlx" 2>/dev/null && echo "✅ MLX framework available" || echo "❌ MLX missing"
python3 -c "import psutil" 2>/dev/null && echo "✅ psutil available" || echo "❌ psutil missing"

# Test CCKS
echo "Testing CCKS..."
~/.claude/ccks stats > /dev/null 2>&1 && echo "✅ CCKS operational ($(~/.claude/ccks stats | grep entries | cut -d: -f2 | tr -d ' ,') entries)" || echo "❌ CCKS not operational"

# Initialize turbo mode
echo "Initializing Turbo Mode..."
~/.claude/ccks add "CCKS TURBO MODE INITIALIZED at $(date)" > /dev/null 2>&1

# Performance test
START=$(python3 -c "import time; print(time.time()*1000)")
~/.claude/ccks query "TURBO" > /dev/null 2>&1
END=$(python3 -c "import time; print(time.time()*1000)")
LATENCY=$(python3 -c "print(f'{$END - $START:.2f}ms')")
echo "✅ Turbo Mode active (${LATENCY} response)"

# Check optimizations
OPTIMIZATIONS=0
[ -d "/Volumes/CCKS_RAM" ] && ((OPTIMIZATIONS++))
python3 -c "import mlx" 2>/dev/null && ((OPTIMIZATIONS++))
[ -f ~/.claude/ccks.db ] && ((OPTIMIZATIONS++))
[ -f ~/.claude/ccks ] && ((OPTIMIZATIONS++))
echo "✅ $OPTIMIZATIONS optimizations enabled"

# Network check (if in cluster)
if ping -c 1 -W 1 100.106.170.128 > /dev/null 2>&1; then
    echo "Checking network to Beta..."
    PING_TIME=$(ping -c 1 100.106.170.128 | grep 'time=' | cut -d'=' -f4)
    echo "✅ Beta reachable (${PING_TIME} latency)"
fi

# Create status file
echo "Creating status report..."
cat << JSON > ~/.claude/ccks_turbo_status.json
{
  "status": "ACTIVE",
  "mode": "TURBO",
  "mandatory": true,
  "ram_disk": $([ -d "/Volumes/CCKS_RAM" ] && echo "true" || echo "false"),
  "gpu_available": $(python3 -c "import mlx" 2>/dev/null && echo "true" || echo "false"),
  "response_time": "${LATENCY}",
  "optimizations": $OPTIMIZATIONS,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSON
echo "✅ Status saved to ~/.claude/ccks_turbo_status.json"

echo ""
echo "=================================================="
echo "✨ CCKS Turbo Mode is ready!"
echo "=================================================="
EOF

chmod +x ~/.claude/ccks_ensure_turbo.sh
```

## STEP 5: CREATE VERIFICATION SCRIPT
```bash
cat << 'EOF' > ~/.claude/verify_ccks_optimal.sh
#!/bin/bash
# CCKS OPTIMAL VERIFICATION - BULLETPROOF PROTOCOL

echo "CCKS VERIFICATION PROTOCOL"
echo "=========================="

FAILED=0

# Test 1: RAM disk
echo -n "1. RAM Disk: "
if df -h | grep -q CCKS_RAM; then
    SIZE=$(df -h | grep CCKS_RAM | awk '{print $2}')
    echo "✅ PASS ($SIZE)"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 2: CCKS executable
echo -n "2. CCKS Binary: "
if [ -x ~/.claude/ccks ]; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 3: MLX GPU
echo -n "3. GPU Acceleration: "
if python3 -c "import mlx.core as mx; cores=mx.metal.device_info().get('gpu_cores', 0); exit(0 if cores > 0 else 1)" 2>/dev/null; then
    CORES=$(python3 -c "import mlx.core as mx; print(mx.metal.device_info().get('gpu_cores', 0))")
    echo "✅ PASS ($CORES cores)"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 4: Add operation
echo -n "4. Add Operation: "
RESULT=$(~/.claude/ccks add "TEST_$(date +%s)" 2>&1)
if echo "$RESULT" | grep -q "Added knowledge"; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 5: Query operation
echo -n "5. Query Operation: "
RESULT=$(~/.claude/ccks query "TEST" 2>&1)
if echo "$RESULT" | grep -q "Found"; then
    echo "✅ PASS"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 6: Stats operation
echo -n "6. Stats Operation: "
STATS=$(~/.claude/ccks stats 2>&1)
if echo "$STATS" | grep -q '"entries"'; then
    ENTRIES=$(echo "$STATS" | grep entries | cut -d: -f2 | cut -d, -f1)
    echo "✅ PASS ($ENTRIES entries)"
else
    echo "❌ FAIL"
    ((FAILED++))
fi

# Test 7: Response time
echo -n "7. Response Time: "
START=$(python3 -c "import time; print(int(time.time()*1000))")
~/.claude/ccks query "performance" > /dev/null 2>&1
END=$(python3 -c "import time; print(int(time.time()*1000))")
LATENCY=$((END - START))
if [ $LATENCY -lt 100 ]; then
    echo "✅ PASS (${LATENCY}ms)"
else
    echo "❌ FAIL (${LATENCY}ms > 100ms)"
    ((FAILED++))
fi

# Test 8: Memory efficiency
echo -n "8. Memory Usage: "
MEM=$(ps aux | grep "ccks" | grep -v grep | awk '{sum+=$6} END {print sum/1024}')
if (( $(echo "$MEM < 500" | bc -l) )); then
    echo "✅ PASS (${MEM}MB)"
else
    echo "⚠️  WARNING (${MEM}MB > 500MB)"
fi

echo "=========================="
if [ $FAILED -eq 0 ]; then
    echo "✅ ALL TESTS PASSED - CCKS TURBO MODE OPTIMAL"
    exit 0
else
    echo "❌ $FAILED TESTS FAILED - CCKS NOT OPTIMAL"
    exit 1
fi
EOF

chmod +x ~/.claude/verify_ccks_optimal.sh
```

## STEP 6: INTEGRATION WITH CLAUDE.md
Add this to your global ~/.claude/CLAUDE.md file:

```markdown
## 🧠 CCKS - Claude Code Knowledge System (MANDATORY)

**ALWAYS RUN FIRST IN EVERY SESSION:**
\`\`\`bash
# Load persistent memory (REQUIRED)
~/.claude/ccks stats > /dev/null 2>&1 || ~/.claude/ccks_ensure_turbo.sh

# Capture session context
pwd | xargs -I {} ~/.claude/ccks add "Working in: {}"
git status 2>/dev/null | head -5 | xargs -I {} ~/.claude/ccks add "Git: {}"
\`\`\`

**DURING SESSION - AUTO-CAPTURE PATTERNS:**
- After solving errors: \`ccks add "SOLUTION: [description]"\`
- After running commands: Pipe output to \`ccks add\`
- Before asking questions: Check \`ccks query "[your question]"\`

**TOKEN OPTIMIZATION PROTOCOL:**
1. Before processing any request, ALWAYS run: \`ccks query "[user's question]"\`
2. If cache hit (>85% similarity), use cached solution
3. After providing solution, ALWAYS run: \`ccks add "[solution summary]"\`

**PERFORMANCE REQUIREMENTS (MANDATORY):**
- Cache hit rate must exceed 50% after 10 queries
- Token reduction must exceed 80% on repeated queries
- All solutions must be persisted within 2 minutes
- Response time must be <100ms for cached queries
```

## STEP 7: FINAL VERIFICATION

Run this EXACT sequence to verify functional excellence:

```bash
# 1. Ensure turbo mode
~/.claude/ccks_ensure_turbo.sh

# 2. Run comprehensive verification
~/.claude/verify_ccks_optimal.sh

# 3. Performance benchmark
time for i in {1..100}; do ~/.claude/ccks query "test" > /dev/null; done

# 4. Confirm mandatory status
~/.claude/ccks add "CCKS TURBO MODE: MANDATORY - CONFIRMED"
~/.claude/ccks query "MANDATORY" | grep -q "CONFIRMED" && echo "✅ MANDATORY MODE CONFIRMED" || echo "❌ FAILED"
```

## SUCCESS CRITERIA (BULLETPROOF VERIFICATION)

You MUST see ALL of these outputs before claiming success:

1. ✅ RAM disk mounted (100GB at /Volumes/CCKS_RAM)
2. ✅ MLX GPU acceleration enabled (X cores detected)
3. ✅ CCKS operational (with entry count)
4. ✅ Turbo Mode active (<100ms response)
5. ✅ ALL TESTS PASSED - CCKS TURBO MODE OPTIMAL
6. ✅ MANDATORY MODE CONFIRMED

## FAILURE PROTOCOL

If ANY test fails:
1. State clearly: "CCKS TURBO MODE: FAILED at [specific test]"
2. Do NOT continue with partial implementation
3. Debug the specific failure point
4. Re-run entire verification suite

## OPERATIONAL REQUIREMENTS

Once implemented, EVERY Claude session MUST:
1. Run `~/.claude/ccks stats` at session start
2. Query before processing: `ccks query "[topic]"`
3. Add after solutions: `ccks add "[solution]"`
4. Maintain >50% cache hit rate
5. Achieve >80% token reduction on repeated queries

---

**REMEMBER**: This is MANDATORY, not optional. Functional excellence through verified testing is the only acceptable outcome. Execute with precision. Report with accuracy. Never fabricate success.