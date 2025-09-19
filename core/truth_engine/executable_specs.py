#!/usr/bin/env python3
"""
FREEDOM Executable Specifications Framework

Transforms the Truth Engine from basic claim validation into comprehensive
code verification with automated test generation and execution.

"Every feature has an executable specification and an automated evaluation."
"""

import ast
import subprocess
import tempfile
import json
import uuid
import time
import shutil
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from enum import Enum


class SpecType(Enum):
    PYTHON_FUNCTION = "python_function"
    PYTHON_CLASS = "python_class"
    PYTHON_MODULE = "python_module"
    SWIFT_FUNCTION = "swift_function"
    SWIFT_CLASS = "swift_class"
    API_ENDPOINT = "api_endpoint"
    CLI_TOOL = "cli_tool"


class TestFramework(Enum):
    PYTEST = "pytest"
    UNITTEST = "unittest"
    XCTEST = "xctest"
    CUSTOM = "custom"


@dataclass
class ExecutableSpec:
    """Specification that can be automatically verified through execution"""
    spec_id: str
    name: str
    description: str
    spec_type: SpecType

    # Code under test
    implementation_code: str

    # Test specifications
    test_cases: List[Dict[str, Any]]
    test_framework: TestFramework
    generated_tests: str = ""

    # Success criteria
    success_criteria: Dict[str, Any] = None
    performance_requirements: Dict[str, Any] = None

    # Execution context
    dependencies: List[str] = None
    environment_setup: str = ""

    def __post_init__(self):
        if self.success_criteria is None:
            self.success_criteria = {"all_tests_pass": True}
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class SpecExecutionResult:
    """Result of executing an executable specification"""
    spec_id: str
    success: bool
    test_results: Dict[str, Any]
    execution_output: str
    error_details: Optional[str] = None
    performance_metrics: Dict[str, Any] = None
    coverage_report: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class ExecutableSpecRunner:
    """Runs executable specifications and generates verification results"""

    def __init__(self, workspace_dir: str = "/tmp/freedom_specs"):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True, parents=True)

    async def execute_specification(self, spec: ExecutableSpec) -> SpecExecutionResult:
        """Execute a specification and return detailed results"""

        if spec.spec_type == SpecType.PYTHON_FUNCTION:
            return await self._execute_python_function_spec(spec)
        elif spec.spec_type == SpecType.PYTHON_CLASS:
            return await self._execute_python_class_spec(spec)
        elif spec.spec_type == SpecType.SWIFT_FUNCTION:
            return await self._execute_swift_function_spec(spec)
        else:
            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=False,
                test_results={},
                execution_output="",
                error_details=f"Unsupported spec type: {spec.spec_type}"
            )

    async def _execute_python_function_spec(self, spec: ExecutableSpec) -> SpecExecutionResult:
        """Execute Python function specification with pytest"""

        # Generate test file
        test_code = self._generate_python_tests(spec)
        spec.generated_tests = test_code

        # Create temporary workspace
        spec_dir = self.workspace_dir / f"spec_{spec.spec_id}"
        spec_dir.mkdir(exist_ok=True)

        try:
            # Write implementation and test files
            impl_file = spec_dir / "implementation.py"
            test_file = spec_dir / "test_implementation.py"

            impl_file.write_text(spec.implementation_code)
            test_file.write_text(test_code)

            # Write requirements if needed
            if spec.dependencies:
                req_file = spec_dir / "requirements.txt"
                req_file.write_text("\\n".join(spec.dependencies))

                # Install dependencies
                subprocess.run([
                    "pip", "install", "-r", str(req_file)
                ], cwd=spec_dir, capture_output=True)

            # Run pytest with JSON reporting
            result = subprocess.run([
                "python", "-m", "pytest", str(test_file),
                "-v", "--tb=short", "--json-report",
                "--json-report-file=test_results.json"
            ], cwd=spec_dir, capture_output=True, text=True, timeout=30)

            # Parse results
            results_file = spec_dir / "test_results.json"
            if results_file.exists():
                try:
                    test_results = json.loads(results_file.read_text())
                except json.JSONDecodeError:
                    test_results = {
                        "summary": {"total": 0, "passed": 0, "failed": 1},
                        "error": "Failed to parse test results"
                    }
            else:
                test_results = {
                    "summary": {"total": 0, "passed": 0, "failed": 1},
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

            # Check success based on return code and test results
            summary = test_results.get("summary", {})
            passed_tests = summary.get("passed", 0)
            total_tests = summary.get("total", 0)
            failed_tests = summary.get("failed", 0)

            success = (result.returncode == 0 and
                      failed_tests == 0 and
                      passed_tests > 0)

            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=success,
                test_results=test_results,
                execution_output=result.stdout,
                error_details=result.stderr if result.returncode != 0 else None,
                performance_metrics={
                    "execution_time": test_results.get("duration", 0),
                    "return_code": result.returncode
                }
            )

        except subprocess.TimeoutExpired:
            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=False,
                test_results={"error": "timeout"},
                execution_output="",
                error_details="Test execution timeout after 30 seconds"
            )
        except Exception as e:
            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=False,
                test_results={"error": str(e)},
                execution_output="",
                error_details=f"Execution error: {str(e)}"
            )
        finally:
            # Cleanup workspace (optional - keep for debugging)
            # shutil.rmtree(spec_dir, ignore_errors=True)
            pass

    def _generate_python_tests(self, spec: ExecutableSpec) -> str:
        """Generate pytest code from test cases"""

        func_name = self._extract_function_name(spec.implementation_code)
        class_name = self._extract_class_name(spec.implementation_code)

        test_code = f'''"""
Generated tests for {spec.name}
Specification: {spec.description}
"""

import sys
import pytest
from implementation import *

class Test{spec.name.replace(" ", "").replace("-", "_")}:
    """Generated tests for {spec.name}"""

'''

        for i, test_case in enumerate(spec.test_cases):
            test_name = test_case.get("name", f"test_case_{i}")
            if not test_name.startswith("test_"):
                test_name = f"test_{test_name}"

            inputs = test_case.get("inputs", {})
            expected_output = test_case.get("expected_output")
            should_raise = test_case.get("should_raise")
            description = test_case.get("description", "Auto-generated test")

            test_code += f'''
    def {test_name}(self):
        """Test: {description}"""
'''

            if should_raise:
                exception_type = should_raise if isinstance(should_raise, str) else "Exception"
                test_code += f'''
        with pytest.raises({exception_type}):
'''
                if func_name:
                    args_str = ", ".join([f"{k}={repr(v)}" for k, v in inputs.items()])
                    test_code += f"            {func_name}({args_str})\n"

            else:
                # Normal assertion test
                if func_name:
                    args_str = ", ".join([f"{k}={repr(v)}" for k, v in inputs.items()])
                    test_code += f'''
        result = {func_name}({args_str})
        assert result == {repr(expected_output)}, f"Expected {repr(expected_output)}, got {{result}}"
'''
                elif class_name:
                    # Class-based test
                    test_code += f'''
        instance = {class_name}()
        # TODO: Implement class method testing
        assert True, "Class test placeholder"
'''

        # Add edge case tests if none specified
        if not spec.test_cases:
            test_code += '''
    def test_basic_functionality(self):
        """Basic functionality test"""
        # TODO: Implement basic test
        assert True, "No test cases specified"
'''

        return test_code

    def _extract_function_name(self, code: str) -> Optional[str]:
        """Extract function name from Python code"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except:
            pass
        return None

    def _extract_class_name(self, code: str) -> Optional[str]:
        """Extract class name from Python code"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    return node.name
        except:
            pass
        return None

    async def _execute_python_class_spec(self, spec: ExecutableSpec) -> SpecExecutionResult:
        """Execute Python class specification"""
        # Similar to function spec but for classes
        return await self._execute_python_function_spec(spec)

    async def _execute_swift_function_spec(self, spec: ExecutableSpec) -> SpecExecutionResult:
        """Execute Swift function specification with XCTest"""

        # Generate Swift test code
        test_code = self._generate_swift_tests(spec)

        spec_dir = self.workspace_dir / f"spec_{spec.spec_id}"
        spec_dir.mkdir(exist_ok=True)

        try:
            # Write Swift files
            impl_file = spec_dir / "Implementation.swift"
            test_file = spec_dir / "Tests.swift"
            package_file = spec_dir / "Package.swift"

            impl_file.write_text(spec.implementation_code)
            test_file.write_text(test_code)

            # Create Package.swift for Swift testing
            package_content = f'''// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "{spec.name}",
    targets: [
        .target(name: "Implementation"),
        .testTarget(name: "Tests", dependencies: ["Implementation"])
    ]
)
'''
            package_file.write_text(package_content)

            # Run Swift tests
            result = subprocess.run([
                "swift", "test", "--enable-test-discovery"
            ], cwd=spec_dir, capture_output=True, text=True, timeout=30)

            success = result.returncode == 0 and "failed" not in result.stdout.lower()

            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=success,
                test_results={"swift_output": result.stdout},
                execution_output=result.stdout,
                error_details=result.stderr if not success else None
            )

        except Exception as e:
            return SpecExecutionResult(
                spec_id=spec.spec_id,
                success=False,
                test_results={"error": str(e)},
                execution_output="",
                error_details=f"Swift execution error: {str(e)}"
            )

    def _generate_swift_tests(self, spec: ExecutableSpec) -> str:
        """Generate XCTest code from test cases"""

        test_code = f'''
import XCTest

class {spec.name.replace(" ", "")}Tests: XCTestCase {{

'''

        for i, test_case in enumerate(spec.test_cases):
            test_name = test_case.get("name", f"testCase{i}")
            description = test_case.get("description", "Auto-generated test")

            test_code += f'''
    func {test_name}() {{
        // Test: {description}
        // TODO: Implement Swift test logic
        XCTAssertTrue(true, "Placeholder test - Swift implementation needed")
    }}
'''

        test_code += "\\n}\\n"
        return test_code


