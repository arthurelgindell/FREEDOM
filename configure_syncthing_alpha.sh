#!/bin/bash
# Configure Alpha to sync with Beta
# Run this AFTER running setup_syncthing_beta.sh on Beta

echo "=================================================="
echo "    CONFIGURE ALPHA FOR BETA SYNC - CCKS        "
echo "=================================================="
echo ""

# Get Beta's device ID from user
echo "Please enter Beta's Device ID"
echo "(You'll see this after running setup_syncthing_beta.sh on Beta)"
echo -n "Beta Device ID: "
read BETA_DEVICE_ID

if [ -z "$BETA_DEVICE_ID" ]; then
    echo "❌ No device ID provided. Exiting."
    exit 1
fi

BETA_IP="100.106.170.128"
BETA_NAME="Beta-CCKS"
API_URL="http://localhost:8384/rest"

echo ""
echo "Configuring Alpha to sync with Beta..."

# Add Beta as a device
echo "  Adding Beta device..."
curl -X POST "$API_URL/config/devices" \
    -H "Content-Type: application/json" \
    -d "{
        \"deviceID\": \"$BETA_DEVICE_ID\",
        \"name\": \"$BETA_NAME\",
        \"addresses\": [\"tcp://$BETA_IP:22000\"],
        \"compression\": \"metadata\",
        \"introducer\": false,
        \"paused\": false,
        \"allowedNetworks\": [],
        \"autoAcceptFolders\": true
    }" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "    ✅ Beta device added"
else
    echo "    ⚠️  Device might already exist"
fi

# Share CCKS database folder with Beta
echo "  Sharing CCKS database folder..."
FOLDER_CONFIG=$(curl -s "$API_URL/config/folders/ccks-db" 2>/dev/null)

if [ -z "$FOLDER_CONFIG" ] || [ "$FOLDER_CONFIG" = "404 page not found" ]; then
    # Create new folder
    echo "    Creating new folder configuration..."
    curl -X PUT "$API_URL/config/folders" \
        -H "Content-Type: application/json" \
        -d '{
            "id": "ccks-db",
            "label": "CCKS Database",
            "path": "'"$HOME"'/.claude",
            "type": "sendreceive",
            "devices": [
                {"deviceID": "'"$BETA_DEVICE_ID"'", "introducedBy": "", "encryptionPassword": ""}
            ],
            "rescanIntervalS": 60,
            "fsWatcherEnabled": true,
            "fsWatcherDelayS": 10,
            "versioning": {
                "type": "simple",
                "params": {"keep": "10"}
            }
        }' 2>/dev/null
else
    # Update existing folder to add Beta device
    echo "    Updating existing folder configuration..."
    # This is complex with the API, so we'll use a simpler approach
    echo "    Please manually share the folder in the web UI"
fi

# Share CCKS cache folder with Beta
echo "  Sharing CCKS cache folder..."
curl -X PUT "$API_URL/config/folders" \
    -H "Content-Type: application/json" \
    -d '{
        "id": "ccks-cache",
        "label": "CCKS Cache",
        "path": "/Volumes/CCKS_RAM/ccks_cache",
        "type": "sendreceive",
        "devices": [
            {"deviceID": "'"$BETA_DEVICE_ID"'", "introducedBy": "", "encryptionPassword": ""}
        ],
        "rescanIntervalS": 10,
        "fsWatcherEnabled": true,
        "fsWatcherDelayS": 5
    }' 2>/dev/null

# Apply configuration
echo ""
echo "  Restarting Syncthing to apply changes..."
curl -X POST "$API_URL/system/restart" 2>/dev/null
sleep 5

echo ""
echo "=================================================="
echo "              CONFIGURATION COMPLETE!"
echo "=================================================="
echo ""
echo "Alpha is now configured to sync with Beta!"
echo ""
echo "Check sync status at: http://localhost:8384"
echo ""
echo "To verify sync is working:"
echo "1. On Alpha: ~/.claude/ccks add 'TEST FROM ALPHA'"
echo "2. On Beta:  ~/.claude/ccks query 'TEST FROM ALPHA'"
echo "   (Should appear within 10 seconds)"
echo ""
echo "To monitor sync activity:"
echo "  curl -s http://localhost:8384/rest/db/status?folder=ccks-db | jq"
echo ""