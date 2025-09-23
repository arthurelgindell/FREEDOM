#!/bin/bash
# CCKS Turbo Mode Auto-Start Script
# Ensures all optimizations are available for Claude Code

set -e

# Log startup
echo "$(date): Starting CCKS Turbo Mode..." >> /tmp/ccks-turbo.log

# 1. Create RAM disk if not exists (10GB)
if [ ! -d "/Volumes/CCKS_RAM" ]; then
    echo "$(date): Creating 10GB RAM disk..." >> /tmp/ccks-turbo.log

    # Create RAM disk
    DISK_ID=$(hdiutil attach -nomount ram://20971520 2>/dev/null)

    if [ $? -eq 0 ]; then
        # Format the RAM disk
        diskutil erasevolume HFS+ "CCKS_RAM" $DISK_ID >/dev/null 2>&1

        # Create cache directory
        mkdir -p /Volumes/CCKS_RAM/cache

        # Create symlink for CCKS
        ln -sfn /Volumes/CCKS_RAM/cache ~/.claude/ccks_cache_ram

        echo "$(date): RAM disk created at /Volumes/CCKS_RAM" >> /tmp/ccks-turbo.log
    else
        echo "$(date): Failed to create RAM disk" >> /tmp/ccks-turbo.log
    fi
else
    echo "$(date): RAM disk already exists" >> /tmp/ccks-turbo.log
fi

# 2. Initialize CCKS with Turbo Mode
if [ -f ~/.claude/ccks ]; then
    echo "$(date): Initializing CCKS..." >> /tmp/ccks-turbo.log

    # Check CCKS stats
    python3 ~/.claude/ccks stats > /tmp/ccks-stats.json 2>&1

    # Preload FREEDOM files if available
    if [ -d "/Volumes/DATA/FREEDOM" ]; then
        echo "$(date): Preloading FREEDOM files..." >> /tmp/ccks-turbo.log

        # Run the mmap addon to preload files
        python3 ~/.claude/ccks_mmap_addon.py > /dev/null 2>&1 &

        # Run GPU accelerator initialization
        python3 ~/.claude/ccks_gpu_accelerator.py > /dev/null 2>&1 &
    fi
fi

# 3. Check Beta system connectivity
ping -c 1 -t 1 100.84.202.68 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "$(date): Beta system reachable" >> /tmp/ccks-turbo.log
else
    echo "$(date): Beta system unreachable" >> /tmp/ccks-turbo.log
fi

# 4. Initialize Turbo Mode components
if [ -f ~/.claude/ccks_turbo.py ]; then
    echo "$(date): Activating CCKS Turbo Mode..." >> /tmp/ccks-turbo.log

    # Run turbo mode in background to initialize all components
    python3 -c "
import sys
sys.path.insert(0, '/Users/arthurdell/.claude')
try:
    from ccks_turbo import CCKSTurbo
    turbo = CCKSTurbo()
    stats = turbo.stats()
    print(f'Turbo Mode Active: {len(stats[\"optimizations_active\"])} optimizations')

    # Warm up the cache
    result = turbo.turbo_query('FREEDOM initialization', use_gpu=True)
    print(f'Cache warmed up: {result[\"response_time_ms\"]:.2f}ms')
except Exception as e:
    print(f'Error: {e}')
" >> /tmp/ccks-turbo.log 2>&1
fi

# 5. Create status file for verification
echo "{
    \"status\": \"active\",
    \"timestamp\": \"$(date)\",
    \"ram_disk\": \"$([ -d '/Volumes/CCKS_RAM' ] && echo 'mounted' || echo 'not mounted')\",
    \"beta_connected\": \"$(ping -c 1 -t 1 100.84.202.68 > /dev/null 2>&1 && echo 'yes' || echo 'no')\"
}" > ~/.claude/ccks_turbo_status.json

echo "$(date): CCKS Turbo Mode startup complete" >> /tmp/ccks-turbo.log

# Keep the service healthy
exit 0