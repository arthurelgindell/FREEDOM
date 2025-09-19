#!/bin/bash
# Claude Code Knowledge System - Quick Install Script

set -e

echo "🧠 Claude Code Knowledge System Installer"
echo "=========================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check if we're in the knowledge system directory
if [ ! -f "claude_knowledge_db.py" ]; then
    echo "❌ Please run this script from the claude-knowledge-system directory"
    exit 1
fi

# Install DuckDB if needed
echo "📦 Checking dependencies..."
python3 -c "import duckdb" 2>/dev/null || {
    echo "Installing DuckDB..."
    pip3 install duckdb
}

# Test the knowledge base
echo "🔍 Testing knowledge base..."
python3 claude_knowledge_db.py stats

# Copy CLAUDE.md to home directory if it doesn't exist
if [ ! -f "~/CLAUDE.md" ]; then
    echo "📄 Installing CLAUDE.md to home directory..."
    cp CLAUDE.md ~/CLAUDE.md
    echo "✅ CLAUDE.md installed to ~/CLAUDE.md"
else
    echo "⚠️  CLAUDE.md already exists in home directory"
    echo "   To update: cp CLAUDE.md ~/CLAUDE.md"
fi

# Make the script executable
chmod +x claude_knowledge_db.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start Claude Code in any directory with CLAUDE.md present"
echo "2. The system will auto-load knowledge base context"
echo "3. Use 'python3 claude_knowledge_db.py search \"term\"' to search previous conversations"
echo ""
echo "🎯 The knowledge base contains:"
python3 claude_knowledge_db.py stats | grep -E "(Conversations|Messages|Topics|Context)"
echo ""
echo "Happy coding with persistent memory! 🚀"