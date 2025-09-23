#!/bin/bash
# CCKS Syncthing Verification Test Suite
# Run this after both Alpha and Beta are configured

echo "=================================================="
echo "    CCKS SYNCTHING VERIFICATION TEST SUITE      "
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_KEY="xxFa94mGY4SeuPHECNMaRzWiyJSiGmkV"
API_URL="http://localhost:8384/rest"

echo "Test 1: Checking Syncthing Status"
echo "=================================="
STATUS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/system/status" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'✅ Syncthing Running')
    print(f'   Version: {data.get(\"version\", \"unknown\")}')
    print(f'   Uptime: {data.get(\"uptime\", 0)} seconds')
except:
    print('❌ Syncthing API not responding')
    sys.exit(1)
" 2>/dev/null)

echo "$STATUS"
echo ""

echo "Test 2: Checking Device Connections"
echo "===================================="
CONNECTIONS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/system/connections" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    connected = 0
    for device_id, info in data.get('connections', {}).items():
        if device_id != 'J64ABTL-XGEG4FK-IWADAUE-4GYS4NQ-UNTQE22-BZSUUU2-ZFNCRTY-WCGCYAO' and info.get('connected'):
            connected += 1
            print(f'✅ Beta Connected: {device_id[:7]}...')
            print(f'   Address: {info.get(\"address\", \"unknown\")}')
    if connected == 0:
        print('⏳ No devices connected yet')
        print('   Waiting for Beta to connect...')
except:
    print('❌ Could not check connections')
" 2>/dev/null)

echo "$CONNECTIONS"
echo ""

echo "Test 3: CCKS Database Sync Test"
echo "================================"
# Generate unique test ID
TEST_ID=$(date +%s)
TEST_CONTENT="SYNC_TEST_ALPHA_${TEST_ID}"

echo "Adding test entry to CCKS..."
~/.claude/ccks add "$TEST_CONTENT" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test entry added to Alpha CCKS${NC}"
    echo "   Content: $TEST_CONTENT"
else
    echo -e "${RED}❌ Failed to add test entry${NC}"
fi
echo ""

echo "Test 4: Folder Sync Status"
echo "=========================="
FOLDER_STATUS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/db/status?folder=ccks-db" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    state = data.get('state', 'unknown')
    need = data.get('needFiles', 0)
    global_files = data.get('globalFiles', 0)
    local_files = data.get('localFiles', 0)
    if state == 'idle':
        print(f'✅ CCKS-DB folder synced')
    else:
        print(f'⏳ CCKS-DB folder: {state}')
    print(f'   Files: {local_files}/{global_files} (Need: {need})')
except:
    print('❌ CCKS-DB folder not configured')
" 2>/dev/null)

echo "$FOLDER_STATUS"
echo ""

echo "Test 5: CCKS Entry Count Comparison"
echo "==================================="
ALPHA_COUNT=$(~/.claude/ccks stats 2>/dev/null | grep '"entries"' | cut -d: -f2 | cut -d, -f1 | tr -d ' ')
echo "Alpha CCKS entries: $ALPHA_COUNT"

echo ""
echo "Test 6: Performance Check"
echo "========================="
START=$(python3 -c "import time; print(int(time.time()*1000))")
~/.claude/ccks query "SYNC_TEST" > /dev/null 2>&1
END=$(python3 -c "import time; print(int(time.time()*1000))")
LATENCY=$((END - START))

if [ $LATENCY -lt 100 ]; then
    echo -e "${GREEN}✅ CCKS query performance: ${LATENCY}ms${NC}"
else
    echo -e "${YELLOW}⚠️  CCKS query performance: ${LATENCY}ms (slower than target)${NC}"
fi
echo ""

echo "=================================================="
echo "              TEST SUMMARY                       "
echo "=================================================="
echo ""
echo "To verify on Beta, run these commands:"
echo ""
echo "1. Check if test entry synced:"
echo "   ~/.claude/ccks query '$TEST_CONTENT'"
echo ""
echo "2. Add entry from Beta:"
echo "   ~/.claude/ccks add 'TEST_FROM_BETA_$(date +%s)'"
echo ""
echo "3. Check on Alpha (after 10 seconds):"
echo "   ~/.claude/ccks query 'TEST_FROM_BETA'"
echo ""
echo "4. Compare entry counts on both machines:"
echo "   ~/.claude/ccks stats | grep entries"
echo ""

# Monitor mode option
echo "Run with -m flag to enter monitoring mode:"
echo "  $0 -m"
echo ""

if [ "$1" = "-m" ]; then
    echo "Entering monitoring mode..."
    sleep 2
    /Volumes/DATA/FREEDOM/monitor_syncthing_connection.sh
fi