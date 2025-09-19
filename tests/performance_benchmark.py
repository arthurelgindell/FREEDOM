#!/usr/bin/env python3
"""
FREEDOM Platform - Performance Benchmark Suite
WORKSTREAM 7: Verification & Observability

Comprehensive performance testing for all FREEDOM services:
- API Gateway response times and throughput
- Knowledge Base ingest and query performance
- MLX inference latency and throughput
- Database performance under load
- End-to-end workflow performance

CRITICAL: Following FREEDOM principles - performance targets must be measurable and verified.
"""

import os
import sys
import time
import json
import uuid
import asyncio
import statistics
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

import requests
import psycopg2
from concurrent.futures import ThreadPoolExecutor, as_completed

# Performance test configuration
BENCHMARK_CONFIG = {
    "api_gateway_url": "http://localhost:8080",
    "kb_service_url": "http://localhost:8000",
    "mlx_service_url": "http://localhost:8001",
    "postgres_host": "localhost",
    "postgres_port": 5432,
    "postgres_db": "freedom_kb",
    "postgres_user": "freedom",
    "postgres_password": "freedom_dev",
    "api_key": os.getenv("FREEDOM_API_KEY", "dev-key-change-in-production"),
    "timeout": 60,
    "correlation_id": str(uuid.uuid4())
}

# Performance targets (these are the measurable goals)
PERFORMANCE_TARGETS = {
    "api_gateway_health_p95": 100,  # ms
    "kb_query_p95": 500,           # ms
    "kb_ingest_p95": 1000,         # ms
    "mlx_inference_p95": 5000,     # ms (model inference is naturally slower)
    "concurrent_requests_success_rate": 0.95,  # 95% success rate under load
    "database_query_p95": 50,      # ms for simple queries
}

@dataclass
class BenchmarkResult:
    """Performance benchmark result"""
    test_name: str
    operation: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: Optional[str] = None
    correlation_id: Optional[str] = None
    additional_metrics: Optional[Dict] = None

@dataclass
class PerformanceStats:
    """Performance statistics summary"""
    operation: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    min_duration_ms: float
    max_duration_ms: float
    mean_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    requests_per_second: float
    target_p95_ms: Optional[float] = None
    target_met: Optional[bool] = None

