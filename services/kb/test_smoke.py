#!/usr/bin/env python3
"""
FREEDOM Knowledge Base Smoke Tests
Bulletproof operator protocol - prove functionality or fail hard
"""

import asyncio
import httpx
import json
import time
import sys
import os
from typing import Dict, Any

# Test configuration
BASE_URL = os.getenv('KB_SERVICE_URL', 'http://localhost:8000')
TIMEOUT = 30.0

# Test data
SAMPLE_SPEC = {
    "technology_name": "kubernetes",
    "version": "1.28",
    "component_type": "api",
    "component_name": "Pod",
    "specification": {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "test-pod",
            "labels": {"app": "test"}
        },
        "spec": {
            "containers": [{
                "name": "test-container",
                "image": "nginx:latest",
                "ports": [{"containerPort": 80}]
            }]
        }
    },
    "source_url": "https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/",
    "confidence_score": 0.95
}

QUERY_TEST = {
    "query": "How to create a Pod in Kubernetes?",
    "limit": 5,
    "similarity_threshold": 0.7
}


class SmokeTestRunner:
    """Bulletproof smoke test runner"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=TIMEOUT)
        self.results = []
        self.failed = False

    async def test_health_check(self) -> bool:
        """Test 1: Health check must return healthy status"""
        try:
            print("🔍 Testing health check endpoint...")
            response = await self.client.get(f"{BASE_URL}/health")

            if response.status_code != 200:
                print(f"❌ FAILED: Health check returned {response.status_code}")
                return False

            data = response.json()
            if data.get('status') != 'healthy':
                print(f"❌ FAILED: Service status is {data.get('status')}")
                return False

            if not data.get('database_connected'):
                print("❌ FAILED: Database not connected")
                return False

            if not data.get('pgvector_available'):
                print("❌ FAILED: pgvector extension not available")
                return False

            print("✅ PASSED: Health check successful")
            print(f"   Database: {data.get('database_connected')}")
            print(f"   pgvector: {data.get('pgvector_available')}")
            print(f"   Specifications: {data.get('total_specifications', 0)}")
            return True

        except Exception as e:
            print(f"❌ FAILED: Health check exception: {e}")
            return False

    async def test_ingest_specification(self) -> Dict[str, Any]:
        """Test 2: Ingest specification must succeed and return ID"""
        try:
            print("📥 Testing specification ingestion...")
            response = await self.client.post(
                f"{BASE_URL}/ingest",
                json=SAMPLE_SPEC
            )

            if response.status_code != 200:
                print(f"❌ FAILED: Ingest returned {response.status_code}")
                print(f"   Response: {response.text}")
                return {}

            data = response.json()
            if not data.get('success'):
                print(f"❌ FAILED: Ingest unsuccessful: {data.get('message')}")
                return {}

            spec_id = data.get('specification_id')
            if not spec_id:
                print("❌ FAILED: No specification ID returned")
                return {}

            processing_time = data.get('processing_time_ms', 0)
            print("✅ PASSED: Specification ingested successfully")
            print(f"   Specification ID: {spec_id}")
            print(f"   Processing time: {processing_time:.2f}ms")

            return {"spec_id": spec_id, "processing_time": processing_time}

        except Exception as e:
            print(f"❌ FAILED: Ingest exception: {e}")
            return {}

    async def test_query_knowledge_base(self) -> bool:
        """Test 3: Query must return relevant results"""
        try:
            print("🔍 Testing knowledge base query...")
            response = await self.client.post(
                f"{BASE_URL}/query",
                json=QUERY_TEST
            )

            if response.status_code != 200:
                print(f"❌ FAILED: Query returned {response.status_code}")
                print(f"   Response: {response.text}")
                return False

            data = response.json()
            results = data.get('results', [])
            processing_time = data.get('processing_time_ms', 0)

            # Must return at least one result for Kubernetes query
            if len(results) == 0:
                print("❌ FAILED: Query returned no results")
                return False

            # Check result structure
            first_result = results[0]
            required_fields = ['id', 'technology_name', 'similarity_score']
            for field in required_fields:
                if field not in first_result:
                    print(f"❌ FAILED: Missing field '{field}' in result")
                    return False

            # Performance requirement: <800ms p99 at 10 RPS
            if processing_time > 800:
                print(f"⚠️  WARNING: Query took {processing_time:.2f}ms (target: <800ms)")

            print("✅ PASSED: Query returned valid results")
            print(f"   Results count: {len(results)}")
            print(f"   Processing time: {processing_time:.2f}ms")
            print(f"   Top result similarity: {first_result.get('similarity_score', 0):.3f}")
            return True

        except Exception as e:
            print(f"❌ FAILED: Query exception: {e}")
            return False

    async def test_performance_baseline(self) -> bool:
        """Test 4: Performance baseline - simulate load"""
        try:
            print("⚡ Testing performance baseline...")

            # Perform 10 concurrent queries
            query_tasks = []
            for i in range(10):
                task = self.client.post(f"{BASE_URL}/query", json=QUERY_TEST)
                query_tasks.append(task)

            start_time = time.time()
            responses = await asyncio.gather(*query_tasks, return_exceptions=True)
            total_time = time.time() - start_time

            # Analyze results
            successful_queries = 0
            total_processing_time = 0

            for response in responses:
                if isinstance(response, Exception):
                    continue

                if response.status_code == 200:
                    successful_queries += 1
                    data = response.json()
                    total_processing_time += data.get('processing_time_ms', 0)

            if successful_queries < 8:  # Allow 20% failure rate
                print(f"❌ FAILED: Only {successful_queries}/10 queries succeeded")
                return False

            avg_processing_time = total_processing_time / successful_queries if successful_queries > 0 else 0
            qps = successful_queries / total_time

            print("✅ PASSED: Performance baseline acceptable")
            print(f"   Successful queries: {successful_queries}/10")
            print(f"   Average processing time: {avg_processing_time:.2f}ms")
            print(f"   Queries per second: {qps:.1f}")
            print(f"   Total test time: {total_time:.2f}s")

            return True

        except Exception as e:
            print(f"❌ FAILED: Performance test exception: {e}")
            return False

    async def test_stats_endpoint(self) -> bool:
        """Test 5: Stats endpoint must return service statistics"""
        try:
            print("📊 Testing stats endpoint...")
            response = await self.client.get(f"{BASE_URL}/stats")

            if response.status_code != 200:
                print(f"❌ FAILED: Stats returned {response.status_code}")
                return False

            data = response.json()
            required_fields = ['service_uptime_seconds', 'database_stats']
            for field in required_fields:
                if field not in data:
                    print(f"❌ FAILED: Missing field '{field}' in stats")
                    return False

            uptime = data.get('service_uptime_seconds', 0)
            db_stats = data.get('database_stats', {})

            print("✅ PASSED: Stats endpoint working")
            print(f"   Service uptime: {uptime:.1f}s")
            print(f"   Total specifications: {db_stats.get('total_specifications', 0)}")
            print(f"   Unique technologies: {db_stats.get('unique_technologies', 0)}")
            return True

        except Exception as e:
            print(f"❌ FAILED: Stats test exception: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all smoke tests in sequence"""
        print("🚀 FREEDOM Knowledge Base Service - Smoke Tests")
        print("=" * 60)

        tests = [
            ("Health Check", self.test_health_check),
            ("Specification Ingestion", self.test_ingest_specification),
            ("Knowledge Base Query", self.test_query_knowledge_base),
            ("Performance Baseline", self.test_performance_baseline),
            ("Stats Endpoint", self.test_stats_endpoint)
        ]

        all_passed = True
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 40)

            try:
                result = await test_func()
                if isinstance(result, dict):
                    # For tests that return data, consider them passed if dict is not empty
                    passed = bool(result)
                else:
                    passed = result

                if not passed:
                    all_passed = False
                    print(f"💥 {test_name} FAILED")
                else:
                    print(f"🎯 {test_name} PASSED")

            except Exception as e:
                all_passed = False
                print(f"💥 {test_name} FAILED with exception: {e}")

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 ALL SMOKE TESTS PASSED - Service is functional")
            return True
        else:
            print("🔥 SMOKE TESTS FAILED - Service is not operational")
            return False

    async def cleanup(self):
        """Cleanup resources"""
        await self.client.aclose()


async def main():
    """Main test runner following bulletproof operator protocol"""
    runner = SmokeTestRunner()

    try:
        success = await runner.run_all_tests()
        await runner.cleanup()

        if success:
            print("\n✅ VERIFICATION COMPLETE: Knowledge Base service is operational")
            sys.exit(0)
        else:
            print("\n❌ VERIFICATION FAILED: Knowledge Base service is not working")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        await runner.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner failed: {e}")
        await runner.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())