"""
FREEDOM State Manager
Manages conversation state and agent coordination using Redis
"""

import json
import redis
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    """Represents the state of a multi-agent conversation"""
    
    conversation_id: str
    participants: List[str] = Field(default_factory=list)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    consensus: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def add_message(self, agent: str, content: str, message_type: str = "text"):
        """Add a message to the conversation"""
        self.messages.append({
            "agent": agent,
            "content": content,
            "type": message_type,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
        if agent not in self.participants:
            self.participants.append(agent)


class StateManager:
    """Manages conversation state in Redis"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.verify_connection()
    
    def verify_connection(self):
        """Verify Redis connection"""
        try:
            self.redis_client.ping()
            print("✅ Redis connection established")
        except redis.ConnectionError:
            print("❌ Redis connection failed - ensure Redis container is running")
            raise
    
    def save_state(self, state: ConversationState):
        """Save conversation state to Redis"""
        key = f"conversation:{state.conversation_id}"
        value = state.model_dump_json()
        self.redis_client.set(key, value)
        self.redis_client.expire(key, 86400)  # 24 hour expiry
    
    def load_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Load conversation state from Redis"""
        key = f"conversation:{conversation_id}"
        value = self.redis_client.get(key)
        if value:
            return ConversationState.model_validate_json(value)
        return None
    
    def list_conversations(self) -> List[str]:
        """List all active conversations"""
        keys = self.redis_client.keys("conversation:*")
        return [key.split(":")[1] for key in keys]


if __name__ == "__main__":
    # Test the state manager
    manager = StateManager()
    
    # Create test conversation
    state = ConversationState(conversation_id="test-001")
    state.add_message("qwen", "I can implement this quickly using local compute")
    state.add_message("claude", "Let me design the architecture first")
    state.add_message("gpt4", "I'll validate the approach")
    
    # Save and load
    manager.save_state(state)
    loaded = manager.load_state("test-001")
    
    if loaded:
        print(f"✅ State management working: {len(loaded.messages)} messages")
    else:
        print("❌ State management failed")