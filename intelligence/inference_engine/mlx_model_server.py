#!/usr/bin/env python3
"""
FREEDOM MLX Model Server - Local AI Inference Engine
Optimized for Apple Silicon with MLX framework
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass
import logging
from enum import Enum

try:
    import mlx
    import mlx.core as mx
    import mlx.nn as nn
    import mlx_lm
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    print("⚠️ MLX not available - install with: pip install mlx mlx-lm")

# Import Truth Engine for verification
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from core.truth_engine.truth_engine import TruthEngine, ClaimType


class ModelStatus(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


@dataclass
class ModelInfo:
    model_id: str
    model_path: str
    model_type: str
    status: ModelStatus
    load_time: Optional[float] = None
    last_used: Optional[float] = None
    token_count: int = 0
    trust_score: float = 1.0


class MLXModelServer:
    """
    Local model server using Apple MLX for blazing fast inference
    """
    
    def __init__(self, workspace_path: Optional[str] = None):
        self.workspace_path = Path(workspace_path) if workspace_path else Path(__file__).parent.parent.parent
        self.models_dir = self.workspace_path / "models"
        self.loaded_models: Dict[str, Any] = {}
        self.model_info: Dict[str, ModelInfo] = {}
        self.truth_engine = TruthEngine()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for model server"""
        logger = logging.getLogger("MLXModelServer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
            # Also log to file
            file_handler = logging.FileHandler(
                self.workspace_path / "mlx_model_server.log"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    async def initialize(self) -> bool:
        """Initialize the model server"""
        if not MLX_AVAILABLE:
            self.logger.error("MLX not available - cannot initialize server")
            return False
            
        self.logger.info("Initializing MLX Model Server")
        
        # Create models directory if it doesn't exist
        self.models_dir.mkdir(exist_ok=True)
        
        # Scan for available models
        await self.scan_models()
        
        # Submit initialization claim to truth engine
        claim_id = self.truth_engine.submit_claim(
            source_id="MLXModelServer",
            claim_text="Model server initialized successfully",
            claim_type=ClaimType.BEHAVIORAL,
            evidence={
                "mlx_available": MLX_AVAILABLE,
                "models_found": len(self.model_info),
                "workspace": str(self.workspace_path)
            }
        )
        
        self.truth_engine.verify_claim(claim_id, "initialization_check", "MLXModelServer")
        
        self.logger.info(f"MLX Model Server ready with {len(self.model_info)} models available")
        return True
    
    async def scan_models(self) -> Dict[str, ModelInfo]:
        """Scan for available models in the models directory"""
        self.logger.info(f"Scanning for models in {self.models_dir}")
        
        # Look for MLX model directories
        for model_dir in self.models_dir.rglob("*"):
            if model_dir.is_dir() and (model_dir / "config.json").exists():
                model_id = model_dir.name
                self.model_info[model_id] = ModelInfo(
                    model_id=model_id,
                    model_path=str(model_dir),
                    model_type="mlx",
                    status=ModelStatus.UNLOADED
                )
                self.logger.info(f"Found model: {model_id}")
        
        return self.model_info
    
    async def load_model(self, model_id: str) -> bool:
        """Load a model into memory"""
        if model_id not in self.model_info:
            self.logger.error(f"Model {model_id} not found")
            return False
            
        if model_id in self.loaded_models:
            self.logger.info(f"Model {model_id} already loaded")
            return True
            
        model_info = self.model_info[model_id]
        model_info.status = ModelStatus.LOADING
        
        try:
            start_time = time.time()
            
            # Load model using mlx_lm
            if MLX_AVAILABLE:
                model, tokenizer = mlx_lm.load(model_info.model_path)
                self.loaded_models[model_id] = {
                    "model": model,
                    "tokenizer": tokenizer
                }
            else:
                # Simulate model loading for testing
                self.loaded_models[model_id] = {
                    "model": None,
                    "tokenizer": None
                }
            
            load_time = time.time() - start_time
            model_info.status = ModelStatus.READY
            model_info.load_time = load_time
            
            self.logger.info(f"Model {model_id} loaded in {load_time:.2f}s")
            
            # Verify model loading
            claim_id = self.truth_engine.submit_claim(
                source_id="MLXModelServer",
                claim_text=f"Model {model_id} loaded successfully",
                claim_type=ClaimType.BEHAVIORAL,
                evidence={
                    "model_id": model_id,
                    "load_time": load_time,
                    "model_path": model_info.model_path
                }
            )
            
            return True
            
        except Exception as e:
            model_info.status = ModelStatus.ERROR
            self.logger.error(f"Failed to load model {model_id}: {e}")
            return False
    
    async def generate(
        self, 
        model_id: str, 
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        stream: bool = False
    ) -> AsyncIterator[str]:
        """Generate text using the specified model"""
        
        # Ensure model is loaded
        if model_id not in self.loaded_models:
            if not await self.load_model(model_id):
                yield f"Error: Failed to load model {model_id}"
                return
        
        model_info = self.model_info[model_id]
        model_info.last_used = time.time()
        
        try:
            if MLX_AVAILABLE and self.loaded_models[model_id]["model"]:
                # Real MLX generation
                model_data = self.loaded_models[model_id]
                
                if stream:
                    # Streaming generation
                    async for token in self._stream_generate(
                        model_data["model"],
                        model_data["tokenizer"],
                        prompt,
                        max_tokens,
                        temperature
                    ):
                        yield token
                else:
                    # Non-streaming generation
                    result = await self._generate_complete(
                        model_data["model"],
                        model_data["tokenizer"],
                        prompt,
                        max_tokens,
                        temperature
                    )
                    yield result
            else:
                # Fallback for testing
                yield f"[Simulated response from {model_id}]: {prompt[:50]}..."
                
            model_info.token_count += max_tokens
            
        except Exception as e:
            self.logger.error(f"Generation error: {e}")
            yield f"Error: {str(e)}"
    
    async def _stream_generate(
        self, model, tokenizer, prompt: str, 
        max_tokens: int, temperature: float
    ) -> AsyncIterator[str]:
        """Stream tokens as they are generated"""
        # This would use mlx_lm.generate with streaming
        # For now, simulate streaming
        response = f"Streaming response to: {prompt}"
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.1)
    
    async def _generate_complete(
        self, model, tokenizer, prompt: str,
        max_tokens: int, temperature: float
    ) -> str:
        """Generate complete response"""
        # This would use mlx_lm.generate
        # For now, return simulated response
        return f"Complete response to: {prompt}"
    
    async def unload_model(self, model_id: str) -> bool:
        """Unload a model from memory"""
        if model_id not in self.loaded_models:
            return True
            
        try:
            del self.loaded_models[model_id]
            self.model_info[model_id].status = ModelStatus.UNLOADED
            self.logger.info(f"Model {model_id} unloaded")
            return True
        except Exception as e:
            self.logger.error(f"Failed to unload model {model_id}: {e}")
            return False
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics for all models"""
        stats = {
            "total_models": len(self.model_info),
            "loaded_models": len(self.loaded_models),
            "models": {}
        }
        
        for model_id, info in self.model_info.items():
            stats["models"][model_id] = {
                "status": info.status.value,
                "load_time": info.load_time,
                "last_used": info.last_used,
                "token_count": info.token_count,
                "trust_score": info.trust_score
            }
        
        return stats


# Example usage
async def main():
    """Example of using the MLX Model Server"""
    server = MLXModelServer()
    
    # Initialize server
    if await server.initialize():
        print("✅ Server initialized")
        
        # Get available models
        stats = server.get_model_stats()
        print(f"📊 Available models: {stats['total_models']}")
        
        # Generate some text
        model_id = "test-model"  # Replace with actual model
        async for token in server.generate(
            model_id=model_id,
            prompt="Hello, world!",
            stream=True
        ):
            print(token, end="", flush=True)
        
        print("\n✅ Generation complete")


if __name__ == "__main__":
    asyncio.run(main())