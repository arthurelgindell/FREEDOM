#!/usr/bin/env python3
"""
End-to-end RAG system test
Tests the complete pipeline from query to retrieval
"""

import requests
import json
import time

def test_health():
    """Test API health endpoint"""
    response = requests.get("http://localhost:5003/health")
    assert response.status_code == 200
    data = response.json()
    print(f"✓ Health Check: {data['status']}")
    print(f"  Database: {data['database']}")
    print(f"  Chunks: {data['chunks_count']}")
    return data['chunks_count'] > 0

def test_stats():
    """Test statistics endpoint"""
    response = requests.get("http://localhost:5003/stats")
    assert response.status_code == 200
    data = response.json()
    print(f"\n✓ Statistics:")
    print(f"  Total chunks: {data['total_chunks']}")

    print(f"\n  Top Technologies:")
    for tech in data['technology_distribution'][:5]:
        print(f"    - {tech['technology']}: {tech['count']} chunks")

    print(f"\n  Component Types:")
    for comp_type in data['type_distribution']:
        print(f"    - {comp_type['type']}: {comp_type['count']} chunks")

    return True

def test_simple_search():
    """Test simple search without RAG"""
    test_queries = [
        ("configuration", None),
        ("docker", None),
        ("redis", None),
    ]

    print(f"\n✓ Simple Search Tests:")
    for query, tech_filter in test_queries:
        params = {"q": query, "limit": 2}
        if tech_filter:
            params["technology"] = tech_filter

        response = requests.get("http://localhost:5003/search", params=params)
        data = response.json()

        print(f"\n  Query: '{query}'" + (f" (technology={tech_filter})" if tech_filter else ""))
        print(f"  Results: {data['total']}")
        print(f"  Time: {data['retrieval_time_ms']}ms")

        if data['results']:
            for result in data['results'][:2]:
                print(f"    • {result['component']} ({result['technology']})")
                print(f"      Score: {result.get('score', 0):.3f}")
                print(f"      Preview: {result['text'][:100]}...")

def test_rag_queries():
    """Test full RAG queries with context assembly"""
    test_cases = [
        {
            "query": "What technologies are available?",
            "top_k": 5,
            "hybrid_alpha": 0.3
        },
        {
            "query": "configuration settings",
            "top_k": 3,
            "hybrid_alpha": 0.0  # Pure sparse search
        },
        {
            "query": "Docker deployment",
            "top_k": 3,
            "hybrid_alpha": 0.5
        }
    ]

    print(f"\n✓ RAG Query Tests:")
    for test_case in test_cases:
        response = requests.post(
            "http://localhost:5003/query",
            json=test_case
        )

        if response.status_code != 200:
            print(f"  Error: {response.status_code} - {response.text}")
            continue

        data = response.json()

        print(f"\n  Query: '{test_case['query']}'")
        print(f"  Settings: top_k={test_case['top_k']}, alpha={test_case['hybrid_alpha']}")
        print(f"  Chunks retrieved: {len(data['chunks'])}")
        print(f"  Time: {data['retrieval_time_ms']}ms")
        print(f"  Cached: {data['cached']}")

        if data['chunks']:
            print(f"  Top results:")
            for i, chunk in enumerate(data['chunks'][:2], 1):
                print(f"    {i}. {chunk['component']} ({chunk.get('technology', 'N/A')})")
                print(f"       Score: {chunk.get('score', 0):.3f}")

        if data['context']:
            print(f"  Context length: {len(data['context'])} chars")
            print(f"  Context preview: {data['context'][:200]}...")

def test_performance():
    """Test query performance and caching"""
    query = {"query": "test caching performance", "top_k": 5}

    print(f"\n✓ Performance Test:")

    # First query (not cached)
    start = time.time()
    response1 = requests.post("http://localhost:5003/query", json=query)
    time1 = (time.time() - start) * 1000
    data1 = response1.json()

    print(f"  First query: {data1['retrieval_time_ms']}ms (total: {time1:.0f}ms)")
    print(f"  Cached: {data1['cached']}")

    # Second query (should be cached)
    start = time.time()
    response2 = requests.post("http://localhost:5003/query", json=query)
    time2 = (time.time() - start) * 1000
    data2 = response2.json()

    print(f"  Second query: {data2['retrieval_time_ms']}ms (total: {time2:.0f}ms)")
    print(f"  Cached: {data2['cached']}")

    if data2['cached']:
        speedup = time1 / time2
        print(f"  Cache speedup: {speedup:.1f}x faster")

def main():
    """Run all tests"""
    print("="*60)
    print("FREEDOM RAG System - End-to-End Test")
    print("="*60)

    try:
        # Check if API is running
        try:
            requests.get("http://localhost:5003/health", timeout=1)
        except requests.exceptions.ConnectionError:
            print("❌ API server not running on port 5003")
            print("   Start with: python3 rag_api.py")
            return

        # Run tests
        if not test_health():
            print("❌ No chunks in database")
            return

        test_stats()
        test_simple_search()
        test_rag_queries()
        test_performance()

        print("\n" + "="*60)
        print("✅ All tests completed successfully!")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()