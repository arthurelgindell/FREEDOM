"""
FREEDOM AI Council Graph
Orchestrates multi-agent collaboration using LangGraph
"""

from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import asyncio
import uuid

from ..agents.base import BaseAgent
from ..agents.lm_studio import create_qwen_agent
from ..agents.claude import create_claude_agent
from ..agents.openai_gpt import create_gpt5_agent
from ..agents.gemini import create_gemini_agent
from ..state.manager import StateManager, ConversationState


class AICouncil:
    """Orchestrates the AI Council collaboration"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.state_manager = StateManager()
        self.graph = None
        self.setup_agents()
        self.build_graph()
    
    def setup_agents(self):
        """Initialize ALL FOUR agents as EQUALS"""
        # ALL AGENTS ARE EQUAL MEMBERS OF THE COUNCIL
        
        # Local execution specialist
        self.agents["qwen"] = create_qwen_agent()
        
        # Deep reasoning specialist
        self.agents["claude"] = create_claude_agent()
        
        # Next-gen problem solving
        self.agents["gpt5"] = create_gpt5_agent()
        
        # Multimodal and long context
        self.agents["gemini"] = create_gemini_agent()
        
        print(f"✅ Initialized {len(self.agents)} EQUAL agents in the Council")
    
    def build_graph(self):
        """Build the LangGraph workflow"""
        # Define state schema
        from typing import TypedDict
        
        class GraphState(TypedDict):
            prompt: str
            responses: Dict[str, str]
            consensus: str
            final_response: str
            current_agent: str
            conversation_id: str
            context: Dict[str, Any]
        
        workflow = StateGraph(GraphState)
        
        # Add nodes for each agent
        for agent_name in self.agents:
            workflow.add_node(agent_name, self.agent_node)
        
        # Add consensus node
        workflow.add_node("consensus", self.consensus_node)
        
        # Add edges (fully connected for now)
        for agent_name in self.agents:
            workflow.add_edge(agent_name, "consensus")
        
        # Set entry point
        workflow.set_entry_point(list(self.agents.keys())[0])
        
        # Compile
        memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=memory)
        
        print("✅ Council graph compiled")
    
    async def agent_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state through an agent"""
        agent_name = state.get("current_agent")
        agent = self.agents.get(agent_name)
        
        if not agent:
            return state
        
        prompt = state.get("prompt", "")
        response = await agent.generate_response(prompt, state)
        
        # Update state
        state["responses"] = state.get("responses", {})
        state["responses"][agent_name] = response
        
        return state
    
    async def consensus_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Determine consensus from agent responses"""
        responses = state.get("responses", {})
        
        if not responses:
            state["consensus"] = "No responses received"
            return state
        
        # Simple consensus: most detailed response wins for now
        # TODO: Implement sophisticated consensus algorithm
        longest_response = max(responses.items(), key=lambda x: len(x[1]))
        state["consensus"] = f"Selected {longest_response[0]}'s approach"
        state["final_response"] = longest_response[1]
        
        return state
    
    async def process_request(self, prompt: str, conversation_id: str = None) -> Dict[str, Any]:
        """Process a request through the council"""
        
        # Create or load conversation state
        if conversation_id:
            conv_state = self.state_manager.load_state(conversation_id)
            if not conv_state:
                conv_state = ConversationState(conversation_id=conversation_id)
        else:
            conv_state = ConversationState(conversation_id=str(uuid.uuid4()))
        
        # Prepare initial state
        initial_state = {
            "prompt": prompt,
            "conversation_id": conv_state.conversation_id,
            "responses": {},
            "context": conv_state.context
        }
        
        # Run through each agent
        results = {}
        for agent_name, agent in self.agents.items():
            print(f"🤖 Consulting {agent_name}...")
            response = await agent.generate_response(prompt, initial_state)
            results[agent_name] = response
            conv_state.add_message(agent_name, response)
        
        # Determine consensus
        initial_state["responses"] = results
        final_state = await self.consensus_node(initial_state)
        
        # Save state
        conv_state.consensus = final_state.get("consensus")
        self.state_manager.save_state(conv_state)
        
        return {
            "conversation_id": conv_state.conversation_id,
            "responses": results,
            "consensus": final_state.get("consensus"),
            "final_response": final_state.get("final_response"),
            "agent_count": len(self.agents)
        }


# Test function
async def test_council():
    """Test the AI Council"""
    council = AICouncil()
    
    result = await council.process_request(
        "How should we implement a Redis cache layer in Python?"
    )
    
    print("\n=== AI Council Results ===")
    print(f"Conversation ID: {result['conversation_id']}")
    print(f"Consensus: {result['consensus']}")
    print(f"\nFinal Response:\n{result['final_response']}")


if __name__ == "__main__":
    asyncio.run(test_council())