"""
Claude Agent for FREEDOM
Handles Anthropic Claude API interactions
EQUAL member of the AI Council
"""

import os
from typing import Dict, Any, Optional
from anthropic import Anthropic
from .base import BaseAgent, AgentConfig


class ClaudeAgent(BaseAgent):
    """Agent that communicates with Anthropic Claude"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.client = Anthropic(api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY"))
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using Claude API"""
        
        messages = []
        
        # Add conversation history
        for msg in self.conversation_history[-5:]:
            messages.append(msg)
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=self.get_system_prompt(),
                messages=messages
            )
            
            content = response.content[0].text
            self.add_to_history("assistant", content)
            return content
            
        except Exception as e:
            return f"Claude Error: {str(e)}"
    
    async def validate_response(self, response: str) -> bool:
        """Validate Claude response"""
        if not response or "Error" in response:
            return False
        if len(response) < 5:
            return False
        return True


# Factory function
def create_claude_agent() -> ClaudeAgent:
    """Create a Claude 3 agent - EQUAL member of council"""
    config = AgentConfig(
        name="Claude",
        model="claude-3-haiku-20240307",
        role="Deep reasoning and architecture specialist",
        capabilities=[
            "Architectural design",
            "Deep logical reasoning",
            "Code review and analysis",
            "Complex problem decomposition"
        ],
        temperature=0.5,
        max_tokens=2000
    )
    return ClaudeAgent(config)