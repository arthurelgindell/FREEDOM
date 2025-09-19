#!/usr/bin/env python3
"""
FREEDOM Truth Loop Integration

Implements the truth verification loop in FREEDOM orchestration that ensures
"Every feature has an executable specification and an automated evaluation.
If tests fail, the system loops until they pass."
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.truth_engine.enhanced_truth_engine import EnhancedTruthEngine
from core.truth_engine.executable_specs import SpecType


class TruthLoop:
    """Implements the truth verification loop in FREEDOM orchestration"""

    def __init__(self, truth_engine: Optional[EnhancedTruthEngine] = None):
        self.truth_engine = truth_engine or EnhancedTruthEngine()
        self.max_iterations = 3
        self.iteration_delay = 1.0  # seconds between iterations

    async def verify_with_iteration(
        self,
        objective: str,
        implementation_code: str,
        source_id: str,
        spec_type: SpecType = SpecType.PYTHON_FUNCTION
    ) -> Dict[str, Any]:
        """Run truth verification with iteration until success or max attempts"""

        iteration = 0
        claim_id = None
        all_attempts = []

        print(f"🔍 Starting truth verification loop for: {objective}")

        while iteration < self.max_iterations:
            iteration += 1
            attempt_start = time.time()

            print(f"💭 Truth verification attempt {iteration}/{self.max_iterations}")

            try:
                # Submit claim with current implementation
                claim_id = await self.truth_engine.submit_code_claim(
                    source_id=f"{source_id}-iteration-{iteration}",
                    objective=objective,
                    implementation_code=implementation_code,
                    spec_type=spec_type
                )

                print(f"📝 Claim submitted: {claim_id[:8]}...")

                # Verify claim
                verification_success = await self.truth_engine.verify_code_claim(
                    claim_id,
                    f"TruthLoop-{iteration}"
                )

                attempt_duration = time.time() - attempt_start
                attempt_result = {
                    "iteration": iteration,
                    "claim_id": claim_id,
                    "success": verification_success,
                    "duration": attempt_duration,
                    "timestamp": time.time()
                }
                all_attempts.append(attempt_result)

                if verification_success:
                    print(f"✅ Truth verification SUCCEEDED on iteration {iteration}")
                    return {
                        "success": True,
                        "claim_id": claim_id,
                        "iterations": iteration,
                        "total_attempts": len(all_attempts),
                        "status": "verified",
                        "message": f"Code verified successfully after {iteration} iteration(s)",
                        "attempts": all_attempts,
                        "final_result": "TRUTH_VERIFIED"
                    }

                # Get failure report for analysis
                report = self.truth_engine.generate_truth_loop_report(claim_id)
                attempt_result["failure_report"] = report

                print(f"❌ Truth verification failed on iteration {iteration}")
                if report.get("recommendations"):
                    print(f"💡 Recommendations: {', '.join(report['recommendations'])}")

                # If max retries reached, return failure
                if iteration >= self.max_iterations:
                    print(f"🛑 Max iterations ({self.max_iterations}) reached without verification")
                    return {
                        "success": False,
                        "claim_id": claim_id,
                        "iterations": iteration,
                        "total_attempts": len(all_attempts),
                        "status": "max_iterations_exceeded",
                        "message": f"Max iterations ({self.max_iterations}) reached without verification",
                        "attempts": all_attempts,
                        "final_report": report,
                        "final_result": "TRUTH_FAILED"
                    }

                # Wait before next iteration
                if iteration < self.max_iterations:
                    print(f"⏳ Waiting {self.iteration_delay}s before retry...")
                    await asyncio.sleep(self.iteration_delay)

            except Exception as e:
                attempt_duration = time.time() - attempt_start
                error_result = {
                    "iteration": iteration,
                    "claim_id": claim_id,
                    "success": False,
                    "duration": attempt_duration,
                    "timestamp": time.time(),
                    "error": str(e)
                }
                all_attempts.append(error_result)

                print(f"💥 Truth verification ERROR on iteration {iteration}: {str(e)}")

                return {
                    "success": False,
                    "claim_id": claim_id,
                    "iterations": iteration,
                    "total_attempts": len(all_attempts),
                    "status": "error",
                    "message": f"Truth verification error: {str(e)}",
                    "attempts": all_attempts,
                    "final_result": "TRUTH_ERROR"
                }

        return {
            "success": False,
            "iterations": iteration,
            "total_attempts": len(all_attempts),
            "status": "max_iterations_exceeded",
            "message": f"Exhausted all {self.max_iterations} iterations without success",
            "attempts": all_attempts,
            "final_result": "TRUTH_EXHAUSTED"
        }

    def generate_iteration_summary(self, result: Dict[str, Any]) -> str:
        """Generate a human-readable summary of the truth loop execution"""

        summary = []
        summary.append(f"🎯 TRUTH VERIFICATION SUMMARY")
        summary.append(f"=" * 40)
        summary.append(f"Final Result: {result['final_result']}")
        summary.append(f"Success: {result['success']}")
        summary.append(f"Total Iterations: {result['iterations']}")
        summary.append(f"Total Attempts: {result['total_attempts']}")
        summary.append(f"Status: {result['status']}")
        summary.append("")

        if result.get('attempts'):
            summary.append("📊 Attempt Details:")
            for attempt in result['attempts']:
                status = "✅ PASS" if attempt['success'] else "❌ FAIL"
                summary.append(f"  Iteration {attempt['iteration']}: {status} ({attempt['duration']:.2f}s)")
                if attempt.get('error'):
                    summary.append(f"    Error: {attempt['error']}")

        summary.append("")
        summary.append(f"💬 Message: {result['message']}")

        return "\n".join(summary)


class MockModelClient:
    """Mock model client for testing purposes"""

    async def generate(self, prompt: str) -> Dict[str, Any]:
        """Generate a mock response for specification generation"""

        import json

        # Extract function type from prompt
        if "fibonacci" in prompt.lower():
            spec_data = {
                "name": "fibonacci_calculator",
                "description": "Calculates fibonacci numbers recursively",
                "implementation_code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "test_cases": [
                    {
                        "name": "test_fibonacci_base_cases",
                        "description": "Test fibonacci base cases",
                        "inputs": {"n": 0},
                        "expected_output": 0
                    },
                    {
                        "name": "test_fibonacci_one",
                        "description": "Test fibonacci of 1",
                        "inputs": {"n": 1},
                        "expected_output": 1
                    },
                    {
                        "name": "test_fibonacci_five",
                        "description": "Test fibonacci of 5",
                        "inputs": {"n": 5},
                        "expected_output": 5
                    }
                ],
                "dependencies": [],
                "success_criteria": {"all_tests_pass": True}
            }
        elif "square" in prompt.lower():
            spec_data = {
                "name": "square_calculator",
                "description": "Calculates the square of a number",
                "implementation_code": "def square_number(x):\n    return x * x",
                "test_cases": [
                    {
                        "name": "test_square_positive",
                        "description": "Test squaring positive numbers",
                        "inputs": {"x": 5},
                        "expected_output": 25
                    },
                    {
                        "name": "test_square_zero",
                        "description": "Test squaring zero",
                        "inputs": {"x": 0},
                        "expected_output": 0
                    },
                    {
                        "name": "test_square_negative",
                        "description": "Test squaring negative numbers",
                        "inputs": {"x": -3},
                        "expected_output": 9
                    }
                ],
                "dependencies": [],
                "success_criteria": {"all_tests_pass": True}
            }
        else:
            spec_data = {
                "name": "generic_function",
                "description": "A generic test function",
                "implementation_code": "def generic_function(x):\n    return x * 2",
                "test_cases": [
                    {
                        "name": "test_basic_functionality",
                        "description": "Test basic functionality",
                        "inputs": {"x": 5},
                        "expected_output": 10
                    }
                ],
                "dependencies": [],
                "success_criteria": {"all_tests_pass": True}
            }

        return {"content": json.dumps(spec_data)}


# Integration functions for FREEDOM orchestration
async def truth_checker_with_loop(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced truth checker with iteration loop for LangGraph integration"""

    truth_loop = TruthLoop()

    # Set up mock model client for testing
    mock_client = MockModelClient()
    truth_loop.truth_engine.set_model_client(mock_client)

    objective = state.get("objective", "Unknown objective")
    implementation_code = state.get("generated_code", "")
    source_id = state.get("selected_model", "unknown")

    result = await truth_loop.verify_with_iteration(
        objective=objective,
        implementation_code=implementation_code,
        source_id=source_id
    )

    # Update state with truth verification results
    state["truth_status"] = result["success"]
    state["iteration_count"] = result["iterations"]
    state["truth_verification_result"] = result
    state["truth_summary"] = truth_loop.generate_iteration_summary(result)

    if not result["success"]:
        if "truth_errors" not in state:
            state["truth_errors"] = []
        state["truth_errors"].append(result.get("message", "Verification failed"))

    return state


