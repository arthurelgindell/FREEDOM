#!/usr/bin/env python3
"""
Task Executor for CrewAI System
Handles task creation, execution, and result management
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

from crewai import Task, Crew, Process, Agent


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrewProcess(Enum):
    """Crew execution process types"""
    SEQUENTIAL = Process.sequential
    HIERARCHICAL = Process.hierarchical


@dataclass
class TaskConfig:
    """Configuration for task creation"""
    description: str
    expected_output: str
    agent: Optional[Agent] = None
    context: Optional[List[Task]] = None
    tools: Optional[List] = None
    async_execution: bool = False
    callback: Optional[Callable] = None
    
    def to_task(self) -> Task:
        """Convert config to CrewAI Task"""
        return Task(
            description=self.description,
            expected_output=self.expected_output,
            agent=self.agent,
            context=self.context,
            tools=self.tools,
            async_execution=self.async_execution,
            callback=self.callback
        )


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    agents_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def successful(self) -> bool:
        """Check if task was successful"""
        return self.status == TaskStatus.COMPLETED


class TaskExecutor:
    """Executes tasks using CrewAI crews"""
    
    def __init__(self, agent_manager=None):
        self.agent_manager = agent_manager
        self.logger = logging.getLogger(__name__)
        self._active_tasks: Dict[str, TaskStatus] = {}
        self._task_results: Dict[str, TaskResult] = {}
    
    def create_task(self, config: TaskConfig) -> Task:
        """Create a task from configuration"""
        return config.to_task()
    
    def create_crew(self, agents: List[Agent], 
                   process: CrewProcess = CrewProcess.SEQUENTIAL,
                   verbose: bool = True,
                   memory: bool = True) -> Crew:
        """Create a crew with specified agents and process"""
        return Crew(
            agents=agents,
            process=process.value,
            verbose=verbose,
            memory=memory
        )
    
    async def execute_task(self, task: Task, agents: List[Agent], 
                          process: CrewProcess = CrewProcess.SEQUENTIAL) -> TaskResult:
        """Execute a single task with a crew"""
        task_id = self._generate_task_id(task.description)
        self._active_tasks[task_id] = TaskStatus.RUNNING
        
        start_time = time.time()
        
        try:
            # Create crew
            crew = self.create_crew(agents, process)
            
            # Assign task to crew
            crew.tasks = [task]
            
            # Execute
            self.logger.info(f"Executing task {task_id} with {len(agents)} agents")
            result = await self._execute_crew(crew)
            
            # Create result
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                output=result,
                execution_time=time.time() - start_time,
                agents_used=[agent.role for agent in agents]
            )
            
            self._task_results[task_id] = task_result
            self._active_tasks[task_id] = TaskStatus.COMPLETED
            
            return task_result
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}")
            
            task_result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                agents_used=[agent.role for agent in agents]
            )
            
            self._task_results[task_id] = task_result
            self._active_tasks[task_id] = TaskStatus.FAILED
            
            return task_result
    
    async def _execute_crew(self, crew: Crew) -> Any:
        """Execute crew in async context"""
        # CrewAI's kickoff is synchronous, so we run it in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, crew.kickoff)
    
    async def execute_batch_tasks(self, task_configs: List[TaskConfig], 
                                agents: List[Agent],
                                process: CrewProcess = CrewProcess.SEQUENTIAL,
                                max_concurrent: int = 3) -> List[TaskResult]:
        """Execute multiple tasks with concurrency control"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_limit(config: TaskConfig):
            async with semaphore:
                task = self.create_task(config)
                return await self.execute_task(task, agents, process)
        
        # Execute all tasks
        tasks = [execute_with_limit(config) for config in task_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_id = self._generate_task_id(task_configs[i].description)
                processed_results.append(TaskResult(
                    task_id=task_id,
                    status=TaskStatus.FAILED,
                    error=str(result),
                    execution_time=0.0
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def _generate_task_id(self, description: str) -> str:
        """Generate unique task ID"""
        content = f"{description}_{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get current status of a task"""
        return self._active_tasks.get(task_id)
    
    def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """Get result of a completed task"""
        return self._task_results.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self._active_tasks and self._active_tasks[task_id] == TaskStatus.RUNNING:
            self._active_tasks[task_id] = TaskStatus.CANCELLED
            self.logger.info(f"Cancelled task {task_id}")
            return True
        return False
    
    def get_active_tasks(self) -> Dict[str, TaskStatus]:
        """Get all active tasks"""
        return {k: v for k, v in self._active_tasks.items() 
                if v in [TaskStatus.PENDING, TaskStatus.RUNNING]}
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        total_tasks = len(self._task_results)
        if total_tasks == 0:
            return {"total_tasks": 0}
        
        successful = sum(1 for r in self._task_results.values() if r.successful)
        failed = total_tasks - successful
        avg_time = sum(r.execution_time for r in self._task_results.values()) / total_tasks
        
        return {
            "total_tasks": total_tasks,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_tasks,
            "average_execution_time": avg_time,
            "active_tasks": len(self.get_active_tasks())
        }


class TaskBuilder:
    """Helper class for building complex tasks"""
    
    @staticmethod
    def create_research_task(topic: str, depth: str = "comprehensive") -> TaskConfig:
        """Create a research task"""
        return TaskConfig(
            description=f"Research {topic} and provide {depth} analysis",
            expected_output=f"A {depth} report on {topic} including key findings, analysis, and recommendations"
        )
    
    @staticmethod
    def create_analysis_task(data_source: str, analysis_type: str) -> TaskConfig:
        """Create a data analysis task"""
        return TaskConfig(
            description=f"Analyze {data_source} using {analysis_type} analysis",
            expected_output=f"Analysis results including insights, patterns, and actionable recommendations"
        )
    
    @staticmethod
    def create_verification_task(claim: str, evidence_required: bool = True) -> TaskConfig:
        """Create a verification task"""
        return TaskConfig(
            description=f"Verify the claim: '{claim}'",
            expected_output=f"Verification result with {'evidence' if evidence_required else 'assessment'} and confidence level"
        )
    
    @staticmethod
    def create_quality_check_task(output: str, standards: List[str]) -> TaskConfig:
        """Create a quality assurance task"""
        standards_text = ", ".join(standards)
        return TaskConfig(
            description=f"Review and ensure quality of: {output}",
            expected_output=f"Quality assessment against standards: {standards_text}, with pass/fail status and improvements"
        )
