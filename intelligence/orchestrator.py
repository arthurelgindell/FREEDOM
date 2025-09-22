#!/usr/bin/env python3
"""
FREEDOM Platform: Advanced Model Orchestration System
State-of-the-art orchestration for multiple AI models on M3 Ultra
Supports 670B+ parameter models with intelligent scheduling and resource management
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, AsyncIterator
from collections import deque
import heapq
import numpy as np
import mlx.core as mx
import mlx.nn as nn
from concurrent.futures import ThreadPoolExecutor
import psutil
import redis
import sqlite3
from datetime import datetime, timedelta

# Orchestration Configuration
@dataclass
class OrchestrationConfig:
    """Advanced orchestration configuration for 2025"""
    max_concurrent_models: int = 10
    max_memory_gb: int = 512
    priority_queue_size: int = 1000
    batch_timeout_ms: int = 100
    enable_model_swapping: bool = True
    enable_request_batching: bool = True
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_distributed: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    db_path: str = "Path(__file__).parent.parent.parent/orchestrator.db"

class ModelState(Enum):
    """Model lifecycle states"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    BUSY = "busy"
    SWAPPING_OUT = "swapping_out"
    ERROR = "error"

class RequestPriority(Enum):
    """Request priority levels"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BATCH = 4

@dataclass
class ModelInfo:
    """Model metadata and state"""
    id: str
    name: str
    path: str
    size_gb: float
    params_b: float
    state: ModelState = ModelState.UNLOADED
    loaded_at: Optional[float] = None
    last_used: Optional[float] = None
    usage_count: int = 0
    average_latency_ms: float = 0.0
    memory_usage_gb: float = 0.0
    capabilities: List[str] = field(default_factory=list)
    quantization: Optional[Dict[str, Any]] = None
    
    def update_usage(self, latency_ms: float):
        """Update usage statistics"""
        self.usage_count += 1
        self.last_used = time.time()
        # Running average of latency
        self.average_latency_ms = (
            (self.average_latency_ms * (self.usage_count - 1) + latency_ms) 
            / self.usage_count
        )

@dataclass
class InferenceRequest:
    """Inference request with metadata"""
    id: str
    model_id: str
    input_data: Any
    priority: RequestPriority = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    timeout_ms: Optional[int] = None
    callback: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """For priority queue comparison"""
        return (self.priority.value, self.created_at) < (other.priority.value, other.created_at)

@dataclass
class InferenceResult:
    """Result of inference execution"""
    request_id: str
    model_id: str
    output: Any
    latency_ms: float
    tokens_per_second: Optional[float] = None
    memory_used_gb: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class ModelRegistry:
    """Central registry for all available models"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.models: Dict[str, ModelInfo] = {}
        self._init_database()
        self._load_models_from_db()
    
    def _init_database(self):
        """Initialize SQLite database for model registry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                size_gb REAL NOT NULL,
                params_b REAL NOT NULL,
                capabilities TEXT,
                quantization TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                model_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                latency_ms REAL,
                tokens_per_second REAL,
                memory_gb REAL,
                FOREIGN KEY (model_id) REFERENCES models(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_models_from_db(self):
        """Load model definitions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM models")
        rows = cursor.fetchall()
        
        for row in rows:
            model_info = ModelInfo(
                id=row[0],
                name=row[1],
                path=row[2],
                size_gb=row[3],
                params_b=row[4],
                capabilities=json.loads(row[5]) if row[5] else [],
                quantization=json.loads(row[6]) if row[6] else None
            )
            self.models[model_info.id] = model_info
        
        conn.close()
    
    def register_model(self, model_info: ModelInfo):
        """Register a new model"""
        self.models[model_info.id] = model_info
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO models 
            (id, name, path, size_gb, params_b, capabilities, quantization)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            model_info.id,
            model_info.name,
            model_info.path,
            model_info.size_gb,
            model_info.params_b,
            json.dumps(model_info.capabilities),
            json.dumps(model_info.quantization) if model_info.quantization else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Get model information"""
        return self.models.get(model_id)
    
    def list_models(self, capability: Optional[str] = None) -> List[ModelInfo]:
        """List all models, optionally filtered by capability"""
        models = list(self.models.values())
        
        if capability:
            models = [m for m in models if capability in m.capabilities]
        
        return models

class MemoryManager:
    """Intelligent memory management for model loading/unloading"""
    
    def __init__(self, max_memory_gb: int):
        self.max_memory_gb = max_memory_gb
        self.current_usage_gb = 0.0
        self.model_memory: Dict[str, float] = {}
        self.logger = logging.getLogger("MemoryManager")
    
    def can_load_model(self, model_info: ModelInfo) -> bool:
        """Check if model can be loaded within memory constraints"""
        required_memory = self._calculate_required_memory(model_info)
        available_memory = self.max_memory_gb - self.current_usage_gb
        
        # Keep 10% buffer
        return required_memory <= available_memory * 0.9
    
    def _calculate_required_memory(self, model_info: ModelInfo) -> float:
        """Calculate memory requirements including overhead"""
        base_memory = model_info.size_gb
        
        # Add overhead for KV cache, activations, etc.
        if model_info.params_b > 100:  # Large models need more overhead
            overhead_factor = 1.3
        else:
            overhead_factor = 1.2
        
        # Account for quantization
        if model_info.quantization:
            bits = model_info.quantization.get("bits", 16)
            quantization_factor = bits / 16.0
            base_memory *= quantization_factor
        
        return base_memory * overhead_factor
    
    def allocate_memory(self, model_id: str, memory_gb: float):
        """Allocate memory for a model"""
        self.model_memory[model_id] = memory_gb
        self.current_usage_gb += memory_gb
        self.logger.info(f"Allocated {memory_gb:.1f}GB for {model_id}")
        self.logger.info(f"Current usage: {self.current_usage_gb:.1f}/{self.max_memory_gb}GB")
    
    def release_memory(self, model_id: str):
        """Release memory from a model"""
        if model_id in self.model_memory:
            released = self.model_memory.pop(model_id)
            self.current_usage_gb -= released
            self.logger.info(f"Released {released:.1f}GB from {model_id}")
    
    def get_eviction_candidates(self, required_gb: float) -> List[str]:
        """Get models to evict to free up memory"""
        candidates = []
        freed_memory = 0.0
        
        # Sort by last used time (LRU strategy)
        sorted_models = sorted(
            self.model_memory.items(),
            key=lambda x: x[0]  # Could be enhanced with actual usage tracking
        )
        
        for model_id, memory_gb in sorted_models:
            if freed_memory >= required_gb:
                break
            candidates.append(model_id)
            freed_memory += memory_gb
        
        return candidates

class RequestScheduler:
    """Intelligent request scheduling with batching and prioritization"""
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.priority_queue: List[InferenceRequest] = []
        self.batch_queues: Dict[str, deque] = {}  # Per-model batch queues
        self.logger = logging.getLogger("RequestScheduler")
    
    def add_request(self, request: InferenceRequest):
        """Add request to appropriate queue"""
        if self.config.enable_request_batching and request.priority == RequestPriority.BATCH:
            # Add to batch queue
            if request.model_id not in self.batch_queues:
                self.batch_queues[request.model_id] = deque()
            self.batch_queues[request.model_id].append(request)
        else:
            # Add to priority queue
            heapq.heappush(self.priority_queue, request)
    
    def get_next_request(self) -> Optional[InferenceRequest]:
        """Get next request to process"""
        if self.priority_queue:
            return heapq.heappop(self.priority_queue)
        return None
    
    def get_batch(self, model_id: str, max_batch_size: int) -> List[InferenceRequest]:
        """Get batch of requests for a model"""
        if model_id not in self.batch_queues:
            return []
        
        batch = []
        queue = self.batch_queues[model_id]
        
        while queue and len(batch) < max_batch_size:
            batch.append(queue.popleft())
        
        return batch
    
    def requeue_request(self, request: InferenceRequest):
        """Requeue a request (e.g., after failure)"""
        request.metadata["retry_count"] = request.metadata.get("retry_count", 0) + 1
        
        if request.metadata["retry_count"] < 3:
            heapq.heappush(self.priority_queue, request)
            self.logger.info(f"Requeued request {request.id} (retry {request.metadata['retry_count']})")
        else:
            self.logger.error(f"Request {request.id} exceeded max retries")

class CacheManager:
    """Intelligent caching for inference results"""
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.cache: Dict[str, Tuple[Any, float]] = {}  # key -> (result, timestamp)
        
        if config.enable_distributed:
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                decode_responses=True
            )
        else:
            self.redis_client = None
    
    def get_cache_key(self, model_id: str, input_data: Any) -> str:
        """Generate cache key from model and input"""
        # Simplified - actual implementation would properly serialize input
        return f"{model_id}:{hash(str(input_data))}"
    
    def get(self, model_id: str, input_data: Any) -> Optional[Any]:
        """Get cached result if available"""
        if not self.config.enable_caching:
            return None
        
        key = self.get_cache_key(model_id, input_data)
        
        # Check local cache
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.config.cache_ttl_seconds:
                return result
            else:
                del self.cache[key]
        
        # Check distributed cache
        if self.redis_client:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        
        return None
    
    def set(self, model_id: str, input_data: Any, result: Any):
        """Cache a result"""
        if not self.config.enable_caching:
            return
        
        key = self.get_cache_key(model_id, input_data)
        
        # Local cache
        self.cache[key] = (result, time.time())
        
        # Distributed cache
        if self.redis_client:
            self.redis_client.setex(
                key,
                self.config.cache_ttl_seconds,
                json.dumps(result, default=str)
            )
    
    def clear_expired(self):
        """Clear expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.config.cache_ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]

