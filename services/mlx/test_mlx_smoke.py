#!/usr/bin/env python3
"""
MLX Service Smoke Tests
Tests for FREEDOM MLX inference service integration
"""

import asyncio
import httpx
import json
import time
import sys
import os
from typing import Dict, Any

# Test configuration
MLX_SERVICE_URL = os.getenv("MLX_SERVICE_URL", "http://localhost:8001")
API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://localhost:8080")
API_KEY = os.getenv("FREEDOM_API_KEY", "dev-key-change-in-production")

class MLXSmokeTests:
    """Comprehensive smoke tests for MLX service"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300.0)
        self.test_results = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def log_test(self, test_name: str, success: bool, message: str, duration: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "duration": duration
        })
        print(f"{status} {test_name}: {message} ({duration:.2f}s)")

    async def test_mlx_service_health(self) -> bool:
        """Test MLX service health endpoint"""
        start_time = time.time()
        try:
            response = await self.client.get(f"{MLX_SERVICE_URL}/health")
            duration = time.time() - start_time

            if response.status_code == 200:
                health_data = response.json()
                mlx_server_reachable = health_data.get("mlx_server_reachable", False)
                status = health_data.get("status", "unknown")

                if mlx_server_reachable and status == "healthy":
                    self.log_test(
                        "MLX Service Health",
                        True,
                        f"Service healthy, MLX server reachable: {status}",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "MLX Service Health",
                        False,
                        f"Service status: {status}, MLX reachable: {mlx_server_reachable}",
                        duration
                    )
                    return False
            else:
                self.log_test(
                    "MLX Service Health",
                    False,
                    f"Health check failed: {response.status_code}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "MLX Service Health",
                False,
                f"Connection failed: {str(e)}",
                duration
            )
            return False

    async def test_mlx_list_models(self) -> bool:
        """Test MLX model listing"""
        start_time = time.time()
        try:
            response = await self.client.get(f"{MLX_SERVICE_URL}/models")
            duration = time.time() - start_time

            if response.status_code == 200:
                models_data = response.json()
                available_models = models_data.get("available_models", [])
                current_model = models_data.get("current_model", "")

                self.log_test(
                    "MLX List Models",
                    True,
                    f"Found {len(available_models)} models, current: {current_model}",
                    duration
                )
                return True
            else:
                self.log_test(
                    "MLX List Models",
                    False,
                    f"Failed to list models: {response.status_code}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "MLX List Models",
                False,
                f"Request failed: {str(e)}",
                duration
            )
            return False

    async def test_mlx_direct_inference(self) -> bool:
        """Test direct MLX inference"""
        start_time = time.time()
        try:
            inference_request = {
                "prompt": "What is artificial intelligence? Respond in 50 words or less.",
                "max_tokens": 100,
                "temperature": 0.7,
                "stream": False
            }

            response = await self.client.post(
                f"{MLX_SERVICE_URL}/inference",
                json=inference_request
            )
            duration = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "")
                model = result.get("model", "")
                usage = result.get("usage", {})

                if content and len(content.strip()) > 10:
                    self.log_test(
                        "MLX Direct Inference",
                        True,
                        f"Generated {len(content)} chars using {model}",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "MLX Direct Inference",
                        False,
                        "Generated content too short or empty",
                        duration
                    )
                    return False
            else:
                self.log_test(
                    "MLX Direct Inference",
                    False,
                    f"Inference failed: {response.status_code} - {response.text}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "MLX Direct Inference",
                False,
                f"Request failed: {str(e)}",
                duration
            )
            return False

    async def test_api_gateway_health(self) -> bool:
        """Test API Gateway health with MLX service check"""
        start_time = time.time()
        try:
            response = await self.client.get(f"{API_GATEWAY_URL}/health")
            duration = time.time() - start_time

            if response.status_code == 200:
                health_data = response.json()
                mlx_status = health_data.get("mlx_service_status", "unknown")
                mlx_response_time = health_data.get("mlx_service_response_time_ms", 0)

                if mlx_status == "healthy":
                    self.log_test(
                        "API Gateway MLX Health",
                        True,
                        f"MLX service healthy via gateway ({mlx_response_time:.1f}ms)",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "API Gateway MLX Health",
                        False,
                        f"MLX service status: {mlx_status}",
                        duration
                    )
                    return False
            else:
                self.log_test(
                    "API Gateway MLX Health",
                    False,
                    f"Gateway health check failed: {response.status_code}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "API Gateway MLX Health",
                False,
                f"Connection failed: {str(e)}",
                duration
            )
            return False

    async def test_api_gateway_inference(self) -> bool:
        """Test inference through API Gateway"""
        start_time = time.time()
        try:
            inference_request = {
                "prompt": "Explain machine learning briefly.",
                "max_tokens": 75,
                "temperature": 0.5,
                "stream": False
            }

            headers = {
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            }

            response = await self.client.post(
                f"{API_GATEWAY_URL}/inference",
                json=inference_request,
                headers=headers
            )
            duration = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "")
                correlation_id = result.get("correlation_id", "")

                if content and len(content.strip()) > 10:
                    self.log_test(
                        "API Gateway Inference",
                        True,
                        f"Generated response via gateway (ID: {correlation_id[:8]}...)",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "API Gateway Inference",
                        False,
                        "Generated content too short or empty",
                        duration
                    )
                    return False
            else:
                self.log_test(
                    "API Gateway Inference",
                    False,
                    f"Gateway inference failed: {response.status_code} - {response.text}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "API Gateway Inference",
                False,
                f"Request failed: {str(e)}",
                duration
            )
            return False

    async def test_api_gateway_models(self) -> bool:
        """Test model listing through API Gateway"""
        start_time = time.time()
        try:
            headers = {
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            }

            response = await self.client.post(
                f"{API_GATEWAY_URL}/inference/models",
                headers=headers
            )
            duration = time.time() - start_time

            if response.status_code == 200:
                models_data = response.json()
                available_models = models_data.get("available_models", [])

                self.log_test(
                    "API Gateway Models",
                    True,
                    f"Listed {len(available_models)} models via gateway",
                    duration
                )
                return True
            else:
                self.log_test(
                    "API Gateway Models",
                    False,
                    f"Gateway models failed: {response.status_code}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "API Gateway Models",
                False,
                f"Request failed: {str(e)}",
                duration
            )
            return False

    async def test_performance_baseline(self) -> bool:
        """Test inference performance baseline"""
        start_time = time.time()
        try:
            # Test with a small prompt for speed
            inference_request = {
                "prompt": "Hello",
                "max_tokens": 20,
                "temperature": 0.1,
                "stream": False
            }

            headers = {
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            }

            response = await self.client.post(
                f"{API_GATEWAY_URL}/inference",
                json=inference_request,
                headers=headers
            )
            duration = time.time() - start_time

            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                tokens_generated = usage.get("completion_tokens", 0)

                if tokens_generated > 0:
                    tokens_per_second = tokens_generated / duration
                    self.log_test(
                        "Performance Baseline",
                        True,
                        f"Generated {tokens_generated} tokens at {tokens_per_second:.1f} tok/s",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "Performance Baseline",
                        False,
                        "No tokens generated",
                        duration
                    )
                    return False
            else:
                self.log_test(
                    "Performance Baseline",
                    False,
                    f"Performance test failed: {response.status_code}",
                    duration
                )
                return False

        except Exception as e:
            duration = time.time() - start_time
            self.log_test(
                "Performance Baseline",
                False,
                f"Request failed: {str(e)}",
                duration
            )
            return False

    async def run_all_tests(self) -> bool:
        """Run all smoke tests"""
        print("🚀 Starting MLX Service Smoke Tests")
        print("=" * 50)

        total_start = time.time()

        # Core service tests
        test_functions = [
            self.test_mlx_service_health,
            self.test_mlx_list_models,
            self.test_mlx_direct_inference,
            self.test_api_gateway_health,
            self.test_api_gateway_inference,
            self.test_api_gateway_models,
            self.test_performance_baseline
        ]

        results = []
        for test_func in test_functions:
            result = await test_func()
            results.append(result)

        total_duration = time.time() - total_start

        # Summary
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total) * 100

        print("\n" + "=" * 50)
        print(f"📊 Test Summary:")
        print(f"   Passed: {passed}/{total} ({success_rate:.1f}%)")
        print(f"   Total Duration: {total_duration:.2f}s")

        if success_rate >= 100:
            print("🎉 All tests passed! MLX integration ready for production.")
            return True
        elif success_rate >= 80:
            print("⚠️  Most tests passed. Check failed tests before deployment.")
            return False
        else:
            print("❌ Critical failures detected. MLX integration not ready.")
            return False

async def main():
    """Main test runner"""
    try:
        async with MLXSmokeTests() as tests:
            success = await tests.run_all_tests()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Test runner failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))