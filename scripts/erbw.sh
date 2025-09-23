#!/usr/bin/env bash
# FREEDOM Ephemeral RAM Branch Workflow (ERBW) Controller
# RAM-native, self-healing development loop with automatic GC
set -euo pipefail

RAM_BASE="/Volumes/CCKS_RAM/freedom_dev"
REPO_PATH="/Volumes/DATA/FREEDOM"  # Main repo on disk
BR_ROOT="$RAM_BASE/branches"
SNAPSHOTS="$RAM_BASE/snapshots"
META="$RAM_BASE/.freedom"
NODE="${FREEDOM_NODE:-alpha}"      # alpha|beta|gamma
TTL_HOURS="${ERBW_TTL_HOURS:-8}"
PERF_BUDGET_MS="${ERBW_PERF_BUDGET_MS:-500}"
REQUIRE_CANARY="${ERBW_REQUIRE_CANARY:-false}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure required tools
require() {
    command -v "$1" >/dev/null || {
        echo -e "${RED}Error: Missing required tool: $1${NC}"
        exit 1
    }
}

# Initialize ERBW structure
init_erbw() {
    mkdir -p "$BR_ROOT"
    mkdir -p "$SNAPSHOTS"
    mkdir -p "$META/locks"
    mkdir -p "$META/survivors"
    mkdir -p "$META/gc"
    mkdir -p "$META/metrics"
    mkdir -p "$META/syncthing/ignore.d"

    # Ensure we have a working git repo in RAM
    if [ ! -d "$RAM_BASE/source/.git" ]; then
        echo -e "${YELLOW}Initializing git in RAM source...${NC}"
        cd "$RAM_BASE/source"
        git init
        git remote add origin "$(cd "$REPO_PATH" && git remote get-url origin)"
        git fetch origin main --depth=1
        git reset --hard origin/main
    fi
}

# SPAWN - Create ephemeral work branch
cmd_spawn() {
    local feature="${1:-}"
    if [ -z "$feature" ]; then
        echo -e "${RED}Error: Feature name required${NC}"
        echo "Usage: freedomctl spawn <feature-name>"
        exit 1
    fi

    init_erbw

    local stamp
    stamp=$(date +"%y%m%d-%H%M")
    local br="ewb/${feature}-${stamp}-${NODE}"
    local br_path="$BR_ROOT/${br//\//-}"

    echo -e "${BLUE}Spawning ephemeral branch: $br${NC}"

    # Work in RAM source
    cd "$RAM_BASE/source"
    git fetch origin main --depth=1

    # Create branch from origin/main without checking it out in main working tree
    git branch "$br" origin/main 2>/dev/null || git branch -f "$br" origin/main

    # Create worktree in branches directory
    if [ -d "$br_path" ]; then
        git worktree remove --force "$br_path" 2>/dev/null || true
        rm -rf "$br_path"
    fi
    git worktree add "$br_path" "$br"

    # Write metadata
    cat > "$META/locks/${br//\//-}.json" <<EOF
{
    "branch": "$br",
    "feature": "$feature",
    "node": "$NODE",
    "spawned": "$(date -Iseconds)",
    "ttl_hours": $TTL_HOURS,
    "path": "$br_path",
    "status": "spawned"
}
EOF

    echo -e "${GREEN}✓ Spawned: $br${NC}"
    echo -e "${GREEN}  Path: $br_path${NC}"
    echo "$br_path"
}

# MUTATE - Execute changes in branch
cmd_mutate() {
    local path="${1:-}"
    shift || true

    if [ -z "$path" ] || [ ! -d "$path" ]; then
        echo -e "${RED}Error: Valid branch path required${NC}"
        exit 1
    fi

    echo -e "${BLUE}Mutating in: $path${NC}"
    echo -e "${YELLOW}Command: $*${NC}"

    (cd "$path" && "$@")
    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ Mutation successful${NC}"
    else
        echo -e "${RED}✗ Mutation failed (exit code: $result)${NC}"
    fi

    return $result
}

