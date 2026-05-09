from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from backend.app.tools.base import RuntimeTool, ToolResult, ToolSpec


class CurrentTimeTool(RuntimeTool):
    spec = ToolSpec(
        name="current_time",
        description="Return the current date and time for a timezone.",
        input_schema={
            "type": "object",
            "properties": {"timezone": {"type": "string", "default": "UTC"}},
        },
    )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        timezone_name = str(arguments.get("timezone") or "UTC")
        try:
            tz = ZoneInfo(timezone_name)
        except Exception:
            tz = UTC
            timezone_name = "UTC"
        now = datetime.now(tz)
        return ToolResult(
            content=f"Current time in {timezone_name}: {now.isoformat(timespec='seconds')}",
            data={"timezone": timezone_name, "iso": now.isoformat(timespec="seconds")},
        )

