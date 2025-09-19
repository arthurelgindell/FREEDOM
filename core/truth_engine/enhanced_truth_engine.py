#!/usr/bin/env python3
"""
from pathlib import Path
FREEDOM Enhanced Truth Engine

Integrates executable specifications with the Truth Engine for automated
code verification with iteration until success.

"Every feature has an executable specification and an automated evaluation.
If tests fail, the system loops until they pass."
"""

import time
import json
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from .truth_engine import TruthEngine, Claim, ClaimType, VerificationStatus, VerificationResult
from .executable_specs import (
    ExecutableSpec, ExecutableSpecRunner, SpecificationGenerator,
    SpecType, SpecExecutionResult
)


class EnhancedTruthEngine(TruthEngine):
    """Truth Engine with executable specification support"""

    def __init__(self, db_path: str = "Path(__file__).parent.parent.parent/core/truth_engine/truth.db"):
        super().__init__(db_path)
        self.spec_runner = ExecutableSpecRunner()
        self.spec_generator = SpecificationGenerator()

    def set_model_client(self, model_client):
        """Set model client for specification generation"""
        self.spec_generator.set_model_client(model_client)

    async def submit_code_claim(
        self,
        source_id: str,
        objective: str,
        implementation_code: str,
        spec_type: SpecType = SpecType.PYTHON_FUNCTION
    ) -> str:
        """Submit a claim about code that can be automatically verified"""

        # Generate executable specification
        spec = await self.spec_generator.generate_spec_from_objective(objective, spec_type)
        spec.implementation_code = implementation_code  # Use actual implementation

        # Submit as computational claim
        claim_id = self.submit_claim(
            source_id=source_id,
            claim_text=f"This code implements: {objective}",
            claim_type=ClaimType.COMPUTATIONAL,
            evidence={
                "objective": objective,
                "implementation_code": implementation_code,
                "executable_spec": self._serialize_spec(spec),
                "verification_method": "executable_specification",
                "spec_type": spec_type.value
            }
        )

        return claim_id

    async def verify_code_claim(self, claim_id: str, verifier_id: str) -> bool:
        """Verify a code claim using executable specifications"""

        claim = self._get_claim(claim_id)
        if not claim:
            self._log_operation(verifier_id, "verification_error", {
                "claim_id": claim_id,
                "error": "Claim not found"
            })
            return False

        spec_data = claim.evidence.get("executable_spec")
        if not spec_data:
            self._log_operation(verifier_id, "verification_error", {
                "claim_id": claim_id,
                "error": "No executable specification found"
            })
            return False

        try:
            # Reconstruct specification
            spec = self._deserialize_spec(spec_data)

            # Execute specification
            result = await self.spec_runner.execute_specification(spec)

            # Determine new status based on test results
            new_status = VerificationStatus.VERIFIED if result.success else VerificationStatus.FAILED

            # Create verification result
            verification_result = VerificationResult(
                claim_id=claim_id,
                method="executable_specification",
                success=result.success,
                evidence={
                    "test_results": result.test_results,
                    "execution_output": result.execution_output,
                    "error_details": result.error_details,
                    "performance_metrics": result.performance_metrics,
                    "spec_id": spec.spec_id,
                    "generated_tests": spec.generated_tests
                },
                timestamp=time.time(),
                verifier_id=verifier_id
            )

            # Store verification (use base truth engine method)
            verification_id = self._generate_verification_id(claim_id, "executable_specification", verifier_id)
            self._store_verification(verification_id, verification_result)

            # Update claim status in database
            self._update_claim_verification_status(claim_id, new_status)

            # Log detailed results
            summary = result.test_results.get("summary", {})
            self._log_operation(verifier_id, "code_claim_verification", {
                "claim_id": claim_id,
                "success": result.success,
                "tests_passed": summary.get("passed", 0),
                "tests_failed": summary.get("failed", 0),
                "tests_total": summary.get("total", 0),
                "execution_time": result.performance_metrics.get("execution_time", 0) if result.performance_metrics else 0,
                "spec_type": spec.spec_type.value
            })

            return result.success

        except Exception as e:
            self._log_operation(verifier_id, "verification_error", {
                "claim_id": claim_id,
                "error": str(e)
            })
            return False

    def generate_truth_loop_report(self, claim_id: str) -> Dict[str, Any]:
        """Generate detailed report for truth loop iteration"""

        claim = self._get_claim(claim_id)
        if not claim:
            return {"error": "Claim not found"}

        # Get all verification attempts
        verifications = self._get_claim_verifications(claim_id)

        # Analyze latest verification for recommendations
        latest_verification = verifications[-1] if verifications else None
        recommendations = []

        if latest_verification and not latest_verification.success:
            error_details = latest_verification.evidence.get("error_details", "")
            test_results = latest_verification.evidence.get("test_results", {})

            if error_details:
                if "syntax" in error_details.lower():
                    recommendations.append("Fix syntax errors in implementation")
                elif "timeout" in error_details.lower():
                    recommendations.append("Optimize code performance or increase timeout")
                elif "import" in error_details.lower():
                    recommendations.append("Check for missing dependencies or imports")
                else:
                    recommendations.append("Review error details and fix implementation issues")

            summary = test_results.get("summary", {})
            if summary.get("failed", 0) > 0:
                recommendations.append("Check test failures - implementation may not match requirements")

            if not recommendations:
                recommendations.append("Review implementation logic against objective requirements")

        return {
            "claim_id": claim_id,
            "objective": claim.evidence.get("objective", ""),
            "current_status": claim.verification_status.value,
            "verification_attempts": len(verifications),
            "latest_verification": {
                "success": latest_verification.success if latest_verification else False,
                "timestamp": latest_verification.timestamp if latest_verification else None,
                "test_summary": latest_verification.evidence.get("test_results", {}).get("summary", {}) if latest_verification else {}
            } if latest_verification else None,
            "should_retry": claim.verification_status == VerificationStatus.FAILED,
            "max_retries_reached": len(verifications) >= 3,
            "recommendations": recommendations,
            "spec_type": claim.evidence.get("spec_type", "unknown")
        }

    def _get_claim_verifications(self, claim_id: str) -> List[VerificationResult]:
        """Get all verification attempts for a claim"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT verification_id, method, success, evidence, timestamp, verifier_id
            FROM verifications
            WHERE claim_id = ?
            ORDER BY timestamp ASC
        """, (claim_id,))

        verifications = []
        for row in cursor.fetchall():
            verification_id, method, success, evidence_json, timestamp, verifier_id = row
            evidence = json.loads(evidence_json)

            verifications.append(VerificationResult(
                claim_id=claim_id,
                method=method,
                success=bool(success),
                evidence=evidence,
                timestamp=timestamp,
                verifier_id=verifier_id
            ))

        conn.close()
        return verifications

    def _generate_verification_id(self, claim_id: str, method: str, verifier_id: str) -> str:
        """Generate unique verification ID"""
        import hashlib
        return hashlib.sha256(
            f"{claim_id}:{method}:{verifier_id}:{time.time()}".encode()
        ).hexdigest()

    def _store_verification(self, verification_id: str, verification_result: VerificationResult):
        """Store verification result in database"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO verifications
            (verification_id, claim_id, method, success, evidence, timestamp, verifier_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            verification_id,
            verification_result.claim_id,
            verification_result.method,
            verification_result.success,
            json.dumps(verification_result.evidence),
            verification_result.timestamp,
            verification_result.verifier_id
        ))
        conn.commit()
        conn.close()

    def _update_claim_verification_status(self, claim_id: str, status: VerificationStatus):
        """Update claim verification status"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE claims
            SET verification_status = ?
            WHERE claim_id = ?
        """, (status.value, claim_id))
        conn.commit()
        conn.close()

    def _serialize_spec(self, spec: ExecutableSpec) -> Dict[str, Any]:
        """Serialize ExecutableSpec for JSON storage"""
        spec_dict = asdict(spec)
        # Convert enums to string values for JSON serialization
        spec_dict['spec_type'] = spec.spec_type.value
        spec_dict['test_framework'] = spec.test_framework.value
        return spec_dict

    def _deserialize_spec(self, spec_data: Dict[str, Any]) -> ExecutableSpec:
        """Deserialize ExecutableSpec from JSON data"""
        # Convert string values back to enums
        spec_data['spec_type'] = SpecType(spec_data['spec_type'])
        from .executable_specs import TestFramework
        spec_data['test_framework'] = TestFramework(spec_data['test_framework'])
        return ExecutableSpec(**spec_data)

    def _get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get claim from database"""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT claim_id, source_id, claim_text, claim_type, evidence,
                   timestamp, verification_status, verification_methods, verification_results
            FROM claims
            WHERE claim_id = ?
        """, (claim_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        claim_id, source_id, claim_text, claim_type, evidence_json, timestamp, \
        verification_status, verification_methods_json, verification_results_json = row

        return Claim(
            claim_id=claim_id,
            source_id=source_id,
            claim_text=claim_text,
            claim_type=ClaimType(claim_type),
            evidence=json.loads(evidence_json),
            timestamp=timestamp,
            verification_status=VerificationStatus(verification_status),
            verification_methods=json.loads(verification_methods_json) if verification_methods_json else [],
            verification_results=json.loads(verification_results_json) if verification_results_json else {}
        )


class TruthLoop:
    """Implements the truth verification loop - iterate until success"""

    def __init__(self, truth_engine: EnhancedTruthEngine):
        self.truth_engine = truth_engine
        self.max_iterations = 3

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

        while iteration < self.max_iterations:
            iteration += 1

            try:
                print(f"🔄 Truth Loop Iteration {iteration}: Verifying code...")

                # Submit claim
                claim_id = await self.truth_engine.submit_code_claim(
                    source_id=f"{source_id}-iteration-{iteration}",
                    objective=objective,
                    implementation_code=implementation_code,
                    spec_type=spec_type
                )

                # Verify claim
                verification_success = await self.truth_engine.verify_code_claim(
                    claim_id,
                    f"TruthLoop-{iteration}"
                )

                # Get detailed report
                report = self.truth_engine.generate_truth_loop_report(claim_id)
                all_attempts.append(report)

                if verification_success:
                    return {
                        "success": True,
                        "claim_id": claim_id,
                        "iterations": iteration,
                        "status": "verified",
                        "message": f"✅ Code verified successfully after {iteration} iteration(s)",
                        "final_report": report,
                        "all_attempts": all_attempts
                    }

                # Log failure and continue if retries available
                print(f"❌ Iteration {iteration} failed:")
                for rec in report.get("recommendations", []):
                    print(f"   💡 {rec}")

                # If max retries reached, return failure
                if iteration >= self.max_iterations:
                    return {
                        "success": False,
                        "claim_id": claim_id,
                        "iterations": iteration,
                        "status": "failed",
                        "message": f"❌ Max iterations ({self.max_iterations}) reached without verification",
                        "final_report": report,
                        "all_attempts": all_attempts
                    }

            except Exception as e:
                error_attempt = {
                    "iteration": iteration,
                    "error": str(e),
                    "timestamp": time.time()
                }
                all_attempts.append(error_attempt)

                return {
                    "success": False,
                    "claim_id": claim_id,
                    "iterations": iteration,
                    "status": "error",
                    "message": f"💥 Truth verification error: {str(e)}",
                    "all_attempts": all_attempts
                }

        return {
            "success": False,
            "iterations": iteration,
            "status": "max_iterations_exceeded",
            "all_attempts": all_attempts
        }

    async def verify_and_improve(
        self,
        objective: str,
        implementation_code: str,
        source_id: str,
        model_client=None,
        spec_type: SpecType = SpecType.PYTHON_FUNCTION
    ) -> Dict[str, Any]:
        """Verify with automatic code improvement based on test failures"""

        current_code = implementation_code
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Run verification
            result = await self.verify_with_iteration(
                objective, current_code, source_id, spec_type
            )

            if result["success"]:
                result["final_code"] = current_code
                result["code_improved"] = current_code != implementation_code
                return result

            # If we have a model client, try to improve the code
            if model_client and iteration < self.max_iterations:
                try:
                    report = result.get("final_report", {})
                    recommendations = report.get("recommendations", [])

                    improvement_prompt = f"""
