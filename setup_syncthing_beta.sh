#!/bin/bash
# Syncthing Setup Script for Beta Node
# Run this script on Beta (100.106.170.128) to set up CCKS replication

echo "=================================================="
echo "    SYNCTHING SETUP FOR BETA - CCKS REPLICATION  "
echo "=================================================="
echo ""

# Configuration
ALPHA_DEVICE_ID="J64ABTL-XGEG4FK-IWADAUE-4GYS4NQ-UNTQE22-BZSUUU2-ZFNCRTY-WCGCYAO"
ALPHA_IP="100.106.170.82"
ALPHA_NAME="Alpha-CCKS"

# Step 1: Check if Syncthing is installed
echo "Step 1: Checking Syncthing installation..."
if ! command -v syncthing &> /dev/null; then
    echo "  Installing Syncthing via Homebrew..."
    brew install syncthing
else
    echo "  ✅ Syncthing already installed"
fi

# Step 2: Check target folders
echo ""
echo "Step 2: Verifying target folders..."
echo -n "  ~/.claude: "
if [ -d "$HOME/.claude" ]; then
    echo "✅ EXISTS"
    ls -la ~/.claude/ccks* 2>/dev/null | head -3
else
    echo "❌ MISSING - Creating..."
    mkdir -p ~/.claude
fi

echo -n "  /Volumes/DATA/FREEDOM: "
if [ -d "/Volumes/DATA/FREEDOM" ]; then
    echo "✅ EXISTS"
else
    echo "⚠️  NOT FOUND - This should match Alpha's structure"
fi

echo -n "  /Volumes/CCKS_RAM: "
if [ -d "/Volumes/CCKS_RAM" ]; then
    echo "✅ EXISTS"
else
    echo "⚠️  NOT FOUND - Creating RAM disk..."
    SIZE_IN_BLOCKS=$((100 * 1024 * 2048))  # 100GB
    DEVICE=$(hdiutil attach -nomount ram://$SIZE_IN_BLOCKS)
    diskutil erasevolume HFS+ "CCKS_RAM" $DEVICE
    mkdir -p /Volumes/CCKS_RAM/ccks_cache
    echo "    ✅ RAM disk created"
fi

# Step 3: Start Syncthing
echo ""
echo "Step 3: Starting Syncthing..."
pkill syncthing 2>/dev/null
sleep 2
/opt/homebrew/opt/syncthing/bin/syncthing --no-browser --no-restart --gui-address="0.0.0.0:8384" > /tmp/syncthing_beta.log 2>&1 &
SYNC_PID=$!
echo "  Syncthing started with PID: $SYNC_PID"
sleep 5

# Step 4: Get Beta's device ID
echo ""
echo "Step 4: Getting Beta device ID..."
BETA_DEVICE_ID=$(/opt/homebrew/opt/syncthing/bin/syncthing --device-id 2>&1 | grep -E "^[A-Z0-9]{7}-" | head -1)
echo "  Beta Device ID: $BETA_DEVICE_ID"

# Step 5: Configure folders via API
echo ""
echo "Step 5: Configuring sync folders..."
API_URL="http://localhost:8384/rest"

# Wait for API to be ready
for i in {1..10}; do
    if curl -s -o /dev/null -w "%{http_code}" $API_URL/system/status | grep -q 200; then
        echo "  ✅ API ready"
        break
    fi
    echo "  Waiting for API... ($i/10)"
    sleep 2
done

# Add Alpha as a device
echo "  Adding Alpha device..."
curl -X POST "$API_URL/config/devices" \
    -H "Content-Type: application/json" \
    -d "{
        \"deviceID\": \"$ALPHA_DEVICE_ID\",
        \"name\": \"$ALPHA_NAME\",
        \"addresses\": [\"tcp://$ALPHA_IP:22000\"],
        \"compression\": \"metadata\",
        \"introducer\": false,
        \"paused\": false,
        \"allowedNetworks\": [],
        \"autoAcceptFolders\": true
    }" 2>/dev/null

# Configure CCKS database folder
echo "  Configuring CCKS database folder..."
curl -X PUT "$API_URL/config/folders" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "ccks-db",
        "label": "CCKS Database",
        "path": "'"$HOME"'/.claude",
        "type": "sendreceive",
        "devices": [
            {"deviceID": "'"$ALPHA_DEVICE_ID"'", "introducedBy": "", "encryptionPassword": ""}
        ],
        "rescanIntervalS": 60,
        "fsWatcherEnabled": true,
        "fsWatcherDelayS": 10,
        "versioning": {
            "type": "simple",
            "params": {"keep": "10"}
        }
    }' 2>/dev/null

# Configure CCKS cache folder
echo "  Configuring CCKS cache folder..."
curl -X PUT "$API_URL/config/folders" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "ccks-cache",
        "label": "CCKS Cache",
        "path": "/Volumes/CCKS_RAM/ccks_cache",
        "type": "sendreceive",
        "devices": [
            {"deviceID": "'"$ALPHA_DEVICE_ID"'", "introducedBy": "", "encryptionPassword": ""}
        ],
        "rescanIntervalS": 10,
        "fsWatcherEnabled": true,
        "fsWatcherDelayS": 5
    }' 2>/dev/null

# Step 6: Restart Syncthing to apply configuration
echo ""
echo "Step 6: Restarting Syncthing with new configuration..."
curl -X POST "$API_URL/system/restart" 2>/dev/null
sleep 5

# Step 7: Display status
echo ""
echo "=================================================="
echo "              SETUP COMPLETE!"
echo "=================================================="
echo ""
echo "Beta Device ID: $BETA_DEVICE_ID"
echo "Alpha Device ID: $ALPHA_DEVICE_ID"
echo ""
echo "Web UI: http://$(hostname -I 2>/dev/null || echo localhost):8384"
echo "Log file: /tmp/syncthing_beta.log"
echo ""
echo "NEXT STEPS:"
echo "1. On Alpha, add Beta device with ID: $BETA_DEVICE_ID"
echo "2. Share the ccks-db and ccks-cache folders with Beta"
echo "3. Accept the folder shares on Beta (or auto-accept is enabled)"
echo ""
echo "To monitor sync status:"
echo "  tail -f /tmp/syncthing_beta.log"
echo ""
echo "To check CCKS on Beta:"
echo "  ~/.claude/ccks stats"
echo ""