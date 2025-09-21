#!/bin/bash

# FREEDOM Platform Dashboard Launcher
# Launches the monitoring dashboard in a new Terminal window

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_SCRIPT="$SCRIPT_DIR/freedom_dashboard.py"

# Check if dashboard script exists
if [ ! -f "$DASHBOARD_SCRIPT" ]; then
    echo "Error: Dashboard script not found at $DASHBOARD_SCRIPT"
    exit 1
fi

echo "Launching FREEDOM Platform Monitoring Dashboard..."
echo "----------------------------------------"
echo "Controls:"
echo "  Q - Quit"
echo "  P - Pause/Resume"
echo "  R - Force Refresh"
echo "----------------------------------------"
echo ""

# Launch the dashboard
cd /Volumes/DATA/FREEDOM
python3 "$DASHBOARD_SCRIPT"