"""
Circuit breaker pattern implementation for model connections.
Protects against cascading failures and provides graceful degradation.
"""

import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict
from collections import deque


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5           # Failures before opening
    recovery_timeout: int = 60           # Seconds before trying half-open
    success_threshold: int = 3           # Successes in half-open before closing
    half_open_max_attempts: int = 3      # Max attempts in half-open state
    window_size: int = 60                # Time window for failure counting (seconds)
    min_throughput: int = 10             # Min requests before evaluating
    failure_rate_threshold: float = 0.5  # Failure rate to open circuit


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: list = field(default_factory=list)
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    current_state: CircuitState = CircuitState.CLOSED


class CircuitBreaker:
    """Circuit breaker for protecting model API calls"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()

        # Sliding window for tracking recent requests
        self.request_window = deque(maxlen=100)

        # State management
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_state_change = time.time()
        self.half_open_attempts = 0

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        async with self._lock:
            # Check if we should attempt the call
            if not self._should_attempt():
                self.stats.rejected_requests += 1
                raise CircuitOpenError(f"Circuit breaker {self.name} is OPEN")

            # For half-open state, limit attempts
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_attempts += 1

        # Execute the function
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            await self._record_success(time.time() - start_time)
            return result

        except Exception as e:
            await self._record_failure(time.time() - start_time)
            raise

    def _should_attempt(self) -> bool:
        """Check if we should attempt the request"""
        current_time = time.time()

        if self.state == CircuitState.CLOSED:
            return True

        elif self.state == CircuitState.OPEN:
            # Check if we should transition to half-open
            time_since_change = current_time - self.last_state_change
            if time_since_change >= self.config.recovery_timeout:
                self._transition_to_half_open()
                return True
            return False

        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited attempts in half-open state
            return self.half_open_attempts < self.config.half_open_max_attempts

        return False

    async def _record_success(self, response_time: float):
        """Record successful request"""
        async with self._lock:
            current_time = time.time()
            self.stats.total_requests += 1
            self.stats.successful_requests += 1
            self.stats.last_success_time = current_time

            # Add to sliding window
            self.request_window.append({
                'timestamp': current_time,
                'success': True,
                'response_time': response_time
            })

            # Update state based on success
            if self.state == CircuitState.HALF_OPEN:
                self.consecutive_successes += 1
                self.consecutive_failures = 0

                # Check if we should close the circuit
                if self.consecutive_successes >= self.config.success_threshold:
                    self._transition_to_closed()

            elif self.state == CircuitState.CLOSED:
                self.consecutive_failures = 0

    async def _record_failure(self, response_time: float):
        """Record failed request"""
        async with self._lock:
            current_time = time.time()
            self.stats.total_requests += 1
            self.stats.failed_requests += 1
            self.stats.last_failure_time = current_time

            # Add to sliding window
            self.request_window.append({
                'timestamp': current_time,
                'success': False,
                'response_time': response_time
            })

            # Update failure counts
            self.consecutive_failures += 1
            self.consecutive_successes = 0

            # Check if we should open the circuit
            if self.state == CircuitState.CLOSED:
                if self._should_open_circuit():
                    self._transition_to_open()

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                self._transition_to_open()

    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open based on failure criteria"""
        # Check consecutive failures
        if self.consecutive_failures >= self.config.failure_threshold:
            return True

        # Check failure rate in time window
        current_time = time.time()
        window_start = current_time - self.config.window_size

        recent_requests = [
            r for r in self.request_window
            if r['timestamp'] >= window_start
        ]

        if len(recent_requests) >= self.config.min_throughput:
            failure_count = sum(1 for r in recent_requests if not r['success'])
            failure_rate = failure_count / len(recent_requests)

            if failure_rate >= self.config.failure_rate_threshold:
                return True

        return False

    def _transition_to_open(self):
        """Transition to OPEN state"""
        self.state = CircuitState.OPEN
        self.last_state_change = time.time()
        self.half_open_attempts = 0
        self.stats.state_changes.append({
            'timestamp': self.last_state_change,
            'from_state': self.stats.current_state,
            'to_state': CircuitState.OPEN
        })
        self.stats.current_state = CircuitState.OPEN
        print(f"🔴 Circuit breaker {self.name} is now OPEN")

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.half_open_attempts = 0
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.stats.state_changes.append({
            'timestamp': self.last_state_change,
            'from_state': self.stats.current_state,
            'to_state': CircuitState.HALF_OPEN
        })
        self.stats.current_state = CircuitState.HALF_OPEN
        print(f"🟡 Circuit breaker {self.name} is now HALF-OPEN")

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.stats.state_changes.append({
            'timestamp': self.last_state_change,
            'from_state': self.stats.current_state,
            'to_state': CircuitState.CLOSED
        })
        self.stats.current_state = CircuitState.CLOSED
        print(f"🟢 Circuit breaker {self.name} is now CLOSED")

    def is_open(self) -> bool:
        """Check if circuit is open"""
        return self.state == CircuitState.OPEN

    def is_closed(self) -> bool:
        """Check if circuit is closed"""
        return self.state == CircuitState.CLOSED

    def is_half_open(self) -> bool:
        """Check if circuit is half-open"""
        return self.state == CircuitState.HALF_OPEN

    def get_stats(self) -> CircuitBreakerStats:
        """Get current statistics"""
        return self.stats

    def reset(self):
        """Manually reset the circuit breaker"""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.half_open_attempts = 0
        self.last_state_change = time.time()
        self.request_window.clear()
        print(f"♻️ Circuit breaker {self.name} has been reset")

    def force_open(self):
        """Manually force circuit to open state"""
        self._transition_to_open()

    def force_close(self):
        """Manually force circuit to closed state"""
        self._transition_to_closed()


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different models"""

    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        self.default_config = default_config or CircuitBreakerConfig()
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        async with self._lock:
            if name not in self.breakers:
                breaker_config = config or self.default_config
                self.breakers[name] = CircuitBreaker(name, breaker_config)
            return self.breakers[name]

    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all breakers"""
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()

    def get_health_status(self) -> Dict[str, str]:
        """Get health status of all circuits"""
        return {
            name: breaker.state.value
            for name, breaker in self.breakers.items()
        }


class CircuitOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class ModelConnectionPool:
    """Connection pool with circuit breaker protection"""

    def __init__(self, config: Dict[str, Any], breaker_manager: CircuitBreakerManager):
        self.config = config
        self.breaker_manager = breaker_manager
        self.sessions: Dict[str, Any] = {}  # Model-specific sessions

    async def call_model_with_breaker(self, model_name: str, func: Callable, *args, **kwargs) -> Any:
        """Call model function through circuit breaker"""
        breaker = await self.breaker_manager.get_breaker(model_name)

        try:
            return await breaker.call(func, *args, **kwargs)
        except CircuitOpenError:
            # Return None or raise custom error for handling
            print(f"⚠️ Model {model_name} circuit is open, skipping call")
            raise
        except Exception as e:
            # Log the error and re-raise
            print(f"❌ Model {model_name} call failed: {e}")
            raise

    def get_available_models(self) -> list:
        """Get list of models with closed circuits"""
        available = []
        for name, breaker in self.breaker_manager.breakers.items():
            if breaker.is_closed() or breaker.is_half_open():
                available.append(name)
        return available