# VERIFY - Run Truth Engine gates
cmd_verify() {
    local path="${1:-}"
    if [ -z "$path" ] || [ ! -d "$path" ]; then
        echo -e "${RED}Error: Valid branch path required${NC}"
        exit 1
    fi

    local br
    br=$(git -C "$path" rev-parse --abbrev-ref HEAD)
    local start_time=$(date +%s)

    echo -e "${BLUE}Verifying branch: $br${NC}"
    echo -e "${BLUE}Path: $path${NC}"

    local gates_passed=true
    local results=""

    # Gate 1: Lint
    echo -e "\n${YELLOW}Gate 1: Lint${NC}"
    if (cd "$path" && python3 -m ruff check . 2>/dev/null); then
        echo -e "${GREEN}✓ Lint passed${NC}"
        results="${results}\"lint\":\"pass\","
    else
        echo -e "${RED}✗ Lint failed${NC}"
        gates_passed=false
        results="${results}\"lint\":\"fail\","
    fi

    # Gate 2: Unit tests
    echo -e "\n${YELLOW}Gate 2: Unit Tests${NC}"
    if (cd "$path" && python3 -m pytest -q tests/unit 2>/dev/null); then
        echo -e "${GREEN}✓ Unit tests passed${NC}"
        results="${results}\"unit\":\"pass\","
    else
        echo -e "${RED}✗ Unit tests failed${NC}"
        gates_passed=false
        results="${results}\"unit\":\"fail\","
    fi

    # Gate 3: Integration tests
    echo -e "\n${YELLOW}Gate 3: Integration Tests${NC}"
    if (cd "$path" && python3 -m pytest -q tests/integration 2>/dev/null); then
        echo -e "${GREEN}✓ Integration tests passed${NC}"
        results="${results}\"int\":\"pass\","
    else
        echo -e "${RED}✗ Integration tests failed${NC}"
        gates_passed=false
        results="${results}\"int\":\"fail\","
    fi

    # Gate 4: Performance
    echo -e "\n${YELLOW}Gate 4: Performance${NC}"
    local perf_time=$(python3 -c "import time; s=time.time(); exec(open('$path/scripts/council_cli.py').read(), {'__name__':'__main__'}); print(int((time.time()-s)*1000))" 2>/dev/null || echo "999999")
    if [ "$perf_time" -lt "$PERF_BUDGET_MS" ]; then
        echo -e "${GREEN}✓ Performance passed (${perf_time}ms < ${PERF_BUDGET_MS}ms)${NC}"
        results="${results}\"perf\":\"pass\","
    else
        echo -e "${RED}✗ Performance failed (${perf_time}ms >= ${PERF_BUDGET_MS}ms)${NC}"
        gates_passed=false
        results="${results}\"perf\":\"fail\","
    fi

    # Gate 5: Canary (optional)
    if [ "$REQUIRE_CANARY" = "true" ]; then
        echo -e "\n${YELLOW}Gate 5: Canary${NC}"
        if (cd "$path" && python3 scripts/council_cli.py status 2>/dev/null | grep -q "ready"); then
            echo -e "${GREEN}✓ Canary passed${NC}"
            results="${results}\"canary\":\"pass\""
        else
            echo -e "${RED}✗ Canary failed${NC}"
            gates_passed=false
            results="${results}\"canary\":\"fail\""
        fi
    else
        results="${results}\"canary\":\"skip\""
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Write metrics
    cat > "$META/metrics/${br//\//-}.json" <<EOF
{
    "branch": "$br",
    "verified": "$(date -Iseconds)",
    "duration_seconds": $duration,
    "gates_passed": $gates_passed,
    "truth_gates": {$results},
    "node": "$NODE",
    "perf_time_ms": ${perf_time:-0}
}
EOF

    if [ "$gates_passed" = true ]; then
        echo -e "\n${GREEN}✅ VERIFICATION PASSED - Branch survives!${NC}"
        echo -e "${GREEN}Survival Certificate: $META/metrics/${br//\//-}.json${NC}"
        return 0
    else
        echo -e "\n${RED}❌ VERIFICATION FAILED - Branch must vanish!${NC}"
        return 1
    fi
}

