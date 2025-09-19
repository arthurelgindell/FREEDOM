#!/usr/bin/env python3
"""
Integration script for the intelligent model router
Demonstrates how to integrate the router with existing FREEDOM agents
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.orchestration.agents.routed_agent import (
    create_routed_coder_agent, 
    create_routed_analyst_agent,
    create_routed_general_agent
)
from core.orchestration.model_router import TaskType

async def test_routed_agents():
    """Test the routed agents with different task types"""
    
    print("🤖 Testing Routed Agents")
    print("=" * 50)
    
    # Create different types of routed agents
    coder_agent = create_routed_coder_agent()
    analyst_agent = create_routed_analyst_agent()
    general_agent = create_routed_general_agent()
    
    # Test cases
    test_cases = [
        {
            "agent": coder_agent,
            "prompt": "Write a Python function to sort a list of integers using quicksort",
            "context": {"task_type": "code_generation", "complexity": 4}
        },
        {
            "agent": analyst_agent,
            "prompt": "Analyze the pros and cons of microservices architecture vs monolithic architecture",
            "context": {"task_type": "reasoning", "complexity": 7}
        },
        {
            "agent": general_agent,
            "prompt": "Explain the concept of machine learning in simple terms",
            "context": {"task_type": "completion", "complexity": 3}
        },
        {
            "agent": coder_agent,
            "prompt": "Create a comprehensive web scraping framework with error handling, rate limiting, and data validation",
            "context": {"task_type": "code_generation", "complexity": 8}
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {case['agent'].config.name} ---")
        print(f"Prompt: {case['prompt'][:60]}...")
        print(f"Context: {case['context']}")
        
        try:
            response = await case['agent'].generate_response(
                case['prompt'], 
                case['context']
            )
            
            print(f"✅ Response length: {len(response)} chars")
            print(f"   Preview: {response[:100]}...")
            
            # Get routing stats
            stats = await case['agent'].get_routing_stats()
            print(f"   Routing stats: {len(stats)} models tracked")
            
        except Exception as e:
            print(f"❌ Error: {e}")

async def test_router_integration():
    """Test direct router integration"""
    
    print("\n🔧 Testing Router Integration")
    print("=" * 50)
    
    from core.orchestration.model_router import IntelligentModelRouter
    from core.orchestration.model_client import UnifiedModelClient
    
    router = IntelligentModelRouter()
    client = UnifiedModelClient(router)
    
    # Test different routing scenarios
    scenarios = [
        {
            "prompt": "Simple hello world",
            "task_type": TaskType.CODE_GENERATION,
            "complexity": 1,
            "expected": "Should route to local"
        },
        {
            "prompt": "Complex philosophical analysis of AI consciousness",
            "task_type": TaskType.REASONING,
            "complexity": 9,
            "expected": "Should route to Claude"
        },
        {
            "prompt": "Complete this code: def fibonacci(n):",
            "task_type": TaskType.COMPLETION,
            "complexity": 2,
            "expected": "Should route to local or OpenAI"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i} ---")
        print(f"Prompt: {scenario['prompt']}")
        print(f"Expected: {scenario['expected']}")
        
        try:
            result = await client.generate(
                scenario['prompt'],
                scenario['task_type'],
                scenario['complexity']
            )
            
            if result['success']:
                decision = result['routing_decision']
                print(f"✅ Selected: {decision.selected_model.value}")
                print(f"   Reasoning: {decision.reasoning}")
                print(f"   Execution time: {result['execution_time']:.2f}s")
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

async def test_analytics():
    """Test analytics and optimization"""
    
    print("\n📊 Testing Analytics")
    print("=" * 50)
    
    from core.orchestration.router_analytics import RouterAnalytics
    
    analytics = RouterAnalytics()
    
    # Get performance report
    performance = analytics.get_model_performance_report(hours=1)
    print(f"Performance report: {len(performance)} models")
    
    # Get cost analysis
    costs = analytics.get_cost_analysis(days=1)
    print(f"Total cost: ${costs['total_cost']:.6f}")
    
    # Get optimization recommendations
    recommendations = analytics.get_optimization_recommendations()
    print(f"Recommendations: {len(recommendations['recommendations'])}")
    
    for rec in recommendations['recommendations']:
        print(f"  - {rec['type']}: {rec['issue']}")

async def main():
    """Run all integration tests"""
    
    print("🎯 FREEDOM Router Integration Test")
    print("=" * 60)
    
    # Test 1: Routed agents
    await test_routed_agents()
    
    # Test 2: Direct router integration
    await test_router_integration()
    
    # Test 3: Analytics
    await test_analytics()
    
    print("\n" + "=" * 60)
    print("🏁 Integration tests completed!")
    print("\nNext steps:")
    print("1. Set up API keys for commercial models (Claude, OpenAI, Gemini)")
    print("2. Ensure LM Studio is running on localhost:1234")
    print("3. Run: python core/orchestration/test_router.py")
    print("4. Integrate routed agents into your orchestrator graphs")

if __name__ == "__main__":
    asyncio.run(main())

