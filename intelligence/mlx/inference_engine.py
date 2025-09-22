#!/usr/bin/env python3
"""
MLX Inference Engine Module
Handles optimized inference execution with performance monitoring
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging
import numpy as np
import mlx.core as mx
import mlx.nn as nn

from .config import MLXConfig, InferenceConfig, get_config
from .model_loader import ModelHandle
from .errors import InferenceError


@dataclass
class InferenceResult:
    """Result of an inference operation"""
    output: Any
    model_id: str
    latency_ms: float
    tokens_per_second: Optional[float] = None
    tokens_generated: Optional[int] = None
    memory_used_gb: Optional[float] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def successful(self) -> bool:
        """Check if inference was successful"""
        return self.output is not None


@dataclass
class InferenceMetrics:
    """Metrics collected during inference"""
    start_time: float
    end_time: Optional[float] = None
    tokens_processed: int = 0
    peak_memory_gb: float = 0.0
    gpu_utilization: float = 0.0
    
    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds"""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate tokens per second"""
        duration_s = (self.end_time - self.start_time) if self.end_time else 0
        return self.tokens_processed / duration_s if duration_s > 0 else 0


# InferenceError is now imported from errors.py


class MLXInferenceEngine:
    """High-performance inference engine for MLX models"""
    
    def __init__(self, config: Optional[MLXConfig] = None):
        self.config = config or get_config()
        self.inference_config = InferenceConfig()
        self.device = mx.default_device()
        self._active_inferences = 0
        self._total_inferences = 0
        self._inference_lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self._performance_history: List[InferenceMetrics] = []
        self._max_history = 100
    
    @asynccontextmanager
    async def _inference_context(self):
        """Context manager for inference operations"""
        async with self._inference_lock:
            self._active_inferences += 1
            
        try:
            # Set up MLX context
            with mx.stream(mx.gpu):
                yield
        finally:
            self._active_inferences -= 1
            self._total_inferences += 1
    
    async def run_inference(self, model_handle: ModelHandle, 
                          tokens: Union[mx.array, np.ndarray, List[int]],
                          max_tokens: Optional[int] = None,
                          temperature: Optional[float] = None,
                          **kwargs) -> InferenceResult:
        """Run inference on a model"""
        metrics = InferenceMetrics(start_time=time.time())
        
        try:
            async with self._inference_context():
                # Convert input to MLX array
                input_tokens = self._prepare_input(tokens)
                metrics.tokens_processed = input_tokens.shape[-1]
                
                # Configure inference
                inference_params = self._prepare_inference_params(
                    max_tokens, temperature, **kwargs
                )
                
                # Execute inference
                output = await self._execute_inference(
                    model_handle, input_tokens, inference_params, metrics
                )
                
                # Finalize metrics
                metrics.end_time = time.time()
                self._record_metrics(metrics)
                
                return InferenceResult(
                    output=output,
                    model_id=model_handle.model_id,
                    latency_ms=metrics.duration_ms,
                    tokens_per_second=metrics.tokens_per_second,
                    tokens_generated=metrics.tokens_processed,
                    memory_used_gb=model_handle.size_gb,
                    metrics=self._collect_metrics(metrics)
                )
                
        except Exception as e:
            self.logger.error(f"Inference failed for {model_handle.model_id}: {e}")
            metrics.end_time = time.time()
            
            return InferenceResult(
                output=None,
                model_id=model_handle.model_id,
                latency_ms=metrics.duration_ms,
                metrics={"error": str(e)}
            )
    
    def _prepare_input(self, tokens: Union[mx.array, np.ndarray, List[int]]) -> mx.array:
        """Prepare input tokens for inference"""
        if isinstance(tokens, mx.array):
            return tokens
        elif isinstance(tokens, np.ndarray):
            return mx.array(tokens, dtype=mx.int32)
        else:  # List
            return mx.array(tokens, dtype=mx.int32)
    
    def _prepare_inference_params(self, max_tokens: Optional[int] = None,
                                temperature: Optional[float] = None,
                                **kwargs) -> Dict[str, Any]:
        """Prepare inference parameters"""
        params = {
            "max_tokens": max_tokens or self.inference_config.default_max_tokens,
            "temperature": temperature or self.inference_config.temperature,
            "top_p": kwargs.get("top_p", self.inference_config.top_p),
            "repetition_penalty": kwargs.get("repetition_penalty", 
                                           self.inference_config.repetition_penalty),
            "stream": kwargs.get("stream", self.inference_config.stream)
        }
        
        # Add any additional parameters
        params.update({k: v for k, v in kwargs.items() 
                      if k not in params})
        
        return params
    
    async def _execute_inference(self, model_handle: ModelHandle,
                               input_tokens: mx.array,
                               params: Dict[str, Any],
                               metrics: InferenceMetrics) -> Any:
        """Execute the actual inference"""
        model = model_handle.model
        
        # For demonstration, simulate inference
        # In real implementation, this would call actual MLX model
        if isinstance(model, dict) and model.get("type") == "mock_model":
            # Simulate inference delay based on model size and tokens
            delay = 0.001 * model_handle.params_b * input_tokens.shape[-1] / 40
            await asyncio.sleep(delay)
            
            # Generate mock output
            output_length = params["max_tokens"]
            output = mx.random.randint(0, 32000, (1, output_length))
            
            # Force evaluation for timing
            mx.eval(output)
            
            return output
        else:
            # Real model inference would go here
            with mx.no_grad():
                output = model(input_tokens)
                mx.eval(output)
                return output
    
    def _collect_metrics(self, metrics: InferenceMetrics) -> Dict[str, Any]:
        """Collect comprehensive metrics"""
        return {
            "duration_ms": metrics.duration_ms,
            "tokens_per_second": metrics.tokens_per_second,
            "tokens_processed": metrics.tokens_processed,
            "timestamp": metrics.start_time,
            "device": str(self.device),
            "active_inferences": self._active_inferences
        }
    
    def _record_metrics(self, metrics: InferenceMetrics):
        """Record metrics for performance tracking"""
        self._performance_history.append(metrics)
        
        # Keep only recent history
        if len(self._performance_history) > self._max_history:
            self._performance_history.pop(0)
    
    async def run_batch_inference(self, model_handle: ModelHandle,
                                batch_tokens: List[Union[mx.array, np.ndarray, List[int]]],
                                **kwargs) -> List[InferenceResult]:
        """Run inference on a batch of inputs"""
        self.logger.info(f"Running batch inference with {len(batch_tokens)} inputs")
        
        # Process in parallel up to a limit
        max_concurrent = min(len(batch_tokens), 4)
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_limit(tokens):
            async with semaphore:
                return await self.run_inference(model_handle, tokens, **kwargs)
        
        # Execute batch
        tasks = [process_with_limit(tokens) for tokens in batch_tokens]
        results = await asyncio.gather(*tasks)
        
        # Log batch statistics
        successful = sum(1 for r in results if r.successful)
        avg_latency = sum(r.latency_ms for r in results) / len(results)
        
        self.logger.info(
            f"Batch complete: {successful}/{len(results)} successful, "
            f"avg latency: {avg_latency:.1f}ms"
        )
        
        return results
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self._performance_history:
            return {
                "total_inferences": self._total_inferences,
                "active_inferences": self._active_inferences,
                "no_history": True
            }
        
        latencies = [m.duration_ms for m in self._performance_history]
        tps_values = [m.tokens_per_second for m in self._performance_history if m.tokens_per_second > 0]
        
        return {
            "total_inferences": self._total_inferences,
            "active_inferences": self._active_inferences,
            "latency_stats": {
                "mean_ms": np.mean(latencies),
                "median_ms": np.median(latencies),
                "p95_ms": np.percentile(latencies, 95),
                "p99_ms": np.percentile(latencies, 99),
                "min_ms": np.min(latencies),
                "max_ms": np.max(latencies)
            },
            "throughput_stats": {
                "mean_tps": np.mean(tps_values) if tps_values else 0,
                "max_tps": np.max(tps_values) if tps_values else 0,
                "meets_target": np.mean(tps_values) >= self.config.target_tokens_per_second if tps_values else False
            },
            "history_size": len(self._performance_history)
        }
    
    async def benchmark_model(self, model_handle: ModelHandle,
                            test_prompts: List[str],
                            warmup_runs: int = 3) -> Dict[str, Any]:
        """Benchmark a model's performance"""
        self.logger.info(f"Benchmarking {model_handle.model_id}")
        
        # Convert prompts to token arrays (mock tokenization)
        test_tokens = [mx.array([i] * 50) for i in range(len(test_prompts))]
        
        # Warmup runs
        self.logger.info(f"Running {warmup_runs} warmup iterations")
        for i in range(warmup_runs):
            await self.run_inference(model_handle, test_tokens[0], max_tokens=100)
        
        # Clear history for clean benchmark
        self._performance_history.clear()
        
        # Run benchmark
        self.logger.info(f"Running benchmark with {len(test_prompts)} prompts")
        start_time = time.time()
        
        results = await self.run_batch_inference(
            model_handle, test_tokens, max_tokens=100
        )
        
        total_time = time.time() - start_time
        
        # Collect benchmark results
        successful_results = [r for r in results if r.successful]
        
        return {
            "model_id": model_handle.model_id,
            "total_prompts": len(test_prompts),
            "successful": len(successful_results),
            "failed": len(results) - len(successful_results),
            "total_time_s": total_time,
            "throughput": len(successful_results) / total_time if total_time > 0 else 0,
            "latency_stats": {
                "mean_ms": np.mean([r.latency_ms for r in successful_results]),
                "median_ms": np.median([r.latency_ms for r in successful_results]),
                "p95_ms": np.percentile([r.latency_ms for r in successful_results], 95),
                "p99_ms": np.percentile([r.latency_ms for r in successful_results], 99)
            },
            "tokens_per_second": {
                "mean": np.mean([r.tokens_per_second for r in successful_results if r.tokens_per_second]),
                "max": np.max([r.tokens_per_second for r in successful_results if r.tokens_per_second]),
                "meets_target": np.mean([r.tokens_per_second for r in successful_results if r.tokens_per_second]) >= self.config.target_tokens_per_second
            }
        }
