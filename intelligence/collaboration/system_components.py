#!/usr/bin/env python3
"""
System Components for CrewAI
Centralized component management and initialization
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging

from crewai.tools import BaseTool

# Import FREEDOM components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "core" / "truth_engine"))
sys.path.append(str(Path(__file__).parent.parent / "inference_engine"))

try:
    from truth_engine import TruthEngine
    from mlx_model_server import MLXModelServer
except ImportError:
    # Mock imports for development
    class TruthEngine:
        def __init__(self): pass
        def verify_claim(self, claim): return {"verified": True, "confidence": 0.9}
        def submit_claim(self, **kwargs): pass
    
    class MLXModelServer:
        def __init__(self, workspace_path): pass
        def get_available_models(self): return []
        def generate_response(self, **kwargs): return {"response": "Mock response"}


@dataclass
class CrewAIConfig:
    """Configuration for CrewAI system"""
    workspace_path: str = "/Volumes/DATA/FREEDOM"
    enable_truth_engine: bool = True
    enable_mlx_server: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    database_path: Optional[str] = None
    
    @property
    def truth_engine_config(self) -> Dict[str, Any]:
        """Truth engine configuration"""
        return {
            "enabled": self.enable_truth_engine,
            "workspace": self.workspace_path
        }
    
    @property
    def mlx_config(self) -> Dict[str, Any]:
        """MLX server configuration"""
        return {
            "enabled": self.enable_mlx_server,
            "workspace": self.workspace_path
        }


class ToolRegistry:
    """Registry for CrewAI tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool"""
        self.tools[name] = tool
        self.logger.info(f"Registered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tools"""
        return list(self.tools.keys())
    
    def get_tools_by_capability(self, capability: str) -> List[BaseTool]:
        """Get tools by capability"""
        matching_tools = []
        for tool in self.tools.values():
            if hasattr(tool, 'description') and capability.lower() in tool.description.lower():
                matching_tools.append(tool)
        return matching_tools


class SystemComponents:
    """Container for all system components"""
    
    def __init__(self, config: CrewAIConfig):
        self.config = config
        self.logger = self._setup_logging()
        
        # Initialize components
        self.truth_engine: Optional[TruthEngine] = None
        self.mlx_server: Optional[MLXModelServer] = None
        self.tools = ToolRegistry()
        
        # Component initialization happens in initialize()
        self._initialized = False
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        if self.config.enable_logging:
            logging.basicConfig(
                level=getattr(logging, self.config.log_level),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        return logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize all components"""
        if self._initialized:
            return
        
        self.logger.info("Initializing system components")
        
        # Initialize Truth Engine
        if self.config.enable_truth_engine:
            try:
                self.truth_engine = TruthEngine()
                self.logger.info("Truth Engine initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Truth Engine: {e}")
                self.truth_engine = None
        
        # Initialize MLX Server
        if self.config.enable_mlx_server:
            try:
                self.mlx_server = MLXModelServer(self.config.workspace_path)
                self.logger.info("MLX Model Server initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize MLX Server: {e}")
                self.mlx_server = None
        
        self._initialized = True
        self.logger.info("System components initialized")
    
    async def cleanup(self):
        """Cleanup all components"""
        self.logger.info("Cleaning up system components")
        
        # Cleanup components that need it
        # (Most components handle their own cleanup)
        
        self._initialized = False
        self.logger.info("System components cleaned up")
    
    def get_component_status(self) -> Dict[str, bool]:
        """Get status of all components"""
        return {
            "truth_engine": self.truth_engine is not None,
            "mlx_server": self.mlx_server is not None,
            "tools_registered": len(self.tools.tools) > 0,
            "initialized": self._initialized
        }
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """Validate system configuration"""
        issues = []
        
        # Check workspace path
        workspace = Path(self.config.workspace_path)
        if not workspace.exists():
            issues.append(f"Workspace path does not exist: {self.config.workspace_path}")
        
        # Check database path if specified
        if self.config.database_path:
            db_path = Path(self.config.database_path)
            if not db_path.parent.exists():
                issues.append(f"Database directory does not exist: {db_path.parent}")
        
        # Check component dependencies
        if self.config.enable_truth_engine and not self._check_truth_engine_available():
            issues.append("Truth Engine is enabled but not available")
        
        if self.config.enable_mlx_server and not self._check_mlx_server_available():
            issues.append("MLX Server is enabled but not available")
        
        return len(issues) == 0, issues
    
    def _check_truth_engine_available(self) -> bool:
        """Check if Truth Engine is available"""
        try:
            # Try to import and instantiate
            engine = TruthEngine()
            return True
        except Exception:
            return False
    
    def _check_mlx_server_available(self) -> bool:
        """Check if MLX Server is available"""
        try:
            # Try to import and instantiate
            server = MLXModelServer(self.config.workspace_path)
            return True
        except Exception:
            return False


class ComponentFactory:
    """Factory for creating system components with dependencies"""
    
    @staticmethod
    def create_default_components(workspace_path: str = "/Volumes/DATA/FREEDOM") -> SystemComponents:
        """Create system components with default configuration"""
        config = CrewAIConfig(workspace_path=workspace_path)
        return SystemComponents(config)
    
    @staticmethod
    def create_minimal_components(workspace_path: str = "/Volumes/DATA/FREEDOM") -> SystemComponents:
        """Create minimal system components (no external dependencies)"""
        config = CrewAIConfig(
            workspace_path=workspace_path,
            enable_truth_engine=False,
            enable_mlx_server=False
        )
        return SystemComponents(config)
    
    @staticmethod
    def create_testing_components() -> SystemComponents:
        """Create components for testing"""
        config = CrewAIConfig(
            workspace_path="/tmp/freedom_test",
            enable_truth_engine=True,
            enable_mlx_server=True,
            enable_logging=False
        )
        return SystemComponents(config)
