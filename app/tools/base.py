"""
Base Tool definition for Agent Actions.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    message: str = ""
    error: str = ""


class BaseTool(ABC):
    """
    Abstract base class for all tools available to the action planner and agent.
    """
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with supplied keyword arguments.
        """
        pass
