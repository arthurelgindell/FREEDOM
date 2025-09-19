#!/usr/bin/env python3
"""
FREEDOM CrewAI Multi-Agent Collaboration System (Refactored)

Simplified multi-agent collaboration using modular components:
- AgentManager: Handles agent creation and lifecycle
- TaskExecutor: Manages task execution
- DatabaseService: Provides data persistence
- SystemComponents: Manages shared resources

No external dependencies. Complete data sovereignty.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from crewai import Process
from crewai.tools import BaseTool

# Import modular components
from .agent_manager import AgentManager, AgentRole
from .task_executor import TaskExecutor, TaskConfig, CrewProcess
from .database_service import CrewDatabaseService
from .system_components import SystemComponents, CrewAIConfig, ComponentFactory

# Import FREEDOM tools
from .tools import (
    FREEDOMTool,
    TruthVerificationTool,
    MLXInferenceTool,
    FileAnalysisTool
)


class FREEDOMCrewSystem:
    """
    Simplified multi-agent collaboration system using modular components
    """
    
    def __init__(self, config: Optional[CrewAIConfig] = None):
        self.config = config or CrewAIConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize modular components
        self.components = ComponentFactory.create_default_components(self.config.workspace_path)
        self.agent_manager = AgentManager()
        self.task_executor = TaskExecutor(self.agent_manager)
        self.database = CrewDatabaseService(
            self.config.database_path or 
            str(Path(self.config.workspace_path) / "intelligence" / "collaboration" / "crew_system.db")
        )
        
        # Tools will be initialized after components
        self.tools: Dict[str, FREEDOMTool] = {}
        
        self._initialized = False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()
    
    async def initialize(self):
        """Initialize system components"""
        if self._initialized:
            return
        
        self.logger.info("Initializing FREEDOM CrewAI System")
        
        # Initialize system components
        await self.components.initialize()
        
        # Validate configuration
        valid, issues = self.components.validate_configuration()
        if not valid:
            self.logger.warning(f"Configuration issues: {issues}")
        
        # Initialize tools
        self._initialize_tools()
        
        # Create default agents
        self._create_default_agents()
        
        self._initialized = True
        self.logger.info("FREEDOM CrewAI System initialized")
    
    async def cleanup(self):
        """Cleanup system resources"""
        self.logger.info("Cleaning up FREEDOM CrewAI System")
        
        await self.components.cleanup()
        
        self._initialized = False
        self.logger.info("Cleanup complete")
    
    def _initialize_tools(self):
        """Initialize FREEDOM tools"""
        if self.components.truth_engine:
            self.tools["truth_verification"] = TruthVerificationTool(
                self.components.truth_engine, 
                self.components.mlx_server
            )
            self.components.tools.register_tool("truth_verification", self.tools["truth_verification"])
        
        if self.components.mlx_server:
            self.tools["mlx_inference"] = MLXInferenceTool(
                self.components.truth_engine,
                self.components.mlx_server
            )
            self.components.tools.register_tool("mlx_inference", self.tools["mlx_inference"])
        
        # File analysis is always available
        self.tools["file_analysis"] = FileAnalysisTool(
            self.components.truth_engine,
            self.components.mlx_server
        )
        self.components.tools.register_tool("file_analysis", self.tools["file_analysis"])
        
        self.logger.info(f"Initialized {len(self.tools)} FREEDOM tools")
    
    def _create_default_agents(self):
        """Create default agents with appropriate tools"""
        # Truth Verifier
        if "truth_verification" in self.tools and "mlx_inference" in self.tools:
            self.agent_manager.create_agent(
                AgentRole.TRUTH_VERIFIER.value,
                [self.tools["truth_verification"], self.tools["mlx_inference"]]
            )
        
        # Data Analyst
        if "file_analysis" in self.tools and "mlx_inference" in self.tools:
            self.agent_manager.create_agent(
                AgentRole.DATA_ANALYST.value,
                [self.tools["file_analysis"], self.tools["mlx_inference"]]
            )
        
        # Researcher
        if "mlx_inference" in self.tools and "file_analysis" in self.tools:
            self.agent_manager.create_agent(
                AgentRole.RESEARCHER.value,
                [self.tools["mlx_inference"], self.tools["file_analysis"]]
            )
        
        # QA Specialist
        if "truth_verification" in self.tools and "mlx_inference" in self.tools:
            self.agent_manager.create_agent(
                AgentRole.QA_SPECIALIST.value,
                [self.tools["truth_verification"], self.tools["mlx_inference"]]
            )
        
        self.logger.info(f"Created {len(self.agent_manager.registry.created_agents)} default agents")
    
    async def execute_crew_task(self, task_description: str, expected_output: str,
                               agent_roles: List[str], 
                               process: Process = Process.sequential) -> Dict[str, Any]:
        """Execute a task using a crew of agents"""
        self.logger.info(f"Executing crew task: {task_description}")
        
        # Get agents
        agents = []
        for role in agent_roles:
            agent = self.agent_manager.registry.get_agent(role)
            if agent:
                agents.append(agent)
            else:
                self.logger.warning(f"Agent role {role} not found")
        
        if not agents:
            return {
                "success": False,
                "error": "No valid agents found",
                "agents_requested": agent_roles
            }
        
        # Create task config
        task_config = TaskConfig(
            description=task_description,
            expected_output=expected_output
        )
        
        # Create task
        task = self.task_executor.create_task(task_config)
        
        # Log task to database
        await self.database.log_task(
            task_id=task_config.description[:16],  # Simple ID
            description=task_description,
            expected_output=expected_output,
            agents=[agent.role for agent in agents]
        )
        
        # Execute task
        crew_process = CrewProcess.SEQUENTIAL if process == Process.sequential else CrewProcess.HIERARCHICAL
        result = await self.task_executor.execute_task(task, agents, crew_process)
        
        # Update database
        await self.database.update_task_status(
            task_id=result.task_id,
            status=result.status,
            result=str(result.output) if result.output else None,
            error=result.error
        )
        
        # Submit to truth engine if available
        if self.components.truth_engine and result.successful:
            self.components.truth_engine.submit_claim(
                source_id="FREEDOMCrewSystem",
                claim_text=f"Crew task completed with {len(agents)} agents",
                claim_type="COMPUTATIONAL",
                evidence={
                    "task_id": result.task_id,
                    "agents": result.agents_used,
                    "execution_time": result.execution_time
                }
            )
        
        return {
            "success": result.successful,
            "result": result.output,
            "execution_time": result.execution_time,
            "agents_used": result.agents_used,
            "task_id": result.task_id,
            "error": result.error
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        # Get component status
        component_status = self.components.get_component_status()
        
        # Get agent status
        available_agents = self.agent_manager.registry.list_available_agents()
        created_agents = list(self.agent_manager.registry.created_agents.keys())
        
        # Get task executor stats
        executor_stats = self.task_executor.get_execution_stats()
        
        # Get database stats
        db_stats = self.database.get_task_statistics()
        
        return {
            "initialized": self._initialized,
            "components": component_status,
            "agents": {
                "available": available_agents,
                "created": created_agents,
                "total": len(available_agents)
            },
            "tools": {
                "registered": self.components.tools.list_tools(),
                "total": len(self.components.tools.tools)
            },
            "executor": executor_stats,
            "database": db_stats
        }
    
    async def batch_execute_tasks(self, task_configs: List[Dict[str, Any]], 
                                max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """Execute multiple tasks in parallel"""
        self.logger.info(f"Executing {len(task_configs)} tasks in batch")
        
        # Convert to TaskConfig objects
        configs = []
        for config in task_configs:
            configs.append(TaskConfig(
                description=config["description"],
                expected_output=config["expected_output"]
            ))
        
        # Get agents for execution
        agent_roles = task_configs[0].get("agents", [AgentRole.RESEARCHER.value])
        agents = []
        for role in agent_roles:
            agent = self.agent_manager.registry.get_agent(role)
            if agent:
                agents.append(agent)
        
        if not agents:
            return [{"success": False, "error": "No agents available"} for _ in configs]
        
        # Execute batch
        results = await self.task_executor.execute_batch_tasks(
            configs, agents, max_concurrent=max_concurrent
        )
        
        # Convert results
        output = []
        for result in results:
            output.append({
                "success": result.successful,
                "task_id": result.task_id,
                "output": result.output,
                "error": result.error,
                "execution_time": result.execution_time
            })
        
        return output


async def demo_simplified_crew_system():
    """Demonstrate the simplified CrewAI system"""
    print("🤝 FREEDOM CrewAI System Demo (Refactored)")
    print("=" * 50)
    
    # Create system with async context manager
    async with FREEDOMCrewSystem() as system:
        # Show system status
        status = system.get_system_status()
        print(f"\n📊 System Status:")
        print(f"  Components: {status['components']}")
        print(f"  Agents: {status['agents']['total']} available")
        print(f"  Tools: {status['tools']['total']} registered")
        
        # Example 1: Simple task
        print("\n📋 Example 1: Truth Verification Task")
        result1 = await system.execute_crew_task(
            task_description="Verify the claim: 'The FREEDOM project uses modular architecture'",
            expected_output="Verification result with evidence",
            agent_roles=[AgentRole.TRUTH_VERIFIER.value]
        )
        print(f"Result: {'✅ Success' if result1['success'] else '❌ Failed'}")
        print(f"Execution time: {result1['execution_time']:.2f}s")
        
        # Example 2: Multi-agent collaboration
        print("\n📋 Example 2: Research + QA Task")
        result2 = await system.execute_crew_task(
            task_description="Research best practices for AI system architecture and verify quality",
            expected_output="Research report with quality assurance verification",
            agent_roles=[AgentRole.RESEARCHER.value, AgentRole.QA_SPECIALIST.value],
            process=Process.sequential
        )
        print(f"Result: {'✅ Success' if result2['success'] else '❌ Failed'}")
        print(f"Agents used: {result2['agents_used']}")
        
        # Example 3: Batch execution
        print("\n📋 Example 3: Batch Task Execution")
        batch_tasks = [
            {
                "description": "Analyze system performance metrics",
                "expected_output": "Performance analysis report",
                "agents": [AgentRole.DATA_ANALYST.value]
            },
            {
                "description": "Research optimization strategies",
                "expected_output": "Optimization recommendations",
                "agents": [AgentRole.RESEARCHER.value]
            },
            {
                "description": "Verify data integrity",
                "expected_output": "Data integrity verification report",
                "agents": [AgentRole.TRUTH_VERIFIER.value]
            }
        ]
        
        batch_results = await system.batch_execute_tasks(batch_tasks, max_concurrent=2)
        successful = sum(1 for r in batch_results if r['success'])
        print(f"Batch results: {successful}/{len(batch_results)} successful")
        
        # Final status
        final_status = system.get_system_status()
        print(f"\n📊 Final Statistics:")
        print(f"  Total tasks executed: {final_status['executor'].get('total_tasks', 0)}")
        print(f"  Success rate: {final_status['executor'].get('success_rate', 0):.1%}")
        print(f"  Average execution time: {final_status['executor'].get('average_execution_time', 0):.2f}s")
        
    print("\n✅ Simplified CrewAI System Demo Complete!")
    print("\nModular Components:")
    print("  • AgentManager: Centralized agent lifecycle")
    print("  • TaskExecutor: Simplified task execution")
    print("  • DatabaseService: Persistent storage")
    print("  • SystemComponents: Shared resource management")


if __name__ == "__main__":
    asyncio.run(demo_simplified_crew_system())