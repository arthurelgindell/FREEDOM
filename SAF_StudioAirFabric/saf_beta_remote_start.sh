#!/bin/bash
# SAF Remote Beta Node Starter
# Starts Ray worker on BETA machine via SSH from ALPHA

echo "========================================="
echo "   SAF - Remote BETA Node Starter       "
echo "========================================="
echo ""

# Configuration
BETA_IP="100.84.202.68"
ALPHA_IP="100.106.170.128"
PORT="6380"
BETA_USER="arthurdell"  # Update if different

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check SSH connectivity
echo "🔍 Checking SSH connectivity to BETA..."
if ssh -o ConnectTimeout=5 "$BETA_USER@$BETA_IP" "echo 'SSH connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH connection established${NC}"
else
    echo -e "${RED}❌ Cannot SSH to BETA${NC}"
    echo ""
    echo "Please ensure:"
    echo "1. SSH keys are configured between ALPHA and BETA"
    echo "2. BETA machine is powered on"
    echo "3. Tailscale is connected"
    echo ""
    echo "To set up SSH keys (if not done):"
    echo "  ssh-keygen -t ed25519"
    echo "  ssh-copy-id $BETA_USER@$BETA_IP"
    exit 1
fi

# Check if Ray is installed on BETA
echo ""
echo "🔍 Checking Ray installation on BETA..."
if ssh "$BETA_USER@$BETA_IP" "which ray" 2>/dev/null; then
    echo -e "${GREEN}✅ Ray is installed on BETA${NC}"
else
    echo -e "${YELLOW}⚠️  Ray not found on BETA - attempting to install...${NC}"
    ssh "$BETA_USER@$BETA_IP" "pip3 install ray" || {
        echo -e "${RED}❌ Failed to install Ray on BETA${NC}"
        exit 1
    }
fi

# Stop any existing Ray on BETA
echo ""
echo "🛑 Stopping existing Ray instances on BETA..."
ssh "$BETA_USER@$BETA_IP" "ray stop --force 2>/dev/null" 2>/dev/null

sleep 2

# Start Ray worker on BETA
echo ""
echo "🚀 Starting Ray worker on BETA..."
echo "   Connecting to head at: $ALPHA_IP:$PORT"
echo ""

# Create start script on BETA
ssh "$BETA_USER@$BETA_IP" "cat > /tmp/start_ray_worker.sh" << 'SCRIPT'
#!/bin/bash
ray start \
    --address="100.106.170.128:6380" \
    --node-ip-address="100.84.202.68" \
    --num-cpus=32 \
    --memory=$((220 * 1024 * 1024 * 1024)) \
    --disable-usage-stats
SCRIPT

# Make it executable and run
ssh "$BETA_USER@$BETA_IP" "chmod +x /tmp/start_ray_worker.sh && /tmp/start_ray_worker.sh" 2>&1 | while read line; do
    if [[ $line == *"Ray runtime started"* ]]; then
        echo -e "${GREEN}✅ BETA worker started successfully!${NC}"
    elif [[ $line == *"Connected to Ray"* ]]; then
        echo -e "${GREEN}✅ Connected to cluster${NC}"
    fi
    echo "$line"
done

# Verify cluster status
echo ""
echo "🔍 Verifying cluster status..."
sleep 3

# Check from ALPHA
ray status 2>/dev/null | head -20

# Count nodes
if ray status 2>/dev/null | grep -q "2 node(s)"; then
    echo ""
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}   ✅ 2-NODE CLUSTER ACTIVE${NC}"
    echo -e "${GREEN}=========================================${NC}"
    echo ""
    echo "📊 Cluster Resources:"
    echo "   • 2 Mac Studio nodes (ALPHA + BETA)"
    echo "   • 64 CPU cores total"
    echo "   • 440 GB memory total"
    echo "   • MLX GPU acceleration on both nodes"
    echo ""
    echo "🧪 Test the cluster:"
    echo "   python3 SAF_StudioAirFabric/saf_2node_test.py"
    echo ""
    echo "📊 Monitor the cluster:"
    echo "   python3 SAF_StudioAirFabric/saf_cluster_monitor.py"
else
    echo -e "${YELLOW}⚠️  BETA may still be connecting...${NC}"
    echo "Check status with: ray status"
fi