#!/usr/bin/env python3
"""
FREEDOM Platform Monitoring - Simple Terminal Version
Real-time monitoring without curses dependency
"""

import os
import sys
import time
import json
import subprocess
import sqlite3
from datetime import datetime
from collections import deque

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def clear_screen():
    """Clear the terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def get_docker_status():
    """Get Docker container status"""
    try:
        result = subprocess.run(['docker', 'ps', '--format',
                                'table {{.Names}}\t{{.Status}}\t{{.State}}'],
                               capture_output=True, text=True)
        return result.stdout.strip().split('\n')
    except:
        return ["Docker not available"]

def get_system_resources():
    """Get system resource usage"""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu': cpu,
            'memory': memory.percent,
            'memory_used': memory.used / (1024**3),  # GB
            'memory_total': memory.total / (1024**3),  # GB
            'disk': disk.percent,
            'disk_used': disk.used / (1024**3),  # GB
            'disk_total': disk.total / (1024**3)  # GB
        }
    except ImportError:
        return {
            'cpu': 'N/A',
            'memory': 'N/A',
            'memory_used': 0,
            'memory_total': 0,
            'disk': 'N/A',
            'disk_used': 0,
            'disk_total': 0
        }

def check_service_health():
    """Check health of key services"""
    services = []

    # Check PostgreSQL
    try:
        result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'],
                               capture_output=True, text=True, timeout=2)
        pg_status = "✓ ONLINE" if result.returncode == 0 else "✗ OFFLINE"
        pg_color = Colors.GREEN if result.returncode == 0 else Colors.FAIL
    except:
        pg_status = "✗ UNREACHABLE"
        pg_color = Colors.FAIL
    services.append(('PostgreSQL', pg_status, pg_color))

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
        r.ping()
        redis_status = "✓ ONLINE"
        redis_color = Colors.GREEN
    except:
        redis_status = "✗ OFFLINE"
        redis_color = Colors.FAIL
    services.append(('Redis', redis_status, redis_color))

    # Check Truth Engine DB
    truth_db = '/Volumes/DATA/FREEDOM/core/truth_engine/truth.db'
    if os.path.exists(truth_db):
        size_mb = os.path.getsize(truth_db) / (1024 * 1024)
        truth_status = f"✓ {size_mb:.1f}MB"
        truth_color = Colors.GREEN
    else:
        truth_status = "✗ NOT FOUND"
        truth_color = Colors.FAIL
    services.append(('Truth Engine', truth_status, truth_color))

    # Check API endpoints
    api_checks = [
        ('TechKnowledge API', 'http://localhost:5001/health'),
        ('Router Service', 'http://localhost:5002/health'),
        ('Firecrawl API', 'http://localhost:3002/v0/health'),
    ]

    for name, url in api_checks:
        try:
            import requests
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                status = "✓ HEALTHY"
                color = Colors.GREEN
            else:
                status = f"✗ ERROR {response.status_code}"
                color = Colors.FAIL
        except:
            status = "✗ OFFLINE"
            color = Colors.FAIL
        services.append((name, status, color))

    return services

def draw_progress_bar(percent, width=30, filled_char='█', empty_char='░'):
    """Draw a progress bar"""
    if percent == 'N/A':
        return '[N/A]'
    filled = int(width * percent / 100)
    bar = filled_char * filled + empty_char * (width - filled)

    # Color based on percentage
    if percent > 90:
        color = Colors.FAIL
    elif percent > 70:
        color = Colors.WARNING
    else:
        color = Colors.GREEN

    return f"{color}[{bar}] {percent:5.1f}%{Colors.END}"

def display_dashboard():
    """Display the monitoring dashboard"""
    while True:
        try:
            clear_screen()

            # Header
            print(f"{Colors.HEADER}{Colors.BOLD}")
            print("=" * 80)
            print("                 FREEDOM PLATFORM MONITORING DASHBOARD")
            print("=" * 80)
            print(f"{Colors.END}")

            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Colors.CYAN}Last Update: {timestamp}{Colors.END}")
            print()

            # Docker Services
            print(f"{Colors.BLUE}{Colors.BOLD}▶ DOCKER CONTAINERS{Colors.END}")
            print("-" * 40)
            docker_status = get_docker_status()
            for line in docker_status[:10]:  # Show first 10 containers
                if 'NAMES' in line:
                    print(f"{Colors.BOLD}{line}{Colors.END}")
                elif 'running' in line.lower():
                    print(f"{Colors.GREEN}{line}{Colors.END}")
                elif 'exited' in line.lower():
                    print(f"{Colors.FAIL}{line}{Colors.END}")
                else:
                    print(line)
            print()

            # System Resources
            print(f"{Colors.BLUE}{Colors.BOLD}▶ SYSTEM RESOURCES{Colors.END}")
            print("-" * 40)
            resources = get_system_resources()

            print(f"CPU Usage:    {draw_progress_bar(resources['cpu'])}")
            print(f"Memory Usage: {draw_progress_bar(resources['memory'])} "
                  f"({resources['memory_used']:.1f}GB / {resources['memory_total']:.1f}GB)")
            print(f"Disk Usage:   {draw_progress_bar(resources['disk'])} "
                  f"({resources['disk_used']:.1f}GB / {resources['disk_total']:.1f}GB)")
            print()

            # Service Health
            print(f"{Colors.BLUE}{Colors.BOLD}▶ SERVICE HEALTH CHECKS{Colors.END}")
            print("-" * 40)
            services = check_service_health()

            for name, status, color in services:
                print(f"{name:<20} {color}{status}{Colors.END}")
            print()

            # Redis Queues
            print(f"{Colors.BLUE}{Colors.BOLD}▶ REDIS QUEUES{Colors.END}")
            print("-" * 40)
            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, decode_responses=True)

                queues = ['crawl_queue', 'processing_queue', 'knowledge_queue']
                for queue in queues:
                    length = r.llen(queue)
                    color = Colors.GREEN
                    if length > 100:
                        color = Colors.WARNING
                    if length > 500:
                        color = Colors.FAIL
                    print(f"{queue:<20} {color}{length:>6} items{Colors.END}")
            except:
                print(f"{Colors.FAIL}Redis not available{Colors.END}")
            print()

            # Alerts
            print(f"{Colors.BLUE}{Colors.BOLD}▶ SYSTEM ALERTS{Colors.END}")
            print("-" * 40)

            alerts = []
            if resources['cpu'] != 'N/A' and resources['cpu'] > 80:
                alerts.append((f"High CPU usage: {resources['cpu']:.1f}%", Colors.WARNING))
            if resources['memory'] != 'N/A' and resources['memory'] > 80:
                alerts.append((f"High memory usage: {resources['memory']:.1f}%", Colors.WARNING))

            if alerts:
                for alert, color in alerts:
                    print(f"{color}⚠ {alert}{Colors.END}")
            else:
                print(f"{Colors.GREEN}✓ All systems operational{Colors.END}")

            # Footer
            print()
            print("-" * 80)
            print(f"{Colors.CYAN}Press Ctrl+C to exit | Refreshing every 3 seconds{Colors.END}")

            # Wait before refresh
            time.sleep(3)

        except KeyboardInterrupt:
            print(f"\n{Colors.CYAN}Dashboard stopped.{Colors.END}")
            break
        except Exception as e:
            print(f"{Colors.FAIL}Error: {e}{Colors.END}")
            time.sleep(3)

def main():
    """Main entry point"""
    try:
        # Try to import required packages
        import psutil
        import redis
        import requests
    except ImportError as e:
        print(f"{Colors.WARNING}Installing required dependencies...{Colors.END}")
        subprocess.run([sys.executable, "-m", "pip", "install",
                       "--break-system-packages", "--user",
                       "psutil", "redis", "requests"],
                      capture_output=True)
        print(f"{Colors.GREEN}Dependencies installed. Starting dashboard...{Colors.END}")
        time.sleep(2)

    display_dashboard()

if __name__ == "__main__":
    main()