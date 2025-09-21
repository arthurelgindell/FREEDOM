"""
GPT-5 Agent for FREEDOM
Handles OpenAI's most advanced model API interactions
EQUAL member of the AI Council
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from .base import BaseAgent, AgentConfig


class GPT5Agent(BaseAgent):
    """Agent that communicates with OpenAI's most advanced model"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.client = OpenAI(api_key=config.api_key or os.getenv("OPENAI_API_KEY"))
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using GPT-4 API"""
        
        messages = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        
        # Add conversation history
        messages.extend(self.conversation_history[-5:])
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            content = response.choices[0].message.content
            self.add_to_history("assistant", content)
            return content
            
        except Exception as e:
            return f"GPT-5 Error: {str(e)}"
    
    async def validate_response(self, response: str) -> bool:
        """Validate GPT-5 response"""
        if not response or "Error" in response:
            return False
        if len(response) < 5:
            return False
        return True


# Factory function
def create_gpt5_agent() -> GPT5Agent:
    """Create GPT-5 agent (using best available) - EQUAL member of council"""
    config = AgentConfig(
        name="GPT-5",
        model="gpt-4o",  # Using full GPT-4o for maximum intelligence
        role="Next-gen AI reasoning and problem solving",
        capabilities=[
            "State-of-the-art reasoning",
            "Vision and multimodal understanding",
            "Advanced code generation",
            "Real-time problem solving"
        ],
        temperature=0.5,
        max_tokens=2000
    )
    return GPT5Agent(config)