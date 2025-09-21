# FREEDOM Platform - Operations Manual

## Overview
Comprehensive operational procedures for maintaining the FREEDOM platform in production. This manual covers daily health checks, performance monitoring, alerting, log analysis, troubleshooting, and scaling procedures to ensure optimal system operation.

**Target Audience**: Operations team, Site Reliability Engineers
**Prerequisites**: System administration knowledge, Docker familiarity
**Update Frequency**: Daily health checks, weekly performance reviews

## Success Criteria
- ✅ 99.9% service uptime
- ✅ <3 second average response time
- ✅ Zero data loss incidents
- ✅ Proactive issue detection and resolution
- ✅ Comprehensive operational visibility

---

## Daily Operations Procedures

### Morning Health Check (8:00 AM)
```bash
#!/bin/bash
# Daily morning health check script
cd /Volumes/DATA/FREEDOM

echo "=========================================="
echo "FREEDOM Platform Daily Health Check"
echo "Date: $(date)"
echo "=========================================="

# 1. Service Status Check
echo "1. Checking Service Status..."
docker-compose ps
echo ""

# 2. Health Endpoints
echo "2. Testing Health Endpoints..."
make health
echo ""

# 3. Resource Usage
echo "3. System Resources..."
docker stats --no-stream
echo ""

# 4. Database Health
echo "4. Database Status..."
docker-compose exec postgres pg_isready -U freedom -d freedom_kb
docker-compose exec postgres psql -U freedom -d freedom_kb -c "SELECT COUNT(*) as documents FROM documents;"
echo ""

# 5. MLX Performance Test
echo "5. MLX Performance Check..."
python -c "
import time, requests
start = time.time()
try:
    response = requests.post('http://localhost:8001/v1/chat/completions',
        json={'messages': [{'role': 'user', 'content': 'Daily health check'}], 'max_tokens': 10},
        timeout=30)
    end = time.time()
    if response.status_code == 200:
        print(f'✅ MLX responding in {end-start:.2f}s')
    else:
        print(f'❌ MLX error: {response.status_code}')
except Exception as e:
    print(f'❌ MLX unreachable: {e}')
"
echo ""

# 6. Storage Check
echo "6. Storage Status..."
df -h /Volumes/DATA/FREEDOM
echo ""

# 7. Recent Errors
echo "7. Recent Error Check..."
docker-compose logs --since=24h | grep -i error | tail -5
echo ""

echo "Daily health check completed at $(date)"
```

### Evening Maintenance (8:00 PM)
```bash
#!/bin/bash
# Daily evening maintenance script
cd /Volumes/DATA/FREEDOM

echo "=========================================="
echo "FREEDOM Platform Evening Maintenance"
echo "Date: $(date)"
echo "=========================================="

# 1. Log Rotation
echo "1. Rotating logs..."
find logs/ -name "*.log" -size +100M -exec gzip {} \;
find logs/ -name "*.log.gz" -mtime +7 -delete
echo "✅ Log rotation completed"

# 2. Performance Metrics Collection
echo "2. Collecting performance metrics..."
python -c "
import json, time, requests
from datetime import datetime

metrics = {
    'timestamp': datetime.now().isoformat(),
    'services': {}
}

# API Gateway metrics
try:
    start = time.time()
    response = requests.get('http://localhost:8080/health', timeout=10)
    metrics['services']['api_gateway'] = {
        'status': response.status_code,
        'response_time': time.time() - start
    }
except Exception as e:
    metrics['services']['api_gateway'] = {'error': str(e)}

# MLX Service metrics
try:
    start = time.time()
    response = requests.get('http://localhost:8001/health', timeout=10)
    metrics['services']['mlx_server'] = {
        'status': response.status_code,
        'response_time': time.time() - start
    }
except Exception as e:
    metrics['services']['mlx_server'] = {'error': str(e)}

# Save metrics
with open(f'logs/daily_metrics_{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
    json.dump(metrics, f, indent=2)

print('✅ Metrics collected')
"

# 3. Database Maintenance
echo "3. Database maintenance..."
docker-compose exec postgres psql -U freedom -d freedom_kb -c "VACUUM ANALYZE;"
echo "✅ Database maintenance completed"

# 4. Docker Cleanup
echo "4. Docker cleanup..."
docker system prune -f --filter "until=24h"
echo "✅ Docker cleanup completed"

echo "Evening maintenance completed at $(date)"
```

---

## Performance Monitoring

### Real-Time Monitoring Dashboard
```bash
#!/bin/bash
# Real-time monitoring dashboard
watch -n 5 'clear; echo "=== FREEDOM PLATFORM DASHBOARD ===" && \
echo "Last Update: $(date)" && \
echo "" && \
echo "=== SERVICE STATUS ===" && \
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" && \
echo "" && \
echo "=== RESOURCE USAGE ===" && \
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" && \
echo "" && \
echo "=== DISK USAGE ===" && \
df -h /Volumes/DATA/FREEDOM | tail -1 && \
echo "" && \
echo "=== RECENT ERRORS ===" && \
docker-compose logs --since=5m 2>&1 | grep -i error | tail -3'
```

