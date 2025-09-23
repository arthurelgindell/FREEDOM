#!/bin/bash
# SAF Service Health Monitor
# Monitors and auto-restarts SAF services if they fail

# Configuration
LOG_DIR="/Volumes/DATA/FREEDOM/SAF_StudioAirFabric/logs"
ALPHA_IP="100.106.170.128"
BETA_IP="100.84.202.68"
PORT="6380"
CHECK_INTERVAL=60  # seconds
MAX_RESTART_ATTEMPTS=5
RESTART_COOLDOWN=300  # 5 minutes

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Logging
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/saf-monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_ray_status() {
    python3.9 -c "
import ray
try:
    ray.init(address='$ALPHA_IP:$PORT', ignore_reinit_error=True)
    nodes = ray.nodes()
    alive = [n for n in nodes if n['Alive']]
    print(len(alive))
    ray.shutdown()
except:
    print(0)
" 2>/dev/null
}

check_gpu_on_beta() {
    python3.9 -c "
import ray
try:
    ray.init(address='$ALPHA_IP:$PORT', ignore_reinit_error=True)
    nodes = ray.nodes()
    beta_nodes = [n for n in nodes if n['Alive'] and '$BETA_IP' in n.get('NodeManagerAddress', '')]
    if beta_nodes:
        print('1')
    else:
        print('0')
    ray.shutdown()
except:
    print('0')
" 2>/dev/null
}

restart_alpha() {
    log_message "Restarting ALPHA node..."
    launchctl unload ~/Library/LaunchAgents/com.freedom.saf-alpha.plist 2>/dev/null
    sleep 5
    launchctl load ~/Library/LaunchAgents/com.freedom.saf-alpha.plist
}

restart_beta() {
    log_message "Attempting to restart BETA node..."
    ssh arthurdell@$BETA_IP "launchctl unload ~/Library/LaunchAgents/com.freedom.saf-beta.plist 2>/dev/null; sleep 5; launchctl load ~/Library/LaunchAgents/com.freedom.saf-beta.plist" 2>/dev/null
}

# Main monitoring loop
log_message "SAF Service Monitor started"
restart_count=0
last_restart_time=0

while true; do
    # Check cluster health
    node_count=$(check_ray_status)

    if [ "$node_count" -eq "0" ]; then
        echo -e "${RED}❌ Ray cluster is DOWN${NC}"
        log_message "ERROR: Ray cluster is down"

        # Check if we should restart
        current_time=$(date +%s)
        time_since_restart=$((current_time - last_restart_time))

        if [ $restart_count -lt $MAX_RESTART_ATTEMPTS ] && [ $time_since_restart -gt $RESTART_COOLDOWN ]; then
            log_message "Attempting restart (attempt $((restart_count + 1))/$MAX_RESTART_ATTEMPTS)"
            restart_alpha
            sleep 30
            restart_count=$((restart_count + 1))
            last_restart_time=$current_time
        else
            log_message "ERROR: Max restart attempts reached or in cooldown period"
        fi

    elif [ "$node_count" -eq "1" ]; then
        echo -e "${YELLOW}⚠️  Only 1 node active${NC}"
        log_message "WARNING: Only 1 node active, checking BETA..."

        beta_status=$(check_gpu_on_beta)
        if [ "$beta_status" -eq "0" ]; then
            log_message "BETA node not found, attempting restart..."
            restart_beta
        fi

    else
        echo -e "${GREEN}✅ Cluster healthy: $node_count nodes${NC}"
        log_message "Cluster healthy: $node_count nodes active"
        restart_count=0  # Reset counter on success
    fi

    # Additional health checks
    if [ "$node_count" -gt "0" ]; then
        # Check if GPU tasks can run
        gpu_test=$(python3.9 -c "
import ray
import time
try:
    ray.init(address='$ALPHA_IP:$PORT', ignore_reinit_error=True)
    @ray.remote
    def test_gpu():
        try:
            import mlx.core as mx
            a = mx.ones((100, 100))
            b = mx.ones((100, 100))
            c = a @ b
            mx.eval(c)
            return True
        except:
            return False
    result = ray.get(test_gpu.remote())
    ray.shutdown()
    print('1' if result else '0')
except:
    print('0')
" 2>/dev/null)

        if [ "$gpu_test" -eq "1" ]; then
            echo -e "${GREEN}✅ GPU tasks working${NC}"
        else
            echo -e "${YELLOW}⚠️  GPU tasks not working${NC}"
            log_message "WARNING: GPU task test failed"
        fi
    fi

    # Wait before next check
    sleep $CHECK_INTERVAL
done