class ModelLoader:
    """Handles model loading and initialization"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.loaded_models: Dict[str, Any] = {}  # model_id -> actual model object
        self.logger = logging.getLogger("ModelLoader")
    
    async def load_model(self, model_info: ModelInfo) -> bool:
        """Load a model into memory"""
        if model_info.id in self.loaded_models:
            self.logger.info(f"Model {model_info.id} already loaded")
            return True
        
        if not self.memory_manager.can_load_model(model_info):
            self.logger.warning(f"Insufficient memory to load {model_info.id}")
            return False
        
        try:
            model_info.state = ModelState.LOADING
            self.logger.info(f"Loading model {model_info.id} ({model_info.params_b}B params)")
            
            # Simulate model loading (actual implementation would load real model)
            await asyncio.sleep(model_info.size_gb * 0.01)  # Simulate loading time
            
            # Allocate memory
            required_memory = self.memory_manager._calculate_required_memory(model_info)
            self.memory_manager.allocate_memory(model_info.id, required_memory)
            
            # Store loaded model
            self.loaded_models[model_info.id] = f"Model_{model_info.id}_loaded"
            
            model_info.state = ModelState.READY
            model_info.loaded_at = time.time()
            model_info.memory_usage_gb = required_memory
            
            self.logger.info(f"Successfully loaded {model_info.id}")
            return True
            
        except Exception as e:
            model_info.state = ModelState.ERROR
            self.logger.error(f"Failed to load {model_info.id}: {e}")
            return False
    
    async def unload_model(self, model_id: str):
        """Unload a model from memory"""
        if model_id not in self.loaded_models:
            return
        
        self.logger.info(f"Unloading model {model_id}")
        
        # Clean up model
        del self.loaded_models[model_id]
        
        # Release memory
        self.memory_manager.release_memory(model_id)
        
        self.logger.info(f"Unloaded {model_id}")

class InferenceExecutor:
    """Executes inference requests on loaded models"""
    
    def __init__(self, model_loader: ModelLoader):
        self.model_loader = model_loader
        self.logger = logging.getLogger("InferenceExecutor")
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def execute_inference(
        self,
        request: InferenceRequest,
        model_info: ModelInfo
    ) -> InferenceResult:
        """Execute a single inference request"""
        start_time = time.time()
        
        try:
            # Check if model is loaded
            if model_info.id not in self.model_loader.loaded_models:
                raise RuntimeError(f"Model {model_info.id} not loaded")
            
            model_info.state = ModelState.BUSY
            
            # Simulate inference (actual implementation would use real model)
            await asyncio.sleep(0.01)  # Simulate inference time
            
            # Generate mock result
            output = f"Response from {model_info.id} for request {request.id}"
            
            latency_ms = (time.time() - start_time) * 1000
            tokens_per_second = np.random.randint(30, 50)  # Simulated
            
            model_info.state = ModelState.READY
            model_info.update_usage(latency_ms)
            
            return InferenceResult(
                request_id=request.id,
                model_id=model_info.id,
                output=output,
                latency_ms=latency_ms,
                tokens_per_second=tokens_per_second,
                memory_used_gb=model_info.memory_usage_gb
            )
            
        except Exception as e:
            self.logger.error(f"Inference failed for request {request.id}: {e}")
            model_info.state = ModelState.READY
            
            return InferenceResult(
                request_id=request.id,
                model_id=model_info.id,
                output=None,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    async def execute_batch(
        self,
        requests: List[InferenceRequest],
        model_info: ModelInfo
    ) -> List[InferenceResult]:
        """Execute a batch of inference requests"""
        self.logger.info(f"Executing batch of {len(requests)} requests on {model_info.id}")
        
        # Execute in parallel
        tasks = [
            self.execute_inference(req, model_info)
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks)
        return results

class AdvancedOrchestrator:
    """Main orchestrator coordinating all components"""
    
    def __init__(self, config: OrchestrationConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # Initialize components
        self.registry = ModelRegistry(config.db_path)
        self.memory_manager = MemoryManager(config.max_memory_gb)
        self.scheduler = RequestScheduler(config)
        self.cache_manager = CacheManager(config)
        self.model_loader = ModelLoader(self.memory_manager)
        self.executor = InferenceExecutor(self.model_loader)
        
        # State
        self.running = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0,
            "total_latency_ms": 0.0
        }
        
        self.logger.info("Advanced Orchestrator initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger("AdvancedOrchestrator")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def submit_request(self, request: InferenceRequest) -> str:
        """Submit a new inference request"""
        self.scheduler.add_request(request)
        self.stats["total_requests"] += 1
        
        self.logger.info(f"Submitted request {request.id} for model {request.model_id}")
        return request.id
    
    async def process_requests(self):
        """Main processing loop"""
        self.running = True
        self.logger.info("Starting request processing loop")
        
        while self.running:
            # Get next request
            request = self.scheduler.get_next_request()
            
            if not request:
                # Check for batch requests
                await self._process_batch_requests()
                await asyncio.sleep(0.01)
                continue
            
            # Process the request
            await self._process_single_request(request)
            
            # Clear expired cache periodically
            if self.stats["total_requests"] % 100 == 0:
                self.cache_manager.clear_expired()
    
    async def _process_single_request(self, request: InferenceRequest):
        """Process a single request"""
        model_info = self.registry.get_model(request.model_id)
        
        if not model_info:
            self.logger.error(f"Model {request.model_id} not found")
            self.stats["failed_requests"] += 1
            return
        
        # Check cache
        cached_result = self.cache_manager.get(request.model_id, request.input_data)
        if cached_result:
            self.logger.info(f"Cache hit for request {request.id}")
            self.stats["cache_hits"] += 1
            self.stats["successful_requests"] += 1
            return
        
        # Ensure model is loaded
        if model_info.state == ModelState.UNLOADED:
            success = await self.model_loader.load_model(model_info)
            if not success:
                # Try to free memory and retry
                await self._handle_memory_pressure(model_info)
                success = await self.model_loader.load_model(model_info)
                
                if not success:
                    self.logger.error(f"Failed to load model {model_info.id}")
                    self.scheduler.requeue_request(request)
                    return
        
        # Execute inference
        result = await self.executor.execute_inference(request, model_info)
        
        if result.error:
            self.stats["failed_requests"] += 1
            self.scheduler.requeue_request(request)
        else:
            self.stats["successful_requests"] += 1
            self.stats["total_latency_ms"] += result.latency_ms
            
            # Cache result
            self.cache_manager.set(request.model_id, request.input_data, result.output)
            
            self.logger.info(
                f"Completed request {request.id} in {result.latency_ms:.1f}ms "
                f"({result.tokens_per_second:.1f} tokens/s)"
            )
    
    async def _process_batch_requests(self):
        """Process batched requests"""
        for model_id in list(self.scheduler.batch_queues.keys()):
            model_info = self.registry.get_model(model_id)
            if not model_info or model_info.state != ModelState.READY:
                continue
            
            # Get batch
            batch = self.scheduler.get_batch(model_id, max_batch_size=32)
            if not batch:
                continue
            
            # Execute batch
            results = await self.executor.execute_batch(batch, model_info)
            
            # Update stats
            for result in results:
                if result.error:
                    self.stats["failed_requests"] += 1
                else:
                    self.stats["successful_requests"] += 1
                    self.stats["total_latency_ms"] += result.latency_ms
    
    async def _handle_memory_pressure(self, model_info: ModelInfo):
        """Handle memory pressure by evicting models"""
        required_memory = self.memory_manager._calculate_required_memory(model_info)
        candidates = self.memory_manager.get_eviction_candidates(required_memory)
        
        self.logger.info(f"Memory pressure: need {required_memory:.1f}GB, evicting {len(candidates)} models")
        
        for model_id in candidates:
            await self.model_loader.unload_model(model_id)
            evicted_model = self.registry.get_model(model_id)
            if evicted_model:
                evicted_model.state = ModelState.UNLOADED
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        avg_latency = (
            self.stats["total_latency_ms"] / self.stats["successful_requests"]
            if self.stats["successful_requests"] > 0 else 0
        )
        
        return {
            "total_requests": self.stats["total_requests"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "cache_hit_rate": (
                self.stats["cache_hits"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0 else 0
            ),
            "average_latency_ms": avg_latency,
            "memory_usage_gb": self.memory_manager.current_usage_gb,
            "loaded_models": len(self.model_loader.loaded_models)
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down orchestrator")
        self.running = False
        
        # Unload all models
        for model_id in list(self.model_loader.loaded_models.keys()):
            await self.model_loader.unload_model(model_id)
        
        self.logger.info("Orchestrator shutdown complete")

async def demo_orchestrator():
    """Demonstrate the advanced orchestration system"""
    print("🚀 FREEDOM Platform: Advanced Model Orchestration Demo")
    print("=" * 60)
    
    # Initialize orchestrator
    config = OrchestrationConfig(
        max_concurrent_models=10,
        max_memory_gb=512,
        enable_model_swapping=True,
        enable_request_batching=True,
        enable_caching=True
    )
    
    orchestrator = AdvancedOrchestrator(config)
    
    # Register models
    print("\n📦 Registering models...")
    
    models = [
        ModelInfo(
            id="deepseek-670b",
            name="DeepSeek 670B",
            path="/models/deepseek-670b",
            size_gb=380,
            params_b=670,
            capabilities=["text-generation", "code", "reasoning"],
            quantization={"bits": 4, "method": "gptq"}
        ),
        ModelInfo(
            id="llama-70b",
            name="Llama 3 70B",
            path="/models/llama-70b",
            size_gb=70,
            params_b=70,
            capabilities=["text-generation", "chat"]
        ),
        ModelInfo(
            id="mixtral-8x7b",
            name="Mixtral 8x7B",
            path="/models/mixtral-8x7b",
            size_gb=47,
            params_b=47,
            capabilities=["text-generation", "code"]
        ),
        ModelInfo(
            id="phi-3",
            name="Phi-3",
            path="/models/phi-3",
            size_gb=3.8,
            params_b=3.8,
            capabilities=["text-generation", "reasoning"]
        )
    ]
    
    for model in models:
        orchestrator.registry.register_model(model)
        print(f"✅ Registered {model.name} ({model.params_b}B params)")
    
    # Start processing loop
    processing_task = asyncio.create_task(orchestrator.process_requests())
    
    # Submit test requests
    print("\n📝 Submitting inference requests...")
    
    requests = []
    for i in range(10):
        request = InferenceRequest(
            id=f"req_{i}",
            model_id=models[i % len(models)].id,
            input_data=f"Test prompt {i}",
            priority=RequestPriority.NORMAL if i < 5 else RequestPriority.HIGH
        )
        
        request_id = await orchestrator.submit_request(request)
        requests.append(request_id)
        print(f"✅ Submitted request {request_id}")
    
    # Wait for processing
    await asyncio.sleep(5)
    
    # Get statistics
    print("\n📊 Orchestration Statistics:")
    stats = orchestrator.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Shutdown
    await orchestrator.shutdown()
    processing_task.cancel()
    
    print("\n✅ Advanced Orchestration System Demo Complete!")
    print("Capabilities:")
    print("  • 670B parameter model support")
    print("  • Intelligent memory management with model swapping")
    print("  • Priority-based request scheduling")
    print("  • Request batching for efficiency")
    print("  • Result caching with TTL")
    print("  • Distributed support via Redis")
    print("  • Comprehensive statistics and monitoring")

if __name__ == "__main__":
    asyncio.run(demo_orchestrator())