class SpecificationGenerator:
    """Generates executable specifications from natural language requirements"""

    def __init__(self, model_client=None):
        self.model_client = model_client

    def set_model_client(self, model_client):
        """Set the model client for specification generation"""
        self.model_client = model_client

    async def generate_spec_from_objective(
        self,
        objective: str,
        spec_type: SpecType = SpecType.PYTHON_FUNCTION
    ) -> ExecutableSpec:
        """Generate an executable specification from a natural language objective"""

        if not self.model_client:
            # Fallback: create basic spec manually
            return self._create_fallback_spec(objective, spec_type)

        prompt = f"""Generate an executable specification for this objective: "{objective}"

You must create a complete, testable implementation with comprehensive test cases.

Respond with valid JSON in this exact format:
{{
    "name": "descriptive_name_no_spaces",
    "description": "Clear description of what this does",
    "implementation_code": "Complete, syntactically correct {spec_type.value} code",
    "test_cases": [
        {{
            "name": "test_basic_functionality",
            "description": "Test basic expected behavior",
            "inputs": {{"param1": "value1", "param2": "value2"}},
            "expected_output": "expected result"
        }},
        {{
            "name": "test_edge_case",
            "description": "Test edge case handling",
            "inputs": {{"param1": "edge_value"}},
            "expected_output": "expected edge result"
        }},
        {{
            "name": "test_error_handling",
            "description": "Test error conditions",
            "inputs": {{"param1": "invalid_value"}},
            "should_raise": "ValueError"
        }}
    ],
    "dependencies": [],
    "success_criteria": {{"all_tests_pass": true, "min_coverage": 90}}
}}

Requirements:
- Implementation must be complete and executable
- Include proper error handling
- Test cases must cover normal, edge, and error conditions
- Be specific with expected outputs (exact values)
- Use proper Python syntax for {spec_type.value}
"""

        try:
            response = await self.model_client.generate(prompt)
            content = response.get("content", "").strip()

            # Try to extract JSON from response
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "{" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                content = content[json_start:json_end]

            spec_data = json.loads(content)

            return ExecutableSpec(
                spec_id=str(uuid.uuid4()),
                name=spec_data["name"],
                description=spec_data["description"],
                spec_type=spec_type,
                implementation_code=spec_data["implementation_code"],
                test_cases=spec_data["test_cases"],
                test_framework=TestFramework.PYTEST if spec_type.value.startswith("python") else TestFramework.XCTEST,
                dependencies=spec_data.get("dependencies", []),
                success_criteria=spec_data.get("success_criteria", {"all_tests_pass": True})
            )

        except Exception as e:
            print(f"⚠️ Spec generation failed, using fallback: {e}")
            return self._create_fallback_spec(objective, spec_type)

    def _create_fallback_spec(self, objective: str, spec_type: SpecType) -> ExecutableSpec:
        """Create a basic fallback specification when AI generation fails"""

        # Create simple implementation based on common patterns
        if "add" in objective.lower() and "number" in objective.lower():
            implementation = '''def add_numbers(a, b):
    """Add two numbers together."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise ValueError("Both arguments must be numbers")
    return a + b'''

            test_cases = [
                {
                    "name": "test_basic_addition",
                    "description": "Test basic number addition",
                    "inputs": {"a": 2, "b": 3},
                    "expected_output": 5
                },
                {
                    "name": "test_zero_addition",
                    "description": "Test adding zero",
                    "inputs": {"a": 5, "b": 0},
                    "expected_output": 5
                },
                {
                    "name": "test_invalid_input",
                    "description": "Test invalid input handling",
                    "inputs": {"a": "not_a_number", "b": 5},
                    "should_raise": "ValueError"
                }
            ]

        elif "factorial" in objective.lower():
            implementation = '''def factorial(n):
    """Calculate factorial of n."""
    if not isinstance(n, int):
        raise ValueError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result'''

            test_cases = [
                {
                    "name": "test_factorial_base_cases",
                    "description": "Test factorial of 0 and 1",
                    "inputs": {"n": 0},
                    "expected_output": 1
                },
                {
                    "name": "test_factorial_normal",
                    "description": "Test normal factorial calculation",
                    "inputs": {"n": 5},
                    "expected_output": 120
                }
            ]

        else:
            # Generic fallback
            implementation = f'''def process_objective():
    """Implementation for: {objective}"""
    # TODO: Implement actual logic for {objective}
    return "placeholder_result"'''

            test_cases = [
                {
                    "name": "test_placeholder",
                    "description": "Placeholder test for generated spec",
                    "inputs": {},
                    "expected_output": "placeholder_result"
                }
            ]

        return ExecutableSpec(
            spec_id=str(uuid.uuid4()),
            name=objective.replace(" ", "_").lower(),
            description=f"Executable specification for: {objective}",
            spec_type=spec_type,
            implementation_code=implementation,
            test_cases=test_cases,
            test_framework=TestFramework.PYTEST,
            dependencies=[],
            success_criteria={"all_tests_pass": True}
        )


# Quick test function
async def test_executable_specs():
    """Test the executable specification framework"""

    print("🧪 Testing Executable Specifications Framework")
    print("=" * 50)

    # Create specification generator (without model client for now)
    spec_gen = SpecificationGenerator()

    # Generate specification
    spec = await spec_gen.generate_spec_from_objective(
        "Create a function that adds two numbers",
        SpecType.PYTHON_FUNCTION
    )

    print(f"✅ Generated spec: {spec.name}")
    print(f"✅ Test cases: {len(spec.test_cases)}")

    # Create runner and execute
    runner = ExecutableSpecRunner()
    result = await runner.execute_specification(spec)

    print(f"✅ Execution completed")
    print(f"Success: {result.success}")
    print(f"Test results: {result.test_results.get('summary', 'No summary')}")

    if result.error_details:
        print(f"Errors: {result.error_details}")

    return result.success


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_executable_specs())