#!/usr/bin/env python3
"""
SAF 2-Node Cluster Test Suite
Tests distributed computing across ALPHA and BETA nodes
"""

import ray
import time
import numpy as np
import psutil
from datetime import datetime

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_cluster_connectivity():
    """Test basic cluster connectivity and resource discovery"""
    print_header("1. CLUSTER CONNECTIVITY TEST")

    try:
        # Connect to existing cluster
        ray.init(address='100.106.170.128:6380', ignore_reinit_error=True)

        # Get cluster info
        nodes = ray.nodes()
        resources = ray.cluster_resources()

        print(f"✅ Connected to Ray cluster")
        print(f"\n📊 Cluster Overview:")
        print(f"   Total Nodes: {len(nodes)}")
        print(f"   Total CPUs: {int(resources.get('CPU', 0))}")
        print(f"   Total Memory: {resources.get('memory', 0) / (1024**3):.1f} GB")
        print(f"   Object Store: {resources.get('object_store_memory', 0) / (1024**3):.1f} GB")

        # Node details
        print(f"\n📍 Node Details:")
        for i, node in enumerate(nodes):
            if node['Alive']:
                node_ip = node['NodeManagerAddress']
                node_resources = node['Resources']
                node_name = "ALPHA (Head)" if i == 0 else f"BETA (Worker {i})"

                print(f"\n   {node_name}:")
                print(f"   • IP: {node_ip}")
                print(f"   • CPUs: {int(node_resources.get('CPU', 0))}")
                print(f"   • Memory: {node_resources.get('memory', 0) / (1024**3):.1f} GB")
                print(f"   • Status: {'✅ Active' if node['Alive'] else '❌ Inactive'}")

        return len(nodes)

    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return 0

def test_distributed_compute():
    """Test distributed computation across nodes"""
    print_header("2. DISTRIBUTED COMPUTATION TEST")

    @ray.remote
    def compute_pi(num_samples):
        """Monte Carlo Pi estimation"""
        import random
        import socket
        import os

        # Get node info
        hostname = socket.gethostname()
        pid = os.getpid()

        # Monte Carlo simulation
        count = 0
        for _ in range(num_samples):
            x = random.random()
            y = random.random()
            if x*x + y*y <= 1:
                count += 1

        pi_estimate = 4.0 * count / num_samples
        return pi_estimate, hostname, pid

    try:
        # Run tasks across multiple workers
        num_tasks = 8
        samples_per_task = 1000000

        print(f"🔄 Distributing {num_tasks} tasks across cluster...")
        print(f"   Samples per task: {samples_per_task:,}")

        start = time.time()
        futures = [compute_pi.remote(samples_per_task) for _ in range(num_tasks)]
        results = ray.get(futures)
        elapsed = time.time() - start

        # Analyze results
        pi_estimates = [r[0] for r in results]
        hostnames = set(r[1] for r in results)
        pids = set(r[2] for r in results)

        avg_pi = sum(pi_estimates) / len(pi_estimates)

        print(f"\n✅ Computation completed in {elapsed:.2f}s")
        print(f"   π estimate: {avg_pi:.6f} (actual: 3.141593)")
        print(f"   Error: {abs(avg_pi - 3.141593):.6f}")
        print(f"   Unique hosts: {len(hostnames)} - {hostnames}")
        print(f"   Worker processes: {len(pids)}")
        print(f"   Throughput: {(num_tasks * samples_per_task / elapsed) / 1e6:.1f}M samples/sec")

        return True

    except Exception as e:
        print(f"❌ Distributed compute failed: {e}")
        return False

def test_mlx_distributed():
    """Test MLX operations distributed across nodes"""
    print_header("3. MLX DISTRIBUTED GPU TEST")

    @ray.remote
    def mlx_matrix_ops(size=2048):
        """MLX matrix operations on Metal GPU"""
        try:
            import mlx.core as mx
            import socket
            import time

            hostname = socket.gethostname()

            # Matrix multiplication
            A = mx.random.normal(shape=(size, size))
            B = mx.random.normal(shape=(size, size))

            start = time.time()
            C = A @ B
            mx.eval(C)  # Force evaluation
            elapsed = time.time() - start

            # Calculate performance
            flops = 2 * size**3
            gflops = (flops / elapsed) / 1e9

            return {
                'hostname': hostname,
                'size': size,
                'time': elapsed,
                'gflops': gflops
            }
        except ImportError:
            return {
                'hostname': socket.gethostname(),
                'error': 'MLX not available'
            }

    try:
        # Run MLX tasks on multiple nodes
        tasks = 4
        matrix_size = 2048

        print(f"🔄 Running {tasks} MLX tasks (matrix size: {matrix_size}x{matrix_size})...")

        futures = [mlx_matrix_ops.remote(matrix_size) for _ in range(tasks)]
        results = ray.get(futures)

        # Analyze results
        successful = [r for r in results if 'gflops' in r]
        failed = [r for r in results if 'error' in r]

        if successful:
            total_gflops = sum(r['gflops'] for r in successful)
            avg_time = sum(r['time'] for r in successful) / len(successful)
            hosts = set(r['hostname'] for r in successful)

            print(f"\n✅ MLX operations completed")
            print(f"   Successful tasks: {len(successful)}/{tasks}")
            print(f"   Average time: {avg_time:.3f}s")
            print(f"   Total GFLOPS: {total_gflops:.1f}")
            print(f"   Hosts used: {hosts}")

        if failed:
            print(f"\n⚠️  {len(failed)} tasks failed (MLX not available on some nodes)")

        return len(successful) > 0

    except Exception as e:
        print(f"❌ MLX distributed test failed: {e}")
        return False