### Performance Metrics Collection
```bash
# Create comprehensive metrics collector
cat > /Volumes/DATA/FREEDOM/scripts/metrics_collector.py << 'EOF'
#!/usr/bin/env python3
"""
FREEDOM Platform Metrics Collector
Collects and stores system performance metrics
"""

import json
import time
import requests
import subprocess
import psutil
from datetime import datetime
import sqlite3
import os

class MetricsCollector:
    def __init__(self):
        self.db_path = '/Volumes/DATA/FREEDOM/logs/metrics.db'
        self.init_database()

    def init_database(self):
        """Initialize metrics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TEXT PRIMARY KEY,
                service TEXT,
                metric_name TEXT,
                metric_value REAL,
                unit TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def collect_service_metrics(self):
        """Collect metrics from all services"""
        timestamp = datetime.now().isoformat()
        metrics = []

        # API Gateway metrics
        try:
            start_time = time.time()
            response = requests.get('http://localhost:8080/health', timeout=5)
            response_time = time.time() - start_time

            metrics.append((timestamp, 'api_gateway', 'response_time', response_time, 'seconds'))
            metrics.append((timestamp, 'api_gateway', 'status_code', response.status_code, 'code'))

            if response.status_code == 200:
                metrics.append((timestamp, 'api_gateway', 'availability', 1, 'boolean'))
            else:
                metrics.append((timestamp, 'api_gateway', 'availability', 0, 'boolean'))

        except Exception as e:
            metrics.append((timestamp, 'api_gateway', 'availability', 0, 'boolean'))

        # MLX Server metrics
        try:
            start_time = time.time()
            response = requests.get('http://localhost:8001/health', timeout=10)
            response_time = time.time() - start_time

            metrics.append((timestamp, 'mlx_server', 'response_time', response_time, 'seconds'))
            metrics.append((timestamp, 'mlx_server', 'status_code', response.status_code, 'code'))

            if response.status_code == 200:
                metrics.append((timestamp, 'mlx_server', 'availability', 1, 'boolean'))
            else:
                metrics.append((timestamp, 'mlx_server', 'availability', 0, 'boolean'))

        except Exception as e:
            metrics.append((timestamp, 'mlx_server', 'availability', 0, 'boolean'))

        # Database metrics
        try:
            result = subprocess.run(
                ['docker-compose', 'exec', '-T', 'postgres', 'pg_isready', '-U', 'freedom', '-d', 'freedom_kb'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                metrics.append((timestamp, 'database', 'availability', 1, 'boolean'))
            else:
                metrics.append((timestamp, 'database', 'availability', 0, 'boolean'))

        except Exception as e:
            metrics.append((timestamp, 'database', 'availability', 0, 'boolean'))

        # System metrics
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/Volumes/DATA/FREEDOM')

        metrics.extend([
            (timestamp, 'system', 'cpu_usage', cpu_usage, 'percent'),
            (timestamp, 'system', 'memory_usage', memory.percent, 'percent'),
            (timestamp, 'system', 'disk_usage', (disk.used / disk.total) * 100, 'percent'),
            (timestamp, 'system', 'memory_available', memory.available / (1024**3), 'GB'),
            (timestamp, 'system', 'disk_free', disk.free / (1024**3), 'GB')
        ])

        return metrics

    def collect_docker_metrics(self):
        """Collect Docker container metrics"""
        timestamp = datetime.now().isoformat()
        metrics = []

        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 'json'],
                capture_output=True, text=True, timeout=15
            )

            for line in result.stdout.strip().split('\n'):
                if line:
                    container_stats = json.loads(line)
                    container_name = container_stats['Name']

                    # Parse CPU percentage
                    cpu_str = container_stats['CPUPerc'].rstrip('%')
                    if cpu_str != '--':
                        metrics.append((timestamp, f'container_{container_name}', 'cpu_usage', float(cpu_str), 'percent'))

                    # Parse memory usage
                    mem_usage = container_stats['MemUsage']
                    if '/' in mem_usage:
                        used_str = mem_usage.split('/')[0].strip()
                        if 'MiB' in used_str:
                            used_mb = float(used_str.replace('MiB', ''))
                            metrics.append((timestamp, f'container_{container_name}', 'memory_usage', used_mb, 'MB'))
                        elif 'GiB' in used_str:
                            used_gb = float(used_str.replace('GiB', ''))
                            metrics.append((timestamp, f'container_{container_name}', 'memory_usage', used_gb * 1024, 'MB'))

        except Exception as e:
            print(f"Error collecting Docker metrics: {e}")

        return metrics

    def store_metrics(self, metrics):
        """Store metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.executemany(
            'INSERT OR REPLACE INTO metrics VALUES (?, ?, ?, ?, ?)',
            metrics
        )

        conn.commit()
        conn.close()

    def collect_and_store(self):
        """Main collection method"""
        print(f"Collecting metrics at {datetime.now()}")

        service_metrics = self.collect_service_metrics()
        docker_metrics = self.collect_docker_metrics()

        all_metrics = service_metrics + docker_metrics
        self.store_metrics(all_metrics)

        print(f"Stored {len(all_metrics)} metrics")
        return len(all_metrics)

    def generate_report(self, hours=24):
        """Generate performance report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get metrics from last N hours
        cursor.execute('''
            SELECT service, metric_name, AVG(metric_value) as avg_value,
                   MIN(metric_value) as min_value, MAX(metric_value) as max_value,
                   COUNT(*) as sample_count
            FROM metrics
            WHERE datetime(timestamp) > datetime('now', '-{} hours')
            GROUP BY service, metric_name
            ORDER BY service, metric_name
        '''.format(hours))

        results = cursor.fetchall()
        conn.close()

        print(f"\n=== PERFORMANCE REPORT (Last {hours} hours) ===")
        current_service = None
        for row in results:
            service, metric, avg, min_val, max_val, count = row
            if service != current_service:
                print(f"\n{service.upper()}:")
                current_service = service
            print(f"  {metric}: avg={avg:.2f}, min={min_val:.2f}, max={max_val:.2f} (n={count})")

if __name__ == "__main__":
    collector = MetricsCollector()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'report':
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        collector.generate_report(hours)
    else:
        collector.collect_and_store()
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/metrics_collector.py
```

