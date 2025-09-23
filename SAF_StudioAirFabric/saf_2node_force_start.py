#!/usr/bin/env python3.9
"""
SAF 2-Node Cluster Force Start
Works around Python version mismatches between nodes
"""

import os
import sys
import subprocess
import time

def start_alpha():
    """Start Ray head node on ALPHA with Python 3.9"""
    print("🚀 Starting ALPHA node (head) with Python 3.9...")

    # Stop any existing Ray
    subprocess.run(["python3.9", "-m", "ray.scripts.scripts", "stop", "--force"],
                   capture_output=True)
    time.sleep(2)

    # Start Ray head
    env = os.environ.copy()
    env["RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER"] = "1"

    result = subprocess.run([
        "python3.9", "-m", "ray.scripts.scripts", "start", "--head",
        "--node-ip-address=100.106.170.128",
        "--port=6380",
        "--num-cpus=32",
        "--disable-usage-stats"
    ], env=env, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ ALPHA node started successfully")
        print(result.stdout)
        return True
    else:
        print("❌ Failed to start ALPHA:")
        print(result.stderr)
        return False

def connect_beta_workaround():
    """Connect BETA with version mismatch workaround"""
    print("\n🔗 Connecting BETA node (worker)...")

    # Create a Python script that bypasses version check
    bypass_script = """
import os
os.environ['RAY_ENABLE_WINDOWS_OR_OSX_CLUSTER'] = '1'

# Monkey-patch the version check
import ray._private.utils
original_check = ray._private.utils.check_version_info

def bypass_check(*args, **kwargs):
    print("⚠️  Bypassing version check for testing purposes")
    return

ray._private.utils.check_version_info = bypass_check

# Now start Ray normally
import sys
sys.argv = ['ray', 'start',
            '--address=100.106.170.128:6380',
            '--node-ip-address=100.84.202.68',
            '--num-cpus=32',
            '--disable-usage-stats']

from ray.scripts.scripts import main
main()
"""

    # Write bypass script to temp file on BETA
    print("📝 Creating bypass script on BETA...")

    cmd = f'echo "{bypass_script}" > /tmp/ray_bypass.py'
    result = subprocess.run(
        ["ssh", "arthurdell@100.84.202.68", cmd],
        capture_output=True, text=True
    )

    # Execute bypass script on BETA
    print("🔧 Starting Ray on BETA with version bypass...")
    result = subprocess.run(
        ["ssh", "arthurdell@100.84.202.68", "python3 /tmp/ray_bypass.py"],
        capture_output=True, text=True
    )

    if "Ray runtime started" in result.stdout or "successfully" in result.stdout.lower():
        print("✅ BETA node connected (with version bypass)")
        return True
    else:
        print("⚠️  BETA connection status uncertain")
        print("Output:", result.stdout[:500])
        return False

def verify_cluster():
    """Verify 2-node cluster is working"""
    print("\n🔍 Verifying cluster status...")

    import ray
    try:
        ray.init(address='100.106.170.128:6380', ignore_reinit_error=True)

        nodes = ray.nodes()
        alive = [n for n in nodes if n['Alive']]

        print(f"\n📊 Cluster Status:")
        print(f"  Nodes: {len(alive)}")

        if len(alive) == 2:
            print("  ✅ 2-NODE CLUSTER ACTIVE!")

            # Get node details
            for i, node in enumerate(alive):
                ip = node['NodeManagerAddress']
                cpus = node['Resources'].get('CPU', 0)
                mem = node['Resources'].get('memory', 0) / (1024**3)
                print(f"\n  Node {i+1} ({ip}):")
                print(f"    CPUs: {int(cpus)}")
                print(f"    Memory: {mem:.1f} GB")

            # Test distributed compute
            @ray.remote
            def get_hostname():
                import socket
                return socket.gethostname()

            hosts = ray.get([get_hostname.remote() for _ in range(4)])
            unique_hosts = set(hosts)
            print(f"\n  Test tasks ran on: {unique_hosts}")

            return True
        else:
            print(f"  ⚠️  Only {len(alive)} node(s) detected")
            return False

    except Exception as e:
        print(f"❌ Cluster verification failed: {e}")
        return False
    finally:
        ray.shutdown()

def main():
    print("=" * 60)
    print("   SAF 2-NODE CLUSTER FORCE START")
    print("   Working around Python version mismatches")
    print("=" * 60)
    print()

    # Start ALPHA
    if not start_alpha():
        print("\n❌ Failed to start ALPHA node")
        return 1

    time.sleep(3)

    # Connect BETA
    if not connect_beta_workaround():
        print("\n⚠️  BETA connection may have failed")
        print("Try running manually on BETA machine:")
        print("  python3 /tmp/ray_bypass.py")

    time.sleep(3)

    # Verify
    if verify_cluster():
        print("\n" + "=" * 60)
        print("🎉 2-NODE CLUSTER SUCCESSFULLY STARTED!")
        print("=" * 60)
        print("\nRun tests with:")
        print("  python3.9 SAF_StudioAirFabric/saf_2node_test.py")
        print("\nMonitor with:")
        print("  python3.9 SAF_StudioAirFabric/saf_cluster_monitor.py")
        return 0
    else:
        print("\n⚠️  Cluster not fully operational")
        print("Check both nodes and network connectivity")
        return 1

if __name__ == "__main__":
    sys.exit(main())