# SAF Quick Reference Card

## 🚀 Start 2-Node GPU Cluster

### Step 1: Start ALPHA (This Machine)
```bash
export RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1
python3.9 -m ray.scripts.scripts start --head \
    --node-ip-address="100.106.170.128" \
    --port="6380" \
    --num-cpus="32" \
    --disable-usage-stats
```

### Step 2: Connect BETA (Remote)
```bash
ssh arthurdell@100.84.202.68 \
    "source ~/ray_env/bin/activate && python ~/connect_to_ray.py"
```

### Step 3: Verify Cluster
```bash
python3.9 -m ray.scripts.scripts status
# Should show ~96 CPUs (3 workers)
```

### Step 4: Test GPU Distribution
```bash
python3.9 test_gpu_force_beta.py
# Must show: "Task executed on: BETA.local"
```

## 📊 Monitor Operations

### Real-time Monitor
```bash
python3.9 SAF_StudioAirFabric/saf_cluster_monitor.py
```

### Check Node Distribution
```python
import ray
ray.init(address='100.106.170.128:6380')

@ray.remote
def where_am_i():
    import socket
    return socket.gethostname()

hosts = ray.get([where_am_i.remote() for _ in range(10)])
print(f"ALPHA: {hosts.count('ALPHA.local')}")
print(f"BETA: {hosts.count('BETA.local')}")
```

## 🛠️ Troubleshooting

### Stop Everything
```bash
# On ALPHA
python3.9 -m ray.scripts.scripts stop --force

# On BETA (via SSH)
ssh arthurdell@100.84.202.68 "ray stop --force"
```

### Clean Up
```bash
rm -rf /tmp/ray/session_*
pkill -f ray::
```

### Restart Fresh
```bash
# Just repeat Step 1 and 2 above
```

## 🎯 Force GPU Task on BETA

```python
import ray
ray.init(address='100.106.170.128:6380')

# Get BETA node ID
nodes = ray.nodes()
beta = [n for n in nodes if '100.84.202.68' in n.get('NodeManagerAddress', '')][0]
beta_id = beta['NodeID']

# Force task on BETA
@ray.remote(
    scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
        node_id=beta_id, soft=False
    )
)
def gpu_on_beta():
    import mlx.core as mx
    # Your GPU code
    return "Success on BETA"

result = ray.get(gpu_on_beta.remote())
```

## 📈 Performance Metrics

| Node | IP | CPUs | RAM | GPU GFLOPS |
|------|-----|------|-----|------------|
| ALPHA | 100.106.170.128 | 32 | 431 GB | 110-118 |
| BETA | 100.84.202.68 | 32 | ~400 GB | 21.5 |
| **Total** | **Cluster** | **64** | **~860 GB** | **140+** |

## ⚠️ Important Notes

1. **Python Versions**: 3.9.23 (ALPHA) vs 3.9.6 (BETA) - bypass script handles this
2. **Port**: Using 6380 (not 6379 which Redis uses)
3. **Environment Variable**: RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER=1 required
4. **Virtual Env on BETA**: Must activate ~/ray_env/bin/activate

## 🎉 Success Indicator

```
Task executed on: BETA.local
✅ SUCCESS! GPU working on BETA
   Performance: XX.X GFLOPS
```

If you see this, SAF is working!