# PERSIST - Commit and push survivor
cmd_persist() {
    local path="${1:-}"
    if [ -z "$path" ] || [ ! -d "$path" ]; then
        echo -e "${RED}Error: Valid branch path required${NC}"
        exit 1
    fi

    local br
    br=$(git -C "$path" rev-parse --abbrev-ref HEAD)

    echo -e "${BLUE}Persisting survivor branch: $br${NC}"

    # Stage all changes
    (cd "$path" && git add -A)

    # Check if there are changes to commit
    if git -C "$path" diff --cached --quiet; then
        echo -e "${YELLOW}No changes to commit${NC}"
    else
        # Commit with ERBW signature
        (cd "$path" && git commit -m "ERBW Survivor: ${br}

Branch survived all Truth Engine gates
Node: ${NODE}
Timestamp: $(date -Iseconds)

🤖 Generated with FREEDOM ERBW
Co-Authored-By: CCKS Turbo <noreply@freedom.local>")
    fi

    # Push to origin
    echo -e "${BLUE}Pushing to origin...${NC}"
    (cd "$path" && git push -u origin "$br")

    # Mark as survivor
    mv "$META/locks/${br//\//-}.json" "$META/survivors/${br//\//-}.json" 2>/dev/null || true

    # Convert to SVB (Survivor Branch)
    local svb_name="svb/${br#ewb/}"
    echo -e "${BLUE}Converting to Survivor Branch: $svb_name${NC}"
    (cd "$path" && git branch -m "$br" "$svb_name" && git push origin ":$br" "$svb_name")

    echo -e "${GREEN}✅ Branch persisted as survivor: $svb_name${NC}"
}

# VANISH - Remove failed branch
cmd_vanish() {
    local path="${1:-}"
    if [ -z "$path" ] || [ ! -d "$path" ]; then
        echo -e "${YELLOW}Path not found, may already be vanished${NC}"
        return 0
    fi

    local br
    br=$(git -C "$path" rev-parse --abbrev-ref HEAD 2>/dev/null) || true

    echo -e "${RED}Vanishing failed branch: $br${NC}"

    # Remove worktree
    git -C "$RAM_BASE/source" worktree remove --force "$path" 2>/dev/null || true

    # Delete branch
    if [ -n "$br" ]; then
        git -C "$RAM_BASE/source" branch -D "$br" 2>/dev/null || true
    fi

    # Archive metadata
    if [ -f "$META/locks/${br//\//-}.json" ]; then
        mv "$META/locks/${br//\//-}.json" "$META/gc/${br//\//-}-$(date +%s).json" 2>/dev/null || true
    fi

    echo -e "${RED}✗ Branch vanished: $br${NC}"
}

# SNAPSHOT - Create compressed artifact
cmd_snapshot() {
    local path="${1:-}"
    if [ -z "$path" ] || [ ! -d "$path" ]; then
        echo -e "${RED}Error: Valid branch path required${NC}"
        exit 1
    fi

    local name
    name=$(basename "$path")
    local snapshot_file="$SNAPSHOTS/${name}-$(date +%s).tar.zst"

    echo -e "${BLUE}Creating snapshot: $snapshot_file${NC}"

    # Create snapshot with high compression
    tar -I "zstd -19 --long" -cf "$snapshot_file" -C "$path" . \
        --exclude=.git \
        --exclude=__pycache__ \
        --exclude=*.pyc \
        --exclude=node_modules \
        --exclude=.pytest_cache

    local size
    size=$(du -h "$snapshot_file" | cut -f1)

    echo -e "${GREEN}✓ Snapshot created: $snapshot_file ($size)${NC}"
    echo "$snapshot_file"
}

# GC - Garbage collect stale branches
cmd_gc() {
    echo -e "${BLUE}Running garbage collection (TTL: ${TTL_HOURS}h)${NC}"

    local count=0
    local ttl_seconds=$((TTL_HOURS * 3600))
    local now=$(date +%s)

    # Find and remove stale branches
    if [ -d "$BR_ROOT" ]; then
        find "$BR_ROOT" -maxdepth 1 -mindepth 1 -type d | while IFS= read -r dir; do
            local mtime=$(stat -f %m "$dir" 2>/dev/null || stat -c %Y "$dir" 2>/dev/null)
            local age=$((now - mtime))

            if [ $age -gt $ttl_seconds ]; then
                echo -e "${YELLOW}GC: Removing stale branch: $(basename "$dir") (age: $((age/3600))h)${NC}"
                cmd_vanish "$dir"
                ((count++))
            fi
        done
    fi

    # Clean old snapshots (keep last 10)
    if [ -d "$SNAPSHOTS" ]; then
        ls -t "$SNAPSHOTS"/*.tar.zst 2>/dev/null | tail -n +11 | while IFS= read -r file; do
            echo -e "${YELLOW}GC: Removing old snapshot: $(basename "$file")${NC}"
            rm -f "$file"
            ((count++))
        done
    fi

    # Clean old GC metadata (older than 7 days)
    if [ -d "$META/gc" ]; then
        find "$META/gc" -name "*.json" -mtime +7 -delete
    fi

    echo -e "${GREEN}✓ GC complete: cleaned $count items${NC}"
}

# STATUS - Show current ERBW state
cmd_status() {
    echo -e "${BLUE}ERBW Status Report${NC}"
    echo -e "${BLUE}==================${NC}"

    echo -e "\n${YELLOW}Configuration:${NC}"
    echo "  Node: $NODE"
    echo "  TTL: ${TTL_HOURS}h"
    echo "  Performance Budget: ${PERF_BUDGET_MS}ms"
    echo "  Require Canary: $REQUIRE_CANARY"

    echo -e "\n${YELLOW}Active Branches:${NC}"
    if [ -d "$BR_ROOT" ]; then
        local count=0
        for dir in "$BR_ROOT"/*; do
            if [ -d "$dir" ]; then
                local br_name=$(basename "$dir")
                local size=$(du -sh "$dir" | cut -f1)
                echo "  • $br_name ($size)"
                ((count++))
            fi
        done
        echo "  Total: $count branches"
    else
        echo "  None"
    fi

    echo -e "\n${YELLOW}Survivors:${NC}"
    if [ -d "$META/survivors" ]; then
        local survivor_count=$(ls "$META/survivors"/*.json 2>/dev/null | wc -l)
        echo "  Total: $survivor_count survived branches"
    else
        echo "  None"
    fi

    echo -e "\n${YELLOW}Snapshots:${NC}"
    if [ -d "$SNAPSHOTS" ]; then
        local snapshot_count=$(ls "$SNAPSHOTS"/*.tar.zst 2>/dev/null | wc -l)
        local total_size=$(du -sh "$SNAPSHOTS" 2>/dev/null | cut -f1)
        echo "  Count: $snapshot_count"
        echo "  Total Size: ${total_size:-0}"
    else
        echo "  None"
    fi

    echo -e "\n${YELLOW}RAM Usage:${NC}"
    df -h "$RAM_BASE" | tail -1 | awk '{print "  Used: "$3" / "$2" ("$5")"}'
}

# Usage help
usage() {
    cat <<EOF
${BLUE}freedomctl - FREEDOM Ephemeral RAM Branch Workflow${NC}

${YELLOW}Commands:${NC}
  spawn <feature>       Create ephemeral RAM branch (EWB)
  mutate <path> <cmd>   Run mutation command in branch
  verify <path>         Run Truth Engine gates
  persist <path>        Commit & push survivor branch
  vanish <path>         Remove failed branch
  snapshot <path>       Create compressed artifact
  gc                    Cleanup stale branches (TTL=${TTL_HOURS}h)
  status                Show ERBW system status

${YELLOW}Environment Variables:${NC}
  FREEDOM_NODE          Node name (default: alpha)
  ERBW_TTL_HOURS        Branch TTL in hours (default: 8)
  ERBW_PERF_BUDGET_MS   Performance budget in ms (default: 500)
  ERBW_REQUIRE_CANARY   Require canary tests (default: false)

${YELLOW}Example Workflow:${NC}
  # Spawn a new feature branch
  path=\$(freedomctl spawn my-feature)

  # Make changes
  freedomctl mutate "\$path" vim core/main.py
  freedomctl mutate "\$path" make format

  # Verify (gates must pass)
  freedomctl verify "\$path" || freedomctl vanish "\$path"

  # Persist survivor
  freedomctl snapshot "\$path"
  freedomctl persist "\$path"

${YELLOW}Survival Rules:${NC}
  • Must pass ALL Truth Engine gates
  • Must meet performance budget
  • Must improve or maintain value metrics
  • Only survivors can reach main branch

EOF
}

# Main entry point
main() {
    require git
    require python3
    require tar
    require zstd

    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        spawn) cmd_spawn "$@";;
        mutate) cmd_mutate "$@";;
        verify) cmd_verify "$@";;
        persist) cmd_persist "$@";;
        vanish) cmd_vanish "$@";;
        snapshot) cmd_snapshot "$@";;
        gc) cmd_gc;;
        status) cmd_status;;
        *) usage;;
    esac
}

main "$@"