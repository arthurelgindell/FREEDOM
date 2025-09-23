#!/bin/bash
# SAF Beta Node (Worker) Startup Script
# Starts Ray worker node on BETA Mac Studio
# This script should be run on the BETA machine

echo "========================================="
echo "   SAF - Starting BETA Node (Worker)    "
echo "========================================="
echo ""

# Configuration
ALPHA_IP="100.106.170.128"  # Tailscale IP for alpha (head node)
BETA_IP="100.84.202.68"     # Tailscale IP for beta
PORT="6380"
CPUS="32"
MEMORY="220GB"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check connectivity to head node
echo "🔍 Checking connectivity to ALPHA node..."
if ping -c 2 "$ALPHA_IP" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ALPHA node reachable at $ALPHA_IP${NC}"
else
    echo -e "${RED}❌ Cannot reach ALPHA node at $ALPHA_IP${NC}"
    echo "   Please ensure:"
    echo "   1. ALPHA node is running Ray head"
    echo "   2. Tailscale is connected"
    echo "   3. Network is properly configured"
    exit 1
fi

# Stop any existing Ray instance
echo ""
echo "🛑 Stopping any existing Ray instances..."
ray stop --force 2>/dev/null

sleep 2

# Join the cluster
echo ""
echo "🔗 Joining Ray cluster..."
echo "   Head node: $ALPHA_IP:$PORT"
echo "   This node IP: $BETA_IP"
echo "   CPUs: $CPUS"
echo "   Memory: $MEMORY"
echo ""

# Start Ray worker node
ray start \
    --address="$ALPHA_IP:$PORT" \
    --node-ip-address="$BETA_IP" \
    --num-cpus="$CPUS" \
    --memory="$((220 * 1024 * 1024 * 1024))" \
    2>&1 | while read line; do
        if [[ $line == *"Ray runtime started"* ]]; then
            echo -e "${GREEN}✅ Successfully joined cluster!${NC}"
        elif [[ $line == *"Connected to Ray cluster"* ]]; then
            echo -e "${GREEN}✅ Connected to Ray cluster${NC}"
        elif [[ $line == *"Error"* ]] || [[ $line == *"Failed"* ]]; then
            echo -e "${RED}$line${NC}"
        else
            echo "$line"
        fi
    done

# Verify connection
echo ""
echo "🔍 Verifying cluster connection..."
sleep 3

# Check if we successfully joined
if ray status 2>/dev/null | grep -q "2 node(s)"; then
    echo -e "${GREEN}✅ BETA successfully joined the cluster!${NC}"
    echo ""
    echo "📊 Cluster Status:"
    ray status 2>/dev/null | head -20
else
    echo -e "${YELLOW}⚠️  Connection status uncertain. Checking Ray processes...${NC}"
    if pgrep -f "ray::" > /dev/null; then
        echo "Ray processes are running. Connection may still be establishing."
    else
        echo -e "${RED}❌ Ray worker failed to start${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   BETA Node Ready${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "📊 Total cluster resources:"
echo "   • 2 nodes (ALPHA + BETA)"
echo "   • 64 CPU cores total"
echo "   • 440 GB memory total"
echo ""
echo "🔍 Monitor from ALPHA with:"
echo "   ray status"
echo "   Dashboard: http://$ALPHA_IP:8265"