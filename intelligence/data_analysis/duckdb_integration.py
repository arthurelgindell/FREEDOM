#!/usr/bin/env python3
"""
DuckDB Integration for FREEDOM Platform
Local-first analytical database for AI data processing
"""

import os
import json
import time
import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import numpy as np

class FREEDOMDuckDBIntegration:
    """DuckDB integration for FREEDOM platform data analysis"""
    
    def __init__(self, db_path: str = "freedom_analytics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize DuckDB connection
        self.conn = duckdb.connect(str(self.db_path))
        
        # Set up FREEDOM-specific configuration
        self._setup_freedom_config()
        
        print(f"🔍 FREEDOM DuckDB Integration initialized")
        print(f"   Database: {self.db_path}")
        print(f"   DuckDB Version: {duckdb.__version__}")
    
    def _setup_freedom_config(self):
        """Set up FREEDOM-specific DuckDB configuration"""
        # Enable extensions for AI/ML workloads
        self.conn.execute("INSTALL 'json';")
        self.conn.execute("LOAD 'json';")
        
        # Set memory limit for local operation
        self.conn.execute("SET memory_limit='8GB';")
        
        # Enable parallel processing
        self.conn.execute("SET threads=8;")
        
        # Create FREEDOM-specific schemas
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS freedom_ai;")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS freedom_metrics;")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS freedom_models;")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS freedom_agents;")
    
    def create_ai_metrics_table(self):
        """Create table for AI model performance metrics"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS freedom_ai.metrics (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            model_name VARCHAR,
            model_type VARCHAR,
            metric_name VARCHAR,
            metric_value DOUBLE,
            run_id VARCHAR,
            experiment_id VARCHAR,
            platform VARCHAR DEFAULT 'freedom'
        );
        """
        self.conn.execute(create_sql)
        print("✅ Created AI metrics table")
    
    def create_model_performance_table(self):
        """Create table for model performance tracking"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS freedom_models.performance (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            model_name VARCHAR,
            model_version VARCHAR,
            tokens_per_second DOUBLE,
            memory_usage_gb DOUBLE,
            model_size_gb DOUBLE,
            efficiency_score DOUBLE,
            accuracy DOUBLE,
            loss DOUBLE,
            run_id VARCHAR,
            platform VARCHAR DEFAULT 'freedom'
        );
        """
        self.conn.execute(create_sql)
        print("✅ Created model performance table")
    
    def create_agent_activity_table(self):
        """Create table for agent activity tracking"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS freedom_agents.activity (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            agent_id VARCHAR,
            agent_type VARCHAR,
            task_type VARCHAR,
            completion_time DOUBLE,
            success_rate DOUBLE,
            resource_usage DOUBLE,
            status VARCHAR,
            error_message VARCHAR,
            platform VARCHAR DEFAULT 'freedom'
        );
        """
        self.conn.execute(create_sql)
        print("✅ Created agent activity table")
    
    def create_truth_engine_table(self):
        """Create table for Truth Engine verification data"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS freedom_ai.truth_verification (
            id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP,
            claim_id VARCHAR,
            verification_method VARCHAR,
            verification_time DOUBLE,
            trust_score DOUBLE,
            confidence DOUBLE,
            verification_result VARCHAR,
            platform VARCHAR DEFAULT 'freedom'
        );
        """
        self.conn.execute(create_sql)
        print("✅ Created Truth Engine verification table")
    
    def log_mlx_performance(self, 
                          model_name: str,
                          tokens_per_second: float,
                          memory_usage: float,
                          model_size: float,
                          run_id: str = None,
                          experiment_id: str = None):
        """Log MLX model performance metrics"""
        
        efficiency_score = tokens_per_second / memory_usage if memory_usage > 0 else 0
        
        insert_sql = """
        INSERT INTO freedom_models.performance 
        (id, timestamp, model_name, model_version, tokens_per_second, 
         memory_usage_gb, model_size_gb, efficiency_score, run_id, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        record_id = f"mlx_{int(time.time() * 1000)}"
        
        self.conn.execute(insert_sql, (
            record_id,
            datetime.now(),
            model_name,
            "mlx",
            tokens_per_second,
            memory_usage,
            model_size,
            efficiency_score,
            run_id or "unknown",
            "freedom"
        ))
        
        print(f"📊 Logged MLX performance for {model_name}")
        print(f"   Tokens/sec: {tokens_per_second:.2f}")
        print(f"   Efficiency: {efficiency_score:.2f} tokens/sec/GB")
    
    def log_agent_activity(self,
                          agent_id: str,
                          agent_type: str,
                          task_type: str,
                          completion_time: float,
                          success_rate: float,
                          resource_usage: float,
                          status: str = "completed",
                          error_message: str = None):
        """Log agent activity metrics"""
        
        insert_sql = """
        INSERT INTO freedom_agents.activity 
        (id, timestamp, agent_id, agent_type, task_type, completion_time, 
         success_rate, resource_usage, status, error_message, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        record_id = f"agent_{int(time.time() * 1000)}"
        
        self.conn.execute(insert_sql, (
            record_id,
            datetime.now(),
            agent_id,
            agent_type,
            task_type,
            completion_time,
            success_rate,
            resource_usage,
            status,
            error_message,
            "freedom"
        ))
        
        print(f"🤖 Logged agent activity for {agent_id}")
        print(f"   Task: {task_type}")
        print(f"   Success Rate: {success_rate:.2f}")
    
    def log_truth_verification(self,
                              claim_id: str,
                              verification_method: str,
                              verification_time: float,
                              trust_score: float,
                              confidence: float,
                              verification_result: str):
        """Log Truth Engine verification data"""
        
        insert_sql = """
        INSERT INTO freedom_ai.truth_verification 
        (id, timestamp, claim_id, verification_method, verification_time, 
         trust_score, confidence, verification_result, platform)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        record_id = f"truth_{int(time.time() * 1000)}"
        
        self.conn.execute(insert_sql, (
            record_id,
            datetime.now(),
            claim_id,
            verification_method,
            verification_time,
            trust_score,
            confidence,
            verification_result,
            "freedom"
        ))
        
        print(f"🔍 Logged Truth Engine verification for {claim_id}")
        print(f"   Trust Score: {trust_score:.2f}")
        print(f"   Method: {verification_method}")
    
    def analyze_model_performance(self, 
                                model_name: str = None,
                                days_back: int = 30) -> pd.DataFrame:
        """Analyze model performance over time"""
        
        where_clause = ""
        params = []
        
        if model_name:
            where_clause = "WHERE model_name = ? AND timestamp >= ?"
            params = [model_name, datetime.now() - timedelta(days=days_back)]
        else:
            where_clause = "WHERE timestamp >= ?"
            params = [datetime.now() - timedelta(days=days_back)]
        
        query = f"""
        SELECT 
            model_name,
            DATE(timestamp) as date,
            AVG(tokens_per_second) as avg_tokens_per_second,
            AVG(memory_usage_gb) as avg_memory_usage,
            AVG(efficiency_score) as avg_efficiency,
            COUNT(*) as measurement_count
        FROM freedom_models.performance 
        {where_clause}
        GROUP BY model_name, DATE(timestamp)
        ORDER BY date DESC, model_name
        """
        
        result = self.conn.execute(query, params).fetchdf()
        print(f"📈 Analyzed performance for {len(result)} model-days")
        return result
    
    def analyze_agent_efficiency(self, 
                               agent_type: str = None,
                               days_back: int = 30) -> pd.DataFrame:
        """Analyze agent efficiency metrics"""
        
        where_clause = ""
        params = []
        
        if agent_type:
            where_clause = "WHERE agent_type = ? AND timestamp >= ?"
            params = [agent_type, datetime.now() - timedelta(days=days_back)]
        else:
            where_clause = "WHERE timestamp >= ?"
            params = [datetime.now() - timedelta(days=days_back)]
        
        query = f"""
        SELECT 
            agent_type,
            task_type,
            AVG(completion_time) as avg_completion_time,
            AVG(success_rate) as avg_success_rate,
            AVG(resource_usage) as avg_resource_usage,
            COUNT(*) as task_count
        FROM freedom_agents.activity 
        {where_clause}
        GROUP BY agent_type, task_type
        ORDER BY avg_success_rate DESC, avg_completion_time ASC
        """
        
        result = self.conn.execute(query, params).fetchdf()
        print(f"🤖 Analyzed efficiency for {len(result)} agent-task combinations")
        return result
    
    def analyze_truth_verification_trends(self, 
                                        days_back: int = 30) -> pd.DataFrame:
        """Analyze Truth Engine verification trends"""
        
        query = """
        SELECT 
            DATE(timestamp) as date,
            verification_method,
            AVG(trust_score) as avg_trust_score,
            AVG(verification_time) as avg_verification_time,
            COUNT(*) as verification_count
        FROM freedom_ai.truth_verification 
        WHERE timestamp >= ?
        GROUP BY DATE(timestamp), verification_method
        ORDER BY date DESC, avg_trust_score DESC
        """
        
        params = [datetime.now() - timedelta(days=days_back)]
        result = self.conn.execute(query, params).fetchdf()
        print(f"🔍 Analyzed Truth Engine trends for {len(result)} verification-days")
        return result
    
    def get_platform_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive platform health metrics"""
        
        # Model performance metrics
        model_query = """
        SELECT 
            COUNT(*) as total_measurements,
            AVG(tokens_per_second) as avg_tokens_per_second,
            AVG(efficiency_score) as avg_efficiency,
            MAX(timestamp) as last_measurement
        FROM freedom_models.performance
        WHERE timestamp >= ?
        """
        
        model_result = self.conn.execute(model_query, [datetime.now() - timedelta(days=7)]).fetchone()
        
        # Agent activity metrics
        agent_query = """
        SELECT 
            COUNT(*) as total_activities,
            AVG(success_rate) as avg_success_rate,
            AVG(completion_time) as avg_completion_time,
            MAX(timestamp) as last_activity
        FROM freedom_agents.activity
        WHERE timestamp >= ?
        """
        
        agent_result = self.conn.execute(agent_query, [datetime.now() - timedelta(days=7)]).fetchone()
        
        # Truth Engine metrics
        truth_query = """
        SELECT 
            COUNT(*) as total_verifications,
            AVG(trust_score) as avg_trust_score,
            AVG(verification_time) as avg_verification_time,
            MAX(timestamp) as last_verification
        FROM freedom_ai.truth_verification
        WHERE timestamp >= ?
        """
        
        truth_result = self.conn.execute(truth_query, [datetime.now() - timedelta(days=7)]).fetchone()
        
        health_metrics = {
            "timestamp": datetime.now().isoformat(),
            "model_performance": {
                "total_measurements": model_result[0] or 0,
                "avg_tokens_per_second": model_result[1] or 0,
                "avg_efficiency": model_result[2] or 0,
                "last_measurement": model_result[3].isoformat() if model_result[3] else None
            },
            "agent_activity": {
                "total_activities": agent_result[0] or 0,
                "avg_success_rate": agent_result[1] or 0,
                "avg_completion_time": agent_result[2] or 0,
                "last_activity": agent_result[3].isoformat() if agent_result[3] else None
            },
            "truth_verification": {
                "total_verifications": truth_result[0] or 0,
                "avg_trust_score": truth_result[1] or 0,
                "avg_verification_time": truth_result[2] or 0,
                "last_verification": truth_result[3].isoformat() if truth_result[3] else None
            }
        }
        
        print("📊 Generated platform health metrics")
        return health_metrics
    
    def export_analytics_report(self, 
                              output_path: str = "freedom_analytics_report.json",
                              days_back: int = 30) -> str:
        """Export comprehensive analytics report"""
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "period_days": days_back,
            "platform": "FREEDOM",
            "health_metrics": self.get_platform_health_metrics(),
            "model_performance": self.analyze_model_performance(days_back=days_back).to_dict('records'),
            "agent_efficiency": self.analyze_agent_efficiency(days_back=days_back).to_dict('records'),
            "truth_verification_trends": self.analyze_truth_verification_trends(days_back=days_back).to_dict('records')
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 Exported analytics report to {output_file}")
        return str(output_file)
    
    def create_performance_dashboard_data(self) -> Dict[str, Any]:
        """Create data for performance dashboard"""
        
        # Get recent performance data
        recent_query = """
        SELECT 
            model_name,
            tokens_per_second,
            memory_usage_gb,
            efficiency_score,
            timestamp
        FROM freedom_models.performance
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 100
        """
        
        recent_data = self.conn.execute(recent_query, [datetime.now() - timedelta(hours=24)]).fetchdf()
        
        # Get agent success rates
        agent_query = """
        SELECT 
            agent_type,
            AVG(success_rate) as avg_success_rate,
            COUNT(*) as task_count
        FROM freedom_agents.activity
        WHERE timestamp >= ?
        GROUP BY agent_type
        """
        
        agent_data = self.conn.execute(agent_query, [datetime.now() - timedelta(hours=24)]).fetchdf()
        
        # Get truth verification stats
        truth_query = """
        SELECT 
            verification_method,
            AVG(trust_score) as avg_trust_score,
            COUNT(*) as verification_count
        FROM freedom_ai.truth_verification
        WHERE timestamp >= ?
        GROUP BY verification_method
        """
        
        truth_data = self.conn.execute(truth_query, [datetime.now() - timedelta(hours=24)]).fetchdf()
        
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "recent_performance": recent_data.to_dict('records'),
            "agent_success_rates": agent_data.to_dict('records'),
            "truth_verification_stats": truth_data.to_dict('records')
        }
        
        print("📊 Generated dashboard data")
        return dashboard_data
    
    def close(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()
            print("🔒 DuckDB connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

def main():
    """Example usage of FREEDOM DuckDB integration"""
    print("🔍 FREEDOM DuckDB Integration Example")
    print("=" * 50)
    
    with FREEDOMDuckDBIntegration() as db:
        # Create tables
        db.create_ai_metrics_table()
        db.create_model_performance_table()
        db.create_agent_activity_table()
        db.create_truth_engine_table()
        
        # Log some sample data
        print("\n📊 Logging sample data...")
        
        # MLX performance data
        db.log_mlx_performance(
            model_name="Qwen3-30B-A3B-Instruct",
            tokens_per_second=268.5,
            memory_usage=4.2,
            model_size=15.8,
            run_id="run_001"
        )
        
        # Agent activity data
        db.log_agent_activity(
            agent_id="agent_001",
            agent_type="autonomous",
            task_type="code_generation",
            completion_time=2.3,
            success_rate=0.95,
            resource_usage=1.2
        )
        
        # Truth Engine data
        db.log_truth_verification(
            claim_id="claim_001",
            verification_method="semantic_analysis",
            verification_time=0.045,
            trust_score=0.87,
            confidence=0.92,
            verification_result="verified"
        )
        
        # Generate analytics
        print("\n📈 Generating analytics...")
        
        # Model performance analysis
        model_perf = db.analyze_model_performance(days_back=7)
        print(f"Model performance data: {len(model_perf)} records")
        
        # Agent efficiency analysis
        agent_eff = db.analyze_agent_efficiency(days_back=7)
        print(f"Agent efficiency data: {len(agent_eff)} records")
        
        # Truth verification trends
        truth_trends = db.analyze_truth_verification_trends(days_back=7)
        print(f"Truth verification data: {len(truth_trends)} records")
        
        # Platform health metrics
        health = db.get_platform_health_metrics()
        print(f"Platform health: {health['model_performance']['total_measurements']} measurements")
        
        # Export report
        report_path = db.export_analytics_report("freedom_analytics_report.json")
        print(f"Analytics report exported to: {report_path}")
        
        # Dashboard data
        dashboard = db.create_performance_dashboard_data()
        print(f"Dashboard data generated: {len(dashboard['recent_performance'])} recent records")
    
    print("\n✅ FREEDOM DuckDB Integration example completed!")

if __name__ == "__main__":
    main()
