#!/usr/bin/env python3
"""
FREEDOM Platform Professional Dashboard
Modern terminal monitoring using Rich library
"""

import os
import sys
import time
import json
import sqlite3
import subprocess
import threading
from datetime import datetime, timedelta
from collections import deque, defaultdict
import signal

# Import Rich components
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich import box
from rich.progress_bar import ProgressBar
from rich.syntax import Syntax
from rich.tree import Tree

# Try imports for monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import docker
    DOCKER_AVAILABLE = True
    docker_client = docker.from_env()
except:
    DOCKER_AVAILABLE = False
    docker_client = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class FreedomDashboard:
    def __init__(self):
        self.console = Console()
        self.running = True
        self.data = defaultdict(dict)
        self.layout = self.create_layout()

        # Historical data for sparklines
        self.cpu_history = deque(maxlen=20)
        self.memory_history = deque(maxlen=20)
        self.network_history = deque(maxlen=20)

    def create_layout(self):
        """Create the dashboard layout"""
        layout = Layout(name="root")

        # Main vertical split
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=1),
        )

        # Body horizontal split
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=3),
        )

        # Left side panels
        layout["left"].split(
            Layout(name="services", ratio=2),
            Layout(name="resources", ratio=2),
            Layout(name="alerts", ratio=1),
        )

        # Right side panels
        layout["right"].split(
            Layout(name="health", ratio=1),
            Layout(name="databases", ratio=1),
            Layout(name="logs", ratio=2),
        )

        return layout

    def create_header(self):
        """Create dashboard header"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="left")
        grid.add_column(justify="center")
        grid.add_column(justify="right")

        # Status indicator
        status = "[bold green]● LIVE[/]" if self.running else "[bold yellow]● PAUSED[/]"

        # Title
        title = "[bold cyan]FREEDOM PLATFORM[/] [dim]Professional Monitoring[/]"

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        grid.add_row(
            status,
            title,
            f"[dim]{timestamp}[/]"
        )

        return Panel(grid, style="bold blue", box=box.DOUBLE)

    def create_services_panel(self):
        """Create Docker services panel with status indicators"""
        table = Table(
            title="[bold]Docker Services[/]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )

        table.add_column("Service", style="white", width=20)
        table.add_column("Status", width=10)
        table.add_column("CPU", justify="right", width=8)
        table.add_column("Memory", justify="right", width=10)
        table.add_column("Uptime", justify="right", width=12)

        if DOCKER_AVAILABLE and docker_client:
            try:
                containers = docker_client.containers.list(all=True)

                for container in containers[:8]:  # Limit to 8 containers
                    name = container.name[:20]
                    status = container.status

                    # Status with color
                    if status == 'running':
                        status_text = "[green]● Running[/]"

                        # Get stats if running
                        try:
                            stats = container.stats(stream=False)

                            # CPU calculation
                            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                       stats['precpu_stats']['cpu_usage']['total_usage']
                            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                         stats['precpu_stats']['system_cpu_usage']
                            cpu_percent = 0.0
                            if system_delta > 0:
                                cpu_percent = (cpu_delta / system_delta) * 100
                            cpu_text = f"{cpu_percent:.1f}%"

                            # Memory calculation
                            mem_mb = stats['memory_stats'].get('usage', 0) / (1024 * 1024)
                            mem_text = f"{mem_mb:.0f}MB"

                            # Uptime
                            created = datetime.fromisoformat(container.attrs['State']['StartedAt'].replace('Z', '+00:00'))
                            uptime = datetime.now(created.tzinfo) - created
                            hours = int(uptime.total_seconds() // 3600)
                            minutes = int((uptime.total_seconds() % 3600) // 60)
                            uptime_text = f"{hours}h {minutes}m"

                        except:
                            cpu_text = "N/A"
                            mem_text = "N/A"
                            uptime_text = "N/A"
                    else:
                        status_text = f"[red]● {status.title()}[/]"
                        cpu_text = "-"
                        mem_text = "-"
                        uptime_text = "-"

                    table.add_row(name, status_text, cpu_text, mem_text, uptime_text)

            except Exception as e:
                table.add_row("Error", f"[red]{str(e)[:30]}[/]", "-", "-", "-")
        else:
            table.add_row("Docker", "[yellow]Not Available[/]", "-", "-", "-")

        return Panel(table, border_style="blue")

    def create_resources_panel(self):
        """Create system resources panel with progress bars"""
        if PSUTIL_AVAILABLE:
            # Get current metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()

            # Store history
            self.cpu_history.append(cpu_percent)
            self.memory_history.append(memory.percent)

            # Create visual bars
            def create_bar(value, max_value=100, width=30, gradient=True):
                filled = int(width * value / max_value)

                if gradient:
                    if value > 80:
                        color = "red"
                    elif value > 60:
                        color = "yellow"
                    else:
                        color = "green"
                else:
                    color = "cyan"

                bar = f"[{color}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/]"
                return bar

            # Create content
            content = []

            # CPU with sparkline
            cpu_sparkline = self.create_sparkline(self.cpu_history)
            content.append(f"[bold]CPU Usage[/] {cpu_percent:5.1f}%")
            content.append(create_bar(cpu_percent))
            content.append(f"[dim]{cpu_sparkline}[/]")
            content.append("")

            # Memory
            content.append(f"[bold]Memory[/] {memory.percent:5.1f}% ({memory.used/1024**3:.1f}GB / {memory.total/1024**3:.1f}GB)")
            content.append(create_bar(memory.percent))
            content.append("")

            # Disk
            content.append(f"[bold]Disk[/] {disk.percent:5.1f}% ({disk.used/1024**3:.1f}GB / {disk.total/1024**3:.1f}GB)")
            content.append(create_bar(disk.percent))
            content.append("")

            # Network
            content.append(f"[bold]Network[/]")
            content.append(f"↓ {net_io.bytes_recv/1024**2:,.0f} MB  ↑ {net_io.bytes_sent/1024**2:,.0f} MB")

            # Load average
            load_avg = os.getloadavg()
            content.append("")
            content.append(f"[bold]Load[/] {load_avg[0]:.2f} {load_avg[1]:.2f} {load_avg[2]:.2f}")

            text = "\n".join(content)
        else:
            text = "[yellow]psutil not available[/]"

        return Panel(text, title="[bold]System Resources[/]", border_style="green")

    def create_sparkline(self, data, width=20):
        """Create a sparkline from data"""
        if not data:
            return ""

        blocks = " ▁▂▃▄▅▆▇█"
        min_val = min(data)
        max_val = max(data)

        if max_val == min_val:
            return blocks[4] * len(data)

        sparkline = ""
        for value in data:
            index = int((value - min_val) / (max_val - min_val) * (len(blocks) - 1))
            sparkline += blocks[index]

        return sparkline

    def create_health_panel(self):
        """Create service health checks panel"""
        tree = Tree("[bold]Service Health[/]")

        # Database checks
        db_branch = tree.add("[bold cyan]Databases[/]")

        # PostgreSQL
        try:
            result = subprocess.run(['pg_isready', '-h', 'localhost', '-p', '5432'],
                                  capture_output=True, timeout=1)
            if result.returncode == 0:
                db_branch.add("[green]✓ PostgreSQL[/] - Online")
            else:
                db_branch.add("[red]✗ PostgreSQL[/] - Offline")
        except:
            db_branch.add("[yellow]? PostgreSQL[/] - Unknown")

        # Redis
        if REDIS_AVAILABLE:
            try:
                r = redis.Redis(host='localhost', port=6379, socket_connect_timeout=1)
                r.ping()
                db_branch.add("[green]✓ Redis[/] - Online")
            except:
                db_branch.add("[red]✗ Redis[/] - Offline")
        else:
            db_branch.add("[yellow]? Redis[/] - Not installed")

        # Truth Engine
        truth_db = '/Volumes/DATA/FREEDOM/core/truth_engine/truth.db'
        if os.path.exists(truth_db):
            size_mb = os.path.getsize(truth_db) / (1024 * 1024)
            db_branch.add(f"[green]✓ Truth Engine[/] - {size_mb:.1f}MB")
        else:
            db_branch.add("[red]✗ Truth Engine[/] - Not found")

        # API Services
        api_branch = tree.add("[bold cyan]API Services[/]")

        services = [
            ('TechKnowledge', 'http://localhost:5001/health'),
            ('Router', 'http://localhost:5002/health'),
            ('Firecrawl', 'http://localhost:3002/v0/health'),
        ]

        for name, url in services:
            try:
                import requests
                response = requests.get(url, timeout=0.5)
                if response.status_code == 200:
                    api_branch.add(f"[green]✓ {name}[/] - Healthy")
                else:
                    api_branch.add(f"[yellow]! {name}[/] - Status {response.status_code}")
            except:
                api_branch.add(f"[red]✗ {name}[/] - Offline")

        return Panel(tree, border_style="cyan")

    def create_database_panel(self):
        """Create database statistics panel"""
        table = Table(
            title="[bold]Database Statistics[/]",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold magenta"
        )

        table.add_column("Database", style="white", width=15)
        table.add_column("Size", justify="right", width=10)
        table.add_column("Tables", justify="right", width=8)
        table.add_column("Connections", justify="right", width=12)

        # PostgreSQL
        try:
            import psycopg2
            conn = psycopg2.connect(host='localhost', port=5432, database='postgres')
            cur = conn.cursor()

            cur.execute("SELECT pg_database_size('postgres')")
            db_size = cur.fetchone()[0] / (1024 * 1024)

            cur.execute("SELECT count(*) FROM pg_stat_activity")
            conn_count = cur.fetchone()[0]

            table.add_row("PostgreSQL", f"{db_size:.1f}MB", "N/A", str(conn_count))

            cur.close()
            conn.close()
        except:
            table.add_row("PostgreSQL", "[dim]Offline[/]", "-", "-")

        # Truth Engine
        truth_db = '/Volumes/DATA/FREEDOM/core/truth_engine/truth.db'
        if os.path.exists(truth_db):
            size_mb = os.path.getsize(truth_db) / (1024 * 1024)

            try:
                conn = sqlite3.connect(truth_db)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cur.fetchone()[0]
                conn.close()

                table.add_row("Truth Engine", f"{size_mb:.1f}MB", str(table_count), "N/A")
            except:
                table.add_row("Truth Engine", f"{size_mb:.1f}MB", "Error", "N/A")
        else:
            table.add_row("Truth Engine", "[dim]Not Found[/]", "-", "-")

        # Redis
        if REDIS_AVAILABLE:
            try:
                r = redis.Redis(host='localhost', port=6379, decode_responses=True)
                info = r.info()

                # Get memory usage
                mem_mb = info.get('used_memory', 0) / (1024 * 1024)

                # Get connected clients
                clients = info.get('connected_clients', 0)

                # Get number of keys
                keys = r.dbsize()

                table.add_row("Redis", f"{mem_mb:.1f}MB", f"{keys} keys", str(clients))
            except:
                table.add_row("Redis", "[dim]Offline[/]", "-", "-")
        else:
            table.add_row("Redis", "[dim]Not Available[/]", "-", "-")

        return Panel(table, border_style="magenta")

    def create_logs_panel(self):
        """Create logs panel with syntax highlighting"""
        logs = []

        if DOCKER_AVAILABLE and docker_client:
            try:
                containers = docker_client.containers.list()

                for container in containers[:3]:  # Get logs from first 3 containers
                    try:
                        log_lines = container.logs(tail=5, timestamps=True).decode('utf-8').split('\n')

                        for line in log_lines:
                            if line.strip():
                                # Parse and format log
                                parts = line.split(' ', 1)
                                if len(parts) == 2:
                                    timestamp = parts[0][:19]
                                    message = parts[1][:100]  # Truncate message

                                    # Color based on log level
                                    if 'ERROR' in message or 'CRITICAL' in message:
                                        color = "red"
                                    elif 'WARNING' in message:
                                        color = "yellow"
                                    elif 'INFO' in message:
                                        color = "cyan"
                                    else:
                                        color = "white"

                                    logs.append(f"[dim]{timestamp}[/] [{color}]{container.name[:15]}[/] {message}")
                    except:
                        pass

            except:
                logs.append("[red]Error fetching Docker logs[/]")
        else:
            logs.append("[yellow]Docker not available for log streaming[/]")

        if not logs:
            logs.append("[dim]No recent logs[/]")

        # Limit to last 15 lines
        logs = logs[-15:]

        return Panel(
            "\n".join(logs),
            title="[bold]Recent Logs[/]",
            border_style="yellow"
        )

    def create_alerts_panel(self):
        """Create alerts panel"""
        alerts = []

        # Check for critical conditions
        if PSUTIL_AVAILABLE:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()

            if cpu > 90:
                alerts.append("[red bold]⚠ CRITICAL[/] High CPU usage: {:.1f}%".format(cpu))
            elif cpu > 75:
                alerts.append("[yellow]⚠ WARNING[/] Elevated CPU: {:.1f}%".format(cpu))

            if mem.percent > 90:
                alerts.append("[red bold]⚠ CRITICAL[/] High memory usage: {:.1f}%".format(mem.percent))
            elif mem.percent > 75:
                alerts.append("[yellow]⚠ WARNING[/] Elevated memory: {:.1f}%".format(mem.percent))

        # Check Docker containers
        if DOCKER_AVAILABLE and docker_client:
            try:
                containers = docker_client.containers.list(all=True)
                stopped = [c.name for c in containers if c.status != 'running']

                if stopped:
                    alerts.append(f"[yellow]⚠ WARNING[/] Stopped: {', '.join(stopped[:3])}")
            except:
                pass

        if not alerts:
            alerts.append("[green]✓[/] All systems operational")

        return Panel(
            "\n".join(alerts),
            title="[bold]System Alerts[/]",
            border_style="red" if len(alerts) > 1 else "green"
        )

    def create_footer(self):
        """Create dashboard footer"""
        footer_text = "[dim]Press [bold]q[/] to quit | [bold]p[/] to pause | [bold]r[/] to refresh | Updates every 2s[/]"
        return Align.center(footer_text)

    def update_dashboard(self):
        """Update all dashboard panels"""
        self.layout["header"].update(self.create_header())
        self.layout["services"].update(self.create_services_panel())
        self.layout["resources"].update(self.create_resources_panel())
        self.layout["health"].update(self.create_health_panel())
        self.layout["databases"].update(self.create_database_panel())
        self.layout["logs"].update(self.create_logs_panel())
        self.layout["alerts"].update(self.create_alerts_panel())
        self.layout["footer"].update(self.create_footer())

        return self.layout

    def run(self):
        """Run the dashboard with live updates"""
        with Live(
            self.update_dashboard(),
            refresh_per_second=0.5,
            screen=True,
            auto_refresh=True
        ) as live:
            while self.running:
                time.sleep(2)  # Update interval
                live.update(self.update_dashboard())

def handle_interrupt(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n[cyan]Dashboard stopped.[/]")
    sys.exit(0)

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, handle_interrupt)

    # Check and install dependencies if needed
    try:
        from rich import console
    except ImportError:
        print("Installing required dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install",
                       "--break-system-packages", "--user",
                       "rich", "psutil", "docker", "redis", "psycopg2-binary", "requests"],
                      capture_output=True)
        print("Dependencies installed. Please restart the dashboard.")
        sys.exit(0)

    # Run dashboard
    dashboard = FreedomDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()