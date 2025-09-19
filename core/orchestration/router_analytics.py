import sqlite3
import time
from typing import Dict, Any, Optional
from .model_router import RoutingDecision, ModelType

from pathlib import Path
class RouterAnalytics:
    """Analyze router performance and optimize decisions"""
    
    def __init__(self, db_path: str = "Path(__file__).parent.parent.parent/router_analytics.db"):
        self.db_path = db_path
        self._init_analytics_db()
    
    def _init_analytics_db(self):
        """Setup analytics database"""
        conn = sqlite3.connect(self.db_path)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS routing_decisions (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                objective TEXT,
                task_type TEXT,
                complexity INTEGER,
                selected_model TEXT,
                reasoning TEXT,
                estimated_cost REAL,
                actual_cost REAL,
                execution_time REAL,
                estimated_time REAL,
                success BOOLEAN,
                tokens_used INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_execution(self, decision: RoutingDecision, result: Dict[str, Any]):
        """Log completed execution for analysis"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO routing_decisions 
            (timestamp, objective, task_type, complexity, selected_model, reasoning, 
             estimated_cost, actual_cost, execution_time, estimated_time, success, tokens_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.time(),
            result.get("objective", "")[:100],  # Truncate
            result.get("task_type", ""),
            result.get("complexity", 5),
            decision.selected_model.value,
            decision.reasoning,
            decision.estimated_cost,
            result.get("actual_cost", 0.0),
            result.get("execution_time", 0.0),
            decision.estimated_time,
            result.get("success", False),
            result.get("response", {}).get("tokens_used", 0)
        ))
        conn.commit()
        conn.close()
    
    def get_model_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report for all models"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT 
                selected_model,
                COUNT(*) as total_requests,
                AVG(execution_time) as avg_time,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                SUM(actual_cost) as total_cost,
                SUM(tokens_used) as total_tokens
            FROM routing_decisions 
            WHERE timestamp > ? 
            GROUP BY selected_model
        """, (time.time() - (hours * 3600),))
        
        results = {}
        for row in cursor.fetchall():
            model, total, avg_time, successes, cost, tokens = row
            results[model] = {
                "total_requests": total,
                "success_rate": successes / total if total > 0 else 0,
                "avg_execution_time": avg_time or 0,
                "total_cost": cost or 0,
                "total_tokens": tokens or 0,
                "cost_per_token": (cost / tokens) if tokens > 0 else 0
            }
        
        conn.close()
        return results
    
    def get_routing_accuracy(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze routing decision accuracy"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT 
                selected_model,
                reasoning,
                success,
                execution_time,
                estimated_time
            FROM routing_decisions 
            WHERE timestamp > ? AND estimated_time > 0
        """, (time.time() - (hours * 3600),))
        
        accuracy_data = {}
        for row in cursor.fetchall():
            model, reasoning, success, actual_time, estimated_time = row
            if model not in accuracy_data:
                accuracy_data[model] = {
                    "time_accuracy": [],
                    "success_rate": [],
                    "reasoning_patterns": {}
                }
            
            # Time accuracy (how close estimated vs actual)
            if actual_time and estimated_time:
                time_accuracy = 1 - abs(actual_time - estimated_time) / estimated_time
                accuracy_data[model]["time_accuracy"].append(max(0, time_accuracy))
            
            # Success rate
            accuracy_data[model]["success_rate"].append(1 if success else 0)
            
            # Reasoning patterns
            if reasoning not in accuracy_data[model]["reasoning_patterns"]:
                accuracy_data[model]["reasoning_patterns"][reasoning] = {"total": 0, "successes": 0}
            accuracy_data[model]["reasoning_patterns"][reasoning]["total"] += 1
            if success:
                accuracy_data[model]["reasoning_patterns"][reasoning]["successes"] += 1
        
        # Calculate averages
        for model in accuracy_data:
            time_acc = accuracy_data[model]["time_accuracy"]
            success_acc = accuracy_data[model]["success_rate"]
            
            accuracy_data[model]["avg_time_accuracy"] = sum(time_acc) / len(time_acc) if time_acc else 0
            accuracy_data[model]["avg_success_rate"] = sum(success_acc) / len(success_acc) if success_acc else 0
            
            # Best reasoning patterns
            best_reasoning = None
            best_rate = 0
            for reasoning, stats in accuracy_data[model]["reasoning_patterns"].items():
                rate = stats["successes"] / stats["total"] if stats["total"] > 0 else 0
                if rate > best_rate:
                    best_rate = rate
                    best_reasoning = reasoning
            
            accuracy_data[model]["best_reasoning"] = best_reasoning
            accuracy_data[model]["best_reasoning_rate"] = best_rate
        
        conn.close()
        return accuracy_data
    
    def get_cost_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze cost patterns and optimization opportunities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT 
                DATE(timestamp, 'unixepoch') as date,
                selected_model,
                SUM(actual_cost) as daily_cost,
                SUM(tokens_used) as daily_tokens,
                COUNT(*) as daily_requests
            FROM routing_decisions 
            WHERE timestamp > ? AND success = 1
            GROUP BY date, selected_model
            ORDER BY date DESC
        """, (time.time() - (days * 86400),))
        
        cost_data = {}
        for row in cursor.fetchall():
            date, model, cost, tokens, requests = row
            if date not in cost_data:
                cost_data[date] = {}
            cost_data[date][model] = {
                "cost": cost or 0,
                "tokens": tokens or 0,
                "requests": requests,
                "cost_per_token": (cost / tokens) if tokens > 0 else 0
            }
        
        # Calculate totals and trends
        total_cost = 0
        total_tokens = 0
        model_totals = {}
        
        for date, models in cost_data.items():
            for model, stats in models.items():
                total_cost += stats["cost"]
                total_tokens += stats["tokens"]
                
                if model not in model_totals:
                    model_totals[model] = {"cost": 0, "tokens": 0, "requests": 0}
                model_totals[model]["cost"] += stats["cost"]
                model_totals[model]["tokens"] += stats["tokens"]
                model_totals[model]["requests"] += stats["requests"]
        
        return {
            "daily_breakdown": cost_data,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "model_totals": model_totals,
            "avg_cost_per_token": total_cost / total_tokens if total_tokens > 0 else 0
        }
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Generate recommendations for router optimization"""
        performance = self.get_model_performance_report(24)
        accuracy = self.get_routing_accuracy(24)
        costs = self.get_cost_analysis(7)
        
        recommendations = []
        
        # Check for underperforming models
        for model, stats in performance.items():
            if stats["success_rate"] < 0.8:
                recommendations.append({
                    "type": "performance",
                    "model": model,
                    "issue": f"Low success rate: {stats['success_rate']:.2%}",
                    "suggestion": "Consider reducing complexity threshold or improving error handling"
                })
        
        # Check for cost optimization opportunities
        if costs["total_cost"] > 0:
            local_requests = costs["model_totals"].get("local_mlx", {}).get("requests", 0)
            total_requests = sum(m["requests"] for m in costs["model_totals"].values())
            
            if local_requests / total_requests < 0.5:
                recommendations.append({
                    "type": "cost",
                    "issue": f"Only {local_requests/total_requests:.1%} requests using local models",
                    "suggestion": "Increase local model usage by lowering complexity threshold"
                })
        
        # Check for routing accuracy
        for model, stats in accuracy.items():
            if stats["avg_time_accuracy"] < 0.7:
                recommendations.append({
                    "type": "accuracy",
                    "model": model,
                    "issue": f"Poor time estimation accuracy: {stats['avg_time_accuracy']:.2%}",
                    "suggestion": "Update performance metrics with recent data"
                })
        
        return {
            "recommendations": recommendations,
            "performance_summary": performance,
            "accuracy_summary": {k: v["avg_success_rate"] for k, v in accuracy.items()},
            "cost_summary": costs
        }
