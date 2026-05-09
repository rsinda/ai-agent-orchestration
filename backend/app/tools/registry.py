from typing import Any

from backend.app.tools.base import RuntimeTool, ToolResult, ToolSpec
from backend.app.tools.calculator import CalculatorTool
from backend.app.tools.current_time import CurrentTimeTool
from backend.app.tools.text_stats import TextStatsTool
from backend.app.tools.web_search import WebSearchTool


class ToolRegistry:
    def __init__(self, tools: list[RuntimeTool] | None = None) -> None:
        tool_list = tools or [CalculatorTool(), WebSearchTool(), CurrentTimeTool(), TextStatsTool()]
        self._tools = {tool.spec.name: tool for tool in tool_list}

    def specs(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Unknown tool '{name}'. Available tools: {', '.join(self.names())}")
        return await tool.run(arguments)


default_tool_registry = ToolRegistry()

