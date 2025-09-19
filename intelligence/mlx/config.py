#!/usr/bin/env python3
"""
MLX Configuration Module
Centralized configuration management for MLX components
"""

import os
from typing import Dict, Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path


class MLXConfig(BaseModel):
    """MLX optimization configuration with validation"""
    
    # Hardware specifications
    unified_memory_gb: int = Field(default=512, ge=8, le=2048)
    gpu_cores: int = Field(default=80, ge=1, le=128)
    memory_bandwidth_gb_s: int = Field(default=819, ge=100)
    
    # Performance targets
    target_tokens_per_second: int = Field(default=40, ge=1)
    max_context_length: int = Field(default=128000, ge=1024)
    
    # Quantization settings
    quantization_bits: int = Field(default=4, ge=2, le=16)
    use_mixed_precision: bool = True
    group_size: int = Field(default=64, ge=32)
    
    # Batch optimization
    dynamic_batching: bool = True
    optimal_batch_sizes: Optional[Dict[str, int]] = None
    
    # Resource limits
    max_model_params_b: int = Field(default=670, ge=1)
    memory_buffer_percent: float = Field(default=0.1, ge=0.0, le=0.5)
    
    @validator('optimal_batch_sizes', pre=True, always=True)
    def set_optimal_batch_sizes(cls, v):
        """Set default optimal batch sizes if not provided"""
        if v is None:
            return {
                "small": 64,    # < 7B params
                "medium": 32,   # 7B-30B params  
                "large": 16,    # 30B-70B params
                "xlarge": 8,    # 70B-200B params
                "xxlarge": 4    # 200B+ params
            }
        return v
    
    @classmethod
    def from_env(cls) -> 'MLXConfig':
        """Create config from environment variables"""
        return cls(
            unified_memory_gb=int(os.getenv('MLX_MEMORY_GB', '512')),
            gpu_cores=int(os.getenv('MLX_GPU_CORES', '80')),
            memory_bandwidth_gb_s=int(os.getenv('MLX_MEMORY_BANDWIDTH', '819')),
            target_tokens_per_second=int(os.getenv('MLX_TARGET_TPS', '40')),
            max_context_length=int(os.getenv('MLX_MAX_CONTEXT', '128000')),
            quantization_bits=int(os.getenv('MLX_QUANT_BITS', '4')),
            use_mixed_precision=os.getenv('MLX_MIXED_PRECISION', 'true').lower() == 'true',
            dynamic_batching=os.getenv('MLX_DYNAMIC_BATCHING', 'true').lower() == 'true'
        )
    
    def get_batch_size_for_model(self, model_params_b: float) -> int:
        """Get optimal batch size based on model size"""
        if model_params_b < 7:
            return self.optimal_batch_sizes["small"]
        elif model_params_b < 30:
            return self.optimal_batch_sizes["medium"]
        elif model_params_b < 70:
            return self.optimal_batch_sizes["large"]
        elif model_params_b < 200:
            return self.optimal_batch_sizes["xlarge"]
        else:
            return self.optimal_batch_sizes["xxlarge"]
    
    @property
    def available_memory_gb(self) -> float:
        """Calculate available memory after buffer"""
        return self.unified_memory_gb * (1 - self.memory_buffer_percent)


class QuantizationConfig(BaseModel):
    """Quantization-specific configuration"""
    
    bits: int = Field(default=4, ge=2, le=16)
    group_size: int = Field(default=64, ge=32)
    method: str = Field(default="gptq", pattern="^(gptq|awq|ggml)$")
    calibration_samples: int = Field(default=128, ge=32)
    use_activation_quantization: bool = False
    
    def get_compression_ratio(self, original_bits: int = 16) -> float:
        """Calculate compression ratio from quantization"""
        return original_bits / self.bits


class InferenceConfig(BaseModel):
    """Inference-specific configuration"""
    
    default_max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    repetition_penalty: float = Field(default=1.0, ge=0.0, le=2.0)
    stream: bool = True
    timeout_seconds: int = Field(default=300, ge=1)
    
    # Memory optimization
    use_kv_cache: bool = True
    kv_cache_max_tokens: Optional[int] = None
    
    @validator('kv_cache_max_tokens', pre=True, always=True)
    def set_kv_cache_max(cls, v, values):
        """Set KV cache size if not specified"""
        if v is None and values.get('use_kv_cache'):
            return values.get('default_max_tokens', 512) * 2
        return v


class ModelLoadingConfig(BaseModel):
    """Model loading configuration"""
    
    lazy_load: bool = True
    use_mmap: bool = True
    prefetch_layers: bool = True
    parallel_loading: bool = True
    max_loading_threads: int = Field(default=4, ge=1, le=16)
    
    # Memory mapping
    mmap_threshold_gb: float = Field(default=10.0, ge=1.0)
    
    def should_use_mmap(self, model_size_gb: float) -> bool:
        """Determine if memory mapping should be used"""
        return self.use_mmap and model_size_gb >= self.mmap_threshold_gb


# Global configuration instance
_global_config: Optional[MLXConfig] = None


def get_config() -> MLXConfig:
    """Get global MLX configuration"""
    global _global_config
    if _global_config is None:
        _global_config = MLXConfig.from_env()
    return _global_config


def set_config(config: MLXConfig):
    """Set global MLX configuration"""
    global _global_config
    _global_config = config


def reset_config():
    """Reset configuration to defaults"""
    global _global_config
    _global_config = None
