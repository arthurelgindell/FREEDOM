#!/bin/bash
# SAF Service Installation Script
# Installs SAF as a persistent system service using launchd

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================="
echo "   SAF Service Installation"
echo "========================================="
echo ""

# Configuration
PLIST_DIR="$HOME/Library/LaunchAgents"
SAF_DIR="/Volumes/DATA/FREEDOM/SAF_StudioAirFabric"
HOSTNAME=$(hostname -s)

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p "$PLIST_DIR"
mkdir -p "$SAF_DIR/logs"

# Determine which node we're on
if [[ "$HOSTNAME" == "ALPHA" ]]; then
    echo -e "${GREEN}🖥️  Detected ALPHA node${NC}"
    PLIST_FILE="com.freedom.saf-alpha.plist"
    SERVICE_NAME="com.freedom.saf-alpha"

    # Stop any existing Ray
    echo "🛑 Stopping existing Ray instances..."
    python3.9 -m ray.scripts.scripts stop --force 2>/dev/null || true

    # Copy plist
    echo "📝 Installing service configuration..."
    cp "$SAF_DIR/$PLIST_FILE" "$PLIST_DIR/"

elif [[ "$HOSTNAME" == "BETA" ]]; then
    echo -e "${GREEN}🖥️  Detected BETA node${NC}"
    PLIST_FILE="com.freedom.saf-beta.plist"
    SERVICE_NAME="com.freedom.saf-beta"

    # Ensure connect script exists
    if [ ! -f "$HOME/connect_to_ray.py" ]; then
        echo "⚠️  Creating connect_to_ray.py script..."
        cat > "$HOME/connect_to_ray.py" << 'EOF'
import os
import sys
import time

# Wait for network to be ready
time.sleep(10)

os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'

# Monkey-patch version check
import ray._private.utils
def bypass_version_check(*args, **kwargs):
    print("Bypassing version check for 2-node cluster")
    return
ray._private.utils.check_version_info = bypass_version_check

# Retry connection with exponential backoff
max_retries = 10
retry_delay = 5

for attempt in range(max_retries):
    try:
        from ray.scripts.scripts import main
        sys.argv = ['ray', 'start', '--address=100.106.170.128:6380',
                    '--node-ip-address=100.84.202.68', '--num-cpus=32',
                    '--disable-usage-stats', '--block']
        main()
        break
    except Exception as e:
        print(f"Connection attempt {attempt + 1} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            print("Failed to connect after all retries")
            sys.exit(1)
EOF
    fi

    # Copy plist (you'll need to copy this file to BETA manually)
    echo -e "${YELLOW}📋 Copy this file to BETA:${NC}"
    echo "   scp $SAF_DIR/$PLIST_FILE arthurdell@100.84.202.68:~/Library/LaunchAgents/"
    echo ""
    echo "Then on BETA, run:"
    echo "   launchctl load ~/Library/LaunchAgents/$PLIST_FILE"
    exit 0

else
    echo -e "${RED}❌ Unknown hostname: $HOSTNAME${NC}"
    echo "This script must be run on ALPHA or BETA"
    exit 1
fi

# Load the service
echo ""
echo "🚀 Loading SAF service..."

# Unload if already loaded
launchctl unload "$PLIST_DIR/$PLIST_FILE" 2>/dev/null || true

# Load the service
if launchctl load "$PLIST_DIR/$PLIST_FILE"; then
    echo -e "${GREEN}✅ Service loaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to load service${NC}"
    exit 1
fi

# Verify service is running
echo ""
echo "🔍 Verifying service status..."
sleep 5

if launchctl list | grep -q "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ Service is registered${NC}"

    # Check Ray status
    sleep 10
    if python3.9 -m ray.scripts.scripts status 2>/dev/null | grep -q "node"; then
        echo -e "${GREEN}✅ Ray is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Ray may still be starting...${NC}"
    fi
else
    echo -e "${RED}❌ Service not found in launchctl list${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}   SAF Service Installed Successfully${NC}"
echo "========================================="
echo ""
echo "📋 Service will:"
echo "   • Start automatically on boot"
echo "   • Restart if crashed"
echo "   • Wait for network connectivity"
echo "   • Log to $SAF_DIR/logs/"
echo ""
echo "🛠️  Management Commands:"
echo "   View status:  launchctl list | grep saf"
echo "   View logs:    tail -f $SAF_DIR/logs/saf-alpha.log"
echo "   Stop service: launchctl unload ~/Library/LaunchAgents/$PLIST_FILE"
echo "   Start service: launchctl load ~/Library/LaunchAgents/$PLIST_FILE"
echo ""

if [[ "$HOSTNAME" == "ALPHA" ]]; then
    echo "📌 Next Steps:"
    echo "   1. Copy service to BETA:"
    echo "      scp $SAF_DIR/com.freedom.saf-beta.plist arthurdell@100.84.202.68:~/"
    echo "   2. SSH to BETA and install:"
    echo "      ssh arthurdell@100.84.202.68"
    echo "      ./saf_install_service.sh"
fi