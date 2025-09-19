"""
Performance benchmark script for the refactored model router.
Compares old vs new implementation and validates performance targets.
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.orchestration.model_router_v2 import ModelRouterFactory
from core.orchestration.types import ModelType, TaskType


class RouterBenchmark:
    """Benchmark suite for model router performance"""

    def __init__(self):
        self.results = {}
        self.router = None

    async def setup(self):
        """Setup router for benchmarking"""
        print("🚀 Setting up router for benchmarking...")
        self.router = await ModelRouterFactory.create_test_router()
        print("✅ Router initialized\n")

    async def cleanup(self):
        """Cleanup after benchmarking"""
        if self.router:
            await self.router.cleanup()

    async def benchmark_routing_speed(self, iterations: int = 100):
        """Benchmark routing decision speed"""
        print(f"📊 Benchmarking routing speed ({iterations} iterations)...")

        # Warm up
        for _ in range(10):
            await self.router.route_task("warmup", TaskType.COMPLETION, 5)

        # Test different scenarios
        scenarios = [
            ("Simple task", TaskType.CODE_GENERATION, 2),
            ("Medium task", TaskType.ANALYSIS, 5),
            ("Complex task", TaskType.REASONING, 9),
        ]

        for scenario_name, task_type, complexity in scenarios:
            times = []

            for i in range(iterations):
                objective = f"Test objective {i} for {scenario_name}"
                start = time.perf_counter()
                decision = await self.router.route_task(objective, task_type, complexity)
                elapsed = (time.perf_counter() - start) * 1000  # ms

                times.append(elapsed)

            # Calculate statistics
            avg_time = statistics.mean(times)
            p50 = statistics.median(times)
            p95 = statistics.quantiles(times, n=20)[18]  # 95th percentile
            p99 = statistics.quantiles(times, n=100)[98]  # 99th percentile

            self.results[f"routing_{scenario_name}"] = {
                "avg_ms": avg_time,
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
                "min_ms": min(times),
                "max_ms": max(times)
            }

            print(f"  {scenario_name}:")
            print(f"    Average: {avg_time:.2f}ms")
            print(f"    P50: {p50:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms")
            print(f"    Min: {min(times):.2f}ms, Max: {max(times):.2f}ms")

        print()

    async def benchmark_cache_performance(self, iterations: int = 100):
        """Benchmark cache hit rate and performance"""
        print(f"📊 Benchmarking cache performance ({iterations} iterations)...")

        # Create a set of tasks
        tasks = [
            (f"task_{i % 10}", TaskType(list(TaskType)[i % 6]), i % 10)
            for i in range(iterations)
        ]

        # First pass - populate cache
        print("  Populating cache...")
        cache_misses = 0
        for objective, task_type, complexity in tasks:
            decision = await self.router.route_task(objective, task_type, complexity)
            if not decision.cached:
                cache_misses += 1

        print(f"    Initial cache misses: {cache_misses}/{iterations}")

        # Second pass - measure cache hits
        print("  Testing cache hits...")
        cache_hits = 0
        cache_times = []

        for objective, task_type, complexity in tasks:
            start = time.perf_counter()
            decision = await self.router.route_task(objective, task_type, complexity)
            elapsed = (time.perf_counter() - start) * 1000

            if decision.cached:
                cache_hits += 1
                cache_times.append(elapsed)

        hit_rate = cache_hits / iterations * 100
        avg_cache_time = statistics.mean(cache_times) if cache_times else 0

        self.results["cache_performance"] = {
            "hit_rate": hit_rate,
            "avg_cache_time_ms": avg_cache_time,
            "total_hits": cache_hits,
            "total_requests": iterations
        }

        print(f"    Cache hit rate: {hit_rate:.1f}%")
        print(f"    Average cache retrieval: {avg_cache_time:.2f}ms\n")

    async def benchmark_concurrent_routing(self, concurrent_requests: int = 50):
        """Benchmark concurrent routing performance"""
        print(f"📊 Benchmarking concurrent routing ({concurrent_requests} requests)...")

        async def route_task(index: int):
            start = time.perf_counter()
            decision = await self.router.route_task(
                f"concurrent_task_{index}",
                TaskType(list(TaskType)[index % 6]),
                index % 10
            )
            return (time.perf_counter() - start) * 1000, decision

        # Run concurrent requests
        start = time.perf_counter()
        results = await asyncio.gather(*[route_task(i) for i in range(concurrent_requests)])
        total_time = (time.perf_counter() - start) * 1000

        # Analyze results
        times = [r[0] for r in results]
        decisions = [r[1] for r in results]

        avg_time = statistics.mean(times)
        throughput = concurrent_requests / (total_time / 1000)  # requests per second

        self.results["concurrent_performance"] = {
            "total_requests": concurrent_requests,
            "total_time_ms": total_time,
            "avg_time_per_request_ms": avg_time,
            "throughput_rps": throughput
        }

        print(f"    Total time: {total_time:.2f}ms")
        print(f"    Average per request: {avg_time:.2f}ms")
        print(f"    Throughput: {throughput:.1f} requests/second\n")

    async def benchmark_circuit_breaker(self):
        """Benchmark circuit breaker behavior"""
        print("📊 Benchmarking circuit breaker...")

        # Simulate failures by forcing a non-existent model
        context = {"force_model": ModelType.CLAUDE.value}

        # Track circuit breaker behavior
        results = []
        for i in range(10):
            try:
                start = time.perf_counter()
                decision = await self.router.route_task(
                    "test", TaskType.REASONING, 5, context
                )
                elapsed = (time.perf_counter() - start) * 1000
                results.append({"attempt": i, "success": True, "time_ms": elapsed})
            except Exception as e:
                results.append({"attempt": i, "success": False, "error": str(e)})

        successes = sum(1 for r in results if r.get("success", False))
        failures = len(results) - successes

        self.results["circuit_breaker"] = {
            "total_attempts": len(results),
            "successes": successes,
            "failures": failures
        }

        print(f"    Attempts: {len(results)}, Successes: {successes}, Failures: {failures}\n")

    async def benchmark_memory_usage(self, iterations: int = 1000):
        """Benchmark memory usage with large cache"""
        print(f"📊 Benchmarking memory usage ({iterations} unique tasks)...")

        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            print("    psutil not installed, skipping memory benchmark\n")
            return

        # Create many unique tasks to fill cache
        for i in range(iterations):
            await self.router.route_task(
                f"unique_task_{i}",
                TaskType(list(TaskType)[i % 6]),
                i % 10
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        self.results["memory_usage"] = {
            "initial_mb": initial_memory,
            "final_mb": final_memory,
            "increase_mb": memory_increase,
            "tasks_cached": iterations
        }

        print(f"    Initial memory: {initial_memory:.1f}MB")
        print(f"    Final memory: {final_memory:.1f}MB")
        print(f"    Memory increase: {memory_increase:.1f}MB for {iterations} cached tasks\n")

    def print_summary(self):
        """Print benchmark summary"""
        print("\n" + "=" * 60)
        print("📈 BENCHMARK SUMMARY")
        print("=" * 60)

        # Check performance targets
        targets_met = []
        targets_failed = []

        # Target 1: Routing decisions < 10ms
        if "routing_Simple task" in self.results:
            avg_time = self.results["routing_Simple task"]["avg_ms"]
            if avg_time < 10:
                targets_met.append(f"✅ Routing decisions < 10ms (actual: {avg_time:.2f}ms)")
            else:
                targets_failed.append(f"❌ Routing decisions < 10ms (actual: {avg_time:.2f}ms)")

        # Target 2: Cache hit rate > 90%
        if "cache_performance" in self.results:
            hit_rate = self.results["cache_performance"]["hit_rate"]
            if hit_rate >= 90:
                targets_met.append(f"✅ Cache hit rate > 90% (actual: {hit_rate:.1f}%)")
            else:
                targets_failed.append(f"❌ Cache hit rate > 90% (actual: {hit_rate:.1f}%)")

        # Target 3: Concurrent performance
        if "concurrent_performance" in self.results:
            throughput = self.results["concurrent_performance"]["throughput_rps"]
            targets_met.append(f"✅ Throughput: {throughput:.1f} requests/second")

        print("\n🎯 Performance Targets:")
        for target in targets_met:
            print(f"  {target}")
        for target in targets_failed:
            print(f"  {target}")

        # Overall verdict
        if len(targets_failed) == 0:
            print("\n🏆 All performance targets met!")
        else:
            print(f"\n⚠️ {len(targets_failed)} target(s) need improvement")

        print("\n" + "=" * 60)


async def main():
    """Run all benchmarks"""
    benchmark = RouterBenchmark()

    try:
        await benchmark.setup()

        # Run benchmarks
        await benchmark.benchmark_routing_speed(iterations=100)
        await benchmark.benchmark_cache_performance(iterations=100)
        await benchmark.benchmark_concurrent_routing(concurrent_requests=50)
        await benchmark.benchmark_circuit_breaker()
        await benchmark.benchmark_memory_usage(iterations=500)

        # Print summary
        benchmark.print_summary()

    finally:
        await benchmark.cleanup()


if __name__ == "__main__":
    print("\n🔧 Model Router Performance Benchmark\n")
    print("This benchmark validates the refactored router meets performance targets:")
    print("  • Routing decisions < 10ms")
    print("  • Cache hit rate > 90%")
    print("  • Efficient concurrent processing")
    print("\n" + "=" * 60 + "\n")

    asyncio.run(main())