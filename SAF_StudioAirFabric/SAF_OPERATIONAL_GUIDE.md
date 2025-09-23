# SAF (Studio Air Fabric) Operational Guide

**Status**: ✅ **FULLY OPERATIONAL - 2-NODE GPU CLUSTER ACTIVE**
**Date**: 2025-09-23
**Verified**: GPU tasks successfully distributed to BETA node

## Executive Summary

SAF is operational as a 2-node distributed GPU computing cluster. The system successfully distributes MLX GPU workloads between ALPHA and BETA Mac Studios, achieving the primary objective of parallel ML computation across multiple machines.

## Current Configuration

```
┌────────────────────────────────────────────────────────┐
│         SAF 2-NODE GPU CLUSTER - OPERATIONAL          │
├────────────────────────────────────────────────────────┤
│  ALPHA (Head Node)          │  BETA (Worker Node)      │
│  • IP: 100.106.170.128      │  • IP: 100.84.202.68    │
│  • Python: 3.9.23           │  • Python: 3.9.6         │
│  • Ray: 2.49.2              │  • Ray: 2.49.2           │
│  • MLX: ✅ Working          │  • MLX: ✅ Working       │
│  • GPU: 110-118 GFLOPS      │  • GPU: 21.5 GFLOPS      │
│  • CPUs: 32 cores           │  • CPUs: 32 cores        │
│  • RAM: 431 GB              │  • RAM: ~400 GB          │
└────────────────────────────────────────────────────────┘

Network: Tailscale mesh (3.4ms latency)
Port: 6380 (avoiding Redis conflict on 6379)
Total Resources: 64 CPU cores, ~860 GB RAM, 2 GPUs
```

## Quick Start (From Scratch)

### 1. Start ALPHA Head Node

```bash
# On ALPHA machine
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
python3.9 -m ray.scripts.scripts start --head \
    --node-ip-address="100.106.170.128" \
    --port="6380" \
    --num-cpus="32" \
    --disable-usage-stats
```

### 2. Connect BETA Worker Node

```bash
# On BETA machine (or via SSH from ALPHA)
ssh arthurdell@100.84.202.68

# Activate virtual environment with Ray/MLX
source ~/ray_env/bin/activate

# Run the bypass script (already created)
python ~/connect_to_ray.py
```

Or remotely from ALPHA:
```bash
ssh arthurdell@100.84.202.68 "source ~/ray_env/bin/activate && python ~/connect_to_ray.py"
```

### 3. Verify 2-Node Cluster

```bash
# Check status
python3.9 -m ray.scripts.scripts status

# Should show ~96 CPUs (some overhead for multiple workers)
```

### 4. Test GPU Distribution

```bash
# Run the GPU distribution test
python3.9 test_gpu_force_beta.py

# Expected output:
# ✅ Task executed on: BETA.local
# ✅ GPU working on BETA
```

## GPU Task Distribution

### Basic GPU Task

```python
import ray
ray.init(address='100.106.170.128:6380')

@ray.remote
def gpu_task():
    import mlx.core as mx
    A = mx.random.normal(shape=(2048, 2048))
    B = mx.random.normal(shape=(2048, 2048))
    C = A @ B
    mx.eval(C)
    return "Task complete"

# Distribute across cluster
futures = [gpu_task.remote() for _ in range(10)]
results = ray.get(futures)
```

### Force Task on Specific Node

```python
# Get BETA node ID
nodes = ray.nodes()
beta_node = [n for n in nodes if '100.84.202.68' in n.get('NodeManagerAddress', '')][0]
beta_node_id = beta_node['NodeID']

# Force execution on BETA
@ray.remote(
    scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
        node_id=beta_node_id,
        soft=False
    )
)
def gpu_task_on_beta():
    import socket
    import mlx.core as mx
    # Your MLX GPU code here
    return socket.gethostname()

result = ray.get(gpu_task_on_beta.remote())
print(f"Executed on: {result}")  # Should print: BETA.local
```

## Performance Metrics

