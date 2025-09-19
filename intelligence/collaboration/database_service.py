#!/usr/bin/env python3
"""
Database Service for CrewAI System
Handles data persistence and retrieval for crew operations
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
from contextlib import contextmanager

from .task_executor import TaskResult, TaskStatus


@dataclass
class TaskRecord:
    """Database record for a task"""
    task_id: str
    description: str
    expected_output: str
    agents: List[str]
    status: str
    result: Optional[str]
    error: Optional[str]
    created_time: float
    completed_time: Optional[float]
    execution_time: Optional[float]
    metadata: Dict[str, Any]


@dataclass
class AgentActivity:
    """Record of agent activity"""
    agent_id: str
    task_id: str
    action: str
    timestamp: float
    details: Optional[Dict[str, Any]] = None


class DatabasePool:
    """Simple connection pool for SQLite"""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool_size = pool_size
        self._ensure_database()
    
    def _ensure_database(self):
        """Ensure database file exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def acquire(self):
        """Acquire a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class CrewDatabaseService:
    """Database service for CrewAI system"""
    
    def __init__(self, db_path: str = "Path(__file__).parent.parent.parent/intelligence/collaboration/crew_system.db"):
        self.db_pool = DatabasePool(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with self.db_pool.acquire() as conn:
            # Tasks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crew_tasks (
                    task_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    expected_output TEXT,
                    agents TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_time REAL NOT NULL,
                    completed_time REAL,
                    execution_time REAL,
                    metadata TEXT
                )
            ''')
            
            # Agent activities table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    details TEXT,
                    FOREIGN KEY (task_id) REFERENCES crew_tasks (task_id)
                )
            ''')
            
            # Task dependencies table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    dependent_task_id TEXT NOT NULL,
                    required_task_id TEXT NOT NULL,
                    PRIMARY KEY (dependent_task_id, required_task_id),
                    FOREIGN KEY (dependent_task_id) REFERENCES crew_tasks (task_id),
                    FOREIGN KEY (required_task_id) REFERENCES crew_tasks (task_id)
                )
            ''')
            
            # Agent performance metrics
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_metrics (
                    agent_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    PRIMARY KEY (agent_id, metric_name, timestamp)
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON crew_tasks(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created ON crew_tasks(created_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_activities_agent ON agent_activities(agent_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_activities_task ON agent_activities(task_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_metrics_agent ON agent_metrics(agent_id)')
    
    async def log_task(self, task_id: str, description: str, expected_output: str,
                      agents: List[str], metadata: Optional[Dict[str, Any]] = None):
        """Log a new task"""
        with self.db_pool.acquire() as conn:
            conn.execute('''
                INSERT INTO crew_tasks 
                (task_id, description, expected_output, agents, status, created_time, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                description,
                expected_output,
                json.dumps(agents),
                TaskStatus.PENDING.value,
                time.time(),
                json.dumps(metadata or {})
            ))
        
        self.logger.info(f"Logged new task: {task_id}")
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               result: Optional[str] = None,
                               error: Optional[str] = None):
        """Update task status"""
        with self.db_pool.acquire() as conn:
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                completed_time = time.time()
                
                # Calculate execution time
                cursor = conn.execute(
                    'SELECT created_time FROM crew_tasks WHERE task_id = ?',
                    (task_id,)
                )
                row = cursor.fetchone()
                if row:
                    execution_time = completed_time - row['created_time']
                else:
                    execution_time = None
                
                conn.execute('''
                    UPDATE crew_tasks 
                    SET status = ?, result = ?, error = ?, 
                        completed_time = ?, execution_time = ?
                    WHERE task_id = ?
                ''', (status.value, result, error, completed_time, execution_time, task_id))
            else:
                conn.execute('''
                    UPDATE crew_tasks 
                    SET status = ?
                    WHERE task_id = ?
                ''', (status.value, task_id))
        
        self.logger.info(f"Updated task {task_id} status to {status.value}")
    
    async def log_agent_activity(self, agent_id: str, task_id: str, 
                               action: str, details: Optional[Dict[str, Any]] = None):
        """Log agent activity"""
        with self.db_pool.acquire() as conn:
            conn.execute('''
                INSERT INTO agent_activities 
                (agent_id, task_id, action, timestamp, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                agent_id,
                task_id,
                action,
                time.time(),
                json.dumps(details or {})
            ))
    
    async def add_task_dependency(self, dependent_task_id: str, required_task_id: str):
        """Add a dependency between tasks"""
        with self.db_pool.acquire() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO task_dependencies 
                (dependent_task_id, required_task_id)
                VALUES (?, ?)
            ''', (dependent_task_id, required_task_id))
    
    async def record_agent_metric(self, agent_id: str, metric_name: str, metric_value: float):
        """Record an agent performance metric"""
        with self.db_pool.acquire() as conn:
            conn.execute('''
                INSERT INTO agent_metrics 
                (agent_id, metric_name, metric_value, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (agent_id, metric_name, metric_value, time.time()))
    
    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get a task by ID"""
        with self.db_pool.acquire() as conn:
            cursor = conn.execute(
                'SELECT * FROM crew_tasks WHERE task_id = ?',
                (task_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return TaskRecord(
                    task_id=row['task_id'],
                    description=row['description'],
                    expected_output=row['expected_output'],
                    agents=json.loads(row['agents']),
                    status=row['status'],
                    result=row['result'],
                    error=row['error'],
                    created_time=row['created_time'],
                    completed_time=row['completed_time'],
                    execution_time=row['execution_time'],
                    metadata=json.loads(row['metadata'] or '{}')
                )
        
        return None
    
    def get_tasks_by_status(self, status: TaskStatus, limit: int = 100) -> List[TaskRecord]:
        """Get tasks by status"""
        with self.db_pool.acquire() as conn:
            cursor = conn.execute('''
                SELECT * FROM crew_tasks 
                WHERE status = ? 
                ORDER BY created_time DESC 
                LIMIT ?
            ''', (status.value, limit))
            
            tasks = []
            for row in cursor:
                tasks.append(TaskRecord(
                    task_id=row['task_id'],
                    description=row['description'],
                    expected_output=row['expected_output'],
                    agents=json.loads(row['agents']),
                    status=row['status'],
                    result=row['result'],
                    error=row['error'],
                    created_time=row['created_time'],
                    completed_time=row['completed_time'],
                    execution_time=row['execution_time'],
                    metadata=json.loads(row['metadata'] or '{}')
                ))
            
            return tasks
    
    def get_agent_activities(self, agent_id: Optional[str] = None, 
                           task_id: Optional[str] = None,
                           limit: int = 100) -> List[AgentActivity]:
        """Get agent activities"""
        with self.db_pool.acquire() as conn:
            query = 'SELECT * FROM agent_activities WHERE 1=1'
            params = []
            
            if agent_id:
                query += ' AND agent_id = ?'
                params.append(agent_id)
            
            if task_id:
                query += ' AND task_id = ?'
                params.append(task_id)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            
            activities = []
            for row in cursor:
                activities.append(AgentActivity(
                    agent_id=row['agent_id'],
                    task_id=row['task_id'],
                    action=row['action'],
                    timestamp=row['timestamp'],
                    details=json.loads(row['details'] or '{}')
                ))
            
            return activities
    
    def get_agent_metrics(self, agent_id: str, metric_name: Optional[str] = None,
                         since: Optional[float] = None) -> List[Tuple[str, float, float]]:
        """Get agent performance metrics"""
        with self.db_pool.acquire() as conn:
            query = 'SELECT metric_name, metric_value, timestamp FROM agent_metrics WHERE agent_id = ?'
            params = [agent_id]
            
            if metric_name:
                query += ' AND metric_name = ?'
                params.append(metric_name)
            
            if since:
                query += ' AND timestamp >= ?'
                params.append(since)
            
            query += ' ORDER BY timestamp DESC'
            
            cursor = conn.execute(query, params)
            return [(row[0], row[1], row[2]) for row in cursor]
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get overall task statistics"""
        with self.db_pool.acquire() as conn:
            # Task counts by status
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count 
                FROM crew_tasks 
                GROUP BY status
            ''')
            status_counts = dict(cursor.fetchall())
            
            # Average execution time
            cursor = conn.execute('''
                SELECT AVG(execution_time) 
                FROM crew_tasks 
                WHERE execution_time IS NOT NULL
            ''')
            avg_execution_time = cursor.fetchone()[0] or 0
            
            # Tasks per agent
            cursor = conn.execute('''
                SELECT agents, COUNT(*) as count 
                FROM crew_tasks 
                GROUP BY agents
            ''')
            
            agent_task_counts = {}
            for row in cursor:
                agents = json.loads(row[0])
                for agent in agents:
                    agent_task_counts[agent] = agent_task_counts.get(agent, 0) + row[1]
            
            # Recent activity
            cursor = conn.execute('''
                SELECT COUNT(*) 
                FROM crew_tasks 
                WHERE created_time > ?
            ''', (time.time() - 86400,))  # Last 24 hours
            recent_tasks = cursor.fetchone()[0]
            
            return {
                "status_counts": status_counts,
                "average_execution_time": avg_execution_time,
                "agent_task_counts": agent_task_counts,
                "recent_tasks_24h": recent_tasks,
                "total_tasks": sum(status_counts.values())
            }
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records"""
        cutoff_time = time.time() - (days * 86400)
        
        with self.db_pool.acquire() as conn:
            # Delete old completed tasks
            conn.execute('''
                DELETE FROM crew_tasks 
                WHERE status IN (?, ?) 
                AND completed_time < ?
            ''', (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, cutoff_time))
            
            # Delete orphaned activities
            conn.execute('''
                DELETE FROM agent_activities 
                WHERE task_id NOT IN (SELECT task_id FROM crew_tasks)
            ''')
            
            # Delete old metrics
            conn.execute('''
                DELETE FROM agent_metrics 
                WHERE timestamp < ?
            ''', (cutoff_time,))
        
        self.logger.info(f"Cleaned up records older than {days} days")
