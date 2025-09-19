#!/usr/bin/env python3
"""
MLX Module for FREEDOM Intelligence Platform
Modular components for model optimization on Apple Silicon
"""

from .config import (
    MLXConfig, 
    QuantizationConfig, 
    InferenceConfig, 
    ModelLoadingConfig,
    get_config,
    set_config,
    reset_config
)

from .resource_manager import (
    MemoryManager,
    ResourceMonitor,
    ModelAllocation,
    cleanup_memory
)

from .model_loader import (
    MLXModelLoader,
    ModelHandle,
    ModelLoadError,
    InsufficientMemoryError
)

from .inference_engine import (
    MLXInferenceEngine,
    InferenceResult,
    InferenceMetrics,
    InferenceError
)

from .quantization_service import (
    MLXQuantizationService,
    QuantizationMethod,
    QuantizationResult,
    QuantizationStrategy
)

from .errors import (
    MLXError,
    ModelLoadError,
    InferenceError,
    MemoryError,
    QuantizationError,
    ConfigurationError,
    ResourceExhaustedError,
    with_error_recovery,
    ErrorHandler,
    get_error_handler
)

__all__ = [
    # Config
    "MLXConfig",
    "QuantizationConfig", 
    "InferenceConfig",
    "ModelLoadingConfig",
    "get_config",
    "set_config",
    "reset_config",
    
    # Resource Management
    "MemoryManager",
    "ResourceMonitor",
    "ModelAllocation",
    "cleanup_memory",
    
    # Model Loading
    "MLXModelLoader",
    "ModelHandle",
    "ModelLoadError",
    "InsufficientMemoryError",
    
    # Inference
    "MLXInferenceEngine",
    "InferenceResult",
    "InferenceMetrics",
    "InferenceError",
    
    # Quantization
    "MLXQuantizationService",
    "QuantizationMethod",
    "QuantizationResult",
    "QuantizationStrategy",
    
    # Error Handling
    "MLXError",
    "ModelLoadError",
    "InferenceError",
    "MemoryError",
    "QuantizationError",
    "ConfigurationError",
    "ResourceExhaustedError",
    "with_error_recovery",
    "ErrorHandler",
    "get_error_handler"
]

__version__ = "2.0.0"  # Refactored modular version
