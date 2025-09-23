#!/usr/bin/env python3.9
"""
CRITICAL TEST: GPU Distribution to BETA
This test MUST pass for SAF to be considered functional
"""

import ray
import time
import sys

def test_gpu_distribution():
    """Test distributing MLX GPU tasks to BETA node"""
    print("=" * 60)
    print("   CRITICAL: GPU DISTRIBUTION TEST")
    print("   Testing MLX GPU workloads on BETA")
    print("=" * 60)

    # Connect to cluster
    ray.init(address='100.106.170.128:6380', ignore_reinit_error=True)

    # Get cluster info
    nodes = ray.nodes()
    print(f"\n📊 Cluster nodes detected: {len(nodes)}")

    # Define GPU task
    @ray.remote
    def gpu_task(task_id):
        """Run MLX GPU computation and report which node executed it"""
        import socket
        import platform

        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)

        # Try to run MLX GPU computation
        try:
            import mlx.core as mx

            # Create GPU computation
            size = 2048
            A = mx.random.normal(shape=(size, size))
            B = mx.random.normal(shape=(size, size))

            start = time.time()
            C = A @ B  # Matrix multiplication on GPU
            mx.eval(C)  # Force GPU evaluation
            elapsed = time.time() - start

            # Calculate performance
            flops = 2 * size**3
            gflops = (flops / elapsed) / 1e9

            return {
                'task_id': task_id,
                'hostname': hostname,
                'ip': ip,
                'mlx_available': True,
                'gpu_task_completed': True,
                'gflops': gflops,
                'time': elapsed,
                'node_type': 'ALPHA' if 'ALPHA' in hostname else 'BETA'
            }
        except Exception as e:
            return {
                'task_id': task_id,
                'hostname': hostname,
                'ip': ip,
                'mlx_available': False,
                'gpu_task_completed': False,
                'error': str(e),
                'node_type': 'ALPHA' if 'ALPHA' in hostname else 'BETA'
            }

    # Launch GPU tasks
    print("\n🚀 Launching 8 GPU tasks across cluster...")
    futures = [gpu_task.remote(i) for i in range(8)]
    results = ray.get(futures)

    # Analyze results
    alpha_tasks = [r for r in results if 'ALPHA' in r['hostname']]
    beta_tasks = [r for r in results if 'BETA' in r['hostname']]

    print(f"\n📍 Task Distribution:")
    print(f"   ALPHA executed: {len(alpha_tasks)} tasks")
    print(f"   BETA executed: {len(beta_tasks)} tasks")

    # Check GPU availability
    alpha_gpu = any(r['gpu_task_completed'] for r in alpha_tasks) if alpha_tasks else False
    beta_gpu = any(r['gpu_task_completed'] for r in beta_tasks) if beta_tasks else False

    print(f"\n🖥️ GPU Status:")
    print(f"   ALPHA GPU (MLX): {'✅ Working' if alpha_gpu else '❌ Not Working'}")
    print(f"   BETA GPU (MLX): {'✅ Working' if beta_gpu else '❌ Not Working'}")

    # Performance summary
    if any(r['gpu_task_completed'] for r in results):
        total_gflops = sum(r.get('gflops', 0) for r in results if r['gpu_task_completed'])
        print(f"\n⚡ Performance:")
        print(f"   Total GFLOPS: {total_gflops:.1f}")

    # Detailed results
    print(f"\n📋 Detailed Results:")
    for r in results:
        status = "✅ GPU" if r['gpu_task_completed'] else "❌ No GPU"
        gflops = f"{r.get('gflops', 0):.1f} GFLOPS" if r.get('gflops') else "N/A"
        print(f"   Task {r['task_id']}: {r['hostname']} - {status} - {gflops}")

    # CRITICAL VERDICT
    print("\n" + "=" * 60)
    print("   VERDICT")
    print("=" * 60)

    if beta_tasks and beta_gpu:
        print("✅ SUCCESS: GPU tasks distributed to BETA!")
        print("✅ SAF IS FULLY FUNCTIONAL!")
        print(f"   - BETA executed {len(beta_tasks)} GPU tasks")
        print(f"   - Performance: {sum(r.get('gflops', 0) for r in beta_tasks if r['gpu_task_completed']):.1f} GFLOPS on BETA")
        success = True
    elif beta_tasks:
        print("⚠️  PARTIAL: Tasks reached BETA but GPU not working")
        print(f"   - BETA executed {len(beta_tasks)} tasks")
        print("   - MLX GPU not functional on BETA")
        success = False
    else:
        print("❌ FAILURE: No tasks distributed to BETA")
        print("   - All tasks ran on ALPHA only")
        print("   - 2-node cluster not functional")
        success = False

    ray.shutdown()
    return success

if __name__ == "__main__":
    success = test_gpu_distribution()
    sys.exit(0 if success else 1)