async def test_truth_loop():
    """Standalone test function for the truth loop"""

    print("🚀 TESTING TRUTH LOOP FUNCTIONALITY")
    print("=" * 50)

    # Initialize truth loop
    truth_loop = TruthLoop()

    # Set up mock model client
    mock_client = MockModelClient()
    truth_loop.truth_engine.set_model_client(mock_client)

    # Test 1: Working code that should pass
    print("\n📝 Test 1: Code that should PASS verification")
    working_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

    result1 = await truth_loop.verify_with_iteration(
        objective="Create a function that calculates fibonacci numbers",
        implementation_code=working_code,
        source_id="test-working-code"
    )

    print(truth_loop.generate_iteration_summary(result1))

    # Test 2: Broken code that should fail
    print("\n📝 Test 2: Code that should FAIL verification")
    broken_code = """
def fibonacci(n):
    return "this is broken"
"""

    result2 = await truth_loop.verify_with_iteration(
        objective="Create a function that calculates fibonacci numbers",
        implementation_code=broken_code,
        source_id="test-broken-code"
    )

    print(truth_loop.generate_iteration_summary(result2))

    return result1["success"] and not result2["success"]


if __name__ == "__main__":
    # Run standalone test
    success = asyncio.run(test_truth_loop())
    print(f"\n🎯 TRUTH LOOP TEST: {'PASSED' if success else 'FAILED'}")