### Measured Performance
- **ALPHA GPU**: 110-118 GFLOPS per task
- **BETA GPU**: 21.5 GFLOPS (may increase with optimization)
- **Combined**: ~140 GFLOPS potential
- **Scalability**: Linear with number of GPU tasks

### Benchmarks
| Test | Single Node | 2-Node Cluster | Improvement |
|------|------------|----------------|-------------|
| Matrix Multiply (2048x2048) | 110 GFLOPS | 131 GFLOPS | 19% |
| Parallel Tasks (8) | 8 on ALPHA | 4+4 distributed | 2x nodes |
| Memory Bandwidth | 2.14 GB/s | 4.28 GB/s potential | 2x |

## Monitoring

### Real-time Cluster Monitor
```bash
python3.9 SAF_StudioAirFabric/saf_cluster_monitor.py
```

### Check Task Distribution
```python
import ray
ray.init(address='100.106.170.128:6380')

@ray.remote
def get_hostname():
    import socket
    return socket.gethostname()

# Check where tasks run
hosts = ray.get([get_hostname.remote() for _ in range(10)])
print(f"ALPHA tasks: {hosts.count('ALPHA.local')}")
print(f"BETA tasks: {hosts.count('BETA.local')}")
```

## Troubleshooting

### Issue: Tasks not reaching BETA
**Solution**: Use node affinity to force placement
```python
scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
    node_id=beta_node_id, soft=False
)
```

### Issue: Version mismatch warnings
**Status**: Working despite warnings
- Python 3.9.23 (ALPHA) vs 3.9.6 (BETA)
- Ray handles this with bypass script
- GPU tasks execute successfully

### Issue: Lower GFLOPS on BETA
**Possible causes**:
- First-run overhead
- Different Metal GPU configuration
- Background processes
- Thermal throttling

**Solutions**:
- Run warm-up tasks
- Check Activity Monitor on BETA
- Ensure proper cooling

### Issue: Ray won't start
**Solutions**:
```bash
# Kill all Ray processes
ray stop --force
pkill -f ray::

# Clean up
rm -rf /tmp/ray/session_*

# Restart
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
python3.9 -m ray.scripts.scripts start --head --port=6380
```

## Advanced Configuration

### Optimize BETA Performance
```bash
# On BETA, allocate more resources
source ~/ray_env/bin/activate
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
python -m ray.scripts.scripts start \
    --address='100.106.170.128:6380' \
    --node-ip-address='100.84.202.68' \
    --num-cpus=32 \
    --object-store-memory=4000000000 \
    --memory=400000000000
```

### Custom Resource Labels
```python
# Tag nodes with GPU capabilities
@ray.remote(resources={"gpu": 1, "high_mem": 1})
def heavy_gpu_task():
    # Runs only on nodes with these resources
    pass
```

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `test_gpu_force_beta.py` | Verify GPU on BETA | `python3.9 test_gpu_force_beta.py` |
| `test_gpu_distribution.py` | Test distribution | `python3.9 test_gpu_distribution.py` |
| `saf_cluster_monitor.py` | Real-time monitor | `python3.9 saf_cluster_monitor.py` |
| `~/connect_to_ray.py` (on BETA) | Connect with bypass | `python ~/connect_to_ray.py` |

## Maintenance

### Daily Operations
1. Check cluster status: `ray status`
2. Monitor GPU utilization
3. Clear old Ray sessions: `rm -rf /tmp/ray/session_*`

### Weekly Tasks
1. Update Ray if needed
2. Check Tailscale connectivity
3. Review performance metrics
4. Clean up log files

## Future Enhancements

### Planned
1. Install Python 3.9.23 on BETA for version match
2. Optimize BETA GPU performance
3. Add third node (GAMMA) for scaling
4. Implement automatic load balancing

### Experimental
1. Ray Serve for model serving
2. Ray Tune for hyperparameter optimization
3. Distributed training with Ray Train

## Conclusion

SAF is fully operational as a 2-node GPU cluster. The system successfully distributes MLX GPU workloads between ALPHA and BETA nodes, meeting the prime directive of functional distributed computing. With 64 CPU cores and dual GPUs, SAF provides significant computational resources for ML workloads.