### Performance Alerts Configuration
```bash
# Create alerting system
cat > /Volumes/DATA/FREEDOM/scripts/alert_manager.py << 'EOF'
#!/usr/bin/env python3
"""
FREEDOM Platform Alert Manager
Monitors metrics and sends alerts for threshold violations
"""

import sqlite3
import json
import subprocess
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText

class AlertManager:
    def __init__(self):
        self.db_path = '/Volumes/DATA/FREEDOM/logs/metrics.db'
        self.alert_log = '/Volumes/DATA/FREEDOM/logs/alerts.log'
        self.config = self.load_alert_config()

    def load_alert_config(self):
        """Load alert thresholds and configuration"""
        return {
            'thresholds': {
                'api_gateway_response_time': 5.0,  # seconds
                'mlx_server_response_time': 10.0,  # seconds
                'system_cpu_usage': 80.0,          # percent
                'system_memory_usage': 85.0,       # percent
                'system_disk_usage': 90.0,         # percent
                'service_availability': 0.95       # 95% uptime
            },
            'notification': {
                'methods': ['log', 'console', 'macos'],  # Available: log, console, email, macos
                'email': {
                    'enabled': False,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'recipients': []
                }
            }
        }

    def check_thresholds(self, minutes=15):
        """Check metrics against thresholds for recent period"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent metrics
        cursor.execute('''
            SELECT service, metric_name, AVG(metric_value) as avg_value
            FROM metrics
            WHERE datetime(timestamp) > datetime('now', '-{} minutes')
            GROUP BY service, metric_name
        '''.format(minutes))

        results = cursor.fetchall()
        conn.close()

        alerts = []

        for service, metric, avg_value in results:
            threshold_key = f"{service}_{metric}"
            threshold = self.config['thresholds'].get(threshold_key)

            if threshold is not None:
                if metric == 'availability':
                    if avg_value < threshold:
                        alerts.append({
                            'severity': 'CRITICAL',
                            'service': service,
                            'metric': metric,
                            'value': avg_value,
                            'threshold': threshold,
                            'message': f"{service} availability ({avg_value:.2%}) below threshold ({threshold:.2%})"
                        })
                else:
                    if avg_value > threshold:
                        severity = 'CRITICAL' if metric == 'availability' else 'WARNING'
                        alerts.append({
                            'severity': severity,
                            'service': service,
                            'metric': metric,
                            'value': avg_value,
                            'threshold': threshold,
                            'message': f"{service} {metric} ({avg_value:.2f}) exceeds threshold ({threshold})"
                        })

        return alerts

    def send_alert(self, alert):
        """Send alert using configured methods"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        alert_message = f"[{timestamp}] {alert['severity']}: {alert['message']}"

        methods = self.config['notification']['methods']

        # Log to file
        if 'log' in methods:
            with open(self.alert_log, 'a') as f:
                f.write(f"{alert_message}\n")

        # Console output
        if 'console' in methods:
            print(alert_message)

        # macOS notification
        if 'macos' in methods:
            try:
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{alert["message"]}" with title "FREEDOM Alert - {alert["severity"]}"'
                ], check=False)
            except Exception as e:
                print(f"Failed to send macOS notification: {e}")

        # Email notification
        if 'email' in methods and self.config['notification']['email']['enabled']:
            self.send_email_alert(alert_message)

    def send_email_alert(self, message):
        """Send email alert"""
        try:
            email_config = self.config['notification']['email']

            msg = MIMEText(message)
            msg['Subject'] = 'FREEDOM Platform Alert'
            msg['From'] = email_config['username']

            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])

            for recipient in email_config['recipients']:
                msg['To'] = recipient
                server.send_message(msg)

            server.quit()
            print("Email alert sent successfully")

        except Exception as e:
            print(f"Failed to send email alert: {e}")

    def run_alert_check(self):
        """Main alert checking method"""
        alerts = self.check_thresholds()

        if alerts:
            print(f"Found {len(alerts)} alerts")
            for alert in alerts:
                self.send_alert(alert)
        else:
            print("No alerts triggered")

        return len(alerts)

if __name__ == "__main__":
    manager = AlertManager()
    manager.run_alert_check()
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/alert_manager.py
```

---

## Log Analysis and Troubleshooting

