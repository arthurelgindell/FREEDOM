"""
Model Router - Backwards Compatible Wrapper

⚠️ LEGACY COMPATIBILITY LAYER ⚠️
This file maintains backwards compatibility for existing code.
New code should use model_router_v2.py directly:

    from core.orchestration.model_router_v2 import ModelRouterFactory
    router = await ModelRouterFactory.create()

This wrapper delegates all operations to the new refactored implementation.
"""

from .migrate_router import BackwardsCompatibleRouter
from .model_router_v2 import RoutingDecision, ModelPerformance
from .types import ModelType, TaskType

# Export the backwards compatible router as IntelligentModelRouter
IntelligentModelRouter = BackwardsCompatibleRouter

# Re-export common types for compatibility
__all__ = [
    'IntelligentModelRouter',
    'RoutingDecision',
    'ModelPerformance',
    'ModelType',
    'TaskType',
    'CostTracker'
]

# Legacy CostTracker for compatibility
class CostTracker:
    """Legacy CostTracker - now handled by metrics module"""
    
    def __init__(self):
        self.daily_costs = {}
        self.model_costs = {}
    
    def track_usage(self, model_type: ModelType, actual_cost: float, tokens_used: int):
        """Track actual usage for improving estimates"""
        import time
        today = time.strftime("%Y-%m-%d")
        
        if today not in self.daily_costs:
            self.daily_costs[today] = 0.0
        
        self.daily_costs[today] += actual_cost
        
        if model_type not in self.model_costs:
            self.model_costs[model_type] = {"total_cost": 0.0, "total_tokens": 0}
        
        self.model_costs[model_type]["total_cost"] += actual_cost
        self.model_costs[model_type]["total_tokens"] += tokens_used
    
    def get_daily_budget_remaining(self, daily_budget: float = 10.0) -> float:
        """Check remaining daily budget"""
        import time
        today = time.strftime("%Y-%m-%d")
        used_today = self.daily_costs.get(today, 0.0)
        return max(0.0, daily_budget - used_today)