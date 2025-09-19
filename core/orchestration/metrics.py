"""
Optimized performance metrics calculation for model router.
Uses efficient data structures and algorithms for real-time metrics.
"""

import asyncio
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol
import numpy as np


@dataclass
class ModelPerformance:
    """Performance metrics for a model"""
    model_type: str
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    tokens_per_second: float
    success_rate: float
    error_rate: float
    total_requests: int
    total_tokens: int
    cost_per_token: float
    total_cost: float
    last_updated: float = field(default_factory=time.time)


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    model_type: str
    start_time: float
    end_time: float
    duration: float
    success: bool
    tokens_used: int
    cost: float
    error: Optional[str] = None


class MetricsInterface(Protocol):
    """Protocol for metrics implementations"""

    async def record_response(self, model_type: str, duration: float,
                             success: bool, tokens: int = 0) -> None:
        """Record a model response"""
        ...

    def get_performance_stats(self, model_type: str) -> ModelPerformance:
        """Get performance statistics for a model"""
        ...


class RouterMetrics:
    """Optimized metrics calculation with sliding windows"""

    def __init__(self, window_size: int = 100, time_window: int = 300):
        """
        Initialize metrics tracker.

        Args:
            window_size: Number of recent requests to keep
            time_window: Time window in seconds for rate calculations
        """
        self.window_size = window_size
        self.time_window = time_window

        # Use deque for efficient sliding windows
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.request_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self.token_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))

        # Counters for overall statistics
        self.success_counts: Dict[str, int] = defaultdict(int)
        self.failure_counts: Dict[str, int] = defaultdict(int)
        self.total_tokens: Dict[str, int] = defaultdict(int)
        self.total_cost: Dict[str, float] = defaultdict(float)

        # Pre-computed percentiles for efficiency
        self._cached_percentiles: Dict[str, Dict[str, float]] = {}
        self._cache_timestamp: Dict[str, float] = {}
        self._cache_ttl = 5.0  # Cache for 5 seconds

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def record_response(self, model_type: str, duration: float,
                             success: bool, tokens: int = 0, cost: float = 0.0) -> None:
        """Record a model response with optimized data structures"""
        async with self._lock:
            current_time = time.time()

            # Add to sliding windows
            self.response_times[model_type].append(duration)
            self.request_timestamps[model_type].append(current_time)
            self.token_counts[model_type].append(tokens)

            # Update counters
            if success:
                self.success_counts[model_type] += 1
            else:
                self.failure_counts[model_type] += 1

            self.total_tokens[model_type] += tokens
            self.total_cost[model_type] += cost

            # Invalidate cache for this model
            if model_type in self._cached_percentiles:
                del self._cached_percentiles[model_type]
                del self._cache_timestamp[model_type]

    def get_performance_stats(self, model_type: str) -> ModelPerformance:
        """Get performance statistics with caching for expensive calculations"""
        current_time = time.time()

        # Check if we have cached percentiles
        if (model_type in self._cached_percentiles and
            current_time - self._cache_timestamp.get(model_type, 0) < self._cache_ttl):
            percentiles = self._cached_percentiles[model_type]
        else:
            percentiles = self._calculate_percentiles(model_type)
            self._cached_percentiles[model_type] = percentiles
            self._cache_timestamp[model_type] = current_time

        # Calculate rates
        success_rate = self._calculate_success_rate(model_type)
        tokens_per_second = self._calculate_throughput(model_type)

        # Calculate average cost per token
        total_tokens = self.total_tokens[model_type]
        cost_per_token = self.total_cost[model_type] / max(1, total_tokens)

        return ModelPerformance(
            model_type=model_type,
            avg_response_time=percentiles.get('mean', 0),
            p50_response_time=percentiles.get('p50', 0),
            p95_response_time=percentiles.get('p95', 0),
            p99_response_time=percentiles.get('p99', 0),
            tokens_per_second=tokens_per_second,
            success_rate=success_rate,
            error_rate=1.0 - success_rate,
            total_requests=self.success_counts[model_type] + self.failure_counts[model_type],
            total_tokens=total_tokens,
            cost_per_token=cost_per_token,
            total_cost=self.total_cost[model_type],
            last_updated=current_time
        )

    def _calculate_percentiles(self, model_type: str) -> Dict[str, float]:
        """Calculate percentiles using numpy for efficiency"""
        times = list(self.response_times[model_type])

        if not times:
            return {'mean': 0, 'p50': 0, 'p95': 0, 'p99': 0}

        # Use numpy for fast percentile calculation
        times_array = np.array(times)

        return {
            'mean': float(np.mean(times_array)),
            'p50': float(np.percentile(times_array, 50)),
            'p95': float(np.percentile(times_array, 95)),
            'p99': float(np.percentile(times_array, 99))
        }

    def _calculate_success_rate(self, model_type: str) -> float:
        """Calculate success rate"""
        success = self.success_counts[model_type]
        failure = self.failure_counts[model_type]
        total = success + failure

        if total == 0:
            return 1.0

        return success / total

    def _calculate_throughput(self, model_type: str) -> float:
        """Calculate tokens per second in recent time window"""
        current_time = time.time()
        window_start = current_time - self.time_window

        # Get requests within time window
        timestamps = self.request_timestamps[model_type]
        tokens = self.token_counts[model_type]

        if not timestamps:
            return 0.0

        # Find requests within window
        total_tokens = 0
        for i, timestamp in enumerate(timestamps):
            if timestamp >= window_start:
                total_tokens += tokens[i]

        # Calculate rate
        time_span = current_time - window_start
        if time_span > 0:
            return total_tokens / time_span

        return 0.0

    def get_all_stats(self) -> Dict[str, ModelPerformance]:
        """Get statistics for all models"""
        stats = {}
        for model_type in set(list(self.success_counts.keys()) + list(self.failure_counts.keys())):
            stats[model_type] = self.get_performance_stats(model_type)
        return stats

    def get_model_comparison(self) -> Dict[str, Dict[str, float]]:
        """Get comparison metrics across all models"""
        all_stats = self.get_all_stats()

        comparison = {}
        for model_type, stats in all_stats.items():
            comparison[model_type] = {
                'avg_response_time': stats.avg_response_time,
                'p99_response_time': stats.p99_response_time,
                'success_rate': stats.success_rate,
                'tokens_per_second': stats.tokens_per_second,
                'cost_efficiency': stats.tokens_per_second / max(0.0001, stats.cost_per_token)
            }

        return comparison

    def reset_model_metrics(self, model_type: str):
        """Reset metrics for a specific model"""
        self.response_times[model_type].clear()
        self.request_timestamps[model_type].clear()
        self.token_counts[model_type].clear()
        self.success_counts[model_type] = 0
        self.failure_counts[model_type] = 0
        self.total_tokens[model_type] = 0
        self.total_cost[model_type] = 0.0

        # Clear cache
        if model_type in self._cached_percentiles:
            del self._cached_percentiles[model_type]
            del self._cache_timestamp[model_type]


