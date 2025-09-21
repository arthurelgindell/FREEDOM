"""
FREEDOM Agent Base Class
Defines the interface for all AI agents in the system
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import asyncio


class AgentConfig(BaseModel):
    """Configuration for an agent"""
    name: str
    model: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    role: str = "assistant"
    capabilities: List[str] = Field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all FREEDOM agents"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.conversation_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a response to a prompt"""
        pass
    
    @abstractmethod
    async def validate_response(self, response: str) -> bool:
        """Validate if a response meets quality criteria"""
        pass
    
    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        return f"""You are {self.config.name}, an AI agent in the FREEDOM collaborative system.
Your role: {self.config.role}
Your capabilities: {', '.join(self.config.capabilities)}

You work collaboratively with other AI agents to solve problems.
Always be concise, accurate, and focus on your specialized capabilities.
When you see solutions from other agents, build upon them constructively."""
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name='{self.config.name}' model='{self.config.model}'>"