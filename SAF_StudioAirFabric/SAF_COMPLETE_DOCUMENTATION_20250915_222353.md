# Studio Air Fabric (SAF) - Complete Documentation
## 2-Node Mac Studio M3 Ultra Cluster with Ray + MLX

### Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Installation Guide](#installation-guide)
4. [Network Configuration](#network-configuration)
5. [Operational Commands](#operational-commands)
6. [Performance Metrics](#performance-metrics)
7. [Troubleshooting](#troubleshooting)
8. [Future Upgrades](#future-upgrades)

---

## Executive Summary

**Studio Air Fabric** is a distributed computing cluster built on two Mac Studio M3 Ultra nodes, leveraging Apple's native Metal acceleration through MLX while orchestrating workloads via Ray.

### Key Achievements
- ✅ **2-node Ray cluster operational** with 64 CPUs and 670GB RAM
- ✅ **MLX Metal acceleration preserved** (no virtualization)
- ✅ **Python version matching solved** via pyenv
- ✅ **945 Mbps network throughput** (10GbE ready)
- ✅ **Web dashboard** at http://192.168.1.172:8265
- ⚠️ **GPU cores NOT clustered** - Each node uses local GPU independently

### System Specifications
| Component | ALPHA Node | BETA Node |
|-----------|------------|-----------|
| Hardware | Mac Studio M3 Ultra | Mac Studio M3 Ultra |
| CPUs | 32 cores | 32 cores |
| GPU | 76-core GPU (local) | 76-core GPU (local) |
| RAM | ~444 GB | ~225 GB |
| Network | 1Gbps (10GbE capable) | 1Gbps (10GbE capable) |
| IP Address | 192.168.1.172 | 192.168.1.42 |
| Python | 3.9.23 (Homebrew) | 3.9.23 (pyenv) |
| Ray | 2.49.1 | 2.49.1 |
| MLX | 0.29.1 | 0.29.1 |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Studio Air Fabric (SAF)                   │
├───────────────────────────┬─────────────────────────────────┤
│         ALPHA Node        │          BETA Node              │
│   (Head/Orchestrator)     │        (Worker Node)            │
├───────────────────────────┼─────────────────────────────────┤
│   Mac Studio M3 Ultra     │    Mac Studio M3 Ultra          │
│   32 CPU / 444GB RAM      │    32 CPU / 225GB RAM           │
│   Python 3.9.23           │    Python 3.9.23                │
│   Ray Head + Worker       │    Ray Worker                   │
│   MLX Metal Acceleration  │    MLX Metal Acceleration       │
└───────────────────────────┴─────────────────────────────────┘
                    │                    │
                    └────────┬───────────┘
                             │
                    ┌────────┴────────┐
                    │  1Gbps Network   │
                    │  (10GbE Ready)   │
                    └─────────────────┘
```

### Software Stack
- **Orchestration**: Ray 2.49.1 (distributed computing)
- **ML Framework**: MLX 0.29.1 (Apple Metal acceleration)
- **Language Models**: MLX-LM 0.27.1
- **Python**: 3.9.23 (exact match required)
- **Network**: Tailscale VPN for secure remote access

---

## Installation Guide

### Prerequisites
- 2x Mac Studio M3 Ultra
- Network connectivity (1Gbps minimum)
- Admin access on both machines
- SSH key authentication configured

### Step 1: Install Python 3.9.23 on ALPHA

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.9
brew install python@3.9

# Verify version
python3.9 --version  # Should show 3.9.23
```

### Step 2: Install Python 3.9.23 on BETA

```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Reload shell
source ~/.zshrc

# Install Python 3.9.23
pyenv install 3.9.23
pyenv global 3.9.23

# Verify
python3 --version  # Should show 3.9.23
```

### Step 3: Create Virtual Environments

**On ALPHA:**
```bash
python3.9 -m venv ~/saf-venv-39
source ~/saf-venv-39/bin/activate
pip install --upgrade pip
pip install "ray[default]==2.*" mlx mlx-lm
```

**On BETA:**
```bash
python3 -m venv ~/saf-venv-matched
source ~/saf-venv-matched/bin/activate
pip install --upgrade pip
pip install "ray[default]==2.*" mlx mlx-lm
```

### Step 4: Start Ray Cluster

**On ALPHA (Head Node):**
```bash
source ~/saf-venv-39/bin/activate
RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start \
  --head \
  --port=6380 \
  --dashboard-host=0.0.0.0 \
  --node-ip-address=192.168.1.172
```

**On BETA (Worker Node):**
```bash
source ~/saf-venv-matched/bin/activate
RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start \
  --address="192.168.1.172:6380"
```

### Step 5: Verify Cluster

```bash
# On ALPHA
source ~/saf-venv-39/bin/activate
ray status

# Expected output:
# Active:
#  2 nodes
# Resources:
#  64.0 CPU
#  670.67GiB memory
```

---

## Network Configuration

### Current Setup
- **Speed**: 945 Mbps (94.5% of 1Gbps theoretical)
- **Latency**: <1ms between nodes
- **Router**: Linksys Smart Wi-Fi (bottleneck)

### Network Test Tool
```python
# network_speed_test.py - Created during setup
# Server (ALPHA)
python3 network_speed_test.py server

# Client (BETA)
python3 network_speed_test.py client 192.168.1.172
```

### 10GbE Upgrade Path

**Recommended Switch**: QNAP QSW-M408-4C ($379)
- 4x 10Gb RJ45 ports
- 4x 1Gb RJ45 ports
- Silent operation
- Web management

**Configuration for 10GbE:**
```bash
# Check current speed
networksetup -getMedia "Ethernet"

# Force 10Gb (after hardware upgrade)
sudo networksetup -setMedia "Ethernet" "10Gbase-T <full-duplex>"

# Enable jumbo frames
sudo networksetup -setMTU "Ethernet" 9000
```

---

## Operational Commands

### Daily Operations

**Start Cluster:**
```bash
# ALPHA
source ~/saf-venv-39/bin/activate
RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start --head --port=6380 --dashboard-host=0.0.0.0 --node-ip-address=192.168.1.172

# BETA (via SSH)
ssh arthurdell@beta 'source ~/saf-venv-matched/bin/activate && RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start --address="192.168.1.172:6380"'
```

**Check Status:**
```bash
ray status
# or visit http://192.168.1.172:8265
```

**Stop Cluster:**
```bash
# Both nodes
ray stop
```

### Testing Scripts

**Single Node Test (saf_test.py):**
```python
import ray
import mlx.core as mx

ray.init(address="auto")

@ray.remote
def matmul_sum(n):
    a = mx.random.uniform(shape=[n, n])
    b = mx.random.uniform(shape=[n, n])
    return mx.matmul(a, b).sum().item()

futures = [matmul_sum.remote(4096) for _ in range(4)]
results = ray.get(futures)
print(f"Results: {results}")
```

**Run Test:**
```bash
source ~/saf-venv-39/bin/activate
python saf_test.py
```

---

## Performance Metrics

### Computational Performance
- **Single Node**: 4 parallel MLX tasks in 0.22s
- **Cluster Total**: 64 CPUs, 670GB RAM
- **MLX Operations**: Native Metal acceleration on both nodes
- **GPU Performance**: ~6 TFLOPS per node (152 total GPU cores, not pooled)

### GPU Clustering Reality
- **GPU Memory**: NOT shared between nodes
- **GPU Cores**: 76 per node (152 total) but operate independently
- **Distribution**: Task-level parallelism, not GPU-level
- **Architecture**: Each node processes tasks with its local GPU
- **Use Case**: Best for embarrassingly parallel workloads

### Network Performance
| Metric | Current (1Gbps) | After 10GbE Upgrade |
|--------|-----------------|---------------------|
| Throughput | 945 Mbps | 9,400 Mbps |
| Transfer 10GB | 80 seconds | 8 seconds |
| Ray object sync | 125 MB/s | 1.25 GB/s |
| Latency | <1ms | <1ms |

### Benchmark Results
```bash
# Network throughput test
python network_speed_test.py server  # ALPHA
ssh arthurdell@beta "python3 network_speed_test.py client 192.168.1.172"
# Result: 945.11 Mbps
```

---

## Troubleshooting

### Common Issues and Solutions

**1. Python Version Mismatch**
```
Error: Version mismatch: Python 3.9.23 vs 3.9.6
Solution: Ensure exact Python versions match using pyenv
```

**2. Ray Port Conflicts**
```
Error: Port 6379 already in use
Solution: Use port 6380 (Redis uses 6379)
```

**3. Node Connection Timeout**
```
Error: Failed to connect to GCS
Solution:
- Check firewall settings
- Verify IP addresses
- Ensure RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 is set
```

**4. MLX Import Error**
```
Error: No module named 'mlx'
Solution: pip install mlx mlx-lm in virtual environment
```

### Debug Commands
```bash
# Check Ray processes
ps aux | grep ray

# Check network connectivity
ping -c 3 192.168.1.42  # From ALPHA
ping -c 3 192.168.1.172  # From BETA

# Check Python versions
python3 --version  # On both nodes

# Check listening ports
lsof -i :6380
lsof -i :8265

# SSH connectivity test
ssh arthurdell@beta hostname
```

---

## Future Upgrades

### Immediate (This Week)
- [x] Python version matching via pyenv
- [x] 2-node cluster operational
- [ ] Persistent service configuration (launchd)
- [ ] Automated startup scripts

### Short Term (This Month)
- [ ] 10GbE switch installation ($379)
- [ ] NFS shared storage configuration
- [ ] Model repository setup
- [ ] MLX model serving API

### Medium Term (Quarter)
- [ ] Add 3rd node for redundancy
- [ ] Kubernetes orchestration
- [ ] Distributed training pipelines
- [ ] Monitoring with Prometheus/Grafana

### Long Term (Year)
- [ ] Scale to 4+ nodes
- [ ] Implement fault tolerance
- [ ] Production ML serving
- [ ] Integration with cloud services

---

## File Inventory

### Created During Setup
1. **saf_test.py** - Single node MLX test
2. **saf_2node_test.py** - Two-node cluster test
3. **saf_2node_distributed.py** - Forced distribution test
4. **network_speed_test.py** - Network throughput tool
5. **saf_10gbe_optimization.md** - Network upgrade guide
6. **saf_10gbe_switch_buying_guide.md** - Hardware recommendations
7. **saf_network_performance_report.md** - Performance analysis
8. **saf_deployment_summary.md** - Quick reference
9. **saf_final_status.md** - Current state summary
10. **saf_status.sh** - Quick cluster status check script
11. **saf_verify_2nodes.py** - 2-node verification test
12. **saf_gpu_test.py** - GPU/Metal clustering test
13. **saf_gpu_distributed.py** - GPU distribution test
14. **saf_gpu_final_test.py** - Final GPU verification

### Configuration Files
- **~/saf-venv-39/** - ALPHA virtual environment
- **~/saf-venv-matched/** - BETA virtual environment
- **~/.pyenv/** - Python version management (BETA)

---

## Quick Reference Card

```bash
# Quick Status Check
./saf_status.sh

# Start Everything (ALPHA)
source ~/saf-venv-39/bin/activate
RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start --head --port=6380 --dashboard-host=0.0.0.0 --node-ip-address=192.168.1.172

# Join BETA
ssh arthurdell@beta 'source ~/saf-venv-matched/bin/activate && RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 ray start --address="192.168.1.172:6380"'

# Check Status
ray status
open http://192.168.1.172:8265

# Run Test
python saf_test.py

# Stop Everything
ray stop
ssh arthurdell@beta "ray stop"
```

---

## GPU Clustering Clarification

### What GPU Clustering Means Here
**Studio Air Fabric does NOT provide traditional GPU clustering.** Instead:

1. **Independent GPUs**: Each Mac Studio has its own 76-core GPU
2. **No Memory Pooling**: GPU memory is NOT shared between nodes
3. **No Direct GPU Communication**: Unlike NVIDIA NVLink or AMD Infinity Fabric
4. **Task-Level Distribution**: Ray sends different tasks to different nodes
5. **Local GPU Acceleration**: Each task uses the node's local Metal GPU via MLX

### Architecture Reality
```
Traditional GPU Cluster (NOT what we have):
[GPU 1] ←→ [GPU 2]  (Shared memory, direct communication)

Studio Air Fabric (What we have):
[Node 1: CPU + GPU] ← Ray Orchestration → [Node 2: CPU + GPU]
     ↓                                           ↓
  Task A uses                                Task B uses
  local GPU                                  local GPU
```

### Practical Implications

**Good For:**
- Batch processing different models simultaneously
- Parallel inference on separate data sets
- Training multiple small models concurrently
- Any embarrassingly parallel ML workload

**Not Good For:**
- Single large models requiring >128GB unified memory
- Models requiring GPU-to-GPU communication
- Distributed training of a single large model
- Workloads requiring unified GPU memory space

### Performance Expectations
- **Single Node**: ~6 TFLOPS with 76 GPU cores
- **Both Nodes**: ~12 TFLOPS total (when both process tasks)
- **Scaling**: Near-linear for independent tasks
- **Bottleneck**: Network bandwidth for data transfer (currently 1Gbps)

---

## Support Information

### Key Decisions Made
1. **No Docker**: Preserves MLX Metal acceleration
2. **pyenv on BETA**: Solves Python version matching
3. **Port 6380**: Avoids Redis conflict on 6379
4. **1Gbps for now**: 10GbE ready with switch upgrade

### Critical Success Factors
- Exact Python version matching (3.9.23)
- RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 environment variable
- Direct network connectivity (no NAT)
- SSH key authentication for remote management

### Contact
- Dashboard: http://192.168.1.172:8265
- ALPHA: 192.168.1.172
- BETA: 192.168.1.42
- Tailscale: alpha (100.106.170.128), beta (100.84.202.68)

---

**Document Version**: 1.1
**Date**: September 15, 2025
**Status**: FULLY OPERATIONAL ✅

**Current State**:
- 2-node Ray cluster active (64 CPUs, 668GB RAM)
- MLX Metal acceleration preserved on both nodes
- Dashboard accessible at http://192.168.1.172:8265
- Status check script: `./saf_status.sh`

*Studio Air Fabric - Distributed AI Computing on Apple Silicon*