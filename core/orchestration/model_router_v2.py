"""
Refactored Intelligent Model Router with dependency injection, caching, and circuit breakers.
High-performance routing decisions with < 10ms latency.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import aiohttp

from .types import ModelType, TaskType
from .config import RouterConfig, ModelConfig
from .cache import RoutingCache, CacheInterface, HybridCache
from .circuit_breaker import CircuitBreakerManager, CircuitOpenError, CircuitBreakerConfig
from .metrics import RouterMetrics, MetricsInterface, MetricsCollector
from .model_detector import get_model_detector


@dataclass
class RoutingDecision:
    """Routing decision with all metadata"""
    selected_model: ModelType
    model_name: str
    reasoning: str
    estimated_cost: float
    estimated_time: float
    confidence: float
    cached: bool = False
    fallback_models: List[ModelType] = None


class ModelConnectionPool:
    """Connection pool with circuit breaker protection for each model"""

    def __init__(self, config: RouterConfig, breaker_manager: CircuitBreakerManager):
        self.config = config
        self.breaker_manager = breaker_manager
        self.sessions: Dict[ModelType, aiohttp.ClientSession] = {}
        self.health_status: Dict[ModelType, bool] = {}

    async def initialize(self):
        """Initialize connection sessions"""
        for model_type in ModelType:
            model_config = self.config.get_model_config(model_type)
            if model_config:
                # Create session with appropriate timeout
                timeout = aiohttp.ClientTimeout(total=model_config.timeout)
                self.sessions[model_type] = aiohttp.ClientSession(timeout=timeout)

                # Create circuit breaker for this model
                breaker_config = CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=model_config.timeout * 2,
                    success_threshold=2
                )
                await self.breaker_manager.get_breaker(model_type.value, breaker_config)

    async def get_session(self, model_type: ModelType) -> Optional[aiohttp.ClientSession]:
        """Get session for a model"""
        return self.sessions.get(model_type)

    async def check_health(self, model_type: ModelType) -> bool:
        """Check if model endpoint is healthy"""
        if model_type == ModelType.LOCAL_MLX:
            return await self._check_local_health()

        # For SaaS models, check circuit breaker state
        breaker = await self.breaker_manager.get_breaker(model_type.value)
        return not breaker.is_open()

    async def _check_local_health(self) -> bool:
        """Check local LM Studio health"""
        try:
            session = self.sessions.get(ModelType.LOCAL_MLX)
            if not session:
                return False

            model_config = self.config.get_model_config(ModelType.LOCAL_MLX)
            base_url = model_config.endpoint.replace('/chat/completions', '')

            async with session.get(f"{base_url}/models", timeout=2) as response:
                return response.status == 200
        except:
            return False

    async def call_with_circuit_breaker(self, model_type: ModelType, func, *args, **kwargs):
        """Call function through circuit breaker"""
        breaker = await self.breaker_manager.get_breaker(model_type.value)
        return await breaker.call(func, *args, **kwargs)

    async def cleanup(self):
        """Close all sessions"""
        for session in self.sessions.values():
            await session.close()


class IntelligentModelRouter:
    """High-performance model router with caching and circuit breakers"""

    def __init__(
        self,
        config: Optional[RouterConfig] = None,
        cache: Optional[CacheInterface] = None,
        metrics: Optional[MetricsInterface] = None,
        connection_pool: Optional[ModelConnectionPool] = None
    ):
        # Use provided dependencies or create defaults
        self.config = config or RouterConfig()
        self.cache = None  # Will be initialized in async setup
        self.metrics = metrics or RouterMetrics()
        self.breaker_manager = CircuitBreakerManager()
        self.connection_pool = connection_pool or ModelConnectionPool(self.config, self.breaker_manager)

        # Model detector for local models
        self.model_detector = None
        self.available_local_models = {}

        # Routing cache
        self.routing_cache = None

        # Metrics collector
        self.metrics_collector = MetricsCollector()
        self.metrics_collector.router_metrics = self.metrics

    async def initialize(self):
        """Async initialization of router components"""
        # Initialize cache
        if self.cache is None:
            hybrid_cache = HybridCache(
                redis_url=self.config.cache_config.get("redis_url"),
                memory_size=100
            )
            await hybrid_cache.connect()
            self.cache = hybrid_cache

        self.routing_cache = RoutingCache(self.cache)

        # Initialize connection pool
        await self.connection_pool.initialize()

        # Initialize model detector
        await self._initialize_model_detector()

        # Start metrics collector
        await self.metrics_collector.start()

        print("✅ Model router initialized successfully")

    async def _initialize_model_detector(self):
        """Initialize the model detector and get available models"""
        try:
            self.model_detector = await get_model_detector()
            self.available_local_models = self.model_detector.available_models
        except Exception as e:
            print(f"Warning: Could not initialize model detector: {e}")
            self.available_local_models = {}

    async def route_task(
        self,
        objective: str,
        task_type: TaskType,
        complexity: int = 5,
        context: Dict[str, Any] = None
    ) -> RoutingDecision:
        """
        Main routing logic with caching and performance optimization.
        Target: < 10ms routing decision time.
        """
        start_time = time.time()
        context = context or {}

        # Check for forced routing (debugging/testing)
        if "force_model" in context:
            return await self._create_forced_decision(context["force_model"], task_type)

        # Generate cache key
        cache_key = RoutingCache.create_task_hash(objective, task_type, complexity, context)

        # Check cache first
        cached_decision = await self.routing_cache.get_cached_decision(cache_key)
        if cached_decision:
            self.metrics_collector.aggregated_metrics.record_cache_hit()
            decision = self._deserialize_decision(cached_decision)
            decision.cached = True

            # Record metrics
            routing_time = (time.time() - start_time) * 1000  # Convert to ms
            print(f"⚡ Cached routing decision in {routing_time:.2f}ms")
            return decision

        self.metrics_collector.aggregated_metrics.record_cache_miss()

        # Perform routing calculation
        decision = await self._calculate_routing_decision(
            objective, task_type, complexity, context
        )

        # Cache the decision
        await self.routing_cache.cache_decision(
            cache_key,
            self._serialize_decision(decision),
            ttl=self.config.cache_config.get("ttl", 3600)
        )

        # Record metrics
        routing_time = (time.time() - start_time) * 1000  # Convert to ms
        await self.metrics.record_response(
            "routing",
            routing_time / 1000,  # Convert back to seconds for metrics
            True
        )

        # Record routing decision
        self.metrics_collector.aggregated_metrics.record_routing_decision({
            'task_type': task_type.value,
            'complexity': complexity,
            'selected_model': decision.selected_model.value,
            'routing_time_ms': routing_time
        })

        print(f"🎯 Routing decision in {routing_time:.2f}ms: {decision.selected_model.value}")
        return decision

    async def _calculate_routing_decision(
        self,
        objective: str,
        task_type: TaskType,
        complexity: int,
        context: Dict[str, Any]
    ) -> RoutingDecision:
        """Calculate optimal routing decision"""
        # Get preferred models for task type
        preferred_models = self.config.get_preferred_models(task_type)

        # Filter by available models (circuit breaker status)
        available_models = await self._get_available_models(preferred_models)

        if not available_models:
            # All preferred models are down, use fallback
            return await self._create_fallback_decision(task_type)

        # Simple tasks - use local if available
        if complexity <= 3 and ModelType.LOCAL_MLX in available_models:
            if await self.connection_pool.check_health(ModelType.LOCAL_MLX):
                return RoutingDecision(
                    selected_model=ModelType.LOCAL_MLX,
                    model_name=await self._get_model_name(ModelType.LOCAL_MLX, task_type),
                    reasoning=f"Local model optimal for simple task (complexity={complexity})",
                    estimated_cost=0.0,
                    estimated_time=2.0,
                    confidence=0.9,
                    fallback_models=available_models[1:3]
                )

        # Check for escalation conditions
        if await self._should_escalate(context, complexity):
            escalated_model = await self._select_escalation_model(
                preferred_models[0] if preferred_models else ModelType.LOCAL_MLX,
                task_type,
                available_models
            )
            return RoutingDecision(
                selected_model=escalated_model,
                model_name=await self._get_model_name(escalated_model, task_type),
                reasoning=f"Escalated due to failures or complexity",
                estimated_cost=self._estimate_cost(escalated_model, objective),
                estimated_time=3.0,
                confidence=0.85,
                fallback_models=[m for m in available_models if m != escalated_model][:2]
            )

        # Complex tasks - use best available model
        if complexity >= 7:
            best_model = await self._select_best_model_for_complexity(
                task_type, complexity, available_models
            )
            return RoutingDecision(
                selected_model=best_model,
                model_name=await self._get_model_name(best_model, task_type),
                reasoning=f"Selected for complex task (complexity={complexity})",
                estimated_cost=self._estimate_cost(best_model, objective),
                estimated_time=4.0,
                confidence=0.9,
                fallback_models=[m for m in available_models if m != best_model][:2]
            )

        # Default to first available preferred model
        default_model = available_models[0]
        return RoutingDecision(
            selected_model=default_model,
            model_name=await self._get_model_name(default_model, task_type),
            reasoning=f"Default selection for {task_type.value}",
            estimated_cost=self._estimate_cost(default_model, objective),
            estimated_time=2.5,
            confidence=0.75,
            fallback_models=available_models[1:3]
        )

    async def _get_available_models(self, preferred_models: List[ModelType]) -> List[ModelType]:
        """Get available models based on circuit breaker status"""
        available = []
        for model in preferred_models:
            breaker = await self.breaker_manager.get_breaker(model.value)
            if not breaker.is_open():
                available.append(model)
        return available

    async def _should_escalate(self, context: Dict[str, Any], complexity: int) -> bool:
        """Check if we should escalate to a different model"""
        # Check for repeated failures
        local_failures = context.get("local_failures", 0)
        if local_failures >= 2:
            self.metrics_collector.aggregated_metrics.record_escalation(
                "local", "saas"
            )
            return True

        # Check complexity threshold
        if complexity >= self.config.escalation_rules[0].complexity_threshold:
            return True

        return False

    async def _select_escalation_model(
        self,
        from_model: ModelType,
        task_type: TaskType,
        available_models: List[ModelType]
    ) -> ModelType:
        """Select model for escalation"""
        # Try to find configured escalation path
        escalation_target = self.config.get_escalation_path(from_model, task_type)

        if escalation_target and escalation_target in available_models:
            return escalation_target

        # Fallback to best available SaaS model
        saas_models = [m for m in available_models if m != ModelType.LOCAL_MLX]
        if saas_models:
            return saas_models[0]

        # Last resort - return any available model
        return available_models[0] if available_models else ModelType.LOCAL_MLX

    async def _select_best_model_for_complexity(
        self,
        task_type: TaskType,
        complexity: int,
        available_models: List[ModelType]
    ) -> ModelType:
        """Select best model for complex tasks"""
        # Prioritize based on task type
        if task_type in [TaskType.REASONING, TaskType.ANALYSIS]:
            if ModelType.CLAUDE in available_models:
                return ModelType.CLAUDE
            if ModelType.GEMINI in available_models:
                return ModelType.GEMINI

        if task_type == TaskType.CODE_GENERATION:
            if ModelType.OPENAI in available_models:
                return ModelType.OPENAI
            if ModelType.CLAUDE in available_models:
                return ModelType.CLAUDE

        # Default to first available
        return available_models[0]

    async def _get_model_name(self, model_type: ModelType, task_type: TaskType) -> str:
        """Get actual model name for API calls"""
        if model_type == ModelType.LOCAL_MLX and self.model_detector:
            # Use dynamic detection for local models
            best_model = self.model_detector.get_best_model_for_task(
                task_type.value, 5
            )
            if best_model:
                return best_model

        # Use configured model name
        model_config = self.config.get_model_config(model_type)
        return model_config.model_name if model_config else "unknown"

    def _estimate_cost(self, model_type: ModelType, objective: str) -> float:
        """Estimate cost based on objective length and model pricing"""
        estimated_tokens = len(objective.split()) * 1.5  # Rough estimation
        model_config = self.config.get_model_config(model_type)

        if model_config:
            # Assume 50/50 input/output ratio
            input_cost = estimated_tokens * 0.5 * model_config.cost_per_input_token
            output_cost = estimated_tokens * 0.5 * model_config.cost_per_output_token
            return input_cost + output_cost

        return 0.0

    async def _create_forced_decision(self, forced_model: str, task_type: TaskType) -> RoutingDecision:
        """Create a forced routing decision"""
        model_type = ModelType(forced_model)
        return RoutingDecision(
            selected_model=model_type,
            model_name=await self._get_model_name(model_type, task_type),
            reasoning="Forced routing via context",
            estimated_cost=0.0,
            estimated_time=1.0,
            confidence=1.0,
            cached=False
        )

    async def _create_fallback_decision(self, task_type: TaskType) -> RoutingDecision:
        """Create fallback decision when all models are down"""
        return RoutingDecision(
            selected_model=ModelType.LOCAL_MLX,
            model_name="fallback",
            reasoning="All preferred models unavailable",
            estimated_cost=0.0,
            estimated_time=5.0,
            confidence=0.5,
            cached=False
        )

    def _serialize_decision(self, decision: RoutingDecision) -> Dict[str, Any]:
        """Serialize routing decision for caching"""
        data = asdict(decision)
        data['selected_model'] = decision.selected_model.value
        if decision.fallback_models:
            data['fallback_models'] = [m.value for m in decision.fallback_models]
        return data

    def _deserialize_decision(self, data: Dict[str, Any]) -> RoutingDecision:
        """Deserialize routing decision from cache"""
        data['selected_model'] = ModelType(data['selected_model'])
        if 'fallback_models' in data and data['fallback_models']:
            data['fallback_models'] = [ModelType(m) for m in data['fallback_models']]
        return RoutingDecision(**data)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current router metrics"""
        return self.metrics_collector.get_dashboard_data()

    async def cleanup(self):
        """Cleanup resources"""
        await self.metrics_collector.stop()
        await self.connection_pool.cleanup()
        if hasattr(self.cache, 'disconnect'):
            await self.cache.disconnect()


class ModelRouterFactory:
    """Factory for creating configured model routers"""

    @staticmethod
    async def create(
        config_path: Optional[str] = None,
        use_redis: bool = True,
        metrics_enabled: bool = True
    ) -> IntelligentModelRouter:
        """Create and initialize a model router"""
        # Load configuration
        config = RouterConfig(config_path) if config_path else RouterConfig()

        # Create cache
        cache = None
        if use_redis and config.cache_config.get("redis_url"):
            cache = HybridCache(
                redis_url=config.cache_config["redis_url"],
                memory_size=100
            )
            await cache.connect()

        # Create metrics
        metrics = RouterMetrics() if metrics_enabled else None

        # Create router
        router = IntelligentModelRouter(
            config=config,
            cache=cache,
            metrics=metrics
        )

        # Initialize
        await router.initialize()

        return router

    @staticmethod
    async def create_test_router() -> IntelligentModelRouter:
        """Create a test router with in-memory cache"""
        from .cache import InMemoryCache

        config = RouterConfig()
        cache = InMemoryCache()
        metrics = RouterMetrics()

        router = IntelligentModelRouter(
            config=config,
            cache=cache,
            metrics=metrics
        )

        await router.initialize()
        return router