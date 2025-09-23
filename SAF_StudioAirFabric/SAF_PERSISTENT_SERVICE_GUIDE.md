# SAF Persistent Service Configuration Guide

**Status**: ✅ Service Framework Created
**Date**: 2025-09-23

## Overview

SAF can be configured to run as a persistent system service that:
- Starts automatically on system boot
- Restarts if crashed
- Waits for network connectivity
- Maintains 24/7 availability

## Service Architecture

```
┌─────────────────────────────────────────────┐
│         Persistent SAF Services             │
├─────────────────────────────────────────────┤
│  ALPHA (Head Service)                       │
│  • com.freedom.saf-alpha.plist              │
│  • Auto-starts Ray head on boot             │
│  • Restarts on failure                      │
│  • Logs to: logs/saf-alpha.log              │
├─────────────────────────────────────────────┤
│  BETA (Worker Service)                      │
│  • com.freedom.saf-beta.plist               │
│  • Waits for head node availability         │
│  • Connects with retry logic                │
│  • Logs to: ~/saf-beta.log                  │
├─────────────────────────────────────────────┤
│  Monitor Service (Optional)                 │
│  • com.freedom.saf-monitor.plist            │
│  • Health checks every 60 seconds           │
│  • Auto-restarts failed nodes               │
│  • Logs to: logs/saf-monitor.log            │
└─────────────────────────────────────────────┘
```

## Installation

### On ALPHA (Head Node)

1. **Install the service**:
```bash
cd /Volumes/DATA/FREEDOM
./SAF_StudioAirFabric/saf_install_service.sh
```

2. **Verify installation**:
```bash
# Check service status
launchctl list | grep saf

# Check Ray cluster
python3.9 -m ray.scripts.scripts status
```

### On BETA (Worker Node)

1. **Copy files to BETA**:
```bash
# From ALPHA
scp SAF_StudioAirFabric/com.freedom.saf-beta.plist arthurdell@100.84.202.68:~/
scp SAF_StudioAirFabric/saf_install_service.sh arthurdell@100.84.202.68:~/
```

2. **SSH to BETA and install**:
```bash
ssh arthurdell@100.84.202.68

# Create connect script if not exists
cat > ~/connect_to_ray.py << 'EOF'
import os
import sys
import time

time.sleep(10)  # Wait for network
os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'

import ray._private.utils
def bypass_version_check(*args, **kwargs):
    return
ray._private.utils.check_version_info = bypass_version_check

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
        print(f"Attempt {attempt + 1} failed: {e}")
        time.sleep(retry_delay)
        retry_delay *= 2
EOF

# Install service
mkdir -p ~/Library/LaunchAgents
cp com.freedom.saf-beta.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.freedom.saf-beta.plist
```

## Service Management

### Start Services
```bash
# ALPHA
launchctl load ~/Library/LaunchAgents/com.freedom.saf-alpha.plist

# BETA (via SSH)
ssh arthurdell@100.84.202.68 \
  "launchctl load ~/Library/LaunchAgents/com.freedom.saf-beta.plist"
```

### Stop Services
```bash
# ALPHA
launchctl unload ~/Library/LaunchAgents/com.freedom.saf-alpha.plist

# BETA (via SSH)
ssh arthurdell@100.84.202.68 \
  "launchctl unload ~/Library/LaunchAgents/com.freedom.saf-beta.plist"
```

### View Service Status
```bash
# List all SAF services
launchctl list | grep saf

# Check specific service
launchctl print gui/$(id -u)/com.freedom.saf-alpha
```

### Monitor Logs
```bash
# ALPHA logs
tail -f /Volumes/DATA/FREEDOM/SAF_StudioAirFabric/logs/saf-alpha.log
tail -f /Volumes/DATA/FREEDOM/SAF_StudioAirFabric/logs/saf-alpha-error.log

# BETA logs (via SSH)
ssh arthurdell@100.84.202.68 "tail -f ~/saf-beta.log"

# Monitor service logs
tail -f /Volumes/DATA/FREEDOM/SAF_StudioAirFabric/logs/saf-monitor.log
```

## Auto-Recovery Features

### Built-in Recovery
The launchd configuration includes:
- **KeepAlive**: Restarts on crash
- **NetworkState**: Waits for network
- **ThrottleInterval**: 30-second cooldown between restarts
- **Nice**: -5 priority for better performance

### Monitor Service (Optional)
Install the monitor for additional health checks:

```bash
# Install monitor
cp SAF_StudioAirFabric/com.freedom.saf-monitor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.freedom.saf-monitor.plist

# Monitor will:
# - Check cluster health every 60 seconds
# - Restart nodes if they fail
# - Test GPU functionality
# - Log all events
```

## Troubleshooting

### Service Won't Start
```bash
# Check error logs
tail -50 /Volumes/DATA/FREEDOM/SAF_StudioAirFabric/logs/saf-alpha-error.log

# Check launchd errors
log show --predicate 'subsystem == "com.apple.xpc.launchd"' --last 1h | grep saf

# Manual start for testing
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
python3.9 -m ray.scripts.scripts start --head --port=6380
```

### Exit Code 78 (Configuration Error)
- Check Python path: `/usr/bin/python3.9`
- Verify working directory exists
- Check environment variables in plist

### Service Starts But Ray Not Accessible
- Port 6380 may be in use
- Check for zombie Ray processes: `pkill -f ray::`
- Clean session files: `rm -rf /tmp/ray/session_*`

### BETA Won't Connect
- Ensure ALPHA service is running first
- Check network connectivity: `ping 100.106.170.128`
- Verify Python virtual environment on BETA

## Performance Optimization

### Resource Allocation
Modify in plist files:
```xml
<string>--num-cpus=32</string>
<string>--memory=400000000000</string>
<string>--object-store-memory=4000000000</string>
```

### Start Priority
Control start order:
```xml
<!-- ALPHA: Start immediately -->
<key>RunAtLoad</key>
<true/>

<!-- BETA: Start 2 minutes after boot -->
<key>StartCalendarInterval</key>
<dict>
    <key>Minute</key>
    <integer>2</integer>
</dict>
```

## Verification

### Full System Test
```bash
# 1. Check services are loaded
launchctl list | grep saf

# 2. Verify Ray cluster
python3.9 -m ray.scripts.scripts status

# 3. Test GPU distribution
python3.9 test_gpu_force_beta.py

# 4. Monitor health
python3.9 SAF_StudioAirFabric/saf_cluster_monitor.py
```

### Expected Output
```
com.freedom.saf-alpha    (running)
com.freedom.saf-beta     (running via SSH)
com.freedom.saf-monitor  (optional)

Cluster: 2 nodes, 64 CPUs, ~860 GB RAM
GPU Test: Task executed on BETA.local ✅
```

## Benefits of Persistent Service

1. **24/7 Availability**: Always ready for ML workloads
2. **Auto-Recovery**: Self-heals from crashes
3. **Zero Maintenance**: Set and forget
4. **Boot Resilience**: Survives system restarts
5. **Network Aware**: Waits for connectivity

## Security Considerations

- Services run as user (not root)
- No password storage in plists
- SSH keys used for BETA connection
- Logs stored locally only

## Conclusion

With persistent services configured, SAF provides enterprise-grade reliability for distributed GPU computing. The system automatically maintains itself, recovers from failures, and ensures the 2-node cluster is always available for ML workloads.