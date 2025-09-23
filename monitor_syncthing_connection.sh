#!/bin/bash
# Monitor Syncthing for Beta connection
# This script watches for Beta to connect and alerts when sync is active

echo "=================================================="
echo "    SYNCTHING CONNECTION MONITOR - ALPHA        "
echo "=================================================="
echo ""
echo "Watching for Beta connection..."
echo "Alpha Device ID: J64ABTL-XGEG4FK-IWADAUE-4GYS4NQ-UNTQE22-BZSUUU2-ZFNCRTY-WCGCYAO"
echo ""

API_URL="http://localhost:8384/rest"
BETA_CONNECTED=false
LAST_CHECK=""

while true; do
    # Get current time
    NOW=$(date '+%H:%M:%S')

    # Check connections
    CONNECTIONS=$(curl -s "$API_URL/system/connections" 2>/dev/null)

    if [ ! -z "$CONNECTIONS" ]; then
        # Check if we have any connected devices (besides ourselves)
        CONNECTED_COUNT=$(echo "$CONNECTIONS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
connected = 0
for device_id, info in data.get('connections', {}).items():
    if device_id != 'J64ABTL-XGEG4FK-IWADAUE-4GYS4NQ-UNTQE22-BZSUUU2-ZFNCRTY-WCGCYAO' and info.get('connected'):
        connected += 1
        print(f'✅ Device connected: {device_id[:7]}... at {info.get(\"address\", \"unknown\")}')
print(f'Total connected devices: {connected}')
" 2>/dev/null || echo "0")

        # Check folder sync status
        DB_STATUS=$(curl -s "$API_URL/db/status?folder=ccks-db" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    state = data.get('state', 'unknown')
    need = data.get('needFiles', 0)
    global_files = data.get('globalFiles', 0)
    local_files = data.get('localFiles', 0)
    print(f'CCKS-DB: {state} | Files: {local_files}/{global_files} | Need: {need}')
except:
    print('CCKS-DB: Not configured')
" 2>/dev/null)

        CACHE_STATUS=$(curl -s "$API_URL/db/status?folder=ccks-cache" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    state = data.get('state', 'unknown')
    global_files = data.get('globalFiles', 0)
    local_files = data.get('localFiles', 0)
    print(f'CCKS-Cache: {state} | Files: {local_files}/{global_files}')
except:
    print('CCKS-Cache: Not configured')
" 2>/dev/null)

        # Clear screen and show status
        clear
        echo "=================================================="
        echo "    SYNCTHING CONNECTION MONITOR - $NOW         "
        echo "=================================================="
        echo ""
        echo "Connection Status:"
        echo "$CONNECTED_COUNT"
        echo ""
        echo "Folder Status:"
        echo "  $DB_STATUS"
        echo "  $CACHE_STATUS"
        echo ""

        # Check for recent events
        EVENTS=$(curl -s "$API_URL/events?limit=5" 2>/dev/null | python3 -c "
import sys, json
try:
    events = json.load(sys.stdin)
    for event in events:
        event_type = event.get('type', '')
        if 'Device' in event_type or 'Folder' in event_type:
            print(f'  {event.get(\"time\", \"\")[:19]} - {event_type}')
except:
    pass
" 2>/dev/null)

        if [ ! -z "$EVENTS" ]; then
            echo "Recent Events:"
            echo "$EVENTS"
            echo ""
        fi

        # Show CCKS stats
        echo "CCKS Status:"
        CCKS_STATS=$(~/.claude/ccks stats 2>/dev/null | grep entries || echo "CCKS not available")
        echo "  $CCKS_STATS"
        echo ""

        # Instructions
        if echo "$CONNECTED_COUNT" | grep -q "Total connected devices: 0"; then
            echo "⏳ Waiting for Beta to connect..."
            echo ""
            echo "On Beta machine, run:"
            echo "  1. tailscale file get"
            echo "  2. chmod +x setup_syncthing_beta.sh"
            echo "  3. ./setup_syncthing_beta.sh"
            echo "  4. Copy the Beta Device ID shown"
            echo "  5. On Alpha, run: /Volumes/DATA/FREEDOM/configure_syncthing_alpha.sh"
        else
            echo "✅ BETA CONNECTED - Sync Active!"
            echo ""
            echo "Test sync with:"
            echo "  ~/.claude/ccks add 'TEST FROM ALPHA $(date)'"
        fi

        echo ""
        echo "Press Ctrl+C to exit | Web UI: http://localhost:8384"
    else
        echo "[$NOW] Syncthing API not responding..."
    fi

    sleep 5
done