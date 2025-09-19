#!/usr/bin/env python3
"""
MLX Resource Management Module
Handles memory allocation, model lifecycle, and resource optimization
"""

import asyncio
import time
import psutil
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

from .config import MLXConfig, get_config


@dataclass
class ModelAllocation:
    """Tracks resource allocation for a model"""
    model_id: str
    size_gb: float
    allocated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    priority: int = 0  # Higher priority models are kept in memory longer
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = time.time()
        self.access_count += 1


class MemoryManager:
    """Manages unified memory allocation for models"""
    
    def __init__(self, config: Optional[MLXConfig] = None):
        self.config = config or get_config()
        self.allocations: OrderedDict[str, ModelAllocation] = OrderedDict()
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Track system memory
        self._update_system_memory()
    
    def _update_system_memory(self):
        """Update system memory statistics"""
        mem = psutil.virtual_memory()
        self.system_total_gb = mem.total / (1024**3)
        self.system_available_gb = mem.available / (1024**3)
        self.system_used_percent = mem.percent
    
    @property
    def allocated_gb(self) -> float:
        """Total allocated memory in GB"""
        return sum(alloc.size_gb for alloc in self.allocations.values())
    
    @property
    def available_gb(self) -> float:
        """Available memory in GB"""
        return self.config.available_memory_gb - self.allocated_gb
    
    def calculate_requirements(self, model_size_b: float, overhead_factor: float = 1.2) -> float:
        """Calculate memory requirements for a model"""
        # Base memory from parameters
        bytes_per_param = self.config.quantization_bits / 8
        base_memory_gb = (model_size_b * 1e9 * bytes_per_param) / (1024**3)
        
        # Adjust overhead based on model size
        if model_size_b > 100:  # Large models need more overhead
            overhead_factor = 1.3
        
        # Include KV cache overhead
        kv_cache_gb = self._estimate_kv_cache_size(model_size_b)
        
        return (base_memory_gb + kv_cache_gb) * overhead_factor
    
    def _estimate_kv_cache_size(self, model_size_b: float) -> float:
        """Estimate KV cache size for a model"""
        # Rough estimate: 10% of model size for KV cache at max context
        context_factor = self.config.max_context_length / 128000  # Normalize to 128K
        return model_size_b * 0.1 * context_factor
    
    async def can_allocate(self, required_gb: float) -> bool:
        """Check if memory can be allocated"""
        async with self._lock:
            return required_gb <= self.available_gb
    
    async def allocate_model(self, model_id: str, size_gb: float, priority: int = 0) -> ModelAllocation:
        """Allocate memory for a model"""
        async with self._lock:
            if model_id in self.allocations:
                # Model already allocated, update access
                allocation = self.allocations[model_id]
                allocation.update_access()
                return allocation
            
            if size_gb > self.available_gb:
                raise MemoryError(
                    f"Insufficient memory: need {size_gb:.1f}GB, "
                    f"have {self.available_gb:.1f}GB available"
                )
            
            allocation = ModelAllocation(
                model_id=model_id,
                size_gb=size_gb,
                priority=priority
            )
            
            self.allocations[model_id] = allocation
            self.logger.info(
                f"Allocated {size_gb:.1f}GB for model {model_id} "
                f"({self.allocated_gb:.1f}/{self.config.available_memory_gb:.1f}GB used)"
            )
            
            return allocation
    
    async def release_model(self, model_id: str) -> Optional[float]:
        """Release memory allocation for a model"""
        async with self._lock:
            if model_id not in self.allocations:
                return None
            
            allocation = self.allocations.pop(model_id)
            self.logger.info(
                f"Released {allocation.size_gb:.1f}GB from model {model_id} "
                f"({self.allocated_gb:.1f}/{self.config.available_memory_gb:.1f}GB used)"
            )
            
            return allocation.size_gb
    
    async def get_eviction_candidates(self, required_gb: float) -> List[str]:
        """Get models to evict to free required memory"""
        async with self._lock:
            candidates = []
            freed_gb = 0.0
            
            # Sort by priority (ascending) and last accessed time (ascending)
            sorted_allocs = sorted(
                self.allocations.items(),
                key=lambda x: (x[1].priority, x[1].last_accessed)
            )
            
            for model_id, allocation in sorted_allocs:
                if freed_gb >= required_gb:
                    break
                
                candidates.append(model_id)
                freed_gb += allocation.size_gb
            
            return candidates
    
    async def evict_lru_model(self) -> Optional[str]:
        """Evict least recently used model"""
        async with self._lock:
            if not self.allocations:
                return None
            
            # Find LRU model with lowest priority
            lru_model = min(
                self.allocations.items(),
                key=lambda x: (x[1].priority, x[1].last_accessed)
            )
            
            model_id = lru_model[0]
            allocation = self.allocations.pop(model_id)
            
            self.logger.info(
                f"Evicted LRU model {model_id} (freed {allocation.size_gb:.1f}GB)"
            )
            
            return model_id
    
    def get_allocation_stats(self) -> Dict[str, any]:
        """Get memory allocation statistics"""
        self._update_system_memory()
        
        return {
            "allocated_gb": self.allocated_gb,
            "available_gb": self.available_gb,
            "total_gb": self.config.available_memory_gb,
            "utilization_percent": (self.allocated_gb / self.config.available_memory_gb) * 100,
            "num_models": len(self.allocations),
            "system_memory": {
                "total_gb": self.system_total_gb,
                "available_gb": self.system_available_gb,
                "used_percent": self.system_used_percent
            },
            "models": [
                {
                    "id": model_id,
                    "size_gb": alloc.size_gb,
                    "age_seconds": time.time() - alloc.allocated_at,
                    "access_count": alloc.access_count,
                    "priority": alloc.priority
                }
                for model_id, alloc in self.allocations.items()
            ]
        }