### Centralized Log Analysis
```bash
# Create log analysis script
cat > /Volumes/DATA/FREEDOM/scripts/log_analyzer.py << 'EOF'
#!/usr/bin/env python3
"""
FREEDOM Platform Log Analyzer
Centralized log analysis and error detection
"""

import re
import json
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class LogAnalyzer:
    def __init__(self):
        self.error_patterns = {
            'connection_error': r'connection.*(?:refused|timeout|failed)',
            'memory_error': r'(?:out of memory|memory error|oom)',
            'database_error': r'(?:database|postgres|sql).*(?:error|failed)',
            'mlx_error': r'(?:mlx|model).*(?:error|failed|timeout)',
            'api_error': r'(?:api|http).*(?:error|failed|500|502|503|504)',
            'docker_error': r'docker.*(?:error|failed|exit)'
        }

        self.warning_patterns = {
            'slow_response': r'response.*time.*(?:slow|high|\d+\.?\d*s)',
            'high_memory': r'memory.*(?:high|usage|pressure)',
            'disk_space': r'disk.*(?:space|full|low)',
            'retry': r'retrying|retry|attempt'
        }

    def get_docker_logs(self, service=None, since='1h'):
        """Get logs from Docker containers"""
        try:
            cmd = ['docker-compose', 'logs', '--since', since]
            if service:
                cmd.append(service)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.stdout
        except Exception as e:
            print(f"Error getting Docker logs: {e}")
            return ""

    def analyze_logs(self, logs, pattern_dict):
        """Analyze logs for patterns"""
        findings = defaultdict(list)

        for line in logs.split('\n'):
            if not line.strip():
                continue

            # Extract timestamp
            timestamp_match = re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', line)
            timestamp = timestamp_match.group() if timestamp_match else 'unknown'

            # Check against patterns
            for pattern_name, pattern in pattern_dict.items():
                if re.search(pattern, line, re.IGNORECASE):
                    findings[pattern_name].append({
                        'timestamp': timestamp,
                        'line': line.strip(),
                        'service': self.extract_service_name(line)
                    })

        return findings

    def extract_service_name(self, log_line):
        """Extract service name from log line"""
        service_match = re.search(r'(\w+)_\d+\s*\|', log_line)
        if service_match:
            return service_match.group(1)
        return 'unknown'

    def generate_summary_report(self, hours=24):
        """Generate comprehensive log analysis report"""
        print(f"=== LOG ANALYSIS REPORT (Last {hours} hours) ===")
        print(f"Generated: {datetime.now()}")
        print()

        # Get logs
        logs = self.get_docker_logs(since=f'{hours}h')

        if not logs:
            print("No logs found")
            return

        # Analyze errors
        errors = self.analyze_logs(logs, self.error_patterns)
        warnings = self.analyze_logs(logs, self.warning_patterns)

        # Error summary
        print("=== ERROR SUMMARY ===")
        if errors:
            for error_type, occurrences in errors.items():
                print(f"{error_type}: {len(occurrences)} occurrences")
                services = Counter(occ['service'] for occ in occurrences)
                for service, count in services.most_common(3):
                    print(f"  - {service}: {count}")
        else:
            print("✅ No errors found")
        print()

        # Warning summary
        print("=== WARNING SUMMARY ===")
        if warnings:
            for warning_type, occurrences in warnings.items():
                print(f"{warning_type}: {len(occurrences)} occurrences")
        else:
            print("✅ No warnings found")
        print()

        # Service-specific analysis
        print("=== SERVICE-SPECIFIC ANALYSIS ===")
        services = ['api', 'mlx-server', 'kb-service', 'postgres', 'castle-gui']

        for service in services:
            service_logs = self.get_docker_logs(service=service, since=f'{hours}h')
            if service_logs:
                error_count = sum(len(occurrences) for occurrences in
                                self.analyze_logs(service_logs, self.error_patterns).values())
                warning_count = sum(len(occurrences) for occurrences in
                                  self.analyze_logs(service_logs, self.warning_patterns).values())

                status = "✅ HEALTHY" if error_count == 0 else f"❌ {error_count} ERRORS"
                if warning_count > 0:
                    status += f" ({warning_count} warnings)"

                print(f"{service}: {status}")
        print()

        # Recent critical errors
        print("=== RECENT CRITICAL ERRORS ===")
        critical_errors = []
        for error_type, occurrences in errors.items():
            if error_type in ['connection_error', 'memory_error', 'database_error']:
                critical_errors.extend(occurrences[-3:])  # Last 3 of each type

        if critical_errors:
            for error in sorted(critical_errors, key=lambda x: x['timestamp'])[-5:]:
                print(f"[{error['timestamp']}] {error['service']}: {error['line'][:100]}...")
        else:
            print("✅ No critical errors found")

    def troubleshoot_service(self, service_name):
        """Focused troubleshooting for specific service"""
        print(f"=== TROUBLESHOOTING: {service_name.upper()} ===")

        # Get recent logs for service
        logs = self.get_docker_logs(service=service_name, since='2h')

        if not logs:
            print(f"❌ No logs found for {service_name}")
            return

        # Analyze errors and warnings
        errors = self.analyze_logs(logs, self.error_patterns)
        warnings = self.analyze_logs(logs, self.warning_patterns)

        # Service status
        try:
            result = subprocess.run(['docker-compose', 'ps', service_name],
                                  capture_output=True, text=True)
            print(f"Container Status:\n{result.stdout}")
        except Exception as e:
            print(f"Error checking container status: {e}")

        # Recent errors
        if errors:
            print("\nRecent Errors:")
            for error_type, occurrences in errors.items():
                if occurrences:
                    latest = occurrences[-1]
                    print(f"  {error_type}: {latest['line'][:100]}...")

        # Suggested actions
        print(f"\nSuggested Actions for {service_name}:")
        if service_name == 'mlx-server':
            print("  1. Check model loading: docker-compose logs mlx-server | grep 'model'")
            print("  2. Verify model files: ls -la models/")
            print("  3. Check memory usage: docker stats mlx-server")
            print("  4. Restart if needed: docker-compose restart mlx-server")
        elif service_name == 'postgres':
            print("  1. Check connectivity: docker-compose exec postgres pg_isready")
            print("  2. Check disk space: df -h")
            print("  3. Review recent queries: docker-compose logs postgres | tail -20")
            print("  4. Check for locks: docker-compose exec postgres psql -c 'SELECT * FROM pg_locks;'")
        elif service_name == 'api':
            print("  1. Check health endpoint: curl http://localhost:8080/health")
            print("  2. Verify environment vars: docker-compose exec api env | grep -E '(API_KEY|URL)'")
            print("  3. Check upstream services: make health")
            print("  4. Review rate limiting: docker-compose logs api | grep -i rate")

if __name__ == "__main__":
    analyzer = LogAnalyzer()

    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'troubleshoot' and len(sys.argv) > 2:
            analyzer.troubleshoot_service(sys.argv[2])
        elif sys.argv[1] == 'report':
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            analyzer.generate_summary_report(hours)
    else:
        analyzer.generate_summary_report()
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/log_analyzer.py
```

### Common Troubleshooting Procedures

#### Service Restart Procedures
```bash
# Individual service restart
restart_service() {
    local service_name="$1"
    echo "Restarting $service_name..."

    # Graceful restart
    docker-compose restart "$service_name"

    # Wait for health check
    sleep 30

    # Verify restart
    if docker-compose ps "$service_name" | grep -q "Up"; then
        echo "✅ $service_name restarted successfully"

        # Service-specific health checks
        case "$service_name" in
            "api")
                curl -f http://localhost:8080/health || echo "❌ API health check failed"
                ;;
            "mlx-server")
                curl -f http://localhost:8001/health || echo "❌ MLX health check failed"
                ;;
            "postgres")
                docker-compose exec postgres pg_isready -U freedom -d freedom_kb || echo "❌ DB health check failed"
                ;;
        esac
    else
        echo "❌ $service_name restart failed"
        docker-compose logs --tail=20 "$service_name"
    fi
}

# Complete system restart
full_system_restart() {
    echo "Performing full system restart..."

    # Graceful shutdown
    docker-compose down
    sleep 10

    # Start all services
    docker-compose up -d

    # Wait for all services
    sleep 60

    # Comprehensive health check
    make health
}
```

