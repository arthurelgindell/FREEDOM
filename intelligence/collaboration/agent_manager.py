#!/usr/bin/env python3
"""
Agent Manager for CrewAI System
Handles agent creation, registration, and lifecycle management
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

from crewai import Agent, Tool
from crewai.tools import BaseTool


class AgentRole(Enum):
    """Standard agent roles in the system"""
    TRUTH_VERIFIER = "truth_verifier"
    DATA_ANALYST = "data_analyst"
    RESEARCHER = "researcher"
    QA_SPECIALIST = "qa_specialist"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """Configuration for creating an agent"""
    role: str
    goal: str
    backstory: str
    tools: List[BaseTool] = field(default_factory=list)
    verbose: bool = True
    allow_delegation: bool = False
    max_iter: int = 10
    memory: bool = True
    
    @classmethod
    def from_role(cls, role: AgentRole, tools: List[BaseTool]) -> 'AgentConfig':
        """Create agent config from predefined role"""
        configs = {
            AgentRole.TRUTH_VERIFIER: cls(
                role="Truth Verification Specialist",
                goal="Verify claims and ensure truth accuracy in all operations",
                backstory="""You are a specialized AI agent focused on truth verification. 
                Your primary responsibility is to verify claims using the FREEDOM Truth Engine 
                and ensure all information is accurate and trustworthy. You maintain the highest 
                standards of truth and transparency.""",
                tools=tools,
                allow_delegation=False
            ),
            AgentRole.DATA_ANALYST: cls(
                role="Data Analysis Specialist",
                goal="Analyze data and extract meaningful insights",
                backstory="""You are a specialized AI agent focused on data analysis. 
                Your expertise lies in analyzing files, extracting information, and providing 
                insights. You work with various data formats and maintain data integrity.""",
                tools=tools,
                allow_delegation=False
            ),
            AgentRole.RESEARCHER: cls(
                role="Research Specialist",
                goal="Conduct research and generate comprehensive reports",
                backstory="""You are a specialized AI agent focused on research and analysis. 
                Your role is to gather information, analyze data, and generate comprehensive 
                reports. You excel at synthesizing information from multiple sources.""",
                tools=tools,
                allow_delegation=True
            ),
            AgentRole.QA_SPECIALIST: cls(
                role="Quality Assurance Specialist",
                goal="Ensure quality and accuracy of all outputs",
                backstory="""You are a specialized AI agent focused on quality assurance. 
                Your role is to review outputs, verify accuracy, and ensure all work meets 
                the highest standards. You maintain quality control throughout the process.""",
                tools=tools,
                allow_delegation=False
            )
        }
        
        return configs.get(role, cls(
            role="Custom Agent",
            goal="Perform specialized tasks",
            backstory="You are a specialized AI agent.",
            tools=tools
        ))


class AgentRegistry:
    """Registry for managing available agent types"""
    
    def __init__(self):
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.created_agents: Dict[str, Agent] = {}
        self.logger = logging.getLogger(__name__)
        
        # Register default agents
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register standard agent configurations"""
        for role in AgentRole:
            if role != AgentRole.CUSTOM:
                self.register_agent_config(role.value, AgentConfig.from_role(role, []))
    
    def register_agent_config(self, agent_id: str, config: AgentConfig):
        """Register an agent configuration"""
        self.agent_configs[agent_id] = config
        self.logger.info(f"Registered agent config: {agent_id}")
    
    def create_agent(self, agent_id: str, tools: Optional[List[BaseTool]] = None) -> Agent:
        """Create an agent instance from configuration"""
        if agent_id not in self.agent_configs:
            raise ValueError(f"Unknown agent type: {agent_id}")
        
        config = self.agent_configs[agent_id]
        
        # Override tools if provided
        if tools:
            config = AgentConfig(
                role=config.role,
                goal=config.goal,
                backstory=config.backstory,
                tools=tools,
                verbose=config.verbose,
                allow_delegation=config.allow_delegation,
                max_iter=config.max_iter,
                memory=config.memory
            )
        
        # Create agent
        agent = Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=config.tools,
            verbose=config.verbose,
            allow_delegation=config.allow_delegation,
            max_iter=config.max_iter,
            memory=config.memory
        )
        
        # Cache created agent
        self.created_agents[agent_id] = agent
        self.logger.info(f"Created agent: {agent_id}")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get a previously created agent"""
        return self.created_agents.get(agent_id)
    
    def list_available_agents(self) -> List[str]:
        """List all available agent types"""
        return list(self.agent_configs.keys())
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an agent type"""
        if agent_id not in self.agent_configs:
            return None
        
        config = self.agent_configs[agent_id]
        return {
            "id": agent_id,
            "role": config.role,
            "goal": config.goal,
            "backstory": config.backstory,
            "allow_delegation": config.allow_delegation,
            "max_iter": config.max_iter,
            "memory": config.memory
        }


class AgentManager:
    """High-level manager for agent operations"""
    
    def __init__(self, registry: Optional[AgentRegistry] = None):
        self.registry = registry or AgentRegistry()
        self.logger = logging.getLogger(__name__)
    
    def create_agent(self, role: str, tools: List[BaseTool], 
                    custom_config: Optional[AgentConfig] = None) -> Agent:
        """Create an agent with specified role and tools"""
        if custom_config:
            # Register custom config temporarily
            self.registry.register_agent_config(f"custom_{role}", custom_config)
            return self.registry.create_agent(f"custom_{role}", tools)
        else:
            # Use predefined role
            return self.registry.create_agent(role, tools)
    
    def create_agent_team(self, roles: List[str], shared_tools: List[BaseTool]) -> Dict[str, Agent]:
        """Create a team of agents with shared tools"""
        team = {}
        
        for role in roles:
            try:
                agent = self.create_agent(role, shared_tools)
                team[role] = agent
            except Exception as e:
                self.logger.error(f"Failed to create agent {role}: {e}")
        
        self.logger.info(f"Created agent team with {len(team)} agents")
        return team
    
    def get_agent_capabilities(self, agent: Agent) -> Dict[str, Any]:
        """Get detailed capabilities of an agent"""
        return {
            "role": agent.role,
            "goal": agent.goal,
            "tools": [tool.name for tool in agent.tools] if hasattr(agent, 'tools') else [],
            "allow_delegation": agent.allow_delegation if hasattr(agent, 'allow_delegation') else False,
            "max_iterations": agent.max_iter if hasattr(agent, 'max_iter') else 10,
            "has_memory": agent.memory if hasattr(agent, 'memory') else False
        }
    
    def update_agent_tools(self, agent: Agent, new_tools: List[BaseTool]):
        """Update an agent's available tools"""
        if hasattr(agent, 'tools'):
            agent.tools = new_tools
            self.logger.info(f"Updated tools for agent: {agent.role}")
        else:
            self.logger.warning(f"Agent {agent.role} does not support tool updates")
    
    def clone_agent(self, agent: Agent, new_role: Optional[str] = None) -> Agent:
        """Create a copy of an agent with optional modifications"""
        config = AgentConfig(
            role=new_role or agent.role,
            goal=agent.goal,
            backstory=agent.backstory if hasattr(agent, 'backstory') else "",
            tools=agent.tools if hasattr(agent, 'tools') else [],
            verbose=agent.verbose if hasattr(agent, 'verbose') else True,
            allow_delegation=agent.allow_delegation if hasattr(agent, 'allow_delegation') else False
        )
        
        return Agent(
            role=config.role,
            goal=config.goal,
            backstory=config.backstory,
            tools=config.tools,
            verbose=config.verbose,
            allow_delegation=config.allow_delegation
        )
