#!/usr/bin/env python3.9
"""
FORCE GPU task execution on BETA node
"""

import ray
import time
import sys

def main():
    print("=" * 60)
    print("   FORCING GPU TASK ON BETA")
    print("=" * 60)

    ray.init(address='100.106.170.128:6380', ignore_reinit_error=True)

    # Get BETA node info
    nodes = ray.nodes()
    beta_nodes = [n for n in nodes if n['Alive'] and '100.84.202.68' in n.get('NodeManagerAddress', '')]

    if not beta_nodes:
        print("❌ BETA node not found in cluster")
        return False

    beta_node_id = beta_nodes[0]['NodeID']
    print(f"✅ Found BETA node: {beta_node_id[:8]}...")

    # Force task on BETA using node affinity
    @ray.remote(
        num_cpus=1,
        scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
            node_id=beta_node_id,
            soft=False
        )
    )
    def gpu_task_on_beta():
        import socket
        hostname = socket.gethostname()

        # Test MLX
        try:
            import mlx.core as mx

            # Small GPU test
            A = mx.random.normal(shape=(1024, 1024))
            B = mx.random.normal(shape=(1024, 1024))
            start = time.time()
            C = A @ B
            mx.eval(C)
            elapsed = time.time() - start

            return {
                'hostname': hostname,
                'mlx_working': True,
                'time': elapsed,
                'gflops': (2 * 1024**3 / elapsed) / 1e9
            }
        except Exception as e:
            return {
                'hostname': hostname,
                'mlx_working': False,
                'error': str(e)
            }

    print("\n🚀 Forcing GPU task on BETA node...")
    try:
        result = ray.get(gpu_task_on_beta.remote())

        print(f"\n📍 Task executed on: {result['hostname']}")

        if 'BETA' in result['hostname']:
            if result['mlx_working']:
                print(f"✅ SUCCESS! GPU working on BETA")
                print(f"   Performance: {result['gflops']:.1f} GFLOPS")
                return True
            else:
                print(f"❌ Task reached BETA but MLX failed")
                print(f"   Error: {result.get('error', 'Unknown')}")
                return False
        else:
            print(f"❌ Task did NOT run on BETA (ran on {result['hostname']})")
            return False

    except Exception as e:
        print(f"❌ Failed to execute task: {e}")
        return False
    finally:
        ray.shutdown()

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "=" * 60)
        print("🎉 SAF IS FUNCTIONAL - GPU TASKS CAN RUN ON BETA!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ SAF FAILED - Cannot distribute GPU to BETA")
        print("=" * 60)
    sys.exit(0 if success else 1)