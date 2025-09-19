"""
Gemini Agent for FREEDOM
Handles Google Gemini API interactions
EQUAL member of the AI Council
"""

import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from .base import BaseAgent, AgentConfig


class GeminiAgent(BaseAgent):
    """Agent that communicates with Google Gemini"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        genai.configure(api_key=config.api_key or os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(config.model)
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using Gemini API"""
        
        # Build conversation context
        full_prompt = self.get_system_prompt() + "\n\n"
        
        # Add recent history
        for msg in self.conversation_history[-5:]:
            full_prompt += f"{msg['role']}: {msg['content']}\n"
        
        # Add current prompt
        full_prompt += f"user: {prompt}\nassistant: "
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_tokens
                )
            )
            
            content = response.text
            self.add_to_history("assistant", content)
            return content
            
        except Exception as e:
            return f"Gemini Error: {str(e)}"
    
    async def validate_response(self, response: str) -> bool:
        """Validate Gemini response"""
        if not response or "Error" in response:
            return False
        if len(response) < 5:
            return False
        return True


# Factory function
def create_gemini_agent() -> GeminiAgent:
    """Create a Gemini agent - EQUAL member of council"""
    config = AgentConfig(
        name="Gemini",
        model="gemini-1.5-flash",
        role="Multimodal analysis and long context processing",
        capabilities=[
            "1M+ token context window",
            "Image and video analysis",
            "Document processing",
            "Multilingual understanding"
        ],
        temperature=0.5,
        max_tokens=2000
    )
    return GeminiAgent(config)