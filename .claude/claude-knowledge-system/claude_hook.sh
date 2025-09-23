#!/bin/bash
# Hook for Claude Code integration
# Add this to your shell profile to auto-start CCKS

# Start CCKS engine in background on Claude Code launch
if ! pgrep -f "ccks_engine.py" > /dev/null; then
    python3 ~/.claude/claude-knowledge-system/ccks_engine.py daemon &
    echo "🧠 CCKS started in background"
fi

# Function to query CCKS
ccks_query() {
    python3 ~/.claude/claude-knowledge-system/ccks_engine.py query "$*"
}

# Function to add to CCKS
ccks_add() {
    python3 ~/.claude/claude-knowledge-system/ccks_engine.py add "$*"
}

# Export functions
export -f ccks_query
export -f ccks_add
