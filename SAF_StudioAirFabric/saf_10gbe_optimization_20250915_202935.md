# Studio Air Fabric - 10GbE Network Optimization Guide

## Current Situation
- Both ALPHA and BETA Mac Studios have 10GbE capability
- Currently running at 1Gbps due to auto-negotiation
- Both nodes support: 10Gbase-T, 5000Base-T, 2500Base-T, 1000baseT

## Requirements for 10GbE

### 1. Hardware Requirements ✓
- **NICs**: Mac Studio built-in 10GbE ✅ (Confirmed on both nodes)
- **Switch**: Need 10GbE switch with at least 2 ports
- **Cables**: Cat6a (55m max) or Cat7 (100m max) required

### 2. Current Bottleneck
The 1Gbps limitation is because:
- Your switch likely only supports 1Gbps
- OR cables are Cat5e/Cat6 (not Cat6a/Cat7)

## Solution Options

### Option 1: Direct Connection (No Switch) - RECOMMENDED
Connect ALPHA and BETA directly with a Cat6a/Cat7 cable:

```bash
# On ALPHA - Force 10Gb and configure static IP
sudo networksetup -setMedia "Ethernet" "10Gbase-T <full-duplex>"
sudo networksetup -setmanual "Ethernet" 10.0.0.10 255.255.255.0

# On BETA - Force 10Gb and configure static IP
sudo networksetup -setMedia "Ethernet" "10Gbase-T <full-duplex>"
sudo networksetup -setmanual "Ethernet" 10.0.0.11 255.255.255.0
```

### Option 2: Upgrade Switch
Purchase a 10GbE switch (examples):
- Ubiquiti Flex XG (4x 10GbE) - $299
- QNAP QSW-308-1C (3x 10GbE + 8x 1GbE) - $249
- MikroTik CRS305-1G-4S+IN (4x SFP+) - $149 + DAC cables

### Option 3: Intermediate Speeds
If 10GbE isn't feasible, try 2.5Gb or 5Gb (many newer switches support this):

```bash
# Try 5Gbps
sudo networksetup -setMedia "Ethernet" "5000Base-T <full-duplex>"

# Or try 2.5Gbps
sudo networksetup -setMedia "Ethernet" "2500Base-T <full-duplex>"
```

## Testing Performance

### 1. Install iperf3
```bash
brew install iperf3
```

### 2. Run Speed Test
```bash
# On ALPHA (server)
iperf3 -s

# On BETA (client)
iperf3 -c 10.0.0.10 -t 30
```

Expected Results:
- 1Gbps: ~940 Mbps
- 2.5Gbps: ~2.35 Gbps
- 5Gbps: ~4.7 Gbps
- 10Gbps: ~9.4 Gbps

## MTU Optimization (Jumbo Frames)

After establishing 10GbE connection:

```bash
# Enable jumbo frames (MTU 9000) for better throughput
sudo ifconfig en0 mtu 9000

# Make permanent
sudo networksetup -setMTU "Ethernet" 9000
```

## Ray Cluster Performance Tuning

Once 10GbE is working, optimize Ray for high bandwidth:

```python
# In ray.init() or ray start
ray.init(
    _system_config={
        "object_spilling_config": json.dumps({
            "type": "filesystem",
            "params": {
                "directory_path": "/tmp/ray",
                "buffer_size": 100_000_000,  # 100MB buffer
            }
        }),
        "max_io_workers": 8,  # Increase I/O workers
        "object_store_memory": 10_000_000_000,  # 10GB object store
    }
)
```

## Quick Test Commands

```bash
# Check current speed
ifconfig en0 | grep media

# Check link status
networksetup -getMedia "Ethernet"

# Force renegotiation
sudo ifconfig en0 down && sudo ifconfig en0 up

# Monitor traffic
nettop -m tcp
```

## Troubleshooting

1. **Link won't negotiate 10Gb**
   - Check cable rating (must be Cat6a or Cat7)
   - Try different cable
   - Check for damaged connectors

2. **Intermittent connection**
   - Reduce to 5Gbps (more tolerant of cable issues)
   - Check cable length (<55m for Cat6a)

3. **High CPU usage**
   - Enable flow control: `sudo networksetup -setMedia "Ethernet" "10Gbase-T <full-duplex, flow-control>"`
   - Disable EEE if latency sensitive: Remove `energy-efficient-ethernet`

## Recommended Action

For immediate testing without new hardware:
1. Get a Cat6a or Cat7 cable ($20-30)
2. Connect ALPHA and BETA directly (no switch)
3. Configure static IPs on separate subnet (10.0.0.x)
4. Force 10Gb media settings
5. Test with iperf3

This will give you 10x performance improvement for Ray distributed tasks!