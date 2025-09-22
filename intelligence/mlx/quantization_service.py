#!/usr/bin/env python3
"""
MLX Quantization Service Module
Handles model quantization for memory optimization
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import numpy as np
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_map, tree_flatten

from .config import QuantizationConfig, MLXConfig, get_config
from .model_loader import ModelHandle


class QuantizationMethod(Enum):
    """Available quantization methods"""
    GPTQ = "gptq"  # GPU-aware quantization
    AWQ = "awq"    # Activation-aware quantization
    GGML = "ggml"  # GGML quantization format
    DYNAMIC = "dynamic"  # Dynamic quantization


@dataclass
class QuantizationResult:
    """Result of quantization operation"""
    original_size_gb: float
    quantized_size_gb: float
    compression_ratio: float
    method: str
    bits: int
    quality_score: Optional[float] = None
    time_taken_s: float = 0.0
    
    @property
    def size_reduction_percent(self) -> float:
        """Calculate size reduction percentage"""
        return (1 - self.quantized_size_gb / self.original_size_gb) * 100


class QuantizationStrategy:
    """Base class for quantization strategies"""
    
    def __init__(self, config: QuantizationConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def quantize(self, model: Any, calibration_data: Optional[mx.array] = None) -> Any:
        """Quantize model weights"""
        raise NotImplementedError
    
    def estimate_quality_loss(self, original_weights: mx.array, quantized_weights: mx.array) -> float:
        """Estimate quality loss from quantization"""
        # Calculate MSE between original and quantized weights
        mse = mx.mean((original_weights - quantized_weights) ** 2)
        # Normalize by variance of original weights
        variance = mx.var(original_weights)
        quality_score = 1.0 - (mse / (variance + 1e-8))
        return float(quality_score)


class GPTQStrategy(QuantizationStrategy):
    """GPTQ quantization strategy"""
    
    async def quantize(self, model: Any, calibration_data: Optional[mx.array] = None) -> Any:
        """Apply GPTQ quantization"""
        self.logger.info(f"Applying GPTQ quantization with {self.config.bits} bits")
        
        def quantize_weight(w):
            if isinstance(w, mx.array) and w.ndim >= 2:
                # Calculate scale for quantization
                w_max = mx.max(mx.abs(w))
                scale = w_max / (2**(self.config.bits-1) - 1)
                
                # Quantize
                w_quantized = mx.round(w / scale)
                
                # Clip to bit range
                max_val = 2**(self.config.bits-1) - 1
                w_quantized = mx.clip(w_quantized, -max_val, max_val)
                
                # Store scale for dequantization
                return {"quantized": w_quantized, "scale": scale, "bits": self.config.bits}
            return w
        
        # Apply quantization to all weights
        quantized_model = tree_map(quantize_weight, model)
        
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return quantized_model


class AWQStrategy(QuantizationStrategy):
    """Activation-aware Weight Quantization strategy"""
    
    async def quantize(self, model: Any, calibration_data: Optional[mx.array] = None) -> Any:
        """Apply AWQ quantization"""
        self.logger.info(f"Applying AWQ quantization with {self.config.bits} bits")
        
        # AWQ considers activation patterns for better quantization
        # This is a simplified version
        
        def quantize_weight_awq(w):
            if isinstance(w, mx.array) and w.ndim >= 2:
                # Calculate importance based on weight magnitude
                importance = mx.mean(mx.abs(w), axis=0, keepdims=True)
                
                # Apply importance-weighted quantization
                w_scaled = w * (1 + 0.1 * importance)  # Boost important weights
                
                # Standard quantization
                w_max = mx.max(mx.abs(w_scaled))
                scale = w_max / (2**(self.config.bits-1) - 1)
                w_quantized = mx.round(w_scaled / scale)
                
                # Clip and store
                max_val = 2**(self.config.bits-1) - 1
                w_quantized = mx.clip(w_quantized, -max_val, max_val)
                
                return {
                    "quantized": w_quantized, 
                    "scale": scale, 
                    "importance": importance,
                    "bits": self.config.bits
                }
            return w
        
        quantized_model = tree_map(quantize_weight_awq, model)
        
        await asyncio.sleep(0.15)  # AWQ takes slightly longer
        
        return quantized_model


class DynamicQuantizationStrategy(QuantizationStrategy):
    """Dynamic quantization strategy"""
    
    async def quantize(self, model: Any, calibration_data: Optional[mx.array] = None) -> Any:
        """Apply dynamic quantization"""
        self.logger.info("Applying dynamic quantization")
        
        # Dynamic quantization quantizes weights at runtime based on activations
        # This is a placeholder implementation
        
        def prepare_dynamic_quant(w):
            if isinstance(w, mx.array) and w.ndim >= 2:
                return {
                    "weight": w,
                    "quantize_on_forward": True,
                    "bits": self.config.bits
                }
            return w
        
        prepared_model = tree_map(prepare_dynamic_quant, model)
        
        await asyncio.sleep(0.05)  # Dynamic prep is fast
        
        return prepared_model


class MLXQuantizationService:
    """Service for model quantization"""
    
    def __init__(self, config: Optional[QuantizationConfig] = None):
        self.config = config or QuantizationConfig()
        self.mlx_config = get_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize strategies
        self.strategies = {
            QuantizationMethod.GPTQ: GPTQStrategy(self.config),
            QuantizationMethod.AWQ: AWQStrategy(self.config),
            QuantizationMethod.DYNAMIC: DynamicQuantizationStrategy(self.config)
        }
    
    async def quantize_model(self, model_handle: ModelHandle, 
                           method: Optional[QuantizationMethod] = None,
                           calibration_data: Optional[mx.array] = None) -> Tuple[ModelHandle, QuantizationResult]:
        """Quantize a model to reduce memory usage"""
        import time
        start_time = time.time()
        
        # Select quantization method
        if method is None:
            method = self._select_quantization_method(model_handle.params_b)
        
        self.logger.info(
            f"Quantizing {model_handle.model_id} ({model_handle.params_b}B params) "
            f"using {method.value} to {self.config.bits} bits"
        )
        
        # Get strategy
        strategy = self.strategies.get(method)
        if not strategy:
            raise ValueError(f"Unknown quantization method: {method}")
        
        # Calculate original size
        original_size = self._estimate_model_size(model_handle.model, bits=16)
        
        # Apply quantization
        quantized_model = await strategy.quantize(model_handle.model, calibration_data)
        
        # Calculate quantized size
        quantized_size = self._estimate_model_size(quantized_model, bits=self.config.bits)
        
        # Create quantized model handle
        quantized_handle = ModelHandle(
            model_id=f"{model_handle.model_id}_q{self.config.bits}",
            model=quantized_model,
            config={
                **model_handle.config,
                "quantization": {
                    "method": method.value,
                    "bits": self.config.bits,
                    "group_size": self.config.group_size
                }
            },
            size_gb=quantized_size / (1024**3),
            params_b=model_handle.params_b
        )
        
        # Create result
        result = QuantizationResult(
            original_size_gb=original_size / (1024**3),
            quantized_size_gb=quantized_size / (1024**3),
            compression_ratio=original_size / quantized_size,
            method=method.value,
            bits=self.config.bits,
            time_taken_s=time.time() - start_time
        )
        
        self.logger.info(
            f"Quantization complete: {result.size_reduction_percent:.1f}% size reduction "
            f"({result.original_size_gb:.1f}GB -> {result.quantized_size_gb:.1f}GB)"
        )
        
        return quantized_handle, result
    
    def _select_quantization_method(self, model_params_b: float) -> QuantizationMethod:
        """Select optimal quantization method based on model size"""
        if model_params_b < 7:
            # Small models: use dynamic quantization
            return QuantizationMethod.DYNAMIC
        elif model_params_b < 70:
            # Medium models: use GPTQ
            return QuantizationMethod.GPTQ
        else:
            # Large models: use AWQ for better quality
            return QuantizationMethod.AWQ
    
    def _estimate_model_size(self, model: Any, bits: int) -> float:
        """Estimate model size in bytes"""
        total_params = 0
        
        for layer in tree_flatten(model):
            if isinstance(layer, mx.array):
                total_params += layer.size
            elif isinstance(layer, dict) and "quantized" in layer:
                # Quantized weight
                total_params += layer["quantized"].size
        
        size_bytes = total_params * (bits / 8)
        return size_bytes
    
    async def quantize_for_target_size(self, model_handle: ModelHandle,
                                     target_size_gb: float) -> Tuple[ModelHandle, QuantizationResult]:
        """Quantize model to fit within target size"""
        current_size_gb = model_handle.size_gb
        
        # Determine required compression ratio
        required_ratio = current_size_gb / target_size_gb
        
        # Select appropriate bit width
        if required_ratio <= 2:
            bits = 8
        elif required_ratio <= 4:
            bits = 4
        elif required_ratio <= 8:
            bits = 2
        else:
            self.logger.warning(
                f"Cannot achieve {required_ratio:.1f}x compression with standard quantization"
            )
            bits = 2  # Maximum compression
        
        # Update config with selected bits
        self.config.bits = bits
        
        return await self.quantize_model(model_handle)
    
    def dequantize_weights(self, quantized_weights: Dict[str, Any]) -> mx.array:
        """Dequantize weights for inference"""
        if not isinstance(quantized_weights, dict) or "quantized" not in quantized_weights:
            return quantized_weights
        
        # Dequantize
        w_quantized = quantized_weights["quantized"]
        scale = quantized_weights["scale"]
        
        return w_quantized * scale
    
    async def calibrate_quantization(self, model_handle: ModelHandle,
                                   calibration_dataset: List[mx.array],
                                   num_samples: Optional[int] = None) -> mx.array:
        """Generate calibration data for quantization"""
        num_samples = num_samples or self.config.calibration_samples
        
        self.logger.info(f"Generating calibration data with {num_samples} samples")
        
        # Select subset of calibration data
        if len(calibration_dataset) > num_samples:
            indices = np.random.choice(len(calibration_dataset), num_samples, replace=False)
            calibration_subset = [calibration_dataset[i] for i in indices]
        else:
            calibration_subset = calibration_dataset
        
        # Concatenate samples
        calibration_data = mx.concatenate(calibration_subset, axis=0)
        
        return calibration_data
    
    def get_quantization_stats(self, model_handle: ModelHandle) -> Dict[str, Any]:
        """Get quantization statistics for a model"""
        if "quantization" not in model_handle.config:
            return {"quantized": False}
        
        quant_config = model_handle.config["quantization"]
        
        # Calculate theoretical compression
        original_bits = 16  # Assume FP16 original
        quantized_bits = quant_config.get("bits", self.config.bits)
        theoretical_compression = original_bits / quantized_bits
        
        return {
            "quantized": True,
            "method": quant_config.get("method", "unknown"),
            "bits": quantized_bits,
            "group_size": quant_config.get("group_size", self.config.group_size),
            "theoretical_compression": theoretical_compression,
            "estimated_quality_retention": 1.0 - (0.1 * (original_bits - quantized_bits))
        }