#### Database Recovery Procedures
```bash
# Database connection issues
troubleshoot_database() {
    echo "=== DATABASE TROUBLESHOOTING ==="

    # Check container status
    echo "1. Container Status:"
    docker-compose ps postgres

    # Check connectivity
    echo "2. Connection Test:"
    docker-compose exec postgres pg_isready -U freedom -d freedom_kb

    # Check database size
    echo "3. Database Size:"
    docker-compose exec postgres psql -U freedom -d freedom_kb -c "
        SELECT pg_size_pretty(pg_database_size('freedom_kb')) as db_size;
    "

    # Check active connections
    echo "4. Active Connections:"
    docker-compose exec postgres psql -U freedom -d freedom_kb -c "
        SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';
    "

    # Check for locks
    echo "5. Current Locks:"
    docker-compose exec postgres psql -U freedom -d freedom_kb -c "
        SELECT count(*) as locks FROM pg_locks;
    "

    # Recommended actions
    echo "6. Recommended Actions:"
    echo "   - If connection fails: docker-compose restart postgres"
    echo "   - If locks detected: docker-compose exec postgres psql -c 'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = \"idle in transaction\";'"
    echo "   - For corruption: Restore from backup (see rollback runbook)"
}
```

#### MLX Performance Issues
```bash
# MLX troubleshooting
troubleshoot_mlx() {
    echo "=== MLX SERVER TROUBLESHOOTING ==="

    # Check model loading
    echo "1. Model Loading Status:"
    docker-compose logs mlx-server | grep -i "model" | tail -5

    # Check memory usage
    echo "2. Memory Usage:"
    docker stats mlx-server --no-stream

    # Test inference
    echo "3. Inference Test:"
    python -c "
import time, requests
try:
    start = time.time()
    response = requests.post('http://localhost:8001/v1/chat/completions',
        json={'messages': [{'role': 'user', 'content': 'test'}], 'max_tokens': 5},
        timeout=30)
    end = time.time()
    print(f'Status: {response.status_code}, Time: {end-start:.2f}s')
except Exception as e:
    print(f'Error: {e}')
"

    # Check GPU availability
    echo "4. GPU Status:"
    docker-compose exec mlx-server python -c "
import mlx.core as mx
print(f'Metal available: {mx.metal.is_available()}')
if mx.metal.is_available():
    print(f'Memory info: {mx.metal.get_memory_info()}')
"

    # Recommended actions
    echo "5. Recommended Actions:"
    echo "   - If slow: Check model quantization and memory settings"
    echo "   - If failing: Verify model files exist and are complete"
    echo "   - If OOM: Reduce model size or increase Docker memory"
    echo "   - If Metal issues: Check Apple Silicon compatibility"
}
```

---

## Scaling and Capacity Planning

### Horizontal Scaling Procedures
```bash
# Scale specific services
scale_service() {
    local service_name="$1"
    local replicas="$2"

    echo "Scaling $service_name to $replicas replicas..."

    # Update docker-compose for scaling
    docker-compose up -d --scale "$service_name=$replicas" "$service_name"

    # Verify scaling
    docker-compose ps "$service_name"

    # Load balancer configuration (if applicable)
    if [ "$service_name" = "api" ]; then
        echo "Note: Update load balancer configuration for multiple API instances"
    fi
}

# Auto-scaling based on load
auto_scale_check() {
    echo "=== AUTO-SCALING CHECK ==="

    # Check CPU usage
    cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" api | sed 's/%//')
    memory_usage=$(docker stats --no-stream --format "{{.MemPerc}}" api | sed 's/%//')

    echo "Current API resource usage:"
    echo "  CPU: ${cpu_usage}%"
    echo "  Memory: ${memory_usage}%"

    # Scaling decisions
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo "⚠️  High CPU usage detected - consider scaling up"
    fi

    if (( $(echo "$memory_usage > 80" | bc -l) )); then
        echo "⚠️  High memory usage detected - consider scaling up"
    fi

    # Check response times
    python -c "
import time, requests
times = []
for i in range(5):
    start = time.time()
    try:
        response = requests.get('http://localhost:8080/health', timeout=10)
        times.append(time.time() - start)
    except:
        times.append(10)  # Timeout penalty

avg_time = sum(times) / len(times)
print(f'Average response time: {avg_time:.2f}s')
if avg_time > 2:
    print('⚠️  High response times detected - consider scaling up')
"
}
```

### Capacity Planning
```bash
# Generate capacity planning report
capacity_planning_report() {
    echo "=== CAPACITY PLANNING REPORT ==="
    echo "Date: $(date)"
    echo ""

    # Historical performance data
    echo "Historical Performance (Last 7 days):"
    python /Volumes/DATA/FREEDOM/scripts/metrics_collector.py report 168  # 7 days
    echo ""

    # Resource utilization trends
    echo "Resource Utilization Trends:"

    # Disk usage trend
    echo "Disk Usage:"
    df -h /Volumes/DATA/FREEDOM | tail -1
    du -sh /Volumes/DATA/FREEDOM/logs/
    du -sh /Volumes/DATA/FREEDOM/models/
    echo ""

    # Memory trends
    echo "Memory Utilization:"
    free -h 2>/dev/null || vm_stat | head -5
    echo ""

    # Database growth
    echo "Database Growth:"
    docker-compose exec postgres psql -U freedom -d freedom_kb -c "
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as size,
            pg_stat_get_tuples_inserted(c.oid) as inserts,
            pg_stat_get_tuples_updated(c.oid) as updates
        FROM pg_tables pt
        JOIN pg_class c ON c.relname = pt.tablename
        WHERE schemaname = 'public'
        ORDER BY pg_relation_size(schemaname||'.'||tablename) DESC;
    "
    echo ""

    # Recommendations
    echo "Capacity Recommendations:"

    # Check disk space
    disk_usage=$(df -h /Volumes/DATA/FREEDOM | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 80 ]; then
        echo "  🔴 URGENT: Disk usage at ${disk_usage}% - cleanup or expand storage"
    elif [ "$disk_usage" -gt 70 ]; then
        echo "  🟡 WARNING: Disk usage at ${disk_usage}% - monitor closely"
    else
        echo "  🟢 Disk usage at ${disk_usage}% - healthy"
    fi

    # Check model storage
    model_size=$(du -sm /Volumes/DATA/FREEDOM/models/ | cut -f1)
    echo "  Model storage: ${model_size}MB"
    if [ "$model_size" -gt 50000 ]; then  # 50GB
        echo "    Consider model cleanup or compression"
    fi

    # Performance recommendations
    echo ""
    echo "Performance Optimization Opportunities:"
    echo "  - Review model quantization for memory efficiency"
    echo "  - Implement connection pooling for database"
    echo "  - Consider CDN for static assets"
    echo "  - Implement horizontal scaling for API layer"
}
```