class FreedomPerformanceBenchmark:
    """Performance benchmark suite for FREEDOM platform"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []
        self.correlation_id = BENCHMARK_CONFIG["correlation_id"]
        self.start_time = time.time()

        print(f"🚀 FREEDOM Performance Benchmark Suite")
        print(f"Run ID: {self.correlation_id}")
        print(f"Started at: {datetime.utcnow().isoformat()}")
        print("="*80)

    def log_progress(self, message: str):
        """Log progress with timestamp"""
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")

    def record_result(self, test_name: str, operation: str, duration_ms: float,
                     success: bool, error: str = None, metrics: Dict = None):
        """Record a benchmark result"""
        result = BenchmarkResult(
            test_name=test_name,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error=error,
            timestamp=datetime.utcnow().isoformat(),
            correlation_id=self.correlation_id,
            additional_metrics=metrics
        )
        self.results.append(result)

    def calculate_stats(self, operation: str) -> PerformanceStats:
        """Calculate performance statistics for an operation"""
        operation_results = [r for r in self.results if r.operation == operation]

        if not operation_results:
            raise ValueError(f"No results found for operation: {operation}")

        successful_results = [r for r in operation_results if r.success]
        durations = [r.duration_ms for r in successful_results]

        if not durations:
            # All requests failed
            return PerformanceStats(
                operation=operation,
                total_requests=len(operation_results),
                successful_requests=0,
                failed_requests=len(operation_results),
                success_rate=0.0,
                min_duration_ms=0,
                max_duration_ms=0,
                mean_duration_ms=0,
                median_duration_ms=0,
                p95_duration_ms=0,
                p99_duration_ms=0,
                requests_per_second=0,
            )

        # Calculate statistics
        durations_sorted = sorted(durations)
        total_time = max(r.timestamp for r in operation_results) - min(r.timestamp for r in operation_results) if len(operation_results) > 1 else 1

        # Handle timestamp calculation more carefully
        timestamps = [datetime.fromisoformat(r.timestamp.replace('Z', '+00:00')) for r in operation_results]
        if len(timestamps) > 1:
            time_span = (max(timestamps) - min(timestamps)).total_seconds()
            requests_per_second = len(successful_results) / max(time_span, 1)
        else:
            requests_per_second = 1.0

        target_p95 = PERFORMANCE_TARGETS.get(f"{operation}_p95")
        p95_value = durations_sorted[int(0.95 * len(durations_sorted))] if durations_sorted else 0

        return PerformanceStats(
            operation=operation,
            total_requests=len(operation_results),
            successful_requests=len(successful_results),
            failed_requests=len(operation_results) - len(successful_results),
            success_rate=len(successful_results) / len(operation_results),
            min_duration_ms=min(durations),
            max_duration_ms=max(durations),
            mean_duration_ms=statistics.mean(durations),
            median_duration_ms=statistics.median(durations),
            p95_duration_ms=p95_value,
            p99_duration_ms=durations_sorted[int(0.99 * len(durations_sorted))] if durations_sorted else 0,
            requests_per_second=requests_per_second,
            target_p95_ms=target_p95,
            target_met=p95_value <= target_p95 if target_p95 else None
        )

    def benchmark_api_gateway_health(self, num_requests: int = 50) -> None:
        """Benchmark API Gateway health endpoint performance"""
        self.log_progress(f"Benchmarking API Gateway health ({num_requests} requests)")

        def make_health_request():
            start_time = time.time()
            try:
                response = requests.get(
                    f"{BENCHMARK_CONFIG['api_gateway_url']}/health",
                    headers={"x-correlation-id": f"{self.correlation_id}-health"},
                    timeout=BENCHMARK_CONFIG["timeout"]
                )
                duration_ms = (time.time() - start_time) * 1000
                success = response.status_code == 200

                self.record_result(
                    "api_gateway_health",
                    "api_gateway_health",
                    duration_ms,
                    success,
                    None if success else f"HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                return success

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.record_result(
                    "api_gateway_health",
                    "api_gateway_health",
                    duration_ms,
                    False,
                    str(e)
                )
                return False

        # Execute requests concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]

        success_count = sum(results)
        self.log_progress(f"API Gateway health: {success_count}/{num_requests} successful")

    def benchmark_kb_query_performance(self, num_requests: int = 30) -> None:
        """Benchmark Knowledge Base query performance"""
        self.log_progress(f"Benchmarking KB query performance ({num_requests} requests)")

        test_queries = [
            "machine learning algorithms",
            "database optimization techniques",
            "API security best practices",
            "cloud infrastructure monitoring",
            "container orchestration patterns"
        ]

        def make_query_request(query_text: str, request_id: int):
            start_time = time.time()
            try:
                response = requests.post(
                    f"{BENCHMARK_CONFIG['api_gateway_url']}/kb/query",
                    json={
                        "query": query_text,
                        "limit": 10,
                        "similarity_threshold": 0.5
                    },
                    headers={
                        "X-API-Key": BENCHMARK_CONFIG["api_key"],
                        "x-correlation-id": f"{self.correlation_id}-query-{request_id}"
                    },
                    timeout=BENCHMARK_CONFIG["timeout"]
                )
                duration_ms = (time.time() - start_time) * 1000
                success = response.status_code == 200

                result_count = 0
                if success:
                    try:
                        result_data = response.json()
                        result_count = result_data.get("total_results", 0)
                    except:
                        pass

                self.record_result(
                    "kb_query_performance",
                    "kb_query",
                    duration_ms,
                    success,
                    None if success else f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "result_count": result_count, "query_length": len(query_text)}
                )
                return success

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.record_result(
                    "kb_query_performance",
                    "kb_query",
                    duration_ms,
                    False,
                    str(e)
                )
                return False

        # Execute queries with different texts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(num_requests):
                query = test_queries[i % len(test_queries)]
                futures.append(executor.submit(make_query_request, query, i))

            results = [future.result() for future in as_completed(futures)]

        success_count = sum(results)
        self.log_progress(f"KB query: {success_count}/{num_requests} successful")

    def benchmark_kb_ingest_performance(self, num_requests: int = 20) -> None:
        """Benchmark Knowledge Base ingest performance"""
        self.log_progress(f"Benchmarking KB ingest performance ({num_requests} requests)")

        def make_ingest_request(request_id: int):
            start_time = time.time()
            try:
                test_spec = {
                    "technology_name": "FREEDOM_BENCHMARK",
                    "version": "1.0.0",
                    "component_type": "benchmark_component",
                    "component_name": f"perf_test_spec_{request_id}_{int(time.time())}",
                    "specification": {
                        "description": f"Performance test specification #{request_id}",
                        "features": [f"feature_{i}" for i in range(5)],
                        "benchmark_timestamp": datetime.utcnow().isoformat(),
                        "request_id": request_id
                    },
                    "source_url": f"https://freedom.benchmark/test-{request_id}",
                    "confidence_score": 0.9
                }

                response = requests.post(
                    f"{BENCHMARK_CONFIG['api_gateway_url']}/kb/ingest",
                    json=test_spec,
                    headers={
                        "X-API-Key": BENCHMARK_CONFIG["api_key"],
                        "x-correlation-id": f"{self.correlation_id}-ingest-{request_id}"
                    },
                    timeout=BENCHMARK_CONFIG["timeout"]
                )
                duration_ms = (time.time() - start_time) * 1000
                success = response.status_code == 200

                spec_id = None
                if success:
                    try:
                        result_data = response.json()
                        spec_id = result_data.get("specification_id")
                    except:
                        pass

                self.record_result(
                    "kb_ingest_performance",
                    "kb_ingest",
                    duration_ms,
                    success,
                    None if success else f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "spec_id": spec_id}
                )
                return success

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.record_result(
                    "kb_ingest_performance",
                    "kb_ingest",
                    duration_ms,
                    False,
                    str(e)
                )
                return False

        # Execute ingest requests sequentially to avoid overwhelming the system
        results = []
        for i in range(num_requests):
            result = make_ingest_request(i)
            results.append(result)
            time.sleep(0.1)  # Small delay between ingests

        success_count = sum(results)
        self.log_progress(f"KB ingest: {success_count}/{num_requests} successful")

    def benchmark_mlx_inference_performance(self, num_requests: int = 10) -> None:
        """Benchmark MLX inference performance"""
        self.log_progress(f"Benchmarking MLX inference performance ({num_requests} requests)")

        test_prompts = [
            "Explain quantum computing in simple terms.",
            "What are the benefits of microservices architecture?",
            "How does machine learning improve software development?",
            "Describe the principles of API design.",
            "What is the future of artificial intelligence?"
        ]

        def make_inference_request(prompt: str, request_id: int):
            start_time = time.time()
            try:
                response = requests.post(
                    f"{BENCHMARK_CONFIG['api_gateway_url']}/inference",
                    json={
                        "prompt": prompt,
                        "max_tokens": 100,
                        "temperature": 0.7,
                        "stream": False
                    },
                    headers={
                        "X-API-Key": BENCHMARK_CONFIG["api_key"],
                        "x-correlation-id": f"{self.correlation_id}-inference-{request_id}"
                    },
                    timeout=BENCHMARK_CONFIG["timeout"]
                )
                duration_ms = (time.time() - start_time) * 1000
                success = response.status_code == 200

                token_count = 0
                if success:
                    try:
                        result_data = response.json()
                        usage = result_data.get("usage", {})
                        token_count = usage.get("completion_tokens", 0)
                    except:
                        pass

                self.record_result(
                    "mlx_inference_performance",
                    "mlx_inference",
                    duration_ms,
                    success,
                    None if success else f"HTTP {response.status_code}",
                    {"status_code": response.status_code, "token_count": token_count, "prompt_length": len(prompt)}
                )
                return success

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.record_result(
                    "mlx_inference_performance",
                    "mlx_inference",
                    duration_ms,
                    False,
                    str(e)
                )
                return False

        # Execute inference requests sequentially (inference is resource-intensive)
        results = []
        for i in range(num_requests):
            prompt = test_prompts[i % len(test_prompts)]
            result = make_inference_request(prompt, i)
            results.append(result)
            time.sleep(0.5)  # Longer delay for inference

        success_count = sum(results)
        self.log_progress(f"MLX inference: {success_count}/{num_requests} successful")

    def benchmark_database_performance(self, num_queries: int = 100) -> None:
        """Benchmark direct database performance"""
        self.log_progress(f"Benchmarking database performance ({num_queries} queries)")

        def execute_db_query():
            start_time = time.time()
            conn = None
            try:
                conn = psycopg2.connect(
                    host=BENCHMARK_CONFIG["postgres_host"],
                    port=BENCHMARK_CONFIG["postgres_port"],
                    database=BENCHMARK_CONFIG["postgres_db"],
                    user=BENCHMARK_CONFIG["postgres_user"],
                    password=BENCHMARK_CONFIG["postgres_password"],
                    connect_timeout=10
                )

                cursor = conn.cursor()
                # Simple query to test basic performance
                cursor.execute("SELECT COUNT(*) FROM specifications WHERE created_at > NOW() - INTERVAL '7 days';")
                result = cursor.fetchone()
                cursor.close()

                duration_ms = (time.time() - start_time) * 1000
                success = result is not None

                self.record_result(
                    "database_performance",
                    "database_query",
                    duration_ms,
                    success,
                    None,
                    {"result": result[0] if result else None}
                )
                return success

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                self.record_result(
                    "database_performance",
                    "database_query",
                    duration_ms,
                    False,
                    str(e)
                )
                return False
            finally:
                if conn:
                    conn.close()

        # Execute database queries concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(execute_db_query) for _ in range(num_queries)]
            results = [future.result() for future in as_completed(futures)]

        success_count = sum(results)
        self.log_progress(f"Database queries: {success_count}/{num_queries} successful")

    def benchmark_concurrent_load(self, concurrent_users: int = 20, requests_per_user: int = 5) -> None:
        """Benchmark system performance under concurrent load"""
        self.log_progress(f"Benchmarking concurrent load ({concurrent_users} users, {requests_per_user} requests each)")

        def user_simulation(user_id: int):
            """Simulate a user making multiple requests"""
            user_results = []
            for req_id in range(requests_per_user):
                # Mix of different operations
                operations = [
                    ("health", lambda: requests.get(f"{BENCHMARK_CONFIG['api_gateway_url']}/health")),
                    ("query", lambda: requests.post(
                        f"{BENCHMARK_CONFIG['api_gateway_url']}/kb/query",
                        json={"query": f"test query from user {user_id}", "limit": 5},
                        headers={"X-API-Key": BENCHMARK_CONFIG["api_key"]}
                    )),
                ]

                op_name, op_func = operations[req_id % len(operations)]
                start_time = time.time()

                try:
                    response = op_func()
                    duration_ms = (time.time() - start_time) * 1000
                    success = response.status_code == 200

                    self.record_result(
                        "concurrent_load",
                        "concurrent_requests",
                        duration_ms,
                        success,
                        None if success else f"HTTP {response.status_code}",
                        {"user_id": user_id, "request_id": req_id, "operation": op_name}
                    )
                    user_results.append(success)

                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_result(
                        "concurrent_load",
                        "concurrent_requests",
                        duration_ms,
                        False,
                        str(e),
                        {"user_id": user_id, "request_id": req_id}
                    )
                    user_results.append(False)

                time.sleep(0.1)  # Small delay between user requests

            return user_results

        # Execute concurrent user simulations
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(user_simulation, user_id) for user_id in range(concurrent_users)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())

        success_count = sum(all_results)
        total_requests = len(all_results)
        self.log_progress(f"Concurrent load: {success_count}/{total_requests} successful")

    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        self.log_progress("Generating performance report...")

        operations = [
            "api_gateway_health",
            "kb_query",
            "kb_ingest",
            "mlx_inference",
            "database_query",
            "concurrent_requests"
        ]

        report = {
            "benchmark_info": {
                "run_id": self.correlation_id,
                "start_time": datetime.utcfromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "total_duration_seconds": time.time() - self.start_time,
                "total_requests": len(self.results)
            },
            "performance_targets": PERFORMANCE_TARGETS,
            "operation_stats": {},
            "targets_summary": {
                "total_targets": 0,
                "targets_met": 0,
                "targets_failed": 0
            }
        }

        # Calculate stats for each operation
        for operation in operations:
            try:
                stats = self.calculate_stats(operation)
                report["operation_stats"][operation] = asdict(stats)

                # Update targets summary
                if stats.target_p95_ms is not None:
                    report["targets_summary"]["total_targets"] += 1
                    if stats.target_met:
                        report["targets_summary"]["targets_met"] += 1
                    else:
                        report["targets_summary"]["targets_failed"] += 1

            except ValueError:
                # No results for this operation
                report["operation_stats"][operation] = None

        return report

    def print_performance_summary(self, report: Dict):
        """Print human-readable performance summary"""
        print("\n" + "="*80)
        print("FREEDOM Platform Performance Benchmark Results")
        print("="*80)

        print(f"Run ID: {report['benchmark_info']['run_id']}")
        print(f"Duration: {report['benchmark_info']['total_duration_seconds']:.1f}s")
        print(f"Total Requests: {report['benchmark_info']['total_requests']}")
        print("")

        # Performance targets summary
        targets = report['targets_summary']
        if targets['total_targets'] > 0:
            target_success_rate = targets['targets_met'] / targets['total_targets'] * 100
            print(f"Performance Targets: {targets['targets_met']}/{targets['total_targets']} met ({target_success_rate:.1f}%)")
            print("")

        # Operation details
        for operation, stats in report['operation_stats'].items():
            if stats is None:
                print(f"{operation:25} NO DATA")
                continue

            success_rate = stats['success_rate'] * 100
            target_status = ""
            if stats['target_p95_ms'] is not None:
                target_met = "✅" if stats['target_met'] else "❌"
                target_status = f"Target: {stats['target_p95_ms']}ms {target_met}"

            print(f"{operation:25} "
                  f"P95: {stats['p95_duration_ms']:6.1f}ms "
                  f"Mean: {stats['mean_duration_ms']:6.1f}ms "
                  f"Success: {success_rate:5.1f}% "
                  f"RPS: {stats['requests_per_second']:5.1f} "
                  f"{target_status}")

        print("")

        # Overall assessment
        failed_targets = [op for op, stats in report['operation_stats'].items()
                         if stats and stats.get('target_met') is False]

        if failed_targets:
            print("❌ PERFORMANCE BENCHMARK FAILED")
            print(f"Failed operations: {', '.join(failed_targets)}")
            print("Performance targets not met. Optimization required.")
        elif targets['total_targets'] > 0:
            print("✅ PERFORMANCE BENCHMARK PASSED")
            print("All performance targets met successfully.")
        else:
            print("⚠️  PERFORMANCE BENCHMARK COMPLETED")
            print("No specific performance targets configured.")

    def run_all_benchmarks(self) -> bool:
        """Run all performance benchmarks"""
        try:
            # Core service performance
            self.benchmark_api_gateway_health(50)
            self.benchmark_database_performance(100)

            # Knowledge base performance
            self.benchmark_kb_query_performance(30)
            self.benchmark_kb_ingest_performance(20)

            # MLX inference performance (may fail if no model loaded)
            try:
                self.benchmark_mlx_inference_performance(10)
            except Exception as e:
                self.log_progress(f"MLX inference benchmark skipped: {e}")

            # Concurrent load testing
            self.benchmark_concurrent_load(20, 5)

            # Generate and display report
            report = self.generate_performance_report()
            self.print_performance_summary(report)

            # Save detailed report
            report_file = f"/tmp/freedom_performance_report_{self.correlation_id}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nDetailed report saved to: {report_file}")

            # Determine overall success
            targets = report['targets_summary']
            if targets['total_targets'] > 0:
                return targets['targets_failed'] == 0
            else:
                # If no targets, check if basic operations are working
                successful_ops = sum(1 for stats in report['operation_stats'].values()
                                   if stats and stats['success_rate'] > 0.8)
                return successful_ops >= 3  # At least 3 operations must be working well

        except Exception as e:
            self.log_progress(f"Benchmark suite error: {e}")
            return False

def main():
    """Main entry point"""
    try:
        benchmark = FreedomPerformanceBenchmark()
        success = benchmark.run_all_benchmarks()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\nPerformance benchmarks interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Benchmark framework error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()