"""
Configuration management for the orchestration system.
Separates configuration from routing logic for better maintainability.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from .types import ModelType, TaskType


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    model_type: ModelType
    model_name: str
    endpoint: str
    max_tokens: int
    temperature: float
    cost_per_input_token: float
    cost_per_output_token: float
    timeout: int = 30
    retry_count: int = 3
    rate_limit_rpm: int = 60  # Requests per minute
    capabilities: List[TaskType] = field(default_factory=list)


@dataclass
class EscalationRule:
    """Rule for escalating from one model to another"""
    from_model: ModelType
    to_model: ModelType
    failure_threshold: int
    complexity_threshold: int
    task_types: List[TaskType]


class RouterConfig:
    """Central configuration for the model router"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "router_config.json"
        self.models: Dict[ModelType, ModelConfig] = {}
        self.escalation_rules: List[EscalationRule] = []
        self.task_preferences: Dict[TaskType, List[ModelType]] = {}
        self.circuit_breaker_config = {
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "half_open_attempts": 3
        }
        self.cache_config = {
            "ttl": 3600,  # 1 hour
            "max_entries": 1000,
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
        }
        self.performance_config = {
            "metrics_window_size": 100,
            "min_samples_for_stats": 10,
            "outlier_percentile": 99
        }

        self._load_config()

    def _load_config(self):
        """Load configuration from environment and files"""
        # Load default model configs
        self._load_default_models()

        # Load escalation rules
        self._load_escalation_rules()

        # Load task preferences
        self._load_task_preferences()

        # Override with config file if exists
        if self.config_path.exists():
            self._load_from_file()

        # Override with environment variables
        self._load_from_environment()

    def _load_default_models(self):
        """Load default model configurations"""
        # Get base URLs from environment
        lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")

        self.models = {
            ModelType.LOCAL_MLX: ModelConfig(
                model_type=ModelType.LOCAL_MLX,
                model_name="auto",  # Will be detected dynamically
                endpoint=f"{lm_studio_url}/chat/completions",
                max_tokens=4096,
                temperature=0.7,
                cost_per_input_token=0.0,
                cost_per_output_token=0.0,
                timeout=30,
                retry_count=2,
                rate_limit_rpm=1000,  # Local has higher limit
                capabilities=[TaskType.CODE_GENERATION, TaskType.CODE_REFACTOR,
                            TaskType.COMPLETION, TaskType.ANALYSIS]
            ),
            ModelType.CLAUDE: ModelConfig(
                model_type=ModelType.CLAUDE,
                model_name=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
                endpoint="https://api.anthropic.com/v1/messages",
                max_tokens=8192,
                temperature=0.0,
                cost_per_input_token=0.000003,  # $3 per million
                cost_per_output_token=0.000015,  # $15 per million
                timeout=60,
                retry_count=3,
                rate_limit_rpm=50,
                capabilities=[TaskType.REASONING, TaskType.ANALYSIS,
                            TaskType.CREATIVE, TaskType.CODE_REFACTOR]
            ),
            ModelType.OPENAI: ModelConfig(
                model_type=ModelType.OPENAI,
                model_name=os.getenv("OPENAI_MODEL", "gpt-4o"),
                endpoint="https://api.openai.com/v1/chat/completions",
                max_tokens=4096,
                temperature=0.0,
                cost_per_input_token=0.0000025,  # $2.50 per million
                cost_per_output_token=0.00001,    # $10 per million
                timeout=45,
                retry_count=3,
                rate_limit_rpm=60,
                capabilities=[TaskType.CODE_GENERATION, TaskType.COMPLETION,
                            TaskType.ANALYSIS, TaskType.CREATIVE]
            ),
            ModelType.GEMINI: ModelConfig(
                model_type=ModelType.GEMINI,
                model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
                endpoint="https://generativelanguage.googleapis.com/v1/models",
                max_tokens=8192,
                temperature=0.0,
                cost_per_input_token=0.00000125,  # $1.25 per million
                cost_per_output_token=0.000005,    # $5 per million
                timeout=60,
                retry_count=3,
                rate_limit_rpm=40,
                capabilities=[TaskType.REASONING, TaskType.ANALYSIS,
                            TaskType.CREATIVE, TaskType.CODE_GENERATION]
            )
        }

    def _load_escalation_rules(self):
        """Load default escalation rules"""
        self.escalation_rules = [
            EscalationRule(
                from_model=ModelType.LOCAL_MLX,
                to_model=ModelType.OPENAI,
                failure_threshold=2,
                complexity_threshold=7,
                task_types=[TaskType.CODE_GENERATION, TaskType.COMPLETION]
            ),
            EscalationRule(
                from_model=ModelType.LOCAL_MLX,
                to_model=ModelType.CLAUDE,
                failure_threshold=2,
                complexity_threshold=7,
                task_types=[TaskType.REASONING, TaskType.ANALYSIS]
            ),
            EscalationRule(
                from_model=ModelType.OPENAI,
                to_model=ModelType.CLAUDE,
                failure_threshold=3,
                complexity_threshold=9,
                task_types=[TaskType.REASONING, TaskType.ANALYSIS]
            ),
            EscalationRule(
                from_model=ModelType.GEMINI,
                to_model=ModelType.CLAUDE,
                failure_threshold=3,
                complexity_threshold=8,
                task_types=[TaskType.REASONING, TaskType.CODE_REFACTOR]
            )
        ]

    def _load_task_preferences(self):
        """Load default task preferences"""
        self.task_preferences = {
            TaskType.CODE_GENERATION: [ModelType.LOCAL_MLX, ModelType.OPENAI, ModelType.CLAUDE],
            TaskType.CODE_REFACTOR: [ModelType.LOCAL_MLX, ModelType.CLAUDE, ModelType.OPENAI],
            TaskType.REASONING: [ModelType.CLAUDE, ModelType.GEMINI, ModelType.OPENAI],
            TaskType.ANALYSIS: [ModelType.CLAUDE, ModelType.GEMINI, ModelType.LOCAL_MLX],
            TaskType.COMPLETION: [ModelType.OPENAI, ModelType.LOCAL_MLX, ModelType.CLAUDE],
            TaskType.CREATIVE: [ModelType.CLAUDE, ModelType.GEMINI, ModelType.OPENAI]
        }

    def _load_from_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)

                # Update model configs
                if "models" in config_data:
                    for model_type_str, model_config in config_data["models"].items():
                        model_type = ModelType(model_type_str)
                        if model_type in self.models:
                            # Update existing config
                            for key, value in model_config.items():
                                if hasattr(self.models[model_type], key):
                                    setattr(self.models[model_type], key, value)

                # Update other configs
                if "circuit_breaker" in config_data:
                    self.circuit_breaker_config.update(config_data["circuit_breaker"])

                if "cache" in config_data:
                    self.cache_config.update(config_data["cache"])

                if "performance" in config_data:
                    self.performance_config.update(config_data["performance"])

        except FileNotFoundError:
            pass  # Use defaults
        except json.JSONDecodeError as e:
            print(f"Error loading config file: {e}")

    def _load_from_environment(self):
        """Override configuration with environment variables"""
        # Update Redis URL if set
        if redis_url := os.getenv("REDIS_URL"):
            self.cache_config["redis_url"] = redis_url

        # Update API keys and endpoints
        if claude_key := os.getenv("ANTHROPIC_API_KEY"):
            # Key is handled by the client, but we can validate it exists
            pass

        if openai_key := os.getenv("OPENAI_API_KEY"):
            # Key is handled by the client
            pass

        if gemini_key := os.getenv("GOOGLE_API_KEY"):
            # Key is handled by the client
            pass

    def get_model_config(self, model_type: ModelType) -> ModelConfig:
        """Get configuration for a specific model"""
        return self.models.get(model_type)

    def get_escalation_path(self, from_model: ModelType, task_type: TaskType) -> Optional[ModelType]:
        """Get the next model in the escalation path"""
        for rule in self.escalation_rules:
            if rule.from_model == from_model and task_type in rule.task_types:
                return rule.to_model
        return None

    def get_preferred_models(self, task_type: TaskType) -> List[ModelType]:
        """Get preferred models for a task type"""
        return self.task_preferences.get(task_type, [ModelType.LOCAL_MLX])

    def save_to_file(self, path: Optional[Path] = None):
        """Save current configuration to file"""
        save_path = path or self.config_path

        config_data = {
            "models": {
                model_type.value: {
                    "model_name": config.model_name,
                    "endpoint": config.endpoint,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "cost_per_input_token": config.cost_per_input_token,
                    "cost_per_output_token": config.cost_per_output_token,
                    "timeout": config.timeout,
                    "retry_count": config.retry_count,
                    "rate_limit_rpm": config.rate_limit_rpm
                }
                for model_type, config in self.models.items()
            },
            "circuit_breaker": self.circuit_breaker_config,
            "cache": self.cache_config,
            "performance": self.performance_config
        }

        with open(save_path, 'w') as f:
            json.dump(config_data, f, indent=2)