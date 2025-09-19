#!/usr/bin/env python3
"""
FREEDOM Platform - Metrics Collector
WORKSTREAM 7: Verification & Observability

Centralized metrics collection and analysis tool for FREEDOM platform.
Aggregates metrics from all services and provides operational insights.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class ServiceMetrics:
    """Service metrics snapshot"""
    service_name: str
    timestamp: str
    metrics_available: bool
    metrics_size: int
    response_time_ms: float
    key_metrics: Dict[str, Any]
    health_status: str
    error: Optional[str] = None

class FreedomMetricsCollector:
    """Centralized metrics collector for FREEDOM platform"""

    def __init__(self):
        self.config = {
            "api_gateway_url": "http://localhost:8080",
            "kb_service_url": "http://localhost:8000",
            "mlx_service_url": "http://localhost:8001",
            "timeout": 30
        }
        self.metrics_snapshots: List[ServiceMetrics] = []

    def parse_prometheus_metrics(self, metrics_text: str) -> Dict[str, Any]:
        """Parse Prometheus metrics format into structured data"""
        parsed_metrics = {}

        for line in metrics_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Simple parsing - split on first space
            parts = line.split(' ', 1)
            if len(parts) != 2:
                continue

            metric_name = parts[0]
            metric_value = parts[1]

            # Extract base metric name (before labels)
            base_name = metric_name.split('{')[0]

            try:
                value = float(metric_value)
                if base_name not in parsed_metrics:
                    parsed_metrics[base_name] = []
                parsed_metrics[base_name].append({
                    'full_name': metric_name,
                    'value': value
                })
            except ValueError:
                continue

        return parsed_metrics

    def collect_service_metrics(self, service_name: str, base_url: str) -> ServiceMetrics:
        """Collect metrics from a specific service"""
        start_time = time.time()

        try:
            # Get health status
            health_response = requests.get(
                f"{base_url}/health",
                timeout=self.config["timeout"]
            )
            health_status = "healthy" if health_response.status_code == 200 else "unhealthy"

            # Get metrics
            metrics_response = requests.get(
                f"{base_url}/metrics",
                timeout=self.config["timeout"]
            )

            response_time_ms = (time.time() - start_time) * 1000

            if metrics_response.status_code == 200:
                metrics_text = metrics_response.text
                parsed_metrics = self.parse_prometheus_metrics(metrics_text)

                # Extract key metrics based on service type
                key_metrics = self.extract_key_metrics(service_name, parsed_metrics)

                return ServiceMetrics(
                    service_name=service_name,
                    timestamp=datetime.utcnow().isoformat(),
                    metrics_available=True,
                    metrics_size=len(metrics_text),
                    response_time_ms=response_time_ms,
                    key_metrics=key_metrics,
                    health_status=health_status
                )
            else:
                return ServiceMetrics(
                    service_name=service_name,
                    timestamp=datetime.utcnow().isoformat(),
                    metrics_available=False,
                    metrics_size=0,
                    response_time_ms=response_time_ms,
                    key_metrics={},
                    health_status=health_status,
                    error=f"Metrics endpoint returned {metrics_response.status_code}"
                )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return ServiceMetrics(
                service_name=service_name,
                timestamp=datetime.utcnow().isoformat(),
                metrics_available=False,
                metrics_size=0,
                response_time_ms=response_time_ms,
                key_metrics={},
                health_status="unreachable",
                error=str(e)
            )

    def extract_key_metrics(self, service_name: str, parsed_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics specific to each service type"""
        key_metrics = {}

        if service_name == "api_gateway":
            # API Gateway specific metrics
            if "gateway_requests_total" in parsed_metrics:
                total_requests = sum(m['value'] for m in parsed_metrics["gateway_requests_total"])
                key_metrics["total_requests"] = total_requests

            if "gateway_request_duration_seconds" in parsed_metrics:
                # This would need more sophisticated percentile calculation
                key_metrics["request_duration_metrics_available"] = True

            if "gateway_active_connections" in parsed_metrics:
                active_connections = parsed_metrics["gateway_active_connections"][-1]['value'] if parsed_metrics["gateway_active_connections"] else 0
                key_metrics["active_connections"] = active_connections

            if "gateway_kb_requests_total" in parsed_metrics:
                kb_requests = sum(m['value'] for m in parsed_metrics["gateway_kb_requests_total"])
                key_metrics["kb_requests_total"] = kb_requests

            if "gateway_mlx_requests_total" in parsed_metrics:
                mlx_requests = sum(m['value'] for m in parsed_metrics["gateway_mlx_requests_total"])
                key_metrics["mlx_requests_total"] = mlx_requests

        elif service_name == "mlx_service":
            # MLX Service specific metrics
            if "mlx_inference_requests_total" in parsed_metrics:
                total_inferences = sum(m['value'] for m in parsed_metrics["mlx_inference_requests_total"])
                key_metrics["total_inferences"] = total_inferences

            if "mlx_active_requests" in parsed_metrics:
                active_requests = parsed_metrics["mlx_active_requests"][-1]['value'] if parsed_metrics["mlx_active_requests"] else 0
                key_metrics["active_requests"] = active_requests

            if "mlx_model_loaded" in parsed_metrics:
                model_loaded = parsed_metrics["mlx_model_loaded"][-1]['value'] if parsed_metrics["mlx_model_loaded"] else 0
                key_metrics["model_loaded"] = bool(model_loaded)

            if "mlx_inference_duration_seconds" in parsed_metrics:
                key_metrics["inference_duration_metrics_available"] = True

        # Common process metrics
        if "process_resident_memory_bytes" in parsed_metrics:
            memory_bytes = parsed_metrics["process_resident_memory_bytes"][-1]['value'] if parsed_metrics["process_resident_memory_bytes"] else 0
            key_metrics["memory_usage_mb"] = memory_bytes / (1024 * 1024)

        if "process_cpu_seconds_total" in parsed_metrics:
            cpu_seconds = parsed_metrics["process_cpu_seconds_total"][-1]['value'] if parsed_metrics["process_cpu_seconds_total"] else 0
            key_metrics["cpu_seconds_total"] = cpu_seconds

        return key_metrics

    def collect_all_metrics(self) -> List[ServiceMetrics]:
        """Collect metrics from all FREEDOM services"""
        services = [
            ("api_gateway", self.config["api_gateway_url"]),
            ("mlx_service", self.config["mlx_service_url"]),
        ]

        snapshots = []

        for service_name, base_url in services:
            print(f"📊 Collecting metrics from {service_name}...")
            snapshot = self.collect_service_metrics(service_name, base_url)
            snapshots.append(snapshot)

            status = "✅" if snapshot.metrics_available else "❌"
            print(f"   {status} {service_name}: {snapshot.health_status} ({snapshot.response_time_ms:.1f}ms)")

            if snapshot.error:
                print(f"      Error: {snapshot.error}")

        self.metrics_snapshots.extend(snapshots)
        return snapshots

    def generate_operational_report(self, snapshots: List[ServiceMetrics]) -> Dict[str, Any]:
        """Generate operational report from metrics"""
        report = {
            "collection_timestamp": datetime.utcnow().isoformat(),
            "services_checked": len(snapshots),
            "services_healthy": sum(1 for s in snapshots if s.health_status == "healthy"),
            "services_with_metrics": sum(1 for s in snapshots if s.metrics_available),
            "total_metrics_size": sum(s.metrics_size for s in snapshots),
            "average_response_time_ms": sum(s.response_time_ms for s in snapshots) / len(snapshots) if snapshots else 0,
            "service_details": {},
            "operational_insights": []
        }

        # Service details
        for snapshot in snapshots:
            report["service_details"][snapshot.service_name] = asdict(snapshot)

        # Operational insights
        unhealthy_services = [s for s in snapshots if s.health_status != "healthy"]
        if unhealthy_services:
            report["operational_insights"].append({
                "type": "warning",
                "message": f"{len(unhealthy_services)} services are not healthy",
                "services": [s.service_name for s in unhealthy_services]
            })

        missing_metrics = [s for s in snapshots if not s.metrics_available]
        if missing_metrics:
            report["operational_insights"].append({
                "type": "warning",
                "message": f"{len(missing_metrics)} services have no metrics",
                "services": [s.service_name for s in missing_metrics]
            })

        # Resource usage insights
        for snapshot in snapshots:
            if "memory_usage_mb" in snapshot.key_metrics:
                memory_mb = snapshot.key_metrics["memory_usage_mb"]
                if memory_mb > 1000:  # More than 1GB
                    report["operational_insights"].append({
                        "type": "info",
                        "message": f"{snapshot.service_name} using {memory_mb:.1f}MB memory"
                    })

        # Traffic insights
        for snapshot in snapshots:
            if snapshot.service_name == "api_gateway":
                total_requests = snapshot.key_metrics.get("total_requests", 0)
                if total_requests > 0:
                    report["operational_insights"].append({
                        "type": "info",
                        "message": f"API Gateway has processed {total_requests} total requests"
                    })

                active_connections = snapshot.key_metrics.get("active_connections", 0)
                if active_connections > 50:
                    report["operational_insights"].append({
                        "type": "warning",
                        "message": f"API Gateway has {active_connections} active connections"
                    })

        return report

    def print_operational_summary(self, report: Dict[str, Any]):
        """Print human-readable operational summary"""
        print("\n" + "="*80)
        print("FREEDOM Platform Operational Status")
        print("="*80)

        print(f"Collection Time: {report['collection_timestamp']}")
        print(f"Services: {report['services_healthy']}/{report['services_checked']} healthy")
        print(f"Metrics: {report['services_with_metrics']}/{report['services_checked']} available")
        print(f"Average Response Time: {report['average_response_time_ms']:.1f}ms")
        print("")

        # Service status
        print("Service Status:")
        for service_name, details in report["service_details"].items():
            status_icon = "✅" if details["health_status"] == "healthy" else "❌"
            metrics_icon = "📊" if details["metrics_available"] else "📈"

            print(f"  {status_icon} {metrics_icon} {service_name:15} "
                  f"{details['health_status']:10} "
                  f"({details['response_time_ms']:5.1f}ms)")

            # Key metrics summary
            key_metrics = details.get("key_metrics", {})
            if key_metrics:
                for metric_name, value in key_metrics.items():
                    if isinstance(value, (int, float)):
                        if metric_name.endswith("_mb"):
                            print(f"    {metric_name}: {value:.1f}MB")
                        elif metric_name.endswith("_total"):
                            print(f"    {metric_name}: {value:.0f}")
                        else:
                            print(f"    {metric_name}: {value}")
                    else:
                        print(f"    {metric_name}: {value}")

        print("")

        # Operational insights
        if report["operational_insights"]:
            print("Operational Insights:")
            for insight in report["operational_insights"]:
                icon = "⚠️ " if insight["type"] == "warning" else "ℹ️ "
                print(f"  {icon} {insight['message']}")
            print("")

        # Overall status
        if report["services_healthy"] == report["services_checked"]:
            print("🟢 All services operational")
        elif report["services_healthy"] > 0:
            print("🟡 Some services have issues")
        else:
            print("🔴 Multiple services down")

    def save_metrics_snapshot(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save metrics snapshot to file"""
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"/tmp/freedom_metrics_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📄 Metrics snapshot saved to: {filename}")
        return filename

def main():
    """Main entry point"""
    try:
        collector = FreedomMetricsCollector()

        print("🚀 FREEDOM Platform Metrics Collection")
        print("="*50)

        # Collect metrics from all services
        snapshots = collector.collect_all_metrics()

        # Generate operational report
        report = collector.generate_operational_report(snapshots)

        # Display summary
        collector.print_operational_summary(report)

        # Save detailed report
        filename = collector.save_metrics_snapshot(report)

        # Exit with status based on service health
        healthy_services = report["services_healthy"]
        total_services = report["services_checked"]

        if healthy_services == total_services:
            print("\n✅ All services operational")
            sys.exit(0)
        elif healthy_services > 0:
            print(f"\n⚠️  {total_services - healthy_services} services have issues")
            sys.exit(1)
        else:
            print("\n❌ Multiple services down")
            sys.exit(2)

    except KeyboardInterrupt:
        print("\nMetrics collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Metrics collection error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()