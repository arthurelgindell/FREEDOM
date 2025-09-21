#!/usr/bin/env python3
"""
FREEDOM Platform Terminal Monitoring Dashboard
Comprehensive real-time monitoring for all platform systems
"""

import os
import sys
import time
import json
import subprocess
import threading
import queue
import sqlite3
import redis
import psutil
import docker
from datetime import datetime, timedelta
from collections import deque, defaultdict
import curses
from curses import wrapper
import signal

class FreedomDashboard:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.running = True
        self.data = defaultdict(dict)
        self.logs = defaultdict(lambda: deque(maxlen=10))
        self.alerts = deque(maxlen=20)
        self.docker_client = docker.from_env()
        self.redis_client = None
        self.last_update = time.time()

        # Color pairs
        self.init_colors()

        # Layout configuration
        self.layout = {
            'header': {'height': 3, 'y': 0},
            'services': {'height': 12, 'y': 3},
            'resources': {'height': 8, 'y': 15},
            'databases': {'height': 6, 'y': 23},
            'queues': {'height': 5, 'y': 29},
            'logs': {'height': 10, 'y': 34},
            'alerts': {'height': 5, 'y': 44}
        }

        # Service definitions
        self.services = {
            'core': ['techknowledge', 'router', 'firecrawl', 'playwright_worker'],
            'databases': ['postgres', 'redis'],
            'support': ['truth_engine']
        }

        # Monitoring threads
        self.threads = []
        self.data_queue = queue.Queue()

    def init_colors(self):
        """Initialize color pairs for the dashboard"""
        curses.start_color()
        curses.use_default_colors()

        # Define color pairs
        curses.init_pair(1, curses.COLOR_GREEN, -1)    # Good/Running
        curses.init_pair(2, curses.COLOR_YELLOW, -1)   # Warning
        curses.init_pair(3, curses.COLOR_RED, -1)      # Error/Critical
        curses.init_pair(4, curses.COLOR_CYAN, -1)     # Info
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # Highlight
        curses.init_pair(6, curses.COLOR_WHITE, -1)    # Normal
        curses.init_pair(7, curses.COLOR_BLUE, -1)     # Headers

        self.colors = {
            'good': curses.color_pair(1),
            'warning': curses.color_pair(2),
            'error': curses.color_pair(3),
            'info': curses.color_pair(4),
            'highlight': curses.color_pair(5),
            'normal': curses.color_pair(6),
            'header': curses.color_pair(7)
        }

    def draw_border(self, win, title=""):
        """Draw border with optional title"""
        height, width = win.getmaxyx()

        # Draw corners
        win.addch(0, 0, curses.ACS_ULCORNER)
        win.addch(0, width-1, curses.ACS_URCORNER)
        win.addch(height-1, 0, curses.ACS_LLCORNER)
        win.addch(height-1, width-1, curses.ACS_LRCORNER)

        # Draw horizontal lines
        for x in range(1, width-1):
            win.addch(0, x, curses.ACS_HLINE)
            win.addch(height-1, x, curses.ACS_HLINE)

        # Draw vertical lines
        for y in range(1, height-1):
            win.addch(y, 0, curses.ACS_VLINE)
            win.addch(y, width-1, curses.ACS_VLINE)

        # Add title if provided
        if title:
            title = f" {title} "
            win.addstr(0, 2, title, self.colors['header'] | curses.A_BOLD)

    def draw_header(self):
        """Draw dashboard header"""
        height, width = self.stdscr.getmaxyx()
        header_win = curses.newwin(3, width, 0, 0)

        # Title
        title = "FREEDOM PLATFORM MONITORING DASHBOARD"
        header_win.addstr(1, (width - len(title)) // 2, title,
                         self.colors['header'] | curses.A_BOLD)

        # Timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_win.addstr(1, width - len(timestamp) - 2, timestamp,
                         self.colors['info'])

        # Status indicator
        status = "● LIVE" if self.running else "● PAUSED"
        color = self.colors['good'] if self.running else self.colors['warning']
        header_win.addstr(1, 2, status, color | curses.A_BOLD)

        self.draw_border(header_win)
        header_win.refresh()

    def draw_services_panel(self):
        """Draw Docker services monitoring panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['services']['height']
        panel_y = self.layout['services']['y']

        services_win = curses.newwin(panel_height, width // 2, panel_y, 0)
        self.draw_border(services_win, "DOCKER SERVICES")

        y_pos = 2

        try:
            containers = self.docker_client.containers.list(all=True)

            for container in containers:
                if y_pos >= panel_height - 2:
                    break

                name = container.name[:20]
                status = container.status

                # Determine color based on status
                if status == 'running':
                    color = self.colors['good']
                    status_icon = "●"
                elif status == 'exited':
                    color = self.colors['error']
                    status_icon = "●"
                else:
                    color = self.colors['warning']
                    status_icon = "◐"

                # Get container stats if running
                cpu_percent = "---"
                mem_usage = "---"

                if status == 'running':
                    try:
                        stats = container.stats(stream=False)
                        # CPU calculation
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                   stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                      stats['precpu_stats']['system_cpu_usage']
                        if system_delta > 0:
                            cpu_percent = f"{(cpu_delta / system_delta) * 100:.1f}%"

                        # Memory calculation
                        mem_mb = stats['memory_stats']['usage'] / (1024 * 1024)
                        mem_usage = f"{mem_mb:.0f}MB"
                    except:
                        pass

                # Display service info
                line = f"{status_icon} {name:<20} CPU:{cpu_percent:>6} MEM:{mem_usage:>8}"
                services_win.addstr(y_pos, 2, line[:width//2-4], color)
                y_pos += 1

        except Exception as e:
            services_win.addstr(2, 2, f"Error: {str(e)[:40]}", self.colors['error'])

        services_win.refresh()

    def draw_health_checks_panel(self):
        """Draw service health checks panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['services']['height']
        panel_y = self.layout['services']['y']

        health_win = curses.newwin(panel_height, width // 2, panel_y, width // 2)
        self.draw_border(health_win, "HEALTH CHECKS")

        y_pos = 2

        # Define health check endpoints
        health_checks = [
            ('TechKnowledge API', 'http://localhost:5001/health'),
            ('Router Service', 'http://localhost:5002/health'),
            ('Firecrawl API', 'http://localhost:3002/v0/health'),
            ('Playwright Worker', 'http://localhost:5003/health'),
            ('PostgreSQL', 'postgres://localhost:5432'),
            ('Redis Queue', 'redis://localhost:6379'),
            ('Truth Engine DB', '/Volumes/DATA/FREEDOM/core/truth_engine/truth.db')
        ]

        for service_name, endpoint in health_checks:
            if y_pos >= panel_height - 2:
                break

            # Check health status
            status = "UNKNOWN"
            color = self.colors['warning']
            response_time = "---"

            if 'http' in endpoint:
                try:
                    import requests
                    start_time = time.time()
                    response = requests.get(endpoint, timeout=1)
                    response_time = f"{(time.time() - start_time) * 1000:.0f}ms"

                    if response.status_code == 200:
                        status = "HEALTHY"
                        color = self.colors['good']
                    else:
                        status = f"ERROR ({response.status_code})"
                        color = self.colors['error']
                except:
                    status = "UNREACHABLE"
                    color = self.colors['error']

            elif 'postgres' in endpoint:
                try:
                    import psycopg2
                    conn = psycopg2.connect(host='localhost', port=5432,
                                           database='postgres',
                                           connect_timeout=1)
                    conn.close()
                    status = "CONNECTED"
                    color = self.colors['good']
                except:
                    status = "OFFLINE"
                    color = self.colors['error']

            elif 'redis' in endpoint:
                try:
                    r = redis.Redis(host='localhost', port=6379,
                                   socket_connect_timeout=1)
                    r.ping()
                    status = "CONNECTED"
                    color = self.colors['good']
                except:
                    status = "OFFLINE"
                    color = self.colors['error']

            elif '.db' in endpoint:
                if os.path.exists(endpoint):
                    status = "AVAILABLE"
                    color = self.colors['good']
                    # Get file size
                    size_mb = os.path.getsize(endpoint) / (1024 * 1024)
                    response_time = f"{size_mb:.0f}MB"
                else:
                    status = "NOT FOUND"
                    color = self.colors['error']

            # Display health check
            status_icon = "✓" if status in ["HEALTHY", "CONNECTED", "AVAILABLE"] else "✗"
            line = f"{status_icon} {service_name:<18} {status:<12} {response_time:>8}"
            health_win.addstr(y_pos, 2, line[:width//2-4], color)
            y_pos += 1

        health_win.refresh()

    def draw_resources_panel(self):
        """Draw system resources monitoring panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['resources']['height']
        panel_y = self.layout['resources']['y']

        resources_win = curses.newwin(panel_height, width, panel_y, 0)
        self.draw_border(resources_win, "SYSTEM RESOURCES")

        # CPU Usage
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        avg_cpu = sum(cpu_percent) / len(cpu_percent)

        y_pos = 2
        resources_win.addstr(y_pos, 2, "CPU Usage:", self.colors['header'] | curses.A_BOLD)

        # CPU bar graph
        bar_width = 40
        for i, core_usage in enumerate(cpu_percent[:4]):  # Show first 4 cores
            y_pos += 1
            filled = int(core_usage * bar_width / 100)
            bar = "█" * filled + "░" * (bar_width - filled)

            color = self.colors['good']
            if core_usage > 80:
                color = self.colors['error']
            elif core_usage > 60:
                color = self.colors['warning']

            resources_win.addstr(y_pos, 2, f"Core {i}: [{bar}] {core_usage:5.1f}%", color)

        # Memory Usage
        mem = psutil.virtual_memory()
        y_pos += 2
        resources_win.addstr(y_pos, 2, "Memory Usage:", self.colors['header'] | curses.A_BOLD)

        y_pos += 1
        mem_filled = int(mem.percent * bar_width / 100)
        mem_bar = "█" * mem_filled + "░" * (bar_width - mem_filled)

        mem_color = self.colors['good']
        if mem.percent > 90:
            mem_color = self.colors['error']
        elif mem.percent > 75:
            mem_color = self.colors['warning']

        mem_info = f"RAM: [{mem_bar}] {mem.percent:5.1f}% ({mem.used/1024**3:.1f}GB/{mem.total/1024**3:.1f}GB)"
        resources_win.addstr(y_pos, 2, mem_info, mem_color)

        # Disk Usage
        disk = psutil.disk_usage('/')
        disk_filled = int(disk.percent * bar_width / 100)
        disk_bar = "█" * disk_filled + "░" * (bar_width - disk_filled)

        disk_color = self.colors['good']
        if disk.percent > 90:
            disk_color = self.colors['error']
        elif disk.percent > 75:
            disk_color = self.colors['warning']

        # Network I/O
        net_io = psutil.net_io_counters()
        y_pos = 2
        x_pos = width // 2 + 2

        resources_win.addstr(y_pos, x_pos, "Network I/O:", self.colors['header'] | curses.A_BOLD)
        y_pos += 1
        resources_win.addstr(y_pos, x_pos, f"↓ RX: {net_io.bytes_recv/1024**2:,.0f} MB", self.colors['info'])
        y_pos += 1
        resources_win.addstr(y_pos, x_pos, f"↑ TX: {net_io.bytes_sent/1024**2:,.0f} MB", self.colors['info'])

        # Process Count
        y_pos += 2
        proc_count = len(psutil.pids())
        resources_win.addstr(y_pos, x_pos, f"Processes: {proc_count}", self.colors['normal'])

        # Load Average
        y_pos += 1
        load_avg = os.getloadavg()
        resources_win.addstr(y_pos, x_pos, f"Load: {load_avg[0]:.2f} {load_avg[1]:.2f} {load_avg[2]:.2f}",
                           self.colors['normal'])

        resources_win.refresh()

    def draw_database_panel(self):
        """Draw database statistics panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['databases']['height']
        panel_y = self.layout['databases']['y']

        db_win = curses.newwin(panel_height, width // 2, panel_y, 0)
        self.draw_border(db_win, "DATABASE STATS")

        y_pos = 2

        # PostgreSQL Stats
        db_win.addstr(y_pos, 2, "PostgreSQL:", self.colors['header'] | curses.A_BOLD)
        y_pos += 1

        try:
            import psycopg2
            conn = psycopg2.connect(host='localhost', port=5432,
                                   database='postgres')
            cur = conn.cursor()

            # Get database size
            cur.execute("SELECT pg_database_size('postgres')")
            db_size = cur.fetchone()[0] / (1024 * 1024)
            db_win.addstr(y_pos, 4, f"Size: {db_size:.1f} MB", self.colors['normal'])
            y_pos += 1

            # Get connection count
            cur.execute("SELECT count(*) FROM pg_stat_activity")
            conn_count = cur.fetchone()[0]
            db_win.addstr(y_pos, 4, f"Connections: {conn_count}", self.colors['normal'])

            cur.close()
            conn.close()
        except:
            db_win.addstr(y_pos, 4, "PostgreSQL Offline", self.colors['error'])

        # Truth Engine Stats
        y_pos = 2
        db_win.addstr(y_pos, width//4 + 2, "Truth Engine:", self.colors['header'] | curses.A_BOLD)
        y_pos += 1

        truth_db = '/Volumes/DATA/FREEDOM/core/truth_engine/truth.db'
        if os.path.exists(truth_db):
            size_mb = os.path.getsize(truth_db) / (1024 * 1024)
            db_win.addstr(y_pos, width//4 + 4, f"Size: {size_mb:.1f} MB", self.colors['normal'])

            try:
                conn = sqlite3.connect(truth_db)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cur.fetchone()[0]
                y_pos += 1
                db_win.addstr(y_pos, width//4 + 4, f"Tables: {table_count}", self.colors['normal'])
                conn.close()
            except:
                pass
        else:
            db_win.addstr(y_pos, width//4 + 4, "Not Found", self.colors['error'])

        db_win.refresh()

    def draw_queue_panel(self):
        """Draw Redis queue monitoring panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['queues']['height']
        panel_y = self.layout['queues']['y']

        queue_win = curses.newwin(panel_height, width // 2, panel_y, width // 2)
        self.draw_border(queue_win, "REDIS QUEUES")

        y_pos = 2

        try:
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)

            # Get queue lengths
            queues = ['crawl_queue', 'processing_queue', 'knowledge_queue']

            for queue_name in queues:
                if y_pos >= panel_height - 1:
                    break

                queue_len = r.llen(queue_name)

                color = self.colors['good']
                if queue_len > 100:
                    color = self.colors['warning']
                if queue_len > 500:
                    color = self.colors['error']

                queue_win.addstr(y_pos, 2, f"{queue_name:<20} {queue_len:>6} items", color)
                y_pos += 1

        except:
            queue_win.addstr(2, 2, "Redis Offline", self.colors['error'])

        queue_win.refresh()

    def draw_logs_panel(self):
        """Draw recent logs panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['logs']['height']
        panel_y = self.layout['logs']['y']

        logs_win = curses.newwin(panel_height, width, panel_y, 0)
        self.draw_border(logs_win, "RECENT LOGS")

        y_pos = 2

        # Get recent Docker logs
        try:
            containers = self.docker_client.containers.list()
            all_logs = []

            for container in containers[:3]:  # Get logs from first 3 containers
                try:
                    logs = container.logs(tail=3, timestamps=True).decode('utf-8').split('\n')
                    for log in logs:
                        if log.strip():
                            # Parse timestamp and message
                            parts = log.split(' ', 1)
                            if len(parts) == 2:
                                timestamp = parts[0][:19]  # Get just the datetime part
                                message = parts[1][:width-25]  # Truncate message
                                all_logs.append((timestamp, container.name[:15], message))
                except:
                    pass

            # Sort logs by timestamp
            all_logs.sort(key=lambda x: x[0], reverse=True)

            # Display recent logs
            for timestamp, container, message in all_logs[:panel_height-3]:
                if y_pos >= panel_height - 1:
                    break

                # Determine log level color
                color = self.colors['normal']
                if 'ERROR' in message or 'CRITICAL' in message:
                    color = self.colors['error']
                elif 'WARNING' in message:
                    color = self.colors['warning']
                elif 'INFO' in message:
                    color = self.colors['info']

                log_line = f"{timestamp} [{container}] {message}"
                logs_win.addstr(y_pos, 2, log_line[:width-4], color)
                y_pos += 1

        except Exception as e:
            logs_win.addstr(2, 2, f"Error fetching logs: {str(e)[:width-10]}",
                          self.colors['error'])

        logs_win.refresh()

    def draw_alerts_panel(self):
        """Draw alerts and notifications panel"""
        height, width = self.stdscr.getmaxyx()
        panel_height = self.layout['alerts']['height']
        panel_y = self.layout['alerts']['y']

        # Ensure panel doesn't exceed screen height
        if panel_y + panel_height > height:
            panel_height = height - panel_y

        alerts_win = curses.newwin(panel_height, width, panel_y, 0)
        self.draw_border(alerts_win, "ALERTS & NOTIFICATIONS")

        y_pos = 2

        # Check for critical conditions and generate alerts
        alerts = []

        # CPU Alert
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 90:
            alerts.append(("CRITICAL", f"High CPU usage: {cpu_percent:.1f}%", self.colors['error']))
        elif cpu_percent > 75:
            alerts.append(("WARNING", f"Elevated CPU usage: {cpu_percent:.1f}%", self.colors['warning']))

        # Memory Alert
        mem = psutil.virtual_memory()
        if mem.percent > 90:
            alerts.append(("CRITICAL", f"High memory usage: {mem.percent:.1f}%", self.colors['error']))
        elif mem.percent > 75:
            alerts.append(("WARNING", f"Elevated memory usage: {mem.percent:.1f}%", self.colors['warning']))

        # Docker Container Alerts
        try:
            containers = self.docker_client.containers.list(all=True)
            stopped = [c.name for c in containers if c.status != 'running']
            if stopped:
                alerts.append(("WARNING", f"Stopped containers: {', '.join(stopped[:3])}",
                             self.colors['warning']))
        except:
            pass

        # Display alerts
        if not alerts:
            alerts_win.addstr(y_pos, 2, "✓ All systems operational", self.colors['good'])
        else:
            for level, message, color in alerts[:panel_height-3]:
                if y_pos >= panel_height - 1:
                    break

                timestamp = datetime.now().strftime("%H:%M:%S")
                alert_line = f"[{timestamp}] {level}: {message}"
                alerts_win.addstr(y_pos, 2, alert_line[:width-4], color)
                y_pos += 1

        alerts_win.refresh()

    def draw_footer(self):
        """Draw dashboard footer with controls"""
        height, width = self.stdscr.getmaxyx()

        footer_text = " [Q]uit | [P]ause | [R]efresh | [L]ogs | [H]elp | ↑↓ Scroll "
        footer_y = height - 1

        # Center the footer text
        footer_x = (width - len(footer_text)) // 2

        self.stdscr.addstr(footer_y, footer_x, footer_text,
                          self.colors['info'] | curses.A_REVERSE)

    def refresh_display(self):
        """Refresh entire dashboard display"""
        self.stdscr.clear()

        # Draw all panels
        self.draw_header()
        self.draw_services_panel()
        self.draw_health_checks_panel()
        self.draw_resources_panel()
        self.draw_database_panel()
        self.draw_queue_panel()
        self.draw_logs_panel()
        self.draw_alerts_panel()
        self.draw_footer()

        self.stdscr.refresh()

    def run(self):
        """Main dashboard loop"""
        # Set up curses environment
        curses.curs_set(0)  # Hide cursor
        self.stdscr.nodelay(True)  # Non-blocking input
        self.stdscr.keypad(True)  # Enable special keys

        last_refresh = time.time()
        refresh_interval = 2.0  # Refresh every 2 seconds

        while self.running:
            try:
                # Check for user input
                key = self.stdscr.getch()

                if key == ord('q') or key == ord('Q'):
                    self.running = False
                    break
                elif key == ord('p') or key == ord('P'):
                    # Pause/Resume
                    self.running = not self.running
                elif key == ord('r') or key == ord('R'):
                    # Force refresh
                    self.refresh_display()

                # Auto-refresh at interval
                current_time = time.time()
                if current_time - last_refresh >= refresh_interval:
                    self.refresh_display()
                    last_refresh = current_time

                # Small delay to prevent CPU spinning
                time.sleep(0.1)

            except KeyboardInterrupt:
                break
            except curses.error:
                # Handle resize events
                pass
            except Exception as e:
                # Log error but continue running
                pass

        # Cleanup
        curses.curs_set(1)  # Show cursor again

def main(stdscr):
    """Main entry point for curses wrapper"""
    dashboard = FreedomDashboard(stdscr)
    dashboard.run()

if __name__ == "__main__":
    # Handle terminal resize
    signal.signal(signal.SIGWINCH, signal.SIG_IGN)

    try:
        # Check dependencies
        import docker
        import redis
        import psutil
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install",
                       "docker", "redis", "psutil", "psycopg2-binary", "requests"],
                      capture_output=True)
        print("Dependencies installed. Please run the dashboard again.")
        sys.exit(1)

    # Run dashboard
    wrapper(main)