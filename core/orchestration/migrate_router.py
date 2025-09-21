"""
Migration Router - Backwards Compatibility Wrapper
Provides legacy compatibility for model router transitions
"""

from typing import Dict, Any, Optional, List
from .types import ModelType, TaskType


class BackwardsCompatibleRouter:
    """
    Legacy router wrapper maintaining compatibility with existing code.
    Redirects to microservices architecture for actual functionality.
    """

    def __init__(self):
        self.legacy_mode = True
        self.microservice_endpoint = "http://localhost:8080"

    async def route_request(self, task_type: TaskType, **kwargs) -> Dict[str, Any]:
        """
        Legacy routing method - now redirects to microservices
        """
        return {
            "status": "legacy_compatibility",
            "message": "Router migrated to microservices",
            "redirect_to": f"{self.microservice_endpoint}/api/v1/inference",
            "task_type": task_type.value if hasattr(task_type, 'value') else str(task_type)
        }

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Legacy model listing - now redirects to microservices
        """
        return [
            {
                "name": "microservice_api",
                "endpoint": f"{self.microservice_endpoint}/api/v1/models",
                "status": "active"
            }
        ]

    def select_model(self, task_type: TaskType, constraints: Optional[Dict] = None) -> str:
        """
        Legacy model selection - returns microservice endpoint
        """
        return "microservice_gateway"

    async def health_check(self) -> Dict[str, Any]:
        """
        Health check for backwards compatibility
        """
        return {
            "status": "legacy_compatible",
            "migration_status": "completed",
            "active_endpoint": self.microservice_endpoint
        }