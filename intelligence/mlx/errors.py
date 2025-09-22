#!/usr/bin/env python3
"""
MLX Error Handling Module
Centralized error handling and recovery mechanisms for MLX operations
"""

import asyncio
import functools
import logging
from typing import TypeVar, Callable, Any, Optional, Union, Type
from datetime import datetime, timedelta
import traceback

from .resource_manager import cleanup_memory


# Type variable for decorators
T = TypeVar('T')


class MLXError(Exception):
    """Base exception for all MLX operations"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}
        self.timestamp = datetime.now()


class ModelLoadError(MLXError):
    """Error during model loading"""
    pass


class InferenceError(MLXError):
    """Error during inference execution"""
    pass


class MemoryError(MLXError):
    """Memory allocation or management error"""
    pass


class QuantizationError(MLXError):
    """Error during model quantization"""
    pass


class ConfigurationError(MLXError):
    """Configuration validation error"""
    pass


class ResourceExhaustedError(MLXError):
    """Resource exhaustion error"""
    pass


class ErrorContext:
    """Context information for error handling"""
    
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3
        self.last_error: Optional[Exception] = None
        self.error_history: list[tuple[datetime, Exception]] = []
        
    def record_error(self, error: Exception):
        """Record an error occurrence"""
        self.last_error = error
        self.error_history.append((datetime.now(), error))
        # Keep only last 10 errors
        if len(self.error_history) > 10:
            self.error_history.pop(0)
    
    def should_retry(self) -> bool:
        """Determine if operation should be retried"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1


def with_error_recovery(
    recoverable_errors: tuple[Type[Exception], ...] = (MemoryError, ResourceExhaustedError),
    cleanup_on_error: bool = True,
    max_retries: int = 3,
    backoff_factor: float = 2.0
):
    """
    Decorator for error recovery with exponential backoff
    
    Args:
        recoverable_errors: Tuple of exception types that should trigger recovery
        cleanup_on_error: Whether to run memory cleanup on recoverable errors
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            context = ErrorContext()
            context.max_retries = max_retries
            logger = logging.getLogger(func.__module__)
            
            while True:
                try:
                    # Attempt the operation
                    result = await func(*args, **kwargs)
                    
                    # Success - reset retry count if we had retries
                    if context.retry_count > 0:
                        logger.info(f"{func.__name__} succeeded after {context.retry_count} retries")
                    
                    return result
                    
                except recoverable_errors as e:
                    context.record_error(e)
                    
                    if not context.should_retry():
                        logger.error(f"{func.__name__} failed after {context.retry_count} retries: {e}")
                        raise
                    
                    context.increment_retry()
                    wait_time = (backoff_factor ** (context.retry_count - 1))
                    
                    logger.warning(
                        f"{func.__name__} failed with {type(e).__name__}: {e}. "
                        f"Retry {context.retry_count}/{context.max_retries} in {wait_time}s"
                    )
                    
                    # Run cleanup if requested
                    if cleanup_on_error and isinstance(e, MemoryError):
                        logger.info("Running memory cleanup before retry")
                        await cleanup_memory()
                    
                    # Wait before retry
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    # Non-recoverable error
                    logger.error(f"{func.__name__} failed with non-recoverable error: {e}")
                    logger.debug(traceback.format_exc())
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For synchronous functions, convert to async and run
            if not asyncio.iscoroutinefunction(func):
                return func(*args, **kwargs)
            
            # Run async function in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


class ErrorHandler:
    """Centralized error handler with logging and metrics"""
    
    def __init__(self, component_name: str):
        self.component_name = component_name
        self.logger = logging.getLogger(component_name)
        self.error_counts: dict[str, int] = {}
        self.last_errors: dict[str, Exception] = {}
    
    def handle_error(self, error: Exception, context: Optional[dict] = None) -> None:
        """Handle and log an error with context"""
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.last_errors[error_type] = error
        
        # Log with appropriate level
        if isinstance(error, MLXError):
            self.logger.error(
                f"{error_type} in {self.component_name}: {error}",
                extra={
                    "error_details": error.details,
                    "context": context or {},
                    "occurrence_count": self.error_counts[error_type]
                }
            )
        else:
            self.logger.exception(
                f"Unexpected error in {self.component_name}",
                extra={"context": context or {}}
            )
    
    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of errors encountered"""
        return {
            "component": self.component_name,
            "error_counts": self.error_counts.copy(),
            "recent_errors": {
                error_type: str(error)
                for error_type, error in self.last_errors.items()
            }
        }
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()
        self.last_errors.clear()


def validate_config(config: dict, required_fields: list[str]) -> None:
    """
    Validate configuration dictionary has required fields
    
    Raises:
        ConfigurationError: If required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        raise ConfigurationError(
            f"Missing required configuration fields: {missing_fields}",
            details={"missing_fields": missing_fields, "provided_config": config}
        )


def assert_memory_available(required_gb: float, available_gb: float) -> None:
    """
    Assert that sufficient memory is available
    
    Raises:
        MemoryError: If insufficient memory
    """
    if required_gb > available_gb:
        raise MemoryError(
            f"Insufficient memory: {required_gb}GB required, {available_gb}GB available",
            details={
                "required_gb": required_gb,
                "available_gb": available_gb,
                "deficit_gb": required_gb - available_gb
            }
        )


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler(component_name: str = "MLX") -> ErrorHandler:
    """Get or create global error handler"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(component_name)
    return _global_error_handler