---

## Backup and Recovery Operations

### Automated Backup Procedures
```bash
# Create comprehensive backup script
cat > /Volumes/DATA/FREEDOM/scripts/backup_system.py << 'EOF'
#!/usr/bin/env python3
"""
FREEDOM Platform Backup System
Automated backup of critical system components
"""

import os
import subprocess
import datetime
import shutil
import json
import tarfile

class BackupManager:
    def __init__(self):
        self.backup_root = '/Volumes/DATA/FREEDOM/backups'
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_dir = f"{self.backup_root}/{self.timestamp}"
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_database(self):
        """Backup PostgreSQL database"""
        print("Backing up database...")

        db_backup_path = f"{self.backup_dir}/database_backup.sql"

        try:
            subprocess.run([
                'docker-compose', 'exec', '-T', 'postgres',
                'pg_dump', '-U', 'freedom', 'freedom_kb'
            ], stdout=open(db_backup_path, 'w'), check=True)

            # Verify backup
            if os.path.getsize(db_backup_path) > 1000:  # At least 1KB
                print(f"✅ Database backup completed: {db_backup_path}")
                return True
            else:
                print("❌ Database backup appears empty")
                return False

        except Exception as e:
            print(f"❌ Database backup failed: {e}")
            return False

    def backup_configurations(self):
        """Backup configuration files"""
        print("Backing up configurations...")

        config_files = [
            'docker-compose.yml',
            '.env',
            'Makefile'
        ]

        config_backup_dir = f"{self.backup_dir}/configurations"
        os.makedirs(config_backup_dir, exist_ok=True)

        for config_file in config_files:
            if os.path.exists(config_file):
                shutil.copy2(config_file, config_backup_dir)
                print(f"  ✅ Backed up {config_file}")

        # Backup entire config directory if it exists
        if os.path.exists('config'):
            shutil.copytree('config', f"{config_backup_dir}/config")
            print("  ✅ Backed up config directory")

        return True

    def backup_logs(self):
        """Backup critical logs"""
        print("Backing up logs...")

        log_backup_dir = f"{self.backup_dir}/logs"
        os.makedirs(log_backup_dir, exist_ok=True)

        # Backup recent logs
        if os.path.exists('logs'):
            for log_file in os.listdir('logs'):
                if log_file.endswith(('.log', '.json')) and os.path.getsize(f"logs/{log_file}") > 0:
                    shutil.copy2(f"logs/{log_file}", log_backup_dir)

        print(f"  ✅ Backed up logs to {log_backup_dir}")
        return True

    def backup_scripts(self):
        """Backup custom scripts"""
        print("Backing up scripts...")

        if os.path.exists('scripts'):
            scripts_backup_dir = f"{self.backup_dir}/scripts"
            shutil.copytree('scripts', scripts_backup_dir)
            print(f"  ✅ Backed up scripts to {scripts_backup_dir}")

        return True

    def create_backup_manifest(self):
        """Create backup manifest with metadata"""
        manifest = {
            'backup_timestamp': self.timestamp,
            'backup_date': datetime.datetime.now().isoformat(),
            'platform_version': self.get_platform_version(),
            'services_status': self.get_services_status(),
            'backup_contents': self.get_backup_contents(),
            'backup_size': self.get_backup_size()
        }

        manifest_path = f"{self.backup_dir}/backup_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print(f"✅ Backup manifest created: {manifest_path}")
        return manifest

    def get_platform_version(self):
        """Get current platform version"""
        try:
            result = subprocess.run(['git', 'describe', '--tags', '--always'],
                                  capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return 'unknown'

    def get_services_status(self):
        """Get current services status"""
        try:
            result = subprocess.run(['docker-compose', 'ps', '--format', 'json'],
                                  capture_output=True, text=True)
            return json.loads(result.stdout) if result.stdout else []
        except:
            return []

    def get_backup_contents(self):
        """List backup contents"""
        contents = []
        for root, dirs, files in os.walk(self.backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.backup_dir)
                contents.append({
                    'file': relative_path,
                    'size': os.path.getsize(file_path)
                })
        return contents

    def get_backup_size(self):
        """Calculate total backup size"""
        total_size = 0
        for root, dirs, files in os.walk(self.backup_dir):
            for file in files:
                total_size += os.path.getsize(os.path.join(root, file))
        return total_size

    def compress_backup(self):
        """Compress backup directory"""
        print("Compressing backup...")

        archive_path = f"{self.backup_root}/freedom_backup_{self.timestamp}.tar.gz"

        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(self.backup_dir, arcname=f"freedom_backup_{self.timestamp}")

        # Remove uncompressed backup
        shutil.rmtree(self.backup_dir)

        print(f"✅ Backup compressed: {archive_path}")
        return archive_path

    def cleanup_old_backups(self, keep_days=7):
        """Remove backups older than specified days"""
        print(f"Cleaning up backups older than {keep_days} days...")

        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=keep_days)

        for item in os.listdir(self.backup_root):
            item_path = os.path.join(self.backup_root, item)
            if os.path.isfile(item_path) and item.startswith('freedom_backup_'):
                # Extract timestamp from filename
                try:
                    timestamp_str = item.replace('freedom_backup_', '').replace('.tar.gz', '')
                    item_date = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')

                    if item_date < cutoff_date:
                        os.remove(item_path)
                        print(f"  🗑️  Removed old backup: {item}")
                except:
                    continue

    def run_full_backup(self):
        """Execute complete backup procedure"""
        print(f"=== FREEDOM PLATFORM BACKUP STARTED ===")
        print(f"Timestamp: {self.timestamp}")
        print(f"Backup directory: {self.backup_dir}")
        print()

        results = {
            'database': self.backup_database(),
            'configurations': self.backup_configurations(),
            'logs': self.backup_logs(),
            'scripts': self.backup_scripts()
        }

        # Create manifest
        manifest = self.create_backup_manifest()

        # Compress backup
        archive_path = self.compress_backup()

        # Cleanup old backups
        self.cleanup_old_backups()

        print()
        print(f"=== BACKUP COMPLETED ===")
        print(f"Archive: {archive_path}")
        print(f"Size: {manifest['backup_size'] / (1024*1024):.1f} MB")
        print(f"Success rate: {sum(results.values())}/{len(results)} components")

        if all(results.values()):
            print("✅ All components backed up successfully")
            return True
        else:
            print("⚠️  Some backup components failed")
            return False

if __name__ == "__main__":
    # Change to FREEDOM directory
    os.chdir('/Volumes/DATA/FREEDOM')

    backup_manager = BackupManager()
    backup_manager.run_full_backup()
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/backup_system.py
```

