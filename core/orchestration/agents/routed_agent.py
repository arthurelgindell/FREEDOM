"""
Intelligent Routed Agent for FREEDOM
Uses the model router to automatically select the best model for each task
"""

import asyncio
from typing import Dict, Any, Optional, List
from .base import BaseAgent, AgentConfig
from ..model_router import IntelligentModelRouter, TaskType, ModelType
from ..model_client import UnifiedModelClient
from ..router_analytics import RouterAnalytics

class RoutedAgent(BaseAgent):
    """Agent that uses intelligent routing to select optimal models"""
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.router = IntelligentModelRouter()
        self.client = UnifiedModelClient(self.router)
        self.analytics = RouterAnalytics()
        
        # Override capabilities to include routing
        self.config.capabilities.extend([
            "Intelligent model selection",
            "Cost optimization",
            "Performance monitoring",
            "Automatic fallback"
        ])
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate response using intelligent routing"""
        
        context = context or {}
        
        # Determine task type and complexity from context
        task_type = self._determine_task_type(prompt, context)
        complexity = self._assess_complexity(prompt, context)
        
        # Add routing context
        routing_context = {
            "agent_name": self.config.name,
            "agent_role": self.config.role,
            "conversation_length": len(self.conversation_history),
            **context
        }
        
        # Generate with routing
        result = await self.client.generate(
            prompt=prompt,
            task_type=task_type,
            complexity=complexity,
            max_retries=2
        )
        
        # Log for analytics
        if result["success"]:
            self.analytics.log_execution(
                result["routing_decision"],
                {
                    "objective": prompt[:100],
                    "task_type": task_type.value,
                    "complexity": complexity,
                    "execution_time": result["execution_time"],
                    "success": True,
                    "response": result["response"]
                }
            )
            
            # Add to conversation history
            response_content = result["response"]["content"]
            self.add_to_history("assistant", response_content)
            
            return response_content
        else:
            error_msg = f"Generation failed: {result.get('error', 'Unknown error')}"
            self.add_to_history("assistant", error_msg)
            return error_msg
    
    def _determine_task_type(self, prompt: str, context: Dict[str, Any]) -> TaskType:
        """Determine the task type from prompt and context"""
        
        # Check for explicit task type in context
        if "task_type" in context:
            try:
                return TaskType(context["task_type"])
            except ValueError:
                pass
        
        # Analyze prompt content
        prompt_lower = prompt.lower()
        
        # Code generation patterns
        code_patterns = [
            "write", "create", "implement", "build", "develop", "code",
            "function", "class", "method", "algorithm", "script"
        ]
        if any(pattern in prompt_lower for pattern in code_patterns):
            return TaskType.CODE_GENERATION
        
        # Code refactoring patterns
        refactor_patterns = [
            "refactor", "optimize", "improve", "clean up", "restructure",
            "refactor", "modify", "update", "enhance"
        ]
        if any(pattern in prompt_lower for pattern in refactor_patterns):
            return TaskType.CODE_REFACTOR
        
        # Reasoning patterns
        reasoning_patterns = [
            "analyze", "explain", "why", "how", "reasoning", "logic",
            "think through", "consider", "evaluate", "assess"
        ]
        if any(pattern in prompt_lower for pattern in reasoning_patterns):
            return TaskType.REASONING
        
        # Analysis patterns
        analysis_patterns = [
            "analyze", "examine", "investigate", "study", "review",
            "compare", "contrast", "evaluate", "assess"
        ]
        if any(pattern in prompt_lower for pattern in analysis_patterns):
            return TaskType.ANALYSIS
        
        # Creative patterns
        creative_patterns = [
            "creative", "imagine", "design", "brainstorm", "ideate",
            "story", "narrative", "artistic", "innovative"
        ]
        if any(pattern in prompt_lower for pattern in creative_patterns):
            return TaskType.CREATIVE
        
        # Default to completion for general tasks
        return TaskType.COMPLETION
    
    def _assess_complexity(self, prompt: str, context: Dict[str, Any]) -> int:
        """Assess task complexity on a scale of 1-10"""
        
        # Check for explicit complexity in context
        if "complexity" in context:
            return max(1, min(10, int(context["complexity"])))
        
        # Base complexity on prompt characteristics
        complexity = 3  # Default moderate complexity
        
        # Length factor
        word_count = len(prompt.split())
        if word_count > 100:
            complexity += 2
        elif word_count > 50:
            complexity += 1
        
        # Technical complexity indicators
        technical_terms = [
            "algorithm", "architecture", "system", "framework", "database",
            "api", "microservice", "distributed", "concurrent", "parallel",
            "machine learning", "neural network", "optimization", "scalability"
        ]
        if any(term in prompt.lower() for term in technical_terms):
            complexity += 2
        
        # Multi-step task indicators
        multi_step_indicators = [
            "step", "phase", "stage", "process", "workflow", "pipeline",
            "first", "then", "next", "finally", "after", "before"
        ]
        if any(indicator in prompt.lower() for indicator in multi_step_indicators):
            complexity += 1
        
        # Problem-solving indicators
        problem_indicators = [
            "problem", "issue", "bug", "error", "debug", "troubleshoot",
            "fix", "resolve", "solve", "challenge"
        ]
        if any(indicator in prompt.lower() for indicator in problem_indicators):
            complexity += 1
        
        # Research/analysis indicators
        research_indicators = [
            "research", "investigate", "analyze", "study", "examine",
            "compare", "evaluate", "assess", "review"
        ]
        if any(indicator in prompt.lower() for indicator in research_indicators):
            complexity += 1
        
        return max(1, min(10, complexity))
    
    async def validate_response(self, response: str) -> bool:
        """Enhanced validation using routing context"""
        
        # Basic validation
        if not response or "Error" in response or "Failed" in response:
            return False
        
        if len(response) < 10:
            return False
        
        # Check for model-specific quality indicators
        if "I apologize" in response or "I cannot" in response:
            return False
        
        # Check for incomplete responses
        if response.endswith("...") or response.count(".") < 1:
            return False
        
        return True
    
    async def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics and performance metrics"""
        return self.analytics.get_model_performance_report()
    
    async def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for router optimization"""
        return self.analytics.get_optimization_recommendations()
    
    def get_system_prompt(self) -> str:
        """Enhanced system prompt with routing awareness"""
        base_prompt = super().get_system_prompt()
        
        routing_info = f"""
