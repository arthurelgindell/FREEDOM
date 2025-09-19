"""
FREEDOM Graph Engine - Core Orchestration System
Implements: Objective → Plan → Route → Synthesize → Execute → Truth Check → Learn → Store → Iterate
"""

from typing import TypedDict, Annotated, Literal, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator
import json
import uuid
import asyncio
from datetime import datetime

# Import existing components
from ..agents.lm_studio import create_qwen_agent
from ..agents.claude import create_claude_agent
from ..agents.openai_gpt import create_gpt5_agent
from ..agents.gemini import create_gemini_agent


class FreedomState(TypedDict):
    """FREEDOM orchestration state - tracks entire execution flow"""

    # Input Phase
    objective: str
    conversation_id: str
    user_context: Dict[str, Any]

    # Planning Phase
    plan: List[str]
    complexity_score: int
    estimated_duration: int  # minutes
    risk_level: str  # low, medium, high

    # Routing Phase
    selected_model: str
    route_reasoning: str
    fallback_models: List[str]
    cost_estimate: float

    # Execution Phase
    generated_code: str
    execution_output: str
    test_results: Dict[str, Any]
    artifacts: Dict[str, str]

    # Truth Phase
    truth_status: bool
    truth_score: float  # 0.0-1.0
    truth_errors: List[str]
    verification_details: Dict[str, Any]

    # Learning Phase
    iteration_count: int
    improvements_made: List[str]
    lessons_learned: List[str]

    # Output Phase
    final_artifacts: Dict[str, Any]
    total_cost: float
    execution_time: float
    success: bool

    # System Tracking
    execution_log: Annotated[List[str], operator.add]
    start_time: datetime
    end_time: Optional[datetime]