class AggregatedMetrics:
    """Aggregated metrics across all models and routing decisions"""

    def __init__(self):
        self.routing_decisions: deque = deque(maxlen=1000)
        self.cache_hits = 0
        self.cache_misses = 0
        self.escalations = 0
        self.circuit_breaker_trips = 0
        self.start_time = time.time()

    def record_routing_decision(self, decision: Dict[str, any]):
        """Record a routing decision"""
        self.routing_decisions.append({
            'timestamp': time.time(),
            **decision
        })

    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1

    def record_escalation(self, from_model: str, to_model: str):
        """Record a model escalation"""
        self.escalations += 1

    def record_circuit_breaker_trip(self, model: str):
        """Record a circuit breaker trip"""
        self.circuit_breaker_trips += 1

    def get_summary(self) -> Dict[str, any]:
        """Get aggregated metrics summary"""
        total_cache_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / max(1, total_cache_requests)

        uptime = time.time() - self.start_time

        return {
            'uptime_seconds': uptime,
            'total_routing_decisions': len(self.routing_decisions),
            'cache_hit_rate': cache_hit_rate,
            'total_escalations': self.escalations,
            'circuit_breaker_trips': self.circuit_breaker_trips,
            'decisions_per_minute': len(self.routing_decisions) / max(1, uptime / 60)
        }


class MetricsCollector:
    """Central metrics collector combining all metrics sources"""

    def __init__(self):
        self.router_metrics = RouterMetrics()
        self.aggregated_metrics = AggregatedMetrics()
        self._export_interval = 60  # Export metrics every minute
        self._export_task = None

    async def start(self):
        """Start metrics collection and export"""
        if not self._export_task:
            self._export_task = asyncio.create_task(self._export_loop())

    async def stop(self):
        """Stop metrics collection"""
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass

    async def _export_loop(self):
        """Periodically export metrics"""
        while True:
            try:
                await asyncio.sleep(self._export_interval)
                await self._export_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error exporting metrics: {e}")

    async def _export_metrics(self):
        """Export metrics to monitoring system"""
        # Get all metrics
        model_stats = self.router_metrics.get_all_stats()
        aggregated = self.aggregated_metrics.get_summary()

        # Here you would send to Prometheus, CloudWatch, etc.
        print(f"📊 Metrics Export: {len(model_stats)} models, "
              f"Cache Hit Rate: {aggregated['cache_hit_rate']:.2%}")

    def get_dashboard_data(self) -> Dict[str, any]:
        """Get data for metrics dashboard"""
        return {
            'models': self.router_metrics.get_all_stats(),
            'comparison': self.router_metrics.get_model_comparison(),
            'aggregated': self.aggregated_metrics.get_summary()
        }