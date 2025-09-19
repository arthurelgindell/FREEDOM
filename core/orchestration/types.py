"""
Common types and enums for the orchestration system
"""

from enum import Enum

class ModelType(Enum):
    LOCAL_MLX = "local_mlx"
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"

class TaskType(Enum):
    CODE_GENERATION = "code_generation"
    CODE_REFACTOR = "code_refactor"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    COMPLETION = "completion"
    CREATIVE = "creative"

