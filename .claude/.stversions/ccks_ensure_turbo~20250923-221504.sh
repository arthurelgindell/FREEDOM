#!/bin/bash
# CCKS Turbo Mode Ensure Script
# Bulletproof initialization - ensures all components are running

set -e

echo "🚀 Ensuring CCKS Turbo Mode is active..."

# Function to check and create RAM disk
ensure_ram_disk() {
    if [ ! -d "/Volumes/CCKS_RAM" ]; then
        echo "Creating RAM disk..."
        DISK_ID=$(hdiutil attach -nomount ram://20971520 2>/dev/null)
        if [ $? -eq 0 ]; then
            diskutil erasevolume HFS+ "CCKS_RAM" $DISK_ID >/dev/null 2>&1
            mkdir -p /Volumes/CCKS_RAM/cache
            ln -sfn /Volumes/CCKS_RAM/cache ~/.claude/ccks_cache_ram
            echo "✅ RAM disk created"
        else
            echo "⚠️  Could not create RAM disk (may need sudo)"
        fi
    else
        echo "✅ RAM disk already mounted"
    fi
}

# Function to check Python dependencies
check_dependencies() {
    echo "Checking dependencies..."

    # Check if MLX is available
    python3 -c "import mlx" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ MLX framework available"
    else
        echo "⚠️  MLX not installed (GPU acceleration limited)"
    fi

    # Check if psutil is available
    python3 -c "import psutil" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ psutil available"
    else
        echo "Installing psutil..."
        pip3 install psutil --quiet
    fi
}

# Function to test CCKS
test_ccks() {
    echo "Testing CCKS..."

    # Check basic CCKS functionality
    if [ -f ~/.claude/ccks ]; then
        ~/.claude/ccks stats > /tmp/ccks-test.json 2>&1
        if [ $? -eq 0 ] && [ -s /tmp/ccks-test.json ]; then
            entries=$(cat /tmp/ccks-test.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('entries', 0))" 2>/dev/null || echo "0")
            echo "✅ CCKS operational ($entries entries)"
        else
            echo "⚠️  CCKS may have issues - trying direct test"
            ~/.claude/ccks stats 2>/dev/null | head -2
        fi
    else
        echo "❌ CCKS not found at ~/.claude/ccks"
        return 1
    fi
}

# Function to initialize Turbo Mode
init_turbo() {
    echo "Initializing Turbo Mode..."

    if [ -f ~/.claude/ccks_turbo.py ]; then
        # Test turbo mode
        python3 -c "
import sys
sys.path.insert(0, '/Users/arthurdell/.claude')
sys.path.insert(0, '/Volumes/DATA/FREEDOM/core')

try:
    from ccks_turbo import CCKSTurbo
    turbo = CCKSTurbo()

    # Run a test query
    result = turbo.turbo_query('test', use_gpu=True)
    print(f'✅ Turbo Mode active ({result[\"response_time_ms\"]:.2f}ms response)')

    # Show stats
    stats = turbo.stats()
    active = [opt for opt in stats['optimizations_active'] if opt]
    print(f'✅ {len(active)} optimizations enabled')
except Exception as e:
    print(f'⚠️  Turbo Mode error: {e}')
"
    else
        echo "❌ Turbo Mode not found at ~/.claude/ccks_turbo.py"
        return 1
    fi
}

# Function to check network to Beta
check_network() {
    echo "Checking network to Beta..."

    ping -c 1 -t 2 100.84.202.68 > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        latency=$(ping -c 3 100.84.202.68 | grep avg | awk -F'/' '{print $5}')
        echo "✅ Beta reachable (${latency}ms latency)"
    else
        echo "⚠️  Beta unreachable (distributed processing unavailable)"
    fi
}

# Function to create status report
create_status_report() {
    echo "Creating status report..."

    cat > ~/.claude/ccks_turbo_status.json <<EOF
{
    "status": "active",
    "timestamp": "$(date)",
    "components": {
        "ram_disk": $([ -d "/Volumes/CCKS_RAM" ] && echo "true" || echo "false"),
        "mlx_gpu": $(python3 -c "import mlx" 2>/dev/null && echo "true" || echo "false"),
        "beta_network": $(ping -c 1 -t 1 100.84.202.68 > /dev/null 2>&1 && echo "true" || echo "false"),
        "ccks_entries": $(~/.claude/ccks stats 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('entries', 0))" 2>/dev/null || echo "0")
    }
}
EOF

    echo "✅ Status saved to ~/.claude/ccks_turbo_status.json"
}

# Main execution
main() {
    echo "=================================================="
    echo "CCKS TURBO MODE INITIALIZATION"
    echo "=================================================="
    echo ""

    ensure_ram_disk
    check_dependencies
    test_ccks
    init_turbo
    check_network
    create_status_report

    echo ""
    echo "=================================================="
    echo "✨ CCKS Turbo Mode is ready!"
    echo "=================================================="
}

# Run the main function
main

# Exit successfully
exit 0