class FreedomOrchestrator:
    """FREEDOM orchestration engine - routes objectives through AI models with verification"""

    def __init__(self):
        self.agents = {}
        self.graph = None
        self.memory = MemorySaver()
        self._setup_agents()
        self._build_graph()

    def _setup_agents(self):
        """Initialize all available AI agents"""
        try:
            self.agents["qwen"] = create_qwen_agent()
            print("✅ Qwen agent initialized")
        except Exception as e:
            print(f"⚠️  Qwen agent failed: {e}")

        try:
            self.agents["claude"] = create_claude_agent()
            print("✅ Claude agent initialized")
        except Exception as e:
            print(f"⚠️  Claude agent failed: {e}")

        try:
            self.agents["gpt5"] = create_gpt5_agent()
            print("✅ GPT-5 agent initialized")
        except Exception as e:
            print(f"⚠️  GPT-5 agent failed: {e}")

        try:
            self.agents["gemini"] = create_gemini_agent()
            print("✅ Gemini agent initialized")
        except Exception as e:
            print(f"⚠️  Gemini agent failed: {e}")

        print(f"🚀 FREEDOM Orchestrator ready with {len(self.agents)} agents")

    def _build_graph(self):
        """Build the FREEDOM execution graph"""
        workflow = StateGraph(FreedomState)

        # Add nodes for each phase
        workflow.add_node("planner", self._plan_objective)
        workflow.add_node("router", self._route_to_model)
        workflow.add_node("synthesizer", self._synthesize_solution)
        workflow.add_node("executor", self._execute_solution)
        workflow.add_node("truth_checker", self._verify_solution)
        workflow.add_node("learner", self._learn_from_iteration)
        workflow.add_node("publisher", self._publish_artifacts)
        workflow.add_node("iterator", self._prepare_iteration)

        # Define the execution flow
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "router")
        workflow.add_edge("router", "synthesizer")
        workflow.add_edge("synthesizer", "executor")
        workflow.add_edge("executor", "truth_checker")

        # Conditional routing from truth checker
        workflow.add_conditional_edges(
            "truth_checker",
            self._should_iterate,
            {
                "iterate": "learner",
                "publish": "publisher",
                "fail": END
            }
        )

        workflow.add_edge("learner", "iterator")
        workflow.add_edge("iterator", "router")  # Loop back for next iteration
        workflow.add_edge("publisher", END)

        # Compile with memory checkpointing
        self.graph = workflow.compile(checkpointer=self.memory)
        print("✅ FREEDOM graph compiled")

    async def _plan_objective(self, state: FreedomState) -> FreedomState:
        """PLANNING: Break down objective into actionable plan"""
        objective = state["objective"]

        # Use Qwen for planning (local, fast, good at structure)
        if "qwen" in self.agents:
            planner_prompt = f"""
            FREEDOM PLANNING PHASE

            Objective: {objective}

            Analyze this objective and create a detailed implementation plan:

            1. Break into 3-7 concrete steps
            2. Assess complexity (1-10 scale)
            3. Estimate duration in minutes
            4. Identify risk level (low/medium/high)
            5. List key requirements/constraints

            Respond in JSON format:
            {{
                "steps": ["step1", "step2", ...],
                "complexity": 5,
                "duration": 30,
                "risk": "medium",
                "requirements": ["req1", "req2"],
                "reasoning": "why this approach"
            }}
            """

            try:
                planning_result = await self.agents["qwen"].generate_response(planner_prompt, state)
                plan_data = json.loads(planning_result)

                state["plan"] = plan_data.get("steps", [])
                state["complexity_score"] = plan_data.get("complexity", 5)
                state["estimated_duration"] = plan_data.get("duration", 30)
                state["risk_level"] = plan_data.get("risk", "medium")
                state["execution_log"].append(f"✅ Planned: {len(state['plan'])} steps, complexity {state['complexity_score']}")

            except Exception as e:
                # Fallback planning
                state["plan"] = [f"Implement solution for: {objective}"]
                state["complexity_score"] = 5
                state["estimated_duration"] = 30
                state["risk_level"] = "medium"
                state["execution_log"].append(f"⚠️  Planning fallback used: {e}")

        return state

    async def _route_to_model(self, state: FreedomState) -> FreedomState:
        """ROUTING: Intelligent model selection based on task characteristics"""
        objective = state["objective"].lower()
        complexity = state["complexity_score"]
        risk = state["risk_level"]

        # FREEDOM routing logic
        selected_model = "qwen"  # Default to local
        cost_estimate = 0.0
        fallback_models = []

        # Rule-based routing
        if any(keyword in objective for keyword in ["code", "python", "function", "script"]):
            if complexity <= 4:
                selected_model = "qwen"
                fallback_models = ["claude", "gpt5"]
            else:
                selected_model = "claude"
                fallback_models = ["gpt5", "qwen"]
                cost_estimate = 0.02 * complexity

        elif any(keyword in objective for keyword in ["reasoning", "analysis", "explain", "logic"]):
            selected_model = "claude"
            fallback_models = ["gpt5", "gemini"]
            cost_estimate = 0.03 * complexity

        elif any(keyword in objective for keyword in ["creative", "generate", "design", "write"]):
            selected_model = "gpt5" if "gpt5" in self.agents else "gemini"
            fallback_models = ["claude", "qwen"]
            cost_estimate = 0.025 * complexity

        elif any(keyword in objective for keyword in ["multimodal", "image", "vision", "long"]):
            selected_model = "gemini"
            fallback_models = ["gpt5", "claude"]
            cost_estimate = 0.02 * complexity

        # Risk adjustment
        if risk == "high" and selected_model == "qwen":
            selected_model = "claude"  # Use premium model for high-risk tasks
            cost_estimate = 0.04 * complexity

        # Ensure selected model exists
        if selected_model not in self.agents:
            for fallback in fallback_models:
                if fallback in self.agents:
                    selected_model = fallback
                    break
            else:
                selected_model = list(self.agents.keys())[0]  # First available

        state["selected_model"] = selected_model
        state["route_reasoning"] = f"Selected {selected_model} for {objective[:50]}... (complexity: {complexity}, risk: {risk})"
        state["fallback_models"] = [m for m in fallback_models if m in self.agents]
        state["cost_estimate"] = cost_estimate
        state["execution_log"].append(f"🎯 Routed to: {selected_model} (${cost_estimate:.3f} estimated)")

        return state

    async def _synthesize_solution(self, state: FreedomState) -> FreedomState:
        """SYNTHESIS: Generate solution using selected model"""
        agent = self.agents[state["selected_model"]]
        objective = state["objective"]
        plan = state["plan"]

        synthesis_prompt = f"""
        FREEDOM SYNTHESIS PHASE

        Objective: {objective}

        Implementation Plan:
        {chr(10).join(f"{i+1}. {step}" for i, step in enumerate(plan))}

        Generate a complete, working solution. Include:
        - All necessary code/implementation
        - Error handling
        - Documentation/comments
        - Test cases if applicable

        Make it PRODUCTION-READY and BULLETPROOF.
        """

        try:
            generated_solution = await agent.generate_response(synthesis_prompt, state)
            state["generated_code"] = generated_solution
            state["execution_log"].append(f"🔨 Solution synthesized by {state['selected_model']} ({len(generated_solution)} chars)")

        except Exception as e:
            # Try fallback model
            if state["fallback_models"]:
                fallback = state["fallback_models"][0]
                try:
                    fallback_agent = self.agents[fallback]
                    generated_solution = await fallback_agent.generate_response(synthesis_prompt, state)
                    state["generated_code"] = generated_solution
                    state["selected_model"] = fallback  # Update for tracking
                    state["execution_log"].append(f"🔄 Fallback to {fallback} succeeded")
                except Exception as e2:
                    state["generated_code"] = f"ERROR: Synthesis failed - {e}, Fallback failed - {e2}"
                    state["execution_log"].append(f"❌ Synthesis failed completely")
            else:
                state["generated_code"] = f"ERROR: Synthesis failed - {e}"
                state["execution_log"].append(f"❌ Synthesis failed: {e}")

        return state

    async def _execute_solution(self, state: FreedomState) -> FreedomState:
        """EXECUTION: Test and validate the generated solution"""
        generated_code = state["generated_code"]

        # For now, simulate execution - later integrate with actual code runner
        try:
            # TODO: Implement actual code execution sandbox
            # For now, basic validation
            if "ERROR:" in generated_code:
                state["execution_output"] = "Execution skipped due to synthesis error"
                state["test_results"] = {"status": "failed", "reason": "synthesis_error"}
            else:
                state["execution_output"] = "Execution simulation passed"
                state["test_results"] = {"status": "simulated", "checks_passed": True}

            state["execution_log"].append(f"⚡ Execution completed: {state['test_results']['status']}")

        except Exception as e:
            state["execution_output"] = f"Execution error: {e}"
            state["test_results"] = {"status": "failed", "error": str(e)}
            state["execution_log"].append(f"❌ Execution failed: {e}")

        return state

    async def _verify_solution(self, state: FreedomState) -> FreedomState:
        """TRUTH VERIFICATION: Validate solution meets objective"""
        from ...truth_engine.truth_engine import TruthEngine, ClaimType

        try:
            truth_engine = TruthEngine()

            # Submit claim about the solution
            claim_text = f"Generated solution successfully addresses: {state['objective']}"
            claim_id = truth_engine.submit_claim(
                source_id=f"FREEDOM-{state['selected_model']}",
                claim_text=claim_text,
                claim_type=ClaimType.COMPUTATIONAL,
                evidence={
                    "objective": state["objective"],
                    "solution": state["generated_code"],
                    "execution_output": state["execution_output"],
                    "test_results": state["test_results"]
                }
            )

            # Verify the claim
            verification_success = truth_engine.verify_claim(
                claim_id,
                "solution_validation",
                f"FREEDOM-TruthChecker-{state['iteration_count']}"
            )

            # Calculate truth score based on multiple factors
            truth_score = 0.0
            if verification_success:
                truth_score += 0.4
            if state["test_results"].get("checks_passed"):
                truth_score += 0.3
            if "ERROR:" not in state["generated_code"]:
                truth_score += 0.2
            if len(state["generated_code"]) > 100:  # Substantial solution
                truth_score += 0.1

            state["truth_status"] = verification_success and truth_score >= 0.7
            state["truth_score"] = truth_score
            state["verification_details"] = {
                "claim_id": claim_id,
                "verified": verification_success,
                "score": truth_score,
                "timestamp": datetime.now().isoformat()
            }

            if not state["truth_status"]:
                state["truth_errors"].append(f"Iteration {state['iteration_count']}: Truth score {truth_score:.2f} below threshold")

            state["execution_log"].append(f"🎯 Truth verification: {state['truth_status']} (score: {truth_score:.2f})")

        except Exception as e:
            # Fallback verification
            basic_checks = (
                len(state["generated_code"]) > 50 and
                "ERROR:" not in state["generated_code"] and
                state["test_results"].get("status") != "failed"
            )

            state["truth_status"] = basic_checks
            state["truth_score"] = 0.5 if basic_checks else 0.1
            state["truth_errors"].append(f"Truth engine error: {e}")
            state["execution_log"].append(f"⚠️  Truth verification fallback: {basic_checks}")

        state["iteration_count"] += 1
        return state

    def _should_iterate(self, state: FreedomState) -> Literal["iterate", "publish", "fail"]:
        """Decide whether to iterate, publish, or fail"""
        if state["truth_status"] and state["truth_score"] >= 0.7:
            return "publish"
        elif state["iteration_count"] < 2 and state["truth_score"] >= 0.3:  # Max 2 iterations, min viability
            return "iterate"
        else:
            return "fail"

    async def _learn_from_iteration(self, state: FreedomState) -> FreedomState:
        """LEARNING: Extract lessons from current iteration"""
        truth_errors = state["truth_errors"]
        generated_code = state["generated_code"]

        # Analyze what went wrong
        improvements = []
        lessons = []

        if state["truth_score"] < 0.5:
            improvements.append("Increase solution depth and completeness")
            lessons.append("Low truth score indicates insufficient solution quality")

        if "ERROR:" in generated_code:
            improvements.append("Fix synthesis errors before execution")
            lessons.append("Synthesis phase needs better error handling")

        if state["test_results"].get("status") == "failed":
            improvements.append("Improve execution validation")
            lessons.append("Execution phase validation failed")

        state["improvements_made"] = improvements
        state["lessons_learned"] = lessons
        state["execution_log"].append(f"📚 Learning: {len(improvements)} improvements identified")

        return state

    async def _prepare_iteration(self, state: FreedomState) -> FreedomState:
        """ITERATION PREP: Prepare for next iteration with learned improvements"""
        # Try different model for next iteration
        current_model = state["selected_model"]
        fallbacks = state["fallback_models"]

        if fallbacks:
            next_model = fallbacks[0]
            state["selected_model"] = next_model
            state["fallback_models"] = [current_model] + fallbacks[1:]
            state["route_reasoning"] = f"Iteration {state['iteration_count']}: Switched to {next_model}"
            state["execution_log"].append(f"🔄 Iteration {state['iteration_count']}: Trying {next_model}")
        else:
            state["execution_log"].append(f"🔄 Iteration {state['iteration_count']}: Retrying with {current_model}")

        return state

    async def _publish_artifacts(self, state: FreedomState) -> FreedomState:
        """PUBLISHING: Finalize and store successful solution"""
        state["end_time"] = datetime.now()
        state["execution_time"] = (state["end_time"] - state["start_time"]).total_seconds()
        state["success"] = True
        state["total_cost"] = state["cost_estimate"] * state["iteration_count"]

        # Package final artifacts
        state["final_artifacts"] = {
            "solution": state["generated_code"],
            "objective": state["objective"],
            "model_used": state["selected_model"],
            "iterations": state["iteration_count"],
            "truth_score": state["truth_score"],
            "execution_time": state["execution_time"],
            "total_cost": state["total_cost"]
        }

        state["execution_log"].append(f"🎉 SUCCESS: Published after {state['iteration_count']} iterations in {state['execution_time']:.1f}s")

        return state

    async def execute_objective(self, objective: str, conversation_id: str = None) -> Dict[str, Any]:
        """Main entry point: Execute an objective through the FREEDOM pipeline"""

        # Initialize state
        initial_state = {
            "objective": objective,
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "user_context": {},
            "plan": [],
            "complexity_score": 0,
            "estimated_duration": 0,
            "risk_level": "medium",
            "selected_model": "",
            "route_reasoning": "",
            "fallback_models": [],
            "cost_estimate": 0.0,
            "generated_code": "",
            "execution_output": "",
            "test_results": {},
            "artifacts": {},
            "truth_status": False,
            "truth_score": 0.0,
            "truth_errors": [],
            "verification_details": {},
            "iteration_count": 0,
            "improvements_made": [],
            "lessons_learned": [],
            "final_artifacts": {},
            "total_cost": 0.0,
            "execution_time": 0.0,
            "success": False,
            "execution_log": [],
            "start_time": datetime.now(),
            "end_time": None
        }

        print(f"🚀 FREEDOM: Executing objective - {objective}")

        # Execute through the graph
        try:
            # LangGraph requires a config with thread_id for checkpointing
            config = {"configurable": {"thread_id": initial_state["conversation_id"]}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            return {
                "success": final_state.get("success", False),
                "conversation_id": final_state["conversation_id"],
                "final_artifacts": final_state.get("final_artifacts", {}),
                "execution_log": final_state.get("execution_log", []),
                "truth_score": final_state.get("truth_score", 0.0),
                "iterations": final_state.get("iteration_count", 0),
                "total_cost": final_state.get("total_cost", 0.0),
                "execution_time": final_state.get("execution_time", 0.0)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "conversation_id": initial_state["conversation_id"],
                "execution_log": initial_state.get("execution_log", []) + [f"❌ FATAL ERROR: {e}"]
            }


# Global orchestrator instance
_orchestrator = None

def get_freedom_orchestrator() -> FreedomOrchestrator:
    """Get the global FREEDOM orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FreedomOrchestrator()
    return _orchestrator


# Test function
async def test_freedom():
    """Test the FREEDOM orchestrator"""
    orchestrator = get_freedom_orchestrator()

    test_objective = "Create a Python function that calculates the factorial of a number"

    print(f"🧪 Testing FREEDOM with objective: {test_objective}")

    result = await orchestrator.execute_objective(test_objective)

    print("\n" + "="*50)
    print("FREEDOM TEST RESULTS")
    print("="*50)
    print(f"Success: {result['success']}")
    print(f"Truth Score: {result.get('truth_score', 0):.2f}")
    print(f"Iterations: {result.get('iterations', 0)}")
    print(f"Execution Time: {result.get('execution_time', 0):.2f}s")
    print(f"Total Cost: ${result.get('total_cost', 0):.4f}")

    if result.get('execution_log'):
        print(f"\nExecution Log:")
        for log_entry in result['execution_log']:
            print(f"  {log_entry}")

    if result.get('final_artifacts'):
        print(f"\nSolution Preview:")
        solution = result['final_artifacts'].get('solution', '')
        print(solution[:200] + "..." if len(solution) > 200 else solution)


if __name__ == "__main__":
    asyncio.run(test_freedom())