You are powered by an intelligent model router that automatically selects the best AI model for each task:
- Local models (Qwen) for fast, simple tasks
- Commercial APIs (Claude, OpenAI, Gemini) for complex reasoning
- Automatic fallback and cost optimization

Current routing decision will be made based on task complexity and type.
Focus on delivering high-quality responses regardless of the underlying model.
"""
        
        return base_prompt + routing_info


# Factory functions for different routed agents
def create_routed_coder_agent() -> RoutedAgent:
    """Create a routed agent optimized for coding tasks"""
    config = AgentConfig(
        name="RoutedCoder",
        model="intelligent_router",
        role="Intelligent code generation specialist",
        capabilities=[
            "Code generation",
            "Code refactoring", 
            "Debugging",
            "Architecture design",
            "Performance optimization",
            "Intelligent model selection"
        ],
        temperature=0.3
    )
    return RoutedAgent(config)

def create_routed_analyst_agent() -> RoutedAgent:
    """Create a routed agent optimized for analysis tasks"""
    config = AgentConfig(
        name="RoutedAnalyst",
        model="intelligent_router",
        role="Intelligent analysis specialist",
        capabilities=[
            "Data analysis",
            "Research",
            "Reasoning",
            "Problem solving",
            "Strategic thinking",
            "Intelligent model selection"
        ],
        temperature=0.5
    )
    return RoutedAgent(config)

def create_routed_general_agent() -> RoutedAgent:
    """Create a general-purpose routed agent"""
    config = AgentConfig(
        name="RoutedGeneral",
        model="intelligent_router",
        role="General-purpose intelligent assistant",
        capabilities=[
            "General assistance",
            "Creative tasks",
            "Problem solving",
            "Research",
            "Writing",
            "Intelligent model selection"
        ],
        temperature=0.7
    )
    return RoutedAgent(config)

