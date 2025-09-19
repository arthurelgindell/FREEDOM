#!/usr/bin/env python3
"""
FREEDOM Analytics Module
High-performance analytics using DuckDB
"""

import duckdb
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List
import json

class Analytics:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "freedom_analytics.db"
        self.db_path = str(db_path)
        self._init_tables()
    
    @contextmanager
    def connection(self):
        """Context manager for database connections"""
        conn = duckdb.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_tables(self):
        """Initialize required database tables"""
        with self.connection() as conn:
            # Create sequences for auto-incrementing IDs
            try:
                conn.execute("CREATE SEQUENCE IF NOT EXISTS metrics_seq")
                conn.execute("CREATE SEQUENCE IF NOT EXISTS performance_seq")
                conn.execute("CREATE SEQUENCE IF NOT EXISTS health_seq")
                conn.execute("CREATE SEQUENCE IF NOT EXISTS events_seq")
            except:
                pass  # Sequences might already exist
            
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER DEFAULT nextval('metrics_seq'),
                    component VARCHAR NOT NULL,
                    metric_type VARCHAR NOT NULL,
                    value DOUBLE NOT NULL,
                    unit VARCHAR,
                    metadata VARCHAR,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Model performance table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER DEFAULT nextval('performance_seq'),
                    model_name VARCHAR NOT NULL,
                    inference_time_ms DOUBLE NOT NULL,
                    tokens_per_second DOUBLE,
                    memory_usage_mb DOUBLE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System health table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER DEFAULT nextval('health_seq'),
                    component VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    details VARCHAR,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Events table for general logging
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER DEFAULT nextval('events_seq'),
                    event_type VARCHAR NOT NULL,
                    data VARCHAR,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def log_event(self, event_type: str, data: Dict = None):
        """Log a general event"""
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO events (event_type, data)
                VALUES (?, ?)
            """, [event_type, json.dumps(data) if data else None])
    
    def log_metric(self, component: str, metric_type: str, value: float, 
                   unit: str = None, metadata: Dict = None):
        """Log a system metric"""
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO system_metrics (component, metric_type, value, unit, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, [component, metric_type, value, unit, json.dumps(metadata) if metadata else None])
    
    def log_model_performance(self, model_name: str, inference_time_ms: float,
                             tokens_per_second: float = None, memory_usage_mb: float = None):
        """Log model performance metrics"""
        with self.connection() as conn:
            conn.execute("""
                INSERT INTO model_performance 
                (model_name, inference_time_ms, tokens_per_second, memory_usage_mb)
                VALUES (?, ?, ?, ?)
            """, [model_name, inference_time_ms, tokens_per_second, memory_usage_mb])
    
    def get_system_health(self) -> List[Dict[str, Any]]:
        """Get current system health metrics"""
        with self.connection() as conn:
            result = conn.execute("SELECT * FROM system_health").fetchall()
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row)) for row in result]
    
    def query(self, sql: str, params: List = None) -> List[Dict[str, Any]]:
        """Execute arbitrary query"""
        with self.connection() as conn:
            result = conn.execute(sql, params or []).fetchall()
            columns = [desc[0] for desc in conn.description]
            return [dict(zip(columns, row)) for row in result]

# Module-level instance
analytics = Analytics()
