#!/usr/bin/env python3
"""
MLX Model Loading Module
Handles efficient model loading with memory management and optimization
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import logging
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_map

from .config import MLXConfig, ModelLoadingConfig, get_config
from .resource_manager import MemoryManager, ModelAllocation
from .errors import ModelLoadError, InsufficientMemoryError


@dataclass
class ModelHandle:
    """Handle to a loaded model with metadata"""
    model_id: str
    model: Any  # The actual MLX model object
    config: Dict[str, Any]
    size_gb: float
    params_b: float
    loaded_at: float = None
    allocation: Optional[ModelAllocation] = None
    
    def __post_init__(self):
        if self.loaded_at is None:
            self.loaded_at = time.time()


# ModelLoadError and InsufficientMemoryError are now imported from errors.py


class MLXModelLoader:
    """Manages model loading with memory constraints"""
    
    def __init__(self, config: Optional[MLXConfig] = None, memory_manager: Optional[MemoryManager] = None):
        self.config = config or get_config()
        self.memory_manager = memory_manager or MemoryManager(self.config)
        self.loading_config = ModelLoadingConfig()
        self.loaded_models: Dict[str, ModelHandle] = {}
        self._loading_locks: Dict[str, asyncio.Lock] = {}
        self.logger = logging.getLogger(__name__)
    
    async def load_model(self, model_path: str, model_size_b: float, 
                        model_id: Optional[str] = None, 
                        priority: int = 0) -> ModelHandle:
        """Load a model with memory management"""
        model_path = Path(model_path)
        model_id = model_id or model_path.stem
        
        # Check if already loaded
        if model_id in self.loaded_models:
            self.logger.info(f"Model {model_id} already loaded")
            return self.loaded_models[model_id]
        
        # Ensure only one loading operation per model
        if model_id not in self._loading_locks:
            self._loading_locks[model_id] = asyncio.Lock()
        
        async with self._loading_locks[model_id]:
            # Double-check after acquiring lock
            if model_id in self.loaded_models:
                return self.loaded_models[model_id]
            
            # Calculate memory requirements
            memory_required = self.memory_manager.calculate_requirements(model_size_b)
            
            # Check and allocate memory
            if not await self.memory_manager.can_allocate(memory_required):
                # Try to free memory
                await self._free_memory_for_model(memory_required)
                
                # Check again
                if not await self.memory_manager.can_allocate(memory_required):
                    raise InsufficientMemoryError(
                        f"Need {memory_required:.1f}GB, have "
                        f"{self.memory_manager.available_gb:.1f}GB available"
                    )
            
            # Allocate memory
            allocation = await self.memory_manager.allocate_model(
                model_id, memory_required, priority
            )
            
            try:
                # Determine loading strategy
                loading_strategy = self._determine_loading_strategy(model_size_b)
                
                # Load model
                self.logger.info(f"Loading model {model_id} with strategy: {loading_strategy}")
                model_handle = await self._load_with_strategy(
                    model_path, model_id, model_size_b, loading_strategy
                )
                
                # Set allocation
                model_handle.allocation = allocation
                
                # Store loaded model
                self.loaded_models[model_id] = model_handle
                
                self.logger.info(
                    f"Successfully loaded {model_id} ({model_size_b}B params, "
                    f"{memory_required:.1f}GB memory)"
                )
                
                return model_handle
                
            except Exception as e:
                # Release memory on failure
                await self.memory_manager.release_model(model_id)
                raise ModelLoadError(f"Failed to load model {model_id}: {e}")
    
    def _determine_loading_strategy(self, model_size_b: float) -> str:
        """Determine optimal loading strategy based on model size"""
        if model_size_b < 7:
            return "direct"  # Load directly into memory
        elif model_size_b < 70:
            return "sequential"  # Load layers sequentially
        elif model_size_b < 200:
            return "chunked"  # Load in chunks with memory mapping
        else:
            return "streaming"  # Stream from disk as needed
    
    async def _load_with_strategy(self, model_path: Path, model_id: str, 
                                 model_size_b: float, strategy: str) -> ModelHandle:
        """Load model using specified strategy"""
        if strategy == "direct":
            return await self._load_direct(model_path, model_id, model_size_b)
        elif strategy == "sequential":
            return await self._load_sequential(model_path, model_id, model_size_b)
        elif strategy == "chunked":
            return await self._load_chunked(model_path, model_id, model_size_b)
        else:  # streaming
            return await self._load_streaming(model_path, model_id, model_size_b)
    
    async def _load_direct(self, model_path: Path, model_id: str, model_size_b: float) -> ModelHandle:
        """Direct model loading for smaller models"""
        # Load config
        config_path = model_path / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                model_config = json.load(f)
        else:
            model_config = {"model_type": "unknown", "size_b": model_size_b}
        
        # Simulate model loading (replace with actual MLX loading)
        await asyncio.sleep(0.1 * model_size_b)  # Simulate loading time
        
        # Create mock model
        model = self._create_mock_model(model_config)
        
        # Apply optimizations
        model = self._optimize_model(model)
        
        return ModelHandle(
            model_id=model_id,
            model=model,
            config=model_config,
            size_gb=model_size_b * 0.5,  # Rough estimate
            params_b=model_size_b
        )
    
    async def _load_sequential(self, model_path: Path, model_id: str, model_size_b: float) -> ModelHandle:
        """Sequential loading for medium models"""
        self.logger.info(f"Loading {model_id} sequentially")
        
        # Load in stages to reduce peak memory
        stages = ["embeddings", "layers", "head"]
        model_parts = {}
        
        for stage in stages:
            await asyncio.sleep(0.05 * model_size_b)  # Simulate loading
            model_parts[stage] = f"{stage}_loaded"
        
        # Combine parts
        model = self._create_mock_model({"parts": model_parts, "size_b": model_size_b})
        
        return ModelHandle(
            model_id=model_id,
            model=model,
            config={"loading": "sequential", "size_b": model_size_b},
            size_gb=model_size_b * 0.5,
            params_b=model_size_b
        )
    
    async def _load_chunked(self, model_path: Path, model_id: str, model_size_b: float) -> ModelHandle:
        """Chunked loading for large models"""
        self.logger.info(f"Loading {model_id} in chunks")
        
        # Use memory mapping for large models
        if self.loading_config.should_use_mmap(model_size_b * 0.5):
            self.logger.info(f"Using memory mapping for {model_id}")
        
        # Simulate chunked loading
        num_chunks = int(model_size_b / 10)  # 10GB chunks
        for i in range(num_chunks):
            await asyncio.sleep(0.01)
            if i % 10 == 0:
                self.logger.debug(f"Loaded chunk {i}/{num_chunks}")
        
        model = self._create_mock_model({"chunks": num_chunks, "size_b": model_size_b})
        
        return ModelHandle(
            model_id=model_id,
            model=model,
            config={"loading": "chunked", "size_b": model_size_b},
            size_gb=model_size_b * 0.5,
            params_b=model_size_b
        )
    
    async def _load_streaming(self, model_path: Path, model_id: str, model_size_b: float) -> ModelHandle:
        """Streaming loading for very large models"""
        self.logger.info(f"Setting up streaming for {model_id}")
        
        # For very large models, set up on-demand loading
        model = self._create_streaming_model(model_id, model_size_b)
        
        return ModelHandle(
            model_id=model_id,
            model=model,
            config={"loading": "streaming", "size_b": model_size_b},
            size_gb=model_size_b * 0.3,  # Only partial model in memory
            params_b=model_size_b
        )
    
    def _create_mock_model(self, config: Dict[str, Any]) -> Any:
        """Create a mock model for demonstration"""
        # In real implementation, this would create actual MLX model
        return {
            "type": "mock_model",
            "config": config,
            "forward": lambda x: x  # Mock forward function
        }
    
    def _create_streaming_model(self, model_id: str, size_b: float) -> Any:
        """Create a streaming model wrapper"""
        return {
            "type": "streaming_model",
            "model_id": model_id,
            "size_b": size_b,
            "stream": True
        }
    
    def _optimize_model(self, model: Any) -> Any:
        """Apply MLX-specific optimizations to model"""
        # In real implementation, apply actual optimizations
        if isinstance(model, dict):
            model["optimized"] = True
        
        # Enable graph optimization
        mx.simplify()
        
        return model
    
    async def _free_memory_for_model(self, required_gb: float):
        """Free memory by evicting models"""
        candidates = await self.memory_manager.get_eviction_candidates(required_gb)
        
        for model_id in candidates:
            await self.unload_model(model_id)
    
    async def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        if model_id not in self.loaded_models:
            return False
        
        self.logger.info(f"Unloading model {model_id}")
        
        # Remove from loaded models
        model_handle = self.loaded_models.pop(model_id)
        
        # Release memory
        await self.memory_manager.release_model(model_id)
        
        # Clean up resources
        del model_handle.model
        
        self.logger.info(f"Unloaded {model_id}, freed {model_handle.size_gb:.1f}GB")
        return True
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.loaded_models.keys())
    
    def get_model(self, model_id: str) -> Optional[ModelHandle]:
        """Get a loaded model handle"""
        return self.loaded_models.get(model_id)
    
    async def preload_models(self, model_configs: List[Dict[str, Any]]):
        """Preload multiple models based on priority"""
        # Sort by priority (descending)
        sorted_configs = sorted(
            model_configs, 
            key=lambda x: x.get("priority", 0), 
            reverse=True
        )
        
        loaded = []
        failed = []
        
        for config in sorted_configs:
            try:
                handle = await self.load_model(
                    config["path"],
                    config["size_b"],
                    config.get("id"),
                    config.get("priority", 0)
                )
                loaded.append(handle.model_id)
            except Exception as e:
                self.logger.error(f"Failed to preload {config.get('id', config['path'])}: {e}")
                failed.append(config.get("id", config["path"]))
        
        self.logger.info(f"Preloaded {len(loaded)} models, {len(failed)} failed")
        return {"loaded": loaded, "failed": failed}
