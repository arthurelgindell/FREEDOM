"""
Dynamic Model Detector for LM Studio
Detects what models are actually loaded and available
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
from .types import ModelType

class ModelDetector:
    """Detects available models in LM Studio"""
    
    def __init__(self, lm_studio_base: str = "http://localhost:1234/v1"):
        self.lm_studio_base = lm_studio_base
        self.available_models = {}
        self.model_capabilities = {}
    
    async def detect_available_models(self) -> Dict[str, List[str]]:
        """Detect what models are actually loaded in LM Studio"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.lm_studio_base}/models", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("data", [])
                        
                        # Categorize models by type
                        categorized = {
                            "code_models": [],
                            "general_models": [],
                            "embedding_models": []
                        }
                        
                        for model in models:
                            model_id = model.get("id", "")
                            
                            # Categorize based on model name
                            if "qwen" in model_id.lower() or "coder" in model_id.lower():
                                categorized["code_models"].append(model_id)
                            elif "embed" in model_id.lower():
                                categorized["embedding_models"].append(model_id)
                            else:
                                categorized["general_models"].append(model_id)
                        
                        self.available_models = categorized
                        return categorized
                    else:
                        print(f"⚠️  LM Studio not responding: {response.status}")
                        return {}
        except Exception as e:
            print(f"⚠️  Could not detect LM Studio models: {e}")
            return {}
    
    def get_best_model_for_task(self, task_type: str, complexity: int) -> Optional[str]:
        """Get the best available model for a specific task"""
        if not self.available_models:
            return None
        
        # For code generation tasks
        if task_type in ["code_generation", "code_refactor"]:
            if self.available_models.get("code_models"):
                return self.available_models["code_models"][0]  # Use first code model
            elif self.available_models.get("general_models"):
                return self.available_models["general_models"][0]  # Fallback to general
        
        # For other tasks
        elif self.available_models.get("general_models"):
            return self.available_models["general_models"][0]
        
        # Fallback to any available model
        all_models = (self.available_models.get("code_models", []) + 
                     self.available_models.get("general_models", []))
        return all_models[0] if all_models else None
    
    def get_model_capabilities(self, model_id: str) -> Dict[str, bool]:
        """Determine model capabilities based on model name"""
        capabilities = {
            "code_generation": False,
            "reasoning": False,
            "analysis": False,
            "creative": False,
            "completion": False
        }
        
        model_lower = model_id.lower()
        
        # Code models
        if "qwen" in model_lower and "coder" in model_lower:
            capabilities["code_generation"] = True
            capabilities["reasoning"] = True
        elif "qwen" in model_lower:
            capabilities["code_generation"] = True
            capabilities["reasoning"] = True
            capabilities["analysis"] = True
        elif "mistral" in model_lower:
            capabilities["reasoning"] = True
            capabilities["analysis"] = True
            capabilities["creative"] = True
        elif "embed" in model_lower:
            # Embedding models have limited capabilities
            capabilities["completion"] = True
        else:
            # Default capabilities for unknown models
            capabilities["reasoning"] = True
            capabilities["analysis"] = True
            capabilities["completion"] = True
        
        return capabilities
    
    async def test_model_performance(self, model_id: str) -> Dict[str, float]:
        """Test model performance with a simple prompt"""
        try:
            test_prompt = "Write a simple hello world function in Python"
            
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": test_prompt}],
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            start_time = asyncio.get_event_loop().time()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.lm_studio_base}/chat/completions",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        end_time = asyncio.get_event_loop().time()
                        
                        response_time = end_time - start_time
                        content = result["choices"][0]["message"]["content"]
                        tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        
                        return {
                            "response_time": response_time,
                            "tokens_per_second": tokens_used / response_time if response_time > 0 else 0,
                            "success": True,
                            "content_length": len(content)
                        }
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_model_summary(self) -> str:
        """Get a summary of available models"""
        if not self.available_models:
            return "No models detected in LM Studio"
        
        summary = "Available LM Studio Models:\n"
        
        for category, models in self.available_models.items():
            if models:
                summary += f"  {category.replace('_', ' ').title()}:\n"
                for model in models:
                    capabilities = self.get_model_capabilities(model)
                    caps = [k for k, v in capabilities.items() if v]
                    summary += f"    - {model} (capabilities: {', '.join(caps)})\n"
        
        return summary

# Global detector instance
_detector = None

async def get_model_detector() -> ModelDetector:
    """Get or create the global model detector"""
    global _detector
    if _detector is None:
        _detector = ModelDetector()
        await _detector.detect_available_models()
    return _detector
