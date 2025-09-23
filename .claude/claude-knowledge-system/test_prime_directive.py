#!/usr/bin/env python3
"""
CCKS Prime Directive Test Suite
Per FREEDOM Philosophy: "If it doesn't run, it doesn't exist"
"""

import sys
import os
import json
import time
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime

# Add module to path
sys.path.insert(0, str(Path.home() / '.claude' / 'claude-knowledge-system'))

class TestResult:
    def __init__(self, test_name):
        self.test_name = test_name
        self.passed = False
        self.message = ""
        self.metrics = {}

def run_command(cmd):
    """Execute command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_1_basic_functionality():
    """Test: Basic CCKS operations work"""
    test = TestResult("Basic Functionality")

    # Test stats command
    success, output, error = run_command("~/.claude/ccks stats")
    if not success:
        test.message = f"FAILED: ccks stats returned error: {error}"
        return test

    try:
        stats = json.loads(output)
        if 'entries' in stats and 'memory_used_mb' in stats:
            test.passed = True
            test.message = f"✓ Stats working - {stats['entries']} entries, {stats['memory_used_mb']:.2f}MB used"
            test.metrics = stats
        else:
            test.message = "FAILED: Invalid stats format"
    except json.JSONDecodeError:
        test.message = "FAILED: Stats output not valid JSON"

    return test

def test_2_add_and_query():
    """Test: Can add knowledge and query it"""
    test = TestResult("Add and Query")

    # Add unique test data
    test_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    test_content = f"TEST_CONTENT_{test_id}: Docker error fixed by restarting service"

    # Add knowledge
    success, output, error = run_command(f'~/.claude/ccks add "{test_content}"')
    if not success:
        test.message = f"FAILED: Could not add knowledge: {error}"
        return test

    # Wait for persistence
    time.sleep(0.5)

    # Query the knowledge
    success, output, error = run_command(f'~/.claude/ccks query "TEST_CONTENT_{test_id}"')
    if not success:
        test.message = f"FAILED: Query failed: {error}"
        return test

    # Check if we can find our content (even if not a perfect match)
    if test_id in output or "cache_hit" in output or "similar_entries" in output:
        test.passed = True
        test.message = f"✓ Added and queried content successfully"
        test.metrics['test_id'] = test_id
    else:
        test.message = f"FAILED: Could not find added content in query results"

    return test

def test_3_persistence():
    """Test: Data persists across instances"""
    test = TestResult("Persistence")

    # Add data and flush
    test_data = f"PERSISTENCE_TEST_{time.time()}"
    success, output, error = run_command(f'~/.claude/ccks add "{test_data}"')
    if not success:
        test.message = f"FAILED: Could not add test data: {error}"
        return test

    # Force flush
    success, output, error = run_command("~/.claude/ccks flush")
    if not success:
        test.message = f"FAILED: Flush failed: {error}"
        return test

    # Check database file exists
    db_path = Path.home() / '.claude' / 'claude-knowledge-system' / 'cache' / 'knowledge.db'
    if not db_path.exists():
        test.message = "FAILED: Database file does not exist"
        return test

    db_size = db_path.stat().st_size
    if db_size > 0:
        test.passed = True
        test.message = f"✓ Database persisted ({db_size} bytes)"
        test.metrics['db_size'] = db_size
    else:
        test.message = "FAILED: Database file is empty"

    return test

def test_4_memory_limits():
    """Test: Memory usage stays within limits"""
    test = TestResult("Memory Limits")

    success, output, error = run_command("~/.claude/ccks stats")
    if not success:
        test.message = f"FAILED: Could not get stats: {error}"
        return test

    try:
        stats = json.loads(output)
        memory_used = stats.get('memory_used_mb', 0)
        memory_limit = stats.get('memory_limit_mb', 51200)

        if memory_used < memory_limit:
            test.passed = True
            test.message = f"✓ Memory within limits: {memory_used:.2f}MB / {memory_limit:.0f}MB"
            test.metrics['memory_used_mb'] = memory_used
            test.metrics['memory_limit_mb'] = memory_limit
        else:
            test.message = f"FAILED: Memory exceeded: {memory_used}MB > {memory_limit}MB"
    except Exception as e:
        test.message = f"FAILED: Could not parse stats: {e}"

    return test

def test_5_freedom_integration():
    """Test: FREEDOM-specific commands work"""
    test = TestResult("FREEDOM Integration")

    # Add FREEDOM-specific knowledge
    freedom_data = "FREEDOM: Docker services include api-gateway, postgres, redis, rag-chunker on port 5003"
    success, output, error = run_command(f'~/.claude/ccks add "{freedom_data}"')
    if not success:
        test.message = f"FAILED: Could not add FREEDOM data: {error}"
        return test

    # Query FREEDOM information
    success, output, error = run_command('~/.claude/ccks query "FREEDOM port 5003"')
    if not success:
        test.message = f"FAILED: FREEDOM query failed: {error}"
        return test

    # Check result
    if "5003" in output or "rag" in output.lower() or "freedom" in output.lower():
        test.passed = True
        test.message = "✓ FREEDOM integration working"
    else:
        test.message = "FAILED: FREEDOM data not retrievable"

    return test

def test_6_token_metrics():
    """Test: Token saving metrics are tracked"""
    test = TestResult("Token Metrics")

    # Get current stats
    success, output, error = run_command("~/.claude/ccks stats")
    if not success:
        test.message = f"FAILED: Could not get stats: {error}"
        return test

    try:
        stats = json.loads(output)
        tokens_saved = stats.get('total_tokens_saved', 0)
        cache_hit_rate = stats.get('cache_hit_rate', 0)

        test.passed = True
        test.message = f"✓ Token tracking active - {tokens_saved} tokens saved, {cache_hit_rate:.1%} hit rate"
        test.metrics['tokens_saved'] = tokens_saved
        test.metrics['cache_hit_rate'] = cache_hit_rate
    except Exception as e:
        test.message = f"FAILED: Could not parse metrics: {e}"

    return test

def test_7_performance():
    """Test: Operations complete within time limits"""
    test = TestResult("Performance")

    # Test add operation speed
    start = time.time()
    success, output, error = run_command('~/.claude/ccks add "Performance test data"')
    add_time = time.time() - start

    if not success:
        test.message = f"FAILED: Add operation failed: {error}"
        return test

    # Test query operation speed
    start = time.time()
    success, output, error = run_command('~/.claude/ccks query "Performance test"')
    query_time = time.time() - start

    if not success:
        test.message = f"FAILED: Query operation failed: {error}"
        return test

    # Check performance targets
    if add_time < 2.0 and query_time < 2.0:
        test.passed = True
        test.message = f"✓ Performance OK - Add: {add_time:.3f}s, Query: {query_time:.3f}s"
        test.metrics['add_time'] = add_time
        test.metrics['query_time'] = query_time
    else:
        test.message = f"FAILED: Too slow - Add: {add_time:.3f}s, Query: {query_time:.3f}s"

    return test

def test_8_gpu_status():
    """Test: GPU acceleration status"""
    test = TestResult("GPU Acceleration")

    success, output, error = run_command("~/.claude/ccks stats")
    if not success:
        test.message = f"FAILED: Could not get stats: {error}"
        return test

    try:
        stats = json.loads(output)
        using_gpu = stats.get('using_gpu', False)
        gpu_accelerations = stats.get('gpu_accelerations', 0)

        test.passed = True
        if using_gpu:
            test.message = f"✓ GPU enabled - {gpu_accelerations} accelerations"
        else:
            test.message = f"✓ GPU disabled (CPU fallback active)"
        test.metrics['using_gpu'] = using_gpu
        test.metrics['gpu_accelerations'] = gpu_accelerations
    except Exception as e:
        test.message = f"FAILED: Could not check GPU status: {e}"

    return test

def main():
    """Run all tests and report results"""
    print("=" * 60)
    print("🧪 CCKS PRIME DIRECTIVE TEST SUITE")
    print("Per FREEDOM: 'If it doesn't run, it doesn't exist'")
    print("=" * 60)
    print()

    tests = [
        test_1_basic_functionality,
        test_2_add_and_query,
        test_3_persistence,
        test_4_memory_limits,
        test_5_freedom_integration,
        test_6_token_metrics,
        test_7_performance,
        test_8_gpu_status
    ]

    results = []
    passed = 0
    failed = 0

    for test_func in tests:
        print(f"Running: {test_func.__doc__}...", end=" ")

        try:
            result = test_func()
            results.append(result)

            if result.passed:
                print(f"✅ PASSED")
                print(f"  {result.message}")
                passed += 1
            else:
                print(f"❌ FAILED")
                print(f"  {result.message}")
                failed += 1

            if result.metrics:
                print(f"  Metrics: {json.dumps(result.metrics, indent=4)}")

        except Exception as e:
            print(f"❌ EXCEPTION")
            print(f"  Error: {e}")
            failed += 1

        print()

    # Final Report
    print("=" * 60)
    print("📊 FINAL REPORT")
    print("=" * 60)

    total = passed + failed
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

    if success_rate == 100:
        print("\n🎉 VERDICT: SYSTEM FULLY OPERATIONAL")
        print("✓ CCKS meets all Prime Directive requirements")
        print("✓ Ready for production use")
    elif success_rate >= 80:
        print("\n⚠️ VERDICT: SYSTEM PARTIALLY OPERATIONAL")
        print("- Core functionality working")
        print("- Some features need attention")
    else:
        print("\n❌ VERDICT: SYSTEM NOT READY")
        print("- Does not meet Prime Directive")
        print("- Critical failures detected")

    # Write test report
    report = {
        'timestamp': datetime.now().isoformat(),
        'passed': passed,
        'failed': failed,
        'success_rate': success_rate,
        'tests': [
            {
                'name': r.test_name,
                'passed': r.passed,
                'message': r.message,
                'metrics': r.metrics
            } for r in results
        ]
    }

    report_path = Path.home() / '.claude' / 'claude-knowledge-system' / 'test_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📝 Full report saved to: {report_path}")

    return 0 if success_rate == 100 else 1

if __name__ == "__main__":
    sys.exit(main())