### Recovery Procedures
```bash
# Create recovery script
cat > /Volumes/DATA/FREEDOM/scripts/recovery_system.py << 'EOF'
#!/usr/bin/env python3
"""
FREEDOM Platform Recovery System
Restore system from backup archives
"""

import os
import subprocess
import json
import tarfile
import shutil
from datetime import datetime

class RecoveryManager:
    def __init__(self):
        self.backup_root = '/Volumes/DATA/FREEDOM/backups'
        self.restore_dir = '/tmp/freedom_restore'

    def list_available_backups(self):
        """List available backup archives"""
        backups = []

        if not os.path.exists(self.backup_root):
            return backups

        for item in os.listdir(self.backup_root):
            if item.startswith('freedom_backup_') and item.endswith('.tar.gz'):
                backup_path = os.path.join(self.backup_root, item)
                timestamp_str = item.replace('freedom_backup_', '').replace('.tar.gz', '')

                try:
                    backup_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    size_mb = os.path.getsize(backup_path) / (1024*1024)

                    backups.append({
                        'filename': item,
                        'path': backup_path,
                        'timestamp': timestamp_str,
                        'date': backup_date,
                        'size_mb': size_mb
                    })
                except:
                    continue

        return sorted(backups, key=lambda x: x['date'], reverse=True)

    def extract_backup(self, backup_path):
        """Extract backup archive"""
        print(f"Extracting backup: {backup_path}")

        # Clean restore directory
        if os.path.exists(self.restore_dir):
            shutil.rmtree(self.restore_dir)
        os.makedirs(self.restore_dir)

        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(self.restore_dir)

            # Find extracted directory
            extracted_dirs = [d for d in os.listdir(self.restore_dir)
                            if os.path.isdir(os.path.join(self.restore_dir, d))]

            if extracted_dirs:
                extracted_path = os.path.join(self.restore_dir, extracted_dirs[0])
                print(f"✅ Backup extracted to: {extracted_path}")
                return extracted_path
            else:
                print("❌ No directory found in backup")
                return None

        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            return None

    def load_backup_manifest(self, backup_dir):
        """Load backup manifest"""
        manifest_path = os.path.join(backup_dir, 'backup_manifest.json')

        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                return json.load(f)
        return None

    def restore_database(self, backup_dir):
        """Restore database from backup"""
        print("Restoring database...")

        db_backup_path = os.path.join(backup_dir, 'database_backup.sql')

        if not os.path.exists(db_backup_path):
            print("❌ Database backup not found")
            return False

        try:
            # Ensure postgres is running
            subprocess.run(['docker-compose', 'up', '-d', 'postgres'], check=True)

            # Wait for postgres
            import time
            time.sleep(10)

            # Restore database
            with open(db_backup_path, 'r') as f:
                subprocess.run([
                    'docker-compose', 'exec', '-T', 'postgres',
                    'psql', '-U', 'freedom', '-d', 'freedom_kb'
                ], stdin=f, check=True)

            print("✅ Database restored successfully")
            return True

        except Exception as e:
            print(f"❌ Database restore failed: {e}")
            return False

    def restore_configurations(self, backup_dir):
        """Restore configuration files"""
        print("Restoring configurations...")

        config_backup_dir = os.path.join(backup_dir, 'configurations')

        if not os.path.exists(config_backup_dir):
            print("❌ Configuration backup not found")
            return False

        try:
            # Restore main config files
            for item in os.listdir(config_backup_dir):
                src_path = os.path.join(config_backup_dir, item)

                if os.path.isfile(src_path):
                    shutil.copy2(src_path, '.')
                    print(f"  ✅ Restored {item}")
                elif os.path.isdir(src_path) and item == 'config':
                    if os.path.exists('config'):
                        shutil.rmtree('config')
                    shutil.copytree(src_path, 'config')
                    print(f"  ✅ Restored config directory")

            print("✅ Configurations restored successfully")
            return True

        except Exception as e:
            print(f"❌ Configuration restore failed: {e}")
            return False

    def restore_scripts(self, backup_dir):
        """Restore custom scripts"""
        print("Restoring scripts...")

        scripts_backup_dir = os.path.join(backup_dir, 'scripts')

        if not os.path.exists(scripts_backup_dir):
            print("⚠️  Scripts backup not found (this may be normal)")
            return True

        try:
            if os.path.exists('scripts'):
                shutil.rmtree('scripts')
            shutil.copytree(scripts_backup_dir, 'scripts')

            # Make scripts executable
            for root, dirs, files in os.walk('scripts'):
                for file in files:
                    if file.endswith('.py') or file.endswith('.sh'):
                        file_path = os.path.join(root, file)
                        os.chmod(file_path, 0o755)

            print("✅ Scripts restored successfully")
            return True

        except Exception as e:
            print(f"❌ Scripts restore failed: {e}")
            return False

    def run_recovery(self, backup_filename=None):
        """Execute complete recovery procedure"""
        print("=== FREEDOM PLATFORM RECOVERY STARTED ===")

        # Change to FREEDOM directory
        os.chdir('/Volumes/DATA/FREEDOM')

        # List available backups
        backups = self.list_available_backups()

        if not backups:
            print("❌ No backups found")
            return False

        # Select backup
        if backup_filename:
            selected_backup = next((b for b in backups if b['filename'] == backup_filename), None)
            if not selected_backup:
                print(f"❌ Backup not found: {backup_filename}")
                return False
        else:
            print("Available backups:")
            for i, backup in enumerate(backups[:5]):  # Show last 5
                print(f"  {i+1}. {backup['filename']} ({backup['size_mb']:.1f} MB) - {backup['date']}")

            try:
                choice = int(input("Select backup (1-5): ")) - 1
                selected_backup = backups[choice]
            except (ValueError, IndexError):
                print("❌ Invalid selection")
                return False

        print(f"Selected backup: {selected_backup['filename']}")

        # Stop services
        print("Stopping services...")
        subprocess.run(['docker-compose', 'down'])

        # Extract backup
        backup_dir = self.extract_backup(selected_backup['path'])
        if not backup_dir:
            return False

        # Load manifest
        manifest = self.load_backup_manifest(backup_dir)
        if manifest:
            print(f"Backup from: {manifest['backup_date']}")
            print(f"Platform version: {manifest['platform_version']}")

        # Restore components
        results = {
            'configurations': self.restore_configurations(backup_dir),
            'database': self.restore_database(backup_dir),
            'scripts': self.restore_scripts(backup_dir)
        }

        # Start services
        print("Starting services...")
        subprocess.run(['docker-compose', 'up', '-d'])

        # Cleanup
        shutil.rmtree(self.restore_dir)

        print()
        print("=== RECOVERY COMPLETED ===")
        print(f"Success rate: {sum(results.values())}/{len(results)} components")

        if all(results.values()):
            print("✅ All components restored successfully")
            print("🔍 Verify system health with: make health")
            return True
        else:
            print("⚠️  Some recovery components failed")
            return False

if __name__ == "__main__":
    import sys

    recovery_manager = RecoveryManager()

    backup_file = sys.argv[1] if len(sys.argv) > 1 else None
    recovery_manager.run_recovery(backup_file)
EOF

chmod +x /Volumes/DATA/FREEDOM/scripts/recovery_system.py
```

