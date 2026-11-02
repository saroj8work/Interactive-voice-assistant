"""
Central Tool Registry for the Voice Agent.
Manages discovery, validation, and safe dispatching of tool executions.
"""
from typing import Dict, List, Any
from app.tools.base import BaseTool, ToolResult
from app.tools.weather import WeatherTool
from app.tools.system import SystemTool
from app.tools.notes import NoteTool
from app.tools.timer import TimerTool
from app.tools.calculator import CalculatorTool
from app.tools.search import KnowledgeSearchTool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self.register(WeatherTool())
        self.register(SystemTool())
        self.register(NoteTool())
        self.register(TimerTool())
        self.register(CalculatorTool())
        self.register(KnowledgeSearchTool())

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def execute_tool(self, name: str, params: Dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found",
                message=f"Agent error: Tool '{name}' is not registered.",
            )
        try:
            return tool.execute(**params)
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                message=f"Execution error in '{name}': {str(e)}",
            )


# Global singleton registry
tool_registry = ToolRegistry()
