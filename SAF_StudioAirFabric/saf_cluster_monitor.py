#!/usr/bin/env python3
"""
SAF Cluster Real-time Monitor
Monitors the health and performance of the 2-node Ray cluster
"""

import ray
import time
import psutil
from datetime import datetime
import os
import sys

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_color(value, thresholds):
    """Return color based on value and thresholds"""
    if value < thresholds[0]:
        return '\033[0;32m'  # Green
    elif value < thresholds[1]:
        return '\033[1;33m'  # Yellow
    else:
        return '\033[0;31m'  # Red

def format_bytes(bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes) < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"

def monitor_cluster():
    """Main monitoring function"""
    try:
        # Connect to cluster
        ray.init(address='100.106.170.128:6380', ignore_reinit_error=True)
    except Exception as e:
        print(f"❌ Failed to connect to Ray cluster: {e}")
        print("\nMake sure Ray head is running:")
        print("  ./SAF_StudioAirFabric/saf_start_alpha.sh")
        return

    print("Connected to Ray cluster. Starting monitor...")
    print("Press Ctrl+C to exit\n")

    try:
        while True:
            clear_screen()

            # Header
            print("=" * 70)
            print("   SAF CLUSTER MONITOR - Real-time Status")
            print("=" * 70)
            print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)

            # Get cluster info
            nodes = ray.nodes()
            resources = ray.cluster_resources()
            available = ray.available_resources()

            # Overall cluster status
            num_nodes = len([n for n in nodes if n['Alive']])
            total_cpus = int(resources.get('CPU', 0))
            used_cpus = total_cpus - int(available.get('CPU', 0))
            cpu_usage = (used_cpus / total_cpus * 100) if total_cpus > 0 else 0

            total_mem = resources.get('memory', 0) / (1024**3)
            used_mem = (resources.get('memory', 0) - available.get('memory', 0)) / (1024**3)
            mem_usage = (used_mem / total_mem * 100) if total_mem > 0 else 0

            # Color coding
            cpu_color = get_color(cpu_usage, [50, 80])
            mem_color = get_color(mem_usage, [60, 85])
            NC = '\033[0m'

            print("\n📊 CLUSTER OVERVIEW")
            print("-" * 70)
            print(f"  Nodes:     {num_nodes} {'✅' if num_nodes == 2 else '⚠️ (expecting 2)'}")
            print(f"  CPUs:      {cpu_color}{used_cpus}/{total_cpus} cores ({cpu_usage:.1f}% used){NC}")
            print(f"  Memory:    {mem_color}{used_mem:.1f}/{total_mem:.1f} GB ({mem_usage:.1f}% used){NC}")
            print(f"  Object Store: {available.get('object_store_memory', 0) / (1024**3):.1f} GB available")

            # Per-node details
            print("\n📍 NODE STATUS")
            print("-" * 70)

            node_names = {
                0: "ALPHA (Head)",
                1: "BETA (Worker)"
            }

            for i, node in enumerate(nodes):
                if node['Alive']:
                    node_ip = node['NodeManagerAddress']
                    node_res = node['Resources']
                    node_name = node_names.get(i, f"Node {i}")

                    node_cpus = int(node_res.get('CPU', 0))
                    node_mem = node_res.get('memory', 0) / (1024**3)

                    # Try to get usage (this is approximate)
                    status = "✅ Active"

                    print(f"\n  {node_name} ({node_ip}):")
                    print(f"    Status: {status}")
                    print(f"    CPUs:   {node_cpus} cores")
                    print(f"    Memory: {node_mem:.1f} GB")

                    # Object store info if available
                    obj_store = node_res.get('object_store_memory', 0) / (1024**3)
                    if obj_store > 0:
                        print(f"    Object Store: {obj_store:.1f} GB")

            # Active tasks
            try:
                from ray import state
                tasks = state.tasks()
                if tasks:
                    running = [t for t in tasks if t.state == "RUNNING"]
                    pending = [t for t in tasks if t.state == "PENDING_NODE_ASSIGNMENT"]

                    print("\n🔄 ACTIVE TASKS")
                    print("-" * 70)
                    print(f"  Running: {len(running)}")
                    print(f"  Pending: {len(pending)}")
                    print(f"  Total:   {len(tasks)}")
            except:
                pass

            # Network stats (if available)
            print("\n🌐 NETWORK")
            print("-" * 70)

            # Test connectivity to beta
            import subprocess
            try:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", "100.84.202.68"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Parse ping time
                    for line in result.stdout.split('\n'):
                        if 'time=' in line:
                            ping_time = float(line.split('time=')[1].split()[0])
                            ping_color = get_color(ping_time, [5, 20])
                            print(f"  ALPHA → BETA: {ping_color}{ping_time:.1f} ms{NC}")
                            break
                else:
                    print("  ALPHA → BETA: ❌ Unreachable")
            except:
                pass

            # Tailscale status
            try:
                result = subprocess.run(
                    ["tailscale", "status"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'beta' in line.lower():
                            status = "✅ Connected" if 'idle' in line or 'active' in line else "❌ Offline"
                            print(f"  Tailscale:    {status}")
                            break
            except:
                pass

            # Performance metrics
            print("\n⚡ PERFORMANCE")
            print("-" * 70)

            # Local system metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            net = psutil.net_io_counters()

            cpu_color = get_color(cpu_percent, [60, 85])
            mem_color = get_color(memory.percent, [70, 90])

            print(f"  System CPU:    {cpu_color}{cpu_percent:.1f}%{NC}")
            print(f"  System Memory: {mem_color}{memory.percent:.1f}%{NC} ({memory.available / (1024**3):.1f} GB available)")
            print(f"  Network I/O:   ↑ {format_bytes(net.bytes_sent)} / ↓ {format_bytes(net.bytes_recv)}")

            # Footer with instructions
            print("\n" + "=" * 70)
            if num_nodes == 1:
                print("  ⚠️  Single node mode - Start BETA node to enable 2-node cluster")
                print("  Run on BETA: ./SAF_StudioAirFabric/saf_start_beta.sh")
            elif num_nodes == 2:
                print("  ✅ 2-node cluster operational - Ready for distributed workloads")
            else:
                print("  ❌ No nodes detected - Start Ray cluster first")

            print("=" * 70)
            print("  Press Ctrl+C to exit | Refreshing every 2 seconds...")

            # Refresh interval
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n✅ Monitor stopped")
        ray.shutdown()
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
        ray.shutdown()

if __name__ == "__main__":
    monitor_cluster()