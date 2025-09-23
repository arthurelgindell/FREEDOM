#!/bin/bash
# Network Performance Monitoring Script
# Continuously monitors Alpha-Beta network performance

echo "📊 Network Performance Monitor"
echo "=============================="
echo "Press Ctrl+C to stop"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to get current stats
get_stats() {
    # Tailscale connection status
    TS_STATUS=$(tailscale status | grep beta | awk '{print $6}')

    # Quick ping test (3 pings)
    PING_RESULT=$(ping -c 3 -q 100.84.202.68 2>/dev/null | grep "round-trip" | awk -F'/' '{print $5}')

    # Docker API health
    API_START=$(date +%s%N)
    curl -s http://localhost:8080/health > /dev/null 2>&1
    API_END=$(date +%s%N)
    API_TIME=$(( ($API_END - $API_START) / 1000000 ))

    # SSH connection test
    SSH_START=$(date +%s%N)
    ssh -o ConnectTimeout=2 beta-ts "echo 'connected'" > /dev/null 2>&1
    SSH_STATUS=$?
    SSH_END=$(date +%s%N)
    SSH_TIME=$(( ($SSH_END - $SSH_START) / 1000000 ))

    # Get Tailscale TX/RX bytes
    TS_STATS=$(tailscale status --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for peer in data.get('Peer', {}).values():
        if peer.get('HostName') == 'beta':
            tx = peer.get('TxBytes', 0) / 1048576  # Convert to MB
            rx = peer.get('RxBytes', 0) / 1048576
            print(f'{tx:.1f},{rx:.1f}')
            break
except:
    print('0,0')
" 2>/dev/null)

    TX_MB=$(echo $TS_STATS | cut -d',' -f1)
    RX_MB=$(echo $TS_STATS | cut -d',' -f2)

    # Display results
    clear
    echo "📊 Network Performance Monitor - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"
    echo ""

    # Tailscale Status
    echo "🔐 TAILSCALE:"
    if [ "$TS_STATUS" = "active" ] || [ "$TS_STATUS" = "idle" ]; then
        echo -e "  Status: ${GREEN}●${NC} Connected ($TS_STATUS)"
    else
        echo -e "  Status: ${RED}●${NC} Disconnected"
    fi
    echo "  TX: ${TX_MB} MB | RX: ${RX_MB} MB"
    echo ""

    # Latency
    echo "⏱️  LATENCY:"
    if [ -n "$PING_RESULT" ]; then
        LATENCY_VAL=$(echo $PING_RESULT | cut -d'.' -f1)
        if [ "$LATENCY_VAL" -lt 2 ]; then
            echo -e "  Beta (100.84.202.68): ${GREEN}${PING_RESULT} ms${NC}"
        elif [ "$LATENCY_VAL" -lt 5 ]; then
            echo -e "  Beta (100.84.202.68): ${YELLOW}${PING_RESULT} ms${NC}"
        else
            echo -e "  Beta (100.84.202.68): ${RED}${PING_RESULT} ms${NC}"
        fi
    else
        echo -e "  Beta: ${RED}Unreachable${NC}"
    fi
    echo ""

    # SSH
    echo "🔗 SSH CONNECTION:"
    if [ $SSH_STATUS -eq 0 ]; then
        echo -e "  Status: ${GREEN}●${NC} Connected (${SSH_TIME}ms)"
    else
        echo -e "  Status: ${RED}●${NC} Failed"
    fi
    echo ""

    # Docker Services
    echo "🐳 DOCKER SERVICES:"
    if [ "$API_TIME" -lt 100 ]; then
        echo -e "  API Gateway: ${GREEN}${API_TIME}ms${NC}"
    elif [ "$API_TIME" -lt 200 ]; then
        echo -e "  API Gateway: ${YELLOW}${API_TIME}ms${NC}"
    else
        echo -e "  API Gateway: ${RED}${API_TIME}ms${NC}"
    fi

    # Quick service check
    SERVICES_UP=$(docker ps --format "{{.Status}}" | grep -c "Up")
    SERVICES_TOTAL=$(docker ps -a --format "{{.Status}}" | wc -l)
    echo "  Services Running: $SERVICES_UP/$SERVICES_TOTAL"
    echo ""

    # TCP Settings
    echo "⚙️  TCP SETTINGS:"
    echo -n "  Send Buffer: "
    sysctl -n net.inet.tcp.sendspace
    echo -n "  Recv Buffer: "
    sysctl -n net.inet.tcp.recvspace
    echo -n "  Delayed ACK: "
    sysctl -n net.inet.tcp.delayed_ack
    echo ""

    # Performance Rating
    echo "📈 PERFORMANCE RATING:"
    if [ -n "$PING_RESULT" ]; then
        LATENCY_VAL=$(echo $PING_RESULT | cut -d'.' -f1)
        if [ "$LATENCY_VAL" -lt 2 ] && [ "$API_TIME" -lt 50 ] && [ $SSH_STATUS -eq 0 ]; then
            echo -e "  ${GREEN}⭐⭐⭐⭐⭐ EXCELLENT${NC}"
        elif [ "$LATENCY_VAL" -lt 5 ] && [ "$API_TIME" -lt 100 ]; then
            echo -e "  ${GREEN}⭐⭐⭐⭐ VERY GOOD${NC}"
        elif [ "$LATENCY_VAL" -lt 10 ] && [ "$API_TIME" -lt 200 ]; then
            echo -e "  ${YELLOW}⭐⭐⭐ GOOD${NC}"
        else
            echo -e "  ${RED}⭐⭐ NEEDS ATTENTION${NC}"
        fi
    fi
    echo ""
    echo "------------------------------------------------------------"
    echo "Commands: [q]uit | [t]est throughput | [o]ptimize | [r]efresh"
}

# Main monitoring loop
while true; do
    get_stats

    # Wait for input with timeout
    read -t 5 -n 1 key

    case $key in
        q|Q)
            echo "Exiting monitor..."
            exit 0
            ;;
        t|T)
            echo ""
            echo "Testing throughput (this will take about 10 seconds)..."
            # Quick throughput test
            dd if=/dev/urandom bs=1048576 count=10 2>/dev/null | ssh beta-ts "cat > /dev/null" &
            PID=$!
            sleep 1
            kill -0 $PID 2>/dev/null && echo "Upload test running..."
            wait $PID
            echo "Throughput test complete!"
            sleep 2
            ;;
        o|O)
            echo ""
            echo "Running optimization script..."
            /Volumes/DATA/FREEDOM/scripts/optimize_network.sh
            sleep 3
            ;;
        r|R)
            echo "Refreshing..."
            ;;
    esac
done