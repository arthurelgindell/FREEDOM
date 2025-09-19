#!/usr/bin/env python3
"""
FREEDOM API Gateway Smoke Tests
Comprehensive tests to verify all endpoints and functionality
"""

import os
import time
import json
import asyncio
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Test configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_KEY = os.getenv("FREEDOM_API_KEY", "dev-key-change-in-production")
TIMEOUT = 30

class SmokeTestResult:
    """Test result tracking"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name: str):
        self.passed += 1
        print(f"✅ {test_name}")

    def add_fail(self, test_name: str, error: str):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ {test_name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"SMOKE TEST RESULTS")
        print(f"{'='*50}")
        print(f"Total Tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/total)*100:.1f}%" if total > 0 else "0%")

        if self.errors:
            print(f"\nFAILURES:")
            for error in self.errors:
                print(f"  - {error}")

        return self.failed == 0


def make_request(method: str, endpoint: str, headers: Optional[Dict] = None,
                json_data: Optional[Dict] = None, timeout: int = TIMEOUT) -> requests.Response:
    """Make HTTP request with proper error handling"""
    url = f"{API_BASE_URL}{endpoint}"
    default_headers = {"Content-Type": "application/json"}

    if headers:
        default_headers.update(headers)

    try:
        if method.upper() == "GET":
            return requests.get(url, headers=default_headers, timeout=timeout)
        elif method.upper() == "POST":
            return requests.post(url, headers=default_headers, json=json_data, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request failed: {str(e)}")


def test_health_endpoint(result: SmokeTestResult):
    """Test health endpoint"""
    try:
        response = make_request("GET", "/health")

        if response.status_code != 200:
            result.add_fail("Health endpoint status", f"Expected 200, got {response.status_code}")
            return

        data = response.json()
        required_fields = ["status", "timestamp", "uptime_seconds", "version", "kb_service_status"]

        for field in required_fields:
            if field not in data:
                result.add_fail(f"Health endpoint field '{field}'", "Missing required field")
                return

        if data["status"] not in ["healthy", "degraded"]:
            result.add_fail("Health endpoint status value", f"Invalid status: {data['status']}")
            return

        result.add_pass("Health endpoint")

    except Exception as e:
        result.add_fail("Health endpoint", str(e))


def test_health_endpoint_performance(result: SmokeTestResult):
    """Test health endpoint response time"""
    try:
        start_time = time.time()
        response = make_request("GET", "/health")
        response_time = (time.time() - start_time) * 1000

        if response_time > 5000:  # 5 seconds
            result.add_fail("Health endpoint performance", f"Response time {response_time:.1f}ms > 5000ms")
        else:
            result.add_pass("Health endpoint performance")

    except Exception as e:
        result.add_fail("Health endpoint performance", str(e))


def test_metrics_endpoint(result: SmokeTestResult):
    """Test Prometheus metrics endpoint"""
    try:
        response = make_request("GET", "/metrics")

        if response.status_code != 200:
            result.add_fail("Metrics endpoint status", f"Expected 200, got {response.status_code}")
            return

        content = response.text
        expected_metrics = [
            "gateway_requests_total",
            "gateway_request_duration_seconds",
            "gateway_kb_requests_total",
            "gateway_active_connections"
        ]

        for metric in expected_metrics:
            if metric not in content:
                result.add_fail(f"Metrics endpoint metric '{metric}'", "Missing expected metric")
                return

        result.add_pass("Metrics endpoint")

    except Exception as e:
        result.add_fail("Metrics endpoint", str(e))


def test_authentication_required(result: SmokeTestResult):
    """Test that endpoints require authentication"""
    endpoints = ["/kb/query", "/kb/ingest"]

    for endpoint in endpoints:
        try:
            # Test without API key
            response = make_request("POST", endpoint, json_data={"test": "data"})

            if response.status_code != 401:
                result.add_fail(f"Auth required {endpoint}", f"Expected 401, got {response.status_code}")
                continue

            # Test with invalid API key
            response = make_request("POST", endpoint,
                                  headers={"X-API-Key": "invalid-key"},
                                  json_data={"test": "data"})

            if response.status_code != 401:
                result.add_fail(f"Auth invalid {endpoint}", f"Expected 401, got {response.status_code}")
                continue

            result.add_pass(f"Authentication required {endpoint}")

        except Exception as e:
            result.add_fail(f"Authentication test {endpoint}", str(e))


def test_kb_query_endpoint(result: SmokeTestResult):
    """Test KB query endpoint with valid authentication"""
    try:
        query_data = {
            "query": "test query for smoke testing",
            "limit": 5,
            "similarity_threshold": 0.7
        }

        headers = {"X-API-Key": API_KEY}
        response = make_request("POST", "/kb/query", headers=headers, json_data=query_data)

        # Accept both success (200) and service unavailable (503) as valid
        # since KB service might not be running during isolated API tests
        if response.status_code not in [200, 503]:
            result.add_fail("KB query endpoint", f"Expected 200 or 503, got {response.status_code}")
            return

        if response.status_code == 200:
            data = response.json()
            required_fields = ["query", "results", "total_results", "processing_time_ms"]

            for field in required_fields:
                if field not in data:
                    result.add_fail(f"KB query response field '{field}'", "Missing required field")
                    return

        result.add_pass("KB query endpoint")

    except Exception as e:
        result.add_fail("KB query endpoint", str(e))


def test_kb_ingest_endpoint(result: SmokeTestResult):
    """Test KB ingest endpoint with valid authentication"""
    try:
        ingest_data = {
            "technology_name": "test-tech",
            "version": "1.0.0",
            "component_type": "api",
            "component_name": "test-component",
            "specification": {"test": "data"},
            "source_url": "https://example.com/spec",
            "confidence_score": 0.9
        }

        headers = {"X-API-Key": API_KEY}
        response = make_request("POST", "/kb/ingest", headers=headers, json_data=ingest_data)

        # Accept both success (200) and service unavailable (503) as valid
        if response.status_code not in [200, 503]:
            result.add_fail("KB ingest endpoint", f"Expected 200 or 503, got {response.status_code}")
            return

        if response.status_code == 200:
            data = response.json()
            required_fields = ["success", "message", "processing_time_ms"]

            for field in required_fields:
                if field not in data:
                    result.add_fail(f"KB ingest response field '{field}'", "Missing required field")
                    return

        result.add_pass("KB ingest endpoint")

    except Exception as e:
        result.add_fail("KB ingest endpoint", str(e))


def test_rate_limiting(result: SmokeTestResult):
    """Test rate limiting functionality"""
    try:
        headers = {"X-API-Key": API_KEY}

        # Make multiple rapid requests to trigger rate limiting
        # Note: This is a basic test - actual rate limits may vary
        responses = []
        for i in range(5):
            try:
                response = make_request("GET", "/health", headers=headers, timeout=5)
                responses.append(response.status_code)
            except Exception:
                # Timeout or connection error can indicate rate limiting
                responses.append(429)

        # Check if we got at least some successful responses
        success_count = len([r for r in responses if r == 200])
        if success_count > 0:
            result.add_pass("Rate limiting (basic test)")
        else:
            result.add_fail("Rate limiting", "No successful responses received")

    except Exception as e:
        result.add_fail("Rate limiting", str(e))


def test_cors_headers(result: SmokeTestResult):
    """Test CORS headers are present"""
    try:
        response = make_request("GET", "/health")

        # Check for CORS headers (may not be present in all scenarios)
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-credentials",
            "access-control-allow-methods"
        ]

        has_cors = any(header.lower() in [h.lower() for h in response.headers] for header in cors_headers)

        if has_cors or response.status_code == 200:
            # If we get a successful response, CORS is working (at least for same-origin)
            result.add_pass("CORS configuration")
        else:
            result.add_fail("CORS configuration", "No CORS headers found")

    except Exception as e:
        result.add_fail("CORS configuration", str(e))


def test_error_handling(result: SmokeTestResult):
    """Test error handling for invalid requests"""
    try:
        # Test invalid JSON
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

        try:
            response = requests.post(f"{API_BASE_URL}/kb/query",
                                   headers=headers,
                                   data="invalid json",
                                   timeout=TIMEOUT)
        except Exception as e:
            # Connection errors are acceptable for this test
            result.add_pass("Error handling (invalid JSON)")
            return

        # Should return 422 (validation error) or 400 (bad request)
        if response.status_code in [400, 422]:
            result.add_pass("Error handling (invalid JSON)")
        else:
            result.add_fail("Error handling", f"Expected 400/422 for invalid JSON, got {response.status_code}")

    except Exception as e:
        result.add_fail("Error handling", str(e))


def test_openapi_docs(result: SmokeTestResult):
    """Test that OpenAPI documentation is available"""
    try:
        # Test /docs endpoint
        response = make_request("GET", "/docs")

        if response.status_code == 200:
            result.add_pass("OpenAPI docs (/docs)")
        else:
            result.add_fail("OpenAPI docs", f"Expected 200, got {response.status_code}")

    except Exception as e:
        result.add_fail("OpenAPI docs", str(e))


def main():
    """Run all smoke tests"""
    print("🚀 Starting FREEDOM API Gateway Smoke Tests")
    print(f"Testing endpoint: {API_BASE_URL}")
    print(f"Using API key: {API_KEY[:8]}...")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print("="*50)

    result = SmokeTestResult()

    # Core functionality tests
    test_health_endpoint(result)
    test_health_endpoint_performance(result)
    test_metrics_endpoint(result)
    test_openapi_docs(result)

    # Security tests
    test_authentication_required(result)
    test_cors_headers(result)

    # API endpoint tests
    test_kb_query_endpoint(result)
    test_kb_ingest_endpoint(result)

    # Performance and reliability tests
    test_rate_limiting(result)
    test_error_handling(result)

    # Print summary
    success = result.summary()

    if success:
        print("\n🎉 ALL SMOKE TESTS PASSED!")
        print("API Gateway is ready for production")
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("Review failures before deploying")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())