def test_large_memory_workload():
    """Test large memory allocations across nodes"""
    print_header("4. DISTRIBUTED MEMORY TEST")

    @ray.remote
    def allocate_and_process(gb_size):
        """Allocate and process large memory blocks"""
        import socket
        import numpy as np
        import time

        hostname = socket.gethostname()

        # Allocate memory
        size = int(gb_size * 1024 * 1024 * 1024 / 8)  # 8 bytes per float64

        start = time.time()
        data = np.random.random(size)
        result = np.sum(data)
        elapsed = time.time() - start

        return {
            'hostname': hostname,
            'gb_allocated': gb_size,
            'sum': result,
            'time': elapsed
        }

    try:
        # Test different memory sizes across nodes
        memory_sizes = [1, 2, 4]  # GB

        print(f"🔄 Testing memory allocation across nodes...")

        for gb in memory_sizes:
            futures = [allocate_and_process.remote(gb) for _ in range(2)]
            results = ray.get(futures)

            hosts = set(r['hostname'] for r in results)
            total_time = sum(r['time'] for r in results)

            print(f"\n   {gb} GB allocation:")
            print(f"   • Nodes used: {hosts}")
            print(f"   • Total time: {total_time:.2f}s")
            print(f"   • Throughput: {(2 * gb) / total_time:.2f} GB/s")

        print(f"\n✅ Memory test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Memory test failed: {e}")
        return False

def test_cross_node_communication():
    """Test data transfer between nodes"""
    print_header("5. CROSS-NODE COMMUNICATION TEST")

    @ray.remote
    def producer(size_mb):
        """Produce data on one node"""
        import socket
        import numpy as np

        hostname = socket.gethostname()
        data = np.random.random(int(size_mb * 1024 * 1024 / 8))

        return {
            'data': data,
            'producer_host': hostname,
            'size_mb': size_mb
        }

    @ray.remote
    def consumer(data_ref):
        """Consume data on another node"""
        import socket
        import numpy as np
        import time

        hostname = socket.gethostname()

        start = time.time()
        data = ray.get(data_ref)
        result = np.mean(data['data'])
        elapsed = time.time() - start

        return {
            'consumer_host': hostname,
            'producer_host': data['producer_host'],
            'result': result,
            'transfer_time': elapsed,
            'size_mb': data['size_mb']
        }

    try:
        sizes = [10, 50, 100]  # MB

        print(f"🔄 Testing cross-node data transfer...")

        for size_mb in sizes:
            # Create data on one node
            data_ref = producer.remote(size_mb)

            # Consume on multiple nodes
            futures = [consumer.remote(data_ref) for _ in range(2)]
            results = ray.get(futures)

            # Analyze transfer
            for r in results:
                if r['producer_host'] != r['consumer_host']:
                    bandwidth = size_mb / r['transfer_time']
                    print(f"\n   {size_mb} MB transfer:")
                    print(f"   • {r['producer_host']} → {r['consumer_host']}")
                    print(f"   • Time: {r['transfer_time']:.3f}s")
                    print(f"   • Bandwidth: {bandwidth:.1f} MB/s")

        print(f"\n✅ Cross-node communication test completed")
        return True

    except Exception as e:
        print(f"❌ Communication test failed: {e}")
        return False

def main():
    """Run all 2-node cluster tests"""
    print("\n" + "=" * 60)
    print("   SAF 2-NODE CLUSTER TEST SUITE")
    print("   Testing ALPHA + BETA Configuration")
    print("=" * 60)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Track test results
    tests = []

    # Run tests
    num_nodes = test_cluster_connectivity()
    tests.append(("Connectivity", num_nodes > 0))

    if num_nodes > 0:
        tests.append(("Distributed Compute", test_distributed_compute()))
        tests.append(("MLX GPU", test_mlx_distributed()))
        tests.append(("Memory Management", test_large_memory_workload()))

        if num_nodes > 1:
            tests.append(("Cross-Node Communication", test_cross_node_communication()))
        else:
            print("\n⚠️  Skipping cross-node tests (only 1 node detected)")

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, r in tests if r)
    total = len(tests)

    for name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")

    print(f"\n  Overall: {passed}/{total} tests passed")

    if num_nodes == 2 and passed == total:
        print("\n🎉 2-NODE CLUSTER FULLY OPERATIONAL!")
        print("   ALPHA + BETA working together successfully")
        print("   Ready for distributed ML workloads")
    elif num_nodes == 1:
        print("\n⚠️  SINGLE NODE MODE")
        print("   Only ALPHA node detected")
        print("   Run saf_start_beta.sh on BETA machine to enable 2-node cluster")
    else:
        print("\n❌ CLUSTER NOT FULLY OPERATIONAL")

    # Cleanup
    try:
        ray.shutdown()
    except:
        pass

    return passed == total

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)