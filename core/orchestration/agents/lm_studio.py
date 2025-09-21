"""
LM Studio Agent for FREEDOM
Handles local model execution via LM Studio API
"""

import aiohttp
import json
from typing import Dict, Any, Optional
from .base import BaseAgent, AgentConfig


class LMStudioAgent(BaseAgent):
    """Agent that communicates with LM Studio local models"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.config.endpoint = config.endpoint or "http://localhost:1234/v1/chat/completions"
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using LM Studio API"""
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history[-5:])  # Last 5 messages
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        self.add_to_history("assistant", content)
                        return content
                    else:
                        error = await response.text()
                        return f"Error from LM Studio: {error}"
        except Exception as e:
            return f"Failed to connect to LM Studio: {str(e)}"
    
    async def validate_response(self, response: str) -> bool:
        """Basic validation for LM Studio responses"""
        # Check response is not empty and not an error
        if not response or "Error" in response or "Failed" in response:
            return False
        
        # Check minimum length
        if len(response) < 10:
            return False
        
        return True
    
    async def execute_code(self, code: str) -> Dict[str, Any]:
        """Execute code locally (for Qwen Coder model)"""
        # This would integrate with the Truth Engine for validation
        # For now, return a placeholder
        return {
            "executed": False,
            "reason": "Code execution integration pending"
        }


# Factory function
def create_qwen_agent() -> LMStudioAgent:
    """Create a Qwen 2.5 Coder agent"""
    config = AgentConfig(
        name="Qwen",
        model="qwen2.5-coder-32b",
        role="Local execution specialist",
        capabilities=[
            "Fast code generation",
            "Local execution",
            "File system operations",
            "High-velocity iteration"
        ],
        temperature=0.3  # Lower temperature for code
    )
    return LMStudioAgent(config)