class ResourceMonitor:
    """Monitors system resources and provides optimization recommendations"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(__name__)
        self._monitoring = False
        self._monitor_task = None
    
    async def start_monitoring(self, interval_seconds: int = 60):
        """Start resource monitoring"""
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        self.logger.info(f"Started resource monitoring (interval: {interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped resource monitoring")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                await self._check_resources()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")
                await asyncio.sleep(interval)
    
    async def _check_resources(self):
        """Check system resources and log warnings"""
        stats = self.memory_manager.get_allocation_stats()
        
        # Check memory pressure
        if stats["utilization_percent"] > 90:
            self.logger.warning(
                f"High memory utilization: {stats['utilization_percent']:.1f}%"
            )
        
        # Check system memory
        if stats["system_memory"]["used_percent"] > 95:
            self.logger.warning(
                f"Critical system memory usage: {stats['system_memory']['used_percent']:.1f}%"
            )
        
        # Check for idle models
        current_time = time.time()
        for model in stats["models"]:
            if model["age_seconds"] > 3600 and model["access_count"] < 10:
                self.logger.info(
                    f"Model {model['id']} is idle (age: {model['age_seconds']:.0f}s, "
                    f"accesses: {model['access_count']})"
                )
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get resource optimization recommendations"""
        recommendations = []
        stats = self.memory_manager.get_allocation_stats()
        
        # Memory utilization recommendations
        if stats["utilization_percent"] > 80:
            recommendations.append(
                f"Memory utilization is high ({stats['utilization_percent']:.1f}%). "
                "Consider evicting unused models."
            )
        
        # Idle model recommendations
        for model in stats["models"]:
            if model["age_seconds"] > 1800 and model["access_count"] < 5:
                recommendations.append(
                    f"Model {model['id']} appears idle. Consider unloading to free "
                    f"{model['size_gb']:.1f}GB of memory."
                )
        
        # Quantization recommendations
        large_unquantized = [
            m for m in stats["models"] 
            if m["size_gb"] > 50 and "quantized" not in m["id"].lower()
        ]
        if large_unquantized:
            recommendations.append(
                f"Consider quantizing {len(large_unquantized)} large models to "
                "reduce memory usage by up to 75%."
            )
        
        return recommendations


async def cleanup_memory():
    """Global memory cleanup function"""
    import gc
    import mlx.core as mx
    
    # Force garbage collection
    gc.collect()
    
    # Clear MLX caches
    mx.simplify()
    mx.eval()
    
    # Log cleanup
    logging.getLogger(__name__).info("Performed memory cleanup")