---

## Operational Automation

### Cron Job Setup
```bash
# Setup operational automation
setup_operational_automation() {
    echo "Setting up operational automation..."

    # Create cron jobs file
    cat > /tmp/freedom_operations_cron << EOF
# FREEDOM Platform Operational Automation

# Metrics collection every 5 minutes
*/5 * * * * cd /Volumes/DATA/FREEDOM && python scripts/metrics_collector.py

# Alert checking every 10 minutes
*/10 * * * * cd /Volumes/DATA/FREEDOM && python scripts/alert_manager.py

# Daily health check at 8:00 AM
0 8 * * * cd /Volumes/DATA/FREEDOM && bash scripts/daily_health_check.sh

# Daily backup at 2:00 AM
0 2 * * * cd /Volumes/DATA/FREEDOM && python scripts/backup_system.py

# Weekly log analysis on Sundays at 10:00 AM
0 10 * * 0 cd /Volumes/DATA/FREEDOM && python scripts/log_analyzer.py report 168

# Monthly capacity planning on 1st of month at 9:00 AM
0 9 1 * * cd /Volumes/DATA/FREEDOM && bash scripts/capacity_planning.sh

# Cleanup old logs weekly
0 3 * * 0 find /Volumes/DATA/FREEDOM/logs -name "*.log" -mtime +30 -delete

# Docker cleanup weekly
0 4 * * 0 docker system prune -f --filter "until=168h"
EOF

    # Install cron jobs
    crontab /tmp/freedom_operations_cron
    rm /tmp/freedom_operations_cron

    echo "✅ Operational automation configured"
    echo "Current cron jobs:"
    crontab -l | grep -i freedom
}
```

### Quick Operations Reference
```bash
# Create operations cheat sheet
cat > /Volumes/DATA/FREEDOM/docs/runbooks/quick-reference.md << 'EOF'
# FREEDOM Platform - Quick Operations Reference

## Emergency Commands
```bash
# Full system restart
docker-compose down && docker-compose up -d

# Emergency stop
docker-compose down

# Health check
make health

# Check all service logs
docker-compose logs -f

# Individual service restart
docker-compose restart [service-name]
```

## Daily Operations
```bash
# Morning health check
python scripts/daily_health_check.py

# Check resource usage
docker stats --no-stream

# Review recent errors
docker-compose logs --since=24h | grep -i error

# Performance test
python scripts/metrics_collector.py && python scripts/metrics_collector.py report 1
```

## Troubleshooting
```bash
# Service-specific troubleshooting
python scripts/log_analyzer.py troubleshoot [service-name]

# Database issues
python scripts/troubleshoot_database.py

# MLX performance issues
python scripts/troubleshoot_mlx.py

# Check disk space
df -h /Volumes/DATA/FREEDOM
```

## Backup & Recovery
```bash
# Create backup
python scripts/backup_system.py

# List available backups
python scripts/recovery_system.py

# Restore from backup
python scripts/recovery_system.py [backup-filename]

# Emergency rollback
git checkout graveyard/pre-reset && docker-compose down && docker-compose up -d
```

## Monitoring
```bash
# Real-time dashboard
python scripts/monitoring_dashboard.py

# Generate performance report
python scripts/metrics_collector.py report 24

# Check alerts
python scripts/alert_manager.py

# Log analysis
python scripts/log_analyzer.py report 24
```
EOF
```

---

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create Cold Start Runbook with complete setup procedures", "status": "completed", "activeForm": "Creating Cold Start Runbook with complete setup procedures"}, {"content": "Create Rollback Runbook with graveyard/pre-reset procedures", "status": "completed", "activeForm": "Creating Rollback Runbook with graveyard/pre-reset procedures"}, {"content": "Create MLX Models Management runbook", "status": "completed", "activeForm": "Creating MLX Models Management runbook"}, {"content": "Create Operations Manual with health checks and monitoring", "status": "completed", "activeForm": "Creating Operations Manual with health checks and monitoring"}]