#!/usr/bin/env python3
"""
MLX Advanced Optimizer for FREEDOM Platform
Facade for modular MLX optimization components

⚠️ LEGACY COMPATIBILITY LAYER ⚠️
This class exists for backward compatibility. New code should use the modular 
components directly from intelligence.mlx:
- MLXConfig for configuration
- MLXModelLoader for model loading
- MLXInferenceEngine for inference
- MLXQuantizationService for quantization
- MemoryManager for resource management

Each method below indicates which module it delegates to.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import modular components
from intelligence.mlx import (
    MLXConfig,
    MemoryManager,
    ResourceMonitor,
    MLXModelLoader,
    MLXInferenceEngine,
    MLXQuantizationService,
    QuantizationMethod,
    cleanup_memory,
    ModelLoadError,
    InferenceError,
    with_error_recovery
)


class MLXAdvancedOptimizer:
    """
    Simplified facade for MLX optimization using modular components
    """
    
    def __init__(self, config: Optional[MLXConfig] = None):
        self.config = config or MLXConfig()
        self.logger = self._setup_logging()
        
        # Initialize modular components
        self.memory_manager = MemoryManager(self.config)
        self.model_loader = MLXModelLoader(self.config, self.memory_manager)
        self.inference_engine = MLXInferenceEngine(self.config)
        self.quantization_service = MLXQuantizationService()
        self.resource_monitor = ResourceMonitor(self.memory_manager)
        
        # Start resource monitoring
        asyncio.create_task(self.resource_monitor.start_monitoring())
        
        self.logger.info("MLX Advanced Optimizer initialized with modular components")
        self.logger.info(f"Unified Memory: {self.config.unified_memory_gb}GB")
        self.logger.info(f"Target TPS: {self.config.target_tokens_per_second}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the optimizer"""
        logger = logging.getLogger("MLXAdvancedOptimizer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    @with_error_recovery(recoverable_errors=(ModelLoadError,), cleanup_on_error=True)
    async def load_large_model(self, model_path: str, model_params_b: float) -> Dict[str, Any]:
        """
        Load large models using the modular loader with error recovery
        
        Delegates to: MLXModelLoader.load_model()
        """
        self.logger.info(f"Loading {model_params_b}B parameter model from {model_path}")
        
        try:
            # Use model loader component
            model_handle = await self.model_loader.load_model(
                model_path=model_path,
                model_size_b=model_params_b
            )
            
            # Return loading configuration
            return {
                "model_id": model_handle.model_id,
                "model_path": model_path,
                "size_gb": model_handle.size_gb,
                "params_b": model_handle.params_b,
                "batch_size": self.config.get_batch_size_for_model(model_params_b),
                "max_context_length": self.config.max_context_length,
                "loaded": True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    async def run_inference(self, model_id: str, tokens: Any) -> Dict[str, Any]:
        """
        Run optimized inference using the inference engine
        
        Delegates to: MLXInferenceEngine.run_inference()
        """
        # Get model handle
        model_handle = self.model_loader.get_model(model_id)
        if not model_handle:
            raise ValueError(f"Model {model_id} not loaded")
        
        # Run inference
        result = await self.inference_engine.run_inference(
            model_handle=model_handle,
            tokens=tokens
        )
        
        return {
            "output": result.output,
            "metrics": result.metrics,
            "latency_ms": result.latency_ms,
            "tokens_per_second": result.tokens_per_second,
            "achieved_target": result.tokens_per_second >= self.config.target_tokens_per_second
        }
    
    async def quantize_model(self, model_id: str) -> Dict[str, Any]:
        """
        Quantize model using the quantization service
        
        Delegates to: MLXQuantizationService.quantize_model()
        """
        self.logger.info(f"Quantizing model {model_id}")
        
        # Get model handle
        model_handle = self.model_loader.get_model(model_id)
        if not model_handle:
            raise ValueError(f"Model {model_id} not loaded")
        
        # Quantize model
        quantized_handle, result = await self.quantization_service.quantize_model(
            model_handle=model_handle
        )
        
        # Store quantized model
        self.model_loader.loaded_models[quantized_handle.model_id] = quantized_handle
        
        return {
            "quantized_model_id": quantized_handle.model_id,
            "original_size_gb": result.original_size_gb,
            "quantized_size_gb": result.quantized_size_gb,
            "reduction_percent": result.size_reduction_percent,
            "method": result.method,
            "bits": result.bits
        }
    
    async def optimize_context_window(self, model_id: str, target_context: int) -> Dict[str, Any]:
        """Optimize for large context windows"""
        self.logger.info(f"Optimizing {model_id} for {target_context} token context")
        
        # Get model info
        model_handle = self.model_loader.get_model(model_id)
        if not model_handle:
            raise ValueError(f"Model {model_id} not loaded")
        
        # Calculate memory requirements for context
        kv_cache_gb = (target_context * model_handle.params_b * 0.1) / 1024
        
        # Check if we can support the context
        available_memory = self.memory_manager.available_gb
        
        if kv_cache_gb > available_memory * 0.3:
            # Use sliding window attention
            optimization_strategy = "sliding_window"
            effective_context = min(target_context, 32768)
        else:
            optimization_strategy = "full_attention"
            effective_context = target_context
        
        return {
            "model_id": model_id,
            "strategy": optimization_strategy,
            "effective_context": effective_context,
            "kv_cache_size_gb": kv_cache_gb,
            "memory_available_gb": available_memory
        }
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get current memory statistics"""
        return self.memory_manager.get_allocation_stats()
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations from resource monitor"""
        return self.resource_monitor.get_optimization_recommendations()
    
    async def benchmark_performance(self, model_id: str, test_prompts: List[str]) -> Dict[str, Any]:
        """Benchmark model performance"""
        model_handle = self.model_loader.get_model(model_id)
        if not model_handle:
            raise ValueError(f"Model {model_id} not loaded")
        
        # Run benchmark using inference engine
        benchmark_result = await self.inference_engine.benchmark_model(
            model_handle=model_handle,
            test_prompts=test_prompts
        )
        
        return benchmark_result
    
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up MLX optimizer resources")
        
        # Stop monitoring
        await self.resource_monitor.stop_monitoring()
        
        # Clean up memory
        await cleanup_memory()
        
        self.logger.info("Cleanup complete")


class ModelOrchestrator:
    """
    Simplified orchestrator using modular components
    """
    
    def __init__(self, optimizer: MLXAdvancedOptimizer):
        self.optimizer = optimizer
        self.logger = logging.getLogger("ModelOrchestrator")
    
    async def load_model_zoo(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load multiple models with priority-based loading
        """
        # Prepare model configs with priorities
        model_configs = [
            {
                "id": model["id"],
                "path": model["path"],
                "size_b": model["params_b"],
                "priority": model.get("priority", 0)
            }
            for model in models
        ]
        
        # Use model loader's preload functionality
        result = await self.optimizer.model_loader.preload_models(model_configs)
        
        # Get memory stats
        memory_stats = self.optimizer.get_memory_stats()
        
        self.logger.info(
            f"Loaded {len(result['loaded'])} models, "
            f"using {memory_stats['allocated_gb']:.1f}GB / "
            f"{memory_stats['total_gb']:.1f}GB"
        )
        
        return result
    
    async def run_parallel_inference(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run inference on multiple models in parallel
        """
        # Create tasks for parallel execution
        tasks = []
        for request in requests:
            model_id = request["model_id"]
            tokens = request.get("tokens", [1, 2, 3])  # Mock tokens
            
            if self.optimizer.model_loader.get_model(model_id):
                task = self.optimizer.run_inference(model_id, tokens)
            else:
                # Create failed task
                async def failed_task():
                    return {
                        "model_id": model_id,
                        "status": "model_not_loaded",
                        "error": f"Model {model_id} not found"
                    }
                task = failed_task()
            
            tasks.append(task)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "model_id": requests[i]["model_id"],
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append({
                    "model_id": requests[i]["model_id"],
                    "status": "completed",
                    **result
                })
        
        return processed_results


async def run_mlx_optimization_demo():
    """Demonstrate refactored MLX optimization with modular components"""
    print("🚀 MLX Advanced Optimization Demo (Refactored)")
    print("=" * 60)
    
    # Initialize optimizer with M3 Ultra configuration
    config = MLXConfig(
        unified_memory_gb=512,
        gpu_cores=80,
        memory_bandwidth_gb_s=819
    )
    optimizer = MLXAdvancedOptimizer(config)
    
    try:
        # Test large model loading
        print("\n📦 Testing DeepSeek 670B Model Loading...")
        loading_config = await optimizer.load_large_model(
            model_path="/models/deepseek-670b",
            model_params_b=670
        )
        print(f"Loading result: {json.dumps(loading_config, indent=2)}")
        
        # Test context optimization
        print("\n📝 Testing Context Window Optimization...")
        if loading_config["loaded"]:
            context_config = await optimizer.optimize_context_window(
                model_id=loading_config["model_id"],
                target_context=128000
            )
            print(f"Context optimization: {json.dumps(context_config, indent=2)}")
        
        # Test quantization
        print("\n🔧 Testing Model Quantization...")
        if loading_config["loaded"]:
            quant_result = await optimizer.quantize_model(loading_config["model_id"])
            print(f"Quantization result: {json.dumps(quant_result, indent=2)}")
        
        # Test multi-model orchestration
        print("\n🎭 Testing Multi-Model Orchestration...")
        orchestrator = ModelOrchestrator(optimizer)
        
        test_models = [
            {"id": "llama-70b", "path": "/models/llama-70b", "params_b": 70, "priority": 2},
            {"id": "mixtral-8x7b", "path": "/models/mixtral-8x7b", "params_b": 47, "priority": 1},
            {"id": "phi-3", "path": "/models/phi-3", "params_b": 3.8, "priority": 0}
        ]
        
        load_results = await orchestrator.load_model_zoo(test_models)
        print(f"Model loading results: {json.dumps(load_results, indent=2)}")
        
        # Test parallel inference
        print("\n⚡ Testing Parallel Inference...")
        inference_requests = [
            {"model_id": "llama-70b"},
            {"model_id": "mixtral-8x7b"},
            {"model_id": "phi-3"}
        ]
        
        inference_results = await orchestrator.run_parallel_inference(inference_requests)
        print(f"Inference results: {json.dumps(inference_results, indent=2)}")
        
        # Show memory stats
        print("\n📊 Memory Statistics:")
        memory_stats = optimizer.get_memory_stats()
        print(json.dumps(memory_stats, indent=2))
        
        # Show optimization recommendations
        print("\n💡 Optimization Recommendations:")
        recommendations = optimizer.get_optimization_recommendations()
        for rec in recommendations:
            print(f"  • {rec}")
        
        print("\n✅ Refactored MLX Optimization Demo Complete!")
        print("\nModular Components:")
        print("  • Config: Centralized configuration management")
        print("  • MemoryManager: Intelligent memory allocation")
        print("  • ModelLoader: Efficient model loading strategies")
        print("  • InferenceEngine: Optimized inference execution")
        print("  • QuantizationService: Model compression")
        print("  • ResourceMonitor: Real-time resource tracking")
        
    finally:
        # Cleanup
        await optimizer.cleanup()


if __name__ == "__main__":
    asyncio.run(run_mlx_optimization_demo())