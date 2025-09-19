import asyncio
import time
import aiohttp
import os
from typing import Dict, Any, Optional
from .model_router import IntelligentModelRouter, RoutingDecision
from .types import ModelType, TaskType

# Import the existing configuration system
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from api.core.config import get_settings

class UnifiedModelClient:
    """Single interface to all models with automatic routing"""
    
    def __init__(self, router: IntelligentModelRouter):
        self.router = router
        self.clients = self._setup_clients()
    
    def _setup_clients(self):
        """Setup clients for each model type"""
        clients = {
            ModelType.LOCAL_MLX: LMStudioClient(self.router.lm_studio_base)
        }
        
        # Only add commercial clients if API keys are available
        try:
            clients[ModelType.CLAUDE] = ClaudeClient()
        except ValueError:
            print("⚠️  Claude API key not set - Claude client unavailable")
            
        try:
            clients[ModelType.OPENAI] = OpenAIClient()
        except ValueError:
            print("⚠️  OpenAI API key not set - OpenAI client unavailable")
            
        try:
            clients[ModelType.GEMINI] = GeminiClient()
        except ValueError:
            print("⚠️  Gemini API key not set - Gemini client unavailable")
        
        return clients
    
    async def generate(
        self, 
        prompt: str, 
        task_type: TaskType = TaskType.CODE_GENERATION,
        complexity: int = 5,
        max_retries: int = 2,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate response with automatic routing and fallback"""
        
        attempt = 0
        local_failures = 0
        
        while attempt < max_retries:
            try:
                # Get routing decision
                routing_context = context or {}
                routing_context["local_failures"] = local_failures
                decision = await self.router.route_task(prompt, task_type, complexity, routing_context)
                
                # Execute with selected model
                if decision.selected_model not in self.clients:
                    raise Exception(f"Client for {decision.selected_model.value} not available - missing API key")
                
                client = self.clients[decision.selected_model]
                start_time = time.time()
                
                response = await client.generate(prompt, decision.model_name)
                
                execution_time = time.time() - start_time
                
                # Track performance
                self.router.cost_tracker.track_usage(
                    decision.selected_model,
                    decision.estimated_cost,  # Update with actual cost if available
                    response.get("tokens_used", 0)
                )
                
                return {
                    "response": response,
                    "routing_decision": decision,
                    "execution_time": execution_time,
                    "attempt": attempt + 1,
                    "success": True
                }
                
            except Exception as e:
                attempt += 1
                
                # Track local failures for escalation
                if decision.selected_model == ModelType.LOCAL_MLX:
                    local_failures += 1
                
                print(f"⚠️  Attempt {attempt} failed with {decision.selected_model.value}: {e}")
                
                # If local model failed and we have retries left, try commercial API
                if (decision.selected_model == ModelType.LOCAL_MLX and 
                    attempt < max_retries and 
                    local_failures >= 1):
                    
                    print(f"🔄 Escalating to commercial API after local failure...")
                    # Force escalation to commercial API
                    routing_context["local_failures"] = 3  # Force escalation
                    continue
                
                if attempt >= max_retries:
                    return {
                        "response": None,
                        "error": str(e),
                        "routing_decision": decision,
                        "success": False,
                        "attempts": attempt
                    }
        
        return {"success": False, "error": "Max retries exceeded"}

class LMStudioClient:
    """Client for your local LM Studio"""
    
    def __init__(self, base_url: str = None):
        if base_url:
            self.base_url = base_url
        else:
            # Try to get URL from existing config system
            try:
                settings = get_settings()
                self.base_url = settings.lm_studio_url.replace('/chat/completions', '')
            except:
                self.base_url = "http://localhost:1234/v1"
    
    async def generate(self, prompt: str, model_name: str) -> Dict[str, Any]:
        """Generate using LM Studio API"""
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "content": result["choices"][0]["message"]["content"],
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        "model": model_name
                    }
                else:
                    raise Exception(f"LM Studio error: {response.status}")

class ClaudeClient:
    """Client for Anthropic Claude API"""
    
    def __init__(self):
        # Try to get API key from existing config system first
        try:
            settings = get_settings()
            self.api_key = settings.anthropic_api_key
        except:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in config or environment")
    
    async def generate(self, prompt: str, model_name: str) -> Dict[str, Any]:
        """Generate using Claude API"""
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model_name,
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "content": result["content"][0]["text"],
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        "model": model_name
                    }
                else:
                    raise Exception(f"Claude API error: {response.status}")

class OpenAIClient:
    """Client for OpenAI API"""
    
    def __init__(self):
        # Try to get API key from existing config system first
        try:
            settings = get_settings()
            self.api_key = settings.openai_api_key
        except:
            self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in config or environment")
    
    async def generate(self, prompt: str, model_name: str) -> Dict[str, Any]:
        """Generate using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "content": result["choices"][0]["message"]["content"],
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        "model": model_name
                    }
                else:
                    raise Exception(f"OpenAI API error: {response.status}")

class GeminiClient:
    """Client for Google Gemini API"""
    
    def __init__(self):
        # Try to get API key from existing config system first
        try:
            settings = get_settings()
            self.api_key = settings.gemini_api_key
        except:
            self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in config or environment")
    
    async def generate(self, prompt: str, model_name: str) -> Dict[str, Any]:
        """Generate using Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000
            }
        }
        
        params = {"key": self.api_key}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                params=params,
                timeout=30
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "content": result["candidates"][0]["content"]["parts"][0]["text"],
                        "tokens_used": result.get("usageMetadata", {}).get("totalTokenCount", 0),
                        "model": model_name
                    }
                else:
                    raise Exception(f"Gemini API error: {response.status}")
