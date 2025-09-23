#!/bin/bash
# SAF Alpha Node (Head) Startup Script - Simple version without dashboard
# Starts Ray head node on ALPHA Mac Studio

echo "========================================="
echo "   SAF - Starting ALPHA Node (Head)     "
echo "========================================="
echo ""

# Configuration
ALPHA_IP="100.106.170.128"  # Tailscale IP for alpha
PORT="6380"  # Using 6380 to avoid Redis conflict
CPUS="32"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Stop any existing Ray instance
echo "🛑 Stopping any existing Ray instances..."
ray stop --force 2>/dev/null

sleep 2

# Start Ray head node WITHOUT dashboard (to avoid dependency issues)
echo ""
echo "🚀 Starting Ray HEAD node on ALPHA..."
echo "   IP: $ALPHA_IP"
echo "   Port: $PORT"
echo "   CPUs: $CPUS"
echo ""

# Start Ray with explicit configuration
ray start --head \
    --node-ip-address="$ALPHA_IP" \
    --port="$PORT" \
    --num-cpus="$CPUS" \
    --disable-usage-stats \
    2>&1 | while read line; do
        if [[ $line == *"Ray runtime started"* ]]; then
            echo -e "${GREEN}✅ Ray head node started successfully!${NC}"
        elif [[ $line == *"ray.init"* ]]; then
            echo -e "${YELLOW}📋 Connection info for worker nodes:${NC}"
        fi
        echo "$line"
    done

# Extract connection string
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}   ALPHA Node Ready${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "📋 To connect BETA node, run on beta machine:"
echo ""
echo -e "${YELLOW}ray start --address='$ALPHA_IP:$PORT' --num-cpus=32${NC}"
echo ""
echo "🔍 Check cluster status with:"
echo "   ray status"
echo ""

# Quick status check
sleep 3
echo "🔍 Current cluster status:"
ray status 2>/dev/null | head -15 || echo "Status check failed - cluster may still be initializing"