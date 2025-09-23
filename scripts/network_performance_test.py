#!/usr/bin/env python3
"""Network Performance Test between Alpha and Beta Systems"""

import subprocess
import json
import time
import statistics
from datetime import datetime
import sys

def run_command(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip() if result.returncode == 0 else None
    except subprocess.TimeoutExpired:
        return None

def test_latency(host, count=10):
    """Test network latency using ping"""
    print(f"\n📊 Testing latency to {host}...")

    cmd = f"ping -c {count} -q {host}"
    output = run_command(cmd)

    if output:
        # Parse ping statistics
        lines = output.split('\n')
        for line in lines:
            if 'min/avg/max/stddev' in line:
                stats = line.split('=')[1].strip().split('/')
                return {
                    'min_ms': float(stats[0]),
                    'avg_ms': float(stats[1]),
                    'max_ms': float(stats[2]),
                    'stddev_ms': float(stats[3].split()[0])
                }
    return None

def test_throughput_iperf(host):
    """Test network throughput using nc (netcat) since iperf may not be installed"""
    print(f"\n📊 Testing throughput to {host}...")

    # First check if we can reach the host
    test_cmd = f"ssh {host} 'echo connected' 2>/dev/null"
    if not run_command(test_cmd):
        return None

    # Create test file (10MB)
    test_file = "/tmp/network_test_10mb.bin"
    run_command(f"dd if=/dev/urandom of={test_file} bs=1048576 count=10 2>/dev/null")

    # Test upload speed
    start_time = time.time()
    upload_cmd = f"cat {test_file} | ssh {host} 'cat > /tmp/test_recv.bin'"
    run_command(upload_cmd)
    upload_time = time.time() - start_time
    upload_mbps = (10 * 8) / upload_time if upload_time > 0 else 0

    # Test download speed
    start_time = time.time()
    download_cmd = f"ssh {host} 'cat /tmp/test_recv.bin' > /tmp/test_download.bin"
    run_command(download_cmd)
    download_time = time.time() - start_time
    download_mbps = (10 * 8) / download_time if download_time > 0 else 0

    # Cleanup
    run_command(f"rm {test_file} /tmp/test_download.bin 2>/dev/null")
    run_command(f"ssh {host} 'rm /tmp/test_recv.bin' 2>/dev/null")

    return {
        'upload_mbps': round(upload_mbps, 2),
        'download_mbps': round(download_mbps, 2),
        'upload_time_s': round(upload_time, 3),
        'download_time_s': round(download_time, 3)
    }

def test_mtu(host):
    """Test Maximum Transmission Unit"""
    print(f"\n📊 Testing MTU to {host}...")

    # Test different packet sizes
    sizes = [1400, 1450, 1472, 1500, 1600, 4000, 8000]
    max_working = 0

    for size in sizes:
        cmd = f"ping -c 1 -D -s {size} {host} 2>/dev/null"
        if run_command(cmd):
            max_working = size
        else:
            break

    # Add overhead (28 bytes for IP + ICMP headers)
    return max_working + 28 if max_working > 0 else None

def test_docker_network():
    """Test Docker network performance between services"""
    print("\n📊 Testing Docker network performance...")

    results = {}

    # Test API Gateway health endpoint
    start = time.time()
    api_health = run_command("curl -s http://localhost:8080/health")
    api_time = (time.time() - start) * 1000

    if api_health:
        results['api_gateway_health_ms'] = round(api_time, 2)

    # Test inter-service communication
    services = [
        ('postgres', '5432'),
        ('kb-service', '8000'),
        ('mlx-server', '8001'),
        ('techknowledge', '8002'),
        ('redis', '6379')
    ]

    for service, port in services:
        start = time.time()
        cmd = f"nc -zv localhost {port} 2>&1"
        if run_command(cmd):
            results[f"{service}_connect_ms"] = round((time.time() - start) * 1000, 2)

    return results

def test_tailscale_specific():
    """Test Tailscale-specific metrics"""
    print("\n📊 Testing Tailscale metrics...")

    # Get Tailscale status
    status = run_command("tailscale status --json")
    if not status:
        return None

    try:
        data = json.loads(status)
        peer_status = data.get('Peer', {})

        # Find beta node
        beta_info = None
        for peer_id, peer in peer_status.items():
            if peer.get('HostName') == 'beta':
                beta_info = peer
                break

        if beta_info:
            return {
                'relay_latency_ms': beta_info.get('CurAddr', {}).get('Latency', 0) * 1000,
                'rx_bytes': beta_info.get('RxBytes', 0),
                'tx_bytes': beta_info.get('TxBytes', 0),
                'last_seen': beta_info.get('LastSeen', ''),
                'online': beta_info.get('Online', False)
            }
    except:
        pass

    return None

def generate_report(results):
    """Generate performance report"""
    print("\n" + "="*60)
    print("🎯 NETWORK PERFORMANCE REPORT")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # System Info
    print("\n📦 SYSTEM CONFIGURATION:")
    print("  Alpha: Mac Studio M3 Ultra (512GB RAM, 80-core GPU)")
    print("  Beta:  Mac Studio M3 Ultra (256GB RAM, 80-core GPU)")
    print("  Network: Tailscale Mesh VPN")

    # Latency Results
    if results.get('tailscale_latency'):
        print("\n⏱️ TAILSCALE LATENCY (100.84.202.68):")
        lat = results['tailscale_latency']
        print(f"  Min:    {lat['min_ms']:.2f} ms")
        print(f"  Avg:    {lat['avg_ms']:.2f} ms")
        print(f"  Max:    {lat['max_ms']:.2f} ms")
        print(f"  StdDev: {lat['stddev_ms']:.2f} ms")

    if results.get('local_latency'):
        print("\n⏱️ LOCAL NETWORK LATENCY (beta.local):")
        lat = results['local_latency']
        print(f"  Min:    {lat['min_ms']:.2f} ms")
        print(f"  Avg:    {lat['avg_ms']:.2f} ms")
        print(f"  Max:    {lat['max_ms']:.2f} ms")
        print(f"  StdDev: {lat['stddev_ms']:.2f} ms")

    # Throughput Results
    if results.get('throughput'):
        print("\n📈 NETWORK THROUGHPUT:")
        tp = results['throughput']
        print(f"  Upload:   {tp['upload_mbps']:.2f} Mbps")
        print(f"  Download: {tp['download_mbps']:.2f} Mbps")

    # MTU Results
    if results.get('mtu'):
        print(f"\n📏 MAXIMUM TRANSMISSION UNIT:")
        print(f"  MTU: {results['mtu']} bytes")

    # Docker Network
    if results.get('docker'):
        print("\n🐳 DOCKER NETWORK PERFORMANCE:")
        docker = results['docker']
        for key, value in docker.items():
            service = key.replace('_', ' ').title()
            print(f"  {service}: {value} ms")

    # Tailscale Metrics
    if results.get('tailscale_metrics'):
        print("\n🔐 TAILSCALE METRICS:")
        ts = results['tailscale_metrics']
        if ts.get('online'):
            print(f"  Status: ✅ Online")
        else:
            print(f"  Status: ❌ Offline")
        if ts.get('rx_bytes'):
            print(f"  RX: {ts['rx_bytes'] / 1024 / 1024:.2f} MB")
        if ts.get('tx_bytes'):
            print(f"  TX: {ts['tx_bytes'] / 1024 / 1024:.2f} MB")

    # Performance Analysis
    print("\n📊 PERFORMANCE ANALYSIS:")

    if results.get('tailscale_latency') and results.get('local_latency'):
        ts_avg = results['tailscale_latency']['avg_ms']
        local_avg = results['local_latency']['avg_ms']
        overhead = ((ts_avg - local_avg) / local_avg) * 100 if local_avg > 0 else 0

        print(f"  Tailscale Overhead: {overhead:.1f}%")

        if ts_avg < 1:
            print("  Rating: ⭐⭐⭐⭐⭐ Excellent (<1ms)")
        elif ts_avg < 5:
            print("  Rating: ⭐⭐⭐⭐ Very Good (<5ms)")
        elif ts_avg < 10:
            print("  Rating: ⭐⭐⭐ Good (<10ms)")
        elif ts_avg < 20:
            print("  Rating: ⭐⭐ Fair (<20ms)")
        else:
            print("  Rating: ⭐ Needs Optimization (>20ms)")

    if results.get('throughput'):
        tp = results['throughput']
        avg_speed = (tp['upload_mbps'] + tp['download_mbps']) / 2

        if avg_speed > 1000:
            print(f"  Throughput: ⭐⭐⭐⭐⭐ Gigabit+ ({avg_speed:.0f} Mbps)")
        elif avg_speed > 500:
            print(f"  Throughput: ⭐⭐⭐⭐ Excellent ({avg_speed:.0f} Mbps)")
        elif avg_speed > 100:
            print(f"  Throughput: ⭐⭐⭐ Good ({avg_speed:.0f} Mbps)")
        elif avg_speed > 50:
            print(f"  Throughput: ⭐⭐ Fair ({avg_speed:.0f} Mbps)")
        else:
            print(f"  Throughput: ⭐ Poor ({avg_speed:.0f} Mbps)")

    print("\n" + "="*60)

    # Save results to JSON
    report_file = f"/Volumes/DATA/FREEDOM/documents/reports/NETWORK_PERFORMANCE_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n📝 Full report saved to: {report_file}")

def main():
    """Main test execution"""
    print("🚀 Starting Network Performance Tests...")
    print("   Testing connections between Alpha and Beta systems")

    results = {}

    # Test Tailscale connection
    results['tailscale_latency'] = test_latency('100.84.202.68')

    # Test local network (if available)
    results['local_latency'] = test_latency('beta.local')

    # Test throughput via SSH
    results['throughput'] = test_throughput_iperf('beta-ts')

    # Test MTU
    results['mtu'] = test_mtu('100.84.202.68')

    # Test Docker network
    results['docker'] = test_docker_network()

    # Get Tailscale metrics
    results['tailscale_metrics'] = test_tailscale_specific()

    # Generate report
    generate_report(results)

    return 0

if __name__ == "__main__":
    sys.exit(main())