The following code failed verification for the objective: "{objective}"

Current code:
```python
{current_code}
```

Test failures and recommendations:
{chr(10).join([f"- {rec}" for rec in recommendations])}

Please provide an improved version of the code that addresses these issues.
Respond with only the corrected Python code, no explanations.
"""

                    response = await model_client.generate(improvement_prompt)
                    improved_code = response.get("content", "").strip()

                    # Extract code from response if wrapped in backticks
                    if "```python" in improved_code:
                        start = improved_code.find("```python") + 9
                        end = improved_code.find("```", start)
                        improved_code = improved_code[start:end].strip()
                    elif "```" in improved_code:
                        start = improved_code.find("```") + 3
                        end = improved_code.rfind("```")
                        improved_code = improved_code[start:end].strip()

                    if improved_code and improved_code != current_code:
                        print(f"🔧 Code improvement attempt {iteration}")
                        current_code = improved_code
                        continue

                except Exception as e:
                    print(f"⚠️ Code improvement failed: {e}")

            # No improvement possible, return failure
            result["final_code"] = current_code
            result["code_improved"] = False
            return result

        return {
            "success": False,
            "iterations": self.max_iterations,
            "status": "max_iterations_exceeded",
            "message": "Could not verify code after maximum iterations with improvements",
            "final_code": current_code
        }


# Test function
async def test_truth_loop():
    """Test the truth loop functionality"""

    print("🧪 Testing Truth Loop - Iteration Until Success")
    print("=" * 60)

    # Initialize enhanced truth engine
    truth_engine = EnhancedTruthEngine()
    truth_loop = TruthLoop(truth_engine)

    # Test with working code
    good_code = '''
def add_numbers(a, b):
    """Add two numbers together."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("Both arguments must be numbers")
    return a + b
'''

    print("Testing with GOOD CODE:")
    result1 = await truth_loop.verify_with_iteration(
        objective="Create a function that adds two numbers",
        implementation_code=good_code,
        source_id="test-good-code"
    )

    print(f"Result: {result1['success']}")
    print(f"Message: {result1['message']}")
    print(f"Iterations: {result1['iterations']}")

    # Test with broken code
    bad_code = '''
def add_numbers(a, b):
    return a - b  # Wrong operation!
'''

    print("\\nTesting with BAD CODE:")
    result2 = await truth_loop.verify_with_iteration(
        objective="Create a function that adds two numbers",
        implementation_code=bad_code,
        source_id="test-bad-code"
    )

    print(f"Result: {result2['success']}")
    print(f"Message: {result2['message']}")
    print(f"Iterations: {result2['iterations']}")

    print("\\n" + "=" * 60)
    print("TRUTH LOOP TEST COMPLETE")

    return result1['success'] and not result2['success']  # Good should pass, bad should fail


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_truth_loop())